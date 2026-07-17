from __future__ import annotations

import pytest
from django.db import IntegrityError

from ai_visibility.teams.tests.factories import MembershipFactory
from ai_visibility.teams.tests.factories import TeamFactory

pytestmark = pytest.mark.django_db


def test_team_defaults():
    team = TeamFactory()
    assert team.min_aggregation_size == 5
    assert str(team) == team.name


def test_membership_unique_per_user_team():
    membership = MembershipFactory()
    with pytest.raises(IntegrityError):
        MembershipFactory(user=membership.user, team=membership.team)
