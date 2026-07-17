from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from ai_visibility.metrics.services import capture_baseline
from ai_visibility.metrics.services import upsert_snapshot
from ai_visibility.teams.tests.factories import TeamFactory

pytestmark = pytest.mark.django_db


def test_capture_freezes_latest_value_per_metric_and_versions():
    team = TeamFactory()
    for week, val in ((dt.date(2026, 6, 29), "10"), (dt.date(2026, 7, 6), "12")):
        upsert_snapshot(
            team=team,
            metric_key="pr_throughput",
            period_start=week,
            period_end=week + dt.timedelta(days=6),
            granularity="weekly",
            value=Decimal(val),
        )
    b1 = capture_baseline(team)
    assert b1.values["pr_throughput"] == "12.0000"
    b2 = capture_baseline(team)
    assert b2.version == b1.version + 1  # old baseline kept, immutable
