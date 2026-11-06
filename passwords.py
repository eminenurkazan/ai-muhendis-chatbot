"""Parola kuralları ve sürümlenmiş, salt içeren parola özetleri."""

import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def validate_password(password: str) -> None:
    if not isinstance(password, str) or not 8 <= len(password) <= 1024:
        raise ValueError("Parola 8-1024 karakter uzunluğunda olmalı.")
    if not (any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c in "0123456789" for c in password)):
        raise ValueError("Parola büyük harf, küçük harf ve rakam içermeli.")


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not isinstance(password, str) or len(password) > 1024:
        return False
    try:
        algorithm, rounds, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256" or rounds != str(ITERATIONS):
            return False
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError):
        return False
