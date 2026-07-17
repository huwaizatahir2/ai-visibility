# AI Visibility

**Self-hosted platform for measuring AI coding-tool impact on developer productivity.**

AI Visibility answers three questions about your team's use of AI coding tools (Claude Code first) — using data you already own (GitHub, New Relic, SonarQube) plus lightweight in-app surveys — and reports them at the **team level only**, never as individual surveillance.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Why

Adopting an AI coding tool without measurement leaves you with anecdote ("it feels faster") instead of a defensible read on value. AI Visibility implements the [DX AI Measurement framework](https://getdx.com/blog/ai-measurement-hub/) — **Utilization / Impact / Cost** — so every metric answers exactly one question, and speed is never reported without its quality counterweight.

| Dimension | Question | Guardrail |
|---|---|---|
| **Utilization** | Are devs actually using the tool? | Paired with Impact — usage ≠ value |
| **Impact** | Is it improving speed, quality, experience? | Speed metrics always shown beside quality metrics |
| **Cost** | Does time saved beat what we spend? | Cross-checked against objective throughput |

> Real productivity gains land around **5–15%**, not 50–100%. AI Visibility is built to measure that honestly, including the guardrails that stop a team "winning" on speed while quietly degrading quality.

## Features

- **Multi-tenant** — one deployment, many teams. Each team configures its own integrations; data is strictly team-scoped.
- **Pluggable collectors** — scheduled jobs pull metrics from **GitHub** (PR throughput, cycle time, revert rate, % AI-assisted), **New Relic** (Claude Code OpenTelemetry usage/cost, change-failure signals), and **SonarQube** (new-code quality gate). Adding a source is a subclass + registration.
- **In-app surveys** — DX Core 4 quarterly, DXI-lite (14 drivers), and pulse checks. **Anonymous by construction** — responses carry no link to the respondent.
- **Baseline capture** — freeze your "before AI" numbers in one click; every chart shows the delta against it.
- **Guardrails enforced in code** — no per-individual view exists; aggregates render only when a team has at least *N* contributing members (default 5); speed metrics render only beside their paired quality metric.
- **ROI reporting** — worked net-time-gain and payback math, always shown next to the objective throughput cross-check.

## Architecture

```
Celery Beat ─► Collectors ─► MetricSnapshot (Postgres time-series) ─► Dashboards
   (weekly)     GitHub          ▲                                       (HTMX + Chart.js)
                New Relic        │
                SonarQube    Surveys ─► aggregated answers
```

Django 6 monolith (server-rendered, HTMX + Chart.js + Bootstrap 5 — no SPA build step). Six domain apps:

| App | Responsibility |
|---|---|
| `teams` | Teams, memberships/roles, per-provider integration config (credentials encrypted at rest) |
| `metrics` | Metric catalog + `MetricSnapshot` time-series + versioned `Baseline` |
| `collectors` | Pluggable collector framework, Celery tasks, run logging |
| `surveys` | Anonymous tokenized surveys, aggregation into metric snapshots |
| `dashboards` | Guardrailed aggregation + DX Core 4 / Utilization / Impact / Cost views |
| `reports` | ROI calculator + monthly leadership report |

Full design: [`docs/specs/2026-07-16-ai-visibility-design.md`](docs/specs/2026-07-16-ai-visibility-design.md).

## Quickstart (local, Docker)

Prerequisites: Docker + Docker Compose.

```bash
git clone https://github.com/huwaizatahir2/ai-visibility.git
cd ai-visibility

# Generate a field-encryption key and put it in .envs/.local/.django (FIELD_ENCRYPTION_KEY)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

docker compose -f docker-compose.local.yml build
docker compose -f docker-compose.local.yml up -d
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
docker compose -f docker-compose.local.yml run --rm django python manage.py createsuperuser
```

App: <http://localhost:8000> · Mailpit (emails): <http://localhost:8025>

Run the tests:

```bash
docker compose -f docker-compose.local.yml run --rm django pytest
```

## Configuration

Environment variables (local values live in `.envs/.local/`; **production uses separate secrets** — see the deployment strategy):

| Variable | Purpose |
|---|---|
| `FIELD_ENCRYPTION_KEY` | Fernet key encrypting integration credentials at rest. **Generate a fresh one per environment.** |
| `ALLOWED_OAUTH_DOMAINS` | Comma-separated email-domain allowlist for Google sign-in. Empty = open (OSS default). |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_SECRET` | Google OAuth app credentials (leave blank to disable Google login). |
| `DATABASE_URL`, `REDIS_URL`, `DJANGO_SECRET_KEY`, … | Standard cookiecutter-django settings. |

> The `.envs/.local/*` files are committed (dev-only convenience, per cookiecutter). They contain **local** throwaway secrets only. Never reuse them in production — production secrets are rendered from Ansible Vault (see below).

## Enabling Claude Code telemetry (the usage/cost half)

Claude Code emits OpenTelemetry metrics. Point them at New Relic (native OTLP), and AI Visibility's New Relic collector pulls weekly aggregates. Add to each developer's shell profile or managed settings:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.nr-data.net:4317
export OTEL_EXPORTER_OTLP_HEADERS="api-key=<YOUR_NEW_RELIC_INGEST_KEY>"
```

Then add the team's New Relic account id + query key on the team's integration page. (Exact `claude_code.*` metric names evolve — verify against current Claude Code monitoring docs.)

## Adding a collector

Collectors are auto-registered plugins. Subclass `BaseCollector`, declare the metrics it produces, implement `collect()`, and register it:

```python
from ai_visibility.collectors.base import BaseCollector, MetricValue, register
from decimal import Decimal

@register
class MyCollector(BaseCollector):
    provider = "mysource"
    metrics_produced = ["pr_throughput"]

    def collect(self, period_start, period_end):
        return [MetricValue("pr_throughput", Decimal("42"))]
```

The scheduled task and dashboards pick it up automatically once the team enables a `mysource` integration.

## Guardrails (please read before adapting)

These are deliberate and enforced in code, not just policy:

- **Team-level aggregation only.** No view, query, or export exposes per-individual metrics. Ranking individuals turns the metric into a target and corrupts the data (Goodhart's law).
- **Minimum group size.** Aggregates are withheld below a configurable member count (default 5).
- **Baseline first.** Capture the pre-AI baseline before heavy adoption — it's the one irreversible measurement.
- **Pair every metric.** Speed without quality is a trap; the UI enforces the pairing.

## Deployment

One instance per organization, many teams per instance. Provisioned with **Terraform** (AWS EC2 + RDS Postgres), configured and deployed with **Ansible**. See:

- [`docs/DEPLOYMENT-STRATEGY.md`](docs/DEPLOYMENT-STRATEGY.md) — the strategy and rationale
- [`infra/`](infra/) — Terraform module + Ansible playbooks

## Documentation

- [Measurement plan](ai-productivity-measurement-plan.md) — the framework this implements
- [Design spec](docs/specs/2026-07-16-ai-visibility-design.md)
- [Implementation plan](docs/plans/2026-07-16-ai-visibility-implementation.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT — see [LICENSE](LICENSE).
