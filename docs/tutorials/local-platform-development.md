---
sources:
  - pixi.toml
  - src/platform/README.md
  - src/platform/config/settings/base.py
  - src/platform/config/urls.py
  - src/platform/config/local_dev/mint.py
  - .github/workflows/platform-ci.yml
  - docs/dreams/platform-dev-boots-local.md
verified: 2026-09-20
---

# Local Platform Development

This tutorial guides Platform Builders and New Developers through standing up the `src/platform/` Django application locally. The PyForge platform is the central monolithic host for the enterprise API, Wagtail CMS, and local AI engines.

## Prerequisites
- A working `pixi` installation.
- Ensure you have read the [PyForge Ecosystem Architecture](../explanation/pyforge-ecosystem-architecture.md) to understand the relationship between the platform and the CLI stations.

## Step 1: Provision the Development Environment
The platform dependencies are managed via the `platform-dev` environment in `pixi.toml` — the no-Docker local baseline. It composes the image's `python-agent-platform` feature (Django, Wagtail, Langflow, the ASGI stack) with per-user server processes: PostgreSQL 17 + pgvector, Redis, the Silo S3-compatible object store, plus `helm`/`kubectl` for chart work and `django-debug-toolbar` for the local settings leaf.

```bash
pixi install -e platform-dev
```

## Step 2: Configure the Database
The platform expects a PostgreSQL instance at `DATABASE_URL` (default `postgres:///platform`, from `src/platform/config/settings/base.py`). `platform-dev` ships the server itself, so run it as a per-user process from that env (`pixi shell -e platform-dev`, then `initdb` / `pg_ctl start`) rather than installing a system PostgreSQL; the container alternative is `docker compose -f src/platform/compose/compose.yml up postgres redis`.

All `manage.py` commands run from `src/platform/`; `manage.py` defaults to `config.settings.local` and sets `COMPONENT_RUNTIME=local` for that leaf (only that exact value selects local development — anything else is treated as deployed). Apply the migrations:
```bash
cd src/platform
pixi run -e platform-dev python manage.py migrate
```

> [!NOTE]
> Production DDL is owned by Liquibase (`src/platform/db/changelog/`), not by `migrate`. If you add first-party models, generate the Django migration with `makemigrations`, keep `makemigrations --check` green, and add the matching Liquibase changeset — the CI step `python -m db.sqlmigrate_extraction` fails on a production migration with no changeset. Station dashboards live in `src/shared/packages/pyforge-<station>/src/pyforge/<station>/dashboard/`, behind each package's `[dashboard]` extra.

## Step 3: Mint a Local Identity
Identity is OIDC-delegated: there is no local password login and no `createsuperuser` path — staff and superuser derive from IdP group claims. For local development without Keycloak, mint a persona JWT:
```bash
cd src/platform
COMPONENT_RUNTIME=local pixi run -e platform-dev python -m config.local_dev.mint staff
```
To sign in through a real IdP instead, start the compose stack's Keycloak (`docker compose -f src/platform/compose/compose.yml up keycloak platform`) and configure the `COMPONENT_OIDC_*` variables described in `src/platform/README.md`.

## Step 4: Run the Local Development Server
Start the Django development server:
```bash
cd src/platform
pixi run -e platform-dev python manage.py runserver
```

You can now access:
- The Wagtail front door (Lane 1) at `http://localhost:8000/`
- The Wagtail admin at `http://localhost:8000/cms/`
- The Django admin at `http://localhost:8000/admin/`
- Station portals under `http://localhost:8000/stations/<name>/`

## Step 5: Run the Platform Tests
The Platform CI `test` job runs from `src/platform/` in the slim `platform-ci-test` environment (the sole authority for that job's dependencies): `manage.py check`, Ruff, mypy, the policy suite, the sqlmigrate extraction, and then the full suite. Mirror it locally:
```bash
pixi install -e platform-ci-test
cd src/platform
pixi run -e platform-ci-test python manage.py check
pixi run -e platform-ci-test python -m pytest tests/policy -v
pixi run -e platform-ci-test python -m pytest -v
```

> [!IMPORTANT]
> The `dashboard/` extra is the only place Django lives in a station package. Never import `django` or `channels` at the module level in the base `pyforge-<station>` packages. The base packages must be capable of importing and running their CLI without the `[dashboard]` extra installed.
