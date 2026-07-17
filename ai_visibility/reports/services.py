from __future__ import annotations

from decimal import Decimal

from ai_visibility.dashboards.services import GroupTooSmallError
from ai_visibility.dashboards.services import metric_series
from ai_visibility.metrics.models import MetricSnapshot
from ai_visibility.reports.roi import WEEKS_PER_MONTH
from ai_visibility.reports.roi import compute_roi
from ai_visibility.surveys.models import SurveyRun
from ai_visibility.surveys.services import response_rate

HEADLINE_METRICS = [
    "pr_throughput",
    "perceived_delivery",
    "dxi_lite",
    "code_maintainability",
    "change_failure_rate",
]
# Quality guardrails vs baseline (KR5): must not regress.
GUARDRAIL_METRICS = ["pr_revert_rate", "change_failure_rate", "sonar_gate_passed"]


def _latest_value(team, metric_key: str) -> Decimal | None:
    snap = (
        MetricSnapshot.objects.filter(team=team, metric__key=metric_key)
        .order_by("-period_start")
        .first()
    )
    return snap.value if snap else None


def build_monthly_report(team) -> dict:
    """Assemble the one-page leadership report context for a team."""
    context: dict = {"team": team}
    try:
        context["headline"] = [metric_series(team, k) for k in HEADLINE_METRICS]
        context["guardrails"] = [metric_series(team, k) for k in GUARDRAIL_METRICS]
        context["throughput"] = metric_series(team, "pr_throughput")
        context["too_small"] = False
    except GroupTooSmallError as exc:
        context["too_small"] = True
        context["min_size"] = exc.args[0]

    hours = _latest_value(team, "hours_saved_week") or Decimal(0)
    weekly_cost = _latest_value(team, "cc_cost_usd") or Decimal(0)
    context["roi"] = compute_roi(
        devs=team.memberships.count(),
        hours_saved_per_dev_week=hours,
        loaded_hourly_cost=team.loaded_hourly_cost_usd,
        monthly_spend=weekly_cost * WEEKS_PER_MONTH,
    )

    last_run = (
        SurveyRun.objects.filter(team=team, status=SurveyRun.Status.CLOSED)
        .order_by("-closes_at")
        .first()
    )
    context["response_rate"] = response_rate(last_run) if last_run else None
    return context
