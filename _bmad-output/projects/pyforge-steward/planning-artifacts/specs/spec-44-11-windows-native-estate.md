---
title: '44.11: Windows-native estate'
type: 'feature'
created: '2026-09-18'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the estate to clone and run natively — links generated as junctions, paths under the limit, no shell-only tasks — with the host reached remotely

**Approach:** the Windows population does recipe, station and planning work first-class.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-44-11-windows-native-estate.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `44-11-windows-native-estate` off `blocked` (operator confirmation required).
- Do not dispatch outward Foundry/archive/conda-forge work without operator confirmation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| a fresh clone on Windows with `core.symlinks` off **When** the link step runs **Then** every runtime link (`.claude/skills/<x>`, the two BMAD planning links, `… | the link step runs **Then** every runtime link (`.claude/skills/<x>`, the two BMAD planning links, `.cursor/skills/<x>`… | every runtime link (`.claude/skills/<x>`, the two BMAD planning links, `.cursor/skills/<x>` where Cursor is detected) exists as a junction, none is tracked in git, and a doctor preflight reports them… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the preflight fails loud on a link that is a text file and on the deepest tracked path exceeding the Windows limit from the clone root; long-path registry settings are never assumed | n/a |
| And-clause from epics.md | when the story lands | no pixi task invokes `bash -c`, `sed`, `grep`, `awk`, `find` or `tee` (audited in a test); runtime state resolves to gitignored `var/` | n/a |
| And-clause from epics.md | when the story lands | a win-64 CI leg runs the station suites, the link check and the detectors green; the remote-dev profile for the host is documented in the bootstrap Spec | n/a |

</intent-contract>

## Binding

Parent Spec capability: `fnd:CAP-1, fnd:CAP-2, fnd:CAP-3`.
Surface: named on the story in epics.md
Ledger key: `44-11-windows-native-estate`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-44-11-windows-native-estate.md`.

## Epic excerpt

As a developer on a stock Windows machine with no WSL and no Developer Mode,
I want the estate to clone and run natively — links generated as junctions, paths under the limit, no shell-only tasks — with the host reached remotely,
So that the Windows population does recipe, station and planning work first-class.

**Type:** feature • **Effort:** L • **Deps:** S-44.3 • **FR/AD:** fnd:CAP-1, fnd:CAP-2, fnd:CAP-3 • fnd:AD-5, fnd:AD-19
**Given** a fresh clone on Windows with `core.symlinks` off **When** the link step runs **Then** every runtime link (`.claude/skills/<x>`, the two BMAD planning links, `.cursor/skills/<x>` where Cursor is detected) exists as a junction, none is tracked in git, and a doctor preflight reports them healthy
**And** the preflight fails loud on a link that is a text file and on the deepest tracked path exceeding the Windows limit from the clone root; long-path registry settings are never assumed
**And** no pixi task invokes `bash -c`, `sed`, `grep`, `awk`, `find` or `tee` (audited in a test); runtime state resolves to gitignored `var/`
**And** a win-64 CI leg runs the station suites, the link check and the detectors green; the remote-dev profile for the host is documented in the bootstrap Spec

