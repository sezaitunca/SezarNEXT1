"""
SEZARNEXT Comparison Engine
===========================
Uygunluk filtreleme + çok kriterli karşılaştırma tablosu üretimi.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.benefit_engine import CostBreakdown, evaluate
from engine.financial_math import format_pct, format_try
from schemas.campaign_schema import SezarNextCampaign


@dataclass
class ComparisonRequest:
    amount: float
    months: int
    product_type: str | None = None
    currency: str = "TRY"
    top_k: int = 10


@dataclass
class ComparisonResult:
    request: ComparisonRequest
    banks_checked: int
    products_found: int
    products_eligible: int
    breakdowns: list[CostBreakdown]

    @property
    def best(self) -> CostBreakdown | None:
        return self.breakdowns[0] if self.breakdowns else None

    def table(self) -> list[dict]:
        return [b.to_row() for b in self.breakdowns]

    def pretty_table(self) -> str:
        if not self.breakdowns:
            return "Kriterlere uyan ürün bulunamadı."
        header = (
            f"{'#':<3}{'Banka':<22}{'Kâr Payı':>10}{'Taksit':>16}"
            f"{'Masraf':>14}{'Kazanç':>14}{'Net Maliyet':>17}{'Skor':>8}"
        )
        lines = [header, "-" * len(header)]
        for i, b in enumerate(self.breakdowns, 1):
            lines.append(
                f"{i:<3}{b.bank[:21]:<22}{format_pct(b.profit_rate):>10}"
                f"{format_try(b.monthly_payment):>16}{format_try(b.total_fees):>14}"
                f"{format_try(b.total_gains):>14}{format_try(b.net_economic_cost):>17}"
                f"{b.benefit_score:>8.1f}"
            )
        return "\n".join(lines)


def filter_eligible(campaigns: list[SezarNextCampaign], req: ComparisonRequest) -> list[SezarNextCampaign]:
    out = []
    for c in campaigns:
        if req.currency and c.currency.value != req.currency:
            continue
        if not c.is_active():
            continue
        if c.is_eligible(req.amount, req.months, req.product_type):
            out.append(c)
    return out


def compare(campaigns: list[SezarNextCampaign], req: ComparisonRequest) -> ComparisonResult:
    """Ana karşılaştırma akışı: filtrele → fayda hesapla → sırala."""
    banks = {c.bank for c in campaigns}
    eligible = filter_eligible(campaigns, req)
    breakdowns = evaluate(eligible, req.amount, req.months)
    breakdowns.sort(key=lambda b: b.net_economic_cost)
    return ComparisonResult(
        request=req,
        banks_checked=len(banks),
        products_found=len(campaigns),
        products_eligible=len(eligible),
        breakdowns=breakdowns[: req.top_k],
    )
