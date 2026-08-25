import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from engine.financial_math import (build_payment_plan, effective_annual_cost_rate,
                                   format_try, monthly_installment)


class TestInstallment:
    def test_known_value(self):
        # 100.000 TL, aylık %2, 12 ay → yaklaşık 9.455,96 TL
        assert monthly_installment(100_000, 2.0, 12) == pytest.approx(9455.96, abs=0.5)

    def test_zero_rate(self):
        assert monthly_installment(120_000, 0.0, 12) == 10_000.0

    def test_invalid_term(self):
        with pytest.raises(ValueError):
            monthly_installment(100_000, 2.0, 0)


class TestPlan:
    def test_schedule_closes_to_zero(self):
        plan = build_payment_plan(500_000, 1.89, 24, with_schedule=True)
        assert len(plan.schedule) == 24
        assert plan.schedule[-1]["remaining"] == pytest.approx(0.0, abs=1.0)

    def test_total_consistency(self):
        plan = build_payment_plan(500_000, 1.89, 24)
        assert plan.total_payment == pytest.approx(plan.principal + plan.total_profit_share)


class TestEffectiveRate:
    def test_fees_increase_cost(self):
        base = effective_annual_cost_rate(500_000, 2.0, 24)
        with_fee = effective_annual_cost_rate(500_000, 2.0, 24, upfront_fees=10_000)
        assert with_fee > base


def test_format_try():
    assert format_try(1234567.89) == "1.234.567,89 TL"
