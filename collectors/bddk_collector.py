"""
SEZARNEXT Collect — BDDK Collector
==================================
Türkiye'de faaliyet gösteren katılım bankalarının kurumsal listesini sağlar.

Çevrimiçi mod: BDDK/TKBB kurumsal listesinden çeker (ağ erişimi gerekir).
Çevrimdışı mod: yerleşik kayıtlı liste (registry) kullanılır — demo ve
on-premise kurulumlar için varsayılan davranıştır.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

BDDK_SOURCE = "https://www.bddk.org.tr/Kuruluslar/Liste/68"
TKBB_SOURCE = "https://www.tkbb.org.tr/"


@dataclass
class Bank:
    name: str
    slug: str
    website: str | None = None
    type: str = "katılım"
    source: str = BDDK_SOURCE


# Kamuya açık kurumsal bilgi: Türkiye'de faaliyet gösteren katılım bankaları.
# (Ürün/oran verisi bu listeden gelmez; yalnızca kurum keşfi içindir.)
REGISTRY: list[Bank] = [
    Bank("Ziraat Katılım Bankası A.Ş.", "ziraat-katilim", "https://www.ziraatkatilim.com.tr"),
    Bank("Vakıf Katılım Bankası A.Ş.", "vakif-katilim", "https://www.vakifkatilim.com.tr"),
    Bank("Türkiye Emlak Katılım Bankası A.Ş.", "emlak-katilim", "https://www.emlakkatilim.com.tr"),
    Bank("Kuveyt Türk Katılım Bankası A.Ş.", "kuveyt-turk", "https://www.kuveytturk.com.tr"),
    Bank("Albaraka Türk Katılım Bankası A.Ş.", "albaraka-turk", "https://www.albaraka.com.tr"),
    Bank("Türkiye Finans Katılım Bankası A.Ş.", "turkiye-finans", "https://www.turkiyefinans.com.tr"),
    Bank("Hayat Katılım Bankası A.Ş.", "hayat-finans", "https://www.hayatfinans.com.tr"),
    Bank("Dünya Katılım Bankası A.Ş.", "dunya-katilim", "https://www.dunyakatilim.com.tr"),
    Bank("Golden Global Yatırım Bankası A.Ş.", "golden-global", "https://www.goldenglobalbank.com.tr"),
]


def get_banks(offline: bool = True, timeout: int = 10) -> list[Bank]:
    """Katılım bankası listesini döndürür."""
    if offline:
        return list(REGISTRY)
    try:  # pragma: no cover - ağ gerektirir
        import requests
        from bs4 import BeautifulSoup

        html = requests.get(BDDK_SOURCE, timeout=timeout).text
        soup = BeautifulSoup(html, "html.parser")
        names = [
            a.get_text(strip=True)
            for a in soup.select("a")
            if "katılım" in a.get_text(strip=True).lower()
        ]
        if not names:
            return list(REGISTRY)
        seen, out = set(), []
        for n in names:
            slug = slugify(n)
            if slug in seen:
                continue
            seen.add(slug)
            out.append(Bank(n, slug))
        return out
    except Exception:
        return list(REGISTRY)


def slugify(name: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    s = name.translate(tr).lower()
    return "-".join("".join(ch if ch.isalnum() else " " for ch in s).split())[:40]


def save_registry(path: str | Path) -> None:
    Path(path).write_text(
        json.dumps([asdict(b) for b in REGISTRY], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
