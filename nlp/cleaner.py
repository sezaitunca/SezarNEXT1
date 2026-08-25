"""
SEZARNEXT NLP Core — Text Cleaning
==================================
HTML kaynaklı gürültüyü temizler, Türkçe finansal metni tek satıra indirger.
Regex tabanlıdır; harici bağımlılık gerektirmez (bs4 varsa kullanır).
"""

from __future__ import annotations

import html
import re
import unicodedata

# Sayfa iskeletinden gelen ve anlam taşımayan bloklar
_BOILERPLATE = (
    "çerez politikası",
    "kişisel verilerin korunması",
    "kvkk aydınlatma metni",
    "tüm hakları saklıdır",
    "bize ulaşın",
    "müşteri hizmetleri",
    "sosyal medya",
    "site haritası",
    "gizlilik politikası",
)

_SCRIPT_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\u00a0\u200b]+")
_NL_RE = re.compile(r"\n{3,}")


def strip_html(raw: str) -> str:
    """HTML etiketlerini kaldırır. bs4 mevcutsa daha güvenli yol kullanılır."""
    try:  # pragma: no cover - ortama bağlı
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text("\n")
    except Exception:
        text = _SCRIPT_RE.sub(" ", raw)
        text = _TAG_RE.sub(" ", text)
    return html.unescape(text)


def fix_turkish(text: str) -> str:
    """Bozuk kodlama ve Türkçe karakter sorunlarını onarır."""
    repl = {
        "Ä±": "ı", "Ä°": "İ", "ÅŸ": "ş", "Åž": "Ş", "Ã§": "ç", "Ã‡": "Ç",
        "ÄŸ": "ğ", "Äž": "Ğ", "Ã¶": "ö", "Ã–": "Ö", "Ã¼": "ü", "Ãœ": "Ü",
        "â€™": "'", "â€œ": '"', "â€": '"', "â€“": "-", "â€”": "-",
        "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2022": "-",
    }
    for bad, good in repl.items():
        text = text.replace(bad, good)
    return unicodedata.normalize("NFC", text)


def drop_boilerplate(text: str) -> str:
    kept = []
    for line in text.split("\n"):
        low = line.strip().lower()
        if not low:
            continue
        if any(bp in low for bp in _BOILERPLATE):
            continue
        if len(low) < 3:
            continue
        kept.append(line.strip())
    return "\n".join(kept)


def clean(raw: str, keep_lines: bool = False) -> str:
    """Ana temizleme boru hattı: HTML → Türkçe onarım → boilerplate → boşluk."""
    if not raw:
        return ""
    text = strip_html(raw) if "<" in raw and ">" in raw else raw
    text = fix_turkish(text)
    text = drop_boilerplate(text)
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    if not keep_lines:
        text = text.replace("\n", " ")
        text = _WS_RE.sub(" ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """Türkçe cümle bölme. Sayı içindeki noktaları (750.000) korur."""
    protected = re.sub(r"(?<=\d)\.(?=\d)", "\u0000", text)
    parts = re.split(r"(?<=[.!?;:])\s+(?=[A-ZÇĞİÖŞÜ0-9])|\n+", protected)
    out = []
    for p in parts:
        p = p.replace("\u0000", ".").strip()
        if len(p) > 8:
            out.append(p)
    return out
