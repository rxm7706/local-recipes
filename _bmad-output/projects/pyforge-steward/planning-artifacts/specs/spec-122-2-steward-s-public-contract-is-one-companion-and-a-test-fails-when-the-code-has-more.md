---
title: '122.2: Steward''s public contract is one companion and a test fails when the code has more'
type: 'feature'
created: '2026-11-10'
status: 'blocked'
flag-exempt: detector-or-gate
difficulty: heavy
story: 122.2
spec: pyforge-steward
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
  - src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py
  - src/shared/packages/pyforge-steward/README.md
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-123.2, S-123.3).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** Decision D1 of 2026-11-10: the Spec is not a contract a second root can build against, because most of the public surface is written nowhere but the code.

**Approach:** Write `contract.md` beside `SPEC.md` as hand-written tables (no generator) and a closed-world meta-test (`live_tree`, it reads the Spec folder) that diffs the parser, the source and the MCP face against it. Build after control-plane 121.2 (the `cutover` rows), Story 123.2 (`root_layout`, the public `sync` name) and Story 123.3 (estate plan's exit 3), so the test starts true.

Ledger key: `122-2-steward-s-public-contract-is-one-companion-and-a-test-fails-when-the-code-has-more`. Type / Effort / Deps: feature / L / S-121.2, S-122.1, S-123.2, S-123.3.

### Living CAP citations

- **`spec-pyforge-steward` CAP-179** — the public contract is one companion, and a meta-test fails when the code has more; minted 2026-11-10 `(ready 2026-11-10)` and rendered at mint.

## Boundaries & Constraints

**Always:**
- Name the capability on every row, qualified when another Spec owns it (`spec-python-foundry-cutover:CAP-8` for `pyforge.cutover_root`, `spec-pyforge-unifying-strategy:CAP-20` for the MCP face).
- Read django-steward and `django_pyforge/station_cli.py` by AST, never by import.
- Say in the contract that environment reads and flag keys built by concatenation are out of an AST scan's reach.

**Never:**
- Never change runtime code.
- Never generate contract.md.
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — the contract test passes.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py -q
  ```
- **AC2 — each family's check can fire.** Expected: exit 0 with at least 7 tests selected (verb, flag, flag key, environment variable, exit code, MCP tool, a Spec verb that is neither live nor retired), each feeding the checker one planted extra and asserting it is reported.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py -q -k fires
  ```
- **AC3 — every steward flag key is a row.** Expected: exit 0; prints `30 []`.
  ```bash
  python3 -c "import json;k=[x for x in json.load(open('src/platform/config/flags.json'))['flags'] if x.startswith('pyforge.steward.')];t=open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md').read();m=[x for x in k if x not in t];print(len(k),m);raise SystemExit(bool(m))"
  ```
- **AC4 — the MCP tools and targets are named.** Expected: prints 5 or more.
  ```bash
  grep -cE 'start_duty|get_duty|ci-status|estate-plan|estate-status' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
  ```
- **AC5 — retired verbs are a table.** Expected: prints 3.
  ```bash
  grep -cE '`steward (deploy dashboard|deploy status|cutover apply)`' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
  ```
- **AC6 — estate plan's refusal is recorded.** Expected: prints 1 or more, on a row that gives exit 3 for a failed pixi dry run (Story 123.3).
  ```bash
  grep -c 'estate plan' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
  ```
- **AC7 — the estate-bound constants are listed.** Expected: prints 1 or more.
  ```bash
  grep -c 'root_layout' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
  ```
- **AC8 — the README points at the contract and lists exit 3.** Expected: prints 2 or more.
  ```bash
  grep -cE 'contract\.md|`3`' src/shared/packages/pyforge-steward/README.md
  ```
- **AC9 — Post-condition (Story 124.2 runs it): the test reads only what steward's live job already fires on.** Expected: exit 0 once Story 124.2 has landed; red before it by design (other units' new reads).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q
  ```
- **AC10 — package half.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json
  ```
- **AC11 — live-tree half.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```
- **AC12 — lint and types.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-179

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 122.
- Ledger key: `122-2-steward-s-public-contract-is-one-companion-and-a-test-fails-when-the-code-has-more` (`backlog` at mint).
- Deps: S-121.2, S-122.1, S-123.2, S-123.3.
- Surface: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md` (new), `src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py` (new), `src/shared/packages/pyforge-steward/README.md`.
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py -q` — expected: exit 0.
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py -q -k fires` — expected: exit 0 with at least 7 tests selected (verb, flag, flag key, environment variable, exit code, MCP tool, a Spec verb that is neither live nor retired), each feeding the checker one planted extra and asserting it is reported.

## Notes

- Cross-station: none. A later story that adds a contract item owns its row through its dependency on this story.
- `sync._default_transport` is listed as a private name the host still imports (DW-steward-74-1); `five_tier.py` is a check library with no verb.
- Until Story 124.2 lands, steward's trigger-map test may red on other units' new reads (a planned red window); this story is judged by its own test modules and by steward's package half without that module.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.
