---
spec: bmad-loop-governance
status: shipped
owner-dream: docs/dreams/pyforge-marshal.md
program: regenerable-factory (post-program backfill, user-directed)
surface:
  - .bmad-loop/**
surface-drift: exempt   # policy.toml model flips are per-story operational tuning on loop branches; the paper trail is run journals + loop commits
companions:
  - ../spec-multi-loop-isolation/SPEC.md                  # the concurrency harness kernel (Wave 0)
  - ../../../../../../docs/specs/bmad-loop-adoption.md       # adopted: the adoption effort (legacy Tier-1, in force)
  - ../../../../../../docs/dreams/pyforge-marshal.md         # adopted: the Dream (doctrine + frontier)
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
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `a0aba94b0a`: `git log --oneline --all --grep='^Merge bmad-loop/'` shows the exact subject convention live and recent (e.g. `57c001c9d7c Merge bmad-loop/20260910-100021-1dbc/15-2-... into loop/pyforge-mason (bmad-loop)`, dated 2026-09-10). Escalation-pause behavior is exercised by `test_dispatch.py`/`test_dispatch_land_heal.py` among others under `src/shared/packages/pyforge-marshal/tests/unit/`.
- **CAP-2 — concurrent loop homes.** Intent: loops for different projects run
  simultaneously via per-loop worktrees with single-sourced Tier-3 state (the
  adopted multi-loop-isolation kernel). Success: its CAP-3 isolation check;
  live proof = the warden wave running beside main-checkout work today.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `a0aba94b0a`: `spec-multi-loop-isolation` CAP-3 exists (`bmad-loop-worktree --verify <slug-a> <slug-b>`, real executable at `scripts/bmad-loop-worktree`); 8 populated loop homes coexist live under `~/.bmad-loops/` right now (atlas/doctor/herald/marshal/mason/scribe/steward/warden), each with its own `.bmad-loop/policy.toml`.
- **CAP-3 — model tiering as policy.** Intent: `.bmad-loop/policy.toml`
  `[adapter.*]` selects the model per role — mechanical default (sonnet),
  deliberate flips to opus for HARD stories, committed on the loop branch as
  paper trail. Success: each flip is a loop-branch commit naming the story
  class; verify commands stay project-scoped.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `a0aba94b0a`: `~/.bmad-loops/pyforge-marshal/.bmad-loop/policy.toml`'s live `[adapter]` block carries `model = "sonnet"` (mechanical default) with an inline dated comment recording an opus flip-and-revert; `git log -- .bmad-loop/policy.toml` in that loop home shows real committed policy-flip history (e.g. `6ec077455a1 bmad-loop policy: unattended runs — gates.mode "per-story-spec-approval" -> "none"`).
- **CAP-4 — every run visible.** Intent: run journals + sprint feeds +
  merge-subject conventions feed the program console (factory-console kernel),
  so progress is derivable from ledgers, never hand-trusted. Success: the
  console's per-project done-detection keys on the loop's merge subjects;
  sprint feeds flip from journal events.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `a0aba94b0a`: `merge_subject`/`MERGE_SUBJECT` handling is real, live code in `core/dispatch_landing.py`, `dispatch_land.py`, `core/promotion.py`, `core/identity.py`, `dispatch_supervisor/__main__.py`, `adapters/harness_bmadloop.py` — not a paper claim. `fleet-picture`'s own per-station tables (this session's own reports) are the running proof sprint feeds are ledger-derived.

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
