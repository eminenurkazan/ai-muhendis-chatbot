"""PostgreSQL DATABASE_URL ayarından bağımsız SQL Server bağlantısı."""

from __future__ import annotations

import os


class MSSQLConnectionError(RuntimeError):
    """Bağlantı dizesini veya sürücünün ham hatasını sızdırmayan hata."""


def connection_string() -> str:
    value = os.environ.get("MSSQL_CONNECTION_STRING", "").strip()
    if not value:
        raise MSSQLConnectionError("MSSQL_CONNECTION_STRING tanımlı değil.")
    return value


def connect():
    """Windows hesabı veya ortamda tanımlanan kimlikle SQL Server'a bağlan."""
    value = connection_string()
    try:
        import pyodbc
    except ImportError:
        raise MSSQLConnectionError("pyodbc kurulu değil; requirements.txt dosyasını yükle.") from None
    try:
        return pyodbc.connect(value, timeout=5)
    except pyodbc.Error:
        raise MSSQLConnectionError(
            "SQL Server bağlantısı kurulamadı; SQLEXPRESS hizmetini, sürücüyü ve MSSQL ayarlarını kontrol et."
        ) from None
