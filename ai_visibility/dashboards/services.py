from __future__ import annotations

from decimal import Decimal

from ai_visibility.metrics.models import Baseline
from ai_visibility.metrics.models import MetricDefinition
from ai_visibility.metrics.models import MetricSnapshot

DEFAULT_LIMIT = 26


class GroupTooSmallError(Exception):
    """Raised when a team has too few members to show aggregates safely."""


def _check_group(team) -> None:
    if team.memberships.count() < team.min_aggregation_size:
        raise GroupTooSmallError(team.min_aggregation_size)


def metric_series(
    team,
    metric_key: str,
    granularity: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict:
    """Time series for a metric with its baseline and delta, guardrailed.

    ``granularity`` is optional: when omitted the metric's natural cadence is
    used (system metrics are weekly, survey metrics quarterly), so a single
    view can mix both — e.g. the DX Core 4 overview.
    """
    _check_group(team)
    metric = MetricDefinition.objects.get(key=metric_key)
    query = MetricSnapshot.objects.filter(team=team, metric=metric, dimensions={})
    if granularity is not None:
        query = query.filter(granularity=granularity)
    snaps = list(query.order_by("-period_start")[:limit])
    snaps.reverse()

    baseline = Baseline.objects.filter(team=team).order_by("-version").first()
    baseline_value = None
    if baseline and metric_key in baseline.values:
        baseline_value = Decimal(baseline.values[metric_key])

    points = [
        {"period": s.period_start.isoformat(), "value": float(s.value)} for s in snaps
    ]
    latest = points[-1]["value"] if points else None
    delta_pct = None
    if latest is not None and baseline_value not in (None, Decimal(0)):
        delta_pct = round(
            (latest - float(baseline_value)) / float(baseline_value) * 100, 1
        )

    return {
        "key": metric_key,
        "name": metric.name,
        "unit": metric.unit,
        "direction": metric.direction,
        "points": points,
        "baseline": float(baseline_value) if baseline_value is not None else None,
        "delta_pct": delta_pct,
    }


def paired_series(team, metric_key: str, **kwargs) -> dict:
    """A metric series alongside its quality counterweight (golden rule)."""
    metric = MetricDefinition.objects.get(key=metric_key)
    paired = None
    if metric.paired_with:
        paired = metric_series(team, metric.paired_with.key, **kwargs)
    return {"metric": metric_series(team, metric_key, **kwargs), "paired": paired}


def freshness(team) -> dict:
    """Provider -> datetime of its latest successful collector run (or None)."""
    out = {}
    providers = team.integrations.filter(enabled=True).values_list(
        "provider", flat=True
    )
    for provider in providers:
        run = (
            team.collector_runs.filter(provider=provider, status="success")
            .order_by("-finished_at")
            .first()
        )
        out[provider] = run.finished_at if run else None
    return out
