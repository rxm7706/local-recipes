---
title: A story's orchestrator-recorded baseline can never drift out from under its own worktree
type: dream
owner: marshal
status: realized
---

# A story's orchestrator-recorded baseline can never drift out from under its own worktree

## The Dream

`bmad-loop` mounts each story in its own isolated git worktree and records `task.baseline_commit`
once, when that worktree opens — engine.py's own comment says it is meant to stay "fixed across
the whole dev retry loop." In practice it can silently drift to a later commit while a dev session
is still running, so a story that does completely real, reviewed, honest work gets permanently
rejected by its own verify gate (`spec baseline ... does not match orchestrator-recorded
baseline ...`) and deferred — with the run then dispatching the *next* story rather than pausing
or escalating. The dream is a fix (or, short of that, a durable containment) that makes this class
of failure impossible, or at minimum loud and self-healing, instead of silently burning hours of
real compute per occurrence.

## What it looks like when real

- `task.baseline_commit`, once captured for a story's worktree, cannot be overwritten by anything
  outside that story's own dev-retry loop — whatever process/path currently mutates it out from
  under an in-flight sibling story either stops touching tasks it doesn't own, or explicitly
  rebases the affected worktree onto the new baseline (and re-stamps the spec's `baseline_revision`
  to match) rather than leaving the two to silently diverge.
- On a genuine, unavoidable divergence (e.g. an operator's own out-of-band recovery advancing the
  shared branch — exactly what PR #482 did to 9.6), the verify gate treats an *ancestor* baseline
  the same way `_verify_shared_gates`'s existing `allow_ancestor_baseline` carve-out already does
  for the re-arm path (verify.py:1220-1235) — landing the honest work instead of discarding it.
- A defer for this specific reason is loud, not silent: it should escalate/pause rather than let
  the dispatcher roll on to the next story, so `fleet-picture`'s ATTENTION block (or an equivalent)
  actually names it instead of the operator having to notice via a dashboard-accuracy audit, the
  way this Dream itself was discovered (2026-08-14).
- The existing manual recovery path (this repo's own `attempt-preserve/*` branch / `failed/*/
  changes.patch` salvage, performed by hand three times in one session — 8.1-9.5, then 9.6, then
  mason 3.6/3.7/3.9) becomes unnecessary for this specific failure mode, or at minimum scriptable
  instead of a multi-step manual git-archaeology procedure repeated per occurrence.

## What is real

- **`scm.keep_failed`'s auto-preserve safety net** (this repo's existing operational reliance) —
  every deferred story's real commits survive as an `attempt-preserve/<run>-<hash>` branch, or a
  raw `failed/<story>/changes.patch` when no such branch exists. This is what made every recovery
  this session possible; it is a safety net for the symptom, not a fix for the cause.
- **`runs.py`'s operator-driven `resolve`/re-arm path already knows this exact hazard** —
  `_resolve_escalation` (runs.py:872-908) explicitly re-stamps BOTH `task.baseline_commit` (from
  `state.project`'s live HEAD) AND the spec's `baseline_revision` together on a human-initiated
  re-drive, with comments naming precisely the failure this Dream is about ("without this, the
  re-driven step-04 would build its review diff... since the ORIGINAL pre-attempt sha, clawing
  back the very resolve-session commits the advance above just blessed"). The automatic retry path
  (`engine.py`'s `_dev_phase`/`_rollback_or_pause`) has no equivalent re-stamp.
- **`_verify_shared_gates`'s `allow_ancestor_baseline` carve-out** (verify.py:1220-1235) already
  treats an ancestor baseline as sound for the deferred-work-bundle re-arm case (#161) — the
  pattern this Dream wants extended to the plain-retry path already exists in the codebase for a
  sibling case.
- **A related, already-acknowledged-as-upstream containment exists**: `story-status-check`
  (pixi.toml, `docs/dreams/...` — "no story reads `done` in a sprint feed without having landed")
  is a DIFFERENT failure mode (dev self-marks done before review converges) with the exact same
  "the real fix belongs upstream in bmad-loop; this is the containment" framing this Dream's
  problem deserves too. `loop-stall-check` is a second precedent — a local detector containing an
  upstream bmad-loop blind spot (a session stalled at an interactive prompt reads healthy) rather
  than waiting for the upstream fix.
- **Two live, independently-confirmed occurrences in one session (2026-08-14)**: marshal's Epic 8/9
  batch (8.1-8.4, 9.1-9.5 — 9 stories, ~8 hours, PR #482) and mason's 3.6/3.7/3.9 (PR #483) both hit
  this exact signature. A THIRD occurrence — marshal 9.6 (PR #484) — happened on the very next story
  after the Epic 8/9 recovery landed, on the same live run, confirming this is not a one-off but a
  live, recurring hazard as long as `loop/pyforge-<slug>`'s tip keeps moving while sibling stories
  sit in-flight (multiple concurrent worker slots, or an out-of-band operator recovery like #482
  itself). Full per-occurrence evidence (journal excerpts, exact commit hashes, code-line citations)
  is recorded in `spec-pyforge-marshal`'s `.memlog.md`.
- **Installed version**: `bmad-loop 0.9.0` (`pixi.toml` pins `>=0.9.0`), source
  `https://github.com/bmad-code-org/bmad-loop`.

## Constraints

- **Cannot be fixed by editing the installed package in place.** `bmad_loop` ships via a
  pixi/conda-forge dependency (git-pinned upstream), not code this repo owns under `src/`; editing
  `.pixi/envs/*/site-packages/bmad_loop/` directly is wiped on the next `pixi install` and, more
  urgently, would be a live edit to a package TWO currently-running loops (marshal, mason) are
  actively importing and executing against mid-run — not something to do without stopping them
  first and confirming with the operator.
- **A local mitigation must not paper over the defer.** Whatever ships here should either make the
  underlying race genuinely impossible, or make the defer immediately loud and recoverable — not
  quietly reduce the manual-recovery burden while leaving the silent-hours-of-burned-compute
  failure mode intact.

## Non-goals

- **Not a rewrite of `bmad-loop`'s concurrency/worktree model.** The dream is the narrow baseline-
  drift bug, not a broader redesign of how the orchestrator manages parallel worker slots against
  one shared target branch.
- **Not retroactive cleanup of past occurrences.** The three known occurrences this session
  (8.1-9.5, 9.6, mason 3.6/3.7/3.9) are already recovered (PRs #482, #483, #484); this Dream is
  about preventing/containing the NEXT one.

## Backlog: what's needed to report this upstream

Per the operator's explicit 2026-08-14 request to track both an in-repo Dream/Spec AND a clear
path to reporting this upstream. Items 1–2 + filing completed 2026-08-23 (Story 20.3):

1. **Confirm repo access** — DONE 2026-08-23. Viewer `rxm7706` has `pull` only on
   `bmad-code-org/bmad-loop` (no push/triage/maintain). Issues enabled; Discussions disabled.
   Filing channel = **GitHub Issue** (not PR, not Discussion).
2. **Check for an existing issue first** — DONE 2026-08-23. Searched `baseline_commit`,
   orchestrator-recorded / mid-flight drift, `intent_gap` / `attempt-preserve` / `keep_failed`.
   No duplicate of mid-flight `task.baseline_commit` overwrite during an in-flight automatic
   retry, nor of intent-gap revert without preserve. Adjacent but distinct:
   [bmad-loop#640](https://github.com/bmad-code-org/bmad-loop/issues/640) (`rearm_escalation`
   advances task baseline without updating the spec's `baseline_revision`) — related shape on
   the *re-arm* path only.
3. **Package the evidence** — DONE 2026-08-23 (filed body includes journal timeline + source
   citations). This Dream's "What is real" section + `spec-pyforge-marshal`'s `.memlog.md`
   remain the in-repo archive.
4. **Minimal repro, if requested** — still open. The three live occurrences are entangled with
   this repo's multi-worktree fleet; an upstream-friendly minimal repro does not exist yet.
5. **Decide the interim mitigation independent of upstream's timeline** — in progress in-repo
   (Stories 20.1–20.2 shipped loud-defer containment; 20.4+ own intent-gap preservation). Never
   edit the installed `bmad_loop` package.

### Filed issue (was DRAFT — filed 2026-08-23)

**Upstream:** https://github.com/bmad-code-org/bmad-loop/issues/701

Prepared 2026-08-14; filed 2026-08-23 after gates 1–2 cleared (Story 20.3). Coordinated body also
carries Story 10.1 intent-gap evidence on the shared report path. Historical draft text retained
below for the paper trail:

> **Title:** `task.baseline_commit` can drift to a later commit while a story's dev session is
> still running, permanently failing its own verify gate
>
> **Body:**
>
> ### Summary
>
> A story's isolated-worktree `task.baseline_commit` is meant to stay fixed for its whole dev-retry
> loop (the comment at `engine.py` around line 1229 says so explicitly), captured once via
> `verify.rev_parse_head(self.workspace.root)` when the worktree opens (`engine.py:1707`). We
> observed it change to a *later* commit — the shared target branch's tip, many stories ahead —
> while a dev session was still mid-flight, with the story's own worktree never having moved.
> `_verify_shared_gates` (`verify.py:1211-1235`) then compares the dev session's own (correct)
> `baseline_revision` against the drifted `task.baseline_commit`, finds a mismatch, and the story
> is permanently deferred (`spec baseline ... does not match orchestrator-recorded baseline ...`)
> even though the completed attempt did real, reviewed, honest work. The run then dispatches the
> *next* story rather than pausing or escalating, so the failure is silent until an operator
> notices via other means.
>
> ### Evidence (one occurrence, full journal timeline)
>
> Run `20260813-094919-bfcb`, story `9-6-plan-and-action-types-repo-fingerprint-and-the-plan-builder`,
> `journal.jsonl`:
>
> ```
> worktree-opened      story=9-6  (branch/worktree created — baseline should be ~523e938c79 here)
> dev-decision  attempt=1  session_status=timeout  action=retry
> rollback-auto         baseline=26102ea12c6d...   <-- ALREADY drifted, ~3h after worktree-opened
> attempt-commits-preserved  ref=attempt-preserve/...-523e938c  count=124
> dev-decision  attempt=2  session_status=completed  action=defer
>   reason="spec baseline 523e938c7978 does not match orchestrator-recorded baseline 26102ea12c6d"
> story-deferred  reason=(same)
> worktree-opened  story=10-1  (dispatcher moves on)
> ```
>
> The worktree's own preserve-ref name (`attempt-preserve/20260813-094919-bfcb-523e938c`) confirms
> its real basis never moved past `523e938c79`. `task.baseline_commit` was already the later commit
> by the time `rollback-auto` fired after attempt 1's timeout — i.e. it drifted *during* attempt 1,
> not at any point our own code touched. Between those two commits, the shared target branch
> (`loop/pyforge-marshal`) had several sibling stories land (an operator-driven out-of-band
> recovery in our case, but plausibly any concurrent landing on the same branch).
>
> ### What we found in the source (`bmad-loop` 0.9.0)
>
> - `engine.py:1707` (`_dev_phase`) sets `task.baseline_commit` exactly once per dev-phase
>   invocation, from `self.workspace.root`'s HEAD — which is the per-story isolated worktree
>   (`self.workspace = unit.workspace` at `engine.py:622`, set before `drive()` runs). We could
>   not find, via static reading, the exact call site that overwrites it again mid-flight for an
>   already-open worktree; happy to help narrow this down further if useful.
> - `runs.py:872-908` (the operator-driven `resolve`/re-arm path) already handles an equivalent
>   hazard explicitly: it re-stamps BOTH `task.baseline_commit` (from `state.project`'s live HEAD)
>   AND the spec's `baseline_revision` together, with a comment naming precisely this failure
>   ("without this, the re-driven step-04 would build its review diff... clawing back the very
>   resolve-session commits the advance above just blessed"). This suggests the maintainers are
>   already aware of the *shape* of this problem for the re-arm path; we couldn't find the
>   equivalent protection on the automatic retry path.
> - `verify.py:1220-1235`'s `allow_ancestor_baseline` carve-out already treats an *ancestor*
>   baseline as sound for one specific case (#161, deferred-work-bundle re-arm). Extending that
>   carve-out (or an equivalent) to the plain-retry path looks like it would fix or at least
>   contain this.
>
> ### Impact
>
> Three occurrences in one session across two different projects (9 stories, ~8 hours; then this
> one story; then 3 more stories in a sibling project) — each required manual git archaeology
> (`attempt-preserve/*` branches, `failed/*/changes.patch`) to recover, since `scm.keep_failed`'s
> safety net preserved the work but nothing in the automatic path re-lands it.
>
> ### Environment
>
> `bmad-loop 0.9.0`, multi-worktree isolated mode, `branch_per` targeting a single shared
> `loop/<project>` branch across concurrently-scheduled stories.

## Kinships

[[pyforge-marshal]] (the estate; owns `bmad-loop` adoption per `docs/specs/bmad-loop-adoption.md`) ·
`spec-pyforge-marshal`'s `.memlog.md` (full per-occurrence journal evidence and code citations,
recorded during the 2026-08-14 recovery of 8.1-9.5, 9.6, and — via the mason project's own memlog —
3.6/3.7/3.9)

## Realization log

- **2026-08-14** — Dream captured. Surfaced during a dashboard-accuracy audit that found marshal
  story 9.6 showing `done` on the dashboard but `backlog` in the tracked ledger — investigating the
  mismatch uncovered a THIRD live occurrence of the same bug already recovered twice earlier in the
  same session (marshal 8.1-9.5 via PR #482, mason 3.6/3.7/3.9 via PR #483). Root-caused this
  occurrence against `bmad-loop`'s own journal.jsonl and installed source
  (`.pixi/envs/local-recipes/.../site-packages/bmad_loop/`), landed the recovered story (PR #484),
  then captured this Dream per the operator's explicit priority request — Dream + Spec in-repo, plus
  a tracked backlog of what reporting it upstream would require.
- **2026-08-14** — Spec authored (spec-bmad-loop-baseline-drift, pyforge-marshal) by the 2026-08-14
  dream-backlog audit: Marshal-side loud-defer containment + the gated upstream-report track. The
  drafted issue stays unfiled pending repo-access + duplicate-search.
- **2026-08-23** — Story 20.3 gated upstream filing: Gate (1) repo access → issue channel only
  (`pull`, no push; Discussions off); Gate (2) duplicate search → no match (adjacent #640 noted).
  Filed coordinated issue https://github.com/bmad-code-org/bmad-loop/issues/701 (baseline-drift +
  Story 10.1 intent-gap evidence). Registered in
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-register.json`
  (`baseline-commit-midflight-drift`). No edits to the installed `bmad_loop` package.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`.**
  Epic 20 Stories 20.1–20.3 are `done` and neither this Dream nor its Spec recorded it:
  `scripts/bmad_loop_baseline_drift_check.py` + the `baseline-drift-check` pixi task
  (`pixi.toml:932`), the loud `--json` defer surface for fleet-picture, and the gated upstream
  filing (bmad-loop issue #701, `upstream-register.json` `baseline-commit-midflight-drift`). Both
  open questions were answered by the implementation: post-hoc journal-signature match only, and
  report-only — exit 1 plus `--json`. Spec `ready` → `shipped`.
  **Residual carried forward:** the detector scans `~/.bmad-loops/<slug>/.bmad-loop/runs/` only
  (`bmad_loop_baseline_drift_check.py:72,142`) while the live engine is `marshal factory dispatch`,
  whose journals live under `_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/`;
  the newest loop-home run in any of the eight homes is 2026-08-22. It exits 0 "OK" on an empty
  observation plane instead of reporting could-not-observe — a false green by the repo's own
  standard (`pixi.toml:1033`). Re-pointed by marshal **Story 33.7**. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
