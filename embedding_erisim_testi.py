"""Cloudflare BGE-M3 ile tek cumlelik embedding baglanti testi.

Python 3.11+; ek paket gerektirmez. Account ID ve token terminalden
alinir. Token ekranda gosterilmez ve herhangi bir dosyaya kaydedilmez.
Yalnizca bir API istegi gonderilir; otomatik tekrar yapilmaz.
"""

import getpass
import json
import math
import re
import sys
import urllib.error
import urllib.request


MODEL = "@cf/baai/bge-m3"
DIMENSION = 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Authorization basliginin baska bir adrese iletilmesini engeller."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_embedding(payload):
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise ValueError("API basarili bir embedding yaniti vermedi.")
    data = payload.get("result", payload)
    if not isinstance(data, dict) or data.get("error"):
        raise ValueError("API yanitinda hata var.")
    rows = data.get("data")
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("Bir metin icin bir embedding bekleniyordu.")
    row = rows[0]
    if not isinstance(row, dict) or row.get("index", 0) != 0:
        raise ValueError("Embedding sirasi dogrulanamadi.")
    vector = row.get("embedding")
    if not isinstance(vector, list) or len(vector) != DIMENSION:
        raise ValueError("Beklenen vektor boyutu 1024; API yaniti farkli.")
    for value in vector:
        if type(value) not in (int, float):
            raise ValueError("Vektorde sayisal olmayan deger var.")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("Vektorde gecersiz sayisal deger var.")
    if not any(value != 0 for value in vector):
        raise ValueError("API yalnizca sifirlardan olusan vektor dondurdu.")
    return vector


def request_embedding(account_id, token):
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        "/ai/v1/embeddings"
    )
    body = json.dumps({
        "model": MODEL,
        "input": ["Oracle veritabanina baglanirken ORA-12541 hatasi aliyorum."],
    }).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=60) as response:
        raw = response.read(262145)
    if len(raw) > 262144:
        raise ValueError("API yaniti beklenenden buyuk.")
    return validate_embedding(json.loads(raw))


def main():
    print("Cloudflare embedding baglanti testi")
    print(f"Model: {MODEL}")
    if not sys.stdin.isatty():
        print("Bu dosyayi PowerShell terminalinden calistir.")
        return 1

    account_id = input("Account ID: ").strip()
    if not re.fullmatch(r"[a-fA-F0-9]{32}", account_id):
        print("Account ID, 32 karakterlik hesap kimligi olmali; URL yapistirma.")
        return 1
    token = getpass.getpass("Workers AI API token (yazarken gorunmez): ").strip()
    if not token or not token.isascii() or any(c.isspace() for c in token):
        print("Yalnizca API token degerini yapistir; Bearer veya tirnak ekleme.")
        return 1

    print("Bir kisa cumle buluta gonderiliyor...")
    try:
        vector = request_embedding(account_id, token)
    except urllib.error.HTTPError as exc:
        hints = {
            400: "API girdi veya model istegini kabul etmedi.",
            401: "API token kabul edilmedi; dogru tokeni kopyaladigini kontrol et.",
            403: "Hesap ve Workers AI token izinlerini kontrol et.",
            404: "Hesap, API adresi veya model bulunamadi.",
            429: "Kota veya hiz sinirina ulasildi; hemen tekrar deneme.",
        }
        print(f"TEST TAMAMLANMADI: HTTP {exc.code}.")
        print(hints.get(exc.code, "Cloudflare istegi tamamlayamadi."))
        return 1
    except (urllib.error.URLError, TimeoutError):
        print("TEST TAMAMLANMADI: Baglanti kurulamadi veya zaman asimina ugradi.")
        return 1
    except (ValueError, OverflowError):
        print("TEST TAMAMLANMADI: API yanitinda gecerli 1024 boyutlu vektor yok.")
        return 1

    print(f"Vektor boyutu: {len(vector)}")
    print("TEST BASARILI: Buluttan gecerli embedding alindi.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nTest iptal edildi.")
        sys.exit(1)
