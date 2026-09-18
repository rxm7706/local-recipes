---
title: '46.1: A bare clone bootstraps the substrate'
type: 'feature'
created: '2026-09-18'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As an agent starting on a cloud runner (Devin, Copilot cloud, Cursor background), I want nightly-built substrate artifacts (codegraph, cocoindex distills, planning-graph export) published as CI/release assets and a `pyforge context bootstrap` fetch-or-rebuild command, So that a bare clone opens on the shared substrate instead of re-deriving it privately at ACU/quota cost.

**Approach:** a publisher (nightly workflow or release-asset upload) for the substrate artifacts, plus the `pyforge context bootstrap` CLI in pyforge-core or marshal (fetch-or-rebuild; rebuild is loud and attributable, never silent).

Ledger key: `46-1-a-bare-clone-bootstraps-the-substrate`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / L / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-192 (story slice CAP-19(a) of the reminted CAP-192). Fold remint: `spec-marshal-token-economy` CAP-19 → CAP-192 (`spec-marshal-token-economy` absorbed).
- Living: `spec-pyforge-marshal CAP-192` ← `spec-marshal-token-economy CAP-19`.

## Acceptance Criteria

- Given a fresh clone with no `.codegraph/`, no distills, no planning graph When `pyforge context bootstrap` runs Then it fetches the latest published artifacts and verifies their digests, or rebuilds locally with a named finding And the fetched substrate is byte-identical to what a loop home produced

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not cite absorbed `spec-marshal-token-economy` CAP-19..24 as living numbers; use CAP-192..197.
- Do not flip the parent Dream to `realized` (benchmark artifact is the realized-guard).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a fresh clone with no `.codegraph/`, no distills, no planning graph | `pyforge context bootstrap` runs | it fetches the latest published artifacts and verifies their digests, or rebuild | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
