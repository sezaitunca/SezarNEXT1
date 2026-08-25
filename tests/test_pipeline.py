import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from nlp.pipeline import inspect, run_pipeline

TEXT = ("750.000 TL'ye kadar 36 ay vadeli, aylık %2,05 kâr payı oranıyla taşıt "
        "finansmanı fırsatı. Tahsis ücreti alınmaz.")


class TestPipeline:
    def test_end_to_end(self):
        res = run_pipeline(TEXT, bank="X Katılım", source_url="https://x.local")
        c = res.campaign
        assert c is not None and res.is_valid
        assert c.profit_rate == 2.05
        assert c.financing_amount_max == 750000.0
        assert c.maturity_months == 36
        assert c.product_type.value == "taşıt_finansmanı"
        assert c.confidence_score > 0.7

    def test_evidence_attached(self):
        c = run_pipeline(TEXT, "X", "https://x.local").campaign
        assert {e.field_name for e in c.evidence_items} >= {"profit_rate", "maturity_months"}

    def test_inspector_stages(self):
        out = inspect(TEXT)
        for key in ("1_original_text", "5_detected_entities", "7_validation", "8_evidence"):
            assert key in out

    def test_garbage_input_is_safe(self):
        res = run_pipeline("...", bank="X", source_url="https://x.local")
        assert res.campaign is None or res.campaign.profit_rate is None
