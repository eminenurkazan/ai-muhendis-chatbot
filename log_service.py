"""Yönetici günlük görüntüleme; salt okunur, model çağrısı yok."""
from contextlib import closing
from datetime import timezone
import json

import pyodbc
from mssql import connection as database
from mssql.repository import MSSQLRepository, RepositoryError


class LogsUnavailable(Exception):
    pass


def _run(operation):
    try:
        with closing(database.connect()) as connection:
            return operation(MSSQLRepository(connection))
    except (database.MSSQLConnectionError, RepositoryError, pyodbc.Error):
        raise LogsUnavailable("Günlüklere şu anda ulaşılamıyor.") from None


def _public(row: dict) -> dict:
    created = row["created_at"]
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    try:
        details = json.loads(row["details_json"]) if row.get("details_json") else None
    except ValueError:
        details = None
    return {"id": str(row["id"]), "created_at": created, "level": row["level"], "event_type": row["event_type"],
            "correlation_id": str(row["correlation_id"]), "user_email": row.get("user_email"), "details": details}


def list_logs(**filters) -> dict:
    page = _run(lambda repository: repository.admin_logs(**filters))
    return {"items": [_public(row) for row in page["items"]], "next_offset": page["next_offset"]}


def summary(days: int = 7) -> dict:
    return _run(lambda repository: repository.log_summary(days))
