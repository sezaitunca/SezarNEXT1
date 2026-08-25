import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime

from engine.benefit_engine import compute_cost, evaluate
from schemas.campaign_schema import ProductType, SezarNextCampaign


def make(bank, rate, fee=0.0, reward=0.0, waiver=False):
    return SezarNextCampaign(
        bank=bank, source_url="https://x.local", product_name=f"{bank} taşıt",
        product_type=ProductType.TASIT_FINANSMANI, profit_rate=rate,
        financing_amount_max=1_000_000, maturity_months=36,
        allocation_fee=fee, reward_amount=reward, fee_waiver=waiver,
        scraped_at=datetime(2026, 8, 25), is_synthetic=True,
    )


class TestBenefit:
    def test_lower_rate_lower_cost_all_else_equal(self):
        a = compute_cost(make("A", 1.80), 500_000, 24)
        b = compute_cost(make("B", 2.00), 500_000, 24)
        assert a.net_economic_cost < b.net_economic_cost

    def test_campaign_can_beat_lower_rate(self):
        """Benefit Engine'in varlık nedeni: yüksek oran + büyük kazanç kazanabilir."""
        cheap_rate = make("DüşükOran", 1.80)
        rich_campaign = make("YüksekKazanç", 1.90, reward=30_000)
        res = evaluate([cheap_rate, rich_campaign], 500_000, 24)
        winner = min(res, key=lambda b: b.net_economic_cost)
        assert winner.bank == "YüksekKazanç"

    def test_fees_counted(self):
        no_fee = compute_cost(make("A", 1.90), 500_000, 24)
        fee = compute_cost(make("B", 1.90, fee=15_000), 500_000, 24)
        assert fee.net_economic_cost - no_fee.net_economic_cost == 15_000

    def test_scores_bounded(self):
        res = evaluate([make("A", 1.8), make("B", 2.1), make("C", 2.4)], 500_000, 24)
        assert max(b.benefit_score for b in res) == 100.0
        assert min(b.benefit_score for b in res) == 0.0

    def test_reasons_generated(self):
        res = evaluate([make("A", 1.8), make("B", 2.1)], 500_000, 24)
        assert all(b.reasons for b in res)
