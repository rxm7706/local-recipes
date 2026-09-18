---
title: '46.9: Benchmark legs run per layer with cache-hit rates'
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

**Problem:** As an operator trusting the savings numbers, I want `marshal benchmark compare` to run one leg per layer — each leg reporting prompt-cache hit rate alongside weighted tokens, with the 28.5 equivalence gate applied per leg, So that a cache-colliding wire layer shows as worse weighted tokens, unmasked by other layers' gains, and Claude wire savings become verified instead of asserted.

**Approach:** `core/token_economy_benchmark.py` leg runner + per-leg artifact schema (cache-hit rate field).

Ledger key: `46-9-benchmark-legs-run-per-layer-with-cache-hit-rates`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-196 (fold remint of `spec-marshal-token-economy` CAP-23; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-196` ← `spec-marshal-token-economy CAP-23`.

## Acceptance Criteria

- Given a named story and the five layers When the benchmark runs one leg per layer Then each artifact reports weighted tokens, dollars if the catalog is declared, and cache-hit rate, and a non-identical landing voids that leg only

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
| a named story and the five layers | the benchmark runs one leg per layer | each artifact reports weighted tokens, dollars if the catalog is declared, and c | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.9 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
