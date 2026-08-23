---
title: Baseline-drift defers get loud
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 422067bba23070a9e1d13f8b7c2df9dccb0ac443
followup_review_recommended: false
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-1 (`scripts/bmad_loop_baseline_drift_check.py`, Story 20.1 / PR #680) detects unrecovered baseline-drift defers, but FR-188 CAP-2 requires loud-defer containment: the finding must exit non-zero **and** surface where the operator already looks (`fleet-picture` ATTENTION), naming recovery inputs so a live recurrence cannot read healthy.

**Approach:** Complete CAP-2 on top of the shipped CAP-1 detector — wire/verify ATTENTION-plane surfacing (exit/report path + `fleet-picture` or equivalent). Pre-existing ATTENTION probe stubs in `scripts/fleet_picture.py` may already call the detector; this story owns proving the contract end-to-end and closing any gaps (message richness, tests, healthy-run silence). Loud defer only — never quiet auto-land. Do not edit `bmad_loop`.

## Acceptance Criteria

- Unrecovered baseline-drift fixture/run → detector exits non-zero **and** `fleet-picture` (or documented equivalent ATTENTION surface) names recovery inputs: story, run, preserved ref/patch, drifted-vs-real baselines (inline or via an unambiguous pointer to `baseline-drift-check` output that carries those fields).
- Clean / recovered state → no ATTENTION need line for baseline-drift; containment output cannot read healthy when an unrecovered defer exists.
- No quiet auto-land of deferred work; no edits to the `bmad_loop` package.
- Does not implement 20.3 upstream filing or 20.4–20.10.

## Boundaries & Constraints

**Never:** Edit `bmad_loop`. Never implement 20.3–20.10. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward 15-4.

</intent-contract>

## Code Map

- `scripts/bmad_loop_baseline_drift_check.py` — `collect_findings()`, human stdout, `--json` machine list (CAP-2 feed for fleet-picture)
- `scripts/fleet_picture.py` — `baseline_drift_findings()`, `_baseline_drift_needs_lines()`, ATTENTION `needs.extend(...)` wiring
- `tests/scripts/test_bmad_loop_baseline_drift_check.py` — CAP-1 + `--json` / `collect_findings`
- `tests/scripts/test_fleet_picture_baseline_drift_attention.py` — ATTENTION naming, silence, `main()` wiring, probe contracts

## Verification

- Fixture unrecovered → detector exit 1 + ATTENTION `>>` names story/run/baselines/preserve-or-patch
- Clean/recovered → no baseline-drift need line; unrecovered cannot print the healthy-only ATTENTION sentence alone
- `pixi run --frozen -e local-recipes pytest tests/scripts/test_bmad_loop_baseline_drift_check.py tests/scripts/test_fleet_picture_baseline_drift_attention.py -q` green

## Spec Change Log

### 2026-08-23 — Review pass Code Map / Verification refresh
- Trigger: review found Code Map/Verification still CAP-1-shaped after `--json` + ATTENTION helpers landed.
- Amended: Code Map and Verification outside `<intent-contract>` to name `collect_findings`, `--json`, `_baseline_drift_needs_lines`, and the new ATTENTION test module.
- Known-bad avoided: shipping CAP-2 with a Code Map that only points at the thin pre-existing probe.
- KEEP: intent-contract unchanged; loud-defer-only / no `bmad_loop` edits.

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 3, medium 4, low 1)
- defer: 0
- reject: count absorbed (pointer-only AC variants, N>1 first-finding-only matching dream_chain, pixi.toml/dream doc churn, harness duplication, JSON schema versioning)
- addressed_findings:
  - `[high]` `[patch]` Assert `check=False` (+ DEVNULL stdin) on `baseline_drift_findings` probe; exit outside `{0,1}` raises
  - `[high]` `[patch]` `main()` ATTENTION wiring tests: unrecovered names recovery inputs; clean silence; probe raise degrades
  - `[medium]` `[patch]` Unicode line-break sanitization + non-list `refs` normalization
  - `[medium]` `[patch]` Restore stuck-orchestrator causal framing on the needs line
  - `[medium]` `[patch]` Empty/non-list `--json` stdout guarded before `json.loads`
  - `[low]` `[patch]` Document `--json` in detector EXIT docstring + timeout rationale on probe

## Auto Run Result

Status: done

Summary: CAP-2 loud-defer containment — detector `--json` / `collect_findings`; fleet-picture ATTENTION inlines story/run/baselines/preserve-or-patch plus `baseline-drift-check` pointer; clean/recovered silent; no `bmad_loop` edits.

Files changed:
- `scripts/bmad_loop_baseline_drift_check.py` — structured collection + `--json`
- `scripts/fleet_picture.py` — JSON probe + rich needs assembly + ATTENTION wiring
- `tests/scripts/test_bmad_loop_baseline_drift_check.py` — CAP-1/`--json` coverage
- `tests/scripts/test_fleet_picture_baseline_drift_attention.py` — ATTENTION / main() contract tests
- this story spec — Code Map/Verification + triage + auto-run result

Review: 8 patches applied (3 high, 4 medium, 1 low); 0 deferred; follow-up score = `3×0 medium + 1×0 low` after address (patched highs fixed) → `followup_review_recommended: false`

Verification: `pixi run --frozen -e local-recipes pytest tests/scripts/test_bmad_loop_baseline_drift_check.py tests/scripts/test_fleet_picture_baseline_drift_attention.py -q` → green (see commit-time re-run)

Residual risks: ATTENTION still expands only the first finding inline (count covers the rest; full list via `baseline-drift-check`) — same pattern as dream-chain.
