---
spec: durable-runs
status: in-progress
owner-dream: docs/dreams/durable-runs.md
surface:
  - scripts/unpushed_work_check.py
  - scripts/loop_push_watch.py
companions: []
sources:
  - ../../../../../../docs/dreams/durable-runs.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. `docs/dreams/durable-runs.md` is listed in `sources:` for narrative rationale and prose color this contract intentionally omits.

# SPEC — durable runs

## Why

An unattended factory that can lose its own output is not autonomous, it is
lucky. Every artifact a run produces — commit, story spec, verdict, the tokens
that bought them — should be durable the moment it exists, not the moment
somebody remembers to save it. Measured 2026-07-31: 6 station loop branches on
no remote, ~5,150 lines on `recover/*`, herald 1.2's 734-line transport story
(spec included) unpushed six days, 156 dangling commits one `git gc` from
unrecoverable, and marshal 1.8's 1,748 lines sitting 40 minutes as a
local-only commit. Nine detectors ran green throughout because none asked the
durability question — the window is not a backlog, it reopens every ~60–90
minutes as each station finishes a dev phase.

## Capabilities

- **CAP-1 — unpushed-work detection.** *(shipped)*
  - **intent:** A `scope=runtime` detector finds local branches carrying
    unique content that are on no remote, plus dangling commits holding real
    work `git gc` may collect, and reports `unknown` rather than a false green
    where it structurally cannot run (a CI runner has neither local branches
    nor dangling objects).
  - **success:** `scripts/unpushed_work_check.py` (pixi task
    `unpushed-work-check`) flags every such branch and commit; it is excluded
    from the CI detector set rather than run there vacuously.

- **CAP-2 — interval push stopgap.** *(shipped)*
  - **intent:** While any `bmad-loop` engine runs, push every loop home's
    station and per-story branches on an interval, bounding worst-case loss to
    one interval instead of leaving it unbounded; exits on its own when the
    fleet does, and is read-only against working trees so it is safe beside a
    live run.
  - **success:** `scripts/loop_push_watch.py` (pixi task `loop-push-watch`)
    runs on a default 1800s interval with `--interval N` / `--once` /
    `--quiet`.

- **CAP-3 — stage-boundary push.**
  - **intent:** Marshal's supervisor around `bmad-loop` (a git-pinned external
    dependency, so this is a wrapper seam rather than a patch to its
    completion path) pushes after each stage boundary of a run — after the
    dev commit, after the review verdict, after the merge — so loss is bounded
    by a stage rather than a timer.
  - **success:** a session killed between two stage boundaries loses at most
    the incomplete stage; CAP-2's interval window is no longer the binding
    bound on worst-case loss.

- **CAP-4 — durability wired into fleet launch.**
  - **intent:** The interval-push watcher (or its CAP-3 successor) starts
    automatically as part of launching the fleet, rather than depending on a
    human to remember to start it — it was absent for the entire 2026-07-31
    incident for exactly that reason.
  - **success:** starting the fleet starts the watcher with no separate manual
    step.

- **CAP-5 — durability as a reported run property.**
  - **intent:** The fleet console refuses to report a chain's row clean when
    its branches are unpushed, the same refusal discipline it already applies
    to an unowned Dream row.
  - **success:** an unpushed-work finding surfaces on the owning chain's
    dashboard row, not only in a separate detector's CLI output.

- **CAP-6 — branch retirement.**
  - **intent:** The inverse of CAP-1 — derive which station/story branches may
    be released: content reachable in `main` **by patch-id** (not a diff
    heuristic — three-dot mismeasures squash-merges, two-dot mismeasures
    branches `main` has moved past), the branch's run concluded, and its story
    `done` with a recorded merge sha. `loop/*` branches and `rescue/*` tags are
    never candidates.
  - **success:** a pruning run proposes a retirement only where it can name
    the evidence (merge sha + patch-id match + concluded run) per branch,
    dry-run by default like `adopt`, and refuses rather than defaults to
    delete on anything it cannot prove.

## Constraints

- CAP-2 and CAP-3 are push-only against working trees and remotes — never
  force-push, never rewrite history — so they cannot disturb a live session or
  destroy work.
- CAP-1 (`unpushed-work-check`) is `scope=runtime` and must stay out of the
  `scope=repo`/CI detector set: a CI runner has neither local branches nor
  dangling objects, so running it there is a vacuous pass, not a stricter
  gate.
- CAP-6 must classify by patch-id matching against `main`, never a two-dot or
  three-dot diff heuristic — both were tried in this Dream's own authoring
  session and both misclassified real cases (squash-merges; branches `main`
  had since moved past).
- `loop/*` branches and `rescue/*` tags are permanently excluded from CAP-6:
  `loop/*` is how the fleet operates, and `rescue/*` tags are the only
  reachability for commits `git gc` would otherwise collect — untagging one
  re-arms the failure it exists to prevent.

## Non-goals

- A general git-hygiene tool. Scope is bounded to the loop/story/station
  branches this factory's fleet creates, not arbitrary developer branches.
- Replacing CAP-2 with CAP-3 outright — the interval watch is an explicit
  stopgap that remains as a floor/backstop once stage-boundary push ships.
- Rescue-tag lifecycle management. CAP-6 reads `rescue/*` only as a permanent
  exclusion; it does not manage when a rescue tag itself may finally be
  dropped.

## Success signal

A dev phase that finishes and is immediately killed leaves no work
recoverable only from one disk — verified by re-running the 2026-07-31
audit (`unpushed-work-check` + a dangling-commit scan) and finding zero
station branches on no remote and zero dangling commits holding unrecorded
work. Separately, a `branch-retirement` dry run over the current ~62-branch
estate names evidence (merge sha, patch-id match, concluded run) for every
branch it proposes to retire, and proposes zero retirements it cannot prove.
