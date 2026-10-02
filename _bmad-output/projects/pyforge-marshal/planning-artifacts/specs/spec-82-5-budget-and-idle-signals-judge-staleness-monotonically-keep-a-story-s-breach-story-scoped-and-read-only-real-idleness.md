---
title: '82.5: Budget and idle signals judge staleness monotonically, keep a story''s breach story-scoped, and read only real idleness'
type: 'fix'
created: '2026-10-02'
status: 'in-progress'
baseline_revision: '3df4ea57b77418a4307b0d0ab54fb681a80e2a14'
review_loop_iteration: 0
followup_review_recommended: false
warnings: [oversized]
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The supervisor's budget and idle signals misread time and observation. Re-verified at HEAD a7cdb91fe4:

- The usage-staleness gate computes `is_stale = state_mtime is None or (moment.timestamp() - state_mtime) > threshold_s`
  (`supervisor/__main__.py:1840`), a wall-clock delta, while every other elapsed-time decision in the tick loop uses
  `clock.monotonic()` (`core/supervise.py`'s `Sample.monotonic_s`). A forward NTP step or a suspend marks a fresh sample
  stale; a backward step marks a stale one fresh, and a hard `harness.stop` can follow (DW-FU-3-6-5).
- The window is `threshold_s = float(idle_threshold_minutes) * 60.0` (`:842`), 25 minutes by default, but bmad-loop writes
  `state.json` only at session boundaries and the rendered harness policy allows `session_timeout_min = 180`
  (`adapters/harness_bmadloop.py:292`). From minute 25 of any session both token ceilings are skipped and `MRS-SUPV-006` is
  journaled on healthy stories (DW-FU-3-6-6).
- `_act_on_budget_transition` (`:1477`) answers a per-story breach with `harness.stop` on the whole run (`:1590`) and ends
  the tick loop with `detach_reason = "budget-" + scope + "-" + metric + "-exceeded"` (`:1639`): one outlier story abandons
  the rest of an overnight wave under a story-scoped reason (DW-FU-3-6-8).
- `core/supervise.py::_anchor_index` (`:183-192`) re-arms the idle window only when
  `current.pane_content != previous.pane_content or current.log_mtime != previous.log_mtime` (`:190`). Two samples that are
  both `None` (a broken `tmux`, a permissions error, a missing log) compare equal and read as maximal idleness, driving the
  ladder against a working session (DW-FU-3-5-6); and a raw whole-string `!=` means a redrawing spinner, counter or token
  tally re-arms the window every tick, so a hung session never leaves `LadderRung.NONE` (DW-FU-3-5-9).

**Approach:**

- Freshness is monotonic: the supervisor records the monotonic reading at which it first observed each distinct
  `state.json` mtime, and a sample is stale when the monotonic time since then exceeds the window; an mtime ahead of the wall
  clock is unevaluable, never fresh.
- The staleness window is its own value, no shorter than the rendered session timeout, which `cli/spin.py` passes the
  supervisor beside `idle_threshold_minutes`.
- A per-story breach journals a story-scoped observation (the story, metric, observed and limit values) with a new MRS-SUPV
  finding and leaves the run going; a per-run breach still stops the run as today. A per-story breach is reported once per
  story.
- `Sample` says whether each channel was observed. Samples where neither the pane nor the log was observable hold the
  ladder at its current rung and journal one unobservable WARN; they never count as idleness.
- The pane comparison ignores volatile redraws: digit runs and spinner glyphs are normalised away before comparing, so only
  substantive output re-arms the window; the log mtime still re-arms it as today.

Ledger key: `82-5-budget-and-idle-signals-judge-staleness-monotonically-keep-a-story-s-breach-story-scoped-and-read-only-real-idleness`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-2 (idleness is detected from external evidence; per-story and per-run ceilings), with Story 3.6
  (FR-13, FR-14; AD-8, AD-32) and Story 3.5 (FR-12; AD-9, AD-32). Story 3.6's rule that a story-scope breach mirrors the
  ladder's terminal `defer` is the defect this story corrects. No new CAP; no flag.

## Acceptance Criteria

- Given a `state.json` mtime first observed 40 minutes ago (monotonic), a 25-minute idle threshold and a 180-minute session timeout When the budget tick runs Then the sample is usable and no `MRS-SUPV-006` is journaled
- Given a wall clock stepped forward one hour between two ticks with an unchanged `state.json` When the budget tick runs Then the sample's freshness does not change
- Given an mtime later than the current wall clock When the budget tick runs Then the sample is unevaluable, not fresh
- Given a per-story token or wall-clock breach When the tick acts Then the run is not stopped, a story-scoped observation names the story with observed and limit, and the tick loop continues
- Given a per-run breach When the tick acts Then the run stops and detaches as today
- Given two consecutive samples with `pane_content` and `log_mtime` both unobservable When the ladder evaluates Then it stays at its rung and one unobservable WARN is journaled
- Given panes that differ only in a seconds counter or a spinner glyph with an unchanged log mtime When the ladder evaluates past the threshold Then it escalates
- Given each fix reverted in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Keep `core/supervise.py` pure. Keep the ladder's rungs, order and thresholds. Register every new code in
`core/findings.py` and `core/verdict.py`. Close DW-FU-3-6-5, DW-FU-3-6-6, DW-FU-3-6-8, DW-FU-3-5-6 and DW-FU-3-5-9 in
`deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this story).

**Never:** Do not invent a per-story skip in bmad-loop or write its state. Do not loosen the per-run ceilings. Do not change
the supervisor's journal attach, detach or signal handling (Story 82.4's surface).

</intent-contract>

## Code Map

Package root `src/shared/packages/pyforge-marshal/` (paths below are relative to `src/pyforge/marshal/` unless `tests/`).
Line anchors re-verified at HEAD 3df4ea57b7 (the contract's anchors still hold).

- `core/supervise.py` -- pure core. `Sample` (`:146`) gains observed-ness; `_anchor_index` (`:182`) is the shared change scan
  behind `idle_since`/`idle_anchor`/`evaluate_idle` (`:248`). Add here, pure and I/O-free: `normalise_pane`,
  `shows_fresh_output`, `UsageFreshness`, `MtimeSighting`, `judge_usage_freshness`; `evaluate_idle` takes `held`.
- `supervisor/__main__.py` -- impure edge. `threshold_s` (`:842`); `run_supervisor` signature (`:752`); loop state
  (`usage_stale` `:1117`, `last_acted_rung` `:1370`); `_act_on_budget_transition` (`:1477`, `harness.stop` `:1590`,
  `detach_reason` `:1639`); staleness gate (`:1838-1887`); sample build, history trim and ladder (`:1936-2037`, the trim
  compares raw panes at `:1999-2001`); `main()` argv parse (`:2780-2871`); module docstring usage line (`:4`).
- `cli/spin.py` -- spawn argv (`:1279-1295`); `idle_threshold_minutes` is read at `:1237`. The new window is passed
  beside it.
- `adapters/harness_bmadloop.py` -- `_POLICY_TEMPLATE` carries `session_timeout_min = 180` (`:292`) and is never
  overwritten by `render_policy_toml`; precedent for deriving a module constant from it:
  `ADAPTER_REVIEW_MODEL_STOCK_DEFAULT` (`:1033`).
- `core/findings.py` (registry `:1466-1480`, narrative `:215-310`) and `core/verdict.py` (map `:867-879`) -- register the
  new codes; `MRS-SUPV-010` is the highest in use, so `-011`/`-012` are free.
- `tests/unit/test_supervise.py`, `tests/unit/test_supervisor.py` (`FakeObserver` `:211`, `AdvancingClock` `:169`,
  existing guards `test_an_unobservable_session_is_never_treated_as_idle` `:1640`,
  `test_a_flaky_pane_capture_never_re_arms_the_idle_window` `:1689`,
  `test_a_channel_that_breaks_mid_run_is_never_treated_as_idle` `:2360`), `tests/unit/test_spin.py`,
  `tests/unit/test_cli.py`, `tests/unit/test_policy.py` -- the argv shape is asserted in the last three.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW rows at `:3711`, `:3752`,
  `:3891`, `:3905`, `:3933`.

Read-only evidence driving the design:

- The supervisor already drops a pane-`None` sample and holds the ladder at `NONE` (`:1938-2035`); the defect that remains
  is the pure core (`None == None` reads as no change) and that a dark tick resets `last_acted_rung` to `NONE`, which
  re-fires a nudge on resume. Existing tests pin that pane-dark and both-dark runs take no ladder action; keep them green.
- `FakeObserver.state_json_mtime` defaults to `float("inf")` as a stand-in for "never stale". An mtime ahead of the wall
  clock is now unevaluable (AC 3), so the default moves to the fake clocks' shared start instant.
- `core/supervise.py` stays pure: freshness state (the sighting) is held by the caller and passed in and out.

## Design Notes

- Freshness: age = (wall delta at the mtime's FIRST sighting, clamped to zero) + (monotonic time since that sighting).
  The wall delta is used once, so a later step or suspend cannot move it, and a `state.json` that was already old at attach
  is stale at once. A new mtime ahead of the wall clock is unevaluable and is not recorded. `None` is stale as before.
- Window: `max(idle_threshold_minutes, RENDERED_SESSION_TIMEOUT_MIN)`, passed as an optional eleventh argv value and an
  optional `run_supervisor` parameter. When omitted the supervisor derives the same floor itself, so a direct caller never
  regains the 25-minute trap.
- Per-story breach: one `budget-story-breach` observation per (story, metric), `MRS-SUPV-014` WARN, no stop, no detach.
  Per-run breach is unchanged.
- Unobservable: a sample is dark when neither channel was observed. A dark tick holds `last_acted_rung`, appends no sample,
  and journals one `idle-unobservable` WARN (`MRS-SUPV-015`) per dark episode. Pane-dark with a live log keeps today's
  behaviour exactly.
- Volatile redraws: `normalise_pane` strips digit runs and spinner glyphs (Braille U+2800-28FF, U+25D0-25D3, U+25F4-25F7,
  U+2722-274B) before the pane comparison; the log mtime comparison is unchanged. The supervisor's history trim uses the
  same `shows_fresh_output`, so the two cannot disagree.

## Tasks & Acceptance

**Execution:**
- `core/supervise.py` -- add `Sample.pane_observed`/`log_observed`/`observable`, make `_anchor_index` skip dark samples and
  compare panes through `shows_fresh_output`, add `evaluate_idle(held=)`, `UsageFreshness`, `MtimeSighting`,
  `judge_usage_freshness` -- the pure decisions for ACs 1-3, 6, 7
- `adapters/harness_bmadloop.py` -- export `RENDERED_SESSION_TIMEOUT_MIN` derived from `_POLICY_TEMPLATE` -- one source for
  the window floor
- `cli/spin.py` -- pass `max(idle_threshold_minutes, RENDERED_SESSION_TIMEOUT_MIN)` as the eleventh argv value -- AC 1
- `supervisor/__main__.py` -- accept the optional window (argv and `run_supervisor`), replace the wall-clock gate with
  `judge_usage_freshness`, make a per-story breach an observation, hold on a dark tick and journal it once, use
  `shows_fresh_output` in the trim -- ACs 1-7
- `core/findings.py`, `core/verdict.py` -- register `MRS-SUPV-014` (story budget breach) and `MRS-SUPV-015` (idle channels
  unobservable), both WARN -- boundary rule
- `tests/unit/test_supervise.py`, `tests/unit/test_supervisor.py`, `tests/unit/test_spin.py`, `tests/unit/test_cli.py`,
  `tests/unit/test_policy.py` -- one failing-on-revert test per fix; `FakeObserver` default moves off `inf`; argv
  assertions gain the new value -- AC 8
- `deferred-work-ledger.md` -- close DW-FU-3-6-5, DW-FU-3-6-6, DW-FU-3-6-8, DW-FU-3-5-6, DW-FU-3-5-9 with a `resolved:`
  line naming this story -- boundary rule

**Acceptance Criteria:** the eight criteria in the intent contract above, unchanged.

## Spec Change Log

- 2026-10-02: planned from the pre-authored contract; contract preserved verbatim. No amendments.

## Binding

Parent: Stories 3.5 and 3.6, `spec-pyforge-marshal` CAP-2; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-5-budget-and-idle-signals-judge-staleness-monotonically-keep-a-story-s-breach-story-scoped-and-read-only-real-idleness`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-3-6-5, DW-FU-3-6-6, DW-FU-3-6-8, DW-FU-3-5-6, DW-FU-3-5-9.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.

### 2026-10-02 — Landing refused on a merge conflict with Story 82.4 (operator fix)
- PR #1740 conflicted with `main` after Story 82.4 landed (MRS-DISP-038): both stories minted `MRS-SUPV-011`/`012` with different meanings, and both appended tests at the end of `tests/unit/test_supervisor.py`.
  - `[high]` `[patch]` 82.5's two codes renumbered to the next free ones: `MRS-SUPV-014` (per-story budget breach) and `MRS-SUPV-015` (idle channels unobservable), in this spec, `core/findings.py`, `core/verdict.py`, `supervisor/__main__.py` and both tests. 82.4 keeps `011`-`013` and `MRS-SPIN-018`.
  - `[high]` `[patch]` `test_supervisor.py` resolved as the 3-way merge of both bodies plus both appended blocks; 82.4's `test_a_signal_never_overrides_a_budget_stop_reason` now drives a per-RUN breach (`budget-run-tokens-exceeded`), because under this story a per-story breach no longer stops the run. `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exit 0 (10005 passed); pyforge-core's suite exit 0 (2156 passed); `pixi run --frozen -e pyforge-guild lint-types` exit 0.
