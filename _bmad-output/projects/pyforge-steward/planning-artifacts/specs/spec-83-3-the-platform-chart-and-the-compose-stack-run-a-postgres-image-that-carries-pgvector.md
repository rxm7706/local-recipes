---
title: "83.3: The platform chart and the compose stack run a Postgres image that carries pgvector"
type: 'fix'
created: '2026-10-02'
status: 'done'
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

### 2026-10-02 — Review pass
- verdicts: 23 findings — high 0, medium 5, low 15, false 3, maybe-false 0
- findings:
  - Blind Hunter
    - `[medium]` `[patch]` The DW row is not closed (epics.md AC and Binding say "Closes: DW-FU-41-3-9"; ledger row still `open`) — `deferred-work-ledger.md` row closed with `resolution:` and `verified:` in the Story 83.1 format, citing the live changeset run.
    - `[low]` `[patch]` The "swap the image" guidance omits pgvector — one sentence added to the swap bullet in `docs/explanation/platform-deployment-architecture.md`. The `values.yaml` comments that say "OFFICIAL postgres image" (`dataMountPath`, `runAsUser`) stay: checked live, `pgvector/pgvector:pg17` has the same `PGDATA` (`/var/lib/postgresql/data`) and uid 999 as stock `postgres:17`, so they remain accurate.
    - `[low]` `[patch]` The bring-your-own PostgreSQL path has the same failure and is undocumented — pre-existing gap, fixed now under the fix-now default: prerequisite sentence added to `src/platform/deploy/overlays/external-postgres/README.md`.
    - `[low]` `[reject]` No test or CI step shows the bundled database accepts `CREATE EXTENSION vector` — the live run was done 2026-10-02 (changeset exit 0 on `pgvector/pgvector:pg17`, `vector 0.8.7`; exit 3 with the `vector.control` error on stock `postgres:17`); scribe's own CI suites already run this image (`pyforge-station-tests.yml:284`); a docker-backed chart test is new infrastructure, more than a direct correction, and a regression to the stock image is already caught by the two new tests.
    - `[low]` `[reject]` The helper test is brittle and narrow — strict `[expected]` equality and the `(doc.get("metadata") or {})` idiom match the file's existing `_assert_postgres_backup_cronjob_present`; a later sidecar is speculative; the keycloak-db-init Job renders the same image through the same `platform.imageRef` (the verification-gap layer rendered a mirror and saw both).
    - `[low]` `[reject]` CI still runs the app against stock `postgres:17` (`platform-ci.yml:180`, `:385`) — neither job applies the changelog (the only `liquibase` match in the file is a comment), so no failure occurs; switching unrelated CI lanes is not required by the intent's Approach.
    - `[low]` `[reject]` Image provenance and pinning are loose; the comment overclaims "official" — the tag `pg17` is fixed by the intent contract; `postgres.image.digest` already pins (`platform.imageRef` prefers a digest), so an estate that wants a pinned image has the knob; the comment repeats the contract's own phrase and the image is built on the Debian PostgreSQL 17.11 image (checked live).
    - `[medium]` `[patch]` No upgrade check or note for an existing PVC — verified live 2026-10-02: a volume initialised by stock `postgres:17` starts under `pgvector/pgvector:pg17` and reads fine, then PostgreSQL logs `database "platform" has a collation version mismatch` (2.41 vs 2.36, Debian 13 vs Debian 12). Documented in the new upgrade bullet; `values.yaml` comment points to it.
    - `[false]` `[reject]` Nothing shows the helm-gated test ran — it ran: helm 4.3.0 on `PATH`, `CI` unset, 127 passed with `-rs` showing no skips, and the mutation run (values reverted) failed both new real tests; recorded under `## Auto Run Result`.
  - Edge Case Hunter
    - `[medium]` `[patch]` Upgrade of a release still on stock `postgres:17`: the `pre-upgrade` Liquibase hook (weight -1) runs before the StatefulSet rolls and fails on the old pod — true by Helm's hook ordering; one-time `helm upgrade --no-hooks` step documented in the new bullet.
    - `[low]` `[patch]` Documented OCP/Bitnami swap advice omits pgvector — same defect as the Blind Hunter swap-guidance finding; same fix.
    - `[low]` `[patch]` External overlay does not state the vector prerequisite — same defect as the Blind Hunter bring-your-own finding; same fix.
    - `[medium]` `[patch]` Floating `pg17` tag and a different base OS can break an in-place swap on an existing PVC — the glibc half is the Blind Hunter PVC finding (verified live, documented); the floating-tag half is rejected for the reason on the pinning row (tag fixed by the contract, digest override exists).
    - `[low]` `[reject]` The compose test should assert no `digest` default — speculative: `values.yaml` has no `postgres.image.digest` key today and a future digest default is a new change with its own test; the guard adds a branch for a state not shown.
    - `[medium]` `[patch]` The claim "every install and upgrade" is fixed only on the install path in one step — same defect as the hook-ordering finding; same fix.
  - Verification Gap Reviewer (other findings)
    - `[low]` `[reject]` `_default_image_references()` derives the AD-1 inventory from `values.yaml`, so that test passes with either repository — true and intended by the contract ("follows the change"); the pins are the two new tests, which fail under the mutation.
    - `[low]` `[patch]` The fix covers only the bundled PostgreSQL; the external overlay's prerequisites never mention `vector` — same defect as the Blind Hunter bring-your-own finding; same fix.
  - Intent Alignment Auditor (divergences)
    - `[low]` `[reject]` The runtime outcome (`vector.control` present, changelog applies) is untested at the chart-test surface — the live run 2026-10-02 supplies it; see the Blind Hunter row on the same claim.
    - `[false]` `[reject]` Whether the gke/ocp/air-gap smoke jobs assert Liquibase completion is unverified — the reviewer states no bad outcome; `helm install` waits for hook Jobs, so a failing changelog fails those installs, and the air-gap job fails on `ImagePullBackOff`/`ErrImagePull`, which the changed preload step prevents.
    - `[low]` `[reject]` The keycloak-db-init Job has no assertion — see the Blind Hunter helper-test row; the contract's AC names the StatefulSet only.
    - `[low]` `[patch]` The external-Postgres overlay still runs the hook against the operator's database and its docs are silent — same defect as the Blind Hunter bring-your-own finding; same fix.
    - `[false]` `[reject]` `compose.yml` runs `migrate`, not Liquibase, so the compose change is parity rather than a fix — a true observation with no bad outcome; the contract asks for the compose image change.
    - `[low]` `[reject]` `platform-ci.yml:180` and `:385` still run `postgres:17` — see the CI row above.

## Auto Run Result

Status: done

**Summary.** The chart's `postgres.image` default and the compose `postgres` service now run `pgvector/pgvector:pg17` (PostgreSQL stays 17; `registry`/`repository`/`tag`/`digest` still override). The Liquibase hook's `pyforge-scribe:1` changeset therefore finds `vector.control`. Run live 2026-10-02: the changeset exits 0 on `pgvector/pgvector:pg17` (`vector 0.8.7` created) and exits 3 with the `vector.control` error on stock `postgres:17`.

**Files changed.**
- `src/platform/deploy/charts/platform/values.yaml` -- `postgres.image` is `pgvector/pgvector` / `pg17`; comment explains why and points to the upgrade note.
- `src/platform/compose/compose.yml` -- `postgres` service image is `pgvector/pgvector:pg17`.
- `src/platform/tests/test_chart_invariants.py` -- `test_postgres_statefulset_runs_the_pgvector_image` (default and mirror render), `test_compose_postgres_service_runs_the_pgvector_image` (no helm needed), and a guard-removed companion; no existing test changed.
- `.github/workflows/platform-ci.yml` -- the air-gap smoke step pulls and `kind load`s `pgvector/pgvector:pg17`.
- `docs/explanation/platform-deployment-architecture.md` -- stale image line; replacement `postgres.image` must carry pgvector; new bullet for upgrading a release that already runs stock `postgres:17`.
- `src/platform/deploy/overlays/external-postgres/README.md` -- the external PostgreSQL must provide the `vector` extension.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` -- DW-FU-41-3-9 closed.
- `.memlog.md` of `spec-pyforge-unifying-strategy` and `spec-pyforge-doctor` -- surface reconcile entries naming the governed paths (`platform-ci.yml` and the ledger have no Spec surface). No baseline stamped.

**Review findings.** 23 findings; 5 grouped patch entries applied (3 medium, 2 low); 0 deferred; the rest rejected with the reasons in `## Review Triage Log`.

**Follow-up review recommended: true.** Three medium entries were patched. The unverified risk: the `helm upgrade --no-hooks` two-step upgrade procedure in the new docs bullet follows from Helm's hook ordering and was never run against a cluster.

**Verification.**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- exit 0, 1926 passed, 5 skipped.
- `pixi run --frozen -e pyforge-guild platform-ci-local -- --test` -- exit 0, every stage PASS.
- `tests/test_chart_invariants.py` + `tests/test_helm_gate.py` with helm 4.3.0 on `PATH`, `CI` unset -- exit 0, 127 passed, none skipped (run before and after the review patches).
- Mutation: `values.yaml` set back to `postgres` / `"17"` -- both new real tests failed; the file was restored.
- `python scripts/spec_surface_reconcile.py` -- exit 0; `deferred-work-check` and `story-status-check` -- exit 0.
- Live image checks (docker): changeset on both images; a volume initialised by stock `postgres:17` started under the pgvector image.

**Residual risks.** `pr-preflight` was not run. The air-gap CI edit can be proven only in GitHub Actions (needs docker and kind). The `helm upgrade --no-hooks` procedure is documented, not executed.
