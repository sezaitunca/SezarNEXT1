"""
SEZARNEXT Live Decision Journey
===============================
Jüri demosu. Altı aşamalı karar yolculuğu:

    1. Intent        — sorgunun yapılandırılması
    2. Retrieval     — uygun ürünlerin bulunması
    3. Comparison    — çok kriterli karşılaştırma tablosu
    4. Benefit       — net ekonomik maliyet hesabı
    5. SEZAR Agent   — kararın açıklanması
    6. Evidence      — "Nereden biliyorsun?" → kaynak doğrulama

Çalıştırma:
    python -m demo.scenarios.live_decision_journey
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.sezar_agent import SezarAgent  # noqa: E402
from collectors.store import load_campaigns  # noqa: E402
from engine.financial_math import format_pct, format_try  # noqa: E402
from knowledge.evidence import build_card, coverage  # noqa: E402

QUESTION = "500.000 TL taşıt finansmanına ihtiyacım var. 24 ay için en avantajlı seçeneği bul."

W = 78


def stage(no: int, title: str, pause: float = 0.0) -> None:
    print()
    print("═" * W)
    print(f"  AŞAMA {no} — {title}")
    print("═" * W)
    if pause:
        time.sleep(pause)


def banner() -> None:
    print("╔" + "═" * (W - 2) + "╗")
    print("║" + "SEZARNEXT".center(W - 2) + "║")
    print("║" + "AI-Powered Participation Finance Intelligence".center(W - 2) + "║")
    print("╚" + "═" * (W - 2) + "╝")


def run(pause: float = 0.0) -> None:
    banner()
    campaigns = load_campaigns()
    if not campaigns:
        print("Veri yok. Önce çalıştırın: python -m demo.build_demo_data")
        return

    agent = SezarAgent(campaigns)
    st = agent.stats()
    print(f"\n  Aktif Bankalar        {st['banks']:>6}")
    print(f"  Aktif Kayıtlar        {st['campaigns']:>6}")
    print(f"  Finansman Ürünleri    "
          f"{sum(v for k, v in st['by_product'].items() if 'finansman' in k):>6}")
    print(f"  Kart Kampanyaları     {st['by_product'].get('kredi_kartı', 0):>6}")
    print(f"  Ortalama Confidence   {st['avg_confidence']:>6}")
    print(f"  Evidence Coverage     {coverage(campaigns) * 100:>5.1f}%")
    if any(c.is_synthetic for c in campaigns):
        print("\n  [Bu demo SENTETİK veriyle çalışmaktadır — gerçek banka oranları değildir.]")

    print("\n" + "─" * W)
    print(f"  KULLANICI: {QUESTION}")
    print("─" * W)

    response = agent.ask(QUESTION)
    q, result = response.query, response.result

    # ---- 1. Intent ----
    stage(1, "INTENT", pause)
    print(f"  Intent            : {q.intent}")
    print(f"  Amount            : {q.amount:,.0f} TRY".replace(",", "."))
    print(f"  Term              : {q.months} months")
    print(f"  Product           : {q.product_type}")
    print(f"  Priority profile  : {q.priority}")
    print(f"  Router confidence : {q.confidence}")
    hits = q.signals["ontology_hits"] or [
        f"{k} ({v})" for k, v in sorted(q.signals["product_scores"].items(), key=lambda x: -x[1])[:3]
    ]
    print(f"  Ontology signals  : {', '.join(hits)}")

    # ---- 2. Retrieval ----
    stage(2, "RETRIEVAL", pause)
    print(f"  {result.banks_checked} banks checked")
    print(f"  {result.products_found} products in knowledge base")
    print(f"  {result.products_eligible} products eligible for 500.000 TL / 24 ay")

    # ---- 3. Comparison ----
    stage(3, "COMPARISON", pause)
    print(result.pretty_table())

    # ---- 4. Benefit Engine ----
    stage(4, "BENEFIT ENGINE", pause)
    b = result.best
    print("  Net Ekonomik Maliyet dökümü — " + b.bank)
    print()
    print(f"    Kâr payı yükü            {format_try(b.profit_share_cost):>18}")
    print(f"  + Tahsis ücreti            {format_try(b.allocation_fee):>18}")
    print(f"  + Ekspertiz / diğer        "
          f"{format_try(b.expertise_fee + b.insurance_fee + b.other_fees):>18}")
    print(f"  - Nakit iade (BD)          {format_try(b.reward_amount):>18}")
    print(f"  - Para puan (BD)           {format_try(b.shopping_points):>18}")
    print(f"  - İndirim / muafiyet       {format_try(b.discount_gain + b.waiver_gain):>18}")
    print("  " + "─" * 44)
    print(f"  = NET EKONOMİK MALİYET     {format_try(b.net_economic_cost):>18}")
    print(f"    Yıllık maliyet oranı     {format_pct(b.effective_annual_rate):>18}")
    print(f"    Benefit Score            {b.benefit_score:>15.1f}/100")

    # ---- 5. SEZAR Agent ----
    stage(5, "SEZAR AGENT", pause)
    print("  SEZAR:")
    for line in response.text.split("\n"):
        print("  " + line)

    # ---- 6. Evidence ----
    stage(6, "EVIDENCE", pause)
    print("  JÜRİ: Nereden biliyorsun?")
    print()
    print("  SEZAR:")
    for line in build_card(b.campaign, "profit_rate").render().split("\n"):
        print("  " + line)

    # ---- Ek: ödeme planı ----
    print()
    print("═" * W)
    print("  EK — ÖDEME PLANI")
    print("═" * W)
    print(agent.payment_plan(rows=4))

    print()
    print("═" * W)
    print("  SEZARNEXT — Katılım finansını veriden karara dönüştüren")
    print("              açıklanabilir yapay zekâ ajanı.")
    print("═" * W)


if __name__ == "__main__":
    run(pause=float(sys.argv[1]) if len(sys.argv) > 1 else 0.0)
