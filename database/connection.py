"""Veritabanı bağlantısı ve ortak hata mesajları."""

from __future__ import annotations

import os


class DatabaseError(RuntimeError):
    """Kullanıcıya güvenli ve açıklayıcı veritabanı hatası."""


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value:
        raise DatabaseError(
            "DATABASE_URL tanımlı değil. PostgreSQL bağlantı adresini "
            "ortam değişkeni olarak ayarla."
        )
    return value


def connect():
    """pgvector adapter'ı kayıtlı, açık bir psycopg bağlantısı döndürür."""

    url = database_url()
    try:
        import psycopg
        from pgvector.psycopg import register_vector
    except ImportError as exc:
        raise DatabaseError(
            "Veritabanı paketleri eksik. "
            "'.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt' çalıştır."
        ) from exc

    try:
        connection = psycopg.connect(url)
        register_vector(connection)
        return connection
    except Exception as exc:
        raise DatabaseError(
            "PostgreSQL bağlantısı kurulamadı. Sunucu, port ve DATABASE_URL değerini kontrol et."
        ) from exc
