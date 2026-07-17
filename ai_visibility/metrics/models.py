from __future__ import annotations

from django.db import models


class MetricDefinition(models.Model):
    """Catalog entry describing one metric and its quality counterweight."""

    class Dimension(models.TextChoices):
        UTILIZATION = "utilization", "Utilization"
        IMPACT_SPEED = "impact_speed", "Impact — speed"
        IMPACT_QUALITY = "impact_quality", "Impact — quality"
        IMPACT_EXPERIENCE = "impact_experience", "Impact — experience"
        COST = "cost", "Cost"

    class Direction(models.TextChoices):
        HIGHER_BETTER = "higher", "Higher is better"
        LOWER_BETTER = "lower", "Lower is better"

    key = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    dimension = models.CharField(max_length=20, choices=Dimension.choices)
    unit = models.CharField(max_length=30)  # count, hours, %, usd, score_1_5, bool
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        default=Direction.HIGHER_BETTER,
    )
    description = models.TextField(blank=True)
    # The quality metric this one must be shown beside (golden rule).
    paired_with = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self) -> str:
        return self.key


class MetricSnapshot(models.Model):
    """One value of one metric for one team over one period."""

    class Granularity(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        PER_RELEASE = "per_release", "Per release"
        QUARTERLY = "quarterly", "Quarterly"

    class Source(models.TextChoices):
        SYSTEM = "system", "System"
        SURVEY = "survey", "Survey"
        MANUAL = "manual", "Manual"

    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    metric = models.ForeignKey(MetricDefinition, on_delete=models.PROTECT)
    period_start = models.DateField()
    period_end = models.DateField()
    granularity = models.CharField(max_length=15, choices=Granularity.choices)
    value = models.DecimalField(max_digits=14, decimal_places=4)
    dimensions = models.JSONField(default=dict, blank=True)
    dimensions_hash = models.CharField(max_length=64, editable=False)
    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.SYSTEM,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "team",
                    "metric",
                    "period_start",
                    "granularity",
                    "dimensions_hash",
                ],
                name="uniq_snapshot_period",
            ),
        ]
        indexes = [
            models.Index(fields=["team", "metric", "period_start"]),
        ]

    def __str__(self) -> str:
        return f"{self.metric.key}={self.value} [{self.period_start}]"
