from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from ai_visibility.surveys.models import SurveyRun
from ai_visibility.surveys.services import close_survey_run


@shared_task
def close_due_survey_runs() -> None:
    """Close every open run whose window has ended, aggregating its answers."""
    now = timezone.now()
    due = SurveyRun.objects.filter(status=SurveyRun.Status.OPEN, closes_at__lt=now)
    for run in due:
        close_survey_run(run)
