from __future__ import annotations

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
