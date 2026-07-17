from __future__ import annotations

from decimal import Decimal

import pytest

from ai_visibility.metrics.models import MetricSnapshot
from ai_visibility.surveys.models import Answer
from ai_visibility.surveys.models import Response
from ai_visibility.surveys.models import SurveyRun
from ai_visibility.surveys.services import close_survey_run
from ai_visibility.surveys.services import open_survey_run
from ai_visibility.teams.tests.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def test_close_aggregates_numeric_answers_into_snapshots():
    membership = MembershipFactory()
    run = open_survey_run(team=membership.team, template_key="dx_core4_quarterly")
    question = run.template.questions.get(metric_key="hours_saved_week")
    for val in (2, 4):
        response = Response.objects.create(run=run)
        Answer.objects.create(response=response, question=question, value=Decimal(val))

    close_survey_run(run)

    snap = MetricSnapshot.objects.get(
        team=membership.team, metric__key="hours_saved_week"
    )
    assert snap.value == Decimal("3")  # mean of 2 and 4
    assert snap.source == MetricSnapshot.Source.SURVEY
    run.refresh_from_db()
    assert run.status == SurveyRun.Status.CLOSED


def test_close_dxi_lite_aggregates_overall_mean():
    membership = MembershipFactory()
    run = open_survey_run(team=membership.team, template_key="dxi_lite")
    response = Response.objects.create(run=run)
    for question in run.template.questions.all():
        Answer.objects.create(response=response, question=question, value=Decimal(4))

    close_survey_run(run)

    snap = MetricSnapshot.objects.get(team=membership.team, metric__key="dxi_lite")
    assert snap.value == Decimal("4")
