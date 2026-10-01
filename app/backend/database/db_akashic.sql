-- ============================================================
-- AKASHIC
-- Location-Based Information System
-- "Informasi yang hadir di tempat yang tepat."
--
-- Database schema + data awal (MySQL 8.x)
--
-- Cara import:
--   mysql -u root -p < backend/database/db_akashic.sql
--
-- PERINGATAN: script ini menghapus (DROP) tabel lama.
-- ============================================================

CREATE DATABASE IF NOT EXISTS db_akashic
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE db_akashic;

SET NAMES utf8mb4;
SET time_zone = '+00:00';

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS activity_logs;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS push_subscriptions;
DROP TABLE IF EXISTS news;
DROP TABLE IF EXISTS news_sources;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS informations;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS region_keywords;
DROP TABLE IF EXISTS regions;
DROP TABLE IF EXISTS password_resets;
DROP TABLE IF EXISTS admins;

SET FOREIGN_KEY_CHECKS = 1;


-- ============================================================
-- 1. ADMINS
-- Akun administrator. Password disimpan sebagai hash (Werkzeug).
-- ============================================================

CREATE TABLE admins (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    last_login DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_admin_username (username),
    UNIQUE KEY uq_admin_email (email),
    KEY idx_admin_status (status)
) ENGINE=InnoDB;


-- ============================================================
-- 2. PASSWORD_RESETS
-- Token reset password. Yang disimpan hanya hash SHA-256 token,
-- sehingga kebocoran database tidak membocorkan token aktif.
-- ============================================================

CREATE TABLE password_resets (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    admin_id BIGINT UNSIGNED NOT NULL,
    token_hash CHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_password_reset_token (token_hash),
    KEY idx_password_reset_admin (admin_id),
    KEY idx_password_reset_expires (expires_at),

    CONSTRAINT fk_password_reset_admin
        FOREIGN KEY (admin_id)
        REFERENCES admins(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 3. REGIONS
-- Wilayah hierarkis (parent_id) dengan batas wilayah berupa
-- POLYGON / MULTIPOLYGON (SRID 4326 / WGS84).
--
-- Kolom bertipe GEOMETRY agar wilayah yang terdiri dari beberapa
-- pulau (MULTIPOLYGON) tetap dapat disimpan. Backend hanya
-- menerima POLYGON dan MULTIPOLYGON.
--
-- Tidak memakai SPATIAL INDEX karena MySQL mewajibkan kolom
-- NOT NULL, sedangkan wilayah boleh belum memiliki polygon.
-- Pencocokan titik dilakukan oleh Region Engine (Shapely).
-- ============================================================

CREATE TABLE regions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    parent_id BIGINT UNSIGNED NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    type ENUM(
        'COUNTRY',
        'PROVINCE',
        'REGENCY',
        'CITY',
        'DISTRICT',
        'VILLAGE',
        'LOCAL'
    ) NOT NULL,
    geometry GEOMETRY SRID 4326 NULL,
    description TEXT NULL,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_region_code (code),
    KEY idx_region_parent (parent_id),
    KEY idx_region_type (type),
    KEY idx_region_status (status),

    CONSTRAINT fk_region_parent
        FOREIGN KEY (parent_id)
        REFERENCES regions(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 4. REGION_KEYWORDS
-- Kata kunci untuk memperkirakan relevansi berita eksternal
-- terhadap suatu wilayah.
-- ============================================================

CREATE TABLE region_keywords (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id BIGINT UNSIGNED NOT NULL,
    keyword VARCHAR(150) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_region_keyword (region_id, keyword),
    KEY idx_keyword (keyword),

    CONSTRAINT fk_region_keyword_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 5. CATEGORIES
-- Kategori untuk Information, Event, dan News.
-- ============================================================

CREATE TABLE categories (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(120) NOT NULL,
    description TEXT NULL,
    icon VARCHAR(100) NULL,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_category_name (name),
    UNIQUE KEY uq_category_slug (slug)
) ENGINE=InnoDB;


-- ============================================================
-- 6. INFORMATIONS
-- Informasi internal yang dibuat administrator.
-- ============================================================

CREATE TABLE informations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    category_id BIGINT UNSIGNED NOT NULL,
    region_id BIGINT UNSIGNED NOT NULL,
    admin_id BIGINT UNSIGNED NULL,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    summary TEXT NULL,
    content LONGTEXT NOT NULL,
    image VARCHAR(500) NULL,
    priority ENUM('LOW', 'NORMAL', 'HIGH', 'CRITICAL')
        NOT NULL DEFAULT 'NORMAL',
    status ENUM('DRAFT', 'PUBLISHED', 'EXPIRED', 'ARCHIVED')
        NOT NULL DEFAULT 'DRAFT',
    published_at DATETIME NULL,
    expired_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_information_slug (slug),
    KEY idx_information_category (category_id),
    KEY idx_information_region (region_id),
    KEY idx_information_admin (admin_id),
    KEY idx_information_status_published (status, published_at),

    CONSTRAINT fk_information_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_information_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_information_admin
        FOREIGN KEY (admin_id)
        REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 7. EVENTS
-- Kegiatan yang memiliki waktu dan lokasi.
-- ============================================================

CREATE TABLE events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id BIGINT UNSIGNED NOT NULL,
    category_id BIGINT UNSIGNED NULL,
    admin_id BIGINT UNSIGNED NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    location_name VARCHAR(255) NULL,
    latitude DECIMAL(10,7) NULL,
    longitude DECIMAL(10,7) NULL,
    start_at DATETIME NOT NULL,
    end_at DATETIME NULL,
    status ENUM('DRAFT', 'PUBLISHED', 'CANCELLED', 'ARCHIVED')
        NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_event_region (region_id),
    KEY idx_event_category (category_id),
    KEY idx_event_admin (admin_id),
    KEY idx_event_status_start (status, start_at),

    CONSTRAINT fk_event_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_event_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_event_admin
        FOREIGN KEY (admin_id)
        REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 8. NEWS_SOURCES
-- Sumber berita eksternal (RSS). region_id dan category_id
-- adalah metadata bawaan sumber, mis. portal berita daerah.
-- ============================================================

CREATE TABLE news_sources (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    website_url VARCHAR(500) NOT NULL,
    rss_url VARCHAR(500) NOT NULL,
    region_id BIGINT UNSIGNED NULL,
    category_id BIGINT UNSIGNED NULL,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    last_checked_at DATETIME NULL,
    last_error VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_news_source_rss (rss_url),
    KEY idx_news_source_status (status),
    KEY idx_news_source_region (region_id),

    CONSTRAINT fk_news_source_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_news_source_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 9. NEWS
-- Metadata berita eksternal. Isi artikel tidak disalin;
-- URL sumber asli selalu disimpan.
--
-- external_id = SHA-256 dari guid/URL item RSS, dipakai untuk
-- deduplikasi. Berita baru berstatus PENDING sampai dimoderasi.
-- ============================================================

CREATE TABLE news (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_id BIGINT UNSIGNED NOT NULL,
    region_id BIGINT UNSIGNED NULL,
    category_id BIGINT UNSIGNED NULL,
    external_id CHAR(64) NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT NULL,
    source_url VARCHAR(1000) NOT NULL,
    image_url VARCHAR(1000) NULL,
    author VARCHAR(150) NULL,
    keywords VARCHAR(500) NULL,
    relevance_method ENUM('KEYWORD', 'METADATA', 'KEYWORD_AND_METADATA')
        NULL,
    status ENUM('PENDING', 'APPROVED', 'REJECTED', 'ARCHIVED')
        NOT NULL DEFAULT 'PENDING',
    published_at DATETIME NULL,
    discovered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    moderated_by BIGINT UNSIGNED NULL,
    moderated_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_news_external_id (external_id),
    KEY idx_news_source (source_id),
    KEY idx_news_region (region_id),
    KEY idx_news_category (category_id),
    KEY idx_news_status_published (status, published_at),

    CONSTRAINT fk_news_source
        FOREIGN KEY (source_id)
        REFERENCES news_sources(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_news_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_news_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_news_moderator
        FOREIGN KEY (moderated_by)
        REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 10. PUSH_SUBSCRIPTIONS
-- Web Push subscription milik browser, bukan identitas pengguna.
-- region_id hanya wilayah terakhir yang dipilih browser
-- (ditimpa, bukan riwayat) agar notifikasi sesuai wilayah.
-- Koordinat tidak pernah disimpan.
-- ============================================================

CREATE TABLE push_subscriptions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    endpoint TEXT NOT NULL,
    endpoint_hash CHAR(64) NOT NULL,
    p256dh_key VARCHAR(255) NOT NULL,
    auth_key VARCHAR(255) NOT NULL,
    region_id BIGINT UNSIGNED NULL,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_push_endpoint_hash (endpoint_hash),
    KEY idx_push_status (status),
    KEY idx_push_region (region_id),

    CONSTRAINT fk_push_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 11. NOTIFICATIONS
-- Notifikasi yang dikirim saat Information/Event diterbitkan
-- atau News disetujui.
-- ============================================================

CREATE TABLE notifications (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id BIGINT UNSIGNED NULL,
    information_id BIGINT UNSIGNED NULL,
    event_id BIGINT UNSIGNED NULL,
    news_id BIGINT UNSIGNED NULL,
    type ENUM('INFORMATION', 'EVENT', 'NEWS') NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    url VARCHAR(1000) NULL,
    sent_count INT UNSIGNED NOT NULL DEFAULT 0,
    failed_count INT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_notification_region (region_id),
    KEY idx_notification_information (information_id),
    KEY idx_notification_event (event_id),
    KEY idx_notification_news (news_id),
    KEY idx_notification_type (type),
    KEY idx_notification_created (created_at),

    CONSTRAINT fk_notification_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_notification_information
        FOREIGN KEY (information_id)
        REFERENCES informations(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_notification_event
        FOREIGN KEY (event_id)
        REFERENCES events(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_notification_news
        FOREIGN KEY (news_id)
        REFERENCES news(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 12. ACTIVITY_LOGS
-- Audit aktivitas admin: LOGIN, LOGOUT, CREATE, UPDATE, DELETE,
-- PUBLISH, IMPORT_NEWS, UPDATE_REGION, MODERATE_NEWS, dll.
-- ============================================================

CREATE TABLE activity_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    admin_id BIGINT UNSIGNED NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NULL,
    entity_id BIGINT UNSIGNED NULL,
    description VARCHAR(500) NULL,
    ip_address VARCHAR(45) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_activity_admin (admin_id),
    KEY idx_activity_action (action),
    KEY idx_activity_created (created_at),

    CONSTRAINT fk_activity_admin
        FOREIGN KEY (admin_id)
        REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- DATA AWAL
--
-- Tidak ada akun admin bawaan (tanpa password default).
-- Admin pertama dibuat melalui halaman /auth/register yang
-- hanya terbuka selama tabel admins masih kosong.
-- ============================================================

INSERT INTO categories (name, slug, description, icon) VALUES
    ('Pengumuman', 'pengumuman', 'Pengumuman resmi dan layanan publik.', 'megaphone'),
    ('Pendidikan', 'pendidikan', 'Sekolah, beasiswa, dan kegiatan pendidikan.', 'book'),
    ('Kesehatan', 'kesehatan', 'Layanan dan informasi kesehatan.', 'heart'),
    ('Transportasi', 'transportasi', 'Lalu lintas, jalan, dan transportasi umum.', 'route'),
    ('Cuaca & Bencana', 'cuaca-bencana', 'Peringatan cuaca dan kebencanaan.', 'alert'),
    ('Budaya & Wisata', 'budaya-wisata', 'Kegiatan budaya, festival, dan pariwisata.', 'star'),
    ('Berita Daerah', 'berita-daerah', 'Berita eksternal dari media.', 'news');


-- ------------------------------------------------------------
-- Wilayah awal: Indonesia > Aceh > Kota Langsa > kecamatan.
-- Batas wilayah adalah penyederhanaan dari data OpenStreetMap
-- (c) OpenStreetMap contributors, lisensi ODbL. Batas ini
-- bersifat perkiraan; admin dapat menggantinya kapan saja.
-- Koordinat WKT memakai urutan longitude latitude.
-- ------------------------------------------------------------

INSERT INTO regions (id, parent_id, code, name, type, geometry, description) VALUES
    (1, NULL, 'ID', 'Indonesia', 'COUNTRY',
     ST_GeomFromText('POLYGON ((94.77171 5.79699, 95.11972 6.27445, 95.97362 5.68736, 97.60207 5.41943, 103.03500 1.31833, 103.74069 1.13036, 104.51860 1.44058, 104.77537 1.34123, 105.36813 2.31060, 105.18003 2.75671, 105.43730 3.22969, 107.29530 4.21998, 108.08015 4.98827, 109.82654 2.17105, 109.53805 1.92714, 109.66199 1.61742, 110.57541 0.85382, 111.82861 0.98618, 112.50103 1.58372, 113.63210 1.21912, 114.56690 1.42774, 114.79982 2.25054, 115.23743 2.50599, 115.08970 2.82324, 115.56738 3.16224, 115.55835 3.91919, 115.90105 4.39493, 118.26646 4.09065, 118.82303 2.35144, 120.22069 1.23413, 120.86474 1.57636, 124.22843 1.34819, 124.96242 2.78920, 125.24815 4.75756, 126.61976 5.76256, 127.34075 4.80537, 127.09311 3.83546, 128.74748 2.74470, 129.27486 0.91257, 130.65577 0.74581, 131.31030 1.28163, 132.27168 -0.14016, 132.65088 -0.15730, 134.37141 1.12996, 135.40974 -0.23947, 136.47144 -0.88550, 138.77736 -1.38451, 141.01302 -2.40220, 141.01944 -9.13556, 140.86013 -9.38541, 139.41137 -8.48775, 137.51874 -8.59573, 138.16875 -6.40259, 137.57468 -5.53972, 136.14822 -4.87326, 135.04220 -5.68038, 134.79109 -7.19577, 134.38419 -7.27077, 132.89438 -6.28716, 131.87542 -7.79787, 130.87267 -8.53624, 128.49818 -8.55160, 125.62275 -8.12028, 124.99422 -8.55051, 125.15943 -9.75479, 122.89003 -11.20857, 121.83781 -10.83989, 121.22042 -11.02291, 120.02291 -10.52044, 118.91206 -9.83675, 118.37102 -9.10595, 116.97538 -9.30620, 106.35550 -7.58250, 105.10528 -6.98845, 103.83331 -5.45636, 102.12755 -5.66952, 98.72148 -1.80398, 96.86824 1.31313, 95.20806 2.88601, 95.16262 4.83619, 94.77171 5.79699), (124.35478 -9.48524, 124.49242 -8.96934, 124.08336 -9.07356, 124.35478 -9.48524), (104.39256 1.29259, 104.39702 1.29662, 104.39318 1.30142, 104.39256 1.29259))', 4326, 'axis-order=long-lat'),
     'Batas wilayah perkiraan, disederhanakan dari OpenStreetMap.');

INSERT INTO regions (id, parent_id, code, name, type, geometry, description) VALUES
    (2, 1, 'ID-11', 'Aceh', 'PROVINCE',
     ST_GeomFromText('POLYGON ((94.77171 5.79699, 94.93259 6.16326, 95.00655 6.24444, 95.18805 6.26260, 95.97362 5.68736, 96.85626 5.47436, 97.50180 5.45080, 97.60207 5.41943, 98.04642 5.04290, 98.41708 4.58372, 98.68668 4.43955, 98.43937 4.28247, 98.19879 4.30255, 98.07202 4.25040, 98.09475 4.20859, 98.06199 4.18513, 98.04024 4.04116, 98.09360 3.96807, 98.01065 3.95018, 98.00780 3.90183, 97.90062 3.91091, 97.90870 3.81843, 97.80050 3.72256, 97.87178 3.61262, 97.86813 3.57112, 97.95880 3.48324, 97.93355 3.44223, 97.94871 3.39002, 98.02925 3.33075, 97.90464 3.25812, 97.98218 3.11607, 97.98091 3.07928, 97.93010 3.05472, 97.94185 2.90397, 98.05412 2.81998, 98.09941 2.82300, 98.11691 2.78504, 98.06937 2.76417, 98.11070 2.61133, 98.07733 2.56134, 98.19707 2.31184, 98.12842 2.16098, 98.19765 2.10485, 98.17863 2.07768, 97.75076 1.96094, 96.72039 1.45869, 95.78345 2.38085, 95.26483 2.80984, 95.18440 2.98015, 95.16262 4.83619, 94.77171 5.79699))', 4326, 'axis-order=long-lat'),
     'Batas wilayah perkiraan, disederhanakan dari OpenStreetMap.');

INSERT INTO regions (id, parent_id, code, name, type, geometry, description) VALUES
    (3, 2, 'ID-11.74', 'Kota Langsa', 'CITY',
     ST_GeomFromText('MULTIPOLYGON (((97.89754 4.44323, 97.90459 4.45268, 97.90859 4.45027, 97.90924 4.48931, 97.95012 4.51541, 97.95243 4.52237, 97.97764 4.54316, 97.97496 4.56102, 97.98410 4.54659, 97.98390 4.53492, 97.98901 4.53130, 98.02512 4.53717, 98.03763 4.54623, 98.03913 4.52706, 98.05690 4.53756, 98.06509 4.55329, 98.08372 4.53548, 98.06807 4.52504, 98.07174 4.51342, 98.06200 4.51098, 98.05704 4.51749, 98.05299 4.51066, 98.05465 4.49580, 98.05863 4.49469, 98.05773 4.47747, 98.04590 4.46386, 98.04028 4.42564, 98.02700 4.41661, 97.96789 4.40664, 97.96358 4.41772, 97.95570 4.41752, 97.95362 4.43047, 97.94513 4.42938, 97.94572 4.43632, 97.92978 4.40881, 97.92390 4.40839, 97.89938 4.43578, 97.89754 4.44323)), ((98.05612 4.56276, 98.06453 4.55786, 98.05930 4.55539, 98.05612 4.56276)), ((98.04579 4.54648, 98.05058 4.53852, 98.04161 4.53667, 98.04579 4.54648)))', 4326, 'axis-order=long-lat'),
     'Batas wilayah perkiraan, disederhanakan dari OpenStreetMap.');

INSERT INTO regions (id, parent_id, code, name, type, geometry, description) VALUES
    (4, 3, 'ID-11.74.01', 'Langsa Timur', 'DISTRICT',
     ST_GeomFromText('POLYGON ((97.97931 4.42123, 97.98157 4.42522, 97.99152 4.42794, 97.98786 4.42973, 97.99172 4.44865, 98.00000 4.45321, 98.00179 4.46119, 98.00695 4.46461, 98.00306 4.47084, 98.00676 4.47889, 98.00296 4.48381, 98.01184 4.49149, 98.01760 4.48610, 98.02211 4.49737, 98.03332 4.50145, 98.03271 4.50618, 98.01733 4.51070, 98.01671 4.51766, 98.02782 4.52746, 98.03726 4.53098, 98.03913 4.52706, 98.05478 4.53569, 98.06474 4.54731, 98.06524 4.55323, 98.08372 4.53548, 98.06807 4.52504, 98.07154 4.52198, 98.07174 4.51342, 98.06200 4.51098, 98.05704 4.51749, 98.05708 4.51230, 98.05299 4.51066, 98.05465 4.49580, 98.05863 4.49469, 98.05808 4.47915, 98.04590 4.46386, 98.04028 4.42564, 98.02700 4.41661, 98.01156 4.41126, 97.99984 4.41453, 97.99876 4.41076, 97.98626 4.41045, 97.98262 4.41210, 97.98242 4.41926, 97.97931 4.42123))', 4326, 'axis-order=long-lat'),
     'Batas wilayah perkiraan, disederhanakan dari OpenStreetMap.');

INSERT INTO regions (id, parent_id, code, name, type, geometry, description) VALUES
    (5, 3, 'ID-11.74.02', 'Langsa Barat', 'DISTRICT',
     ST_GeomFromText('MULTIPOLYGON (((98.05612 4.56276, 98.06453 4.55786, 98.05930 4.55539, 98.05612 4.56276)), ((98.04031 4.54064, 98.04579 4.54648, 98.05058 4.53852, 98.04161 4.53667, 98.04031 4.54064)), ((97.95644 4.50797, 97.96078 4.51291, 97.96186 4.52064, 97.97049 4.52317, 97.96600 4.52395, 97.96193 4.53071, 97.97955 4.54553, 97.97496 4.56102, 97.98410 4.54659, 97.98390 4.53492, 97.98901 4.53130, 98.00173 4.53066, 98.01853 4.53773, 98.02512 4.53717, 98.02847 4.54280, 98.03870 4.54566, 98.03726 4.53098, 98.02782 4.52746, 98.01634 4.51633, 98.01733 4.51070, 98.03271 4.50618, 98.03332 4.50145, 98.02211 4.49737, 98.01760 4.48610, 98.01184 4.49149, 98.00296 4.48381, 98.00676 4.47889, 98.00513 4.47237, 97.99278 4.47036, 97.98973 4.47549, 97.97941 4.47313, 97.97272 4.47857, 97.97048 4.47583, 97.96697 4.47715, 97.96784 4.48416, 97.95747 4.48636, 97.95939 4.49760, 97.95644 4.50797)))', 4326, 'axis-order=long-lat'),
     'Batas wilayah perkiraan, disederhanakan dari OpenStreetMap.');

INSERT INTO regions (id, parent_id, code, name, type, geometry, description) VALUES
    (6, 3, 'ID-11.74.03', 'Langsa Kota', 'DISTRICT',
     ST_GeomFromText('POLYGON ((97.95395 4.47031, 97.95905 4.47598, 97.95584 4.47952, 97.96567 4.48521, 97.96697 4.47715, 97.97048 4.47583, 97.97272 4.47857, 97.97941 4.47313, 97.98973 4.47549, 97.99761 4.46742, 97.99020 4.46292, 97.97989 4.46394, 97.97851 4.45895, 97.97264 4.45830, 97.97170 4.46799, 97.96598 4.46590, 97.95395 4.47031))', 4326, 'axis-order=long-lat'),
     'Batas wilayah perkiraan, disederhanakan dari OpenStreetMap.');

INSERT INTO regions (id, parent_id, code, name, type, geometry, description) VALUES
    (7, 3, 'ID-11.74.04', 'Langsa Lama', 'DISTRICT',
     ST_GeomFromText('POLYGON ((97.89754 4.44323, 97.90235 4.44595, 97.90525 4.45304, 97.90794 4.44706, 97.90912 4.44979, 97.91409 4.44773, 97.91188 4.45106, 97.91904 4.45018, 97.92416 4.45597, 97.92467 4.45364, 97.93242 4.45701, 97.93424 4.46475, 97.93837 4.46225, 97.94354 4.46748, 97.94509 4.46425, 97.95012 4.46656, 97.95032 4.47010, 97.96598 4.46590, 97.97170 4.46799, 97.97264 4.45830, 97.97725 4.45816, 97.97989 4.46394, 97.98324 4.46207, 97.98525 4.46540, 97.99380 4.46363, 98.00073 4.47277, 98.00380 4.47225, 98.00696 4.46467, 98.00179 4.46119, 98.00000 4.45321, 97.99172 4.44865, 97.98786 4.42973, 97.99152 4.42794, 97.98157 4.42522, 97.97931 4.42123, 97.98242 4.41926, 97.98262 4.41210, 97.98994 4.40978, 97.96728 4.40689, 97.96358 4.41772, 97.95570 4.41752, 97.95362 4.43047, 97.94513 4.42938, 97.94572 4.43632, 97.93412 4.42218, 97.92978 4.40881, 97.92390 4.40839, 97.89938 4.43578, 97.89754 4.44323))', 4326, 'axis-order=long-lat'),
     'Batas wilayah perkiraan, disederhanakan dari OpenStreetMap.');

INSERT INTO regions (id, parent_id, code, name, type, geometry, description) VALUES
    (8, 3, 'ID-11.74.05', 'Langsa Baro', 'DISTRICT',
     ST_GeomFromText('POLYGON ((97.90924 4.48931, 97.95012 4.51541, 97.95212 4.52203, 97.96193 4.53071, 97.96600 4.52395, 97.97070 4.52488, 97.96805 4.52044, 97.96186 4.52064, 97.96078 4.51291, 97.95689 4.50957, 97.95939 4.49760, 97.95747 4.48636, 97.96328 4.48485, 97.96135 4.48040, 97.95584 4.47952, 97.95905 4.47598, 97.95428 4.46930, 97.95032 4.47010, 97.95012 4.46656, 97.94509 4.46425, 97.94350 4.46747, 97.93837 4.46225, 97.93438 4.46484, 97.93242 4.45701, 97.92467 4.45364, 97.92416 4.45597, 97.91904 4.45018, 97.91188 4.45106, 97.91409 4.44773, 97.90912 4.44979, 97.90794 4.44706, 97.90924 4.48931))', 4326, 'axis-order=long-lat'),
     'Batas wilayah perkiraan, disederhanakan dari OpenStreetMap.');

INSERT INTO region_keywords (region_id, keyword) VALUES
    (2, 'Aceh'),
    (2, 'Provinsi Aceh'),
    (2, 'Pemerintah Aceh'),
    (3, 'Langsa'),
    (3, 'Kota Langsa'),
    (3, 'Pemko Langsa'),
    (4, 'Langsa Timur'),
    (5, 'Langsa Barat'),
    (6, 'Langsa Kota'),
    (7, 'Langsa Lama'),
    (8, 'Langsa Baro');


-- ------------------------------------------------------------
-- Sumber berita RSS awal. Dapat diubah melalui Admin > Settings.
-- ------------------------------------------------------------

INSERT INTO news_sources (name, website_url, rss_url, region_id, category_id) VALUES
    ('ANTARA Aceh', 'https://aceh.antaranews.com',
     'https://aceh.antaranews.com/rss/terkini.xml', 2, 7),
    ('Google News: Langsa', 'https://news.google.com',
     'https://news.google.com/rss/search?q=Langsa&hl=id&gl=ID&ceid=ID:id', NULL, 7),
    ('ANTARA News', 'https://www.antaranews.com',
     'https://www.antaranews.com/rss/terkini.xml', NULL, 7);
