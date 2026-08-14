---
spec: scratch-worktree-lifecycle
status: ready
owner-dream: docs/dreams/scratch-worktree-lifecycle.md
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
sources:
  - ../../../../../../docs/dreams/scratch-worktree-lifecycle.md
open_questions:
  - "Whether the Tier-3 feed rsync-mirroring step (implementation-artifacts/ never exists in a fresh worktree) gets its own verb or joins `start` — Spec-time-deferred in the Dream; the five-step ritual includes it only when a story touches the gitignored feed."
  - "`workspace update` (single-repo form: fast-forward the scratch branch from its source) — the one source feature the Dream's feature audit left 'Omitted, not ruled out'; nothing directly observed this session maps onto it."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/scratch-worktree-lifecycle.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# Story-scoped scratch worktrees get a named lifecycle: `steward workspace start/ls/status/clean`

## Why

A toil to retire. Every story-scoped scratch worktree in this repo is a hand-typed five-step
ritual: `git worktree add <path> -b <branch> origin/<source>`, do the work, `git worktree remove
<path>`, plus (when the story touches the gitignored Tier-3 feed) manually `rsync`-mirroring
`implementation-artifacts/` in and back out because it never exists in a fresh worktree. Nothing
wraps this. The evidence is direct, current-session observation: a dozen-plus scratch worktrees
created and destroyed by hand across one session's landing passes, each the identical five
commands, each a chance to typo the branch/source pairing or forget the cleanup.

Ownership was investigated, not assumed. Marshal's `spec-pyforge-marshal` CAP-1 is scoped in its
own words to "an isolated... place for a **loop** to run" — `marshal init` creates exactly one
worktree per station slug at a fixed loop-home path, and `cli/init.py`'s docstring explicitly
declines to generalize. Steward's `provision.py` disclaim ("`marshal init`... it never
provisions") covers only loop-home duplication, not worktree tooling for a different purpose —
and a human/agent's point-in-time workspace is squarely Steward's developer-ergonomics estate.

Sizing: quick-dev-sized (1–2 stories) per the standing prefer-quick-dev-over-loop guidance —
thin wrappers over `git worktree` plus a bookkeeping file; steward's sprint is complete, so
capacity exists.

## Capabilities

- **CAP-1**
  - **intent:** `steward workspace start <slug> [--from <branch>]` creates a worktree at a
    conventional scratch path, checks out a new branch off the given source (defaulting to
    `origin/main`), records it in the tool's own bookkeeping, and prints the path — replacing the
    copy-pasted `git worktree add` invocation with one command that cannot typo the
    branch-name/source pairing.
  - **success:** One command yields a ready worktree; its path is printed (and in `--json`,
    machine-readable); the worktree appears in `workspace ls` immediately after.
- **CAP-2**
  - **intent:** `steward workspace ls` enumerates every currently-open scratch worktree this tool
    created, with its branch — a cheap enumeration that spawns no per-worktree git-status
    subprocess, answering "what did I leave open" without `git worktree list | grep`.
  - **success:** `ls` returns instantly regardless of worktree count and reports only
    tool-created worktrees; dirty/ahead/merged fields are absent by design (that is `status`).
- **CAP-3**
  - **intent:** `steward workspace status [<slug>]` reports, per worktree, what `ls` deliberately
    does not: dirty/clean, ahead/behind its source, and whether its branch has already merged —
    the verb that pays the per-worktree git-subprocess cost, mirroring the source dream's own
    `ls`/`status` split.
  - **success:** For each (or the named) tool-created worktree, `status` reports the three health
    facts accurately against live git state; `ls`'s output and cost are unchanged by CAP-3.
- **CAP-4**
  - **intent:** `steward workspace clean [--merged-only]` removes scratch worktrees whose branch
    has already merged (unfiltered, it prompts per-worktree), following `bmad-loop clean`'s
    archive-not-delete discipline rather than destructive removal.
  - **success:** After `clean --merged-only`, no merged tool-created worktree remains open;
    unmerged ones are untouched; nothing is irrecoverably deleted where the archive discipline
    applies; the bookkeeping record is updated to match.
- **CAP-5**
  - **intent:** The tool keeps a bookkeeping record of which worktrees *it* created, and
    `ls`/`status`/`clean` operate only on that set — so they NEVER see, list, or clean Marshal's
    loop-home worktrees (`<loop-home-root>/<slug>`), which are a different lifecycle at different
    paths.
  - **success:** With loop-home worktrees present on disk, `ls` and `clean` enumerate zero of
    them; a hand-made `git worktree add` outside the tool is likewise invisible to it.

## Constraints

- **Always (HARD):** never touch a loop-run worktree — CAP-5's own-worktrees-only bookkeeping is
  the enforcement mechanism, not a best-effort path filter.
- **Always:** wrap, never reimplement — every verb is a thin, named `git worktree` invocation
  plus bookkeeping; no custom git-plumbing logic that could drift from git's own semantics
  (Steward's hexagonal identity).
- **Always:** every verb accepts `--json` for machine-readable output, per this repo's
  established convention (`fleet-picture --json`, every detector's `--json`).

## Non-goals

- **Not** multi-repo coordination — no `.code-workspace` generation, no `clone-repos`, no
  project registry; this repo is a mono-repo and stays one (the source dream's 1,187-LOC
  multi-repo shape was audited feature-by-feature and narrowed in the Dream).
- **Not** automatic editor launch or a `workspace open` verb — `start` reports a path; opening
  it is the caller's next step.
- **Not** a replacement for `bmad-loop clean` — its archive-not-delete handling of loop-run
  worktrees is untouched; CAP-4 borrows the discipline for a disjoint worktree set.

## Success signal

Today, landing one story means hand-typing the five-step ritual, and the current session alone
repeated it a dozen-plus times. After this ships, the same landing pass is
`steward workspace start <slug>` → work → `steward workspace clean --merged-only`, with
`ls`/`status` answering "what's open / what's healthy" in between — and running
`steward workspace ls --json` on a machine with live Marshal loop homes returns none of them.

## Open Questions

- "Whether the Tier-3 feed rsync-mirroring step (`implementation-artifacts/` never exists in a
  fresh worktree) gets its own verb or joins `start` — Spec-time-deferred in the Dream."
- "`workspace update` (single-repo form: fast-forward the scratch branch from its source) — the
  one source feature the Dream left 'Omitted, not ruled out'; include only if a real observed
  need surfaces."
