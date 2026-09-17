---
title: A scratch worktree for one story's work is one command, not five
type: dream
owner: steward
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-steward]]** on 2026-09-17 (one-chain-per-station steward fold; folded from `scratch-worktree-lifecycle`).


# A scratch worktree for one story's work is one command, not five

## The Dream

Landing a single story — or drafting a Dream, or any point-in-time task scoped to one story's
worth of work — currently means a human or agent hand-typing the same five-step ritual every
time: `git worktree add <scratch-path> -b <branch> origin/<source-branch>`, do the work, `git
worktree remove <scratch-path>`, and (if the story touched a gitignored Tier-3 feed) manually
`rsync`-mirroring it in and back out because `implementation-artifacts/` never exists in a fresh
worktree. Nothing wraps this. The pattern is right there in this repo's own recent history — a
dozen-plus scratch worktrees created and destroyed by hand in a single session's worth of landing
passes, each one the identical five commands, each one a chance to typo the branch name or forget
the cleanup. `steward workspace start/ls/clean` (or an equivalent verb set) makes this one command
each: open a scratch worktree for a named story, see what's currently open, and prune what's
already merged — the same shape `bmad-loop clean` already gives loop-run worktrees, but for
human/agent-driven point-in-time work instead.

## What it looks like when real

- `steward workspace start <story-or-task-slug> [--from <branch>]` creates a worktree at a
  conventional scratch path, checks out a new branch off the given source (defaulting to
  `origin/main`), and reports the path — replacing the current copy-pasted `git worktree add`
  invocation with one command that can't typo the branch-name/source pairing.
- `steward workspace ls` lists every currently-open scratch worktree this tool created and its
  branch — answering "what did I leave open" without a raw `git worktree list | grep`.
- `steward workspace status [<slug>]` reports, per worktree, what `ls` deliberately does not:
  dirty/clean, ahead/behind its source, and whether its branch has already merged — the health
  check `ls` only gestures at. Kept as its own verb rather than folded into `ls`'s output because
  `ls` should stay a cheap enumeration (no git-status subprocess per worktree) while `status` is
  the one that pays that cost, mirroring `developer-workspace-management`'s own split between
  `ls` and `status` in its source form.
- `steward workspace clean [--merged-only]` removes worktrees whose branch has already merged
  (or, unfiltered, prompts per-worktree) — the same shape as `bmad-loop clean`'s archive-not-delete
  discipline for loop-run worktrees, applied to this tool's own scratch worktrees instead.
- Every verb accepts `--json` for machine-readable output, matching this repo's own established
  convention (`fleet-picture --json`, every detector's `--json`) — `ls`/`status` in particular are
  exactly the kind of output another tool (or a future automated landing pass) would want to
  consume programmatically rather than scrape from text.
- Nothing here reimplements git — every verb is a thin, named wrapper around `git worktree`
  itself, matching Steward's own "hexagonal wrap-never-reimplement" identity.

## What is real

Nothing built yet — this is a fresh `dreamt`-stage capture, motivated by directly observed
repetition rather than speculation. The five-step manual pattern this replaces is the literal
sequence used throughout the current session's own landing passes (create scratch worktree off
`origin/loop/pyforge-<slug>`, merge `origin/main`, do the work, mirror the gitignored Tier-3 feed
in via `rsync` when needed, remove the worktree) — evidence that this gap is live, not
hypothetical, though no incident (unlike [[bmad-switch-scope-enforcement]]'s DW-1-4-2) has yet
resulted from it; it is pure toil, not yet a documented bug.

A sibling org's `developer-workspace-management` dream (`wf-dev-cli`'s `commands/workspace.py`,
1,187 LOC) does a related, much larger thing: MULTI-repo worktree coordination (a "workspace" is
several repos' worktrees, one per registered project, opened together via a generated
`.code-workspace` file and editor launch). That shape doesn't map onto this repo, which is a
single mono-repo — there is no second repo to coordinate, no `.code-workspace` file needed since
the editor already opens the one root. This Dream keeps only the piece that transfers: the
open/list/clean lifecycle for a scratch worktree, scoped to one repo, one branch, one story.

## Whose job this is, and why it isn't Marshal's

Investigated directly, not assumed, because Marshal already owns `marshal init`/`bmad-loop-worktree`
— the closest-looking existing machinery:

- Marshal's own `spec-pyforge-marshal/SPEC.md` CAP-1 contract is scoped, in its own words, to
  "an isolated... place for a **loop** to run" — every success criterion (marker/symlink
  agreement, Tier-3 backlink, teardown refusing on uncommitted work) is phrased around loop-run
  isolation specifically, never a general story-scoped developer worktree.
  `marshal init <slug>` creates exactly ONE worktree per station slug, at a fixed path
  (`<loop-home-root>/<slug>`), on a fixed branch (`loop/<slug>`) — there is no notion of "one
  more, for this specific story, then discard it."
- `cli/init.py`'s own module docstring explicitly declines to generalize: "no legacy sibling-repo
  layout (the spec's own Boundaries & Constraints — do not reinvent the sibling-repo layout)."
  Marshal has already, deliberately, drawn this line.
- Steward's own `provision.py` disclaims worktree creation ("`marshal init`... it never
  provisions") — but that disclaim is scoped to NOT duplicating Marshal's LOOP-home machinery,
  not a blanket refusal of worktree creation for a different purpose. Steward's own Dream is "the
  estate the factory stands on" — developer/operator ergonomics broadly — and this is squarely
  that: a human or agent's own point-in-time workspace, not a loop's.

## Constraints

- **Never touch a loop-run worktree.** This tool's scratch worktrees and Marshal's loop homes
  are different lifecycles at different paths; this Dream must not read, list, or clean anything
  under Marshal's `<loop-home-root>/<slug>` paths.
- **Wrap, never reimplement.** Every verb is a named `git worktree` invocation plus bookkeeping —
  no custom git-plumbing logic that could drift from git's own semantics.
- **A scratch worktree that touches a BMAD project should verify its context**, not assume it —
  see Kinships below.

## Non-goals

- **Not multi-repo coordination.** No `.code-workspace` file, no `clone-repos`, no notion of a
  "project" spanning several git repositories — this repo is a mono-repo and stays one.
- **Not automatic editor launch.** `workspace start` reports a path; opening it in an editor is
  the caller's own next step, same as any `git worktree add` today.
- **Not a replacement for `bmad-loop clean`** — that tool's archive-not-delete discipline for
  loop-run worktrees is untouched and out of scope here.

See "Full feature audit" below for the per-feature reasoning behind these and every other
capability the source dream carried that this one doesn't.

## Full feature audit against `developer-workspace-management`

Every verb the sibling org's dream names, and this Dream's disposition on each — so a future
reader can decide whether to include or enhance any of the omitted ones without reconstructing
this audit by hand:

| Source feature | Disposition | Why |
|---|---|---|
| `workspace start {feature}` (multi-repo) | **Included, narrowed** | Kept, scoped to one repo — no second repo exists here to coordinate. |
| `.code-workspace` file generation | **Omitted** | No second repo to open together; the editor already opens this repo's one root. |
| Auto-open editor | **Omitted** | Keeps the verb scriptable/composable rather than assuming an interactive editor session — same reasoning as `workspace open` below. |
| `workspace add` (add a repo to an existing workspace) | **Omitted** | No multi-repo "workspace" concept exists here to add a repo *to*. |
| `workspace rm` (remove a repo from a workspace) | **Omitted** | Same reasoning as `add`. |
| `workspace clean` | **Included** | `workspace clean [--merged-only]`. |
| `workspace ls` | **Included** | `workspace ls`. |
| `workspace status` (parallel git-health checks) | **Included** (2026-08-14 audit) | Was folded into `ls`'s description in the first draft, undersold as a result; now its own verb — see "What it looks like when real." |
| `workspace open` (reopen editor) | **Omitted** | Same reasoning as auto-open — this tool reports paths, not opens editors. |
| `workspace update` (sync/update across repos) | **Omitted, not ruled out** | No PyForge equivalent identified yet. In single-repo form this would mean "fast-forward the scratch branch from its source" — plausible and useful, but unlike `start`/`ls`/`clean`/`status` it doesn't map onto anything directly observed this session, so it's left as a genuine open question rather than silently dropped. |
| `workspace clone-repos` | **Omitted** | Mono-repo — nothing to clone. |
| JSON output | **Included** (2026-08-14 audit) | Missing from the first draft despite matching this repo's own strong `--json`-everywhere convention; now every verb. |
| `pyforge.toml [projects]` registry | **Omitted** | No config file of this shape exists or is needed for a single mono-repo; see [[developer-machine-bootstrap]]'s own audit for the adjacent question of whether *any* `pyforge.toml`-equivalent belongs in this repo. |
| `argcomplete` tab completion | **Omitted, unverified** | No PyForge CLI (checked: `fleet-picture`, the detectors, `bmad-switch`) currently registers tab completion — adding it here would set a repo-wide precedent this one Dream shouldn't decide unilaterally. |

## Kinships

[[bmad-switch-scope-enforcement]] (a scratch worktree opened against a specific BMAD project is
exactly the caller [[bmad-switch-scope-enforcement]]'s `verify_scope` primitive was designed for —
cross-station kinship, Marshal's mechanism called from a Steward-owned verb, not a merge) ·
[[pyforge-steward]] (the estate; this Dream's natural home per steward's own developer-ergonomics
identity) · [[bmad-module-provisioning]] (the investigative-rigor precedent this Dream's
"whose job" section follows — ruling a nearby station out on its own documented boundaries rather
than by default)

## Realization log

- **2026-08-14** — Dream captured, alongside [[developer-machine-bootstrap]] and
  [[bmad-switch-scope-enforcement]], while evaluating a sibling org's dream catalog for PyForge
  fit. Scoped down hard from the source dream's multi-repo `.code-workspace` shape to a
  single-repo scratch-worktree lifecycle, grounded in this session's own directly-observed
  repetition (a dozen-plus hand-run `git worktree add`/`remove` cycles across landing passes, no
  tool wrapping any of it). Ownership investigated rather than assumed: Marshal's `marshal init`
  is explicitly loop-home-scoped (its CAP-1 contract's own words) and its own docstring declines
  to generalize ("do not reinvent the sibling-repo layout"); assigned to Steward as the
  developer-ergonomics station whose disclaim of loop-worktree creation was scoped to avoiding
  duplication of Marshal's machinery, not a refusal of worktree tooling generally.

- **2026-08-14 (same day)** — Feature-parity audit against the source dream, requested after the
  initial capture, found `workspace status` and JSON output silently undersold rather than
  deliberately excluded; both folded in above. Every other source feature now carries an explicit
  disposition in "Full feature audit" rather than living only in a conversation transcript.

- **2026-08-14** — Spec authored (spec-scratch-worktree-lifecycle, pyforge-steward) by the
  2026-08-14 dream-backlog audit: workspace start/ls/status/clean over git worktree,
  own-worktrees-only bookkeeping, archive-not-delete clean.
