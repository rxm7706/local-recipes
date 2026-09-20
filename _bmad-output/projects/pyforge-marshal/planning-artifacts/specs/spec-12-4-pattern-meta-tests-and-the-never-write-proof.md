---
title: Pattern meta-tests and the never-write proof
type: test
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: c4c54211cf
---

<intent-contract>

## Intent

**Problem:** Twelve conflict-prevention patterns (P-01–P-12) must be enforced by executable tests so future stories cannot violate Genesis invariants (FR-100, SC-08, NFR-R4).

**Approach:** Extend `tests/meta/` with AST/import scans and fixture-driven proofs for P-01, P-02, P-03, P-07, layer rules, and SC-08 never-write against planning-artifacts and docs/dreams (including symlinked planning-artifacts case).

## Acceptance Criteria

- P-01: AST scan — no writes outside `fs.py` (`open(w)`, `Path.write_*`, `shutil.copy*`, `os.remove/rename`).
- P-02: `copier` imported only in `engine/copier.py`; no private Copier modules.
- P-03: detect runs against write-blocking fixture.
- P-07: no hash comparison inside `apply/`.
- Layer rule: no upward imports; `detect` never imports `apply`/`engine`.
- SC-08: `marshal seed update --run` against malicious manifest/migration cannot write to `docs/dreams/**` or `**/planning-artifacts/**` — raises `NeverWriteViolation`; symlink case included.

## Boundaries & Constraints

**Never:** Weaken never-write guard for convenience. P-09 covered by Story 12-3 — do not duplicate.

</intent-contract>

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `7e8631433f` (2026-08-23, "Merge pull request #651 from rxm7706/marshal/12-4-pattern-meta-tests"); also `7d4357acab` (2026-08-23, "Merge pull request #649 from rxm7706/marshal/12-4-pattern-meta-tests"). Ledger row `12-4-pattern-meta-tests-and-the-never-write-proof: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `src/shared/packages/pyforge-marshal/tests/meta/test_p01_write_primitives_only_in_fs.py`, `src/shared/packages/pyforge-marshal/tests/meta/test_p02_copier_sole_ownership.py`, `src/shared/packages/pyforge-marshal/tests/meta/test_sc08_never_write_update_proof.py`, `src/shared/packages/pyforge-marshal/tests/meta/test_seed_layer_import_rules.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
