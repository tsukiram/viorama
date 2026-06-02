# White Box Testing — Viorama.site

Pengujian White Box Testing dilaksanakan menggunakan metode Unit Testing terhadap enam modul utama sistem. Setiap fungsi inti pada masing-masing modul diuji secara independen dengan menyusun skenario test case berdasarkan kelas masukan valid dan tidak valid, kemudian membandingkan keluaran aktual dengan keluaran yang diharapkan. Total terdapat 14 skenario test case yang dieksekusi dalam pengujian White Box Testing ini.

---

## Tabel 1 — Hasil Pengujian Discuss Agent Module

| No | Modul | Fungsi | Kelas Input | Output yang Diharapkan | Output Aktual | Status |
|----|-------|--------|-------------|----------------------|---------------|--------|
| 1 | Discuss Agent | `_initialize_clients()` | API key valid | Klien Discuss Agent dan Search Agent berhasil diinisiasi | Kedua klien berhasil diinisiasi tanpa error | Valid |
| 2 | Discuss Agent | `run_interactive_session()` | Pertanyaan pengguna tentang topik KTI | Dialog diproses, user intent teridentifikasi, respons dikirim ke Search Agent | Dialog berjalan, intent terdeteksi dan diteruskan dengan benar | Valid |

```python
# app/gemini_client/searching_v2.py

def _initialize_clients(self):
    self.api_key = self._get_active_api_key()
    if not self.api_key:
        return False
    self.discuss_client = genai.Client(api_key=self.api_key)
    self.search_client  = genai.Client(api_key=self.api_key)
    return True

def run_interactive_session(self, user_input):
    # Proses input melalui discuss agent, identifikasi intent pencarian
    response = self.discuss_agent.send_message(user_input)
    system_output, user_output = self.process_discuss_response(response.text)
    return system_output, user_output, None
```

---

## Tabel 2 — Hasil Pengujian Search Agent Module

| No | Modul | Fungsi | Kelas Input | Output yang Diharapkan | Output Aktual | Status |
|----|-------|--------|-------------|----------------------|---------------|--------|
| 3 | Search Agent | `search_repository()` | Query kata kunci valid | Daftar hasil pencarian dari repositori Digilib dikembalikan | Hasil pencarian berhasil diambil dari Digilib | Valid |
| 4 | Search Agent | `search_papers()` | Deskripsi topik pencarian valid | Daftar paper relevan beserta metadata dikembalikan | Paper relevan berhasil ditemukan dan dikembalikan | Valid |
| 5 | Search Agent | `process_keyword_search()` | Deskripsi pencarian dan chat_id valid | Keyword diproses, hasil pencarian di-inject ke konteks respons | Proses pencarian berjalan, hasil tersimpan ke database | Valid |

```python
# app/gemini_client/searching_v2.py

def search_repository(self, query, max_results=None, filters=None):
    url = self._build_advanced_url(query, **filters or {})
    response = requests.get(url, timeout=15)
    results = self.extract_metadata(response.text)
    return results[:max_results] if max_results else results

def search_papers(self, query, filters=None):
    results = self.search_repository(query, filters=filters)
    return self.fetch_metadata(results)

def process_keyword_search(self, user_description, chat_id=None, app_context=None, filters=None):
    # Parsing keyword dari output discuss agent
    # Eksekusi pencarian untuk setiap keyword
    # Inject hasil ke konteks untuk respons final
    ...
```

---

## Tabel 3 — Hasil Pengujian General Agent Module

| No | Modul | Fungsi | Kelas Input | Output yang Diharapkan | Output Aktual | Status |
|----|-------|--------|-------------|----------------------|---------------|--------|
| 6 | General Agent | `_initialize_client()` | API key valid | Klien General Agent berhasil diinisiasi | Klien berhasil diinisiasi tanpa error | Valid |
| 7 | General Agent | `run_interactive_session()` | Pertanyaan tentang layanan perpustakaan | Respons berisi informasi layanan perpustakaan yang relevan | Jawaban sesuai konteks pertanyaan layanan perpustakaan | Valid |

```python
# app/gemini_client/general_knowledge.py

def _initialize_client(self):
    self.api_key = self._get_active_api_key()
    if not self.api_key:
        return False
    self.client = genai.Client(api_key=self.api_key)
    return True

def run_interactive_session(self, user_input):
    response = self.agent.send_message(user_input)
    return response.text
```

---

## Tabel 4 — Hasil Pengujian Authentication Module

| No | Modul | Fungsi | Kelas Input | Output yang Diharapkan | Output Aktual | Status |
|----|-------|--------|-------------|----------------------|---------------|--------|
| 8 | Authentication | `login()` | Username dan password valid | Session user_id tersimpan, redirect ke halaman beranda | Session tersimpan, pengguna diarahkan ke beranda | Valid |
| 9 | Authentication | `login()` | Username atau password tidak valid | Flash error "Username atau password salah", redirect ke halaman login | Pesan error ditampilkan, pengguna tidak masuk | Valid |
| 10 | Authentication | `register()` | Data registrasi lengkap dan valid | Akun baru tersimpan di database, redirect ke halaman login | Akun berhasil dibuat, pengguna diarahkan ke login | Valid |

```python
# app/routes/auth.py

def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home.home'))
        else:
            flash('Username atau password salah.', 'danger')
            return redirect(url_for('auth.login'))

def register():
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
    # Simpan akun baru
    ...
```

---

## Tabel 5 — Hasil Pengujian Saved Paper Module

| No | Modul | Fungsi | Kelas Input | Output yang Diharapkan | Output Aktual | Status |
|----|-------|--------|-------------|----------------------|---------------|--------|
| 11 | Saved Paper | `index()` | User login, terdapat paper yang telah disimpan | Halaman daftar paper tersimpan ditampilkan beserta metadata | Daftar paper tersimpan berhasil ditampilkan | Valid |
| 12 | Saved Paper | `remove_paper()` | Kode eprint paper valid dan milik user | Paper dihapus dari daftar tersimpan, redirect ke halaman saved | Paper berhasil dihapus dari database | Valid |

```python
# app/routes/saved.py

def index():
    user = User.query.get(session['user_id'])
    saved_papers = SavedPaper.query.filter_by(user_id=user.id).all()
    return render_template('saved.html', papers=saved_papers)

def remove_paper(eprint_code):
    paper = SavedPaper.query.filter_by(
        user_id=session['user_id'], eprint_code=eprint_code).first()
    if paper:
        db.session.delete(paper)
        db.session.commit()
    return redirect(url_for('saved.index'))
```

---

## Tabel 6 — Hasil Pengujian Paper Extraction Module

| No | Modul | Fungsi | Kelas Input | Output yang Diharapkan | Output Aktual | Status |
|----|-------|--------|-------------|----------------------|---------------|--------|
| 13 | Paper Extraction | `extract_metadata()` | HTML halaman paper valid dari repositori Digilib | Metadata judul, abstrak, tahun, dan kode eprint berhasil diekstrak | Metadata paper berhasil diekstrak sesuai struktur HTML | Valid |
| 14 | Paper Extraction | `fetch_metadata()` | Daftar URL hasil pencarian valid | Metadata lengkap untuk setiap paper dalam daftar dikembalikan | Metadata seluruh paper berhasil diambil | Valid |

```python
# app/gemini_client/searching_v2.py

def extract_metadata(self, html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for item in soup.find_all('tr', class_='ep_search_result'):
        title = item.find('a').get_text(strip=True)
        link  = item.find('a')['href']
        code  = link.split('/')[-1]
        results.append({'title': title, 'link': link, 'code': code})
    return results

def fetch_metadata(self, search_results):
    metadata_list = []
    for result in search_results:
        meta = self._fetch_single_metadata(result['link'])
        metadata_list.append(meta)
    return metadata_list
```

---

## Ringkasan Hasil Pengujian White Box Testing

| No | Modul | Jumlah Fungsi Diuji | Jumlah Test Case | Valid | Tidak Valid |
|----|-------|-------------------|-----------------|-------|------------|
| 1 | Discuss Agent Module | 2 | 2 | 2 | 0 |
| 2 | Search Agent Module | 3 | 3 | 3 | 0 |
| 3 | General Agent Module | 2 | 2 | 2 | 0 |
| 4 | Authentication Module | 2 | 3 | 3 | 0 |
| 5 | Saved Paper Module | 2 | 2 | 2 | 0 |
| 6 | Paper Extraction Module | 2 | 2 | 2 | 0 |
| | **Total** | **13** | **14** | **14** | **0** |

Seluruh skenario test case menghasilkan output aktual yang sesuai dengan output yang diharapkan. Tingkat keberhasilan pengujian White Box Testing mencapai **100%** (14/14 Valid).
