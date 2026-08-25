import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime

from agent.query_router import route
from agent.sezar_agent import SezarAgent
from schemas.campaign_schema import ProductType, SezarNextCampaign


def sample():
    return [
        SezarNextCampaign(
            bank=f"{c} Katılım", source_url="https://x.local", product_name="Taşıt Finansmanı",
            product_type=ProductType.TASIT_FINANSMANI, profit_rate=r,
            financing_amount_max=1_000_000, maturity_months=36,
            evidence_text=f"aylık %{r} kâr payı", confidence_score=0.9,
            scraped_at=datetime(2026, 8, 25), is_synthetic=True,
        )
        for c, r in [("A", 1.89), ("B", 2.05), ("C", 1.95)]
    ]


class TestRouter:
    def test_parses_amount_and_term(self):
        q = route("500.000 TL için 24 ay vadeli en avantajlı taşıt finansmanını bul")
        assert q.amount == 500_000 and q.months == 24
        assert q.product_type == "taşıt_finansmanı"
        assert q.intent == "COMPARE_FINANCING"

    def test_scaled_amount(self):
        assert route("750 bin TL 36 ay konut").amount == 750_000

    def test_evidence_intent(self):
        assert route("nereden biliyorsun?").intent == "EXPLAIN_EVIDENCE"

    def test_priority_profile(self):
        assert route("aylık taksiti en düşük olan hangisi?").priority == "cash_flow"


class TestAgent:
    def test_answers_comparison(self):
        a = SezarAgent(sample())
        r = a.ask("500.000 TL 24 ay taşıt finansmanı en avantajlı hangisi?")
        assert "A Katılım" in r.text
        assert r.result.products_eligible == 3

    def test_asks_for_missing_info(self):
        r = SezarAgent(sample()).ask("taşıt finansmanı istiyorum")
        assert "gerekiyor" in r.text

    def test_evidence_after_comparison(self):
        a = SezarAgent(sample())
        a.ask("500.000 TL 24 ay taşıt finansmanı")
        r = a.ask("nereden biliyorsun?")
        assert "Kaynak doğrulandı" in r.text

    def test_no_answer_without_data(self):
        r = SezarAgent([]).ask("500.000 TL 24 ay taşıt finansmanı")
        assert "bulunamadı" in r.text
