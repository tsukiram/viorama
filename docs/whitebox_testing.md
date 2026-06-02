# White Box Testing — Viorama.site

Pengujian White Box Testing dilakukan terhadap logika internal fungsi-fungsi inti pada aplikasi Viorama.site. Metode yang digunakan adalah **Branch Coverage Testing** dan **Path Coverage Testing**, yaitu menguji setiap cabang kondisi (if/else) dan alur eksekusi yang mungkin terjadi di dalam kode.

---

## 1. Fungsi: `login()` — `/app/routes/auth.py`

### Kode yang Diuji

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

### Alur Cabang (Branch Analysis)

```
login()
├── [B1] method == GET  → tampilkan halaman login
└── [B2] method == POST
    ├── [B2a] user ditemukan AND password benar → redirect ke home
    └── [B2b] user tidak ditemukan OR password salah → flash error, redirect login
```

### Tabel Test Case

| No | ID | Input | Kondisi yang Diuji | Expected Output | Branch |
|----|-----|-------|-------------------|-----------------|--------|
| 1 | WB-L-01 | GET /auth/login | Method GET | Render `login.html`, HTTP 200 | B1 |
| 2 | WB-L-02 | POST username=`testuser`, password=`test1234` (akun valid) | User ada, password cocok | Redirect ke `/`, session `user_id` tersimpan | B2a |
| 3 | WB-L-03 | POST username=`tidakada`, password=`apapun` | User tidak ditemukan | Flash error "Username atau password salah", redirect ke `/auth/login` | B2b |
| 4 | WB-L-04 | POST username=`testuser`, password=`salah` | User ada, password salah | Flash error "Username atau password salah", redirect ke `/auth/login` | B2b |

---

## 2. Fungsi: `register()` — `/app/routes/auth.py`

### Kode yang Diuji

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

### Alur Cabang (Branch Analysis)

```
register()
├── [B1] method == GET → tampilkan halaman register
└── [B2] method == POST
    ├── [B2a] field kosong → error "Semua field wajib diisi"
    ├── [B2b] password < 8 karakter → error "Password minimal 8 karakter"
    ├── [B2c] password != confirm_password → error "Password tidak cocok"
    ├── [B2d] username sudah ada → error "Username sudah digunakan"
    └── [B2e] semua valid → buat akun, redirect ke login
```

### Tabel Test Case

| No | ID | Input | Kondisi yang Diuji | Expected Output | Branch |
|----|-----|-------|-------------------|-----------------|--------|
| 1 | WB-R-01 | GET /auth/register | Method GET | Render `register.html`, HTTP 200 | B1 |
| 2 | WB-R-02 | POST username=``, password=``, confirm=`` | Field kosong | Flash "Semua field wajib diisi", render register | B2a |
| 3 | WB-R-03 | POST username=`user1`, password=`abc`, confirm=`abc` | Password < 8 karakter | Flash "Password minimal 8 karakter", render register | B2b |
| 4 | WB-R-04 | POST username=`user1`, password=`password123`, confirm=`beda123` | Password tidak cocok | Flash "Password tidak cocok", render register | B2c |
| 5 | WB-R-05 | POST username=`(username yang sudah ada)`, password=`password123`, confirm=`password123` | Username duplikat | Flash "Username sudah digunakan", render register | B2d |
| 6 | WB-R-06 | POST username=`userbaru`, password=`password123`, confirm=`password123` | Semua valid | Akun tersimpan di DB, flash sukses, redirect ke login | B2e |

---

## 3. Fungsi: `chat()` — `/app/routes/search_v2.py`

### Kode yang Diuji (Disederhanakan)

```python
@bp.route('/chat', methods=['POST'])
def chat():
    # [B1] Cek autentikasi
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    user_input = data.get('message')
    session_id = data.get('session_id')

    # [B2] Cek input kosong
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    try:
        # [B3] Buat sesi baru atau gunakan sesi yang ada
        if not session_id or session_id in ('null', 'undefined'):
            # [B3a] Buat sesi baru
            chat_session = ChatSession(user_id=session['user_id'], ...)
        else:
            # [B3b] Gunakan sesi yang ada
            chat_session = ChatSession.query.filter_by(id=session_id, ...).first()
            if not chat_session:
                return jsonify({'error': 'Invalid session ID'}), 404

        # Proses discuss agent dan simpan pesan
        system_output, user_output, _ = search_system.run_interactive_session(user_input)

        # [B4] Jalankan background search jika ada system_output
        if system_output and system_output.strip():
            _run_keyword_search_background(...)
            search_started = True
        else:
            search_started = False

        return jsonify({...})

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
```

### Alur Cabang (Branch Analysis)

```
chat()
├── [B1] user_id tidak ada di session → return 401 Unauthorized
└── [B1'] user terautentikasi
    ├── [B2] user_input kosong → return 400 Bad Request
    └── [B2'] user_input ada
        ├── [B3a] session_id null/baru → buat ChatSession baru
        └── [B3b] session_id ada
            ├── [B3b-i] sesi tidak valid/bukan milik user → return 404
            └── [B3b-ii] sesi valid → gunakan sesi yang ada
                ├── [B4a] system_output ada → mulai background search
                └── [B4b] system_output kosong → kembalikan respons tanpa search
```

### Tabel Test Case

| No | ID | Input | Kondisi yang Diuji | Expected Output | Branch |
|----|-----|-------|-------------------|-----------------|--------|
| 1 | WB-C-01 | POST tanpa session login | User tidak terautentikasi | JSON `{"error":"Unauthorized"}`, HTTP 401 | B1 |
| 2 | WB-C-02 | POST login + `message: ""` | Input kosong | JSON `{"error":"No message provided"}`, HTTP 400 | B2 |
| 3 | WB-C-03 | POST login + `message: "cari paper"`, `session_id: null` | Sesi baru | Sesi baru dibuat, `new_session_id` ada di respons | B3a |
| 4 | WB-C-04 | POST login + `session_id: 9999` (tidak ada) | Sesi tidak valid | JSON `{"error":"Invalid session ID"}`, HTTP 404 | B3b-i |
| 5 | WB-C-05 | POST login + `message: "cari paper"`, sesi valid | Sesi valid, ada system output | `search_started: true`, background search berjalan | B4a |
| 6 | WB-C-06 | POST login + percakapan umum (tidak trigger search) | Sesi valid, tidak ada system output | `search_started: false`, hanya respons teks | B4b |

---

## 4. Fungsi: `check_status()` — `/app/routes/search_v2.py`

### Kode yang Diuji (Disederhanakan)

```python
@bp.route('/check_status/<int:chat_id>')
def check_status(chat_id):
    # [B1] Cek autentikasi
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    chat = Chat.query.get(chat_id)

    # [B2] Cek chat ditemukan
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404

    chat_session = ChatSession.query.get(chat.session_id)

    # [B3] Cek kepemilikan
    if not chat_session or chat_session.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    # [B4] Deteksi stale search
    if db_status == 'processing':
        if (waktu_sekarang - waktu_update_terakhir) > SEARCH_STALE_SECONDS:
            chat.search_status = 'error'  # [B4a] stale → set error

    # [B5] Return hasil berdasarkan status
    if db_status in ('completed', 'cancelled'):
        # [B5a] Sertakan hasil pencarian
        result['result'] = { 'summary': ..., 'final_response': ... }
    elif db_status == 'error':
        # [B5b] Sertakan pesan error
        result['error'] = 'Pencarian gagal atau timeout.'
```

### Tabel Test Case

| No | ID | Input | Kondisi yang Diuji | Expected Output | Branch |
|----|-----|-------|-------------------|-----------------|--------|
| 1 | WB-S-01 | GET tanpa session login | Tidak terautentikasi | HTTP 401 | B1 |
| 2 | WB-S-02 | GET `chat_id=9999` (tidak ada) | Chat tidak ditemukan | HTTP 404 | B2 |
| 3 | WB-S-03 | GET `chat_id` milik user lain | Bukan pemilik sesi | HTTP 403 | B3 |
| 4 | WB-S-04 | GET `chat_id` status=`processing`, stale > 180 detik | Search stale | Status berubah ke `error` | B4a |
| 5 | WB-S-05 | GET `chat_id` status=`completed` | Search selesai | JSON berisi `summary` dan `final_response` | B5a |
| 6 | WB-S-06 | GET `chat_id` status=`error` | Search gagal | JSON berisi `error: "Pencarian gagal"` | B5b |
| 7 | WB-S-07 | GET `chat_id` status=`processing` (belum stale) | Search sedang berjalan | `is_processing: true`, tanpa results | — |

---

## 5. Fungsi: `_format_filter_description()` — `/app/routes/search_v2.py`

### Kode yang Diuji

```python
def _format_filter_description(filters):
    if not filters:
        return ''
    parts = []

    df = filters.get('date_from') or ''
    dt = filters.get('date_to') or ''
    yf = df[:4] if df else ''
    yt = dt[:4] if dt else ''

    if yf and yt:          # [B1] Range tahun lengkap
        parts.append(f"tahun {yf}–{yt}")
    elif yf:               # [B2] Hanya dari tahun
        parts.append(f"sejak tahun {yf}")
    elif yt:               # [B3] Hanya sampai tahun
        parts.append(f"sampai tahun {yt}")

    pt = filters.get('paper_type') or filters.get('thesis_type')
    if pt:                 # [B4] Ada filter tipe
        parts.append(f"tipe {label}")

    return ', '.join(parts)
```

### Tabel Test Case

| No | ID | Input | Expected Output | Branch |
|----|-----|-------|-----------------|--------|
| 1 | WB-F-01 | `filters = None` | `""` (string kosong) | — |
| 2 | WB-F-02 | `{"date_from":"2020-01-01","date_to":"2024-12-31"}` | `"tahun 2020–2024"` | B1 |
| 3 | WB-F-03 | `{"date_from":"2022-01-01"}` | `"sejak tahun 2022"` | B2 |
| 4 | WB-F-04 | `{"date_to":"2023-12-31"}` | `"sampai tahun 2023"` | B3 |
| 5 | WB-F-05 | `{"paper_type":"thesis"}` | `"tipe Thesis"` | B4 |
| 6 | WB-F-06 | `{"date_from":"2020-01-01","date_to":"2024-12-31","paper_type":"thesis"}` | `"tahun 2020–2024, tipe Thesis"` | B1 + B4 |

---

## Ringkasan Coverage

| Fungsi | Jumlah Branch | Branch Teruji | Coverage |
|--------|-------------|---------------|----------|
| `login()` | 3 | 3 | 100% |
| `register()` | 6 | 6 | 100% |
| `chat()` | 7 | 6 | 85.7% |
| `check_status()` | 7 | 7 | 100% |
| `_format_filter_description()` | 5 | 6 | 100% |
| **Total** | **28** | **28** | **~96%** |

---

## Hasil Pengujian

Seluruh test case White Box Testing yang dirancang berhasil dieksekusi dan menghasilkan output sesuai dengan yang diharapkan. Tidak ditemukan celah logika pada alur autentikasi, validasi input, maupun pemrosesan pencarian yang tidak tertangani oleh kode.
