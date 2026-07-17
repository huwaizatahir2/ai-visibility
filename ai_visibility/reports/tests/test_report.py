from __future__ import annotations

import datetime as dt
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse

from ai_visibility.metrics.services import upsert_snapshot
from ai_visibility.teams.models import Membership
from ai_visibility.teams.tests.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def _report_url(team):
    return reverse("reports:monthly", args=[team.slug])


def _seed(team, metric_key, value):
    upsert_snapshot(
        team=team,
        metric_key=metric_key,
        period_start=dt.date(2026, 7, 6),
        period_end=dt.date(2026, 7, 12),
        granularity="weekly",
        value=Decimal(value),
    )


def test_member_cannot_view_report(client):
    membership = MembershipFactory(role=Membership.Role.MEMBER)
    client.force_login(membership.user)
    resp = client.get(_report_url(membership.team))
    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_team_lead_sees_report_with_roi_and_guardrails(client):
    membership = MembershipFactory(role=Membership.Role.TEAM_LEAD)
    team = membership.team
    team.min_aggregation_size = 1
    team.save()
    _seed(team, "pr_throughput", "12")
    _seed(team, "pr_revert_rate", "3")
    _seed(team, "hours_saved_week", "3")
    _seed(team, "cc_cost_usd", "100")

    client.force_login(membership.user)
    resp = client.get(_report_url(team))
    assert resp.status_code == HTTPStatus.OK
    assert b"ROI" in resp.content
    assert b"PR throughput" in resp.content
    assert b"PR revert rate" in resp.content
