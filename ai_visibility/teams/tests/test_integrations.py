from __future__ import annotations

import pytest

from ai_visibility.teams.tests.factories import IntegrationConfigFactory

pytestmark = pytest.mark.django_db


def test_credentials_roundtrip_and_encrypted_at_rest():
    ic = IntegrationConfigFactory(provider="github")
    ic.set_credentials({"token": "ghp_secret"})
    ic.save()
    ic.refresh_from_db()
    assert ic.get_credentials() == {"token": "ghp_secret"}
    assert "ghp_secret" not in ic._credentials  # ciphertext only


def test_empty_credentials_returns_empty_dict():
    ic = IntegrationConfigFactory(provider="sonarqube")
    assert ic.get_credentials() == {}
