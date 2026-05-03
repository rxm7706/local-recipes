---
project_name: 'local-recipes'
user_name: 'rxm7706'
date: '2026-04-30'
sections_completed: ['default_conventions', 'tech_stack', 'recipe_format', 'compiler_stdlib', 'python_policy', 'dependency_resolution', 'mcp_lifecycle', 'sha256', 'build_test', 'anti_patterns', 'canonical_patterns', 'air_gapped', 'submission_workflow', 'repository_conventions']
existing_patterns_found: 1392
status: 'complete'
rule_count: 44
optimized_for_llm: true
sync_sources: ['CLAUDE.md', '.claude/skills/conda-forge-expert/SKILL.md', '.claude/skills/conda-forge-expert/reference/', '.claude/skills/conda-forge-expert/quickref/']
maintenance_model: 'hand-edited; per-section sync tags identify the upstream source — update here in the same PR as the upstream change'
---

# Project Context for AI Agents

_Foundational rules every BMAD agent reads on spawn. Mirrors `CLAUDE.md` (repo-wide guidance) and the `conda-forge-expert` skill (conda-forge specifics); hand-maintained — verify alignment when sources change._

---

## Default Conventions

- Maintainer for new recipes: `rxm7706` (in `extra.recipe-maintainers`)
- Recipe format emitted by `generate_recipe_from_pypi`: v1 `recipe.yaml`
- Default channel: `conda-forge`
- Target platforms: linux-64, linux-aarch64, osx-64, osx-arm64, win-64
- Build engine: pixi + rattler-build (NOT conda-build, except for legacy v0 maintenance during migration)

## Technology Stack

Versions live in `pixi.toml` — read it, do not duplicate version numbers in prose. Highlights not obvious from the manifest:
- 7 pixi envs; **`local-recipes`** is the default (set via the `default-env:` directive at the top of `[environments]` in `pixi.toml`)
- 5 build platforms (above)
- FastMCP server at `.claude/tools/conda_forge_server.py` exposes the recipe lifecycle as MCP tools

## Recipe Format Rules

(Sync: `.claude/skills/conda-forge-expert/reference/recipe-yaml-reference.md` + `meta-yaml-reference.md`)

- **Always use v1 `recipe.yaml`** with `schema_version: 1` and the rattler-build schema header (`# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json`).
- v0 `meta.yaml` is migration source only. **When you touch a v0 recipe, migrate it in the same PR**: `migrate_to_v1` → `validate_recipe` → delete `meta.yaml` → commit.
- v1 substitution: `${{ name }}` / `${{ version }}`. v0 Jinja2 `{{ name }}` is only relevant inside the migration PR itself.
- License: valid SPDX identifier. `license_file` MUST be a list, even with one entry.

## Compiler & stdlib Rule (auto-rejection trigger)

(Sync: `.claude/skills/conda-forge-expert/SKILL.md` § Critical Constraints + `reference/recipe-yaml-reference.md` § Requirements)

Any recipe using `${{ compiler("c") }}`, `${{ compiler("cxx") }}`, or `${{ compiler("rust") }}` MUST include `${{ stdlib("c") }}` in `requirements.build`. `optimize_recipe` flags this as **STDLIB-001**. Missing stdlib = automatic conda-forge CI rejection.

## Python Version Policy

(Sync: `.claude/skills/conda-forge-expert/reference/python-min-policy.md`)

- Floor tracks `conda-forge-pinning-feedstock`. Current floor: `"3.10"` (3.9 dropped August 2025).
- `noarch: python` recipes use the CFEP-25 triad: `host: python ${{ python_min }}.*` / `run: python >=${{ python_min }}` / test `python_version: ${{ python_min }}.*`.
- Compiled Python packages: `python >=3.10`, no `python_min` variable (build matrix handles versioning via the global pin).
- Never downgrade below the current floor in a new submission.

## Dependency Resolution

(Sync: `.claude/skills/conda-forge-expert/reference/mcp-tools.md` § Core Capabilities, `check_dependencies` / `get_conda_name`)

- Resolve PyPI → conda names via `get_conda_name` MCP tool or `name_resolver.py`. Don't guess.
- Verify all deps with `check_dependencies` before submission.
- When a pinned version is unavailable on conda-forge: loosen the pin to the available version and add a TODO in this exact format: `# TODO(pin-tighten): <pkg> >=<target> when available on conda-forge`.

## Autonomous MCP Lifecycle (the spine)

(Sync: `.claude/skills/conda-forge-expert/SKILL.md` § Primary Workflow: The Autonomous Loop)

```
generate_recipe_from_pypi
  → validate_recipe
  → edit_recipe
  → scan_for_vulnerabilities
  → optimize_recipe
  → trigger_build
  → get_build_summary
  → analyze_build_failure (loop back to edit_recipe)
  → submit_pr(dry_run=True)
  → submit_pr()
```

Use `edit_recipe` with structured actions for routine version/SHA/maintainer changes. Hand-edit YAML only for changes the structured action set doesn't cover.

## SHA256 Verification

(Sync: `.claude/skills/conda-forge-expert/reference/recipe-yaml-reference.md` + `mcp-tools.md` `edit_recipe` action set)

- SHA256 source of truth: PyPI JSON API (`https://pypi.org/pypi/<pkg>/<ver>/json` → `urls[].digests.sha256`) or `sha256sum` of the downloaded source tarball.
- Write SHA256 with `edit_recipe`; never hand-edit.

## Build & Test Rules

(Sync: `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` § Project Pixi Tasks + Building § build-locally.py)

- Native linux-64 = full build + test via `rattler-build`.
- Cross-platform builds (osx-*, win-64, linux-aarch64) skip tests with `--no-test`; win-64 also passes `--allow-symlinks-on-windows`.
- Linux builds run inside Docker (`build-locally.py`); osx/win run directly on host.
- For local cross-platform on a Linux host: build linux-64 + linux-aarch64 only; rely on conda-forge CI for osx/win unless explicitly requested.

## Anti-Patterns

The canonical lint codes come from `optimize_recipe`: **DEP-001, DEP-002, PIN-001, ABT-001, SCRIPT-001/002, SEL-001/002, STDLIB-001**. Run `optimize_recipe` and fix what it flags.

Three project-specific gotchas the linter doesn't catch:
- **Bare `pnpm --version` / `npm --version` in `build.bat`** — the .cmd shim silently terminates the parent script. Always prefix with `call`: `call pnpm --version`.
- **Mocking the network in `.claude/skills/conda-forge-expert/tests/`** — the suite uses real fixtures + the `network` and `slow` pytest markers. Run `pixi run -e local-recipes test` for the offline subset.
- **`submit_pr` without `dry_run=True` first** — always dry-run to verify `gh auth`, fork existence, and branch state.

## Canonical Patterns

- **npm-ecosystem recipes**: `npm pack` + `npm install --global` + `pnpm-licenses` for license capture. Default source = npm registry. `license_file` as a list. No `__unix` / `__win` selectors.
- **GitHub-only sources** (no PyPI): use `update_recipe_from_github` for autotick. Always `dry_run=True` first.
- **v0 → v1 migration**: `migrate_to_v1` invokes feedrattler. Always migrate v0 when you touch the recipe — see Recipe Format Rules above.

## Air-Gapped / Enterprise

(Sync: CLAUDE.md → "Project Documentation Reference" → `docs/enterprise-deployment.md`)

- All workflows MUST function offline.
- Channel resolution is configurable via `.pixi/config.toml`; auth via env vars per `docs/enterprise-deployment.md` (e.g., `JFROG_API_KEY` for Artifactory; other providers via their respective env vars).
- Local CVE database (`update_cve_database`) and PyPI mapping cache (`update_mapping_cache`) MUST be refreshable from internal sources.

## Submission Workflow

(Sync: `.claude/skills/conda-forge-expert/reference/mcp-tools.md` → `submit_pr`)

- Target: `conda-forge/staged-recipes` fork → upstream PR.
- **Submission-ready gate** (all four required): `validate_recipe` clean + `optimize_recipe` clean + `scan_for_vulnerabilities` clean + linux-64 build green.
- ALWAYS `submit_pr(recipe_name, dry_run=True)` first; verifies `gh auth`, fork, branch state.
- After merge, work moves to `<package>-feedstock` repo. Post-publish fixes go to `conda-forge-repodata-patches-feedstock`, not feedstock rebuilds.

## Repository Conventions

- Recipes: `recipes/<package-name>/recipe.yaml` (canonical). `meta.yaml` is transient migration state only.
- CI helpers: canonical implementation lives in `.claude/skills/conda-forge-expert/scripts/`; the public CLI surface is the thin wrapper layer at `.claude/scripts/conda-forge-expert/`. Wrap them as pixi tasks (pointing at the wrapper layer) before adding new CLIs elsewhere.
- Skill data (mutable runtime state, gitignored): `.claude/data/conda-forge-expert/` — cf_atlas.db, vdb/, cve/, pypi_conda_map.json, inventory_cache/.
- Pass extra args to pixi tasks after `--`: `pixi run -e local-recipes validate -- recipes/numpy`.
- Project docs: `docs/`. BMAD planning artifacts: `_bmad-output/planning-artifacts/`.

---

## Usage

- **BMAD agents**: read on spawn; cite specific sections rather than restating rules.
- **Humans**: keep this file in sync with the source files identified in each section's `(Sync: ...)` tag. After the 2026-Q2 multi-skill restructure, sources live in `CLAUDE.md` (repo-wide guidance) and `.claude/skills/conda-forge-expert/{SKILL.md,reference/*,quickref/*}` (conda-forge specifics). When a source changes, update the matching section here in the same PR.

<!-- Sync sources: CLAUDE.md (repo-wide) + .claude/skills/conda-forge-expert/ (conda-forge specifics). Hand-maintained — verify alignment when sources change. -->
