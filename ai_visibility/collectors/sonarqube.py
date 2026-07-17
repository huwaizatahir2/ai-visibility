"""SonarQube collector: new-code quality gate and new bugs."""

from __future__ import annotations

from decimal import Decimal

import requests

from ai_visibility.collectors.base import BaseCollector
from ai_visibility.collectors.base import MetricValue
from ai_visibility.collectors.base import register

TIMEOUT = (10, 30)
GATE_OK = "OK"


def _period_value(measure: dict) -> Decimal:
    raw = measure.get("period", {}).get("value") or measure.get("value") or "0"
    return Decimal(raw)


@register
class SonarQubeCollector(BaseCollector):
    provider = "sonarqube"
    metrics_produced = ["sonar_new_bugs", "sonar_gate_passed"]

    def collect(self, period_start, period_end) -> list[MetricValue]:
        cfg = self.integration.config
        auth = (self.integration.get_credentials()["token"], "")
        base = cfg["base_url"].rstrip("/")
        key = cfg["project_key"]

        measures = requests.get(
            f"{base}/api/measures/component",
            auth=auth,
            timeout=TIMEOUT,
            params={"component": key, "metricKeys": "new_bugs,new_coverage"},
        )
        measures.raise_for_status()
        by_key = {m["metric"]: m for m in measures.json()["component"]["measures"]}

        gate = requests.get(
            f"{base}/api/qualitygates/project_status",
            auth=auth,
            timeout=TIMEOUT,
            params={"projectKey": key},
        )
        gate.raise_for_status()
        gate_passed = gate.json()["projectStatus"]["status"] == GATE_OK

        return [
            MetricValue("sonar_new_bugs", _period_value(by_key.get("new_bugs", {}))),
            MetricValue("sonar_gate_passed", Decimal(1) if gate_passed else Decimal(0)),
        ]
