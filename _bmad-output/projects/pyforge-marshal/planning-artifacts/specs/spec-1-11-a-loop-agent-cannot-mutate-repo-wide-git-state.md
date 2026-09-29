---
title: '1.11: A loop agent cannot mutate repo-wide git state'
type: 'feature'
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

**Problem:** As the operator, I want isolation to cover the shared git directory, not just the working tree, So that one dev session cannot silently change what every other worktree can see.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `1-11-a-loop-agent-cannot-mutate-repo-wide-git-state`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / S / S-1.6.

### Living CAP citations

- Cited from epics.md: FR-178

## Acceptance Criteria

- Given a provisioned loop home When `marshal preflight` (or `homes`) runs Then a mutation of the shared git directory — `info/exclude` at minimum — is reported against a recorded baseline, naming the rule and what it hides And the report distinguishes shared-state mutation from ordinary worktree state: FR-8's isolation check covers worktrees and branches and does not see this And the filesystem-walking guard `test_skill_files_tracked.py` is left in place — it walks the tree instead of asking git, so it is the only signal that survives the rule, and it is what caught the third recurrence And a test proves the detection on a fixture whose `info/exclude` carries a rule the tracked tree would otherwise match

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a provisioned loop home | `marshal preflight` (or `homes`) runs | a mutation of the shared git directory — `info/exclude` at minimum — is reported | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 1.11 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9784448e3c` (2026-08-09, "marshal 1.11: a loop agent cannot mutate repo-wide git state"). Ledger row `1-11-a-loop-agent-cannot-mutate-repo-wide-git-state: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `docs/dashboard/data.js`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_init.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_upstream_cli.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
