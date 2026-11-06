"""Kayıt doğrulaması ve kullanıcı oluşturma transaction'ı."""

from contextlib import closing
from email_domains import validate_email_tld

from email_validator import EmailNotValidError, validate_email
import pyodbc

from mssql import connection as database
from mssql.repository import MSSQLRepository, RepositoryConflictError, RepositoryError
from passwords import hash_password, validate_password


class RegistrationConflict(Exception):
    """E-posta zaten kayıtlı."""


class RegistrationUnavailable(Exception):
    """Kayıt hizmeti kullanılamıyor."""


def normalize_email(email: str) -> str:
    if not isinstance(email, str) or len(email) > 320:
        raise ValueError("Geçerli bir e-posta adresi gerekli.")
    try:
        return validate_email(email.strip(), check_deliverability=False,
                              allow_smtputf8=False).normalized
    except EmailNotValidError:
        raise ValueError("Geçerli bir e-posta adresi gerekli.") from None


def register_user(email: str, password: str) -> dict:
    email = normalize_email(email)
    validate_email_tld(email)
    validate_password(password)
    # Yavaş hash işlemi sırasında veritabanı bağlantısını açık tutma.
    encoded = hash_password(password)
    try:
        with closing(database.connect()) as connection:
            try:
                user = MSSQLRepository(connection).create_user(email, encoded)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
    except RepositoryConflictError:
        raise RegistrationConflict("Bu e-posta adresiyle kayıt oluşturulamıyor.") from None
    except (database.MSSQLConnectionError, RepositoryError, pyodbc.Error):
        raise RegistrationUnavailable("Kayıt hizmetine şu anda ulaşılamıyor. Daha sonra tekrar dene.") from None
    # SQL sonucu genişlese bile parola özeti istemciye taşınmaz.
    return {key: user[key] for key in ("id", "email", "role", "is_active")}
