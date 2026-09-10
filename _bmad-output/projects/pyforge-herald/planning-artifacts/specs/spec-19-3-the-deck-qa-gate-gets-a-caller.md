---
title: 'The deck-QA gate gets a caller'
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `herald deck qa <slug>` works — it is fully wired (`cli.py:331-341` / `:764-765` /
`:982-995`, `deck_qa.py`, 665 lines, all of Epic 14's stories 14.1/14.2/14.3 `done`) — but nothing
calls it. `pixi.toml` names `deck_qa` only inside a playwright dependency comment, no CI job
invokes it, and `docs/specs/presentation-deck.md`'s verify checklist is still entirely
run-shaped (manual steps, not an automated one). This is exactly the "capability shipped but
never exercised" gap Epic 19 exists to close.

**Approach:** Add a pixi task that invokes the existing gate, name that task as a step in
`presentation-deck.md`'s verify checklist, and run it against one existing deck
(`presentations/agentic-sdlc/`) so its report lands under `.herald/deck-qa/<slug>/`. The gate's
own code (`deck_qa.py`) is unchanged — this story gives the gate a caller, it does not add a
gate. The story also records, explicitly, whether the gate's verdict is advisory or blocking —
a deliberate choice, never accidental, and never a second PR gate.

## Boundaries & Constraints

**Always:**
- `deck_qa.py` stays unchanged — this story adds no gate.
- The gate is run against `presentations/agentic-sdlc/`, producing a report under
  `.herald/deck-qa/<slug>/`.
- `presentation-deck.md`'s verify checklist names the new pixi task as a step.
- The verdict's advisory-vs-blocking status is an explicit, recorded choice.

**Never:**
- Never a second PR gate — the deck-QA gate's verdict does not compete with or duplicate the
  existing PR quality-gate verdict.
- Never blocking by accident — if blocking is chosen, it must be stated, not incidental.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Baseline (today) | `pixi.toml` names `deck_qa` only in a playwright dependency comment; no CI job | the gap this story closes | — |
| pixi task invoked | new pixi task run against `presentations/agentic-sdlc/` | one report produced under `.herald/deck-qa/agentic-sdlc/`; the gate has at least one caller outside its own test file | — |
| Verify checklist consulted | operator reads `docs/specs/presentation-deck.md` § verify checklist | the deck-qa task is named as an explicit step | — |
| Verdict mode recorded | story records advisory vs blocking | explicit choice stated in the story, never accidental | never registers as a second PR gate |

</intent-contract>

## Code Map

- `pixi.toml` — add a `deck-qa` task (`local-recipes` or `pyforge-herald` feature)
- `docs/specs/presentation-deck.md` § verify checklist — name the new task as a step
- `.github/workflows/` — optionally, a deck lane
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_qa.py` — unchanged (read-only
  reference)
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py:331-341` / `:764-765` /
  `:982-995` — existing `herald deck qa <slug>` wiring (read-only reference)
- `presentations/agentic-sdlc/` — verification target
- `.herald/deck-qa/<slug>/` — report output location

## Tasks & Acceptance

**Execution:**
- feature: add a `deck-qa` pixi task that invokes `herald deck qa <slug>`
- docs: name the new task as a step in `presentation-deck.md`'s verify checklist
- feature: run the gate against `presentations/agentic-sdlc/`, producing a report under
  `.herald/deck-qa/agentic-sdlc/`
- decision: record, explicitly, whether the gate's verdict is advisory or blocking

**Acceptance Criteria:**
- Given `herald deck qa <slug>` works (`cli.py:331-341` / `:764-765` / `:982-995`; `deck_qa.py`,
  665 lines) and nothing calls it — no pixi task (`pixi.toml` names `deck_qa` only in a
  playwright dependency comment), no CI job, and `docs/specs/presentation-deck.md`'s verify
  checklist is still entirely run-shaped, which is the exact gap the Spec was written to close —
  when a pixi task invokes the gate and `presentation-deck.md`'s verify checklist names it as a
  step, then one existing deck (`presentations/agentic-sdlc/`) is run through the gate, its
  report is produced under `.herald/deck-qa/<slug>/`, and the gate has at least one caller
  outside its own test file.
- And the gate's verdict is advisory or blocking by explicit choice recorded in the story — never
  blocking by accident, and never a second PR gate.

## Spec Change Log

## Review Triage Log
