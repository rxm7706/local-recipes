---
title: "31.1: Scribe's public contract is written down, and a meta-test holds it"
type: 'feature'
created: '2026-11-10'
status: 'done'
flag-exempt: detector-or-gate   # a contract record and the meta-test that judges it; a gated gate reports a silent green (spec-feature-flag-governance Q2)
difficulty: 'medium'
story: 31-1-scribe-s-public-contract-is-written-down-and-a-meta-test-holds-it
spec: spec-pyforge-scribe
surface:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/contract.md
  - src/shared/packages/pyforge-scribe/tests/meta/test_public_contract.py
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-31-1-scribe-s-public-contract-is-written-down-and-a-meta-test-holds-it.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - docs/dreams/pyforge-scribe.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py
  - src/shared/packages/django-scribe
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** At `82a2b18828` the scribe Spec names three of the CLI's five command groups (`capture`, `recall`,
`graph`, `index`, `catalog`), no MCP tool and no environment variable (audit MUST 4, decision D1). The code is right;
the record of its public contract is missing, and nothing stops a new verb, flag or variable from shipping unrecorded.

**Approach:** A Spec companion, `spec-pyforge-scribe/contract.md`, with one table per family, and a meta-test that
derives the code side and fails naming each item the companion lacks. No product code.

- **CLI verbs and flags:** a row per verb path, each starting `` | `scribe <path>` | ``: `capture` (`--type`,
  `--text`, `--promote`, `--transcripts`, `--source`), `recall`, `graph compile`, `index build`, `index report`,
  `index move-list` (marked retired with CAP-34; the verb stays until a Story removes it), `index refresh`,
  `catalog bmad-estate` (`--write`, `--check`, `--root`, `--output`, `--pipeline-truth`); the same tree is reached as
  `pyforge scribe`.
- **MCP tools:** `start_recall`, `get_recall`, the runner `run_recall`, served at `POST /stations/scribe/mcp`; the host
  code is django-scribe's, under `spec-pyforge-unifying-strategy:CAP-20`.
- **Feature-flag keys:** `pyforge.scribe.bmad_estate_catalog`.
- **Environment variables:** the package's (`SCRIBE_GRAPHIFY_EXTRA`, `SCRIBE_COCOINDEX_EXTRA`, `SCRIBE_GRAPH_DSN`,
  `DATABASE_URL`, `PYFORGE_GRAPHSTORE_OWNER`, `QUERY_PLANE_DUCKDB`); the surface scripts' (`PYFORGE_SCRIBE_TRIGGER_BACKEND`,
  `SCRIBE_PG_SOCKET_DIR`, `XDG_RUNTIME_DIR`, `PIXI_BIN`, `USER`); inherited through `pyforge.core`
  (`PYFORGE_FLAGS_PATH`, `PYFORGE_ENVIRONMENT`).
- **Exit codes:** scribe's 0, 1 (catalog drift) and 2 (usage or could-not-run), and each surface script's own codes.

`tests/meta/test_public_contract.py` derives the code side: the click tree of `pyforge.scribe.cli.app` for verbs and
flags, an AST scan of `typer.Exit(code=)` and of `os.environ` reads over the package and the surface scripts, string
literals matching `pyforge.<station>.<name>` for flag keys, and the `*_TOOL` constants of django-scribe's
`mcp_asgi.py` read as text. It reads outside the package, so it carries `pytestmark = pytest.mark.live_tree` from its
first commit (Story 33.1 registers the mark; until then an unregistered mark is a warning).

Ledger key: `31-1-scribe-s-public-contract-is-written-down-and-a-meta-test-holds-it`.
Type / Effort / Deps: feature (flag-exempt: detector-or-gate) / M / none.

### Living CAP citations

- `spec-pyforge-scribe` CAP-4, as amended at the 2026-11-10 mint (FR-54): five command groups and a written contract,
  held by this test. This story contributes the contract half of audit MUST 4; the finding closes with Story 31.2's
  re-derive, which lists `contract.md` under `companions:`.

## Boundaries & Constraints

**Always:**
- Read the portal and the host as text; every pixi command is `--frozen`.
- Name the missing item and its family in the failure message.

**Never:**
- Do not change a verb, a flag or an exit code: this story records the contract, it does not move it.
- Do not import `django`, `django_scribe_portal` or `django_pyforge` from the test.
- Do not edit `SPEC.md` (Story 31.2 re-derives it).

</intent-contract>

## Acceptance Criteria

- **AC1 — The contract test passes on the live tree.**
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_public_contract.py -q` exits 0.
- **AC2 — The guard fires.** A contract text missing one item of each family (verb path, flag, MCP tool, flag key,
  environment variable, exit code) is reported by name:
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_public_contract.py -q -k test_checker_names_a_missing` exits 0 and its summary line reads `6 passed`.
- **AC3 — Every verb path is a row.**
  `grep -cE '^\| `scribe (capture|recall|graph compile|index build|index report|index move-list|index refresh|catalog bmad-estate)` ' _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/contract.md` prints 8.
- **AC4 — MCP tools, the flag key and the driver variables are named.**
  `grep -c -e start_recall -e get_recall -e pyforge.scribe.bmad_estate_catalog -e SCRIBE_GRAPH_DSN -e PYFORGE_GRAPHSTORE_OWNER -e QUERY_PLANE_DUCKDB -e SCRIBE_GRAPHIFY_EXTRA -e SCRIBE_COCOINDEX_EXTRA -e PYFORGE_SCRIBE_TRIGGER_BACKEND -e SCRIBE_PG_SOCKET_DIR _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/contract.md` prints 10 or more.
- **AC5 — No host or portal import.**
  `git grep -nE '^(from|import) (django|django_scribe_portal|django_pyforge)' -- src/shared/packages/pyforge-scribe/tests/meta/test_public_contract.py` exits 1 (no match).
- **AC6 — Lint and types.** `pixi run --frozen -e pyforge-guild lint-types` exits 0.

## Binding

- Parent capability: `spec-pyforge-scribe` CAP-4 (amended 2026-11-10); FR-54.
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 31. Ledger key `31-1-scribe-s-public-contract-is-written-down-and-a-meta-test-holds-it`, minted `backlog`.
- Deps: none. Wave BUILD-1 of the cutover-readiness plan.

## Notes

- Shared request (steward-station, needed by this story): the scribe live-test trigger paths gain the scribe Spec
  folder's `contract.md`, `src/shared/packages/django-scribe`, `scripts/scribe_*.py` and `scripts/bmad_estate_check.py`,
  each declared in `ROOT_HANDOFF_INPUTS` where the test hands over the root (steward's trigger-map test).
- The `Surface reconcile` event for the paths this story moves is written by the scribe closer, Story 31.4; no build
  story stamps a baseline (doctor:S-58.4 runs every scoped stamp once).
- Every direct pytest command carries the task's `PYTHONPATH` so the live source is imported.

## Spec Change Log

- 2026-11-10: minted with Epic 31 at the cutover-readiness mint, from the station Dream's entry of the same date.

## Gate findings (build, BUILD-1)

- 2026-11-11, `pixi run -e pyforge-scribe pyforge-scribe-test`: Story 33.1's split guard (`test_live_tree_split.py::test_the_suite_splits_on_live_tree_and_postgres_and_skips_only_listed_sites`) named `tests/meta/test_public_contract.py` for resolving the repository root at import (`ROOT = _repo_root()` in the module body). Fixed in that file: `_repo_root()` is cached with `functools.cache`, and the module constants are now the helpers `_packages()`, `_contract()` and `_mcp_asgi()`, called only inside the tests and fixtures. Both modules pass (37 tests), ruff check and format are clean, and the station suite exits 0 (533 passed, 5 skipped).
