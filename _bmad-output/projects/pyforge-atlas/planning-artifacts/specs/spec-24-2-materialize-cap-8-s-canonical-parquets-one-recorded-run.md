---
title: 'Story 24.2: Materialize CAP-8''s canonical Parquets — one recorded run'
type: 'ops'
created: '2026-09-18'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/docs/dreams/atlas-kedro-catalog-expansion.md'
warnings: []
deferred: []
---

<!--
Contract-spec minted 2026-09-18 from epics.md Story 24.2 Intent + ACs
(ledger key 24-2-materialize-cap-8-s-canonical-parquets-one-recorded-run).
No original story file existed. Re-key 2026-09-17:
25-2-materialize-cap-8-s-canonical-parquets-one-recorded-run → this key.
Ledger status stays blocked (attended, credentialed Artifactory path).
This file does not flip that row.
-->

<intent-contract>

## Intent

**Problem:** Epics 21, 22 and 23 are 100% `done` and the catalog **declares** both
canonical exports — and a declared Kedro dataset is a contract, not data. CAP-8's
success criterion is not exercised until an attended operator materializes
`identity_complete_export.parquet` and `enterprise_jfrog_consumption.parquet`
against live sources.

**Approach:** An attended operator runs the `derived_artifacts` /
`artifactory_downloads` pipelines end to end against live sources with the
Artifactory credentials configured, and records the run as a tracked artifact
(command line, dataset paths, row counts, date). The Dream Realization log cites
that record; `docs/dreams/atlas-kedro-catalog-expansion.md` moves `specified` →
`realized` in the same commit that records the run.

## Boundaries & Constraints

**Always:**
- Read `conf/base/catalog.yml` (`identity_complete_export`,
  `enterprise_jfrog_consumption`) — do not edit the catalog declaration to fake data.
- Record the run under `planning-artifacts/` (command line, dataset paths, row
  counts, date) and cite it from the Dream's Realization log.
- Close `DW-FU-23-5` citing this story; take `DW-D2-3`'s open residual (the
  data-present visual pass) in the same attended session — this run is its
  missing precondition.
- Keep the ledger key `blocked` when the credentialed path is unavailable; do
  not declare success.

**Never:**
- Weaken a gate or fabricate a row to reach green. Honest-empty stays honest.
- Flip the ledger `blocked` row from this mint, or from any unattended run.
- Disagree with `spec-conda-forge-packaging-inventory-operations` about whether
  the attended, credentialed Artifactory path has been met (one precondition,
  two Specs — prose cross-station note only; not a `Deps:` token).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Credentialed attended run | Live sources + Artifactory credentials configured | Both Parquets exist with non-zero rows; run record + Dream `specified` → `realized` in one commit | N/A |
| Credentialed path unavailable | No live Artifactory credentials | Story stays `blocked`; no success declared | Do not fabricate rows |
| Honest-empty live result | Live run returns zero rows | Honest-empty stays honest; no gate weakened | Do not fabricate rows |

</intent-contract>

## Code Map

- `derived_artifacts` / `artifactory_downloads` pipelines — attended live run (read/run, not redesigned)
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` — `identity_complete_export`, `enterprise_jfrog_consumption` (read, not edited)
- tracked run record under `_bmad-output/projects/pyforge-atlas/planning-artifacts/` (new when the attended run happens)
- `docs/dreams/atlas-kedro-catalog-expansion.md` — Realization log + status `specified` → `realized` (same commit as the run record)
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` — close `DW-FU-23-5`; take `DW-D2-3` residual in the same attended session

## Tasks & Acceptance

**Execution:**
- `ops` — attended end-to-end run of the pipelines against live sources with Artifactory credentials configured
- `ops` — write the tracked run record (command line, dataset paths, row counts, date)
- `docs` — cite the run from the Dream Realization log and move the Dream `specified` → `realized` in that same commit
- `docs` — close `DW-FU-23-5` citing this story; take `DW-D2-3`'s data-present visual pass in the same session

**Acceptance Criteria:**

- Given Epics 21, 22 and 23 are 100% `done` and the catalog **declares** both canonical exports — and a declared Kedro dataset is a contract, not data
- When an attended operator runs the pipelines end to end against live sources with the Artifactory credentials configured, and records the run as a tracked artifact (command line, dataset paths, row counts, date)
- Then `identity_complete_export.parquet` and `enterprise_jfrog_consumption.parquet` both exist with non-zero rows, the run record is cited from the Dream's Realization log, and `docs/dreams/atlas-kedro-catalog-expansion.md` moves `specified` → `realized` **in the same commit that records the run**
- And `DW-FU-23-5` closes citing this story, and `DW-D2-3`'s open residual — the data-present visual pass — is taken in the same attended session, because this run is precisely its missing precondition
- And no gate is weakened and no row is fabricated to reach a green: honest-empty stays honest, and if the credentialed path is unavailable the story stays `blocked` rather than declaring success

**Cross-station note** *(prose, deliberately NOT a cross-project `Deps:` token)*: the attended, credentialed Artifactory path this story needs is the **same event** `spec-conda-forge-packaging-inventory-operations` holds itself `in-progress` for ("CAP-2 (17.2) code landed, live-execution verification deferred (attended, credentialed run pending)"). One precondition, two Specs — they must not disagree about whether it has been met.

## Verification

**Commands:**
- Attended (not CI): run `derived_artifacts` and `artifactory_downloads` against live sources with Artifactory credentials configured — expected: both canonical Parquets exist with non-zero rows
- Record the run (command line, dataset paths, row counts, date) under `planning-artifacts/` and cite it from `docs/dreams/atlas-kedro-catalog-expansion.md` in the same commit
- If the credentialed path is unavailable: leave ledger status `blocked`; do not declare success

## Spec Change Log

- 2026-09-18: minted contract-spec from `epics.md` Story 24.2 Intent + ACs. Filename is the exact ledger key after the 2026-09-17 re-key (`25-2-…` → `24-2-…`). Status `blocked` matches the ledger; this mint does not flip that row.
