from __future__ import annotations

from django.urls import path

from ai_visibility.teams import views

app_name = "teams"
urlpatterns = [
    path(
        "<slug:team_slug>/settings/", views.TeamSettingsView.as_view(), name="settings"
    ),
    path(
        "<slug:team_slug>/integrations/<str:provider>/",
        views.update_integration,
        name="update_integration",
    ),
    path(
        "<slug:team_slug>/baseline/",
        views.capture_team_baseline,
        name="capture_baseline",
    ),
    path("<slug:team_slug>/surveys/launch/", views.launch_survey, name="launch_survey"),
]
