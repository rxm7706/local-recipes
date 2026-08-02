---
spec: pr-lifecycle
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/pr-lifecycle.md
surface: []          # archived — no live surface of its own; see § What carries forward
companions: []
sources:
  - ../../../../../../docs/dreams/pr-lifecycle.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included. It states what was contracted, why it
> ended, and what survives — not a plan for work that will not happen.

# pr-lifecycle — retirement record

## Why it was contracted

`bmad-loop` drives a story to a merged commit on its station branch and stops. Everything
after — open the PR, know which labels this repo demands, wait for the right checks, merge,
delete the branch, resync — was hand-driven or improvised from memory each time. Evidence,
2026-07-31: one session hand-drove five PRs (#170–174), each repeating the same six-step
sequence by hand; #170 merged with a broken detector because nothing in the landing path
asked what the change had broken. Four capabilities: a landing policy surface (CAP-1), one
verb performing the whole sequence idempotently (CAP-2), refusal semantics mirroring teardown
(CAP-3), and a verdict + paper trail for the last mile (CAP-4).

## Why it ended

**Retired 2026-08-02, as part of a dream-consolidation pass — fully decomposed, not a
duplicate.** All four capabilities are accounted for in `spec-pyforge-marshal`'s real PRD,
under CAP-9 (the 2026-07-31 operator ruling that resolved the PRD's own open question #10):

- **CAP-1** (landing policy surface) → **FR-59** (landing rules declared policy, including
  this fork's `maintenance` label and the ungated `environment.yaml` sync trigger as named
  policy keys, not memorized habits).
- **CAP-2** (`marshal land <story>`, idempotent open/label/wait/merge/retire/resync) and
  **CAP-3** (refusal semantics mirroring teardown's FR-8: no merge on a red required check,
  no merge past an unacknowledged advisory finding, no silent force) → both folded into
  **FR-60** (`marshal land` — its Consequences state the refusal semantics directly rather
  than splitting them into a separate FR).
- **CAP-4** (a verdict and paper trail for the last mile) → also **FR-60**'s Consequences
  ("every landing writes a journal verdict: which checks were required, which passed, what
  merged, under whose authority") — the audit-triad framing this capability borrowed from
  [[fidelity-enforcement]] CAP-6 stays true at the FR grain: Marshal performs the landing and
  writes the verdict; Doctor and Scribe's own roles in that triad are their chains' concern,
  not restated here.

## What carries forward

Everything — this Dream's own evidence (the five hand-driven PRs, the #170 detector break,
the Epic 10 squash-merge incident) is cited directly in the consolidated `pyforge-marshal.md`
and in FR-59/FR-60's own Grounding notes. FR-59/60 in the real PRD are the current, binding
contract for everything this Spec proposed. The distinction this Spec drew between FR-59's
per-landing branch-retirement key and [[durable-runs]]'s fleet-wide sweep (FR-63) is preserved
verbatim in FR-63's own Consequences ("the two share no code path but must not disagree").

## Non-goals

- **Reviving this Dream as written.** Its intent already lives in FR-59/60.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design — the backlog items are FR-59/60's own stories.
- **Redefining the merge-subject contract.** That stays story 1.2's / `spec-pyforge-marshal`'s
  own, consumed by FR-60, not restated here.

## Success signal

A reader arriving at this Dream learns in one page that all four capabilities landed in
FR-59/60 — not a gap, not a duplicate — without re-deriving the mapping.
