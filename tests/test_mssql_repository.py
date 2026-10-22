"""Yerel SQL Server entegrasyon testleri; tüm örnek kayıtlar geri alınır."""

import json
import os
import unittest
from uuid import uuid4

from mssql.repository import MSSQLRepository, RecordNotFoundError, RepositoryConflictError, RepositoryError


@unittest.skipUnless(os.environ.get("MSSQL_TEST_CONNECTION_STRING"), "Yerel MSSQL test bağlantısı tanımlı değil.")
class MSSQLRepositoryTests(unittest.TestCase):
    def setUp(self):
        import pyodbc
        self.connection = pyodbc.connect(os.environ["MSSQL_TEST_CONNECTION_STRING"], timeout=5, autocommit=False)
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        self.repo = MSSQLRepository(self.connection)

    def user(self):
        return self.repo.create_user(f"test-{uuid4()}@example.invalid", "test-only-not-a-real-password-hash")

    def test_user_lookup_normalizes_email_and_does_not_return_hash(self):
        email = f"Test-{uuid4()}@example.invalid"
        user = self.repo.create_user(f" {email} ", "test-only-not-a-real-password-hash")
        found = self.repo.find_user_by_email(email.upper())
        self.assertEqual(found["id"], user["id"])
        self.assertNotIn("password_hash", found)
        self.assertEqual(found["role"], "user")

    def test_duplicate_normalized_email_has_safe_error(self):
        user = self.user()
        with self.assertRaises(RepositoryConflictError) as caught:
            self.repo.create_user(user["email"].upper(), "test-only-not-a-real-password-hash")
        self.assertNotIn(user["email"], str(caught.exception))
        self.assertNotIn("INSERT", str(caught.exception))

    def test_sessions_are_scoped_to_owner_and_sql_text_is_saved_as_data(self):
        owner, other = self.user(), self.user()
        title = "Türkçe sohbet '; DROP TABLE dbo.users; --"
        session = self.repo.create_session(owner["id"], title)
        self.assertEqual(self.repo.list_sessions(owner["id"])[0]["id"], session["id"])
        self.assertEqual(self.repo.list_sessions(owner["id"])[0]["title"], title)
        self.assertEqual(self.repo.list_sessions(other["id"]), [])
        with self.assertRaises(RecordNotFoundError):
            self.repo.list_messages(other["id"], session["id"])
        with self.assertRaises(RecordNotFoundError):
            self.repo.add_message(other["id"], session["id"], "user", "İzinsiz mesaj")
        self.assertEqual(self.repo.list_messages(owner["id"], session["id"]), [])

    def test_messages_keep_order_unicode_and_source_snapshot(self):
        owner = self.user()
        session = self.repo.create_session(owner["id"], "Geçici sohbet")
        request_id = str(uuid4())
        citations = [{"ticket_id": "1007444.0"}]
        snapshot = [{"ticket_id": "1007444.0", "text": "UAT doğrulaması"}]
        self.repo.add_message(owner["id"], session["id"], "user", "Numara değişikliği iptal edilince ne olmuş?")
        self.repo.add_message(owner["id"], session["id"], "assistant", "UAT'ta doğrulanmış.",
                              request_id=request_id, citations=citations, source_snapshot=snapshot,
                              model_name="test-model")
        rows = self.repo.list_messages(owner["id"], session["id"])
        self.assertEqual([row["message_seq"] for row in rows], [1, 2])
        self.assertEqual(rows[1]["content"], "UAT'ta doğrulanmış.")
        self.assertEqual(json.loads(rows[1]["citations_json"]), citations)
        self.assertEqual(json.loads(rows[1]["source_snapshot_json"]), snapshot)
        self.assertEqual(len(self.repo.list_messages(owner["id"], session["id"], after_seq=1)), 1)

    def test_unknown_user_and_invalid_inputs_are_rejected(self):
        with self.assertRaises(RecordNotFoundError):
            self.repo.create_session(str(uuid4()), "Sahipsiz sohbet")
        owner = self.user()
        with self.assertRaises(ValueError):
            self.repo.create_session(owner["id"], "Sohbet", "unknown")
        session = self.repo.create_session(owner["id"], "Sohbet")
        with self.assertRaises(ValueError):
            self.repo.add_message(owner["id"], session["id"], "system", "İçerik")
        with self.assertRaises(ValueError):
            self.repo.add_message(owner["id"], session["id"], "user", " ")
        self.assertEqual(self.repo.list_messages(owner["id"], session["id"]), [])

    def test_system_database_is_rejected(self):
        self.connection.execute("USE master")
        with self.assertRaises(RepositoryError):
            MSSQLRepository(self.connection)


if __name__ == "__main__":
    unittest.main()
