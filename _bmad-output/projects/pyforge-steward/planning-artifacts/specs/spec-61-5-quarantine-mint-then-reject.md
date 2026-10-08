---
title: '61.5: Quarantine — mint then reject'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      This PR touches only non-recipe paths and needs the `maintenance` label at PR open time.
    evidence: |-
      Diff is under src/shared/packages/pyforge-steward and planning memlogs only.
      AGENTS.md requires `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/quarantine.py
    severity: low
declared_low_risk: false
baseline_revision: 'ca4cc7f7d968255480f18d70cd5e45e6f9b1f681'
---

<intent-contract>

## Intent

**Problem:** Inbound rows arrive without a passport.

**Approach:** First 14 days (config) mint into quarantine; after that, no mint. No title-match endpoint exists.

## Boundaries & Constraints

**Always:**
- First configured window (default 14 days) mints into quarantine.
- After the window, no mint.

**Never:**
- Do not add a title-match endpoint.
- Do not treat Epic 8 as this product.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new inbound, day 3 | no passport | mint into quarantine | n/a |
| new inbound, day 15 | no passport | no mint | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-5`.
Surface: quarantine shelf on the existing app..
Ledger key: `61-5-quarantine-mint-then-reject`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-5-quarantine-mint-then-reject.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 1, false 2, maybe-false 0
- findings:
  - `[low]` `[reject]` `QuarantineShelfRowAdmin` allows editing `linked_at` but there is no automated test for human link flow — rejected: admin edit is the v1 human-link path per Dream ruling 3; linking is out of matrix scope.
  - `[false]` `[reject]` claim that day-15 row should fail duty `ok=False` — refuted: matrix "refuse" applies to mint, not shelf admit; `test_admit_inbound_day_15_refuses_mint_still_quarantines` and duty return `ok=True` with `mint_status=refused`.
  - `[false]` `[reject]` missing separate HTTP route registration for quarantine shelf — refuted: epic surface matches standup/shipped pattern (view factory in `views_htmx.py`, adopter wires URLconf).

## Auto Run Result

**Summary:** Inbound rows without a passport land on a quarantine shelf (`QuarantineShelfRow`). During `corridor.yaml`'s `quarantine.missing_passport_window_days` (default 14), admit mints a vendor passport and records `passport_id`; after the window mint is refused but the row still quarantines with `passport_id` null. New `steward quarantine admit|shelf` duty and `quarantine_htmx_view` expose the shelf; no title-match endpoint.

**Files changed:**
- `corridor/corridor.yaml` — `quarantine.missing_passport_window_days: 14`
- `corridor.py` — `QuarantineDecl` on `CorridorConfig`
- `quarantine.py` / `dashboard/quarantine_admit.py` — admit + shelf logic
- `dashboard/models.py` + migration `0008_quarantineshelfrow.py`
- `cli.py` — 26th duty `quarantine`
- `dashboard/admin.py`, `views_htmx.py`, `dashboard/__init__.py`
- `tests/unit/test_quarantine.py` plus duty-count / invariant updates

**Review findings breakdown:** 0 patched; 1 deferred (maintenance label in frontmatter); 2 rejected as above.

**Follow-up review recommendation:** `false`

**Verification performed:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0 (2068 passed, 2 skipped)
- Matrix audit: day-3 and day-15 rows covered in `test_quarantine.py`
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile (paths named below)

**Residual risks:** none rated high/medium. Human linking is admin-only with no HTMX link action in v1.

**Surface reconcile (memlog paths, 2026-10-08):**
- Owning spec `spec-pyforge-steward/.memlog.md`: `src/shared/packages/pyforge-steward/corridor/corridor.yaml`, `src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/quarantine.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/__init__.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/admin.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/models.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/migrations/0008_quarantineshelfrow.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/quarantine_admit.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/views_htmx.py`, `src/shared/packages/pyforge-steward/tests/unit/test_quarantine.py`, `src/shared/packages/pyforge-steward/tests/unit/test_corridor.py`, `src/shared/packages/pyforge-steward/tests/unit/test_cli.py`, `src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py`, `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py`
- Co-governor `pyforge-marshal/spec-pyforge-core/.memlog.md`: `src/shared/packages/pyforge-steward/src/pyforge/steward/quarantine.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/quarantine_admit.py`
