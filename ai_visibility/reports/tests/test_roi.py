from __future__ import annotations

from decimal import Decimal

from ai_visibility.reports.roi import compute_roi


def test_worked_example_from_measurement_plan():
    result = compute_roi(
        devs=10,
        hours_saved_per_dev_week=Decimal("3.0"),
        loaded_hourly_cost=Decimal("40"),
        monthly_spend=Decimal("1000"),
    )
    assert result.monthly_value == Decimal("5160.00")  # 3 x 10 x 4.3 x 40
    assert result.net_gain == Decimal("4160.00")
    assert result.roi_multiple == Decimal("5.16")


def test_zero_spend_has_no_multiple():
    result = compute_roi(
        devs=1,
        hours_saved_per_dev_week=Decimal("1"),
        loaded_hourly_cost=Decimal("40"),
        monthly_spend=Decimal("0"),
    )
    assert result.roi_multiple is None
