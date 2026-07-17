from __future__ import annotations

from django.db import migrations

# key -> (name, cadence, [(order, text, qtype, metric_key), ...])
DX_CORE4 = [
    (1, "Claude Code helps me deliver work faster.", "likert", "perceived_delivery"),
    (2, "Code produced with AI is easy to understand and modify.", "likert", "code_maintainability"),
    (3, "I'm confident the changes I ship won't break things.", "likert", "change_confidence"),
    (4, "I'm satisfied using Claude Code in my workflow.", "likert", "ai_satisfaction"),
    (5, "How many hours did Claude Code save you this week?", "number", "hours_saved_week"),
    (6, "What percent of your time this week was on feature work vs toil?", "percent", "pct_feature_work"),
]

DXI_DRIVERS = [
    "I have enough uninterrupted focus time for deep work.",
    "I can iterate on my code locally quickly.",
    "Our release process is smooth and low-friction.",
    "Our codebase is easy to understand and modify.",
    "Documentation helps me get my work done.",
    "My tools and development environment are adequate.",
    "Builds and tests are fast enough.",
    "On-call and incident load is manageable.",
    "Requirements for my work are clear.",
    "Cross-team dependencies rarely block me.",
    "I can easily understand unfamiliar parts of the codebase.",
    "Technical debt does not slow me down much.",
    "I am confident shipping changes to production.",
    "Overall, my day-to-day developer experience is good.",
]

PULSE = [
    (1, "Was your recent work easier thanks to AI assistance?", "likert", ""),
]


def seed(apps, schema_editor):
    survey_template = apps.get_model("surveys", "SurveyTemplate")
    question = apps.get_model("surveys", "Question")

    core4, _ = survey_template.objects.update_or_create(
        key="dx_core4_quarterly",
        defaults={"name": "DX Core 4 (quarterly)", "cadence": "quarterly"},
    )
    for order, text, qtype, metric_key in DX_CORE4:
        question.objects.update_or_create(
            template=core4,
            order=order,
            defaults={"text": text, "qtype": qtype, "metric_key": metric_key},
        )

    dxi, _ = survey_template.objects.update_or_create(
        key="dxi_lite",
        defaults={"name": "DXI-lite (14 drivers)", "cadence": "quarterly"},
    )
    for order, text in enumerate(DXI_DRIVERS, start=1):
        question.objects.update_or_create(
            template=dxi,
            order=order,
            defaults={"text": text, "qtype": "likert", "metric_key": ""},
        )

    pulse, _ = survey_template.objects.update_or_create(
        key="pulse",
        defaults={"name": "Pulse check", "cadence": "adhoc"},
    )
    for order, text, qtype, metric_key in PULSE:
        question.objects.update_or_create(
            template=pulse,
            order=order,
            defaults={"text": text, "qtype": qtype, "metric_key": metric_key},
        )


def unseed(apps, schema_editor):
    survey_template = apps.get_model("surveys", "SurveyTemplate")
    survey_template.objects.filter(
        key__in=["dx_core4_quarterly", "dxi_lite", "pulse"],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("surveys", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
