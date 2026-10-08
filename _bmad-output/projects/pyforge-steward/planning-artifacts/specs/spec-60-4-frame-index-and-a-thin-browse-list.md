---
title: '60.4: Frame index and a thin browse list'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
baseline_revision: '94935697bd15e25fd1fdfdd1d8bf7165c6a6c0e4'
---

<intent-contract>

## Intent

**Problem:** Operators read YAML by hand and Frames have no catalog row.

**Approach:** A read-only list shows modules and Frames (name, tier, link or install hint). A Frame listing is a reviewed git add; share uses CAP-3 backends. It is not an App Store, MyBMAD, Collab, or nebari-frames.

## Boundaries & Constraints

**Always:**
- Read-only list of modules and Frames with name, tier, link or install hint.

**Never:**
- Do not build an App Store, MyBMAD, Collab, or nebari-frames.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Frame listing | reviewed git add | row appears on the browse list | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-self-hosted-bmad-marketplace CAP-4 CAP-7`.
Surface: docs/foundry/frames/; a generated index or existing chrome page..
Ledger key: `60-4-frame-index-and-a-thin-browse-list`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-60-4-frame-index-and-a-thin-browse-list.md`.

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py` — `index_artifacts`, `_writes_estate_browse_indexes`, extended `render`/`check` drift and `format_listings` (Story 60.1 engine).
- `src/shared/packages/pyforge-steward/tests/unit/test_catalog.py` — browse/index render, I/O matrix, real-tree sync tests.
- `docs/foundry/frames/frame-index.yaml` — generated Frame-only index (CAP-7).
- `docs/foundry/frames/browse.yaml` — generated modules + Frames browse list (CAP-4).
- `docs/foundry/frames/README.md` — operator pointer to generated files and `steward catalog list`.

## Tasks & Acceptance

**Execution:** (landed in worktree commits on `dispatch/pyforge-steward/60.4`.)

**Acceptance Criteria:**
- Given the committed tree, when `steward catalog render --check` runs, then `docs/foundry/frames/frame-index.yaml` and `browse.yaml` are in sync and list every estate Frame and wielded module with `trust_tier` and `link` or `install_hint`.
- Given a new Frame listing collected by `estate-frames`, when `steward catalog render` runs on the estate catalog, then the Frame row appears in both YAML indexes.
- Given `steward catalog list`, when it runs, then stdout includes `link=` or `install=` for each row (terminal browse without opening YAML).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 after memlog reconcile (S-13.7).

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** Story 60.4 extends `steward catalog render` to write two generated YAML files under `docs/foundry/frames/`: `frame-index.yaml` (Frames only, CAP-7) and `browse.yaml` (all catalog listings — wielded modules plus Frames, CAP-4). Each row carries `name`, `kind`, `trust_tier`, `source`, and `link` or `install_hint`. Indexes are written only for the committed estate catalog path (`src/shared/packages/pyforge-steward/catalog`), so `--catalog` test fixtures do not touch the real repo. `steward catalog list` text output now includes link/install columns. Operators are pointed at the generated files from `docs/foundry/frames/README.md`.

**Verification performed.** `pyforge-steward-test`: 2048 passed, 5 skipped. `python scripts/spec_surface_reconcile.py`: OK after memlog reconcile on `spec-pyforge-steward`.

**Governed paths reconciled (memlog).**
- `spec-pyforge-steward/.memlog.md`: `catalog.py`, `test_catalog.py`, `frame-index.yaml`, `browse.yaml`, `README.md`.
- `spec-self-hosted-bmad-marketplace/.memlog.md`: Story 60.4 landing note (CAP-4 / CAP-7).
