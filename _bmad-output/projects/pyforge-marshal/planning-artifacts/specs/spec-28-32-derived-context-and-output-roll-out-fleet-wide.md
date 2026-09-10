---
title: 'Derived-context and output roll out fleet-wide'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/hashes.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-28-scribe-exposes-caller-declared-derived-context-refresh-closing-the-cap-5-cap-6-gap.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-30-output-caveman-compresses-dispatch-sessions-too-not-just-spin.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Stories 28.28 and 28.30 proved `derived-context` and `output` genuinely work end-to-end, but only `pyforge-marshal` had either layer enabled. The other 7 stations' dispatch sessions got zero benefit from two proven-working, zero-further-engineering layers — the same shape Story 28.27 already closed for `planning-graph`.

**Approach:** Enable `[context."derived-context"]` and `[context.output]` for the 7 non-marshal stations' `marshal-policy.toml`, mirroring 28.27's rollout pattern. Before rolling out, a real bug was found and fixed: `seed/detect/kit.py::_carve_out_state` string-sliced a Python `str` using `RegionSpan.body_span`'s BYTE offsets (documented in `regions/parse.py`) instead of byte-slicing — desyncing whenever non-ASCII content preceded the caveman carve-out region, exactly what the real packaged `SKILL.md` carries. This made `marshal seed kit`/`run_preflight` re-deploy the caveman skill on every single preflight (never idempotent) and reported a false carve-out-mismatch WARN (`MRS-PREFLIGHT-015`) even on a byte-correct, freshly-deployed file. Fixed by using the already-correct, already-tested `detect/hashes.py::region_body_text` instead. Rolling out `output` onto the broken detection would have reproduced this identically on all 7 stations' loop homes the moment the layer was enabled.

## Boundaries & Constraints

**Always:** Verify each station's `derived-context` retrieval genuinely reports `mode: incremental` with zero findings, not just that the policy flag is set. Fix the carve-out detection bug BEFORE rolling `output` out further — rolling onto broken detection would just multiply the bug.

**Never:** Touch `wire`/`structure-graph` policy for any station in this story — `wire` stays documented-incompatible (28.29) and `structure-graph` splits into 28.31 (dispatch spike, unresolved) / 28.33 (spin reference, this same pass).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CARVE_OUT_BYTE_BUG (the live bug) | Upstream skill body has non-ASCII content before the carve-out region | Pre-fix: `_carve_out_state` reports "no longer matches" even on a fresh, correct deployment. Post-fix: reports intact | N/A |
| ROLLOUT_PER_STATION | 7 stations gain both layers | Each reports `mode: incremental`, zero findings for `derived-context`; `output` deploys the skill cleanly with no finding | N/A |
| IDEMPOTENCY | A loop home preflighted twice in a row | Second run reports `already-present`, not `applied`, for caveman-skill | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py` — `_carve_out_state` now calls `detect/hashes.py::region_body_text` instead of a naive `str` slice
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_kit.py` — new regression test with a non-ASCII upstream body
- 7 station `marshal-policy.toml` files — `[context."derived-context"]` + `[context.output]` `enabled = true`

## Tasks & Acceptance

**Execution:**
- `seed/detect/kit.py` — byte-slice fix — fix
- `tests/unit/test_seed_kit.py` — 1 new regression test (verified it reproduces the bug on the pre-fix code, then passes post-fix)
- 7 `marshal-policy.toml` files — enable both layers — feature

**Acceptance Criteria:**
- Given the carve-out fix, when a non-ASCII upstream skill is deployed and immediately checked, then `kit_checks` reports `KitStatus.OK`, not `MISSING`
- Given all 8 stations post-rollout, when `marshal context refresh --project <slug> --epic 1 --format json` runs, then every result reports `mode: incremental` with zero findings
- Given all 8 stations post-rollout, when `_seed_dispatch_output_layer` runs against a scratch worktree with the station's own resolved policy, then the skill deploys with no finding

## Spec Change Log

## Review Triage Log

## Auto Run Result

Status: done

**Summary:** Rolled out `derived-context` + `output` to all 7 remaining stations. Found and fixed a genuine, previously-undiscovered byte/character-offset bug in the caveman carve-out detection along the way — live-verified via a real `marshal preflight pyforge-marshal` run BEFORE the fix, which showed the caveman skill being needlessly re-applied on every single preflight and a persistent false `MRS-PREFLIGHT-015` WARN. Fixing this first was load-bearing, not a side quest: rolling `output` out onto the broken detection would have reproduced the same bug on all 7 stations the moment the layer went live.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py` — `_carve_out_state` byte-slice fix
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_kit.py` — 1 new regression test
- 7 station `marshal-policy.toml` files — both layers enabled
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — 28-32 → done

**Review:** Implementation verified directly against the spec's own I/O matrix, a unit regression test proven to fail pre-fix and pass post-fix, and live per-station verification for both layers; no separate review-loop pass for this story.

**Verification:** `pyforge-marshal-test` → 7705 passed. Live: `marshal preflight pyforge-marshal` run twice in a row reports `already-present` (not `applied`) on the second run, and no `MRS-PREFLIGHT-015` finding. All 7 other stations: `marshal context refresh --project <slug> --epic 1` → `mode: incremental`, zero findings; `_seed_dispatch_output_layer` against a scratch worktree with each station's own resolved policy → skill deployed, no finding.

**Residual risks:** The carve-out bug fix was verified against `pyforge-marshal`'s own live loop home only; the other 7 stations' loop homes have not yet had `marshal preflight` run against them post-fix (their `output`/`structure-graph`/`wire` kit items were never provisioned before this pass either, since only `planning-graph` was on). The bug is fixed at the source, so the next `marshal preflight <slug>` for any of them will provision correctly — no further action needed, but not independently re-verified per station in this pass beyond the `_seed_dispatch_output_layer` direct-call check above (which bypasses the loop-home-only `marshal seed kit` write path entirely, since dispatch never uses it).

## Verification

**Commands:**
- `pixi run -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_seed_kit.py -q` — expected: 64 passed
- `pixi run -e pyforge-marshal marshal preflight pyforge-marshal` (run twice) — expected: second run reports `already-present` for caveman-skill, no `MRS-PREFLIGHT-015`
- `for p in pyforge-atlas pyforge-steward pyforge-warden pyforge-doctor pyforge-herald pyforge-mason pyforge-scribe; do pixi run -e pyforge-marshal marshal context refresh --project "$p" --epic 1 --format json; done` — expected: every result `mode: incremental`, zero findings
