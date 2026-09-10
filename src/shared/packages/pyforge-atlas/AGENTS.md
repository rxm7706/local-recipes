# Agent Guidelines

This is a [Kedro](https://docs.kedro.org) project. These guidelines help AI coding assistants work with it correctly.

<!-- bmad:context -->
<!-- Verified 2026-09-06 against 9e91e2e7cb. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## pyforge-atlas (Kedro/Dagster/DuckDB cf_atlas migration)

Subtree-exclusive rules for `src/shared/packages/pyforge-atlas/` — the repo-wide surface is the
root `AGENTS.md`. Recovered 2026-09-06 (Story 30.2) from the retired `pyforge-atlas/project-context.md`
rulebook; content confirmed still true against the live tree, not carried over unverified.

## Policy

- **Testing Contract (NFR-1/2/5):** every verify gate is fixture-based, non-credentialed, runs
  `--frozen`, and lives in the tracked `tests/` tree — never `.claude/data/` or another gitignored
  location. A non-JFrog host never receives `X-JFrog-Art-Api`. Credentialed runs are attended-only.
  Offline/air-gapped degradation is skip-and-mark-stale, never fail (NFR-3) — keep the last-good
  dataset and reuse it; use the `not-applicable` token for nodes that don't apply offline.
- **Architectural Boundaries — import-direction (AD-1, NFR-5):** no Dagster, `kedro-mcp`, or agent
  imports in `pipelines/`, `datasets/`, `hooks.py`. Core domain logic lives in `pipelines/` and
  `datasets/`; orchestration/MCP concerns are layered above. This is a binding meta-test that ships
  with `kedro-catalog-check` and must pass in CI.
- **Naming & schema consistency:** pipeline packages snake_case; dataset names `<domain>_<entity>`
  with a layer-tag suffix; canonical join keys are `conda_name` / `pypi_name` /
  `(conda_name, advisory_id)` — never a purl as an internal join key; timestamps normalize to epoch
  seconds at ingest (never ms or ISO strings in the columnar store); schema evolution is
  additive-first (new columns only; a rename needs a deprecation period); degradation vocabulary is
  `stale` / `unresolved` / `not-applicable` and the three are never interchanged; ported nodes carry
  a `# legacy: Phase <ID>` provenance comment (`CFA` = `conda_forge_atlas.py @ b18cbb5`, the legacy
  monolith's commit pin).
- **Exit-Code Convention — frozen, universal (NFR-6):** `0` pass, `1` policy fail, `2` error/crash,
  `130` interrupted. Indeterminate always maps to `1`. Never use any other code.
- **Compliance Report Structure (NFR-6, FR-18):** every gate produces a four-axis `ComplianceReport`
  (or compatible JSON) with the frozen exit-code convention above, for the CI exit-code gate.
  `inventory-match` keeps a one-release `INVENTORY_MATCH_LEGACY_EXIT=1` deprecated compatibility
  window.
- **MCP tool bodies are exactly one of two shapes** (AST-scanned test, `mcp/tools.py`):
  `session.run(pipeline_name=..., ...)` or `_provenance.load_with_provenance(catalog, ...)`. No
  direct `ibis`/`pandas`/`duckdb` imports there — data logic stays in `semantic/`/`datasets/`.
  `mcp/server.py` lazy-imports fastmcp inside `build_server()` so the module imports without
  fastmcp/kedro_mcp present.
- **Credential scoping is declarative in the catalog, not runtime host-detection**: a catalog entry
  either has a `credentials:` key or it doesn't; `tests/catalog/test_credential_scoping.py` asserts
  the credentialed-entry set against a fixed allowlist and guards JFrog-substring tricks with a
  real suffix-match on the hostname.
- **`observability.py` is the sole module allowed to import `openlineage`/`opentelemetry`**
  (AST-enforced); both backends are no-op by default; nodes stay pure `DataFrame→DataFrame`.
- **`IncrementalParquetDataset` (`datasets/incremental_parquet.py`) TTL gotchas:** staleness uses
  strict `<` (not `>=`) to match legacy SQL; `ttl_seconds` is injected post-construction by
  `hooks.py` from `params:ttls.<name>`, never passed at catalog-resolution time; the outer Kedro
  `version:` kwarg is rejected with `ValueError` (IO delegates to a composed inner
  `ParquetDataset`, and Kedro version tracking would break that delegation).
- **Pipeline registration** (`pipeline_registry.py`) uses `find_pipelines(raise_errors=True)` and
  guards the empty-scaffold case (`sum()` over an empty dict is `int 0`, not a `Pipeline`).
  Individual pipelines wire nodes via `inputs=`/`outputs=` catalog-name strings, never procedural
  calls — Kedro resolves DAG order from the declared edges.
- **Semantic Layer reading discipline (FR-8, Ibis→DuckDB):** `semantic/` metric expressions are
  pure Ibis (`ibis.Expr`), never pandas or raw SQL — reads go through Ibis table objects
  (`con.read_parquet(...)` returns an Ibis table, not a DataFrame); orchestration nodes stay
  `DataFrame→DataFrame` at the boundary only.
- **Pandera is the shipped default validator** for data-quality contracts before bad data lands.
  **Great Expectations participates only at conda-forge 1.18.2 semantics** (`validation.py`,
  AD-9) — the in-env GX is 1.19.0, which cannot be statically guaranteed to stay within
  1.18.2-only features, so GX sits behind a validator-agnostic hook and is never load-bearing
  until conda-forge's own GX pin catches up to 1.19. (An earlier draft of this note
  mis-attributed the 1.18.2 cap to Pandera too; corrected 2026-09-06 against `validation.py`'s
  own docstring, the only tracked place either constraint is stated.)
- Pixi-first, Python 3.14 floor, conda-forge-only toolchain; no pip-installed packages outside pixi.
- Any story touching recipe code or atlas tooling invokes `conda-forge-expert` first (CLAUDE.md
  Rule 1); a closed conda-forge effort ends with the Rule-2 retro.

## Where things are

- Verify gates: `kedro-test` (import smoke + scaffold layout), `kedro-catalog-check` (AD-1
  meta-tests), `parity-diff` (fixture-mode parity vs legacy snapshots), `dagster-dryrun`
  (Definitions load-only, no daemon), `bsl-metric-check` (semantic metric-parity).
- Fixtures: `tests/fixtures/parity/` (captured legacy snapshots), `tests/fixtures/credentials/`
  (safe non-secret placeholders), `tests/fixtures/data/` (static Parquet for offline gate runs).
- Spec (binding contract): `docs/specs/cfe-atlas-datapipeline-kedro-migration.md`.
- Module layout is live and grows (`pipelines/`, `datasets/`, `mcp/`, `semantic/`, `a2a/`,
  `artifactory/`, `trending_candidates/`, …) — read the directory, don't cite a frozen
  listing here; one already went stale between 2026-08-24 and 2026-09-06.

## Known pitfalls

- Worktree/BMAD: loop stories run in worktrees only after the symlink bootstrap; all BMAD writes
  resolve through the `_bmad-output` symlinks; switch the active project with
  `scripts/bmad-switch pyforge-atlas` (never hand-edit the symlinks) — except from a parallel
  agent, per the root AGENTS.md's parallel-agents rule.
- Incremental re-materialization is the headline claim (NFR-4) and must be benchmarked, not
  assumed. Cold-start performance is benchmarked, never promised; per-node timeouts are explicit
  so the 1800s coarse-cap silent-phase-drop stays structurally impossible (NFR-9).

<!-- /bmad:context -->

<!-- kedro-skills:catalog-config:start -->
## Catalog config

Kedro catalog configuration guidance for conf/**/*.yml files. Use when adding datasets, editing catalog entries, setting up factories, or working with credentials and parameter interpolation.

IMPORTANT: When working on files matching `conf/**/*.yml`, `conf/**/*.yaml`, do NOT answer from internal knowledge.
You MUST read `.agents/skills/catalog-config/SKILL.md` BEFORE writing, editing, or suggesting changes to them.
Your training data is likely outdated — that file holds the current, verified guidance.
If you cannot read the file, tell the user instead of guessing.
<!-- kedro-skills:catalog-config:end -->
