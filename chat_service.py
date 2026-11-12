"""Authenticated-user scoped chat history operations; no model calls."""
from contextlib import closing
from datetime import timezone
import json

import pyodbc
from mssql import connection as database
from mssql.repository import MSSQLRepository, RecordNotFoundError, RepositoryError
from conversation import history_from_messages
from request_replay import ReplayConflict, ReplayStore

# Retain successful generation if saving fails, so an explicit retry can save it.
# SQL remains authoritative across process restarts after a successful commit.
_generated_turns = ReplayStore()


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


def save_feedback(user_id, chat_id, request_id, rating, comment=None):
    return _run(lambda repo: repo.save_feedback(user_id, chat_id, request_id, rating, comment), write=True)


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


def _saved_response(state, question):
    rows = state["saved"]
    if not rows:
        return None
    if len(rows) != 2 or [row["role"] for row in rows] != ["user", "assistant"]:
        raise ChatUnavailable("Kaydedilen soru ve yanıt birlikte okunamadı.")
    if rows[0]["content"] != question:
        raise ReplayConflict("Aynı istek kimliği farklı bir soru için kullanılamaz.")
    try:
        response = json.loads(rows[1]["response_json"])
        if not isinstance(response, dict) or response.get("answer") != rows[1]["content"]:
            raise ValueError
        return response
    except (TypeError, ValueError):
        raise ChatUnavailable("Kaydedilen yanıt okunamadı.") from None


def _clean_question(question):
    question = question.strip()
    if not question or len(question) > 2000:
        raise ValueError("Soru boş olamaz ve 2000 karakteri geçemez.")
    return question


def _context(state):
    """Kayıtlı sohbetten uzmanlık modu ve sınırlı geçmiş; istemciden gelmez."""
    mode = state["session"]["expertise_mode"]
    history = history_from_messages([
        {"role": row["role"], "content": row["content"],
         "status": "complete" if row["message_status"] == "completed" else "failed"}
        for row in state["recent"]
    ])
    return mode, history


def _replay_key(user_id, chat_id, state):
    # The sequence is part of the cache key: concurrent changes need fresh context.
    return (str(user_id), str(chat_id), state["last_seq"])


def _saver(user_id, chat_id, request_id, question, response, state):
    def save(repo):
        current = repo.turn_state(user_id, chat_id, request_id, lock=True)
        previous = _saved_response(current, question)
        if previous is not None:
            return previous
        if current["last_seq"] != state["last_seq"]:
            raise ReplayConflict("Bu sohbet başka bir istekle güncellendi. Sohbeti yeniden açıp sorunu tekrar gönder.")
        repo.save_turn(user_id, chat_id, request_id, question, response)
        return response
    return save


def answer_chat(user_id, chat_id, question, request_id, generate):
    """Read context, release SQL, generate, then atomically save one complete turn."""
    question = _clean_question(question)
    state = _run(lambda repo: repo.turn_state(user_id, chat_id, request_id))
    saved = _saved_response(state, question)
    if saved is not None:
        return saved
    mode, history = _context(state)
    response = _generated_turns.run(
        _replay_key(user_id, chat_id, state), request_id, {"question": question, "mode": mode},
        lambda: generate(question, expertise_mode=mode, history=history),
    )
    return _run(_saver(user_id, chat_id, request_id, question, response, state), write=True)


async def answer_chat_async(user_id, chat_id, question, request_id, generate):
    """``answer_chat`` ile aynı kurallar; SQL adımları iş parçacığında, model üretimi ``await`` ile.

    ``generate`` bir coroutine işlevidir (``generate(question, expertise_mode=..., history=...)``).
    SQL bağlantısı model çağrısı sırasında açık tutulmaz.
    """
    from async_utils import run_blocking
    question = _clean_question(question)
    state = await run_blocking(_run, lambda repo: repo.turn_state(user_id, chat_id, request_id))
    saved = _saved_response(state, question)
    if saved is not None:
        return saved
    mode, history = _context(state)
    response = await _generated_turns.run_async(
        _replay_key(user_id, chat_id, state), request_id, {"question": question, "mode": mode},
        lambda: generate(question, expertise_mode=mode, history=history),
    )
    return await run_blocking(_run, _saver(user_id, chat_id, request_id, question, response, state), write=True)
