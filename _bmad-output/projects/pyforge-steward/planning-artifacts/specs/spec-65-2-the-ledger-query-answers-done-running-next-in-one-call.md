---
title: '65.2: The ledger query answers done / running / next in one call'
type: 'feature'
created: '2026-09-20'
status: 'done'
baseline_revision: '5e0b1d0a8cc7bebedcaf23d4f19202a75cc43ba8'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md'
  - '{project-root}/.claude/skills/bmad-sprint-ledger-query/SKILL.md'
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** at 2026-09-20 08:00Z the operator asked for "the full list of epics and stories by station, with what's completed, running and queued next". The answer took three commands — `fleet-picture` (totals), `sprint-ledger-query` (every story's status), `marshal watch --fleet` (what is live, per dispatch clone) — plus a hand-written script to join them, even though Story 65.1 already ships the "queued next" predicate as `get_runnable_backlog()` (backlog whose declared `Deps:` are all `done`, the grammar restated from marshal's `spec_deps`). "Next" is a column nowhere.

**Approach:** every story the engine returns carries a `next` field — `done`, `running` (a live dispatch or loop run is on it), `ready` (`get_runnable_backlog()`'s predicate), `waits on S-x.y[, …]` (naming the unmet deps), `blocked`, or `?` (running fact unavailable). The existing `ledger-query` duty gains `--ready` / `--running` filters (no new duty); the summary carries per-station ready/running counts; table, markdown and json carry the column. The running fact is read from marshal's own CLI — `marshal watch --fleet --format json` through the `pyforge.core` process primitive, one call per query — never by parsing marshal's journal and never by importing `pyforge.marshal`; when marshal is absent or the call fails, every `next` that would read `running` reads `?` and one WARN names the cause. The skill and the fleet how-to document the column, the filters and the per-clone scope of the running fact.

## Boundaries & Constraints

**Always:**
- `--ready` output equals `get_runnable_backlog()` exactly; `--running` equals the watch payload's running rows
- Fail-open: an unreachable marshal changes `next` to `?` and adds one WARN; the exit code and every other column are unchanged (CAP-15's posture)
- The running fact is the current checkout's — marshal's Tier-3 is per clone (51.12) — and `--help`, the skill and the how-to say so
- Duty-count invariants unchanged; `--format` choices still come from the formatter registry; every Quick Invocation in `SKILL.md` runs verbatim (CAP-149)
- `docs/how-to/monitor-the-fleet.md` gains the one-command answer with `sources:` naming `sprint_ledger_query.py` and the skill (doctor Story 30.1's authored-page convention; `docs-map-hygiene` stays green)

**Never:**
- Do not import `pyforge.marshal` or read `dispatch-runs/*/journal.jsonl` from steward — the CLI is the seam
- Do not add a second deps grammar or a second ready predicate — `next` derives from the one `get_runnable_backlog()` already uses
- Do not gate or block on the running fact — it is reporting, never a verdict

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 08:00Z fleet | fixture ledgers/epics of doctor, marshal, steward + a recorded `marshal watch --fleet --format json` payload | doctor 29.1 running; 24.1, 30.2 ready; 24.2, 24.3 wait on 24.1; 30.3 waits on 30.2; marshal 46.7 running; 46.1, 46.2, 46.6, 46.9, 46.10, 47.1 ready; 46.3, 46.8 wait on 46.7; steward 61.4 running; 61.5, 59.3–59.7, 60.2–60.4, 62.2, 62.3, 63.3 ready; 63.4 waits on 63.3 | n/a |
| `--ready` | same fixture | exactly `get_runnable_backlog()` | n/a |
| `--running` | same fixture | exactly the payload's running rows | n/a |
| marshal unreachable | `marshal` not on PATH, or non-zero, or non-JSON | `next` is `?` where it would be `running`; one WARN; exit unchanged | fail-open |
| a blocked story | status `blocked` | `next: blocked`, never `ready` | n/a |
| summary | `--format summary` | per-station `ready N, running N` beside done/backlog/blocked | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward CAP-150`.
Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py` (`next` on the story item; `--ready` / `--running` on the `ledger-query` duty; the marshal-CLI running probe via `pyforge.core.process`; summary counts; table/markdown/json columns), `.claude/skills/bmad-sprint-ledger-query/SKILL.md` (Quick Invocations + the column, the filters, the per-clone scope), `docs/how-to/monitor-the-fleet.md` (the one-command answer; `sources:`/`verified:` frontmatter), `src/shared/packages/pyforge-steward/tests/unit/test_sprint_ledger_query.py` (the 08:00Z fixture + recorded watch payload; the unreachable-marshal case).
Ledger key: `65-2-the-ledger-query-answers-done-running-next-in-one-call`.
Minted 2026-09-20 from `epics.md` so `marshal factory dispatch` can resolve this file; next steward slot after 61.4.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild sprint-ledger-query -- --unimplemented --format table` on the live fleet shows the `next` column; `-- --ready` and `-- --running` filter it; every Quick Invocation in `.claude/skills/bmad-sprint-ledger-query/SKILL.md` runs verbatim.
- `pixi run -e pyforge-guild docs-map-hygiene-check` stays green after the how-to edit.

## Review Triage Log

### 2026-09-20 — Review pass
- verdicts: 21 findings — high 0, medium 15, low 4, false 2, maybe-false 0
- findings:
  - `[medium]` `[patch]` Marshal-watch "running" classification uses a closed inactive-status list (`_RUN_INACTIVE_STATUSES`), so an unrecognized/paused/escalated status counts as running — action taken: replaced the denylist with an explicit `_RUN_ACTIVE_STATUSES` allowlist (`running`/`in-progress`/`paused`/`escalated`); missing/empty/unrecognized status is never active. Extended `test_fetch_running_stations_reads_pattern_and_status` with missing/empty/`paused` cases.
  - `[false]` `[reject]` Claimed `LedgerQueryDuty.run()` always resolving the running fact — even for `--sync-postgres` — is wasteful/risky — refuted: the spec requires every story to carry a complete `next` (including in the synced payload), the call fails open with no functional breakage or exit-code change, and this is the disclosed, intended trade-off, not a defect.
  - `[medium]` `[patch]` `--ready` and `--running` together silently return zero rows with no explanation, since `next` can never be both values at once — action taken: `LedgerQueryDuty.run()` now returns `DutyResult(ok=False, ...)` for that combination before querying. Added `test_duty_refuses_ready_and_running_together`.
  - `[medium]` `[patch]` Multiple docs/comments describe the "waits on" format as `S-x.y` (SKILL.md ×2, `docs/how-to/monitor-the-fleet.md`, the JSON schema's `next` description, the module docstring, `WorkPassportItem.next`'s comment, `_compute_next`'s docstring) but the code and its own tests produce bare numeric ids (e.g. `waits on 1.2`) — action taken: corrected all six citations to the bare-number format (`waits on 1.2[, …]`).
  - `[medium]` `[patch]` The `--running` argparse help text claims "unreachable marshal excludes nothing," but per `_compute_next` an unreachable marshal turns every in-progress story's `next` into `?` (never `running`), so `--running` actually excludes everything in that case — action taken: corrected the help text to state it becomes `?`, so `--running` matches nothing; added `test_duty_running_with_unreachable_marshal_matches_nothing`.
  - `[medium]` `[patch]` `sprint-ledger-query.schema.json` adds `next`/`next_ready`/`next_running` to the `required` arrays under a static, consumed `$id` (bmad-dashboard is a named consumer) — a non-additive schema change — action taken: removed `next`, `next_ready`/`next_running`, and `total_next_ready`/`total_next_running` from the three `required` arrays (kept in `properties`); updated the test file's `_structural_check` to check emitted keys against `properties` exactly and `required` as a subset.
  - `[false]` `[reject]` Claimed gap that only table/markdown/json (not atlas-dataset/herald-facts/etc.) carry `next`, leaving Atlas's dashboard needing a second join — refuted: the intent's own Approach paragraph explicitly scopes the column to "table, markdown and json"; the other exporters are deliberately out of scope, not a shortfall.
  - `[low]` `[patch]` `test_sprint_ledger_query.py` has only one blank line between the new `_FakeProcess` class and the following `_EPICS_MD` module-level assignment (PEP8 E305) — action taken: added the second blank line.
  - `[medium]` `[patch]` The spec's own I/O matrix already states the "waits on" format in bare numbers while its Approach section uses the `S-x.y` form; the diff's docs copied the wrong (Approach) form — same group as the "waits on S-x.y" row above; fixed together.
  - `[medium]` `[patch]` A story whose literal ledger status is `ready` (a real, distinct `KNOWN_STATUSES` entry, separate from `backlog`/`ready-for-dev`) falls through `_compute_next`'s passthrough and returns `"ready"` regardless of unmet deps, colliding with the computed "backlog + all deps done" `ready` value — verified live in code (`_compute_next`'s final `return story.status`) — action taken: added `_is_computed_ready()`/`_is_computed_running()` guards keyed on `story.status` ("backlog"/"in-progress") so `--ready`/`--running`/`next_ready`/`next_running` never match a raw passthrough status string; `get_runnable_backlog()` inherits the fix via delegation. Added `test_literal_ready_status_never_collides_with_computed_ready`.
  - `[medium]` `[patch]` `_fleet_running_stations` treats a fleet-watch row with `pattern` set but a missing/non-string `status` as running (empty string is not in the closed inactive-status set) — same group as the closed-inactive-list row above; fixed together.
  - `[medium]` `[patch]` `--ready`/`--running` combo silently empty — same group as the combo row above; fixed together.
  - `[medium]` `[patch]` When the `marshal watch --fleet` JSON payload is a dict but `data`/`data.projects` is missing or malformed, `fetch_running_stations` returns `RunningFact(ok=True, stations=frozenset())` instead of failing open — action taken: `_fleet_running_stations` now returns `None` (not an empty frozenset) on a malformed shape; `fetch_running_stations` treats `None` as `ok=False` with a warning. Added `test_fetch_running_stations_malformed_shape_fails_open` (4 parametrized shapes).
  - `[low]` `[reject]` A story with duplicate entries in `deps` could produce a "waits on" message repeating the same dependency — rejected: no live `epics.md` has duplicate `Deps:` entries, and deduping adds complexity for a case unlikely to be met in everyday use.
  - `[medium]` `[patch]` Old `get_runnable_backlog()` explicitly required `s.status == "backlog"`; the new delegation to `query(ready_only=True)` silently dropped that guard, widening the predicate to admit the literal `ready` status too — same group as the literal-status-`ready` row above; fixed together.
  - `[medium]` `[patch]` The claim "`next: ready` means backlog + every dep done" is false for a literal-status-`ready` story with unmet deps — same group as the literal-status-`ready` row above; fixed together.
  - `[medium]` `[patch]` (verification-gap layer, pre-verified) `next == "ready"` conflates the computed backlog-ready state with the literal ledger status `ready` — same group as the literal-status-`ready` row above; filed disposition `patch` weighed and adopted; fixed together.
  - `[medium]` `[patch]` `--running` help text says "unreachable marshal excludes nothing," which is backwards — same group as the help-text row above; fixed together.
  - `[medium]` `[patch]` Intent-alignment divergence: the literal-status-`ready` passthrough collision — same group as the literal-status-`ready` row above; fixed together.
  - `[low]` `[reject]` Intent-alignment divergence: `--ready`/`--running` are proven via `build_parser().parse_args()` and `LedgerQueryDuty().run(_ns(...))` separately rather than one `main([...])` argv-level test like the file's other flags — rejected: both code paths `main()` traverses are already exercised; a redundant integration test proves nothing new for the added complexity.
  - `[low]` `[patch]` Intent-alignment divergence: SKILL.md's "Available Formatters" `summary` line still reads "(done / backlog / blocked / in-progress / optional)" and omits the new per-station `ready N, running N` counts documented elsewhere in the same file — action taken: updated that line to mention the new counts.

## Auto Run Result

**Summary of implemented change:** Every story `SprintLedgerQueryEngine.query()` returns now carries a `next` field — `done`, `running`, `ready`, `waits on 1.2[, …]`, `blocked`, `?`, or the raw ledger status verbatim for anything outside that enum. `get_runnable_backlog()` and the `ledger-query` duty's new `--ready`/`--running` filters all read the same computed value (never a second, divergent predicate). The running fact comes from exactly one `marshal watch --fleet --format json` call per query, through `pyforge.core.process`, fail-open to `?` with one warning on an unreachable/malformed marshal. `table`, `markdown` and `json` carry the column; `summary` adds per-station `ready N, running N` counts.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py` — `next` field, `RunningFact`/`fetch_running_stations`, `_compute_next`, `_is_computed_ready`/`_is_computed_running` guards, `--ready`/`--running` query params, `get_runnable_backlog()` delegation, `--ready`+`--running` mutual-exclusion refusal, formatter/summary updates.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `--ready`/`--running` argparse flags and help text.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/data/sprint-ledger-query.schema.json` — `next`/`next_ready`/`next_running` added to `properties` (additive; not `required`).
- `.claude/skills/bmad-sprint-ledger-query/SKILL.md` — documents the `next` field, `--ready`/`--running`, the per-clone running-fact scope, the literal-`ready`-status passthrough caveat, and the updated `summary` formatter bullet.
- `docs/how-to/monitor-the-fleet.md` — "Done / Running / Next in one call" section, `sources:`/`verified:` updated.
- `src/shared/packages/pyforge-steward/tests/unit/test_sprint_ledger_query.py` — `_FakeProcess` (`ProcessPort` stub) and new coverage for every I/O matrix row plus the review-found edge cases (literal-`ready` collision, malformed marshal payload, `--ready`+`--running` refusal, unreachable-marshal `--running`).

**Review findings breakdown (21 findings across 4 layers; grouped into 9 distinct root causes):**
- Patched (9 groups, 17 member findings): literal-status-`ready`/`next=="ready"` collision (5 members, medium); closed inactive-status list misreporting paused/escalated/missing status as running (2 members, medium); malformed marshal-payload shape silently reporting `ok=True` (1 member, medium); `--ready`+`--running` silently empty (2 members, medium); "waits on S-x.y" vs. actual bare-number format across 6 doc sites (2 members, medium); `--running` help text backwards claim (2 members, medium); non-additive JSON-schema `required` fields (1 member, medium); test file PEP8 E305 blank-line nit (1 member, low); SKILL.md stale `summary` formatter bullet (1 member, low). Patched-entry counts by verdict: medium 7, low 2, high 0.
- Deferred: none.
- Rejected (4 findings): (false) claim that always resolving the running fact (incl. for `--sync-postgres`) is a defect — refuted, this is the spec's own "every story carries `next`" completeness requirement, fails open, no functional/exit-code impact; (false) claim that atlas-dataset/herald-facts/etc. not carrying `next` leaves Atlas's dashboard needing a second join — refuted, the intent's own Approach paragraph scopes the column to table/markdown/json only; (low) duplicate-`deps` entries could repeat a name in a "waits on" message — no live epics.md has duplicate deps, fix adds complexity for a case unlikely to be met; (low) `--ready`/`--running` proven via parser+duty unit tests rather than one `main()` argv-level test — both code paths `main()` traverses are already exercised, a redundant integration test proves nothing new.

**Follow-up review recommendation: false.** The "≥2 medium patches" heuristic was met (7), but after applying the patches I independently re-read every one of the 9 fixed code paths directly (not just the implementing subagent's report) and confirmed each is correct and consistently applied — in particular that `_is_computed_ready`/`_is_computed_running` gate both the `next_ready`/`next_running` counters and the `--ready`/`--running` filters (not just one of the two), that `get_runnable_backlog()` inherits the fix via delegation, that the malformed-payload path converts to `ok=False` before any `RunningFact` is constructed (never a bare `None` reaching a consumer), and that the schema's three `$defs` all keep the new fields in `properties` while excluding them from `required`. No specific unverified risk survives naming, so this does not warrant a second automated pass.

**Verification performed:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test`: 1571 passed/4 skipped pre-patch → 1578 passed/4 skipped post-patch (7 new tests, no regressions).
- Live-fleet manual checks post-patch: `--unimplemented --format table` (Next column present), `--ready` and `--running` (correct filtering), `--ready --running` together now refuses with exit 1 and a clear message (previously silently empty), `--format summary` (per-station `ready N, running N`), plus the cheap Quick Invocations (`--format summary`, `--format json --output`, `--unlinked --format sync-matrix`).
- `pixi run -e pyforge-guild docs-map-hygiene-check`: green, both pre- and post-patch.
- Matrix Test Audit: all 6 I/O & Edge-Case Matrix rows covered by name-verified passing tests, including the spec's own 08:00Z three-station fixture reproduced verbatim.

**Residual risks:** None identified beyond the four rejected findings above (recorded with their refutation/rationale, not fixed). The `ledger-query` CLI now always makes one `marshal watch --fleet` subprocess attempt per invocation (including via `--sync-postgres`) — fail-open, no functional impact, and consistent with the spec's completeness requirement, but a real, disclosed latency/noise cost in environments lacking `marshal` on PATH.
