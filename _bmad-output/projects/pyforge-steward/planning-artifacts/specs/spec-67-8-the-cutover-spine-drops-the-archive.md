---
title: '67.8: The cutover spine drops the archive'
type: 'docs'
created: '2026-09-25'
status: 'ready'
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

**Problem:** The spine still describes `local-recipes` as a read-only archive after Phase 6 (fnd:AD-1, the roles table, the Phase 6 node, the CAP-7 trace row, fnd:AD-21's wording).

**Approach:** Append a memlog entry naming the 2026-09-25 ruling to the spine's `.memlog.md`, then re-render the cutover section through `bmad-architecture`.

## Boundaries & Constraints

**Always:**
- Spine changes go through `bmad-architecture` from its memlog.
- Re-stamp scoped: one `--spec` per Spec the detector names.
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per named Spec, re-run the check and read its exit code; never a bare stamp.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not hand-edit the spine body.
- Do not run a bare `--write-baseline`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| spine re-rendered | grep for archive wording in the cutover section | no AD calls local-recipes archived or read-only | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-7 (retired)`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `67-8-the-cutover-spine-drops-the-archive`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-67-8-the-cutover-spine-drops-the-archive.md`.

## Epic excerpt

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** fnd:CAP-7 (retired) • fnd:AD-1, fnd:AD-21 • Spec memlog 2026-09-25 (steps 3–4 note)
**Surface:** `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md` and its `.memlog.md`, through `bmad-architecture` (fnd:AD-1's "read-only at a pinned SHA after Phase 6" rule, the three-roles table's Archive row, the Phase 6 diagram node, the `fnd:CAP-7` trace row, and fnd:AD-21's naming of the oracle).
**Given** the operator retired `fnd:CAP-7` on 2026-09-25 and the spine still describes a Phase 6 archive
**When** `bmad-architecture` re-renders the cutover section from a memlog entry naming the ruling
**Then** no AD describes `local-recipes` as archived or read-only; fnd:AD-21's oracle is "the archived suite at a pinned source SHA", with no repository archive implied; the trace table maps no story to `fnd:CAP-7`
**And** the spine re-stamp is scoped (`--spec` for each Spec the detector names)

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamp.
