from __future__ import annotations

import datetime as dt

from celery import shared_task
from django.utils import timezone

from ai_visibility.collectors import github  # noqa: F401  (registers collector)
from ai_visibility.collectors import newrelic  # noqa: F401
from ai_visibility.collectors import sonarqube  # noqa: F401
from ai_visibility.collectors.base import REGISTRY
from ai_visibility.collectors.models import CollectorRun
from ai_visibility.metrics.services import upsert_snapshot
from ai_visibility.teams.models import IntegrationConfig
from ai_visibility.teams.models import Team


def last_full_week(today: dt.date | None = None) -> tuple[dt.date, dt.date]:
    """Monday to Sunday of the week before ``today`` (defaults to now)."""
    today = today or timezone.localdate()
    start_of_this_week = today - dt.timedelta(days=today.weekday())
    start = start_of_this_week - dt.timedelta(days=7)
    return start, start + dt.timedelta(days=6)


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
)
def run_collector(self, team_id: int, provider: str) -> None:
    """Run one provider's collector for a team over the last full week."""
    team = Team.objects.get(pk=team_id)
    integration = IntegrationConfig.objects.get(
        team=team,
        provider=provider,
        enabled=True,
    )
    run = CollectorRun.objects.create(team=team, provider=provider)
    period_start, period_end = last_full_week()
    try:
        collector = REGISTRY[provider](team, integration)
        values = collector.collect(period_start, period_end)
        for mv in values:
            upsert_snapshot(
                team=team,
                metric_key=mv.metric_key,
                period_start=period_start,
                period_end=period_end,
                granularity="weekly",
                value=mv.value,
                dimensions=mv.dimensions,
            )
        run.status = CollectorRun.Status.SUCCESS
        run.snapshots_written = len(values)
    except Exception as exc:
        run.status = CollectorRun.Status.FAILED
        run.error = str(exc)[:2000]
        raise
    finally:
        run.finished_at = timezone.now()
        run.save()


@shared_task
def run_all_collectors() -> None:
    """Fan out one collector task per enabled, registered integration."""
    integrations = IntegrationConfig.objects.filter(
        enabled=True,
        provider__in=list(REGISTRY),
    )
    for integration in integrations:
        run_collector.delay(integration.team_id, integration.provider)
