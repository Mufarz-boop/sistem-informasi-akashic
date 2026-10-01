"""Koneksi MySQL berbasis connection pool.

Semua query di Akashic melewati helper di file ini sehingga:
- parameter selalu dikirim terpisah dari SQL (anti SQL injection),
- koneksi selalu dikembalikan ke pool,
- model tidak perlu mengurus cursor/commit secara manual.
"""

import logging
from contextlib import contextmanager

import mysql.connector
from mysql.connector import pooling

from config import Config

logger = logging.getLogger(__name__)

_pool = None


class DatabaseUnavailable(Exception):
    """Database belum siap atau tidak dapat dihubungi."""


def init_pool():
    """Membuat connection pool. Aman dipanggil berulang kali."""
    global _pool
    if _pool is not None:
        return _pool
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="akashic_pool",
            pool_size=Config.DB_POOL_SIZE,
            pool_reset_session=True,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            time_zone="+00:00",
            autocommit=False,
        )
    except mysql.connector.Error as exc:
        logger.error("Gagal terhubung ke MySQL: %s", exc)
        raise DatabaseUnavailable(str(exc)) from exc
    return _pool


def _get_connection():
    pool = init_pool()
    try:
        return pool.get_connection()
    except mysql.connector.Error as exc:
        logger.error("Gagal mengambil koneksi dari pool: %s", exc)
        raise DatabaseUnavailable(str(exc)) from exc


@contextmanager
def transaction():
    """Context manager untuk beberapa query dalam satu transaksi.

    Contoh:
        with transaction() as cursor:
            cursor.execute("INSERT ...", (a, b))
            new_id = cursor.lastrowid
    """
    conn = _get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def fetch_one(sql, params=None):
    with transaction() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchone()


def fetch_all(sql, params=None):
    with transaction() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()


def execute(sql, params=None):
    """Menjalankan INSERT/UPDATE/DELETE.

    Mengembalikan lastrowid untuk INSERT, atau jumlah baris yang
    terpengaruh untuk UPDATE/DELETE.
    """
    with transaction() as cursor:
        cursor.execute(sql, params or ())
        if cursor.lastrowid:
            return cursor.lastrowid
        return cursor.rowcount


def ping():
    try:
        return fetch_one("SELECT 1 AS ok")["ok"] == 1
    except (DatabaseUnavailable, mysql.connector.Error):
        return False
