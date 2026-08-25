"""
SEZARNEXT Collect — Bank Discovery
==================================
Bir bankanın kurumsal sitesinde ürün ve kampanya sayfalarını keşfeder.
Sitemap → aday URL desenleri → link taraması sırasıyla ilerler.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

PRODUCT_PATTERNS = [
    r"finansman", r"kredi", r"tasit|taşıt|arac|araç", r"konut", r"ihtiyac|ihtiyaç",
    r"katilma-hesabi|katılma-hesabı", r"kart", r"yatirim|yatırım", r"sukuk",
    r"bireysel", r"ticari", r"kobi",
]
CAMPAIGN_PATTERNS = [r"kampanya", r"firsat|fırsat", r"avantaj", r"promosyon", r"duyuru"]

CANDIDATE_PATHS = [
    "/kampanyalar", "/kampanya", "/bireysel/kampanyalar", "/firsatlar",
    "/bireysel/finansman", "/bireysel/krediler", "/tasit-finansmani",
    "/konut-finansmani", "/ihtiyac-finansmani", "/bireysel/kartlar",
    "/katilma-hesabi", "/sitemap.xml",
]


def classify_url(url: str) -> str:
    low = url.lower()
    if any(re.search(p, low) for p in CAMPAIGN_PATTERNS):
        return "campaign"
    if any(re.search(p, low) for p in PRODUCT_PATTERNS):
        return "product"
    return "other"


def candidate_urls(base_url: str) -> list[str]:
    return [urljoin(base_url, p) for p in CANDIDATE_PATHS]


def discover(base_url: str, fetcher=None, max_links: int = 120) -> dict[str, list[str]]:
    """
    Aday URL'leri döndürür. `fetcher` verilmezse ağ erişimi denenmez;
    yalnızca desen tabanlı aday listesi üretilir (offline mod).
    """
    result: dict[str, list[str]] = {"product": [], "campaign": [], "other": []}

    if fetcher is None:
        for u in candidate_urls(base_url):
            result[classify_url(u)].append(u)
        return result

    try:  # pragma: no cover
        from bs4 import BeautifulSoup

        html = fetcher(base_url)
        soup = BeautifulSoup(html, "html.parser")
        host = urlparse(base_url).netloc
        seen = set()
        for a in soup.find_all("a", href=True):
            url = urljoin(base_url, a["href"])
            if urlparse(url).netloc != host or url in seen:
                continue
            seen.add(url)
            result[classify_url(url)].append(url)
            if len(seen) >= max_links:
                break
    except Exception:
        for u in candidate_urls(base_url):
            result[classify_url(u)].append(u)
    return result
