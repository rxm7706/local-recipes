---
title: PR lifecycle — a story lands itself
type: dream
owner: marshal
status: realized
archived-reason: absorbed
---

> **Superseded 2026-08-02 (dream consolidation).** Fully decomposed into `spec-pyforge-marshal`
> and the real PRD as FR-59 (landing rules are declared policy) and FR-60 (`marshal land` —
> idempotent open/label/wait/merge/retire/resync) — see
> [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). See `spec-pr-lifecycle` for the
> retirement record.

# PR lifecycle — a story lands itself

## The Dream

The engine drives a story to a merged commit on its station branch and stops.
Everything after that — open the PR, know which labels this repo demands, wait
for the right checks, merge, delete the branch, resync — is done by a human
typing, or by an agent improvising the same sequence from memory each time.

A factory whose last mile is hand-driven is not unattended; it is unattended
until the interesting part. **The Dream is that a story that passed its gates
lands on `main` without anyone driving it**, and that the rules for landing are
declared once, in code, instead of remembered correctly five times a day.

> If a human has to remember the repo's merge rules, the repo's merge rules are
> not enforced — they are a habit with a good track record.

## Why now — one session's evidence

On 2026-07-31 a single session hand-drove **five PRs** (#170–#174). Every one
repeated the same sequence: create with `--repo` (this fork needs it), add the
`maintenance` label (the inherited linter reds on any non-`recipes/` change),
regenerate `environment.yaml` if `pixi.toml` moved (an **ungated** check the
label does not suppress), poll the linter, squash-merge, delete the branch,
resync `main`, and re-verify the working tree.

Every step is a written rule. Not one is enforced by anything but attention:

- **#170 merged with a broken detector.** It changed a file governed by
  `spec-pyforge-genesis` without moving that Spec's memlog. The only check that
  ran was the inherited linter, so it went green. Nothing in the landing path
  asked what the change had actually broken.
- **Label and env-sync are repo-specific and easy to miss.** They are documented
  in `CLAUDE.md` precisely because they are forgotten; documentation is what you
  write when a rule has no home in code.
- **Merge strategy is load-bearing and invisible.** Squash-merging once made
  Epic 10's story commits unreachable from `main` and froze a dashboard at 36/38
  with a ticking clock on a finished story.

The cost is not the typing. It is that the last mile is the one place with no
supervisor, no journal, and no verdict — in a factory whose whole claim is that
every stage has all three.

## What is real

- **The engine lands on the station branch.** `bmad-loop` merges each story
  worktree into `loop/<slug>` with a recorded subject. That much is automatic
  and durable.
- **From station branch to `main` is entirely manual.** No tooling owns it.
- **The pieces exist, unassembled:** `gh` is provisioned, the checks exist
  (`linter`, `detectors`), the merge-subject contract is already Marshal's
  (story 1.2), and `marshal config` already knows how to compose and record a
  policy — which is where landing rules belong.

## What is real, part two — the last mile has no idea a run is happening (measured 2026-08-09)

`marshal land` shipped and does what CAP-2 asked: open/label/wait/merge/retire/resync, no
human in the sequencing loop. Operating it during a **live** run exposed two things the
Dream never considered, because when it was written landing happened *after* a run, never
*during* one.

- **`land` would have destroyed a running fleet.** Its head branch is *the loop-home station
  branch* (`cli/land.py` resolves `head_branch` to exactly that), and
  `landing_branch_retirement` defaults to **True**. Invoked while bmad-loop was mid-story on
  `loop/pyforge-doctor`, it would have merged and then **deleted the branch the harness was
  actively merging stories into**. Nothing in the verb asks whether a run is in flight. It
  was avoided on 2026-08-09 only because a human read the source first — which is not a
  safety mechanism.
- **"Resync" does not mean what the operator needs it to mean.** `landing_resync` resyncs
  the **feed**; `landing_resync_commands` defaults to empty. Nothing brings the loop home's
  station branch back to `main` after a landing, so it drifts from the moment the first PR
  merges. Measured the same day: `loop/pyforge-doctor` **5 commits behind main** minutes
  after its own stories landed, and — before that — **8 PRs behind** on origin between runs,
  reported clean by every detector.

Both are the same shape as the durability finding of the same day: **the verb is right, its
awareness of context is missing.** A last mile that cannot tell whether the road is still in
use is not finished.

## The frontier

- **Landing as a policy surface, not a script.** Required checks, merge
  strategy, label rules, branch-delete behaviour, and the env-sync trigger
  declared in `EffectivePolicy` with provenance — the same treatment gates got.
  A repo states its rules; Marshal executes them.
- **`marshal land <story>`** — open, label, wait, merge, delete, resync. Idempotent
  and re-entrant, because the interesting failure is a half-landed story: PR open,
  checks green, merge never issued.
- **Refuses, like teardown does.** Story 1.8 established the shape — a
  destructive step that will not proceed on unmerged work without an explicit
  flag. Landing needs the same: no merge on a red required check, no merge past
  an unacknowledged advisory finding, no silent force.
- **A verdict and a paper trail for the last mile.** Which checks were required,
  which passed, what merged, under whose authority — the audit triad applied to
  landing ([[fidelity-enforcement]]: Marshal builds, Doctor judges, Scribe records).
- **Unattended is the point.** A run that ends with "somebody should open a PR"
  has not ended.

## What this is not

Marshal's Epic 4 (*landing with a durable paper trail*) is about the record a
landing leaves. This is about **performing** the landing at all. They meet, and
the record is worthless if the act is still manual.

It also does not touch the engine — **wrap, never absorb** holds. `bmad-loop`
deliberately leaves this gap open; Marshal fills it *around* the engine, in the
supervisor, exactly as it does for provisioning and teardown.

## Kinships

[[pyforge-marshal]] (this resolves an open question its Spec parked —
see the log below) · [[durable-runs]] (both are about work surviving the gap
between stages; that one saves it, this one lands it) ·
[[fidelity-enforcement]] (the required-checks decision is a gate question, and
today's advisory CI is why "merged green" and "actually green" can differ) ·
[[pyforge-doctor]] (holds the verdict on Marshal's own rows) · [[pyforge-charter]].

## Realization log

- **2026-08-09 (later)** — Reopened again, for the half FR-173 missed. That FR
  makes a LANDING leave the home current; it says nothing about pushing the
  station branch, and — decisively — a landing done **by hand** never runs that
  code at all. Every landing on 2026-08-09 was `gh pr merge`, so the eight loop
  homes drifted **33–74 commits** behind main with nothing reporting it, and
  origin's `loop/*` refs drifted further still. The cost was not cosmetic:
  mason's stale home made the S-13.7 surface guard silently stop biting (0/3
  reconciled, against steward's 4/4 from a current home) and **nothing failed and
  nothing was logged**. The durable fix is therefore a CHECK at the chokepoint
  every spin must pass — preflight — rather than a promise attached to a landing
  path that can be bypassed.

- **2026-08-09** — Reopened after operating `marshal land` alongside a live 9-story run.
  Two gaps, neither of which existed when the Dream was written because landing was then a
  post-run act: the verb retires the station branch with no live-run guard, and its
  "resync" is the feed rather than the loop home's own currency with `main`. Recorded here
  rather than as a new Dream — this IS the last mile, it just turns out the last mile has
  to know whether anyone is still driving on it.

- **2026-07-31** — Dream seeded (operator call): **"Marshal should own the PR
  lifecycle."** This **resolves open question #10 in `spec-pyforge-marshal`**,
  which asked whether PR-lifecycle automation belongs to Marshal, upstream, or
  the provisioning station, and recorded it as *currently a non-goal*. The Spec's
  non-goal must therefore be amended — re-derived from its memlog, not
  hand-patched — and this Dream is the input for that. Evidence at seeding: five
  PRs hand-driven in one session, one of which (#170) merged a real detector
  break because nothing in the landing path asked. Constraint carried forward
  unchanged: **wrap, never absorb** — the engine keeps dev/verify/review/commit.
