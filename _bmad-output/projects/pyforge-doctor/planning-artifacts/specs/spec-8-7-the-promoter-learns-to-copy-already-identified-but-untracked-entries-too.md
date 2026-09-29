---
title: "Story 8.7: The promoter learns to copy already-identified-but-untracked entries too"
type: "feature"
created: "2026-08-28"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-09-18"
---

<!-- MINTED 2026-09-18 from epics.md Intent + ACs (Story 8.7). No Tier-3 draft was
     present under planning-artifacts/specs/ as spec-<ledger-key>.md. -->

## Intent

Close the gap Story 8.6 named as future work: an entry that already carries a real `DW-*`
id in Tier-3 but has no tracked twin was never touched by any tool —
`deferred_work_promote.py`'s `orphans = [e for e in entries if e.id is None]` filter
excluded it by design (Stories 8.1–8.4 scope).

Two live bugs surface before the real run: (a) `Tier3Shape.IDENTIFIED_PLAIN` entries
(bmad-loop harvest-damping and follow-up-review-budget) carry no `summary:` field — the
blank-summary guard hard-aborts the whole project batch on just one (would have blocked
5 of 8 projects). Fix: exclude on blank/whitespace-only summary, regardless of origin.
(b) untracked-membership used a loose `DW-` token harvest over raw tracked text, so a
prose mention classified an id as already tracked and permanently skipped. Fix: check
real `### DW-*:` headers.

**FR/AD:** FR-15 (`spec-deferred-work-visibility`, CAP-13)
**Deps:** S-8.6
**Surface:** `scripts/deferred_work_promote.py` (`_promote_project`, `_format_promoted_entry`,
`_describe_counts`), `tests/scripts/test_deferred_work_promote.py`

## Acceptance Criteria

- **Given** an already-identified Tier-3 entry whose id is not yet a real `### DW-*:`
  header anywhere in the tracked ledger, **When** `--fix` runs, **Then** it promotes
  verbatim under its own id (no minting), folded into the same batch/validate/write
  pipeline orphans already use — one combined message, one combined atomic write.
- **Given** the fixed tool run for real, **When** it processes the live fleet, **Then**
  blank-summary entries are excluded (not whole-batch abort) and membership is decided
  by real `### DW-*:` headers, not a loose `DW-` token harvest.

## Delivery Record

From `epics.md` Outcome (2026-08-28). Two-round adversarial review (isolated `tmp_path`
fixtures). Fleet-wide `--fix`, all 8 projects, zero `ABORTED`, zero duplicate ids:
atlas +5, doctor +25, marshal +12, mason +12, steward +11 (65 total);
herald/scribe/warden clean no-ops. Baseline correctly untouched (0 orphans freshly
promoted — restamp trigger stays "at least one orphan actually landed in `to_write`").

**Bounded:** combined detector count drops from 70 to 5 (atlas `DW-6`, scribe `DW-1..4`)
— spec-frontmatter fingerprint drift. Reconciling a stale-fingerprint Tier-3 reference
against its already-promoted twin is future work, not claimed here.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station verify
  suite; contract mint, no new per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `754b21ea86` (2026-08-28, "fix(doctor 8.7): promoter learns to copy already-identified-but-untracked entries"); also `4abc3e0e68` (2026-08-26, "Record Story 8.7 as done in the tracked epics and spec."). Ledger row `8-7-the-promoter-learns-to-copy-already-identified-but-untracked-entries-too: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/SPEC.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`, `scripts/deferred_work_promote.py`, `tests/scripts/test_deferred_work_promote.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
