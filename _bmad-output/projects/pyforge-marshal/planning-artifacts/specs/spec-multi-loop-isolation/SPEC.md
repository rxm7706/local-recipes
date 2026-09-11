---
spec: multi-loop-isolation
status: shipped
owner-dream: docs/dreams/pyforge-marshal.md
program: regenerable-factory (Wave 0)
surface:
  - scripts/bmad-switch
  - scripts/bmad-loop-worktree
companions: []
sources:
  - ../../../../../../docs/dreams/pyforge-marshal.md
  - ../../../../../../docs/dreams/regenerable-factory.md
assumptions:
  - bmad-loop resolves its sprint feed and journals via the repo-relative
    implementation-artifacts path of its CWD, so the backlink makes the main
    checkout's store canonical for a loop worktree.
  - Loop agent sessions inherit BMAD_ACTIVE_PROJECT from the launching env.
open_questions: []
---

# SPEC — multi-loop isolation harness

## Why

Only one bmad-loop can run per checkout: the gitignored active-project marker
+ `_bmad-output` symlinks are per-working-tree global state, and two loop
homes would also fight over the tree's HEAD. This blocks running the
regenerable-factory backfill loop concurrently with the Warden 6.3 resume.
bmad-loop already isolates each *story* in a worktree; the missing layer is
one worktree per *loop home*.

## Capabilities

- **CAP-1 — worktree-aware `bmad-switch`.**
  Intent: run inside a linked worktree, where the gitignored Tier-3 target
  (`projects/<slug>/implementation-artifacts`) does not exist; auto-provision
  it as an absolute symlink back to the main checkout's canonical dir
  (creating the canonical dir if absent), then switch normally. Refuse to
  replace a real non-empty local dir. Marker + planning symlinks remain
  per-worktree.
  Success: `bmad-switch <slug>` succeeds in a fresh worktree; the worktree's
  `implementation-artifacts` realpath equals the main checkout's; the main
  checkout's own marker/symlinks are unchanged.
  **Verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): `scripts/bmad-switch::ensure_tier3_backlink` matches this CAP's contract line for line (creates the canonical dir if absent, symlinks back, refuses a real non-empty local dir with the exact quoted error text). Corroborated by live production use earlier this session, not a fresh synthetic run: `~/.bmad-loops/pyforge-marshal` and `~/.bmad-loops/pyforge-mason` are real linked worktrees this tool provisioned, both successfully read/merged/pushed against in this same session.

- **CAP-2 — `bmad-loop-worktree` provisioner.**
  Intent: `bmad-loop-worktree <slug>` creates (or reuses) a worktree on
  branch `loop/<slug>`, runs `bmad-switch <slug>` inside it, verifies, and
  prints the launch line (`cd <wt> && BMAD_ACTIVE_PROJECT=<slug> …`).
  `--remove` tears the worktree + branch down.
  Success: provisioning is idempotent; the printed line is directly runnable;
  `--remove` leaves `git worktree list` clean.
  **Verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): `home_path`/`provision` in `scripts/bmad-loop-worktree` create `~/.bmad-loops/<slug>` on branch `loop/<slug>` (or reuse it — `home.exists()` short-circuits to a plain re-`bmad-switch`, confirming idempotency by code inspection), matching this session's live loop-homes exactly. Did not exercise `--remove` live (out of scope for this sweep — no throwaway slug to safely tear down without touching real project state).

- **CAP-3 — isolation verification.**
  Intent: `bmad-loop-worktree --verify <slug-a> <slug-b>` asserts the two
  provisioned worktrees hold independent markers/symlinks, share canonical
  Tier-3 with the main checkout (realpath identity), and the main checkout's
  active project is untouched.
  Success: exit 0 on isolation; non-zero with a named finding on any
  cross-talk.
  **Verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep), CODE-LEVEL ONLY: `cmd_verify` (`scripts/bmad-loop-worktree:156`) checks exactly the three named invariants (marker identity, `planning-artifacts` symlink naming its own slug, Tier-3 realpath equal to canonical) plus main-checkout-untouched, returning 0/2 accordingly — matches the CAP text line for line. Deliberately NOT run live against real slugs this pass (the directive excludes touching `~/.bmad-loops/pyforge-marshal`/`pyforge-mason`, and `--verify` calls `provision()` which is not purely read-only); no dedicated automated test exists for this path (`tests/scripts/test_bmad_switch_hard_fail.py` covers `bmad-switch --current` drift detection, a different concern).

## Constraints

- Deterministic harness, not a skill (Marshal doctrine: what governs the
  agent is not authored by the agent). Stdlib-only Python in `scripts/`,
  matching `bmad-switch` style.
- No migration: canonical Tier-3 stays in the main checkout; worktrees only
  point back. Every consumer keeps the identical repo-relative path.
- Loop merges publish via `git push origin HEAD:main` (rebase/retry on
  non-FF); `main` is never checked out in a second tree.
- `BMAD_ACTIVE_PROJECT` is exported per loop env as belt-and-suspenders — it
  outranks the marker, but the hard-coded `planning_artifacts` key still
  resolves through the per-worktree symlinks, which stay load-bearing.

## Non-goals

- Fixing `planning_artifacts` composition upstream in bmad-method (tracked as
  Herald/upstream scope).
- Modifying bmad-loop itself.
- win-64 (bmad-loop is Linux/macOS; Windows via WSL).

## Success signal

`bmad-loop-worktree --verify` passes for two different slugs on one machine
with the main checkout untouched. Program-level proof: the regenerable-factory
backfill loop and the Warden 6.3 resume run concurrently to merged stories.
