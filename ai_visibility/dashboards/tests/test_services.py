from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from ai_visibility.dashboards.services import GroupTooSmallError
from ai_visibility.dashboards.services import metric_series
from ai_visibility.dashboards.services import paired_series
from ai_visibility.metrics.services import capture_baseline
from ai_visibility.metrics.services import upsert_snapshot
from ai_visibility.teams.tests.factories import MembershipFactory
from ai_visibility.teams.tests.factories import TeamFactory

pytestmark = pytest.mark.django_db


def _weekly(team, metric_key, week, value):
    upsert_snapshot(
        team=team,
        metric_key=metric_key,
        period_start=week,
        period_end=week + dt.timedelta(days=6),
        granularity="weekly",
        value=Decimal(value),
    )


def test_series_blocked_below_min_group_size():
    team = TeamFactory(min_aggregation_size=5)
    MembershipFactory.create_batch(3, team=team)
    with pytest.raises(GroupTooSmallError):
        metric_series(team, "pr_throughput")


def test_series_returns_period_value_pairs_with_baseline_delta():
    team = TeamFactory(min_aggregation_size=1)
    MembershipFactory(team=team)
    _weekly(team, "pr_throughput", dt.date(2026, 6, 29), "10")
    _weekly(team, "pr_throughput", dt.date(2026, 7, 6), "12")
    capture_baseline(team)  # baseline captures 12
    _weekly(team, "pr_throughput", dt.date(2026, 7, 13), "15")

    series = metric_series(team, "pr_throughput")
    assert series["points"][-1]["value"] == 15.0
    assert series["baseline"] == 12.0
    assert series["delta_pct"] == 25.0


def test_paired_series_returns_metric_and_counterweight():
    team = TeamFactory(min_aggregation_size=1)
    MembershipFactory(team=team)
    series = paired_series(team, "pr_throughput")
    assert series["metric"]["key"] == "pr_throughput"
    assert series["paired"]["key"] == "pr_revert_rate"
