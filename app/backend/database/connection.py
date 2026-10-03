import mysql.connector
from mysql.connector import Error

from config import Config


def get_connection():
    """
    Membuat koneksi ke database MySQL Akashic.
    """

    try:
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
        )

        if connection.is_connected():
            return connection

        raise RuntimeError(
            "[Database] Koneksi MySQL gagal dibuat."
        )

    except Error as error:
        raise RuntimeError(
            f"[Database] MySQL connection error: {error}"
        ) from error