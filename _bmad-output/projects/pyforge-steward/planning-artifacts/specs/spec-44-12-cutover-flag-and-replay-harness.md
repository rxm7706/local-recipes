---
title: 'Cutover flag and replay harness'
type: 'feature'
created: '2026-09-13'
status: 'done'
difficulty: medium
story: 44.12
spec: python-foundry-cutover
surface: ["src/shared/packages/pyforge-steward/**", "src/shared/packages/pyforge-core/**", "src/platform/config/flags.json", "src/platform/tests/test_openfeature_file_flags.py"]
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Foundry exists, but there is no flag reader and no replayable
cutover plan. Every later fold/move would be a hand copy that cannot be
re-run after `local-recipes` keeps moving.

**Approach:** Land `pyforge.cutover_root` on the local-recipes flag tree
(same shape as foundry's epoch file). Host reads it in-process; CLIs read
it through a `pyforge-core` reader. Add `steward cutover plan
--regenerate|--append` and `steward cutover apply --phase <n>` that
preserve `moved` rows and are idempotent. A flip while any Marshal loop is
running is refused and, when allowed, is recorded in the Dream Realization
log. Do not flip the default to `foundry` in this Story.

## Boundaries & Constraints

**Always:**
- Default variant stays `local-recipes` (`fnd:AD-17`).
- `--regenerate` and `--append` preserve `moved` rows (test on status).
- `apply --phase` is idempotent when re-run against the same foundry tree.
- 44.1 stays `blocked`: this harness does not claim 100% of tracked paths
  or the scored capability ledger. Regenerated rows cover the trees later
  phases apply (packages, estate, factory island), plus identity/secret
  kinds when the rule matches.

**Never:**
- Never flip `pyforge.cutover_root` to `foundry`.
- Never dispatch 44.8 / 44.9 / 44.10 / 44.11 / 44.15.
- Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.
- Never commit on the shared primary checkout.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CLI reads flag | `flags.json` default | `local-recipes` | Missing file / unknown variant is a named fail |
| Host reads flag | in-process OpenFeature tree | same default | same |
| plan --regenerate twice | existing `moved` rows | those rows kept | n/a |
| plan --append | new paths since `source_sha` | delta folded; `moved` kept | n/a |
| apply --phase twice | same foundry dest | second run no-ops | n/a |
| flip while loop running | live marshal session | refuse | named fail, no write |
| flip when idle | operator-attended (later) | Realization log stamp | n/a |

</intent-contract>

## Code Map

- `src/platform/config/flags.json` — add `pyforge.cutover_root`.
- `src/shared/packages/pyforge-core/` — flag reader used by CLIs.
- `src/shared/packages/pyforge-steward/` — `cutover` duty (`plan` / `apply`).
- Foundry dest default: sibling `python-foundry` or `CUTOVER_FOUNDRY_ROOT`.

## Acceptance Criteria

1. Host and `pyforge-core` reader agree on `pyforge.cutover_root`; default `local-recipes`.
2. `steward cutover plan --regenerate` and `--append` preserve `moved` rows (unit test).
3. `steward cutover apply --phase <n>` is idempotent (unit test).
4. Flip is refused while any loop is running.
5. Ledger key `44-12-cutover-flag-and-replay-harness` is the only 44.x key this Story may mark `done`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `08613ac92f` (2026-09-13, "Merge pull request #1339 from rxm7706/steward-44-12-cutover-harness"). Ledger row `44-12-cutover-flag-and-replay-harness: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/platform/config/flags.json`, `src/shared/packages/django-pyforge/src/django_pyforge/flags.py`, `src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py`, `src/shared/packages/pyforge-core/tests/unit/test_cutover_root.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py`, `src/shared/packages/pyforge-steward/tests/unit/test_cli.py`, `src/shared/packages/pyforge-steward/tests/unit/test_cutover.py`, `src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `backlog` → `done` (ledger row `44-12-cutover-flag-and-replay-harness: done`).
- `## Auto Run Result` reconstructed from git (none survived).
