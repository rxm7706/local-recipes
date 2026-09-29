---
title: "Story 8.6: DW-FU-8-4 closes — the collision-abort redesign, plus the parsing gap it surfaced"
type: "bug"
created: "2026-08-28"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-09-18"
---

<!-- MINTED 2026-09-18 from epics.md Intent + ACs (Story 8.6). No Tier-3 draft was
     present under planning-artifacts/specs/ as spec-<ledger-key>.md. -->

## Intent

Close `DW-FU-8-4`: once a project promotes once, the whole-batch-abort guard fires forever
on the old, already-promoted orphan's own now-expected re-collision, permanently blocking
any genuinely new orphan added later. Completes the real fleet-wide `--fix` run Epic 8's
closing note left out of scope. Live-confirmed against all 8 fleet projects at Story 8.4's
landing — every one would abort outright if `--fix` were run unscoped.

A second, independent parsing bug surfaces on the same real run: `_consume_bulleted_field_block`
truncates a header-owned entry whose fields are every one its own dashed bullet (no indented
continuation lines) at the second bullet, because any `_BULLET_START_RE` match is treated as
a block-ending sibling — even one whose own key is a recognized field of the same entry
(doctor's `DW-FU-12-4/5/5-2`, steward's `DW-FU-11-4`).

**FR/AD:** FR-15 (`spec-deferred-work-visibility`, CAP-12)
**Deps:** S-8.4, S-8.5
**Surface:** `scripts/deferred_work_promote.py` (`_BatchValidation`, `_validate_batch`,
`_promote_project`), `pyforge-doctor` `sources/chain.py` (`_consume_bulleted_field_block`),
`tests/scripts/test_deferred_work_promote.py`, `tests/unit/test_sources_chain_deferred_work.py`

## Acceptance Criteria

- **Given** a project's orphan batch where some entries' content already reached the tracked
  ledger by another path (an old, already-promoted orphan re-colliding against its own
  tracked twin), **When** `--fix` runs, **Then** those entries are silently excluded from
  the write (never re-promoted) while the rest of a clean batch — including a genuinely new
  orphan added since the last run — still promotes; any other collision (duplicate id, blank
  summary, a genuinely new duplicate summary within the batch) still hard-aborts the whole
  batch, unchanged.
- **Given** the fixed tool run for real, **When** it processes doctor's/steward's live
  Tier-3 files, **Then** the header-owned dashed-bullet truncation is fixed:
  `entry_id is not None` (header-owned) now checks `_KNOWN_FIELD_KEYS` first — a known-keyed
  dashed bullet is a continuation, not a new sibling; headerless blocks (`entry_id is None`)
  are untouched.

## Delivery Record

From `epics.md` Outcome (2026-08-28). Both fixes landed together. Adversarial review found
no HIGH/MEDIUM defects; `already_minted` is populated before validation; empty `to_write`
short-circuits before race-check/write/baseline-restamp. Fleet-wide `--fix` (clean, no
concurrent agents): doctor +72, herald +12, marshal +196, mason +21, steward +72;
atlas/scribe/warden clean no-ops.

**Bounded:** `deferred-work-check` combined `tier3-only-deferral`/`tier3-entry-unidentified`
count drops from 111 (post-8.5) to 70 — remaining are already-identified Tier-3 entries
never copied to a tracked ledger (`deferred_work_promote.py` orphan-only scope). Not claimed
resolved here.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station verify
  suite; contract mint, no new per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `27e7f340f6` (2026-08-28, "fix(doctor 8.6): DW-FU-8-4 closes -- fleet-wide deferred-work promotion unblocked"). Ledger row `8-6-dw-fu-8-4-closes-the-collision-abort-redesign-plus-the-parsing-gap-it-surfaced: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/SPEC.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`, `scripts/.deferred-work-baseline.json`, `scripts/deferred_work_promote.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` (+1 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
