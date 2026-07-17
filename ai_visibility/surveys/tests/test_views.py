from __future__ import annotations

import datetime as dt
from http import HTTPStatus

import pytest
from django.urls import reverse
from django.utils import timezone

from ai_visibility.surveys.services import open_survey_run
from ai_visibility.teams.tests.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def _open_run_with_token():
    membership = MembershipFactory()
    run = open_survey_run(team=membership.team, template_key="dx_core4_quarterly")
    return run.tokens.first()


def test_submit_consumes_token_and_stores_unlinked_response(client):
    token = _open_run_with_token()
    url = reverse("surveys:answer", args=[token.token])
    payload = {f"q_{q.id}": 4 for q in token.run.template.questions.all()}
    resp = client.post(url, payload)
    assert resp.status_code == HTTPStatus.FOUND
    token.refresh_from_db()
    assert token.consumed
    response = token.run.responses.get()
    assert not hasattr(response, "user_id")  # anonymity
    assert response.answers.count() == token.run.template.questions.count()


def test_consumed_token_shows_already_page(client):
    token = _open_run_with_token()
    token.consumed = True
    token.save()
    resp = client.get(reverse("surveys:answer", args=[token.token]))
    assert b"already" in resp.content.lower()


def test_closed_run_rejects_submission(client):
    token = _open_run_with_token()
    run = token.run
    run.closes_at = timezone.now() - dt.timedelta(days=1)
    run.save()
    resp = client.post(reverse("surveys:answer", args=[token.token]), {})
    assert resp.status_code == HTTPStatus.GONE
