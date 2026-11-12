"""Uygulama olay günlüğü (MSSQL ``app_logs``). Parola, token, API anahtarı ve soru metni yazılmaz.

``log_event`` isteği asla bozmaz ve beklemez: olay bir kuyruğa girer, arka plandaki tek iş parçacığı
kısa bir transaction ile SQL'e yazar. Kuyruk doluysa veya yazma başarısız olursa olay sessizce atılır
(yalnız hata türü standart loga düşer).
"""
from __future__ import annotations

import json
import logging
import queue
import os
import re
import sys
import threading
from contextlib import closing

import request_context

logger = logging.getLogger(__name__)

LEVELS = ("debug", "info", "warning", "error")
_SECRET_KEY = re.compile(r"pass|token|secret|authorization|api[_-]?key|cookie|credential|session", re.I)
MAX_STRING = 300
MAX_DETAILS_JSON = 4000
_queue: queue.Queue = queue.Queue(maxsize=1000)
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()


def sanitize(value, depth: int = 0):
    """JSON'a uygun, kısaltılmış ve gizli anahtarları maskelenmiş kopya üretir."""
    if depth > 3:
        return "[derin]"
    if isinstance(value, dict):
        return {str(key)[:60]: ("[gizli]" if _SECRET_KEY.search(str(key)) else sanitize(item, depth + 1))
                for key, item in list(value.items())[:30]}
    if isinstance(value, (list, tuple)):
        return [sanitize(item, depth + 1) for item in list(value)[:20]]
    if isinstance(value, str):
        return value[:MAX_STRING]
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else None
    return str(value)[:MAX_STRING]


def _disabled() -> bool:
    """Birim testleri gerçek günlük tablosunu kirletmesin; APP_LOG_IN_TESTS=1 ile açılabilir."""
    if os.environ.get("APP_LOG_DISABLED") == "1":
        return True
    # Yalnız birim test çalıştırıcısıyla başlatılan süreçte (python -m unittest / pytest); bir bağımlılığın
    # unittest'i içe aktarması günlüğü kapatmaz.
    runner = (sys.argv[0] if sys.argv else "").lower()  # "python.exe -m unittest" veya pytest yolu
    return ("unittest" in runner or "pytest" in runner) and os.environ.get("APP_LOG_IN_TESTS") != "1"


def _details_json(details) -> str | None:
    if not details:
        return None
    text = json.dumps(sanitize(details), ensure_ascii=False, allow_nan=False)
    return text if len(text) <= MAX_DETAILS_JSON else json.dumps({"truncated": True}, ensure_ascii=False)


def write_event(connection, record: dict) -> None:
    """Tek olayı verilen bağlantıda yazar; commit çağırana aittir."""
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT dbo.app_logs (user_id, correlation_id, level, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
            record["user_id"], record["correlation_id"], record["level"], record["event_type"], record["details_json"])
    finally:
        cursor.close()


def _run_worker() -> None:
    from mssql import connection as database
    while True:
        record = _queue.get()
        try:
            with closing(database.connect()) as connection:
                write_event(connection, record)
                connection.commit()
        except Exception as error:  # günlük yazımı asla uygulamayı düşürmemeli
            logger.warning("app_logs yazılamadı: %s", type(error).__name__)
        finally:
            _queue.task_done()


def _ensure_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run_worker, name="app-log-writer", daemon=True)
            _worker.start()


def log_event(level: str, event_type: str, *, user_id: str | None = None, details: dict | None = None,
              correlation_id: str | None = None) -> None:
    """Olayı kuyruğa alır. Geçersiz düzey/olay adı veya doluluk durumunda sessizce atlar."""
    if _disabled():
        return
    try:
        if level not in LEVELS or not isinstance(event_type, str) or not 1 <= len(event_type) <= 100:
            return
        record = {"user_id": str(user_id) if user_id else None,
                  "correlation_id": correlation_id or request_context.correlation_id(),
                  "level": level, "event_type": event_type, "details_json": _details_json(details)}
        _ensure_worker()
        _queue.put_nowait(record)
    except Exception as error:
        logger.warning("Olay kuyruğa alınamadı: %s", type(error).__name__)


def flush(timeout: float = 5.0) -> None:
    """Kuyruktaki olayların yazılmasını bekler (testler ve kapanış için)."""
    done = threading.Event()
    threading.Thread(target=lambda: (_queue.join(), done.set()), daemon=True).start()
    done.wait(timeout)
