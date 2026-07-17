from __future__ import annotations

from django.urls import path

from ai_visibility.dashboards import views

app_name = "dashboards"
urlpatterns = [
    path("<slug:team_slug>/", views.OverviewView.as_view(), name="overview"),
    path(
        "<slug:team_slug>/utilization/",
        views.UtilizationView.as_view(),
        name="utilization",
    ),
    path("<slug:team_slug>/impact/", views.ImpactView.as_view(), name="impact"),
    path("<slug:team_slug>/cost/", views.CostView.as_view(), name="cost"),
]
