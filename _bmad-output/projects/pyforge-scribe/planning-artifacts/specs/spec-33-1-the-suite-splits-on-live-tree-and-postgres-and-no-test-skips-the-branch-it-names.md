---
title: '33.1: The suite splits on live_tree and postgres, and no test skips the branch it names'
type: 'fix'
created: '2026-11-10'
status: 'backlog'
difficulty: 'medium'
story: 33-1-the-suite-splits-on-live-tree-and-postgres-and-no-test-skips-the-branch-it-names
spec: spec-pyforge-scribe
surface:
  - src/shared/packages/pyforge-scribe/pyproject.toml
  - src/shared/packages/pyforge-scribe/tests/unit/conftest.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_operations.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_navigation_owner.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_recall_semantic.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_cli.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_compile.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_extras_cocoindex_flow.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_extras_graphify.py
  - src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py
  - src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py
  - src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py
  - src/shared/packages/pyforge-scribe/tests/meta/test_skf_skill_ownership.py
  - src/shared/packages/pyforge-scribe/tests/meta/test_station_persona.py
  - src/shared/packages/pyforge-scribe/tests/meta/test_live_tree_split.py
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-33-1-the-suite-splits-on-live-tree-and-postgres-and-no-test-skips-the-branch-it-names.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - src/shared/packages/pyforge-steward/pyproject.toml
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/cocoindex_flow.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Scribe's suite is not an oracle a second root can run (audit SHOULD S2, S1; decision D2): it has no
live-tree split; four unit modules find the repository by counting parents (`parents[5]`, `parents[6]`); the
Postgres-bound tests fail rather than skip, with no marker saying so; and seven tests of the "extra unavailable"
branches skip whenever graphifyy or cocoindex is installed, which they always are in `-e pyforge-scribe`, the only
environment the suite runs in. Those seven are hollow.

**Approach:** Test-only.

- `pyproject.toml` gains `[tool.pytest.ini_options]` markers: `live_tree` in the wording steward and doctor use
  (`src/shared/packages/pyforge-steward/pyproject.toml`), and `postgres: needs PostgreSQL 17 with pgvector at
  SCRIBE_GRAPH_DSN; fails, never skips, when the server is absent`.
- Module-level `pytestmark = pytest.mark.live_tree` on the five `tests/meta` modules, `test_navigation_owner.py`,
  `test_graph_store_pg.py` and `test_recall_semantic.py`; the `postgres` param of conftest's `graph_store_factory`
  carries both marks (the fixture reads the host's changesets under `src/platform/db/changelog/changes`), so the
  flat-file param of `test_graph_store_operations.py` stays in the package half.
- The parent counting becomes one walk-up finder in `tests/unit/conftest.py`.
- The seven skip-when-installed tests simulate absence instead (`monkeypatch.setitem(sys.modules, 'graphify', None)`,
  likewise cocoindex; the lazy imports sit in `extras/graphify.py` and `extras/cocoindex_flow.py`).
- `tests/meta/test_live_tree_split.py` holds a closed list of the skip sites that remain, each with its reason: the
  four `importorskip` tests of `test_graph_store_plane.py` and the django `importorskip` in `test_first_portal_slice.py`
  (DW-scribe-cutover-2026-11-10-2), the two win32 `skipif`s of `test_instruction_surface_parity.py`, the
  win32-or-root `skipif` in `test_compile.py`, and the two git-missing `skipif`s of `test_catalog_bmad_estate.py`; a
  skip site not on the list fails the guard.

Until steward-station changes the pixi task, `pyforge-scribe-test` still runs both halves, so nothing reds in between.
The new meta-tests of Stories 31.1, 32.1, 32.2, 32.3 and 33.2 carry the marker and must pass this guard.

Ledger key: `33-1-the-suite-splits-on-live-tree-and-postgres-and-no-test-skips-the-branch-it-names`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- `spec-pyforge-scribe` CAP-31, as amended at the 2026-11-10 mint: the oracle clause, held by `test_live_tree_split.py`.
- `spec-pyforge-scribe` CAP-33: the cocoindex-absent branch of `scribe index refresh` runs.
- Relay of `spec-pyforge-steward:CAP-175` (the live-tree split).

## Boundaries & Constraints

**Always:**
- Every pixi command is `--frozen`.
- A test that needs the server fails, never skips, when it is absent.

**Never:**
- Do not change product code.
- Do not edit the root `pixi.toml`, the CI workflow or the trigger map (steward-station's; shared requests).

</intent-contract>

## Acceptance Criteria

- **AC1 — Both markers are registered.**
  `python3 -c "import tomllib,sys;m=tomllib.load(open('src/shared/packages/pyforge-scribe/pyproject.toml','rb'))['tool']['pytest']['ini_options']['markers'];sys.exit(0 if any(x.startswith('live_tree:') for x in m) and any(x.startswith('postgres:') for x in m) else 1)"` exits 0.
- **AC2 — No test finds the repository by counting parents.** `git grep -nE 'parents\[[3-9]\]' -- src/shared/packages/pyforge-scribe/tests` exits 1 (no match).
- **AC3 — No test skips because an extra is installed.** `git grep -nE 'pytest\.skip\("(graphifyy|cocoindex) is installed' -- src/shared/packages/pyforge-scribe/tests` exits 1 (no match).
- **AC4 — All seven "extra unavailable" branches run in the station environment.**
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit -q -k 'unavailable or not_installed' -rs`
  exits 0, its summary line reads `7 passed`, and no line of the report starts with `SKIPPED`.
- **AC5 — The split guard passes and proves itself** (a module that resolves the repository root without the marker,
  a marked module that does not, a postgres-marked test under a skip, a skip on an installed extra, a skip site missing
  from the closed list: each planted and named):
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_live_tree_split.py -q` exits 0.
- **AC6 — The package half runs with the package copied alone, outside the repository.**
  `pixi run --frozen -e pyforge-scribe bash -c 'T=$(mktemp -d) && cp -r src/shared/packages/pyforge-scribe "$T/pkg" && cd "$T/pkg" && PYTHONPATH="$T/pkg/src" python -m pytest tests -m "not live_tree and not postgres" -q -p no:cacheprovider'` exits 0.
- **AC7 — A missing server fails, it does not skip.**
  `SCRIBE_GRAPH_DSN=postgres://postgres:scribe@127.0.0.1:1/none PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py -q -x -rs`
  exits 1, the output names `durable GraphStore requires PostgreSQL`, and no line starts with `SKIPPED`.
- **AC8 — The whole suite with the server up.** `pixi run --frozen -e pyforge-scribe-pg scribe-pg-up && pixi run --frozen -e pyforge-scribe pyforge-scribe-test` exits 0.
- **AC9 — Lint and types.** `pixi run --frozen -e pyforge-guild lint-types` exits 0.

## Binding

- Parent capability: `spec-pyforge-scribe` CAP-31 (amended 2026-11-10); CAP-33's absent-extra branch; relay of
  `spec-pyforge-steward:CAP-175`.
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 33. Ledger key `33-1-the-suite-splits-on-live-tree-and-postgres-and-no-test-skips-the-branch-it-names`,
  minted `backlog`.
- Deps: none. Wave BUILD-1.

## Notes

- Closes audit SHOULD S2 (tests as oracle) and S1 (literals that bind to A's tree).
- Shared requests (steward-station, needed by this story): `pyforge-scribe-test` selects
  `-m "not slow and not live_tree"` and a new `pyforge-scribe-live-test` runs the live half with its own coverage
  report, both in `pyforge-station-tests` and the `pr-preflight` lane table (steward:S-124.1); a `scribe-live-test` CI
  job with the pgvector pg17 service and a `scribe_live_paths` trigger array; a django-scribe lane for the portal
  render test (DW-steward-cutover-2026-11-10-12).

## Spec Change Log

- 2026-11-10: minted with Epic 33 at the cutover-readiness mint.
