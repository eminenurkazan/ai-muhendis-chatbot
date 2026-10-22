"""SQL Server bağlantısını yalnızca okuyarak kontrol et."""

from __future__ import annotations

from contextlib import closing

from .connection import connect


def main() -> None:
    with closing(connect()) as connection:
        database_name, user_name = connection.execute(
            "SELECT DB_NAME(), SUSER_SNAME()"
        ).fetchone()
    print(f"SQL Server bağlantısı başarılı: database={database_name}, user={user_name}")


if __name__ == "__main__":
    main()
