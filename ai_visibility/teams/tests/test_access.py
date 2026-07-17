from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied

from ai_visibility.teams.access import require_role
from ai_visibility.teams.access import require_team_member
from ai_visibility.teams.access import teams_for
from ai_visibility.teams.models import Membership
from ai_visibility.teams.tests.factories import MembershipFactory
from ai_visibility.teams.tests.factories import TeamFactory

pytestmark = pytest.mark.django_db


def test_teams_for_returns_only_member_teams():
    membership = MembershipFactory()
    TeamFactory()  # unrelated team
    assert list(teams_for(membership.user)) == [membership.team]


def test_require_team_member_denies_outsider():
    membership = MembershipFactory()
    outsider = MembershipFactory().user
    with pytest.raises(PermissionDenied):
        require_team_member(outsider, membership.team)


def test_require_role_enforces_role():
    membership = MembershipFactory(role=Membership.Role.MEMBER)
    with pytest.raises(PermissionDenied):
        require_role(membership.user, membership.team, Membership.Role.ORG_ADMIN)
    # allowed role passes
    assert (
        require_role(membership.user, membership.team, Membership.Role.MEMBER)
        == membership
    )
