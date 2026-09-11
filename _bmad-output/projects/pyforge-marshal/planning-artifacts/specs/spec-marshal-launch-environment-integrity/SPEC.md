---
id: SPEC-marshal-launch-environment-integrity
spec: marshal-launch-environment-integrity
status: shipped
updated: "2026-09-11"
owner-dream: docs/dreams/marshal-launch-environment-integrity.md
covers-dreams:
  - docs/dreams/marshal-launch-environment-integrity.md
companions: []
sources:
  - ../../../../../../docs/dreams/marshal-launch-environment-integrity.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to
> build, test, and validate. `sources:` is for traceability only — consult it for narrative
> rationale this contract intentionally omits.

# Marshal trusts the environment it launches into — until it silently doesn't

## Why

A single long recovery session (2026-09-10) hit five silent-success failure modes in
`factory dispatch`/`factory spin` — the tool's own reported verdict (`ok`, `clean`, `0 done`,
`STUCK`) gave no signal anything was wrong. Four were closed the same session by direct fixes
named in the Dream itself. The remaining three — no refusal on a duplicate `factory spin`
launch, no mid-session worktree checkpointing before a crash, and a crashed session
indistinguishable from a genuinely failed one to `factory drain` — were decomposed into this
Epic. **Retroactive Spec** (authored 2026-09-11): the Dream's own Realization log already
claimed `status: specified` and full decomposition into marshal Epic 34, but no dedicated Spec
file was ever produced — `dream-chain-check`'s INV-1 correctly flagged the gap. All four
capabilities below are already shipped; this Spec documents what was built, matching sibling
already-shipped specs' own retroactive-documentation convention.

## Capabilities

- **CAP-1** — `factory spin` refuses a second launch against a live loop home
  - **intent:** Reuse `cli/dispatch.py`'s `station_in_flight_conflict` check (a narrowed call,
    never a re-derived guard) so a second `factory spin <slug>` refuses before launching
    anything while a prior spin run for that slug is still live, naming the live run's id/pid.
  - **success:** A fixture reproduces the exact 2026-09-10 race (two spin calls six seconds
    apart) and asserts the second refuses. (Story 34.1.)
  - **verified:** landed via `local-recipes#1153` (merged 2026-09-10T11:59Z).

- **CAP-2** — A dispatch/spin session's worktree is checkpointed before it can be lost to a crash
  - **intent:** The supervisor's own poll loop commits a local-only `wip: <story>
    (auto-checkpoint)` commit — never pushed, never opens a PR — when uncommitted changes sit
    past an idle threshold, or on an explicit `factory checkpoint <slug>` call.
  - **success:** A fixture simulating a mid-session crash after the checkpoint fires asserts the
    worktree's uncommitted changes survive as a commit, not working-tree state a
    `git worktree remove --force` could destroy. (Story 34.2.)
  - **verified:** landed via `local-recipes#1158` (merged 2026-09-10T12:48Z; a same-day follow-up
    commit `b046a48` fixed a core import boundary and promoted the ledger to `done`). Live in
    continuous production use since — real `wip: <story> (auto-checkpoint)` commits exist for
    numerous stories across the fleet (21.7, 22.12, 49.4–49.7, 49.14, 16.4, confirmed via
    `git log --grep`), not just this story's own fixture.

- **CAP-3** — `factory drain` tells a crashed session apart from a genuinely failed one
  - **intent:** A blocked story whose last recorded verdict shows zero git progress and zero
    review/verify-cycle evidence classifies as **environment** rather than **story**; a
    sanctioned retry path clears only environment-classified blocks, never weakening
    `factory drain`'s existing never-auto-retried/never-forced-past guarantee for a genuine
    failure.
  - **success:** A fixture reproduces one of each (a crashed-before-any-progress run, a real
    verify failure) and asserts only the crashed one is eligible for the new retry path.
    (Story 34.3.)
  - **verified:** landed via commit `55153c8` ("Classify factory drain blocks as environment vs
    story failures"), merged to `main` as `dcda31b8cb` ("Merge 34-3 into main", 2026-09-10T14:08Z).

- **CAP-4** — The ATTENTION-block's own refused-verdict check gets the same test coverage its
  `station_state()` sibling has
  - **intent:** A dedicated fixture pins `fleet_picture.py`'s `main()` ATTENTION-block branch
    (mocking `subprocess.run` for the `marshal status --format json` call), matching the
    coverage `station_state()`'s own `fix/fleet-picture-stale-dispatch-verdict` fix already has.
  - **success:** A station with `dispatch_phase` set and a `refused` verdict produces the
    `dispatch verify REFUSED` ATTENTION line; the same refused verdict with `dispatch_phase=None`
    (a different engine live) produces no such line — the exact regression the fix guards
    against. Test-coverage-only, no behavior change. (Story 34.4.)
  - **verified:** landed via `local-recipes#1145` (merged 2026-09-10T10:13Z, minted the story) and
    merged to `main` as `02237d61b9` ("Merge 34-4 into main", 2026-09-10T14:24Z).

## Constraints

- Story 34.1 reuses `station_in_flight_conflict` as a narrowed call, never a re-derived guard —
  mirrors Epic 22/28's own "narrowed conflict, not a new one" precedent.
- Story 34.2's checkpoint commit is local-only — never pushed, never opens a PR; landing a story
  remains a human/operator-triggered act.
- Story 34.3 never weakens `factory drain`'s existing never-auto-retried/never-forced-past
  guarantee for a genuine story failure — only adds a way to tell an environment crash apart
  from one.

## Non-goals

- Not a rewrite of the dispatch/spin split, the Tier-3/ledger two-file design, or
  `promote_sprint_status.py`'s architecture — every fix works within the existing shape (the
  Dream's other four environment-integrity findings are closed directly by its own 2026-09-10
  work, not by this Epic).
- Not a general crash-recovery framework for every marshal subprocess — scope is the dev/review
  session a story's worktree lives in.

## Success signal

All four capabilities are live in `main`: a duplicate `factory spin` refuses with the live run's
id/pid named; a crashed session's worktree survives as an auto-checkpoint commit (confirmed by
real checkpoint commits across the fleet, not just a fixture); `factory drain` classifies a
crashed-before-progress block as environment and offers a sanctioned retry path distinct from a
genuine failure's permanent block; the ATTENTION-block's refused-verdict branch has the same
dedicated unit coverage its `station_state()` sibling already had.
