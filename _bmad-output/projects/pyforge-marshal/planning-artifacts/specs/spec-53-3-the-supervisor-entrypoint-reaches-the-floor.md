---
title: '53.3: The supervisor entrypoint reaches the floor'
type: 'chore'
created: '2026-09-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'd50aedbd22c5b8a531f25d90fca1532a3cae6ace'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_thresholds.toml
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** As the operator who landed 53.2 behind a dated exception, I want `dispatch_supervisor/__main__.py` (623 statements, 388 uncovered, 35% on 2026-09-20; 36% on `main` before 53.2 touched 15 of its 1,895 lines) unit-covered to the 80% floor and the `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` exception removed from `coverage_thresholds.toml`, So that Epic 53 closes with no named debt and the touched-module gate is whole again for marshal.

**Approach:** ports-driven unit tests of the supervisor's finalize / halt / land / completion sequences (the same fakes `test_dispatch_supervisor_*.py` already use), added until the gate reports ≥ 80%; then delete the exception entry. No production change unless a test proves a defect (which becomes its own finding).

Ledger key: `53-3-the-supervisor-entrypoint-reaches-the-floor`.
Ledger status (do not edit the ledger): `backlog`.

### Living CAP citations

- `spec-pyforge-marshal` CAP-264; the gate itself is `spec-pyforge-steward:CAP-153`.

## Acceptance Criteria

- Given the module sits at 35% behind a dated exception, When this story lands, Then `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` reports `pyforge.marshal.dispatch_supervisor.__main__` ≥ 80%.
- The `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` entry is gone from `coverage_thresholds.toml` and the gate's OK line names no dated exception for marshal.
- `test_the_live_file_names_the_supervisor_exception_with_its_story` in `tests/unit/test_coverage_gate_module_floors.py` is retired with the entry (it pins the exception's presence, not its absence).

## Boundaries & Constraints

- Coverage comes from tests, never from excluding lines or lowering floors.
- The supervisor's process boundary is faked through its ports (`HarnessPort`, `VcsPort`, `ForgePort`); no live harness, no network.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary checkout's copy of this file).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass.

**Manual checks:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — the module ≥ 80%, no exception named.

</intent-contract>

## Auto Run Result

**Summary:** Story 53.3 implemented in one pass. `dispatch_supervisor/__main__.py` goes from 35% (388 of 623 statements uncovered, behind the dated exception Story 53.2 opened) to **94% with branch coverage / 96% statements** (27 statements missed), entirely through new ports-driven unit tests; the `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` entry is deleted from `coverage_thresholds.toml`, so marshal holds no per-module coverage exception at all. **No production code was changed** — the module under test is byte-identical to `baseline_revision`.

**Files changed this run:**
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_main_loop.py` (**new**, 96 tests) — direct-call tests of the module's helpers (`_append_entry` incl. the sidecar offload above `SIDECAR_THRESHOLD_BYTES`, `_fold_dispatch_journal`, `_maybe_fetch_origin_main`, `_commit_pre_verify_wip`, `_launch_story_started_ts`, `_journal_dispatch_timing` / `_preserve` / `_blocked` / `_finalize_attempt`, `_load_known_story_keys`, `gather_dispatch_git_facts` incl. the station-branch PR corroboration path, the six journal predicates, `_worktree_story_spec`, `_spec_land_block_reason`, `_blocked_halt_reason`, `_attempted_change_patch_paths`, `_commit_and_journal_blocked_halt`, `_promote_blocked_twin`, `_run_and_journal_dispatch_push` / `_verification` / `_landing`, `_land_or_journal_block`, `_session_awaits_verification`, `_run_supervisor_finalize_sequence`), 15 `run_dispatch_supervisor` tick-loop scenarios (heartbeat, verification, landing, blocked halt, stale-blocked advisory, finalize, preserve, timing) and 2 `main()` argv tests. The process boundary is faked through the ports only — `FakeFs` / `FakeVcs` / `FakeProcess` / `FakePublisher` plus a `_FakeClock` patched over the module's `time` (so `_TICK_SECONDS` never sleeps and a non-terminating loop raises instead of hanging). No live harness, no network, no subprocess.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_thresholds.toml` — the `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` block removed; the comment documenting the per-module-exception mechanism stays and now records that none is held.
- `src/shared/packages/pyforge-marshal/tests/unit/test_coverage_gate_module_floors.py` — `test_the_live_file_names_the_supervisor_exception_with_its_story` retired (it pinned the entry's presence); `test_the_live_file_holds_no_module_exception` (`load_module_floors() == {}`) pins the absence in its place. The five mechanism tests over the synthetic TOML are untouched.
- Surface reconcile: `.memlog.md` entries on `spec-pyforge-marshal` (the two test files) and its co-governor `spec-pyforge-core` (the thresholds file), then a scoped `--write-baseline --spec` for exactly those two Specs.

**Acceptance criteria:**
- AC-1 — `pyforge-marshal-coverage-gate` measures `pyforge.marshal.dispatch_supervisor.__main__` at **94%** (`623 stmts / 27 miss / 172 branch`), above the 80% floor. The gate itself reports `touched source modules: (none)` for this branch (it changed no station `.py` source), then `pyforge-marshal unit floor: 80%`, exit 0.
- AC-2 — the entry is gone (`tomllib` parses the file to `{'defaults': {'unit': 80.0, 'integration': 70.0}}`, no `modules` table) and the gate's OK line names no dated exception for marshal.
- AC-3 — `test_the_live_file_names_the_supervisor_exception_with_its_story` is retired with the entry.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — pass (8492 passed, 1 skipped, 12 deselected).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — pass (130 passed, 3 skipped).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — exit 0, the module at 94%, no exception named.
- `pixi run -e pyforge-guild pr-preflight` — exit 0 (lint/format/mypy over the ten packages, `detectors-ci`, the CFE regression suite, `pyforge-core` + all 8 station suites, every station's touched-module coverage gate, site-check).

**Findings (recorded, not fixed — the story's Approach forbids a production change without a proven defect):**
- `dispatch_supervisor/__main__.py:1558` is unreachable. Inside `if verdict == DispatchSessionVerdict.LIVE:`, `should_terminalize_verify_refusal(...)` can never return `True`: it requires `not session_alive` **and** `verification_verdict == "refused"` **and** git progress, but the only path that yields a `LIVE` verdict for a dead session is `resolve_terminal_session_verdict`'s marshal-initiated-stop branch (`core/supervise.py:718-720`), which is reached only *after* the refused+progress case has already returned `FAILED` at `supervise.py:714-717`. The line is dead defensive code; removing it is a production change that buys nothing but coverage, which this story's Boundaries forbid.
- The other 26 uncovered statements are the `except` arms of PEP 758 unparenthesized multi-exception handlers around filesystem/VCS reads whose fake cannot fail in a way the surrounding code distinguishes (`532-533, 537-538, 659, 681-682, 765-766, 772, 783-784, 1379-1380, 1538-1539, 1542, 1618-1619, 1637-1638, 1700-1701, 1744-1745`) plus `1895` (the `if __name__ == "__main__":` dispatch).
- Unrelated to this story, surfaced by `pr-preflight` in this session: `.claude/skills/conda-forge-expert/tests/unit/test_inventory_channel_auth_host_gate.py::test_malformed_base_url_does_not_crash_the_allowlist_scan` fails in any session running behind the headroom wire-compression proxy, because `_fallback_configured_enterprise_hosts()` scans every `*_BASE_URL` environment variable and the test does not clear the ambient ones — `ANTHROPIC_BASE_URL=http://127.0.0.1:9108` leaks `127.0.0.1` into the asserted set. It passes with that variable unset, and CI (which never sets it) is unaffected. A fix belongs to the CFE skill's own chain (its Rule 1 / Rule 2 retro obligations), not to a marshal dispatch.

**Residual risks:** none blocking. The new suite is pure-fake and clock-patched, so it adds ~1s to the marshal unit suite and cannot hang. Marshal now carries no named coverage debt, so any future module that falls below 80% reds the gate instead of hiding behind an entry.
