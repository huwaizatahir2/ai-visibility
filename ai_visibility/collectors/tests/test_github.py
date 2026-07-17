from __future__ import annotations

from decimal import Decimal

import pytest
import responses

from ai_visibility.collectors.github import SEARCH_URL
from ai_visibility.collectors.github import GitHubCollector
from ai_visibility.teams.tests.factories import IntegrationConfigFactory

pytestmark = pytest.mark.django_db

ITEMS = [
    {
        "title": "feat: a",
        "body": "- [x] AI-assisted",
        "pull_request": {"merged_at": "2026-07-07T12:00:00Z"},
        "created_at": "2026-07-07T00:00:00Z",
    },
    {
        "title": 'Revert "feat: a"',
        "body": "",
        "pull_request": {"merged_at": "2026-07-08T06:00:00Z"},
        "created_at": "2026-07-08T00:00:00Z",
    },
    {
        "title": "fix: b",
        "body": "- [x] AI-assisted",
        "pull_request": {"merged_at": "2026-07-09T18:00:00Z"},
        "created_at": "2026-07-09T00:00:00Z",
    },
]


@responses.activate
def test_github_collector_computes_four_metrics():
    responses.get(SEARCH_URL, json={"total_count": 3, "items": ITEMS})
    ic = IntegrationConfigFactory(provider="github", config={"repos": ["acme/app"]})
    ic.set_credentials({"token": "t"})
    ic.save()

    values = {
        mv.metric_key: mv.value
        for mv in GitHubCollector(ic.team, ic).collect(None, None)
    }
    assert values["pr_throughput"] == Decimal("3")
    assert values["pr_cycle_time_hours"] == Decimal("12")  # median of 12, 6, 18
    assert values["pr_revert_rate"] == Decimal("33.33")
    assert values["pct_ai_assisted_prs"] == Decimal("66.67")
