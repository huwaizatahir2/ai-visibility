from __future__ import annotations

from django.urls import path

from ai_visibility.surveys import views

app_name = "surveys"
urlpatterns = [
    path("done/", views.done, name="done"),
    path("<uuid:token>/", views.answer, name="answer"),
]
