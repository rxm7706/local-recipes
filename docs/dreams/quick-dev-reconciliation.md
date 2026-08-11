---
title: Two ways to finish a story, and Marshal has only ever heard of one
type: dream
owner: marshal
status: dreamt
---

# Two ways to finish a story, and Marshal has only ever heard of one

## The Dream

A human can run `bmad-quick-dev` directly against any station's codebase, right
now, with no Marshal involvement at all — it is a generic BMAD skill
(`.claude/skills/bmad-quick-dev/`), documented in `pyforge-marshal`'s own
architecture doc as a parallel choice to the loop, not something the loop
drives: `architecture-bmad-infra.md:1003`'s flow diagram shows the fork
explicitly —

```
        ┌───────┴────────┐
        │ attended       │ unattended
        ▼                ▼
4a. bmad-quick-dev   4b. bmad-loop drives DEV→VERIFY→REVIEW→VERIFY→COMMIT
    / bmad-dev-story     in a loop home (~/.bmad-loops/<slug>), one worktree
                         + branch per story, squash-merged
```

— two labelled, equally legitimate branches of the SAME step, never a
Marshal-orchestrated choice. `architecture-bmad-infra.md:455` describes
`bmad-quick-dev` as one of BMAD's four implementation skills ("implement any
intent against existing conventions"); nothing in that description, or
anywhere else `pyforge-marshal`'s own source was searched, treats it as
something Marshal is aware of. A repo-wide grep of
`src/shared/packages/pyforge-marshal/` for `quick-dev` / `quick_dev` returns
**zero matches** — every hit in the project lives in planning prose
(`architecture-bmad-infra.md`, `development-guide.md`,
`source-tree-analysis.md`), never in `core/`, `cli/`, `adapters/`, or a
schema.

That absence is not cosmetic — it is a real hole in the ledger a run-loop
story finishes into. `sprint-status-ledger.yaml`'s own header names the
mechanism precisely: it is "the TRACKED twin of
`implementation-artifacts/sprint-status.yaml`" promoted by
`scripts/promote_sprint_status.py`, and that script's docstring is explicit
about who writes the source of truth it promotes — "**bmad-loop** marks a
story `done` at DEV completion" (`scripts/promote_sprint_status.py:24`). The
`development_status:` map underneath (`sprint-status-ledger.yaml:17-`) is a
flat `<story-key>: done | backlog` vocabulary with no third value and no
sibling field for *how* a story reached `done`. A story a human finishes by
hand through `bmad-quick-dev` never touches this map at all — bmad-loop never
ran, so nothing ever calls the code path that flips its key to `done`. The
work can be real, tested, merged to `main`, and durable, and the ledger will
still show it as `backlog` forever, because the only thing that promotes a
key out of `backlog` is a signal only the loop emits.

The same gap repeats one layer up. `marshal status`'s fleet view
(`core/status.py::derive_home_state`, Story 5.1, `epics.md:1131-1140`) derives
"what is running?" from journals and run state — "never from a hand-maintained
file" is the AD-5 promise the story's own acceptance criteria state
verbatim. A quick-dev session against a station's codebase leaves no journal
entry at all: no run id, no story-sequence record, nothing `derive_home_state`
can read. So Marshal cannot distinguish "the loop is between stories, nobody
is working" from "a human just landed a real story by hand" — both report
identically as an idle home, because the fleet view was built to answer "is
the loop doing something," never "did the work get done."

Epic 4's landing machinery — the one place `pyforge-marshal` already builds a
durability guarantee around a *finished* story — makes the same assumption.
Story 4.1's spec-promotion predicate (`epics.md:792-810`) promotes "every
merged story's spec... automatically and durably" the moment bmad-loop's own
journal shows a merge; Story 4.6's reconciliation (`epics.md:893-912`) closes
an open `intent` entry only against evidence bmad-loop itself produced (a
commit sha, a worktree absence, a PR number tied to *its own* run). Neither
story has any path for "a spec that was never in loop scratch to begin with,
because a human wrote and merged it directly." A quick-dev'd story's spec —
if one exists at all — gets none of the promotion, durability, or
reconciliation guarantees a loop-landed story gets by construction.

This is a genuine gap, not a rediscovery: a repo-wide search of
`pyforge-marshal`'s 120-story backlog (`epics.md`) for "quick-dev",
"mixed mode", "hand-implement", or any reconciliation language pointed at a
non-loop completion path returns nothing. The one open question that brushes
against it — PRD `Q-16`, "the route-versus-contain boundary, per `bmad-*`
skill Marshal routes to" (`prd.md:961`) — is about whether Marshal should
*invoke* a BMAD skill on an operator's behalf, a different question from this
one: this Dream is not about Marshal calling `bmad-quick-dev`, it is about
Marshal noticing, after the fact, that someone already did.

## What it looks like when real

- An operator can hand-pick any backlog story and run `bmad-quick-dev`
  against it directly — today's workflow, unchanged — while that station's
  `bmad-loop` run sits between stories, or is actively mid-run on a
  **different** story, and Marshal's own tracked state stays coherent either
  way.
- After that quick-dev session lands (merged to the integration branch, by
  whatever path the operator used), something folds its completion into
  `sprint-status-ledger.yaml` — or the mechanism that feeds it — so the story
  reads `done`, not `backlog`, without an operator hand-editing a generated
  file.
- The recorded fact distinguishes *how* the story reached `done` — via
  `bmad-loop` or via `bmad-quick-dev` — so `marshal status` / the fleet
  dashboard can show it, and nobody has to reconstruct the answer from commit
  archaeology (the exact failure mode `promote_sprint_status.py`'s own
  docstring already documents for a different reason — PR #132's squashed
  merge subjects).
- A quick-dev'd story's spec gets the same promotion/durability treatment
  Story 4.1 already gives a loop-landed one — "promoted" still means "will
  still exist next week," regardless of which path produced it.
- None of this requires quick-dev to change, or to run *through* Marshal.
  The reconciliation happens by observing what already happened (git,
  merged specs, story identity) — the same "derive, never hand-maintain"
  discipline AD-5 and AD-33 already hold Marshal's status/journal split to.

## Constraints

- **Not a routing change.** This Dream does not decide whether Marshal ever
  *invokes* `bmad-quick-dev` on an operator's behalf — that is PRD `Q-16`'s
  open question, untouched here. This is strictly about reconciling a
  completion that already happened outside Marshal's control back into
  Marshal's own tracked state.
- **Not a concurrency mechanism.** "Mid-run, a different story" means the
  ledger stays coherent when a quick-dev completion is folded in around a
  live loop run — it does not mean Marshal orchestrates the two happening
  *simultaneously*, or arbitrates a conflict if they ever touch the same
  files. Any locking/coordination machinery for genuinely concurrent writers
  is out of scope for this Dream.
- **Stays inside AD-5/AD-33.** Whatever detects a quick-dev completion reads
  git (repository facts) and existing spec/story-identity artifacts — never
  a new hand-maintained flag, and never something the loop's own journal
  format has to grow a special case for.
- **No implementation detail is prescribed.** Whether detection watches merge
  commits, story-key naming, spec promotion, or some combination is a design
  decision for the Spec and its downstream story, not settled here.

## Realization log

- **2026-08-11** — Captured after the operator asked why `bmad-loop`-driven
  unattended development is slower/costlier than a supervised `bmad-quick-dev`
  session, and what Marshal could do to let development mix modes. Confirmed
  via grep: zero references to `quick-dev`/`quick_dev` anywhere in
  `src/shared/packages/pyforge-marshal/` (only in planning prose). Confirmed
  via `epics.md`: no existing FR/epic/story covers mixed-mode tracking.
  Queued as a Dream rather than touched directly — `core/status.py`,
  `cli/deploy.py`, `scripts/promote_sprint_status.py`, and
  `sprint-status-ledger.yaml`'s generator were deliberately left untouched
  pending the Spec/story chain. Companion pain, same investigation, separate
  Dream (different subsystem, different epic):
  [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md).
