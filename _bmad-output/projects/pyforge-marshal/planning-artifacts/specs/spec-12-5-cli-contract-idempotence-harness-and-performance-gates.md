---
title: CLI contract, idempotence harness, and performance gates
type: test
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 686de783c4
---

<intent-contract>

## Intent

**Problem:** Genesis verbs need machine-stable flags, exit codes, idempotence proofs, and bounded runtimes so unattended and interactive use stay predictable (FR-123/124/126, NFR-P1–P3, SC-03/SC-09).

**Approach:** Add an integration contract suite under `tests/integration/` (and CLI surface in `cli/seed.py`) that asserts `--json`/`--quiet`/`--dry-run` contracts, exit-code taxonomy, argparse-only (no typer/rich), AD-60 idempotence harness across init/adopt/update, and performance gates on a local-recipes-sized fixture.

## Acceptance Criteria

- Every verb accepts `--json` and `--quiet`; `--json` schema-stable across verbs (FR-123, NFR-12).
- Mutating verbs accept `--dry-run`; `adopt` / `update` default to dry-run (FR-124).
- Exit codes match S-7.2 taxonomy for every failure mode (FR-126).
- Import test: zero `typer`/`rich` imports under `src/` (AD-51 amended).
- Idempotence harness (AD-60): run → detect+plan → zero actions for `init`, `adopt` (SC-03), `update`.
- Performance: `check` < 5 s (NFR-P1); `adopt --dry-run` < 10 s (NFR-P2); `init` e2e < 5 min (NFR-P3, SC-09) on local-recipes-sized fixture.

## Boundaries & Constraints

**Never:** Reintroduce typer/rich. Do not weaken never-write / offline gates from Stories 12-3/12-4.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/tests/integration/`
- `src/shared/packages/pyforge-marshal/` CLI (`cli/seed.py` and related)

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
