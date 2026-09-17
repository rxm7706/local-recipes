---
title: "Story 47.3: _bmad/** joins Epic 44's surface and PROJECTS.md carries the cutover layout"
type: story
created: 2026-09-07
baseline_revision: 8d056151f8
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: pyforge-steward
warnings: []
deferred: []
---

# Story 47.3: `_bmad/**` joins Epic 44's surface and `PROJECTS.md` carries the cutover layout

<intent-contract>

## Intent

Two small, mechanical gaps closed. First: `marshal-policy.toml`'s
`[epic_surfaces] "44"` entry (the marshal scope-fence every dispatched
Epic 44 story's diff is checked against, `MRS-GATE-007`) omits `_bmad/**` —
verified live, the entry's own 30+ globs cover `src/`, `docs/dreams/`,
`skills/`, `.claude/skills/`, `pixi.toml`, etc., but never `_bmad/`. fnd:AD-12
(architecture spine, already `[ADOPTED]`) explicitly assigns Story 44.5 the
job of moving `_bmad/`, `_bmad-output/projects/`, and `docs/dreams/` "as one
unit" — without `_bmad/**` in the surface list, that exact move would trip
`MRS-GATE-007`'s hard scope-violation refusal the moment 44.5 actually runs.
Second: `_bmad-output/PROJECTS.md`'s two sections describing the marker +
symlink mechanism (§ Config layering, § Adding a new project) are written
as permanent, local-recipes-only facts with no acknowledgment that fnd:AD-12
moves the ENTIRE mechanism (marker, both planning symlinks, the whole
`_bmad/` + `_bmad-output/projects/` tree) into the foundry as one unit at
the cutover flip (fnd:AD-17) — a reader has no way to know from PROJECTS.md
itself that this same mechanism keeps working, unchanged in its own logic,
just re-rooted, rather than being replaced or left behind.

## Boundaries & Constraints

- **This story does not implement the fnd:AD-12 move itself** (that is Story
  44.5's own job, still `blocked` in the ledger pending solutioning
  review) — it only makes the SCOPE FENCE ready to accept that future
  change without tripping a gate, and makes the DOCUMENTATION honest about
  what will happen when it does.
- **`_bmad/**` is added ONLY to epic "44"'s surface list** in
  `marshal-policy.toml` — no other epic's surface list is touched (verified
  live: no other epic's own move/relocation story needs this glob today).
- **The new PROJECTS.md subsection is descriptive of a FUTURE state gated
  on the fnd:AD-17 flip**, never phrased as already true — it must not read as
  if the marker/symlinks already point at a foundry root today (they do
  not; `bmad-switch`'s own behavior is completely unchanged by this
  story).
- **"Never copied" is the load-bearing phrase from fnd:AD-12 itself** (verified
  by reading the architecture spine directly): the marker and both
  planning symlinks are per-working-tree state, RECREATED by
  `bmad-switch` / `bmad-loop-worktree` in whatever root is active — this
  story's new subsection states this explicitly, mirroring fnd:AD-19's own
  "generated per-machine links, gitignored" convention for
  `.claude/skills`/`.cursor/skills` (the cutover's target-tree diagram,
  read directly) so a reader sees the SAME principle applied to both
  mechanisms rather than two independently-invented explanations.
- **No code change.** The Surface line names only
  `marshal-policy.toml`, `PROJECTS.md`, and a memlog entry — `dispatch_verify.py`
  (the file that actually reads `[epic_surfaces]`) is read for
  understanding only, never edited.
- **`cutover-readiness.md` G1 and G8 rows are updated** (this story's own
  named job in both the P/G tables), not any other row.

## I/O Matrix

| Input | Behavior |
|---|---|
| `marshal-policy.toml`'s `[epic_surfaces] "44"` list | Gains `"_bmad/**"` as one new entry; every existing entry unchanged |
| A hypothetical future diff touching `_bmad/**` under Epic 44 | Would now pass `MRS-GATE-007`'s scope check (previously would have hard-refused as `SCOPE_VIOLATION`) |
| `PROJECTS.md` | Gains one new subsection (placed after § Adding a new project, before § Reading another project's artifacts) describing the fnd:AD-12 cutover-target layout; the two existing sections (§ Config layering, § Adding a new project) are otherwise unchanged — this story adds context, it does not rewrite them |
| `cutover-readiness.md` G1 | State cell: `_bmad/**` added, dated |
| `cutover-readiness.md` G8 | State cell: PROJECTS.md subsection added, dated, naming the two sections no longer left silently un-cross-referenced |
| `.memlog.md` (spec-bmad-suite-lifecycle) | One new event |
| `sprint-status-ledger.yaml` | `47-3-...: backlog` → `done` |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/marshal-policy.toml`
  - `[epic_surfaces] "44"` list: add `"_bmad/**",` as a new line (placed
    near the other top-level repo-root globs already in the list —
    `.gitignore`, `pixi.toml`, `pixi.lock`, `environment.yaml` — for
    readability, not functionally required since TOML array order doesn't
    matter).
- `_bmad-output/PROJECTS.md`
  - New subsection, "## Cutover target (foundry, fnd:AD-12)", inserted after
    § Adding a new project (line ~85) and before § Reading another
    project's artifacts (line ~87). Content: states that `_bmad/`,
    `_bmad-output/projects/`, and `docs/dreams/` move whole into
    `python-foundry` as one unit at Story 44.5 (cited, not restated in
    depth — points at the architecture spine's own fnd:AD-12); the marker
    file and BOTH planning symlinks are per-working-tree state, recreated
    fresh by `bmad-switch`/`bmad-loop-worktree` in whichever root is
    active, NEVER copied as static content — mirroring fnd:AD-19's own
    generated-per-machine-links principle for `.claude/skills`/
    `.cursor/skills`; `bmad-switch`'s own command surface and semantics
    (§ Active project switching, above) are completely unchanged by the
    move — only the root it operates against changes, and only at the
    fnd:AD-17 flip, not before.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md`
  - G1 row: state cell dated, records the glob addition.
  - G8 row: state cell dated, records the new subsection and that the two
    cited PROJECTS.md sections no longer contradict fnd:AD-12/fnd:AD-19 (they were
    never WRONG, just silent about the future move — this story adds the
    missing cross-reference, it does not correct an error in the existing
    two sections).
- `.memlog.md` for `spec-bmad-suite-lifecycle`: one event.
- `sprint-status-ledger.yaml`: `47-3-...: backlog` → `done`.

## Tasks & Acceptance

1. **Add `_bmad/**` to Epic 44's marshal-policy surface.**
   - AC: `grep -A2 '"_bmad/\*\*"' marshal-policy.toml` shows the new entry
     inside the `"44"` array (not any other epic's array); every other
     epic's `[epic_surfaces]` array is byte-identical before/after.
2. **Write the new PROJECTS.md subsection.**
   - AC: the subsection exists, is placed correctly, cites fnd:AD-12 and fnd:AD-19
     by name, uses the word "never copied" (or equivalent) for both the
     marker and the two planning symlinks, and does not claim the foundry
     root is active today.
3. **Update `cutover-readiness.md` G1 and G8; no other row.**
   - AC: `git diff` on this file shows only G1 and G8 changed.
4. **Memlog + ledger.**
   - AC: one new event; ledger key `done`.

## Spec Change Log

- 2026-09-07: initial draft, written directly (no fork) after reading
  `marshal-policy.toml`'s full `[epic_surfaces] "44"` list (confirming
  `_bmad/**` genuinely absent), the architecture spine's fnd:AD-12/fnd:AD-17/fnd:AD-19
  text directly, `PROJECTS.md` in full (confirming the exact line ranges
  G8 cites), and `dispatch_verify.py`'s own consumption of
  `effective.epic_surfaces.value` (confirming this is a real, live
  scope-fence, not decorative).

## Review Triage Log

Two independent, context-free reviewer subagents ran against the diff
(Blind Hunter + Verification Gap; a documented two-reviewer reduction for
this doc/config-only, zero-source-code-change, low-blast-radius story,
matching the precedent already established for Stories 47.1/47.2). 0
findings requiring a patch; 1 low-severity, pre-existing-terminology note
that predates this story.

- **Blind Hunter**: independently confirmed `_bmad/**` was genuinely
  absent from epic "44"'s array before this change and that no other
  epic's array was touched; read `dispatch_verify.py`/`core/gate.py`'s
  actual `fnmatch.fnmatch` matching logic directly and live-confirmed
  `fnmatch.fnmatch("_bmad/custom/config.toml", "_bmad/**")` returns
  `True` (noting, informationally, that `fnmatch` has no true globstar
  semantics — `_bmad/**` translates identically to `_bmad/*` — but this
  is pre-existing, identical behavior for every other `**` entry in the
  file, not something this story introduces or needs to fix); read
  fnd:AD-12/fnd:AD-17/fnd:AD-19's actual spine text directly and confirmed the new
  PROJECTS.md subsection's paraphrases are accurate, not distorted;
  confirmed the future-state disclaimer is unambiguous and live-checked
  against this worktree's actual marker/symlink state; confirmed
  `cutover-readiness.md`'s diff touches only G1/G8. One LOW finding:
  the new subsection's "Story 44.5, blocked pending solutioning review"
  phrasing doesn't literally match the ledger's own `backlog` status for
  that key — but this is INHERITED terminology already used identically
  by `epics.md`'s own Epic 44 banner and `marshal-policy.toml`'s
  pre-existing comment on the same "44" array, not something this story
  introduced. Not patched: fixing a repo-wide terminology convention this
  story didn't create is out of scope for a two-line surface addition and
  a documentation subsection; a future story addressing Epic 44's own
  status terminology consistently is the right place for it.
- **Verification Gap**: independently re-ran every Task's AC via direct
  commands (line-range boundary check on the "44" array, section-order
  and citation verification on PROJECTS.md, `git diff --numstat` on
  cutover-readiness.md, event-count diff on the memlog, the ledger flip)
  — all four proven exactly as claimed, zero gaps.

Post-review verification: `pixi run -e pyforge-steward pyforge-steward-test`
→ **1180 passed** (unchanged — this story makes no source-code changes).

## Design Notes

- **Why the new PROJECTS.md subsection is placed between § Adding a new
  project and § Reading another project's artifacts, not appended at the
  end of the file:** it is a direct extension of the two sections G8
  cites (§ Config layering's marker/symlink mechanism, and § Adding a new
  project's directory-creation walkthrough) — placing it immediately after
  them, rather than at the document's end, keeps the cross-reference
  physically adjacent to what it's cross-referencing, matching this
  file's own existing convention of grouping related "how the switching
  mechanism works" content together before the more general "reading
  without switching" sections that follow.

## Auto Run Result

Status: done
Blocking condition: none

Implementation delivered all 4 tasks cleanly: `"_bmad/**"` added to epic
44's marshal-policy surface array (verified as the sole change to that
array); a new "## Cutover target (foundry, fnd:AD-12)" subsection added to
PROJECTS.md at the correct location, citing fnd:AD-12/fnd:AD-19 accurately and
explicitly disclaiming present-tense truth. `cutover-readiness.md`'s G1/G8
rows resolved with dated notes; no other row touched. A 2-reviewer pass
(Blind Hunter + Verification Gap, documented reduction given the doc-only
shape) found zero findings requiring a patch — one low-severity note about
inherited, pre-existing "blocked" terminology in Epic 44's own convention,
correctly left unpatched as out of this story's narrow scope. Final suite:
1180 passed (unchanged, zero source-code changes).
