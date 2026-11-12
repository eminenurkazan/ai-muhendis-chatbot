"""Yerel uygulama verileri için parametreli MSSQL sorguları.

Bağlantı ve transaction çağırana aittir: bu sınıf commit/rollback yapmaz.
user_id ileride doğrulanmış oturumdan gelmelidir; tek başına kimlik doğrulamaz.
"""

from __future__ import annotations

import json
from contextlib import closing
from uuid import UUID, uuid4

import pyodbc


class RepositoryError(RuntimeError):
    """Ham SQL, bağlantı dizesi veya kayıt içeriği göstermeyen hata."""


class RepositoryConflictError(RepositoryError):
    """Benzersizlik veya veri bütünlüğü kuralı ihlali."""


class RecordNotFoundError(RepositoryError):
    """Kayıt yok veya bu kullanıcıya ait değil."""


def _uuid(value: str) -> str:
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Geçerli bir kayıt kimliği gerekli.") from None


def _text(value: str, maximum: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Metin boş olamaz.")
    if maximum is not None and len(value) > maximum:
        raise ValueError(f"Metin {maximum} karakteri aşamaz.")
    return value


class MSSQLRepository:
    def __init__(self, connection):
        if connection.autocommit:
            raise ValueError("Bu katman autocommit=False olan bir bağlantı gerektirir.")
        self.connection = connection
        database = self._query("SELECT DB_NAME() AS name")[0]["name"]
        if database != "ServisMasasiApp":
            raise RepositoryError("Uygulama bağlantısı ServisMasasiApp veritabanını seçmeli.")
        # Hesaplanmış email_normalized alanının indeksi için oturum ayarları.
        self._query(
            "SET NOCOUNT ON; SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON; "
            "SET ANSI_PADDING ON; SET ANSI_WARNINGS ON; SET ARITHABORT ON; "
            "SET CONCAT_NULL_YIELDS_NULL ON; SET NUMERIC_ROUNDABORT OFF;"
        )

    def _query(self, sql: str, *parameters) -> list[dict]:
        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute(sql, parameters)
                results = []
                while True:
                    if cursor.description is not None:
                        columns = [column[0] for column in cursor.description]
                        results.extend(dict(zip(columns, row)) for row in cursor.fetchall())
                    # OUTPUT satırlarından sonra gelebilen SQL hatalarını da oku.
                    if not cursor.nextset():
                        break
                return results
        except pyodbc.IntegrityError:
            raise RepositoryConflictError("Kayıt, benzersizlik veya veri bütünlüğü kuralıyla çakışıyor.") from None
        except pyodbc.Error:
            raise RepositoryError("Veritabanı işlemi tamamlanamadı.") from None

    def create_user(self, email: str, password_hash: str) -> dict:
        email = _text(_text(email).strip(), 320)
        if len(email) < 3 or "@" not in email:
            raise ValueError("Geçerli bir e-posta adresi gerekli.")
        _text(password_hash, 255)
        return self._query(
            "INSERT dbo.users (id, email, password_hash) "
            "OUTPUT inserted.id, inserted.email, inserted.role, inserted.is_active "
            "VALUES (?, ?, ?)",
            str(uuid4()), email, password_hash,
        )[0]

    def find_user_by_email(self, email: str) -> dict | None:
        rows = self._query(
            "SELECT id, email, role, is_active FROM dbo.users "
            "WHERE email_normalized = LOWER(LTRIM(RTRIM(?)) COLLATE Latin1_General_100_CI_AS_SC)",
            _text(_text(email).strip(), 320),
        )
        return rows[0] if rows else None

    def find_user_for_login(self, email: str) -> dict | None:
        """Hash yalnızca kimlik doğrulama hizmetinde kullanılır; API'ye verilmez."""
        rows = self._query(
            "SELECT id, email, role, is_active, password_hash FROM dbo.users "
            "WHERE email_normalized = LOWER(LTRIM(RTRIM(?)) COLLATE Latin1_General_100_CI_AS_SC)",
            _text(_text(email).strip(), 320),
        )
        return rows[0] if rows else None

    def find_user_by_id(self, user_id: str) -> dict | None:
        rows = self._query(
            "SELECT id, email, role, is_active FROM dbo.users WHERE id = ?", _uuid(user_id),
        )
        return rows[0] if rows else None

    def create_session(self, user_id: str, title: str, expertise_mode: str = "service_desk") -> dict:
        if expertise_mode not in {"service_desk", "windows_server", "oracle_db"}:
            raise ValueError("Uzmanlık modu geçersiz.")
        rows = self._query(
            "INSERT dbo.chat_sessions (id, user_id, title, expertise_mode) "
            "OUTPUT inserted.id, inserted.user_id, inserted.title, inserted.expertise_mode "
            "SELECT ?, id, ?, ? FROM dbo.users WHERE id = ? AND is_active = 1",
            str(uuid4()), _text(title, 200), expertise_mode, _uuid(user_id),
        )
        if not rows:
            raise RecordNotFoundError("Etkin kullanıcı bulunamadı.")
        return rows[0]

    def list_sessions(self, user_id: str, *, offset: int = 0, limit: int = 100) -> list[dict]:
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 101:
            raise ValueError("Geçersiz sohbet sayfalama sınırı.")
        return self._query(
            "SELECT s.id, s.title, s.expertise_mode, s.created_at, s.updated_at "
            "FROM dbo.chat_sessions s JOIN dbo.users u ON u.id = s.user_id "
            "WHERE s.user_id = ? AND u.is_active = 1 ORDER BY s.updated_at DESC, s.id "
            "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
            _uuid(user_id), offset, limit,
        )

    def get_session(self, user_id: str, session_id: str) -> dict:
        rows = self._query(
            "SELECT s.id, s.title, s.expertise_mode, s.created_at, s.updated_at "
            "FROM dbo.chat_sessions s JOIN dbo.users u ON u.id=s.user_id "
            "WHERE s.id=? AND s.user_id=? AND u.is_active=1",
            _uuid(session_id), _uuid(user_id),
        )
        if not rows:
            raise RecordNotFoundError("Sohbet bulunamadı.")
        return rows[0]

    def _owned_session(self, user_id: str, session_id: str, *, lock: bool = False) -> None:
        # Kilit, aynı sohbete paralel yazan işlemlerin sıra numarası çakışmasını önler.
        hint = "WITH (UPDLOCK, HOLDLOCK)" if lock else ""
        rows = self._query(
            f"SELECT s.id FROM dbo.chat_sessions s {hint} "
            "JOIN dbo.users u ON u.id = s.user_id "
            "WHERE s.id = ? AND s.user_id = ? AND u.is_active = 1",
            _uuid(session_id), _uuid(user_id),
        )
        if not rows:
            raise RecordNotFoundError("Sohbet bulunamadı veya bu kullanıcıya ait değil.")

    def add_message(
        self, user_id: str, session_id: str, role: str, content: str, *,
        citations: list | None = None, source_snapshot: list | None = None,
        request_id: str | None = None, model_name: str | None = None,
    ) -> dict:
        if role not in {"user", "assistant"}:
            raise ValueError("Mesaj rolü geçersiz.")
        _text(content)
        if model_name is not None:
            _text(model_name, 100)
        if request_id is not None:
            request_id = _uuid(request_id)
        for value in (citations, source_snapshot):
            if value is not None and not isinstance(value, list):
                raise ValueError("Kaynak bilgileri liste olmalı.")
        citations_json = None if citations is None else json.dumps(citations, ensure_ascii=False, allow_nan=False)
        snapshot_json = None if source_snapshot is None else json.dumps(source_snapshot, ensure_ascii=False, allow_nan=False)
        self._owned_session(user_id, session_id, lock=True)
        row = self._query(
            "INSERT dbo.chat_messages "
            "(id, session_id, message_seq, role, content, citations_json, source_snapshot_json, request_id, model_name) "
            "OUTPUT inserted.id, inserted.message_seq, inserted.role, inserted.content, inserted.message_status "
            "SELECT ?, ?, COALESCE(MAX(message_seq), 0) + 1, ?, ?, ?, ?, ?, ? "
            "FROM dbo.chat_messages WHERE session_id = ?",
            str(uuid4()), _uuid(session_id), role, content, citations_json, snapshot_json,
            request_id, model_name, _uuid(session_id),
        )[0]
        self._query("UPDATE dbo.chat_sessions SET updated_at = SYSUTCDATETIME() WHERE id = ?", _uuid(session_id))
        return row

    def list_messages(self, user_id: str, session_id: str, *, after_seq: int = 0, limit: int = 100) -> list[dict]:
        if type(after_seq) is not int or not 0 <= after_seq <= 2147483647 or type(limit) is not int or not 1 <= limit <= 101:
            raise ValueError("Mesaj başlangıç sırası sıfır veya pozitif olmalı.")
        self._owned_session(user_id, session_id)
        return self._query(
            "SELECT TOP (?) m.id, m.message_seq, m.role, m.content, m.message_status, m.request_id, "
            "m.citations_json, m.source_snapshot_json, m.model_name, m.created_at, "
            "f.rating AS feedback_rating, f.comment AS feedback_comment "
            "FROM dbo.chat_messages m JOIN dbo.chat_sessions s ON s.id = m.session_id "
            "JOIN dbo.users u ON u.id = s.user_id "
            "LEFT JOIN dbo.feedback f ON f.message_id = m.id "
            "WHERE m.session_id = ? AND m.message_seq > ? AND s.user_id = ? AND u.is_active = 1 "
            "ORDER BY m.message_seq",
            limit, _uuid(session_id), after_seq, _uuid(user_id),
        )

    def save_feedback(self, user_id: str, session_id: str, request_id: str,
                      rating: int, comment: str | None = None) -> dict:
        if type(rating) is not int or not 1 <= rating <= 5:
            raise ValueError("Puan 1 ile 5 arasında olmalı.")
        if comment is not None:
            if not isinstance(comment, str) or len(comment) > 2000:
                raise ValueError("Yorum en fazla 2000 karakter olmalı.")
            comment = comment.strip() or None
        # Serialize the upsert and check ownership before resolving the answer.
        self._owned_session(user_id, session_id, lock=True)
        messages = self._query(
            "SELECT id FROM dbo.chat_messages WHERE session_id=? AND request_id=? "
            "AND role=N'assistant' AND message_status=N'completed'",
            _uuid(session_id), _uuid(request_id),
        )
        if len(messages) != 1:
            raise RecordNotFoundError("Değerlendirilecek yanıt bulunamadı.")
        message_id = str(messages[0]["id"])
        existing = self._query("SELECT id FROM dbo.feedback WHERE message_id=?", message_id)
        if existing:
            self._query(
                "UPDATE dbo.feedback SET rating=?, comment=?, updated_at=SYSUTCDATETIME() WHERE message_id=?",
                rating, comment, message_id,
            )
        else:
            self._query(
                "INSERT dbo.feedback (id, message_id, rating, comment) VALUES (?, ?, ?, ?)",
                str(uuid4()), message_id, rating, comment,
            )
        return {"rating": rating, "comment": comment}

    def turn_state(self, user_id: str, session_id: str, request_id: str, *, lock=False) -> dict:
        """Short transaction: authorize, check durable retry, read bounded context."""
        self._owned_session(user_id, session_id, lock=lock)
        session = self.get_session(user_id, session_id)
        saved = self._query(
            "SELECT role, content, response_json FROM dbo.chat_messages "
            "WHERE session_id=? AND request_id=? ORDER BY message_seq",
            _uuid(session_id), _uuid(request_id),
        )
        recent = self._query(
            "SELECT TOP (6) message_seq, role, content, message_status "
            "FROM dbo.chat_messages WHERE session_id=? ORDER BY message_seq DESC",
            _uuid(session_id),
        )
        return {"session": session, "saved": saved, "recent": list(reversed(recent)),
                "last_seq": recent[0]["message_seq"] if recent else 0}

    def save_turn(self, user_id: str, session_id: str, request_id: str,
                  question: str, response: dict) -> None:
        """Caller owns transaction; question, answer and replay payload commit together."""
        self.add_message(user_id, session_id, "user", question, request_id=request_id)
        answer = self.add_message(
            user_id, session_id, "assistant", response["answer"], request_id=request_id,
            citations=response.get("used_source_ids", []), source_snapshot=response.get("sources", []),
        )
        self._query(
            "UPDATE dbo.chat_messages SET response_json=?, latency_ms=? WHERE id=?",
            json.dumps(response, ensure_ascii=False, allow_nan=False), response.get("elapsed_ms"),
            str(answer["id"]),
        )

    def admin_report(self, days: int = 30, top: int = 10) -> dict:
        """Aggregate usage and quality figures for the admin panel (read-only).

        Counts cover messages created in the last ``days`` days. Ratings are
        user feedback, not an independent measure of technical correctness.
        """
        if type(days) is not int or not 1 <= days <= 365 or type(top) is not int or not 1 <= top <= 50:
            raise ValueError("Gün sayısı 1-365, liste uzunluğu 1-50 olmalı.")
        since = "DATEADD(day, -?, SYSUTCDATETIME())"
        totals = self._query(
            "SELECT "
            "(SELECT COUNT(*) FROM dbo.users) AS users_total, "
            "(SELECT COUNT(*) FROM dbo.users WHERE is_active = 1) AS users_active, "
            "(SELECT COUNT(*) FROM dbo.chat_sessions WHERE created_at >= " + since + ") AS chats, "
            "(SELECT COUNT(*) FROM dbo.chat_messages WHERE role = N'user' AND created_at >= " + since + ") AS questions, "
            "(SELECT COUNT(*) FROM dbo.chat_messages WHERE role = N'assistant' AND message_status = N'completed' "
            " AND created_at >= " + since + ") AS answers, "
            "(SELECT COUNT(*) FROM dbo.chat_messages WHERE role = N'assistant' AND message_status = N'completed' "
            " AND created_at >= " + since + " AND JSON_VALUE(response_json, '$.insufficient_context') = 'true') AS no_context_answers, "
            "(SELECT AVG(CAST(latency_ms AS float)) FROM dbo.chat_messages WHERE role = N'assistant' "
            " AND latency_ms IS NOT NULL AND created_at >= " + since + ") AS avg_latency_ms",
            days, days, days, days, days)[0]
        rated = self._query(
            "SELECT f.rating, COUNT(*) AS n FROM dbo.feedback f JOIN dbo.chat_messages m ON m.id = f.message_id "
            "WHERE m.created_at >= " + since + " GROUP BY f.rating", days)
        distribution = {rating: 0 for rating in range(1, 6)}
        for row in rated:
            distribution[int(row["rating"])] = int(row["n"])
        rated_total = sum(distribution.values())
        top_questions = self._query(
            "SELECT TOP (?) LOWER(LEFT(LTRIM(RTRIM(q.content)), 300)) AS question, COUNT(*) AS asked, "
            "AVG(CAST(f.rating AS float)) AS avg_rating, COUNT(f.id) AS rated "
            "FROM dbo.chat_messages q "
            "LEFT JOIN dbo.chat_messages a ON a.session_id = q.session_id AND a.request_id = q.request_id "
            "AND a.role = N'assistant' AND a.message_status = N'completed' "
            "LEFT JOIN dbo.feedback f ON f.message_id = a.id "
            "WHERE q.role = N'user' AND q.created_at >= " + since + " "
            "GROUP BY LOWER(LEFT(LTRIM(RTRIM(q.content)), 300)) "
            "ORDER BY COUNT(*) DESC, MAX(q.created_at) DESC",
            top, days)
        by_mode = self._query(
            "SELECT s.expertise_mode AS expertise_mode, COUNT(*) AS questions "
            "FROM dbo.chat_messages q JOIN dbo.chat_sessions s ON s.id = q.session_id "
            "WHERE q.role = N'user' AND q.created_at >= " + since + " "
            "GROUP BY s.expertise_mode ORDER BY COUNT(*) DESC", days)
        daily = self._query(
            "SELECT CAST(created_at AS date) AS day, COUNT(*) AS questions FROM dbo.chat_messages "
            "WHERE role = N'user' AND created_at >= " + since + " GROUP BY CAST(created_at AS date) ORDER BY day", days)
        answers = int(totals["answers"])
        return {
            "days": days,
            "users_total": int(totals["users_total"]), "users_active": int(totals["users_active"]),
            "chats": int(totals["chats"]), "questions": int(totals["questions"]), "answers": answers,
            "answers_with_sources": answers - int(totals["no_context_answers"]),
            "avg_latency_ms": None if totals["avg_latency_ms"] is None else round(float(totals["avg_latency_ms"])),
            "rated_total": rated_total, "satisfied": distribution[4] + distribution[5],
            "rating_distribution": distribution,
            "avg_rating": None if not rated_total else round(sum(k * v for k, v in distribution.items()) / rated_total, 2),
            "top_questions": [{"question": row["question"], "asked": int(row["asked"]), "rated": int(row["rated"]),
                               "avg_rating": None if row["avg_rating"] is None else round(float(row["avg_rating"]), 2)}
                              for row in top_questions],
            "by_mode": [{"expertise_mode": row["expertise_mode"], "questions": int(row["questions"])} for row in by_mode],
            "daily": [{"day": str(row["day"]), "questions": int(row["questions"])} for row in daily],
        }
