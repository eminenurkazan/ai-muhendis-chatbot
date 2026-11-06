"""IANA uzantı listesine göre e-posta alan adı kontrolü (ağ çağrısı yapmaz)."""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def registered_tlds() -> frozenset[str]:
    # Public reference data only; no credentials or user data are cached.
    path = Path(__file__).parent / "auth_frontend" / "tlds.json"
    return frozenset(json.loads(path.read_text(encoding="utf-8-sig")))


def validate_email_tld(email: str) -> None:
    try:
        domain = email.strip().rsplit("@", 1)[1].encode("idna").decode("ascii").lower()
        if domain.rsplit(".", 1)[-1] not in registered_tlds():
            raise ValueError
    except (IndexError, UnicodeError, ValueError):
        raise ValueError("Geçerli bir e-posta adresi gir.") from None
