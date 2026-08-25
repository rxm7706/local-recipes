---
title: pyforge dispatches without reimplementing
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
context:
  - src/shared/packages/pyforge-core/README.md
  - src/shared/packages/pyforge-core/src/pyforge/core/process.py
  - src/shared/packages/pyforge-core/tests/meta/conftest.py
  - src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py
warnings: []
baseline_revision: 8c97d5baecf3b33350bb7ae571e341e7eeaa691b
review_loop_iteration: 0
followup_review_recommended: false
deferred:
  - summary: >-
      Full `pyforge-core-test` still reds on pre-existing marshal/steward
      sole-ownership scans unrelated to dispatch.
    evidence: |-
      test_atomic_write_sole_ownership, test_exception_root_sole_ownership,
      and test_process_sole_ownership fail on sibling sources this story
      did not edit (same class as Story 32.1 deferred). CI for 22.1 runs
      unit + parity + leaf + plugin conformance only.
    location: >-
      src/shared/packages/pyforge-core/tests/meta/
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Operators must memorize eight station console scripts. FR-13 / canopy AD-14 require one grammar `pyforge <station> <noun> <verb>` that reaches the same behaviour as each station binary, without absorbing those CLIs.

**Approach:** Add a `pyforge` console script on `pyforge-core` that maps the station token to that package's primary console script and forwards the remaining argv through `PosixProcess`. CI generates a verb-parity matrix from sibling sources; drift fails the build. Unintrospectable CLIs are named preparatory stories, never silent skips.

## Acceptance Criteria

- Given the eight station console scripts, when CI generates the parity matrix, then every introspected verb is reachable through both the station script and `pyforge <station> …`.
- Given a station verb the unified entry cannot reach, when the matrix check runs, then the build fails.
- Given `pyforge-core` sources, when reviewed, then no station duty logic is copied in; dispatch only.
- Given a station CLI that cannot be introspected, when the matrix check runs, then a named preparatory story id is required; omitting the station is a failure.

## Boundaries & Constraints

**Always:** `pyforge.core` stays stdlib-only (no `import pyforge.<station>`). Forward argv; do not re-parse station flags. Write specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`. Reuse `PosixProcess`. Primary console script per `pyforge-*` dist (skip `*-mcp` and `pyforge-testing-kit`).

**Block If:** A change would add a third-party runtime dep to pyforge-core, import a station package, or put `pyforge.*` under `src/platform/`.

**Never:** Story 23.1; Epic 30 console deletion; MinIO; Liquibase 27-1; station logic copied into core; silent skip of an unintrospectable CLI.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Forward | `pyforge steward keys list` | Child argv `steward keys list`; child's exit code | Child nonzero is forwarded, not raised |
| Unknown station | `pyforge nope verb x` | No subprocess; usage on stderr | Exit 2 |
| Missing binary | Station mapped, executable absent | No station traceback | `ProcessError` → exit 127 |
| Matrix drift | New `add_parser("…")` on a mapped station | Matrix includes it; unified path reachable | Missing map/script fails CI |
| Unintrospectable | Atlas Kedro/Click (no static parsers) | Named prep story id present | Silent skip fails CI |
| Extra script | `marshal-mcp` beside `marshal` | Primary is `marshal` only | MCP script is not the station token |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` — **new** `main`, `dispatch_argv`, `primary_console_script`, `station_script_map` (stdlib `tomllib` + `importlib.metadata`; no station imports)
- `src/shared/packages/pyforge-core/src/pyforge/core/process.py` — **reuse** `PosixProcess.run` / `ProcessError` (do not fork subprocess)
- `src/shared/packages/pyforge-core/src/pyforge/core/errors.py` — `DispatchError` subclasses `PyforgeError` if a dedicated type is needed; do not invent a second root
- `src/shared/packages/pyforge-core/pyproject.toml` — `[project.scripts] pyforge = "pyforge.core.dispatch:main"`; `dependencies = []` stays empty
- `src/shared/packages/pyforge-core/README.md` — document grammar, dispatch-only rule, prep-story rule
- `src/shared/packages/pyforge-core/tests/unit/test_dispatch.py` — forward / unknown / missing-binary (inject `ProcessPort`)
- `src/shared/packages/pyforge-core/tests/meta/test_cli_parity_matrix.py` — generate matrix from sibling `pyproject.toml` + AST `add_parser` / Typer `@app.command`; fail on drift; fail on silent skip
- `src/shared/packages/pyforge-core/tests/meta/conftest.py` — reuse `PACKAGES_ROOT` / `sibling_station_dirs`
- `src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py` — **read-only** unless a new import fails it
- `.github/workflows/pyforge-core.yml` — **new** PR/push job: pip-install pyforge-core + pytest; run `tests/` (parity matrix is CI)
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-22-prep-atlas-kedro-cli-introspection.md` — **named** preparatory story (atlas Kedro CLI); id must match the matrix constant
- Mason `cli.py` noun/verb argparse is the grammar exemplar; do not copy mason duties
- Station CLIs (read-only): steward/herald/warden/mason/doctor argparse; marshal `cli/*.py` `add_parser`; scribe Typer; atlas `__main__.py` Kedro `find_run_command` — unintrospectable

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` — add dispatch-only front door — FR-13
- `src/shared/packages/pyforge-core/pyproject.toml` — declare `pyforge` script
- `src/shared/packages/pyforge-core/README.md` — grammar + no-reimplement + prep-story
- `src/shared/packages/pyforge-core/tests/unit/test_dispatch.py` — I/O matrix rows except CI matrix
- `src/shared/packages/pyforge-core/tests/meta/test_cli_parity_matrix.py` — generate matrix; fail drift and silent skip
- `.github/workflows/pyforge-core.yml` — CI runs the suite
- `spec-22-prep-atlas-kedro-cli-introspection.md` — named prep story for atlas

**Acceptance Criteria:**
- Given the eight station console scripts, when CI generates the parity matrix, then every introspected verb is reachable through both paths.
- Given a station verb the unified entry cannot reach, when the matrix check runs, then CI fails.
- Given pyforge-core, when inspected, then dispatch only — no copied station logic.
- Given a station CLI that cannot be introspected, when the matrix check runs, then a named preparatory story is required rather than a silent skip.

## Design Notes

Runtime: `importlib.metadata.distribution("pyforge-<token>")` for installed stations; tests also build the map from sibling `pyproject.toml` so CI does not need all eight envs. Primary script: name equal to the station token, else dist name, else first console script whose name does not end in `-mcp`.

`pyforge <station> <rest…>` → `<primary> <rest…>` (cwd inherited via `PosixProcess`; no `env=` override). Unknown station: exit 2. Missing executable: exit 127.

Introspection is AST-only in tests (argparse `add_parser("x")`, Typer `command("x")` / `add_typer(..., name=)`). Atlas Kedro/Click has no static parser tree — `PREPARATORY_UNINTROSPECTABLE["atlas"] = "spec-22-prep-atlas-kedro-cli-introspection"`. Dispatch to `pyforge-atlas` still works.

Do not hardcode a verb allowlist in `dispatch.py`; forwarding is how a newly added verb stays reachable. The matrix proves the station is mapped; a synthetic unmapped station with parsers must fail.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 1: (high 0, medium 1, low 0)
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` silent-skip test now calls `generate_parity_matrix` on a temp tree and expects `ParityMatrixError` instead of duplicating the predicate

## Auto Run Result

Status: done

Summary: Unified `pyforge` console script on pyforge-core dispatches `pyforge <station> <rest>` to each station's primary console script via `PosixProcess`. CI generates an AST/pyproject parity matrix; atlas Kedro is a named preparatory story.

Files:
- `dispatch.py` — dispatch-only front door
- `pyproject.toml` — `pyforge` script
- `test_dispatch.py` / `test_cli_parity_matrix.py` — I/O + matrix
- `.github/workflows/pyforge-core.yml` — CI generates the matrix
- `spec-22-prep-atlas-kedro-cli-introspection.md` — named prep story

Review: 1 medium patch applied; 1 deferred (pre-existing sole-ownership reds in full `pyforge-core-test`); follow-up score 3 → false.

Verification: 141 passed on the spec command subset; `dispatch_argv(['pyforge','steward','keys','list'], …)` → `['steward', 'keys', 'list']`.

## Verification

**Commands:**
- `pixi run -e pyforge-core pytest -q src/shared/packages/pyforge-core/tests/unit src/shared/packages/pyforge-core/tests/meta/test_cli_parity_matrix.py src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — expected: all pass (parity matrix generated; sibling sole-ownership reds are pre-existing and out of this story)
- `python -c "from pyforge.core.dispatch import dispatch_argv; print(dispatch_argv(['pyforge','steward','keys','list'], packages_root=__import__('pathlib').Path('src/shared/packages')))"` from repo root with PYTHONPATH=`src/shared/packages/pyforge-core/src` — expected: `['steward', 'keys', 'list']`
