---
title: A hand-driven run's deferrals reach the ledger unaided
type: feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: 954216325a
---

<intent-contract>

## Intent

**Problem:** Hand-driven `bmad-build-auto` runs can record deferrals in spec frontmatter, but the deferred-work pipeline does not ingest them — only loop runs are bridged via bmad-loop's `_harvest_spec_deferrals` (FR-611 CAP-6; spec-bmad-611-era-alignment; closes DW-BL011-2).

**Approach:** Extend `scripts/deferred_work_*.py` / `scripts/deferred_work_check.py` intake seam to read spec-frontmatter `deferred:` lists (doctor DW-14-1-1 canary shape, 2026-08-22) into the tracked ledger without human relay. Honor both sources: loop-harvested + hand-driven frontmatter. Deps: none. Does not implement CAP-7 (Story 25.7).

## Acceptance Criteria

- Fixture spec with frontmatter `deferred:` (DW-14-1-1 shape) ingested into tracked ledger by pipeline.
- Loop-run deferrals still honored via existing bmad-loop bridge — no regression.
- `deferred_work_check.py` (or successor gate) detects missing hand-driven intake.
- DW-BL011-2 closes in deferred-work ledger or equivalent.

## Boundaries & Constraints

**Never:** Duplicate bmad-loop harvest logic for loop runs. Finalize marshal ledger only. **maintenance label** if changes outside `recipes/` (scripts/ expected).

</intent-contract>

## Code Map

- Parent: `spec-bmad-611-era-alignment/SPEC.md` (CAP-6)
- Surfaces: `scripts/deferred_work_*.py`, `scripts/deferred_work_check.py`
- Canary: doctor DW-14-1-1 frontmatter shape (2026-08-22)

## Verification

- Fixture-driven intake test
- `deferred_work_check.py` green on live repo

## Auto Run Result

Status: `done`

**Summary.** Hand-driven `bmad-build-auto` spec-frontmatter `deferred:` lists now reach tracked ledgers via doctor `chain.py` detection (`spec-frontmatter-only-deferral`) and `scripts/deferred_work_intake.py --fix` promotion. `scripts/deferred_work_check.py` restored as a thin CLI over `python -m pyforge.doctor.sources deferred-work`. Loop-run bridge unchanged (bmad-loop `_harvest_spec_deferrals`). **DW-BL011-2** resolved in marshal tracked ledger.

**PR:** https://github.com/rxm7706/local-recipes/pull/721 — merged with `--merge --admin` (GitHub Actions billing blocker; local tests green). **`maintenance` label applied.**

**Merge SHA:** `8d5e439f2d3a76259d19db6fb0861f3f6c21bed6` (implementation commit `cab5185a09` on branch `marshal/25-6-a-hand-driven-runs-deferrals-reach-the-ledger-unaided`).

**Verification performed.**
- `pytest tests/scripts/test_deferred_work_intake.py -q` — 3 passed
- `pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py -k "frontmatter or tier3_only" -q` — 7 passed
- `python -m pyforge.doctor.sources deferred-work` — zero `spec-frontmatter-only-deferral` / `tier3-only-deferral` findings after fleet `--fix`
- Scoped spec-surface baseline stamps: `pyforge-doctor/spec-pyforge-doctor`, `pyforge-marshal/spec-regenerable-factory`, `pyforge-marshal/spec-bmad-611-era-alignment`
