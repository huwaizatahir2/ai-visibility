from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.views.generic import TemplateView

from ai_visibility.metrics.services import capture_baseline
from ai_visibility.surveys.services import open_survey_run
from ai_visibility.teams.access import require_role
from ai_visibility.teams.access import require_team_member
from ai_visibility.teams.forms import IntegrationForm
from ai_visibility.teams.models import IntegrationConfig
from ai_visibility.teams.models import Membership
from ai_visibility.teams.models import Team

LEADS = (Membership.Role.TEAM_LEAD, Membership.Role.ORG_ADMIN)


def _get_team(slug: str) -> Team:
    return get_object_or_404(Team, slug=slug)


class TeamSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "teams/settings.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.team = _get_team(kwargs["team_slug"])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        require_team_member(request.user, self.team)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membership = require_team_member(self.request.user, self.team)
        existing = {i.provider: i for i in self.team.integrations.all()}
        context["team"] = self.team
        context["can_edit"] = membership.role in LEADS
        context["is_org_admin"] = membership.role == Membership.Role.ORG_ADMIN
        context["providers"] = [
            {"key": value, "label": label, "config": existing.get(value)}
            for value, label in IntegrationConfig.Provider.choices
        ]
        return context


@login_required
def update_integration(request, team_slug: str, provider: str):
    team = _get_team(team_slug)
    require_role(request.user, team, *LEADS)
    integration, _created = IntegrationConfig.objects.get_or_create(
        team=team,
        provider=provider,
    )
    if request.method == "POST":
        form = IntegrationForm(request.POST, instance=integration)
        if form.is_valid():
            form.save()
            messages.success(request, f"{provider} integration saved.")
    return redirect("teams:settings", team_slug=team.slug)


@login_required
def capture_team_baseline(request, team_slug: str):
    team = _get_team(team_slug)
    require_role(request.user, team, Membership.Role.ORG_ADMIN)
    if request.method == "POST":
        baseline = capture_baseline(team)
        messages.success(request, f"Baseline v{baseline.version} captured.")
    return redirect("teams:settings", team_slug=team.slug)


@login_required
def launch_survey(request, team_slug: str):
    team = _get_team(team_slug)
    require_role(request.user, team, *LEADS)
    if request.method == "POST":
        template_key = request.POST.get("template_key", "dx_core4_quarterly")
        open_survey_run(team=team, template_key=template_key)
        messages.success(request, "Survey launched.")
    return redirect("teams:settings", team_slug=team.slug)
