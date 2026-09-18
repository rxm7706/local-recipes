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
