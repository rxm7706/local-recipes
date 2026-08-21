---
id: SPEC-dashboard-velocity-captures-hand-driven-work
spec: dashboard-velocity-captures-hand-driven-work
status: draft
owner-dream: docs/dreams/dashboard-velocity-captures-hand-driven-work.md
surface:
  - docs/dashboard/generate.py
  - docs/dashboard/index.html
  - docs/dashboard/data.js
companions:
  - signal-inventory.md
sources:
  - ../../../../../../docs/dreams/dashboard-velocity-captures-hand-driven-work.md
open_questions:
  - "Wall-clock bound choice: ts(final_revision) - ts(baseline_revision) overstates (the baseline commit predates dispatch by the idle gap); first-commit-in-baseline..final-range -> final understates (excludes pre-first-commit work). Story-level design; whichever bound is chosen, the caption must state what is measured."
  - "Render surface for the wall-clock class: the timing strip only, or also a visually distinct bar class on the velocity graph? CAP-2's distinction requirement holds either way."
  - "Partial journal coverage (a story escalated in-loop, finished by hand): the journal floor wins the velocity axis per the precedence constraint — is the hand-finished remainder ever surfaced, or accepted as under-measurement? (Proposed: accepted; the existing 'closed sessions only — a floor, not a total' caption already covers it.)"
  - "Should bmad-dev-auto's HALT protocol additionally stamp a first-party duration (the Dream's capture point (a))? It only helps future stories, the skill lives in the regenerated BMAD install layer (override survivability requires bmad-customize), and it is probably superseded by the single-story-dispatch verb journaling sessions at source — see Assumptions."
---

> **Canonical contract.** This SPEC and `signal-inventory.md` are the complete,
> preservation-validated contract for the work. The Dream in frontmatter is its origin; the
> code facts below were verified against `docs/dashboard/generate.py`,
> `.claude/skills/bmad-dev-auto/step-03-implement.md`/`step-04-review.md`, and
> `pyforge.marshal.cli.deploy` on 2026-08-21.

# Every done story leaves a timing mark — "unmeasured" stops meaning "not loop-driven"

## Why

A pain to solve. The console's velocity chart (`docs/dashboard/generate.py::scan_timing`,
~L2730) derives "active agent-compute per story" exclusively from bmad-loop run journals —
`session-start`/`session-end` pairs (matched by `task_id`) in
`~/.bmad-loops/<slug>/.bmad-loop/runs/*/journal.jsonl`. A story completed by any other route —
a hand-orchestrated `bmad-dev-auto` sequence (doctor's Epic 8, 2026-08-15; the 22-story
dispatch session, 2026-08-21), a `bmad-quick-dev` session — leaves no journal, so it lands in
the same absent bucket as stories that predate loop instrumentation entirely, and the chart's
own caption ("the rest predate loop instrumentation") is now false for part of that bucket. A
hand-driven story finished today has real timing signal available (see `signal-inventory.md`)
and shows nothing. Confirmed live 2026-08-15: doctor 8.1–8.4, real reviewed and PR-landed
work, zero velocity bars. The storage half already exists — `scan_timing` preserves curated
`timing`/`velocity` per field and marks its own output `derived: true` — what is missing is
the derivation that fills the gap for hand-driven stories from the signal they actually leave.

## Capabilities

- **CAP-1 — wall-clock fallback derivation.**
  - **intent:** The dashboard generator derives a wall-clock duration for every `done` story
    that has a tracked/promoted story spec carrying resolvable `baseline_revision` and
    `final_revision` frontmatter (written by `bmad-dev-auto` steps 03/04, preserved verbatim
    by spec promotion) and zero closed bmad-loop journal sessions — offline, from local git
    commit timestamps only.
  - **success:** After a local generate, doctor's 8.1–8.4 carry timing marks derived from
    their promoted specs' revision fields; a re-run refreshes (never permanently freezes)
    the derived values, matching the existing `derived: true` discipline.
- **CAP-2 — fidelity is visible, never blended.**
  - **intent:** A wall-clock-derived mark is visually and textually distinguished from
    journal-derived active agent-compute wherever both render — wall-clock measures a
    different thing (includes waits; excludes nothing), and `scan_timing`'s own comments
    already forbid sharing the active-compute axis undistinguished (the atlas precedent).
  - **success:** On a line mixing both classes, a reader can tell each story's metric class
    from the rendered chart/caption alone; no wall-clock number appears as if it were
    active-compute.
- **CAP-3 — the coverage caption partitions by true reason.**
  - **intent:** The coverage statement stops lumping every unmeasured story under "predates
    loop instrumentation" and instead states the real classes: journal-measured,
    wall-clock-derived, spec-without-revision-fields, and no-spec-at-all (the only class
    that stays absent).
  - **success:** For a line containing hand-driven stories, the rendered caption names each
    absence class accurately; no caption claims "predates instrumentation" for a story whose
    spec carries revision fields.

## Constraints

- **Never fabricate.** A story with no resolvable signal — no spec, spec without revision
  fields, `NO_VCS` sentinel, or revisions that do not resolve in local history — stays
  absent. The existing "deliberately absent rather than plotted" discipline survives intact.
- **Curated values are untouchable.** Warden's curated `timing`+`velocity` and atlas's
  curated `timing` are byte-identical before and after this work; the fallback fills only
  where nothing curated exists, per the existing per-field `derived: true` rules.
- **Per-story precedence.** A story with at least one closed journal session is
  journal-measured; the wall-clock fallback applies only at zero journal coverage for that
  story key. Derivation and merging are per-story, not per-project — a mixed line (doctor)
  must gain fallback marks without disturbing its journal-derived spans.
- **Emit the full renderer contract or nothing.** `velocity.{bars,sub,foot}` and
  `timing.{perStory,epicMin,metric,note,totalLabel,total}` are all-or-nothing shapes; a
  partial object passes the truthiness guard and aborts the whole render (2026-07-26
  incident, documented in `scan_timing`).
- **Offline derivation.** The automatic path reads local git only — no `gh`, no network.
  PR-timestamp numbers remain a curated/manual path (how atlas's were produced).
- **Honest bound.** Whichever wall-clock bound the implementation chooses (open question 1),
  the caption states what is measured — a floor, a ceiling, or a span definition — never an
  unqualified "duration".

## Non-goals

- **Not** retrofitting timing for stories with no spec file or no revision fields — truly
  pre-instrumentation work stays absent, correctly (Dream non-goal).
- **Not** a new orchestration path, and **not** the at-source session journaling for
  hand-driven dispatch — that is the natural territory of the
  `marshal-single-story-dispatch` chain (see Assumptions); this spec only changes how
  already-shipped work is reflected in the console.
- **Not** a change to `marshal deploy reconcile-completions` (Story 5.9) or ledger
  semantics — reconciliation detects completions and promotes specs; this spec consumes its
  output (the promoted spec with intact frontmatter), it does not extend it.
- **Not** re-deriving or second-guessing any curated number.

## Success signal

On the next local dashboard generate after this ships, every `done` story on the board with a
promoted spec carrying resolvable revision fields shows a timing mark — doctor's hand-driven
8.1–8.4 included — with its metric class (wall-clock vs active-compute) legible from the
render; warden's and atlas's curated numbers are byte-identical; and the only stories still
absent are those with genuinely no signal, with a caption that says exactly that.

## Assumptions

- Headless express distill from the Dream; gaps became open questions rather than invented
  answers.
- `baseline_revision`/`final_revision` survive spec promotion verbatim
  (`_execute_promotion_plan` copies Tier-3 bytes; verified against promoted marshal
  spec-11-3 on 2026-08-21) and the promotion pipeline continues to preserve them — the
  tracked spec archive is the durable signal store this spec reads.
- The repo's merge policy (`--merge`, never `--squash`) keeps `final_revision` reachable
  from main. Derivation runs on a local generate with full history; results persist to the
  Pages render via the committed `data.js`, the same model journal-derived velocity already
  uses (CI has no `~/.bmad-loops` and may lack full history — it re-renders, it does not
  re-derive).
- **Convergence, not absorption:** `docs/dreams/marshal-single-story-dispatch.md` (filed
  2026-08-21, being specified in a parallel session) proposes productizing the hand-driven
  single-story dispatch ritual as a marshal verb. If that verb journals its sessions, it
  becomes the natural at-source *producer* of the per-story effort signal this spec
  *displays* — closing the gap at the source with first-party fidelity. This spec is
  deliberately independent of it: the derivation here covers stories already landed (and any
  future route that never adopts the verb), and nothing here blocks or presumes the verb's
  design.
- Claude Code session transcripts were evaluated and rejected as a signal: per-machine, not
  durable, no story-key structure (`signal-inventory.md` § rejected).
