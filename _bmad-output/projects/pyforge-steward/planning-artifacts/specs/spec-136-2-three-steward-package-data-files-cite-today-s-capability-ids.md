---
title: '136.2: Three steward package-data files cite today''s capability ids'
type: 'fix'
created: '2026-11-25'
status: 'in-review'
story: 136-2-three-steward-package-data-files-cite-today-s-capability-ids
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/data/sprint-ledger-query.schema.json'
  - 'src/shared/packages/pyforge-steward/measures/measures.yaml'
  - 'src/shared/packages/pyforge-steward/catalog/catalog.yaml'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md'
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

**Problem:** `DW-steward-122-4-1`. `sprint-ledger-query.schema.json:5` cites `spec-sprint-ledger-query-module CAP-4` (today spec-pyforge-steward:CAP-148), `measures/measures.yaml:1` cites `spec-build-league-scorecard CAP-2` (today CAP-45) and `catalog/catalog.yaml:1` cites `spec-self-hosted-bmad-marketplace CAP-1` (today CAP-117). `oracle-map.md`'s CAP-179 row note still says `test_cap_citations.py` holds help and output only, though since Story 122.4 it also holds every comment and docstring under the package's `src` and `tests`.

**Approach:** Re-key the three citations by the provenance map `test_cap_citations.py` already holds, extend that test to read these three files so the ids cannot drift back, check whether a consumer pins the schema's `description` text before changing it, and amend the oracle-map note.

Ledger key: `136-2-three-steward-package-data-files-cite-today-s-capability-ids`.

### Living CAP citations

- spec-pyforge-steward CAP-179 (the public contract and the ids the package cites; realized, no text change; its `oracle-map.md` row note is amended); reads CAP-148, CAP-45 and CAP-117 (no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change a schema key, a measure or a catalog entry; only the citing comment or description moves.
- Never change the schema's `$id`.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-122-4-1` reports three package-data files that cite an absorbed Spec's capability id and an `oracle-map.md` note that understates what `test_cap_citations.py` holds
**When** each citation is re-keyed to the station Spec's id by the provenance map and the test reads the three files
**Then** no file under the steward package cites `spec-sprint-ledger-query-module`, `spec-build-league-scorecard` or `spec-self-hosted-bmad-marketplace` as a live id, the three files cite spec-pyforge-steward:CAP-148, CAP-45 and CAP-117, and a test fails when one of them cites an absorbed Spec again
**And** `oracle-map.md`'s CAP-179 row note says the test holds help, output, comments, docstrings and the three data files, and the row reads resolved

- **AC1 — No absorbed-Spec id is left in the three files.** Expected: exit 1 (no line matches).

  ```bash
  grep -n -E 'spec-sprint-ledger-query-module CAP|spec-build-league-scorecard CAP|spec-self-hosted-bmad-marketplace CAP' src/shared/packages/pyforge-steward/src/pyforge/steward/data/sprint-ledger-query.schema.json src/shared/packages/pyforge-steward/measures/measures.yaml src/shared/packages/pyforge-steward/catalog/catalog.yaml
  ```

- **AC2 — The citation test holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-179 (the public contract and the ids the package cites; realized, no text change; its `oracle-map.md` row note is amended); reads CAP-148, CAP-45 and CAP-117 (no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-2-three-steward-package-data-files-cite-today-s-capability-ids`.
- Deferred-work row: `DW-steward-122-4-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: reproduced `DW-steward-122-4-1` on the unchanged tree: AC1's grep exited 0 with three lines (`sprint-ledger-query.schema.json:5` citing `spec-sprint-ledger-query-module CAP-4`, `measures/measures.yaml:1` citing `spec-build-league-scorecard CAP-2`, `catalog/catalog.yaml:1` citing `spec-self-hosted-bmad-marketplace CAP-1`); `oracle-map.md`'s CAP-179 note named help and output only. `SPEC.md`'s provenance lines confirm CAP-148, CAP-45 and CAP-117 as the re-keys.
- 2026-11-25: consumer check: no code, test or workflow reads or pins the schema's `description` text; the only pin is the file's hash in `scripts/.spec-surface-baseline.json` (two governors), which the lead's scoped stamp moves. `$id` and every schema key, measure and catalog entry are unchanged; the schema still parses as JSON.
- 2026-11-25: implemented: the three citations now read `spec-pyforge-steward:CAP-148`, `spec-pyforge-steward:CAP-45` and `spec-pyforge-steward:CAP-117`. One more comment in `catalog/catalog.yaml` (line 69, `spec CAP-5 / CAP-121`, the absorbed marketplace Spec's fifth id beside today's) is collapsed to `spec-pyforge-steward:CAP-121`, a re-key the provenance map holds. `test_cap_citations.py` gains `DATA_FILE_CAPABILITIES`, `data_file_findings`, `test_package_data_files_cite_todays_ids` and a `fires` test (an absorbed Spec cited again, an undefined id, the file's own capability not cited qualified), and three `MODULE_FAMILIES` entries so the re-key guard reads the three files' changed lines. `oracle-map.md`'s CAP-179 note names help, output, comments, docstrings and the three data files.
- 2026-11-25: AC1 exit 1 (no line matches). AC2 exit 1: 16 passed, 1 failed, and the failure is not this story's: `test_comments_and_docstrings_cite_todays_ids` names `tests/meta/test_steward_persona.py:250`, a comment Story 136.4 added in this worktree that cites a bare `CAP-15`. With that one test left out (`-k`), the module exits 0 (16 passed), this story's two new tests and `test_rekey_pairs_follow_the_provenance_map` among them. AC2 needs a re-run once Story 136.4 qualifies that comment.
- 2026-11-25: `lint-types`: ruff, ruff-format and mypy `ok` for pyforge-steward (the task exits 1 on `pyforge-atlas` mypy, another story's file). `test_sprint_ledger_query.py`, `test_catalog.py` and `test_public_contract.py` pass; `pyforge-steward-test` (the package half) exit 0. `test_station_tests_trigger_map.py` has two failures naming `src/platform/ingest/github_projects/*` read from `pyforge-testing-kit/tests/unit/test_branch_diff_guard.py`, neither file this story's. Left for the session lead: the `DW-steward-122-4-1` row, the memlog reconcile and the scoped stamps.
