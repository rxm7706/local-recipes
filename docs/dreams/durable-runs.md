---
title: Durable runs — work survives the machine that made it
type: dream
owner: marshal
status: archived
archived-reason: absorbed
---

> **Superseded 2026-08-02 (dream consolidation).** Fully decomposed into `spec-pyforge-marshal`
> and the real PRD as FR-61 (bounded-loss durability, stage-boundary push + fleet-launch
> wiring), FR-62 (durability as a reported fleet-status dimension), and FR-63 (fleet-wide
> branch retirement) — see [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). Nothing in
> this Dream's real, measured evidence (the 2026-07-31 audit table) is lost — it is cited
> directly in the consolidated Dream. See `spec-durable-runs` for the retirement record.

# Durable runs — work survives the machine that made it

## The Dream

An unattended factory that can lose its own output is not autonomous, it is
lucky. Every artifact a run produces — the commit, the story spec, the verdict,
the token spend that bought them — should be **durable the moment it exists**,
not the moment somebody remembers to save it.

The loss is never only code. A discarded story is lost **compute, tokens, and
wall-clock**: marshal 1.8 was 8.8M weighted tokens and about an hour of a
machine's life, and for forty minutes it existed as an unpushed commit on one
disk. Recovering code is possible. Re-buying the hour is not.

> A run that has to be remembered is a run that can be forgotten.

## Why now — measured, not feared

Asked on 2026-07-31 whether the fleet's work was saved, the answer was no, and
the size of "no" was the surprise:

| At risk | Extent |
|---|---|
| Station loop branches | **6** (marshal, doctor, herald, mason, scribe, steward) — none on any remote |
| `recover/*` branches | **~5,150 lines** across four rescue branches |
| herald 1.2 transport | **734 lines**, 7 files *including its story spec*, unpushed **six days** |
| Dangling commits | **156** holding real content, one `git gc` from unrecoverable |
| marshal story 1.8 | **1,748 lines**, committed by the dev phase and unpushed **40 minutes** |

Nothing detected any of it. Nine detectors ran green throughout, because not one
asked the question. And the precedent was already on the record: scribe 1.3's
1,102 lines survived only as a dangling commit and came back by luck.

**The window is not a backlog — it reopens.** "Everything is saved" was true when
said and false forty minutes later, because a dev phase had finished in between.
Nine stations, one dev phase each per 60–90 minutes: the factory spends most of
its life with an hour of unsaved work somewhere.

## What is real

- **`unpushed-work-check`** — the detector, shipped 2026-07-31. Local branches
  with unique content that are on no remote, plus dangling commits holding real
  work. `scope=runtime`, and that is load-bearing: a CI runner has neither local
  branches nor dangling objects, so this check would pass **vacuously** there —
  a gate reporting success because it stands where the failure cannot occur.
- **`loop-push-watch`** — the stopgap, shipped the same day. Pushes every loop
  home's station and per-story branches on an interval while any engine runs,
  exits by itself when the fleet does. Push is read-only against working trees,
  so it is safe beside a live run. It **bounds** worst-case loss to one interval;
  it does not remove it.
- **156 rescue tags** on origin, making previously unreachable commits reachable.

## The frontier

- **The loop pushes at its own stage boundaries.** The real fix, and the reason
  this Dream exists rather than a cron entry: after the dev commit, after the
  review verdict, after the merge. Loss becomes bounded by a *stage*, not by a
  timer. Marshal owns the run lifecycle, so this is Marshal's to build —
  `bmad-loop` itself is a git-pinned external dependency, so the seam is
  marshal's supervisor around it, not a patch to someone else's completion path.
- **Interval push as the floor, not the ceiling.** Keep the watcher as the
  backstop for whatever the stage hooks miss, and make it part of a fleet launch
  rather than something started by hand — it was absent for this entire run
  because nobody thought of it, which is the same failure one level up.
- **Durability is a run property, and should be reported like one.** A run whose
  work is not on a remote is not "green"; the console should say so on the row,
  the way it refuses to publish an unowned Dream.
- **Nothing should require a human to ask.** The whole finding above surfaced
  because an operator asked twice. Once is attention; twice is luck.
- **Branch retirement — the other half of the lifecycle.** Saving work created 36
  branches and 160 rescue tags in one afternoon; nothing knows when any of them
  may be released. The question is *derivable*, not a judgement call: a story
  branch is retirable when its content is in `main` **by patch-id**, its run is
  concluded, and its story is `done` with a merge sha. Doing that by hand across
  62 branches is 62 chances to be wrong; writing it once is zero.

  Two prefixes are never candidates: `loop/*` is how the fleet works, and
  `rescue/*` tags are the **only** reachability for commits `git gc` would
  otherwise collect — untagging them re-arms the very failure they record.

  **The first pruning run must explain itself.** For each branch it proposes to
  retire it names the evidence — the merge sha, the patch-id match, the concluded
  run — and it refuses on anything it cannot prove, rather than defaulting to
  delete. Dry-run by default, like `adopt`.

  It is the inverse of `unpushed-work-check` and shares its machinery: that one
  finds what must be saved, this finds what may be released. Both answer "where
  does this content exist?"; only the sign differs.

  Recorded because the classification is genuinely hard and looks easy. Two
  quick heuristics were tried and both were wrong — a three-dot diff mismeasures
  squash-merged branches, a two-dot diff mismeasures branches `main` has moved
  past. And the stakes are known: herald 1.2's 734 lines *looked* dead at six
  days old, and scribe 1.3's 1,102 lines showed as 8 insertions in a diffstat.

## What this is not

[[fidelity-enforcement]] asks *does anything go red when a contract and its
artifact disagree* — enforcement. This asks *does the artifact still exist at
all* — durability. They meet at Scribe's leg of the audit triad (a verdict
nobody can retrieve is not auditable), and they must not merge: a factory can
enforce every contract perfectly on work it then loses, and has.

## Kinships

[[pyforge-marshal]] (owns the loop, the run lifecycle, and the fix) ·
[[fidelity-enforcement]] (enforcement to this Dream's durability;
`unpushed-work-check` is the third detector with nowhere to run, which is that
Dream's missing observation plane) · [[pyforge-scribe]] (the record that must
outlive the worktree) · [[pyforge-steward]] (the estate the runs stand on — a
credible claim on this Dream if durability becomes an operations concern rather
than a loop-lifecycle one) · [[pyforge-charter]].

## Realization log

- **2026-07-31** — Dream seeded (operator call), after a push-everything sweep
  found six unpushed station branches, ~5,150 lines on `recover/*`, herald 1.2's
  734-line transport story unpushed for six days, 156 dangling commits, and
  marshal 1.8's 1,748 lines committed forty minutes earlier. Owner **marshal**
  by the run-lifecycle argument; Steward noted as the alternative if this is
  later judged an estate concern. Shipped the same day: `unpushed-work-check`
  (detector) and `loop-push-watch` (stopgap). The durable fix — the loop pushing
  at its own stage boundaries — is deliberately left to the pipeline rather than
  hand-written, which is why this file exists.
