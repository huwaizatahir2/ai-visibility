from __future__ import annotations

import dataclasses
from decimal import Decimal

WEEKS_PER_MONTH = Decimal("4.3")
CENTS = Decimal("0.01")


@dataclasses.dataclass(frozen=True)
class RoiResult:
    monthly_value: Decimal
    net_gain: Decimal
    roi_multiple: Decimal | None


def compute_roi(
    *,
    devs: int,
    hours_saved_per_dev_week: Decimal,
    loaded_hourly_cost: Decimal,
    monthly_spend: Decimal,
) -> RoiResult:
    """Monthly value of time saved, net gain, and ROI multiple (measurement plan §7)."""
    monthly_value = (
        hours_saved_per_dev_week * devs * WEEKS_PER_MONTH * loaded_hourly_cost
    ).quantize(CENTS)
    net_gain = (monthly_value - monthly_spend).quantize(CENTS)
    multiple = (
        (monthly_value / monthly_spend).quantize(CENTS) if monthly_spend else None
    )
    return RoiResult(
        monthly_value=monthly_value, net_gain=net_gain, roi_multiple=multiple
    )
