"""
SEZARNEXT Knowledge Layer — Retriever
=====================================
Hibrit geri getirme: BM25 (sembolik) + yapısal filtre (ürün tipi, banka).
"""

from __future__ import annotations

from knowledge.indexer import BM25Index, build_index_from_campaigns
from schemas.campaign_schema import SezarNextCampaign


class Retriever:
    def __init__(self, campaigns: list[SezarNextCampaign]) -> None:
        self.campaigns = campaigns
        self.index: BM25Index = build_index_from_campaigns(campaigns)

    def search(self, query: str, top_k: int = 5, product_type: str | None = None,
               bank: str | None = None) -> list[tuple[SezarNextCampaign, float]]:
        filters = {}
        if product_type:
            filters["product_type"] = product_type
        if bank:
            filters["bank"] = bank
        hits = self.index.search(query, top_k=top_k, filters=filters or None)
        return [(self.campaigns[d.metadata["index"]], s) for d, s in hits]

    def by_bank(self, bank: str) -> list[SezarNextCampaign]:
        return [c for c in self.campaigns if c.bank.lower() == bank.lower()]

    def by_product(self, product_type: str) -> list[SezarNextCampaign]:
        return [c for c in self.campaigns if c.product_type.value == product_type]
