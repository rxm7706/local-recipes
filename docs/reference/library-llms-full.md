# local-recipes — Library Catalog for LLMs & Agents (library-llms-full.md)

> Purpose: give any LLM or coding agent a complete, self-contained picture of every
> library, CLI, and framework available in this repository's pixi environments —
> what each one is, what it is capable of, how to import/invoke it, and which
> environment provides it.
>
> Source of truth: `pixi.toml` (workspace "staged-recipes" v0.2.0). This file is a
> derived catalog — regenerate it whenever `pixi.toml` changes.
> Generated: 2026-07-12; last full re-sync **2026-08-25**; version-floor re-sync 2026-09-04 (31 floors caught up to `pixi.toml`, prose untouched); version-floor re-sync 2026-09-05 (18 floors caught up to `pixi.toml` after the 2026-09-05 `pixi upgrade` pass -- incl. `pixi` 0.78.0->0.79.0, `bmad-method` 6.11.0->6.12.0, `bmad-suite` 2026.9.1->2026.9.5, `fastmcp-slim` 4.0.0b5->4.0.3, `conda-forge-metadata` 0.16.1->2026.9.5 -- prose untouched) (restored 18-section catalog after a 64-line stub; `environment.yaml` export; platform-ci-test conda-only; kedro-mcp/kedro-skills/boring-semantic-layer on SelfExplainML conda; psycopg >=3.2 / psycopg2 >=2.9.10; Liquibase + OpenFeature; pyforge-testing-kit env); earlier incremental: incrementally updated 2026-07-18 (pyforge-atlas member env + kedro-viz; pyforge-warden + bmad-ui envs; pin corrections), 2026-07-25 (the pyforge-herald / -doctor / -scribe member envs, then pyforge-mason / -steward / -marshal at Story 1.1 — eight `pyforge` packages, 18 envs), 2026-07-30 (24 version floors re-synced to `pixi.toml`; `bmad-manticore`, `ocrmypdf` and `office2pdf` documented — the three deps the agent-CLI recipe wave added without a catalog entry), 2026-08-01 (25 version floors re-synced to `pixi.toml`, incl. `mcp` 1.x->2.0.0 and `fastmcp` pinned back to 2.14.3), 2026-08-09 (`kedro-skills` documented — pyforge-atlas-only, floor `>=0.1.1` (conda SelfExplainML, atlas + local-recipes), Story 12-1; then a second 2026-08-09 pass re-syncing 12 version floors to `pixi.toml` — incl. `fastmcp` 2.14.3->3.4.5 and `pixi` 0.75.0->0.76.1 — and documenting the two deps the catalog had never carried: `pyyaml` (pyforge-doctor) and `httpx2` (pyforge-herald)) and 2026-08-14 (Story 10.2, CAP-5: the new `python-agent-platform` env — the FIRST env in this catalog pinned off `python 3.14.x` (env-scoped `python = "3.12.*"`) — documented with `langflow`/`dbgpt-serve`/`fastapi`/`django-health-check`/`redis-py`; `pixitainer` uncommented + bumped to `>=0.8.3`, linux-64 only; plus 33 unrelated version floors re-synced to `pixi.toml` and `pyforge-core`'s env row added — the catalog was already drifted on these before this story, `llms-full-check` now exits 0) and 2026-08-20 (Story 11.1: the new `platform-dev` env — composes onto `python-agent-platform` — documented with `postgresql`/`pgvector`/`redis-server`/`kubernetes-helm`/`kubernetes-client`; `python-agent-platform` itself gains `chromadb`/`langchain-chroma`/`elevenlabs`/`psycopg`, four deps `langflow.main.create_app()` hard-imports that the recipe only lists as soft `run_constraints`, discovered live wiring the actual Langflow ASGI mount) and 2026-08-23 (Story 12.1: **copier** documented as the pyforge-marshal/Genesis template engine; pyforge-marshal env row updated; quick-index scaffolding line reconciled with Copier adoption) and 2026-08-27 (atlas Story 20.1, CAP-5: **duckdb-server** documented — pyforge-atlas env, linux-64 only, the CAP-19 query plane's optional HTTP/Arrow face behind the one `query-plane-boot` script; import package `pkg`) and 2026-08-29 (32 version floors re-synced to `pixi.toml` after a `pixi update` pass, incl. `pixi` 0.77.0->0.78.0, `fastmcp` 2.14.3->3.4.7, `mcp` re-pointed to the `local-recipes` env's actual floor 1.28.1 (env-scoped ceiling below the other envs' 2.1.1, per steward 21.2's fastmcp<2.0 constraint), `pnpm` 11.24.0->12.0.0, and `duckdb-server` 0.27.0->0.31.0) and 2026-09-12 (version-floor re-sync: 23 floors caught up to `pixi.toml` after a `pixi update` pass, incl. `uv` 0.12.10->0.12.13, `mcp`/`mcp-types` 2.1.1->2.2.0, `kedro` 1.5.0->1.6.0, `python-slugify` 8.0.4->9.0.0, `bmad-suite` 2026.9.5->2026.9.9, `conda-forge-metadata` 2026.9.5->2026.9.10; plus 6 deps the catalog had never carried documented: `boto3`, `silo`, `garage`, `seaweedfs` (§ 13, `platform-object-storage` S3-compatible backend stack, Story 50.1-50.3) and `apscheduler` (§ 7, `pyforge-scribe` trigger backend, Story 8.1) and `prometheus_client` (§ 13a, `platform-ci-test` + `pyforge-doctor`)) and 2026-09-12
(`spec-library-catalog-manifest-sync` CAP-1: new § 1a documents `packaging`, `jsonschema`,
`psutil`, `attrs`, `packageurl-python`, `license-expression` — six deps every affected
station's own nested `pixi.toml [package.run-dependencies]` already declared, root
`pixi.toml` never mirrored; `pydantic`'s existing transitive-only note sharpened to also
name pyforge-atlas's and pyforge-scribe's direct declarations) and 2026-09-19 (§ 1a adds
`tornado` — pyforge-atlas's nested run-dep behind the Bokeh server, the one `undocumented-dep`
`llms-full-check` reported on `main`) and 2026-09-20 (§ 10: headroom-ai's `[proxy]` extra
documented -- `openai`, `orjson`, `magika`, `zstandard`, `onnxruntime`, `watchdog`,
`sqlite-vec`; `pyforge-guild`-only, added after the extra's absence crashed a `marshal
factory dispatch` run; same pass also adds `caveman` to `pyforge-guild` -- its
`caveman-install` presence-probe has no `fallback_bin_dirs` escape hatch, so it needs
the SAME env dispatch runs in, not just `local-recipes`) and 2026-09-24
(`caveman` renamed to `caveman-installer` in both `pyforge-guild` and
`local-recipes` -- conda-forge graduated the package under its correct
upstream name; both envs stay channel-pinned to the local SelfExplainML
build rather than conda-forge's own, since the latter's `nodejs >=26.10`
requirement conflicts with `pyforge-foundry-full`'s libabseil pin as well
as codegraph's) and 2026-09-26 (version-floor re-sync: 57 floors caught up to
`pixi.toml` after a `pixi upgrade` pass, prose untouched except the channel moves:
`bmad-loop`, `caveman-installer`, `codegraph`, `bmad-module-skill-forge`,
`fastmcp`/`fastmcp-slim`, `kedro-mcp`, `silo`, `liquibase-postgresql` and
`openfeature-flagd-api` now resolve from conda-forge and their SelfExplainML
channel pins are gone). Channels: conda-forge + SelfExplainML.
> Platforms: linux-64, win-64, osx-arm64 (macOS >= 14.5 "Sonoma" floor, required by mlx).

## To regenerate (any session): ask Claude Code:

> Regenerate `docs/reference/library-llms-full.md` from `pixi.toml`. Read all of `pixi.toml`, then rewrite the catalog keeping the same 18-section structure: envs table, version pins, per-category library entries with version floors + capabilities + platform caveats, the "explicitly NOT available" section from the commented-out deps, the import-name gotchas table, and the quick capability index. Update the Generated date. Verify with `pixi run -e pyforge-guild llms-full-check`.

**Staleness detector:** `pixi run -e pyforge-guild llms-full-check` (script:
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
- **Python is 3.14.x in every environment except one.** If a library you want to
  add doesn't support 3.14, it won't resolve here. The sole exception is
  `python-agent-platform` (CAP-5, Story 10.2), env-scoped to `python = "3.12.*"`
  only — no other feature/env in `pixi.toml` changes its python floor off 3.14.
- Node.js 24 (LTS) is present, so npm-ecosystem CLIs (pnpm, yarn, marp, pptxgenjs, pptxgenjs-plus, yo)
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
| `pyforge-warden`| pyforge-warden (no-default-feature)                  | Lean env for the built `pyforge-warden` package (`src/shared/packages/pyforge-warden` path dep -> conda pkg + run-deps + pytest; test-oracles py-rattler / py-rattler-build / conda-build). Multi-axis dependency-compliance gate; CLI `warden` (`warden-scan` task), gate `pyforge-warden-test`. Spec: `archive/docs/specs/pyforge-warden.md` |
| `pyforge-atlas`| pyforge-atlas (no-default-feature)                    | Lean env for the `pyforge.atlas` Kedro pipeline member (`src/shared/packages/pyforge-atlas` path dep -> built conda pkg + kedro/kedro-datasets/kedro-dagster/pyforge-warden run-deps + pytest/hatchling/python-build + **kedro-viz** + duckdb-server on linux-64 — the CAP-19 HTTP/Arrow face, raised only by the `query-plane-boot` task). Loop worktrees materialize THIS env; gates: `kedro-test`, `kedro-catalog-check`, `dagster-dryrun`, `viz` |
| `pyforge-herald`| pyforge-herald (no-default-feature)                  | Lean env for the built `pyforge-herald` package (`src/shared/packages/pyforge-herald` path dep -> conda pkg + **mcp** run-dep + pytest/hatchling/python-build). Herald is the Design<->Code bridge; `mcp` is its Story-1.2 primary transport. Spec: `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/` |
| `pyforge-doctor`| pyforge-doctor (no-default-feature)                  | Lean env for the built `pyforge-doctor` package (`src/shared/packages/pyforge-doctor` path dep -> conda pkg + pytest/hatchling/python-build). Fleet-health station. Spec: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/` |
| `detectors` | detectors (no-default-feature) | The Detectors workflow's locked env (`.github/workflows/detectors.yml`: pixi first, pip fallback) — `pyforge-doctor` path dep + its run-deps, `ruamel.yaml`, `playwright-python`. Runs the repo-scope detector subset; builds and tests nothing. |
| `pyforge-scribe`| pyforge-scribe (no-default-feature)                  | Lean env for the built `pyforge-scribe` package (`src/shared/packages/pyforge-scribe` path dep -> conda pkg + pytest/hatchling/python-build). Knowledge/narration station; inherits the `src/sentinel/` knowledge-graph lineage. Spec: `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/` |
| `pyforge-core` | pyforge-core (no-default-feature)                     | Lean env for the built `pyforge-core` package (`src/shared/packages/pyforge-core` path dep -> conda pkg + pytest/hatchling/python-build). Pure-stdlib shared leaf (Story 14.1, `pyforge-scribe` mirror); a real run-dependency of six sibling stations' own envs (atlas, herald, marshal, scribe, steward, warden — see each `[feature.pyforge-<station>.dependencies]`). Spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/` |
| `pyforge-testing-kit` | pyforge-testing-kit (no-default-feature)         | Lean env for the built `pyforge-testing-kit` package (`src/shared/packages/pyforge-testing-kit` path dep -> conda pkg + pytest/hatchling/python-build). Own-leaf shared test mocks (Story 19.2 / FR-130 / Q-26); stdlib-only; test-time path dep of pyforge-marshal + pyforge-doctor feature envs (not a station runtime run-dep). Spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-19-2-the-shared-test-support-kit.md` |
| `pyforge-ci` | python + pyforge-ci (no-default-feature) | Lean CI env for wheel/sdist/.conda publish without the fat `local-recipes` download |
| `pyforge-container` | eight station features (no-default-feature) | Whole-Guild image env: marshal+steward+atlas+warden+doctor+mason+herald+scribe in one `pixi install` |
| `dbgpt-sidecar` | dbgpt-sidecar (no-default-feature) | **`python 3.12.*`.** Container-only sidecar: `dbgpt-app` + siblings; NOT composed onto python-agent-platform (disjoint FastAPI ranges) |
| `platform-ci-test` | platform-ci-test (no-default-feature) | **`python 3.12.*`.** Slim conda-only env for Platform CI's `test` job (psycopg3 vs image psycopg2). No langflow/dbgpt. Install: `pixi install -e platform-ci-test` |
| `pyforge-mason`| pyforge-mason (no-default-feature)                    | Lean env for the built `pyforge-mason` package (`src/shared/packages/pyforge-mason` path dep -> conda pkg + pytest/hatchling/python-build). The Artisan Builder's CLI (`mason recipe`/`package`/`environment`); **no CLI-framework dep by contract** (FR-41 forbids click/typer — argparse only). Tasks: `pyforge-mason-build{,-conda,-dist}`, `pyforge-mason-test`. Spec: `_bmad-output/projects/pyforge-mason/planning-artifacts/` |
| `pyforge-steward`| pyforge-steward (no-default-feature)                | Lean env for the built `pyforge-steward` package (`src/shared/packages/pyforge-steward` path dep -> conda pkg + pytest/hatchling/python-build). The Provisioner's CLI (`steward keys`/`deploy`/`provision`/`budget`); task names mirror `pyforge-warden`'s verbatim. Spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/` |
| `pyforge-marshal`| pyforge-marshal (no-default-feature)                | Lean env for the built `pyforge-marshal` package (`src/shared/packages/pyforge-marshal` path dep -> conda pkg + **copier** + pytest/hatchling/python-build + **import-linter**). Marshal is the harness/orchestration station and ships Genesis (`marshal seed` verbs) via **copier** (NFR-C2, `>=9.17,<10`); `import-linter` enforces AD-3/AD-4 as build-breaking contracts. Tasks: `pyforge-marshal-test`, `pyforge-marshal-build{,-conda,-dist}`. Spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/` |
| `python-agent-platform`| python-agent-platform (no-default-feature)     | **`python 3.12.*` — one of three 3.12 envs (`platform-ci-test`, `dbgpt-sidecar` share the floor).** CAP-5 (Story 10.2, "one factory-sourced environment"): the ONE env that runs the three agentic engines (`langflow`, `dbgpt`, `dbgpt-serve`) alongside `django` on a single conda-forge-sourced interpreter, plus the `fastapi`/`django-health-check`/`psycopg2`/`redis-py` host deps and (Story 11.1) `chromadb`/`langchain-chroma`/`elevenlabs`/`psycopg` — deps `langflow.main.create_app()` hard-imports that the recipe only lists as soft `run_constraints`. `channel-priority = "flexible"` (feature-scoped) lets the solver fall through to a `SelfExplainML`-channel `slowapi` build once conda-forge's own build is ruled out by the `redis-py >=6.0.0` floor. Epic 11's engine-mounting stories and Story 10.3 (container image) both depend on this env existing. Spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/` |
| `platform-dev` | python-agent-platform + platform-dev (no-default-feature) | AD-16, Story 11.1 + 56.1: composes `platform-dev` (`postgresql`/`pgvector`/`redis-server`/`kubernetes-helm`/`kubernetes-client`/`django-debug-toolbar`) ONTO `python-agent-platform` — one env for the full local Tier-1 baseline including `config.settings.local`, zero containers or managed services. |
| `bmad-ui`      | bmad-ui (no-default-feature)                          | **linux-64 only.** BMad Method UI dashboards (`archive/docs/specs/bmad-loop-adoption.md` W4). Consumes the locally-built consume-not-submit mirrors `bmad-dashboard` + `mybmad-dashboard` from `./build_artifacts/linux64` + conda-forge. Tasks: `bmad-dashboard-install` (wires the VS Code extension), `mybmad` (Next.js dashboard + local PostgreSQL on :3002) |
| `bmad-suite-full`| bmad-suite-full (no-default-feature)                | **linux-64 only.** CAP-4 greenfield one-pin proof env (`spec-bmad-suite-metapackage`, story 39.4): composes only `bmad-suite` (>=2026.9.1, SelfExplainML) + a minimal `python` floor — solver smoke without pulling the fat `local-recipes` graph. Not composed into `local-recipes`, which keeps its own 11 explicit `bmad-*` pins for pipeline-truth / doctor drift granularity. Docs: `install-matrix.md`'s Greenfield one-pin section. |

### Version pins agents must respect (don't fight the resolver)

- `python = ">=3.14.6,3.14.*"` at the workspace root (3.14.* in each feature) — check
  3.14 compat before suggesting new deps. **Exception:** `python-agent-platform` pins
  `python = "3.12.*"`, env-scoped (CAP-5, Story 10.2). The same 3.12 floor also applies
  to `platform-ci-test` and `dbgpt-sidecar` — do not raise these back to 3.14.
- `pandas >=1.5.3,<3` and `pyarrow >=13,<22` + `pyarrow-all >=21` → pandas 2.x, pyarrow 21.x.
- `tomlkit <0.13.3` (dagster-dg-core pin), `structlog >24.2.0,<26` (xorq/BSL pin),
  `sqlglot >26.32.0,<28.7.0`.
- LTS pins: `django 5.2.x`, `wagtail 7.4.x`, `coderedcms 6.x`, `channels 4.x`,
  `daphne 4.x`, `nodejs 24.x or 26.x`.
- `pydantic` is not pinned directly in root `pixi.toml` — it is present transitively in
  `local-recipes` (pydantic-ai, fastmcp, agno, etc. all pull pydantic v2) **and** is a
  direct run-dep of `pyforge-atlas`'s and `pyforge-scribe`'s own nested `pixi.toml`
  `[package.run-dependencies]` (undocumented-in-root case, same class as § 1a, but left
  unpinned here since it already resolves and is already noted).

---

## 1. Core runtime & package management

Available in every environment (the `python` feature + workspace `[dependencies]`).

- **python** (>=3.14.6, 3.14.*) — CPython interpreter. All Python libs below target 3.14.
- **pixi** (>=0.80.0) — the package/environment manager itself, available *inside*
  envs for nested workspace operations. `pixi-build` preview is enabled (unlocks
  `[package]`/build tables for the **eight** `pyforge` workspace members under
  `src/shared/packages/` — `pyforge-warden`, `pyforge-atlas`, `pyforge-herald`,
  `pyforge-scribe`, `pyforge-doctor`, `pyforge-mason`, `pyforge-steward`,
  `pyforge-marshal` — each pulled in as a path dependency by its own lean `no-default-feature` env, and each sharing the one PEP 420 implicit
  `pyforge` namespace).
- **conda** (>=26.5.0) — classic conda package manager; needed by conda-build,
  conda-smithy 2026.x, and `conda pypi`.
- **pip** (>=26.2) — standard Python installer (prefer `uv` for speed).
- **uv** (>=0.12.19) — Rust-based, very fast pip/pip-tools replacement: `uv pip install`,
  `uv venv`, `uv pip compile` for lock-style resolution.
- **nodejs** (>=24.19.0,<27.0,!=25.*; 24.x or 26.x LTS, 25.x excluded as Node's non-LTS release) — `node` / `npm` / `npx`; runtime for the JS tools below.
- **gh** (>=2.101.0) — GitHub CLI: PRs, issues, releases, `gh api` for raw REST/GraphQL,
  `gh pr checks`, workflow dispatch. The repo's primary GitHub automation surface.
- **gitpython** (>=3.1.62) — `import git`; programmatic Git (repos, diffs, commits,
  remotes) when shelling out to `git` is awkward.
- **truststore** (>=0.10.4) — `import truststore; truststore.inject_into_ssl()`; makes
  Python TLS use the OS trust store (corporate CAs, JFrog). Set `TRUSTSTORE=1` pattern
  used by the vuln-db tasks.
- **bmad-method** (>=6.12.0) — BMAD-METHOD CLI (`bmad`): AI-driven agile
  planning/dev framework (agents, workflows, story lifecycle). See § 12.
- **spec-kit** (>=1.0.12) — GitHub Spec Kit (`specify` CLI) for spec-driven
  development scaffolding (constitution → specify → plan → tasks → implement).

## 1a. Station manifest mirrors (general Python utilities)

`local-recipes` plus the named `pyforge-*` lean envs only — **not** every environment.
Each is already a direct run-dep of the named station's own
`src/shared/packages/pyforge-<station>/pixi.toml` `[package.run-dependencies]`
(`spec-library-catalog-manifest-sync` CAP-1, 2026-09-12); documented here because that
manifest is a second, un-mirrored source root `pixi.toml` doesn't otherwise expose.

- **packaging** (>=26.3) — version/requirement parsing; `pyforge-marshal`
  (`seed/engine/copier.py`, `seed/detect/referenced_deps.py`), `pyforge-mason`
  (`engines/pep517.py`), `pyforge-warden` (`hygiene.py`, `engines.py`, `extract/*.py`).
- **jsonschema** (>=4.26.0) — JSON Schema validation; `pyforge-doctor` (`__main__.py`),
  `pyforge-marshal` (`seed/state/store.py`), `pyforge-warden` (`report.py`).
- **psutil** (>=7.2.2) — process/system introspection; `pyforge-marshal` only.
- **attrs** (>=26.1.0) — declarative classes; `pyforge-atlas` (`observability.py`) only.
- **packageurl-python** (>=0.17.6) — package-URL (purl) parse/build; `pyforge-warden`
  (`sbom.py`, `sources.py`, `eligibility_sbom.py`); imports as `packageurl`.
- **license-expression** (>=30.4.4) — SPDX license-expression parse/normalize;
  `pyforge-warden` (`license.py`) only; imports as `license_expression`.
- **filelock** (>=3.32.0) — cross-process file locking; `pyforge-atlas`
  (`duckdb_writer.py`, `admission.py`) only. Distinct from the separate marshal/scribe
  filelock *adoption* question tracked in `spec-pyforge-unifying-strategy`'s "Estate
  leverage — installed, bind now" table — this is atlas's own already-shipped use.
- **tornado** (>=6.5.8) — async networking: IOLoop + HTTP server; `pyforge-atlas` only
  (`views/live.py` hard-imports `bokeh.server.server.Server`, which runs on Tornado —
  Story 14.3 / AUD-ATLAS-010: an undeclared module-level import is a runtime dependency).
  Resolvable transitively via **bokeh** in every other env; declared directly only in
  atlas's nested manifest, in step with its `pyproject.toml`.

---

## 2. Conda / conda-forge packaging toolchain

The heart of the factory. In `build`, `grayskull`, `conda-smithy`, and `local-recipes`
per the table above; all of them coexist in `local-recipes`.

Build engines & solvers:
- **conda-build** (>=25.3.1) — v0 recipe engine: builds `meta.yaml` recipes, renders
  Jinja2, runs tests. Never mix v0 and v1 recipes in one build run.
- **rattler-build** (>=0.76.1) — Rust-native v1 recipe engine: builds `recipe.yaml`,
  much faster than conda-build, first-class cross-compilation. Primary local build tool.
- **py-rattler** (>=0.22.0) — `import rattler`; Python bindings to the rattler libs:
  solve environments, fetch/inspect .conda artifacts, repodata handling — programmatic
  conda operations without shelling out.
- **py-rattler-build** (>=0.73.0) — Python bindings to rattler-build (drive v1 builds
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
  programmatically (CRM library + `crm` CLI). **grayskull env only** since
  2026-08-30 (`[feature.crm.dependencies]`): its feedstock's exact click==8.2.1
  pin (feedstock bug, conda-forge/conda-recipe-manager-feedstock#44) walled
  headroom-ai + the dbt trio out of local-recipes. Run via
  `pixi run -e grayskull crm …`.
- **feedrattler** (>=0.3.14) — convert an existing conda-forge feedstock from v0
  `meta.yaml` to v1 `recipe.yaml` end-to-end. **grayskull env only** since
  2026-08-30 (requires conda-recipe-manager; moved with it). Run via
  `pixi run -e grayskull feedrattler …`.

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
- **conda-pypi** (>=0.12.0) — safer PyPI interop for conda envs (`conda pypi install`).

Shell/CI quality:
- **shellcheck** (>=0.10.0) — static analysis for `build.sh` and all shell scripts.

---

## 3. Pixi ecosystem extensions

All in `local-recipes`. These are CLIs invoked as `pixi-<name>` or `pixi <name>`.

- **pixi-build-rattler-build / pixi-build-cmake / pixi-build-python / pixi-build-rust**
  — pixi build backends: let a `pixi.toml` `[package]` build conda packages from
  rattler-build recipes, CMake projects, Python projects (PEP 517), or Cargo crates
  respectively.
- **pixi-pack** (>=0.7.11) / **pixi-unpack** (>=0.7.11) — bundle a pixi environment into a
  single archive for offline/air-gapped machines, and unpack it there.
- **pixi-to-conda-lock** (>=0.4.3) — convert `pixi.lock` → `conda-lock.yml` for tools
  that only understand conda-lock.
- **pixi-diff** (>=0.1.8) — diff two `pixi.lock` files (what changed between lock states).
- **pixi-outdated** (>=0.2.1) — list dependencies in `pixi.toml` with newer versions
  available.
- **pixi-inject** (>=0.1.3) — inject extra conda packages into an existing pixi env
  without editing the manifest.
- **pixi-install-to-prefix** (>=0.1.8) — install a pixi env to an arbitrary directory
  prefix.
- **pixi-inspect** (>=2.0.2) — inspect/retrieve metadata from a conda package.
- **pixi-kernel** (>=0.7.1) — Jupyter kernels backed by pixi envs.
- **pixi-pycharm** (>=0.0.12) — PyCharm/IDE interpreter integration for pixi.
- **pixi-skills** (>=0.1.6) — manage coding-agent skills using pixi.
- **nebi-cli** (>=0.14) — `nebi`; local-first workspace management for pixi projects.
- **pixitainer** (>=0.8.3) — containerize a pixi workspace with a single command.
  **`local-recipes` env, linux-64 only** (`[feature.local-recipes.target.linux-64.dependencies]`):
  its own recipe is `build.skip: "not linux"`, so it cannot live in the cross-platform
  dependencies table without breaking the win-64/osx-arm64-min solves. Story 10.2
  uncommented + bumped the formerly-stale `>=0.7.1` pin — Story 10.3's pixitainer
  container-evaluation AC needs the tool installed and available first.

---

## 4. Python build, publish & supply-chain security

All in `local-recipes`.

- **setuptools** (>=81) / **wheel** (>=0.48.0) — classic build backend + wheel format
  utilities.
- **setuptools-scm** (>=10.3.4) — derive package versions from git tags.
- **hatchling** (>=1.32.4) — modern PEP 517 build backend (Hatch).
- **python-build** (>=1.6.1) — PEP 517 frontend: `python -m build` produces sdist+wheel
  from any backend.
- **twine** (>=7.0.0) — upload artifacts to PyPI (check + upload).
- **pip-audit** (>=2.10.1) — audit installed Python environments / requirements
  against known-vulnerability databases (OSV/PyPI advisory).
- **bandit** (>=1.9.4) — static security linter for Python source (dangerous calls,
  injection patterns, weak crypto).
- **deptry** (>=0.25.1) — dependency-hygiene checker: finds unused, missing, and
  transitive dependencies in a Python project by comparing imports against the
  declared manifest (core of the pyforge-warden effort).
- **osv-scanner** (>=2.6.0) — Google's OSV vulnerability scanner (Go binary): scans
  lockfiles, manifests, SBOMs, and directories against the osv.dev database.
- **appthreat-vulnerability-db** (>=6.7.0) — `import vdb`; AppThreat multi-source
  vulnerability database library (OSV + GHSA sources locally; CVE, EPSS, CWE data
  model). Present in BOTH `local-recipes` and `vuln-db`; the ~600MB local DB lives at
  `.claude/data/conda-forge-expert/vdb/` (built via `pixi run -e vuln-db vdb-refresh`).
- **go-sops** (>=3.13.3) — `sops` binary; encrypted-secrets editor (YAML/JSON/env
  files; age/KMS/PGP backends).
- **age** (>=1.3.2) — `age` / `age-keygen`; modern simple file encryption (the
  default sops backend here).

---

## 5. Project scaffolding & templating

- **copier** (>=9.18.2) — template-based project scaffolding with first-class
  update/recopy support; **pyforge-marshal-only** (Genesis seed installer engine,
  `marshal seed` verbs). Imported only in `seed/engine/copier.py` (P-02).
- **cookiecutter** (>=2.7.1) — template-based project scaffolding from local or git
  templates (general-purpose; not used by Genesis).
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
- **numpy** (>=2.5.3) — n-dimensional arrays, the numeric foundation (NumPy 2.x API).
- **pandas** (>=3.0.6) — DataFrames for tabular data (2.x resolved).
- **polars** (>=1.44.2) — Rust-backed columnar DataFrames; lazy queries, streaming;
  much faster than pandas for large data.
- **pyarrow-all** (>=24.0.0) — `import pyarrow`; Apache Arrow with ALL extras: Parquet,
  Datasets, Flight RPC, ORC, ADBC-adjacent IO. The interchange layer between pandas,
  polars, duckdb, dagster, daft.
- **getdaft** (>=0.6.13) — `import daft`; distributed DataFrames for multimodal data
  (images/urls/embeddings as first-class columns), Rust engine, scales out.
- **dask-core** (>=2026.8.0) — `import dask`; task-graph parallelism (`dask.delayed`,
  bags, dask.dataframe). NOTE: this is *core only* — the `distributed` scheduler is
  not installed; use the threaded/process schedulers.
- **dbgpt** (>=0.8.2) — `import dbgpt`; open-source AI-native data-app development
  framework (AWEL workflows + agents), aka DB-GPT.

SQL engines & tooling:
- **duckdb** (>=1.5.5) — embedded analytical (OLAP) SQL database; reads/writes
  Parquet/CSV/Arrow natively; the default local analytics engine.
- **dbt-core** (>=1.12.5) + **dbt-duckdb** (>=1.11.0) + **dbt-postgres** (>=1.11.0) —
  SQL transformation framework + adapters. Unblocked 2026-08-30: the click conflict
  that pinned the trio out fell when conda-recipe-manager (exact click==8.2.1
  feedstock pin) moved to the grayskull-only `crm` feature.
- **duckdb-server** (>=0.31.0) — Mosaic's DuckDB HTTP/Arrow server (`duckdb-server`
  CLI; the import package is `pkg`, NOT `duckdb_server`). **pyforge-atlas env,
  linux-64 only** (hard-deps `socketify`, which conda-forge lacks on
  osx-arm64/win-64); env supply only, never a package run-dep. The CAP-19 query
  plane's optional HTTP/Arrow face — launched ONLY by
  `pyforge.atlas.query_plane_boot` (Story 20.1's one boot script,
  `query-plane-boot` task) when `PYFORGE_PLATFORM_STACK_UP` is truthy; the
  in-process library face never needs it. NOTE: the installed server hard-codes
  its listen port to 3000 (no port/host flags; one positional arg, the DB path).
- **sqlglot** (>=30.19.0) — parse, transpile, optimize SQL across ~30 dialects;
  build/rewrite SQL ASTs programmatically (used for feedstock analysis).
- **sqlfluff** (>=4.3.0) — SQL linter/formatter, dialect-aware.
- **psycopg2** (>=2.9.10) — real PostgreSQL driver (DB-API).
- **apsw** (>=3.53.4.0) — thin, full-featured SQLite bindings. **vuln-db env only**
  (backend for the AppThreat vdb).

Ibis — one dataframe API over many engines:
- **ibis-framework** (>=12) — `import ibis`; portable dataframe library: write one
  expression, execute on any backend; lazy, SQL-generating.
- **ibis-duckdb / ibis-polars / ibis-sqlite / ibis-postgres / ibis-mssql /
  ibis-oracle** (>=12) — the installed execution backends. (BigQuery via
  google-cloud-bigquery is separate, § 11.)
- **boring-semantic-layer** (>=0.2.0) — lightweight semantic layer on Ibis
  (conda **SelfExplainML**; conda-forge still ~0.2.0): declare metrics/dimensions
  once, query them across backends.

Small utilities:
- **tablib** (>=3.10.0) — one API for tabular import/export: XLSX, CSV, JSON, YAML, ODS.
- **tabulate** (>=0.10.0) — pretty-print tables as text/markdown/grid.
- **tomlkit** (>=0.15.1) — style-preserving TOML read/write (round-trips comments).
  Resolves to 0.13.2: dagster-dg-core and pyforge-marshal both cap it below 0.13.3.
- **structlog** (>=26.1.0) — structured (key-value/JSON) logging.
- **ruamel.yaml** (>=0.18.17) — round-trip YAML that preserves comments and key order
  — the correct choice for editing `recipe.yaml`/`conda-forge.yml` in place.
- **pyyaml** (>=6.0) — plain YAML load/dump; import name is `yaml`, not `pyyaml`.
  Reach for it only when you are READING YAML (pyforge-doctor's `sources/chain.py`
  frontmatter parser, Story 6.6). To EDIT a YAML file in place use `ruamel.yaml`
  above — PyYAML discards comments and reorders keys on round-trip. Also a
  `pyforge-doctor` package run-dependency, not just an env library.
- **frozendict** — immutable mapping type.
- **defusedxml** (>=0.7.1) — XML parsing hardened against XXE/entity bombs; use it for
  untrusted XML.

---

## 7. Workflow orchestration, pipelines & data quality

All in `local-recipes`.

- **dagster** (>=1.13.24) — asset-based data orchestrator: software-defined assets,
  schedules, sensors, partitions, type-checked IO.
- **dagster-webserver** (>=1.13.24) — the Dagster UI (`dagster dev`).
- **dagster-pipes** (>=1.13.24) — run external-process transform logic (scripts,
  containers) with structured logging/metadata back into Dagster.
- **kedro** (>=1.6.0) — opinionated pipeline framework: nodes, pipelines, data
  catalog, config environments. (A Kedro 3.14-compat warning is suppressed via
  `PYTHONWARNINGS` in the env activation.)
- **kedro-datasets** (>=9.6.0) — all Kedro data connectors (pandas/polars/spark
  datasets, APIs, cloud storage).
- **kedro-dagster** (>=0.8.0) — deploy Kedro pipelines onto Dagster.
- **kedro-viz** (>=12.4.0) — interactive browser visualization of Kedro pipelines.
- **kedro-mcp** (>=0.1.2) — MCP server exposing Kedro prompts/tools to agents. From conda-forge (run-depends fastmcp, which conda-forge ships at 4.x on mcp 2.x).
- **kedro-skills** (>=0.1.1) — `kedro skills` CLI: distributes AI coding-agent
  guidance (Markdown) into a Kedro project's `.claude/skills/` / `.agents/skills/`
  trees + an `AGENTS.md` block; ships one skill, `catalog-config`. **pyforge-atlas
  env only** (dev/tooling, never a package run-dep); exact-pinned to the audited
  version (no floor) — see the audit at
  `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption/kedro-skills-audit-report.md`.
- **great-expectations** (>=1.23.2) — data-quality contracts: expectations suites,
  validation, data docs (used inside Kedro nodes).
- **pandera** (>=0.32.1) — lightweight statistical dataframe validation via typed
  schemas (pandas/dask/spark).
- **openlineage-python** (>=1.53.0) — `import openlineage.client`; emit OpenLineage
  data-lineage events.
- **opentelemetry-api / opentelemetry-sdk** (>=1.44.0) — traces/metrics/logs
  instrumentation and export (OTLP).
- **watchdog** (>=6.0.0) — filesystem event monitoring (`watchmedo` CLI); live-reload
  loops.
- **apscheduler** (>=3.11.3) — in-process job scheduler; **pyforge-scribe env only**,
  the opt-in `PYFORGE_SCRIBE_TRIGGER_BACKEND=apscheduler` backend (Story 8.1) — does
  not persist across logout/reboot on its own.

---

## 8. Visualization & dashboards

All in `local-recipes`.

- **matplotlib** (>=3.11.2) — general-purpose static 2D plotting.
- **plotly** (>=7.1.0) — interactive web-based charts (JSON-serializable figures).
- **bokeh** (>=3.9.2) — interactive HTML/JS plots and apps from Python; server mode
  for streaming.
- **panel** (>=1.9.4) — HoloViz app framework: turn plots/widgets/dataframes into
  dashboards and web apps; works in notebooks and as served apps.
- **panel-graphic-walker** (>=0.6.5) — embeds Graphic Walker (open-source Tableau
  alternative) as a Panel pane for drag-and-drop exploration.
- **vizro** (>=0.1.60) — McKinsey's low-code dashboard framework (config-driven, on
  top of Plotly/Dash).
- **vizro-ai** (>=0.4.2) — natural-language → Vizro charts/dashboards (LLM-assisted).
- **vizro-mcp** (>=0.1.4) — MCP server for creating Vizro dashboards from agents.
- **kedro-viz** — (listed in § 7) pipeline DAG visualization.
- **graphviz** (>=14.1.2) — Graph layout engine (the `dot` binary); drives the
  kedro-viz prototype's DAG-image (SVG) emitter.
- **python-graphviz** (>=0.21) — Python interface to Graphviz — **imports as
  `graphviz`**; used by the prototype DAG-image generator.
- **graphviz2drawio** (>=1.2.0) — Convert Graphviz/DOT output into editable
  draw.io (mxGraph) XML diagrams.

NOT available (deliberately excluded, see § 16): streamlit, chainlit, pygwalker,
perspective.

---

## 9. Documents, PDFs, Office, OCR, diagrams & media

All in `local-recipes`. This is the "deckcraft / markitdown" stack — everything needed
to read, convert, and generate documents.

Any-format → Markdown (LLM ingestion):
- **markitdown** (>=0.1.8) — Microsoft's converter: PDF, DOCX, XLSX, PPTX, HTML,
  images (w/ OCR), audio → clean Markdown for LLM pipelines. The loaders below back it.
- **mammoth** (>=1.12.2) — focused, high-fidelity .docx → HTML/Markdown.
- **markdown** (>=3.11) — Markdown → HTML parser.
- **markdownify** (>=1.2.3) — HTML → Markdown.
- **beautifulsoup4** (>=4.15.0) — `from bs4 import BeautifulSoup`; forgiving HTML
  parsing/scraping.
- **lxml** (>=6.1.3) — fast C-backed XML/HTML parsing + XPath.
- **pandoc** (>=3.11) — `pandoc` CLI; universal document converter (md ↔ docx ↔ html
  ↔ latex ↔ epub ↔ rst …).

PDF stack (pick by need):
- **pymupdf** (>=1.28.0) — `import pymupdf` (a.k.a. fitz); fastest PDF text/layout
  extraction + rendering + annotation.
- **pdfplumber** (>=0.11.10) — precise text + **table** extraction with layout
  geometry; best for tabular PDFs.
- **pdfminer.six** (>=20260107) — `import pdfminer`; pure-Python low-level text
  extraction (markitdown's backend).
- **pypdf** (>=6.19.0) — pure-Python PDF read/write/merge/split/encrypt.
- **pdf2image** (>=1.17.0) — PDF pages → PIL images (Poppler-backed) for vision-model
  input.
- **poppler** (>=26.9.0) — PDF rendering binaries (`pdftoppm`, `pdftotext`, …).
- **qpdf** (>=12.4.1) — `qpdf` CLI; PDF transforms: linearize, compress,
  encrypt/decrypt, split.

Office formats:
- **python-docx** (>=1.2.0) — `import docx`; read/write Word .docx.
- **python-pptx** (>=1.0.2) — `import pptx`; read/write PowerPoint .pptx.
- **openpyxl** (>=3.1.5) — read/write Excel .xlsx.
- **xlrd** (>=2.0.2) — read legacy Excel .xls.
- **odfpy** (>=1.4.1) — OpenDocument (.odt/.odp/.ods) read/write.
- **olefile** (>=0.47) — parse legacy OLE2 files (old .doc/.xls containers).
- **office2pdf** (>=0.7.0) — `office2pdf` CLI; DOCX/XLSX/PPTX → PDF. Pure Rust, so no
  LibreOffice/headless-Office dependency. Ships on all three platforms
  (linux-64 / osx-arm64 / win-64), so it is an unconditional `local-recipes` dep.
- **pptxgenjs** (>=4.0.1) — JavaScript (Node) library for *generating* .pptx decks
  programmatically; used by the deck workflows (`docs/specs/presentation-deck.md`).
- **pptxgenjs-plus** (>=4.2.1) — maintained fork of PptxGenJS (`require('pptxgenjs-plus')`).
  SelfExplainML `noarch`; needs `nodejs >=24`. Set `NODE_PATH=$CONDA_PREFIX/lib/node_modules`.
  Does not include the separate `pptxgenjs-plus-jsx` package.

OCR & images:
- **tesseract** (>=5.5.3) — Google's OCR engine binary.
- **pytesseract** (>=0.3.13) — Python wrapper for tesseract (scanned-PDF fallback).
- **ocrmypdf** (>=17.12.1) — `ocrmypdf` CLI; adds a searchable OCR **text layer** to a
  scanned PDF while keeping the original page images (tesseract-backed).
  **linux-64 ONLY here.** The package itself is `noarch`, but it hard-deps `pngquant`,
  which conda-forge ships only for linux-64/osx-64 — so it is declared under
  `[feature.local-recipes.target.linux-64.dependencies]`, not as a shared dep (a shared
  one makes the workspace lock unsolvable on `osx-arm64`). Lift the gate if
  pngquant gains osx-arm64/win-64 builds.
- **pillow** (>=12.3.0) — `from PIL import Image`; image open/convert/resize/draw.

Slides & diagrams:
- **marp-cli** (>=4.2.3) — `marp`; Markdown → HTML/PDF/PPTX slide decks.
- **d2** (>=0.7.1) — `d2` CLI; Terrastruct diagram-as-code compiler (.d2 → SVG/PNG).
- **mermaid-py** (>=0.9.0) — `import mermaid`; render Mermaid diagram source from
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
- **transformers** (>=5.17.0) — model hub + pipelines (text, vision, audio);
  tokenizers; Trainer.
- **accelerate** (>=1.15.0) — device placement / mixed precision / multi-GPU
  launching for HF models.
- **diffusers** (>=0.39.0) — diffusion pipelines (Stable Diffusion et al.) for local
  image generation.
- **sentence-transformers** (>=6.1.0) — dense text embeddings + cosine search; used
  for long-document RAG, slide dedup, template matching.
- **sentencepiece** (>=0.2.1) — subword tokenizer runtime (T5/MarianMT/SD3 need it).
- **hf-transfer** (>=0.1.9) — Rust accelerator for model downloads; enable with
  `HF_HUB_ENABLE_HF_TRANSFER=1`.

Local inference runtimes:
- **llama.cpp** (>=10751) — `llama-cli` / `llama-server` binaries; GGUF model
  inference on CPU/GPU; `llama-server` exposes an OpenAI-compatible API.
- **ollama** (>=0.32.15) — the Ollama server binary (Go): `ollama serve`,
  `ollama run <model>`; local model registry + OpenAI-compatible endpoint.
- **ollama-python** (>=0.6.2) — `import ollama`; Python client for that server.
- **mlx** (>=0.32.0) — Apple's array framework. **linux-64 + osx-arm64 only** (no
  Windows). Metal-accelerated on M-series (2-3x llama.cpp on some workloads);
  on Linux it runs against BLAS/LAPACK — fine for experimentation, no perf win.
- **mlx-lm** (>=0.31.3) — `import mlx_lm`; LLM runner on mlx (generate/serve/convert);
  preferred local runner on Apple Silicon. Same platform limits as mlx.

Knowledge & indexing for agents:
- **cocoindex** (>=1.0.20) — incremental indexing/transformation engine for
  long-horizon agents (recompute only what changed).
- **graphifyy** (>=0.9.51) — turn a folder of code/docs/papers/images into a
  queryable knowledge graph for coding assistants.
- **codegraph** (>=1.6.0) — pre-indexed code knowledge graph for coding agents
  (fewer tokens, fewer tool calls, 100% local). From conda-forge (all platforms
  since 2026-09-25); pinned **linux-64 only** here for now; its build pins nodejs 24.
- **headroom-ai** (>=0.37.0) — context-optimization layer (`headroom` CLI + lib,
  Rust core): prompt/context compression middleware for agent loops. Unblocked
  2026-08-30 (needed click >=8.3.3; see conda-recipe-manager note in § 3).
  All platforms. Do NOT re-declare it as a pypi-dependency: tested 2026-08-30,
  a pypi entry evicts the pyforge-core/pyforge-doctor conda path-packages.
  **`pyforge-guild` only** (not `local-recipes`): its `[proxy]` extra — the
  actual `headroom wrap claude` wire-compression proxy, not just the CLI —
  needs **openai** (>=2.14.0), **orjson** (>=3.9.14), **magika** (>=0.6.0,
  Google's ML file-type sniffer), **zstandard** (>=0.20.0), **onnxruntime**
  (>=1.24.0), **watchdog** (>=4.0.0), and **sqlite-vec** (>=0.1.6, pypi-only —
  not on conda-forge; import name `sqlite_vec`) alongside the already-present
  fastapi/uvicorn/httpx/mcp/websockets. Found missing 2026-09-20: `marshal
  factory dispatch`'s `claude` harness profile always declares a `[wrapper]`,
  so wire `"auto"` always resolves enabled, and without these the wrapper
  crashed the whole dispatch in under 2 seconds (`ModuleNotFoundError:
  openai`) before the harness session ever started.
- **caveman-installer** (>=2.7.0) — Claude Code output-token compression skill
  installer (`caveman-install`; ~65% output-token cut). Renamed 2026-09-24 from
  `caveman` (a local-only name that never actually existed upstream) to the
  package's correct name now that conda-forge has graduated it under it — the
  binary + skill payload are unchanged, so the rename is transparent to every
  consumer (marshal resolves by binary path, not package name). **linux-64
  only** in both envs for now, from conda-forge: build 2 (2026-09-25) ships a
  nodejs-24 variant on every platform, which coexists with codegraph's nodejs
  pin and with `pyforge-foundry-full`'s dagster/protobuf chain (libabseil
  20260107; conda-forge's nodejs >=26.4 links libabseil 20260526). `marshal seed kit`'s caveman-skill item and `marshal
  factory dispatch`'s own `_seed_dispatch_output_layer` both probe
  `caveman-install` with a bare `shutil.which` (no `fallback_bin_dirs`,
  unlike headroom's harness-binary resolution), so it has to be on the SAME
  env's PATH the dispatch process itself runs in -- previously absent from
  `pyforge-guild` on the theory that the `output` layer's graceful skip made
  it safe to omit, but that left every dispatch running unwrapped by default.

---

## 11. LLM APIs, agent frameworks, MCP & A2A

All in `local-recipes`, except `mcp`, which is also a run-dependency of the
`pyforge-herald` package and therefore a member of the lean `pyforge-herald` env.
This is the stack for *building* agents and agent servers.

Provider SDKs:
- **anthropic** (>=0.76.0) — official Claude SDK: Messages API, streaming, tool use,
  prompt caching.
- **google-genai** (>=2.25.0) — `from google import genai`; Gemini API client.
- **github-copilot-sdk** (>=1.0.14) — drive GitHub Copilot programmatically from
  Python.
- **langchain-anthropic** (>=1.3.1) — LangChain chat-model integration for Claude.
- **lumen-ai-anthropic** (>=1.3.0) — Anthropic backend for HoloViz Lumen AI
  (chat-with-your-data on top of Panel).

Agent frameworks:
- **pydantic-ai** (>=2.51.0) — typed agent framework from the Pydantic team:
  structured outputs, tools, dependency injection, model-agnostic.
- **agno** (>=2.6.22) — lightweight multi-modal agent framework: any provider,
  multi-agent teams, memory, knowledge stores, structured outputs, monitoring.

Agentic engines (**`python-agent-platform` env only**, CAP-5, Story 10.2 — the
"one factory-sourced environment" for running these alongside Django on
`python 3.12`, distinct from the agent-*building* SDKs above):
- **langflow** (>=1.12.3) — visual agent/RAG flow builder + runtime (langflow-suite
  feedstock, `python_min` 3.11). Pulls in `slowapi` transitively via
  `langflow-base`, which resolves to a `SelfExplainML`-channel 0.1.10 build here
  (see `channel-priority` note on the feature, § "Version pins" above).
- **chromadb** (>=1.5.9) / **langchain-chroma** (>=1.1.0) /
  **elevenlabs** (>=1.52.0,<2.0.0) — Story 11.1: `langflow.main.create_app()`
  hard-imports all three at module load (`langflow.api.v1.knowledge_bases`,
  `lfx.base.knowledge_bases.backends.chroma`, `langflow.api.v1.voice_mode`),
  even though the langflow-suite recipe lists all three as `run_constraints`
  (soft) rather than `run` (hard) for the `langflow` output — `import
  langflow.main` `ModuleNotFoundError`s on each in turn without them, verified
  live. Pinned to the SAME floors the recipe's own `run_constraints` declare.
- **psycopg** (>=3.2) — Story 11.1: Langflow's own SQLAlchemy engine needs a
  Postgres driver, and neither `psycopg` (v3) nor `asyncpg` is anywhere in the
  langflow-suite recipe (upstream langflow-base gates one behind an unused pip
  extra the conda recipe never turns into a dependency). `LANGFLOW_DATABASE_URL`
  is a `postgresql://` URL; Langflow's own `services/database/service.py`
  rewrites that scheme to `postgresql+psycopg` itself. A DIFFERENT package
  from `psycopg2` (below) — psycopg 3 supports SQLAlchemy's async engine
  natively; conda-forge's `psycopg` build already bundles the compiled
  `psycopg_c` extension (no separate `psycopg-binary`/`psycopg-c` package
  exists on conda-forge, unlike PyPI).
- **dbgpt-serve** (>=0.8.2) — the DB-GPT serving/API layer (db-gpt feedstock),
  installed alongside **dbgpt** (§ 6 — a separate package from the same
  feedstock, also floor `>=0.8.1`, independently pinned in both
  `local-recipes` and this env).

Model Context Protocol (MCP):
- **mcp** (>=2.2.0) — official MCP Python SDK (clients + servers, stdio/SSE).
  This repo's `conda_forge_server` / `gemini_server` (`.claude/tools/`) and the
  local `kedro-mcp` build are all on the SDK's own `mcp.server.mcpserver.MCPServer`
  (the renamed, current-era successor to `mcp.server.fastmcp.FastMCP`) — not
  third-party fastmcp (2026-08-29).
- **fastmcp** (>=4.0.10) — decorator-style third-party framework for building
  MCP servers fast; kedro-mcp's run-dep. From conda-forge since 4.x shipped
  there on mcp 2.x (2026-09-26); the SelfExplainML channel pin is gone.
- **fastmcp-slim** (>=4.0.10) — fastmcp's own exact-pinned core dep.
- **langchain-mcp-adapters** (>=0.3.1) — expose MCP tools/resources as LangChain
  tools and vice versa.
- **django-mcp-server** (>=0.5.7) — serve MCP from a Django app.
- **vizro-mcp** / **kedro-mcp** — domain MCP servers (§ 8 / § 7).

Agent2Agent (A2A) & ACP:
- **a2a-sdk** (>=1.1.2) — `import a2a`; official Python SDK for the Agent2Agent
  protocol (agent cards, task lifecycle, messaging).
- **fasta2a** (>=2.0.1) — FastAPI-style A2A server implementation.
- **claude-agent-acp** (>=0.81.2) — bridge the Claude Agent SDK to the Agent Client
  Protocol (ACP) so editors/clients that speak ACP can drive Claude agents.

---

## 12. BMAD Method suite (agentic SDLC)

All in `local-recipes` unless noted (bmad-method also in the base `python` feature;
`mybmad-dashboard` is `bmad-ui`-only). These power the planning/dev workflow documented
in `CLAUDE.md` and `_bmad-output/`.

- **bmad-method** (>=6.12.0) — core installer/CLI: agents (PM, architect, dev, …),
  planning workflows (PRD → architecture → epics → stories), dev execution. 6.10+
  <!-- governance-currency:ignore-start (bmad-dev-auto is the pre-6.11 name of bmad-build-auto, cited historically for what 6.10 added) -->
  gains `bmad-dev-auto`.
  <!-- governance-currency:ignore-end -->
- **bmad-loop** (>=0.12.0) — deterministic "ralph-loop" orchestrator with TUI; spawns
  coding-agent sessions in tmux (hence tmux below). From conda-forge: a `__unix`
  noarch variant (tmux) and a `__win` one (uv; no multiplexer — psmux is not on
  conda-forge) since 0.12.0 build 1.
- **bmad-builder** (>=2.2.2) — build custom BMAD modules.
- **bmad-module-template** (>=0.1.0) — scaffold for new BMAD modules.
- **bmad-creative-intelligence-suite** (>=0.3.2) — CIS expansion module (creative /
  ideation workflows).
- **bmad-method-test-architecture-enterprise** (>=1.27.2) — TEA module: enterprise
  test-architecture workflows.
- **bmad-eval-quality** (>=4.3.0) — `eval-quality` CLI: compile / seal / preflight /
  score Behavioral Evaluation Contracts (twin-run grading: clean vs planted-defect). Commit-pinned
  0.2.0 line from `main` — npm/tag 0.1.0 lack `score`. Bin is `eval-quality`, not `bmad-eval-quality`.
  Pinned in the linux-64 / osx-arm64 target tables only: SelfExplainML has just the `__unix`
  noarch variant (the `__win` one needs a Windows build), so win-64 skips it like skill-forge.
  <!-- governance-currency:ignore-start (bmad-method-wds-expansion is quoted because it was retired) -->
  (`bmad-method-wds-expansion` retired 2026-09-05: upstream deprecated, folded into BMM as `bmad-ux`.)
  <!-- governance-currency:ignore-end -->
- **bmad-utility-skills** (>=2.0.0) — 10 maintainer utility skills.
- **bmad-labs-skills** (>=1.0.0.dev0) — community skills marketplace (22 skills).
- **bmad-manticore** (>=3.1.0.dev0) — brain dump → a rendered, graphics-rich video in
  your own words. `noarch`. Note the version is a `.dev0` pre-release: upstream wrote
  2.0.0 but never tagged it, so this rides a commit pin until a `v2.0.0` tag appears.
- **bmad-dashboard** (>=1.2.2.dev0) — VS Code extension installer for the BMAD
  dashboard UI. Also provisioned in the `bmad-ui` env (from the locally-built
  consume-not-submit mirror); task `bmad-dashboard-install`.
- **mybmad-dashboard** (>=0.1.0.dev0) — MyBMAD Next.js web dashboard + `mybmad`
  launcher (local PostgreSQL on :3002). **`bmad-ui` env only, linux-64 only** —
  commented out in `local-recipes` (line 681 of `pixi.toml`). Task: `mybmad`.
- **bmad-suite** (>=2026.9.26) — `noarch: generic` metapackage (CAP-1–4,
  `spec-bmad-suite-metapackage`) pinning all 13 active suite members
  (including `bmad-dashboard` + `mybmad-dashboard`) at upstream-aligned
  floors; one install surface for greenfield operators. **`bmad-suite-full`
  env only, linux-64 only** — not in `local-recipes`, which keeps its own
  explicit member pins instead. Docs: `install-matrix.md`'s Greenfield
  one-pin section.
- **tmux** (>=3.7b_) — terminal multiplexer; **linux-64 + osx-arm64 only**; required by
  bmad-loop session spawning.

---

## 13. Web frameworks & cloud services

All in `local-recipes`.

Django stack (LTS-pinned):
- **django** (5.2 LTS) — the web framework.
- **channels** (4.x) + **daphne** (4.x) — WebSockets/async protocol layer + ASGI
  server for Django.
- **asgiref** (>=3.12.1,<4.0) + **channels_redis** (4.x) — **pyforge-steward env only**:
  daphne's WSGI->ASGI adapter (`asgiref`, incl. `database_sync_to_async`) and the
  cross-worker channel-layer backend for `channels` (`channels_redis`, needed once
  workers > 1), Story 9.5.
- **wagtail** (7.4 LTS) — Django CMS.
- **coderedcms** (6.x) — CRX/CodeRed CMS built on Wagtail (marketing-site batteries).
- **django-lasuite** (>=0.0.29) — common library for La Suite numérique Django
  projects.
- **bokeh-django** (>=0.2.1) — serve Bokeh apps inside Django.
- **django-mcp-server** — (§ 11) MCP endpoint inside Django.

Django-host stack (**`python-agent-platform` env only**, CAP-5, Story 10.2 —
the Django host the § 11 agentic engines mount into, Epic 11):
- **django** (>=5.2,<6) — also present in this env (in addition to
  `local-recipes`, above) — a separately-scoped install; the engines
  (`langflow`/`dbgpt`/`dbgpt-serve`) and this Django floor must resolve
  together on the SAME `python 3.12` interpreter.
- **fastapi** (>=0.141.1) — Story 10.1's ASGI/FastAPI-integration seam; also
  arrives transitively via `langflow-base`'s own `fastapi >=0.135.0,<1.0.0`
  run-dep, so the explicit pin only documents intent.
- **django-health-check** (>=4.6.1) — Story 10.1's K8s liveness/readiness
  requirement (CAP-1); needs `django>=5.2`, matching this env's floor. A
  DIFFERENT install from Story 10.1's pip-pinned `django-health-check==3.24.0`
  in `src/platform/requirements/*.txt` — the two are unrelated, differently-scoped
  installs in different environments.
- **psycopg2** (>=2.9.10) — also present in this env (in addition to
  `local-recipes`, § 6) — the PostgreSQL client driver Django/Celery need to
  reach the "infrastructure is exactly PostgreSQL + Redis" backing service.
- **redis-py** (>=8.1.0) — the Redis client driver for the same constraint.
  **Imports as `redis`** (§ 17). This floor also forces the solver off
  conda-forge's `slowapi` (§ 11) onto the `SelfExplainML` build — do not relax it.

`platform-dev` env only (AD-16, Story 11.1 — composes onto `python-agent-platform`,
so `pixi install -e platform-dev` gives the engines above PLUS these; per-user local
PROCESSES, not containers or managed services):
- **postgresql** (>=17) — per-user local PostgreSQL server (`initdb`/`pg_ctl`/`psql`
  binaries). The ONE database `public`/`langflow_schema`/`dbgpt_schema` all share.
- **pgvector** (>=0.8.1) — PostgreSQL extension, same instance — no separate
  vector-store service (AD-1).
- **redis-server** (>=8.10.1) — per-user local Redis server (`redis-server` binary).
  Cache + Celery broker (AD-1). **No native win-64 build** — AD-16's native-Windows
  sub-posture note: `fakeredis` + eager-Celery stand in there, or WSL2/a remote.
- **kubernetes-helm** (>=4.3.0) — the `helm` CLI, for Epic 12 chart work.
- **kubernetes-client** (>=1.34.3) — `kubectl`, for the same chart/deploy work.
- **django-debug-toolbar** (>=8.0.0) — Story 56.1 / pdl:CAP-1. Required because
  `config.settings.local` always imports `debug_toolbar`. Not on the image env.

Cloud / storage / identity:
- **google-cloud-bigquery** (>=3.45.2) — `from google.cloud import bigquery`;
  BigQuery client. Used by cf_atlas Phase P (opt-in `PHASE_P_ENABLED=1`); auth via
  ADC creds cached by the `gcloud` env.
- **google-cloud-sdk** (>=586.0.0) — the `gcloud` CLI. **`gcloud` env only,
  linux/macOS only.** Used once for `gcloud auth application-default login`; after
  that the BigQuery lib picks up cached ADC automatically.
- **azure-identity** (>=1.25.3) — Azure AD/Entra credential objects for all Azure
  SDKs.
- **msgraph-sdk** (>=1.48.0) — Microsoft Graph API client (M365: mail, files, users).
- **minio** (>=7.2.20) — Python client SDK for MinIO / any S3-compatible object
  store.
- **moto** (>=5.2.3) — mock AWS services in tests (S3, EC2, …) without network.
- **boto3** (>=1.43.102 `platform-ci-test`, >=1.43.75 `python-agent-platform`) — AWS
  SDK; `config.object_storage`'s S3 client construction against the local
  Silo/Garage/SeaweedFS backends or real StorageGRID (Story 50.3); not an AWS
  runtime dependency.
- **silo** (>=2026.9.16.0.0.0) — default local S3-compatible object-storage
  server; `platform-object-storage` env only. From conda-forge (date-versioned
  since 2026-09-16); Story 50.1's SelfExplainML build is superseded.
- **garage** (>=2.4.1) — alternative S3-compatible backend; `platform-object-storage`
  env only, linux-64 only (no win-64 conda-forge build).
- **seaweedfs** (>=4.47) — alternative S3-compatible / distributed storage backend
  (files, Iceberg tables); `platform-object-storage` env only, linux-64 only.

HTTP & APIs:
- **requests** (>=2.34.2) — the classic sync HTTP client.
- **httpx** (>=0.28.1) — modern HTTP client, sync + async, HTTP/2.
- **httpx2** (>=2.13.1) — the httpx 2.x line under a separate package name. Declared in
  `[feature.pyforge-herald.dependencies]` ONLY — a different environment from the
  `httpx` (>=0.28.1) above, which belongs to `local-recipes`. Herald's Story 6.4
  evidence-link HTTP client (also a package run-dependency); the floor mirrors `mcp`'s
  own transitive pin. Check which env you are in before assuming which one resolves.
- **gql** (>=4.0.0) — GraphQL client (v4+ drops the websockets dep).

---

## 14. Developer tooling: lint, type-check, test, terminal

All in `local-recipes`.

Linters & formatters:
- **ruff** (>=0.16.9) — extremely fast Python linter + formatter (flake8/isort/black
  replacement). Default Python QA tool here.
- **yamllint** (>=1.38.0) — YAML linting.
- **taplo** (>=0.10.0) — TOML linter/formatter/LSP (use on pixi.toml itself).
- **sqlfluff** — (§ 6) SQL lint/format.
- **nbqa** (>=1.9.0) — run ruff/mypy/etc. over Jupyter notebooks.
- **shellcheck** — (§ 2) shell script analysis.

Type checkers (three available — pick one per task):
- **pyright** (>=1.1.414) — Microsoft's fast type checker (the default for quick
  checks).
- **mypy** (>=2.3.1) — the reference type checker (plugin ecosystem).
- **pyrefly** (>=1.3.1) — Meta's Rust-based checker (fastest on big codebases).

Testing:
- **pytest** (>=9.1.1) — the test framework (repo suites live under
  `.claude/skills/conda-forge-expert/tests`).
- **pytest-mock** (>=3.15.1) — `mocker` fixture over unittest.mock.
- **pytest-cov** (>=7.1.0) — coverage reporting.
- **pytest-xdist** (>=3.8.0) — parallel test execution (`-n auto`).

Browser automation:
- **playwright** (>=1.63.0) — the Node Playwright CLI (browser installs, codegen).
- **playwright-python** (>=1.62.0) — `from playwright.sync_api import ...`; drive
  Chromium/Firefox/WebKit from Python (scraping, E2E, screenshots).

Terminal & CLI building:
- **rich** (>=14.3.4) — rich terminal output: tables, progress bars, markdown,
  syntax highlighting, tracebacks.
- **typer** (>=0.27.2) — build CLIs from type-hinted functions (click-based).

Node package managers:
- **pnpm** (>=12.4.1) — fast, disk-efficient npm alternative (default for JS builds
  here; in .bat scripts always `call pnpm`).
- **yarn** (>=4.18.1) — Yarn Berry.

---

## 15. Vulnerability & SBOM environment (`vuln-db`)

A deliberately separate env (`pixi run -e vuln-db ...`) so `local-recipes` stays lean.
First `vdb-refresh` downloads ~600MB to `.claude/data/conda-forge-expert/vdb/`.

- **appthreat-vulnerability-db** (>=6.7.0) — (see § 4) here it's the primary engine:
  multi-source CVE DB (OSV + GHSA; NVD/npm via sources) queried by `detail-cf-atlas
  --vdb`, `scan-project`, and cf_atlas Phase G/G'. CISA KEV is fetched out-of-band
  (`fetch-cisa-kev` task) because vdb's aqua source hardcodes KEV exclusion.
- **apsw** (>=3.53.4.0) — SQLite backend for vdb.
- **cyclonedx-bom** (>=7.4.0) — `cyclonedx-py` CLI: generate CycloneDX SBOMs from
  environments/requirements/poetry/pipenv.
- **cyclonedx-python-lib** (>=11.12.0) — programmatic CycloneDX BOM model
  (read/build/serialize 1.x BOMs; used by universe-sbom / inventory-match tooling).
- **conda-forge-metadata** (>=2026.9.10) — query conda-forge artifact metadata (which
  files/libs a package ships) — enables `--deep` package inspection.
- Env vars set on activation: `VDB_HOME`, `VDB_CACHE` (repo-local DB paths),
  `TRUSTSTORE=1` (OS trust store TLS).

Tasks in this env: `vdb-refresh`, `scan-project` (manifests/locks/SBOMs/Dockerfiles →
CVEs), `inventory-channel` (conda/PyPI/npm/crates mirrors), `detail-cf-atlas[-vdb]`,
`build-cf-atlas` / `atlas-phase` (Phase G/G' need vdb importable).

---


## 13a. Platform host / CI extras (`python-agent-platform`, `platform-ci-test`, `dbgpt-sidecar`)

Conda pins added 2026-08-25 when Platform CI left PyPI (`[feature.platform-ci-test.pypi-dependencies]` removed) and OpenFeature/Liquibase landed on the host. **`factory_boy`** and **`django_coverage_plugin`** are the conda names (not `factory-boy` / `django-coverage-plugin`). **`redis-py`** is the Redis client (never the `redis` conda package). OpenFeature quartet is **SelfExplainML**.
- **argon2-cffi** (>=25.1.0) — password hashing (Django/allauth).
- **bmad-module-skill-forge** (>=2.2.0) — BMAD Skill Forge module (conda-forge).
- **cachebox** (>=5.2.3) — fast in-process cache.
- **crispy-bootstrap5** (>=2026.9) — django-crispy-forms Bootstrap 5 template pack.
- **cron-descriptor** (>=2.1.0) — human-readable cron strings (django-celery-beat).
- **cryptography** (>=50.0.1) — crypto primitives (Fernet, TLS helpers).
- **django-allauth** (>=65.19.4) — Django auth (accounts/social/MFA); `platform-ci-test` + host.
- **django-anymail** (>=15.2) — Django transactional email backends.
- **django-appconf** (>=1.2.0) — Django app default-settings helper (compressor).
- **django-celery-beat** (>=2.9.0) — periodic Celery tasks in Django DB.
- **django-compressor** (>=4.6.0) — compress JS/CSS in Django.
- **django-crispy-forms** (>=2.6) — Django form rendering.
- **django-debug-toolbar** (>=8.0.0) — Django debug panel (`platform-dev` / `platform-ci-test` / local). Not on `python-agent-platform` (image).
- **django-environ** (>=0.14.0) — 12-factor env → Django settings.
- **django-extensions** (>=4.1) — Django management extras.
- **django-ipware** (>=7.0.1) — client IP from request (wraps python-ipware).
- **django-model-utils** (>=5.0.0) — Django model mixins/utilities.
- **django-redis** (>=7.0.0) — Django cache backend on Redis.
- **django-structlog** (>=10.1.0) — structlog integration for Django.
- **django-stubs** (>=6.1.1) — mypy/django-stubs types (`platform-ci-test`).
- **django-timezone-field** (>=7.2.2) — timezone model field (celery-beat).
- **django_coverage_plugin** (>=3.2.2) — coverage.py Django template plugin (conda name).
- **djlint** (>=1.46.2) — Django/Jinja HTML linter.
- **factory_boy** (>=3.3.3) — test fixtures (conda name `factory_boy`, not factory-boy).
- **fido2** (>=2.2.1) — WebAuthn/FIDO2 (allauth MFA extra).
- **gunicorn** (>=26.2.0) — WSGI HTTP server.
- **hiredis** (>=3.4.2) — fast Redis protocol parser (optional redis-py accel).
- **httptools** (>=0.8.0) — fast HTTP parser (uvicorn[standard]).
- **ipdb** (>=0.13.13) — IPython debugger.
- **liquibase** (>=5.0.4) — DB changelog runner (`python-agent-platform`).
- **liquibase-postgresql** (>=5.0.4) — Liquibase PostgreSQL extension, from conda-forge (versioned with liquibase).
- **mcp-types** (>=2.2.0) — MCP protocol types (host/CI; no fastmcp).
- **openfeature-flagd-api** (>=1.0.0) — OpenFeature flagd API types (conda-forge).
- **openfeature-flagd-core** (>=1.0.0) — OpenFeature flagd core (**SelfExplainML**).
- **openfeature-provider-flagd** (>=0.5.2) — OpenFeature flagd provider (**SelfExplainML**); 0.5.2 needs protobuf 7.
- **openfeature-sdk** (>=0.10.0) — OpenFeature Python SDK (conda-forge).
- **opentelemetry-exporter-otlp-proto-http** (>=1.44.0) — OTLP HTTP exporter.
- **opentelemetry-instrumentation-asgi** (>=0.65b0) — OTel ASGI instrumentation.
- **opentelemetry-instrumentation-celery** (>=0.65b0) — OTel Celery instrumentation.
- **opentelemetry-instrumentation-django** (>=0.65b0) — OTel Django instrumentation.
- **opentelemetry-instrumentation-psycopg** (>=0.65b0) — OTel psycopg v3 instrumentation.
- **opentelemetry-instrumentation-redis** (>=0.65b0) — OTel Redis instrumentation.
- **opentelemetry-instrumentation-wsgi** (>=0.65b0) — OTel WSGI instrumentation.
- **pre-commit** (>=4.6.2) — git hook runner (`platform-ci-test`).
- **prometheus_client** (>=0.26.0) — Prometheus metrics client; `platform-ci-test`
  + `pyforge-doctor` envs.
- **pyjwt** (>=2.15.0) — JSON Web Tokens.
- **pytest-django** (>=4.13.0) — pytest plugin for Django.
- **pytest-sugar** (>=1.1.1) — prettier pytest progress.
- **python-crontab** (>=3.4.0) — crontab parse/edit (celery-beat).
- **python-ipware** (>=3.0.0) — client IP extraction.
- **python-multipart** (>=0.0.32) — multipart form parser (Starlette/FastAPI).
- **python-slugify** (>=9.0.0) — slugify strings.
- **pytz** (>=2026.4.post1) — IANA tz database for `pytz.timezone(...)`; `dbgpt-sidecar` only — `dbgpt_serve` imports it and pandas 3.x no longer pulls it in.
- **qrcode** (>=8.2) — QR codes (allauth MFA extra).
- **rcssmin** (>=1.2.2) — CSS minifier (django-compressor).
- **rjsmin** (>=1.2.5) — JS minifier (django-compressor).
- **sphinx** (>=9.1.0) — docs generator (`platform-ci-test`).
- **sphinx-autobuild** (>=2025.8.25) — live-reload Sphinx.
- **sse-starlette** (>=3.4.11) — Server-Sent Events for Starlette.
- **text-unidecode** (>=1.3) — ASCII transliteration (python-slugify).
- **uvicorn** (>=0.54.0) — ASGI server.
- **uvicorn-worker** (>=0.4.0) — gunicorn worker class for uvicorn.
- **uvloop** (>=0.22.1) — fast asyncio loop (uvicorn[standard], not Windows).
- **vizro-e2e-flow** (>=0.1.7) — Vizro end-to-end flow helper.
- **watchfiles** (>=1.3.0) — file watcher (uvicorn reload).
- **werkzeug** (>=3.1.8) — WSGI utilities (Flask/Django debug).
- **whitenoise** (>=6.12.0) — Django static-file serving.

---
## 16. Explicitly NOT available (don't assume these)

These are commented out in pixi.toml on purpose — do not import them or write code
depending on them without adding them first:

- **streamlit, chainlit, pygwalker, django-pygwalker, perspective** — dashboard tools
  excluded (jupyter deps, platform gaps, or staleness).
- **dlt** — blocked on dlt-pendulum platform coverage / py3.14. (The dbt trio is
  NO LONGER here — unblocked 2026-08-30, see § 4.)
- **crewai** — agent framework, not resolvable here yet.
- **litellm** — LLM router/proxy; deliberately not added (breaks on the repo's
  Python 3.14 floor).
- **crawl4ai, whisper.cpp, imaginairy** — outdated on conda-forge.
- **cibuildwheel** — bashlex fails on linux-aarch64.
- **cdxgen, oras-py, conda-tree, networkx (as direct dep)** — version conflicts.
- **pixi-devenv, pixi-browse, nebi-desktop** — python>=3.13-only or glibc
  constraints. (`pixitainer` is NOT parked — it is live, linux-64-only, in
  `local-recipes`; see § 3.)
- **bmalph, bmad-autopilot** — BMAD-adjacent
  tools parked (unix-only or superseded by bmad-loop). (`mybmad-dashboard` is NOT
  parked — it is live in the `bmad-ui` env; see § 12.
  <!-- governance-currency:ignore-start (bmad-story-automator is quoted because it was retired) -->
  `bmad-story-automator` is
  gone entirely: retired upstream in favor of bmad-loop, recipe removed
  2026-08-21.)
  <!-- governance-currency:ignore-end -->
- **claude-mem, aichat** — parked agent-tooling candidates. (caveman, headroom-ai,
  codegraph, and ppt-master are NO LONGER parked — all live; caveman/headroom-ai
  unblocked 2026-08-30, see § 10.)
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
| redis-py                     | `import redis` (`python-agent-platform` env) |
| python-graphviz              | `import graphviz`                            |
| factory_boy                  | `import factory` (conda name, not factory-boy) |
| duckdb-server                | `import pkg` / `duckdb-server` (CLI; pyforge-atlas env, linux-64) |

---

## 18. Quick capability index ("I need to X → use Y")

- Parse/edit YAML preserving comments → **ruamel.yaml**; lint it → **yamllint**
- Fast dataframes → **polars**; compat dataframes → **pandas**; SQL on files → **duckdb**
- One dataframe API over many DBs → **ibis-framework** (+ backend pkgs); metrics layer → **boring-semantic-layer**
- Orchestrate pipelines → **dagster** or **kedro** (bridge: **kedro-dagster**)
- Validate data → **pandera** (schemas) or **great-expectations** (contracts)
- Any document → Markdown for an LLM → **markitdown**; docx→md → **mammoth**; universal convert → **pandoc**
- Extract PDF text fast → **pymupdf**; PDF tables → **pdfplumber**; PDF→images → **pdf2image**; OCR → **pytesseract**
- Make slides → **marp-cli** (md→deck) or **pptxgenjs**/**pptxgenjs-plus**/**python-pptx** (programmatic)
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
- Scaffold a project → **copier** (pyforge-marshal/Genesis, update-aware) or
  **cookiecutter** (+ **cruft** to stay synced) for general templates
- Web app/CMS → **django** + **wagtail**/**coderedcms**; realtime → **channels**+**daphne**
- Run the agentic engines (langflow/DB-GPT) alongside Django, `python 3.12` →
  **python-agent-platform** env (**langflow**, **dbgpt**, **dbgpt-serve**, § 11/13)
- Secrets in git → **go-sops** + **age**
- Mock AWS in tests → **moto**; test runner → **pytest** (+ xdist/cov/mock)
- Type-check → **pyright** (default), **mypy**, or **pyrefly**; lint/format Python → **ruff**

*End of library-llms-full.md*