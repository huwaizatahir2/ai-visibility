from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class SurveyTemplate(models.Model):
    key = models.SlugField(unique=True)  # dx_core4_quarterly, dxi_lite, pulse
    name = models.CharField(max_length=120)
    cadence = models.CharField(max_length=20)  # quarterly, monthly, adhoc

    def __str__(self) -> str:
        return self.key


class Question(models.Model):
    class QType(models.TextChoices):
        LIKERT = "likert", "Likert (1-5)"
        NUMBER = "number", "Number"
        PERCENT = "percent", "Percent (0-100)"

    template = models.ForeignKey(
        SurveyTemplate,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    order = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=300)
    qtype = models.CharField(max_length=10, choices=QType.choices)
    # Mean answer maps to this metric on close; blank = aggregated separately.
    metric_key = models.SlugField(blank=True, default="")

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.template.key} Q{self.order}"


class SurveyRun(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    template = models.ForeignKey(SurveyTemplate, on_delete=models.PROTECT)
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="survey_runs",
    )
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    def __str__(self) -> str:
        return f"{self.team} · {self.template.key} · {self.status}"


class SurveyToken(models.Model):
    """Proves membership; never linked to a Response — anonymity by construction."""

    run = models.ForeignKey(SurveyRun, on_delete=models.CASCADE, related_name="tokens")
    # For delivery and reminders only; never joined to responses.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    consumed = models.BooleanField(default=False)

    def __str__(self) -> str:
        return str(self.token)


class Response(models.Model):
    run = models.ForeignKey(
        SurveyRun, on_delete=models.CASCADE, related_name="responses",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    # Deliberately NO user/token FK — responses are anonymous.

    def __str__(self) -> str:
        return f"Response to run {self.run_id}"


class Answer(models.Model):
    response = models.ForeignKey(
        Response, on_delete=models.CASCADE, related_name="answers",
    )
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    value = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.question} = {self.value}"
