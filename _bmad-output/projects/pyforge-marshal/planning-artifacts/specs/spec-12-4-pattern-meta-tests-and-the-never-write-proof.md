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
