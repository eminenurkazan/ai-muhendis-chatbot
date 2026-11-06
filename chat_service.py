"""Authenticated-user scoped chat history operations; no model calls."""
from contextlib import closing
from datetime import timezone
import json

import pyodbc
from mssql import connection as database
from mssql.repository import MSSQLRepository, RecordNotFoundError, RepositoryError


class ChatNotFound(Exception):
    pass


class ChatUnavailable(Exception):
    pass


def _dates(row):
    result = dict(row)
    for name in ("created_at", "updated_at"):
        value = result.get(name)
        if value is not None and value.tzinfo is None:
            result[name] = value.replace(tzinfo=timezone.utc)
    return result


def _run(operation, *, write=False):
    try:
        with closing(database.connect()) as connection:
            try:
                result = operation(MSSQLRepository(connection))
                if write:
                    connection.commit()
                return result
            except Exception:
                if write:
                    connection.rollback()
                raise
    except RecordNotFoundError:
        # Same response for missing and someone else's chat; no ownership disclosure.
        raise ChatNotFound("Sohbet bulunamadı.") from None
    except (database.MSSQLConnectionError, RepositoryError, pyodbc.Error):
        raise ChatUnavailable("Sohbet geçmişine şu anda ulaşılamıyor. Biraz sonra tekrar dene.") from None


def create_chat(user_id, title, expertise_mode):
    def create(repository):
        row = repository.create_session(user_id, title, expertise_mode)
        return _dates(repository.get_session(user_id, str(row["id"])))
    return _run(create, write=True)


def list_chats(user_id, offset=0, limit=50):
    rows = _run(lambda repository: repository.list_sessions(user_id, offset=offset, limit=limit + 1))
    return {"items": [_dates(row) for row in rows[:limit]],
            "next_offset": offset + limit if len(rows) > limit else None}


def get_chat(user_id, chat_id):
    return _run(lambda repository: _dates(repository.get_session(user_id, chat_id)))


def list_messages(user_id, chat_id, after_seq=0, limit=50):
    rows = _run(lambda repository: repository.list_messages(user_id, chat_id, after_seq=after_seq, limit=limit + 1))
    items = []
    try:
        for row in rows[:limit]:
            item = _dates(row)
            for stored, public in (("citations_json", "citations"), ("source_snapshot_json", "sources")):
                raw = item.pop(stored, None)
                value = [] if raw is None else json.loads(raw)
                if not isinstance(value, list):
                    raise ValueError
                item[public] = value
            items.append(item)
    except (ValueError, TypeError):
        raise ChatUnavailable("Sohbetin kaynak bilgileri okunamadı.") from None
    return {"items": items, "next_after_seq": items[-1]["message_seq"] if len(rows) > limit else None}
