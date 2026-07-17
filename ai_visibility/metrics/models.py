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
