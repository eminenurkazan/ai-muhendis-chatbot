"""Streamlit arayüzünün FastAPI istemcisi. Kimlik bilgilerini saklamaz veya loglamaz."""

from urllib.parse import urlsplit

import httpx


class ApiError(Exception):
    def __init__(self, status: int | None, message: str):
        super().__init__(message)
        self.status = status


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError
        if parsed.query or parsed.fragment:
            raise ValueError
        return value
    except (ValueError, AttributeError):
        raise ApiError(None, "API adresi geçersiz; http://127.0.0.1:8000 kullanabilirsin.") from None


def request_json(base_url: str, path: str, *, method: str = "GET", payload: dict | None = None,
                 token: str | None = None, timeout: float = 180) -> dict:
    base_url = normalize_base_url(base_url)
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout, connect=8), follow_redirects=False) as client:
            response = client.request(method, base_url + path, json=payload, headers=headers)
    except httpx.TimeoutException:
        raise ApiError(None, "İstek zaman aşımına uğradı. Biraz bekleyip tekrar dene.") from None
    except httpx.RequestError:
        raise ApiError(None, "API'ye bağlanılamadı. API'nin açık olduğunu ve adresini kontrol et.") from None
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code >= 400:
        # Sunucudan gelen ham girdileri, tokenları ve dahili hata ayrıntılarını ekrana taşıma.
        if response.status_code == 401:
            message = "Oturum doğrulanamadı. Yeniden giriş yap."
        elif response.status_code == 403:
            message = "Bu bölüm yalnızca yönetici hesapları içindir."
        elif response.status_code == 404:
            message = "Sohbet bulunamadı veya bu hesaba ait değil." if path.startswith("/chats/") else ("Çalışan API kayıt adresini tanımıyor (404). Eski API'yi kendi terminalinde "
                       "Ctrl+C ile durdurup proje klasöründe `powershell.exe -NoProfile "
                       "-ExecutionPolicy Bypass -File .\\start_api.ps1` komutuyla yeniden başlat.")
        elif response.status_code == 405:
            message = "API isteği reddetti (405). Çalışan API sürümünü yeniden başlatıp tekrar dene."
        elif response.status_code == 422:
            detail = body.get("detail", "Girilen bilgileri kontrol et.")
            if isinstance(detail, list):
                message = "\n".join(item for item in detail if isinstance(item, str))
            else:
                message = str(detail)
        elif response.status_code == 409:
            message = str(body.get("detail", "Bu e-posta ile kayıt oluşturulamadı."))
        elif response.status_code == 503:
            if path in {"/auth/register", "/auth/login", "/auth/me"}:
                message = "Hesap hizmetine şu anda ulaşılamıyor. Veritabanı bağlantısı kontrol edilmeli. Bilgilerin hatalı olduğu anlamına gelmez."
            else:
                # /ask exposes only controlled ServiceUnavailable details; unexpected errors are 502.
                detail = body.get("detail")
                message = detail if isinstance(detail, str) and detail else "Yanıt hizmeti şu anda hazır değil. Biraz sonra tekrar dene."
        elif response.status_code == 502:
            message = "Yanıt oluşturulamadı. Biraz bekleyip tekrar dene."
        elif response.status_code >= 500:
            message = f"Sunucu isteği tamamlayamadı ({response.status_code}). API PowerShell penceresindeki hata iletisini kontrol et."
        else:
            message = f"İstek tamamlanamadı (HTTP {response.status_code}). API adresini ve çalışan sunucuyu kontrol et."
        raise ApiError(response.status_code, message)
    if not isinstance(body, dict):
        raise ApiError(response.status_code, "API beklenmeyen bir yanıt verdi.")
    return body


def register(base_url: str, email: str, password: str) -> dict:
    return request_json(base_url, "/auth/register", method="POST",
                        payload={"email": email, "password": password}, timeout=20)


def login(base_url: str, email: str, password: str) -> dict:
    return request_json(base_url, "/auth/login", method="POST",
                        payload={"email": email, "password": password}, timeout=20)


def current_user(base_url: str, token: str) -> dict:
    return request_json(base_url, "/auth/me", token=token, timeout=15)


def ask(base_url: str, token: str, question: str, expertise_mode: str, *, history=None, request_id=None) -> dict:
    payload = {"question": question, "expertise_mode": expertise_mode}
    if request_id is not None:
        payload["request_id"] = str(request_id)
    if history:
        from conversation import validate_history
        payload["history"] = validate_history(history)
    return request_json(base_url, "/ask", method="POST",
                        payload=payload,
                        token=token, timeout=180)


def create_chat(base_url, token, title, expertise_mode):
    return request_json(base_url, "/chats", method="POST", token=token,
                        payload={"title": title[:200], "expertise_mode": expertise_mode}, timeout=20)


def list_chats(base_url, token, offset=0):
    return request_json(base_url, f"/chats?offset={offset}&limit=50", token=token, timeout=20)


def load_messages(base_url, token, chat_id):
    from uuid import UUID
    chat_id = str(UUID(str(chat_id)))
    messages, after = [], 0
    while True:
        page = request_json(base_url, f"/chats/{chat_id}/messages?after_seq={after}&limit=100",
                            token=token, timeout=20)
        messages.extend(page["items"])
        next_after = page.get("next_after_seq")
        if next_after is None:
            return messages
        if next_after <= after:
            raise ApiError(None, "Sohbet geçmişi okunamadı.")
        after = next_after


def ask_saved(base_url, token, chat_id, question, request_id):
    from uuid import UUID
    chat_id = str(UUID(str(chat_id)))
    return request_json(base_url, f"/chats/{chat_id}/ask", method="POST", token=token,
                        payload={"question": question, "request_id": str(request_id)}, timeout=180)


def admin_report(base_url, token, days=30):
    days = int(days)
    return request_json(base_url, f"/admin/report?days={days}&top=10", token=token, timeout=30)


def save_feedback(base_url, token, chat_id, request_id, rating, comment=None):
    from uuid import UUID
    chat_id, request_id = str(UUID(str(chat_id))), str(UUID(str(request_id)))
    return request_json(base_url, f"/chats/{chat_id}/requests/{request_id}/feedback", method="PUT",
                        token=token, payload={"rating": rating, "comment": comment}, timeout=20)


def kb_summary(base_url, token):
    return request_json(base_url, "/admin/kb/summary", token=token, timeout=30)


def kb_records(base_url, token, *, review_status=None, domain=None, record_type=None, query=None, offset=0):
    from urllib.parse import urlencode
    params = {key: value for key, value in (("review_status", review_status), ("domain", domain),
              ("record_type", record_type), ("q", query)) if value}
    params.update({"offset": int(offset), "limit": 50})
    return request_json(base_url, "/admin/kb/records?" + urlencode(params), token=token, timeout=30)


def kb_upload(base_url, token, payload):
    return request_json(base_url, "/admin/kb/upload", method="POST", payload=payload, token=token, timeout=60)


def kb_approve(base_url, token, ids):
    return request_json(base_url, "/admin/kb/approve", method="POST", payload={"ids": [str(i) for i in ids]},
                        token=token, timeout=180)


def kb_set_status(base_url, token, record_id, excluded):
    from uuid import UUID
    return request_json(base_url, f"/admin/kb/records/{UUID(str(record_id))}/status", method="POST",
                        payload={"excluded": bool(excluded)}, token=token, timeout=30)
