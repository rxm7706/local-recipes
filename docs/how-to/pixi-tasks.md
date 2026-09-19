# Pixi tasks

Task-oriented reference for the pixi task surface. Everything is defined in `pixi.toml`, and every task is bound to one or more environments:

- **`pyforge-guild`** — the session default for every agent and harness (~860 MB): detectors, ledger sync, surface stamps, `fleet-picture`, marshal dispatch/spin, and the `doctor` / `marshal` / `scribe` / `steward` CLIs. `pixi task list -e pyforge-guild` lists the Guild set.
- **`local-recipes`** — Mason's recipe-factory environment (10 GB): rattler-build, the conda-forge-expert wrappers, and the cf_atlas CLIs. It also includes every Guild task, so `pixi run -e local-recipes <guild task>` still works, but it is not the default. `pixi task list -e local-recipes` lists the full set.
- **Per-station and tool envs** — `pyforge-<station>` for each station's own `-test` / `-build` tasks, `grayskull` / `conda-smithy` for recipe scaffolding and lint, `vuln-db` for the vulnerability database, `platform-dev` for the Django host.

Pass extra args after `--`:

```bash
pixi run -e <env> <task> -- [args]
```

The tables below name each task's environment where it is not `local-recipes`.

## Build tasks (per-platform `build-locally.py` wrappers)

| Task | What it does |
|------|--------------|
| `build-linux` | Build all `linux-*` configs (Docker on the host) |
| `build-osx` | Build all `osx-*` configs (native; macOS only) |
| `build-win` | Build all `win-*` configs (native; Windows only) |

## Recipe tooling (conda-forge-expert wrappers)

The `pixi run` task names below are stable; they invoke thin entrypoint
wrappers at `.claude/scripts/conda-forge-expert/` that delegate to the canonical
implementation in `.claude/skills/conda-forge-expert/scripts/`. Run any task
with `--help` to see its options.

| Task | Underlying script |
|------|-------------------|
| `validate` | `validate_recipe.py` — schema + license + checksum + conda-smithy lint |
| `lint-optimize` | `recipe_optimizer.py` — best-practice linter (DEP/SEC/MAINT/STD codes) |
| `check-deps` | `dependency-checker.py` — verify deps resolve on conda-forge |
| `scan-vulnerabilities` | `vulnerability_scanner.py` — OSV.dev / local-DB CVE scan |
| `license-check` | `license-checker.py` — SPDX + license_file validation |
| `analyze-failure` | `failure_analyzer.py` — match a build error log to known patterns |
| `migrate` | `feedstock-migrator.py` — meta.yaml → recipe.yaml v1 |
| `generate-recipe` | `recipe-generator.py` — scaffold from PyPI / template / GitHub |
| `generate-cran` | `recipe-generator.py cran` — scaffold an R recipe from CRAN |
| `generate-cpan` | `recipe-generator.py cpan` — scaffold a Perl recipe from CPAN |
| `generate-luarocks` | `recipe-generator.py luarocks` — scaffold a Lua recipe from LuaRocks |
| `generate-npm` | `recipe-generator.py npm` — scaffold a v1 recipe + build.sh + bld.bat for an npm package |
| `resolve-name` | `name_resolver.py` — PyPI name → conda-forge name |
| `version-check` | `github_version_checker.py` — read-only latest-release lookup |
| `autotick` | `recipe_updater.py` — PyPI autotick |
| `autotick-github` | `github_updater.py` — GitHub-release autotick |
| `autotick-npm` | `npm_updater.py` — npm-registry autotick |

## Scaffolding & Linting (grayskull / conda-smithy)

Tasks for bootstrapping and linting recipes via external generators. Run these in the `grayskull` or `conda-smithy` environments.

| Task | What it does |
|------|--------------|
| `pypi` | Generate a v1 (rattler-build) recipe from PyPI via grayskull |
| `cran` | Generate a v1 recipe from CRAN via grayskull |
| `pypi-v0` | Generate a v0 (meta.yaml) recipe from PyPI |
| `cran-v0` | Generate a v0 recipe from CRAN |
| `lint` | Run the CI-parity `conda-smithy` linter across all recipes |

## Station Operations (PyForge Guild)

Each station's test and build tasks live in that station's own environment (`pixi run -e pyforge-<station> …`); the cross-station tasks live in `pyforge-guild`.

| Task | Environment | What it does |
|------|-------------|--------------|
| `pyforge-mason-build` | `pyforge-mason` | Builds both the conda package and the wheel/sdist for the Mason station |
| `pyforge-mason-test` | `pyforge-mason` | Runs the Mason unit + meta test suite (`pyforge-mason-test-slow` for the real-CFE tests) |
| `pyforge-steward-build` | `pyforge-steward` | Builds both artifacts for the Steward station |
| `pyforge-steward-test` | `pyforge-steward` | Runs the Steward suite across all three tiers |
| `pyforge-<station>-test` / `-build` | `pyforge-<station>` | (Pattern) The same pair for any of the 8 stations |
| `pyforge-station-tests` | `pyforge-guild` | `pyforge-core` + all 8 station suites, mirroring `.github/workflows/pyforge-station-tests.yml` — run before pushing any `pixi.toml` / `pixi.lock` / `pyforge-core` / `pyforge-testing-kit` change |
| `detectors` / `detectors-ci` | `pyforge-guild` | Every detector / the CI-safe subset (see [run-and-understand-detectors.md](run-and-understand-detectors.md)) |
| `fleet-picture` | `pyforge-guild` | Read-only fleet progress report from the tracked sprint ledgers (see [monitor-the-fleet.md](monitor-the-fleet.md)) |
| `pr-preflight` | `pyforge-guild` | Everything a non-recipe PR actually gates on, in one local run |

## Cross-channel package intelligence (Atlas + vulnerability DB)

The atlas (`cf_atlas.db`) is a queryable cross-channel package map combining
conda-forge with PyPI / npm / CRAN / CPAN / LuaRocks linkage. The vulnerability
database adds multi-source CVE lookups (NVD + GHSA + OSV + npm + Snyk + Aqua +
custom). Atlas tasks run in `local-recipes`; vuln-DB tasks run in `vuln-db`.

| Task | What it does |
|------|--------------|
| `build-cf-atlas` | Build the atlas (8-phase pipeline, ~165 MB SQLite) |
| `query-cf-atlas <name>` | Look up a package in the atlas |
| `stats-cf-atlas` | Summary stats (pkg counts, build provenance) |
| `detail-cf-atlas <name>` | Detail card with cross-channel + build matrix (anaconda.org files API; falls back to `current_repodata.json` from prefix.dev / pixi mirror / `CONDA_FORGE_BASE_URL` for air-gapped networks). Add `--vdb` (in `vuln-db` env) for multi-source CVE lookup, `--version VER` to scope the affecting-set to an arbitrary release |
| `detail-cf-atlas-vdb <name>` | Convenience wrapper that presets `--vdb --vdb-all` so you only pass `<name>` and optionally `--version VER` (vuln-db env) |
| `vdb-refresh` | Build/refresh the AppThreat multi-source vulnerability DB (~5–10 min) |
| `scan-project <path>` | Scan a directory or `--github URL` for CVEs across pixi.lock, pixi.toml, Cargo.lock/toml, requirements.txt, pyproject.toml, environment.yml, Containerfile (vuln-db env) |
| `inventory-channel <url>` | Inventory a channel/mirror (conda repodata, PyPI Simple, npm, crates.io). JFrog auth via env vars (vuln-db env) |

## Local builds (Docker-less rattler-build)

| Task | What it does |
|------|--------------|
| `recipe-build` | Build one recipe natively (recommended default) |
| `recipe-build-docker` | Full conda-forge CI fidelity via Docker (alma9) |
| `recipe-build-cross` | Cross-build for a target platform |
| `build-local` | Build a recipe natively (linux-64) with full tests |
| `build-local-all` | Cross-build for every supported platform (skips tests on cross-targets) |
| `build-local-check` | Diagnose what's available locally (rattler-build, SDKs, platforms) |
| `build-local-setup-sdk` | Download MacOSX SDK to `./SDKs/` for `osx-*` cross-builds |

## Maintenance & infrastructure

| Task | What it does |
|------|--------------|
| `health-check` | Full diagnostic on the dev env (Docker, gh, OSV API, scripts) |
| `bootstrap-data` | One-time / periodic full atlas refresh + mapping + CVE + vdb (30-45 min cold, 5-10 min warm) |
| `verify-env` | Confirms the shell is inside the `local-recipes` pixi env and the `# default-env:` directive is intact (`local-recipes` only) |
| `bmad-groundtruth` | Live factory facts as JSON (skill version, schema, MCP tools, atlas phases, pixi envs, gotchas) — also in `pyforge-guild` |
| `bmad-drift-check` | Artifact-vs-live drift report (pins, counts, stale rules, archive hygiene, baseline) — also in `pyforge-guild` |
| `update-cve-db` | Refresh local OSV CVE database |
| `update-mapping-cache` | Refresh PyPI ↔ conda name mapping cache |
| `sync-upstream-conda-forge` | Rebase fork onto `conda-forge/staged-recipes` |
| `submit-pr` | Open a PR against `conda-forge/staged-recipes` (use `--dry-run` first) |
| `test-recipes` | Run `test-recipes.py` (random / targeted recipe smoke validation) |
| `test-skill` | Run the conda-forge-expert test suite |
| `test-all` | Run the full test suite incl. live-network tests |
| `test-coverage` | Test suite with coverage report |

> **`pixi run bmad-preflight` is broken** — it shells out to `bash scripts/ensure-bmad-preflight.sh`,
> which does not exist in the repo. Use `verify-env` + `bmad-groundtruth` instead.

## Enterprise routing

Behind a JFrog Artifactory or other private mirror,
set `JFROG_API_KEY` (or `JFROG_USERNAME`+`JFROG_PASSWORD`) and any
mirror-specific env vars (`CONDA_FORGE_BASE_URL`, `ANACONDA_API_BASE`,
`GITHUB_API_BASE`). The shared `_http.py` helper picks them up at runtime
alongside system trust roots and `~/.netrc`. **No enterprise URLs live in
the committed `pixi.toml`** — the same checkout works externally and
internally. See [`docs/explanation/enterprise-deployment.md`](../explanation/enterprise-deployment.md) for architecture rationale and [`air-gapped mirror setup`](air-gapped-mirror-setup.md) for procedural steps.
