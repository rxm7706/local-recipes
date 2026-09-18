---
title: '40.2: One contiguous FR space, and every installer-only namespace decided'
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

**Problem:** As a fleet operator, I want the separate `FR1..FR62` numbering island resolved by chain rewrite rather than by hand, and each installer-only namespace given an explicit fate, So that one PRD has one numbering space and no bare-digit citation survives.

**Approach:** companion `citation-map.md` — the pre-rewrite ground-truth inventory, holding the full 62-row `FR1..FR62 → FR-66..FR-127` mapping plus per-file citation-site line lists

Ledger key: `40-2-one-contiguous-fr-space-and-every-installer-only-namespace-decided`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / L / S-40.1.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-116` ← `spec-genesis-installer-name-retirement CAP-2`.

## Acceptance Criteria

- Given a no-dash `FR1..FR62` island and installer-only `NFR-O1`/`SC-01..10`/`K-01..03`/ `OQ-1..9` namespaces When this story lands Then every FR is dashed and sequential (verified 2026-09-11: 196 unique numbers, FR-1..FR-196, zero gaps) And each namespace's fate is stated in the PRD — `NFR-O1` retired into `NFR-12`, `SC-01..10` and `K-01..03` adopted as-is

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a no-dash `FR1..FR62` island and installer-only `NFR-O1`/`SC-01..10`/`K-01..03`/ | this story lands | every FR is dashed and sequential (verified 2026-09-11: 196 unique numbers, FR-1 | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 40.2 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
