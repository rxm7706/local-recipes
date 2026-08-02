---
id: SPEC-herald-moments-2-4-missing-surface
spec: herald-moments-2-4-missing-surface
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/herald-moments-2-4-missing-surface.md
surface: []          # archived — this record has no surface of its own; see § What carries forward
sources:
  - ../../../../../../docs/dreams/herald-moments-2-4-missing-surface.md
open_questions: []
---

> **Retirement record — NOT a closeout.** This Dream is `status: archived`
> (`absorbed`). Charter §5 requires every Dream to carry a Spec, archived included: a
> retirement record is how the next reader learns what happened instead of rediscovering
> it. It states what was contracted, why the Dream *file* ended, and — critically here —
> what did **not** end. Read `## What carries forward` before assuming this means the
> work is done; it is the opposite of done.
>
> **Update 2026-08-02 (later same day).** `## What carries forward` below says
> `spec-herald-moments-2-4` and its downstream PRD/Architecture "stay exactly as they are,
> live and unarchived." That is now **false**: per an explicit, same-day user override of
> the keep-chains-separate convention, `spec-herald-moments-2-4`'s three capabilities were
> folded into `spec-pyforge-herald/SPEC.md` as HER-11–HER-13, its PRD into
> `prd-pyforge-herald-2026-08-01/prd.md` as a Satellite section, and its Architecture into
> `architecture-herald-pitch-2026-08-01/ARCHITECTURE-SPINE.md` as AD-11–AD-20. The
> original `spec-herald-moments-2-4/` folder (SPEC.md + .memlog.md; its `epic-structure.md`
> companion moved to `spec-pyforge-herald/`) is archived, unmodified, at
> `archive/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4/`.
> This record's own Non-goals section below (listing "touching spec-herald-moments-2-4" as
> a non-goal) is correspondingly superseded for the same reason. The work itself — Moments
> 2–4 — remains exactly as unbuilt as this record originally said; only its planning
> chain's filing location changed.

# herald-moments-2-4-missing-surface — retirement record

## Why it was contracted

Herald's constitutive Dream ([[pyforge-herald]]) named four moments of proclamation but
only ever built out Moment 1 (Pitch — the deck family). This Dream was opened 2026-08-02
to name and prioritize the three still-missing surfaces: Moment 2 (Progress — make
shipping motion visible), Moment 3 (Success — a claim backed by retrievable evidence),
and Moment 4 (Operations — deprecation/fix/end-of-life notices). Its stated next steps
were to audit any prior Moment 2/3 material, author a Moment 4 spec from first
principles, and decide an orchestration strategy.

## Why it ended (as a top-level Dream file)

**Folded into [[pyforge-herald]] 2026-08-02**, as part of a repo-wide dream-consolidation
pass that reduced Herald from three active Dream files (the constitutive Dream, this one,
and [[fleet-chain-completeness]] — separately reassigned to Marshal the same day for an
unrelated infrastructure-scope reason) down to one. This Dream's own next-steps had
already been executed in full before the consolidation: by 2026-08-02 its audit had run,
its orchestration strategy was decided (a coordinated epic, not three independent ones),
and a complete Spec → PRD → Architecture → Epics chain existed for Moments 2–4. At that
point the Dream's remaining job was narrative — restating "Herald owes Progress, Success
and Operations the way it owes Pitch" — and that narrative duplicated content the
constitutive Dream needed to say about itself anyway. Keeping two Dream files meant Herald's
own scope was split across two documents that had to be read together to get the whole
picture; folding this Dream's narrative into [[pyforge-herald]] restores one source of
truth for "what is Herald and what is it doing right now."

**This is not a duplicate-scope or work-is-done retirement** (contrast
[[pyforge-mason-recipe-validator]] and [[pyforge-marshal-loop-orchestrator]], both retired
because their entire proposal already existed elsewhere as decided, unimplemented scope).
Moments 2–4 are real, unfinished, actively-tracked work. Retiring the Dream *file* here is
a documentation move, not an implementation status change.

## What carries forward

**Everything downstream of this Dream stays exactly as it is, live and unarchived**, and
continues to be Herald's execution reference for Moments 2–4:

- **`spec-herald-moments-2-4`** (a differently-named, still-live sibling of this retirement
  record — do not confuse the two) — the real Spec this Dream produced: CAP-1 (Progress
  Visibility), CAP-2 (Success Proclamation), CAP-3 (Operations Notices), all three
  orchestration decisions locked (coordinated epic; on-ship webhook + weekly-cron trigger
  for Moment 2; auto-extract + operator-review-gate for Moment 3; date/category archive for
  Moment 4).
- **`prd-herald-moments-2-4-2026-08-02/prd.md`** — the PRD decomposing that Spec.
- **`architecture-herald-moments-2-4-2026-08-02/`** — the Architecture spine.
- **`epics.md`** (the Moments-2-4 epic breakdown currently filed at
  `planning-artifacts/epics.md`) — 7 epics, ~12–19 stories (Foundation CLI, Foundation Web,
  Progress, Success, Operations, Integration Testing, Documentation).

As of this record's creation (2026-08-02), **zero stories in that chain are implemented**
— Moments 2–4 have no code yet. This is the immediate next build target once Herald's
in-flight design-code-bridge CLI foundation (`SPEC-design-code-bridge` CAP-1..5, currently
4 of 17 stories done, loop paused mid-story on the fallback transport adapter) clears its
own remaining stories. A reader tracking Herald's real progress should read `epics.md` /
the project's sprint-status feed directly, not this record — this record is a pointer, not
a status board.

## Non-goals

- **Treating this record as evidence Moments 2–4 shipped, or that they were abandoned.**
  Neither is true; they are open, active, in-progress work.
- **Re-deriving Moments 2–4's Spec/PRD/Architecture/Epics from this Dream a second time.**
  They already exist under `spec-herald-moments-2-4` and stay canonical; this record does
  not supersede them.
- **Archiving or otherwise touching `spec-herald-moments-2-4` or its downstream PRD /
  Architecture / Epics.** Only the top-level Dream file (and this meta-level retirement
  record for it) is archived here.

## Success signal

A reader arriving at this Dream learns in one page that its narrative moved into
[[pyforge-herald]], that its own Spec/PRD/Architecture/Epics chain is untouched and still
the live reference for Moments 2–4, and that Moments 2–4 remain unbuilt — without mistaking
"the Dream file is archived" for "the work is finished."
