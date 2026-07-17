from __future__ import annotations

import factory
from factory.django import DjangoModelFactory

from ai_visibility.teams.models import IntegrationConfig
from ai_visibility.teams.models import Membership
from ai_visibility.teams.models import Team
from ai_visibility.users.tests.factories import UserFactory


class TeamFactory(DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Team {n}")
    slug = factory.Sequence(lambda n: f"team-{n}")

    class Meta:
        model = Team


class MembershipFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    team = factory.SubFactory(TeamFactory)

    class Meta:
        model = Membership


class IntegrationConfigFactory(DjangoModelFactory):
    team = factory.SubFactory(TeamFactory)
    provider = "github"

    class Meta:
        model = IntegrationConfig
