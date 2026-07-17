from __future__ import annotations

import pytest

from ai_visibility.metrics.models import MetricDefinition

pytestmark = pytest.mark.django_db


def test_catalog_seeded_with_paired_metrics():
    pr = MetricDefinition.objects.get(key="pr_throughput")
    assert pr.dimension == MetricDefinition.Dimension.IMPACT_SPEED
    assert pr.paired_with.key == "pr_revert_rate"  # golden-rule pairing
    assert MetricDefinition.objects.count() >= 15


def test_pairings_are_bidirectional():
    revert = MetricDefinition.objects.get(key="pr_revert_rate")
    assert revert.paired_with.key == "pr_throughput"
