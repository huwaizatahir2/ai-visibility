"""Jira collector: work-item throughput and lead time."""

from __future__ import annotations

import datetime as dt
import statistics
from decimal import Decimal

import requests

from ai_visibility.collectors.base import BaseCollector
from ai_visibility.collectors.base import MetricValue
from ai_visibility.collectors.base import register

TIMEOUT = (10, 30)
PAGE_SIZE = 100
# Jira Cloud timestamps look like 2026-07-07T12:00:00.000+0000.
JIRA_DT = "%Y-%m-%dT%H:%M:%S.%f%z"


def _parse(ts: str) -> dt.datetime:
    # JIRA_DT ends with %z, so the result is timezone-aware.
    return dt.datetime.strptime(ts, JIRA_DT)  # noqa: DTZ007


@register
class JiraCollector(BaseCollector):
    provider = "jira"
    metrics_produced = ["jira_throughput", "jira_lead_time_hours"]

    def _search(self, jql: str) -> list[dict]:
        creds = self.integration.get_credentials()
        auth = (creds["email"], creds["api_token"])
        base = self.integration.config["base_url"].rstrip("/")
        issues: list[dict] = []
        start_at = 0
        while True:
            resp = requests.get(
                f"{base}/rest/api/3/search",
                auth=auth,
                timeout=TIMEOUT,
                params={
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": PAGE_SIZE,
                    "fields": "created,resolutiondate",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("issues", [])
            issues.extend(batch)
            start_at += len(batch)
            if not batch or start_at >= data.get("total", 0):
                break
        return issues

    def collect(self, period_start, period_end) -> list[MetricValue]:
        clauses = []
        if jql := self.integration.config.get("jql"):
            clauses.append(jql)
        if period_start and period_end:
            clauses.append(
                f"resolved >= '{period_start}' AND resolved <= '{period_end}'",
            )
        full_jql = " AND ".join(clauses) if clauses else "resolved is not EMPTY"
        issues = self._search(full_jql)

        lead_hours = []
        for issue in issues:
            fields = issue.get("fields", {})
            created = fields.get("created")
            resolved = fields.get("resolutiondate")
            if created and resolved:
                delta = _parse(resolved) - _parse(created)
                lead_hours.append(delta.total_seconds() / 3600)

        median_lead = (
            Decimal(statistics.median(lead_hours)).quantize(Decimal("0.01"))
            if lead_hours
            else Decimal("0")
        )
        return [
            MetricValue("jira_throughput", Decimal(len(issues))),
            MetricValue("jira_lead_time_hours", median_lead),
        ]
