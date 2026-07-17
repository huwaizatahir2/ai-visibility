from __future__ import annotations

import json
from decimal import Decimal

import pytest
import responses

from ai_visibility.collectors.newrelic import NERDGRAPH
from ai_visibility.collectors.newrelic import NewRelicCollector
from ai_visibility.teams.tests.factories import IntegrationConfigFactory
from ai_visibility.teams.tests.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def _nrql_callback(request):
    nrql = json.loads(request.body)["variables"]["nrql"]
    if "uniqueCount(user.id)" in nrql:
        results = [{"n": 3}]
    elif "sum(claude_code.session.count)" in nrql:
        results = [{"n": 50}]
    elif "active_time" in nrql:
        results = [{"n": 36000}]
    elif "lines_of_code" in nrql:
        results = [{"n": 1234}]
    elif "cost.usage" in nrql:
        results = [{"n": 42.5}]
    elif "leadTimeSeconds" in nrql:
        results = [{"n": 7200}]  # 2 hours
    elif "NrAiIncident" in nrql:
        results = [{"n": 1}]
    elif "FROM Deployment" in nrql:
        results = [{"n": 4}]  # 4 deploys
    else:  # code_edit_tool.decision
        results = [{"acc": 80, "total": 100}]
    body = {"data": {"actor": {"account": {"nrql": {"results": results}}}}}
    return (200, {}, json.dumps(body))


@responses.activate
def test_newrelic_collector_computes_usage_and_cost():
    responses.add_callback(
        responses.POST,
        NERDGRAPH,
        callback=_nrql_callback,
        content_type="application/json",
    )
    ic = IntegrationConfigFactory(provider="newrelic", config={"account_id": 123})
    ic.set_credentials({"api_key": "NRAK-x"})
    ic.save()
    MembershipFactory.create_batch(5, team=ic.team)  # 5-member team

    values = {
        mv.metric_key: mv.value
        for mv in NewRelicCollector(ic.team, ic).collect(None, None)
    }
    assert values["cc_wau_pct"] == Decimal("60")  # 3 of 5 active
    assert values["cc_sessions"] == Decimal("50")
    assert values["cc_active_hours"] == Decimal("10")  # 36000s / 3600
    assert values["cc_lines_of_code"] == Decimal("1234")
    assert values["cc_cost_usd"] == Decimal("42.5")
    assert values["cc_accept_rate"] == Decimal("80")
    assert values["change_failure_rate"] == Decimal("25")  # 1 incident / 4 deploys
    assert values["lead_time_hours"] == Decimal("2")  # 7200s / 3600
    assert set(values) == set(NewRelicCollector.metrics_produced)
