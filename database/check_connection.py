"""PostgreSQL ve pgvector bağlantısını doğrular."""

from __future__ import annotations

from .connection import DatabaseError, connect


def main() -> None:
    try:
        with connect() as connection:
            database_name, user_name = connection.execute(
                "SELECT current_database(), current_user"
            ).fetchone()
            vector_version = connection.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()
    except DatabaseError:
        raise
    except Exception as exc:
        raise DatabaseError("Bağlantı testi sırasında PostgreSQL sorgusu başarısız oldu.") from exc

    if vector_version is None:
        raise DatabaseError(
            "PostgreSQL'e bağlanıldı fakat pgvector etkin değil. "
            "Önce database/schema.sql dosyasındaki extension satırlarını çalıştır."
        )
    print(f"Bağlantı başarılı: database={database_name}, user={user_name}")
    print(f"pgvector sürümü: {vector_version[0]}")


if __name__ == "__main__":
    try:
        main()
    except DatabaseError as exc:
        raise SystemExit(f"BAĞLANTI BAŞARISIZ: {exc}") from None
