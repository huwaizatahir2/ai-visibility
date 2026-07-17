from __future__ import annotations

import datetime as dt

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from ai_visibility.surveys.models import SurveyRun
from ai_visibility.surveys.models import SurveyTemplate
from ai_visibility.teams.tests.factories import TeamFactory


class SurveyRunFactory(DjangoModelFactory):
    template = factory.LazyFunction(
        lambda: SurveyTemplate.objects.get(key="dx_core4_quarterly"),
    )
    team = factory.SubFactory(TeamFactory)
    opens_at = factory.LazyFunction(timezone.now)
    closes_at = factory.LazyFunction(lambda: timezone.now() + dt.timedelta(days=7))

    class Meta:
        model = SurveyRun
