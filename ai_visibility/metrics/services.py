from __future__ import annotations

import hashlib
import json

from ai_visibility.metrics.models import MetricDefinition
from ai_visibility.metrics.models import MetricSnapshot


def dimensions_hash(dimensions: dict) -> str:
    """Stable hash of a dimensions dict for the snapshot uniqueness key."""
    encoded = json.dumps(dimensions, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def upsert_snapshot(  # noqa: PLR0913
    *,
    team,
    metric_key: str,
    period_start,
    period_end,
    granularity: str,
    value,
    dimensions: dict | None = None,
    source: str = MetricSnapshot.Source.SYSTEM,
) -> MetricSnapshot:
    """Insert or update a snapshot idempotently on its uniqueness key."""
    dimensions = dimensions or {}
    metric = MetricDefinition.objects.get(key=metric_key)
    obj, _created = MetricSnapshot.objects.update_or_create(
        team=team,
        metric=metric,
        period_start=period_start,
        granularity=granularity,
        dimensions_hash=dimensions_hash(dimensions),
        defaults={
            "period_end": period_end,
            "value": value,
            "dimensions": dimensions,
            "source": source,
        },
    )
    return obj
