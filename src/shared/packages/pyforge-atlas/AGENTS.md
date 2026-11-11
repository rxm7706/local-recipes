# Agent Guidelines

This is a [Kedro](https://docs.kedro.org) project. These guidelines help AI coding assistants work with it correctly.

<!-- bmad:context -->
<!-- Verified 2026-11-11 against 72f3e3158f. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## pyforge-atlas (Kedro/Dagster/DuckDB cf_atlas migration)

The `pyforge.atlas` Kedro project: Kedro pipelines over a Parquet store read through DuckDB, Dagster glue, an MCP
face; Python 3.14, pixi env `pyforge-atlas`. These rules are exclusive to `src/shared/packages/pyforge-atlas/`; the
repo-wide surface is the root `AGENTS.md`. The binding contract is
`_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md` and the companions its
`companions:` frontmatter lists.

## Policy

- Testing contract (CAP-2, `gate-contract.md`): every verify gate is fixture-based, non-credentialed, runs `--frozen`,
  and lives in the tracked `tests/` tree — never `.claude/data/` or another gitignored location. Credentialed runs are
  attended-only.
- Offline or air-gapped degradation is skip-and-mark-stale, never fail (`degradation-contract.md`): keep the last-good
  dataset and reuse it; use the `not-applicable` token for nodes that don't apply offline.
- Import direction (AD-1): only `orchestration/definitions.py` imports `dagster`/`kedro_dagster`, nothing imports
  `kedro_mcp`, and `pipelines/`, `datasets/` and `hooks.py` import no agent framework — the binding meta-test is
  `tests/unit/catalog/test_no_inline_io.py`, run by `kedro-catalog-check`. Core domain logic lives in `pipelines/` and
  `datasets/`; orchestration and MCP concerns are layered above.
- The one cross-station code edge is `pipelines/universal_sbom/gate.py` importing `pyforge.warden` lazily inside its
  nodes, the optional `[gate]` extra in `pyproject.toml`; never vendor warden's schema or add a second station import.
- Naming and schema: pipeline packages snake_case; dataset names `<domain>_<entity>` with a layer-tag suffix; canonical
  join keys are `conda_name` / `pypi_name` / `(conda_name, advisory_id)` — never a purl as an internal join key;
  timestamps normalize to epoch seconds at ingest (never ms or ISO strings in the columnar store); schema evolution is
  additive-first (new columns only; a rename needs a deprecation period); degradation vocabulary is `stale` /
  `unresolved` / `not-applicable` and the three are never interchanged; ported nodes carry a `# legacy: Phase <ID>`
  provenance comment (`CFA` = `conda_forge_atlas.py @ b18cbb5`, the legacy monolith's commit pin).
- Exit codes are frozen (`degradation-contract.md`, CAP-13): `0` pass, `1` policy fail, `2` error/crash, `130`
  interrupted; indeterminate always maps to `1`. Never use any other code. The one exception is the attended La Suite
  bring-up, `tools/lasuite_bringup.py`, which is not a gate and keeps its own `0`–`4` (`3`: no `outputs/` stage or
  nothing synced; `4`: a local read error).
- The `universal_sbom` gate node is the single producer of the four-axis `ComplianceReport` and takes its exit code from
  `pyforge.warden.verdict` (CAP-13). `inventory-match` keeps a one-release `INVENTORY_MATCH_LEGACY_EXIT=1` deprecated
  compatibility window.
- MCP tool bodies in `mcp/tools.py` call only the session seam — `session.run(pipeline_name=..., ...)` or
  `_provenance.load_with_provenance(catalog, ...)` — and a small stdlib allowlist; no `pandas`/`numpy`/`duckdb`/`ibis`/
  `pyarrow` there, data logic stays in `semantic/` and `datasets/` (AST-scanned:
  `tests/unit/mcp/test_no_business_logic_in_tool_bodies.py`). `mcp/server.py` lazy-loads the official `mcp` SDK inside
  `build_server()`, so the package imports with the SDK absent; keep it lazy.
- Credential scoping is declarative in the catalog, not runtime host detection: a catalog entry either has a
  `credentials:` key or it doesn't; `tests/unit/catalog/test_credential_scoping.py` asserts the credentialed-entry set
  against a fixed allowlist and suffix-matches the hostname, so a non-JFrog host never receives `X-JFrog-Art-Api`.
- `observability.py` is the sole module allowed to import `openlineage`/`opentelemetry` (AST-enforced in
  `test_no_inline_io.py`); both backends are no-op by default; nodes stay pure `DataFrame→DataFrame`.
- `IncrementalParquetDataset` (`datasets/incremental_parquet.py`) TTL gotchas: staleness uses strict `<` (not `>=`) to
  match legacy SQL; `ttl_seconds` is injected post-construction by `hooks.py` from `params:ttls.<name>`, never passed at
  catalog-resolution time; the outer Kedro `version:` kwarg is rejected with `ValueError` (IO delegates to a composed
  inner `ParquetDataset`, and Kedro version tracking would break that delegation).
- Pipeline registration (`pipeline_registry.py`) uses `find_pipelines(raise_errors=True)` and guards the empty-scaffold
  case (`sum()` over an empty dict is `int 0`, not a `Pipeline`). Pipelines wire nodes via `inputs=`/`outputs=`
  catalog-name strings, never procedural calls — Kedro resolves DAG order from the declared edges.
- Semantic layer (CAP-8): metric expressions are Ibis; `semantic/query_helpers.py` shapes the returned frame with
  pandas. Reads go through Ibis table objects (`con.read_parquet(...)` returns an Ibis table), never raw SQL;
  orchestration nodes stay `DataFrame→DataFrame` at the boundary only.
- Pandera is the shipped default validator. Great Expectations participates only at conda-forge 1.18.2 semantics
  (`validation.py`, AD-9): the shipped path never imports `great_expectations`; `GreatExpectationsBoundaryValidator`
  sits behind the validator-agnostic hook and is never load-bearing until conda-forge's own GX pin reaches 1.19.
- Pixi-first, Python 3.14 floor, conda-forge-only toolchain; no pip-installed packages outside pixi (CAP-72).
- Any story touching recipe code or atlas tooling invokes `conda-forge-expert` first, and a closed conda-forge effort
  ends with its retro (root `AGENTS.md` § Where things are).

## Where things are

- Gates and their tests: `pyforge-atlas-test` (the whole suite; `kedro-test` is its alias), `kedro-catalog-check` →
  `tests/unit/catalog/`, `parity-diff` → `tests/unit/parity/`, `dagster-dryrun` → `tests/unit/orchestration/`,
  `bsl-metric-check` → `tests/unit/semantic/`, `duckdb-singularity` → `tests/unit/singularity/`,
  `query-plane-parity` → `tests/unit/query_plane/`, `vizro-ai-dryrun` → `tests/unit/nl/`, `dashboard-dryrun` →
  `tests/integration/dashboard/`, `wasm-smoke` → `tests/integration/wasm/`, `publish-range` →
  `tests/integration/publish/`. Read each task's environment from the root `pixi.toml`.
- Fixtures: `tests/fixtures/data/` (static Parquet data root for offline gate runs, regenerated by its
  `build_fixture_data.py`), `tests/fixtures/inventory_identity/`, `tests/fixtures/json_sources/`; the parity snapshots
  sit in `tests/unit/parity/fixtures/`.
- Module layout is live and grows (`pipelines/`, `datasets/`, `mcp/`, `semantic/`, `a2a/`, `artifactory/`,
  `trending_candidates/`, …) — read the directory, don't cite a frozen listing here; one already went stale between
  2026-08-24 and 2026-09-06.

## Running and verifying

- The suite has two halves. A test module that reads the repository outside this package (planning artifacts, docs,
  the root `pixi.toml`, the workflows, `scripts/`, `recipes/`, `.claude/`, another package's tree, git state) carries
  `pytestmark = pytest.mark.live_tree` (the marker is registered in `pyproject.toml`) and runs in the live-tree half,
  `-m live_tree`; never skip, `xfail` or delete it instead. The package half, `-m "not live_tree"`, must pass from an
  exported copy of this package alone.

## Known pitfalls

- Worktree/BMAD: loop stories run in worktrees only after the symlink bootstrap; all BMAD writes resolve through the
  `_bmad-output` symlinks; switch the active project with `scripts/bmad-switch pyforge-atlas` (never hand-edit the
  symlinks) — except from a parallel agent, which sets `BMAD_ACTIVE_PROJECT=pyforge-atlas` and writes
  `_bmad-output/projects/pyforge-atlas/` paths, per the root `AGENTS.md`.
- Incremental re-materialization is the headline claim (CAP-3) and must be benchmarked, not assumed. Cold-start
  performance is benchmarked, never promised; per-node timeouts are explicit so the 1800s coarse-cap
  silent-phase-drop stays structurally impossible (CAP-4).

<!-- /bmad:context -->

<!-- kedro-skills:catalog-config:start -->
## Catalog config

Kedro catalog configuration guidance for conf/**/*.yml files. Use when adding datasets, editing catalog entries, setting up factories, or working with credentials and parameter interpolation.

IMPORTANT: When working on files matching `conf/**/*.yml`, `conf/**/*.yaml`, do NOT answer from internal knowledge.
You MUST read `.agents/skills/catalog-config/SKILL.md` BEFORE writing, editing, or suggesting changes to them.
Your training data is likely outdated — that file holds the current, verified guidance.
If you cannot read the file, tell the user instead of guessing.
<!-- kedro-skills:catalog-config:end -->
