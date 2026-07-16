# ai-visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ai-visibility platform — a multi-tenant Django app that measures AI coding-tool impact (Utilization / Impact / Cost) via scheduled collectors (GitHub, New Relic, SonarQube), in-app surveys, guardrailed dashboards, and ROI reports.

**Architecture:** Django 5 monolith from cookiecutter-django. Six domain apps (`teams`, `metrics`, `collectors`, `surveys`, `dashboards`, `reports`). Celery beat runs pluggable collectors that upsert `MetricSnapshot` time-series rows in Postgres; surveys aggregate into the same store; HTMX + Chart.js dashboards render team-scoped aggregates with min-group and metric-pairing guardrails enforced in code.

**Tech Stack:** Python 3.12, Django 5.x, PostgreSQL 16, Celery + Beat + Redis, django-allauth (Google + password), HTMX, Chart.js, Tailwind (django-tailwind-cli), Ruff, pytest-django, factory-boy, responses, Docker Compose, Terraform + Ansible.

**Spec:** `docs/specs/2026-07-16-ai-visibility-design.md`

**Conventions used throughout:**
- Project slug: `ai_visibility`. Domain apps live in `ai_visibility/<app>/`.
- All tests under `ai_visibility/<app>/tests/`. Run inside docker: `docker compose -f docker-compose.local.yml run --rm django pytest <path> -v` — abbreviated below as `dj-pytest <path>`. Define shell alias first:
  `alias dj-pytest='docker compose -f docker-compose.local.yml run --rm django pytest'`
- Commit after every green test. Ruff must pass before each commit (`pre-commit run -a`).

---

## Phase 0 — Scaffold & repo

### Task 1: Generate cookiecutter-django and merge into repo

**Files:**
- Create: entire project skeleton at repo root (merged from cookiecutter output)

- [ ] **Step 1: Generate skeleton in scratchpad**

```bash
cd "$SCRATCHPAD"   # session scratchpad dir
pipx run cookiecutter gh:cookiecutter/cookiecutter-django --no-input \
  project_name="AI Visibility" \
  project_slug="ai_visibility" \
  description="Self-hosted platform measuring AI coding-tool impact on developer productivity (DX Utilization/Impact/Cost framework)." \
  author_name="Huwaiza Tahir" \
  email="muhammadhuwaizatahir@gmail.com" \
  domain_name="example.com" \
  open_source_license="MIT" \
  username_type="email" \
  timezone="Asia/Karachi" \
  use_docker=y \
  postgresql_version="16" \
  cloud_provider="None" \
  mail_service="Other SMTP" \
  use_async=n \
  use_drf=n \
  frontend_pipeline="None" \
  use_celery=y \
  use_mailpit=y \
  use_sentry=n \
  use_whitenoise=y \
  use_heroku=n \
  ci_tool="Github" \
  keep_local_envs_in_vcs=y \
  debug=n
```
(Option names drift between cookiecutter-django releases — if a prompt errors, run interactively and pick the equivalents.)

- [ ] **Step 2: Merge into repo root (repo already has `.git`, `docs/`, plan md)**

```bash
rsync -a "$SCRATCHPAD/ai_visibility/" /Users/huwaiza.tahir/work/projects/ai-visibility/
cd /Users/huwaiza.tahir/work/projects/ai-visibility
```

- [ ] **Step 3: Boot check**

```bash
docker compose -f docker-compose.local.yml build
docker compose -f docker-compose.local.yml up -d
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/   # expect 200
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "chore: scaffold project from cookiecutter-django"
```

### Task 2: Strip cruft, wire Tailwind + HTMX, verify tooling

**Files:**
- Delete: unused cookiecutter extras (docs/ from cookiecutter if generated, unneeded pages)
- Modify: `config/settings/base.py`, `requirements/base.txt` (or `requirements.txt` layout cookiecutter provides), `ai_visibility/templates/base.html`

- [ ] **Step 1: Add deps**

Append to `requirements/base.txt`:
```
django-tailwind-cli==2.*
django-htmx==1.*
cryptography>=42
```

- [ ] **Step 2: Settings**

In `config/settings/base.py` add to `THIRD_PARTY_APPS`: `"django_tailwind_cli"`, `"django_htmx"`; add `"django_htmx.middleware.HtmxMiddleware"` to `MIDDLEWARE`; add:
```python
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY")  # Fernet key, generated per env
```
Add `FIELD_ENCRYPTION_KEY` to `.envs/.local/.django` (generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).

- [ ] **Step 3: Base template** — add to `base.html` `<head>`:
```html
{% load tailwind_cli %} {% tailwind_css %}
<script src="{% static 'js/htmx.min.js' %}" defer></script>
<script src="{% static 'js/chart.umd.min.js' %}" defer></script>
```
Vendor htmx + Chart.js into `ai_visibility/static/js/` (download pinned versions; no CDN — self-contained deploys).

- [ ] **Step 4: Verify lint + tests + rebuild**

```bash
docker compose -f docker-compose.local.yml build django
pre-commit run -a          # ruff lint+format clean
dj-pytest                  # cookiecutter's user tests pass
```

- [ ] **Step 5: Commit** — `git commit -m "chore: add htmx, tailwind, chart.js, field encryption key"`

### Task 3: README, CONTRIBUTING, GitHub publish

**Files:**
- Create: `README.md` (overview, screenshots placeholder, quickstart, architecture diagram, metric catalog table, guardrails section), `CONTRIBUTING.md`, `LICENSE` (MIT — cookiecutter generates), `.github/ISSUE_TEMPLATE/`

- [ ] **Step 1: Write README.md** — sections: What/Why (3 questions framework), Features, Quickstart (docker compose), Configuration (env table incl. `ALLOWED_OAUTH_DOMAINS`, `FIELD_ENCRYPTION_KEY`), Enabling Claude Code OTel → New Relic (copy §5 of measurement plan), Architecture, Adding a collector (plugin how-to), Guardrails (team-level only, min group size), License.
- [ ] **Step 2: Create public repo + push**

```bash
gh auth status                 # verify account first
gh repo create ai-visibility --public --source=. \
  --description "Measure AI coding-tool impact on developer productivity — Utilization / Impact / Cost dashboards, surveys, ROI." \
  --push
```

- [ ] **Step 3: Commit remaining docs** — `git add -A && git commit -m "docs: README, contributing, issue templates" && git push`

---

## Phase 1 — `teams` app

### Task 4: Team + Membership models

**Files:**
- Create: `ai_visibility/teams/` app (`python manage.py startapp` relocated per cookiecutter layout), `ai_visibility/teams/models.py`, `ai_visibility/teams/tests/test_models.py`, `ai_visibility/teams/factories.py`
- Modify: `config/settings/base.py` (`LOCAL_APPS += ["ai_visibility.teams"]`)

- [ ] **Step 1: Failing test**

```python
# ai_visibility/teams/tests/test_models.py
import pytest
from django.db import IntegrityError
from ai_visibility.teams.factories import MembershipFactory, TeamFactory

pytestmark = pytest.mark.django_db


def test_team_defaults():
    team = TeamFactory()
    assert team.min_aggregation_size == 5
    assert str(team) == team.name


def test_membership_unique_per_user_team():
    m = MembershipFactory()
    with pytest.raises(IntegrityError):
        MembershipFactory(user=m.user, team=m.team)
```

```python
# ai_visibility/teams/factories.py
import factory
from ai_visibility.teams import models
from ai_visibility.users.tests.factories import UserFactory


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Team
    name = factory.Sequence(lambda n: f"Team {n}")
    slug = factory.Sequence(lambda n: f"team-{n}")


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Membership
    user = factory.SubFactory(UserFactory)
    team = factory.SubFactory(TeamFactory)
```

- [ ] **Step 2: Run — expect FAIL (models missing)** — `dj-pytest ai_visibility/teams -v`
- [ ] **Step 3: Implement**

```python
# ai_visibility/teams/models.py
from django.conf import settings
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    min_aggregation_size = models.PositiveSmallIntegerField(default=5)
    loaded_hourly_cost_usd = models.DecimalField(max_digits=8, decimal_places=2, default=40)
    timezone = models.CharField(max_length=64, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        ORG_ADMIN = "org_admin", "Org admin"
        TEAM_LEAD = "team_lead", "Team lead"
        MEMBER = "member", "Member"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "team"], name="uniq_membership")]
```

- [ ] **Step 4: Migrate + run — expect PASS** — `docker compose -f docker-compose.local.yml run --rm django python manage.py makemigrations teams && dj-pytest ai_visibility/teams -v`
- [ ] **Step 5: Commit** — `git commit -am "feat(teams): Team and Membership models"`

### Task 5: IntegrationConfig with encrypted credentials

**Files:**
- Modify: `ai_visibility/teams/models.py`, `ai_visibility/teams/factories.py`
- Test: `ai_visibility/teams/tests/test_integrations.py`

- [ ] **Step 1: Failing test**

```python
# ai_visibility/teams/tests/test_integrations.py
import pytest
from ai_visibility.teams.factories import IntegrationConfigFactory

pytestmark = pytest.mark.django_db


def test_credentials_roundtrip_and_encrypted_at_rest():
    ic = IntegrationConfigFactory(provider="github")
    ic.set_credentials({"token": "ghp_secret"})
    ic.save()
    ic.refresh_from_db()
    assert ic.get_credentials() == {"token": "ghp_secret"}
    assert "ghp_secret" not in ic._credentials  # ciphertext only


def test_empty_credentials_returns_empty_dict():
    ic = IntegrationConfigFactory(provider="sonarqube")
    assert ic.get_credentials() == {}
```

- [ ] **Step 2: Run — FAIL** — `dj-pytest ai_visibility/teams/tests/test_integrations.py -v`
- [ ] **Step 3: Implement** (append to `teams/models.py`; factory: `team = SubFactory(TeamFactory)`, `provider = "github"`)

```python
import json
from cryptography.fernet import Fernet


class IntegrationConfig(models.Model):
    class Provider(models.TextChoices):
        GITHUB = "github", "GitHub"
        NEWRELIC = "newrelic", "New Relic"
        SONARQUBE = "sonarqube", "SonarQube"
        JIRA = "jira", "Jira"
        ANTHROPIC = "anthropic", "Anthropic"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="integrations")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)  # non-secret: repos, account ids, project keys
    _credentials = models.TextField(blank=True, default="", db_column="credentials")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["team", "provider"], name="uniq_team_provider")]

    def _fernet(self) -> Fernet:
        from django.conf import settings
        return Fernet(settings.FIELD_ENCRYPTION_KEY)

    def set_credentials(self, data: dict) -> None:
        self._credentials = self._fernet().encrypt(json.dumps(data).encode()).decode()

    def get_credentials(self) -> dict:
        if not self._credentials:
            return {}
        return json.loads(self._fernet().decrypt(self._credentials.encode()))
```

- [ ] **Step 4: Migrate + run — PASS**
- [ ] **Step 5: Commit** — `git commit -am "feat(teams): per-provider integration config with Fernet-encrypted credentials"`

### Task 6: Team scoping helpers

**Files:**
- Create: `ai_visibility/teams/access.py`
- Test: `ai_visibility/teams/tests/test_access.py`

- [ ] **Step 1: Failing test**

```python
# ai_visibility/teams/tests/test_access.py
import pytest
from ai_visibility.teams.access import teams_for, require_team_member
from ai_visibility.teams.factories import MembershipFactory, TeamFactory
from django.core.exceptions import PermissionDenied

pytestmark = pytest.mark.django_db


def test_teams_for_returns_only_member_teams():
    m = MembershipFactory()
    TeamFactory()  # other team
    assert list(teams_for(m.user)) == [m.team]


def test_require_team_member_denies_outsider():
    m = MembershipFactory()
    outsider = MembershipFactory().user
    with pytest.raises(PermissionDenied):
        require_team_member(outsider, m.team)
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# ai_visibility/teams/access.py
from django.core.exceptions import PermissionDenied
from .models import Membership, Team


def teams_for(user):
    return Team.objects.filter(memberships__user=user)


def require_team_member(user, team: Team) -> Membership:
    membership = Membership.objects.filter(user=user, team=team).first()
    if membership is None:
        raise PermissionDenied("Not a member of this team")
    return membership


def require_role(user, team: Team, *roles: str) -> Membership:
    membership = require_team_member(user, team)
    if membership.role not in roles:
        raise PermissionDenied("Insufficient role")
    return membership
```

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(teams): team scoping and role helpers"`

---

## Phase 2 — `metrics` app

### Task 7: MetricDefinition + seeded catalog

**Files:**
- Create: `ai_visibility/metrics/models.py`, `ai_visibility/metrics/migrations/0002_seed_catalog.py` (data migration), `ai_visibility/metrics/tests/test_definitions.py`
- Modify: `config/settings/base.py` (LOCAL_APPS)

- [ ] **Step 1: Failing test**

```python
# ai_visibility/metrics/tests/test_definitions.py
import pytest
from ai_visibility.metrics.models import MetricDefinition

pytestmark = pytest.mark.django_db


def test_catalog_seeded_with_paired_metrics():
    pr = MetricDefinition.objects.get(key="pr_throughput")
    assert pr.dimension == MetricDefinition.Dimension.IMPACT_SPEED
    assert pr.paired_with.key == "pr_revert_rate"  # golden rule pairing
    assert MetricDefinition.objects.count() >= 15
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement model**

```python
# ai_visibility/metrics/models.py
from django.db import models


class MetricDefinition(models.Model):
    class Dimension(models.TextChoices):
        UTILIZATION = "utilization"
        IMPACT_SPEED = "impact_speed"
        IMPACT_QUALITY = "impact_quality"
        IMPACT_EXPERIENCE = "impact_experience"
        COST = "cost"

    class Direction(models.TextChoices):
        HIGHER_BETTER = "higher"
        LOWER_BETTER = "lower"

    key = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    dimension = models.CharField(max_length=20, choices=Dimension.choices)
    unit = models.CharField(max_length=30)  # "count", "hours", "%", "usd", "score_1_5"
    direction = models.CharField(max_length=10, choices=Direction.choices, default=Direction.HIGHER_BETTER)
    description = models.TextField(blank=True)
    paired_with = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self) -> str:
        return self.key
```

- [ ] **Step 4: Data migration seeding catalog** (from measurement plan §3; pairings: `pr_throughput↔pr_revert_rate`, `pr_cycle_time_hours↔sonar_gate_passed`, `cc_lines_of_code↔change_failure_rate`):

Keys to seed — utilization: `cc_wau_pct`, `cc_dau_pct`, `pct_ai_assisted_prs`, `cc_accept_rate`, `cc_active_hours`, `cc_sessions`; impact_speed: `pr_throughput`, `pr_cycle_time_hours`, `lead_time_hours`, `perceived_delivery`; impact_quality: `pr_revert_rate`, `change_failure_rate`, `code_maintainability`, `sonar_gate_passed`, `sonar_new_bugs`; impact_experience: `ai_satisfaction`, `change_confidence`, `pct_feature_work`, `hours_saved_week`, `dxi_lite`; cost: `cc_cost_usd`. Migration uses `MetricDefinition.objects.update_or_create(key=..., defaults=...)` loop over a `CATALOG` list literal; second pass sets `paired_with`.

- [ ] **Step 5: Run — PASS**  |  **Step 6: Commit** — `git commit -am "feat(metrics): metric definition catalog seeded from measurement plan"`

### Task 8: MetricSnapshot with idempotent upsert

**Files:**
- Modify: `ai_visibility/metrics/models.py`
- Create: `ai_visibility/metrics/services.py`
- Test: `ai_visibility/metrics/tests/test_snapshots.py`

- [ ] **Step 1: Failing test**

```python
# ai_visibility/metrics/tests/test_snapshots.py
import datetime as dt
from decimal import Decimal
import pytest
from ai_visibility.metrics.models import MetricSnapshot
from ai_visibility.metrics.services import upsert_snapshot
from ai_visibility.teams.factories import TeamFactory

pytestmark = pytest.mark.django_db
WEEK = (dt.date(2026, 7, 6), dt.date(2026, 7, 12))


def test_upsert_is_idempotent_per_period_and_dimensions():
    team = TeamFactory()
    upsert_snapshot(team=team, metric_key="pr_throughput", period_start=WEEK[0],
                    period_end=WEEK[1], granularity="weekly", value=Decimal("12"))
    upsert_snapshot(team=team, metric_key="pr_throughput", period_start=WEEK[0],
                    period_end=WEEK[1], granularity="weekly", value=Decimal("14"))
    snaps = MetricSnapshot.objects.filter(team=team)
    assert snaps.count() == 1
    assert snaps.get().value == Decimal("14")


def test_different_dimensions_create_separate_rows():
    team = TeamFactory()
    for repo in ("a", "b"):
        upsert_snapshot(team=team, metric_key="pr_throughput", period_start=WEEK[0],
                        period_end=WEEK[1], granularity="weekly", value=Decimal("1"),
                        dimensions={"repo": repo})
    assert MetricSnapshot.objects.filter(team=team).count() == 2
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# append to ai_visibility/metrics/models.py
class MetricSnapshot(models.Model):
    class Granularity(models.TextChoices):
        DAILY = "daily"
        WEEKLY = "weekly"
        PER_RELEASE = "per_release"
        QUARTERLY = "quarterly"

    class Source(models.TextChoices):
        SYSTEM = "system"
        SURVEY = "survey"
        MANUAL = "manual"

    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="snapshots")
    metric = models.ForeignKey(MetricDefinition, on_delete=models.PROTECT)
    period_start = models.DateField()
    period_end = models.DateField()
    granularity = models.CharField(max_length=15, choices=Granularity.choices)
    value = models.DecimalField(max_digits=14, decimal_places=4)
    dimensions = models.JSONField(default=dict, blank=True)
    dimensions_hash = models.CharField(max_length=64, editable=False)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.SYSTEM)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["team", "metric", "period_start", "granularity", "dimensions_hash"],
            name="uniq_snapshot_period")]
        indexes = [models.Index(fields=["team", "metric", "period_start"])]
```

```python
# ai_visibility/metrics/services.py
import hashlib
import json
from ai_visibility.metrics.models import MetricDefinition, MetricSnapshot


def dimensions_hash(dimensions: dict) -> str:
    return hashlib.sha256(json.dumps(dimensions, sort_keys=True).encode()).hexdigest()


def upsert_snapshot(*, team, metric_key, period_start, period_end, granularity,
                    value, dimensions=None, source=MetricSnapshot.Source.SYSTEM) -> MetricSnapshot:
    dimensions = dimensions or {}
    metric = MetricDefinition.objects.get(key=metric_key)
    obj, _created = MetricSnapshot.objects.update_or_create(
        team=team, metric=metric, period_start=period_start,
        granularity=granularity, dimensions_hash=dimensions_hash(dimensions),
        defaults={"period_end": period_end, "value": value,
                  "dimensions": dimensions, "source": source},
    )
    return obj
```

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(metrics): idempotent MetricSnapshot time-series upsert"`

### Task 9: Baseline capture

**Files:**
- Modify: `ai_visibility/metrics/models.py`, `ai_visibility/metrics/services.py`
- Test: `ai_visibility/metrics/tests/test_baseline.py`

- [ ] **Step 1: Failing test**

```python
# ai_visibility/metrics/tests/test_baseline.py
import datetime as dt
from decimal import Decimal
import pytest
from ai_visibility.metrics.services import capture_baseline, upsert_snapshot
from ai_visibility.teams.factories import TeamFactory

pytestmark = pytest.mark.django_db


def test_capture_freezes_latest_value_per_metric_and_versions():
    team = TeamFactory()
    for week, val in ((dt.date(2026, 6, 29), "10"), (dt.date(2026, 7, 6), "12")):
        upsert_snapshot(team=team, metric_key="pr_throughput", period_start=week,
                        period_end=week + dt.timedelta(days=6), granularity="weekly",
                        value=Decimal(val))
    b1 = capture_baseline(team)
    assert b1.values["pr_throughput"] == "12.0000"
    b2 = capture_baseline(team)
    assert b2.version == b1.version + 1  # old baseline kept, immutable
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# append to models.py
class Baseline(models.Model):
    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="baselines")
    version = models.PositiveIntegerField()
    captured_at = models.DateTimeField(auto_now_add=True)
    values = models.JSONField()  # {metric_key: str(value)} — latest snapshot per metric at capture time

    class Meta:
        constraints = [models.UniqueConstraint(fields=["team", "version"], name="uniq_baseline_version")]
```

```python
# append to services.py
from django.db.models import Max
from ai_visibility.metrics.models import Baseline


def capture_baseline(team) -> Baseline:
    latest = {}
    for snap in (MetricSnapshot.objects.filter(team=team)
                 .order_by("metric__key", "-period_start")
                 .distinct("metric__key")):
        latest[snap.metric.key] = str(snap.value)
    version = (Baseline.objects.filter(team=team).aggregate(m=Max("version"))["m"] or 0) + 1
    return Baseline.objects.create(team=team, version=version, values=latest)
```

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(metrics): versioned immutable baseline capture"`

---

## Phase 3 — `collectors` app

### Task 10: BaseCollector, registry, CollectorRun

**Files:**
- Create: `ai_visibility/collectors/base.py`, `ai_visibility/collectors/models.py`, `ai_visibility/collectors/tests/test_base.py`
- Modify: LOCAL_APPS

- [ ] **Step 1: Failing test**

```python
# ai_visibility/collectors/tests/test_base.py
from decimal import Decimal
from ai_visibility.collectors.base import REGISTRY, BaseCollector, MetricValue, register


def test_register_adds_collector_to_registry():
    @register
    class FakeCollector(BaseCollector):
        provider = "fake"
        metrics_produced = ["pr_throughput"]

        def collect(self, period_start, period_end):
            return [MetricValue("pr_throughput", Decimal("1"))]

    assert REGISTRY["fake"] is FakeCollector
    REGISTRY.pop("fake")
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# ai_visibility/collectors/base.py
import abc
import dataclasses
import datetime as dt
from decimal import Decimal


@dataclasses.dataclass
class MetricValue:
    metric_key: str
    value: Decimal
    dimensions: dict = dataclasses.field(default_factory=dict)


class BaseCollector(abc.ABC):
    provider: str
    metrics_produced: list[str]

    def __init__(self, team, integration):
        self.team = team
        self.integration = integration

    @abc.abstractmethod
    def collect(self, period_start: dt.date, period_end: dt.date) -> list[MetricValue]: ...


REGISTRY: dict[str, type[BaseCollector]] = {}


def register(cls: type[BaseCollector]) -> type[BaseCollector]:
    REGISTRY[cls.provider] = cls
    return cls
```

```python
# ai_visibility/collectors/models.py
from django.db import models


class CollectorRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running"
        SUCCESS = "success"
        PARTIAL = "partial"
        FAILED = "failed"

    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="collector_runs")
    provider = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    snapshots_written = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["team", "provider", "-started_at"])]
```

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(collectors): pluggable collector base, registry, run log"`

### Task 11: `run_collector` Celery task + beat schedule

**Files:**
- Create: `ai_visibility/collectors/tasks.py`, `ai_visibility/collectors/tests/test_tasks.py`
- Modify: `config/settings/base.py` (`CELERY_BEAT_SCHEDULE`)

- [ ] **Step 1: Failing test**

```python
# ai_visibility/collectors/tests/test_tasks.py
from decimal import Decimal
import pytest
from ai_visibility.collectors import tasks
from ai_visibility.collectors.base import BaseCollector, MetricValue, register, REGISTRY
from ai_visibility.collectors.models import CollectorRun
from ai_visibility.metrics.models import MetricSnapshot
from ai_visibility.teams.factories import IntegrationConfigFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def fake_collector():
    @register
    class Fake(BaseCollector):
        provider = "fake"
        metrics_produced = ["pr_throughput"]

        def collect(self, period_start, period_end):
            return [MetricValue("pr_throughput", Decimal("7"))]

    yield Fake
    REGISTRY.pop("fake")


def test_run_collector_writes_snapshots_and_logs_success(fake_collector):
    ic = IntegrationConfigFactory(provider="fake")
    tasks.run_collector(ic.team_id, "fake")
    run = CollectorRun.objects.get()
    assert run.status == CollectorRun.Status.SUCCESS
    assert run.snapshots_written == 1
    assert MetricSnapshot.objects.get().value == Decimal("7")


def test_run_collector_logs_failure_on_exception(fake_collector, monkeypatch):
    ic = IntegrationConfigFactory(provider="fake")
    monkeypatch.setattr(fake_collector, "collect", lambda self, s, e: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        tasks.run_collector(ic.team_id, "fake")
    assert CollectorRun.objects.get().status == CollectorRun.Status.FAILED
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# ai_visibility/collectors/tasks.py
import datetime as dt
from celery import shared_task
from django.utils import timezone
from ai_visibility.collectors import github, newrelic, sonarqube  # noqa: F401 — registers collectors
from ai_visibility.collectors.base import REGISTRY
from ai_visibility.collectors.models import CollectorRun
from ai_visibility.metrics.services import upsert_snapshot
from ai_visibility.teams.models import IntegrationConfig, Team


def last_full_week(today: dt.date | None = None) -> tuple[dt.date, dt.date]:
    today = today or timezone.localdate()
    start_of_this_week = today - dt.timedelta(days=today.weekday())
    start = start_of_this_week - dt.timedelta(days=7)
    return start, start + dt.timedelta(days=6)


@shared_task(bind=True, autoretry_for=(ConnectionError, TimeoutError),
             retry_backoff=True, max_retries=3)
def run_collector(self, team_id: int, provider: str) -> None:
    team = Team.objects.get(pk=team_id)
    integration = IntegrationConfig.objects.get(team=team, provider=provider, enabled=True)
    run = CollectorRun.objects.create(team=team, provider=provider)
    period_start, period_end = last_full_week()
    try:
        collector = REGISTRY[provider](team, integration)
        values = collector.collect(period_start, period_end)
        for mv in values:
            upsert_snapshot(team=team, metric_key=mv.metric_key, period_start=period_start,
                            period_end=period_end, granularity="weekly",
                            value=mv.value, dimensions=mv.dimensions)
        run.status = CollectorRun.Status.SUCCESS
        run.snapshots_written = len(values)
    except Exception as exc:
        run.status = CollectorRun.Status.FAILED
        run.error = str(exc)[:2000]
        raise
    finally:
        run.finished_at = timezone.now()
        run.save()


@shared_task
def run_all_collectors() -> None:
    for ic in IntegrationConfig.objects.filter(enabled=True, provider__in=REGISTRY):
        run_collector.delay(ic.team_id, ic.provider)
```

Beat schedule in `config/settings/base.py`:
```python
CELERY_BEAT_SCHEDULE = {
    "run-all-collectors-weekly": {
        "task": "ai_visibility.collectors.tasks.run_all_collectors",
        "schedule": crontab(minute=0, hour=6, day_of_week="mon"),
    },
}
```
(Note: `github.py`/`newrelic.py`/`sonarqube.py` don't exist yet — create empty modules now, filled by Tasks 12-14.)

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(collectors): celery run_collector task with run logging and weekly beat"`

### Task 12: GitHubCollector

**Files:**
- Create: `ai_visibility/collectors/github.py`, `ai_visibility/collectors/tests/test_github.py`, fixture JSON `ai_visibility/collectors/tests/fixtures/github_prs.json`

Config shape: `config={"repos": ["owner/repo1"]}`, credentials `{"token": "..."}`.
Metrics: `pr_throughput` (merged PR count), `pr_cycle_time_hours` (median open→merge), `pr_revert_rate` (title starts "Revert" ÷ total), `pct_ai_assisted_prs` (body contains `[x] AI-assisted`).

- [ ] **Step 1: Failing test** — use `responses` to mock `GET https://api.github.com/search/issues?q=repo:{repo}+is:pr+is:merged+merged:{start}..{end}` returning 3 PRs (one revert-titled, two with checked AI box; created/merged timestamps giving known median). Assert 4 MetricValues with exact expected numbers:

```python
# ai_visibility/collectors/tests/test_github.py
from decimal import Decimal
import pytest
import responses
from ai_visibility.collectors.github import GitHubCollector
from ai_visibility.teams.factories import IntegrationConfigFactory

pytestmark = pytest.mark.django_db
SEARCH_URL = "https://api.github.com/search/issues"
ITEMS = [
    {"title": "feat: a", "body": "- [x] AI-assisted", "pull_request": {"merged_at": "2026-07-07T12:00:00Z"}, "created_at": "2026-07-07T00:00:00Z"},
    {"title": "Revert \"feat: a\"", "body": "", "pull_request": {"merged_at": "2026-07-08T06:00:00Z"}, "created_at": "2026-07-08T00:00:00Z"},
    {"title": "fix: b", "body": "- [x] AI-assisted", "pull_request": {"merged_at": "2026-07-09T18:00:00Z"}, "created_at": "2026-07-09T00:00:00Z"},
]


@responses.activate
def test_github_collector_computes_four_metrics():
    responses.get(SEARCH_URL, json={"total_count": 3, "items": ITEMS})
    ic = IntegrationConfigFactory(provider="github", config={"repos": ["acme/app"]})
    ic.set_credentials({"token": "t"})
    ic.save()
    values = {mv.metric_key: mv.value for mv in
              GitHubCollector(ic.team, ic).collect(None, None)}
    assert values["pr_throughput"] == Decimal("3")
    assert values["pr_cycle_time_hours"] == Decimal("12")        # median of 12, 6, 18
    assert values["pr_revert_rate"] == Decimal("33.33")
    assert values["pct_ai_assisted_prs"] == Decimal("66.67")
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# ai_visibility/collectors/github.py
import datetime as dt
import statistics
from decimal import Decimal
import requests
from .base import BaseCollector, MetricValue, register

TIMEOUT = (10, 30)


def _pct(part: int, whole: int) -> Decimal:
    if not whole:
        return Decimal("0")
    return Decimal(part * 100 / whole).quantize(Decimal("0.01"))


@register
class GitHubCollector(BaseCollector):
    provider = "github"
    metrics_produced = ["pr_throughput", "pr_cycle_time_hours", "pr_revert_rate", "pct_ai_assisted_prs"]

    def collect(self, period_start, period_end):
        token = self.integration.get_credentials()["token"]
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        items = []
        for repo in self.integration.config.get("repos", []):
            q = f"repo:{repo} is:pr is:merged"
            if period_start and period_end:
                q += f" merged:{period_start}..{period_end}"
            page = 1
            while True:
                resp = requests.get("https://api.github.com/search/issues",
                                    params={"q": q, "per_page": 100, "page": page},
                                    headers=headers, timeout=TIMEOUT)
                resp.raise_for_status()
                batch = resp.json()["items"]
                items.extend(batch)
                if len(batch) < 100:
                    break
                page += 1

        total = len(items)
        cycle_hours = [
            (dt.datetime.fromisoformat(i["pull_request"]["merged_at"].replace("Z", "+00:00"))
             - dt.datetime.fromisoformat(i["created_at"].replace("Z", "+00:00"))).total_seconds() / 3600
            for i in items if i.get("pull_request", {}).get("merged_at")
        ]
        reverts = sum(1 for i in items if i["title"].startswith("Revert"))
        ai_assisted = sum(1 for i in items if "[x] AI-assisted" in (i.get("body") or ""))
        return [
            MetricValue("pr_throughput", Decimal(total)),
            MetricValue("pr_cycle_time_hours",
                        Decimal(statistics.median(cycle_hours)).quantize(Decimal("0.01")) if cycle_hours else Decimal("0")),
            MetricValue("pr_revert_rate", _pct(reverts, total)),
            MetricValue("pct_ai_assisted_prs", _pct(ai_assisted, total)),
        ]
```

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(collectors): GitHub PR throughput, cycle time, revert and AI-assisted rates"`

### Task 13: NewRelicCollector (Claude Code OTel + CFR)

**Files:**
- Create: `ai_visibility/collectors/newrelic.py`, `ai_visibility/collectors/tests/test_newrelic.py`

Config: `{"account_id": 123}`, credentials `{"api_key": "NRAK-..."}`. NerdGraph endpoint `https://api.newrelic.com/graphql`.
Metrics via NRQL over `claude_code.*` OTel metrics: `cc_wau_pct` (uniqueCount(user.id) ÷ team member count × 100), `cc_active_hours` (sum active_time ÷ 3600), `cc_accept_rate` (accept decisions ÷ all decisions), `cc_lines_of_code`, `cc_cost_usd`, `cc_sessions`.

- [ ] **Step 1: Failing test** — mock NerdGraph POST with `responses`; one canned JSON per NRQL result (`{"data": {"actor": {"account": {"nrql": {"results": [{...}]}}}}}`); team with 5 members, 3 active users → `cc_wau_pct == Decimal("60")`. Assert all 6 keys present.
- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# ai_visibility/collectors/newrelic.py
from decimal import Decimal
import requests
from .base import BaseCollector, MetricValue, register

NERDGRAPH = "https://api.newrelic.com/graphql"
TIMEOUT = (10, 30)
QUERY = """
query($accountId: Int!, $nrql: Nrql!) {
  actor { account(id: $accountId) { nrql(query: $nrql) { results } } }
}
"""


@register
class NewRelicCollector(BaseCollector):
    provider = "newrelic"
    metrics_produced = ["cc_wau_pct", "cc_active_hours", "cc_accept_rate",
                        "cc_lines_of_code", "cc_cost_usd", "cc_sessions"]

    def _nrql(self, nrql: str) -> list[dict]:
        creds = self.integration.get_credentials()
        resp = requests.post(
            NERDGRAPH, timeout=TIMEOUT,
            headers={"API-Key": creds["api_key"]},
            json={"query": QUERY, "variables": {
                "accountId": int(self.integration.config["account_id"]), "nrql": nrql}},
        )
        resp.raise_for_status()
        return resp.json()["data"]["actor"]["account"]["nrql"]["results"]

    def collect(self, period_start, period_end):
        since = f"SINCE '{period_start}' UNTIL '{period_end + __import__('datetime').timedelta(days=1)}'"
        members = self.team.memberships.count()

        active = self._nrql(f"SELECT uniqueCount(user.id) AS n FROM Metric WHERE metricName = 'claude_code.session.count' {since}")[0]["n"]
        sessions = self._nrql(f"SELECT sum(claude_code.session.count) AS n FROM Metric {since}")[0]["n"] or 0
        active_secs = self._nrql(f"SELECT sum(claude_code.active_time.total) AS n FROM Metric {since}")[0]["n"] or 0
        loc = self._nrql(f"SELECT sum(claude_code.lines_of_code.count) AS n FROM Metric WHERE type = 'added' {since}")[0]["n"] or 0
        cost = self._nrql(f"SELECT sum(claude_code.cost.usage) AS n FROM Metric {since}")[0]["n"] or 0
        decisions = self._nrql(f"SELECT filter(count(*), WHERE decision = 'accept') AS acc, count(*) AS all FROM Metric WHERE metricName = 'claude_code.code_edit_tool.decision' {since}")[0]

        def q(x):
            return Decimal(str(x)).quantize(Decimal("0.01"))

        accept_rate = q(decisions["acc"] * 100 / decisions["all"]) if decisions.get("all") else Decimal("0")
        return [
            MetricValue("cc_wau_pct", q(active * 100 / members) if members else Decimal("0")),
            MetricValue("cc_sessions", q(sessions)),
            MetricValue("cc_active_hours", q(active_secs / 3600)),
            MetricValue("cc_lines_of_code", q(loc)),
            MetricValue("cc_cost_usd", q(cost)),
            MetricValue("cc_accept_rate", accept_rate),
        ]
```
(Exact NRQL metric names drift with Claude Code releases — verify against current monitoring docs during implementation; tests pin the collector's contract, not New Relic's.)

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(collectors): New Relic NRQL collector for Claude Code OTel metrics"`

### Task 14: SonarQubeCollector

**Files:**
- Create: `ai_visibility/collectors/sonarqube.py`, `ai_visibility/collectors/tests/test_sonarqube.py`

Config: `{"base_url": "https://sonar.example.com", "project_key": "xiangqi"}`, credentials `{"token": "..."}`.
Metrics: `sonar_new_bugs`, `sonar_gate_passed` (1/0 from `/api/qualitygates/project_status`), plus `new_coverage` → dimension on `sonar_gate_passed`? No — separate `MetricValue("sonar_new_coverage_pct", ...)` if `new_coverage` in response.

- [ ] **Step 1: Failing test** — mock `GET {base}/api/measures/component?component=xiangqi&metricKeys=new_bugs,new_coverage` and `GET {base}/api/qualitygates/project_status?projectKey=xiangqi` (`{"projectStatus": {"status": "OK"}}`). Assert `sonar_new_bugs == 2`, `sonar_gate_passed == 1`.
- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# ai_visibility/collectors/sonarqube.py
from decimal import Decimal
import requests
from .base import BaseCollector, MetricValue, register

TIMEOUT = (10, 30)


@register
class SonarQubeCollector(BaseCollector):
    provider = "sonarqube"
    metrics_produced = ["sonar_new_bugs", "sonar_gate_passed"]

    def collect(self, period_start, period_end):
        cfg = self.integration.config
        auth = (self.integration.get_credentials()["token"], "")
        base, key = cfg["base_url"].rstrip("/"), cfg["project_key"]

        measures = requests.get(f"{base}/api/measures/component", auth=auth, timeout=TIMEOUT,
                                params={"component": key, "metricKeys": "new_bugs,new_coverage"})
        measures.raise_for_status()
        by_key = {m["metric"]: m for m in measures.json()["component"]["measures"]}

        gate = requests.get(f"{base}/api/qualitygates/project_status", auth=auth,
                            timeout=TIMEOUT, params={"projectKey": key})
        gate.raise_for_status()

        def period_value(m):
            return Decimal(m.get("period", {}).get("value") or m.get("value") or "0")

        values = [
            MetricValue("sonar_new_bugs", period_value(by_key.get("new_bugs", {}))),
            MetricValue("sonar_gate_passed",
                        Decimal("1") if gate.json()["projectStatus"]["status"] == "OK" else Decimal("0")),
        ]
        return values
```

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(collectors): SonarQube new-code quality collector"`

---

## Phase 4 — `surveys` app

### Task 15: Survey models + seeded templates

**Files:**
- Create: `ai_visibility/surveys/models.py`, seed data migration, `ai_visibility/surveys/tests/test_models.py`, `ai_visibility/surveys/factories.py`
- Modify: LOCAL_APPS

Models:

```python
# ai_visibility/surveys/models.py
import uuid
from django.db import models


class SurveyTemplate(models.Model):
    key = models.SlugField(unique=True)          # "dx_core4_quarterly", "dxi_lite", "pulse"
    name = models.CharField(max_length=120)
    cadence = models.CharField(max_length=20)    # "quarterly", "monthly", "adhoc"


class Question(models.Model):
    class QType(models.TextChoices):
        LIKERT = "likert"      # 1-5
        NUMBER = "number"      # e.g. hours saved
        PERCENT = "percent"    # 0-100

    template = models.ForeignKey(SurveyTemplate, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=300)
    qtype = models.CharField(max_length=10, choices=QType.choices)
    metric_key = models.SlugField(blank=True, default="")  # maps mean answer -> MetricSnapshot

    class Meta:
        ordering = ["order"]


class SurveyRun(models.Model):
    class Status(models.TextChoices):
        OPEN = "open"
        CLOSED = "closed"

    template = models.ForeignKey(SurveyTemplate, on_delete=models.PROTECT)
    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="survey_runs")
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)


class SurveyToken(models.Model):
    """Proves membership; NEVER linked to a Response — anonymity by construction."""
    run = models.ForeignKey(SurveyRun, on_delete=models.CASCADE, related_name="tokens")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)  # for delivery/reminders only
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    consumed = models.BooleanField(default=False)


class Response(models.Model):
    run = models.ForeignKey(SurveyRun, on_delete=models.CASCADE, related_name="responses")
    submitted_at = models.DateTimeField(auto_now_add=True)
    # deliberately NO user/token FK


class Answer(models.Model):
    response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    value = models.DecimalField(max_digits=8, decimal_places=2)
```

- [ ] **Step 1: Failing test** — seed check: `SurveyTemplate.objects.get(key="dx_core4_quarterly").questions.count() == 6` with `metric_key` set on all six (`perceived_delivery`, `code_maintainability`, `change_confidence`, `ai_satisfaction`, `hours_saved_week`, `pct_feature_work`); `dxi_lite` has 14 likert questions with `metric_key=""` except aggregate handled at close (mean of all → `dxi_lite`). Anonymity model test: `Response` has no `user` field — `assert not hasattr(Response, "user")`.
- [ ] **Step 2: Run — FAIL**  |  **Step 3: Implement models + seed migration** (question text literals from measurement plan §6)  |  **Step 4: Run — PASS**
- [ ] **Step 5: Commit** — `git commit -am "feat(surveys): survey models with anonymous responses, seeded DX Core 4 + DXI-lite templates"`

### Task 16: Run creation + tokenized email delivery

**Files:**
- Create: `ai_visibility/surveys/services.py`, `ai_visibility/surveys/tests/test_services.py`

- [ ] **Step 1: Failing test**

```python
# ai_visibility/surveys/tests/test_services.py
import pytest
from django.core import mail
from ai_visibility.surveys.models import SurveyTemplate, SurveyToken
from ai_visibility.surveys.services import open_survey_run
from ai_visibility.teams.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def test_open_survey_run_issues_one_token_per_member_and_emails():
    m1 = MembershipFactory()
    MembershipFactory(team=m1.team)
    run = open_survey_run(team=m1.team, template_key="dx_core4_quarterly", days_open=7)
    assert SurveyToken.objects.filter(run=run).count() == 2
    assert len(mail.outbox) == 2
    assert str(SurveyToken.objects.first().token) in mail.outbox[0].body
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement** — `open_survey_run` creates `SurveyRun` (now → now+days), bulk-creates one `SurveyToken` per team member, sends email per member with link `reverse("surveys:answer", args=[token])` via `django.core.mail.send_mail`. Also `response_rate(run) -> Decimal` = consumed ÷ issued × 100.
- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(surveys): survey run opening with tokenized email invites"`

### Task 17: Answer view + anonymity guarantees

**Files:**
- Create: `ai_visibility/surveys/views.py`, `ai_visibility/surveys/urls.py`, templates `surveys/answer.html`, `surveys/done.html`, `surveys/already.html`
- Test: `ai_visibility/surveys/tests/test_views.py`

- [ ] **Step 1: Failing tests**

```python
# ai_visibility/surveys/tests/test_views.py (core cases)
def test_submit_consumes_token_and_stores_unlinked_response(client, open_run_with_token):
    token = open_run_with_token
    url = reverse("surveys:answer", args=[token.token])
    resp = client.post(url, {f"q_{q.id}": 4 for q in token.run.template.questions.all()})
    assert resp.status_code == 302
    token.refresh_from_db()
    assert token.consumed
    response = token.run.responses.get()
    assert not hasattr(response, "user_id")          # schema-level anonymity
    assert response.answers.count() == token.run.template.questions.count()


def test_consumed_token_shows_already_page(client, consumed_token):
    resp = client.get(reverse("surveys:answer", args=[consumed_token.token]))
    assert b"already" in resp.content.lower()


def test_closed_run_rejects_submission(client, token_on_closed_run):
    resp = client.post(reverse("surveys:answer", args=[token_on_closed_run.token]), {})
    assert resp.status_code == 410
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement** — no-login view (token IS auth): GET renders questions (likert radios / number input); POST inside `transaction.atomic()`: re-fetch token `select_for_update`, reject if consumed/closed, create `Response` + `Answer` rows, set `token.consumed=True`, redirect to done page. Validate likert 1–5, percent 0–100.
- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(surveys): anonymous tokenized answer flow"`

### Task 18: Close run → aggregate into MetricSnapshot

**Files:**
- Modify: `ai_visibility/surveys/services.py`, add Celery beat task `close_due_survey_runs`
- Test: `ai_visibility/surveys/tests/test_aggregation.py`

- [ ] **Step 1: Failing test** — run with 2 responses answering `hours_saved_week` 2 and 4 → `close_survey_run(run)` creates snapshot `hours_saved_week == Decimal("3")` (`source="survey"`, granularity `quarterly`), `dxi_lite` snapshot = mean of all 14-question means, run status `closed`.
- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement** — `close_survey_run`: for each question with `metric_key`, mean of answers → `upsert_snapshot(source=SURVEY, granularity=run.template.cadence-mapped, period=run window)`; for `dxi_lite` template overall mean → `dxi_lite`. Beat task closes runs past `closes_at` daily.
- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(surveys): close-run aggregation into metric snapshots"`

---

## Phase 5 — `dashboards` app

### Task 19: Aggregation service + guardrails

**Files:**
- Create: `ai_visibility/dashboards/services.py`, `ai_visibility/dashboards/tests/test_services.py`
- Modify: LOCAL_APPS

- [ ] **Step 1: Failing tests**

```python
def test_series_blocked_below_min_group_size():
    team = TeamFactory(min_aggregation_size=5)
    MembershipFactory.create_batch(3, team=team)
    with pytest.raises(GroupTooSmall):
        metric_series(team, "pr_throughput")


def test_series_returns_period_value_pairs_with_baseline_delta():
    # seed 2 weekly snapshots + baseline v1; assert series values and delta vs baseline
    ...


def test_paired_series_returns_metric_and_counterweight():
    s = paired_series(team, "pr_throughput")
    assert s["metric"]["key"] == "pr_throughput"
    assert s["paired"]["key"] == "pr_revert_rate"
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# ai_visibility/dashboards/services.py
class GroupTooSmall(Exception):
    pass


def _check_group(team):
    if team.memberships.count() < team.min_aggregation_size:
        raise GroupTooSmall(team.min_aggregation_size)


def metric_series(team, metric_key, granularity="weekly", limit=26) -> dict:
    _check_group(team)
    metric = MetricDefinition.objects.get(key=metric_key)
    snaps = (MetricSnapshot.objects
             .filter(team=team, metric=metric, granularity=granularity, dimensions={})
             .order_by("-period_start")[:limit])
    baseline = Baseline.objects.filter(team=team).order_by("-version").first()
    baseline_value = Decimal(baseline.values[metric_key]) if baseline and metric_key in baseline.values else None
    points = [{"period": s.period_start.isoformat(), "value": float(s.value)} for s in reversed(list(snaps))]
    latest = points[-1]["value"] if points else None
    delta_pct = (round((latest - float(baseline_value)) / float(baseline_value) * 100, 1)
                 if latest is not None and baseline_value else None)
    return {"key": metric_key, "name": metric.name, "unit": metric.unit,
            "direction": metric.direction, "points": points,
            "baseline": float(baseline_value) if baseline_value is not None else None,
            "delta_pct": delta_pct}


def paired_series(team, metric_key, **kw) -> dict:
    metric = MetricDefinition.objects.get(key=metric_key)
    return {"metric": metric_series(team, metric_key, **kw),
            "paired": metric_series(team, metric.paired_with.key, **kw) if metric.paired_with else None}


def freshness(team) -> dict:
    """provider -> latest successful CollectorRun finished_at (or None)."""
    out = {}
    for provider in team.integrations.filter(enabled=True).values_list("provider", flat=True):
        run = (team.collector_runs.filter(provider=provider, status="success")
               .order_by("-finished_at").first())
        out[provider] = run.finished_at if run else None
    return out
```

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(dashboards): guardrailed aggregation services (min group, baseline delta, metric pairing)"`

### Task 20: Overview (DX Core 4) page

**Files:**
- Create: `ai_visibility/dashboards/views.py`, `urls.py`, templates `dashboards/overview.html`, partial `dashboards/_metric_card.html`, `dashboards/_chart.html`
- Test: `ai_visibility/dashboards/tests/test_views.py`

- [ ] **Step 1: Failing tests** — login required; member of team A gets 404/403 for team B slug; overview renders 5 headline cards (`pr_throughput`, `perceived_delivery`, `dxi_lite`, `code_maintainability`, `change_failure_rate`) with delta badge; small team renders "group too small" (no numbers in HTML); stale collector (>10 days) shows stale badge.
- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement** — `TeamDashboardView(LoginRequiredMixin, TemplateView)` resolving team by slug + `require_team_member`; context from services; template: Tailwind grid of `_metric_card.html` (name, latest, delta vs baseline arrow colored by `direction`), Chart.js line per card fed by inline `json_script` data; freshness badges from `freshness()`. `GroupTooSmall` caught → guardrail explainer partial.
- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(dashboards): DX Core 4 overview with baseline deltas and freshness badges"`

### Task 21: Utilization / Impact / Cost tabs

**Files:**
- Modify: `views.py`, `urls.py`; templates `dashboards/utilization.html`, `dashboards/impact.html`, `dashboards/cost.html`, partial `dashboards/_paired_panel.html`

- [ ] **Step 1: Failing tests** — utilization lists `cc_wau_pct` (+60–70% benchmark annotation in HTML), `pct_ai_assisted_prs`, `cc_accept_rate`, `cc_sessions`; impact page renders speed metrics ONLY via `_paired_panel.html` — test asserts each speed chart div is accompanied by its paired quality chart div; cost page shows `cc_cost_usd` trend.
- [ ] **Step 2–4: Implement (HTMX `hx-get` tab swaps), run, PASS**
- [ ] **Step 5: Commit** — `git commit -am "feat(dashboards): utilization, impact (paired panels), cost tabs"`

---

## Phase 6 — `reports` app

### Task 22: ROI calculator service

**Files:**
- Create: `ai_visibility/reports/roi.py`, `ai_visibility/reports/tests/test_roi.py`
- Modify: LOCAL_APPS

- [ ] **Step 1: Failing test — measurement plan §7 worked example**

```python
from decimal import Decimal
from ai_visibility.reports.roi import compute_roi


def test_worked_example_from_measurement_plan():
    r = compute_roi(devs=10, hours_saved_per_dev_week=Decimal("3.0"),
                    loaded_hourly_cost=Decimal("40"), monthly_spend=Decimal("1000"))
    assert r.monthly_value == Decimal("5160.00")   # 3 × 10 × 4.3 × 40
    assert r.net_gain == Decimal("4160.00")
    assert r.roi_multiple == Decimal("5.16")


def test_zero_spend_has_no_multiple():
    r = compute_roi(devs=1, hours_saved_per_dev_week=Decimal("1"),
                    loaded_hourly_cost=Decimal("40"), monthly_spend=Decimal("0"))
    assert r.roi_multiple is None
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement**

```python
# ai_visibility/reports/roi.py
import dataclasses
from decimal import Decimal

WEEKS_PER_MONTH = Decimal("4.3")
CENTS = Decimal("0.01")


@dataclasses.dataclass(frozen=True)
class RoiResult:
    monthly_value: Decimal
    net_gain: Decimal
    roi_multiple: Decimal | None


def compute_roi(*, devs: int, hours_saved_per_dev_week: Decimal,
                loaded_hourly_cost: Decimal, monthly_spend: Decimal) -> RoiResult:
    monthly_value = (hours_saved_per_dev_week * devs * WEEKS_PER_MONTH * loaded_hourly_cost).quantize(CENTS)
    net_gain = (monthly_value - monthly_spend).quantize(CENTS)
    multiple = (monthly_value / monthly_spend).quantize(CENTS) if monthly_spend else None
    return RoiResult(monthly_value, net_gain, multiple)
```

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(reports): ROI calculator matching plan worked example"`

### Task 23: Monthly leadership report

**Files:**
- Create: `ai_visibility/reports/views.py`, `services.py`, template `reports/monthly.html` (print-friendly single page)
- Test: `ai_visibility/reports/tests/test_report.py`

- [ ] **Step 1: Failing test** — report view (team_lead+ only) contains: 5 headline metrics with deltas, guardrail section (revert rate, CFR, sonar gate vs baseline — pass/fail flags = KR5), latest survey response rate, ROI block pulling `hours_saved_week` survey snapshot + `cc_cost_usd` + team `loaded_hourly_cost_usd` + member count into `compute_roi`. Cross-check note: throughput trend chart rendered beside ROI (plan §7 caveat).
- [ ] **Step 2–4: Implement, run, PASS**  |  **Step 5: Commit** — `git commit -am "feat(reports): monthly one-page leadership report with guardrail status"`

---

## Phase 7 — Auth & team management UI

### Task 24: Google OAuth + domain restriction + local fallback

**Files:**
- Modify: `config/settings/base.py` (allauth Google provider), `.envs/*`
- Create: `ai_visibility/users/adapters.py` addition, test `ai_visibility/users/tests/test_oauth_domain.py`

- [ ] **Step 1: Failing test** — `SocialAccountAdapter.is_open_for_signup` / `pre_social_login` rejects email `evil@other.com` when `ALLOWED_OAUTH_DOMAINS=["arbisoft.com"]`, allows `dev@arbisoft.com`; allows anyone when list empty.
- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement** — add `allauth.socialaccount.providers.google` to apps; `ALLOWED_OAUTH_DOMAINS = env.list("ALLOWED_OAUTH_DOMAINS", default=[])`; in cookiecutter's existing `SocialAccountAdapter`:

```python
from allauth.exceptions import ImmediateHttpResponse
from django.core.exceptions import PermissionDenied
from django.conf import settings


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        allowed = settings.ALLOWED_OAUTH_DOMAINS
        email = (sociallogin.user.email or "").lower()
        if allowed and email.split("@")[-1] not in allowed:
            raise PermissionDenied("Email domain not allowed")
```
Password auth stays enabled (allauth default). Document Google OAuth app setup in README.

- [ ] **Step 4: Run — PASS**  |  **Step 5: Commit** — `git commit -am "feat(auth): google oauth with configurable domain allowlist"`

### Task 25: Team settings UI (integrations, baseline button, survey launch)

**Files:**
- Create: `ai_visibility/teams/views.py`, `urls.py`, `forms.py`, templates `teams/settings.html`, `teams/integration_form.html`

- [ ] **Step 1: Failing tests** — team_lead can save GitHub integration (credentials write-only: form never renders stored token; saving with blank token keeps old one); member gets 403; org_admin sees "Capture baseline" button → POST creates `Baseline` v(n+1); "Launch survey" POST calls `open_survey_run`.
- [ ] **Step 2–4: Implement (forms with `set_credentials` on save), run, PASS**
- [ ] **Step 5: Commit** — `git commit -am "feat(teams): settings UI for integrations, baseline capture, survey launch"`

---

## Phase 8 — CI & infra

### Task 26: GitHub Actions CI hardening

**Files:**
- Modify: `.github/workflows/ci.yml` (cookiecutter-generated)

- [ ] **Step 1:** Ensure jobs: `lint` (ruff check + format --check via pre-commit), `test` (docker compose pytest with coverage, fail under 85% on domain apps: `--cov=ai_visibility --cov-fail-under=85`), `docker-build`. Add coverage to `requirements/local.txt` if missing.
- [ ] **Step 2:** Push branch, verify green run: `gh run watch`.
- [ ] **Step 3: Commit** — `git commit -am "ci: coverage gate and docker build job"`

### Task 27: Terraform module

**Files:**
- Create: `infra/terraform/{main.tf,variables.tf,outputs.tf,versions.tf}`, `infra/terraform/envs/arbisoft.tfvars.example`

- [ ] **Step 1:** Write module per deployment-strategy doc (`docs/DEPLOYMENT-STRATEGY.md`): VPC (public subnet), EC2 t3.small (Ubuntu 24.04 AMI data source, key pair var), Elastic IP, RDS Postgres 16 (db.t4g.micro, private subnet, SG from EC2 only), security groups (22 restricted to `admin_cidr` var, 80/443 open), S3 + DynamoDB backend for state.
- [ ] **Step 2: Validate** — `terraform -chdir=infra/terraform init -backend=false && terraform -chdir=infra/terraform validate` → `Success`.
- [ ] **Step 3: Commit** — `git commit -am "infra: terraform module for single-instance AWS deployment"`

### Task 28: Ansible playbooks

**Files:**
- Create: `infra/ansible/{inventory.example.ini,bootstrap.yml,deploy.yml,rollback.yml,templates/env.j2,group_vars/all.yml.example}`

- [ ] **Step 1:** `bootstrap.yml`: apt update, install docker + compose plugin, create `deploy` user, ufw (22/80/443). `deploy.yml`: render `.env` from vault vars, `git pull --tags` or pull GHCR image `ghcr.io/<owner>/ai-visibility:<tag>`, `docker compose -f docker-compose.production.yml up -d`, run `migrate`, healthcheck `curl -f localhost/healthz` (add `/healthz` URL returning 200 in `config/urls.py` — trivial view, add here with a test). `rollback.yml`: redeploy previous tag var.
- [ ] **Step 2: Validate** — `ansible-playbook --syntax-check infra/ansible/*.yml` → clean.
- [ ] **Step 3: Commit** — `git commit -am "infra: ansible bootstrap/deploy/rollback playbooks"`

### Task 29: Release pipeline + final docs

**Files:**
- Create: `.github/workflows/release.yml`, finalize `README.md` sections, `docs/DEPLOYMENT.md` runbook (condensed from strategy doc: prerequisites → terraform apply → ansible bootstrap → ansible deploy → onboard team checklist)

- [ ] **Step 1:** `release.yml`: on tag `v*` → build image → push GHCR. (Auto-deploy step documented but commented out — manual `ansible-playbook deploy.yml` first release.)
- [ ] **Step 2:** Full local verify: `pre-commit run -a && dj-pytest && docker compose -f docker-compose.local.yml up -d` + click-through: login → create team → settings → fake integration → dashboard guardrail page.
- [ ] **Step 3: Commit + push + tag** — `git commit -am "docs: deployment runbook and release pipeline" && git push && git tag v0.1.0 && git push --tags`

---

## Self-review notes

- Spec coverage: teams (T4-6, 25), metrics+baseline (T7-9), collectors framework + 3 providers (T10-14), surveys incl. anonymity + aggregation (T15-18), dashboards + guardrails + pairing (T19-21), reports/ROI (T22-23), auth (T24), CI/infra/deploy (T26-29). Jira collector explicitly phase 2 (spec §10). ✓
- Type consistency: `MetricValue(metric_key, value, dimensions)`, `upsert_snapshot(...)` kwargs, `GroupTooSmall`, role strings — used identically across tasks. ✓
- Known intentional deferrals: `change_failure_rate` + `lead_time_hours` land via New Relic deployment markers — v1 seeds definitions, values enterable via admin (`source=manual`) until deploy-marker wiring (documented in README limitations).
