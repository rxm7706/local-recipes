---
title: '3.9: A retired story branch is not a push failure'
type: 'change'
created: '2026-09-18'
status: 'done'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As the operator, I want the durability signal to stop reporting failure on its own success path, So that a real durability alarm still means something when it fires.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `3-9-a-retired-story-branch-is-not-a-push-failure`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: change / S / S-3.8.

### Living CAP citations

- Cited from epics.md: FR-170; AD-46

## Acceptance Criteria

- Given a `dev-commit-landed` or `story-merged` boundary whose per-story branch bmad-loop has already deleted on merge When the supervisor acts on that boundary Then it does not attempt the push and does not register `MRS-SUPV-008` And it proves the work landed — the story's `commit_sha` from `TaskPhaseSnapshot` is reachable from the station branch — and journals a benign `retired-merged` outcome And if that `commit_sha` is not reachable (or is unknown), a distinct and louder finding is registered: a branch that vanished with unlanded work is real loss and must not inherit the benign case's silence And `GitVcs.push` is unchanged — raising on "no such branch" is correct, since falling back would push to a target the caller never named; the defect is the caller asking for a push it does not need And a test proves both directions: a merged-and-deleted branch produces no finding, and a deleted branch whose commit is unreachable from the station branch produces the loud one

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a `dev-commit-landed` or `story-merged` boundary whose per-story branch bmad-loo | the supervisor acts on that boundary | it does not attempt the push and does not register `MRS-SUPV-008` | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 3.9 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `c307e84480` (2026-08-09, "marshal 3.9 + 3.10: the durability guarantee holds; its signal did not"). Ledger row `3-9-a-retired-story-branch-is-not-a-push-failure: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/conda-forge-expert/tests/meta/test_unpushed_work_check.py`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/.memlog.md`, `docs/dashboard/data.js`, `docs/dreams/durable-runs.md`, `scripts/.spec-surface-baseline.json`, `scripts/unpushed_work_check.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` (+4 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
