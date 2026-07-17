from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from ai_visibility.surveys.models import SurveyRun
from ai_visibility.surveys.models import SurveyTemplate
from ai_visibility.surveys.models import SurveyToken


def open_survey_run(*, team, template_key: str, days_open: int = 7) -> SurveyRun:
    """Open a run for a template and email one tokenized link per team member."""
    template = SurveyTemplate.objects.get(key=template_key)
    now = timezone.now()
    run = SurveyRun.objects.create(
        team=team,
        template=template,
        opens_at=now,
        closes_at=now + dt.timedelta(days=days_open),
    )
    tokens = [
        SurveyToken(run=run, user=membership.user)
        for membership in team.memberships.select_related("user")
    ]
    SurveyToken.objects.bulk_create(tokens)

    for token in run.tokens.select_related("user"):
        link = reverse("surveys:answer", args=[token.token])
        send_mail(
            subject=f"Your input on {template.name}",
            message=f"Please take the team survey (anonymous): {link}",
            from_email=None,
            recipient_list=[token.user.email],
        )
    return run


def response_rate(run: SurveyRun) -> Decimal:
    """Consumed tokens as a percentage of issued tokens."""
    issued = run.tokens.count()
    if not issued:
        return Decimal("0")
    consumed = run.tokens.filter(consumed=True).count()
    return (Decimal(consumed) * 100 / Decimal(issued)).quantize(Decimal("0.01"))
