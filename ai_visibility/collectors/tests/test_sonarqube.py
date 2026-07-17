from __future__ import annotations

from decimal import Decimal

import pytest
import responses

from ai_visibility.collectors.sonarqube import SonarQubeCollector
from ai_visibility.teams.tests.factories import IntegrationConfigFactory

pytestmark = pytest.mark.django_db
BASE = "https://sonar.example.com"


@responses.activate
def test_sonarqube_collector_reads_bugs_and_gate():
    responses.get(
        f"{BASE}/api/measures/component",
        json={
            "component": {
                "measures": [
                    {"metric": "new_bugs", "value": "2", "period": {"value": "2"}},
                ],
            },
        },
    )
    responses.get(
        f"{BASE}/api/qualitygates/project_status",
        json={"projectStatus": {"status": "OK"}},
    )
    ic = IntegrationConfigFactory(
        provider="sonarqube",
        config={"base_url": BASE, "project_key": "xiangqi"},
    )
    ic.set_credentials({"token": "sqp_x"})
    ic.save()

    values = {
        mv.metric_key: mv.value
        for mv in SonarQubeCollector(ic.team, ic).collect(None, None)
    }
    assert values["sonar_new_bugs"] == Decimal("2")
    assert values["sonar_gate_passed"] == Decimal("1")
