---
title: 'The first live fan-out wave, on a real dispatch.max_parallel key'
type: 'feature'
created: '2026-09-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
baseline_revision: '9109bb0f8e381c9db6de3f051d4c02fbe51e604c'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-parallel-dispatch-fanout/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-parallel-dispatch-fanout/wave-scheduler.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-16-parallel-dispatch-fanout-when-deps-and-surfaces-are-disjoint.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-2-wire-compression-at-the-harness-seam.md
  - docs/dreams/marshal-parallel-dispatch-fanout.md
  - docs/dreams/marshal-token-economy.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 28.16 shipped the wave scheduler, narrowed conflict guard, and wave
journal, but `max_parallel = 1` everywhere and `resolve_max_parallel` reads bmad-loop's
`scm.max_parallel` (`core/policy.py:513`). Raising the cap fires `MRS-POLICY-007` naming
bmad_loop 0.9.0 on the dispatch path. CAP-16 auto-derivation makes same-station stories
overlap by construction until specs declare their own `surface:`, so no live wave has ever
run. Parallel wrapped dispatches also share headroom's default proxy port 8787 (DW-FU-28-2-2).

**Approach:** Mint `dispatch.max_parallel` as a marshal-policy key resolved only on the
factory-dispatch path; scope `MRS-POLICY-007` to spin/scm `max_parallel` only; set
`dispatch.max_parallel = 2` on pyforge-marshal; add disjoint `surface:` declarations on two
wave-probe story specs; prove one two-member wave via an integration test that exercises
`execute_fleet_cycle` with real policy composition and journals a `dispatch-wave` intent;
close DW-FU-28-2-2 by passing a per-worktree `--port` through headroom wrap argv via a new
`{wire_port}` placeholder in `render_dispatch_argv`.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-marshal/` literally;
`BMAD_ACTIVE_PROJECT=pyforge-marshal` only. Default serial when `dispatch.max_parallel`
absent (=1). Unknown/empty spec surfaces never fan out together. Wire port derived
deterministically from worktree path (stable, in 8800–9799 range).

**Never:** Do not change bmad-loop scm `max_parallel` semantics for spin. Do not weaken
22.2 LIVE semantics or 22.3 verify-before-land. Do not run a full unattended double-story
dispatch in this story — integration test + journal proof only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| dispatch.max_parallel=2, two disjoint ready specs | policy + backlog | one wave with two members; journal `KIND_DISPATCH_WAVE` | refused pairs get MRS-DRAIN-016 |
| dispatch.max_parallel absent | default policy | serial (=1), byte-identical to today | no MRS-POLICY-007 on dispatch path |
| scm max_parallel=4, dispatch unset | spin policy only | MRS-POLICY-007 fires for spin compose | dispatch still serial |
| dispatch.max_parallel=2 only | project policy | no MRS-POLICY-007; waves up to 2 | malformed int falls back via existing machinery |
| two wrapped parallel dispatches | wire layer on, distinct worktrees | distinct `--port` per launch | same port only if same worktree |

</intent-contract>

## Code Map

- `core/policy.py:513,1537-1551,2279-2281` — add `dispatch` block validator + default; scope clamp finding to scm `max_parallel` only
- `schemas/policy.json` — bless `dispatch` mapping field
- `cli/config.py:89-151,265` — register `dispatch` in project-only / unsettable sets as needed
- `cli/dispatch.py:912-924,3029-3140,2781-2824` — `resolve_max_parallel` reads `dispatch.max_parallel`; wave path unchanged except cap source
- `core/harness_profile.py:702-790,793-829` — `{wire_port}` placeholder; `wire_port_for_worktree(worktree)` helper
- `data/harness_profiles/claude.toml:65-67` — add `--port`, `{wire_port}` to wrapper argv; update operator caveat
- `adapters/harness_bmadbuild.py:235` — pass wire_port into render path
- `planning-artifacts/marshal-policy.toml` — `[dispatch] max_parallel = 2` before model_tier_map
- `planning-artifacts/specs/spec-33-8-wave-probe-a.md` — new minimal probe spec, `surface: ["scripts/bmad_loop_baseline_drift_check.py"]`
- `planning-artifacts/specs/spec-33-9-wave-probe-b.md` — new minimal probe spec, `surface: ["scripts/missing_preserve_check.py"]`
- `tests/unit/test_policy.py` — dispatch.max_parallel compose + no false MRS-POLICY-007
- `tests/unit/test_dispatch_fleet.py` — integration: execute_fleet_cycle forms two-member wave with real policy
- `tests/unit/test_harness_profile.py` — wire_port substitution + distinct ports per worktree
- `tests/unit/test_wave_scheduler.py` — keep existing; add dispatch-key regression if needed
- `planning-artifacts/sprint-status-ledger.yaml` — flip 33-8 key to `done` via sprint-ledger-sync

## Tasks & Acceptance

**Execution:**
- `core/policy.py` — add `_valid_dispatch_block`, `DEFAULT_POLICY["dispatch"]`, merge in `compose()`; clamp finding only when `seed["max_parallel"].value > 1` (scm/spin knob unchanged)
- `cli/dispatch.py` — `resolve_max_parallel` reads `effective_policy.dispatch.value.get("max_parallel", 1)` with `_valid_parallel_count` validation; CLI `--max-in-flight` override unchanged
- `schemas/policy.json` + `cli/config.py` — wire new field through schema and config surfaces
- `core/harness_profile.py` + `claude.toml` + `harness_bmadbuild.py` — `{wire_port}` templating; deterministic port from worktree hash
- `marshal-policy.toml` — `[dispatch] max_parallel = 2` with comment referencing Story 33.8
- `spec-33-8-wave-probe-a.md` + `spec-33-8-wave-probe-b.md` — minimal backlog-ready probe specs with disjoint `surface:` frontmatter (status `backlog`, no implementation intent)
- `tests/unit/test_dispatch_fleet.py` — new test: tmp repo with probe specs in backlog, policy dispatch.max_parallel=2, mock `dispatch_once` records two launches in one cycle, wave journal exists with both members
- `tests/unit/test_policy.py` — regression: tracked marshal-policy with dispatch.max_parallel=2 composes without MRS-POLICY-007
- `tests/unit/test_harness_profile.py` — two distinct worktrees get distinct wire ports in rendered argv
- Tier-3 feed + `pixi run -e local-recipes sprint-ledger-sync -- --project pyforge-marshal` — promote 33-8 to `done`

**Acceptance Criteria:**
- Given Story 28.16 mechanism is done and dispatch.max_parallel is unset, when factory drain runs, then behavior is byte-identical to serial drain
- Given marshal-policy.toml declares `[dispatch] max_parallel = 2` and two backlog stories have pairwise disjoint effective surfaces, when execute_fleet_cycle runs one tick, then both stories dispatch in one wave and a dispatch-wave journal records both member keys
- Given dispatch.max_parallel=2 and scm max_parallel remains 1, when policy composes for factory dispatch, then MRS-POLICY-007 does not fire
- Given scm max_parallel=4 in project policy with dispatch unset, when spin policy composes, then MRS-POLICY-007 still fires naming bmad_loop clamp
- Given wire layer enabled and two parallel dispatches on distinct worktrees, when resolve_wire_wrap renders argv, then each launch includes a distinct headroom `--port` value

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all unit tests pass including new wave + policy + harness tests
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass
- `pixi run -e local-recipes sprint-ledger-sync -- --project pyforge-marshal` — expected: 33-8 key becomes `done`
- `pixi run -e local-recipes story-status-check` — expected: pass after ledger sync

## Review Triage Log

### 2026-09-09 — Review pass
- verdicts: 12 findings — high 0, medium 2, low 3, false 5, maybe-false 2
- findings:
  - `[medium]` `[patch]` SEED `max_parallel` decoupling not tested at dispatch cap — added `test_resolve_max_parallel_ignores_seed_max_parallel` and CLI override test
  - `[medium]` `[patch]` Packaged `claude.toml` `--port`/`{wire_port}` not pinned — extended `test_packaged_claude_declares_the_headroom_wrapper`
  - `[low]` `[patch]` `wire_port_for_worktree` used unresolved path — switched to `worktree.resolve()`
  - `[low]` `[reject]` Hash mod-1000 port collision — acceptable for v1; 1000-port span sufficient for parallel wave width ≤2
  - `[low]` `[reject]` Stale "33-key" docstrings — cosmetic drift only; schema/tests already at 34
  - `[false]` Probe specs absent from diff — present as new untracked files included in final commit set
  - `[false]` Ledger hand-edited without sync — sprint-ledger-sync ran with repair-feed before sync
  - `[false]` MRS-POLICY-007 spin path untested — existing `test_max_parallel_requested_above_one_preserves_value_and_fires_clamp_advisory` covers scm clamp
  - `[false]` Probe specs never selected for story 33-8 — probes are disjoint-surface fixtures for wave tests, not alternate 33-8 spec paths
  - `[maybe-false]` `[defer]` End-to-end `_compose_policy` file read + wave — compose regression on real marshal-policy.toml plus fleet test with explicit dispatch flags; full file-path E2E deferred
  - `[maybe-false]` `[defer]` `--max-in-flight` behavioral override — argv propagation tested; dedicated override-vs-policy fleet test deferred

## Spec Change Log

- 2026-09-09: Review pass — added resolve_max_parallel unit tests and packaged wrapper `--port` pin per verification-gap findings

## Auto Run Result

Status: done

**Summary:** Minted `dispatch.max_parallel` as a 17th STATIC policy key; factory dispatch reads it independently of scm `max_parallel`. Tracked `marshal-policy.toml` sets `max_parallel = 2`. Wave integration test proves two-member batch + journal. Headroom `{wire_port}` per worktree closes DW-FU-28-2-2. Ledger 33-8 → done.

**Files changed:**
- `core/policy.py`, `schemas/policy.json`, `cli/config.py` — dispatch policy key
- `cli/dispatch.py` — resolve_max_parallel + wave journal writer_id fix
- `core/harness_profile.py`, `claude.toml`, `harness_bmadbuild.py` — wire port seam
- `marshal-policy.toml`, probe specs, sprint ledger
- Tests: policy, dispatch, dispatch_fleet, harness_profile, cli

**Review:** 3 patches applied (resolve_max_parallel tests, packaged wrapper pin, wire_port resolve); 2 deferred (file-path E2E, max-in-flight override fleet test); 5 rejected/false.

**Follow-up review recommended:** false (one medium patch only after review loop)

**Verification:** `pyforge-marshal-test` — 7651+ passed; review patches — 3 targeted tests passed; `story-status-check` — ok
