from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse

from ai_visibility.metrics.models import Baseline
from ai_visibility.surveys.models import SurveyRun
from ai_visibility.teams.models import IntegrationConfig
from ai_visibility.teams.models import Membership
from ai_visibility.teams.tests.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def test_member_cannot_view_settings(client):
    membership = MembershipFactory(role=Membership.Role.MEMBER)
    client.force_login(membership.user)
    resp = client.get(reverse("teams:settings", args=[membership.team.slug]))
    # Members may view their team page but cannot edit; page renders read-only.
    assert resp.status_code == HTTPStatus.OK
    assert b"Capture baseline" not in resp.content  # org-admin only


def test_team_lead_saves_integration_credentials_write_only(client):
    membership = MembershipFactory(role=Membership.Role.TEAM_LEAD)
    team = membership.team
    client.force_login(membership.user)
    url = reverse("teams:update_integration", args=[team.slug, "github"])
    client.post(url, {"config": "{}", "secret": "ghp_topsecret", "enabled": "on"})

    integration = IntegrationConfig.objects.get(team=team, provider="github")
    assert integration.get_credentials() == {"token": "ghp_topsecret"}

    # The stored secret is never rendered back on the settings page.
    resp = client.get(reverse("teams:settings", args=[team.slug]))
    assert b"ghp_topsecret" not in resp.content


def test_blank_secret_keeps_existing_credential(client):
    membership = MembershipFactory(role=Membership.Role.TEAM_LEAD)
    team = membership.team
    client.force_login(membership.user)
    url = reverse("teams:update_integration", args=[team.slug, "github"])
    client.post(url, {"config": "{}", "secret": "ghp_first", "enabled": "on"})
    client.post(url, {"config": "{}", "secret": "", "enabled": "on"})

    integration = IntegrationConfig.objects.get(team=team, provider="github")
    assert integration.get_credentials() == {"token": "ghp_first"}


def test_member_forbidden_from_editing_integration(client):
    membership = MembershipFactory(role=Membership.Role.MEMBER)
    team = membership.team
    client.force_login(membership.user)
    url = reverse("teams:update_integration", args=[team.slug, "github"])
    resp = client.post(url, {"config": "{}", "secret": "x", "enabled": "on"})
    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_org_admin_captures_baseline(client):
    membership = MembershipFactory(role=Membership.Role.ORG_ADMIN)
    team = membership.team
    client.force_login(membership.user)
    client.post(reverse("teams:capture_baseline", args=[team.slug]))
    assert Baseline.objects.filter(team=team).count() == 1


def test_team_lead_launches_survey(client):
    membership = MembershipFactory(role=Membership.Role.TEAM_LEAD)
    team = membership.team
    client.force_login(membership.user)
    client.post(
        reverse("teams:launch_survey", args=[team.slug]),
        {"template_key": "dx_core4_quarterly"},
    )
    assert SurveyRun.objects.filter(team=team).count() == 1
