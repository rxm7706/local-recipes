---
title: '46.9: Benchmark legs run per layer with cache-hit rates'
type: 'feature'
created: '2026-09-18'
status: 'done'
baseline_revision: '8a2da2c010aec6578d6b6546a321affac249bb1d'
followup_review_recommended: false
review_loop_iteration: 1
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

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — self-review of diff against intent-contract; AC covered by new unit tests)

## Auto Run Result

Status: done

**Summary:** Extended the token-economy benchmark with per-layer leg artifacts (Story 46.9 / CAP-196): each of the five context layers compares an isolated-on leg against a shared baseline via `marshal benchmark compare --per-layer`, reporting weighted tokens, optional USD estimates, and prompt-cache hit rate; the 28.5 equivalence gate voids individual layer rows without voiding siblings.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/token_economy_benchmark.py` — per-layer artifact builder, cache-hit rate helper, leg schema field
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/benchmark.py` — `--per-layer` / `--layer-legs` compare mode; cache-hit rate from harness state
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` / `verdict.py` — register `MRS-BENCH-005`
- `src/shared/packages/pyforge-marshal/tests/unit/test_token_economy_benchmark.py` / `test_cli_benchmark.py` / `test_findings.py` — AC and matrix coverage
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — surface reconcile for governed paths

**Verification:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 11859 passed
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed
- `python scripts/spec_surface_reconcile.py` — OK after memlog reconcile

**Residual risks:** Live orchestration of five isolated harness runs remains operator-driven (same as CAP-9 off/on); per-layer mode assumes `--layer-legs` JSON maps every `CONTEXT_LAYER_NAMES` entry to a recorded leg.
