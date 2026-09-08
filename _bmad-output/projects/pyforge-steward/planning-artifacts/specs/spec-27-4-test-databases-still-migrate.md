---
title: 'Test databases still migrate'
type: 'chore'
created: '2026-08-25'
status: 'done'
baseline_revision: '7baee68ed0d8beefb231e62aefeeb20ec84f3e20'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-27-2-pre-upgrade-job-and-dml-only-app-role.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Production DDL is Liquibase then `migrate --fake` (27.2). If that path leaks into Django's test runner, ephemeral test databases stop applying real migrations and the suite would need a rewrite.

**Approach:** Prove `manage.py test` / pytest still create test DBs with Django `migrate` (not Liquibase, not `--fake`). Add a policy/invariant test that reds if test settings or the runner are pointed at Liquibase or `--fake`. Leave Helm Jobs as 27.2. Do not rewrite the suite.

## Boundaries & Constraints

**Always:** `TEST_RUNNER` remains `django.test.runner.DiscoverRunner`. `BaseDatabaseCreation.create_test_db` still `call_command("migrate", …)` without `--fake`. pytest-django still calls `setup_databases` with migrations on (no `--nomigrations` in platform addopts). Compose/local still `manage.py migrate --noinput` without `--fake`. Helm stays Liquibase weight −1 then `migrate --fake`. Spec at `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`.

**Block If:** A change would rewrite existing tests or reopen 27.3 sqlmigrate extraction.

**Never:** Suite rewrite. Helm `liquibase-job.yaml` / `migrate-job.yaml` edits. 27.3 extraction rewrite. Fifth schema. `import pyforge` under `src/platform/`. Recipes. CRC. `scripts/bmad-switch`. Story 12-7.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Live test settings + Django `create_test_db` + pytest-django `django_db_setup` + compose migrate + Helm Job templates | Policy green: test path is real `migrate`; production Jobs still Liquibase −1 then `migrate --fake` | No error expected |
| Runner pointed at Liquibase | Synthetic `TEST_RUNNER` / test.py / conftest / addopts containing liquibase | Assertion fails naming Liquibase | AssertionError |
| Test migrate --fake | Synthetic test settings or create_test_db source with `--fake` / `fake=True` | Assertion fails naming `--fake` | AssertionError |
| nomigrations | pytest addopts includes `--nomigrations` | Assertion fails | AssertionError |
| Production Jobs drifted | Helm templates drop `--fake` or Liquibase −1 | Assertion fails (27.2 contract) | AssertionError |

</intent-contract>

## Code Map

- `src/platform/config/settings/test.py` -- `TEST_RUNNER = django.test.runner.DiscoverRunner`; comment the canopy:FR-25 carve-out; do not set `TEST["MIGRATE"] = False`
- `src/platform/conftest.py` -- session env only; must not invoke Liquibase
- `src/platform/pyproject.toml` -- `addopts` `--ds=config.settings.test --reuse-db`; must not add `--nomigrations`
- `src/platform/compose/compose.yml` -- local `manage.py migrate --noinput` (no `--fake`)
- `src/platform/deploy/charts/platform/templates/liquibase-job.yaml` -- READ-ONLY 27.2 weight `-1` / `db/liquibase_update.py`
- `src/platform/deploy/charts/platform/templates/migrate-job.yaml` -- READ-ONLY 27.2 `migrate --fake --noinput`
- `src/platform/tests/policy/test_test_databases_still_migrate.py` -- NEW: live inspect + synthetic reds
- `django.db.backends.base.creation.BaseDatabaseCreation.create_test_db` -- live source: `call_command("migrate", …)` without fake
- `pytest_django.fixtures.django_db_setup` -- live source: `setup_databases`; `_disable_migrations` only when `--nomigrations`
- Read-only: `db/sqlmigrate_extraction.py`, `tests/policy/test_sqlmigrate_extraction.py`, `recipes/`

## Tasks & Acceptance

**Execution:**
- `src/platform/config/settings/test.py` -- annotate canopy:FR-25; keep DiscoverRunner
- `src/platform/tests/policy/test_test_databases_still_migrate.py` -- matrix rows (happy + four reds)

**Acceptance Criteria:**
- Given the test runner, when it creates a test database, then it still runs Django `migrate`
- Given this epic, when the suite is considered, then no test-suite rewrite is required
- Given Helm Jobs, when this PR is reviewed, then they still match 27.2 (Liquibase −1, `migrate --fake`)
- Given test settings or the runner pointed at Liquibase or `--fake`, when the policy test runs, then it fails

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Implementation self-review (dispatch; no nested reviewers)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - ruff F401/E501 on the new policy module (unused Path import, line length).
  - Confirmed: TEST_RUNNER stays DiscoverRunner; create_test_db still call_command("migrate") without fake; pytest-django django_db_setup still setup_databases and addopts have no --nomigrations; compose still real migrate; Helm Jobs unchanged (Liquibase −1, migrate --fake). Synthetic reds cover Liquibase runner, --fake, nomigrations, and Helm dropping --fake. Did not rewrite the suite, reopen 27.3, or start 12-7. No `import pyforge` under `src/platform/`. No recipes.

## Auto Run Result

Status: done
Tests: `pytest tests/policy/test_test_databases_still_migrate.py` → 9 passed (cwd src/platform)

## Design Notes

Governed production DDL does not capture ephemeral DBs (canopy:FR-25, canopy:AD-9 last sentence). Proof is source + settings inspection plus synthetic drift — not creating a second test database or rewriting `tests/`. Compose remains the local real-migrate path; Helm remains the fake-after-Liquibase path.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
