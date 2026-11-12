"""Mevcut bir kullanıcıyı yönetici yapar: python -m mssql.promote_admin <e-posta> [--user]."""
import sys
from contextlib import closing

from mssql.connection import connect

SESSION_SETTINGS = ("SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON; SET ANSI_PADDING ON; SET ANSI_WARNINGS ON; "
                    "SET ARITHABORT ON; SET CONCAT_NULL_YIELDS_NULL ON; SET NUMERIC_ROUNDABORT OFF;")


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    role = "user" if "--user" in argv else "admin"
    if len(args) != 1:
        raise SystemExit("Kullanım: python -m mssql.promote_admin <e-posta> [--user]")
    with closing(connect()) as connection:
        try:
            with closing(connection.cursor()) as cursor:
                cursor.execute(SESSION_SETTINGS)
                cursor.execute("UPDATE dbo.users SET role = ? WHERE email_normalized = "
                               "LOWER(LTRIM(RTRIM(?)) COLLATE Latin1_General_100_CI_AS_SC)", role, args[0])
                changed = cursor.rowcount
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    print(f"Rol '{role}' olarak ayarlandı." if changed == 1 else "Kullanıcı bulunamadı; değişiklik yapılmadı.")


if __name__ == "__main__":
    main(sys.argv[1:])
