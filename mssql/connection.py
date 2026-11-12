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


def login_timeout() -> int:
    """MSSQL_LOGIN_TIMEOUT saniye (varsayılan 15, 1-60 arası)."""
    try:
        value = int(os.environ.get("MSSQL_LOGIN_TIMEOUT", "").strip() or 15)
    except ValueError:
        return 15
    return min(max(value, 1), 60)


def _is_timeout(error: Exception) -> bool:
    text = " ".join(str(part) for part in getattr(error, "args", ()))
    return "HYT00" in text or ("08001" in text and "Timeout" in text) or "(258)" in text


def connect():
    """Windows hesabı veya ortamda tanımlanan kimlikle SQL Server'a bağlan."""
    value = connection_string()
    try:
        import pyodbc
    except ImportError:
        raise MSSQLConnectionError("pyodbc kurulu değil; requirements.txt dosyasını yükle.") from None
    # Bellek baskısındaki SQL Server boşta kaldıktan sonra ilk bağlantıda geç yanıt verebilir (zaman aşımı 258).
    # Giriş süresi uzatılır ve zaman aşımına özgü hatada bir kez daha denenir; diğer hatalar hemen bildirilir.
    attempts = 2
    for attempt in range(attempts):
        try:
            return pyodbc.connect(value, timeout=login_timeout())
        except pyodbc.Error as error:
            if attempt + 1 < attempts and _is_timeout(error):
                continue
            break
    raise MSSQLConnectionError(
        "SQL Server bağlantısı kurulamadı; SQLEXPRESS hizmetini, sürücüyü ve MSSQL ayarlarını kontrol et."
    ) from None
