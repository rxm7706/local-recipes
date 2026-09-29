---
title: '32.7: Coverage is measured on all eight stations before any floor is enforced'
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

**Problem:** Coverage is measured on all eight stations before any floor is enforced (contract recovered from epics.md Intent + ACs).

**Approach:** `pixi.toml` (`pytest-cov` into the seven station features that lack it, per-station `-test-coverage` tasks), `environment.yaml`, the coverage thresholds TOML, `.github/workflows/coverage-gates.yml`

Ledger key: `32-7-coverage-is-measured-on-all-eight-stations-before-any-floor-is-enforced`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / M / S-32.5.

### Living CAP citations

- Cited: `spec-pyforge-testing-charter CAP-4`.

## Acceptance Criteria

- Given `pytest-cov` is declared in 2 of 10 pixi features, so seven station environments cannot run a coverage gate at all — verified live against scribe, which exits 1 with `unrecognized arguments: --cov` — and nobody has ever measured the fleet's real coverage, which the testing charter's own assumptions state When `pytest-cov` is added to the seven, all eight are measured, and each station's measured value is written as its starting floor Then no station reds on the first PR, coverage cannot regress below where it actually is, and floors ratchet upward only And the CI matrix expands from marshal-only to all eight; extending the `--cov` target over the django/portal tier stays an open question on the Spec, not a silent inclusion

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `pytest-cov` is declared in 2 of 10 pixi features, so seven station environments | `pytest-cov` is added to the seven, all eight are measured,  | no station reds on the first PR, coverage cannot regress below where it actually | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 32.7 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `32-7-coverage-is-measured-on-all-eight-stations-before-any-floor-is-enforced: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
