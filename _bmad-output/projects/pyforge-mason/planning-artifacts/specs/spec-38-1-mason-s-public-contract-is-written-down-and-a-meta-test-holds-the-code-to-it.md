---
title: "38.1: Mason's public contract is written down, and a meta-test holds the code to it"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a companion document and a check that judges (spec-feature-flag-governance Q1; roster list)
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/exit_codes.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py
  - src/shared/packages/django-mason/src/django_mason_portal/mcp_asgi.py
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-05.md
surface:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md
  - src/shared/packages/pyforge-mason/tests/meta/test_public_contract.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D1. The Spec names eight verbs and `six knobs` in prose; nothing lists the 17 parser nodes and their options, the twelve environment variables Mason reads or sets (eight `MASON_`, three credentials whose presence ship checks, `CFE_RECIPES_ROOT` set for the submit child), the five exit codes, the 22 error identifiers (declared API by the Spec's own constraint) or the four MCP and portal names, and nothing fails when the code gains one. A second repository cannot rebuild a contract that is not written. The same document closes the README and skill gaps the 2026-11-05 audit accepted (MAS-R-F3, F5, F6: ship states, the JSON envelope, the exit-code numbers).

**Approach:**
- `contract.md` is a table per family, one item per row, first cell in backticks, so the test parses it without prose rules.
- Extraction, by AST over the package source, never by importing another package: (1) parser paths and options from `build_parser()` walked through its subparsers (17 nodes: the root, 3 nouns, 12 verbs, doctor; the bare-noun alias `mason package --ship` is a row of `mason package`); (2) environment variables: every module-level name whose identifier contains `ENV` bound to a string literal matching `^[A-Z][A-Z0-9_]+$`, every string member of a module-level tuple whose identifier contains `CREDENTIAL`, and every UPPER_SNAKE literal used as the first argument of `.get(` on a name `environ` or `env` or as an `os.environ[...]` key: twelve, each row saying `read` or `set for the child`; (3) the `EXIT_*` names of `exit_codes.py` (5); (4) the first argument of each `super().__init__` in `errors.py` (22, plus the `channel:<name>` ship-target form as a note); (5) every module-level `*_TOOL` constant in `django-mason`'s `mcp_asgi.py` and `LAST_DIAGNOSE_TOOL` in `django-pyforge`'s `assertion/client.py`, read as text; (6) string literals passed to any flag reader (none today).
- Prose rows the test does not judge: the hook spec `pyforge.mason.build_engine` and its two entry points; the JSON envelope (`schema_version`, `command`, `status`, `data`, `errors`; delegated return codes in `data.returncode`); the ship states `not_attempted`, `pending`, `terminal`, `failed` and `exit 0 does not mean shipped` (AD-9); the DoctorReport field names; the layout Mason assumes at the CFE root and the factory island; that `MASON_FOUNDRY_ROOT` and `MASON_FACTORY_ROOT` have no flag form; and that the MCP face is a supervisor stub whose `run_build` calls no Mason verb, `django-mason` code governed by `spec-pyforge-unifying-strategy`.
- The module reads the planning tree and two other packages, so it carries `pytestmark = pytest.mark.live_tree` (Story 38.2 registers the marker; the two stories are order-independent) and hands the repository root to no package code.
- The ship-root behaviour is recorded as layout only; the behaviour waits on steward Stories 44.8 and 44.9.

Ledger key: `38-1-mason-s-public-contract-is-written-down-and-a-meta-test-holds-the-code-to-it`.
Ledger status: `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- **CAP-5** (amended 2026-11-10; FR-60): the public contract is the companion `contract.md`, held to the code by `tests/meta/test_public_contract.py`. The mint wrote the amendment at `(ready 2026-11-10)`; Story 37.1 writes the shipped marker and adds the companion line.
- AD-9 (ship states), AD-13 (the closed six-flag set); decision D1; EGM findings MAS-R-F3, MAS-R-F5, MAS-R-F6.
- `spec-feature-flag-governance` Q2: `flag-exempt: detector-or-gate` (doctor Story 55.4 is the precedent).

## Boundaries & Constraints

**Always:**
- Read script file names from `cfe._CFE_SCRIPTS`; prove each family by a planted violation in both directions.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never put recipe knowledge in the contract or the test (CAP-7's deny-list scans the package source).
- Never import `django-mason` or `django-pyforge` in the test.
- Never add behaviour or a flag (operator ruling 2026-11-10: no new behaviour and no new kill switch in this PR).
- Never append a `Surface reconcile` line to another Spec's memlog and never run `spec_surface_check.py --write-baseline`: Story 37.4 writes mason's reconcile event, each other Spec's closer writes its own, and doctor Story 58.4 runs every scoped stamp once, after the last edit (cutover readiness plan, integration 2026-11-10).

## Acceptance Criteria

**AC1 — The contract meta-test passes on the tree.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_public_contract.py -q; echo $?
```

Expect: 0.

**AC2 — Each family is proven by a planted violation in both directions.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_public_contract.py -q -k planted; echo $?
```

Expect: 0 and the summary reads `14 passed`: for each of parser path, option, environment variable, exit code, error identifier, MCP or portal name and flag key, one case where the code has an item the contract lacks and one where the contract names an item the code lacks.

**AC3 — The contract lists what the code has today.**

```bash
grep -c '^| `MASON_' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md; grep -cE '^\| `(TWINE_USERNAME|TWINE_PASSWORD|PREFIX_API_KEY|CFE_RECIPES_ROOT)`' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md; grep -cE '^\| `[a-z-]+:[a-z0-9-]+` ' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md; grep -cE '^\| `mason( [a-z]+){0,2}` ' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md; grep -cE '^\| `(run_build|start_build|get_build|last_diagnose)` ' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md; grep -cE '^\| `EXIT_[A-Z_]+` ' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md
```

Expect: prints 8, 4, 22, 17, 4 and 5.

**AC4 — The audit's skill gaps are answered in the contract (MAS-R-F3, F5, F6).**

```bash
grep -c 'exit 0 does not mean shipped' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md; grep -cE 'not_attempted|schema_version' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md; grep -c 'EXIT_INTERRUPTED' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md
```

Expect: each prints 1 or more.

**AC5 — Mason reads no feature flag, as the contract says.**

```bash
grep -rnE 'read_boolean|pyforge\.core\.flags|cutover_root' src/shared/packages/pyforge-mason/src/pyforge/mason; echo $?
```

Expect: no output, then 1.

**AC6 — The module is in the live-tree half.**

```bash
grep -c '^pytestmark = pytest.mark.live_tree' src/shared/packages/pyforge-mason/tests/meta/test_public_contract.py
```

Expect: prints 1.

**AC7 — Lint and types.**

```bash
pixi run -e pyforge-guild lint-types; echo $?
```

Expect: 0.

</intent-contract>

## Binding

- Parent: `spec-pyforge-mason`; amends CAP-5.
- Requirements: FR-60 ← CAP-5.
- Dream: `docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*.
- Epic 38, `### Story 38.1: Mason's public contract is written down, and a meta-test holds the code to it` in `planning-artifacts/epics.md`.
- Wave: BUILD-1 (cutover readiness plan).
- Findings closed: MUST 6; SHOULD: mason src portability.

## Notes

- Cross-station: steward's trigger map must carry the test's outside reads for the mason live job (`contract.md`, `mcp_asgi.py`, `django_pyforge/assertion/client.py`): steward:S-124.2.
