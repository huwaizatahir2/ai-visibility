from __future__ import annotations

from decimal import Decimal

from ai_visibility.collectors.base import REGISTRY
from ai_visibility.collectors.base import BaseCollector
from ai_visibility.collectors.base import MetricValue
from ai_visibility.collectors.base import register


def test_register_adds_collector_to_registry():
    @register
    class FakeCollector(BaseCollector):
        provider = "fake"
        metrics_produced = ["pr_throughput"]

        def collect(self, period_start, period_end):
            return [MetricValue("pr_throughput", Decimal("1"))]

    try:
        assert REGISTRY["fake"] is FakeCollector
    finally:
        REGISTRY.pop("fake", None)
