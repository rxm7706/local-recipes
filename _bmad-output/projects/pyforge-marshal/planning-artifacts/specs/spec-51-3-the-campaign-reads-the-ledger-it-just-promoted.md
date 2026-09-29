---
title: '51.3: The campaign reads the ledger it just promoted'
type: 'fix'
created: '2026-09-19'
status: 'done'
baseline_revision: '9b3c5afec8f41cb92de21433825aad50efbe6826'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every herald 23.x landing on 2026-09-18 promoted the ledger onto `origin/main` and the campaign kept reading the primary checkout's stale copy until an operator pulled

**Approach:** finalize fast-forwards the primary only when it is a clean `main` (refusing by name and journaling otherwise — the checkout may belong to another session) and the campaign otherwise reads the promoted ledger from `origin/main`

## Boundaries & Constraints

**Always:**
- a fixture replaying the herald sequence (ledger promoted remotely, primary one commit behind) reports the story `done` on the next cycle and chains the next ready story with zero operator commands
- a dirty or non-`main` primary is never moved (fixture), `_promote_sprint_ledger` gains no second writer, and a primary already at `origin/main` is byte-identical

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-251`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` (post-ledger refresh step, reusing `cli/land.py::_resync_home_branch`), `.../cli/land.py::_promote_sprint_ledger` (unchanged single writer onto the remote tip), `.../cli/dispatch.py` (the fleet cycle's ledger read — `station_finalize_pending_story` / the `ledger_story_statuses(ledger_path)` call — falls back to `origin/main` when the primary is not a clean `main`), `.../core/dispatch_fleet.py::station_ledger_path`, tests.
Ledger key: `51-3-the-campaign-reads-the-ledger-it-just-promoted`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-3-the-campaign-reads-the-ledger-it-just-promoted.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.3 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.

## Auto Run Result

Status: hollow — landed with NO implementation; re-minted as Story 51.9
Blocking condition: the dispatched session (`pyforge-marshal-20260919T093114631Z-aabf0253`, lr-m50, claude/sonnet) was terminated by Claude Code's print-mode ceiling — `Background tasks still running after 600s; terminating. Set CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 to wait indefinitely.` — while its implementation subagent was still running. The branch's only commit (`67e56ce1f3 wip: 51.3 (auto-checkpoint)`) is this file's `ready → in-progress` flip plus `baseline_revision`. `has_git_progress` (`core/dispatch_completion.py`) counted that flip as progress, the supervisor finalized on harness-done, `dispatch verify` was green by construction on an unchanged tree, `dispatch land` merged PR #1501 (`e7a71df640 Merge pyforge-marshal/51-3 into main`) and finalize promoted `51-3 … : done` (`31364a5d8b`). Nothing under CAP-251's Surface changed: `dispatch_land_finalize/__main__.py`, `cli/land.py`, `cli/dispatch.py`, `core/dispatch_fleet.py` are byte-identical to `origin/main` before the story. Every Then/And of Story 51.3 is unmet.

**Record:** the ledger row stays `done` (a `done` key never moves — `ledger-regression`); this frontmatter is set to `done` so the records agree, and this section carries the truth (the doctor 27.3 / PR #1476 precedent). The story is re-minted as **51.9** with the identical contract; Story 51.4's dependency moves from 51.3 to 51.9; CAP-252's success is widened so a hollow outcome (no changed path outside the story's own spec) never lands either.

**Review findings breakdown:** no review ran (the session died before step 04). A post-hoc pass over the landed diff (Blind Hunter, Edge Case Hunter, Verification Gap; 2026-09-19) confirmed the branch's own diff is one file, +2/−1, and that `story-status`, `status-body-consistency` and `sources/ledger.py` cannot see a hollow landing because the merge subject exists — seeded on `docs/dreams/pyforge-doctor.md` and `docs/dreams/pyforge-marshal.md` 2026-09-19.
