"""Yerel ChatGPT plan erisim testi (Python 3.11+).

Kurulum: python -m pip install "PyJWT[crypto]"
Calistirma: python plus_erisim_testi.py

Bu dosya RAG uygulamasi degil, tek bir baglanti denemesidir.
Kaynaklar (2 Ekim 2026):
https://developers.openai.com/siwc/token-sharing-open-source/sign-in
https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations

Host ve kayit kimligi proje disindaki kullanici klasorunde saklanir.
Erisim, yenileme ve kimlik tokenlari sadece bellekte tutulur; tekrar
calistirmada yeniden giris gerekir. Uretim icin token yenileme ve korumali
kimlik bilgisi saklama ayrica uygulanmalidir. Ucretli API'ye gecis yapilmaz.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid
import webbrowser

import jwt


AUTH = "https://auth.openai.com"
API = "https://api.openai.com/v1"
APP_NAME = "AI Muhendis Chatbot - Yerel Erisim Testi"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
PLAN_SCOPE = "chatgpt.tokens.use.direct"


class TestError(Exception):
    """Kimlik bilgisi icermeyen, terminalde paylasilabilir hata."""


def safe_label(value: object) -> str:
    value = str(value)
    return value if re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value) else "ayrinti-gizlendi"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Bearer tokeni baska bir adrese yonlendirmeyiz.
        return None


def http_open(req: Request, operation: str, timeout: int = 45):
    try:
        return build_opener(NoRedirect()).open(req, timeout=timeout)
    except HTTPError as error:
        code = "unknown_error"
        try:
            body = json.loads(error.read(65536))
            detail = body.get("error", {}) if isinstance(body, dict) else {}
            code = detail.get("code") or detail.get("type") or code if isinstance(detail, dict) else detail
        except (ValueError, AttributeError):
            pass
        request_id = safe_label(error.headers.get("x-request-id", "yok"))
        raise TestError(
            f"{operation}: HTTP {error.code}; kod={safe_label(code)}; request_id={request_id}"
        ) from None
    except (URLError, TimeoutError, OSError):
        raise TestError(f"{operation}: baglanti kurulamadi veya zaman asimi.") from None


def http_json(url: str, operation: str, *, token: str | None = None, form: dict | None = None) -> dict:
    headers = {"Accept": "application/json", "User-Agent": "ai-muhendis-chatbot-access-test/0.1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(form).encode("ascii")
    with http_open(Request(url, data=data, headers=headers), operation) as response:
        try:
            result = json.load(response)
        except (ValueError, UnicodeError):
            raise TestError(f"{operation}: gecerli JSON yaniti alinamadi.") from None
    if not isinstance(result, dict):
        raise TestError(f"{operation}: beklenmeyen yanit bicimi.")
    return result


def state_path() -> Path:
    base = Path(os.environ["LOCALAPPDATA"]) if os.environ.get("LOCALAPPDATA") else Path.home() / ".local" / "share"
    folder = base / "ai-muhendis-chatbot-erisim-testi"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "registration.json"


def write_state(path: Path, state: dict) -> None:
    # Bu dosyada OAuth tokenlari yoktur. Gecici dosya ayni diskte atomik tasinir.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump(state, output, ensure_ascii=False, indent=2)
        if os.name != "nt":
            temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def read_state(path: Path) -> dict:
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            host_id = state["host_id"]
            if not isinstance(host_id, str) or not host_id.startswith("urn:uuid:"):
                raise ValueError
            uuid.UUID(host_id.removeprefix("urn:uuid:"))
            client = state.get("client_id")
            if client is not None and (not isinstance(client, str) or not client or client == "dynamic_agent_client"):
                raise ValueError
            return state
        except (ValueError, KeyError, TypeError):
            raise TestError("Yerel kayit bilgisi okunamadi; bu hatayi paylas.") from None
    state = {"host_id": f"urn:uuid:{uuid.uuid4()}"}
    write_state(path, state)
    return state


def parse_callback(path: str, expected_state: str, saved_client: str | None) -> dict:
    parts = urlsplit(path)
    if parts.path != "/auth/callback":
        raise TestError("Beklenmeyen geri donus yolu.")
    values = parse_qs(parts.query, keep_blank_values=True)

    def one(name: str) -> str:
        found = values.get(name, [])
        if len(found) != 1 or not found[0]:
            raise TestError(f"Geri donuste {name} eksik veya tekrarli.")
        return found[0]

    if not secrets.compare_digest(one("state"), expected_state):
        raise TestError("Geri donus guvenlik kontrolu (state) basarisiz.")
    if "error" in values:
        raise TestError(f"Giris izni tamamlanmadi: {safe_label(one('error'))}")
    code = one("code")
    supplied = one("client_id") if "client_id" in values else None
    if saved_client and supplied and supplied != saved_client:
        raise TestError("Geri donusteki uygulama kaydi beklenen kayitla eslesmiyor.")
    client = saved_client or supplied
    if not client or client == "dynamic_agent_client":
        raise TestError("OpenAI uygulama kayit kimligini dondurmedi; kayit tamamlanmadi.")
    return {"code": code, "client_id": client}


class CallbackServer(HTTPServer):
    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address


def authorize(state: dict, authorization_endpoint: str) -> tuple[dict, str, str]:
    pending_state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    outcome: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Callback URL'sinde kod bulunur; HTTP gunlugune yazmayiz.

        def send_page(self, status: int, body: str):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.headers.get("Host") != f"127.0.0.1:{server.server_port}":
                self.send_page(400, "Gecersiz yerel adres.")
                return
            route = urlsplit(self.path).path
            if route == "/":
                self.send_page(200,
                    "<!doctype html><html lang='tr'><meta charset='utf-8'>"
                    "<title>Yerel model erisim testi</title><h1>ChatGPT hesabini bagla</h1>"
                    "<p>Bu yerel test, sectigin modelden tek bir kisa yanit almak icin "
                    "ChatGPT plan kotani kullanir.</p><p><a href='/authorize'>Continue with ChatGPT</a></p>"
                    "<p>Giris sonrasi bu pencereyi kapatip terminale donebilirsin.</p></html>")
            elif route == "/authorize":
                self.send_response(302)
                self.send_header("Location", auth_url)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Length", "0")
                self.end_headers()
            elif route == "/auth/callback":
                try:
                    outcome["result"] = parse_callback(self.path, pending_state, state.get("client_id"))
                except TestError as error:
                    outcome["error"] = error
                self.send_page(200, "<meta charset='utf-8'><p>Terminale don. Hesap ve erisim kontrolu orada tamamlanacak.</p>")
            else:
                self.send_page(404, "Bulunamadi.")

    with CallbackServer(("127.0.0.1", 0), Handler) as server:
        redirect_uri = f"http://127.0.0.1:{server.server_port}/auth/callback"
        params = {
            "client_id": state.get("client_id") or "dynamic_agent_client",
            "ext_agent_host_id": state["host_id"],
            "response_type": "code", "redirect_uri": redirect_uri,
            "scope": SCOPES, "resource": API, "state": pending_state,
            "nonce": nonce, "code_challenge_method": "S256", "code_challenge": challenge,
        }
        if not state.get("client_id"):
            params["agent_name_hint"] = APP_NAME
        auth_url = authorization_endpoint + "?" + urlencode(params)
        start_url = f"http://127.0.0.1:{server.server_port}/"
        print("1/3 Tarayicida Continue with ChatGPT dugmesine bas ve hesabini sec.")
        print(f"Tarayici acilmazsa bu yerel adresi ac: {start_url}")
        webbrowser.open(start_url)
        deadline = time.monotonic() + 300
        server.timeout = 1
        while not outcome and time.monotonic() < deadline:
            server.handle_request()
        if not outcome:
            raise TestError("Giris icin 5 dakikalik sure doldu. Testi yeniden calistir.")
        if "error" in outcome:
            raise outcome["error"]
    result = outcome["result"]
    result["redirect_uri"] = redirect_uri
    return result, verifier, nonce


def verify_identity(token: str, client_id: str, nonce: str, jwks: dict, issuer: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        # Anahtari tokenin bir URL alanindan degil, OpenAI JWKS'inden seceriz.
        algorithm = header.get("alg")
        if algorithm not in ("RS256", "ES256"):
            raise TestError("ID tokeninin imza algoritmasi desteklenmiyor.")
        keys = [key for key in jwks.get("keys", []) if key.get("kid") == header.get("kid") and key.get("use", "sig") == "sig"]
        if not header.get("kid") or len(keys) != 1:
            raise TestError("ID tokeni icin tek bir dogrulama anahtari bulunamadi.")
        key = jwt.PyJWK.from_dict(keys[0], algorithm=algorithm).key
        claims = jwt.decode(token, key, algorithms=[algorithm], audience=client_id,
                            issuer=issuer, leeway=5,
                            options={"require": ["sub", "exp", "iat", "iss", "aud", "nonce"]})
        if not isinstance(claims.get("nonce"), str) or not secrets.compare_digest(claims["nonce"], nonce):
            raise TestError("ID tokeni guvenlik kontrolu (nonce) basarisiz.")
        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise TestError("Dogrulanmis hesap kimligi yok.")
        return claims
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise TestError("ID tokeninin imzasi veya kimlik alanlari dogrulanamadi.") from None


def choose_model(catalog: dict) -> str:
    models = [model for model in catalog.get("models", [])
              if isinstance(model, dict) and model.get("visibility") == "list" and isinstance(model.get("slug"), str) and model["slug"]]
    if not models:
        raise TestError("Bu hesap icin gorunur bir model listesi alinamadi.")
    print("2/3 Hesabinin model katalogu (erisim tek yanitla dogrulanacak):")
    for number, model in enumerate(models, 1):
        print(f"  {number}. {model.get('display_name') or model['slug']} [{model['slug']}]")
    while True:
        choice = input("Denenecek modelin numarasi (Enter = 1): ").strip() or "1"
        if choice.isdecimal() and 1 <= int(choice) <= len(models):
            return models[int(choice) - 1]["slug"]
        print("Listedeki bir numarayi yaz.")


def sse_events(response):
    data: list[str] = []
    for raw_line in response:
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if not line:
            if data:
                payload = "\n".join(data)
                data = []
                if payload != "[DONE]":
                    yield json.loads(payload)
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
    if data and "\n".join(data) != "[DONE]":
        yield json.loads("\n".join(data))


def consume_answer(events) -> None:
    completed = False
    for event in events:
        kind = event.get("type")
        if kind == "response.output_text.delta":
            print(event.get("delta", ""), end="", flush=True)
        elif kind in ("response.failed", "response.incomplete", "error"):
            detail = event.get("response", {}).get("error") or event.get("error") or event
            code = detail.get("code", kind) if isinstance(detail, dict) else kind
            print()
            raise TestError(f"Yanit tamamlanmadi: {safe_label(code)}. Gorunen metin kismi olabilir.")
        elif kind == "response.completed":
            if event.get("response", {}).get("status") not in (None, "completed"):
                raise TestError("Yanit tamamlandi olayi beklenmeyen bir durum iceriyor.")
            completed = True
    print()
    if not completed:
        raise TestError("Akis basarili tamamlanma olayi (response.completed) gelmeden kesildi.")


def request_answer(token: str, model: str) -> None:
    body = {
        "model": model,
        "input": [{"role": "user", "content": "Yalnizca su iki kelimeyi yaz: Baglanti basarili."}],
        "store": False, "stream": True,
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
               "Accept": "text/event-stream", "User-Agent": "ai-muhendis-chatbot-access-test/0.1"}
    request = Request(API + "/responses", data=json.dumps(body).encode("utf-8"), headers=headers)
    print(f"3/3 Tek kisa mesaj gonderiliyor. Model: {model}")
    with http_open(request, "Model yaniti", timeout=120) as response:
        try:
            consume_answer(sse_events(response))
        except (ValueError, UnicodeError, OSError):
            raise TestError("Yanit akisi okunamadi veya kesildi.") from None
    print("TEST BASARILI: response.completed alindi.")
    print(f"Dogrulanan model: {model}")


def main() -> None:
    print("Yerel ChatGPT plan erisim testi. RAG ve ticket verileri bu testte kullanilmiyor.")
    path = state_path()
    state = read_state(path)
    config = http_json(AUTH + "/.well-known/openid-configuration", "OpenAI kimlik ayarlari")
    if config.get("issuer") != AUTH:
        raise TestError("Beklenmeyen OpenAI kimlik saglayicisi.")
    for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        parts = urlsplit(config.get(field, ""))
        if parts.scheme != "https" or parts.netloc != "auth.openai.com":
            raise TestError("Beklenmeyen OpenAI kimlik dogrulama adresi.")
    callback, verifier, nonce = authorize(state, config["authorization_endpoint"])
    state["client_id"] = callback["client_id"]
    write_state(path, state)  # Kod degisimi basarisizsa da verilen client_id korunur.
    tokens = http_json(config["token_endpoint"], "Giris kodunu degistirme", form={
        "grant_type": "authorization_code", "client_id": callback["client_id"],
        "code": callback["code"], "code_verifier": verifier,
        "redirect_uri": callback["redirect_uri"], "resource": API,
    })
    id_token = tokens.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise TestError("Giris yanitinda kimlik tokeni yok.")
    jwks = http_json(config["jwks_uri"], "OpenAI imza anahtarlari")
    identity = verify_identity(id_token, callback["client_id"], nonce, jwks, config["issuer"])
    if state.get("subject") and state["subject"] != identity["sub"]:
        raise TestError("Secilen hesap bu yerel kayda bagli hesapla eslesmiyor.")
    state["subject"] = identity["sub"]
    write_state(path, state)
    print("Hesap kimligi dogrulandi.")
    if PLAN_SCOPE not in str(tokens.get("scope", "")).split():
        raise TestError("ChatGPT plan kullanimi izni verilmedi; model istegi yapilmadi.")
    token = tokens.get("access_token")
    if not isinstance(token, str) or not token or str(tokens.get("token_type", "")).lower() != "bearer":
        raise TestError("Plan kullanimi icin gecerli erisim tokeni alinamadi.")
    catalog = http_json(API + "/models", "Model listesi", token=token)
    model = choose_model(catalog)
    request_answer(token, model)


if __name__ == "__main__":
    try:
        main()
    except TestError as error:
        print(f"\nTEST TAMAMLANMADI: {error}", file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nTest durduruldu.", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        # Ham istisnalar URL, OAuth kodu veya token icerebilir; yazdirmayiz.
        print(f"\nTEST TAMAMLANMADI: beklenmeyen hata ({type(error).__name__}).", file=sys.stderr)
        sys.exit(1)
