---
title: '51.6: `marshal watch` follows the engine that is actually driving the station'
type: 'fix'
created: '2026-09-19'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
baseline_revision: 'd7f31dd88fdc2ebd05e54ce4e60ea897a839f3af'
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 the fleet watch read `dispatch-runs/` journals directly all day because `_gather_station` lets any `running`/`paused` `bmad-loop list` row win and consults `dispatch_run_id` only when no live row exists

**Approach:** the station's current run is the engine whose last journal fact is most recent

## Boundaries & Constraints

**Always:**
- a fixture with a `paused` loop row from 2026-08 and a dispatch run journaled today reports the dispatch run (harness, key, phase, last fact); with no dispatch run the loop row is chosen exactly as today; neither reports idle
- the choice function is mutation-tested (swapping the comparison re-selects the stale row)

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-254`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py::_gather_station` (the `_LIVE_STATUSES` row wins today; the choice becomes one pure function over the loop row's and the dispatch run's last journal timestamps), its `WatchPorts` / `_default_ports` (importing `iter_dispatch_run_dirs` / `gather_dispatch_journal_facts` from `cli/dispatch.py`, not re-implementing them), tests.
Ledger key: `51-6-marshal-watch-follows-the-engine-that-is-actually-driving-the-station`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-6-marshal-watch-follows-the-engine-that-is-actually-driving-the-station.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.6 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 14 findings — high 1, medium 5, low 3, false 5
- findings:
  - `medium` `patch` the Then clause requires the report to include "(harness, key, phase, last fact)" when the dispatch run wins, but `_snapshot_dispatch`/`_snapshot_loop`/`sections` never surface the winning engine's last-journal-fact timestamp computed in `_gather_station` — it is used only for the comparison, then discarded (`watch.py::_gather_station`, `_snapshot_loop`/`_snapshot_dispatch`). Fix applied: `_gather_station` now returns `last_fact_at` (ISO 8601 or `None`) in both branches, asserted directly in `test_dispatch_run_outranks_a_stale_paused_loop_row`.
  - `medium` `patch` same defect restated by the intent-alignment layer as a surface mismatch: the decision the diff makes (which engine, on what evidence) never reaches the surface the intent-contract's Then clause actually names. Fix applied: same `last_fact_at` field as the row above (shared root cause).
  - `high` `patch` when the new comparison picks the dispatch run over a `paused`/escalated loop row, the loop row's `paused_reason`/`escalation_reason` is dropped: the dispatch branch's returned `paused_or_escalated` reflects only the dispatch side, with no `stale_loop_ignored`/`stale_loop_run_id` pair mirroring the existing `stale_dispatch_ignored`/`stale_dispatch_run_id` fields the `bmad-loop` branch already returns for the reverse case — in `--fleet` mode a station whose loop run is genuinely stuck in escalation silently drops out of the "escalated first" sort the moment a newer unrelated dispatch run appears (`watch.py::_gather_station` lines ~961-995, fleet sort ~line 1116). Fix applied: `stale_loop_ignored`/`stale_loop_run_id` added mirroring the existing convention, OR'd into `paused_or_escalated`, and surfaced in `_user_action`'s new `stale_loop` parameter; new test `test_fleet_mode_escalated_loop_row_outranked_by_dispatch_still_sorts_first` proves the station still sorts first and appears in `user_action_required`.
  - `medium` `patch` no test exercises `_args(fleet=True)` for this change at all, leaving the story's own motivating scenario (a fleet-mode incident, per the Problem statement) unverified by the new test suite. Fix applied: same test as the row above (shared root cause) is this file's first `--fleet`-mode test.
  - `low` `patch` `_loop_journal_last_fact` keeps overwriting `last_ts` with whichever line it parses last rather than computing an explicit maximum like its sibling `_dispatch_journal_last_fact` already does; its own docstring claims "the latest epoch ts," true only if the journal happens to be strictly ordered. Fix applied: tracks an explicit `max_ts` across all parsed lines; new test `test_loop_journal_last_fact_returns_the_true_max_not_the_last_line` proves an out-of-order journal still reports its true maximum.
  - `low` `reject` `_dispatch_journal_last_fact` only considers `launched_at`/`story_started_at`/`story_ended_at` because `DispatchJournalFacts` structurally carries no timestamps for other journal-fact kinds (completion/verification/land/push/wave/preserve) — narrow post-story-end race window, unlikely in everyday use, and the fix requires expanding a shared dataclass's public surface across other consumers, which exceeds a trivial patch.
  - `false` `reject` claim that `dispatch_last_fact`'s linear scan via `iter_dispatch_run_dirs` (vs. the existing `dispatch_run_dir()` direct-path helper) "silently reads wrong data" or meaningfully conflates run-not-found vs. journal-unreadable — refuted: `gather_dispatch_journal_facts` already returns an empty-fact result gracefully either way, and `_dispatch_outranks_loop`'s null-never-outranks contract makes both cases behave identically (loop wins). A style/efficiency preference, not a demonstrated defect.
  - `low` `patch` `_loop_journal_last_fact`'s numeric guard (`isinstance(ts, (int, float)) and not isinstance(ts, bool)`) accepts non-finite floats; `json.loads` parses `NaN`/`Infinity`/`-Infinity` tokens by default, and `datetime.fromtimestamp` then raises on them, crashing `marshal watch` on a malformed line instead of skipping it. Fix applied: added `math.isfinite(ts)` to the guard; new test `test_loop_journal_last_fact_skips_non_finite_ts_instead_of_crashing` proves `NaN`/`Infinity`/`-Infinity` lines are skipped, not fatal.
  - `false` `reject` claim of tz-naive vs. tz-aware datetime mixing in `_dispatch_journal_last_fact` — refuted: every writer of `story_started_at`/`story_ended_at` in this codebase (`_format_entry_ts` and its structurally identical siblings in `dispatch_supervisor/__main__.py`, `supervisor/__main__.py`, `cli/retire.py`, `cli/init.py`, `cli/deploy.py`, `cli/spin.py`) unconditionally appends `"Z"`, so `.replace("Z", "+00:00")` always yields a tz-aware datetime; this scenario is unreachable under the codebase's actual invariants.
  - `medium` `patch` `_default_ports`'s `dispatch_last_fact` closure calls `gather_dispatch_journal_facts` → `LocalFs.read_text`, which raises `FsError` on any non-`FileNotFoundError` `OSError` or a `UnicodeDecodeError` — uncaught in `dispatch_last_fact`, unlike its sibling `loop_last_fact`, which already wraps its own read in `except OSError: return None`. Fix applied: wrapped the `gather_dispatch_journal_facts` call in `try/except FsError: return None`, importing `FsError` from `..adapters.fs_local`.
  - `false` `reject` claim that an empty `run_id`/`loop_id` causes a silent wrong-file read — refuted: no sibling file exists at the collapsed path in this layout, and both closures already return `None` gracefully on any read failure (`except OSError` / `run_dir is None`), matching the intended never-fabricate contract; no demonstrated wrong-data outcome.
  - `medium` `patch` the dedicated `_default_ports` real-I/O test block covers every other port (`list_runs`/`run_status`, `marshal_home`, `loop_sha`, `list_prs`, `discover_projects`/`load_queue`) except the two new ones this story adds (`loop_last_fact`, `dispatch_last_fact`) — if either closure's path construction or lazy import regresses, both would silently return `None` on every call and the engine-selection fix would revert to the pre-fix always-loop-wins behavior in production while the full test suite (which only exercises these ports through injected fakes) stays green. Pre-verified per the verification-gap layer's filed evidence. Fix applied: added `test_default_ports_loop_last_fact_reads_the_real_journal` and `test_default_ports_dispatch_last_fact_reads_the_real_journal`, each writing a real `journal.jsonl` fixture and reading it back through the actual closure.
  - `false` `reject` the "no dispatch run" reading (Reading A vs. Reading B divergence) — refuted as a live gap: this fixture variation is a no-op path unaffected by the diff (gated behind `raw_dispatch_id` being truthy) and was already covered by pre-existing tests before this story.
  - `false` `reject` the fix's scope is narrower than the Problem statement's broader framing (limited to the unpinned branch) — refuted as a defect: explicitly defensible given the Never boundary's "do not... move a primary checkout" spirit and the dedicated pinned-run test (`test_a_pinned_run_id_is_never_overridden_by_a_fresher_dispatch_run`); the auditor itself frames this as a reasonable, intentional scoping choice.
- Patch fixes requested from the same step-03 subagent (`af5d9fa8fa5859b9d`); see its follow-up report for what changed.
