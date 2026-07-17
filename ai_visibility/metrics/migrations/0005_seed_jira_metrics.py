from __future__ import annotations

from django.db import migrations

JIRA_METRICS = [
    ("jira_throughput", "Work-item throughput", "impact_speed", "count", "higher",
     "Resolved Jira work items per period."),
    ("jira_lead_time_hours", "Work-item lead time", "impact_speed", "hours", "lower",
     "Median hours from issue created to resolved."),
]


def seed(apps, schema_editor):
    metric_definition = apps.get_model("metrics", "MetricDefinition")
    for key, name, dimension, unit, direction, description in JIRA_METRICS:
        metric_definition.objects.update_or_create(
            key=key,
            defaults={
                "name": name,
                "dimension": dimension,
                "unit": unit,
                "direction": direction,
                "description": description,
            },
        )


def unseed(apps, schema_editor):
    metric_definition = apps.get_model("metrics", "MetricDefinition")
    metric_definition.objects.filter(key__in=[row[0] for row in JIRA_METRICS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("metrics", "0004_baseline"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
