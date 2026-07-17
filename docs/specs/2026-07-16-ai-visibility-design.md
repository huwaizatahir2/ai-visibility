# ai-visibility — Design Spec

**Date:** 2026-07-16
**Status:** Approved
**Repo:** `ai-visibility` (public, MIT)
**Source plan:** [`ai-productivity-measurement-plan.md`](../../ai-productivity-measurement-plan.md)

## 1. Purpose

Self-hosted Django platform that measures the impact of AI coding tools (Claude Code first) on developer productivity, implementing the DX Utilization / Impact / Cost framework. Built for the xiangqi team at Arbisoft, multi-tenant from day 1 so other teams onboard onto the same instance. Open source so any org can run it.

The platform answers three questions, always paired so no metric is reported alone:

1. **Utilization** — are devs actually using the AI tool?
2. **Impact** — is it improving speed, quality, and developer experience?
3. **Cost** — does time saved beat what we spend?

## 2. Decisions (settled during brainstorming)

| Decision | Choice |
|---|---|
| App scope | Full platform: collectors + storage + surveys + dashboards + reports in one app |
| Tenancy | Multi-tenant day 1 — one deployment, many teams, per-team integration config |
| Frontend | Django templates + HTMX + Chart.js + Tailwind (no SPA) |
| Claude Code telemetry | Devs export OTel → New Relic (native OTLP); Django pulls aggregates via NRQL API |
| Deployment | AWS EC2 + Docker Compose; Terraform provisions, Ansible deploys |
| Boilerplate | cookiecutter-django, cruft stripped in first commits |
| Auth | django-allauth: Google OAuth (env-configurable domain restriction) + password fallback |
| License / name | MIT / `ai-visibility` |

## 3. Stack

- **Python 3.12, Django 5.x** (whatever current cookiecutter-django pins)
- **PostgreSQL 16** — relational + metric time-series (no separate TSDB at this scale)
- **Celery + Celery Beat + Redis** — scheduled collectors, async jobs
- **HTMX + Chart.js + Tailwind CSS** — server-rendered dashboards
- **django-allauth** — Google OAuth + password
- **Ruff** — lint + format; **pytest-django + factory-boy + responses** — tests; **pre-commit**; **GitHub Actions** CI
- **Docker Compose** — django, celeryworker, celerybeat, redis, postgres (local), traefik/nginx (prod)

## 4. Architecture — Django apps

### 4.1 `teams`
- `Team` — name, slug, settings JSON (min aggregation size, loaded hourly cost for ROI, timezone).
- `Membership` — user ↔ team, role: `org_admin` | `team_lead` | `member`.
- `IntegrationConfig` — per team, per provider (`github`, `newrelic`, `sonarqube`, `jira`, `anthropic`): endpoint, credentials (encrypted at rest via `django-cryptography`-style encrypted fields or Fernet-encrypted JSON), provider-specific config (repo list, NR account id, Sonar project key).
- All domain models carry `team` FK; all querysets team-scoped through a manager. No cross-team data leaks.

### 4.2 `metrics`
- `MetricDefinition` — catalog seeded from the measurement plan §3 via data migration/fixture: key (e.g. `pr_throughput`, `wau`, `cc_cost_usd`), dimension (`utilization` | `impact_speed` | `impact_quality` | `impact_experience` | `cost`), unit, direction (higher-better / lower-better), description, `paired_with` (FK — the counterweight metric, e.g. `pr_throughput` ↔ `pr_revert_rate`).
- `MetricSnapshot` — team FK, metric FK, `period_start`, `period_end`, `granularity` (`daily` | `weekly` | `per_release` | `quarterly`), `value` (decimal), `dimensions` JSONB (e.g. `{"repo": "xiangqi-server"}`), `source` (`system` | `survey` | `manual`), unique on (team, metric, period_start, granularity, dimensions-hash).
- `Baseline` — team FK, frozen set of snapshot values + `captured_at`. One-click capture; dashboards compute deltas against it. Immutable once captured (new capture = new version, old kept).

### 4.3 `collectors`
Pluggable framework:

- `BaseCollector` abstract class: `provider`, `metrics_produced`, `collect(team, period) -> list[MetricValue]`. Registry pattern — adding a collector = subclass + register, no core changes.
- `CollectorRun` — team, collector, status (`success` | `failed` | `partial`), started/finished, error text, snapshots written. Powers data-freshness UI and admin alerting.
- Celery beat schedules (per team, respecting each team's enabled integrations):
  - **GitHubCollector** (weekly + on-demand): merged PR count/dev, PR cycle time (open→merge), revert rate (revert-commit detection + `Reverts #` parse), % AI-assisted PRs (parse `- [x] AI-assisted` checkbox from PR body template). GitHub REST API, PAT per team.
  - **NewRelicCollector** (weekly): NRQL queries against `claude_code.*` OTel metrics — WAU/DAU (unique `user.id` count, reported only as team % — never per-user), sessions, active time, lines of code, accept/reject rate, token + cost usage. Also CFR inputs: incident count + deployment markers.
  - **SonarQubeCollector** (weekly): new-code quality gate pass rate, new bugs/smells/coverage on the team's project.
  - **JiraCollector** — phase 2 (issue throughput, lead time on work items). Interface designed now, implemented later.
- Retries: Celery autoretry with exponential backoff, max 3; failure past retries → `CollectorRun.failed` + email to org admins.
- All HTTP mocked in tests with `responses`; recorded fixtures per provider.

### 4.4 `surveys`
- `SurveyTemplate` — seeded: **DX Core 4 quarterly** (perceived delivery, maintainability, change confidence, satisfaction, hours saved, % feature-vs-toil), **DXI-lite** (14 drivers, 1–5), **pulse** (1–2 questions).
- `SurveyRun` — template × team × window (opens/closes), unique tokenized links per member (token proves membership, response stored **without user FK** — anonymous by construction; token single-use, marked consumed separately from the response row).
- `Response` / `Answer` — Likert + numeric + percent types.
- Response-rate tracking (consumed tokens ÷ issued) surfaces KR3 (≥80%) without identifying who answered what.
- Numeric answers (hours saved, % toil) aggregate into `MetricSnapshot` rows (`source=survey`) on run close — surveys and system data land in one store.
- Delivery: emailed links (SMTP/console backend); Slack webhook optional later.

### 4.5 `dashboards`
Server-rendered, HTMX partial refresh, Chart.js:

- **Overview / DX Core 4** — the 5 headline numbers (PR throughput, perceived delivery, DXI-lite, maintainability, change fail %) each vs baseline delta. The OKR view.
- **Utilization** — WAU/DAU %, % AI-assisted PRs, accept rate, sessions/active time trends. Benchmarks annotated (60–70% WAU mature-org line).
- **Impact** — speed metrics rendered **beside their paired quality counterweight** (golden rule enforced by template structure: a speed chart component requires its `paired_with` metric and renders both).
- **Cost / ROI** — spend trend, net time gain, ROI multiple with worked math shown.
- Every panel: data-freshness badge from latest `CollectorRun`; stale (> expected cadence × 1.5) shows warning.
- **Guardrail in code:** no view, queryset, or export exposes per-individual metrics. Aggregates render only when the team's contributing member count ≥ `Team.min_aggregation_size` (default 5); below threshold panel shows "group too small" instead of numbers.

### 4.6 `reports`
- ROI calculator implementing plan §7: inputs (devs, survey hours-saved, loaded hourly cost, spend from `cc_cost_usd`) → value of time saved, net gain, ROI multiple, payback. Always displayed with the same-engineer throughput cross-check trend beside it.
- Monthly leadership report: 1-page HTML (print-to-PDF friendly) — headline five, deltas vs baseline, guardrail status (revert rate / CFR / Sonar gate vs baseline = KR5), response rates.

## 5. Data flow

```
Celery Beat (per-team schedule)
  → Collector.collect() pulls provider API
  → normalize → MetricSnapshot upsert (idempotent per period)
  → CollectorRun logged
Survey close → numeric aggregates → MetricSnapshot (source=survey)
Dashboards → team-scoped aggregate queries → Chart.js JSON
Reports → snapshots + baseline → ROI math → HTML
```

Idempotency: collectors upsert on the unique snapshot key — re-running a period overwrites, never duplicates.

## 6. Auth & permissions

- allauth: Google provider + local accounts. `SOCIALACCOUNT_ALLOWED_DOMAINS`-style env (`ALLOWED_OAUTH_DOMAINS=arbisoft.com`) — empty = open (OSS default).
- Roles: **org_admin** (manage teams, integrations, capture baselines), **team_lead** (run surveys, view own team dashboards, edit team settings), **member** (view own team dashboards, answer surveys).
- Django admin restricted to org_admins; integration credentials write-only in UI (never redisplayed).

## 7. Error handling

- Collector failures: retry ×3 exp backoff → `CollectorRun.failed` → admin email. Partial data marked `partial`, dashboard badge reflects it.
- Provider credential errors surface as actionable messages on the team integrations page ("GitHub token expired").
- Survey link reuse → friendly "already submitted" page.
- All external calls timeout-bounded (10 s connect / 30 s read).

## 8. Testing

- pytest-django, factory-boy factories per model, `responses` for all provider HTTP.
- Collector tests: fixture payload → expected snapshots (value + idempotency).
- Guardrail tests are first-class: min-aggregation blocks, anonymity (no join path from Response to user), team scoping (user of team A gets 404 on team B URLs).
- ROI math property tests against §7 worked example.
- CI: Ruff (lint + format check) → pytest → docker build. Target ≥85% coverage on domain apps.

## 9. Deployment (summary — full strategy in separate doc)

- `infra/terraform/` — module: VPC, EC2 t3.small, RDS Postgres 16, security groups, Elastic IP, S3 backend for state. One workspace per org deployment.
- `infra/ansible/` — playbooks: bootstrap (docker install, user, firewall), deploy (pull image tag, env render from vault, compose up, migrate, healthcheck), rollback.
- GitHub Actions: CI on PR; on tag — build/push image (GHCR) → Ansible deploy.
- New Arbisoft team = row in `teams` (same instance). New org = new Terraform workspace.
- Full runbook: `docs/DEPLOYMENT.md`.

## 10. Out of scope (v1)

- Slack bot delivery, per-PR complexity adjustment, real DXI licensing, GitLab/other VCS collectors (pluggable interface makes them contributions), Grafana embedding.

**Now implemented (originally deferred):** the Jira collector (work-item throughput + lead time) and `change_failure_rate` / `lead_time_hours` via New Relic Change Tracking deployments + incidents.

## 11. Success criteria

Maps to plan §9 OKR: baseline capture + DX Core 4 dashboard live (KR1), WAU tracking (KR2), survey with response-rate ≥80% measurable (KR3), ROI report generatable (KR4), quality guardrail panel (KR5).
