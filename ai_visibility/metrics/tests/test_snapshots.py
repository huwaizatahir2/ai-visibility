from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from ai_visibility.metrics.models import MetricSnapshot
from ai_visibility.metrics.services import upsert_snapshot
from ai_visibility.teams.tests.factories import TeamFactory

pytestmark = pytest.mark.django_db
WEEK = (dt.date(2026, 7, 6), dt.date(2026, 7, 12))


def test_upsert_is_idempotent_per_period_and_dimensions():
    team = TeamFactory()
    upsert_snapshot(
        team=team,
        metric_key="pr_throughput",
        period_start=WEEK[0],
        period_end=WEEK[1],
        granularity="weekly",
        value=Decimal("12"),
    )
    upsert_snapshot(
        team=team,
        metric_key="pr_throughput",
        period_start=WEEK[0],
        period_end=WEEK[1],
        granularity="weekly",
        value=Decimal("14"),
    )
    snaps = MetricSnapshot.objects.filter(team=team)
    assert snaps.count() == 1
    assert snaps.get().value == Decimal("14")


def test_different_dimensions_create_separate_rows():
    team = TeamFactory()
    for repo in ("a", "b"):
        upsert_snapshot(
            team=team,
            metric_key="pr_throughput",
            period_start=WEEK[0],
            period_end=WEEK[1],
            granularity="weekly",
            value=Decimal("1"),
            dimensions={"repo": repo},
        )
    assert MetricSnapshot.objects.filter(team=team).count() == 2
