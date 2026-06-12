# MCP Tools Reference

The conda-forge-expert skill exposes 30+ tools via a FastMCP server at `.claude/tools/conda_forge_server.py`. Full schemas (parameters, defaults, return types) are surfaced at tool-call time; this file is a navigable index by purpose.

The tools fall into three layers:
1. **Recipe authoring** (the original v6.x tooling) — generate / validate / edit / build / migrate / submit.
2. **Atlas intelligence** (added in v7.0.0) — query / report / classify / scan offline against `cf_atlas.db`.
3. **Project / SBOM scanning** (also v7.0.0) — unified `scan_project` covering manifests / images / SBOMs / live envs / Kubernetes / GitOps.

## Core Capabilities

| Tool | Purpose |
|---|---|
| `generate_recipe_from_pypi` | Create a new recipe from a PyPI package. |
| `edit_recipe` | Programmatically modify a recipe file using structured actions. **Preferred method for all edits.** |
| `check_dependencies` | Verify dependencies exist on conda-forge or a custom channel. Uses batch repodata.json fetching (fast, air-gapped-friendly). Supports JFrog Artifactory via `channel` param + auth env vars (`JFROG_API_KEY`, etc.). |
| `validate_recipe` | Lint a recipe against conda-forge standards; also runs `rattler-build lint` when available. |
| `optimize_recipe` | Lint for quality and best practices. Check codes: DEP-001 (dev dep in run), DEP-002 (noarch Python upper bound), PIN-001 (exact pin), ABT-001 (missing license_file), SCRIPT-001/002 (build.sh anti-patterns), SEL-001/002 (redundant selectors, CFEP-25 python_min). |

## Build, Test, and Debug

| Tool | Purpose |
|---|---|
| `trigger_build` | Start a local build asynchronously. |
| `get_build_summary` | Poll for the build result; returns a JSON report. |
| `analyze_build_failure` | Take an error log from a failed build and suggest a structured fix. |

## Security and Maintenance

| Tool | Purpose |
|---|---|
| `update_recipe` | **"Autotick" Bot (PyPI).** Check for new upstream PyPI versions and update the recipe. |
| `update_recipe_from_github` | **"Autotick" Bot (GitHub).** Fetch the latest GitHub release and update. Use for packages not on PyPI. Always `dry_run=True` first. |
| `check_github_version` | Read-only GitHub version check — returns the latest tag without modifying the recipe. |
| `scan_for_vulnerabilities` | Scan a recipe's dependencies against OSV.dev (API primary, local DB offline fallback). |
| `update_cve_database` | Update the local CVE database from `osv.dev`. |
| `update_mapping_cache` | Update the local PyPI-to-Conda name-mapping cache from Grayskull. Run when `get_conda_name` misses a package. |
| `migrate_to_v1` | **meta.yaml → recipe.yaml** via `feedrattler`. meta.yaml is preserved; review and remove it manually after validation. |
| `submit_pr` | Push the recipe to your staged-recipes fork and open a PR to conda-forge. Always `dry_run=True` first. |
| `download_pr_artifacts` | **v8.14.0.** Fetch CI-published `.conda` artifacts from a conda-forge staged-recipes or feedstock PR via the Azure DevOps Build Artifacts REST API. Resolves the Azure `buildId` from `gh pr checks`, anonymously streams the `conda_pkgs_(linux\|osx\|win)` ZIPs (no PAT, no `az login`), and extracts them into `build_artifacts/pr/<pr-number>/<buildId>/extracted/` — a valid `file://` mamba channel. Idempotent (manifest-keyed cache); `force=True` re-fetches. Read-only — no PR modification. Use to spot-check artifacts before merge approval or to bulk-fetch for offline smoke-tests. |
| `get_conda_name` | Resolve a PyPI package name to its conda-forge equivalent. |
| `run_system_health_check` | Full diagnostic on the development environment. |

## Atlas Intelligence (v7.0.0)

These tools wrap the cf_atlas data layer (~16 schema versions, 15 pipeline phases). All read from `cf_atlas.db` offline — no network access required for queries (Phase G's *fresh* vuln data needs the vuln-db env, but cached counts work everywhere).

| Tool | Purpose |
|---|---|
| `query_atlas` | Direct SELECT against `packages` (read-only, write-keywords blocked, LIMIT capped). Use for ad-hoc questions when the higher-level tools don't fit. |
| `package_health` | Full health card for one package — combines Phase B/E/F/G/H/J/K/M/N signals. |
| `my_feedstocks` | List all feedstocks where a maintainer is in the recipe-maintainers list, with download / version / archived / risk per row. |
| `staleness_report` | Stalest feedstocks — sortable by `--by-risk` (Phase G CVE counts) or filterable by `--has-vulns` / `--bot-stuck`. |
| `feedstock_health` | Filter to `stuck` (Phase M errors), `bad` (cf-graph flag), `open-pr` (bot PR), `ci-red` (Phase N CI failure), `open-issues`, `open-prs-human`, or `all`. |
| `whodepends` | Phase J dependency graph — forward (what does X depend on) or `--reverse` (who depends on X). Filter by `--type build/host/run/test`. |
| `behind_upstream` | Per-row upstream-of-record comparison: PyPI / GitHub / GitLab / Codeberg / npm / CRAN / CPAN / LuaRocks / crates.io / RubyGems / NuGet / Maven. Picks the right registry based on `conda_source_registry`. |
| `cve_watcher` | Diff `vuln_history` snapshots — what CVE counts changed in the last N days. Severity filter (Critical / High / KEV / Total) + `--only-increases` filter. |
| `version_downloads` | Per-version download breakdown for one package (Phase I). Sort by upload date or by adoption (`--by-downloads`). |
| `release_cadence` | Trend classifier — accelerating / stable / decelerating / silent — based on rolling 30/90/365-day release counts. |
| `find_alternative` | Suggest healthier replacements for an archived/abandoned package. Ranks by keyword/summary/dependent/maintainer overlap × recency × downloads. |
| `adoption_stage` | Lifecycle stage classifier — bleeding-edge / stable / mature / declining / silent — based on age + cadence + downloads. |
| `scan_project` | Unified scanner: project paths / container images / SBOMs (CycloneDX 1.x + 1.6 + XML; SPDX 2.x JSON + 2.x tag-value + 3.0 JSON-LD; syft / trivy native JSON) / live conda envs / live Python venvs / Kubernetes manifests / Helm charts (rendered) / Kustomize overlays (built) / Argo CD Applications / Flux HelmReleases & Kustomizations / OCI archives. License compatibility check. SBOM emit with optional Phase G vuln annotations. |

### Atlas tool selection cheatsheet

| Question | Tool |
|---|---|
| "What should I work on this week?" (maintainer triage) | `staleness_report --by-risk --maintainer X` |
| "Which feedstocks have stuck bots?" | `feedstock_health stuck --maintainer X` |
| "Which feedstocks are behind upstream?" | `behind_upstream --maintainer X` |
| "What CVEs landed this week?" | `cve_watcher --maintainer X` |
| "Who depends on my package?" | `whodepends <pkg> --reverse` |
| "Is this package still maintained?" | `adoption_stage --package <pkg>` |
| "What can replace this archived dep?" | `find_alternative <archived-name>` |
| "Show me the per-version downloads" | `version_downloads <pkg>` |
| "Scan my pixi.lock / SBOM / Helm chart / live K8s cluster for CVEs" | `scan_project` (unified entry point) |

## Special notes (not surfaced in tool docstrings)

- **`submit_pr` and `update_recipe_from_github`** — always run `dry_run=True` first to verify prerequisites (gh auth, fork presence, branch state).
- **`migrate_to_v1`** — preserves the original `meta.yaml`. Validate the converted `recipe.yaml` first, then remove `meta.yaml` manually. Never leave both files in the same recipe directory at build time.
- **`check_dependencies` JFrog support** — for air-gapped or corporate environments, pass `channel="https://your-jfrog-host/conda-forge"` plus the `JFROG_API_KEY` env var (or `JFROG_USERNAME` + `JFROG_PASSWORD`). See `docs/enterprise-deployment.md`.
- **`update_cve_database`** — runs offline-friendly (downloads OSV.dev's full database to `~/.cache/conda-forge-skill/`); use during initial setup or to refresh CVE feed. Not needed before each scan if the database is recent.

## See also

- **Lifecycle integration** — The 9-step Autonomous Loop (Generate → Validate → Edit → Security Scan → Optimize → Check Deps → Trigger Build → Monitor → Submit PR) in `SKILL.md` § "Primary Workflow: The Autonomous Loop" specifies success criteria and pre-conditions for each tool.
- **Server source** — `.claude/tools/conda_forge_server.py` (FastMCP) for canonical signatures and implementation.
