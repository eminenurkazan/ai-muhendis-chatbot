"""schema.sql dosyasını PostgreSQL üzerinde çalıştırır."""

from __future__ import annotations

from pathlib import Path

import psycopg

from .connection import database_url


def main() -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    schema = schema_path.read_text(encoding="utf-8")
    # pgvector henüz etkin değilken vector adapter'ı kaydedilemez.
    # Şema önce uzantıyı oluşturur; bu bağlantıda adapter gerekmez.
    with psycopg.connect(database_url()) as connection:
        connection.execute(schema)
    print("PostgreSQL şeması oluşturuldu veya zaten mevcuttu.")


if __name__ == "__main__":
    main()
