import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from nlp.entity_extractor import extract_entities


def fields(text):
    return extract_entities(text)["fields"]


class TestProfitRate:
    def test_monthly(self):
        assert fields("aylık %1,89 kâr payı oranıyla")["profit_rate"] == 1.89

    def test_yuzde_variant(self):
        assert fields("aylık yüzde 1,79 kâr payı")["profit_rate"] == 1.79

    def test_zero_rate(self):
        assert fields("%0 kâr payı ile 12 ay vade")["profit_rate"] == 0.0

    def test_annual_not_converted(self):
        """Yıllık oran aylığa BÖLÜNMEZ; türetilmiş sayı kanıtsızdır."""
        f = fields("32 gün vadeli hesapta yıllık %45 kâr payı")
        assert f.get("profit_rate") is None
        assert f["annual_cost_rate"] == 45.0


class TestAmounts:
    def test_kadar(self):
        assert fields("750.000 TL'ye kadar finansman")["financing_amount_max"] == 750000.0

    def test_range(self):
        f = fields("Finansman tutarı 300.000 TL ila 1.200.000 TL arasındadır.")
        assert f["financing_amount_min"] == 300000.0
        assert f["financing_amount_max"] == 1200000.0

    def test_reward_not_treated_as_limit(self):
        """Ödül tutarı finansman limiti sanılmamalıdır."""
        f = fields("Çekilişle 250.000 TL ödül. En az 25.000 TL bakiye gereklidir.")
        assert f.get("financing_amount_max") is None


class TestFees:
    def test_amount_fee(self):
        """'7.500 TL' içindeki '0 TL' muafiyet sanılmamalıdır (regresyon)."""
        f = fields("Tahsis ücreti 7.500 TL'dir.")
        assert f["allocation_fee"] == 7500.0

    def test_waiver(self):
        assert fields("Tahsis ücreti alınmaz.")["allocation_fee"] == 0.0

    def test_rate_fee(self):
        f = fields("Tahsis ücreti %0,5 oranındadır.")
        assert f["allocation_fee"] == 0.5 and f["allocation_fee_is_rate"] is True

    def test_field_isolation(self):
        """Bir alanın muafiyeti diğerini sıfırlamaz."""
        f = fields("Tahsis ücreti 7.500 TL'dir. Ekspertiz ücreti alınmaz.")
        assert f["allocation_fee"] == 7500.0 and f["expertise_fee"] == 0.0


class TestEvidence:
    def test_every_field_has_evidence(self):
        res = extract_entities("750.000 TL'ye kadar 36 ay vadeli aylık %1,89 kâr payı")
        ev = {e.field_name for e in res["evidence"]}
        for f in ("profit_rate", "financing_amount_max", "maturity_months"):
            assert f in ev, f"{f} kanıtsız"

    def test_empty_text(self):
        assert extract_entities("")["fields"] == {}
