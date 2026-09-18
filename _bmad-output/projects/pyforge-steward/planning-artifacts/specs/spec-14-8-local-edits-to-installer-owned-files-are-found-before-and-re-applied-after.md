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

