"""Add the nullable response snapshot column without changing existing messages."""
from contextlib import closing
from pathlib import Path
from mssql.connection import connect


def main():
    with closing(connect()) as connection:
        try:
            with closing(connection.cursor()) as cursor:
                cursor.execute(Path(__file__).with_name("chat_persistence.sql").read_text(encoding="utf-8"))
                while cursor.nextset():
                    pass
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    print("Kalıcı sohbet için veritabanı hazır. Mevcut kayıtlar korundu.")


if __name__ == "__main__":
    main()
