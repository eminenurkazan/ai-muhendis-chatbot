"""JWT ve giriş akışı; canlı model çağrısı yapmaz."""

from datetime import datetime, timezone
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from api import app
import auth_service as auth
from passwords import hash_password

SECRET = "test-key-only-" + "a" * 64
PASSWORD = "TestParola123"


class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user = {"id": str(uuid4()), "email": "test@example.com", "role": "user",
                    "is_active": True, "password_hash": hash_password(PASSWORD)}

    def setUp(self):
        self.environment = patch.dict(os.environ, {"JWT_SECRET_KEY": SECRET})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = TestClient(app)

    def token(self, **overrides):
        now = int(datetime.now(timezone.utc).timestamp())
        claims = {"sub": self.user["id"], "iss": auth.ISSUER, "aud": auth.AUDIENCE,
                  "iat": now, "nbf": now, "exp": now + 1800, "jti": str(uuid4())}
        claims.update(overrides)
        return jwt.encode(claims, SECRET, algorithm="HS256")

    def test_login_issues_limited_token_without_hash_or_password(self):
        with patch.object(auth, "_read_user", return_value=self.user):
            response = self.client.post("/auth/login", json={"email": self.user["email"], "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["expires_in"], 1800)
        self.assertNotIn(PASSWORD, response.text)
        self.assertNotIn("password_hash", response.text)
        claims = jwt.decode(body["access_token"], SECRET, algorithms=["HS256"], audience=auth.AUDIENCE, issuer=auth.ISSUER)
        self.assertEqual(claims["sub"], self.user["id"])
        self.assertEqual(claims["exp"] - claims["iat"], 1800)
        self.assertNotIn("role", claims)

    def test_wrong_password_unknown_and_disabled_user_have_same_error(self):
        bodies = []
        for user, password in ((self.user, "WrongPassword1"), (None, PASSWORD),
                               ({**self.user, "is_active": False}, PASSWORD)):
            with patch.object(auth, "_read_user", return_value=user):
                response = self.client.post("/auth/login", json={"email": self.user["email"], "password": password})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")
            bodies.append(response.json())
        self.assertEqual(bodies[0], bodies[1])
        self.assertEqual(bodies[1], bodies[2])

    def test_missing_or_short_secret_is_not_replaced_by_default(self):
        for secret in ("", "short", "CHANGE_ME_GENERATE_A_RANDOM_SECRET"):
            with patch.dict(os.environ, {"JWT_SECRET_KEY": secret}), patch.object(auth, "_read_user") as read:
                response = self.client.post("/auth/login", json={"email": self.user["email"], "password": PASSWORD})
                self.assertEqual(response.status_code, 503)
                read.assert_not_called()

    def test_bad_login_input_never_echoes_password(self):
        for body in ({"password": PASSWORD}, {"email": "x", "password": {"secret": PASSWORD}},
                     {"email": "test@example.com", "password": PASSWORD, "role": "admin"}):
            response = self.client.post("/auth/login", json=body)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(PASSWORD, response.text)

    def test_unauthed_ask_rejected_before_rag_call(self):
        with patch("rag_service.ask_question") as ask:
            for headers in ({}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer broken"}):
                response = self.client.post("/ask", json={"question": "Test"}, headers=headers)
                self.assertEqual(response.status_code, 401)
            ask.assert_not_called()

    def test_me_uses_current_database_role_and_hides_hash(self):
        with patch.object(auth, "_read_user", return_value={**self.user, "role": "admin"}):
            response = self.client.get("/auth/me", headers={"Authorization": "Bearer " + self.token()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "admin")
        self.assertNotIn("password_hash", response.text)

    def test_expired_wrong_issuer_audience_subject_and_future_tokens_rejected(self):
        now = int(datetime.now(timezone.utc).timestamp())
        for overrides in ({"exp": now - 10}, {"iss": "other"}, {"aud": "other"},
                          {"sub": "not-a-uuid"}, {"nbf": now + 3600}):
            with self.subTest(overrides=overrides), patch.object(auth, "_read_user") as read:
                response = self.client.get("/auth/me", headers={"Authorization": "Bearer " + self.token(**overrides)})
                self.assertEqual(response.status_code, 401)
                read.assert_not_called()

    def test_wrong_signature_algorithm_and_missing_claim_rejected(self):
        good = jwt.decode(self.token(), SECRET, algorithms=["HS256"], audience=auth.AUDIENCE)
        missing = {key: value for key, value in good.items() if key != "exp"}
        tokens = [jwt.encode(good, "b" * 64, algorithm="HS256"),
                  jwt.encode(good, SECRET, algorithm="HS384"),
                  jwt.encode(missing, SECRET, algorithm="HS256")]
        for token in tokens:
            with patch.object(auth, "_read_user") as read:
                self.assertEqual(self.client.get("/auth/me", headers={"Authorization": "Bearer " + token}).status_code, 401)
                read.assert_not_called()

    def test_removed_or_disabled_user_cannot_use_valid_token(self):
        for user in (None, {**self.user, "is_active": False}):
            with patch.object(auth, "_read_user", return_value=user):
                self.assertEqual(self.client.get("/auth/me", headers={"Authorization": "Bearer " + self.token()}).status_code, 401)

    def test_valid_token_database_failure_returns_503(self):
        with patch.object(auth.database, "connect", side_effect=auth.database.MSSQLConnectionError("private")):
            response = self.client.get("/auth/me", headers={"Authorization": "Bearer " + self.token()})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.text)


@unittest.skipUnless(os.environ.get("MSSQL_TEST_CONNECTION_STRING"), "Yerel MSSQL test bağlantısı tanımlı değil.")
class AuthDatabaseTests(unittest.TestCase):
    def test_register_login_me_ask_and_disable_with_real_sql_rollback(self):
        import pyodbc
        connection = pyodbc.connect(os.environ["MSSQL_TEST_CONNECTION_STRING"], timeout=5, autocommit=False)
        self.addCleanup(connection.close)
        self.addCleanup(connection.rollback)

        class RollbackOnlyConnection:
            """API gerçek SQL kullanır; test tüm kayıtları tek transaction'da tutar."""
            autocommit = False

            def cursor(self):
                return connection.cursor()

            def commit(self):
                pass

            def rollback(self):
                connection.rollback()

            def close(self):
                pass

        client = TestClient(app)
        email = f"auth-{uuid4()}@example.com"
        with patch.dict(os.environ, {"JWT_SECRET_KEY": SECRET}), \
             patch.object(auth.database, "connect", return_value=RollbackOnlyConnection()):
            registered = client.post("/auth/register", json={"email": email, "password": PASSWORD})
            self.assertEqual(registered.status_code, 201)
            logged_in = client.post("/auth/login", json={"email": email.upper(), "password": PASSWORD})
            self.assertEqual(logged_in.status_code, 200)
            headers = {"Authorization": "Bearer " + logged_in.json()["access_token"]}
            me = client.get("/auth/me", headers=headers)
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["id"], registered.json()["id"])
            answer = {"answer": "Test", "used_ticket_ids": [], "insufficient_context": True,
                      "retrieved_ticket_ids": [], "elapsed_ms": 0, "expertise_mode": "service_desk",
                      "prompt_version": "test", "used_source_ids": [], "retrieved_source_ids": [], "sources": []}
            with patch("rag_service.ask_question", return_value=answer) as ask:
                self.assertEqual(client.post("/ask", json={"question": "Test"}, headers=headers).status_code, 200)
                ask.assert_called_once()
            connection.cursor().execute("UPDATE dbo.users SET is_active=0 WHERE id=?", registered.json()["id"])
            self.assertEqual(client.get("/auth/me", headers=headers).status_code, 401)
