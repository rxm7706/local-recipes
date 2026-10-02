---
title: '82.5: Budget and idle signals judge staleness monotonically, keep a story''s breach story-scoped, and read only real idleness'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
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
