---
title: "The air-gap distribution contract has a socket"
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: ''
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Air-gap distribution for this repo has no shared contract socket. Steward
12.3 and any future Miniforge/constructor installer would each invent their own
mirrored-channel / pixi-bootstrap / verification shape, so offline consumers cannot
register a backend against a single empty registry.

**Approach:** Ship the contract document, a frozen `AIRGAP_CONTRACT` mapping, an EMPTY
`SUPPORTED_DISTRIBUTABLES` registry (steward `_SUPPORTED_MODULES` precedent), and
shape-validation + register helpers with unit tests. No installer is built here.

## Boundaries & Constraints

**Always:**
- Keep `SUPPORTED_DISTRIBUTABLES` empty in-tree; external deliverables register later.
- Coordinate conceptually with steward 12.3 — consume the same contract keys; do not
  implement steward.
- Document mirrored_channel_set, pixi_bootstrap_path, verification_hooks.

**Never:**
- Build a Miniforge/constructor installer in this repo.
- Implement the 63-family CI architecture.
- Touch recipes/ or conda-forge packaging paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Empty registry | fresh import | `SUPPORTED_DISTRIBUTABLES == {}` | N/A |
| Valid backend register | well-formed `DistributableBackend` | lands in registry under `name` | N/A |
| Duplicate name | second register same name | `ValueError` | refuse overwrite |
| Missing hooks / channels | empty tuples | `ValueError` from `validate_backend_shape` | fail loud |

</intent-contract>

## Code Map

- `docs/reference/airgap-distribution-contract.md` — human contract
- `src/shared/packages/pyforge-mason/src/pyforge/mason/airgap_contract.py` — socket + registry
- `src/shared/packages/pyforge-mason/tests/unit/test_airgap_contract.py` — shape + empty registry

## Tasks

- [x] Contract doc
- [x] Empty registry + validate/register
- [x] Unit tests

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `5a07304fbf` (2026-08-22, "Merge pull request #634 from rxm7706/mason/9-2-airgap-distribution-contract-socket"). Ledger row `9-2-the-air-gap-distribution-contract-has-a-socket: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `docs/reference/airgap-distribution-contract.md`, `src/shared/packages/pyforge-mason/src/pyforge/mason/airgap_contract.py`, `src/shared/packages/pyforge-mason/tests/unit/test_airgap_contract.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
