from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from ai_visibility.dashboards import services
from ai_visibility.dashboards.services import GroupTooSmallError
from ai_visibility.teams.access import require_team_member
from ai_visibility.teams.models import Team

HEADLINE_METRICS = [
    "pr_throughput",
    "perceived_delivery",
    "dxi_lite",
    "code_maintainability",
    "change_failure_rate",
]
UTILIZATION_METRICS = [
    "cc_wau_pct",
    "cc_dau_pct",
    "pct_ai_assisted_prs",
    "cc_accept_rate",
    "cc_sessions",
    "cc_active_hours",
]
SPEED_METRICS = [
    "pr_throughput",
    "pr_cycle_time_hours",
    "lead_time_hours",
    "perceived_delivery",
]
COST_METRICS = ["cc_cost_usd"]

# Weekly-cadence benchmark line for adoption (mature orgs hit 60-70%).
WAU_BENCHMARK = 65


class TeamViewMixin(LoginRequiredMixin):
    """Load the team from the URL slug and enforce membership."""

    active_tab = ""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.team = get_object_or_404(Team, slug=kwargs["team_slug"])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        require_team_member(request.user, self.team)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["team"] = self.team
        context["active_tab"] = self.active_tab
        context["freshness"] = services.freshness(self.team)
        return context

    def _cards(self, keys):
        try:
            return {"cards": [services.metric_series(self.team, k) for k in keys]}
        except GroupTooSmallError as exc:
            return {"too_small": True, "min_size": exc.args[0]}

    def _panels(self, keys):
        try:
            return {"panels": [services.paired_series(self.team, k) for k in keys]}
        except GroupTooSmallError as exc:
            return {"too_small": True, "min_size": exc.args[0]}


class OverviewView(TeamViewMixin, TemplateView):
    template_name = "dashboards/overview.html"
    active_tab = "overview"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._cards(HEADLINE_METRICS))
        return context


class UtilizationView(TeamViewMixin, TemplateView):
    template_name = "dashboards/utilization.html"
    active_tab = "utilization"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._cards(UTILIZATION_METRICS))
        context["wau_benchmark"] = WAU_BENCHMARK
        return context


class ImpactView(TeamViewMixin, TemplateView):
    template_name = "dashboards/impact.html"
    active_tab = "impact"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._panels(SPEED_METRICS))
        return context


class CostView(TeamViewMixin, TemplateView):
    template_name = "dashboards/cost.html"
    active_tab = "cost"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._cards(COST_METRICS))
        return context
