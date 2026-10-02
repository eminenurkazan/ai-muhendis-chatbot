r"""10 ticket icinde Cloudflare BGE-M3 ile anlamsal arama.

Calistirma: .\.venv\Scripts\python.exe ticket_vektor_arama.py
Python 3.11+; yalnizca standart kutuphane kullanilir.
CSV, bu dosyayla ayni klasorde tickets_pilot_10.csv adiyla bulunmali.
Vektorler outputs_local/ticket_vektorleri.json dosyasinda tutulur.
Git'e eklemeden once .gitignore'a outputs_local/ satirini ekle.
Token bellekte tutulur; dosyaya kaydedilmez. Her soru icin bir API istegi
yapilir. CSV degismediyse ticket vektorleri tekrar olusturulmaz.
"""

import csv
import getpass
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.request


MODEL = "@cf/baai/bge-m3"
DIMENSION = 1024
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "tickets_pilot_10.csv"
CACHE_PATH = BASE_DIR / "outputs_local" / "ticket_vektorleri.json"
REQUIRED_COLUMNS = {"issueid", "problem", "solution"}


class PilotError(Exception):
    """Kullaniciya anahtar veya ham API yaniti gostermeyen hata."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_tickets(path):
    raw = path.read_bytes()
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise PilotError("CSV'de eksik sutunlar var: " + ", ".join(sorted(missing)))
        records = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise PilotError(f"CSV satir {line_number}: sutun sayisi tutarsiz.")
            record = {key: value.strip() for key, value in row.items()}
            if any(not record[key] for key in REQUIRED_COLUMNS):
                raise PilotError(f"CSV satir {line_number}: issueid, problem veya solution bos.")
            records.append(record)
    except UnicodeError:
        raise PilotError("CSV dosyasi UTF-8 veya UTF-8-BOM olmali.") from None
    if not 1 <= len(records) <= 10:
        raise PilotError("Bu pilot 1-10 ticket icindir; tickets_pilot_10.csv dosyasini kontrol et.")
    return records, hashlib.sha256(raw).hexdigest()


def embedding_text(record):
    # Kimlik ve onay bilgileri kayitla birlikte saklanir; bu iki metin aranir.
    return f"Problem: {record['problem']}\nSolution: {record['solution']}"


def normalized_vector(vector):
    if not isinstance(vector, list) or len(vector) != DIMENSION:
        raise PilotError("Beklenen vektor boyutu 1024; gelen veri farkli.")
    for value in vector:
        if type(value) not in (int, float):
            raise PilotError("Vektorde sayisal olmayan deger var.")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise PilotError("Vektorde gecersiz sayisal deger var.")
    # Once olceklendirmek, norm hesabinda sayisal tasmayi onler.
    scale = max(abs(value) for value in vector)
    if scale == 0:
        raise PilotError("Sifir vektoru ile arama yapilamaz.")
    scaled = [value / scale for value in vector]
    norm = math.sqrt(math.fsum(value * value for value in scaled))
    return [value / norm for value in scaled]


def response_vectors(payload, count):
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise PilotError("API basarili bir embedding yaniti vermedi.")
    body = payload.get("result", payload)
    if not isinstance(body, dict) or body.get("error"):
        raise PilotError("API yanitinda hata var.")
    rows = body.get("data")
    if not isinstance(rows, list) or len(rows) != count:
        raise PilotError("API'nin dondurdugu vektor sayisi girdi sayisiyla uyusmuyor.")
    ordered = [None] * count
    for row in rows:
        if not isinstance(row, dict):
            raise PilotError("API vektor kaydi gecersiz.")
        index = row.get("index")
        if type(index) is not int or not 0 <= index < count or ordered[index] is not None:
            raise PilotError("API vektor sirasi dogrulanamadi.")
        ordered[index] = normalized_vector(row.get("embedding"))
    return ordered


def cloud_embeddings(account_id, token, texts):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/embeddings"
    request = urllib.request.Request(
        url,
        data=json.dumps({"model": MODEL, "input": texts}, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=60) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise PilotError("API yaniti beklenenden buyuk.")
        return response_vectors(json.loads(raw), len(texts))
    except urllib.error.HTTPError as exc:
        hints = {
            400: "Girdiler veya model istegi kabul edilmedi.",
            401: "API token kabul edilmedi.",
            403: "Hesap ve Workers AI token izinlerini kontrol et.",
            404: "Hesap, API adresi veya model bulunamadi.",
            429: "Kota veya hiz sinirina ulasildi; hemen tekrar deneme.",
        }
        raise PilotError(f"HTTP {exc.code}: " + hints.get(exc.code, "Cloudflare istegi tamamlayamadi.")) from None
    except (urllib.error.URLError, TimeoutError):
        raise PilotError("Baglanti kurulamadi veya zaman asimina ugradi.") from None
    except (ValueError, UnicodeError):
        raise PilotError("API okunabilir bir JSON yaniti vermedi.") from None


def load_cache(path, records, csv_hash):
    if not path.exists():
        return None
    if path.stat().st_size > 2_000_000:
        raise PilotError("Vektor kaydi beklenenden buyuk; outputs_local dosyasini kontrol et.")
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(saved, dict):
            raise PilotError("Vektor kaydi gecersiz.")
        if (saved.get("format_version"), saved.get("model"), saved.get("dimensions"), saved.get("csv_sha256")) != (1, MODEL, DIMENSION, csv_hash):
            return None
        if saved.get("records") != records:
            return None
        vectors = saved.get("vectors")
        if not isinstance(vectors, list) or len(vectors) != len(records):
            raise PilotError("Vektor kaydi eksik.")
        return [normalized_vector(vector) for vector in vectors]
    except (ValueError, UnicodeError):
        raise PilotError("Vektor dosyasi okunamadi; bu olusturulmus JSON dosyasini kaldirip tekrar calistir.") from None


def save_cache(path, records, csv_hash, vectors):
    path.parent.mkdir(parents=True, exist_ok=True)
    saved = {
        "format_version": 1,
        "model": MODEL,
        "dimensions": DIMENSION,
        "csv_sha256": csv_hash,
        "records": records,
        "vectors": vectors,
    }
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            json.dump(saved, handle, ensure_ascii=False, allow_nan=False)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def top_matches(records, vectors, query_vector):
    scored = []
    for record, vector in zip(records, vectors):
        score = math.fsum(left * right for left, right in zip(query_vector, vector))
        scored.append((score, record))
    return sorted(scored, key=lambda pair: pair[0], reverse=True)[:3]


def show_matches(matches):
    print("\nEn yakin ticket'lar (kosinus benzerligi, dogruluk yuzdesi degil):")
    for rank, (score, record) in enumerate(matches, start=1):
        print(f"\n{rank}. issueid={record['issueid']} | benzerlik={score:.4f}")
        print("Problem:", record["problem"])
        print("Cozum:", record["solution"])
        for field in ("category", "resolution", "resolution_confirmed", "source_comment_seq", "solution_scope", "limitations"):
            if record.get(field):
                print(f"{field}: {record[field]}")


def main():
    print("Ticket anlamsal arama pilotu")
    print(f"Model: {MODEL}")
    records, csv_hash = read_tickets(CSV_PATH)
    print(f"Okunan ticket sayisi: {len(records)}")
    vectors = load_cache(CACHE_PATH, records, csv_hash)
    if not sys.stdin.isatty():
        raise PilotError("Dosyayi PowerShell terminalinden calistir.")
    account_id = input("Account ID: ").strip()
    if not re.fullmatch(r"[a-fA-F0-9]{32}", account_id):
        raise PilotError("Account ID, 32 karakterlik hesap kimligi olmali; URL yapistirma.")
    token = getpass.getpass("Workers AI API token (yazarken gorunmez): ").strip()
    if not token or not token.isascii() or any(char.isspace() for char in token):
        raise PilotError("Yalnizca API token degerini yapistir; Bearer veya tirnak ekleme.")

    if vectors is None:
        print(f"{len(records)} ticket icin buluttan vektorler aliniyor...")
        vectors = cloud_embeddings(account_id, token, [embedding_text(record) for record in records])
        save_cache(CACHE_PATH, records, csv_hash, vectors)
        print("Ticket vektorleri kaydedildi: outputs_local/ticket_vektorleri.json")
    else:
        print("Kayitli ticket vektorleri yuklendi.")
    print(f"Vektor boyutu: {DIMENSION}")
    print("\nIlk kaydin issueid degeri:", records[0]["issueid"])
    print("Ilk kaydin problemi:", records[0]["problem"])
    print("Bu problemi kendi sozlerinle Turkce sorarak aramayi deneyebilirsin.")
    print("Her aramada yalnizca sorunun vektoru buluttan alinir. Cikis icin bos Enter.")
    while True:
        query = input("\nSorun: ").strip()
        if not query:
            return 0
        query_vector = cloud_embeddings(account_id, token, [query])[0]
        show_matches(top_matches(records, vectors, query_vector))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PilotError as exc:
        print(f"\nISLEM TAMAMLANMADI: {exc}")
        sys.exit(1)
    except OSError as exc:
        if isinstance(exc, FileNotFoundError):
            print("\nDosya bulunamadi. tickets_pilot_10.csv ile bu Python dosyasini ayni klasore koy.")
        else:
            print("\nYerel dosya okunamadi veya yazilamadi; dosya izinlerini kontrol et.")
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nArama kapatildi.")
        sys.exit(0)
