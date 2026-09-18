---
title: '44.1: The capability ledger and the move-list manifest'
type: 'docs'
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

**Problem:** every capability of the estate given one mode — `rebuild`, `move`, or `retire` — on scored signals, and every tracked path under a `move` capability resolved to exactly one destination

**Approach:** realization is decided per capability and no move story can route a path twice or drop one silently.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-44-1-the-capability-ledger-and-the-move-list-manifest.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `44-1-the-capability-ledger-and-the-move-list-manifest` off `blocked` (operator confirmation required).
- Do not dispatch outward Foundry/archive/conda-forge work without operator confirmation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| `git ls-files` (rows, allowlisted trees included), `scripts/spec_surface_check.py`'s classification (owner only) and `scribe index move-list` extended with a `… | the manifest renders **Then** 100 % of the 24,858 tracked paths carry exactly one destination by ordered precedence, a… | 100 % of the 24,858 tracked paths carry exactly one destination by ordered precedence, a `source_sha` and the foundry epoch SHA; a path matched by two equal-precedence rules is row kind `ambiguous` a… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the manifest is a machine-readable file with per-directory rollups at the spine's seeded location (`docs/foundry/manifest.*`, `[ASSUMPTION]`), rows carry `kind` (`file` | `secret` | `identity`), and… | n/a |
| And-clause from epics.md | when the story lands | `steward cutover plan --regenerate` rebuilds it from scratch and `--append` folds in only the delta since the recorded `source_sha`; both preserve `moved` rows (idempotent over status) | n/a |
| And-clause from epics.md | when the story lands | the capability ledger (`fnd:AD-2`, `fnd:CAP-9`) has one row per capability with mode, state, dependencies and the four signals scored (Spec fidelity, coupling, open debt, irreplaceable state); the fi… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `fnd:CAP-2 (input)`.
Surface: named on the story in epics.md
Ledger key: `44-1-the-capability-ledger-and-the-move-list-manifest`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-44-1-the-capability-ledger-and-the-move-list-manifest.md`.

## Epic excerpt

As a platform operator,
I want every capability of the estate given one mode — `rebuild`, `move`, or `retire` — on scored signals, and every tracked path under a `move` capability resolved to exactly one destination,
So that realization is decided per capability and no move story can route a path twice or drop one silently.

**Type:** docs • **Effort:** M • **Deps:** S-44.13 • **FR/AD:** fnd:CAP-2 (input) • fnd:AD-1, fnd:AD-2, fnd:AD-15, fnd:AD-16 • red-team D-2 • prior art `pyforge.scribe.extras.move_list` (scribe 6.1)
**Given** `git ls-files` (rows, allowlisted trees included), `scripts/spec_surface_check.py`'s classification (owner only) and `scribe index move-list` extended with a `parent_depth` signal (coupling) **When** the manifest renders **Then** 100 % of the 24,858 tracked paths carry exactly one destination by ordered precedence, a `source_sha` and the foundry epoch SHA; a path matched by two equal-precedence rules is row kind `ambiguous` and blocks
**And** the manifest is a machine-readable file with per-directory rollups at the spine's seeded location (`docs/foundry/manifest.*`, `[ASSUMPTION]`), rows carry `kind` (`file` | `secret` | `identity`), and its row shape matches `fnd:AD-2`'s convention
**And** `steward cutover plan --regenerate` rebuilds it from scratch and `--append` folds in only the delta since the recorded `source_sha`; both preserve `moved` rows (idempotent over status)
**And** the capability ledger (`fnd:AD-2`, `fnd:CAP-9`) has one row per capability with mode, state, dependencies and the four signals scored (Spec fidelity, coupling, open debt, irreplaceable state); the first-pass modes in `cutover.md` are presented to the operator row by row, never applied silently

