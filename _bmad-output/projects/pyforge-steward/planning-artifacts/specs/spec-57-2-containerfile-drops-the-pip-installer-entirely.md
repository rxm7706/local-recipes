---
title: '57.2: Containerfile drops the pip installer entirely'
type: 'chore'
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

**Problem:** `[feature.platform-image-pip]` and `scripts/platform_image_pip_layer.py` retired to a tombstone that fails loudly if resurrected

**Approach:** the runtime image never runs a second, overlap-blind installer.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-57-2-containerfile-drops-the-pip-installer-entirely.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| the Containerfile ran `python3 -m pip install --no-deps` for host extras | this story lands **Then** `rg 'pip install --no-deps' src/platform/Containerfile` is empty and `platform_image_pip_laye… | `rg 'pip install --no-deps' src/platform/Containerfile` is empty and `platform_image_pip_layer.py` exits 2 with "retired" in its stderr if invoked | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the 16.1 emitter is unused by the Containerfile | n/a |
| And-clause from epics.md | when the story lands | `tests/packaging/test_platform_image_one_pixi_env.py` covers both claims | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: named on the story in epics.md
Ledger key: `57-2-containerfile-drops-the-pip-installer-entirely`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-57-2-containerfile-drops-the-pip-installer-entirely.md`.

## Epic excerpt

As a platform operator,
I want `[feature.platform-image-pip]` and `scripts/platform_image_pip_layer.py`
retired to a tombstone that fails loudly if resurrected,
So that the runtime image never runs a second, overlap-blind installer.

**Type:** chore • **Effort:** S • **Deps:** S-57.1 • **FR/AD:** spec-platform-image-one-pixi-env CAP-2
**Given** the Containerfile ran `python3 -m pip install --no-deps` for host extras
**When** this story lands **Then** `rg 'pip install --no-deps'
src/platform/Containerfile` is empty and `platform_image_pip_layer.py` exits
2 with "retired" in its stderr if invoked
**And** the 16.1 emitter is unused by the Containerfile
**And** `tests/packaging/test_platform_image_one_pixi_env.py` covers both claims
**Status:** done — shipped `59083b8391` (2026-08-25); re-verified live
2026-09-11 and again 2026-09-14 (3/3 `tests/packaging/test_platform_image_one_pixi_env.py` pass)

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `57-2-containerfile-drops-the-pip-installer-entirely: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
