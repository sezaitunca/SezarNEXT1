"""
SEZAR Agent — Response Generator
================================
Karşılaştırma sonucunu, dokümandaki SEZAR cevap biçimine göre metne dönüştürür.

Şablon tabanlıdır: her sayı motordan gelir, hiçbir sayı üretilmez.
Bu yapı hallucination oranını mimari olarak sıfıra yaklaştırır.
"""

from __future__ import annotations

from engine.comparison_engine import ComparisonResult
from engine.financial_math import format_pct, format_try
from knowledge.evidence import build_card
from schemas.campaign_schema import SezarNextCampaign


def render_answer(result: ComparisonResult, priority_label: str = "net ekonomik maliyet") -> str:
    best = result.best
    if best is None:
        return (
            "Belirttiğiniz tutar ve vade için uygun bir katılım finansmanı ürünü bulunamadı.\n"
            f"Kontrol edilen banka sayısı: {result.banks_checked}\n"
            "Tutarı veya vadeyi değiştirerek tekrar deneyebilirsiniz."
        )

    c = best.campaign
    lines: list[str] = []
    lines.append("En avantajlı seçenek:")
    lines.append(f"{best.bank} — {best.product_name}")
    lines.append("")
    lines.append("Karşılaştırmalı sonuç:")
    lines.append("")
    rows = [
        ("Kâr payı", format_pct(best.profit_rate)),
        ("Vade", f"{best.months} ay"),
        ("Aylık taksit", format_try(best.monthly_payment)),
        ("Toplam geri ödeme", format_try(best.total_payment)),
        ("Masraflar", format_try(best.total_fees) if best.total_fees else "Yok"),
        ("Kampanya avantajı", format_try(best.total_gains) if best.total_gains else "Yok"),
        ("Net ekonomik maliyet", format_try(best.net_economic_cost)),
        ("Yıllık maliyet oranı", format_pct(best.effective_annual_rate)),
    ]
    if best.advantage_vs_median > 0:
        rows.append(("Medyana karşı avantaj", "+" + format_try(best.advantage_vs_median)))
    rows.append(("Benefit Score", f"{best.benefit_score:.1f} / 100"))

    for label, value in rows:
        lines.append(f"  {label:<24}{value}")

    lines.append("")
    lines.append("Neden?")
    for i, reason in enumerate(best.reasons, 1):
        lines.append(f"  {i}. {reason}")

    lines.append("")
    lines.append("Karşılaştırılan:")
    lines.append(f"  {result.banks_checked} banka")
    lines.append(f"  {result.products_eligible} uygun finansman ürünü "
                 f"({result.products_found} ürün tarandı)")

    if c is not None:
        lines.append("")
        lines.append("Kaynak:")
        lines.append(f"  {c.bank}")
        lines.append(f"  {c.source_url}")
        lines.append(f"  Son güncelleme: {c.scraped_at.strftime('%d.%m.%Y')}")
        lines.append(f"  Confidence: {c.confidence_score:.2f}")
        if c.is_synthetic:
            lines.append("  [DEMO VERİSİ — gerçek banka verisi değildir]")
    return "\n".join(lines)


def render_alternatives(result: ComparisonResult, limit: int = 4) -> str:
    if len(result.breakdowns) < 2:
        return ""
    lines = ["Diğer seçenekler:", ""]
    for i, b in enumerate(result.breakdowns[1:limit + 1], 2):
        diff = b.net_economic_cost - result.breakdowns[0].net_economic_cost
        lines.append(
            f"  {i}. {b.bank:<22}{format_pct(b.profit_rate):>8}   "
            f"net maliyet {format_try(b.net_economic_cost):>16}   "
            f"(+{format_try(diff)})"
        )
    return "\n".join(lines)


def render_evidence(campaign: SezarNextCampaign, field_name: str = "profit_rate") -> str:
    return build_card(campaign, field_name).render()


def render_payment_plan(result: ComparisonResult, rows: int = 6) -> str:
    from engine.financial_math import build_payment_plan

    best = result.best
    if best is None:
        return "Plan üretilecek uygun teklif yok."
    plan = build_payment_plan(best.principal, best.profit_rate, best.months, with_schedule=True)
    lines = [
        f"{best.bank} — ödeme planı ({best.months} ay, {format_pct(best.profit_rate)})",
        "",
        f"{'Taksit':<8}{'Ödeme':>16}{'Kâr Payı':>16}{'Anapara':>16}{'Kalan':>18}",
        "-" * 74,
    ]
    for row in plan.schedule[:rows]:
        lines.append(
            f"{row['installment_no']:<8}{format_try(row['payment']):>16}"
            f"{format_try(row['profit_share']):>16}{format_try(row['capital']):>16}"
            f"{format_try(row['remaining']):>18}"
        )
    if len(plan.schedule) > rows:
        lines.append(f"... ({len(plan.schedule) - rows} taksit daha)")
    lines.append("-" * 74)
    lines.append(f"{'TOPLAM':<8}{format_try(plan.total_payment):>16}"
                 f"{format_try(plan.total_profit_share):>16}")
    return "\n".join(lines)


def render_clarification(missing: list[str]) -> str:
    prompts = {
        "amount": "finansman tutarı (örn. 500.000 TL)",
        "months": "vade (örn. 24 ay)",
        "product_type": "ürün türü (örn. taşıt finansmanı)",
    }
    items = [prompts.get(m, m) for m in missing]
    return (
        "Karşılaştırma yapabilmem için şu bilgi(ler) gerekiyor: "
        + ", ".join(items)
        + ".\nÖrnek: \"500.000 TL için 24 ay vadeli en avantajlı taşıt finansmanını bul.\""
    )
