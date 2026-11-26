---
title: '54.1: Atlas''s exit codes are held to their declared domain, and its status page reads the tracked ledger'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 54-1-atlas-s-exit-codes-are-held-to-their-declared-domain-and-its-status-page-reads-the-tracked-ledger
spec: spec-pyforge-atlas
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-atlas/tests/meta/test_exit_codes_match_the_exit_declaration.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/factory_status.py'
  - 'src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_factory_status.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/admission.py'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/dreams/pyforge-atlas.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Atlas's exit codes were left out of the one exit-code declaration. The factory-status page's default status file is the gitignored Tier-3 feed, absent from a fresh clone and CI. `admission.py` says seven MCP `run_*` tools.

**Approach:** Add a package-half meta-test for the `atlas` domain. Point `_default_paths()` at the tracked ledger (the same `development_status` shape) and label each row with the name of the file read. Remove the count from `admission.py`'s docstrings and message.

Ledger key: `54-1-atlas-s-exit-codes-are-held-to-their-declared-domain-and-its-status-page-reads-the-tracked-ledger`.

### Living CAP citations

- spec-pyforge-steward:CAP-184 (amended 2026-11-26; the declaration this story binds to).
- spec-pyforge-steward:CAP-184 (the declaration; amended 2026-11-26) and spec-pyforge-atlas CAP-69 (the Vizro boards; realized, no text change).

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every exit number the station returns today.

**Never:**
- Never change an exit number.
- Never edit the SKF-compiled station skill.

## Acceptance Criteria

**Given** atlas's exit codes are declared only in atlas, the factory-status page defaults to the gitignored Tier-3 feed, and `admission.py` counts seven `run_*` tools
**When** the meta-test is added, the page's default is the tracked ledger, and the count is removed
**Then** the test fails when `EXIT_USAGE` differs from the `atlas` domain; `_default_paths()` names `planning-artifacts/sprint-status-ledger.yaml`; a row's `source` is the name of the file read
**And** no exit number changes, an injected path still wins, and a missing file still contributes no rows

- **AC1 — Atlas's meta-test and factory-status tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/meta/test_exit_codes_match_the_exit_declaration.py src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_factory_status.py -q
  ```

- **AC2 — Atlas's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent and not the implementer's reasoning. Fourteen findings; all accepted and applied in the same change. For this story: the integration test that pinned the old default path now pins the tracked ledger (the live-tree lane would have gone red); a unit test holds the row label; the status card names the tracked ledger; the meta-test also holds every literal code the entry point spells; the declaration says `pyforge atlas` itself exits 0, 1 or 2 and that 130 is the station's other entry points'. Not covered by any test: a code Click or Kedro chooses at run time.
