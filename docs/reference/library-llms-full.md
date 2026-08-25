# local-recipes — Library Catalog for LLMs & Agents (library-llms-full.md)

> Purpose: give any LLM or coding agent a complete, self-contained picture of every
> library, CLI, and framework available in this repository's pixi environments —
> what each one is, what it is capable of, how to import/invoke it, and which
> environment provides it.
>
> Source of truth: `pixi.toml` (workspace "staged-recipes" v0.2.0). This file is a
> derived catalog — regenerate it whenever `pixi.toml` changes.
> Generated: 2026-07-12; incrementally updated 2026-07-18 (pyforge-atlas member env + kedro-viz; pyforge-warden + bmad-ui envs; pin corrections), 2026-07-25 (the pyforge-herald / -doctor / -scribe member envs, then pyforge-mason / -steward / -marshal at Story 1.1 — eight `pyforge` packages, 18 envs), 2026-07-30 (24 version floors re-synced to `pixi.toml`; `bmad-manticore`, `ocrmypdf` and `office2pdf` documented — the three deps the agent-CLI recipe wave added without a catalog entry), 2026-08-01 (25 version floors re-synced to `pixi.toml`, incl. `mcp` 1.x->2.0.0 and `fastmcp` pinned back to 2.14.3), 2026-08-09 (`kedro-skills` documented — pyforge-atlas-only, exact-pinned `==0.1.1`, Story 12-1; then a second 2026-08-09 pass re-syncing 12 version floors to `pixi.toml` — incl. `fastmcp` 2.14.3->3.4.5 and `pixi` 0.75.0->0.76.1 — and documenting the two deps the catalog had never carried: `pyyaml` (pyforge-doctor) and `httpx2` (pyforge-herald)) and 2026-08-14 (Story 10.2, CAP-5: the new `python-agent-platform` env — the FIRST env in this catalog pinned off `python 3.14.x` (env-scoped `python = "3.12.*"`) — documented with `langflow`/`dbgpt-serve`/`fastapi`/`django-health-check`/`redis-py`; `pixitainer` uncommented + bumped to `>=0.8.3`, linux-64 only; plus 33 unrelated version floors re-synced to `pixi.toml` and `pyforge-core`'s env row added — the catalog was already drifted on these before this story, `llms-full-check` now exits 0) and 2026-08-20 (Story 11.1: the new `platform-dev` env — composes onto `python-agent-platform` — documented with `postgresql`/`pgvector`/`redis-server`/`kubernetes-helm`/`kubernetes-client`; `python-agent-platform` itself gains `chromadb`/`langchain-chroma`/`elevenlabs`/`psycopg`, four deps `langflow.main.create_app()` hard-imports that the recipe only lists as soft `run_constraints`, discovered live wiring the actual Langflow ASGI mount) and 2026-08-23 (Story 19.2: `pyforge-testing-kit` lean env row added — own-leaf shared test mocks / FR-130) and 2026-08-23 (Story 12.1: **copier** documented as the pyforge-marshal/Genesis template engine; pyforge-marshal env row updated; quick-index scaffolding line reconciled with Copier adoption) and 2026-08-25 (Story 26.3 / FR-33: `python-agent-platform` gains `openfeature-sdk`, `openfeature-flagd-api`, `openfeature-flagd-core`, `openfeature-provider-flagd`, and `cachebox` `>=5.1,<6` so CAP-13 can evaluate offline; FILE provider is 26.4). Channels: conda-forge + SelfExplainML.
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
- **Python is 3.14.x in every environment except one.** If a library you want to
  add doesn't support 3.14, it won't resolve here. The sole exception is
  `python-agent-platform` (CAP-5, Story 10.2), env-scoped to `python = "3.12.*"`
  only — no other feature/env in `pixi.toml` changes its python floor off 3.14.
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
| `pyforge-core` | pyforge-core (no-default-feature)                     | Lean env for the built `pyforge-core` package (`src/shared/packages/pyforge-core` path dep -> conda pkg + pytest/hatchling/python-build). Pure-stdlib shared leaf (Story 14.1, `pyforge-scribe` mirror); a real run-dependency of six sibling stations' own envs (atlas, herald, marshal, scribe, steward, warden — see each `[feature.pyforge-<station>.dependencies]`). Spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/` |
| `pyforge-testing-kit` | pyforge-testing-kit (no-default-feature)         | Lean env for the built `pyforge-testing-kit` package (`src/shared/packages/pyforge-testing-kit` path dep -> conda pkg + pytest/hatchling/python-build). Own-leaf shared test mocks (Story 19.2 / FR-130 / Q-26); stdlib-only; test-time path dep of pyforge-marshal + pyforge-doctor feature envs (not a station runtime run-dep). Spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-19-2-the-shared-test-support-kit.md` |
|