"""
SEZARNEXT Collect — Bank Adapter Base
=====================================
Her banka sitesi farklı DOM yapısına sahiptir. Adaptör deseni, banka özel
seçicilerini çekirdek boru hattından ayırır: yeni banka eklemek = yeni adaptör.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawCampaign:
    bank: str
    source_url: str
    title: str
    body: str
    scraped_at: datetime


class BaseBankAdapter:
    """Tüm banka adaptörlerinin sözleşmesi."""

    bank_name: str = "Bilinmeyen Banka"
    base_url: str = ""
    # Banka özel CSS seçicileri
    campaign_list_selector: str = ".campaign-item, .kampanya-item, article"
    title_selector: str = "h1, h2, .title"
    body_selector: str = ".content, .detail, .description, p"

    def parse_list(self, html: str, url: str) -> list[RawCampaign]:
        try:
            from bs4 import BeautifulSoup
        except Exception:
            return []
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for node in soup.select(self.campaign_list_selector):
            title_el = node.select_one(self.title_selector)
            title = title_el.get_text(strip=True) if title_el else ""
            body = node.get_text(" ", strip=True)
            if len(body) < 40:
                continue
            out.append(
                RawCampaign(
                    bank=self.bank_name,
                    source_url=url,
                    title=title or body[:60],
                    body=body,
                    scraped_at=datetime.now(),
                )
            )
        return out

    def to_pipeline(self, raw: RawCampaign):
        """Ham kaydı NLP Core'a besler ve SezarNextCampaign üretir."""
        from nlp.pipeline import run_pipeline

        return run_pipeline(
            raw_text=f"{raw.title}. {raw.body}",
            bank=raw.bank,
            source_url=raw.source_url,
            product_name=raw.title,
            scraped_at=raw.scraped_at,
        )


class GenericAdapter(BaseBankAdapter):
    """Seçici bilinmeyen bankalar için sezgisel (heuristic) adaptör."""

    def __init__(self, bank_name: str, base_url: str) -> None:
        self.bank_name = bank_name
        self.base_url = base_url
