# Contributing to AI Visibility

Thanks for your interest. This project is built to be adopted and extended by teams beyond its origin — collectors for new tools, survey templates, and dashboard views are all welcome.

## Ground rules

- **Never weaken the privacy guardrails.** Team-level aggregation, minimum group size, survey anonymity, and metric pairing are load-bearing. PRs that expose per-individual metrics will not be merged.
- **Test-driven.** Write a failing test first, then the implementation. External APIs are mocked with [`responses`](https://github.com/getsentry/responses) — no live network in tests.
- **DRY, YAGNI.** Build what's needed, follow existing patterns.

## Development setup

Everything runs in Docker; you don't need a local Python environment.

```bash
docker compose -f docker-compose.local.yml build
docker compose -f docker-compose.local.yml up -d
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
```

Set `FIELD_ENCRYPTION_KEY` in `.envs/.local/.django` first (see README quickstart).

## The loop

```bash
# run tests
docker compose -f docker-compose.local.yml run --rm django pytest

# lint + format (must pass before commit)
docker compose -f docker-compose.local.yml run --rm --no-deps django ruff check .
docker compose -f docker-compose.local.yml run --rm --no-deps django ruff format .
```

CI runs the same checks plus a coverage gate on the domain apps.

## Adding a collector

See the "Adding a collector" section in the [README](README.md#adding-a-collector). Subclass `BaseCollector`, register it, and add a test that feeds a mocked API payload and asserts the exact `MetricValue`s produced (including idempotency).

## Commit style

Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`). Keep the subject under ~50 characters; explain the *why* in the body when it isn't obvious.

## Pull requests

1. Branch from `main`.
2. Keep the change focused; one concern per PR.
3. Ensure tests + ruff pass locally.
4. Describe what changed and why, and note any guardrail-relevant considerations.
