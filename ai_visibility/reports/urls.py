from __future__ import annotations

from django.urls import path

from ai_visibility.reports import views

app_name = "reports"
urlpatterns = [
    path(
        "<slug:team_slug>/monthly/", views.MonthlyReportView.as_view(), name="monthly"
    ),
]
