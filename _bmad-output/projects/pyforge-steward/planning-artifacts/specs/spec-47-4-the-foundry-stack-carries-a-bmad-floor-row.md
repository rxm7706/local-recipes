---
title: "Story 47.4: The foundry stack carries a bmad-* floor row"
type: story
created: 2026-09-07
baseline_revision: 3fa06f200a
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: pyforge-steward
warnings: []
deferred: []
---

# Story 47.4: The foundry stack carries a `bmad-*` floor row

<intent-contract>

## Intent

Render the already-made 2026-09-06 architecture decision (verified live in
the spine's own memlog: `"the foundry Stack table gains a bmad-* floor row
... relayed from spec-bmad-suite-lifecycle CAP-9; rendered into the spine
by Story 47.4, not by hand now"`) into the actual `ARCHITECTURE-SPINE.md`
§ Stack table — a single new row, content already fully specified by both
the memlog decision and this story's own epics.md text, with zero new
judgment calls to make. Verified live: § Stack (line 249) currently has
exactly 8 rows (pixi, pixi-build backends, Python, rattler-build,
py-rattler-build, conda-smithy, conda-build, GitHub Actions) and none of
them names any `bmad-*` package.

## Boundaries & Constraints

- **The row's content is fixed, not derived here** — both the epics.md
  story text and the spine's own memlog decision independently specify the
  identical package list and floor versions:
  `bmad-method >=6.12.0`, `bmad-loop >=0.11.1`,
  `bmad-module-skill-forge >=2.1.0` (linux-64 only),
  `bmad-creative-intelligence-suite`, `bmad-method-test-architecture-enterprise`,
  `bmad-eval-quality`, `bmad-utility-skills`, `bmad-builder` — plus the note
  that the win-64 leg (Story 44.11) excludes skf and eval-quality. This
  story transcribes that decision, it does not re-decide the package list
  or re-verify each floor version against a live source a second time
  (that verification already happened in the stories that pinned each one:
  46.7 for skf's v2.1.0, 45.1 for eval-quality, etc.).
- **No AD id is added, changed, or renumbered** — the AC's own text says
  "AD ids unchanged." This is a pure content addition to an existing
  table, never a new architecture DECISION requiring its own AD entry.
- **Placement: appended as a new row at the end of the existing 8-row
  table** (after "GitHub Actions") — the table's existing rows group
  loosely by tooling category (pixi tooling, Python, conda-build tooling,
  CI); the BMAD suite doesn't cleanly fit any of those categories, so
  appending is the surgical, non-presumptuous choice (a documented
  judgment call, not silent).
- **`cutover-readiness.md` G9 is updated** (this story's own named job) —
  no other P or G row.
- **No code change; no AD-list change; no other section of
  `ARCHITECTURE-SPINE.md` touched.**

## I/O Matrix

| Input | Behavior |
|---|---|
| `ARCHITECTURE-SPINE.md` § Stack | Gains one new row (9th), exact content as specified above, appended after "GitHub Actions" |
| `cutover-readiness.md` G9 | State cell: dated, records the row addition |
| `.memlog.md` (spec-bmad-suite-lifecycle) | One new event |
| `.memlog.md` (this architecture's own, `architecture-python-foundry-cutover-2026-09-04/.memlog.md`) | Optionally, a follow-on `(event)` line noting the 2026-09-06 decision was rendered (not required by the Surface line, but keeps that memlog's own decision-to-render trail closed — a judgment call, documented if applied) |
| `sprint-status-ledger.yaml` | `47-4-...: backlog` → `done` |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-python-foundry-cutover-2026-09-04/ARCHITECTURE-SPINE.md`
  - § Stack table: new row, `| bmad-* suite floor | bmad-method >=6.12.0,
    bmad-loop >=0.11.1, bmad-module-skill-forge >=2.1.0 (linux-64 only),
    bmad-creative-intelligence-suite, bmad-method-test-architecture-enterprise,
    bmad-eval-quality, bmad-utility-skills, bmad-builder — win-64 (44.11)
    excludes skf and eval-quality |` (exact cell-1 label a judgment call —
    match the existing table's own naming convention, e.g. "pixi (both
    workspaces)" uses a parenthetical scope note, so "bmad-* suite floor"
    or similar is consistent style).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md`
  - G9 row: state cell dated, records the addition.
- `.memlog.md` for `spec-bmad-suite-lifecycle`: one event.
- `sprint-status-ledger.yaml`: `47-4-...: backlog` → `done`.

## Tasks & Acceptance

1. **Add the `bmad-*` floor row to § Stack.**
   - AC: the table has 9 rows after the edit; the new row's content
     matches the epics.md text verbatim for the package/version list and
     the win-64 exclusion note; no existing row's content changed.
2. **Update `cutover-readiness.md` G9; no other row.**
   - AC: `git diff` on this file shows only G9 changed.
3. **Memlog + ledger.**
   - AC: one new event in `spec-bmad-suite-lifecycle/.memlog.md`; ledger
     key `done`.

## Spec Change Log

- 2026-09-07: initial draft, written directly (no fork) after reading
  the architecture spine's own `.memlog.md` (confirming the exact
  2026-09-06 decision text and its explicit "rendered ... by Story 47.4"
  framing) and `ARCHITECTURE-SPINE.md`'s live § Stack table (confirming 8
  rows, no `bmad-*` row today).

## Review Triage Log

One reviewer subagent ran against the diff (a documented single-reviewer
reduction for this XS-effort, one-line-table-addition, zero-source-code-
change story — the smallest and lowest-risk story in this batch). 0
findings requiring a patch; 1 INFO-level, non-blocking note about this
spec's own Boundaries wording, not about the delivered content.

- **Reviewer note (INFO, not patched):** this spec's Boundaries section
  claimed the epics.md story text and the architecture's own memlog
  decision "independently specify the identical package list" — the
  reviewer found the memlog actually uses abbreviated shorthand (`skf`,
  `CIS`, `TEA`, `BMB`, etc.) and never literally states the win-64
  exclusion clause, while epics.md has the full package names and that
  clause spelled out. The DELIVERED table row matches epics.md (the
  operative acceptance-criteria source) exactly, verbatim — the two
  sources are semantically consistent (the memlog's abbreviations are
  established shorthand for the same conda packages, confirmed
  cross-referenced throughout this project's other memlogs), just not
  literally identical strings. This is a precision nit in this spec's own
  prose, not a defect in what shipped; not patched, since editing the
  spec's own already-finalized Boundaries text after the fact to be more
  hedged would not change any delivered artifact.
- Confirmed independently: no other § Stack row, the mermaid diagram, or
  the Structural Seed block was touched; `cutover-readiness.md`'s diff
  touches only G9; exactly one new event landed in each of the two
  memlogs; the ledger key reads `done`.

Post-review verification: `pixi run -e pyforge-steward pyforge-steward-test`
→ **1180 passed** (unchanged — this story makes no source-code changes).

## Design Notes

- **Why this story doesn't invoke the full `bmad-architecture` persona/
  update workflow as a nested skill call:** the Surface line names
  "`bmad-architecture` update" as the CANONICAL mechanism this repo
  generally uses for spine changes, but the actual content here is
  already fully decided (by the cited 2026-09-06 memlog decision) with
  zero open judgment calls beyond table placement — a full persona-driven
  elicitation pass would be disproportionate to a single, fully-specified
  table row for an XS-effort story. This mirrors every other doc-only
  story in this batch (47.1 hand-edited `cutover-readiness.md` directly
  rather than invoking a planning skill to re-derive its own findings).

## Implementation Notes

- Executed exactly as specified — no deviations, no open judgment calls
  beyond the one already documented (Boundaries & Constraints: appending
  after "GitHub Actions"). `ARCHITECTURE-SPINE.md` § Stack gained the 9th
  row verbatim per the Code Map's literal text (also cross-checked against
  the architecture's own `.memlog.md` line 81 decision and `epics.md`
  Story 47.4's acceptance clause — all three sources agree). No AD id
  touched; no other row, the mermaid diagram, or the Structural Seed block
  changed (`git diff` on `ARCHITECTURE-SPINE.md` shows a single added
  line).
- `cutover-readiness.md` G9's Relay cell updated in place with a dated
  RESOLVED note, mirroring the convention already established by G1/G5/G8
  in the same table; `git diff` on that file shows only the G9 line
  changed.
- Added one event to `spec-bmad-suite-lifecycle/.memlog.md` and, as the
  I/O Matrix's optional item, one follow-on `(event)` line in the
  architecture's own `.memlog.md` closing the 2026-09-06 decision's
  render trail.
- `sprint-status-ledger.yaml` key `47-4-the-foundry-stack-carries-a-bmad-floor-row`
  flipped `backlog` → `done`.
- `pyforge-steward-test` re-run clean afterward — no source code touched
  this story, so the suite's pass count is unchanged from before this
  story ran.

## Auto Run Result

Status: done
Blocking condition: none

Smallest, lowest-risk story in this batch: one new row added to
`ARCHITECTURE-SPINE.md`'s § Stack table, content matching epics.md's own
acceptance text verbatim, rendering the already-made 2026-09-06 memlog
decision. `cutover-readiness.md` G9 resolved; no other row touched. A
single-reviewer pass (documented reduction given the trivial scope) found
zero findings requiring a patch — one INFO-level nit about this spec's own
prose (not the delivered content) left unpatched as not worth the churn.
Final suite: 1180 passed (unchanged, zero source-code changes).
