from __future__ import annotations

import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    min_aggregation_size = models.PositiveSmallIntegerField(default=5)
    loaded_hourly_cost_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=40,
    )
    timezone = models.CharField(max_length=64, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        ORG_ADMIN = "org_admin", "Org admin"
        TEAM_LEAD = "team_lead", "Team lead"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "team"], name="uniq_membership"),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.team} ({self.role})"


class IntegrationConfig(models.Model):
    class Provider(models.TextChoices):
        GITHUB = "github", "GitHub"
        NEWRELIC = "newrelic", "New Relic"
        SONARQUBE = "sonarqube", "SonarQube"
        JIRA = "jira", "Jira"
        ANTHROPIC = "anthropic", "Anthropic"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="integrations",
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    enabled = models.BooleanField(default=True)
    # Non-secret provider config: repo lists, account ids, project keys.
    config = models.JSONField(default=dict, blank=True)
    # Fernet-encrypted JSON credentials; never store or display in plaintext.
    _credentials = models.TextField(blank=True, default="", db_column="credentials")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "provider"],
                name="uniq_team_provider",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.team} · {self.get_provider_display()}"

    @staticmethod
    def _fernet() -> Fernet:
        return Fernet(settings.FIELD_ENCRYPTION_KEY)

    def set_credentials(self, data: dict) -> None:
        payload = json.dumps(data).encode()
        self._credentials = self._fernet().encrypt(payload).decode()

    def get_credentials(self) -> dict:
        if not self._credentials:
            return {}
        return json.loads(self._fernet().decrypt(self._credentials.encode()))
