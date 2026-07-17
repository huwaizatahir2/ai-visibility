from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_healthz_ok(client):
    resp = client.get(reverse("healthz"))
    assert resp.status_code == HTTPStatus.OK
    assert resp.json() == {"status": "ok", "db": True}
