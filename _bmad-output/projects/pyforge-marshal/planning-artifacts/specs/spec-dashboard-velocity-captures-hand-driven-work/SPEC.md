---
id: SPEC-dashboard-velocity-captures-hand-driven-work
spec: dashboard-velocity-captures-hand-driven-work
status: shipped
updated: "2026-09-09"
owner-dream: docs/dreams/dashboard-velocity-captures-hand-driven-work.md
surface:
  # SURFACE CORRECTION recorded 2026-09-09 (fleet-readiness batch rows mars-A-D1/D8). Entries are
  # annotated, NOT re-pointed: `scripts/fleet_scan.py`'s destination is owed to steward Cutover
  # Story 44.1, and moving governance here would pre-empt that decision. See § Residual.
  - pyforge.doctor.sources.fleet_scan   # HAS NEVER EXISTED — the real file is `scripts/fleet_scan.py`, governed today by `spec-factory-console`
  - docs/dashboard/index.html           # now a 14-line "console moved" stub (steward Story 30.2)
  - docs/dashboard/data.js              # no longer on disk — retired writer (`fleet_scan.py:6`, `:93`)
companions:
  - signal-inventory.md
sources:
  - ../../../../../../docs/dreams/dashboard-velocity-captures-hand-driven-work.md
open_questions: []
  # ALL FOUR RETIRED 2026-09-09 (operator, fleet-readiness batch row mars-A-B10): OQ-4 CLOSED AS
  # MOOT, and the other three ANSWERED IN THE SHIPPED CODE. Full text with answers in
  # § Open questions -- closed 2026-09-09.
---

> **Canonical contract.** This SPEC and `signal-inventory.md` are the complete,
> preservation-validated contract for the work. The Dream in frontmatter is its origin; the
> code facts below were verified against `pyforge.doctor.sources.fleet_scan`,
> `.claude/skills/bmad-dev-auto/step-03-implement.md`/`step-04-review.md`, and
> `pyforge.marshal.cli.deploy` on 2026-08-21.

# Every done story leaves a timing mark — "unmeasured" stops meaning "not loop-driven"

## Why

A pain to solve. The console's velocity chart (`pyforge.doctor.sources.fleet_scan::scan_timing`,
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
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`: `scripts/fleet_scan.py` genuinely implements this — `_frontmatter_scalars(spec_path, ("baseline_revision", "final_revision"))` (lines 2916-2942) reads the promoted spec's revision pair, the derived ceiling is `final_revision − baseline_revision` commit timestamps (lines 2792, 3243), and derived output is marked `"derived": True` (lines 3178, 3256) matching the existing discipline; `pixi run -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta/test_dashboard_scan_timing_wall_clock.py -q` → 22 passed. **Cannot verify end-to-end** ("after a local generate"): confirmed live that `fleet_scan.py:main()` (lines 3505-3511) unconditionally prints a retirement notice and returns 2 — `_generate`, the only caller of `scan_timing`, is unreachable from the CLI (steward Story 30.2 retired the Guildhall generator), exactly as this Spec's own 2026-09-09 Residual note already documents. The derivation is real and unit-proven; the "next local dashboard generate" it describes has no live entry point to exercise it against.
- **CAP-2 — fidelity is visible, never blended.**
  - **intent:** A wall-clock-derived mark is visually and textually distinguished from
    journal-derived active agent-compute wherever both render — wall-clock measures a
    different thing (includes waits; excludes nothing), and `scan_timing`'s own comments
    already forbid sharing the active-compute axis undistinguished (the atlas precedent).
  - **success:** On a line mixing both classes, a reader can tell each story's metric class
    from the rendered chart/caption alone; no wall-clock number appears as if it were
    active-compute.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`: `TIMING_CLASS_ACTIVE = "active-compute"` / `TIMING_CLASS_WALL_CLOCK = "wall-clock-ceiling"` (lines 2806-2807) back a per-sid `perStoryClass` field (line 3262); epic rollups never blend — `epicMin` (journal) vs a distinct `epicMinWallClock` (line 3266) with a dual `totalLabel`; the class-separation logic is exercised by the 22 passing unit tests in `test_dashboard_scan_timing_wall_clock.py`. Same production-reachability caveat as CAP-1: the render this describes has no live caller (see CAP-1's `main()` finding), so "on the rendered chart" is verified against code + tests, not a live render.
- **CAP-3 — the coverage caption partitions by true reason.**
  - **intent:** The coverage statement stops lumping every unmeasured story under "predates
    loop instrumentation" and instead states the real classes: journal-measured,
    wall-clock-derived, spec-without-revision-fields, and no-spec-at-all (the only class
    that stays absent).
  - **success:** For a line containing hand-driven stories, the rendered caption names each
    absence class accurately; no caption claims "predates instrumentation" for a story whose
    spec carries revision fields.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`: all four named classes exist as distinct constants (`TIMING_COVERAGE_JOURNAL`/`_WALL_CLOCK`/`_SPEC_NO_REVS`/`_NO_SPEC`, lines 2810-2813) and are independently formatted into the caption (lines 3008-3026: "N journal-measured", "N wall-clock-derived", "N spec-without-revision-fields deliberately absent", "N no-spec-at-all deliberately absent") — no blanket "predates loop instrumentation" phrase remains in the caption-building code. Same production-reachability caveat as CAP-1/CAP-2: verified against code + the 22-test suite, not a live rendered caption, since `main()` has no path to `_generate`.

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

## Open questions — closed 2026-09-09

- ~~"Wall-clock bound choice: `ts(final_revision) - ts(baseline_revision)` overstates … whichever
  bound is chosen, the caption must state what is measured."~~ **ANSWERED IN SHIPPED CODE:** the
  bound is the **ceiling**, `ts(final_revision) - ts(baseline_revision)`, and the caption names the
  bound (`scripts/fleet_scan.py:3079-3083`, `:2792`, `:2802`, `:3243`).
- ~~"Render surface for the wall-clock class: the timing strip only, or also a visually distinct
  bar class on the velocity graph?"~~ **ANSWERED IN SHIPPED CODE: `timing.perStory` only, never
  `velocity.bars`.** Every sid carries a `perStoryClass` of `active-compute` | `wall-clock-ceiling`,
  and epic rollups never blend (`epicMin` vs `epicMinWallClock`, dual `totalLabel` at
  `:3085-3089`).
- ~~"Partial journal coverage … is the hand-finished remainder ever surfaced, or accepted as
  under-measurement?"~~ **ANSWERED: the journal floor wins**, and the hand-finished remainder is
  accepted as under-measurement (SPEC.md § Constraints, unchanged in code).
- ~~"Should `bmad-build-auto`'s HALT protocol additionally stamp a first-party duration?"~~
  **CLOSED AS MOOT — no.** This Spec's own convergence assumption is **confirmed**: `marshal
  factory dispatch` writes a per-run `journal.jsonl` with timestamped dispatch-launch
  intent/outcome pairs plus a `session.log`, under
  `_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/<run-id>/` (four live runs
  read: marshal 2026-09-02, atlas 2026-09-01, mason 2026-09-02, steward 2026-09-03). Stamping the
  HALT would add a second, weaker producer in the one layer that does not survive
  `bmad-method update` without `bmad-customize`.

## Residual (2026-09-09) — implemented, zero production consumers

CAP-1..CAP-3 are implemented and unit-tested (7 call sites in
`.claude/skills/conda-forge-expert/tests/meta/test_dashboard_scan_timing_wall_clock.py`) but have
**zero production consumers**: `scan_timing`'s only non-test caller is `_generate` at
`fleet_scan.py:3591`, reachable only from a `main()` that returns 2 (`fleet_scan.py:3505-3511`,
after steward Story 30.2 deleted the Guildhall generator). **The Success signal cannot be
exercised.**

**One decision is owed before steward Cutover Story 44.1 resolves `scripts/fleet_scan.py` to a
destination:** re-home the derivation behind Lane 1 / the atlas Vizro board, **or** retire
CAP-1..CAP-3 with the console that consumed them.
