from __future__ import annotations

from decimal import Decimal

import pytest
import responses

from ai_visibility.collectors.jira import JiraCollector
from ai_visibility.teams.tests.factories import IntegrationConfigFactory

pytestmark = pytest.mark.django_db
BASE = "https://acme.atlassian.net"

ISSUES = [
    {
        "fields": {
            "created": "2026-07-07T00:00:00.000+0000",
            "resolutiondate": "2026-07-07T12:00:00.000+0000",
        },
    },
    {
        "fields": {
            "created": "2026-07-08T00:00:00.000+0000",
            "resolutiondate": "2026-07-08T06:00:00.000+0000",
        },
    },
    {
        "fields": {
            "created": "2026-07-09T00:00:00.000+0000",
            "resolutiondate": "2026-07-09T18:00:00.000+0000",
        },
    },
]


@responses.activate
def test_jira_collector_throughput_and_lead_time():
    responses.get(
        f"{BASE}/rest/api/3/search",
        json={"issues": ISSUES, "total": 3, "startAt": 0, "maxResults": 100},
    )
    ic = IntegrationConfigFactory(
        provider="jira",
        config={"base_url": BASE, "jql": "project = ENG"},
    )
    ic.set_credentials({"email": "a@b.com", "api_token": "t"})
    ic.save()

    values = {
        mv.metric_key: mv.value for mv in JiraCollector(ic.team, ic).collect(None, None)
    }
    assert values["jira_throughput"] == Decimal("3")
    assert values["jira_lead_time_hours"] == Decimal("12")  # median of 12, 6, 18
