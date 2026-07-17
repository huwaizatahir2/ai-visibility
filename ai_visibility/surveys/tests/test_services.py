from __future__ import annotations

from decimal import Decimal

import pytest
from django.core import mail

from ai_visibility.surveys.models import SurveyToken
from ai_visibility.surveys.services import open_survey_run
from ai_visibility.surveys.services import response_rate
from ai_visibility.teams.tests.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def test_open_survey_run_issues_one_token_per_member_and_emails():
    membership = MembershipFactory()
    MembershipFactory(team=membership.team)
    run = open_survey_run(team=membership.team, template_key="dx_core4_quarterly")
    assert SurveyToken.objects.filter(run=run).count() == 2
    assert len(mail.outbox) == 2
    assert str(SurveyToken.objects.first().token) in mail.outbox[0].body


def test_response_rate_reflects_consumed_tokens():
    membership = MembershipFactory()
    MembershipFactory(team=membership.team)
    run = open_survey_run(team=membership.team, template_key="dx_core4_quarterly")
    token = run.tokens.first()
    token.consumed = True
    token.save()
    assert response_rate(run) == Decimal("50.00")
