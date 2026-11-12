"""Admin-only aggregate reporting; read-only, no model calls."""
from contextlib import closing

import pyodbc
from mssql import connection as database
from mssql.repository import MSSQLRepository, RepositoryError


class ReportUnavailable(Exception):
    pass


def _rate(part, whole):
    return None if not whole else round(part / whole * 100, 1)


def report(days: int = 30, top: int = 10) -> dict:
    try:
        with closing(database.connect()) as connection:
            data = MSSQLRepository(connection).admin_report(days, top)
    except (database.MSSQLConnectionError, RepositoryError, pyodbc.Error):
        raise ReportUnavailable("Rapor verilerine şu anda ulaşılamıyor.") from None
    # Two separate, labelled rates: neither proves technical correctness.
    data["satisfaction_rate"] = _rate(data["satisfied"], data["rated_total"])
    data["source_answer_rate"] = _rate(data["answers_with_sources"], data["answers"])
    data["rating_coverage"] = _rate(data["rated_total"], data["answers"])
    return data
