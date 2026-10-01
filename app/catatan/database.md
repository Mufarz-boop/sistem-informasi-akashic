-- ============================================================
-- AKASHIC
-- Location-Based Information System
-- Database Schema
-- MySQL 8.x
-- ============================================================

CREATE DATABASE IF NOT EXISTS db_akashic
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE db_akashic;


-- ============================================================
-- 1. ADMINS
-- Menyimpan akun administrator Akashic.
-- ============================================================

CREATE TABLE admins (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,

    status ENUM('ACTIVE', 'INACTIVE')
        NOT NULL DEFAULT 'ACTIVE',

    last_login DATETIME NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- ============================================================
-- 2. REGIONS
-- Menyimpan wilayah geografis Akashic.
-- Polygon digunakan oleh Region Engine.
-- ============================================================

CREATE TABLE regions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    parent_id BIGINT UNSIGNED NULL,

    code VARCHAR(50) NOT NULL UNIQUE,
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

    geometry POLYGON SRID 4326 NULL,

    description TEXT NULL,

    status ENUM('ACTIVE', 'INACTIVE')
        NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_regions_parent
        FOREIGN KEY (parent_id)
        REFERENCES regions(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    INDEX idx_regions_parent (parent_id),
    INDEX idx_regions_type (type),
    INDEX idx_regions_status (status),

    SPATIAL INDEX idx_regions_geometry (geometry)
) ENGINE=InnoDB;


-- ============================================================
-- 3. REGION_KEYWORDS
-- Keyword yang digunakan untuk mencocokkan berita
-- eksternal dengan wilayah tertentu.
-- ============================================================

CREATE TABLE region_keywords (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    region_id BIGINT UNSIGNED NOT NULL,

    keyword VARCHAR(150) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_region_keywords_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    UNIQUE KEY uq_region_keyword (region_id, keyword),

    INDEX idx_region_keywords_keyword (keyword),
    INDEX idx_region_keywords_region (region_id)
) ENGINE=InnoDB;


-- ============================================================
-- 4. CATEGORIES
-- Kategori informasi yang dibuat oleh admin.
-- ============================================================

CREATE TABLE categories (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(120) NOT NULL UNIQUE,

    description TEXT NULL,
    icon VARCHAR(100) NULL,

    status ENUM('ACTIVE', 'INACTIVE')
        NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- ============================================================
-- 5. INFORMATIONS
-- Informasi resmi yang dibuat oleh administrator.
-- ============================================================

CREATE TABLE informations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    category_id BIGINT UNSIGNED NOT NULL,
    region_id BIGINT UNSIGNED NOT NULL,
    admin_id BIGINT UNSIGNED NOT NULL,

    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,

    summary TEXT NULL,
    content LONGTEXT NOT NULL,

    priority ENUM(
        'LOW',
        'NORMAL',
        'HIGH',
        'CRITICAL'
    ) NOT NULL DEFAULT 'NORMAL',

    status ENUM(
        'DRAFT',
        'PUBLISHED',
        'EXPIRED',
        'ARCHIVED'
    ) NOT NULL DEFAULT 'DRAFT',

    start_at DATETIME NULL,
    expired_at DATETIME NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_informations_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_informations_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_informations_admin
        FOREIGN KEY (admin_id)
        REFERENCES admins(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    INDEX idx_information_region (region_id),
    INDEX idx_information_category (category_id),
    INDEX idx_information_admin (admin_id),
    INDEX idx_information_status (status),
    INDEX idx_information_date (start_at)
) ENGINE=InnoDB;


-- ============================================================
-- 6. EVENTS
-- Menyimpan kegiatan/event yang memiliki waktu dan lokasi.
-- ============================================================

CREATE TABLE events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    region_id BIGINT UNSIGNED NOT NULL,
    admin_id BIGINT UNSIGNED NOT NULL,

    title VARCHAR(255) NOT NULL,
    description TEXT NULL,

    location_name VARCHAR(255) NULL,

    latitude DECIMAL(10,7) NULL,
    longitude DECIMAL(10,7) NULL,

    start_at DATETIME NOT NULL,
    end_at DATETIME NULL,

    status ENUM(
        'DRAFT',
        'PUBLISHED',
        'ONGOING',
        'COMPLETED',
        'CANCELLED'
    ) NOT NULL DEFAULT 'DRAFT',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_events_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_events_admin
        FOREIGN KEY (admin_id)
        REFERENCES admins(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    INDEX idx_events_region (region_id),
    INDEX idx_events_admin (admin_id),
    INDEX idx_events_status (status),
    INDEX idx_events_start (start_at)
) ENGINE=InnoDB;


-- ============================================================
-- 7. NEWS_SOURCES
-- Menyimpan sumber berita eksternal.
-- ============================================================

CREATE TABLE news_sources (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(150) NOT NULL,

    website_url VARCHAR(500) NOT NULL,
    rss_url VARCHAR(500) NULL,
    api_url VARCHAR(500) NULL,

    source_type ENUM(
        'RSS',
        'API',
        'WEB'
    ) NOT NULL DEFAULT 'RSS',

    status ENUM(
        'ACTIVE',
        'INACTIVE'
    ) NOT NULL DEFAULT 'ACTIVE',

    last_checked_at DATETIME NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_news_source_website (website_url),

    INDEX idx_news_sources_status (status),
    INDEX idx_news_sources_type (source_type)
) ENGINE=InnoDB;


-- ============================================================
-- 8. NEWS
-- Menyimpan metadata berita eksternal.
-- Isi artikel tidak disalin ke database.
-- ============================================================

CREATE TABLE news (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    source_id BIGINT UNSIGNED NOT NULL,
    region_id BIGINT UNSIGNED NULL,

    title VARCHAR(500) NOT NULL,
    summary TEXT NULL,

    source_url VARCHAR(1000) NOT NULL,
    image_url VARCHAR(1000) NULL,

    author VARCHAR(150) NULL,

    external_id VARCHAR(255) NULL,

    published_at DATETIME NULL,
    discovered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    relevance_method ENUM(
        'KEYWORD',
        'METADATA',
        'KEYWORD_AND_METADATA'
    ) NULL,

    status ENUM(
        'ACTIVE',
        'HIDDEN'
    ) NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_news_source
        FOREIGN KEY (source_id)
        REFERENCES news_sources(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_news_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    UNIQUE KEY uq_news_external_id (external_id),

    INDEX idx_news_source (source_id),
    INDEX idx_news_region (region_id),
    INDEX idx_news_status (status),
    INDEX idx_news_published (published_at),
    INDEX idx_news_discovered (discovered_at)
) ENGINE=InnoDB;


-- ============================================================
-- 9. PUSH_SUBSCRIPTIONS
-- Menyimpan Web Push Subscription browser.
-- Tidak terhubung dengan akun pengguna.
-- ============================================================

CREATE TABLE push_subscriptions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    endpoint TEXT NOT NULL,

    p256dh_key VARCHAR(255) NOT NULL,
    auth_key VARCHAR(255) NOT NULL,

    user_agent TEXT NULL,

    status ENUM(
        'ACTIVE',
        'INACTIVE'
    ) NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_push_endpoint (endpoint(255)),

    INDEX idx_push_status (status)
) ENGINE=InnoDB;


-- ============================================================
-- 10. NOTIFICATIONS
-- Menyimpan objek notifikasi yang dapat berasal dari
-- Information, News, atau Event.
-- ============================================================

CREATE TABLE notifications (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    region_id BIGINT UNSIGNED NULL,

    information_id BIGINT UNSIGNED NULL,
    news_id BIGINT UNSIGNED NULL,
    event_id BIGINT UNSIGNED NULL,

    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    type ENUM(
        'INFORMATION',
        'NEWS',
        'EVENT'
    ) NOT NULL,

    url VARCHAR(1000) NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_notifications_region
        FOREIGN KEY (region_id)
        REFERENCES regions(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_notifications_information
        FOREIGN KEY (information_id)
        REFERENCES informations(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_notifications_news
        FOREIGN KEY (news_id)
        REFERENCES news(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_notifications_event
        FOREIGN KEY (event_id)
        REFERENCES events(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    INDEX idx_notifications_region (region_id),
    INDEX idx_notifications_information (information_id),
    INDEX idx_notifications_news (news_id),
    INDEX idx_notifications_event (event_id),
    INDEX idx_notifications_type (type),
    INDEX idx_notifications_created (created_at)
) ENGINE=InnoDB;


-- ============================================================
-- 11. ACTIVITY_LOGS
-- Mencatat aktivitas administrator.
-- ============================================================

CREATE TABLE activity_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    admin_id BIGINT UNSIGNED NULL,

    action VARCHAR(100) NOT NULL,
    description TEXT NULL,

    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_activity_logs_admin
        FOREIGN KEY (admin_id)
        REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    INDEX idx_activity_admin (admin_id),
    INDEX idx_activity_action (action),
    INDEX idx_activity_created (created_at)
) ENGINE=InnoDB;

-- ============================================================
-- CATATAN IMPLEMENTASI
-- Skema final yang dipakai aplikasi ada di
-- backend/database/db_akashic.sql. Perbedaan dari rancangan di atas:
--
-- * password_resets   : tabel baru untuk token reset password
--                       (disimpan sebagai hash SHA-256, sekali pakai,
--                       memiliki expired_at).
-- * regions.geometry  : GEOMETRY SRID 4326 (Polygon/MultiPolygon),
--                       urutan koordinat GeoJSON [longitude, latitude].
-- * news_sources      : last_checked_at dan last_error untuk memantau
--                       sumber RSS yang gagal tanpa menghentikan Flask.
-- * news.status       : PENDING -> APPROVED/REJECTED/ARCHIVED; hanya
--                       APPROVED yang tampil di feed publik.
-- * activity_logs     : ditambah entity_type dan entity_id.
-- * Data awal         : wilayah Indonesia > Aceh > Kota Langsa > 5
--                       kecamatan (polygon perkiraan), kategori,
--                       region keywords, dan sumber RSS.
--
-- Koordinat pengunjung TIDAK disimpan di tabel mana pun.
-- ============================================================
