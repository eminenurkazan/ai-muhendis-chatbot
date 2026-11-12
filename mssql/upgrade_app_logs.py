"""Günlük tablosuna zaman indeksini ekler (idempotent). Önce MSSQL_CONNECTION_STRING tanımlanmalıdır."""
from contextlib import closing
from pathlib import Path
from mssql.connection import connect


def main():
    with closing(connect()) as connection:
        try:
            with closing(connection.cursor()) as cursor:
                cursor.execute(Path(__file__).with_name("app_logs_index.sql").read_text(encoding="utf-8"))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    print("Günlük indeksi hazır. Mevcut kayıtlar korundu.")


if __name__ == "__main__":
    main()
