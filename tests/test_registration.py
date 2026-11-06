"""Kayıt akışı: parola güvenliği, HTTP hataları ve transaction sınırları."""

import os
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from api import app
from mssql.repository import MSSQLRepository, RepositoryConflictError
from passwords import hash_password, validate_password, verify_password
import registration_service as service

PASSWORD = "TestParolasi123"


class PasswordTests(unittest.TestCase):
    def test_salts_differ_and_only_correct_password_verifies(self):
        first, second = hash_password(PASSWORD), hash_password(PASSWORD)
        self.assertNotEqual(first, second)
        self.assertNotIn(PASSWORD, first)
        self.assertLessEqual(len(first), 255)
        self.assertTrue(verify_password(PASSWORD, first))
        self.assertFalse(verify_password("YanlisParola1", first))
        self.assertFalse(verify_password(PASSWORD, "bozuk"))

    def test_password_rules_and_no_trimming(self):
        for invalid in ("Kisa1", "abcdefgh1", "ABCDEFGH1", "Abcdefgh", "A1a" * 342):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_password(invalid)
        stored = hash_password(" TestParola1 ")
        self.assertTrue(verify_password(" TestParola1 ", stored))
        self.assertFalse(verify_password("TestParola1", stored))


class RegistrationServiceTests(unittest.TestCase):
    def test_success_commits_hashed_password_and_closes(self):
        connection = MagicMock()
        user = {"id": str(uuid4()), "email": "Test@example.com", "role": "user", "is_active": True,
                "password_hash": "must-not-be-returned"}
        with patch.object(service.database, "connect", return_value=connection), \
             patch.object(service, "MSSQLRepository") as repository:
            repository.return_value.create_user.return_value = user
            result = service.register_user(" Test@example.com ", PASSWORD)
            email, encoded = repository.return_value.create_user.call_args.args
        self.assertEqual(email, "Test@example.com")
        self.assertTrue(verify_password(PASSWORD, encoded))
        self.assertNotIn("password_hash", result)
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        connection.close.assert_called_once()

    def test_duplicate_rolls_back_without_commit(self):
        connection = MagicMock()
        with patch.object(service.database, "connect", return_value=connection), \
             patch.object(service, "MSSQLRepository") as repository:
            repository.return_value.create_user.side_effect = RepositoryConflictError("duplicate")
            with self.assertRaises(service.RegistrationConflict):
                service.register_user("test@example.com", PASSWORD)
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        connection.close.assert_called_once()

    def test_invalid_input_does_not_connect(self):
        with patch.object(service.database, "connect") as connect:
            for email, password in (("not-an-email", PASSWORD), ("test@example.com", "weak")):
                with self.assertRaises(ValueError):
                    service.register_user(email, password)
        connect.assert_not_called()

    def test_connection_failure_is_safe(self):
        with patch.object(service.database, "connect", side_effect=service.database.MSSQLConnectionError("secret")):
            with self.assertRaises(service.RegistrationUnavailable) as error:
                service.register_user("test@example.com", PASSWORD)
        self.assertNotIn("secret", str(error.exception))

    def test_commit_failure_rolls_back_and_hides_driver_details(self):
        connection = MagicMock()
        connection.commit.side_effect = service.pyodbc.Error("private connection details")
        with patch.object(service.database, "connect", return_value=connection), \
             patch.object(service, "MSSQLRepository"):
            with self.assertRaises(service.RegistrationUnavailable) as error:
                service.register_user("test@example.com", PASSWORD)
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()
        self.assertNotIn("private", str(error.exception))


class RegistrationApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_created_response_does_not_contain_password(self):
        user = {"id": str(uuid4()), "email": "test@example.com", "role": "user", "is_active": True}
        with patch.object(service, "register_user", return_value=user):
            response = self.client.post("/auth/register", json={"email": user["email"], "password": PASSWORD})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), user)
        self.assertNotIn(PASSWORD, response.text)

    def test_validation_never_echoes_password_and_rejects_role(self):
        bodies = [
            {"email": "test@example.com", "password": PASSWORD, "role": "admin"},
            {"email": "test@example.com", "password": {"value": PASSWORD}},
            {"password": PASSWORD},
            {"email": "test@example.com", "password": "Kisa1"},
        ]
        with patch.object(service, "register_user") as register:
            for body in bodies:
                response = self.client.post("/auth/register", json=body)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn(PASSWORD, response.text)
            malformed = self.client.post("/auth/register", content='{"password":"' + PASSWORD + '"',
                                         headers={"Content-Type": "application/json"})
            self.assertEqual(malformed.status_code, 422)
            self.assertNotIn(PASSWORD, malformed.text)
        register.assert_not_called()

    def test_service_errors_have_expected_http_status(self):
        for error, status in ((ValueError("Geçersiz bilgi."), 422),
                              (service.RegistrationConflict("Kayıt oluşturulamıyor."), 409),
                              (service.RegistrationUnavailable("Hizmet hazır değil."), 503)):
            with patch.object(service, "register_user", side_effect=error):
                response = self.client.post("/auth/register", json={"email": "test@example.com", "password": PASSWORD})
            self.assertEqual(response.status_code, status)
            self.assertNotIn(PASSWORD, response.text)


@unittest.skipUnless(os.environ.get("MSSQL_TEST_CONNECTION_STRING"), "Yerel MSSQL test bağlantısı tanımlı değil.")
class RegistrationDatabaseTests(unittest.TestCase):
    def test_real_hash_and_case_insensitive_duplicate_with_rollback(self):
        import pyodbc
        connection = pyodbc.connect(os.environ["MSSQL_TEST_CONNECTION_STRING"], autocommit=False, timeout=5)
        self.addCleanup(connection.close)
        self.addCleanup(connection.rollback)
        repository = MSSQLRepository(connection)
        email = f"register-{uuid4()}@example.com"
        user = repository.create_user(email, hash_password(PASSWORD))
        row = connection.cursor().execute("SELECT password_hash FROM dbo.users WHERE id = ?", user["id"]).fetchone()
        self.assertTrue(verify_password(PASSWORD, row[0]))
        self.assertEqual(user["role"], "user")
        with self.assertRaises(RepositoryConflictError):
            repository.create_user(email.upper(), hash_password(PASSWORD))
