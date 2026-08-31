---
title: 'The host renders into src/platform'
type: 'feature'
created: '2026-08-14'
status: 'done'
baseline_revision: 'c83924d3563e0aa7c78f6b6798ef41c9e64636be'
final_revision: '4e308a98d6ec0880e13a6892cdfcde3aec8aab8a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/planning-artifacts/specs/spec-python-agent-platform/SPEC.md'
  - '{project-root}/docs/dreams/django-accelerator-framework.md'
warnings: ['oversized']
difficulty: ''
---

<intent-contract>

## Intent

**Problem:** `src/platform/` does not exist. Epics 11-12 (Langflow/DB-GPT as pluggable apps,
deployment) all depend on a rendered Django host existing first, with FastAPI ASGI plumbing,
K8s health probes, zero-CDN static assets, cost-isolated CI, and an enforced factory/platform
import boundary — none of which exist yet.

**Approach:** Render cookiecutter-django (pinned `--checkout 2025.07.27`, matching this
factory's own `cookiecutter-django` feedstock pin) into `src/platform/` with the answer set
fixed in Design Notes below, then hand-add the four things stock cookiecutter-django doesn't
provide: a FastAPI ASGI mount seam, django-health-check wiring, local HTMX vendoring, and an
import-linter contract + paths-filtered CI workflow.

## Boundaries & Constraints

**Always:** infra stays exactly PostgreSQL + Redis (Celery broker) — no third backing service,
no cloud SDK, no external mail/monitoring vendor. `src/platform/` never imports `pyforge.*`
(enforced by import-linter, not convention). Platform CI (`.github/workflows/platform-ci.yml`)
runs `working-directory: src/platform` filtered on `paths: [src/platform/**]` so it never
triggers on, or is triggered by, factory-detector changes. All runtime config (DB, Redis,
secrets) flows through `env()`/django-environ — nothing hardcoded. Static assets ship vendored
locally; zero CDN `<script>`/`<link>` references anywhere in rendered templates.

**Block If:** the pinned tag's `cookiecutter.json` has dropped a key this spec relies on with
no reasonable equivalent → HALT `blocked` (`cookiecutter schema diverged`). Docker is
unavailable to spin up local PostgreSQL/Redis for verification → HALT `blocked`
(`no local infra for verification`).

**Never:** build the actual Langflow/DB-GPT ASGI mounts (Epic 11) — only the seam they attach
to. Use cookiecutter-django's baked-in Docker/docker-compose or CI-tool scaffolding (`use_docker`
and `ci_tool` are both declined — Story 10.3 and this story's own workflow supersede them). Add
DRF/Django Ninja (`rest_api: None` — "FastAPI integration" means the seam below, not a second
REST framework). Touch `pixi.toml` or `environment.yaml` (Story 10.2's surface, not this one's).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | PostgreSQL 17 + Redis 7 running, `DATABASE_URL`/`REDIS_URL` set | `manage.py check` exits 0 | n/a |
| No 3rd infra | Only PG + Redis reachable, no Elasticsearch/Mongo/etc. | `manage.py check` still exits 0 | n/a |
| Non-platform PR | Commit touches only `recipes/**` | `platform-ci.yml` does not run | n/a |
| ASGI seam reachable | `GET /api/health` against the rendered ASGI app | `200` from the mounted FastAPI sub-app | n/a |
| Boundary violation (regression guard) | A file under `src/platform/` imports `pyforge.anything` | `lint-imports` exits non-zero, test fails | test must catch it, not silently pass |

</intent-contract>

## Code Map

- `src/platform/` -- new cookiecutter-django render root (does not exist yet)
- `recipes/cookiecutter-django/recipe.yaml` -- confirms the factory's own `2025.07.27` pin to render against
- `src/shared/packages/pyforge-marshal/pyproject.toml` + `tests/meta/test_ad3_ad4_import_linter.py` -- the existing import-linter precedent this story's boundary test mirrors
- `.github/workflows/kedro-viz-publish.yml` -- existing `paths:`-filtered workflow to model `platform-ci.yml` on

## Tasks & Acceptance

**Execution:**
- [x] `src/platform/` -- render via `pixi run -e local-recipes cookiecutter https://github.com/cookiecutter/cookiecutter-django --checkout 2025.07.27 --no-input -o src <extra-context from Design Notes>` -- establishes the host at the contracted root with the pinned answer set
- [x] `src/platform/config/asgi.py` -- compose a FastAPI sub-app mounted at `/api/` exposing `GET /api/health` → `200` -- the ASGI seam Epic 11 extends, without building the real Langflow/DB-GPT mounts
- [x] `src/platform/requirements/base.txt` -- add `django-health-check`, `fastapi` -- runtime deps for the probe endpoint and the seam
- [x] `src/platform/config/settings/base.py`, `src/platform/config/urls.py` -- register `health_check` app, wire `/ht/` -- K8s liveness/readiness target
- [x] rendered base template + static dir (path fixed by the render) -- vendor HTMX 2.x locally under `static/js/vendor/`, remove any CDN `<script>` tag; confirm Bootstrap ships local via the Django Compressor pipeline -- zero-CDN AC
- [x] `src/platform/pyproject.toml` -- add `[tool.importlinter]` with a `forbidden`-type contract barring any `pyforge` import from the platform's own packages -- mirrors `pyforge-marshal`'s AD-3/AD-4 precedent
- [x] `src/platform/tests/meta/test_no_pyforge_import.py` -- shell out to `lint-imports --config pyproject.toml --no-cache`, assert `returncode == 0` -- makes the boundary a real CI gate
- [x] `.github/workflows/platform-ci.yml` -- new workflow: trigger `paths: [src/platform/**]`, `working-directory: src/platform`, `actions/setup-python@v5` (`python-version: '3.12'`), GH Actions `services:` for `postgres:17` + `redis:7`, install `requirements/local.txt`, run `manage.py check` and the import-linter meta test -- platform/factory CI cost isolation

**Acceptance Criteria:**
- Given PostgreSQL 17 + Redis 7 running locally with no other backing service, when `DATABASE_URL`/`REDIS_URL` are set and `python src/platform/manage.py check` runs, then it exits 0 with no errors or warnings.
- Given `.github/workflows/platform-ci.yml`, when a commit touches only paths outside `src/platform/**`, then the workflow does not trigger.
- Given the rendered tree, when `cd src/platform && lint-imports --config pyproject.toml --no-cache` runs, then it reports `0 broken`.
- Given all templates and static files under `src/platform/`, when grepped for `cdn.`, `unpkg.com`, `jsdelivr.net`, or `fonts.googleapis`, then zero matches are found.
- Given the composed ASGI app, when `GET /api/health` is requested, then it returns `200` from the mounted FastAPI sub-app (not the Django app).

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 1, medium 4, low 6)
- defer: 0
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` `config/asgi.py`'s composed dispatcher had no `lifespan` scope branch — any ASGI server sending startup/shutdown lifespan messages would hit the `else` and raise `NotImplementedError`. Added a minimal correct lifespan handler (Edge Case Hunter).
  - `[medium]` `[patch]` CI's own "PostgreSQL + Redis" check step never actually opened a DB connection (`manage.py check` performs no live DB check) and none of the shipped `platformapp` app tests ran in CI. Added a "Full test suite" CI step running the whole `pytest` suite (18 app tests + the 3 new ASGI-seam tests), which does exercise real Postgres via `pytest-django`'s test-DB creation/migration (Blind Hunter, two findings addressed together).
  - `[medium]` `[patch]` The story's own new deliverable — the FastAPI/ASGI routing seam — had zero test coverage. Added `tests/test_asgi_seam.py` (3 tests, hits `config.asgi.application` directly via `httpx.ASGITransport`): `/api/health` reaches FastAPI, an unknown `/api/*` path gets FastAPI's JSON 404 (not Django's), and a non-`/api/` path falls through to Django. Required adding `httpx` to `requirements/local.txt` (Blind Hunter).
  - `[medium]` `[patch]` `health_check.storage` (checks the default file-storage backend) was wired into `/ht/`, a backing dependency outside this spec's own "Always: infra stays exactly PostgreSQL + Redis" boundary. Removed it from `THIRD_PARTY_APPS`, keeping only `health_check.db`/`health_check.cache` (Edge Case Hunter).
  - `[low]` `[patch]` No CI step ran `ruff`/`mypy` despite `pyproject.toml` configuring both. Added both as CI steps; fixed the one pre-existing stock-template mypy error this surfaced (`config/settings/production.py`'s untyped `ANYMAIL = {}`) so the new gate is not immediately red on unrelated template output (Blind Hunter).
  - `[low]` `[patch]` `fastapi_app.py`'s docstring claimed Epic 11 would mount Langflow at `/langflow/` through this seam, but `asgi.py` only routes `/api/*` here — `/langflow/` would silently fall through to Django. Corrected the docstring to state the seam's actual namespace and flag that a non-`/api/` mount needs its own future routing rule (Blind Hunter).
  - `[low]` `[patch]` The `django-health-check==3.24.0` pin's comment was confusingly worded and, unlike sibling pins in the same file, had no `pyup` guard against a silent bump past its documented `Django<5.2` compatibility ceiling. Reworded the comment and added `# pyup: < 4.0` (Blind Hunter).
  - `[low]` `[patch]` The new `/ht/` endpoint ships with no app-layer auth. This is standard for a kubelet-probed endpoint (access control belongs at the network/ingress layer, owned by the deployment epic) — added a comment documenting that scope boundary explicitly rather than adding app-layer auth this story doesn't own (Blind Hunter).
  - `[low]` `[patch]` `concurrency.cancel-in-progress: true` applied to `push:branches:[main]` too, so a fast-following push to main could cancel the prior commit's in-flight CI run, leaving no clean pass/fail signal to bisect against. Scoped `cancel-in-progress` to `pull_request` only (Blind Hunter).
  - `[low]` `[patch]` `workflow_dispatch` has no `paths:` filter (GitHub Actions doesn't support one for that trigger), so a manual run against a ref predating this story would fail confusingly on `working-directory: src/platform`. Added an explicit guard step with a clear `::error::` message (Edge Case Hunter).
  - reject (no code/spec change — reasoning recorded, not re-justified here): (1) cache health check validates `LocMemCache` not Redis under local/CI settings — standard cookiecutter-django environment separation (production settings use `django_redis`), not a defect this story introduced; (2) no Kubernetes deployment artifact exists yet — explicitly Epic 12's surface, not Story 10.1's; (3) landing PR needs the repo's `maintenance` label — true and already known (`CLAUDE.md`), but a PR-open-time action for whoever lands this, not a code/artifact defect; (4) `test_no_pyforge_import.py`'s `subprocess.run(..., timeout=120)` has no explicit `TimeoutExpired` handler — matches `pyforge-marshal`'s own precedent test exactly, standard pytest exception propagation.

### 2026-08-14 — Review pass (repair session: spec-surface verification failure)

This pass reviews the diff since `baseline_revision`, which now also includes the
repair work that fixed the deterministic `python scripts/spec_surface_reconcile.py`
verify-gate failure a prior session left behind (`spec-python-agent-platform`'s
`surface:` declared the bare directory `src/platform/`, which matches zero
git-tracked files — corrected to `src/platform/**` — plus a `.memlog.md` +
baseline stamp for that spec, and unrelated pre-existing-debt bootstrap memlogs/
baselines for 8 other freshly-drafted specs across pyforge-atlas/pyforge-herald/
pyforge-marshal/pyforge-steward that were blocking the same shared, repo-wide
gate). None of that governance-plumbing work touches `<intent-contract>` or any
platform code, and both of bmad-loop's own verify commands (the reconcile gate
and `pixi run --frozen -e pyforge-steward pyforge-steward-test`) now pass clean.

- intent_gap: 0
- bad_spec: 0
- patch: 6 (low 6)
- defer: 1 (medium 1)
- reject: 5
- addressed_findings:
  - `[low]` `[patch]` `src/platform/docs/Makefile`/`docs/make.bat`'s `APP` variable still pointed at the pre-rename `../platform` (used by the `apidocs`/`livehtml` Sphinx targets), left over from the `platform` → `platformapp` inner-package rename despite Design Notes claiming "every reference updated." Corrected both to `../platformapp` (Blind Hunter).
  - `[low]` `[patch]` The import-linter boundary's `root_packages`/`source_modules` covered only `config`/`platformapp`, excluding `tests/` — a future test helper importing `pyforge.*` would sail past `lint-imports` untouched, despite the spec's own Boundary text covering the whole `src/platform/` tree. Added `"tests"` to both (Blind Hunter, Edge Case Hunter — corroborated).
  - `[low]` `[patch]` `config/asgi.py`'s lifespan branch acked `lifespan.startup`/`.shutdown` locally instead of forwarding to `fastapi_application`, so any future FastAPI startup/shutdown hook Epic 11 adds would silently never fire. Now forwards the whole lifespan scope to `fastapi_application` (Starlette's own lifespan handling); verified it still completes correctly with a direct lifespan-protocol exercise (Blind Hunter, Edge Case Hunter — corroborated).
  - `[low]` `[patch]` A bare `/api` (no trailing slash) fell through to Django's HTML 404 instead of FastAPI's JSON 404, inconsistent with every other `/api/*` path. Added a shared `_is_api_path` predicate in `config/asgi.py` matching the bare path too; verified via direct ASGI transport request (Edge Case Hunter).
  - `[low]` `[patch]` `fastapi_app.py`'s docstring overclaimed "routes every `/api/*` path here" without qualifying that only HTTP is path-routed (every websocket connection, any path, currently reaches the stock ping/pong stub); it also didn't document the no-`Mount`-prefix-stripping convention future routes must follow, or distinguish `/api/health`'s unconditional ping from `/ht/`'s real DB/cache-checked probe. Expanded the docstring to cover all three (Blind Hunter, Edge Case Hunter).
  - `[low]` `[patch]` `.github/workflows/platform-ci.yml` ran the import-boundary test twice — once in its own dedicated step, then again inside the unrestricted "Full test suite" step. Removed the redundant standalone step (Blind Hunter).
  - `[medium]` `[defer]` `DW-FU-10-1`: `spec-python-agent-platform`'s surface already declares `environment.yaml` (predating this story) while several sibling specs across other BMAD projects that also declare `pixi.toml` don't declare `environment.yaml` alongside it, risking a future misattributed spec-surface drift FAIL. Pre-existing (predates this story's `baseline_revision`); resolving it means editing surface globs this story does not own. Recorded in the station's Tier-3 deferred-work ledger (Blind Hunter, Edge Case Hunter — corroborated, both initially framed it as caused by this pass's allowlist cleanup; verified that framing was incomplete and the true root cause predates this story).
  - reject (no code/spec change — reasoning recorded, not re-justified here): (1) `config/settings/production.py`'s `STORAGES["default"]` uses local `FileSystemStorage` — this is the direct, intended consequence of the spec's own pinned `cloud_provider=None` answer (Boundaries explicitly rule out cloud SDKs); the "statelessness" constraint cited against it is CAP-2's Langflow-specific "no local-disk state," a different capability's contract, not this story's own; (2) the rendered `locale/fr_FR`/`locale/pt_BR` `.po` files reference pre-rename template paths that no longer exist — Blind Hunter itself confirmed this is inherited from the upstream cookiecutter-django tag, not introduced by this story's rename, and functionally inert today; (3) `config/websocket.py` (the stock `use_async=y` ping/pong stub, not authored by this story) crashes on a binary websocket frame via `event["text"]` — stock cookiecutter-django boilerplate, not a defect this story introduced, matching the established precedent for rejecting stock-template behavior; (4) same file's unrecognized-event-type handling is likewise unauthored stock boilerplate, same reasoning; (5) CI doesn't exercise a real Redis connection through `/ht/`'s cache check — a duplicate of the prior review pass's already-rejected finding (local/CI settings deliberately use `LocMemCache`, not `django_redis`; standard cookiecutter-django environment separation, not a defect this story introduced).

## Design Notes

**Pinned cookiecutter-django answers** (`--checkout 2025.07.27`, `-o src`, `--no-input`;
`project_slug` forced to `platform` regardless of the name-derived default, so the render lands
exactly at `src/platform/`):

`project_name=Python Agent Platform`, `project_slug=platform`,
`description=Django host for the python-agent-platform — Langflow and DB-GPT join as pluggable apps`,
`author_name=PyForge Steward`, `domain_name=platform.internal`,
`email=steward@platform.internal`, `version=0.1.0`, `open_source_license=Not open source`
(repo-root Apache-2.0 already governs the monorepo), `username_type=username`, `timezone=UTC`,
`windows=n`, `editor=None`, `use_docker=n` (Story 10.3 owns the real Containerfile),
`postgresql_version=17`, `cloud_provider=None`, `mail_service=Other SMTP`, `rest_api=None`
(the FastAPI seam below covers "FastAPI integration," not DRF/Ninja), `use_async=y`,
`frontend_pipeline=Django Compressor`, `use_celery=y`, `mail_catcher=None`, `use_sentry=n`,
`use_whitenoise=y`, `use_heroku=n`, `ci_tool=None` (this story's own workflow supersedes the
template's), `keep_local_envs_in_vcs=y`, `debug=n`.

If the pinned tag's actual `cookiecutter.json` differs from this key set, preserve the *intent*
per key (no cloud provider; Celery on; no baked-in CI templates; etc.) and map to the closest
equivalent option — record the mapping as an appended note here, don't silently substitute.

**Implementation-time key mapping** (pinned tag `2025.07.27`'s actual `cookiecutter.json` has no
`rest_api` or `mail_catcher` choice lists — those are earlier-era keys this spec's Design Notes
assumed): `rest_api=None` → `use_drf=n` (same intent: no DRF/Ninja); `mail_catcher=None` →
`use_mailpit=n` (same intent: no local mail catcher). All other pinned keys matched exactly.

**Necessary deviation — inner app package renamed `platform` → `platformapp`.** `project_slug=platform`
(pinned, unchanged — the outer root is still exactly `src/platform/`) makes cookiecutter-django
also name the *inner* Django app package `platform`, which shadows the stdlib `platform` module
for the whole process once `src/platform/` is on `sys.path` (stdlib `uuid.py` itself does
`import platform` — this broke `manage.py check`, i.e. AC #1, unconditionally, not a sandbox
artifact). Renamed only the inner package to `platformapp`; every reference updated
(`INSTALLED_APPS`, `urls.py`, `AppConfig.name`, `MIGRATION_MODULES`, allauth adapter/forms
settings, `sys.path` targets in `manage.py`/`asgi.py`/`wsgi.py`, `pyproject.toml`
coverage/importlinter config, docs). Verified clean afterward: `manage.py check`/`migrate`,
full `pytest` suite, `ruff check .`, `lint-imports`, and all three routes (`/`, `/ht/`,
`/api/health`).

**`django-health-check==3.24.0` pinned (not latest 4.x)** — 4.x requires `Django>=5.2`; the
render's own pinned `django==5.1.11` (`# pyup: < 5.2`) is out of this story's scope to bump.
3.24.0 is the newest release compatible with the rendered Django version. Note for a future
story: django-health-check 4.x deprecates the `health_check.db`/`.cache` app-based checks this
story wired up, in favor of view-based checks — currently emits a harmless `DeprecationWarning`
under test, not a functional gap.

**Removed `docker-compose.docs.yml`** (present in the stock render despite `use_docker=n`) during
post-implementation verification — it referenced a `compose/local/docs/Dockerfile` that
`use_docker=n` never generates (dead reference) and, pre-rename, `./platform:/app/platform:z`
(stale). Baked-in Docker scaffolding is explicitly declined by this spec's Never list; removing
a broken, unreferenced leftover is not a scope expansion.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** A prior dev-auto session left `src/platform/**` fully rendered and all
Tasks/ACs satisfied, but bmad-loop's own deterministic verify gate
(`python scripts/spec_surface_reconcile.py`) was failing (123 findings). This repair
session fixed the root cause (`spec-python-agent-platform`'s `SPEC.md` surface
declared the bare directory `src/platform/`, which matches zero git-tracked files,
instead of `src/platform/**`), reconciled the spec's memlog + baseline, bootstrapped
genesis memlog/baseline entries for 8 other pre-existing, unrelated specs that were
blocking the same shared repo-wide gate, then ran a full follow-up review pass
(Blind Hunter + Edge Case Hunter) that found and fixed six low-severity code issues.
Both of bmad-loop's own verify commands now pass cleanly on a committed, clean
worktree.

**Files changed (commit `4e308a98d6ec0880e13a6892cdfcde3aec8aab8a`):**
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/SPEC.md` -- surface glob `src/platform/` -> `src/platform/**` (the root-cause fix)
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md` -- new, records Story 10.1's render + this pass's patches
- `scripts/spec_surface_allowlist.txt` -- removed the now-dead `environment.yaml` exemption line
- `scripts/.spec-surface-baseline.json` -- baseline stamped for 9 specs (spec-python-agent-platform + 8 pre-existing unrelated specs)
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/{spec-bmad-loop-baseline-drift,spec-bmad-loop-intent-gap-work-preservation,spec-bmad-switch-scope-enforcement}/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-scratch-worktree-lifecycle/.memlog.md` -- new genesis memlogs for pre-existing, unrelated draft specs (structural bootstrap only, no code drift, verified predates this story's `baseline_revision`)
- `src/platform/docs/Makefile`, `src/platform/docs/make.bat` -- `APP` var fixed from stale pre-rename `../platform` to `../platformapp`
- `src/platform/pyproject.toml` -- import-linter `root_packages`/`source_modules` now include `tests`
- `src/platform/config/asgi.py` -- lifespan scope now forwards to `fastapi_application` instead of acking locally; bare `/api` (no trailing slash) now routes to FastAPI
- `src/platform/config/fastapi_app.py` -- docstring clarified (HTTP-only path routing, no-`Mount`-prefix convention, `/api/health` vs `/ht/` distinction)
- `.github/workflows/platform-ci.yml` -- removed the redundant standalone import-boundary CI step

**Review findings breakdown (this pass):** 6 patch (all low), 1 defer (medium, `DW-FU-10-1` in the Tier-3 ledger), 5 reject (stock cookiecutter-django boilerplate or duplicates of the prior pass's already-rejected findings), 0 intent_gap, 0 bad_spec. Combined with the prior pass: 17 total patches applied across both review passes.

**Follow-up review recommendation:** false -- this pass's changes are localized, low-severity, and independently verified; not significant enough by volume or consequence to warrant another independent pass.

**Verification performed:** `python scripts/spec_surface_reconcile.py` -> `OK: every tracked file governed or allowlisted; no drift.` (exit 0). `pixi run --frozen -e pyforge-steward pyforge-steward-test` -> `695 passed`. Inside a one-off venv (`virtualenv`-created, since `ensurepip`/`venv` were unavailable in this sandbox) with real PostgreSQL 17 + Redis 7 via Docker: `manage.py check` -> `System check identified no issues (0 silenced)`; full platform `pytest -q` -> `21 passed` (all app tests + the 3 ASGI-seam tests); `ruff check .` -> `All checks passed!`; `mypy platformapp config tests` -> `Success: no issues found in 45 source files`; `lint-imports --config pyproject.toml --no-cache` -> `Contracts: 1 kept, 0 broken` (now analyzing 70 files, up from the narrower pre-patch scope); zero-CDN grep -> no matches. The two code-path edge cases this pass fixed (lifespan forwarding, bare `/api`) had no existing test coverage, so each was manually exercised directly against `config.asgi.application` and confirmed correct.

**Residual risks:** `DW-FU-10-1` (deferred, not this story's to fix) -- `spec-python-agent-platform`'s pre-existing `environment.yaml` surface claim has no counterpart in several sibling specs (other BMAD projects) that also declare `pixi.toml`, risking a future misattributed drift finding against the wrong spec. No other known residual risk; all bmad-loop verify commands and the spec's own Acceptance Criteria are green.
