"""
SEZARNEXT — Financial Math
==========================
Katılım finansmanı (murabaha esaslı) geri ödeme matematiği.

Not: Katılım bankacılığında taksit, peşin bedel üzerine eklenen kâr marjıyla
oluşan vadeli satış bedelinin eşit bölünmesidir. Hesaplama pratikte
konvansiyonel anüite formülüyle aynı sonucu verir; SEZARNEXT terminolojiyi
katılım esaslı kullanır (faiz değil, kâr payı).

Tüm fonksiyonlar saf Python'dur; harici bağımlılık yoktur.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaymentPlan:
    """Bir finansman teklifinin tam geri ödeme planı."""

    principal: float
    monthly_rate: float          # % cinsinden aylık kâr payı
    months: int
    monthly_payment: float
    total_payment: float
    total_profit_share: float    # toplam kâr payı yükü
    schedule: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "principal": round(self.principal, 2),
            "monthly_rate": self.monthly_rate,
            "months": self.months,
            "monthly_payment": round(self.monthly_payment, 2),
            "total_payment": round(self.total_payment, 2),
            "total_profit_share": round(self.total_profit_share, 2),
        }


def monthly_installment(principal: float, monthly_rate_pct: float, months: int) -> float:
    """
    Eşit taksitli murabaha ödemesi.

        T = P * r * (1+r)^n / ((1+r)^n - 1)

    r = 0 ise (kâr payısız / faizsiz kampanya) taksit = P / n.
    """
    if months <= 0:
        raise ValueError("Vade pozitif olmalıdır")
    r = monthly_rate_pct / 100.0
    if r <= 0:
        return principal / months
    factor = (1 + r) ** months
    return principal * r * factor / (factor - 1)


def build_payment_plan(principal: float, monthly_rate_pct: float, months: int,
                       with_schedule: bool = False) -> PaymentPlan:
    inst = monthly_installment(principal, monthly_rate_pct, months)
    total = inst * months
    plan = PaymentPlan(
        principal=principal,
        monthly_rate=monthly_rate_pct,
        months=months,
        monthly_payment=inst,
        total_payment=total,
        total_profit_share=total - principal,
    )
    if with_schedule:
        r = monthly_rate_pct / 100.0
        balance = principal
        for i in range(1, months + 1):
            profit = balance * r
            capital = inst - profit
            balance = max(0.0, balance - capital)
            plan.schedule.append(
                {
                    "installment_no": i,
                    "payment": round(inst, 2),
                    "profit_share": round(profit, 2),
                    "capital": round(capital, 2),
                    "remaining": round(balance, 2),
                }
            )
    return plan


def effective_annual_cost_rate(principal: float, monthly_rate_pct: float, months: int,
                               upfront_fees: float = 0.0) -> float:
    """
    Yıllık maliyet oranı (%). Peşin ücretler nakit akışına dahil edilerek
    IRR (iç verim oranı) bisection ile çözülür → bankalar arası adil kıyas.
    """
    inst = monthly_installment(principal, monthly_rate_pct, months)
    net_cash = principal - upfront_fees
    if net_cash <= 0:
        return float("inf")

    def npv(r: float) -> float:
        return sum(inst / ((1 + r) ** t) for t in range(1, months + 1)) - net_cash

    lo, hi = 0.0, 1.0
    if npv(lo) < 0:
        return 0.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    monthly_irr = (lo + hi) / 2
    return round(((1 + monthly_irr) ** 12 - 1) * 100, 4)


def present_value(amount: float, monthly_rate_pct: float, month: int) -> float:
    """Gelecekteki bir kazancın bugünkü değeri (ödül/iade zamanlaması için)."""
    r = monthly_rate_pct / 100.0
    if r <= 0 or month <= 0:
        return amount
    return amount / ((1 + r) ** month)


def resolve_fee(value: float | None, is_rate: bool, principal: float) -> float:
    """Tahsis ücreti TL mi yüzde mi — tek tipe indirger."""
    if value is None:
        return 0.0
    return principal * value / 100.0 if is_rate else value


def format_try(value: float) -> str:
    """1234567.89 -> '1.234.567,89 TL'"""
    s = f"{value:,.2f}"
    s = s.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
    return f"{s} TL"


def format_pct(value: float) -> str:
    return f"%{value:.2f}".replace(".", ",")
