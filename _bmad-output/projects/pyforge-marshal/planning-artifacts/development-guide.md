---
doc_type: development-guide
project_name: local-recipes
date: 2026-07-25
source_pin: 'conda-forge-expert v8.81.0'
---

# Development Guide

> **Re-grounded 2026-07-25** (source_pin → v8.79.1). **Headline correction: the repo has 18 pixi environments and 17 features, not 9** — a factory family of 9 (`linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`, `gcloud`) plus 6 `no-default-feature` **product** envs (`pyforge-warden`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-scribe`, `pyforge-herald`, `bmad-ui`). Everything downstream of that changed: the **Pixi Tasks Cheatsheet was rebuilt from the live 111-task `local-recipes` surface** (106 own + 5 inherited from `grayskull`/`conda-smithy`), § *Project layout* now carries `src/shared/packages/` and the five PyForge workspace packages, § *Testing* now covers **all three** suites (top-level `tests/`, the skill suite, the five product suites) plus the mandatory `--frozen` rule inside loop worktrees, § *BMAD Workflows* was rewritten against the live skill set and the Dream → Spec flow, and a new § *PR CI gates* documents the two always-on staged-recipes-linter gates. Re-verified **unchanged**: cf_atlas schema **v29**, **46 MCP tools**, **23 cataloged atlas phases** (22 executable), gotchas through **G106**, the three-place rule for new scripts, and the no-mock-the-network test convention. Live detector output: `pixi run --frozen -e local-recipes bmad-groundtruth`.


How to set up, build, test, debug, and contribute to `local-recipes` locally. This guide is for **humans** operating the system — agents read `project-context.md` and `SKILL.md` instead. Air-gapped / enterprise setup lives in `deployment-guide.md`.

---

## Prerequisites

| Tool | Minimum version | Why |
|---|---|---|
| Pixi | `>=0.73.0` everywhere — `requires-pixi` (workspace gate), the `python` + `local-recipes` features, `environment.yaml`, the linter workflow's env, and the `pixi-version` pin in `.github/workflows/dashboard.yml`. Keep all in step. | Sole environment manager. No conda, no venv. |
| Python | `>=3.14.6,3.14.*` (pixi-managed, `feature.python`) | `_bmad/scripts/*.py` need 3.11+ for stdlib `tomllib`; the repo env pins 3.14. |
| Git | any modern | Repo operations. |
| Docker | any modern | Linux builds run inside Docker via `build-locally.py`. Not required for osx/win native. |
| GitHub CLI (`gh`) | `>=2.96.0` | PR submission (`submit_pr`, `prepare_pr`). Pixi-managed. |
| Node.js | `>=24.16.0,24.*,<25.0` (LTS pin) | npm-source recipe generation + the deck/dashboard toolchain. Pixi-managed. |
| Claude Code (CLI) | latest | Driving the system interactively. Optional for cron / scripted use. |

Don't install pixi globally with a manager that conflicts with the repo's pin. Use the official installer or your distro's pixi package.

**Workspace shape** (`[workspace]` in `pixi.toml`): name `staged-recipes`, version 0.2.0, `preview = ["pixi-build"]`, channels `["conda-forge", "SelfExplainML"]`, platforms `["linux-64", "win-64", { name = "osx-arm64-min", platform = "osx-arm64", macos = "14.5" }]`. That last named entry is a virtual-package **floor**, not a pin — the oldest macOS the lock must support, set to 14.5 because `mlx 0.31.2+` requires `__osx >=14.5`; feature `platforms` lists must reference it by the name `osx-arm64-min`, a plain `"osx-arm64"` entry errors. A `TODO` in the manifest tracks adding `osx-64` / `linux-aarch64` / `win-arm64`. There is deliberately **no `[workspace] members` key** — pixi through 0.72.2 has none; workspace members are declared via path dependencies in the product features.

---

## Environments (15) and features (17)

Two families. Task counts are live (`pixi task list --environment <e> --machine-readable`).

**Factory envs (9)** — composed from shared features:

| Env | Features | Tasks | Role |
|---|---|---|---|
| `local-recipes` | python, build, grayskull, conda-smithy, local-recipes | **111** | **The default env.** Everything below plus 106 of its own tasks. |
| `vuln-db` | python, vuln-db | 7 | AppThreat vdb + `scan-project` + `inventory-channel` + `detail-cf-atlas-vdb`. |
| `grayskull` | python, grayskull | 4 | `cran`, `cran-v0`, `pypi`, `pypi-v0` (inherited by `local-recipes`). |
| `conda-smithy` | python, conda-smithy, shellcheck | 1 | `lint` (inherited by `local-recipes`). |
| `linux` / `osx` / `win` | + python (+ build for osx/win) | 1 each | `build-linux` / `build-osx` / `build-win` via `build-locally.py`. |
| `build` | python, build | 0 | Dependency-only env; it is what the CI linter exports `environment.yaml` from. |
| `gcloud` | python, gcloud-sdk | 0 | Dependency-only env. |

**Product envs (6)** — all `no-default-feature = true`:

| Env | Tasks | Notes |
|---|---|---|
| `pyforge-warden` | 7 | `pyforge-warden-{test,build,build-dist,build-conda}`, `warden-scan`, `pyforge-warden-dogfood`, `pyforge-warden-test-corpus-oracle` |
| `pyforge-atlas` | 10 | the 4 `pyforge-atlas-*` + `kedro-test`, `kedro-catalog-check`, `dagster-dryrun`, `parity-diff`, `bsl-metric-check`, `duckdb-singularity`, `viz` |
| `pyforge-doctor` / `pyforge-scribe` / `pyforge-herald` | 4 each | `{test,build,build-dist,build-conda}` |
| `bmad-ui` | 2 | `bmad-dashboard-install`, `mybmad`. linux-64 only; declares its own channels **including `./build_artifacts/linux64`** — it consumes the locally-built `bmad-dashboard` / `mybmad-dashboard` packages. |

`no-default-feature` costs **no tasks** — the default `[dependencies]` table has no `[tasks]` at all. What it excludes is the fat default dep set (`python 3.14.*`, `pixi`, `conda`, `pip`, `uv`), which is why a product env is cheap enough to materialize inside a per-story loop worktree.

The 17 features: `python`, `build`, `linux`, `osx`, `win`, `grayskull`, `conda-smithy`, `shellcheck`, `gcloud-sdk`, `local-recipes`, `vuln-db`, `bmad-ui`, `pyforge-warden`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-scribe`, `pyforge-herald`.

`[feature.local-recipes.activation]` runs `scripts/load-env.sh` and sets `PYTHONWARNINGS="ignore:Kedro is not yet fully compatible"`. A `# default-env: local-recipes` comment sits directly above `[environments]` and **is parsed** by `scripts/load-env.sh` (awk, not TOML) — it is load-bearing, not decoration. If it is absent, `load-env.sh` falls back to the first environment key, which is `linux`.

---

## First-time setup

```bash
git clone <fork-or-upstream> local-recipes
cd local-recipes

# Pixi resolves the default env (local-recipes) on first command:
pixi run health-check                  # validates pixi envs, MCP server, atlas freshness
```

If `health-check` complains about missing data, run a one-time atlas bootstrap:

```bash
pixi run bootstrap-data                # full atlas refresh; 30-45 min cold, 5-10 min warm
pixi run -e vuln-db update-cve-db       # CVE database refresh (separate env)
```

For air-gapped / JFrog setups, see `deployment-guide.md` § Configure `.pixi/config.toml` **before** running these.

### Verify env wiring

```bash
pixi run verify-env                          # confirms default-env directive + pixi.toml integrity
pixi run --frozen -e local-recipes bmad-groundtruth   # live factory facts as JSON
pixi run --frozen -e local-recipes bmad-drift-check   # artifact-vs-live drift report
```

> **`pixi run bmad-preflight` is BROKEN — do not use it.** The task shells out to
> `bash scripts/ensure-bmad-preflight.sh`, and that script **does not exist anywhere in the
> repo** (verified 2026-07-25). The task will fail with `No such file or directory`. Use
> `verify-env` + `bmad-groundtruth` instead. Fixing or removing the task is open work.

> **Do NOT run `scripts/bmad-switch` from a parallel agent (HARD rule, 2026-07-25).** The active-project
> marker and the two gitignored symlinks (`_bmad-output/planning-artifacts` and
> `_bmad-output/implementation-artifacts`) are **per-working-tree global state**. A second agent
> switching them retargets every BMAD write-skill in the tree, including the one already running.
> Address a project by its physical path (`_bmad-output/projects/<slug>/…`) and pass
> `BMAD_ACTIVE_PROJECT=<slug>` per invocation instead. Interactive, single-agent sessions may still
> use `scripts/bmad-switch <slug>` — it re-points both symlinks atomically and writes the marker
> last, and `--current` / `--list` warn on desync.

---

## Project layout (orientation)

See `source-tree-analysis.md` for the full tree. Quick map:

- **`recipes/`** — ~1,667 recipe dirs: 933 with a v1 `recipe.yaml`, 1,024 with a v0 `meta.yaml` (many dirs carry both during a feedstock's v0→v1 transition; counts from `bmad-groundtruth`, and they churn daily)
- **`.claude/skills/conda-forge-expert/`** — Part 1: 66 canonical scripts (~41k LOC), references, guides, quickref, templates, tests
- **`.claude/scripts/conda-forge-expert/`** — Part 1 Tier 2: the public CLI entrypoint layer, 60 entries (57 thin `.py` wrappers + `cross-build.sh` + `native-build.sh` + `README.md`)
- **`.claude/tools/`** — Part 3: `conda_forge_server.py` (46 MCP tools), `gemini_server.py`, `mcp_call.py`
- **`.claude/data/conda-forge-expert/`** — runtime state (gitignored): `cf_atlas.db`, `vdb/`, `cve/`, mappings, caches
- **`.claude/skills/`** — 93 dirs, **89 real skills** (each with a `SKILL.md`): 51 `bmad-*`, 16 `skf-*`, 21 engineering-practice, 1 repo-specific (`conda-forge-expert`). The 4 non-skill dirs are shared payload: `cf-atlas-legacy/`, `data/`, `knowledge/`, `shared/`
- **`src/`** — the PyForge product source tree, **new since this guide was last grounded**:
  - `src/shared/packages/` — five pixi workspace packages, one per Smith, each with its own `pyproject.toml`, `tests/`, and a matching `no-default-feature` pixi env: `pyforge-warden`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-scribe`, `pyforge-herald`. They are wired in as **path dependencies** from `[feature.<name>.dependencies]` (there is no `[workspace] members` key)
  - `src/sentinel/` — the wiki/knowledge agent behind the 14 `wiki-*` tasks
  - `src/prototype/` — prototype/spike code
- **`tests/`** — top-level; contains exactly **one** file, `test_load_env.sh` (see § Testing)
- **`_bmad/`** — Part 4: BMAD installer (6.10.0) + `_bmad/custom/` overrides
- **`_bmad-output/projects/<slug>/`** — 14 BMAD projects; `local-recipes/` holds this doc set
- **`.bmad-loop/`** — external loop harness state: `policy.toml`, `bmad_loop_hook.py` (wired into `.claude/settings.json` on SessionStart / Stop / SessionEnd / PreCompact), and `runs/` (gitignored run scratch, incl. per-story worktrees)
- **`docs/`** — `dreams/` (Tier 0, 26 Dreams), `specs/` (**legacy** Tier 1, 19 intake specs), `reference/` (mcp-server-architecture, enterprise-deployment, developer-guide, library-llms-full, pixi-config-jfrog.example.toml), `dashboard/` (the Guildhall console), `intake/`
- **`scripts/`** — repo-level helpers: `bmad-switch`, `bmad-loop-worktree`, `load-env.sh`, `bmad_drift_check.py`, `spec_surface_check.py`, `llms_full_check.py`, `deck_export.py`, `mirror-channels.py`, `offline-build.sh`, `submit_pr.sh`, `sync-upstream-conda-forge.sh`, `sync_pypi_mappings.py`
- **Ancillary**: `SDKs/` (gitignored macOS SDK), `build_artifacts/` (gitignored, but a **real referenced conda channel** — see `deployment-guide.md`), `archive/`, `_skf-learn/`, `conf/`, `helm/`

---

## Pixi Tasks Cheatsheet

`local-recipes` is the default env and exposes **111** tasks: its own **106** under
`[feature.local-recipes.tasks.*]`, plus 4 inherited from `grayskull` (`pypi`, `pypi-v0`, `cran`,
`cran-v0`) and 1 from `conda-smithy` (`lint`). To run in another env: `pixi run -e <env> <task>`.
To pass args: `pixi run <task> -- <args>`.

> **Not every task you'll want is in `local-recipes`.** `scan-project`, `inventory-channel`,
> `detail-cf-atlas-vdb`, and `vdb-refresh` live **only** in `vuln-db` and need `-e vuln-db`.
> Per-product test/build tasks live only in their product env. Regenerate this list any time with
> `pixi task list --environment <e> --machine-readable`.

> **Inside a bmad-loop worktree, always pass `--frozen`** — `pixi run --frozen -e <env> <task>`.
> See § Testing for why (it is a correctness rule, not a speed tip).

The 106 own tasks group as follows.

### Recipe lifecycle (the 10-step loop, manually invocable)

| Task | What it runs |
|---|---|
| `pixi run generate-recipe -- <pkg>` | Generate v1 recipe.yaml from PyPI |
| `pixi run generate-cran -- <pkg>` | CRAN-source recipe |
| `pixi run generate-cpan -- <pkg>` | CPAN-source recipe |
| `pixi run generate-luarocks -- <pkg>` | LuaRocks-source recipe |
| `pixi run generate-npm -- <pkg>` | npm-source recipe |
| `pixi run validate -- recipes/<pkg>` | rattler-build --render + schema validation |
| `pixi run check-deps -- recipes/<pkg>` | PyPI→conda dep resolution |
| `pixi run resolve-name -- <pypi-name>` | PyPI→conda name lookup |
| `pixi run scan-vulnerabilities -- recipes/<pkg>` | OSV-based vulnerability scan (use `-e vuln-db` for full AppThreat) |
| `pixi run lint-optimize -- recipes/<pkg>` | Run the optimizer lint codes (DEP/PIN/ABT/SCRIPT/SEL/STD/TEST/MAINT/SEC/OPT/SCHEMA/LIC/FMT) |
| `pixi run lint -- recipes/<pkg>` | conda-smithy recipe-lint (CI fidelity) |
| `pixi run license-check -- recipes/<pkg>` | Validate `license_file` + SPDX identifier |
| `pixi run version-check -- recipes/<pkg>` | Check upstream GitHub for newer tag |
| `pixi run migrate -- recipes/<pkg>` | v0 meta.yaml → v1 recipe.yaml migration |
| `pixi run pypi -- <pkg>` | (grayskull, inherited) v1 recipe from a PyPI name |
| `pixi run pypi-v0 -- <pkg>` | (grayskull, inherited) v0 `meta.yaml` from a PyPI name |
| `pixi run cran -- <pkg>` / `cran-v0 -- <pkg>` | (grayskull, inherited) v1 / v0 recipe from a CRAN name |

### Build

| Task | Platforms | Note |
|---|---|---|
| `pixi run recipe-build -- recipes/<pkg>` | host platform | **Recommended default.** Native rattler-build, no Docker; auto-detects platform via `uname`, layers `conda-forge-pinning` over `.ci_support/<platform>.yaml` |
| `pixi run recipe-build-docker -- recipes/<pkg>` | linux-64 in Docker | Opt-in CI-parity check (alma9 sysroot, isolated env). Use when the native build passes and you want CI fidelity before submitting |
| `pixi run recipe-build-cross -- recipes/<pkg>` | cross-target | Produces a downloadable `.conda` for a target the host can't reach natively (e.g. osx-arm64 from linux-64). Mutates a temp recipe copy |
| `pixi run build-local -- recipes/<pkg>` | linux-64 | Full native build **+ test** |
| `pixi run build-local-all -- recipes/<pkg>` | every supported target | Cross-builds skip tests |
| `pixi run build-local-check -- recipes/<pkg>` | — | Diagnose what's available for local cross-platform builds |
| `pixi run build-local-setup-sdk` | (one-time) | **Downloads** the macOS SDK into `./SDKs/` for `osx-*` cross-builds (Apple licence applies). `SDKs/` is gitignored |
| `pixi run -e linux build-linux` / `-e osx build-osx` / `-e win build-win` | per-platform | `build-locally.py --filter '<platform>*'`. `build-locally.py` **refuses to run on `main`** — branch first |
| `pixi run test-recipes` | — | `test-recipes.py` random / targeted recipe smoke validation |
| `pixi run pr-artifacts -- <pr>` | — | Download CI-published `.conda` artifacts from a staged-recipes / feedstock PR via the Azure DevOps Build Artifacts REST API |

### Atlas

| Task | What it runs |
|---|---|
| `pixi run bootstrap-data` | Full atlas refresh + mapping + CVE + vdb |
| `pixi run bootstrap-data -- --fresh` | Hard reset (preserves `cache/parquet/` by default) |
| `pixi run bootstrap-data -- --status` | Print phase_state + TTL eligibility |
| `pixi run atlas-phase -- <ID>` | Run a single phase. **22 executable phases** — B / B.5 / B.6 / C / C.5 / D / O / P / Q / R / S / E / E.5 / F / G / G' / H / J / K / L / M / N (23 cataloged) |
| `pixi run atlas-phase -- --list` | Enumerate known phases |
| `pixi run atlas-phase -- F --reset-ttl` | NULL TTL column, then run Phase F |
| `pixi run build-cf-atlas` | Pipeline phases only (skips mapping + CVE + vdb) |
| `pixi run query-cf-atlas -- <sql>` | Direct SQL query against cf_atlas.db (schema **v29**) |
| `pixi run stats-cf-atlas` | High-level atlas statistics summary |
| `pixi run detail-cf-atlas -- <conda-name>` | All atlas data for one package |
| `pixi run -e vuln-db detail-cf-atlas-vdb -- <conda-name>` | Same, plus vdb data. **`vuln-db` env only** |
| `pixi run -e vuln-db inventory-channel` | Refresh channel inventory cache. **`vuln-db` env only** — `pixi run inventory-channel` fails |

### Atlas-intelligence queries

| Task | What it runs |
|---|---|
| `pixi run staleness-report -- [filters]` | Behind-upstream + unmaintained feedstocks |
| `pixi run feedstock-health -- <name>` | Health summary for one feedstock |
| `pixi run behind-upstream -- [filters]` | Packages with newer upstream versions |
| `pixi run whodepends -- <name>` | Reverse-dependency lookup |
| `pixi run cve-watcher -- [filters]` | New CVEs in your packages |
| `pixi run release-cadence -- <name>` | Release cadence for one package |
| `pixi run version-downloads -- <name>` | Download trend by version |
| `pixi run find-alternative -- <name>` | Similar packages |
| `pixi run adoption-stage -- <name>` | Maturity / popularity tier |
| `pixi run my-feedstocks -- [--triage]` | Per-maintainer feedstock portfolio + triage punch list |
| `pixi run -e vuln-db scan-project -- <path>` | Scan manifest / lock file / SBOM / container. **`vuln-db` env only** — `pixi run scan-project` fails. Accepted input formats: `reference/dependency-input-formats.md` |
| `pixi run platform-breakdown` | ARM / win / EOL download-share breakdown (Phase F+ data) |
| `pixi run pyver-breakdown -- [--policy-check]` | Per-Python download breakdown; flags python_min bump-safe candidates |
| `pixi run channel-split` | Defaults-channel migration opportunities |
| `pixi run pypi-intelligence -- [filters]` | PyPI-intelligence layer (Phase O–S scores) |
| `pixi run pypi-only-candidates -- [filters]` | PyPI packages with no conda-forge feedstock |
| `pixi run lts-registry-gap` | Suggest `lts-registry.yaml` entries by diffing endoflife.date against `v_actionable_packages` (read-only suggester) |

### SBOM / purl / inventory

| Task | What it runs |
|---|---|
| `pixi run export-purls -- [filters]` | Emit package URLs (conda + upstream) for the atlas universe |
| `pixi run mapping-gap` | Rank unmapped PyPI↔conda names |
| `pixi run universe-sbom` | Build the full PyPI + conda-forge CycloneDX inventory |
| `pixi run inventory-match -- <path>` | Match a project's dependency set against the universe inventory |
| `pixi run add-handoff` | Emit the ADD-bucket packaging worklist from `inventory-match` results (name, readiness, template, blockers) |
| `pixi run library-futures` / `recommend-2027` | 2027–2030 library-tier scoring (py314 + LTS / endoflife signals) |

### Security / vulnerability feeds

| Task | What it runs |
|---|---|
| `pixi run scan-vulnerabilities -- recipes/<pkg>` | OSV-based scan (use `-e vuln-db` for full AppThreat) |
| `pixi run update-cve-db` | Refresh the CVE database |
| `pixi run fetch-cisa-kev` | Refresh the CISA Known Exploited Vulnerabilities table in cf_atlas.db (~2 MB JSON from cisa.gov) |
| `pixi run fetch-epss` | Refresh FIRST.org EPSS scores (~3 MB gzipped CSV) |
| `pixi run fetch-cwe-catalog` | Refresh the MITRE CWE Research Concepts table (~640 KB zip) |
| `pixi run cwe-seed-gap` / `spdx-schema-gap` / `license-map-gap` | Read-only suggesters over the hand-curated seed maps — they propose, git review decides |
| `pixi run -e vuln-db vdb-refresh` | Build/refresh the AppThreat vdb (~600 MB, OSV + GHSA) |

### Wiki / knowledge (the `sentinel` agent, `src/sentinel/`)

14 tasks: `wiki-compile`, `wiki-lint`, `wiki-ask`, `wiki-sync`, plus the `-all` fan-out variants
(`wiki-compile-all`, `wiki-lint-all`, `wiki-ask-all`, `wiki-ingest-all`), and `wiki-ingest`,
`wiki-clean`, `wiki-search`, `wiki-chat`, `wiki-summarize`, `wiki-review`. Config for the agent
lives at `conf/base/knowledge.yml`.

### Dashboard / decks / visualization

| Task | What it runs |
|---|---|
| `pixi run dashboard-gen` | Refresh `docs/dashboard/data.js` (the committed Guildhall console seed) from the live per-project `sprint-status.yaml` files |
| `pixi run dashboard-dryrun` | Build the BSL-driven Vizro dashboard **object** offline (no server, no `.run()`) and assert each expected component |
| `pixi run vizro-ai-dryrun` | Offline, no-network, no-live-LLM assertion that the `query_vizro_ai` MCP tool is registered |
| `pixi run deck-export` | Regenerate a deck's derived export artifacts (standalone infographic HTML + PPTX) from its Marp `.md` sources |
| `pixi run kedro-viz-proto` / `capture-kedro-viz-proto` / `kedro-run-proto` / `regenerate-kedro-viz-proto` | Serve, screenshot, smoke-run, and regenerate the dependency-free stub mirror of the pyforge-atlas Kedro DAG (`src/prototype/`) |

### WASM read-surface (pyforge-atlas Wave G)

| Task | What it runs |
|---|---|
| `pixi run wasm-build` | Build the self-contained, backend-free DuckDB-WASM read-surface artifact into `src/shared/packages/pyforge-atlas/wasm/build/` (gitignored) |
| `pixi run wasm-smoke` | Playwright headless-Chromium load-and-query against the built artifact (run `wasm-build` first) |
| `pixi run publish` / `publish-range` | Emit the host-agnostic static-host layout (chunked Parquet + `manifest.json`), then prove it is consumable over HTTP RANGE |

### BMAD / spec governance (detectors — all read-only, all exit non-zero on drift)

| Task | What it runs |
|---|---|
| `pixi run bmad-drift-check` | Artifact-vs-live drift: pins, counts, stale rules, archive hygiene, coverage completeness, baseline. `-- --fix`, `-- --specs`, `-- --integrity-only`, `-- --write-baseline` |
| `pixi run bmad-groundtruth` | The same live facts as JSON — skill version, schema, MCP tools, atlas phases, pixi envs, gotchas |
| `pixi run llms-full-check` | Drift between `docs/reference/library-llms-full.md` and `pixi.toml` — undocumented deps, ghost entries, version-floor drift |
| `pixi run spec-surface-check` | Every tracked file is governed by a spec surface or explicitly allowlisted (`scripts/spec_surface_allowlist.txt`) |
| ~~`pixi run bmad-preflight`~~ | **BROKEN** — invokes `bash scripts/ensure-bmad-preflight.sh`, which does not exist in the repo |

### Submission

| Task | What it runs |
|---|---|
| `pixi run prepare-pr -- <recipe>` | Step 8b: push to fork, NO PR open |
| `pixi run submit-pr -- <recipe>` | Step 9-10: dry-run, then open PR |
| `pixi run submit-pr -- --dry-run <recipe>` | Just dry-run |
| `pixi run autotick -- <recipe>` | Auto-bump version + SHA |
| `pixi run autotick-github -- <recipe>` | GitHub-only autotick |
| `pixi run autotick-npm -- <recipe>` | npm-only autotick |

### Test runners (full detail in § Testing below)

| Task | Scope |
|---|---|
| `pixi run test` | conda-forge-expert suite, offline fast subset (no `network` / `slow` markers) |
| `pixi run test-all` | conda-forge-expert suite in full (includes network + slow) |
| `pixi run test-coverage` | Coverage report over the same suite |
| `pixi run test-skill -- [--unit/--integration/--meta] [--keyword X] [--coverage]` | Scoped skill-suite runner |
| `pixi run -e pyforge-<name> pyforge-<name>-test` | One of the five product suites (`warden`, `atlas`, `doctor`, `scribe`, `herald`) |
| `bash tests/test_load_env.sh` | The top-level suite — 6 bash tests for `scripts/load-env.sh`. **Not pytest, not a pixi task.** See the caveat in § Testing |

### Repo / env hygiene

| Task | What it runs |
|---|---|
| `pixi run sync-upstream-conda-forge` | Pull from conda-forge/staged-recipes upstream |
| `pixi run sync-upstream-public-fork` | Pull from user fork |
| `pixi run update-mapping-cache` | Refresh PyPI→conda mapping |
| `pixi run verify-env` | Confirm the shell is inside the `local-recipes` pixi env |
| `pixi run env-inspect -- [--audit/--freshness/--security/--bus-factor/--licenses/--sbom]` | Inspect a pixi/conda env from multiple angles |
| `pixi run gen-yml-reference` | Regenerate the exhaustive `*-reference-full.md` docs from upstream conda-smithy + rattler-build JSON schemas |
| `pixi run health-check` | System-level health |
| `pixi run analyze-failure -- <log-file>` | Pattern-match a build failure |

---

## Authoring a New Recipe (Manual Workflow)

This mirrors Part 1's 10-step loop, runnable from the shell:

```bash
# 1. Generate
pixi run generate-recipe -- numpy
# (writes recipes/numpy/recipe.yaml)

# 2. Validate
pixi run validate -- recipes/numpy

# 3. (edit_recipe is via Claude Code / MCP; manually: edit recipes/numpy/recipe.yaml)

# 4. Scan (scan-vulnerabilities is in local-recipes; scan-project is vuln-db-only)
pixi run scan-vulnerabilities -- recipes/numpy

# 5. Optimize
pixi run lint-optimize -- recipes/numpy
pixi run lint -- recipes/numpy           # conda-smithy lint, inherited from the conda-smithy feature

# 6. Build — native first, Docker only for CI-parity confirmation
pixi run recipe-build -- recipes/numpy
pixi run recipe-build-docker -- recipes/numpy    # opt-in; alma9 sysroot, full CI fidelity
# Watch logs; on failure, see build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log

# 7-8. Inspect outcome
ls build_artifacts/*/*/numpy-*.conda     # success indicator

# (If failed):
pixi run analyze-failure -- build_artifacts/<config>/bld/rattler-build_numpy_<id>/work/conda_build.log

# 8b. Prepare submission branch (no PR) — CFE branch convention is add-recipe-<name>
pixi run prepare-pr -- numpy
# (returns fork_branch_url; inspect in browser)

# 9-10. Submit
pixi run submit-pr -- --dry-run numpy    # verify gh auth, fork, branch state
pixi run submit-pr -- numpy              # open the PR
```

Before pushing, **strip every `extra.cfe-*` key** — those are local-recipes-internal metadata and
never ship to staged-recipes or a feedstock. Same for the bottom `# CFE comments` block.

If you open the PR by hand rather than via `submit-pr`, `gh pr create` **must** carry
`--repo rxm7706/local-recipes`. This repo is a fork of `conda-forge/staged-recipes`, so `gh`
otherwise defaults the base to `conda-forge:main` and you will open a PR against upstream.

For an interactive AI-driven workflow, use Claude Code with the `conda-forge-expert` skill — it drives the loop with full context and structured actions.

---

## PR CI gates (always-on, every PR to `rxm7706/local-recipes`)

The inherited staged-recipes linter (`.github/workflows/staged-recipes-linter.yml` →
`.github/workflows/scripts/linter.py`) reds two ways that are easy to trip and cheap to pre-empt.
Handle them at PR-open time; don't wait for red CI.

**Gate 1 — anything outside `recipes/` needs the `maintenance` label.** The linter fails on any
changed file that doesn't start with `recipes/` (and on any edit to the example recipes) **unless**
the PR carries the `maintenance` label. Docs, `.github/`, `_bmad-output/`, `src/`, `scripts/`,
`pixi.toml`, dashboards — all of it counts.

```bash
gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance
```

The workflow is triggered on `labeled` and `unlabeled` (as well as `opened` / `synchronize` /
`reopened`) precisely so adding the label re-runs the check.

**Gate 2 — `environment.yaml` must match `pixi.toml`, and the label does NOT suppress it.** The
linter runs `pixi project export conda-environment -e build` and compares it to `environment.yaml`
with an exact `.rstrip()` string comparison, printing a unified diff on mismatch. This check sits
outside the `maintenance` branch, so it fires on **every** PR that changes `pixi.toml`.

```bash
pixi project export conda-environment -e build > environment.yaml
```

Fix `main` directly too whenever a `pixi.toml` dep change lands there. (Verified in sync
2026-07-25. Harmless cosmetic artifact: `python` appears twice in the export — `>=3.14.6,3.14.*`
from `feature.python` and `3.14.*` from the default `[dependencies]`. Both sides agree, so the
comparison passes; don't "fix" it by hand or you'll break the check.)

Recipe-only PRs (touching only `recipes/**`) need neither.

The linter's other checks, for orientation: a recipe must live in its own subdirectory under
`recipes/`; the feedstock must not already exist (it tries `name`, `name.replace('-','_')`,
`name.replace('_','-')`, bioconda, and a PyPI-name collision lookup against
`regro/cf-graph-countyfair`'s `name_mapping.yaml`); every listed maintainer must have commented or
be the PR author (exempt: `conda-forge/r`, `conda-forge/cuda`, and any `org/team` entry); only
`conda-forge/*` teams may be maintainers; and a hint fires if a multi-output recipe omits
`extra.feedstock-name`.

---

## Inspecting a Build Failure

```bash
# Find the most recent build log for a recipe:
ls -t build_artifacts/*/bld/rattler-build_<name>_*/work/conda_build.log | head -1

# Read the tail (most failures show their cause in the last 200 lines):
tail -200 "$(ls -t build_artifacts/*/bld/rattler-build_<name>_*/work/conda_build.log | head -1)"

# Get pattern-matched diagnosis:
pixi run analyze-failure -- "$(ls -t build_artifacts/*/bld/rattler-build_<name>_*/work/conda_build.log | head -1)"
```

If `get_build_summary` reports "build may have crashed" but a fresh `.conda` exists in `build_artifacts/<config>/<subdir>/`, it's a known false-negative (Gotcha G6). Trust the artifact + log, not the summary.

---

## Working with the MCP Server

The MCP server (Part 3) is auto-started by Claude Code at session boot. To invoke a tool from the shell without Claude Code:

```bash
# Via the JSON-RPC client:
python .claude/tools/mcp_call.py validate_recipe '{"recipe_path": "recipes/numpy/recipe.yaml"}'
python .claude/tools/mcp_call.py query_atlas '{"conda_name": "numpy"}'

# Or via a pixi task wrapper if one exists:
pixi run validate -- recipes/numpy
```

The MCP server runs in the pixi env that launched Claude Code (or `mcp_call.py`). For atlas-intelligence tools that need cf_atlas.db, that's `local-recipes`. For Phase G / Phase G' / `scan_for_vulnerabilities` against AppThreat vdb, that's `vuln-db`.

---

## BMAD Workflows

BMAD-METHOD is at **6.10.0**. `.claude/skills/` holds **89 skills** (51 `bmad-*`, 16 `skf-*`, 21
engineering-practice, `conda-forge-expert`), and `_bmad-output/projects/` holds **14 projects**.

### The Dream-first flow (mandatory for any non-trivial effort)

Everything starts from a **Dream** — a raw human aspiration in `docs/dreams/<slug>.md`
(26 of them today). BMAD then turns the Dream into **the Spec**, and the Spec drives the build.

```
docs/dreams/<slug>.md          Tier 0 — the Dream (tracked, permanent)
        ↓  bmad-spec
_bmad-output/projects/<slug>/planning-artifacts/SPEC.md
                               Tier 2 — the Spec: five fields — ## Why, ## Capabilities,
                               ## Constraints, ## Non-goals, ## Success signal — rendered on
                               each run from an append-only .memlog.md, never hand-patched
        ↓  bmad-prd / bmad-architecture / bmad-create-epics-and-stories
        ↓  decompose into epics + stories
_bmad-output/projects/<slug>/implementation-artifacts/
                               Tier 3 — gitignored runtime scratch
```

`docs/specs/` is the **legacy** Tier-1 intake tier (19 files, verified 2026-07-25 —
6 in-progress, 6 shipped, 4 superseded, 3 timeless workflows). It is kept for in-flight
efforts; author no new specs there. List live statuses with
`pixi run --frozen -e local-recipes bmad-drift-check -- --specs`.

**Story specs are durable, not Tier-3.** `bmad-loop` drafts a per-story spec into the run's
gitignored `implementation-artifacts/`; after the story merges, promote it into the tracked
`planning-artifacts/specs/` subdir and commit it. Skipping this loses the spec to worktree
teardown — pyforge-warden lost 13 of 31 that way before the convention existed.

### Entry points

| Skill | Use |
|---|---|
| `bmad-spec` | Distil a Dream (or any intent input) into the Spec — the small-scope entry point |
| `bmad-prd` | Create / update / **validate** a PRD (one skill, three intents) |
| `bmad-architecture` | Create / update the architecture |
| `bmad-create-epics-and-stories` | Break the PRD into epics + stories |
| `bmad-create-story` | Produce one context-filled story file |
| `bmad-quick-dev` | Implement a story / feature / fix from a spec |
| `bmad-dev-auto` | One iteration of an unattended dev loop (gained in 6.10) |
| `bmad-document-project` | Regenerate this doc set from the live repo |
| `bmad-check-implementation-readiness` | Gate report over PRD + UX + architecture + epics |
| `bmad-retrospective` | Closeout retro — **mandatory** for any effort that touched conda-forge work |

> **Deprecated, do not invoke:** `bmad-create-prd` and `bmad-create-architecture` are thin
> deprecated wrappers consolidated into `bmad-prd` and `bmad-architecture`, and are slated for
> removal in v7. (`bmad-edit-prd` and `bmad-validate-prd` are likewise folded into `bmad-prd`.)
> Earlier revisions of this guide recommended the two deprecated names — that was wrong.

### Multi-project addressing

```bash
scripts/bmad-switch --current            # interactive sessions only
scripts/bmad-switch --list               # warns on marker/symlink desync
```

**Never call `scripts/bmad-switch` from a parallel agent.** The marker
(`_bmad/custom/.active-project`) and the two gitignored symlinks
(`_bmad-output/planning-artifacts`, `_bmad-output/implementation-artifacts`) are per-working-tree
global state — `_bmad/bmm/config.yaml` hard-codes the symlink path, so every planning-artifact
write resolves through it regardless of the marker. Address projects by physical path and pass
`BMAD_ACTIVE_PROJECT=<slug>` per invocation.

### bmad-loop (the external deterministic harness)

`bmad-loop >=0.9.0` is a conda-forge dependency, not a skill. Config lives in
`.bmad-loop/policy.toml`; `.bmad-loop/bmad_loop_hook.py` is wired into `.claude/settings.json` on
`SessionStart` / `Stop` / `SessionEnd` / `PreCompact`. `scripts/bmad-loop-worktree` provisions one
worktree per loop home, rooted since 2026-07-25 at the **short** path `~/.bmad-loops/<slug>`
(override with `BMAD_LOOP_HOME_ROOT`) — the long in-repo path triggered a
`pixi-build-python 0.8.3` byte-index-underflow panic.

See `architecture-bmad-infra.md` for the full skill catalog.

---

## Testing

There are **three** test suites, and only one of them is the skill suite.

### 1. Top-level `tests/` — one file, and it mutates the manifest

`tests/` contains exactly one file: **`tests/test_load_env.sh`**, a hand-rolled bash suite (no
pytest, no pixi task) with 6 tests covering `scripts/load-env.sh`. Run it directly:

```bash
bash tests/test_load_env.sh
```

> **Caveat — tests 4 and 5 patch `pixi.toml` in place.** They `cp pixi.toml pixi.toml.bak`,
> `sed -i` the `# default-env:` directive, assert, then `mv` the backup back. **If the run is
> interrupted between the `sed` and the `mv`, your working-tree `pixi.toml` is left patched** (and
> a stray `pixi.toml.bak` remains). Check `git diff pixi.toml` after any aborted run.

### 2. The conda-forge-expert skill suite

`.claude/skills/conda-forge-expert/tests/` — **100 `.py` files** (98 `test_*.py`), **1,186
`def test_`**, ~22.3k LOC. Layout: `unit/` 85 files, `meta/` 9, `integration/` 4, plus
`fixtures/` (39 files) and `data/` (2 JSON schemas). It uses **real fixtures** + the pytest
markers `@pytest.mark.network` and `@pytest.mark.slow`. **Do not mock the network** — that is an
explicit project-context anti-pattern.

```bash
pixi run test                            # offline subset (no markers)
pixi run test-all                        # full suite
pixi run test-coverage                   # coverage report
pixi run test-skill -- --meta            # scope to one layer
pixi run test-skill -- --keyword schema_header

# Raw pytest passthrough:
pixi run test -- -k test_recipe_yaml_schema_header
pixi run test -- -m "network and slow"
```

The **meta-tests** under `tests/meta/` enforce repo invariants:

- `test_all_scripts_runnable.py` — the three-place rule (below)
- `test_bmad_artifacts_in_sync.py` — integrity of this artifact set against the live factory
- `test_recipe_yaml_schema_header.py` — every `recipes/*/recipe.yaml` opens with the
  yaml-language-server directive on line 1
- `test_skill_md_consistency.py` — SKILL.md internal consistency
- `test_spec_surface_check.py` — the newest: every tracked file is spec-governed or allowlisted
- plus `test_actionable_scope.py`, `test_no_redundant_python_min.py`,
  `test_pypi_intelligence_scope.py`, `test_recipe_yaml_parse_audit.py`

If a meta-test fails, **fix the invariant, not the test**.

### 3. The five product suites (`src/shared/packages/*/tests/`)

Driven by the per-product pixi tasks, each in its own lean env:

| Product | `def test_` | Files | Notes |
|---|---|---|---|
| `pyforge-warden` | **1,575** | 65 | unit 1,283 / conformance 244 / meta 45 / root 3. `tests/fixtures/` is **16 MB, 2,031 files** — a 1,988-file recipe corpus, 24 fixture projects, an offline osv-db |
| `pyforge-atlas` | 772 | 110 (26 dirs) | plus `kedro-test`, `kedro-catalog-check`, `dagster-dryrun`, `parity-diff`, `bsl-metric-check`, `duckdb-singularity` |
| `pyforge-herald` | 112 | 5 | |
| `pyforge-doctor` | 62 | 6 | unit 45 / meta 17 |
| `pyforge-scribe` | 18 | 2 | |

```bash
pixi run --frozen -e pyforge-warden pyforge-warden-test
pixi run --frozen -e pyforge-atlas  kedro-test
```

### `--frozen` is mandatory inside a bmad-loop worktree

Not a performance tip — a correctness rule. An **unfrozen** re-solve inside a loop worktree:

1. **panics `pixi-build-python` 0.8.3** (byte-index underflow, `tools.rs:461`) on the ~250-char
   `workDirectory` a worktree path produces; and
2. rewrites `pixi.lock` with **worktree-absolute `file://` channel paths**, which a squash-merge
   would then commit to `main` ("lock poisoning" — one such path has already had to be scrubbed).

Rooting loop homes at `~/.bmad-loops/<slug>` (~197 chars) removes the trigger for the unfrozen
paths, but `--frozen` remains the primary mitigation. Prefer `pixi run --frozen -e <env> <task>`
for every verify command in a worktree.

---

## Debugging Common Issues

### "MCP tool not found"

The server hasn't registered. Check:
1. `.claude/tools/conda_forge_server.py` exists and is executable
2. Pixi env is `local-recipes` (or wherever Claude Code launched)
3. `fastmcp` is installed: `pixi list -e local-recipes fastmcp`
4. Restart Claude Code

### "pixi run X: command not found"

The task doesn't exist or is in a different feature. With 18 envs and 17 features this is the most
common false alarm — `scan-project`, `inventory-channel`, `detail-cf-atlas-vdb`, `vdb-refresh`, and
all 33 product tasks are **not** in `local-recipes`. Check:

```bash
pixi task list --environment <e> --machine-readable   # exact task set for one env
grep -n "tasks.X" pixi.toml                            # find which feature owns the task
pixi run -e <env> X -- <args>                          # specify env explicitly
```

### `bmad-preflight` fails with "No such file or directory"

Expected. The task's command is `bash scripts/ensure-bmad-preflight.sh` and that script does not
exist in the repo. Use `pixi run verify-env` + `pixi run --frozen -e local-recipes bmad-groundtruth`.

### "cf_atlas.db missing schema_version"

The DB is older than v17. Run `bootstrap-data --fresh` or `pixi run atlas-phase B` to trigger a clean rebuild + migration. Migrations are additive and idempotent; running them twice is safe.

### "phase_state table missing"

Same root cause as above — DB predates v7.7. `bootstrap-data --fresh` rebuilds; `--reset-cache` also wipes the parquet cache (rarely needed).

### "Phase H hangs"

Almost certainly the UX bug, not a real hang. Phase H pypi-json fan-out with 770k rows would silently work for 5-11 minutes before printing the first progress line. v7.7.0 added a 60s heartbeat. If you're on an older skill version, just wait.

To skip the wait entirely on cold start: `PHASE_H_SOURCE=cf-graph pixi run atlas-phase H` (uses local cf-graph tarball; 30 seconds total).

### "JFROG_API_KEY leaks to github.com"

Still unresolved in `_http.py` (verified 2026-07-25): when the env var is set, the
`X-JFrog-Art-Api` header attaches to **every** outbound request regardless of host. Don't export
`JFROG_API_KEY` in the same shell that runs `submit_pr` / `prepare_pr` /
`generate_recipe_from_pypi`. A per-callsite opt-out (`skip_auth=True`, 8 callsites) exists but is
not a global fix. See `deployment-guide.md` § The JFROG_API_KEY Cross-Host Leak.

### Build failure that won't reproduce

Check `build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log` — the **most recent** matching directory (use `ls -t ... | head -1`). `rattler-build` doesn't always clean `output_dir` between attempts, so old artifacts can mask current failures. When in doubt, `rm -rf build_artifacts/*/bld/rattler-build_<name>_*` and rebuild fresh.

### Cross-platform build that fails on a single platform

`win-64` is the usual culprit (build.bat shim issues — see Critical Constraint #5 about `call` prefix). Read `guides/cross-compilation.md` and check that `build-local-setup-sdk` ran for osx targets.

---

## Contributing

For changes to **conda-forge-expert** (the skill itself):
1. Identify the layer: SKILL.md / reference/ / guides/ / quickref/ / scripts/ / templates/
2. Edit + add tests (unit + integration as appropriate)
3. Update `CHANGELOG.md` TL;DR with a new entry
4. Bump skill version per semver
5. If the change affects project-context.md drift contract (MINOR or higher), re-verify and re-sync project-context.md

For changes to **cf_atlas pipeline**:
1. Schema changes go in `conda_forge_atlas.py:init_schema()` — additive only
2. Bump `SCHEMA_VERSION` constant
3. Add a migration test to confirm idempotency
4. Update CHANGELOG.md

For changes to **MCP server**:
1. Add `@mcp.tool()` decorator + thin wrapper body to `conda_forge_server.py` (46 tools today)
2. Ensure the wrapped Tier 1 script honors the `--json` contract
3. Add `mcp_call.py` integration test (currently sparse — adding one is +ev)

For **a new script** — the three-place rule, enforced by
`tests/meta/test_all_scripts_runnable.py`. All three, or the meta-test reds:

1. **Canonical implementation** → `.claude/skills/conda-forge-expert/scripts/<name>.py`
   (66 files, ~41,410 LOC — this is the source of truth; edit code here)
2. **Thin CLI wrapper** → `.claude/scripts/conda-forge-expert/<name>.py`
   (a subprocess shim; 60 entries in the dir today)
3. **A pixi task** in `pixi.toml` **and** an entry in the `SCRIPTS` list in
   `tests/meta/test_all_scripts_runnable.py` — a script with no task must instead be added to that
   file's `no_task_allowlist`

For changes to **BMAD infra**:
1. Skill additions live in `.claude/skills/<name>/`
2. Per-skill customization in `_bmad/custom/<name>.toml`
3. Don't edit `_bmad/config.toml` or `_bmad/config.user.toml` directly — both are regenerated by
   the installer. Project-scoped overrides go in
   `_bmad-output/projects/<slug>/.bmad-config.toml` (layers 5 and 6 of the six-layer merge)

For changes that span multiple parts:
1. Plan with `bmad-architecture` (**not** the deprecated `bmad-create-architecture`) or `bmad-quick-dev`
2. Use `bmad-checkpoint-preview` to walk a reviewer through the diff
3. Run `bmad-retrospective` at closeout if it touched conda-forge work

Every PR that changes any of the above touches files outside `recipes/` — see § PR CI gates.

---

## CI Pipeline

The full picture (workflows, gates, what actually deploys) lives in `deployment-guide.md`
§ CI / CD Considerations. The short version for a developer:

**GitHub Actions is where the action is** — **8 active workflows** (re-audited
2026-07-26, PR #127; was 12 + 1 disabled). The three that matter day to day:

- **`staged-recipes-linter.yml`** — runs on every PR (`opened` / `synchronize` / `reopened` /
  `labeled` / `unlabeled`). The two gates are in § PR CI gates above. **This is the one that will
  red your docs PR.**
- **`test-all.yml`** — **`workflow_dispatch` only**, "to preserve GitHub Actions quota". It fans
  out to `test-linux` / `test-macos` / `test-windows` via `workflow_call`, caps an `all` run at
  `head -20` changed recipes, and excludes `example`, `example-new-recipe`, `broken-recipes`.
  Platform jobs branch on recipe type: `recipe.yaml` → rattler-build, `meta.yaml` → conda-build.
  **Recipe builds are not automatic on push — you trigger them.**
- **`dashboard.yml`** — publishes the Guildhall console to GitHub Pages on every push to `main`
  plus a daily cron. The only thing this repo deploys.

Also present: `linter_issue_comment` (re-runs the linter, but **only** when a PR comment says
`please rerun linter` or `/rerun-linter`) and `sync-pypi-mappings` (**dispatch-only**).

Five inherited workflows were **deleted 2026-07-26** (PR #127) once the audit found upstream had
already deleted all five — `correct_directory` and `do_not_edit_example` were folded into
`scripts/linter.py` back in 2024 and had been dead duplicates here for ~2 years; `create_feedstocks`
moved to `conda-forge/admin-requests`; `automate-review-labels` needs conda-forge review teams that
do not apply to a fork; `tokens.yml.notused` was already disabled. Full inventory, provenance and
"when to use": **`docs/reference/github-workflows.md`**.

**`azure-pipelines.yml`** is inherited from upstream but heavily trimmed: branch builds are
**fully disabled** (`trigger.branches.exclude: ["*"]`), PRs to `main` are allowed, and
`[skip ci]` / `[skip azp]` are honored. Upstream's `fast_finish` and `status` aggregation jobs were
deleted. Templates remain in `.azure-pipelines/`. **Unverifiable from the repo:** whether an Azure
DevOps project is actually attached to this fork — treat Azure legs as inherited scaffolding until
someone confirms otherwise.

**Local build config is local-only.** `conda_build_config.yaml` (1,103 lines) is a local copy of
conda-forge-pinning so local rattler-build / conda-build can resolve compilers and `stdlib("c")`
outside CI; `.ci_support/local_testing_overrides.yaml` is explicitly "should NOT be used in real
CI". `.scripts/` (5 CI build drivers) and `.ci_support/{build_all,compute_build_graph}.py` are
identical to upstream.

---

## Where to look when stuck

| Symptom | First file to read |
|---|---|
| Recipe authoring question | `.claude/skills/conda-forge-expert/SKILL.md` |
| MCP tool signature | `.claude/skills/conda-forge-expert/reference/mcp-tools.md` |
| What input formats `scan_project` accepts | `.claude/skills/conda-forge-expert/reference/dependency-input-formats.md` |
| Build failure pattern | `.claude/skills/conda-forge-expert/guides/ci-troubleshooting.md` |
| Cross-compile question | `.claude/skills/conda-forge-expert/guides/cross-compilation.md` |
| Atlas operations | `.claude/skills/conda-forge-expert/guides/atlas-operations.md` |
| Writing or refactoring an atlas phase | `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` |
| Air-gap setup | `docs/reference/enterprise-deployment.md` (or `deployment-guide.md` in this set) |
| MCP server internals | `docs/reference/mcp-server-architecture.md` |
| Which library / CLI is available where | `docs/reference/library-llms-full.md` (detector: `pixi run llms-full-check`) |
| Recipe authoring gotchas | `.claude/skills/conda-forge-expert/SKILL.md` § Recipe Authoring Gotchas (G1–G107) |
| BMAD multi-project | `_bmad-output/PROJECTS.md` |
| Keeping this doc set honest | `_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md` |
| Project-specific rules | `_bmad-output/projects/local-recipes/project-context.md` |
| Recent changes | `.claude/skills/conda-forge-expert/CHANGELOG.md` TL;DR |

> Path note: the reference docs moved under `docs/reference/`. Earlier revisions of this guide
> cited `docs/enterprise-deployment.md` — that path does not exist. Also, `docs/copilot-to-api.md`
> was **purged** from the repo in the 2026-07-24 secret-leak remediation; do not reference it.
