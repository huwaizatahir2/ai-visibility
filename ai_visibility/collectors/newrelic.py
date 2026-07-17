"""New Relic collector: Claude Code OTel usage/cost via NerdGraph NRQL.

Exact ``claude_code.*`` metric names evolve with Claude Code releases; verify
against current monitoring docs. Tests pin this collector's contract, not
New Relic's schema.
"""
# NRQL is not SQL and queries are built from internal constants + a date window
# (never user input), so S608 (SQL-injection heuristic) does not apply here.
# ruff: noqa: S608

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import requests

from ai_visibility.collectors.base import BaseCollector
from ai_visibility.collectors.base import MetricValue
from ai_visibility.collectors.base import register

NERDGRAPH = "https://api.newrelic.com/graphql"
TIMEOUT = (10, 30)
QUERY = """
query($accountId: Int!, $nrql: Nrql!) {
  actor { account(id: $accountId) { nrql(query: $nrql) { results } } }
}
"""


def _q(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


@register
class NewRelicCollector(BaseCollector):
    provider = "newrelic"
    metrics_produced = [
        "cc_wau_pct",
        "cc_sessions",
        "cc_active_hours",
        "cc_lines_of_code",
        "cc_cost_usd",
        "cc_accept_rate",
        "change_failure_rate",
        "lead_time_hours",
    ]

    def _nrql(self, nrql: str) -> list[dict]:
        creds = self.integration.get_credentials()
        resp = requests.post(
            NERDGRAPH,
            timeout=TIMEOUT,
            headers={"API-Key": creds["api_key"]},
            json={
                "query": QUERY,
                "variables": {
                    "accountId": int(self.integration.config["account_id"]),
                    "nrql": nrql,
                },
            },
        )
        resp.raise_for_status()
        return resp.json()["data"]["actor"]["account"]["nrql"]["results"]

    def _scalar(self, nrql: str) -> float:
        return self._nrql(nrql)[0]["n"] or 0

    def _dora_metrics(self, window: str) -> tuple[Decimal, Decimal]:
        """Change-failure rate and lead time from Change Tracking deployments.

        Expects New Relic ``Deployment`` events (Change Tracking) carrying a
        numeric ``leadTimeSeconds`` attribute (commit -> deploy), and open
        incidents in ``NrAiIncident``. CFR = incidents / deployments.
        """
        deploys = self._scalar(f"SELECT count(*) AS n FROM Deployment{window}")
        incidents = self._scalar(
            f"SELECT count(*) AS n FROM NrAiIncident WHERE event = 'open'{window}",
        )
        lead_seconds = self._nrql(
            f"SELECT median(leadTimeSeconds) AS n FROM Deployment{window}",
        )[0]["n"]
        cfr = _q(incidents * 100 / deploys) if deploys else Decimal("0")
        lead_hours = _q(lead_seconds / 3600) if lead_seconds else Decimal("0")
        return cfr, lead_hours

    def collect(self, period_start, period_end) -> list[MetricValue]:
        window = ""
        if period_start and period_end:
            until = period_end + dt.timedelta(days=1)
            window = f" SINCE '{period_start}' UNTIL '{until}'"
        members = self.team.memberships.count()

        active = self._scalar(
            "SELECT uniqueCount(user.id) AS n FROM Metric "
            f"WHERE metricName = 'claude_code.session.count'{window}",
        )
        sessions = self._scalar(
            f"SELECT sum(claude_code.session.count) AS n FROM Metric{window}",
        )
        active_secs = self._scalar(
            f"SELECT sum(claude_code.active_time.total) AS n FROM Metric{window}",
        )
        loc = self._scalar(
            "SELECT sum(claude_code.lines_of_code.count) AS n "
            f"FROM Metric WHERE type = 'added'{window}",
        )
        cost = self._scalar(
            f"SELECT sum(claude_code.cost.usage) AS n FROM Metric{window}",
        )
        decisions = self._nrql(
            "SELECT filter(count(*), WHERE decision = 'accept') AS acc, "
            "count(*) AS total FROM Metric "
            f"WHERE metricName = 'claude_code.code_edit_tool.decision'{window}",
        )[0]

        accept_rate = (
            _q(decisions["acc"] * 100 / decisions["total"])
            if decisions.get("total")
            else Decimal("0")
        )
        wau = _q(active * 100 / members) if members else Decimal("0")
        change_failure_rate, lead_time_hours = self._dora_metrics(window)
        return [
            MetricValue("cc_wau_pct", wau),
            MetricValue("cc_sessions", _q(sessions)),
            MetricValue("cc_active_hours", _q(active_secs / 3600)),
            MetricValue("cc_lines_of_code", _q(loc)),
            MetricValue("cc_cost_usd", _q(cost)),
            MetricValue("cc_accept_rate", accept_rate),
            MetricValue("change_failure_rate", change_failure_rate),
            MetricValue("lead_time_hours", lead_time_hours),
        ]
