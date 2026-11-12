"""MSSQL bağlantısı: giriş süresi, zaman aşımında tek yeniden deneme, gizli bilgi sızdırmama."""
import os
import unittest
from unittest.mock import patch

import pyodbc

from mssql import connection


TIMEOUT = pyodbc.Error("08001", "[08001] [Microsoft][ODBC Driver 18 for SQL Server]Shared Memory Provider: Timeout error [258].  (258)")
LOGIN = pyodbc.Error("28000", "[28000] Login failed for user 'x' Server=secret-host Pwd=hunter2")


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {"MSSQL_CONNECTION_STRING": "DRIVER=x;SERVER=y"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_timeout_is_retried_once_then_succeeds(self):
        with patch("pyodbc.connect", side_effect=[TIMEOUT, "connection"]) as connect:
            self.assertEqual(connection.connect(), "connection")
        self.assertEqual(connect.call_count, 2)
        self.assertEqual(connect.call_args.kwargs["timeout"], 15)

    def test_second_timeout_fails_with_safe_message(self):
        with patch("pyodbc.connect", side_effect=[TIMEOUT, TIMEOUT]) as connect,              self.assertRaises(connection.MSSQLConnectionError) as error:
            connection.connect()
        self.assertEqual(connect.call_count, 2)
        self.assertNotIn("258", str(error.exception))

    def test_non_timeout_errors_are_not_retried_and_do_not_leak(self):
        with patch("pyodbc.connect", side_effect=LOGIN) as connect,              self.assertRaises(connection.MSSQLConnectionError) as error:
            connection.connect()
        self.assertEqual(connect.call_count, 1)
        self.assertNotIn("hunter2", str(error.exception))
        self.assertNotIn("secret-host", str(error.exception))

    def test_login_timeout_setting_is_clamped(self):
        for raw, expected in (("", 15), ("abc", 15), ("0", 1), ("120", 60), ("30", 30)):
            with patch.dict(os.environ, {"MSSQL_LOGIN_TIMEOUT": raw}):
                self.assertEqual(connection.login_timeout(), expected)


if __name__ == "__main__":
    unittest.main()
