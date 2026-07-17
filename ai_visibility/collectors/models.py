from __future__ import annotations

from django.db import models


class CollectorRun(models.Model):
    """Log row for one execution of one collector — powers freshness + alerts."""

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="collector_runs",
    )
    provider = models.CharField(max_length=20)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    snapshots_written = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["team", "provider", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.team} · {self.provider} · {self.status}"
