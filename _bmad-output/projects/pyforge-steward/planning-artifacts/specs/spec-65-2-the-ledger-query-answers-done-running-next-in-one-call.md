---
title: '65.2: The ledger query answers done / running / next in one call'
type: 'feature'
created: '2026-09-20'
status: 'in-progress'
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
