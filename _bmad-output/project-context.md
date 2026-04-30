---
project_name: 'local-recipes'
user_name: 'rxm7706'
date: '2026-04-30'
sections_completed: ['default_conventions', 'tech_stack', 'recipe_format', 'compiler_stdlib', 'python_policy', 'dependency_resolution', 'mcp_lifecycle', 'sha256', 'build_test', 'anti_patterns', 'canonical_patterns', 'air_gapped', 'submission_workflow', 'repository_conventions']
existing_patterns_found: 1392
status: 'complete'
rule_count: 44
optimized_for_llm: true
sync_source: 'CLAUDE.md'
maintenance_model: 'hand-edited; sync with CLAUDE.md per-change'
---

# Project Context for AI Agents

_Foundational rules every BMAD agent reads on spawn. Mirrors `CLAUDE.md`; hand-maintained — verify alignment when `CLAUDE.md` changes._

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

(Sync: CLAUDE.md → "Recipe Formats")

- **Always use v1 `recipe.yaml`** with `schema_version: 1` and the rattler-build schema header (`# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json`).
- v0 `meta.yaml` is migration source only. **When you touch a v0 recipe, migrate it in the same PR**: `migrate_to_v1` → `validate_recipe` → delete `meta.yaml` → commit.
- v1 substitution: `${{ name }}` / `${{ version }}`. v0 Jinja2 `{{ name }}` is only relevant inside the migration PR itself.
- License: valid SPDX identifier. `license_file` MUST be a list, even with one entry.

## Compiler & stdlib Rule (auto-rejection trigger)

(Sync: CLAUDE.md → "⚠️ Critical Build Requirement: `stdlib`")

Any recipe using `${{ compiler("c") }}`, `${{ compiler("cxx") }}`, or `${{ compiler("rust") }}` MUST include `${{ stdlib("c") }}` in `requirements.build`. `optimize_recipe` flags this as **STDLIB-001**. Missing stdlib = automatic conda-forge CI rejection.

## Python Version Policy

(Sync: CLAUDE.md → "Python Version Policy (`python_min`)")

- Floor tracks `conda-forge-pinning-feedstock`. Current floor: `"3.10"` (3.9 dropped August 2025).
- `noarch: python` recipes use the CFEP-25 triad: `host: python ${{ python_min }}.*` / `run: python >=${{ python_min }}` / test `python_version: ${{ python_min }}.*`.
- Compiled Python packages: `python >=3.10`, no `python_min` variable (build matrix handles versioning via the global pin).
- Never downgrade below the current floor in a new submission.

## Dependency Resolution

(Sync: CLAUDE.md → "AI-Assisted Workflow", `check_dependencies` / `get_conda_name`)

- Resolve PyPI → conda names via `get_conda_name` MCP tool or `name_resolver.py`. Don't guess.
- Verify all deps with `check_dependencies` before submission.
- When a pinned version is unavailable on conda-forge: loosen the pin to the available version and add a TODO in this exact format: `# TODO(pin-tighten): <pkg> >=<target> when available on conda-forge`.

## Autonomous MCP Lifecycle (the spine)

(Sync: CLAUDE.md → "Autonomous Recipe Lifecycle Loop")

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

(Sync: CLAUDE.md → "Recipe Formats", and the `edit_recipe` action set)

- SHA256 source of truth: PyPI JSON API (`https://pypi.org/pypi/<pkg>/<ver>/json` → `urls[].digests.sha256`) or `sha256sum` of the downloaded source tarball.
- Write SHA256 with `edit_recipe`; never hand-edit.

## Build & Test Rules

(Sync: CLAUDE.md → "Manual CLI Commands" / `build-locally.py`)

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

(Sync: CLAUDE.md → "AI-Assisted Workflow" → `submit_pr`)

- Target: `conda-forge/staged-recipes` fork → upstream PR.
- **Submission-ready gate** (all four required): `validate_recipe` clean + `optimize_recipe` clean + `scan_for_vulnerabilities` clean + linux-64 build green.
- ALWAYS `submit_pr(recipe_name, dry_run=True)` first; verifies `gh auth`, fork, branch state.
- After merge, work moves to `<package>-feedstock` repo. Post-publish fixes go to `conda-forge-repodata-patches-feedstock`, not feedstock rebuilds.

## Repository Conventions

- Recipes: `recipes/<package-name>/recipe.yaml` (canonical). `meta.yaml` is transient migration state only.
- CI helpers: `.claude/skills/conda-forge-expert/scripts/` — wrap them as pixi tasks before adding new CLIs elsewhere.
- Pass extra args to pixi tasks after `--`: `pixi run -e local-recipes validate -- recipes/numpy`.
- Project docs: `docs/`. BMAD planning artifacts: `_bmad-output/planning-artifacts/`.

---

## Usage

- **BMAD agents**: read on spawn; cite specific sections rather than restating rules.
- **Humans**: keep this file in sync with `CLAUDE.md`. The `(Sync: ...)` tag on each section identifies its source. When `CLAUDE.md` changes, update the matching section here in the same PR — don't merge one without the other.

<!-- Sync source: CLAUDE.md. Hand-maintained — verify alignment when CLAUDE.md changes. -->
