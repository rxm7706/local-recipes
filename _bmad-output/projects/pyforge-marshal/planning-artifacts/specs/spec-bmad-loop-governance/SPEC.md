---
spec: pyforge-marshal
status: shipped
owner-dream: docs/dreams/pyforge-marshal.md
program: regenerable-factory (post-program backfill, user-directed)
surface:
  - .bmad-loop/**
surface-drift: exempt   # policy.toml model flips are per-story operational tuning on loop branches; the paper trail is run journals + loop commits
companions:
  - ../spec-multi-loop-isolation/SPEC.md                  # the concurrency harness kernel (Wave 0)
  - ../../../../../docs/specs/bmad-loop-adoption.md       # adopted: the adoption effort (legacy Tier-1, in force)
  - ../../../../../docs/dreams/pyforge-marshal.md         # adopted: the Dream (doctrine + frontier)
open_questions: []
---

# SPEC — Marshal (graduated-autonomy loop orchestration, as shipped)

## Why

Unattended development a human can trust: autonomy as a gradient, not a leap —
specs in, validated code out, every run visible, everything the agent cannot
safely decide escalated instead of guessed. This kernel binds the shipped
Marshal machinery into the governance map; the Dream carries the doctrine, the
adopted companions carry the harness and adoption detail. Owner: Marshal.

## Capabilities

- **CAP-1 — gated story loops.** Intent: bmad-loop + bmad-dev-auto drive each
  story dev → multi-lens review → verify → merge under `per-story-spec-approval`
  gates, with escalation pausing the run. Success: stories merge with the
  `Merge bmad-loop/<run>/<story>` subject only after an approved spec and a
  green deterministic verify; escalations pause rather than proceed (proven
  across atlas 32/32, warden 26+ stories incl. today's 6.3/6.5).
- **CAP-2 — concurrent loop homes.** Intent: loops for different projects run
  simultaneously via per-loop worktrees with single-sourced Tier-3 state (the
  adopted multi-loop-isolation kernel). Success: its CAP-3 isolation check;
  live proof = the warden wave running beside main-checkout work today.
- **CAP-3 — model tiering as policy.** Intent: `.bmad-loop/policy.toml`
  `[adapter.*]` selects the model per role — mechanical default (sonnet),
  deliberate flips to opus for HARD stories, committed on the loop branch as
  paper trail. Success: each flip is a loop-branch commit naming the story
  class; verify commands stay project-scoped.
- **CAP-4 — every run visible.** Intent: run journals + sprint feeds +
  merge-subject conventions feed the program console (factory-console kernel),
  so progress is derivable from ledgers, never hand-trusted. Success: the
  console's per-project done-detection keys on the loop's merge subjects;
  sprint feeds flip from journal events.

## Constraints

- The harness is the unit of governance and is NOT a skill (execution
  doctrine); skills (bmad-dev-auto, bmad-review lenses) are the unit of
  execution inside it.
- Resumes and long loop commands run BACKGROUNDED (foreground timeouts killed
  a run mid-review once — the 3.1 incident).
- Loop merges publish to `main` via push/batch-PR; `main` is never checked
  out twice (multi-loop-isolation constraint).
- First session in a new loop home requires a one-time CLI folder-trust
  acceptance (documented in the harness provisioner).

## Non-goals

- The `marshal` CLI as a named product (Dream frontier, unbuilt).
- Formal L1–L5 story-mode labeling; fleet-level resource budgets (frontier).
- bmad-loop's own internals (vendor package, pixi-pinned).

## Success signal

A story travels Dream-side spec → gated loop → merged code with zero
ungoverned steps, while a second loop runs concurrently — demonstrated live
by the 2026-07-23/24 warden resume (6.3, 6.5) riding the exact machinery this
kernel describes.
