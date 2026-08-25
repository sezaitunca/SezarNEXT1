"""
SEZARNEXT NLP Core — Numeric Normalization
==========================================
Türkçe finansal metindeki sayısal ifadeleri makine okunabilir hale getirir.

Desteklenen biçimler:
    "750.000 TL"          -> 750000.0
    "1.250.000,50 TL"     -> 1250000.5
    "%2,05"               -> 2.05
    "yüzde 1,89"          -> 1.89
    "750 bin TL"          -> 750000.0
    "1,5 milyon TL"       -> 1500000.0
    "36 ay"               -> 36
    "3 yıl"               -> 36 ay
    "beş yüz bin"         -> 500000.0
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Ölçek ve yazıyla sayı sözlükleri
# ---------------------------------------------------------------------------
SCALES: dict[str, float] = {
    "bin": 1_000,
    "b": 1_000,
    "k": 1_000,
    "milyon": 1_000_000,
    "mn": 1_000_000,
    "m": 1_000_000,
    "milyar": 1_000_000_000,
    "mr": 1_000_000_000,
}

WORD_NUMBERS: dict[str, int] = {
    "sıfır": 0, "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5,
    "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
    "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50, "altmış": 60,
    "yetmiş": 70, "seksen": 80, "doksan": 90, "yüz": 100,
}

CURRENCY_MAP: dict[str, str] = {
    "tl": "TRY", "try": "TRY", "₺": "TRY", "lira": "TRY",
    "usd": "USD", "$": "USD", "dolar": "USD",
    "eur": "EUR", "€": "EUR", "euro": "EUR",
    "gr altın": "XAU", "altın": "XAU",
}

_NUM_RE = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+\.\d{1,2}(?!\d)|\d+(?:,\d+)?")


# ---------------------------------------------------------------------------
# Temel sayı çözümü
# ---------------------------------------------------------------------------
def parse_number(token: str) -> float | None:
    """Türk formatındaki tek bir sayı token'ını float'a çevirir."""
    if token is None:
        return None
    t = token.strip().replace(" ", "").replace("\u00a0", "")
    if not t:
        return None
    t = re.sub(r"[^\d.,-]", "", t)
    if not re.search(r"\d", t):
        return None

    has_dot, has_comma = "." in t, "," in t
    if has_dot and has_comma:
        # 1.250.000,50  -> nokta binlik, virgül ondalık
        t = t.replace(".", "").replace(",", ".")
    elif has_comma:
        # 2,05 -> ondalık ; 1,250,000 gibi kullanım TR'de yok
        if t.count(",") > 1:
            t = t.replace(",", "")
        else:
            t = t.replace(",", ".")
    elif has_dot:
        parts = t.split(".")
        # 750.000 / 1.250.000 -> binlik ayırıcı
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
            t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def tr_lower(text: str) -> str:
    """
    Türkçe duyarlı küçültme.
    Python'da 'İ'.lower() → 'i' + U+0307 (birleşik nokta) üretir; bu, kelime
    sınırlarını bozar ("İki" → "i","ki"). Bu fonksiyon bunu önler.
    """
    t = text.replace("İ", "i").replace("I", "ı").lower()
    return unicodedata.normalize("NFC", "".join(
        c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c) or c in "̧̆̈"
    ))


def parse_word_number(text: str) -> float | None:
    """'beş yüz bin' gibi yazıyla ifadeleri sayıya çevirir."""
    tokens = re.findall(r"[a-zçğıöşü]+", tr_lower(text))
    if not tokens:
        return None
    total, current, seen = 0.0, 0.0, False
    for tok in tokens:
        if tok in WORD_NUMBERS:
            val = WORD_NUMBERS[tok]
            seen = True
            if val == 100:
                current = (current or 1) * 100
            else:
                current += val
        elif tok in SCALES:
            if not seen:
                return None
            total += (current or 1) * SCALES[tok]
            current = 0.0
        else:
            if seen:
                break
    if not seen:
        return None
    return total + current


def normalize_amount(text: str) -> float | None:
    """'750 bin TL', '1,5 milyon', '750.000 TL' -> float"""
    if not text:
        return None
    low = text.lower()
    m = re.search(
        r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*"
        r"(bin|milyon|milyar|mn|mr|k|b)?\b",
        low,
    )
    if m:
        base = parse_number(m.group(1))
        if base is None:
            return None
        scale = SCALES.get(m.group(2), 1.0) if m.group(2) else 1.0
        return base * scale
    return parse_word_number(low)


def normalize_rate(text: str) -> float | None:
    """'%2,05', 'yüzde 1,89', 'aylık 1.89' -> 2.05 / 1.89"""
    if not text:
        return None
    low = text.lower()
    m = re.search(r"%\s*(\d+(?:[.,]\d+)?)", low)
    if not m:
        m = re.search(r"yüzde\s*(\d+(?:[.,]\d+)?)", low)
    if not m:
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", low)
    if not m:
        return None
    val = parse_number(m.group(1))
    if val is None:
        return None
    return round(val, 4)


def normalize_maturity(text: str) -> int | None:
    """'36 ay', '3 yıl', '24 taksit' -> ay cinsinden tam sayı"""
    if not text:
        return None
    low = text.lower()
    m = re.search(r"(\d{1,3})\s*(ay|taksit|vade)", low)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,2})\s*(yıl|sene)", low)
    if m:
        return int(m.group(1)) * 12
    return None


def detect_currency(text: str) -> str:
    low = (text or "").lower()
    for key, code in CURRENCY_MAP.items():
        if key in low:
            return code
    return "TRY"


# ---------------------------------------------------------------------------
# Metin düzeyinde normalizasyon (NLP Inspector'da gösterilir)
# ---------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """
    Metni entity extractor için standart biçime getirir:
      - 'yüzde 2,05' -> '%2,05'
      - '750 bin TL' -> '750000 TL'
      - '3 yıl'      -> '36 ay'
      - birim yazımlarını sadeleştirir
    """
    if not text:
        return ""
    t = " ".join(text.split())

    t = re.sub(r"yüzde\s*(\d+(?:[.,]\d+)?)", r"%\1", t, flags=re.I)
    t = re.sub(r"(\d+(?:[.,]\d+)?)\s*%", r"%\1", t)
    t = re.sub(r"\bTürk Lirası\b|\bTL\.\b|\b₺", "TL", t, flags=re.I)

    def _scale_sub(m: re.Match) -> str:
        val = parse_number(m.group(1))
        scale = SCALES.get(m.group(2).lower(), 1.0)
        if val is None:
            return m.group(0)
        total = val * scale
        return f"{total:.0f}"

    t = re.sub(
        r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(bin|milyon|milyar)\b",
        _scale_sub,
        t,
        flags=re.I,
    )

    def _year_sub(m: re.Match) -> str:
        return f"{int(m.group(1)) * 12} ay"

    t = re.sub(r"(\d{1,2})\s*(?:yıl|sene)\b", _year_sub, t, flags=re.I)
    t = re.sub(r"\s+", " ", t)
    return t.strip()
