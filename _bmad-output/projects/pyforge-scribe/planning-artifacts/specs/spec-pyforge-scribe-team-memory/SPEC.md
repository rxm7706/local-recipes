---
id: SPEC-pyforge-scribe-team-memory
spec: pyforge-scribe-team-memory
status: archived
archived-reason: duplicate
owner-dream: docs/dreams/pyforge-scribe-team-memory.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/pyforge-scribe-team-memory.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`duplicate`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# pyforge-scribe-team-memory — retirement record

## Why it was contracted

A team-memory system for Scribe: structured YAML-frontmatter + prose entries (type ∈
user/project/feedback/reference), a `/remember [type]` capture affordance, a two-layer
model (user auto-memory promoted into team memory after review), an editorial promotion
gate, automatic context loading at session start, and a compact `MEMORY.md` index. Success
criteria named 20+ entries per station across all 8 PyForge stations, a proven promotion
loop, agents referencing loaded memory in decisions, sub-1-minute pattern discovery, and a
50% onboarding-time cut.

## Why it ended

**Retired 2026-08-02, same day it was created.** The dream was generated in a bulk commit
(`dad47c408a`) later found to contain fabricated content elsewhere in the same commit (a
migration note with false claims about the dashboard generator, boilerplate
test-architecture.md files duplicated across stations with only nouns swapped). This dream's
own content did not survive scrutiny as new scope: its six-item "Realization" list maps
near-verbatim onto capabilities already fully contracted in Scribe's own constitutive Spec
(`spec-pyforge-scribe`) and decomposed into `epics.md`:

- **"Structured Memory" (frontmatter, type taxonomy)** ↔ `spec-pyforge-scribe`'s AD-3 (schema
  parity: `.claude/memory/<type>/*.md` frontmatter is byte-identical in shape to user-local
  auto-memory, `type` ∈ `{feedback, project, reference}`) and epics.md FR-8 (Epic 1, Story 1.1).
- **"Automatic Capture" (`/remember [type]`)** ↔ CAP-1 / FR-1, delivered as `scribe capture`
  in Epic 1 Story 1.1 — the same mechanism, different invocation spelling.
- **"Team Layers" (user memory → promoted team memory)** ↔ CAP-1's `scribe capture --promote`
  and MEM-1 in the already-existing `spec-team-memory` (owner-dream `docs/dreams/team-memory.md`,
  absorbed into Scribe 2026-07-25): "an entry written by one operator is present for every
  other operator and agent on the next clone."
- **"Memory Promotion" ("is this a pattern, or just today's frustration?")** ↔ Epic 1 Story 1.3's
  team-relevance test, verbatim in spirit: "would a day-1 contributor benefit from this rule?"
  — proposal-then-confirm, team-voice rewrite (FR-3/FR-4).
- **"Context Loading" (agents load team memory automatically at session start)** ↔ Epic 1
  Story 1.2 ("`CLAUDE.md` wiring — team memory loads automatically") and `spec-pyforge-scribe`'s
  own Why section, which states the identical goal in the identical words: "every session
  starts already knowing what the team knows."
- **"Memory Index" (concise `MEMORY.md`, ~200-line convention)** ↔ epics.md FR-2 exactly
  ("`MEMORY.md` index stays under 200 lines").
- **"Feedback is reactive... pattern is never named"** (the Problem section's pattern-discovery
  complaint) ↔ Epic 2 ("Knowledge Graph — Compile & Recall"), which is `scribe recall`'s
  entire purpose (CAP-3, FR-12/FR-13) — already specified, already storied (2.1–2.4), not new.

Every one of the six Realization items and both remaining Problem-statement complaints resolve
to work already covered by an existing capability, AD, FR, or story in Scribe's live planning
chain. There was no new capability here to specify; authoring a second Spec for the same
surface would have created a competing, driftable contract for scope already under governance
— the same failure mode already retired once this session in `spec-pyforge-marshal-loop-orchestrator`.

## What carries forward

Nothing new — the intent this dream restates already lives in [[pyforge-scribe]],
`spec-pyforge-scribe`, and the pre-existing `spec-team-memory` it absorbed. Those are the
canonical contracts for Scribe's capture/promotion/compile/recall capability (Epic 1 + Epic 2,
9 stories, 22% code-complete). This record exists only so a future reader does not re-derive
the "is this new scope?" question from scratch.

## Non-goals

- **Reviving this Dream as written.** Its intent was never separate from `spec-pyforge-scribe`'s
  or the pre-existing `spec-team-memory`'s; there is nothing here to revive.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design.
- **Treating the numeric success-criteria (20+ entries/station, 50% onboarding cut, etc.) as
  new targets to plan against.** They are elaborations of already-specified capability, not
  evidence of missing scope — Scribe's own Spec already carries its success signal.

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent went,
without re-deriving the duplication or mistaking it for a second contract on top of
`spec-pyforge-scribe`.
