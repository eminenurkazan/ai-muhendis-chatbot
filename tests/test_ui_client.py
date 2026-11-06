"""API istemcisi HTTP durumlarını ve gizli bilgilerin korunmasını sınar."""

import unittest
from unittest.mock import patch

import httpx

import ui_client


class UiClientTests(unittest.TestCase):
    def test_base_url_validation(self):
        self.assertEqual(ui_client.normalize_base_url(" http://localhost:8000/ "), "http://localhost:8000")
        for value in ("", "ftp://localhost", "http://user:pass@localhost", "http://localhost/?token=x"):
            with self.subTest(value=value), self.assertRaises(ui_client.ApiError):
                ui_client.normalize_base_url(value)

    def test_bearer_header_and_ask_payload(self):
        response = httpx.Response(200, json={"answer": "ok"})
        client = unittest.mock.MagicMock()
        client.__enter__.return_value.request.return_value = response
        with patch.object(ui_client.httpx, "Client", return_value=client):
            result = ui_client.ask("http://localhost:8000", "secret-token", "Soru", "oracle_db")
        self.assertEqual(result, {"answer": "ok"})
        args, kwargs = client.__enter__.return_value.request.call_args
        self.assertEqual(args[:2], ("POST", "http://localhost:8000/ask"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret-token")
        self.assertEqual(kwargs["json"], {"question": "Soru", "expertise_mode": "oracle_db"})

    def test_statuses_are_distinct_and_response_does_not_leak_secrets(self):
        for status in (401, 404, 405, 409, 422, 502, 503, 500):
            response = httpx.Response(status, json={"detail": "safe detail", "secret": "secret-token"})
            client = unittest.mock.MagicMock()
            client.__enter__.return_value.request.return_value = response
            with self.subTest(status=status), patch.object(ui_client.httpx, "Client", return_value=client):
                with self.assertRaises(ui_client.ApiError) as caught:
                    ui_client.current_user("http://localhost:8000", "secret-token")
                self.assertEqual(caught.exception.status, status)
                self.assertNotIn("secret-token", str(caught.exception))
                self.assertNotIn("secret-token", caught.exception.__dict__.values())
                if status == 404:
                    self.assertIn("kayıt adresini tanımıyor", str(caught.exception))
                    self.assertIn("start_api.ps1", str(caught.exception))
                if status == 500:
                    self.assertIn("API PowerShell penceresi", str(caught.exception))
        response = httpx.Response(422, json={"detail": "safe detail"})
        client = unittest.mock.MagicMock()
        client.__enter__.return_value.request.return_value = response
        with patch.object(ui_client.httpx, "Client", return_value=client):
            with self.assertRaises(ui_client.ApiError) as error:
                ui_client.request_json("http://localhost:8000", "/auth/register", method="POST")
        self.assertIn("safe detail", str(error.exception))

    def test_timeout_and_connection_errors_are_actionable(self):
        for exception, text in ((httpx.ReadTimeout("private"), "zaman aşım"),
                                (httpx.ConnectError("private"), "bağlanılamadı")):
            client = unittest.mock.MagicMock()
            client.__enter__.return_value.request.side_effect = exception
            with patch.object(ui_client.httpx, "Client", return_value=client):
                with self.assertRaises(ui_client.ApiError) as caught:
                    ui_client.current_user("http://localhost:8000", "secret-token")
            self.assertIn(text, str(caught.exception))
            self.assertNotIn("private", str(caught.exception))
            self.assertIsNone(caught.exception.status)


if __name__ == "__main__":
    unittest.main()
