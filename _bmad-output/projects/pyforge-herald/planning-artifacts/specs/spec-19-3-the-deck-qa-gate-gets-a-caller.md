---
title: 'The deck-QA gate gets a caller'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: b2f99e866acf5ea45b4a90a8edd57b1fb1d03dbd
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
verdict_mode: advisory
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

- 2026-09-10 — Story 19.3 implementation: added `[feature.pyforge-herald.tasks.deck-qa]`
  (`herald deck qa`), deck-QA step 5 in `docs/specs/presentation-deck.md`, and recorded
  `verdict_mode: advisory` (explicit non-blocking choice; never a second PR gate).

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 24 findings — high 0, medium 2, low 3, false 8, maybe-false 0
- findings:
  - `[medium]` `[patch]` Pixi `deck-qa` task unwired from herald meta verification — added `tests/meta/test_deck_qa_pixi_task.py` asserting task registration and `cmd`.
  - `[medium]` `[patch]` Step 5 omitted `npm run build` / repo-root prerequisites — clarified in `presentation-deck.md` step 5.
  - `[low]` `[reject]` Acceptance criteria section lacks deck-QA checkbox — procedure step 5 is the verify checklist surface named in the spec; AC bullets remain run-shaped by design.
  - `[low]` `[reject]` `spec_updated` frontmatter stale in `presentation-deck.md` — legacy Tier-1 workflow doc; not required for this story.
  - `[low]` `[reject]` Empty Spec Change Log at review time — filled in this pass.
  - `[false]` `[reject]` No agentic-sdlc run or `.herald/deck-qa/agentic-sdlc/` report — run during implementation (`pixi run -e pyforge-herald deck-qa agentic-sdlc` exit 0; 51 PNGs under `.herald/deck-qa/agentic-sdlc/render/`); path is gitignored per `/.herald/`.
  - `[false]` `[reject]` Verdict mode recorded only in frontmatter — also stated in pixi task description and presentation-deck step 5 prose.
  - `[false]` `[reject]` I/O matrix "verify checklist" vs "How to use" mismatch — numbered procedure step 5 is the operator verify checklist in this doc.
  - `[false]` `[reject]` Missing slug guard on pixi task — `herald deck qa` argparse rejects missing slug with exit 2.
  - `[false]` `[reject]` Cwd-not-root breaks deck resolution when following docs — step 5 now requires repo root; pixi task description matches.
  - `[false]` `[reject]` Intent divergence on mandatory exercise — acceptance run completed locally; artifacts gitignored, not committable.
  - `[false]` `[reject]` "At least one caller" unsatisfied — `[feature.pyforge-herald.tasks.deck-qa]` in tracked `pixi.toml` plus meta test.
  - `[false]` `[reject]` Partial verify-checklist transformation — intent required naming the task as a step, not converting every manual step.
  - `[defer]` `[defer]` `sprint-status-ledger.yaml` still `backlog` — ledger sync is a separate steward workflow (`sprint-ledger-sync`), not this story's code surface.
  - `[defer]` `[defer]` pyforge-herald SKILL.md Quick Start omits `deck-qa` — agent skill refresh out of scope; CLI unchanged.
  - `[defer]` `[defer]` `docs/dreams/deck-visual-qa.md` still "BUILT, NOT IN EFFECT" — Dream status reconciliation is a follow-on steward/doc pass.
  - `[defer]` `[defer]` Worked Example 1 not amended with deck-QA run record — story execution task satisfied by local run; worked-example append is optional per presentation-deck §7.
  - `[defer]` `[defer]` Parent `spec-deck-visual-qa` memlog stale — parent spec memlog update not in story 19.3 scope.
  - `[defer]` `[defer]` `environment.yaml` not regenerated — pixi task addition only; no dependency change; regenerate if CI sync check flags it on PR.

## Auto Run Result

Status: done

**Summary:** Added `deck-qa` pixi task under `pyforge-herald`, documented it as advisory step 5 in `presentation-deck.md`, and exercised the gate against `presentations/agentic-sdlc/` (51 render PNGs + contact sheet under `.herald/deck-qa/agentic-sdlc/render/`). `deck_qa.py` unchanged.

**Verdict mode:** **advisory** — recorded in spec frontmatter (`verdict_mode: advisory`), pixi task description, and checklist prose. Deliberately not a PR gate or CI blocker.

**Files changed:**
- `pixi.toml` — `[feature.pyforge-herald.tasks.deck-qa]` invokes `herald deck qa`
- `docs/specs/presentation-deck.md` — new advisory verify step 5 (repo root + built `dist/` prerequisite)
- `src/shared/packages/pyforge-herald/tests/meta/test_deck_qa_pixi_task.py` — meta test guards task registration
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-19-3-the-deck-qa-gate-gets-a-caller.md` — status, verdict, review log

**Review:** 2 medium patches applied (meta test, doc prerequisites); 5 rejected; 6 deferred.

**Follow-up review recommended:** false (0 high patches; 2 medium patches only).

**Verification:**
- `pixi run -e pyforge-herald deck-qa agentic-sdlc` — exit 0; JSON report with `render` ok and `image-slot` finding on slide 47-in-action (expected true positive)
- `.herald/deck-qa/agentic-sdlc/render/` — 51 files including `contact-sheet.png`
- `pixi run -e pyforge-herald pyforge-herald-test` — 1255 passed, 4 skipped
