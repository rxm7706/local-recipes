---
spec: bmad-loop-baseline-drift
status: shipped
updated: "2026-09-09"
owner-dream: docs/dreams/bmad-loop-baseline-drift.md
surface:
  - pixi.toml
  - scripts/bmad_loop_baseline_drift_check.py
  - docs/dreams/bmad-loop-baseline-drift.md
sources:
  - ../../../../../../docs/dreams/bmad-loop-baseline-drift.md
open_questions: []
  # ANSWERED BY THE IMPLEMENTATION, retired 2026-09-09 (fleet-readiness batch Class B, row mars-A):
  # detection posture -> POST-HOC JOURNAL-SIGNATURE MATCH ONLY (no live mid-flight comparison);
  # actuation -> REPORT-ONLY (exit 1 plus `--json`), no pause/escalate from outside the package.
  # Full text with answers in § Open questions -- closed 2026-09-09.
decisions:
  - "Detector home (Story 20.1): scripts/bmad_loop_baseline_drift_check.py via baseline-drift-check pixi task (loop-stall-check precedent), not pyforge.doctor.sources."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/bmad-loop-baseline-drift.md` is listed in
> `sources:` for narrative rationale — and the drafted upstream issue text — this contract
> intentionally omits.

# A story's orchestrator-recorded baseline can never *silently* drift out from under its own worktree

## Why

`bmad-loop 0.9.0` mounts each story in an isolated git worktree and stamps `task.baseline_commit`
once when the dev phase opens (`engine.py:1707`, from the worktree's own HEAD; the comment near
engine.py:1229 says it stays "fixed across the whole dev retry loop"). In practice it drifts to the
shared `loop/<slug>` branch's later tip while a dev session is still running. `_verify_shared_gates`
(`verify.py:1211-1235`) then compares the session's own — correct — `baseline_revision` against the
drifted value, mismatches, and permanently defers real, reviewed work (`spec baseline ... does not
match orchestrator-recorded baseline ...`) while the dispatcher silently opens the next story's
worktree (journal: `story-deferred` → `worktree-opened story=10-1`). Hit **five times in one
session** (2026-08-14): marshal 8.1–9.5 (9 stories, ~8h), 9.6, 10.1, and mason 3.6–3.9 plus 3.8 —
each recovered only by manual git archaeology over `attempt-preserve/*` / `failed/*/changes.patch`
(PRs #482–#484), and 9.6 fired on the very next story after the #482 recovery landed on the same
live run.

The package is not ours to fix: `bmad_loop` ships git-pinned via pixi (pixi.toml:1058,
`bmad-code-org/bmad-loop`); editing site-packages is wiped on the next `pixi install` and would be
a live edit under two loops importing it mid-run. But the fix shape is proven inside the package —
the resolve path (`runs.py:872-908`) re-stamps `task.baseline_commit` AND the spec's
`baseline_revision` together with comments naming exactly this hazard, and `verify.py:1220-1235`'s
`allow_ancestor_baseline` carve-out already accepts an ancestor baseline for the re-arm case
(#161). What this repo can own is the posture `story-status-check` / `loop-stall-check` already
take toward bmad-loop blind spots: the real fix belongs upstream; a local detector is the
containment. The sibling loss mode — honest work stranded for other reasons — is
`spec-bmad-loop-intent-gap-work-preservation` (authored in parallel); they share only the
upstream-report path.

## Capabilities

- **CAP-1**
  - **intent:** A Marshal-side detector at the adapter seam — reading only feeds `bmad_loop`
    itself writes (`journal.jsonl`, `state.json`, `attempt-preserve/*` refs, `failed/*/
    changes.patch`), never importing or editing the package — recognizes the baseline-drift
    signature: a defer whose reason matches `spec baseline ... does not match orchestrator-recorded
    baseline`, and/or a recorded `task.baseline_commit` that is not the basis encoded in the
    story's own preserve-ref/worktree.
  - **success:** Replaying run `20260813-094919-bfcb`'s journal (story 9-6) fires the detector
    naming the story, both baselines (`523e938c7978` real vs `26102ea12c6d` drifted), and preserve
    ref `attempt-preserve/20260813-094919-bfcb-523e938c`; a clean run's feeds yield no finding.
- **CAP-2**
  - **intent:** This defer reason can no longer pass silently — loud-defer containment. The
    detector exits non-zero and the finding surfaces where the operator already looks
    (`fleet-picture`'s ATTENTION block or equivalent), stating the recovery inputs: story, run,
    preserved ref/patch, drifted-vs-real baselines — recovery becomes a named next action, not a
    per-occurrence archaeology session. Extending `allow_ancestor_baseline`'s carve-out to the
    plain-retry path is upstream's to land (runs.py's resolve-path re-stamp proves the shape); the
    local analog is detection + loud defer, never a quiet auto-land.
  - **success:** A future occurrence is surfaced by the containment within its watch window with
    recovery inputs named — not discovered via a dashboard-accuracy audit, the way this Dream was
    found; a run carrying such a defer cannot read healthy in the containment's output.
- **CAP-3**
  - **intent:** The drafted upstream issue already in the Dream (lines ~125–201: journal timeline,
    `engine.py:1707` / `runs.py:872-908` / `verify.py:1220-1235` citations, impact) is filed
    against `bmad-code-org/bmad-loop` — strictly gated on the Dream's two backlog preconditions:
    (1) confirm repo access / org relationship (issue vs PR vs discussion); (2) duplicate-search
    first, since the resolve-path comments suggest maintainer awareness of an adjacent shape.
  - **success:** Both gates recorded as checked; then either the issue is filed (URL appended to
    the Dream's Realization log) or a duplicate found and linked instead — either outcome recorded.
    Until the gates clear, the draft stays unfiled by design.

## Constraints

- **HARD:** no in-place edits to the installed `bmad_loop` package — git-pinned pixi dependency,
  actively imported by live loops, wiped on `pixi install`. Every shipped capability lives on this
  repo's side of the seam.
- **Always:** the containment must not paper over the defer — either the race becomes impossible
  (upstream's job) or the defer is immediately loud and recoverable; quietly easing recovery while
  the silent-burned-compute mode survives fails this spec (Dream Constraints, verbatim).
- **Always:** the detector observes runtime feeds (`~/.bmad-loops`, run homes), so it is
  scope=runtime like `loop-stall-check` — excluded from `detectors-ci` per the existing rule that
  CI runners lack that observation plane.

## Non-goals

- **Not** a rewrite of `bmad-loop`'s concurrency/worktree model — the narrow baseline-drift bug only.
- **Not** retroactive cleanup: all known occurrences are already recovered (PRs #482–#484).
- **Not** the sibling problem: work stranded by other loss modes belongs to
  `spec-bmad-loop-intent-gap-work-preservation`; the shared upstream-report path (CAP-3's gates
  apply to a coordinated filing) is referenced, not absorbed.
- **Not** the upstream code fix itself (plain-retry ancestor carve-out or auto-path re-stamp) —
  this spec ships the evidence and the gated report, not the patch.

## Success signal

Today this failure mode is invisible until an operator audits the dashboard — five occurrences in
one session, three hand-recoveries. After this spec: replaying the 9-6 journal trips CAP-1 with
exact story/baselines/refs named; a live recurrence surfaces loudly in the ATTENTION plane instead
of dispatching on in silence (CAP-2); the upstream track is filed or explicitly gated-out, outcome
recorded in the Dream's Realization log (CAP-3). Manual salvage stops being the discovery mechanism.

## Open questions — closed 2026-09-09

Both answered by Story 20.1–20.3's implementation; question text preserved.

- ~~"Detector home (a story-level design decision): a `scripts/*.py` invoked directly
  (loop-stall-check precedent) or a `pyforge.doctor.sources` module behind the dispatcher
  (story-status-check precedent)."~~ **CLOSED at Story 20.1:**
  `scripts/bmad_loop_baseline_drift_check.py` via the `baseline-drift-check` pixi task
  (`pixi.toml:932`) — the loop-stall-check precedent, not `pyforge.doctor.sources`.
- ~~"Detection posture: post-hoc journal-signature match only, or also a live mid-flight
  comparison of `task.baseline_commit` against the worktree's real basis — the latter catches
  drift BEFORE a deferred attempt burns hours."~~ **CLOSED: post-hoc journal-signature match
  only.**
- ~~"Whether pause/escalate can be actuated from outside the package (a bmad-loop CLI surface vs
  report-only) — unsolicited tmux send-keys is against standing policy, so actuation may reduce to
  loud reporting."~~ **CLOSED: report-only** — exit 1 plus `--json`, the loud defer surface
  `fleet-picture` reads. No actuation.

## Assumptions

- `status: shipped` (2026-09-09) — Epic 20 Stories 20.1–20.3 are `done`:
  `scripts/bmad_loop_baseline_drift_check.py` plus the `baseline-drift-check` pixi task
  (`pixi.toml:932`), the loud `--json` defer surface for `fleet-picture`, and the gated upstream
  filing (bmad-loop issue #701, `upstream-register.json` `baseline-commit-midflight-drift`).

## Residual (2026-09-09) — the observation plane is empty

The detector scans `~/.bmad-loops/<slug>/.bmad-loop/runs/` only
(`bmad_loop_baseline_drift_check.py:72`, `:142`). The estate's live engine is
`marshal factory dispatch`, whose journals live under
`_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/`, and the newest loop-home
run in any of the eight homes is 2026-08-22 (atlas). **The detector therefore exits 0 "OK" on an
EMPTY observation plane instead of reporting could-not-observe (`scope=runtime`, exit 2) — a false
green by this repo's own stated standard (`pixi.toml:1033`).** Re-pointing it at the dispatch plane
is marshal **Story 33.7**.
