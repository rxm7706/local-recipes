---
title: '67.4: Upstream tickets for the gaps that need one'
type: 'chore'
created: '2026-09-25'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Gaps whose fix lies outside the estate have no owner outside it.

**Approach:** On the operator's flip, open one upstream issue per approved `upstream` row and link it from the row.

## Boundaries & Constraints

**Always:**
- Outward: dispatched only on explicit operator confirmation, per ticket target.
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per named Spec, re-run the check and read its exit code; never a bare stamp.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not open an issue for a row the operator did not approve.
- Do not flip this key off `blocked`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| approved upstream row | operator names the tracker | one linked open issue | stop and ask |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-13`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `67-4-upstream-tickets-for-the-gaps-that-need-one`.
Ledger status at mint: `blocked` — operator confirmation required to flip.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-67-4-upstream-tickets-for-the-gaps-that-need-one.md`.

## Epic excerpt

**Type:** chore • **Effort:** S • **Deps:** S-67.3 • **FR/AD:** fnd:CAP-13 • Dream 2026-09-25 (campaign phase 3)
**Outward (AGENTS.md policy):** opens issues on repositories outside this estate — held `blocked`; dispatched only on the operator's explicit confirmation, per ticket target.
**Surface:** `docs/foundry/sbom-gaps.md` (ticket links).
**Given** 67.3's list has `upstream` rows
**When** the operator flips this story and names each target tracker
**Then** each `upstream` row links one open issue, and no issue is opened for a row the operator did not approve

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- Every `upstream` row in `docs/foundry/sbom-gaps.md` links an issue the operator approved.
