"""Uygulama kullanıcıları için parola doğrulaması ve süreli JWT."""

from contextlib import closing
from datetime import datetime, timedelta, timezone
import os
from uuid import UUID, uuid4

import jwt
import pyodbc

from mssql import connection as database
from mssql.repository import MSSQLRepository, RepositoryError
from passwords import verify_password
from registration_service import normalize_email

TOKEN_SECONDS = 1800
ISSUER = "servis-masasi-api"
AUDIENCE = "servis-masasi-app"
_DUMMY_HASH = "pbkdf2_sha256$600000$" + "00" * 16 + "$" + "00" * 32


class AuthenticationError(Exception):
    """Kimlik doğrulaması başarısız."""


class AuthenticationUnavailable(Exception):
    """Oturum hizmeti hazır değil."""


def _secret() -> str:
    secret = os.environ.get("JWT_SECRET_KEY", "")
    if len(secret.encode("utf-8")) < 32 or secret == "CHANGE_ME_GENERATE_A_RANDOM_SECRET":
        raise AuthenticationUnavailable("Oturum hizmeti yapılandırılmamış.")
    return secret


def _read_user(method: str, value: str) -> dict | None:
    try:
        with closing(database.connect()) as connection:
            return getattr(MSSQLRepository(connection), method)(value)
    except (database.MSSQLConnectionError, RepositoryError, pyodbc.Error):
        raise AuthenticationUnavailable("Oturum hizmetine şu anda ulaşılamıyor.") from None


def _public(user: dict) -> dict:
    return {key: user[key] for key in ("id", "email", "role", "is_active")}


def login(email: str, password: str) -> dict:
    secret = _secret()
    try:
        email = normalize_email(email)
    except ValueError:
        raise AuthenticationError("E-posta veya parola hatalı.") from None
    user = _read_user("find_user_for_login", email)
    # Olmayan hesapta da aynı maliyetli parola kontrolünü uygula.
    matched = verify_password(password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not matched or not user["is_active"]:
        raise AuthenticationError("E-posta veya parola hatalı.")
    now = datetime.now(timezone.utc)
    token = jwt.encode({
        "sub": str(user["id"]), "iss": ISSUER, "aud": AUDIENCE,
        "iat": now, "nbf": now, "exp": now + timedelta(seconds=TOKEN_SECONDS),
        "jti": str(uuid4()),
    }, secret, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "expires_in": TOKEN_SECONDS,
            "user": _public(user)}


def current_user(token: str) -> dict:
    if not isinstance(token, str) or not token or len(token) > 4096:
        raise AuthenticationError("Oturum geçersiz veya süresi dolmuş.")
    secret = _secret()
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], issuer=ISSUER,
                            audience=AUDIENCE,
                            options={"require": ["sub", "exp", "iat", "nbf", "iss", "aud", "jti"]})
        user_id = str(UUID(claims["sub"]))
        UUID(claims["jti"])
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError):
        raise AuthenticationError("Oturum geçersiz veya süresi dolmuş.") from None
    user = _read_user("find_user_by_id", user_id)
    # Yetki her istekte güncel DB kaydından gelir; kapatılmış hesap erişemez.
    if not user or not user["is_active"]:
        raise AuthenticationError("Oturum geçersiz veya süresi dolmuş.")
    return _public(user)
