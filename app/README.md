# Akashic — Sistem Informasi Akashic

> *Informasi yang hadir di tempat yang tepat.*

Akashic adalah **Location-Based Information System** berbasis web. Browser pengunjung (tanpa akun) mengirim koordinat sementara, **Region Engine** menentukan wilayah dengan Polygon/MultiPolygon dan hierarki `parent_id`, lalu **Feed Engine** menampilkan gabungan **informasi**, **event**, dan **berita eksternal (RSS)** yang relevan. Admin mengelola konten melalui dasbor, dan pengunjung dapat berlangganan **Web Push**.

Stack: Python 3.10+, Flask, MySQL 8, Shapely, APScheduler, feedparser, pywebpush, HTML/CSS/Vanilla JS.

## Menjalankan secara lokal

### 1. MySQL

```bash
# Ubuntu/Debian
sudo apt-get install -y mysql-server
sudo service mysql start

# Import skema + data awal (wilayah Indonesia › Aceh › Kota Langsa beserta kecamatan, kategori, sumber RSS)
sudo mysql < backend/database/db_akashic.sql

# Buat user khusus aplikasi (ganti password)
sudo mysql -e "CREATE USER 'akashic'@'localhost' IDENTIFIED BY 'ganti-password';
               GRANT SELECT, INSERT, UPDATE, DELETE ON db_akashic.* TO 'akashic'@'localhost';"
```

> `db_akashic.sql` menjalankan `DROP TABLE IF EXISTS` untuk semua tabel Akashic — jangan diimport ulang pada database produksi yang sudah berisi data.

### 2. Python environment

```bash
cd app
python3 -m venv akashic-venv
source akashic-venv/bin/activate        # Windows: akashic-venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 3. Konfigurasi `.env`

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # isi SECRET_KEY
```

Isi minimal: `SECRET_KEY`, `DB_USER`, `DB_PASSWORD`. Variabel penting lain:

| Variabel | Keterangan |
|---|---|
| `FLASK_ENV` | `development` (debug) atau `production` |
| `APP_HOST`, `APP_PORT` | alamat server Flask (default `127.0.0.1:5000`) |
| `PUBLIC_BASE_URL` | URL publik, dipakai untuk tautan reset password |
| `CONTACT_EMAIL` | tujuan formulir kontak |
| `SESSION_COOKIE_SECURE` | `true` jika dilayani melalui HTTPS |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIMS_EMAIL` | kunci Web Push |
| `NEWS_COLLECTOR_ENABLED`, `NEWS_COLLECT_INTERVAL_MINUTES` | scheduler pengambilan RSS |
| `LOCATION_MAX_ACCURACY_METERS` | akurasi GPS di atas nilai ini ditandai *approximate* |
| `MAIL_*` | SMTP opsional untuk email reset password |

`.env` tidak boleh di-commit (sudah ada di `.gitignore`).

### 4. Kunci Web Push (opsional)

```bash
cd backend
python manage.py generate-vapid     # salin output ke .env
```

Tanpa kunci VAPID, website tetap berjalan; tombol notifikasi menampilkan bahwa push belum aktif. Web Push membutuhkan HTTPS (atau `localhost`).

### 5. Jalankan

```bash
cd backend
python app.py
```

Buka <http://127.0.0.1:5000>. Scheduler RSS ikut berjalan di proses yang sama; kegagalan satu sumber RSS dicatat di `news_sources.last_error` tanpa menghentikan Flask.

### 6. Admin pertama

Buka <http://127.0.0.1:5000/auth/register> — pendaftaran publik hanya terbuka selama belum ada admin. Setelah itu admin baru hanya bisa didaftarkan oleh admin yang sedang login. Alternatif CLI:

```bash
python manage.py create-admin
```

### 7. Mengambil berita sekarang

```bash
python manage.py collect-news
```

atau tombol **Ambil berita sekarang** di dasbor. Berita baru berstatus `PENDING` dan baru tampil di feed publik setelah disetujui di **Admin › Berita**.

## Halaman

| URL | Keterangan |
|---|---|
| `/` | Beranda, deteksi lokasi, feed wilayah, langganan notifikasi |
| `/information` | Penjelajah feed: pencarian, filter tipe/kategori/wilayah/tanggal, urutan, paginasi |
| `/about`, `/system-description`, `/disclaimer`, `/contact` | Halaman informasi |
| `/auth/login`, `/auth/register`, `/auth/forgot-password`, `/auth/reset-password` | Autentikasi admin |
| `/admin/dashboard`, `/admin/information`, `/admin/events`, `/admin/news`, `/admin/regions`, `/admin/profile`, `/admin/settings` | Dasbor admin |

## API

Semua respons memakai amplop JSON:

```json
{ "success": true,  "data": { }, "message": "..." }
{ "success": false, "data": null, "message": "...", "error": "..." }
```

| Method & path | Akses | Keterangan |
|---|---|---|
| `POST /api/location/detect` | publik | body `{latitude, longitude, accuracy}` → `{region, parent_region, hierarchy, confidence}` |
| `GET /api/feed` | publik | `region_id, category_id, types=information,event,news, q, sort=latest\|oldest\|title, date_from, date_to, page, per_page` |
| `GET /api/information[/<id>]` | publik (admin melihat semua status) | `POST/PUT/DELETE` admin |
| `GET /api/events[/<id>]` | publik | `POST/PUT/DELETE` admin |
| `GET /api/news[/<id>]` | publik hanya `APPROVED` | `PUT/DELETE` admin (moderasi), `POST /api/news/collect`, CRUD `/api/news/sources` |
| `GET /api/regions`, `/api/regions/tree`, `/api/regions/<id>?geometry=1` | publik | `POST/PUT/DELETE` admin, `geometry` = GeoJSON Polygon/MultiPolygon/Feature |
| `GET /api/categories` | publik | `POST/PUT/DELETE` admin |
| `GET /api/notifications/public-key`, `POST /api/notifications/subscribe`, `PUT /api/notifications/region`, `POST /api/notifications/unsubscribe` | publik | Web Push |
| `/api/auth/login, logout, me, status, register, forgot-password, reset-password, profile, password` | — | autentikasi admin |
| `GET /api/admin/dashboard`, `/api/admin/activity`, `/api/admin/settings` | admin | ringkasan, activity log, status konfigurasi |
| `GET /api/health` | publik | status database |

Contoh:

```bash
curl -s -X POST http://127.0.0.1:5000/api/location/detect \
  -H 'Content-Type: application/json' \
  -d '{"latitude":4.4683,"longitude":97.9683,"accuracy":20}'
# → Langsa Kota (Indonesia › Aceh › Kota Langsa › Langsa Kota)
```

Permintaan admin yang mengubah data wajib mengirim header `X-CSRF-Token` (diambil dari `GET /api/auth/me`) dan cookie sesi.

## Privasi & lokasi

- Pengunjung publik tidak memiliki akun. Koordinat hanya dipakai selama satu request untuk menentukan wilayah dan **tidak disimpan** di database maupun log.
- Browser hanya menyimpan ringkasan wilayah (nama/ID) di `sessionStorage`, bukan koordinat.
- Jika izin lokasi ditolak atau tidak tersedia, website tetap menampilkan feed umum dan pengunjung dapat memilih wilayah secara manual.
- Langganan Web Push hanya menyimpan endpoint browser dan wilayah pilihan.

## Keamanan admin

Password di-hash (Werkzeug `generate_password_hash`), sesi bertanda tangan dengan cookie `HttpOnly` + `SameSite=Lax`, CSRF token untuk semua mutasi, penguncian sementara setelah login gagal berulang, token reset password sekali pakai yang disimpan dalam bentuk hash, sesi admin nonaktif langsung dibatalkan, dan seluruh aktivitas dicatat di `activity_logs`.

## Pengujian

```bash
cd backend
flake8 --max-line-length=100 .
python -c "import app; a = app.create_app(start_jobs=False); print(len(list(a.url_map.iter_rules())), 'routes')"
curl -s http://127.0.0.1:5000/api/health
```

## Dokumentasi lain

- [`catatan/description.md`](catatan/description.md) — konsep sistem
- [`catatan/database.md`](catatan/database.md) — rancangan database
- [`catatan/struktur.md`](catatan/struktur.md) — struktur repository
