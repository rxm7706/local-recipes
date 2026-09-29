---
title: '14.8: Local edits to installer-owned files are found before and re-applied after'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the cached package of the installed version (`~/.cache/rattler/cache/pkgs/bmad-method-<v>-*/lib/node_modules/bmad-method/src`, or `--installed-package-root`) **When** the pre-flight runs **Then** every installer-owned file (`.claude/skills/<manifest skill>/**`, `_bmad/scripts/*`) that differs from its packaged copy is listed as a local customization in the CAP-1 report **And** after the apply eac…

**Approach:** every installer-owned file (`.claude/skills/<manifest skill>/**`, `_bmad/scripts/*`) that differs from its packaged copy is listed as a local customization in the CAP-1 report **And** after the apply each one is re-applied by three-way merge (ours = pre-apply bytes, base = old upstream, theirs = new upstream): clean merges written, conflicts flagged with the hunk saved beside the report, never re…

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-14-8-local-edits-to-installer-owned-files-are-found-before-and-re-applied-after.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| the cached package of the installed version (`~/.cache/rattler/cache/pkgs/bmad-method-<v>-*/lib/node_modules/bmad-method/src`, or `--installed-package-root`) *… | the pre-flight runs **Then** every installer-owned file (`.claude/skills/<manifest skill>/**`, `_bmad/scripts/*`) that… | every installer-owned file (`.claude/skills/<manifest skill>/**`, `_bmad/scripts/*`) that differs from its packaged copy is listed as a local customization in the CAP-1 report **And** after the apply… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | after the apply each one is re-applied by three-way merge (ours = pre-apply bytes, base = old upstream, theirs = new upstream): clean merges written, conflicts flagged with the hunk saved beside the… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `upgrade.py` (pre-flight + reconcile), steward CLI (`--installed-package-root`)
Ledger key: `14-8-local-edits-to-installer-owned-files-are-found-before-and-re-applied-after`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-14-8-local-edits-to-installer-owned-files-are-found-before-and-re-applied-after.md`.

## Epic excerpt

**Type:** feature • **Effort:** L • **Deps:** 14.6 • **FR/AD:** spec-bmad-method-core-upgrade CAP-8
**Surface:** `upgrade.py` (pre-flight + reconcile), steward CLI (`--installed-package-root`)
**Given** the cached package of the installed version (`~/.cache/rattler/cache/pkgs/bmad-method-<v>-*/lib/node_modules/bmad-method/src`, or `--installed-package-root`) **When** the
pre-flight runs **Then** every installer-owned file (`.claude/skills/<manifest skill>/**`,
`_bmad/scripts/*`) that differs from its packaged copy is listed as a local customization in
the CAP-1 report **And** after the apply each one is re-applied by three-way merge (ours =
pre-apply bytes, base = old upstream, theirs = new upstream): clean merges written,
conflicts flagged with the hunk saved beside the report, never resolved by taking upstream;
`resolve_config.py` gets the old→new upstream delta replayed on the restored copy instead of
a bare `.bak` restore — **And** the fixture replaying 2026-09-06's seven files ends with six
clean merges and one flagged conflict (step-01 `done` routing) (failure-modes.md trap 16).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `d6758c7978` (2026-09-06, "fix(steward): CAP-8 follow-up review pass — merge-conflict labels, stale-sibling cleanup, package-shape valida"); also `297689f8d6` (2026-09-06, "feat(steward): CAP-8 — local edits to installer-owned files are found before and re-applie"). Ledger row `14-8-local-edits-to-installer-owned-files-are-found-before-and-re-applied-after: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py`, `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py`, `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_preflight.py`, `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_reconcile.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
