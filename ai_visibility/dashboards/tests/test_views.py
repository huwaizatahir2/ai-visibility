from __future__ import annotations

import datetime as dt
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse

from ai_visibility.metrics.services import upsert_snapshot
from ai_visibility.teams.tests.factories import MembershipFactory
from ai_visibility.teams.tests.factories import TeamFactory

pytestmark = pytest.mark.django_db


def _overview_url(team):
    return reverse("dashboards:overview", args=[team.slug])


def test_login_required(client):
    team = TeamFactory()
    resp = client.get(_overview_url(team))
    assert resp.status_code == HTTPStatus.FOUND  # redirect to login


def test_non_member_is_forbidden(client):
    membership = MembershipFactory()  # member of their own team
    other_team = TeamFactory()
    client.force_login(membership.user)
    resp = client.get(_overview_url(other_team))
    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_small_team_shows_guardrail_not_numbers(client):
    team = TeamFactory(min_aggregation_size=5)
    membership = MembershipFactory(team=team)
    upsert_snapshot(
        team=team,
        metric_key="pr_throughput",
        period_start=dt.date(2026, 7, 6),
        period_end=dt.date(2026, 7, 12),
        granularity="weekly",
        value=Decimal("999"),
    )
    client.force_login(membership.user)
    resp = client.get(_overview_url(team))
    assert resp.status_code == HTTPStatus.OK
    assert b"Group too small" in resp.content
    assert b"999" not in resp.content  # no numbers leak below threshold


def test_overview_renders_headline_metric(client):
    team = TeamFactory(min_aggregation_size=1)
    membership = MembershipFactory(team=team)
    client.force_login(membership.user)
    resp = client.get(_overview_url(team))
    assert resp.status_code == HTTPStatus.OK
    assert b"PR throughput" in resp.content


def test_impact_pairs_speed_with_quality(client):
    team = TeamFactory(min_aggregation_size=1)
    membership = MembershipFactory(team=team)
    client.force_login(membership.user)
    resp = client.get(reverse("dashboards:impact", args=[team.slug]))
    assert resp.status_code == HTTPStatus.OK
    # PR throughput (speed) shown beside its quality counterweight, revert rate.
    assert b"PR throughput" in resp.content
    assert b"PR revert rate" in resp.content
