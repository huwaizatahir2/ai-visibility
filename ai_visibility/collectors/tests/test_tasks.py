from __future__ import annotations

from decimal import Decimal

import pytest

from ai_visibility.collectors import tasks
from ai_visibility.collectors.base import REGISTRY
from ai_visibility.collectors.base import BaseCollector
from ai_visibility.collectors.base import MetricValue
from ai_visibility.collectors.base import register
from ai_visibility.collectors.models import CollectorRun
from ai_visibility.metrics.models import MetricSnapshot
from ai_visibility.teams.tests.factories import IntegrationConfigFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def fake_collector():
    @register
    class Fake(BaseCollector):
        provider = "fake"
        metrics_produced = ["pr_throughput"]

        def collect(self, period_start, period_end):
            return [MetricValue("pr_throughput", Decimal("7"))]

    yield Fake
    REGISTRY.pop("fake", None)


def test_run_collector_writes_snapshots_and_logs_success(fake_collector):
    ic = IntegrationConfigFactory(provider="fake")
    tasks.run_collector(ic.team_id, "fake")
    run = CollectorRun.objects.get()
    assert run.status == CollectorRun.Status.SUCCESS
    assert run.snapshots_written == 1
    assert MetricSnapshot.objects.get().value == Decimal("7")


def test_run_collector_logs_failure_on_exception(fake_collector, monkeypatch):
    ic = IntegrationConfigFactory(provider="fake")
    monkeypatch.setattr(fake_collector, "collect", lambda *args: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        tasks.run_collector(ic.team_id, "fake")
    assert CollectorRun.objects.get().status == CollectorRun.Status.FAILED
