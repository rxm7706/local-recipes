---
title: "Story 5-1: Marshal-durability source, independent by construction"
type: "feature"
created: "2026-08-08"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-09"
---

<!-- RECOVERED 2026-08-09 Tier 3 (epics.md-derived Intent + ACs). No session transcript,
     bmad-loop worktree snapshot, or Tier-3 draft survived for this story — it landed via a
     hand-driven PR, not a bmad-loop run, so no spec was ever drafted to promote. Regenerated
     from epics.md per CLAUDE.md's recovery priority order, plus its merged-commit Delivery
     Record. Same class as spec-2-1. -->

## Intent

As the operator, I want Doctor to tell me when a tracked ledger has lost a completion, so
that a durability failure in Marshal's own machinery is caught by **something Marshal does
not control**. FR-14; AD-11, AD-12.

Scope is the SOURCE only. Rendering it is Story 5.2 — deliberately split rather than
folded in, because `sources/marshal.py` shipped with no caller and marking the story done
while the source was unreachable would be the "merged, marked done, never became the
runtime" shape this repo carries as the Atlas Kedro precedent and forbids in Marshal's
marshal:AD-67.

**Surface:** `sources/marshal.py`, `cli_bridge.py` (`run_git`), `models.py`
(`Source.MARSHAL_DURABILITY`), `tests/unit/test_sources_marshal_independence.py`

## Acceptance Criteria

- **Given** a tracked sprint ledger whose working state un-finishes a story, **When** the
  `marshal-durability` source gathers, **Then** a `FAIL` Finding names the project, the
  count and the keys, with a `git checkout HEAD -- <path>` remedy, **And** an aggregate
  `FAIL` states the total across all ledgers.
- **Given** no ledger has regressed, **Then** exactly one `OK` Finding states how many
  ledgers were checked.
- **Given** git is unavailable, the target is not a repository, or no ledger exists,
  **Then** the result is `WARN` — never `OK`, and never an exception.
- **Given** any state at all, **Then** `sources/marshal.py` imports no `pyforge.<station>`
  package — asserted by `test_sources_marshal_independence.py`, including lazy imports and
  string constants that could be fed to `import_module` — **And** every subprocess call
  routes through `cli_bridge` (AD-5/AD-12), asserted by
  `test_cli_bridge_sole_subprocess.py`.

## Delivery Record

Landed as `6a7a099a44` — *"doctor: hold the verdict on Marshal's own row (Charter §6)"*,
2026-08-08T14:57:05-05:00. 6 files, +422/−4:

- `src/pyforge/doctor/sources/marshal.py` (+224) — the source
- `src/pyforge/doctor/cli_bridge.py` (+48) — `run_git()`, added rather than routed around
  when `test_cli_bridge_sole_subprocess.py` caught the first cut calling `subprocess`
  directly (the record AD-12 was written from)
- `src/pyforge/doctor/models.py` (+5) — `Source.MARSHAL_DURABILITY`
- `tests/unit/test_sources_marshal_independence.py` (+118) — the AD-11 guard
- `tests/unit/test_models.py`, `scripts/ledger_regression_check.py`

Verified against the real 2026-08-08 incident: restoring the damaged herald ledger yields
`FAIL`/55; a clean tree yields `OK`/8 ledgers.

## Notes

This story is the origin of **AD-11** ("The Marshal verdict reads artifacts, never the
station") and **AD-12** ("A new subprocess need is satisfied IN `cli_bridge`"), both
recorded in the architecture spine. The independence test written here is the template
every later Epic 6 source copies — `test_sources_board_independence.py`,
`test_sources_chain_independence.py`, and Story 6.7's `test_sources_deps_independence.py`,
which extends it to bar the harness (`bmad_loop`) as well as the station package.

**One gap this story left, exposed by 5.2:** it added `Source.MARSHAL_DURABILITY` to the
Python enum but not to `data/report-schema.json`. Nothing caught it precisely because the
source had no caller — its findings had never been rendered, so they had never been
validated. That is the split working as designed.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `18a5ac49f0` (2026-08-08, "doctor: split Story 5.1 — the source shipped, the wiring did not"); also `bbd4b9f891` (2026-08-07, "herald: Story 5.1 — push regenerated exports with etag guard (CAP-5)"); also `1666be6cde` (2026-08-07, "marshal: manually promote Story 5.1's spec (squash-merge blind spot)"). Ledger row `5-1-marshal-durability-source-independent-by-construction: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md`, `docs/dashboard/data.js`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
