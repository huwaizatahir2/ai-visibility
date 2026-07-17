from __future__ import annotations

from django.db import migrations

# (key, name, dimension, unit, direction, description)
CATALOG = [
    # Utilization
    ("cc_wau_pct", "Weekly active users", "utilization", "%", "higher",
     "Share of the team running the AI tool in a week."),
    ("cc_dau_pct", "Daily active users", "utilization", "%", "higher",
     "Share of the team using the AI tool daily (depth of adoption)."),
    ("pct_ai_assisted_prs", "AI-assisted PRs", "utilization", "%", "higher",
     "Share of merged PRs flagged as AI-assisted."),
    ("cc_accept_rate", "Suggestion accept rate", "utilization", "%", "higher",
     "Edits accepted vs suggested by the AI tool."),
    ("cc_active_hours", "Active AI hours", "utilization", "hours", "higher",
     "Engaged time in the AI tool per period."),
    ("cc_sessions", "AI sessions", "utilization", "count", "higher",
     "Number of AI tool sessions started."),
    ("cc_lines_of_code", "AI-authored lines", "utilization", "count", "higher",
     "Lines of code authored with the AI tool."),
    # Impact — speed
    ("pr_throughput", "PR throughput", "impact_speed", "count", "higher",
     "Merged pull requests per period."),
    ("pr_cycle_time_hours", "PR cycle time", "impact_speed", "hours", "lower",
     "Median hours from PR open to merge."),
    ("lead_time_hours", "Lead time for change", "impact_speed", "hours", "lower",
     "Hours from commit to production (DORA)."),
    ("perceived_delivery", "Perceived rate of delivery", "impact_speed", "score_1_5", "higher",
     "Survey: do devs feel they ship faster?"),
    # Impact — quality
    ("pr_revert_rate", "PR revert rate", "impact_quality", "%", "lower",
     "Reverted PRs as a share of total PRs."),
    ("change_failure_rate", "Change failure rate", "impact_quality", "%", "lower",
     "Deploys causing an incident or rollback (DORA)."),
    ("code_maintainability", "Code maintainability", "impact_quality", "score_1_5", "higher",
     "Survey: is AI-produced code easy to understand and modify?"),
    ("sonar_gate_passed", "Sonar quality gate", "impact_quality", "bool", "higher",
     "Whether the new-code quality gate passed."),
    ("sonar_new_bugs", "New-code bugs", "impact_quality", "count", "lower",
     "New bugs introduced on the analyzed project."),
    # Impact — experience
    ("ai_satisfaction", "AI satisfaction", "impact_experience", "score_1_5", "higher",
     "Survey: satisfaction using the AI tool."),
    ("change_confidence", "Change confidence", "impact_experience", "score_1_5", "higher",
     "Survey: confidence that shipped changes won't break things."),
    ("pct_feature_work", "Time on feature work", "impact_experience", "%", "higher",
     "Survey: share of time on feature work vs toil."),
    ("hours_saved_week", "Hours saved per week", "impact_experience", "hours", "higher",
     "Survey: self-reported hours saved per dev per week."),
    ("dxi_lite", "DXI-lite", "impact_experience", "score_1_5", "higher",
     "Composite developer-experience index (lite)."),
    # Cost
    ("cc_cost_usd", "AI spend", "cost", "usd", "lower",
     "AI tool spend for the period."),
]

# Speed/volume metric -> its quality counterweight (set both directions).
PAIRS = [
    ("pr_throughput", "pr_revert_rate"),
    ("pr_cycle_time_hours", "sonar_gate_passed"),
    ("lead_time_hours", "change_failure_rate"),
    ("perceived_delivery", "code_maintainability"),
    ("cc_lines_of_code", "sonar_new_bugs"),
]


def seed(apps, schema_editor):
    metric_definition = apps.get_model("metrics", "MetricDefinition")
    for key, name, dimension, unit, direction, description in CATALOG:
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
    for speed_key, quality_key in PAIRS:
        speed = metric_definition.objects.get(key=speed_key)
        quality = metric_definition.objects.get(key=quality_key)
        speed.paired_with = quality
        speed.save(update_fields=["paired_with"])
        quality.paired_with = speed
        quality.save(update_fields=["paired_with"])


def unseed(apps, schema_editor):
    metric_definition = apps.get_model("metrics", "MetricDefinition")
    keys = [row[0] for row in CATALOG]
    metric_definition.objects.filter(key__in=keys).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("metrics", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
