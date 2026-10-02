<div align="center">

# 🌌 AKASHIC

### *Informasi yang hadir di tempat yang tepat.*

**Location-Based Information System (LBIS)** — Sistem informasi berbasis web yang menghadirkan informasi relevan sesuai wilayah geografis pengguna, tanpa akun, tanpa instalasi, tanpa pelacakan identitas.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![PWA](https://img.shields.io/badge/PWA-Ready-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[Fitur](#-fitur-utama) · [Arsitektur](#-arsitektur-sistem) · [Instalasi](#-instalasi) · [API](#-api-endpoints) · [Struktur](#-struktur-proyek) · [Kontribusi](#-kontribusi)

</div>

---

## 📑 Daftar Isi

- [Tentang Akashic](#-tentang-akashic)
- [Fitur Utama](#-fitur-utama)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Struktur Proyek](#-struktur-proyek)
- [Skema Database](#-skema-database)
- [Instalasi](#-instalasi)
- [Konfigurasi](#-konfigurasi)
- [Menjalankan Aplikasi](#-menjalankan-aplikasi)
- [API Endpoints](#-api-endpoints)
- [Alur Kerja Sistem](#-alur-kerja-sistem)
- [Roadmap](#-roadmap)
- [Kontribusi](#-kontribusi)
- [Lisensi](#-lisensi)

---

## 🌠 Tentang Akashic

**Akashic** (dari konsep *"Akashic Records"* — catatan universal) adalah sistem informasi berbasis web dengan konsep **Location-Based Information System (LBIS)**.

Sistem ini dirancang untuk menghadirkan informasi yang **relevan secara geografis** kepada pengguna berdasarkan **wilayah** tempat mereka mengakses website — tanpa menjadikan lokasi sebagai identitas pribadi.

### 🎯 Prinsip Desain

| Prinsip | Deskripsi |
|---------|-----------|
| 🔓 **Tanpa Akun** | Pengguna publik tidak perlu login atau registrasi |
| 📍 **Lokasi Opsional** | Izin lokasi diminta, tetapi penolakan tetap memperbolehkan akses |
| 🗺️ **Polygon-Based** | Wilayah ditentukan via polygon, bukan radius sederhana |
| 🌳 **Hierarkis** | Struktur wilayah bertingkat via `parent_id` |
| 🔔 **Push Notification** | Notifikasi real-time berbasis subscription browser |
| 🕵️ **Privacy-First** | Lokasi tidak disimpan sebagai riwayat pergerakan |
| ⏰ **Scheduled Collector** | Berita dikumpulkan otomatis tanpa bergantung user aktif |

---

## ✨ Fitur Utama

### 🌍 Untuk Pengguna Publik

- 📰 **Feed Informasi Terpadu** — Informasi, event, dan berita eksternal dalam satu aliran
- 📍 **Deteksi Wilayah Otomatis** — Menggunakan geolocation browser + Polygon Region Engine
- 🔔 **Web Push Notification** — Notifikasi untuk info/event/berita baru di wilayah pengguna
- 📱 **Progressive Web App** — Dapat diinstal tanpa Play Store/App Store
- 🚫 **Tanpa Login** — Akses langsung tanpa hambatan registrasi
- 🛡️ **Privasi Terjaga** — Lokasi bersifat kontekstual, bukan identitas

### 🛠️ Untuk Admin

- 🗺️ **Manajemen Wilayah** — Kelola hierarki wilayah berbasis polygon
- 🏷️ **Manajemen Kategori** — Kelola kategori informasi dengan slug, warna, icon
- 📝 **Manajemen Informasi** — CRUD informasi internal dengan status draft/published
- 📅 **Manajemen Event** — Kelola event dengan waktu, lokasi, dan koordinat
- 📡 **Moderasi Berita Eksternal** — Review berita hasil auto-collect (approve/reject)
- 📊 **Dashboard Analitik** — Statistik konten & aktivitas
- 📜 **Activity Logs** — Audit trail lengkap aktivitas admin
- 👥 **Role-Based Access** — SUPER_ADMIN, ADMIN, EDITOR, MODERATOR

---

## 🏛️ Arsitektur Sistem

```
                          ┌─────────────────────────────────┐
                          │         BROWSER (PWA)           │
                          │  ┌───────────┐ ┌─────────────┐  │
                          │  │Geolocation│ │ServiceWorker│  │
                          │  └─────┬─────┘ └──────┬──────┘  │
                          └────────┼──────────────┼─────────┘
                                   │              │
                          lat/lng  │              │ Push Sub
                                   ▼              ▲
┌──────────────────────────────────────────────────────────────┐
│                    BACKEND (Flask REST API)                   │
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐  │
│  │  Region    │  │   Feed     │  │    Notification        │  │
│  │  Engine    │→ │   Engine   │→ │    Engine (WebPush)    │  │
│  │ (Polygon)  │  │            │  │                        │  │
│  └────────────┘  └────────────┘  └────────────────────────┘  │
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐  │
│  │  Location  │  │   News     │  │    Auth / Admin        │  │
│  │  Engine    │  │  Collector │  │    Services            │  │
│  └────────────┘  └────────────┘  └────────────────────────┘  │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   MySQL 8.0 (utf8mb4)│
                 │  ┌────────────────┐  │
                 │  │ regions        │  │
                 │  │ informations   │  │
                 │  │ events         │  │
                 │  │ news           │  │
                 │  │ notifications  │  │
                 │  │ push_subs      │  │
                 │  │ categories     │  │
                 │  │ admins         │  │
                 │  │ activity_logs  │  │
                 │  └────────────────┘  │
                 └──────────────────────┘
                            ▲
                            │ Scheduler (cron)
                            │
                    ┌──────────────────┐
                    │  RSS / API       │
                    │  Sumber Berita   │
                    └──────────────────┘
```

---

## 📁 Struktur Proyek

```
app/
├── akashic-venv/                    # Virtual environment (ignored)
├── backend/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py            # Koneksi MySQL
│   │   └── db_akashic.sql           # Skema database
│   ├── models/                      # ORM / Model Layer
│   │   ├── __init__.py
│   │   ├── admins_model.py
│   │   ├── category_model.py
│   │   ├── event_model.py
│   │   ├── information_model.py
│   │   ├── news_model.py
│   │   ├── notification_model.py
│   │   ├── push_subscription.py
│   │   └── region_model.py
│   ├── routes/                      # API Endpoints
│   │   ├── __init__.py
│   │   ├── auth_routes.py
│   │   ├── event_routes.py
│   │   ├── information_routes.py
│   │   ├── location_routes.py
│   │   ├── news_routes.py
│   │   ├── notification_routes.py
│   │   └── region_routes.py
│   ├── services/                    # Business Logic
│   │   ├── feed_engine.py           # Agregasi & sorting feed
│   │   ├── location_engine.py       # Deteksi lokasi → region
│   │   ├── news_collector.py        # RSS/API collector
│   │   ├── notification_engine.py   # Web Push sender
│   │   └── region_engine.py         # Polygon containment
│   ├── app.py                       # Entry point Flask
│   ├── config.py                    # Konfigurasi
│   └── requirements.txt
│
├── catatan/                         # Dokumentasi internal
│   ├── database.md
│   ├── description.md
│   └── struktur.md
│
├── frontend/
│   ├── assets/
│   │   ├── css/style.css
│   │   ├── image/
│   │   └── js/
│   │       ├── feed.js
│   │       ├── location.js
│   │       └── push.js
│   ├── service_worker.js            # PWA Service Worker
│   └── pages/
│       ├── admin/                   # Dashboard Admin
│       │   ├── dashboard-admin.html
│       │   ├── events.html
│       │   ├── information.html
│       │   ├── news.html
│       │   ├── profile.html
│       │   ├── regions.html
│       │   └── setting.html
│       ├── auth/                    # Autentikasi Admin
│       │   ├── forgot-password.html
│       │   ├── login.html
│       │   ├── register.html
│       │   └── reset-password.html
│       ├── error/                   # Halaman Error
│       │   ├── 400.html
│       │   └── 500.html
│       ├── landing/                 # Halaman Publik
│       │   ├── about.html
│       │   ├── base.html
│       │   ├── contact.html
│       │   ├── index.html
│       │   └── information.html
│       └── legal/                   # Halaman Legal
│           ├── disclaimer.html
│           ├── privacy.html
│           └── terms.html
│
├── .env                             # Environment variables (ignored)
├── .gitignore
└── README.md
```

---

## 🗄️ Skema Database

### Tabel Inti (10 Tabel)

| Tabel | Deskripsi | Relasi Utama |
|-------|-----------|--------------|
| **`regions`** | Wilayah hierarkis dengan polygon | `parent_id` → `regions.id` |
| **`admins`** | Akun pengelola sistem | — |
| **`categories`** | Kategori konten | — |
| **`informations`** | Informasi internal (admin) | `region_id`, `category_id`, `admin_id` |
| **`events`** | Event dengan waktu & lokasi | `region_id`, `category_id`, `admin_id` |
| **`news`** | Berita eksternal (auto-collect) | `region_id`, `category_id` |
| **`notifications`** | Antrian notifikasi push | `push_subscription_id`, `region_id`, `*_id` |
| **`push_subscriptions`** | Subscription browser (PWA) | `region_id` |
| **`activity_logs`** | Audit trail admin | `admin_id` |

### Tipe Region (ENUM)

```
COUNTRY → PROVINCE → REGENCY → CITY → DISTRICT → VILLAGE → LOCAL
```

### Role Admin (ENUM)

| Role | Wewenang |
|------|----------|
| `SUPER_ADMIN` | Akses penuh sistem |
| `ADMIN` | Kelola semua konten |
| `EDITOR` | Buat/edit informasi & event |
| `MODERATOR` | Moderasi berita & komentar |

### Status Konten

| Konten | Status |
|--------|--------|
| Informasi | `DRAFT` · `PUBLISHED` · `ARCHIVED` |
| Event | `DRAFT` · `PUBLISHED` · `CANCELLED` · `COMPLETED` · `ARCHIVED` |
| Berita | `PENDING` · `APPROVED` · `REJECTED` · `ARCHIVED` |
| Notifikasi | `PENDING` · `SENT` · `FAILED` · `READ` |

---

## 🚀 Instalasi

### Prasyarat

- **Python** ≥ 3.10
- **MySQL** ≥ 8.0 (dengan dukungan spatial `POLYGON`)
- **Node.js** (opsional, untuk tooling frontend)
- **Git**

### Langkah Instalasi

```bash
# 1. Clone repositori
git clone https://github.com/username/akashic.git
cd akashic

# 2. Buat virtual environment
python -m venv akashic-venv

# 3. Aktivasi virtual environment
# Linux/macOS
source akashic-venv/bin/activate
# Windows
akashic-venv\Scripts\activate

# 4. Install dependencies
pip install -r backend/requirements.txt

# 5. Import skema database
mysql -u root -p < backend/database/db_akashic.sql

# 6. Salin file environment
cp .env.example .env
# Edit .env sesuai konfigurasi lokal
```

---

## ⚙️ Konfigurasi

Buat file `.env` di root proyek:

```env
# ─── Application ───────────────────────────
APP_NAME=Akashic
APP_ENV=development
APP_DEBUG=True
SECRET_KEY=your-super-secret-key-here
BASE_URL=http://localhost:5000

# ─── Database ──────────────────────────────
DB_HOST=localhost
DB_PORT=3306
DB_NAME=db_akashic
DB_USER=root
DB_PASSWORD=your_password

# ─── Web Push (VAPID) ──────────────────────
VAPID_PUBLIC_KEY=your_vapid_public_key
VAPID_PRIVATE_KEY=your_vapid_private_key
VAPID_SUBJECT=mailto:admin@akashic.local

# ─── News Collector ────────────────────────
NEWS_COLLECTOR_INTERVAL_MINUTES=30
NEWS_RELEVANCE_THRESHOLD=0.65

# ─── JWT / Auth ────────────────────────────
JWT_SECRET_KEY=your-jwt-secret
JWT_EXPIRES_HOURS=24
```

### Generate VAPID Keys

```bash
python -m py_vapid --applicationServerKey
```

---

## ▶️ Menjalankan Aplikasi

```bash
# Development
cd backend
python app.py

# Production (dengan Gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Akses di browser: **http://localhost:5000**

### Menjalankan News Collector (Scheduler)

```bash
# Manual trigger
python -m backend.services.news_collector

# Atau via cron (setiap 30 menit)
*/30 * * * * cd /path/to/akashic && akashic-venv/bin/python -m backend.services.news_collector
```

---

## 🔌 API Endpoints

### 🌐 Public API

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `POST` | `/api/location/detect` | Kirim lat/lng, dapatkan region |
| `GET`  | `/api/feed` | Ambil feed berdasarkan region |
| `GET`  | `/api/informations` | Daftar informasi |
| `GET`  | `/api/informations/:slug` | Detail informasi |
| `GET`  | `/api/events` | Daftar event |
| `GET`  | `/api/news` | Daftar berita eksternal |
| `POST` | `/api/push/subscribe` | Daftarkan push subscription |
| `POST` | `/api/push/unsubscribe` | Hapus push subscription |

### 🔐 Admin API

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `POST` | `/api/auth/login` | Login admin |
| `POST` | `/api/auth/logout` | Logout admin |
| `GET`  | `/api/admin/regions` | Kelola wilayah |
| `POST` | `/api/admin/regions` | Tambah wilayah |
| `GET`  | `/api/admin/categories` | Kelola kategori |
| `POST` | `/api/admin/informations` | Buat informasi |
| `PUT`  | `/api/admin/informations/:id` | Edit informasi |
| `POST` | `/api/admin/events` | Buat event |
| `POST` | `/api/admin/news/:id/approve` | Approve berita |
| `POST` | `/api/admin/news/:id/reject` | Reject berita |
| `GET`  | `/api/admin/activity-logs` | Lihat audit trail |

### Contoh Request

```bash
# Deteksi wilayah dari koordinat
curl -X POST http://localhost:5000/api/location/detect \
  -H "Content-Type: application/json" \
  -d '{"latitude": -6.2088, "longitude": 106.8456, "accuracy": 50}'

# Response
{
  "success": true,
  "region": {
    "id": 12,
    "name": "Jakarta Pusat",
    "type": "CITY",
    "parent": { "id": 5, "name": "DKI Jakarta", "type": "PROVINCE" }
  }
}
```

---

## 🔄 Alur Kerja Sistem

### 1️⃣ Alur Deteksi Wilayah

```
User buka website
    │
    ▼
Browser minta izin lokasi
    │
    ├─── Ditolak ──→ Tampilkan feed tanpa filter wilayah
    │
    ▼ Diberikan
Kirim lat/lng/accuracy ke /api/location/detect
    │
    ▼
Location Engine → Region Engine (Polygon containment)
    │
    ▼
Dapatkan region_id (hierarkis)
    │
    ▼
Feed Engine → Agregasi Informasi + Event + News
    │
    ▼
Tampilkan ke pengguna
```

### 2️⃣ Alur Berita Eksternal

```
Scheduler (setiap 30 menit)
    │
    ▼
News Collector → Ambil RSS/API
    │
    ▼
Ekstraksi metadata (title, url, published_at)
    │
    ▼
Region Engine → Analisis keywords → tentukan region
    │
    ▼
Simpan ke tabel `news` (status: PENDING)
    │
    ▼
Admin Dashboard → Moderator review
    │
    ├─── APPROVED ──→ Muncul di feed publik
    └─── REJECTED ──→ Tidak ditampilkan
```

### 3️⃣ Alur Web Push Notification

```
Konten baru dipublikasikan
    │
    ▼
Notification Engine → Filter subscribers berdasarkan region
    │
    ▼
Buat record di `notifications` (status: PENDING)
    │
    ▼
Kirim via Web Push (VAPID)
    │
    ▼
Service Worker di browser terima
    │
    ▼
Tampilkan notifikasi ke user
    │
    ▼
Update status → SENT / FAILED
```

---

## 🗺️ Roadmap

- [x] 🗄️ Desain skema database (10 tabel)
- [x] 🏗️ Struktur proyek backend & frontend
- [ ] 🔧 Implementasi Region Engine (Polygon)
- [ ] 🔧 Implementasi Location Engine
- [ ] 🔧 Implementasi Feed Engine
- [ ] 🔧 Implementasi News Collector
- [ ] 🔧 Implementasi Notification Engine
- [ ] 🔐 Sistem autentikasi admin (JWT)
- [ ] 🎨 Admin Dashboard UI
- [ ] 📱 PWA + Service Worker
- [ ] 🔔 Web Push Notification
- [ ] 📊 Dashboard analitik
- [ ] 🧪 Unit testing & integration testing
- [ ] 🚀 Deployment (Docker + Nginx)

---

## 🤝 Kontribusi

Kontribusi sangat terbuka! Ikuti langkah berikut:

```bash
# 1. Fork repositori
# 2. Buat branch fitur
git checkout -b feature/nama-fitur

# 3. Commit perubahan
git commit -m "feat: menambahkan fitur X"

# 4. Push ke branch
git push origin feature/nama-fitur

# 5. Buat Pull Request
```

### Konvensi Commit

| Prefix | Kegunaan |
|--------|----------|
| `feat:` | Fitur baru |
| `fix:` | Perbaikan bug |
| `docs:` | Dokumentasi |
| `style:` | Formatting |
| `refactor:` | Refactoring |
| `test:` | Testing |
| `chore:` | Maintenance |

---

## 📜 Lisensi

Proyek ini dilisensikan di bawah **MIT License** — lihat file [LICENSE](LICENSE) untuk detail.

---

<div align="center">

### 🌌 Akashic

*"Informasi yang hadir di tempat yang tepat."*

Dibuat dengan ❤️ untuk informasi yang lebih relevan dan kontekstual.

**[⬆ Kembali ke atas](#-akashic)**

</div>