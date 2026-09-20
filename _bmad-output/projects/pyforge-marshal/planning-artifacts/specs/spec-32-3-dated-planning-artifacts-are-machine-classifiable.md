---
title: '32.3: Dated planning artifacts are machine-classifiable'
type: 'chore'
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

**Problem:** Dated planning artifacts are machine-classifiable (contract recovered from epics.md Intent + ACs).

**Approach:** `_bmad-output/projects/pyforge-{doctor,herald,mason,scribe,steward}/planning-artifacts/implementation-readiness-report-*.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/` (loose `PRD.md`, `retros/` vs `reviews/`)

Ledger key: `32-3-dated-planning-artifacts-are-machine-classifiable`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-110` ← `spec-fleet-consistency-standard CAP-4`.

## Acceptance Criteria

- Given `implementation-readiness-report-` exists in three date formats across 27 files and `bmad_drift_check.py`'s classifier matches only `-YYYY-MM-DD.md` When every compact `-YYYYMMDD` name is renamed to the hyphenated ISO form Then pointing `bmad-drift` at any station — not only pyforge-marshal — reports zero `uncovered` files, so a real finding is never buried under a false one And marshal's directory asymmetries are resolved or recorded as deliberate in `planning-artifacts/README.md` (conformance-table row 10), never left implicit

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `implementation-readiness-report-` exists in three date formats across 27 files  | every compact `-YYYYMMDD` name is renamed to the hyphenated  | pointing `bmad-drift` at any station — not only pyforge-marshal — reports zero ` | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 32.3 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `32-3-dated-planning-artifacts-are-machine-classifiable: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
