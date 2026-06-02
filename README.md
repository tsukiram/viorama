# Viorama.site — Library Virtual Assistant

**Prototipe Virtual Assistant Temu Kembali Informasi Karya Tulis Ilmiah**  
Sistem pencarian karya ilmiah berbasis AI (Large Language Model) untuk Perpustakaan UIN Sunan Kalijaga Yogyakarta.

---

## Tentang Aplikasi

Viorama.site adalah prototipe *library virtual assistant* yang membantu pengguna perpustakaan dalam melakukan temu kembali informasi karya tulis ilmiah (skripsi, tesis, disertasi, artikel) menggunakan pendekatan percakapan berbasis AI.

**Fitur utama:**
- **Paper Search** — Pencarian karya ilmiah melalui percakapan natural language
- **General Chat** — Tanya jawab umum tentang layanan perpustakaan
- **Saved Paper** — Penyimpanan referensi karya ilmiah

**Stack:**
- Backend: Python, Flask
- AI: Google Gemini (via `google-genai` SDK)
- Database: SQLite
- Frontend: HTML, CSS (Bootstrap), JavaScript

---

## Instalasi

### 1. Clone repository

```bash
git clone https://github.com/[username]/viorama-website-new.git
cd viorama-website-new
```

### 2. Buat virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi environment

```bash
cp .env.example .env
```

Edit `.env` dan isi nilai `SECRET_KEY`:

```env
SECRET_KEY=your-secret-key-here
```

> Generate secret key: `python -c "import secrets; print(secrets.token_hex(32))"`

### 5. Inisialisasi database

```bash
flask shell
>>> from app import create_app
>>> app = create_app()
>>> from app.models.models import db
>>> with app.app_context():
...     db.create_all()
```

### 6. Jalankan aplikasi

```bash
flask run
```

Buka `http://localhost:5000`

---

## Konfigurasi API Key Gemini

API Key Gemini dikelola melalui halaman admin (`/admin`). Setelah login sebagai admin, tambahkan API Key Gemini melalui menu **API Key Management**.

API Key **tidak** disimpan di file konfigurasi atau environment — seluruhnya tersimpan di database secara terenkripsi.

---

## Struktur Direktori

```
viorama-website-new/
├── app/
│   ├── gemini_client/      # Client untuk Gemini API (search, general, discuss)
│   ├── models/             # Model database (SQLAlchemy)
│   ├── routes/             # Blueprint Flask (auth, search_v2, general, saved, admin)
│   ├── static/             # CSS, JS, assets
│   └── templates/          # HTML templates (Jinja2)
├── docs/
│   └── whitebox_testing.md # Dokumentasi White Box Testing
├── config.py               # Konfigurasi Flask
├── wsgi.py                 # Entry point WSGI
├── requirements.txt
├── .env.example
└── README.md
```

---

## Dokumentasi Testing

| Dokumen | Lokasi |
|---------|--------|
| White Box Testing | [`docs/whitebox_testing.md`](docs/whitebox_testing.md) |

---

## Lisensi

Proyek ini merupakan karya penelitian tesis untuk Program Studi Interdisciplinary Islamic Studies, Konsentrasi Ilmu Perpustakaan dan Informasi, UIN Sunan Kalijaga Yogyakarta.
