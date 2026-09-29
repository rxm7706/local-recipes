---
title: "Story 6-1: Profile `doctor check` and bring it inside its budget"
type: "change"
created: "2026-08-08"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-09"
---

<!-- RECOVERED 2026-08-09 Tier 3 (epics.md-derived Intent + ACs). No session transcript,
     bmad-loop worktree snapshot, or Tier-3 draft survived — this story landed via hand-driven
     PR #323, not a bmad-loop run, so no spec was ever drafted to promote. Regenerated from
     epics.md (which carries a complete, numbers-bearing Outcome section) plus its merged-PR
     Delivery Record, per CLAUDE.md's recovery priority order. -->

## Intent

As the operator, I want `doctor check` **measured** and inside SM-C1 before anything is
added to it, so that Charter §6 compliance is not bought by breaking Doctor's own
performance contract. FR-15; SM-C1.

**Why first.** `DW-DOCTOR-2026-08-08-1` records three timed iterations — 6.92s / 7.04s /
6.73s against 5.0s — and states the cost is **unattributed**: warden's `--version`
subprocesses, the atlas MCP/CLI fallbacks, and the env-hygiene walk were all candidates.
Charter §6 forbids the judged station relaxing its own threshold, so the budget is fixed
and the work must meet it.

**Surface:** `sources/*.py`, `cli/check.py`, `tests/`

## Acceptance Criteria

- **Given** the monorepo root, **When** `doctor check` is profiled per-source, **Then** the
  cost of each gather is **attributed and recorded, not estimated**.
- **And** `test_doctor_check_completes_within_the_five_second_budget` passes on `main`.
- **And** the budget itself is unchanged — **no re-thresholding**.

## Delivery Record

Merged via PR #323 (`d8fec9449a`), commit `d2e5ddc024` — *"doctor 6.1: the profile found a
truncated scan, not a slow one"*, 2026-08-08T17:53:14-05:00. 8 files, +219/−30, principally
`src/pyforge/doctor/checks/env_hygiene.py` (+42) and
`tests/unit/test_checks_env_hygiene.py` (+46).

## Outcome

The profile **cleared two of the three suspects** and found the real defect was not
slowness at all.

- warden's engines gather: **0.18s**
- the atlas fallbacks: **not on `check`'s path at all** — they belong to `monitor`
- env-hygiene: **97%** — 7.73s of parse across 3,721 files

Of that, **6.43s / 3,216 files was the gitignored 590 MB `build_artifacts/`** (third-party
conda sources and test envs). That directory sorts before `docs`/`recipes`/`scripts`/`src`,
so the walk spent its **entire entry cap** inside it and reached **zero** first-party files
— all 609 under `src/` and `scripts/` were unscanned, **including the scanner's own
module**.

So the headline number was hiding a correctness bug: the check was not slow, it was
**truncated**, and it had been reporting clean on a corpus it had never read. Pruning
build-output/tool-cache directory names cut the gather to ~3.2s **and raised** first-party
coverage 0 → 602 files, surfacing a third real finding that had been invisible.

The 5.0s budget is untouched — no re-thresholding, per the AC.

**Residual:** the walk is still `incomplete` (`SDKs/` is 39,379 of 52,968 entries and holds
no Python) — split out as `DW-DOCTOR-2026-08-08-2`, because it needs a design decision, not
a bigger constant.

## Notes

This story created the headroom every later Epic 6 story spends: 5.2's durability gather
(~0.04s) and each of 6.4–6.7's ported sources land inside a budget that was in breach
before this ran. It is also the epic's cleanest instance of a measurement contradicting the
hypothesis that prompted it — the deferred-work entry assumed a slow check, and the profile
found a blind one.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `ca254233ed` (2026-08-14, "Merge branch 'bmad-loop/20260813-094917-9bba/6-11-the-classifier-recognizes-a-spike-report' into land/doctor-6"). Ledger row `6-1-profile-doctor-check-and-bring-it-inside-its-budget: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-drift-new-artifact-shape/.memlog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-drift-new-artifact-shape/SPEC.md`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
