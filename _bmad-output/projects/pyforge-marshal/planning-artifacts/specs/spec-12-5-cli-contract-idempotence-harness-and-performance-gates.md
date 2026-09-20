---
title: CLI contract, idempotence harness, and performance gates
type: test
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 7e8631433f
---

<intent-contract>

## Intent

**Problem:** Genesis seed verbs lack a locked CLI contract (flags, JSON schema, exit codes), idempotence proof, and runtime gates — unattended use is unpredictable (FR-123/124/126, NFR-P1–P3, AD-51/60).

**Approach:** Integration/contract suite under `tests/integration/` plus CLI assertions: `--json`/`--quiet` on all verbs; mutating verbs `--dry-run` (adopt/update default dry-run); exit-code taxonomy per S-7.2; zero typer/rich imports; AD-60 idempotence harness (run → detect+plan → zero actions) for init/adopt/update; performance gates check <5s, adopt --dry-run <10s, init <5min on local-recipes-sized fixture.

## Acceptance Criteria

- All verbs accept `--json` and `--quiet`; `--json` schema-stable across verbs.
- Mutating verbs accept `--dry-run`; `adopt`/`update` default to dry-run.
- Exit codes match S-7.2 taxonomy case by case.
- Import test: zero `typer`/`rich` under `src/`.
- Idempotence harness covers `init`, `adopt`, `update`.
- Performance: `check` < 5 s; `adopt --dry-run` < 10 s; `init` < 5 min (fixture-sized).

## Boundaries & Constraints

**Never:** Reintroduce typer/rich (AD-51). No docs story (12.6).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/tests/integration/` — contract + idempotence + perf
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` — flags if gaps

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- Integration/slow markers as established for perf gates

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `728fc697db` (2026-08-23, "Merge pull request #653 from rxm7706/marshal/12-5-cli-contract-gates"); also `c208eb830a` (2026-08-23, "Merge pull request #652 from rxm7706/marshal/12-5-cli-contract-gates"). Ledger row `12-5-cli-contract-idempotence-harness-and-performance-gates: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/referenced_deps.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
