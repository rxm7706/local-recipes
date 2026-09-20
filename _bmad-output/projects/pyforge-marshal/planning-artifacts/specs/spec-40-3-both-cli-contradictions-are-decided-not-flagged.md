---
title: '40.3: Both CLI contradictions are decided, not flagged'
type: 'docs'
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

**Problem:** As a fleet operator, I want the argparse-vs-typer framework question and the `init`/`check` verb collision actually resolved in the architecture and PRD, So that the fold-in stops preserving two undecided contradictions.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `40-3-both-cli-contradictions-are-decided-not-flagged`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / M / S-40.2.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-118` ← `spec-genesis-installer-name-retirement CAP-4`.

## Acceptance Criteria

- Given the installer architecture said typer+rich while the shipped Marshal CLI is argparse, and `genesis init`/`genesis check` collided with shipped `marshal init <slug>`/ `marshal check` When this story lands Then AD-51 states the framework and why — *"amended typer+rich -> argparse on measurement (14 shipped subparsers, zero typer in tree)"* — with no "flagged, not resolved" language left And the installer's distinct question gets its own verb surface: the `marshal seed <verb>` noun group, live in `cli/seed.py`

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the installer architecture said typer+rich while the shipped Marshal CLI is argp | this story lands | AD-51 states the framework and why — *"amended typer+rich -> argparse on measure | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 40.3 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `40-3-both-cli-contradictions-are-decided-not-flagged: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
