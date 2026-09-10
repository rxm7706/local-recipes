---
title: 'fleet-picture names a stale primary checkout, not just stale loop homes'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - scripts/fleet_picture.py
warnings: []
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** Marshal's unattended CAP-4 land path (`gate_mode: none`) can commit, push, open a PR, verify, and merge a story entirely on its own when nothing needs operator judgment. The operator's own primary checkout has no signal this happened and silently drifts behind `origin/main` — discovered live 2026-09-10 only because the operator happened to run an explicit `git fetch` + `rev-list --count`. `fleet_picture.py` already detects this exact class of staleness for loop homes (`loop_home_staleness()`), just not for the one checkout that matters most: the operator's own.

**Approach:** Add a small, symmetric `primary_checkout_staleness()` function using the same live-fetch-then-`rev-list --count` idiom as `loop_home_staleness()`, and surface it as its own ATTENTION line. Use a much lower threshold than loop homes' `STALE_BEHIND_THRESHOLD = 20` — any drift on the primary checkout is worth surfacing (it's where the next push/merge/worktree-creation happens), unlike a loop home which only matters right before its next spin.

## Boundaries & Constraints

**Always:** Live-fetch `origin/main` before measuring (a stale local remote-tracking ref would defeat the point, per `loop_home_staleness()`'s own docstring rationale). Degrade silently (skip, don't raise) on any fetch/rev-list failure — matches the existing fault-tolerant idiom used throughout this script's ATTENTION-block probes. Keep `fleet-picture` read-only and never-gating (always exits 0) — this is an informational line, not a new failure mode.

**Never:** Touch the loop-home check itself. Add a network call anywhere outside the existing ATTENTION-block try/except pattern. Make this check block or slow down the rest of the report on a hung network fetch (reuse the same `timeout=` values `loop_home_staleness()` already uses).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CURRENT | Primary checkout HEAD == origin/main after fetch | No ATTENTION line | N/A |
| BEHIND | Primary checkout N commits behind (N >= 1) | ATTENTION line naming N and prompting `git pull` | N/A |
| DETACHED_HEAD | Primary checkout has no current branch | No ATTENTION line (skip, same as loop-home's own detached-HEAD skip) | Silent skip |
| FETCH_FAILS | No network / no `origin` remote | No ATTENTION line, no crash | Falls into the existing `watch.append("could not check ...")` degrade path |

</intent-contract>

## Code Map

- `scripts/fleet_picture.py` — add `primary_checkout_staleness(repo: pathlib.Path = REPO, threshold: int = 1) -> int | None`, mirroring `loop_home_staleness()`'s three-subprocess-call shape (branch, fetch, rev-list) but for a single repo root, returning just the commit count (or `None` if under threshold / any failure)
- `scripts/fleet_picture.py` — wire it into the same ATTENTION-block section as the existing `for slug, branch, n in loop_home_staleness(): needs.append(...)` loop, with its own `try/except` following the established pattern
- `tests/scripts/test_fleet_picture_baseline_drift_attention.py` (or the sibling test file covering `loop_home_staleness`) — add unit coverage for the CURRENT/BEHIND/DETACHED_HEAD/FETCH_FAILS matrix above

## Tasks & Acceptance

**Execution:**
- `scripts/fleet_picture.py` — add `primary_checkout_staleness()` and wire its ATTENTION line — core feature
- test file — matrix tests for the new function (mock subprocess the same way existing `loop_home_staleness` tests do, if such tests exist; otherwise add a minimal fixture-based test)

**Acceptance Criteria:**
- Given the primary checkout is 3+ commits behind a live-fetched origin/main, when `fleet-picture` runs, then the ATTENTION block contains a line naming the exact commit count and suggesting `git pull`
- Given the primary checkout is current, when `fleet-picture` runs, then no such line appears
- Given a fetch failure, when `fleet-picture` runs, then the report still completes (exit 0) with no crash

## Spec Change Log

## Review Triage Log

## Auto Run Result

Status: done

**Summary:** Added `primary_checkout_staleness()` to `scripts/fleet_picture.py`, mirroring `loop_home_staleness()`'s live-fetch-then-`rev-list` idiom for the primary checkout itself, wired into the ATTENTION block with its own line and a lower threshold (1, vs. loop homes' 20).

**Files changed:**
- `scripts/fleet_picture.py` — new function + ATTENTION-block wiring
- `tests/scripts/test_fleet_picture_baseline_drift_attention.py` — 4 new tests (behind-count, current-silent, detached-HEAD-silent, missing-repo-silent) using real throwaway git repos
- `spec-20-12-…md` — story contract
- `sprint-status-ledger.yaml` — 20-12 → done

**Review:** Implementation verified directly against the spec's own I/O matrix; no separate review-loop pass for this single-file addition.

**Verification:** `pytest tests/scripts/test_fleet_picture_baseline_drift_attention.py` → 19 passed (15 pre-existing + 4 new). Confirmed the existing `test_main_attention_*` tests still pass unaffected — the blanket `subprocess.run` mock those tests already use makes the new probe resolve safely to `None` without any explicit stub needed.

**Residual risks:** None identified — informational-only addition to a read-only, never-gating report.

## Verification

**Commands:**
- `pixi run -e local-recipes fleet-picture` — live check: run once with the checkout intentionally left a few commits behind (or mock in a unit test) to confirm the new line appears
- `pixi run -e local-recipes python -m pytest tests/scripts/ -k fleet_picture -q` — new/existing tests pass
