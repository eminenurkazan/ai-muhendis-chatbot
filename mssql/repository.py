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
            "m.citations_json, m.source_snapshot_json, m.model_name, m.created_at "
            "FROM dbo.chat_messages m JOIN dbo.chat_sessions s ON s.id = m.session_id "
            "JOIN dbo.users u ON u.id = s.user_id "
            "WHERE m.session_id = ? AND m.message_seq > ? AND s.user_id = ? AND u.is_active = 1 "
            "ORDER BY m.message_seq",
            limit, _uuid(session_id), after_seq, _uuid(user_id),
        )
