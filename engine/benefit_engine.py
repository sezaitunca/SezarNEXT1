"""
SEZARNEXT Benefit Engine
========================
Projeyi sıradan bir karşılaştırma tablosundan ayıran modül.

"Banka A %1,89, Banka B %1,92" demez. Gerçek ekonomik sonucu hesaplar:

    Finansman Maliyeti
  + Ücretler
  + Masraflar
  - Kampanya Kazançları
  - Ödüller
  - Ücret Muafiyetleri
  ------------------------
  = Net Ekonomik Maliyet
  → Net Economic Benefit Score
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.financial_math import (
    build_payment_plan,
    effective_annual_cost_rate,
    present_value,
    resolve_fee,
)
from schemas.campaign_schema import SezarNextCampaign


@dataclass
class CostBreakdown:
    """Tek bir teklifin kalem kalem ekonomik dökümü."""

    bank: str
    product_name: str
    principal: float
    months: int
    profit_rate: float

    monthly_payment: float = 0.0
    total_payment: float = 0.0
    profit_share_cost: float = 0.0

    allocation_fee: float = 0.0
    expertise_fee: float = 0.0
    insurance_fee: float = 0.0
    other_fees: float = 0.0
    total_fees: float = 0.0

    reward_amount: float = 0.0
    shopping_points: float = 0.0
    discount_gain: float = 0.0
    waiver_gain: float = 0.0
    total_gains: float = 0.0

    gross_cost: float = 0.0
    net_economic_cost: float = 0.0
    effective_annual_rate: float = 0.0

    benefit_score: float = 0.0
    advantage_vs_worst: float = 0.0
    advantage_vs_median: float = 0.0

    reasons: list[str] = field(default_factory=list)
    campaign: SezarNextCampaign | None = None

    def to_row(self) -> dict:
        return {
            "bank": self.bank,
            "product": self.product_name,
            "profit_rate": self.profit_rate,
            "months": self.months,
            "monthly_payment": round(self.monthly_payment, 2),
            "total_payment": round(self.total_payment, 2),
            "total_fees": round(self.total_fees, 2),
            "total_gains": round(self.total_gains, 2),
            "net_economic_cost": round(self.net_economic_cost, 2),
            "effective_annual_rate": self.effective_annual_rate,
            "benefit_score": self.benefit_score,
            "advantage_vs_median": round(self.advantage_vs_median, 2),
        }


# Varsayılan ücret tahminleri: veri yoksa 0 kabul edilir (uydurma yapılmaz).
# Bu, SEZARNEXT'in "kanıtsız sayı üretme" ilkesinin fayda motorundaki karşılığıdır.
def compute_cost(campaign: SezarNextCampaign, principal: float, months: int,
                 reward_month: int | None = None) -> CostBreakdown:
    """Tek bir kampanya/ürün için net ekonomik maliyeti hesaplar."""
    rate = campaign.profit_rate or 0.0
    plan = build_payment_plan(principal, rate, months)

    b = CostBreakdown(
        bank=campaign.bank,
        product_name=campaign.product_name,
        principal=principal,
        months=months,
        profit_rate=rate,
        campaign=campaign,
    )
    b.monthly_payment = plan.monthly_payment
    b.total_payment = plan.total_payment
    b.profit_share_cost = plan.total_profit_share

    # --- Ücretler ---
    # Genel muafiyet tüm kalemleri sıfırlar; alan bazlı 0.0 değerleri zaten
    # kaynak metinde "alınmaz" olarak doğrulanmıştır. Bilinmeyen (None) ücret
    # 0 kabul edilir — SEZARNEXT kanıtsız sayı üretmez, varsayım da yapmaz.
    waived = campaign.fee_waiver
    b.allocation_fee = 0.0 if waived else resolve_fee(
        campaign.allocation_fee, campaign.allocation_fee_is_rate, principal
    )
    b.expertise_fee = 0.0 if waived else (campaign.expertise_fee or 0.0)
    b.insurance_fee = campaign.insurance_fee or 0.0
    b.other_fees = campaign.other_fees or 0.0
    b.total_fees = b.allocation_fee + b.expertise_fee + b.insurance_fee + b.other_fees

    # --- Kazançlar (bugünkü değere indirgenmiş) ---
    m = reward_month if reward_month is not None else max(1, min(3, months))
    b.reward_amount = present_value(campaign.reward_amount or 0.0, rate, m)
    b.shopping_points = present_value((campaign.shopping_points or 0.0) * 0.95, rate, m)

    if campaign.discount_rate:
        b.discount_gain = present_value(
            plan.total_profit_share * campaign.discount_rate / 100.0, rate, m
        )

    if waived:
        # Muafiyetin ekonomik değeri: piyasa referansı yerine ilan edilen ücret
        declared = resolve_fee(campaign.allocation_fee, campaign.allocation_fee_is_rate, principal)
        b.waiver_gain = declared if declared > 0 else 0.0

    b.total_gains = b.reward_amount + b.shopping_points + b.discount_gain + b.waiver_gain

    # --- Net ekonomik maliyet ---
    b.gross_cost = b.profit_share_cost + b.total_fees
    b.net_economic_cost = b.gross_cost - b.total_gains
    b.effective_annual_rate = effective_annual_cost_rate(
        principal, rate, months, upfront_fees=b.total_fees
    )
    return b


def score_offers(breakdowns: list[CostBreakdown]) -> list[CostBreakdown]:
    """
    Net Economic Benefit Score (0-100):
      en düşük net maliyet = 100, en yüksek = 0, arası doğrusal.
      Tek teklif varsa 100 verilir.
    """
    if not breakdowns:
        return []
    costs = [b.net_economic_cost for b in breakdowns]
    best, worst = min(costs), max(costs)
    ordered = sorted(costs)
    n = len(ordered)
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    span = worst - best

    for b in breakdowns:
        b.benefit_score = 100.0 if span <= 0 else round(
            100.0 * (worst - b.net_economic_cost) / span, 2
        )
        b.advantage_vs_worst = worst - b.net_economic_cost
        b.advantage_vs_median = median - b.net_economic_cost
        b.reasons = explain(b, breakdowns)
    return breakdowns


def explain(b: CostBreakdown, peers: list[CostBreakdown]) -> list[str]:
    """Kararın gerekçelerini doğal Türkçe cümlelerle üretir (şablon tabanlı, LLM'siz)."""
    from engine.financial_math import format_pct, format_try

    reasons: list[str] = []
    rates = [p.profit_rate for p in peers if p.profit_rate]
    if rates and b.profit_rate and b.profit_rate <= min(rates) + 1e-9:
        reasons.append(
            f"Karşılaştırılan {len(peers)} teklif arasında en düşük kâr payı oranına sahip "
            f"({format_pct(b.profit_rate)})."
        )
    elif rates and b.profit_rate:
        rank = sorted(rates).index(b.profit_rate) + 1
        if rank <= 3:
            reasons.append(
                f"Kâr payı oranı bakımından {len(peers)} teklif içinde {rank}. sırada "
                f"({format_pct(b.profit_rate)})."
            )

    if b.total_fees == 0:
        reasons.append("Tahsis ücreti, ekspertiz ve benzeri masraf bulunmuyor.")
    else:
        peer_fees = [p.total_fees for p in peers]
        if peer_fees and b.total_fees < sum(peer_fees) / len(peer_fees):
            reasons.append(
                f"Toplam masrafı ({format_try(b.total_fees)}) ortalamanın altında."
            )

    if b.reward_amount > 0:
        reasons.append(f"Kampanyadan {format_try(b.reward_amount)} nakit iade kazancı sağlanıyor.")
    if b.shopping_points > 0:
        reasons.append(f"{format_try(b.shopping_points)} para puan ekonomik katkı sağlıyor.")
    if b.discount_gain > 0:
        reasons.append(f"Oran indirimi {format_try(b.discount_gain)} tasarruf üretiyor.")
    if b.waiver_gain > 0:
        reasons.append(f"Ücret muafiyeti {format_try(b.waiver_gain)} avantaj sağlıyor.")

    if b.advantage_vs_median > 0:
        reasons.append(
            f"Medyan teklife kıyasla {format_try(b.advantage_vs_median)} daha düşük "
            f"net ekonomik maliyet oluşturuyor."
        )
    return reasons[:6]


def evaluate(campaigns: list[SezarNextCampaign], principal: float, months: int) -> list[CostBreakdown]:
    """Uygun kampanyalar için tam fayda analizi (uçtan uca)."""
    breakdowns = [compute_cost(c, principal, months) for c in campaigns]
    return score_offers(breakdowns)
