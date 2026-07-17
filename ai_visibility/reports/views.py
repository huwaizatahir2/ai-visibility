from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from ai_visibility.reports.services import build_monthly_report
from ai_visibility.teams.access import require_role
from ai_visibility.teams.models import Membership
from ai_visibility.teams.models import Team


class MonthlyReportView(LoginRequiredMixin, TemplateView):
    template_name = "reports/monthly.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.team = get_object_or_404(Team, slug=kwargs["team_slug"])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        require_role(
            request.user,
            self.team,
            Membership.Role.TEAM_LEAD,
            Membership.Role.ORG_ADMIN,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_monthly_report(self.team))
        return context
