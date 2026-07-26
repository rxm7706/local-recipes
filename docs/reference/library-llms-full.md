# local-recipes — Library Catalog for LLMs & Agents (library-llms-full.md)

> Purpose: give any LLM or coding agent a complete, self-contained picture of every
> library, CLI, and framework available in this repository's pixi environments —
> what each one is, what it is capable of, how to import/invoke it, and which
> environment provides it.
>
> Source of truth: `pixi.toml` (workspace "staged-recipes" v0.2.0). This file is a
> derived catalog — regenerate it whenever `pixi.toml` changes.
> Generated: 2026-07-12; incrementally updated 2026-07-18 (pyforge-atlas member env + kedro-viz; pyforge-warden + bmad-ui envs; pin corrections) and 2026-07-25 (the pyforge-herald / -doctor / -scribe member envs, then pyforge-mason / -steward / -marshal at Story 1.1 — eight `pyforge` packages, 18 envs). Channels: conda-forge + SelfExplainML.
> Platforms: linux-64, win-64, osx-arm64 (macOS >= 14.5 "Sonoma" floor, required by mlx).

## To regenerate (any session): ask Claude Code:

> Regenerate `docs/reference/library-llms-full.md` from `pixi.toml`. Read all of `pixi.toml`, then rewrite the catalog keeping the same 18-section structure: envs table, version pins, per-category library entries with version floors + capabilities + platform caveats, the "explicitly NOT available" section from the commented-out deps, the import-name gotchas table, and the quick capability index. Update the Generated date. Verify with `pixi run -e local-recipes llms-full-check`.

**Staleness detector:** `pixi run -e local-recipes llms-full-check` (script:
`scripts/llms_full_check.py`) exits non-zero when this catalog drifts from `pixi.toml` —
undocumented deps, ghost entries, or version-floor drift. Detector finds; the regeneration
prompt above reconciles.

---

## 0. How to use anything in this catalog

Everything runs through pixi environments. Nothing here is installed globally.

    pixi shell -e local-recipes                 # enter the main environment
    pixi run -e local-recipes python script.py  # one-shot: run python with all libs below
    pixi run -e local-recipes <task> -- <args>  # run one of the ~80 predefined tasks
    pixi run -e vuln-db vdb-refresh             # tasks scoped to other envs

- **Default / kitchen-sink environment: `local-recipes`.** Unless an entry says
  otherwise, every library in this catalog is importable there.
- **Python is 3.14.x in every environment.** If a library you want to add doesn't
  support 3.14, it won't resolve here.
- Node.js 24 (LTS) is present, so npm-ecosystem CLIs (pnpm, yarn, marp, pptxgenjs, yo)
  work inside the env too.
- The repo also exposes conda-forge recipe tooling as pixi tasks and as the
  `conda_forge_server` MCP server — see `CLAUDE.md` and
  `.claude/skills/conda-forge-expert/` for that layer. This file covers the
  *libraries*, not the factory tasks.

### Environments at a glance

| Environment    | Composed of (features)                                | Use it for |
|----------------|-------------------------------------------------------|------------|
| `local-recipes`| python + build + grayskull + conda-smithy + local-recipes | **Default.** Everything: recipe tooling, data stack, ML/LLM, docs, web, agents |
| `build`        | python + build                                        | Minimal conda-build/rattler-build runs |
| `linux`        | linux + python                                        | Docker-driven staged-recipes builds (`build-linux`) |
| `osx` / `win`  | os feature + python + build                           | Native macOS / Windows staged-recipes builds |
| `grayskull`    | python + grayskull                                    | Recipe generation only (`pypi`, `cran` tasks) |
| `conda-smithy` | python + conda-smithy + shellcheck                    | Recipe linting only (`lint` task) |
| `vuln-db`      | python + vuln-db                                      | AppThreat multi-source CVE DB + SBOM work (kept out of local-recipes to stay lean) |
| `gcloud`       | python + gcloud-sdk                                   | One-time `gcloud auth application-default login`; linux/macOS only |
| `pyforge-warden`| pyforge-warden (no-default-feature)                  | Lean env for the built `pyforge-warden` package (`src/shared/packages/pyforge-warden` path dep -> conda pkg + run-deps + pytest; test-oracles py-rattler / py-rattler-build / conda-build). Multi-axis dependency-compliance gate; CLI `warden` (`warden-scan` task), gate `pyforge-warden-test`. Spec: `docs/specs/pyforge-warden.md` |
| `pyforge-atlas`| pyforge-atlas (no-default-feature)                    | Lean env for the `pyforge.atlas` Kedro pipeline member (`src/shared/packages/pyforge-atlas` path dep -> built conda pkg + kedro/kedro-datasets/kedro-dagster/pyforge-warden run-deps + pytest/hatchling/python-build + **kedro-viz**). Loop worktrees materialize THIS env; gates: `kedro-test`, `kedro-catalog-check`, `dagster-dryrun`, `viz` |
| `pyforge-herald`| pyforge-herald (no-default-feature)                  | Lean env for the built `pyforge-herald` package (`src/shared/packages/pyforge-herald` path dep -> conda pkg + **mcp** run-dep + pytest/hatchling/python-build). Herald is the Design<->Code bridge; `mcp` is its Story-1.2 primary transport. Spec: `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/` |
| `pyforge-doctor`| pyforge-doctor (no-default-feature)                  | Lean env for the built `pyforge-doctor` package (`src/shared/packages/pyforge-doctor` path dep -> conda pkg + pytest/hatchling/python-build). Fleet-health station. Spec: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/` |
| `pyforge-scribe`| pyforge-scribe (no-default-feature)                  | Lean env for the built `pyforge-scribe` package (`src/shared/packages/pyforge-scribe` path dep -> conda pkg + pytest/hatchling/python-build). Knowledge/narration station; inherits the `src/sentinel/` knowledge-graph lineage. Spec: `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/` |
| `pyforge-mason`| pyforge-mason (no-default-feature)                    | Lean env for the built `pyforge-mason` package (`src/shared/packages/pyforge-mason` path dep -> conda pkg + pytest/hatchling/python-build). The Artisan Builder's CLI (`mason recipe`/`package`/`environment`); **no CLI-framework dep by contract** (FR-41 forbids click/typer — argparse only). Tasks: `pyforge-mason-build{,-conda,-dist}`, `pyforge-mason-test`. Spec: `_bmad-output/projects/pyforge-mason/planning-artifacts/` |
| `pyforge-steward`| pyforge-steward (no-default-feature)                | Lean env for the built `pyforge-steward` package (`src/shared/packages/pyforge-steward` path dep -> conda pkg + pytest/hatchling/python-build). The Provisioner's CLI (`steward keys`/`deploy`/`provision`/`budget`); task names mirror `pyforge-warden`'s verbatim. Spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/` |
| `pyforge-marshal`| pyforge-marshal (no-default-feature)                | Lean env for the built `pyforge-marshal` package (`src/shared/packages/pyforge-marshal` path dep -> conda pkg + pytest/hatchling/python-build + **import-linter**). Marshal is the harness/orchestration station; `import-linter` is load-bearing, not incidental — it enforces AD-3 (only `adapters/harness_bmadloop.py` may import `bmad_loop`) and AD-4 (`core/**` imports no `subprocess`/`os`/`time`/`adapters`) as **build-breaking contracts** rather than conventions. Task: `pyforge-marshal-test`. Spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/` |
- **graphviz** (>=14.1.2) — Graph layout engine (the `dot` binary); drives the
  kedro-viz prototype's DAG-image (SVG) emitter.
- **python-graphviz** (>=0.21) — Python interface to Graphviz — **imports as
  `graphviz`**; used by the prototype DAG-image generator.
- **graphviz2drawio** (>=1.2.0) — Convert Graphviz/DOT output into editable
  draw.io (mxGraph) XML diagrams.
| `bmad-ui`      | bmad-ui (no-default-feature)                          | **linux-64 only.** BMad Method UI dashboards (`docs/specs/bmad-loop-adoption.md` W4). Consumes the locally-built consume-not-submit mirrors `bmad-dashboard` + `mybmad-dashboard` from `./build_artifacts/linux64` + conda-forge. Tasks: `bmad-dashboard-install` (wires the VS Code extension), `mybmad` (Next.js dashboard + local PostgreSQL on :3002) |

### Version pins agents must respect (don't fight the resolver)

- `python = ">=3.14.6,3.14.*"` at the workspace root (3.14.* in each feature) — check
  3.14 compat before suggesting new deps.
- `pandas >=1.5.3,<3` and `pyarrow >=13,<22` + `pyarrow-all >=21` → pandas 2.x, pyarrow 21.x.
- `tomlkit <0.13.3` (dagster-dg-core pin), `structlog >24.2.0,<26` (xorq/BSL pin),
  `sqlglot >26.32.0,<28.7.0`.
- LTS pins: `django 5.2.x`, `wagtail 7.4.x`, `coderedcms 6.x`, `channels 4.x`,
  `daphne 4.x`, `nodejs 24.x`.
- `pydantic` is not pinned directly but is present transitively (pydantic-ai, fastmcp,
  agno, etc. all pull pydantic v2).

---

## 1. Core runtime & package management

Available in every environment (the `python` feature + workspace `[dependencies]`).

- **python** (>=3.14.6, 3.14.*) — CPython interpreter. All Python libs below target 3.14.
- **pixi** (>=0.73.0) — the package/environment manager itself, available *inside*
  envs for nested workspace operations. `pixi-build` preview is enabled (unlocks
  `[package]`/build tables for the **eight** `pyforge` workspace members under
  `src/shared/packages/` — `pyforge-warden`, `pyforge-atlas`, `pyforge-herald`,
  `pyforge-scribe`, `pyforge-doctor`, `pyforge-mason`, `pyforge-steward`,
  `pyforge-marshal` — each pulled in as a path dependency by its own lean `no-default-feature` env, and each sharing the one PEP 420 implicit
  `pyforge` namespace).
- **conda** (>=26.5.0) — classic conda package manager; needed by conda-build,
  conda-smithy 2026.x, and `conda pypi`.
- **pip** (>=26.1.2) — standard Python installer (prefer `uv` for speed).
- **uv** (>=0.11.32) — Rust-based, very fast pip/pip-tools replacement: `uv pip install`,
  `uv venv`, `uv pip compile` for lock-style resolution.
- **nodejs** (24.x LTS) — `node` / `npm` / `npx`; runtime for the JS tools below.
- **gh** (>=2.96.0) — GitHub CLI: PRs, issues, releases, `gh api` for raw REST/GraphQL,
  `gh pr checks`, workflow dispatch. The repo's primary GitHub automation surface.
- **gitpython** (>=3.1.57) — `import git`; programmatic Git (repos, diffs, commits,
  remotes) when shelling out to `git` is awkward.
- **truststore** (>=0.10.4) — `import truststore; truststore.inject_into_ssl()`; makes
  Python TLS use the OS trust store (corporate CAs, JFrog). Set `TRUSTSTORE=1` pattern
  used by the vuln-db tasks.
- **bmad-method** (>=6.10.0) — BMAD-METHOD CLI (`bmad`): AI-driven agile
  planning/dev framework (agents, workflows, story lifecycle). See § 12.
- **spec-kit** (>=0.14.2) — GitHub Spec Kit (`specify` CLI) for spec-driven
  development scaffolding (constitution → specify → plan → tasks → implement).

---

## 2. Conda / conda-forge packaging toolchain

The heart of the factory. In `build`, `grayskull`, `conda-smithy`, and `local-recipes`
per the table above; all of them coexist in `local-recipes`.

Build engines & solvers:
- **conda-build** (>=25.3.1) — v0 recipe engine: builds `meta.yaml` recipes, renders
  Jinja2, runs tests. Never mix v0 and v1 recipes in one build run.
- **rattler-build** (>=0.70.1) — Rust-native v1 recipe engine: builds `recipe.yaml`,
  much faster than conda-build, first-class cross-compilation. Primary local build tool.
- **py-rattler** (>=0.22.0) — `import rattler`; Python bindings to the rattler libs:
  solve environments, fetch/inspect .conda artifacts, repodata handling — programmatic
  conda operations without shelling out.
- **py-rattler-build** (>=0.70.1) — Python bindings to rattler-build (drive v1 builds
  from Python).
- **conda-libmamba-solver** (>=24.9.0) — fast libmamba solver backend for conda.
- **conda-index** (>=0.3.0) — generate `repodata.json` for local file:// channels
  (e.g. serving `build_artifacts/` as a channel).
- **rattler-build-conda-compat** (>=1.2.0,<2) — compat shims letting conda-forge
  tooling (smithy/CI) understand v1 recipes.

Recipe generation & migration:
- **grayskull** (>=2.7.3) — auto-generate conda recipes from PyPI or CRAN metadata;
  `--use-v1-format` for rattler-build recipes; also the source of the PyPI↔conda name
  mapping the factory caches.
- **conda-recipe-manager** (>=0.8.0) — parse, lint, and migrate recipes v0 ↔ v1
  programmatically (CRM library + `crm` CLI).
- **feedrattler** (>=0.3.14) — convert an existing conda-forge feedstock from v0
  `meta.yaml` to v1 `recipe.yaml` end-to-end.

Linting & feedstock management:
- **conda-smithy** (>=3.44.6,<4) — feedstock generator + `conda-smithy recipe-lint`
  (CI-parity recipe linting; note: CalVer 2026.x needs the `conda` pkg — for strict
  CI-parity use `pixi exec conda-smithy recipe-lint`).
- **conda-forge-ci-setup** (>=4.9.3,<5) — the scripts conda-forge CI itself runs;
  ensures local builds match Azure CI behavior.
- **conda-forge-pinning** (*) — the global pinning manifest (`conda_build_config.yaml`)
  that supplies `${{ python_min }}`, compiler versions, ABI pins.
- **frozendict** (*) — immutable dict; transitive build dep, importable.

Environment packaging & interop:
- **conda-lock** (>=4.0.2) — cross-platform lockfiles for conda envs from
  environment.yml / pyproject.
- **conda-pack** (>=0.9.2) — bundle a live conda env into a relocatable tarball
  (air-gapped deployment).
- **conda-pypi** (>=0.11.0) — safer PyPI interop for conda envs (`conda pypi install`).

Shell/CI quality:
- **shellcheck** (>=0.10.0) — static analysis for `build.sh` and all shell scripts.

---

## 3. Pixi ecosystem extensions

All in `local-recipes`. These are CLIs invoked as `pixi-<name>` or `pixi <name>`.

- **pixi-build-rattler-build / pixi-build-cmake / pixi-build-python / pixi-build-rust**
  — pixi build backends: let a `pixi.toml` `[package]` build conda packages from
  rattler-build recipes, CMake projects, Python projects (PEP 517), or Cargo crates
  respectively.
- **pixi-pack** (>=0.7.10) / **pixi-unpack** (>=0.7.10) — bundle a pixi environment into a
  single archive for offline/air-gapped machines, and unpack it there.
- **pixi-to-conda-lock** (>=0.4.3) — convert `pixi.lock` → `conda-lock.yml` for tools
  that only understand conda-lock.
- **pixi-diff** (>=0.1.7) — diff two `pixi.lock` files (what changed between lock states).
- **pixi-outdated** (>=0.2.1) — list dependencies in `pixi.toml` with newer versions
  available.
- **pixi-inject** (>=0.1.3) — inject extra conda packages into an existing pixi env
  without editing the manifest.
- **pixi-install-to-prefix** (>=0.1.6) — install a pixi env to an arbitrary directory
  prefix.
- **pixi-inspect** (>=2.0.2) — inspect/retrieve metadata from a conda package.
- **pixi-kernel** (>=0.7.1) — Jupyter kernels backed by pixi envs.
- **pixi-pycharm** (>=0.0.12) — PyCharm/IDE interpreter integration for pixi.
- **pixi-skills** (>=0.1.5) — manage coding-agent skills using pixi.
- **nebi-cli** (>=0.13) — `nebi`; local-first workspace management for pixi projects.

---

## 4. Python build, publish & supply-chain security

All in `local-recipes`.

- **setuptools** (>=81) / **wheel** (>=0.47) — classic build backend + wheel format
  utilities.
- **setuptools-scm** (>=10.2) — derive package versions from git tags.
- **hatchling** (>=1.31) — modern PEP 517 build backend (Hatch).
- **python-build** (>=1.5) — PEP 517 frontend: `python -m build` produces sdist+wheel
  from any backend.
- **twine** (>=6.2) — upload artifacts to PyPI (check + upload).
- **pip-audit** (>=2.10.1) — audit installed Python environments / requirements
  against known-vulnerability databases (OSV/PyPI advisory).
- **bandit** (>=1.9.4) — static security linter for Python source (dangerous calls,
  injection patterns, weak crypto).
- **deptry** (>=0.25.1) — dependency-hygiene checker: finds unused, missing, and
  transitive dependencies in a Python project by comparing imports against the
  declared manifest (core of the pyforge-warden effort).
- **osv-scanner** (>=2.4.0) — Google's OSV vulnerability scanner (Go binary): scans
  lockfiles, manifests, SBOMs, and directories against the osv.dev database.
- **appthreat-vulnerability-db** (>=6.7.0) — `import vdb`; AppThreat multi-source
  vulnerability database library (OSV + GHSA sources locally; CVE, EPSS, CWE data
  model). Present in BOTH `local-recipes` and `vuln-db`; the ~600MB local DB lives at
  `.claude/data/conda-forge-expert/vdb/` (built via `pixi run -e vuln-db vdb-refresh`).
- **go-sops** (>=3.13.3) — `sops` binary; encrypted-secrets editor (YAML/JSON/env
  files; age/KMS/PGP backends).
- **age** (>=1.3.1) — `age` / `age-keygen`; modern simple file encryption (the
  default sops backend here).

---

## 5. Project scaffolding & templating

- **cookiecutter** (>=2.7.1) — template-based project scaffolding from local or git
  templates.
- **cruft** (>=2.16.0) — keep cookiecutter-generated projects in sync with their
  upstream template (diff + update).
- **jinja2** (>=3.1.6) — the template engine itself (also used standalone for codegen).
- **jinja2-ospath** (>=0.3.0) — Jinja2 extension adding filesystem-path filters to
  templates.
- **yo** (>=7.0.1) — Yeoman generator runner (e.g. VS Code extension scaffolds via
  `generator-code`).

---

## 6. Data processing & transformation

All in `local-recipes`.

Core arrays/frames:
- **numpy** (>=2.5.1) — n-dimensional arrays, the numeric foundation (NumPy 2.x API).
- **pandas** (>=1.5.3,<3) — DataFrames for tabular data (2.x resolved).
- **polars** (>=1.43.0) — Rust-backed columnar DataFrames; lazy queries, streaming;
  much faster than pandas for large data.
- **pyarrow-all** (>=21) — `import pyarrow`; Apache Arrow with ALL extras: Parquet,
  Datasets, Flight RPC, ORC, ADBC-adjacent IO. The interchange layer between pandas,
  polars, duckdb, dagster, daft.
- **getdaft** (>=0.6.13) — `import daft`; distributed DataFrames for multimodal data
  (images/urls/embeddings as first-class columns), Rust engine, scales out.
- **dask-core** (>=2026.7.1) — `import dask`; task-graph parallelism (`dask.delayed`,
  bags, dask.dataframe). NOTE: this is *core only* — the `distributed` scheduler is
  not installed; use the threaded/process schedulers.
- **dbgpt** (>=0.8.1) — `import dbgpt`; open-source AI-native data-app development
  framework (AWEL workflows + agents), aka DB-GPT.

SQL engines & tooling:
- **duckdb** (>=1.5.5) — embedded analytical (OLAP) SQL database; reads/writes
  Parquet/CSV/Arrow natively; the default local analytics engine.
- **sqlglot** (>26.32,<28.7) — parse, transpile, optimize SQL across ~30 dialects;
  build/rewrite SQL ASTs programmatically (used for feedstock analysis).
- **sqlfluff** (>=4.2.2) — SQL linter/formatter, dialect-aware.
- **psycopg2** (>=2.9.12) — real PostgreSQL driver (DB-API).
- **apsw** (>=3.53.3.1) — thin, full-featured SQLite bindings. **vuln-db env only**
  (backend for the AppThreat vdb).

Ibis — one dataframe API over many engines:
- **ibis-framework** (>=12) — `import ibis`; portable dataframe library: write one
  expression, execute on any backend; lazy, SQL-generating.
- **ibis-duckdb / ibis-polars / ibis-sqlite / ibis-postgres / ibis-mssql /
  ibis-oracle** (>=12) — the installed execution backends. (BigQuery via
  google-cloud-bigquery is separate, § 11.)
- **boring-semantic-layer** (>=0.3.16, PyPI) — lightweight semantic layer on Ibis:
  declare metrics/dimensions once, query them across backends.

Small utilities:
- **tablib** (>=3.9.0) — one API for tabular import/export: XLSX, CSV, JSON, YAML, ODS.
- **tabulate** (>=0.10.0) — pretty-print tables as text/markdown/grid.
- **tomlkit** (<0.13.3) — style-preserving TOML read/write (round-trips comments).
- **structlog** (>24.2,<26) — structured (key-value/JSON) logging.
- **ruamel.yaml** (>=0.18.17) — round-trip YAML that preserves comments and key order
  — the correct choice for editing `recipe.yaml`/`conda-forge.yml` in place.
- **frozendict** — immutable mapping type.
- **defusedxml** (>=0.7.1) — XML parsing hardened against XXE/entity bombs; use it for
  untrusted XML.

---

## 7. Workflow orchestration, pipelines & data quality

All in `local-recipes`.

- **dagster** (>=1.13.15) — asset-based data orchestrator: software-defined assets,
  schedules, sensors, partitions, type-checked IO.
- **dagster-webserver** (>=1.13.15) — the Dagster UI (`dagster dev`).
- **dagster-pipes** (>=1.13.15) — run external-process transform logic (scripts,
  containers) with structured logging/metadata back into Dagster.
- **kedro** (>=1.5.0) — opinionated pipeline framework: nodes, pipelines, data
  catalog, config environments. (A Kedro 3.14-compat warning is suppressed via
  `PYTHONWARNINGS` in the env activation.)
- **kedro-datasets** (>=9.5.0) — all Kedro data connectors (pandas/polars/spark
  datasets, APIs, cloud storage).
- **kedro-dagster** (>=0.7.0) — deploy Kedro pipelines onto Dagster.
- **kedro-viz** (>=12.4.0) — interactive browser visualization of Kedro pipelines.
- **kedro-mcp** (>=0.1.2, PyPI) — MCP server exposing Kedro prompts/tools to agents.
- **great-expectations** (>=1.19.1) — data-quality contracts: expectations suites,
  validation, data docs (used inside Kedro nodes).
- **pandera** (>=0.32.1) — lightweight statistical dataframe validation via typed
  schemas (pandas/dask/spark).
- **openlineage-python** (>=1.52.0) — `import openlineage.client`; emit OpenLineage
  data-lineage events.
- **opentelemetry-api / opentelemetry-sdk** (>=1.44.0) — traces/metrics/logs
  instrumentation and export (OTLP).
- **watchdog** (>=6.0.0) — filesystem event monitoring (`watchmedo` CLI); live-reload
  loops.

---

## 8. Visualization & dashboards

All in `local-recipes`.

- **matplotlib** (>=3.11.1) — general-purpose static 2D plotting.
- **plotly** (>=6.9.0) — interactive web-based charts (JSON-serializable figures).
- **bokeh** (>=3.9.1) — interactive HTML/JS plots and apps from Python; server mode
  for streaming.
- **panel** (>=1.9.3) — HoloViz app framework: turn plots/widgets/dataframes into
  dashboards and web apps; works in notebooks and as served apps.
- **panel-graphic-walker** (>=0.6.5) — embeds Graphic Walker (open-source Tableau
  alternative) as a Panel pane for drag-and-drop exploration.
- **vizro** (>=0.1.59) — McKinsey's low-code dashboard framework (config-driven, on
  top of Plotly/Dash).
- **vizro-ai** (>=0.4.1) — natural-language → Vizro charts/dashboards (LLM-assisted).
- **vizro-mcp** (>=0.1.4) — MCP server for creating Vizro dashboards from agents.
- **kedro-viz** — (listed in § 7) pipeline DAG visualization.

NOT available (deliberately excluded, see § 16): streamlit, chainlit, pygwalker,
perspective.

---

## 9. Documents, PDFs, Office, OCR, diagrams & media

All in `local-recipes`. This is the "deckcraft / markitdown" stack — everything needed
to read, convert, and generate documents.

Any-format → Markdown (LLM ingestion):
- **markitdown** (>=0.1.6) — Microsoft's converter: PDF, DOCX, XLSX, PPTX, HTML,
  images (w/ OCR), audio → clean Markdown for LLM pipelines. The loaders below back it.
- **mammoth** (>=1.12.0) — focused, high-fidelity .docx → HTML/Markdown.
- **markdown** (>=3.10.2) — Markdown → HTML parser.
- **markdownify** (>=1.2.3) — HTML → Markdown.
- **beautifulsoup4** (>=4.15.0) — `from bs4 import BeautifulSoup`; forgiving HTML
  parsing/scraping.
- **lxml** (>=6.1.1) — fast C-backed XML/HTML parsing + XPath.
- **pandoc** (>=3.10) — `pandoc` CLI; universal document converter (md ↔ docx ↔ html
  ↔ latex ↔ epub ↔ rst …).

PDF stack (pick by need):
- **pymupdf** (>=1.28.0) — `import pymupdf` (a.k.a. fitz); fastest PDF text/layout
  extraction + rendering + annotation.
- **pdfplumber** (>=0.11.10) — precise text + **table** extraction with layout
  geometry; best for tabular PDFs.
- **pdfminer.six** (>=20260107) — `import pdfminer`; pure-Python low-level text
  extraction (markitdown's backend).
- **pypdf** (>=6.14.2) — pure-Python PDF read/write/merge/split/encrypt.
- **pdf2image** (>=1.17.0) — PDF pages → PIL images (Poppler-backed) for vision-model
  input.
- **poppler** (>=26.7.0) — PDF rendering binaries (`pdftoppm`, `pdftotext`, …).
- **qpdf** (>=12.3.2) — `qpdf` CLI; PDF transforms: linearize, compress,
  encrypt/decrypt, split.

Office formats:
- **python-docx** (>=1.2.0) — `import docx`; read/write Word .docx.
- **python-pptx** (>=1.0.2) — `import pptx`; read/write PowerPoint .pptx.
- **openpyxl** (>=3.1.5) — read/write Excel .xlsx.
- **xlrd** (>=2.0.2) — read legacy Excel .xls.
- **odfpy** (>=1.4.1) — OpenDocument (.odt/.odp/.ods) read/write.
- **olefile** (>=0.47) — parse legacy OLE2 files (old .doc/.xls containers).
- **pptxgenjs** (>=4.0.1) — JavaScript (Node) library for *generating* .pptx decks
  programmatically; used by the deck workflows (`docs/specs/presentation-deck.md`).

OCR & images:
- **tesseract** (>=5.5.2) — Google's OCR engine binary.
- **pytesseract** (>=0.3.13) — Python wrapper for tesseract (scanned-PDF fallback).
- **pillow** (>=12.3.0) — `from PIL import Image`; image open/convert/resize/draw.

Slides & diagrams:
- **marp-cli** (>=4.2.3) — `marp`; Markdown → HTML/PDF/PPTX slide decks.
- **d2** (>=0.7.1) — `d2` CLI; Terrastruct diagram-as-code compiler (.d2 → SVG/PNG).
- **mermaid-py** (>=0.8.4) — `import mermaid`; render Mermaid diagram source from
  Python.

Audio:
- **pydub** (>=0.25.1) — audio slicing/conversion (needs an ffmpeg binary for
  non-WAV formats — not currently in the env).
- **speechrecognition** (>=3.10.4) — `import speech_recognition`; multi-engine
  speech-to-text wrapper (used by markitdown's audio loader).

Search/ranking:
- **rank-bm25** (>=0.2.2) — `from rank_bm25 import BM25Okapi`; classic BM25 document
  ranking (cheap lexical retrieval next to the embedding stack).

---

## 10. ML, embeddings & local LLM inference

All in `local-recipes` unless noted.

Hugging Face stack:
- **transformers** (>=5.14.1) — model hub + pipelines (text, vision, audio);
  tokenizers; Trainer.
- **accelerate** (>=1.14.0) — device placement / mixed precision / multi-GPU
  launching for HF models.
- **diffusers** (>=0.39.0) — diffusion pipelines (Stable Diffusion et al.) for local
  image generation.
- **sentence-transformers** (>=5.6.1) — dense text embeddings + cosine search; used
  for long-document RAG, slide dedup, template matching.
- **sentencepiece** (>=0.2.1) — subword tokenizer runtime (T5/MarianMT/SD3 need it).
- **hf-transfer** (>=0.1.9) — Rust accelerator for model downloads; enable with
  `HF_HUB_ENABLE_HF_TRANSFER=1`.

Local inference runtimes:
- **llama.cpp** (>=10003) — `llama-cli` / `llama-server` binaries; GGUF model
  inference on CPU/GPU; `llama-server` exposes an OpenAI-compatible API.
- **ollama** (>=0.24.0) — the Ollama server binary (Go): `ollama serve`,
  `ollama run <model>`; local model registry + OpenAI-compatible endpoint.
- **ollama-python** (>=0.6.2) — `import ollama`; Python client for that server.
- **mlx** (>=0.32.0) — Apple's array framework. **linux-64 + osx-arm64 only** (no
  Windows). Metal-accelerated on M-series (2-3x llama.cpp on some workloads);
  on Linux it runs against BLAS/LAPACK — fine for experimentation, no perf win.
- **mlx-lm** (>=0.31.3) — `import mlx_lm`; LLM runner on mlx (generate/serve/convert);
  preferred local runner on Apple Silicon. Same platform limits as mlx.

Knowledge & indexing for agents:
- **cocoindex** (>=1.0.18) — incremental indexing/transformation engine for
  long-horizon agents (recompute only what changed).
- **graphifyy** (>=0.9.26) — turn a folder of code/docs/papers/images into a
  queryable knowledge graph for coding assistants.

---

## 11. LLM APIs, agent frameworks, MCP & A2A

All in `local-recipes`, except `mcp`, which is also a run-dependency of the
`pyforge-herald` package and therefore a member of the lean `pyforge-herald` env.
This is the stack for *building* agents and agent servers.

Provider SDKs:
- **anthropic** (>=0.76.0) — official Claude SDK: Messages API, streaming, tool use,
  prompt caching.
- **google-genai** (>=2.14.0) — `from google import genai`; Gemini API client.
- **github-copilot-sdk** (>=1.0.8) — drive GitHub Copilot programmatically from
  Python.
- **langchain-anthropic** (>=1.3.1) — LangChain chat-model integration for Claude.
- **lumen-ai-anthropic** (>=1.2.1) — Anthropic backend for HoloViz Lumen AI
  (chat-with-your-data on top of Panel).

Agent frameworks:
- **pydantic-ai** (>=2.18.0) — typed agent framework from the Pydantic team:
  structured outputs, tools, dependency injection, model-agnostic.
- **agno** (>=2.6.22) — lightweight multi-modal agent framework: any provider,
  multi-agent teams, memory, knowledge stores, structured outputs, monitoring.

Model Context Protocol (MCP):
- **mcp** (>=1.28.1) — official MCP Python SDK (clients + servers, stdio/SSE).
- **fastmcp** (>=3.4.4) — decorator-style framework for building MCP servers fast
  (this repo's `conda_forge_server` is built on it).
- **langchain-mcp-adapters** (>=0.3.0) — expose MCP tools/resources as LangChain
  tools and vice versa.
- **django-mcp-server** (>=0.5.7) — serve MCP from a Django app.
- **vizro-mcp** / **kedro-mcp** — domain MCP servers (§ 8 / § 7).

Agent2Agent (A2A) & ACP:
- **a2a-sdk** (>=1.1.2) — `import a2a`; official Python SDK for the Agent2Agent
  protocol (agent cards, task lifecycle, messaging).
- **fasta2a** (>=0.6.1) — FastAPI-style A2A server implementation.
- **claude-agent-acp** (>=0.62.0) — bridge the Claude Agent SDK to the Agent Client
  Protocol (ACP) so editors/clients that speak ACP can drive Claude agents.

---

## 12. BMAD Method suite (agentic SDLC)

All in `local-recipes` unless noted (bmad-method also in the base `python` feature;
`mybmad-dashboard` is `bmad-ui`-only). These power the planning/dev workflow documented
in `CLAUDE.md` and `_bmad-output/`.

- **bmad-method** (>=6.10.0) — core installer/CLI: agents (PM, architect, dev, …),
  planning workflows (PRD → architecture → epics → stories), dev execution. 6.10+
  gains `bmad-dev-auto`.
- **bmad-loop** (>=0.9.0) — deterministic "ralph-loop" orchestrator with TUI; spawns
  coding-agent sessions in tmux (hence tmux below; Linux/macOS only, Windows via WSL).
- **bmad-builder** (>=2.1.0) — build custom BMAD modules.
- **bmad-module-template** (>=0.1.0) — scaffold for new BMAD modules.
- **bmad-creative-intelligence-suite** (>=0.2.1) — CIS expansion module (creative /
  ideation workflows).
- **bmad-method-test-architecture-enterprise** (>=1.19.1) — TEA module: enterprise
  test-architecture workflows.
- **bmad-method-wds-expansion** (>=0.4.3) — Whiteport Design Studio (UX/design)
  expansion.
- **bmad-utility-skills** (>=2.0.0) — 10 maintainer utility skills.
- **bmad-labs-skills** (>=1.0.0.dev0) — community skills marketplace (21 skills).
- **bmad-dashboard** (>=1.2.2.dev0) — VS Code extension installer for the BMAD
  dashboard UI. Also provisioned in the `bmad-ui` env (from the locally-built
  consume-not-submit mirror); task `bmad-dashboard-install`.
- **mybmad-dashboard** (>=0.1.0.dev0) — MyBMAD Next.js web dashboard + `mybmad`
  launcher (local PostgreSQL on :3002). **`bmad-ui` env only, linux-64 only** —
  commented out in `local-recipes` (line 681 of `pixi.toml`). Task: `mybmad`.
- **tmux** (>=3.7b_) — terminal multiplexer; **linux-64 + osx-arm64 only**; required by
  bmad-loop session spawning.

---

## 13. Web frameworks & cloud services

All in `local-recipes`.

Django stack (LTS-pinned):
- **django** (5.2 LTS) — the web framework.
- **channels** (4.x) + **daphne** (4.x) — WebSockets/async protocol layer + ASGI
  server for Django.
- **wagtail** (7.4 LTS) — Django CMS.
- **coderedcms** (6.x) — CRX/CodeRed CMS built on Wagtail (marketing-site batteries).
- **django-lasuite** (>=0.0.27) — common library for La Suite numérique Django
  projects.
- **bokeh-django** (>=0.2.1) — serve Bokeh apps inside Django.
- **django-mcp-server** — (§ 11) MCP endpoint inside Django.

Cloud / storage / identity:
- **google-cloud-bigquery** (>=3.42.2) — `from google.cloud import bigquery`;
  BigQuery client. Used by cf_atlas Phase P (opt-in `PHASE_P_ENABLED=1`); auth via
  ADC creds cached by the `gcloud` env.
- **google-cloud-sdk** (>=577.0.0) — the `gcloud` CLI. **`gcloud` env only,
  linux/macOS only.** Used once for `gcloud auth application-default login`; after
  that the BigQuery lib picks up cached ADC automatically.
- **azure-identity** (>=1.25.3) — Azure AD/Entra credential objects for all Azure
  SDKs.
- **msgraph-sdk** (>=1.48.0) — Microsoft Graph API client (M365: mail, files, users).
- **minio** (>=7.2.20) — Python client SDK for MinIO / any S3-compatible object
  store.
- **moto** (>=5.2.2) — mock AWS services in tests (S3, EC2, …) without network.

HTTP & APIs:
- **requests** (>=2.34.2) — the classic sync HTTP client.
- **httpx** (>=0.28.1) — modern HTTP client, sync + async, HTTP/2.
- **gql** (>=4.0.0) — GraphQL client (v4+ drops the websockets dep).

---

## 14. Developer tooling: lint, type-check, test, terminal

All in `local-recipes`.

Linters & formatters:
- **ruff** (>=0.16.0) — extremely fast Python linter + formatter (flake8/isort/black
  replacement). Default Python QA tool here.
- **yamllint** (>=1.38.0) — YAML linting.
- **taplo** (>=0.10.0) — TOML linter/formatter/LSP (use on pixi.toml itself).
- **sqlfluff** — (§ 6) SQL lint/format.
- **nbqa** (>=1.9.0) — run ruff/mypy/etc. over Jupyter notebooks.
- **shellcheck** — (§ 2) shell script analysis.

Type checkers (three available — pick one per task):
- **pyright** (>=1.1.411) — Microsoft's fast type checker (the default for quick
  checks).
- **mypy** (>=2.3.0) — the reference type checker (plugin ecosystem).
- **pyrefly** (>=1.1.1) — Meta's Rust-based checker (fastest on big codebases).

Testing:
- **pytest** (>=9.1.1) — the test framework (repo suites live under
  `.claude/skills/conda-forge-expert/tests`).
- **pytest-mock** (>=3.15.1) — `mocker` fixture over unittest.mock.
- **pytest-cov** (>=7.1.0) — coverage reporting.
- **pytest-xdist** (>=3.8.0) — parallel test execution (`-n auto`).

Browser automation:
- **playwright** (>=1.62.0) — the Node Playwright CLI (browser installs, codegen).
- **playwright-python** (>=1.61.0) — `from playwright.sync_api import ...`; drive
  Chromium/Firefox/WebKit from Python (scraping, E2E, screenshots).

Terminal & CLI building:
- **rich** (>=14.3.4) — rich terminal output: tables, progress bars, markdown,
  syntax highlighting, tracebacks.
- **typer** (>=0.27.0) — build CLIs from type-hinted functions (click-based).

Node package managers:
- **pnpm** (>=11.17.0) — fast, disk-efficient npm alternative (default for JS builds
  here; in .bat scripts always `call pnpm`).
- **yarn** (>=4.17.1) — Yarn Berry.

---

## 15. Vulnerability & SBOM environment (`vuln-db`)

A deliberately separate env (`pixi run -e vuln-db ...`) so `local-recipes` stays lean.
First `vdb-refresh` downloads ~600MB to `.claude/data/conda-forge-expert/vdb/`.

- **appthreat-vulnerability-db** (>=6.7.0) — (see § 4) here it's the primary engine:
  multi-source CVE DB (OSV + GHSA; NVD/npm via sources) queried by `detail-cf-atlas
  --vdb`, `scan-project`, and cf_atlas Phase G/G'. CISA KEV is fetched out-of-band
  (`fetch-cisa-kev` task) because vdb's aqua source hardcodes KEV exclusion.
- **apsw** (>=3.53.3.1) — SQLite backend for vdb.
- **cyclonedx-bom** (>=7.3.0) — `cyclonedx-py` CLI: generate CycloneDX SBOMs from
  environments/requirements/poetry/pipenv.
- **cyclonedx-python-lib** (>=11.11.0) — programmatic CycloneDX BOM model
  (read/build/serialize 1.x BOMs; used by universe-sbom / inventory-match tooling).
- **conda-forge-metadata** (>=0.16.1) — query conda-forge artifact metadata (which
  files/libs a package ships) — enables `--deep` package inspection.
- Env vars set on activation: `VDB_HOME`, `VDB_CACHE` (repo-local DB paths),
  `TRUSTSTORE=1` (OS trust store TLS).

Tasks in this env: `vdb-refresh`, `scan-project` (manifests/locks/SBOMs/Dockerfiles →
CVEs), `inventory-channel` (conda/PyPI/npm/crates mirrors), `detail-cf-atlas[-vdb]`,
`build-cf-atlas` / `atlas-phase` (Phase G/G' need vdb importable).

---

## 16. Explicitly NOT available (don't assume these)

These are commented out in pixi.toml on purpose — do not import them or write code
depending on them without adding them first:

- **streamlit, chainlit, pygwalker, django-pygwalker, perspective** — dashboard tools
  excluded (jupyter deps, platform gaps, or staleness).
- **dbt-core / dbt-duckdb / dbt-postgres, dlt** — dbt pinned out by a click conflict;
  dlt blocked on dlt-pendulum platform coverage / py3.14.
- **crewai** — agent framework, not resolvable here yet.
- **litellm** — LLM router/proxy; deliberately not added (breaks on the repo's
  Python 3.14 floor).
- **crawl4ai, whisper.cpp, imaginairy** — outdated on conda-forge.
- **cibuildwheel** — bashlex fails on linux-aarch64.
- **cdxgen, oras-py, conda-tree, networkx (as direct dep)** — version conflicts.
- **pixitainer, pixi-devenv, pixi-browse, nebi-desktop** — python>=3.13-only or
  glibc constraints.
- **bmad-story-automator, bmalph, bmad-autopilot** — BMAD-adjacent
  tools parked (unix-only or superseded by bmad-loop). (`mybmad-dashboard` is NOT
  parked — it is live in the `bmad-ui` env; see § 12.)
- **claude-mem, caveman, headroom-ai, codegraph, ppt-master, aichat** — parked
  agent-tooling candidates.
- **ffmpeg** — never listed; pydub/audio work beyond WAV needs it added first.

---

## 17. Import-name gotchas (package name ≠ import name)

| Package (pixi.toml)          | Import / invoke as                          |
|------------------------------|---------------------------------------------|
| gitpython                    | `import git`                                 |
| python-build                 | `import build` / `python -m build`           |
| beautifulsoup4               | `from bs4 import BeautifulSoup`              |
| pillow                       | `from PIL import Image`                      |
| pdfminer.six                 | `import pdfminer`                            |
| pymupdf                      | `import pymupdf` (legacy alias `fitz`)       |
| python-docx / python-pptx    | `import docx` / `import pptx`                |
| getdaft                      | `import daft`                                |
| dask-core                    | `import dask`                                |
| ibis-framework               | `import ibis`                                |
| speechrecognition            | `import speech_recognition`                  |
| ollama-python                | `import ollama` (the `ollama` pkg = server binary) |
| playwright-python            | `import playwright` (the `playwright` pkg = Node CLI) |
| appthreat-vulnerability-db   | `import vdb`                                 |
| sentence-transformers        | `from sentence_transformers import SentenceTransformer` |
| rank-bm25                    | `from rank_bm25 import BM25Okapi`            |
| mermaid-py                   | `import mermaid`                             |
| google-genai                 | `from google import genai`                   |
| google-cloud-bigquery        | `from google.cloud import bigquery`          |
| msgraph-sdk                  | `from msgraph import GraphServiceClient`     |
| a2a-sdk                      | `import a2a`                                 |
| openlineage-python           | `import openlineage.client`                  |
| mlx-lm                       | `import mlx_lm`                              |
| go-sops                      | `sops` (CLI)                                 |
| marp-cli                     | `marp` (CLI)                                 |
| cyclonedx-bom                | `cyclonedx-py` (CLI)                         |
| spec-kit                     | `specify` (CLI)                              |
| bmad-method                  | `bmad` (CLI)                                 |
| llama.cpp                    | `llama-cli` / `llama-server` (CLIs)          |
| nebi-cli                     | `nebi` (CLI)                                 |
| ruamel.yaml                  | `from ruamel.yaml import YAML`               |

---

## 18. Quick capability index ("I need to X → use Y")

- Parse/edit YAML preserving comments → **ruamel.yaml**; lint it → **yamllint**
- Fast dataframes → **polars**; compat dataframes → **pandas**; SQL on files → **duckdb**
- One dataframe API over many DBs → **ibis-framework** (+ backend pkgs); metrics layer → **boring-semantic-layer**
- Orchestrate pipelines → **dagster** or **kedro** (bridge: **kedro-dagster**)
- Validate data → **pandera** (schemas) or **great-expectations** (contracts)
- Any document → Markdown for an LLM → **markitdown**; docx→md → **mammoth**; universal convert → **pandoc**
- Extract PDF text fast → **pymupdf**; PDF tables → **pdfplumber**; PDF→images → **pdf2image**; OCR → **pytesseract**
- Make slides → **marp-cli** (md→deck) or **pptxgenjs**/**python-pptx** (programmatic)
- Diagrams as code → **d2** or **mermaid-py**
- Charts → **plotly**/**matplotlib**/**bokeh**; dashboard app → **panel** or **vizro**
- Call Claude → **anthropic**; Gemini → **google-genai**; local LLM → **ollama**/**llama.cpp**/**mlx-lm**
- Build an agent → **pydantic-ai** or **agno**; build an MCP server → **fastmcp**; A2A → **a2a-sdk**/**fasta2a**
- Embeddings/RAG → **sentence-transformers** (+ **rank-bm25** for lexical)
- Generate a conda recipe → **grayskull**; build v1 → **rattler-build**; build v0 → **conda-build**; lint → **conda-smithy**
- Migrate recipe v0→v1 → **conda-recipe-manager** / **feedrattler**
- Scan for CVEs → **pip-audit** (env), **osv-scanner** (lockfiles/SBOMs), **bandit** (code), **appthreat-vulnerability-db** via `vuln-db` env (deps), or the `scan-project` task
- Find unused/missing deps → **deptry**
- SBOMs → **cyclonedx-bom** / **cyclonedx-python-lib** (`vuln-db` env) or the `universe-sbom` task
- Lock/bundle envs → **conda-lock**, **pixi-pack**/**pixi-unpack**, **conda-pack**
- Drive a browser → **playwright-python**
- Build a CLI → **typer** + **rich**
- Scaffold a project → **cookiecutter** (+ **cruft** to stay synced)
- Web app/CMS → **django** + **wagtail**/**coderedcms**; realtime → **channels**+**daphne**
- Secrets in git → **go-sops** + **age**
- Mock AWS in tests → **moto**; test runner → **pytest** (+ xdist/cov/mock)
- Type-check → **pyright** (default), **mypy**, or **pyrefly**; lint/format Python → **ruff**

*End of library-llms-full.md*