---
title: '136.3: The host''s ingest imports steward''s transport by its public name'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
story: 136-3-the-host-s-ingest-imports-steward-s-transport-by-its-public-name
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/platform/ingest/github_projects/pipeline.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py'
  - 'src/shared/packages/pyforge-testing-kit/**'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_object_store_seam_boundaries.py'
  - 'src/shared/packages/pyforge-*/tests/**'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-cutover-2026-11-10-3`. `src/platform/ingest/github_projects/pipeline.py:12` imports the private `pyforge.steward.sync._default_transport`; `sync.py:472` has bound the public `default_transport` since Story 123.2. The 20 diff guards in the eight station suites (`test_story_does_not_add_pyforge_under_src_platform`, and marshal's `test_src_platform_diff_has_no_pyforge_import`) red on any changed `src/platform` file that imports `pyforge`, with no carve-out, so the one-line fix cannot land.

**Approach:** Give the guards the four-file carve-out once, in the testing kit's shared helper the guards call (`pyforge_import_offenders` or its caller), reading the same four paths steward's `test_object_store_seam_boundaries.py` holds, so no guard body is copied 20 times; a carved-out file is admitted only while it is on that list, and any other `src/platform` importer still reds. Then switch the import to `default_transport` and remove the comment on `sync.py` that names this row. Keep `_default_transport` if anything else reads it.

Ledger key: `136-3-the-host-s-ingest-imports-steward-s-transport-by-its-public-name`.

### Living CAP citations

- spec-pyforge-steward CAP-182 (the public name `default_transport`; realized, no text change) and pap:AD-2 (the host never imports `pyforge.*`; the dated carve-out DW-steward-74-1 stands and only shrinks); reads `spec-pyforge-core` (the testing kit's diff guard; no text change).

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never add a fifth path to the carve-out.
- Never weaken the guard for a file outside `src/platform/ingest/github_projects/`.
- Never add a new `pyforge` import under `src/platform/`.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-cutover-2026-11-10-3` reports that the host pipeline imports steward's private `_default_transport`, and that every station suite's diff guard refuses any edit of that file
**When** the kit's diff guard admits the four carved-out files and nothing else, and the pipeline imports `default_transport`
**Then** the pipeline imports the public name, every one of the 20 guards passes on this branch, a test shows the guard still reds a changed `src/platform` file outside the four that imports `pyforge`, and the allowlist is written in one place two tests read
**And** the carve-out does not grow: the four paths are the four of `PLATFORM_PYFORGE_IMPORTERS`, and the row reads resolved under DW-steward-74-1, which stays open

- **AC1 — The private name is gone from the host.** Expected: exit 1 (no line matches).

  ```bash
  grep -rn '_default_transport' src/platform
  ```

- **AC2 — The seam test holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_object_store_seam_boundaries.py -q
  ```

- **AC3 — The kit's guard tests hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pyforge-testing-kit-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-182 (the public name `default_transport`; realized, no text change) and pap:AD-2 (the host never imports `pyforge.*`; the dated carve-out DW-steward-74-1 stands and only shrinks); reads `spec-pyforge-core` (the testing kit's diff guard; no text change).
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-3-the-host-s-ingest-imports-steward-s-transport-by-its-public-name`.
- Deferred-work row: `DW-steward-cutover-2026-11-10-3`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
