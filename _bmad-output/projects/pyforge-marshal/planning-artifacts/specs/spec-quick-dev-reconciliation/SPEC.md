---
id: SPEC-quick-dev-reconciliation
spec: quick-dev-reconciliation
status: shipped
owner-dream: docs/dreams/quick-dev-reconciliation.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - scripts/promote_sprint_status.py
sources:
  - ../../../../../../docs/dreams/quick-dev-reconciliation.md
open_questions:
  - "Which concrete detection signal (a merge-commit heuristic, a spec-promotion event, an explicit operator-declared marker checked against observed diff/merge evidence, or some combination) answers 'did this story complete outside the loop' -- a story-level design decision, not resolved by the Dream."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/quick-dev-reconciliation.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# Two ways to finish a story, and Marshal has only ever heard of one

## Why

A pain to solve. A human can run `bmad-quick-dev` directly against any station's codebase
right now, completely independent of Marshal's own orchestration --
`architecture-bmad-infra.md` documents it as a parallel, equally legitimate branch to
`bmad-loop`, never something Marshal drives or observes. A repo-wide grep of
`src/shared/packages/pyforge-marshal/` for `quick-dev`/`quick_dev` returns zero matches: every
reference lives in planning prose, none in `core/`, `cli/`, `adapters/`, or a schema.

That absence is a real hole in the ledger a loop-landed story finishes into.
`sprint-status-ledger.yaml`'s `development_status:` map is a flat `done | backlog`
vocabulary, and `scripts/promote_sprint_status.py`'s own docstring says plainly that
**bmad-loop** marks a story `done` at DEV completion -- a quick-dev completion never calls
that path, so the key stays `backlog` forever regardless of real, merged, tested work.
`core/status.py::derive_home_state` (Story 5.1, AD-5) derives fleet state from journals and
run state only, and a quick-dev session leaves no journal entry, so Marshal cannot tell "the
loop is between stories" from "a human just landed a real story by hand." Epic 4's own
durability guarantees (spec promotion, reconciliation) key entirely off bmad-loop's journal
signal, so a quick-dev'd story's spec gets none of that treatment either.

This is a genuine, unaddressed gap: no FR/epic/story in `pyforge-marshal`'s 120-story backlog
covers mixed-mode tracking or quick-dev reconciliation. The adjacent PRD open question, `Q-16`
("route-versus-contain boundary, per `bmad-*` skill"), is about whether Marshal ever *invokes*
a skill -- a different question from this one, which is about Marshal *noticing, after the
fact,* that a human already did.

## Capabilities

- **CAP-1**
  - **intent:** Something observes git (repository fact) plus existing spec/story-identity
    artifacts and recognizes that a backlog story's work landed via a path other than
    bmad-loop, without relying on a hand-maintained flag.
  - **success:** Given a story merged to the integration branch with no corresponding
    bmad-loop journal/run record, the detection mechanism identifies it as completed outside
    the loop, naming the story key and the evidence it used.
- **CAP-2**
  - **intent:** A detected non-loop completion is folded into the tracked ledger -- the
    story's key advances out of `backlog` in `sprint-status-ledger.yaml` (or the mechanism
    feeding it) -- and the record distinguishes `bmad-loop` vs `bmad-quick-dev` as the
    completion path.
  - **success:** `marshal status` / the fleet dashboard shows a quick-dev'd story as `done`
    with its completion path labelled, with no operator hand-edit to a generated file and no
    commit-subject archaeology required.
- **CAP-3**
  - **intent:** A quick-dev'd story's spec receives the same durability guarantee Story 4.1
    already gives a loop-landed story's spec.
  - **success:** A quick-dev'd story's spec, once its story is detected as done, is
    promoted/tracked the same way a loop-landed story's spec is -- "promoted" means "will
    still exist next week" regardless of which path produced it.
- **CAP-4**
  - **intent:** An operator can hand-pick any backlog story for `bmad-quick-dev` while that
    station's `bmad-loop` run is between stories, or mid-run on a **different** story, and
    Marshal's own tracked state (ledger, dashboard) stays coherent either way.
  - **success:** Reconciling a quick-dev completion around a live, unrelated loop run neither
    corrupts that run's own journal/state nor blocks the reconciliation -- both are provably
    true in the same test pass.

## Constraints

- **Always:** detection reads git (repository facts) and existing spec/story-identity
  artifacts -- never a new hand-maintained flag, and never a special case bolted onto the
  loop's own journal format (AD-5/AD-33's existing discipline).
- **Always:** `bmad-quick-dev` itself is untouched -- it gains no Marshal dependency and keeps
  working exactly as it does today, run directly by a human against any station's codebase.

## Non-goals

- **Not** a routing change. This spec does not decide whether Marshal ever *invokes*
  `bmad-quick-dev` on an operator's behalf -- that is PRD `Q-16`'s open question, untouched
  here. This is strictly reconciliation of a completion that already happened.
- **Not** a concurrency/locking mechanism. "Mid-run, a different story" means the ledger stays
  coherent when a quick-dev completion is folded in around a live loop run -- it does not mean
  Marshal orchestrates the two happening simultaneously, or arbitrates a same-file conflict.
  Genuine concurrent-writer coordination is a separate, already-scoped investigation thread.
- **Not** a prescription of the detection mechanism -- left to the downstream story's design.

## Success signal

A backlog story implemented and merged entirely via `bmad-quick-dev`, with no `bmad-loop` run
ever touching it, reads `done` (with its completion path labelled `bmad-quick-dev`) in
`sprint-status-ledger.yaml` and the fleet dashboard -- without an operator hand-editing either
-- and its spec is durably promoted the same way a loop-landed story's spec is.

## Open Questions

- "Which concrete detection signal (a merge-commit heuristic, a spec-promotion event, an
  explicit operator-declared marker checked against observed diff/merge evidence, or some
  combination) answers 'did this story complete outside the loop' -- a story-level design
  decision, not resolved by the Dream."
