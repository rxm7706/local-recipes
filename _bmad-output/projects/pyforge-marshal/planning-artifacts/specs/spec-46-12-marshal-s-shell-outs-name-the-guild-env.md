---
title: '46.12: Marshal''s shell-outs name the Guild env'
type: 'fix'
created: '2026-09-20'
status: 'done'
baseline_revision: '7f5584a2e49412b4fe9ee000d8f8b1760d024c4b'
final_revision: 'pending — the merge commit of the fleet/agents-md-mod PR (#1551)'
review_loop_iteration: 1
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `cli/watch.py` shells `pixi run -e local-recipes bmad-loop list|status`, `core/gate.py:646` names `pixi run -e local-recipes platform-ci-local`, and `adapters/scribe_cli.py:77-78` falls back to `.pixi/envs/local-recipes/bin` — but only `pyforge-guild` exists at runtime, and bmad-loop is marshal's own run-dep, already in the Guild.

**Approach:** every argv names `-e pyforge-guild`; the scribe-CLI fallback lists only the Guild env's bin; the watch's fake-port tests assert the Guild argv.

## Boundaries & Constraints

**Always:**
- No `-e local-recipes` or `envs/local-recipes` string remains in `pyforge-marshal/src` (prose in docstrings may describe the past)
- The live watch on the dispatch clones still names the running dispatch

**Never:**
- Do not add a task to `guild-tasks` here — that is steward 63.6's; `bmad-loop` needs none

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| watch probes | `list_runs`, `run_status` | argv `["pixi","run","-e","pyforge-guild","bmad-loop",…]` | unchanged degradation |
| gate verify line | `platform-ci-local` | `pixi run -e pyforge-guild platform-ci-local -- --test` | n/a |
| scribe-CLI fallback | bin dirs | `.pixi/envs/pyforge-scribe/bin`, `.pixi/envs/pyforge-guild/bin` | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-263`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_watch.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_scribe_cli.py`, the gate tests.
Ledger key: `46-12-marshal-s-shell-outs-name-the-guild-env`.
Minted 2026-09-20 from `epics.md` so `marshal factory dispatch` can resolve this file.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- `grep -rn 'local-recipes' src/shared/packages/pyforge-marshal/src` finds no argv or path.

## Review Triage Log

### 2026-09-20 — hand-driven pass (operator: "why didn't we do this in #1551")
  - `[high]` `[patch]` `cli/watch.py` shelled `-e local-recipes bmad-loop list|status`; `core/gate.py` `CROSS_SURFACE_VERIFY_COMMAND` named `-e local-recipes platform-ci-local`; `adapters/scribe_cli.py` fell back to `.pixi/envs/local-recipes/bin`; the three packaged harness profiles' `fallback_bin_dirs` named it too. All repointed at `pyforge-guild` (bmad-loop and headroom are Guild deps; `platform-ci-local` moved to `guild-tasks` by steward 63.6).
  - `[low]` `[patch]` `test_watch.py` asserted the factory argv; updated.

## Auto Run Result

**Status:** done
**Summary:** no runtime `local-recipes` reference remains in `pyforge-marshal/src` (the guard confirms); the watch, gate and scribe-CLI tests pass with the Guild argv.
**Verification:** `pyforge-marshal-test` 8347 passed; the live watch on this host still names the running dispatch (53.2).
**Files changed:** `cli/watch.py`, `core/gate.py`, `adapters/scribe_cli.py`, `core/harness_profile.py` (docstring), `data/harness_profiles/{claude,gemini,copilot}.toml`, `tests/unit/test_watch.py`.
**Residual risks:** none from this change.
**Follow-up review recommendation:** false
