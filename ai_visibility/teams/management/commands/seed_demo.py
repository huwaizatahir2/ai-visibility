"""Seed a realistic demo team so every dashboard renders with real data.

Run: python manage.py seed_demo
Idempotent — it wipes and recreates the demo team + users each time.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ai_visibility.collectors.models import CollectorRun
from ai_visibility.metrics.services import capture_baseline
from ai_visibility.metrics.services import upsert_snapshot
from ai_visibility.surveys.models import SurveyRun
from ai_visibility.surveys.models import SurveyTemplate
from ai_visibility.surveys.models import SurveyToken
from ai_visibility.teams.models import IntegrationConfig
from ai_visibility.teams.models import Membership
from ai_visibility.teams.models import Team

User = get_user_model()

DEMO_PASSWORD = "DevEx-2026-demo"  # noqa: S105 (local demo only)
TEAM_SLUG = "xiangqi"
WEEKS = 12
BASELINE_AFTER_WEEK = 4  # capture baseline once the first weeks exist

# System metrics: (key, start_value, end_value) linearly ramped across weeks.
WEEKLY = [
    ("cc_wau_pct", 22, 78),
    ("cc_dau_pct", 8, 46),
    ("pct_ai_assisted_prs", 11, 63),
    ("cc_accept_rate", 41, 69),
    ("cc_sessions", 30, 122),
    ("cc_active_hours", 16, 58),
    ("cc_lines_of_code", 820, 5200),
    ("cc_cost_usd", 42, 205),
    ("pr_throughput", 9, 15),
    ("pr_cycle_time_hours", 41, 22),
    ("pr_revert_rate", 6.1, 3.2),
    ("lead_time_hours", 60, 34),
    ("change_failure_rate", 14, 8),
    ("sonar_new_bugs", 5, 2),
    ("jira_throughput", 20, 31),
    ("jira_lead_time_hours", 72, 41),
]
# Survey metrics: (key, before_value, now_value) as quarterly snapshots.
SURVEY = [
    ("perceived_delivery", 2.9, 4.1),
    ("code_maintainability", 3.1, 3.8),
    ("change_confidence", 3.0, 3.9),
    ("ai_satisfaction", 3.2, 4.3),
    ("hours_saved_week", 1.5, 3.4),
    ("pct_feature_work", 55, 72),
    ("dxi_lite", 3.1, 3.9),
]

INTEGRATIONS = {
    "github": (
        {"repos": ["arbisoft/xiangqi-server", "arbisoft/xiangqi-client"]},
        {"token": "ghp_demo"},
    ),
    "newrelic": ({"account_id": 1234567}, {"api_key": "NRAK-demo"}),
    "sonarqube": (
        {"base_url": "https://sonar.arbisoft.com", "project_key": "xiangqi"},
        {"token": "sqp_demo"},
    ),
    "jira": (
        {"base_url": "https://arbisoft.atlassian.net", "jql": "project = XIANGQI"},
        {"email": "demo@arbisoft.com", "api_token": "jira_demo"},
    ),
}


def _lerp(start: float, end: float, i: int, n: int) -> Decimal:
    value = start + (end - start) * (i / (n - 1))
    return Decimal(str(round(value, 2)))


class Command(BaseCommand):
    help = "Seed a demo team with realistic metrics, baseline, integrations, survey."

    @transaction.atomic
    def handle(self, *args, **options):
        self._wipe()
        team = Team.objects.create(
            name="Xiangqi",
            slug=TEAM_SLUG,
            min_aggregation_size=5,
            loaded_hourly_cost_usd=Decimal("45"),
        )
        admin = self._make_user("demo@arbisoft.com", "Demo Admin")
        Membership.objects.create(user=admin, team=team, role=Membership.Role.ORG_ADMIN)
        for n in range(1, 8):
            member = self._make_user(f"dev{n}@arbisoft.com", f"Developer {n}")
            Membership.objects.create(
                user=member, team=team, role=Membership.Role.MEMBER
            )

        this_monday = timezone.localdate() - dt.timedelta(
            days=timezone.localdate().weekday()
        )
        weeks = [this_monday - dt.timedelta(days=7 * (WEEKS - i)) for i in range(WEEKS)]

        self._seed_weeks(team, weeks[:BASELINE_AFTER_WEEK], is_start=True)
        self._seed_survey(team, weeks[0] - dt.timedelta(days=90), use_before=True)
        capture_baseline(team)
        self._seed_weeks(team, weeks[BASELINE_AFTER_WEEK:], is_start=False)
        self._seed_survey(team, weeks[-1], use_before=False)
        self._seed_integrations(team)
        self._seed_closed_survey(team)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded demo team '{team.name}'. Login: demo@arbisoft.com / "
                f"{DEMO_PASSWORD}  ·  open /dashboards/{TEAM_SLUG}/",
            ),
        )

    def _wipe(self) -> None:
        Team.objects.filter(slug=TEAM_SLUG).delete()
        User.objects.filter(email__endswith="@arbisoft.com").delete()

    def _make_user(self, email: str, name: str):
        user = User.objects.create_user(email=email, password=DEMO_PASSWORD)
        user.name = name
        user.save(update_fields=["name"])
        EmailAddress.objects.create(
            user=user,
            email=email,
            verified=True,
            primary=True,
        )
        return user

    def _seed_weeks(self, team, weeks, *, is_start: bool) -> None:
        # When seeding the pre-baseline weeks, hold values near the start so the
        # baseline reflects the "before AI" level; later weeks ramp to the end.
        for offset, week in enumerate(weeks):
            i = offset if is_start else BASELINE_AFTER_WEEK + offset
            for key, start, end in WEEKLY:
                upsert_snapshot(
                    team=team,
                    metric_key=key,
                    period_start=week,
                    period_end=week + dt.timedelta(days=6),
                    granularity="weekly",
                    value=_lerp(start, end, i, WEEKS),
                )
            upsert_snapshot(
                team=team,
                metric_key="sonar_gate_passed",
                period_start=week,
                period_end=week + dt.timedelta(days=6),
                granularity="weekly",
                value=Decimal("1"),
            )

    def _seed_survey(self, team, start, *, use_before: bool) -> None:
        for key, before, now in SURVEY:
            upsert_snapshot(
                team=team,
                metric_key=key,
                period_start=start,
                period_end=start + dt.timedelta(days=89),
                granularity="quarterly",
                value=Decimal(str(before if use_before else now)),
                source="survey",
            )

    def _seed_integrations(self, team) -> None:
        now = timezone.now()
        for provider, (config, creds) in INTEGRATIONS.items():
            integration = IntegrationConfig(team=team, provider=provider, config=config)
            integration.set_credentials(creds)
            integration.save()
            CollectorRun.objects.create(
                team=team,
                provider=provider,
                status=CollectorRun.Status.SUCCESS,
                finished_at=now,
                snapshots_written=6,
            )

    def _seed_closed_survey(self, team) -> None:
        template = SurveyTemplate.objects.get(key="dx_core4_quarterly")
        now = timezone.now()
        run = SurveyRun.objects.create(
            team=team,
            template=template,
            opens_at=now - dt.timedelta(days=14),
            closes_at=now - dt.timedelta(days=7),
            status=SurveyRun.Status.CLOSED,
        )
        members = list(team.memberships.select_related("user"))
        for index, membership in enumerate(members):
            SurveyToken.objects.create(
                run=run,
                user=membership.user,
                consumed=index < len(members) - 1,  # 7 of 8 responded
            )
