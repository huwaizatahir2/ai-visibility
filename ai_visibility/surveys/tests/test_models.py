from __future__ import annotations

import pytest

from ai_visibility.surveys.models import Question
from ai_visibility.surveys.models import Response
from ai_visibility.surveys.models import SurveyTemplate

pytestmark = pytest.mark.django_db

DX_CORE4_QUESTIONS = 6
DXI_LITE_DRIVERS = 14


def test_dx_core4_template_seeded_with_metric_keys():
    template = SurveyTemplate.objects.get(key="dx_core4_quarterly")
    questions = template.questions.all()
    assert questions.count() == DX_CORE4_QUESTIONS
    assert all(q.metric_key for q in questions)


def test_dxi_lite_has_fourteen_likert_drivers():
    template = SurveyTemplate.objects.get(key="dxi_lite")
    assert template.questions.count() == DXI_LITE_DRIVERS
    assert all(q.qtype == Question.QType.LIKERT for q in template.questions.all())


def test_response_is_anonymous_by_construction():
    # Schema-level guarantee: a response cannot be linked back to a user.
    assert not hasattr(Response, "user")
    field_names = {f.name for f in Response._meta.get_fields()}
    assert "user" not in field_names
    assert "token" not in field_names
