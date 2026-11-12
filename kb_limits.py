"""Bilgi Merkezi yükleme sınırları; ortam değişkeniyle büyütülebilir (API ve Streamlit aynı değerleri okur).

Varsayılanlar küçüktür. Büyük dosya gerekirse her iki süreçte de değişkenleri tanımlayıp yeniden başlat:
    KB_MAX_UPLOAD_CHARS (varsayılan 1000000, en çok 20000000)
    KB_MAX_ROWS         (varsayılan 500, en çok 20000)
Geçersiz veya sınırı aşan değer varsayılana/üst sınıra çekilir.
"""
import os


def _int_env(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default
    return min(max(value, 1), maximum)


MAX_UPLOAD_CHARS = _int_env("KB_MAX_UPLOAD_CHARS", 1_000_000, 20_000_000)
MAX_ROWS = _int_env("KB_MAX_ROWS", 500, 20_000)
