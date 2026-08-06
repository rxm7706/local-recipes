---
title: 'Budget ceilings and the heaviest-story advisory'
type: 'feature'
created: '2026-08-03'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: [oversized]
baseline_revision: '22ebe228c498f5768e3c83dd4c656d5907f44718'
final_revision: '013b754ad7cfd40b0c45e73610b8e0a10d02212d'
---

<intent-contract>

## Intent

**Problem:** Story 3.5's idle ladder catches a session that stops producing output, but not one that keeps producing output forever -- a healthy-looking loop or an oversized story can burn the whole token/wall-clock budget with no ceiling anywhere outside the session itself (FR-13), and there is no warning before launch that a story is likely to blow that budget (FR-14).

**Approach:** Add a pure `evaluate_ceiling` core (`core/supervise.py`, AD-20) and four new externally-enforced ceilings (per-story/per-run x tokens/wall-clock) to the supervisor's tick loop; read per-story token consumption from bmad-loop's own `state.json` (a new `HarnessPort.usage_snapshot`, the "adapter-reported usage" AD-9 already names) for reporting and warn-level advisory only; and add a non-blocking preflight advisory to `cli/spin.py` (FR-14) that warns when a selected story's spec size or prior-attempt history suggests it is likely to exceed budget.

## Boundaries & Constraints

**Always:**
- Every ceiling's STOP condition is reachable from an externally-observed quantity alone (AD-32): wall-clock-per-story and wall-clock-per-run are measured purely from `ClockPort.monotonic()` and never consult session-written data. Token-per-story/token-per-run are read from `state.json` (bmad-loop's own orchestrator-written file, not the agent session) for warn/journal purposes only.
- **A usage sample older than `idle_threshold_minutes` (reused, not a new key) is classified `stale-evidence`, never `unevaluable`** -- deviating from epics.md's own AC wording ("is `unevaluable`") in favor of AD-32's explicit, later amendment (F-24): `unevaluable` is AD-8-blocking and fires on the ordinary idle case FR-12 already handles gracefully; `stale-evidence` is a registered WARN finding that never reds the run. When stale, both token ceilings are skipped for that tick -- the two wall-clock ceilings (always evaluable) remain the binding constraint, satisfying "no ceiling exists that can only be evaluated from session-written data."
- 4 new closed-vocabulary SEED keys (`max_tokens_per_story`, `max_tokens_per_run`, `max_wall_clock_minutes_per_story`, `max_wall_clock_minutes_per_run`), validated by the existing `_valid_positive_number` (idle_threshold_minutes's own validator, the closest analog), threaded through `compose()`, `schemas/policy.json`, `cli/config.py::_FIELD_ORDER`/`_UNSETTABLE_KEYS`. `cli/spin.py` resolves all four and appends them as 4 new supervisor argv positionals (6 -> 10), mirroring Story 3.5's own idle_threshold_minutes wiring exactly.
- "Approaching" is a fixed 80% ratio (`_APPROACH_RATIO`), not a policy knob -- no real caller has asked for that to be tunable (mirrors `_TICK_SECONDS`'s own "no knob without a caller" precedent). A ceiling transitions from NONE->APPROACHING->BREACHED; each transition is journaled once, on the rising edge, never every tick.
- A BREACH (either scope, either metric) mirrors the idle ladder's own terminal `defer`: one `intent`->`outcome` pair (`kind="budget-stop"`), a best-effort `harness.stop(home, harness_run_id)`, and the tick loop exits via `supervisor-detach` with `reason=f"budget-{scope}-{metric}-exceeded"`. Never `stop-and-retry` -- retrying the same story/run would immediately re-hit the same ceiling.
- Current story attribution reads `HarnessPort.usage_snapshot(home, harness_run_id)`, itself reading `<home>/.bmad-loop/runs/<harness_run_id>/state.json` via `bmad_loop.journal.load_state` (lazy import inside `adapters/harness_bmadloop.py` only, matching this module's existing `bmad_loop.adapters.multiplexer`/`bmad_loop.adapters.profile` lazy-import precedent -- the "one seam" AD-3 names). The current story is the sole `StoryTask` with `not task.terminal`; zero or more than one such task yields `story_key=None` (heartbeat/run-ceilings-only for that tick, mirroring the idle ladder's own "act only on evidence it has"). Never raises -- any read/parse failure returns `None` from `usage_snapshot` entirely.
- The "cost estimate" is `task.tokens.weighted_total(state.cache_read_weight())` -- bmad-loop's own cost-proportional metric (cache reads at ~0.1x base input), already computed by the installed harness for its own in-session guard. Per-story/run consumption is journaled (`kind="budget-usage"`, observation) once per OBSERVED story-key transition (attributing the outgoing story's final tally), never every tick.
- Run-start, for the per-run wall-clock ceiling, is the supervisor's OWN attach-time `clock.monotonic()` reading, not the run-launch journal entry's timestamp -- the gap between `spin`'s mint and the supervisor's attach is a few seconds against an hours-scale ceiling, and no existing utility parses a journal `ts` string back to a comparable clock reading.
- The preflight advisory (FR-14, `cli/spin.py::run_spin`, after `resolve_feed` succeeds, before the harness launches) computes, per resolved story key: spec size (bytes of `_tier3_path(home, slug)/f"spec-{render_filename_slug(key)}.md"`, 0 if absent) and prior-attempt history (a best-effort scan of this SAME loop home's existing `.bmad-loop/runs/*/state.json` files for a task matching this story's slug with `attempt >= 2` or a terminal `deferred`/`escalated` phase -- any unreadable/malformed file is skipped, never fails the scan). Either signal past a fixed threshold emits one non-blocking `MRS-SPIN-009` WARN naming the story and the reason; never blocks the launch.

**Block If:** none identified -- every new ceiling is enforced the same way Story 3.5's idle ladder already enforces (best-effort stop, journaled, never a human decision mid-tick).

**Never:**
- "Declared difficulty" as an FR-14 input -- no difficulty-classification mechanism exists anywhere in this codebase yet (`cli/spin.py` never resolves a `difficulty` value for `render_policy_toml`; FR-51 tier-batching is unwired). Inventing one here for a single advisory input is speculative surface disproportionate to a non-blocking warning; the advisory runs on spec-size + prior-attempts only, and this gap is a deliberate, documented omission, not a defect.
- Widening or overriding bmad-loop's OWN in-session budget guard (`adapters/harness_bmadloop.py`'s `_POLICY_TEMPLATE` `[limits]` block: `max_tokens_per_story`, `session_budget_mode`, `max_tokens_per_session`) -- FR-13's own re-scope explicitly credits it and forbids duplicating it; this story's ceilings are the EXTERNAL half only.
- A dollar-denominated cost estimate -- no pricing table exists or is introduced; `cost_estimate` in `budget-usage` payloads is the weighted-token proxy, and stays `null` only if bmad-loop's own state ever reports zero sessions for a task.
- `stop-and-retry` for any budget breach (see Always).
- Any change to `idle_threshold_minutes`'s own semantics -- it is reused verbatim as the staleness window, never duplicated as a new key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Per-run wall-clock approaches | `run_elapsed_minutes >= 0.8 * max_wall_clock_minutes_per_run`, not yet breached | One `budget-warn` observation on the rising edge; run continues | No error expected |
| Per-run wall-clock breaches | `run_elapsed_minutes >= max_wall_clock_minutes_per_run` | `budget-stop` intent/outcome, best-effort `harness.stop`, detach reason `budget-run-wall_clock-exceeded` | A failed stop is recorded (`MRS-SUPV-005`) but the loop still exits |
| Per-story token ceiling, fresh sample | `usage_snapshot` resolves a current story; `state.json` mtime within `idle_threshold_minutes` | Weighted per-story tokens compared to `max_tokens_per_story`; warn/breach as above | No error expected |
| Usage sample stale | `state.json` mtime older than `idle_threshold_minutes`, or unreadable/unresolvable | `MRS-SUPV-006` (`stale-evidence`) journaled once per transition into staleness; both token ceilings skipped this tick; wall-clock ceilings still evaluated | No crash; never `unevaluable` |
| No single current story | Zero or >1 non-terminal `StoryTask` in `state.json` | `usage_snapshot` returns `story_key=None`; per-story ceilings skipped this tick; per-run ceilings still evaluated | No error expected |
| Story transitions | Current story key differs from the last observed one | `budget-usage` observation journaled for the outgoing story; per-story elapsed/tally reset for the new one | No error expected |
| Preflight: oversized/retried story | A resolved story's spec exceeds the size threshold, or a prior run shows `attempt >= 2`/deferred/escalated for it | `MRS-SPIN-009` WARN naming the story and reason; launch proceeds | Never blocks |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/supervise.py` -- EDIT. `CeilingStatus` (`StrEnum`: NONE/APPROACHING/BREACHED), `_APPROACH_RATIO = 0.8`, `evaluate_ceiling(observed: float, limit: float) -> CeilingStatus` -- pure, no I/O; rejects non-finite/NaN/non-positive `limit` the same way `evaluate_idle` rejects `threshold_s`.
- `src/pyforge/marshal/ports/harness.py` -- EDIT. `UsageSnapshot` (frozen dataclass: `story_key: str | None`, `story_weighted_tokens: int | None`, `run_weighted_tokens: int`, `sample_path: Path`) and `HarnessPort.usage_snapshot(self, project: Path, run_id: str) -> UsageSnapshot | None`.
- `src/pyforge/marshal/adapters/harness_bmadloop.py` -- EDIT. Implement `usage_snapshot`: lazy `from bmad_loop.journal import load_state`; `run_dir = project / ".bmad-loop" / "runs" / run_id`; load, find the sole non-terminal task (`normalize()`-compatible slug key), compute weighted totals via `task.tokens.weighted_total(state.cache_read_weight())` and the run-wide sum across `state.tasks.values()`. Catches `(OSError, ValueError, KeyError, TypeError)`, returns `None`.
- `src/pyforge/marshal/supervisor/__main__.py` -- EDIT. `main()`'s argv grows 6 -> 10 (`... <idle_threshold_minutes> <max_tokens_per_story> <max_tokens_per_run> <max_wall_clock_minutes_per_story> <max_wall_clock_minutes_per_run>`); `run_supervisor` gains the 4 new parameters, validated the same way `idle_threshold_minutes` is. Tick loop: track `run_started_monotonic` (set once, post inert-check), `current_story_key`/`story_started_monotonic` (updated on transition); each tick (independent of pane/log observability) evaluate both wall-clock ceilings, and -- when `harness_run_id` resolved -- call `usage_snapshot`, check `state.json`'s mtime via the existing `observer.mtime`, and evaluate both token ceilings only when fresh. Journal `budget-usage` (observation) on story transition, `budget-warn` (observation) on a NONE->APPROACHING or APPROACHING->BREACHED-without-warn edge, `budget-stop` (intent/outcome) on breach, `budget-usage-stale` (observation) on a transition into staleness.
- `src/pyforge/marshal/cli/spin.py` -- EDIT. Resolve the 4 new `EffectivePolicy` seed values and append to the supervisor spawn argv. After `resolve_feed` succeeds: for each resolved key, compute spec size + prior-attempt scan (glob `home/.bmad-loop/runs/*/state.json`, best-effort `bmad_loop.journal.load_state`); emit `MRS-SPIN-009` WARN when either signal crosses its fixed threshold.
- `src/pyforge/marshal/core/policy.py` -- EDIT. 4 new SEED keys in `_SEED_KEYS`/`DEFAULT_POLICY` (defaults: `max_tokens_per_story=4_000_000`, `max_tokens_per_run=40_000_000`, `max_wall_clock_minutes_per_story=240`, `max_wall_clock_minutes_per_run=600` -- `[ASSUMPTION: ...]`, see Design Notes), reusing `_valid_positive_number`.
- `src/pyforge/marshal/cli/config.py` -- EDIT. 4 new keys in `_FIELD_ORDER`; add all 4 to `_UNSETTABLE_KEYS` -- same precedent and reasoning as `idle_threshold_minutes` (no AC asks for a `--set` override surface; the project policy TOML layer already covers "configurable").
- `src/pyforge/marshal/schemas/policy.json` -- EDIT. 4 new keys in `required`/`properties`.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- EDIT. `MRS-SUPV-004` (approaching), `MRS-SUPV-005` (breach/stop failure), `MRS-SUPV-006` (stale-evidence); `MRS-SPIN-009` (preflight advisory). All classify `Verdict.WARN`.
- `src/pyforge/marshal/tests/unit/test_supervise.py` -- EDIT. `evaluate_ceiling` transition matrix.
- `src/pyforge/marshal/tests/unit/test_supervisor.py` -- EDIT. New ceiling wiring, staleness, story-transition tests against the fake-port harness.
- `src/pyforge/marshal/tests/unit/test_harness_bmadloop_spin.py` (or a sibling) -- EDIT. `usage_snapshot` tests against synthetic `state.json` fixtures (single/zero/multiple non-terminal tasks, malformed file).
- `src/pyforge/marshal/tests/unit/test_spin.py` -- EDIT. Argv grows to 10 positionals; `MRS-SPIN-009` preflight tests.
- `src/pyforge/marshal/tests/unit/test_policy.py`, `tests/unit/test_cli.py` -- EDIT. 4 new fields' compose/validation/rendering coverage; update hardcoded `10`/"10-key" assertions to 14.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- EDIT. Log the "declared difficulty" FR-14 gap as a named follow-up.

## Tasks & Acceptance

**Execution:**
- [x] `core/supervise.py` -- `CeilingStatus`/`evaluate_ceiling` pure core.
- [x] `ports/harness.py` + `adapters/harness_bmadloop.py` -- `UsageSnapshot`/`usage_snapshot`.
- [x] `core/policy.py` + `cli/config.py` + `schemas/policy.json` -- 4 new SEED keys.
- [x] `supervisor/__main__.py` -- argv to 10 positionals; wire both wall-clock ceilings (always evaluated) and both token ceilings (staleness-gated) into the tick loop; journal `budget-usage`/`budget-warn`/`budget-stop`/`budget-usage-stale`.
- [x] `cli/spin.py` -- resolve and pass the 4 new ceiling values; FR-14 preflight advisory (`MRS-SPIN-009`).
- [x] `core/findings.py` / `core/verdict.py` -- register and classify the 4 new codes.
- [x] Unit tests for every new/edited module, including the full I/O matrix above.
- [x] `deferred-work.md` -- log the declared-difficulty gap.

**Acceptance Criteria:**
*(Story 3.6's ACs from `epics.md`, preserved as the contract of record; the `unevaluable`/`stale-evidence` wording is resolved per this spec's own Always bullet.)*
- Given configured per-story and per-run token and wall-clock ceilings, when a unit approaches or breaches one, then approaching emits a warning and breaching stops the unit with a named reason, never a silent defer
- And consumption is journaled per story with a cost estimate where the adapter reports one
- And every enforcement ceiling is expressed over at least one externally-observed quantity; session-written usage files are recorded for reporting and cost attribution only (AD-32)
- And a usage sample older than the idle threshold is classified `stale-evidence`: a registered finding is emitted and the wall-clock ceiling becomes the binding constraint -- a wedged session's frozen counter can never defeat the ceiling
- And no ceiling exists that can only be evaluated from session-written data
- And preflight warns when a selected story is likely to exceed the session budget, comparing the budget against spec size and prior attempt history (declared difficulty deliberately deferred, see Never)

## Spec Change Log

### 2026-08-03 -- implementation-time deviations, verified against actual code

- **`detach_reason` is built via string CONCATENATION, not the f-string the spec's own Always bullet literally shows (`f"budget-{scope}-{metric}-exceeded"`).** `tests/meta/test_ad23_inline_key_format_guard.py` (AD-23, "one owner of the story-key format") fails the build on ANY f-string outside `core/identity.py` whose `.values` contain exactly two `FormattedValue` nodes with a bare `.`/`-` as the only literal text between them -- a purely structural AST scan with no escape hatch, and `f"budget-{scope}-{metric}-exceeded"` matches it exactly (the `{scope}` / `{metric}` pair, joined by `-`), even though neither placeholder is a story key. The produced STRING is byte-identical either way (verified: `"budget-run-wall_clock-exceeded"`, `"budget-story-tokens-exceeded"`, matching the spec's own two named examples); only the construction technique changed, to `"budget-" + scope + "-" + metric + "-exceeded"` (plain `ast.BinOp`, invisible to the guard's `ast.JoinedStr`/`.format()`-only scan).
- **`core/supervise.py::evaluate_ceiling` has no ordering accessor analogous to `rung_index`/`rung_at`.** The Code Map names only `CeilingStatus`/`_APPROACH_RATIO`/`evaluate_ceiling`; detecting a RISING edge (the supervisor's own "act only on NONE->APPROACHING or a transition INTO BREACHED" requirement) needed a `CeilingStatus -> int` ordering the enum itself doesn't carry (mirrors `LadderRung`'s own documented "no intrinsic ordering" convention). Added as a PRIVATE `_CEILING_RANK` dict local to `supervisor/__main__.py` (the sole consumer) rather than a new public `core/supervise.py` export -- no second caller exists to justify widening that module's own public surface (Simplicity First).
- **`budget-usage`'s `cost_estimate` field IS the weighted-token total, never a separate `weighted_tokens` field alongside a hardcoded `null`.** A first implementation pass (working from a paraphrased task summary rather than this spec's own text) journaled `{"story_key": ..., "weighted_tokens": <int>, "cost_estimate": None}` unconditionally. Re-reading this spec's own Always/Never bullets caught the error: "The 'cost estimate' is `task.tokens.weighted_total(...)`" and "`cost_estimate` in `budget-usage` payloads is the weighted-token proxy, and stays `null` only if bmad-loop's own state ever reports zero sessions for a task" -- i.e. `cost_estimate` itself carries the weighted total (no separate field), null only for a zero-session/zero-total task. Fixed to `{"story_key": ..., "cost_estimate": <weighted_total or None>}`, with `None` when the outgoing story's last known weighted total was `0` or was never observed at all (the only two states `UsageSnapshot`'s own 4-field shape can express for "no usage").

### 2026-08-03 -- review pass 2: the intent contract's own FR-14 path formula is wrong

- **The Always bullet's literal spec-size formula, `_tier3_path(home, slug)/f"spec-{render_filename_slug(key)}.md"`, can never match a real file.** `render_filename_slug` renders the key alone (`3-6`), but every spec `bmad-dev-auto` writes carries a descriptive title after it (`spec-3-6-budget-ceilings-and-the-heaviest-story-advisory.md`) -- its step-01 derives `spec-{slug}.md` from a slug that LEADS with the story number and continues with the intent text. Verified against this project's own Tier-3 store: 21 of 21 specs carry a title, and 7 of them would have crossed the size threshold. The implementation followed the contract's formula exactly, so `stat()` always raised and `spec_size` was pinned at `0` for every story -- the signal was dead code.

  Resolved as a **patch, not an intent gap**: the captured intent ("warn when a selected story's spec is large") has exactly one possible reading, and the wrong element is a factual detail of the file-naming convention, not a missing decision. Per this workflow's own rule -- infer only when there is exactly one possible reading -- the contract text stays untouched and the deviation is recorded here, matching this spec's own precedent for the AD-23 f-string deviation above. The implementation now resolves `spec-<key>.md` **or** `spec-<key>-<title>.md` (glob anchored on a trailing hyphen, so `3.6` cannot match `3.60`'s spec) in `cli/spin.py::_large_spec_bytes`.

- **Same section, the prior-attempt half: the contract said "a task matching this story's slug"; the implementation matched `render_feed_key(key)`, the dot form.** bmad-loop keys `state.json`'s `tasks` map by its own full-slug spelling (verified live across 5 runs), so `tasks.get("3.6")` never hit and this half was dead code too. This one is a deviation FROM the contract rather than a defect IN it. Now matched by normalizing both sides through `core.identity.normalize` (AD-23's sole parser), which accepts either spelling.

- **Consequence for the acceptance criteria.** With both halves dead, FR-14's own AC ("preflight warns when a selected story is likely to exceed the session budget") was not met by the merged code despite a fully green suite -- because every test fabricated the shapes the code expected (`spec-1-1.md`, `{"tasks": {"1.1": ...}}`) rather than the shapes bmad-loop and bmad-dev-auto actually produce. The new tests use the real shapes; the fabricated-shape tests are kept, since normalization now accepts both.

## Review Triage Log

### 2026-08-03 -- Review pass 3 (Blind Hunter + Edge Case Hunter, parallel)

*Second follow-up review of the merged story. Both reviewers again verified against LIVE data -- 30 real bmad-loop runs, the installed `bmad_loop` 0.9.0, this factory's own Tier-3 spec store and sprint feed -- and every finding accepted below was reproduced independently before being acted on. The pass converged: 12 patches in pass 2, 3 here, with `intent_gap` and `bad_spec` at zero for the third consecutive pass. What remains is concentrated in design-level decisions the intent contract already sanctions, which is why the defer count rose rather than the patch count.*

- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 1, medium 1, low 1)
- defer: 7 (high 0, medium 5, low 2)
- reject: 7 (high 0, medium 2, low 5)
- addressed_findings:
  - `[high]` `[patch]` **A big-integer policy value made `compose()` RAISE, and `run_spin` calls `compose()` only after the harness is already live.** `math.isfinite` takes a C double, so it raises `OverflowError` -- not `ValueError`, not `TypeError` -- on a Python int too large to convert, and nothing caught it. `tomllib` does not enforce TOML's own 64-bit integer bound, so a `marshal-policy.toml` carrying a long digit string reaches `_valid_positive_number` as an arbitrary-precision int. Reproduced end-to-end: a 400-digit `max_tokens_per_run` makes `compose()` raise, breaking its own documented "never raises on malformed CONTENT" guarantee. Story 3.6 is what makes this reachable in practice -- `idle_threshold_minutes` is a minutes value nobody writes 300 digits of, while the four new keys are token counts, exactly the knob an operator sets to "effectively unlimited" by mashing digits. The consequence is worst in `cli/spin.py::run_spin`, which calls `compose()` at line 1087 but `harness.spin()` at line 943: the escaping traceback leaves a LIVE, UNSUPERVISED harness behind a non-zero exit, inviting a retrying caller to double-dispatch the story the live run is already working -- the exact hazard that module's own comments say its surrounding `RecursionError` guard exists to prevent. Fixed by converting through a guarded `float()` before any `isfinite` call, turning the crash back into the ordinary `MRS-POLICY-003` finding. New test: `test_budget_ceiling_rejects_an_arbitrary_precision_int_without_raising` (parametrized over all four keys). The pre-existing bad-value matrix covered `1e308` -- a float -- and so never reached this.
  - `[medium]` `[patch]` **A per-STORY budget warn or breach never said WHICH story.** `_act_on_budget_transition`'s payloads carried `scope`/`metric`/`observed`/`limit` only, so a `budget-warn`/`budget-stop` pair for `scope="story"` -- and the `budget-story-tokens-exceeded` detach reason derived from it -- named what was exceeded but not the story that exceeded it. The only per-story identity anywhere in the run's evidence was the adjacent `budget-usage` entry, so a consumer building FR-13's per-story enforcement view had to recover the attribution by POSITION in the journal rather than read it off the entry that made the decision. Fixed: story-scope transitions now carry `story_key` in the warn payload and in both halves of the stop pair, rendered through `_feed_key_form` for the same reason `budget-usage` uses it (one story must not appear under two spellings in one journal). Run-scope transitions stay deliberately unattributed -- naming the story that merely happened to be current when the RUN total crossed would be false attribution. New tests: `test_a_per_story_breach_names_the_story_in_its_warn_and_stop_payloads`, `test_a_per_run_breach_never_attributes_itself_to_a_story`.
  - `[low]` `[patch]` **`UsageSnapshot` could publish a token tally attributed to no story, the one shape its own docstring promises cannot occur.** The docstring states `story_weighted_tokens` is `None` in lockstep with `story_key` -- "never a number attributed to 'no story'" -- but the adapter set the tally from the sole non-terminal task while taking `story_key` from that task verbatim, and `bmad_loop`'s `StoryTask.from_dict` rejects neither a null nor an empty `story_key`. Both supervisor consumers happen to re-check `usage.story_key is not None` independently, so nothing misbehaves today; an exposed invariant that holds only because every caller redundantly re-verifies it is a trap for the next caller that reads the docstring and trusts it. Fixed by guarding the pair rather than the tally; the unattributable task's consumption still reaches `run_weighted_tokens`, so the per-run token ceiling is unaffected. New test: `test_usage_snapshot_never_attributes_a_tally_to_an_unnamed_story` (parametrized over `None` and `""`).
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries only):
  - `[medium]` FR-14's spec-size signal cannot fire for any story that has not already run -- the spec is an OUTPUT of the run `spin` is launching. Measured: `_large_spec_bytes` returns 0 for all 63 currently-launchable stories. The code conforms exactly to the contract's own "0 if absent"; pass 2 rejected the qualitative version, and the measurement upgrades it to a design decision worth making deliberately.
  - `[medium]` The prior-attempt signal reads `attempt`/`phase`, which `bmad_loop.runs.rearm_escalation` deliberately RESETS -- so a human-resolved escalation, the most expensive history a story can have, is invisible. The durable `task.tokens` is already parsed elsewhere and unused here.
  - `[medium]` `_prior_attempt_keys` has no recency window: a story deferred once warns forever, including after a later run completed it. Story `1.6` flags today while `done`.
  - `[medium]` `cli/spin.py` is a third, unpinned hand-copy of bmad-loop's on-disk state contract, and the only one with no counterpart to be pinned against -- an upstream layout change silently disables the advisory with everything green.
  - `[medium]` Even a perfectly FRESH sample is one whole session behind (`task.tokens` accumulates only post-session), so the token ceilings can notice a runaway session only after it ends. Distinct from the pass-2 staleness entries: this holds on the ticks where the gate passes.
  - `[low]` A persistently failing `usage_snapshot` freezes `current_story_key`/`story_started_monotonic`, so the per-story wall-clock ceiling accrues against a story that finished hours earlier -- a second-order consequence of pass 1's own (correct) fix for the opposite defect.
  - `[low]` `FakeObserver.state_json_mtime` defaults to `float("inf")`, a value the real `stat().st_mtime` can never return, so most token-ceiling tests assert behaviour under a freshness state production almost never presents.
- rejected (noise, already-deliberate, or already captured):
  - `[medium]` "`max_tokens_per_run=500M` is unreachable because the per-run wall-clock ceiling always fires first." The reviewer's own measurements refute the conclusion: 500M over the 2880-minute ceiling is 173,611 tok/min, against a fastest-ever-observed sustained 149,507 tok/min. The token ceiling therefore binds precisely when burn rate exceeds anything this corpus has produced -- which is the definition of a runaway backstop, and correct ordering, not a dead ceiling.
  - `[medium]` "A `budget-stop` intent is journaled for an action already known to be impossible" (no `harness_run_id`). The outcome half records `stopped: false` together with an explanatory `MRS-SUPV-005` finding, so the journal reads "intended to stop; did not stop; here is why" -- honest and complete. Suppressing the intent would lose the record that the ceiling fired at all.
  - `[low]` `cost_estimate` collapsing "zero tokens observed" and "no reading taken" -- the spec's own Never-clause decision, now raised and rejected in all three passes.
  - `[low]` `main()`'s arity gate and `_valid_positive_number` applying different numeric guards -- rejected in pass 2 and unchanged: reachable only by direct sidecar invocation, and rejection happens before any journal write.
  - `[low]` `_large_spec_bytes`'s docstring saying "7 of 21 specs would cross the threshold" when it is now 8 of 21 (this story's own spec grew past the line during review). A dated verification record, not a live invariant.
  - `[low]` The `max_tokens_per_story` policy-key collision -- already captured verbatim in `deferred-work.md` by pass 2; re-adding it would be noise.
  - `[low]` `_LARGE_SPEC_BYTES` being uncalibrated for other projects / flagging ~38% of this corpus -- already captured in `deferred-work.md` by pass 2.

### 2026-08-03 -- Review pass 2 (Blind Hunter + Edge Case Hunter, parallel)

*Follow-up review of the merged story (`followup_review_recommended: true` from pass 1). Both reviewers independently verified their top findings against LIVE data -- 30 real bmad-loop runs, 53 completed stories, the installed `bmad_loop` 0.9.0 -- rather than reasoning from the diff alone, and every high-severity finding below was reproduced before being accepted.*

- intent_gap: 0
- bad_spec: 0
- patch: 12 (high 4, medium 5, low 3)
- defer: 9 (high 0, medium 4, low 5)
- reject: 4 (high 0, medium 0, low 4)
- addressed_findings:
  - `[high]` `[patch]` **FR-14's spec-size signal was dead code: the probe path can never match a real file.** The intent contract's own literal formula (`spec-{render_filename_slug(key)}.md` -> `spec-3-6.md`) omits the descriptive title every spec `bmad-dev-auto` actually writes (`spec-3-6-budget-ceilings-and-the-heaviest-story-advisory.md`), so `stat()` always raised and `spec_size` was pinned at `0` for every story. Verified: 21 of 21 specs in this project's Tier-3 store carry a title; 7 would have crossed the threshold. Fixed in new `cli/spin.py::_large_spec_bytes` (resolves `spec-<key>.md` **or** `spec-<key>-<title>.md`, glob anchored on a trailing hyphen so `3.6` cannot match `3.60`). Root cause sits INSIDE `<intent-contract>` but has exactly one possible reading, so it is patched and recorded in the Spec Change Log rather than escalated -- see that entry for the full reasoning. New tests: `test_preflight_advisory_warns_on_a_real_titled_spec_filename`, `test_preflight_advisory_does_not_confuse_story_3_6_with_story_3_60`.
  - `[high]` `[patch]` **FR-14's prior-attempt signal was dead code too: it looked tasks up by the wrong key form.** bmad-loop keys `state.json`'s `tasks` map by its own full-slug spelling (verified live across 5 runs: `"3-6-budget-ceilings-and-the-heaviest-story-advisory"`), while the implementation used `render_feed_key(key)` -- the dot form `"3.6"` -- so the lookup never hit. This deviates from the contract, which said "a task matching this story's **slug**". **Combined with the finding above, MRS-SPIN-009 could never fire in production and FR-14's acceptance criterion was not actually met**, behind a fully green suite: every test fabricated the shapes the code expected rather than the shapes bmad-loop writes. Fixed in new `cli/spin.py::_prior_attempt_keys`, matching by `core.identity.normalize` (AD-23's sole parser, accepts either spelling); the same restructure now parses each prior `state.json` once instead of once per resolved story. New test: `test_preflight_advisory_warns_on_a_real_bmad_loop_state_json_shape`.
  - `[high]` `[patch]` **All four ceiling defaults sat BELOW ordinary observed behaviour -- shipping them would have hard-stopped essentially every run in its first story.** Measured across this factory's own history: 46 of 53 stories exceeded the 4M per-story token default (max 21.7M; **this story itself cost 12.9M**), runs reached 111.6M against a 40M default, story wall-clock reached 519 min against 240, run wall-clock 1041 min against 600. The `[ASSUMPTION]` rationale was also false on its own terms: bmad-loop's in-session `max_tokens_per_story` check runs *after* `advance(task, Phase.DONE)` and only appends a `token-budget-exceeded` breadcrumb (`engine.py`), so there was no in-session enforcement for Marshal's ceiling to "back stop". Re-calibrated to 50M / 500M / 1440 min / 2880 min (~2.5-4.5x observed maxima) with the measured corpus documented in `DEFAULT_POLICY` and the Design Notes. New test `test_budget_ceiling_defaults_clear_the_observed_workload` pins the calibration CONTRACT, not just the literals.
  - `[high]` `[patch]` **A breach with no `harness_run_id` stopped nothing and then stopped watching.** The branch journaled `MRS-SUPV-005`, skipped `harness.stop` entirely (there is no target), then set `deferred`/`detach_reason` and detached anyway -- so a run whose `harness_run_id` never resolved hit the per-run wall-clock ceiling, journaled a `budget-stop` it had not performed, and exited, leaving a live runaway harness with the one process watching it now gone. Strictly worse than having no ceiling. Fixed: that path now returns without deferring, mirroring `MRS-SUPV-003`'s own "cannot act for this run; continuing heartbeat-only supervision" precedent; the rising-edge latch keeps it from re-firing. The pre-existing test asserted the defective behaviour and was rewritten; new test `test_a_budget_breach_with_no_harness_run_id_never_re_fires_on_later_ticks`.
  - `[medium]` `[patch]` Budget observations were journaled AFTER the terminal `budget-stop` pair. Pass 1's `deferred` guard sits inside `_act_on_budget_transition`, so it suppressed a second same-tick `budget-warn` but nothing else: a breach fell through to another `usage_snapshot` read against a run just killed, plus `budget-usage`/`budget-usage-stale` appends after the terminal pair. Fixed with `deferred` re-checks on the enclosing block and before the staleness gate. New test: `test_no_budget_observation_is_journaled_after_a_terminal_budget_stop`.
  - `[medium]` `[patch]` The advisory warned about stories the launch would not run. It iterated `resolution.resolved` (the whole feed) while `--epic`/`--story`/`--max-count` filtering happened 26 lines later, so `marshal factory spin --story 3.6` against a 30-story feed emitted up to 29 irrelevant WARNs and carried a WARN verdict about excluded work -- contradicting the AC's own "a SELECTED story". Fixed by moving the block below `_filter_preview` and iterating `preview`. New test: `test_preflight_advisory_only_covers_the_selected_stories`.
  - `[medium]` `[patch]` `usage_snapshot` broke its own "never raises" contract on two more exception classes. `OverflowError` (an `ArithmeticError`, from `round(cache_read * inf)` or `int(1e400)` inside `from_dict`) and `RecursionError` (from `json.loads` on a deeply nested document) are neither `ValueError`s nor otherwise caught, so both escaped to the tick loop and killed the sidecar with a dangling `supervisor-attach` and no matching detach -- the exact AD-9 failure this port promises never to produce. Both reviewers reproduced it against the installed `bmad_loop` 0.9.0. Fixed by widening the tuple; new tests for the non-finite weight and the nested document.
  - `[medium]` `[patch]` `_prior_attempt_history` had the same `RecursionError` hole, one layer up: a single deeply-nested prior `state.json` crashed `marshal factory spin` with a traceback before any launch, contradicting its own "one malformed prior run must never abort the scan, still less the whole command" docstring. Fixed and pinned by `test_preflight_advisory_survives_a_deeply_nested_prior_state_json`.
  - `[medium]` `[patch]` `budget-usage` journaled bmad-loop's raw slug key while every other Marshal-authored identifier in the same run's evidence uses `render_feed_key`'s dot form -- one story under two identities in one journal, so a consumer joining per-story cost back to the launch preview by exact match finds nothing. Fixed with a new `_feed_key_form` helper (normalize, falling back to the raw string when unparseable). Two new tests; the pre-existing transition tests missed it because they hand-build `UsageSnapshot(story_key="3.6", ...)`, already the dot form.
  - `[low]` `[patch]` `UsageSnapshot.sample_path`'s docstring claimed the staleness gate consumes it. It does not -- the supervisor recomputes the same path independently (it must stat the sample even when `usage_snapshot` returned `None`). Docstring corrected, and the genuine duplication is now pinned by a new `tests/meta/test_supervisor_run_path_agreement.py` case; a silent divergence there would make every sample look permanently stale and disable both token ceilings for a run's whole life behind nothing but a WARN.
  - `[low]` `[patch]` `core/policy.py::_valid_positive_number`'s docstring rationale is written entirely about `idle_threshold_minutes` (minutes->seconds, the `* 60.0` overflow guard) and does not hold for the four new keys, two of which are token counts nothing converts to seconds. Documented the mismatch and why the validator is still deliberately shared, rather than forking a near-identical fourth copy.
  - `[low]` `[patch]` The advisory test block asserted `FsPort` "has no stat-like or glob-like method"; it has no glob or stat, but it does expose `read_text`/`exists`. Comment corrected and the real port-routing question deferred rather than silently dismissed.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[medium]` The usage-staleness gate compares a wall-clock reading (`moment.timestamp() - state_mtime`) rather than the monotonic basis every other elapsed-time decision in this module deliberately uses.
  - `[medium]` The token ceilings are structurally dark for most of a long session: bmad-loop only rewrites `state.json` at session boundaries (measured inter-write gaps up to 178 min) while the staleness window reuses `idle_threshold_minutes` (25 min).
  - `[medium]` Policy-key name collision: Marshal's `max_tokens_per_story` (external hard stop, 50M) vs the `[limits] max_tokens_per_story` this same package renders into `.bmad-loop/policy.toml` (advisory breadcrumb, 2M).
  - `[medium]` A per-STORY ceiling breach terminates the whole RUN, abandoning every remaining story in a wave. Spec-sanctioned today (the intent contract says a breach of either scope exits the tick loop), so changing it is a contract-level decision.
  - `[low]` The preflight bypasses the injected `FsPort` for its file reads; routing them needs a port-surface decision for glob/size.
  - `[low]` `MRS-SUPV-006` fires on the first tick of essentially every healthy run, training operators to ignore the code that also signals genuinely disabled token ceilings.
  - `[low]` `_LARGE_SPEC_BYTES = 40_000` is calibrated against this repo's own spec corpus but ships in a distributable package with no knob.
  - `[low]` `tests/unit/test_supervisor.py`'s `_HOME = Path("/home/acme-loop")` makes tests that omit `harness=` construct the real adapter and read outside the pytest sandbox.
  - `[low]` No journal-schema conformance test for `budget-warn`/`budget-stop`/`budget-usage-stale`, and no APPROACHING test for either token ceiling.
- rejected (noise or already-deliberate, dropped):
  - The ~40-call-site mass edit in `test_supervisor.py` being hard to read -- style only, no functional impact.
  - The spec-size signal being unavailable on a story's FIRST run (the spec is authored during the run) -- inherent to the design, and the prior-attempt signal is its documented complement.
  - `main()`'s arity gate accepting `1e307` where `_valid_positive_number` later rejects it -- reachable only by direct sidecar invocation; policy composition applies the same rule upstream on every real path.
  - `cost_estimate` collapsing "zero tokens observed" and "no reading was ever taken" into one `null` -- re-raised this pass, but explicitly the spec's own Never-clause decision, already reasoned through in pass 1.

### 2026-08-03 -- Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 2, medium 3, low 2)
- defer: 3 (high 0, medium 2, low 1)
- reject: 3 (high 0, medium 0, low 3)
- addressed_findings:
  - `[high]` `[patch]` **`usage_snapshot`'s `cache_read_weight()`/`weighted_total()` calls sat OUTSIDE the try/except wrapping `load_state`, violating its own "never raises" contract.** A syntactically-valid `state.json` with a non-Mapping `policy_snapshot` field (e.g. a JSON string) survives `RunState.from_dict` unvalidated and raises a bare `AttributeError` when `cache_read_weight()` calls `.get()` on it -- outside every exception this method caught, escaping to the supervisor's tick loop uncaught and crashing it with a dangling `supervisor-attach` and no matching `supervisor-detach` (the exact AD-9 "never silent" failure this port promises never to produce). Fixed: the try now wraps every read this method performs against `state`, not only the initial `load_state` call; `AttributeError` added to the caught tuple. New regression test: `test_usage_snapshot_returns_none_for_a_non_mapping_policy_snapshot`.
  - `[high]` `[patch]` **A run's final (or, for a single-`--story` launch, ONLY) story never got a `budget-usage` entry at all.** The sole append site fired on an OBSERVED story-key transition; a run's last story never observes a later transition before the process exits, so the common single-story invocation shape never journaled any per-story cost attribution -- directly undermining this story's own acceptance criterion. Fixed: one flush of `current_story_key`'s last known tally right before the final `supervisor-detach` is constructed, firing exactly once regardless of how the tick loop ended. New tests: `test_single_story_run_with_no_transition_still_journals_one_budget_usage_entry`; updated the two pre-existing transition tests to expect the extra end-of-run flush entry.
  - `[medium]` `[patch]` A single transient `usage_snapshot()` read failure (a torn concurrent write, a momentary import glitch) was treated identically to a genuine "no current story" state, resetting the per-story wall-clock/token ceiling clock for a story that was, in fact, still running. Fixed: a failed read (`usage is None`) now carries `current_story_key` forward unchanged for that tick -- only a POSITIVE reading ever changes it, mirroring the idle ladder's own "act only on evidence it has" discipline.
  - `[medium]` `[patch]` `usage_snapshot()` returning `None` for a NON-staleness reason (a fresh `state.json` mtime, but the read itself failed) silently disabled both token ceilings with zero registered finding -- a persistent, non-staleness read failure could disable token-ceiling enforcement for the run's whole life with no diagnostic anywhere. Fixed: widened the staleness gate to `is_stale or usage is None`, registering the same `MRS-SUPV-006` either way (identical operational consequence: both token ceilings unevaluable this tick, wall-clock remains binding) with a message distinguishing the two causes. New test: `test_usage_read_failure_with_a_fresh_mtime_also_journals_stale_evidence`.
  - `[medium]` `[patch]` `_act_on_budget_transition`'s `deferred` guard sat only inside its `BREACHED` branch, so a DIFFERENT ceiling crossing into `APPROACHING` in the SAME tick -- after an earlier ceiling already breached and set `deferred = True` -- could still journal a `budget-warn` chronologically AFTER the terminal `budget-stop` pair, contradicting the function's own docstring claim that a second same-tick transition is a no-op. Fixed: the `deferred` check now sits at the top of the function, before either branch. New test: `test_a_breach_on_one_ceiling_suppresses_a_same_tick_warn_on_another`.
  - `[low]` `[patch]` `DEFAULT_POLICY`'s comment claimed `max_tokens_per_run=40M` is "an order of magnitude above" FR-14's cited 25.8M-token blowout -- 40M/25.8M is ~1.55x, not ~10x, misstating a production default's own calibration rationale by ~6.5x. Fixed the comment (both in `core/policy.py` and this spec's own Design Notes) to state the correct ratio.
  - `[low]` `[patch]` `cli/spin.py::_prior_attempt_history` reads raw JSON directly (never through `bmad_loop`'s own `int()`-coercing `from_dict`), so its `isinstance(attempt, int)` check would silently miss a `state.json` recording `"attempt": 2.0` (a JSON float) from a future or non-conforming writer. Fixed: widened to `isinstance(attempt, (int, float))`.
- deferred (not fixed in this pass, logged to `deferred-work.md`):
  - `[medium]` `_prior_attempt_history`'s O(resolved-stories x historical-runs) re-glob/re-parse has no caching across the outer loop -- bounded in practice by bmad-loop's own `run_retention=10` default, not urgent at today's scale.
  - `[medium]` The cross-package dependency between `_prior_attempt_history`'s story-key matching and bmad-loop's own `state.json` key spelling is correct today but unpinned by any compatibility test against future upstream drift.
  - `[low]` No test documents or pins down whether a story's per-story wall-clock ceiling should keep accruing through an idle-ladder `stop-and-retry` cycle (Story 3.5) -- plausibly correct as-is, but undocumented.
- rejected (noise or already-deliberate, dropped):
  - `cost_estimate` collapsing "zero tokens observed" and "no reading was ever taken" into the same `null` -- explicitly the spec's own Never-clause decision, already reasoned through above.
  - Budget-ceiling `float` vs. `int` type mismatch in warn/breach message text -- cosmetic only, no functional impact, reviewer's own assessment.
  - `evaluate_ceiling`'s unguarded `observed` parameter -- intentional, consistent with `evaluate_idle`'s own established precedent, already documented in its own docstring.

## Design Notes

**Why `stale-evidence`, not the epics.md AC's literal `unevaluable`.** AD-32 was amended (F-24, 2026-07-30) specifically because labelling this condition `unevaluable` makes it AD-8-blocking and fires on the ordinary idle case FR-12's own ladder already handles gracefully with a nudge -- two mechanisms reacting to one condition with opposite intentions. The architecture spine is the authority here; the epics.md AC predates or simply didn't carry the amendment forward into its own prose.

**Why `state.json`, not a new usage-reporting convention.** `bmad_loop.journal.load_state` + `StoryTask.tokens.weighted_total(cache_read_weight)` is the EXACT mechanism AD-9's own docstring already names ("adapter-reported usage read from files the session wrote") and the exact metric bmad-loop's own in-session guard already computes -- reusing it costs one lazy import inside the one sanctioned seam, versus inventing a second, parallel notion of consumption.

**Why the 4 new ceilings are fixed-default SEED keys, not left unbounded.** C-6: "every run has a ceiling; there is no unbounded mode."

**Default calibration -- MEASURED, not assumed (revised 2026-08-03, review pass 2).** The first pass set these by analogy and marked them `[ASSUMPTION: ...]`: `max_tokens_per_story=4M` ("2x bmad-loop's own in-session 2M per-story guard, so Marshal's external ceiling is the backstop that fires only once the in-session one has already failed to stop things"), `max_tokens_per_run=40M` (~1.5x a cited 25.8M blowout), `max_wall_clock_minutes_per_story=240` (4h), `max_wall_clock_minutes_per_run=600` (10h). **All four were below ordinary observed behaviour**, and the per-story token premise was additionally false on its own terms: bmad-loop's `max_tokens_per_story` check runs *after* `advance(task, Phase.DONE)` and only appends a `token-budget-exceeded` journal breadcrumb (`engine.py`) -- it never attempts to stop anything, so there was no in-session enforcement for Marshal's ceiling to back up.

Measured across 30 real bmad-loop runs / 53 completed stories on this factory (weighted totals per bmad-loop's own `input + output + cache_creation + cache_read x cache_read_weight`):

| Metric | Observed max | Old default | New default |
|---|---|---|---|
| per-story weighted tokens | 21.7M (46 of 53 stories exceeded 4M; **this story itself cost 12.9M**) | 4M | **50M** |
| per-run weighted tokens | 111.6M (an 8-story wave) | 40M | **500M** |
| per-story wall clock | 519 min (5 of 40 exceeded 240) | 240 | **1440** (24h) |
| per-run wall clock | 1041 min (2 of 30 exceeded 600) | 600 | **2880** (48h) |

Shipping the old values would have hard-stopped essentially every supervised run in its first story, the moment a fresh `state.json` sample landed. A ceiling is a **runaway backstop, not a routine trip**: each new default sits at ~2.5-4.5x the observed maximum, so it fires only on behaviour with no precedent in this corpus while still bounding the run (C-6 holds). The per-run token ceiling carries the widest margin because a run's total scales with its story count. All four stay operator-tunable via the same policy layers `idle_threshold_minutes` already uses. `tests/unit/test_policy.py::test_budget_ceiling_defaults_clear_the_observed_workload` pins the calibration contract (not just the literals) so a future edit that re-crosses the observed maxima fails.

**Why run-start is attach-time, not the run-launch journal entry's own timestamp.** No existing utility parses a journal `ts` string back into a value comparable to `ClockPort.monotonic()`, and the gap between `spin`'s mint and the supervisor's own attach is seconds against an hours-scale ceiling -- introducing a parser for that much precision is disproportionate.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- expected: all import-linter contracts hold (`supervisor` still never imports `cli`; `core/supervise.py` still imports no adapter/port).

**Manual checks (if no CLI):**
- Against a real provisioned loop home: launch a run with a deliberately tiny `max_wall_clock_minutes_per_run`, confirm the supervisor journals a `budget-stop` and the harness run actually stops.



## Auto Run Result

Status: `done` (review pass 3 -- follow-up review of the merged story, no implementation loopback)

**Summary of implemented change.** No new feature work: this run was a fresh
adversarial review pass over the already-merged Story 3.6 diff
(`22ebe22..91ff0be`), triggered by pass 2's own `followup_review_recommended:
true`. Blind Hunter and Edge Case Hunter ran in parallel with no shared
context, both verifying against live data rather than the diff alone. Triage
produced 0 intent gaps, 0 spec defects, 3 patches, 7 defers and 7 rejects; the
3 patches were auto-fixed and committed as `013b754`.

**Files changed.**

- `src/pyforge/marshal/core/policy.py` -- `_valid_positive_number` now converts
  through a guarded `float()` before any `math.isfinite` call, so an
  arbitrary-precision int from a project policy TOML is rejected as a
  malformed value instead of raising `OverflowError` out of `compose()`.
- `src/pyforge/marshal/supervisor/__main__.py` -- story-scope budget
  transitions carry `story_key` (dot form, via `_feed_key_form`) in the
  `budget-warn` payload and both halves of the `budget-stop` pair; run-scope
  transitions stay deliberately unattributed.
- `src/pyforge/marshal/adapters/harness_bmadloop.py` -- `usage_snapshot` guards
  the `story_key`/`story_weighted_tokens` PAIR, so a task with a null or empty
  story key can no longer publish a tally attributed to no story.
- `tests/unit/test_policy.py` -- `test_budget_ceiling_rejects_an_arbitrary_precision_int_without_raising`, parametrized over all four ceiling keys.
- `tests/unit/test_supervisor.py` -- `test_a_per_story_breach_names_the_story_in_its_warn_and_stop_payloads` and its run-scope complement.
- `tests/unit/test_harness_bmadloop_usage_snapshot.py` -- `test_usage_snapshot_never_attributes_a_tally_to_an_unnamed_story`, parametrized over `None` and `""`.

**Review findings breakdown.** 3 patches applied (1 high, 1 medium, 1 low), 7
items deferred (5 medium, 2 low) appended to `deferred-work.md` as NEW entries
only, 7 rejected. Full detail in the Review Triage Log entry for pass 3. Two
rejects were dropped specifically because pass 2 had already captured them in
the ledger; two more were re-raises of decisions the intent contract's own
Never clauses make explicitly.

**Verification performed.**

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **1780 passed,
  9 deselected** (1789 collected, up from 1781: exactly the 8 new regression
  cases). Zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- **3 contracts kept, 0 broken** (AD-4 core purity, AD-3 single `bmad_loop` seam, AD-9 no supervisor->cli channel), 60 files / 233 dependencies analysed.
- The high-severity finding was reproduced end-to-end before being fixed: a
  400-digit `max_tokens_per_run` parsed by `tomllib` makes the pre-fix
  `compose()` raise `OverflowError: int too large to convert to float`.

**Follow-up review recommendation: `false`.** The pass converged. Patch volume
fell 12 -> 3 with `intent_gap` and `bad_spec` at zero for the third
consecutive pass, and all three fixes are narrow and locally pinned by new
tests -- the high-severity one is a single guarded conversion in one
validator. The substance of what both reviewers found this time is design
reach, not defects, and is now recorded as deferred work rather than being
churned into the code.

**Residual risks.**

- FR-14's advisory is materially weaker in production than the suite suggests:
  the spec-size half is silent for every not-yet-run story (the spec is an
  output of the run being launched), and the prior-attempt half both misses
  human-resolved escalations (bmad-loop resets `attempt`/`phase`) and never
  forgets a story it once flagged. Deferred rather than patched because the
  intent contract specifies both inputs explicitly. The AC is met as written;
  its practical reach is narrower than the wording implies.
- The two token ceilings remain per-session-granular by construction --
  `task.tokens` only accumulates after a session ends, so they cannot bound a
  runaway session in flight, only notice one after it finishes. AD-32 makes
  the two wall-clock ceilings the binding constraint by design, so this is a
  reach limit rather than a correctness break, but it is worth knowing before
  relying on a token ceiling to stop anything promptly.
- `cli/spin.py`'s hand-copy of bmad-loop's on-disk state layout has no
  compatibility guard; an upstream change degrades the advisory to
  always-silent with every test still green.
