---
spec: loop-home-fleet-refresh
status: draft
owner-dream: docs/dreams/loop-home-fleet-refresh.md
surface: []          # frontier — likely extends src/shared/packages/pyforge-marshal/**; a decomposition pass will claim it
companions: []
sources:
  - ../../../../../../docs/dreams/loop-home-fleet-refresh.md
  - ../../research/technical-marshal-orchestration-refresh-2026-08-08.md
  - ../../research/domain-marshal-orchestration-2026-08-08.md
open_questions:
  - "Q1 — delivery shape undecided: a `marshal` CLI verb (new `marshal refresh`, or folded into `marshal homes`), a scheduled CI/cron job, or both (verb as the primitive, schedule as the trigger). The 2026-08-08 technical research recommends folding the push half into an existing supervisor duty (classify_push_triggers already fires on the done-phase boundary) rather than a new product."
  - "Q2 — durable record for the 'already verified redundant' divergence verdict: where does it live (journal entry, ledger, marker file in the loop-home) so the same stale-history archaeology (doctor/herald/mason/scribe/steward, re-derived twice on 2026-08-03) is never re-run for the same commit set?"
  - "Q3 — overlap with FR-61 stage-boundary push and loop-push-watch: does this Spec's push step subsume the existing watcher for the refresh path, or only complement it?"
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/loop-home-fleet-refresh.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# SPEC — loop-home fleet refresh

## Why

Keeping every station loop-home (`~/.bmad-loops/pyforge-*`, 9 today) current with `main` is a
hand-run, two-step ritual repeated after nearly every PR merge. Lived again on 2026-08-08: all
9 loop-home worktrees were found **227 commits stale**, pinned at `e7762f5b3f` (PR #265,
predating the entire session), and refreshed by hand — per worktree, `git fetch origin main &&
git merge --ff-only origin/main`, then `git push origin loop/pyforge-<slug>`, then a *second*
separately-remembered step, `pixi run -e pyforge-marshal marshal config --project <slug>
--write-harness-policy <dir>`, because `.bmad-loop/policy.toml` is untracked and leaves `main`
with every refresh (PR #139 incident). The Dream records the same ritual run twice in one
session on 2026-08-03, including re-deriving the identical stale-divergence verdict for the
same 5 stations both times. Nothing detects the staleness, nothing performs the safe part of
the fix, and nothing prompts for the policy re-render — three mechanical steps × N homes,
every time, all judgment-free in the common case.

## Capabilities

- **CAP-1 — fleet-wide staleness detection.**
  - **intent:** For every discovered loop-home (derived from the filesystem/`marshal homes`
    enumeration, never a hardcoded station list), report commits-behind `origin/main` on its
    `loop/pyforge-<slug>` root checkout, plus whether its `.bmad-loop/policy.toml` is missing
    or stale — one row per home, readable at a glance.
  - **success:** run against today's fleet state (all homes pinned 227 commits back) and every
    home is reported stale with its exact commits-behind count; run again after a refresh and
    every home reports clean. A home added to the fleet tomorrow appears without a code change.

- **CAP-2 — automated fast-forward and push, with a clean-worktree safety check.**
  - **intent:** For each stale home whose root checkout passes the safety checks (working tree
    clean per `git status --short`, no live run on that root checkout), perform exactly the
    manual sequence: fetch `origin/main`, `git merge --ff-only origin/main`, push the updated
    `loop/pyforge-<slug>` branch to origin. Homes that fail a check are **reported, never
    touched**, per the Dream's three-case taxonomy: live session → skipped and named; genuine
    divergence (unique commits not reachable from `main`) → reported, left alone; stale/
    redundant divergence (unique commits already squash-merged onto `main`) → reported with
    evidence (which commit, which PR it matches), force-push left to the human.
  - **success:** run against 9 clean-but-stale homes and all 9 end fast-forwarded and pushed,
    matching the 2026-08-08 manual pass byte-for-byte; run against a home with uncommitted
    changes, a diverged home, or a home with an active run, and that home is untouched with
    the reason named in the output.

- **CAP-3 — policy re-render as a checked step of the same refresh.**
  - **intent:** After a home's fast-forward (or when CAP-1 flags its policy file
    missing/stale), re-render `.bmad-loop/policy.toml` via the existing composition path
    (`marshal config --project <slug> --write-harness-policy <dir>`) — never a reimplemented
    renderer. The refresh does not report a home as clean while its policy file is absent or
    behind the composed policy sources.
  - **success:** delete a home's `policy.toml` and run the refresh: the file is back and
    matches what `marshal config` composes for that station; a home refreshed by CAP-2 never
    ends the run with a missing or stale policy file.

## Constraints

- **Never force-push, never discard work.** The tool fast-forwards only (`--ff-only`), and
  only when `git status --short` on that home's root checkout is clean — mirroring the manual
  process's own safety check. Uncommitted work, stashes, and divergent commits are never
  deleted, reset, or overwritten; the stale-redundant force-push case stays a human decision
  (Dream § Constraints, Git Safety Protocol), with the tool's job being evidence, not action.
- **Never touch a home with a live run.** Detect a live tmux session (or an active run in
  `.bmad-loop/runs/*/state.json`) before acting on a root checkout, and distinguish the root
  checkout from per-story worktrees branched off it — updating the root is safe while a
  worktree-branch session is live; the root's own live session is not.
- **Derive the fleet, don't declare it.** Home discovery reuses `marshal homes` enumeration;
  no per-station list is hardcoded (`EXEMPLAR-STANDARD.md` provenance rule).
- **Reuse the existing policy renderer.** CAP-3 shells through / calls into the shipped
  `marshal config --write-harness-policy` path (AD-10/AD-16 composition); it never composes
  policy itself.

## Non-goals

- **Not a general git-sync tool.** Scoped to loop-home root checkouts and their
  `loop/pyforge-<slug>` branches only; it does not sync arbitrary branches, worktrees, or
  repos, and knows nothing about trees outside the fleet.
- **Not `marshal land`.** Opening/merging a story's landing PR into `main` is Story 4.8's
  contract; this Spec is the opposite direction (main → loop-home) plus the fleet push.
- **Not the upstream fix.** Making bmad-loop itself push at its own stage boundaries is named
  by `loop_push_watch.py`'s docstring as the durable upstream fix — out of this repo's hands
  and out of this contract.
- **Not an unattended force-pusher.** No mode, flag, or schedule ever makes the
  stale-redundant-divergence force-push automatic.

## Success signal

The next time `main` moves, no human runs the fetch/ff/push/re-render ritual by hand across
the fleet: one invocation (or its scheduled trigger) reports every home's staleness, brings
every clean home current and pushed with its policy file rendered, and names — with evidence,
untouched — exactly the homes that need a human decision. The 2026-08-08 session's 9-home ×
2-step manual pass, and the 2026-08-03 session's twice-re-derived divergence triage, are the
last of their kind.

## Open Questions

- Q1 — delivery shape undecided: a `marshal` CLI verb (new `marshal refresh`, or folded into
  `marshal homes`), a scheduled CI/cron job, or both (verb as the primitive, schedule as the
  trigger). The 2026-08-08 technical research recommends folding the push half into an
  existing supervisor duty (`classify_push_triggers` already fires on the done-phase boundary)
  rather than a new product.
- Q2 — durable record for the "already verified redundant" divergence verdict: where does it
  live (journal entry, ledger, marker file in the loop-home) so the same stale-history
  archaeology (doctor/herald/mason/scribe/steward, re-derived twice on 2026-08-03) is never
  re-run for the same commit set?
- Q3 — overlap with FR-61 stage-boundary push and `loop-push-watch`: does this Spec's push
  step subsume the existing watcher for the refresh path, or only complement it?
