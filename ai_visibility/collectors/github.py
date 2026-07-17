"""GitHub collector: PR throughput, cycle time, revert rate, % AI-assisted."""

from __future__ import annotations

import datetime as dt
import statistics
from decimal import Decimal

import requests

from ai_visibility.collectors.base import BaseCollector
from ai_visibility.collectors.base import MetricValue
from ai_visibility.collectors.base import register

SEARCH_URL = "https://api.github.com/search/issues"
PER_PAGE = 100
TIMEOUT = (10, 30)
AI_ASSISTED_MARKER = "[x] AI-assisted"


def _pct(part: int, whole: int) -> Decimal:
    if not whole:
        return Decimal("0")
    return Decimal(part * 100 / whole).quantize(Decimal("0.01"))


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


@register
class GitHubCollector(BaseCollector):
    provider = "github"
    metrics_produced = [
        "pr_throughput",
        "pr_cycle_time_hours",
        "pr_revert_rate",
        "pct_ai_assisted_prs",
    ]

    def _search(self, query: str) -> list[dict]:
        token = self.integration.get_credentials()["token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        items: list[dict] = []
        page = 1
        while True:
            resp = requests.get(
                SEARCH_URL,
                params={"q": query, "per_page": PER_PAGE, "page": page},
                headers=headers,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            batch = resp.json()["items"]
            items.extend(batch)
            if len(batch) < PER_PAGE:
                break
            page += 1
        return items

    def collect(self, period_start, period_end) -> list[MetricValue]:
        items: list[dict] = []
        for repo in self.integration.config.get("repos", []):
            query = f"repo:{repo} is:pr is:merged"
            if period_start and period_end:
                query += f" merged:{period_start}..{period_end}"
            items.extend(self._search(query))

        total = len(items)
        cycle_hours = [
            (
                _parse(i["pull_request"]["merged_at"]) - _parse(i["created_at"])
            ).total_seconds()
            / 3600
            for i in items
            if i.get("pull_request", {}).get("merged_at")
        ]
        reverts = sum(1 for i in items if i["title"].startswith("Revert"))
        ai_assisted = sum(
            1 for i in items if AI_ASSISTED_MARKER in (i.get("body") or "")
        )
        median_cycle = (
            Decimal(statistics.median(cycle_hours)).quantize(Decimal("0.01"))
            if cycle_hours
            else Decimal("0")
        )
        return [
            MetricValue("pr_throughput", Decimal(total)),
            MetricValue("pr_cycle_time_hours", median_cycle),
            MetricValue("pr_revert_rate", _pct(reverts, total)),
            MetricValue("pct_ai_assisted_prs", _pct(ai_assisted, total)),
        ]
