# ai-visibility — Deployment Strategy

**Date:** 2026-07-16
**Scope:** Deploying ai-visibility for the xiangqi team first, then other Arbisoft teams, and (as an open-source project) any external org.
**IaC:** Terraform (provisioning) + Ansible (configuration & deploys)

---

## 1. Deployment model

One **instance per organization**, many **teams per instance** (app is multi-tenant).

| Scenario | Action |
|---|---|
| New Arbisoft team (e.g. after xiangqi) | No infra work — org admin creates a `Team` row + integration config in the app |
| New organization (external adopter, separate Arbisoft business unit) | New Terraform workspace → new stack |

This keeps infra flat: adding teams costs zero ops; adding orgs is a repeatable ~30-minute runbook.

## 2. Target architecture (per org)

```
Internet ──► Elastic IP ──► EC2 t3.small (Ubuntu 24.04)
                             ├── traefik (TLS via Let's Encrypt, ports 80/443)
                             ├── django (gunicorn)
                             ├── celeryworker
                             ├── celerybeat
                             └── redis
                                   │
                             RDS PostgreSQL 18 (db.t4g.micro, private subnet)
```

- Docker Compose production stack (cookiecutter-django's `docker-compose.production.yml`, Postgres service removed in favor of RDS).
- Redis stays on-instance (queue only, loss-tolerant — collectors are idempotent and re-runnable).
- RDS chosen over containerized Postgres: automated backups, point-in-time recovery, patching. The metrics data is the product — don't keep it on an instance volume.

**Sizing rationale:** internal tool, ~15 users/org initially, weekly batch collectors. t3.small + db.t4g.micro ≈ **$35–45/month/org**. Scale path: bump instance class; nothing architectural changes until multi-node (not expected).

## 3. Repository layout

```
infra/
  terraform/
    main.tf            # VPC, EC2, EIP, RDS, security groups
    variables.tf       # region, instance sizes, admin_cidr, domain, key pair
    outputs.tf         # instance IP, RDS endpoint
    versions.tf        # pinned providers, S3 backend config
    envs/
      arbisoft.tfvars.example
  ansible/
    inventory.example.ini
    bootstrap.yml      # one-time host prep
    deploy.yml         # every release
    rollback.yml
    templates/env.j2   # production .env rendered from vault
    group_vars/all.yml.example
```

## 4. Terraform (provisioning)

- **State:** S3 bucket + DynamoDB lock table (created once per org account, documented in runbook).
- **Workspaces:** one per org (`terraform workspace new arbisoft`). Same module, different tfvars.
- **Resources:** VPC with one public + one private subnet pair, EC2 with key pair, Elastic IP, RDS Postgres 18 (private, SG allows 5432 from EC2 SG only), security groups (22 from `admin_cidr` only; 80/443 world), optional Route53 record if `domain` var set.
- **Secrets:** none in Terraform — RDS master password generated via `random_password`, written to SSM Parameter Store (SecureString); Ansible reads it from there.

## 5. Ansible (configuration + deploy)

- **bootstrap.yml** (once per host): apt upgrade, install Docker + compose plugin, create `deploy` user with docker group, ufw allow 22/80/443, enable unattended-upgrades.
- **deploy.yml** (every release):
  1. Render `.env` from `templates/env.j2` + Ansible Vault vars (Django secret key, `FIELD_ENCRYPTION_KEY`, DB URL from SSM, OAuth client id/secret, SMTP creds).
  2. Pull image `ghcr.io/<owner>/ai-visibility:<tag>` (tag = playbook var).
  3. `docker compose -f docker-compose.production.yml up -d`.
  4. `docker compose run --rm django python manage.py migrate`.
  5. Healthcheck: `curl -f https://<domain>/healthz` — fail playbook if non-200.
- **rollback.yml**: re-run deploy with previous tag (images immutable and kept on GHCR; DB migrations are additive-only policy — destructive migrations require a two-release deprecation cycle, enforced in code review).
- **Secrets management:** Ansible Vault file per org (`vault-arbisoft.yml`), vault password in team password manager. `FIELD_ENCRYPTION_KEY` backed up there too — losing it loses stored integration credentials (re-enterable, not fatal, but avoid).

## 6. CI/CD pipeline

| Trigger | Pipeline |
|---|---|
| PR | ruff → pytest (coverage ≥85% gate) → docker build |
| Tag `v*` | build production image → push `ghcr.io/<owner>/ai-visibility:vX.Y.Z` + `:latest` |
| Deploy | manual: `ansible-playbook -i inventory deploy.yml -e app_tag=vX.Y.Z` (auto-deploy on tag can be enabled later via GH Actions + SSH once trust established) |

Manual deploy chosen deliberately for v1: internal tool, low release cadence, humans watch first deploys. Automate when boring.

## 7. Environments

- **local** — docker-compose.local.yml, mailpit, runserver. Devs.
- **production (per org)** — the stack above.
- No staging for v1 (YAGNI at this scale — local + feature review covers it). If an org needs one later: another Terraform workspace with `staging.tfvars`.

## 8. Backup & recovery

- **RDS:** automated daily snapshots, 7-day retention (tfvar). Point-in-time recovery on.
- **App host:** stateless by design (images from GHCR, env from vault/SSM) — recovery = `terraform apply` + `bootstrap.yml` + `deploy.yml` (~30 min RTO, RPO = last RDS snapshot/PITR).
- Quarterly restore drill noted in runbook.

## 9. Monitoring & ops

- `/healthz` endpoint (200 + DB check) — pinged by New Relic Synthetics (already in Arbisoft stack) or UptimeRobot for external orgs.
- Collector failures self-report: `CollectorRun.failed` → email to org admins (in-app feature, no infra needed).
- Logs: `docker compose logs` + journald; ship to New Relic via infra agent optional, not required for v1.

## 10. Security posture

- TLS via traefik/Let's Encrypt; HTTP→HTTPS redirect.
- SSH restricted to `admin_cidr`; no password auth.
- DB in private subnet, unreachable from internet.
- Integration API credentials encrypted at rest (Fernet) in Postgres; write-only in UI.
- Google OAuth domain allowlist per org (`ALLOWED_OAUTH_DOMAINS`).
- Dependabot + `pip-audit` in CI (weekly schedule) for dependency CVEs.

## 11. Onboarding runbooks

**New Arbisoft team (no infra):**
1. Org admin: create Team, set `min_aggregation_size`, `loaded_hourly_cost_usd`.
2. Team lead: add GitHub token (repo scope, team's repos), New Relic account id + query key, SonarQube token + project key.
3. Devs: enable Claude Code OTel export → New Relic (env block from README).
4. Add `AI-assisted?` checkbox to the team's PR template.
5. Capture baseline **before** heavy AI adoption. Launch first survey.

**New org (~30 min):**
1. AWS account prereqs: S3 state bucket + DynamoDB lock table.
2. `terraform workspace new <org> && terraform apply -var-file=envs/<org>.tfvars`.
3. Create vault file, set secrets; add host to inventory.
4. `ansible-playbook bootstrap.yml && ansible-playbook deploy.yml -e app_tag=vX.Y.Z`.
5. Create superuser, configure Google OAuth app, proceed as team onboarding above.

## 12. Implementation plan pointer

Infra code tasks are Tasks 26–29 in `docs/plans/2026-07-16-ai-visibility-implementation.md` (Terraform module → Ansible playbooks → release pipeline → runbook docs).
