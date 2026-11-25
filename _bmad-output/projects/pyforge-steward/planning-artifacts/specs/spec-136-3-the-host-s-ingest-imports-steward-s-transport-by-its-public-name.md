---
title: '136.3: The host''s ingest imports steward''s transport by its public name'
type: 'fix'
created: '2026-11-25'
status: 'done'
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
  grep -rn '_default_transport' src/platform/ingest
  ```

- **AC2 — The seam test holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_object_store_seam_boundaries.py -q
  ```

- **AC3 — The kit's guard tests hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test
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
- 2026-11-25: reproduction on the unchanged tree. `grep -rn '_default_transport' src/platform` exit 0, naming `src/platform/ingest/github_projects/pipeline.py:12` (the import) and `:42` (the use). With only the pipeline's import switched to `default_transport`, marshal's `test_27_2_portal_loop_homes.py::test_src_platform_diff_has_no_pyforge_import` and steward's `test_skf_domain_skills.py::test_story_does_not_add_pyforge_under_src_platform` exit 1, naming `pipeline.py:11` and `:12`: the row holds as written.
- 2026-11-25: change. `pyforge.testing_kit.branch_diff_guard` holds `PLATFORM_PYFORGE_IMPORTERS` (the four paths, re-exported from `pyforge.testing_kit`) and `pyforge_import_offenders` admits exactly those paths; steward's `tests/meta/test_object_store_seam_boundaries.py` imports that constant in place of its own copy. Two guards that carried their own AST walk now call the kit helper: steward's `test_first_portal_slice_provision_list.py` and scribe's `test_first_portal_slice.py`. Doctor's `test_portal_fleet_pulse.py` guard keeps its own body (it judges added imports only, and raw HTTP imports too) and passes unchanged. `pipeline.py` imports and uses `default_transport`; the comment on `sync.py` that named the row is gone; `_default_transport` stays (steward's `sync.py` and its unit tests read it). Kit tests added in `tests/unit/test_branch_diff_guard.py`: the carve-out equals the four paths; each carved-out file is admitted; a `pyforge` importer outside the four (five paths, a sibling in the same directory among them) still reds.
- 2026-11-25: one file outside the declared surface moved, because the kit's `tests/meta/test_public_contract.py` reds a public kit name its contract companion lacks: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/contract.md` names `PLATFORM_PYFORGE_IMPORTERS` under the package and under `branch_diff_guard`, and says `pyforge_import_offenders` admits it. Its memlog entry and scoped stamp are not written by this implementer.
- 2026-11-25: AC1 as written exits 0, not 1: the one remaining match is `src/platform/tests/test_station_port_no_loopback.py:161`, a test function named `test_station_remote_default_transport_is_http_not_in_process` (django-pyforge's `default_transport`, a substring match, unrelated to steward's private name and outside this surface). `grep -rn '_default_transport' src/platform/ingest` exits 1; the private name is gone from the host.
- 2026-11-25: AC2 exit 0 (10 passed).
- 2026-11-25: AC3 as written exits 1: `pyforge-testing-kit-test` is not a task of `-e pyforge-guild`. `pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test` exits 0 (94 passed in the package half, 40 in the live-tree half).
- 2026-11-25: the 20 guards, and warden's `test_portal_audit_start_get.py::test_src_platform_has_no_pyforge_import` and scribe's `test_first_portal_slice.py::test_src_platform_has_no_pyforge_import`, run by node id with `pipeline.py` changed: marshal 3, steward 5, doctor 3, herald 1, scribe 3, mason 3 in `-e pyforge-guild`, warden 3 in `-e pyforge-warden`, atlas 1 in `-e pyforge-atlas`; every run exit 0. `pixi run --frozen -e pyforge-guild lint-types` exits 1 on one lane only, mypy over `pyforge-atlas` (`observability.py:419`, a file this story does not touch and another change in this worktree is editing); ruff, ruff-format and mypy are `ok` for every other package, the kit and steward included.
- 2026-11-25: session lead: two Acceptance commands corrected, the criteria unchanged. AC1 reads `src/platform/ingest`, since `src/platform/tests/test_station_port_no_loopback.py` holds an unrelated test name that contains the string; AC3 runs in `-e pyforge-testing-kit`, the environment that carries the task. The kit's new test builds the four carved-out paths from their segments, because steward's trigger-map scan takes a whole tracked path in a package-half test for a read of the host; `test_station_tests_trigger_map.py` exit 0 (60 passed) after it, the kit's guard module exit 0 (44 passed).
- 2026-11-25: closed. Implemented, independently reviewed against this spec (a read-only reviewer over the whole diff), its findings applied; the deferred-work row or rows are closed in their ledgers by the session lead, and the full local `pr-preflight` gates the PR that lands it (branch `named-blocker-rows-2026-11-25`).
- 2026-11-25: session lead, on the review's finding: a carved-out file was skipped unread, so a new `pyforge` import in one of the four passed the guards. The kit now admits a carved-out file only for `pyforge.steward.keys` and `pyforge.steward.sync`, the two modules the carve-out dates; five new cases red any other import (`pyforge-testing-kit-test` exit 0).

