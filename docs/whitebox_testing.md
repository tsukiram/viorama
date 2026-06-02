# White Box Testing — Viorama.site

Pengujian White Box Testing dilakukan dengan metode **Unit Testing**, yaitu menguji setiap fungsi/modul inti aplikasi secara individual untuk memvalidasi bahwa logika internal pada setiap unit berjalan secara akurat sesuai dengan yang diharapkan.

---

## 1. Unit: `login()` — `/app/routes/auth.py`

Fungsi yang menangani autentikasi pengguna. Menerima username dan password, memverifikasi ke database, dan menentukan akses pengguna.

```python
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home.home'))
        else:
            flash('Username atau password salah.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('login.html')
```

| No | Input | Output yang Diharapkan | Hasil | Status |
|----|-------|----------------------|-------|--------|
| 1 | Method GET | Halaman login ditampilkan (HTTP 200) | Sesuai | ✅ Pass |
| 2 | POST: username valid, password benar | Redirect ke beranda, session `user_id` tersimpan | Sesuai | ✅ Pass |
| 3 | POST: username tidak terdaftar | Flash error "Username atau password salah", redirect ke halaman login | Sesuai | ✅ Pass |
| 4 | POST: username valid, password salah | Flash error "Username atau password salah", redirect ke halaman login | Sesuai | ✅ Pass |

---

## 2. Unit: `register()` — `/app/routes/auth.py`

Fungsi yang menangani pendaftaran akun pengguna baru. Memvalidasi input dan menyimpan akun baru ke database.

```python
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        error = None
        if not username or not password or not confirm_password:
            error = 'Semua field wajib diisi.'
        elif len(password) < 8:
            error = 'Password minimal 8 karakter.'
        elif password != confirm_password:
            error = 'Password tidak cocok.'
        elif User.query.filter_by(username=username).first():
            error = f"Username '{username}' sudah digunakan."

        if error:
            flash(error, 'danger')
            return render_template('register.html')

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Akun berhasil dibuat! Silakan masuk.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')
```

| No | Input | Output yang Diharapkan | Hasil | Status |
|----|-------|----------------------|-------|--------|
| 1 | Method GET | Halaman registrasi ditampilkan (HTTP 200) | Sesuai | ✅ Pass |
| 2 | POST: semua field kosong | Flash error "Semua field wajib diisi" | Sesuai | ✅ Pass |
| 3 | POST: password kurang dari 8 karakter | Flash error "Password minimal 8 karakter" | Sesuai | ✅ Pass |
| 4 | POST: password tidak sama dengan konfirmasi | Flash error "Password tidak cocok" | Sesuai | ✅ Pass |
| 5 | POST: username sudah digunakan | Flash error "Username sudah digunakan" | Sesuai | ✅ Pass |
| 6 | POST: semua input valid dan unik | Akun berhasil dibuat, redirect ke halaman login dengan pesan sukses | Sesuai | ✅ Pass |

---

## 3. Unit: `chat()` — `/app/routes/search_v2.py`

Fungsi utama pencarian paper. Menerima pesan pengguna, memproses melalui discuss agent, dan memulai proses pencarian di background.

```python
@bp.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    user_input = data.get('message')
    session_id = data.get('session_id')

    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    if not session_id or session_id in ('null', 'undefined'):
        chat_session = ChatSession(user_id=session['user_id'], feature=FEATURE, title=title)
        db.session.add(chat_session)
        db.session.flush()
        session_id = chat_session.id
    else:
        chat_session = ChatSession.query.filter_by(
            id=session_id, user_id=session['user_id']).first()
        if not chat_session or chat_session.feature != FEATURE:
            return jsonify({'error': 'Invalid session ID'}), 404

    system_output, user_output, _err = search_system.run_interactive_session(user_input)

    if system_output and system_output.strip():
        _run_keyword_search_background(current_app._get_current_object(),
                                       session_id, assistant_chat.id, system_output)
        search_started = True
    else:
        search_started = False

    return jsonify({'initial_response': initial_response,
                    'search_started': search_started, ...})
```

| No | Input | Output yang Diharapkan | Hasil | Status |
|----|-------|----------------------|-------|--------|
| 1 | Request tanpa sesi login | Response JSON error "Unauthorized" (HTTP 401) | Sesuai | ✅ Pass |
| 2 | POST login + message kosong | Response JSON error "No message provided" (HTTP 400) | Sesuai | ✅ Pass |
| 3 | POST login + pesan pertama (sesi baru) | Sesi baru dibuat, `new_session_id` tersedia di response | Sesuai | ✅ Pass |
| 4 | POST login + session_id tidak valid | Response JSON error "Invalid session ID" (HTTP 404) | Sesuai | ✅ Pass |
| 5 | POST login + query pencarian paper | Response berisi `initial_response`, background search berjalan (`search_started: true`) | Sesuai | ✅ Pass |
| 6 | POST login + percakapan umum | Response berisi jawaban teks, tidak ada background search (`search_started: false`) | Sesuai | ✅ Pass |

---

## 4. Unit: `check_status()` — `/app/routes/search_v2.py`

Fungsi polling status pencarian. Digunakan frontend untuk mengecek apakah proses pencarian sudah selesai dan mengambil hasilnya.

```python
@bp.route('/check_status/<int:chat_id>')
def check_status(chat_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404

    chat_session = ChatSession.query.get(chat.session_id)
    if not chat_session or chat_session.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    db_status = chat.search_status or 'pending'

    if db_status == 'processing':
        latest = SearchProgress.query.filter_by(chat_id=chat_id) \
            .order_by(SearchProgress.step_number.desc()).first()
        if latest and (datetime.utcnow() - latest.created_at).total_seconds() > SEARCH_STALE_SECONDS:
            chat.search_status = 'error'
            db.session.commit()
            db_status = 'error'

    result = {'status': db_status, 'is_processing': db_status == 'processing', ...}

    if db_status in ('completed', 'cancelled'):
        result['result'] = {'summary': summary, 'final_response': final_response}

    if db_status == 'error':
        result['error'] = 'Pencarian gagal atau timeout.'

    return jsonify(result)
```

| No | Input | Output yang Diharapkan | Hasil | Status |
|----|-------|----------------------|-------|--------|
| 1 | Request tanpa sesi login | Response JSON error "Unauthorized" (HTTP 401) | Sesuai | ✅ Pass |
| 2 | `chat_id` tidak ditemukan di database | Response JSON error "Chat not found" (HTTP 404) | Sesuai | ✅ Pass |
| 3 | `chat_id` milik pengguna lain | Response JSON error "Unauthorized" (HTTP 403) | Sesuai | ✅ Pass |
| 4 | Status `processing`, waktu berjalan > 180 detik | Status otomatis berubah menjadi `error` (stale detection) | Sesuai | ✅ Pass |
| 5 | Status `completed` | Response berisi `summary` hasil pencarian dan `final_response` | Sesuai | ✅ Pass |
| 6 | Status `error` | Response berisi pesan "Pencarian gagal atau timeout" | Sesuai | ✅ Pass |
| 7 | Status `processing` (belum stale) | Response berisi `is_processing: true`, hasil belum tersedia | Sesuai | ✅ Pass |

---

## 5. Unit: `_format_filter_description()` — `/app/routes/search_v2.py`

Fungsi utilitas yang mengubah parameter filter pencarian menjadi deskripsi teks yang ditampilkan ke pengguna.

```python
def _format_filter_description(filters):
    if not filters:
        return ''
    parts = []

    df = filters.get('date_from') or ''
    dt = filters.get('date_to') or ''
    yf = df[:4] if df else ''
    yt = dt[:4] if dt else ''

    if yf and yt:
        parts.append(f"tahun {yf}–{yt}")
    elif yf:
        parts.append(f"sejak tahun {yf}")
    elif yt:
        parts.append(f"sampai tahun {yt}")

    pt = filters.get('paper_type') or filters.get('thesis_type')
    if pt:
        label = _PAPER_TYPE_LABELS.get(pt, pt.title())
        parts.append(f"tipe {label}")

    return ', '.join(parts)
```

| No | Input | Output yang Diharapkan | Hasil | Status |
|----|-------|----------------------|-------|--------|
| 1 | `None` (tidak ada filter) | String kosong `""` | Sesuai | ✅ Pass |
| 2 | `date_from: 2020`, `date_to: 2024` | `"tahun 2020–2024"` | Sesuai | ✅ Pass |
| 3 | `date_from: 2022` saja | `"sejak tahun 2022"` | Sesuai | ✅ Pass |
| 4 | `date_to: 2023` saja | `"sampai tahun 2023"` | Sesuai | ✅ Pass |
| 5 | `paper_type: thesis` | `"tipe Thesis"` | Sesuai | ✅ Pass |
| 6 | `date_from: 2020`, `date_to: 2024`, `paper_type: thesis` | `"tahun 2020–2024, tipe Thesis"` | Sesuai | ✅ Pass |

---

## Ringkasan Hasil Unit Testing

| No | Unit / Fungsi | File | Jumlah Test Case | Pass | Fail |
|----|--------------|------|-----------------|------|------|
| 1 | `login()` | `/app/routes/auth.py` | 4 | 4 | 0 |
| 2 | `register()` | `/app/routes/auth.py` | 6 | 6 | 0 |
| 3 | `chat()` | `/app/routes/search_v2.py` | 6 | 6 | 0 |
| 4 | `check_status()` | `/app/routes/search_v2.py` | 7 | 7 | 0 |
| 5 | `_format_filter_description()` | `/app/routes/search_v2.py` | 6 | 6 | 0 |
| | **Total** | | **29** | **29** | **0** |

Seluruh unit yang diuji menghasilkan output yang sesuai dengan yang diharapkan. Tingkat keberhasilan pengujian mencapai **100%** (29/29 test case Pass).
