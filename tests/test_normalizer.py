import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from nlp.normalizer import (normalize_amount, normalize_maturity, normalize_rate,
                            normalize_text, parse_number, parse_word_number)


class TestParseNumber:
    def test_thousand_separator(self):
        assert parse_number("750.000") == 750000.0
        assert parse_number("1.250.000") == 1250000.0

    def test_decimal_comma(self):
        assert parse_number("2,05") == 2.05

    def test_mixed(self):
        assert parse_number("1.250.000,50") == 1250000.5

    def test_decimal_dot(self):
        assert parse_number("3.19") == 3.19

    def test_invalid(self):
        assert parse_number("abc") is None
        assert parse_number("") is None


class TestAmounts:
    def test_plain(self):
        assert normalize_amount("750.000 TL") == 750000.0

    def test_scaled(self):
        assert normalize_amount("750 bin TL") == 750000.0
        assert normalize_amount("1,5 milyon TL") == 1500000.0

    def test_words(self):
        assert parse_word_number("beş yüz bin") == 500000.0
        assert parse_word_number("İki yüz bin") == 200000.0  # Türkçe 'İ' regresyon testi


class TestRates:
    def test_percent(self):
        assert normalize_rate("%2,05") == 2.05

    def test_yuzde(self):
        assert normalize_rate("yüzde 1,89") == 1.89

    def test_none(self):
        assert normalize_rate("kâr payı oranı belirtilmemiştir") is None


class TestMaturity:
    def test_months(self):
        assert normalize_maturity("36 ay") == 36

    def test_years(self):
        assert normalize_maturity("3 yıl") == 36


class TestNormalizeText:
    def test_pipeline(self):
        out = normalize_text("yüzde 2,05 ile 750 bin TL, 3 yıl vade")
        assert "%2,05" in out and "750000" in out and "36 ay" in out
