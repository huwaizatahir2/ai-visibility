# Deployment Runbook

Condensed operational steps. For the rationale, see [`DEPLOYMENT-STRATEGY.md`](DEPLOYMENT-STRATEGY.md).

**Model:** one instance per organization, many teams per instance. Adding a team is an in-app action (no infra). Adding an org is the ~30-minute runbook below.

## Prerequisites (once per AWS account)

1. Create an S3 bucket `ai-visibility-tfstate` and a DynamoDB lock table `ai-visibility-tflock` (names configurable in `infra/terraform/versions.tf`).
2. An EC2 key pair for SSH.
3. Tools locally: `terraform >= 1.6`, `ansible-core >= 2.16`, `aws` CLI configured.

## 1. Provision infrastructure (Terraform)

```bash
cd infra/terraform
cp envs/arbisoft.tfvars.example envs/arbisoft.tfvars   # edit: key_pair_name, admin_cidr, region
terraform init
terraform workspace new arbisoft        # one workspace per org
terraform apply -var-file=envs/arbisoft.tfvars
```

Note the outputs: `app_public_ip`, `db_endpoint`, `db_password_ssm_parameter`. Point your DNS A record at `app_public_ip`. Read the DB password:

```bash
aws ssm get-parameter --name /ai-visibility/db_password --with-decryption --query Parameter.Value --output text
```

## 2. Configure secrets (Ansible Vault)

```bash
cd infra/ansible
cp inventory.example.ini inventory.ini             # set ansible_host = app_public_ip
cp group_vars/all.yml.example group_vars/all.yml   # or an encrypted vault file
```

Fill in `all.yml` (ideally `ansible-vault encrypt group_vars/all.yml`): `django_secret_key`, `field_encryption_key` (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`), DB host/password (from step 1), OAuth + SMTP creds, `allowed_oauth_domains`.

> **Keep `field_encryption_key` safe.** Losing it makes stored integration credentials unrecoverable (re-enterable in the UI, but avoid).

## 3. Bootstrap and deploy

```bash
ansible-playbook -i inventory.ini bootstrap.yml            # one-time: docker, deploy user, ufw
ansible-playbook -i inventory.ini deploy.yml -e app_tag=v0.1.0
```

`deploy.yml` renders `.env`, pulls `ghcr.io/huwaizatahir2/ai-visibility:<tag>`, starts the stack, migrates, and health-checks `https://<domain>/healthz/`.

Create the first superuser:

```bash
ssh ubuntu@<app_public_ip>
cd /opt/ai-visibility
docker compose --env-file .env -f docker-compose.production.yml run --rm django python manage.py createsuperuser
```

## 4. Onboard the first team

1. **Org admin** (Django admin or shell): create a `Team`; set `min_aggregation_size` and `loaded_hourly_cost_usd`. Add memberships with roles.
2. **Team lead**: on `…/teams/<slug>/settings/`, add GitHub (repos + token), New Relic (account id + query key), SonarQube (base URL, project key, token).
3. **Devs**: enable Claude Code OTel → New Relic (see the README).
4. Add the `AI-assisted?` checkbox to the team's PR template.
5. **Capture the baseline** before heavy adoption; launch the first survey.

## Releasing a new version

```bash
git tag vX.Y.Z && git push --tags        # CI builds + pushes the image to GHCR
ansible-playbook -i inventory.ini deploy.yml -e app_tag=vX.Y.Z
```

## Rollback

```bash
ansible-playbook -i inventory.ini rollback.yml -e app_tag=<previous-tag>
```

Migrations are additive-only; destructive schema changes require a two-release deprecation cycle.

## Backup & recovery

RDS automated snapshots (7-day retention) with point-in-time recovery. The app host is stateless — recovery is `terraform apply` + `bootstrap.yml` + `deploy.yml` (~30 min RTO).
