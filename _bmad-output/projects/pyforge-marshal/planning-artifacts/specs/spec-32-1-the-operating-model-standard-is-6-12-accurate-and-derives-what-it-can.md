---
title: '32.1: The operating-model standard is 6.12-accurate and derives what it can'
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

**Problem:** The operating-model standard is 6.12-accurate and derives what it can (contract recovered from epics.md Intent + ACs).

**Approach:** `_bmad-output/EXEMPLAR-STANDARD.md`

Ledger key: `32-1-the-operating-model-standard-is-6-12-accurate-and-derives-what-it-can`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / M / —.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-107` ← `spec-fleet-consistency-standard CAP-1`.

## Acceptance Criteria

- Given the standard named four skills removed or renamed in 6.11–6.12 (`bmad-document-project`, `bmad-create-story`, `bmad-check-implementation-readiness`, `bmad-dev-auto`) plus three research skills 6.12 consolidated into `bmad-deep-recon`, and carried dated conformance snapshots its own text warned go stale When the 16-stage skill-mapping table and the conformance-status sections are removed rather than refreshed, and the file is declared a companion of this Spec Then no skill, script or path named in it fails to resolve, INV-0..INV-5 / the conformance table / the kernel-companion rule / the provenance rules survive intact, and the self-invalidating "pyforge-atlas is right and this document is stale" clause is replaced by a reconciliation order And the conformance table gains rows 12–14 (suite standard, hyphenated-ISO naming, tested Python floor) so each new normative claim has its enumeration in the same place as the old ones

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the standard named four skills removed or renamed in 6.11–6.12 (`bmad-document-p | the 16-stage skill-mapping table and the conformance-status  | no skill, script or path named in it fails to resolve, INV-0..INV-5 / the confor | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 32.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `32-1-the-operating-model-standard-is-6-12-accurate-and-derives-what-it-can: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
