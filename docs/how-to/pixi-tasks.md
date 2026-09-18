# Pixi tasks

Task-oriented reference for the `local-recipes` pixi environment. The full task surface is defined in `pixi.toml`. Pass extra args after `--`:

```bash
pixi run -e local-recipes <task> -- [args]
```

List all tasks: `pixi task list -e local-recipes`

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
| `verify-env` | Confirms the shell is inside the `local-recipes` pixi env and the `# default-env:` directive is intact |
| `bmad-groundtruth` | Live factory facts as JSON (skill version, schema, MCP tools, atlas phases, pixi envs, gotchas) |
| `bmad-drift-check` | Artifact-vs-live drift report (pins, counts, stale rules, archive hygiene, baseline) |
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
