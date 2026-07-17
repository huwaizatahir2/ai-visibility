from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied

from ai_visibility.users.adapters import SocialAccountAdapter
from ai_visibility.users.models import User


class _FakeSocialLogin:
    def __init__(self, email):
        self.user = User(email=email)


def test_rejects_disallowed_domain(settings, rf):
    settings.ALLOWED_OAUTH_DOMAINS = ["arbisoft.com"]
    adapter = SocialAccountAdapter()
    with pytest.raises(PermissionDenied):
        adapter.pre_social_login(rf.get("/"), _FakeSocialLogin("evil@other.com"))


def test_allows_permitted_domain(settings, rf):
    settings.ALLOWED_OAUTH_DOMAINS = ["arbisoft.com"]
    adapter = SocialAccountAdapter()
    # Should not raise.
    adapter.pre_social_login(rf.get("/"), _FakeSocialLogin("dev@arbisoft.com"))


def test_empty_allowlist_permits_anyone(settings, rf):
    settings.ALLOWED_OAUTH_DOMAINS = []
    adapter = SocialAccountAdapter()
    adapter.pre_social_login(rf.get("/"), _FakeSocialLogin("anyone@example.org"))
