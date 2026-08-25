"""
SEZARNEXT Ranking Engine
========================
Çok kriterli sıralama (MCDA). Kullanıcı önceliğine göre ağırlık profili seçilir:

  - "net_cost"   : yalnızca net ekonomik maliyet (varsayılan)
  - "cash_flow"  : aylık taksit yükü öncelikli
  - "upfront"    : peşin masraf duyarlı
  - "balanced"   : dengeli profil
"""

from __future__ import annotations

from engine.benefit_engine import CostBreakdown

WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "net_cost": {"net": 1.00, "monthly": 0.00, "fees": 0.00, "gains": 0.00, "rate": 0.00},
    "cash_flow": {"net": 0.35, "monthly": 0.45, "fees": 0.05, "gains": 0.05, "rate": 0.10},
    "upfront": {"net": 0.35, "monthly": 0.10, "fees": 0.45, "gains": 0.05, "rate": 0.05},
    "balanced": {"net": 0.45, "monthly": 0.20, "fees": 0.15, "gains": 0.10, "rate": 0.10},
}


def _norm(values: list[float], lower_is_better: bool = True) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [1.0] * len(values)
    if lower_is_better:
        return [(hi - v) / (hi - lo) for v in values]
    return [(v - lo) / (hi - lo) for v in values]


def rank(breakdowns: list[CostBreakdown], profile: str = "net_cost") -> list[tuple[CostBreakdown, float]]:
    """Ağırlıklı skorla sıralar. (breakdown, skor) çiftleri döndürür."""
    if not breakdowns:
        return []
    w = WEIGHT_PROFILES.get(profile, WEIGHT_PROFILES["net_cost"])

    n_net = _norm([b.net_economic_cost for b in breakdowns])
    n_month = _norm([b.monthly_payment for b in breakdowns])
    n_fees = _norm([b.total_fees for b in breakdowns])
    n_gains = _norm([b.total_gains for b in breakdowns], lower_is_better=False)
    n_rate = _norm([b.profit_rate for b in breakdowns])

    scored = []
    for i, b in enumerate(breakdowns):
        score = (
            w["net"] * n_net[i]
            + w["monthly"] * n_month[i]
            + w["fees"] * n_fees[i]
            + w["gains"] * n_gains[i]
            + w["rate"] * n_rate[i]
        )
        scored.append((b, round(score * 100, 2)))
    scored.sort(key=lambda x: -x[1])
    return scored
