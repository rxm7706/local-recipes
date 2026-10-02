---
title: "83.3: The platform chart and the compose stack run a Postgres image that carries pgvector"
type: 'fix'
created: '2026-10-02'
status: 'in-review'
baseline_revision: '454df87fbce80f0f67bcdbc8af7b6e0ccafa149a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md
  - docs/dreams/pyforge-steward.md
  - src/platform/deploy/charts/platform/values.yaml
  - src/platform/compose/compose.yml
  - src/platform/tests/test_chart_invariants.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The bundled PostgreSQL has no pgvector, verified at HEAD a7cdb91fe4.
`src/platform/deploy/charts/platform/values.yaml:229-234` defaults `postgres.image` to `registry: ""`,
`repository: postgres`, `tag: "17"`, and
`src/platform/compose/compose.yml:43` runs `image: postgres:17`; `grep -rni pgvector src/platform/deploy
src/platform/compose` finds nothing. The Liquibase Job is an unconditional `post-install,pre-upgrade` hook
(`templates/liquibase-job.yaml:14`) that applies the master changelog, including
`src/platform/db/changelog/changes/pyforge-scribe-1-pgvector-extension.sql` (`CREATE EXTENSION IF NOT EXISTS vector;`).
On the stock image that statement fails with `could not open extension control file "vector.control"`, so every install
and upgrade of the chart fails, including estates that never deploy scribe (DW-FU-41-3-9).

**Approach:**

- `values.yaml`: `postgres.image.repository: pgvector/pgvector`, `tag: "pg17"`, the image CI already runs as a service
  container (`.github/workflows/pyforge-station-tests.yml:284`, `.github/workflows/coverage-gates.yml:133`). The
  `registry` override and `platform.imageRef` stay as they are, so an air-gapped estate mirrors the same image.
- `compose.yml`: the `postgres` service runs `pgvector/pgvector:pg17`.
- `test_chart_invariants.py`: a chart test renders the chart and asserts the PostgreSQL StatefulSet's image is
  `pgvector/pgvector:pg17`. The AD-1 inventory test derives its references from `values.yaml`
  (`_default_image_references`, `:258-279`) and follows the change; the synthetic inventory fixtures that name
  `postgres:17` (`:3342`, `:3365`, `:3939`) are inputs to helper tests and need no change unless they assert the default.

Ledger key: `83-3-the-platform-chart-and-the-compose-stack-run-a-postgres-image-that-carries-pgvector`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-unifying-strategy` CAP-9 (schema change is governed: the changelog owns `CREATE EXTENSION`) and CAP-14
  (scribe's graph store on PostgreSQL/pgvector), both shipped by Story 41.3; canopy:AD-9 (the Liquibase pre-upgrade
  Job). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the chart's default values When `helm template` renders it Then the PostgreSQL StatefulSet's container image is `pgvector/pgvector:pg17`
- Given `postgres.image.registry` set to a mirror When the chart renders Then the image is `<mirror>/pgvector/pgvector:pg17`
- Given `compose.yml` When its `postgres` service is read Then its image is `pgvector/pgvector:pg17`
- Given the AD-1 image-inventory test When it runs Then it passes with the pgvector repository in place of `postgres`
- Given `values.yaml` reverted to `postgres:17` When the new chart test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:**
- PostgreSQL stays at major version 17 (the estate's pin; fnd:CAP-12).
- The image stays overridable through `postgres.image.registry` / `repository` / `tag`.
- `templates/keycloak-db-init-job.yaml:34` reuses `postgres.image`; the pgvector image is the official PostgreSQL 17
  image plus the extension, so that Job keeps its `psql`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not raise any PostgreSQL pin to 18.
- Do not guard or remove `pyforge-scribe:1`, and do not move `CREATE EXTENSION` out of the changelog.
- Do not delete or loosen any chart test.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/values.yaml:229-234` -- `postgres.image` default; the one chart edit (`repository`, `tag`). Comment on `:228` says "official image"; adjust.
- `src/platform/deploy/charts/platform/templates/postgres-statefulset.yaml:58` and `keycloak-db-init-job.yaml:34` -- both render `platform.imageRef` over `postgres.image`; no template edit.
- `src/platform/compose/compose.yml:43` -- `image: postgres:17`; header comment `:2` names `postgres:17` as history, leave it.
- `src/platform/tests/test_chart_invariants.py:2239` -- `_render(_CORE_CHART, release="platform")` pattern for the new test; `:2909` AD-1 inventory test reads `_default_image_references()` (`:258`) from `values.yaml`, so it follows with no edit; `:3342/:3365/:3939` synthetic fixtures stay.
- `.github/workflows/platform-ci.yml:1642-1657` -- air-gap smoke pulls and `kind load`s `postgres:17` as "the chart's default infra image". After the change the chart asks for `pgvector/pgvector:pg17`, which an air-gapped node cannot pull: this step must load the new image (ripple of the change, not new scope). `:180` and `:385` are the test job's own service/engine containers (no changelog run: `grep liquibase` empty) and stay.
- `docs/explanation/platform-deployment-architecture.md:107` -- names `postgres:17` StatefulSet; update to the new image.
- `helm` is absent from this worktree's PATH; `.pixi/envs/platform-dev/bin/helm` exists in the shared checkout (read-only use).

## Tasks & Acceptance

**Execution:**
- `src/platform/deploy/charts/platform/values.yaml` -- `postgres.image.repository: pgvector/pgvector`, `tag: "pg17"`; fix the "official image" comment -- the bundled PostgreSQL must carry `vector.control`
- `src/platform/compose/compose.yml` -- `postgres` service `image: pgvector/pgvector:pg17` -- same extension need in the dev stack
- `src/platform/tests/test_chart_invariants.py` -- add `test_postgres_statefulset_runs_the_pgvector_image` (default render asserts `pgvector/pgvector:pg17`; a `postgres.image.registry=<mirror>` render asserts `<mirror>/pgvector/pgvector:pg17`) and a compose-file assertion on the `postgres` service image -- mutation: reverting `values.yaml` fails it
- `.github/workflows/platform-ci.yml` -- air-gap smoke pull / `kind load` / comment name `pgvector/pgvector:pg17` -- the chart's default image changed
- `docs/explanation/platform-deployment-architecture.md` -- `postgres:17` becomes `pgvector/pgvector:pg17` -- stale doc line

**Acceptance Criteria:**
- Given the chart's default values, when `helm template` renders it, then the PostgreSQL StatefulSet container image is `pgvector/pgvector:pg17`
- Given `postgres.image.registry` set to a mirror, when the chart renders, then the image is `<mirror>/pgvector/pgvector:pg17`
- Given `compose.yml`, when its `postgres` service is read, then its image is `pgvector/pgvector:pg17`
- Given the AD-1 image-inventory test, when it runs, then it passes with the pgvector repository in place of `postgres`
- Given `values.yaml` reverted to `postgres:17`, when the new chart test runs, then it fails

## Spec Change Log

## Binding

Parent capabilities: `spec-pyforge-unifying-strategy` CAP-9, CAP-14 (Story 41.3) (defect of shipped behaviour; no new
CAP).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-02 entry.
Closes: DW-FU-41-3-9.
Ledger key: `83-3-the-platform-chart-and-the-compose-stack-run-a-postgres-image-that-carries-pgvector`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 by operator ruling: start Phase 2 of the deferral burn-down after the inflow wave.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass, the chart tests run with helm, none skipped.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
