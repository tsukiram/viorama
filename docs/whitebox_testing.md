# White Box Testing — Viorama.site

Pengujian White Box Testing dilakukan dengan metode **Unit Testing**, yaitu menguji setiap fungsi/modul inti aplikasi secara individual untuk memvalidasi bahwa logika internal pada setiap unit berjalan secara akurat sesuai dengan yang diharapkan.

---

## 1. Unit: `login()` — `/app/routes/auth.py`

Fungsi yang menangani autentikasi pengguna. Menerima username dan password, memverifikasi ke database, dan menentukan akses pengguna.

| No | Input | Output yang Diharapkan | Hasil | Status |
|----|-------|----------------------|-------|--------|
| 1 | Method GET | Halaman login ditampilkan (HTTP 200) | Sesuai | ✅ Pass |
| 2 | POST: username valid, password benar | Redirect ke beranda, session `user_id` tersimpan | Sesuai | ✅ Pass |
| 3 | POST: username tidak terdaftar | Flash error "Username atau password salah", redirect ke halaman login | Sesuai | ✅ Pass |
| 4 | POST: username valid, password salah | Flash error "Username atau password salah", redirect ke halaman login | Sesuai | ✅ Pass |

---

## 2. Unit: `register()` — `/app/routes/auth.py`

Fungsi yang menangani pendaftaran akun pengguna baru. Memvalidasi input dan menyimpan akun baru ke database.

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

| No | Input | Output yang Diharapkan | Hasil | Status |
|----|-------|----------------------|-------|--------|
| 1 | Request tanpa sesi login | Response JSON error "Unauthorized" (HTTP 401) | Sesuai | ✅ Pass |
| 2 | POST login + message kosong | Response JSON error "No message provided" (HTTP 400) | Sesuai | ✅ Pass |
| 3 | POST login + pesan pertama (session baru) | Sesi baru dibuat, `new_session_id` tersedia di response | Sesuai | ✅ Pass |
| 4 | POST login + session_id tidak valid | Response JSON error "Invalid session ID" (HTTP 404) | Sesuai | ✅ Pass |
| 5 | POST login + query pencarian paper | Response berisi `initial_response`, background search berjalan (`search_started: true`) | Sesuai | ✅ Pass |
| 6 | POST login + percakapan umum (bukan pencarian) | Response berisi jawaban teks, tidak ada background search (`search_started: false`) | Sesuai | ✅ Pass |

---

## 4. Unit: `check_status()` — `/app/routes/search_v2.py`

Fungsi polling status pencarian. Digunakan frontend untuk mengecek apakah proses pencarian sudah selesai dan mengambil hasilnya.

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
