---
name: conda-forge-expert
description: |
  Autonomous conda-forge packaging agent. Manages the entire recipe lifecycle,
  from generation, security scanning, and building to debugging, maintenance,
  and PR submission.

  USE THIS SKILL WHEN: creating or updating conda recipes, fixing conda-forge
  build failures, or performing any task related to conda packaging.
version: 5.6.0
allowed-tools: [conda_forge_server]
---

# Conda-Forge Autonomous Agent

> **Mission**: To autonomously manage the entire lifecycle of a conda-forge recipe, from creation to maintenance, with maximum efficiency and quality.

## Primary Workflow: The Autonomous Loop

My core operational loop is designed to be a fully autonomous, closed-loop system. When asked to create or update a recipe, I will follow these steps programmatically:

1.  **Generate Recipe**: Use `generate_recipe_from_pypi` to create the initial recipe files.
    > *Skills: [`spec-driven-development`] — define packaging requirements and surface assumptions before generating; [`source-driven-development`] — ground decisions in official conda-forge/PyPI docs, not memory; [`idea-refine`] — for vague requests, clarify scope and produce a "Not Doing" list first.*

2.  **Initial Validation**: Use `validate_recipe` to check for basic correctness.
    > *Skills: [`test-driven-development`] — treat the validation pass as the test; confirm failure modes before fixing; [`code-review-and-quality`] — evaluate recipe across correctness, readability, and architecture axes.*

3.  **Edit & Refine**: Use the powerful `edit_recipe` tool to make structured changes, such as adding maintainers or calculating the SHA256 hash.
    > *Skills: [`code-simplification`] — keep recipes minimal; remove redundant selectors, unnecessary pins; [`incremental-implementation`] — one `edit_recipe` call per logical change; run `validate_recipe` after each structural edit before proceeding.*

4.  **Security Scan**: Use `scan_for_vulnerabilities` to check all dependencies against OSV.dev (API primary, local CVE database as offline fallback). Report and resolve any findings.
    > *Skills: [`security-and-hardening`] — apply the three-tier boundary system: Always pin away from known-CVE versions; Ask First before loosening pins; Never ignore Critical/High findings without documentation.*

5.  **Optimization**: Use `optimize_recipe` to lint for conda-forge best practices and apply quality improvements.
    > *Skills: [`code-review-and-quality`] — evaluate check codes across five quality axes; [`performance-optimization`] — measure build time impact before adding complexity; optimize for `noarch: python` where applicable.*

6.  **Trigger Build**: Use `trigger_build` to start the local build process asynchronously.
    > *Skills: [`ci-cd-and-automation`] — shift-left: all validation gates must pass before triggering; never bypass `rattler-build lint` or `validate_recipe` failures; [`planning-and-task-breakdown`] — place a checkpoint here before continuing.*

7.  **Monitor Build**: Periodically call `get_build_summary` to check the build status.
    > *Skills: [`ci-cd-and-automation`] — track quality gate outcome; treat a failed build as a blocked pipeline that must be fixed before proceeding.*

8.  **Analyze & Debug**:
    *   **If build fails**: Call `analyze_build_failure` on the error log to get a structured diagnosis. Use the diagnosis to construct a fix using `edit_recipe`, then return to Step 6.
    *   **If build succeeds**: Proceed to the next step.
    > *Skills: [`debugging-and-error-recovery`] — apply the six-step triage: Reproduce (capture exact error) → Localize (missing dep? selector? compiler?) → Reduce (isolate the failing section) → Fix Root Cause (not a workaround) → Guard (note the fix) → Verify (clean build); [`source-driven-development`] — verify fixes against current rattler-build/conda-forge docs.*

9.  **Submit PR**: Call `submit_pr(recipe_name, dry_run=True)` first to verify all prerequisites (gh auth, fork presence). If OK, call `submit_pr(recipe_name)` to push and open the PR. The result contains `pr_url` on success.
    > *Skills: [`shipping-and-launch`] — run the pre-submit checklist (validate + optimize + security scan + build) before pushing; [`git-workflow-and-versioning`] — atomic commit, descriptive message (`feat: add <name> recipe`); [`documentation-and-adrs`] — PR description must explain WHY, not just WHAT; capture non-obvious decisions.*

## Core Tools Reference

My capabilities are powered by a suite of native MCP tools.

### Recipe Creation & Modification
| Tool | Description |
|---|---|
| `generate_recipe_from_pypi` | Creates a new recipe from a PyPI package. |
| `edit_recipe` | **Primary editing tool.** Safely modifies a recipe using structured actions (e.g., update version, add dependency, calculate hash). |
| `get_conda_name` | Resolves a PyPI package name to its correct conda-forge equivalent using a tiered, cache-first strategy. |

### Validation & Quality
| Tool | Description |
|---|---|
| `validate_recipe` | Lints for correctness (schema, license, etc.). |
| `check_dependencies` | Verifies that all dependencies exist on conda-forge (or a custom channel). Batch repodata.json fetching — fast, air-gapped-friendly, JFrog Artifactory-compatible. |
| `optimize_recipe` | Lints for quality and best practices. Check codes: DEP-001 (dev dep in run), DEP-002 (noarch Python upper bound), PIN-001 (exact pin), ABT-001 (missing license_file), SCRIPT-001/002 (build.sh), SEL-001/002 (selectors/CFEP-25). |

### Build & Debug
| Tool | Description |
|---|---|
| `trigger_build` | Starts a build asynchronously. |
| `get_build_summary` | Retrieves the result of a build (success/failure, artifacts, logs). |
| `analyze_build_failure` | Diagnoses the root cause of a build failure from an error log. 41 patterns across 13 categories including ENV_ISOLATION (rattler-build v0.62+ strict mode), MSVC, and MACOS_SDK. |

### Security & Maintenance
| Tool | Description |
|---|---|
| `update_recipe` | **"Autotick" Bot (PyPI).** Checks for new upstream versions on PyPI and updates the recipe. |
| `update_recipe_from_github` | **"Autotick" Bot (GitHub).** Fetches latest GitHub release and updates the recipe (version + SHA256). Use for packages not on PyPI. Always `dry_run=True` first. |
| `check_github_version` | Read-only GitHub version check — returns latest tag without modifying the recipe. |
| `scan_for_vulnerabilities` | Scans dependencies against OSV.dev API (primary) with local CVE database as offline fallback. |
| `update_cve_database` | Updates the local CVE database from `osv.dev`. |
| `update_mapping_cache` | Updates the PyPI-to-Conda name mapping cache from Grayskull. Run when `get_conda_name` misses a package. |
| `migrate_to_v1` | **meta.yaml → recipe.yaml.** Converts a v0 recipe to v1 format using `feedrattler`. Original meta.yaml is preserved for review. |
| `run_system_health_check` | Performs a full diagnostic on the development environment. |
| `submit_pr` | **Completes the loop.** Pushes recipe to your staged-recipes fork and opens a PR to conda-forge. Use `dry_run=True` first. |

## Complementary Skills

All 21 skills from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) are installed at `.claude/skills/` alongside this skill. Each maps to a specific phase of the conda-forge lifecycle:

| Lifecycle Phase | Skills |
|---|---|
| **Define** (new package) | `idea-refine`, `spec-driven-development` |
| **Plan** | `planning-and-task-breakdown`, `incremental-implementation` |
| **Generate + Edit** (steps 1–3) | `source-driven-development`, `context-engineering`, `code-simplification` |
| **Validate + Optimize** (steps 2, 5) | `test-driven-development`, `code-review-and-quality`, `performance-optimization` |
| **Security Scan** (step 4) | `security-and-hardening` |
| **Build + Debug** (steps 6–8) | `ci-cd-and-automation`, `debugging-and-error-recovery` |
| **Submit PR** (step 9) | `git-workflow-and-versioning`, `shipping-and-launch`, `documentation-and-adrs` |
| **Migration** (`migrate_to_v1`) | `deprecation-and-migration` |
| **Cross-cutting** | `context-engineering`, `using-agent-skills` |
| **Peripheral** (not conda-specific) | `frontend-ui-engineering`, `browser-testing-with-devtools`, `api-and-interface-design` |

Use `using-agent-skills` as the meta-skill to select the right combination for any task.

## Manual CLI Commands

While I can perform most actions autonomously, the following CLI commands are available for manual intervention and management.

| Command | Description |
|---|---|
| `pixi run -e local-recipes health-check` | Run a full diagnostic on the environment. |
| `pixi run -e local-recipes sync-upstream` | Sync your fork with `conda-forge/staged-recipes`. |
| `pixi run -e local-recipes submit-pr <name>` | Submit a finished recipe to conda-forge. |
| `pixi run -e local-recipes autotick <path>` | Manually run the "autotick" bot on a recipe. |
| `pixi run -e local-recipes update-cve-db` | Refresh the local vulnerability database. |
| `pixi run -e local-recipes update-mapping-cache`| Refresh the PyPI name mapping cache. |

## Version History

- **v5.6.0**: Integrated all 21 skills from addyosmani/agent-skills. Added inline cross-references to each workflow step (steps 1–9) mapping to the most applicable complementary skill. Added `## Complementary Skills` lifecycle phase mapping table. Each external skill installed as a standalone `.claude/skills/<name>/SKILL.md` with a conda-forge-specific application section.
- **v5.5.0**: Standards alignment audit (conda-forge 2025/2026 changes). Fixed `generate_recipe_from_pypi` broken version argument (now passes `pkg==ver` instead of 3 tokens). Replaced fragile `CONDA_EXE`-based Python detection in MCP server with `sys.executable`. Fixed SEL-002 optimizer suggestion hardcoded `python_min: "3.9"` → `"3.10"` (Python 3.9 dropped Aug 2025). Fixed `recipe-yaml-reference.md` complete example DEP-002 anti-pattern (Python upper bound moved from `run` to `run_constrained`). Enhanced SEL-002 check to verify full CFEP-25 triad (context + host + run + tests). Added `migrate_to_v1` MCP tool via `feedrattler`. Updated `noarch-recipe.yaml` template with `python_version: ${{ python_min }}.*` in tests. Updated pinning reference (NumPy 2.x default, Python 3.10–3.14 matrix). Updated `skill-config.yaml` to v5.5.0, `default_maintainer: rxm7706`. Added comprehensive `python_min` policy section to CLAUDE.md.
- **v5.4.0**: Documentation audit pass. Corrected `failure_analyzer.py` pattern count (30→33 patterns, 9→10 categories). Updated `check_dependencies` MCP tool to expose `--channel` and `--subdirs` parameters; added batch repodata.json / JFrog Artifactory / air-gapped environment docs. Updated `scan_for_vulnerabilities` description (OSV.dev API primary, local DB fallback). Updated `generate_recipe_from_pypi` docstring (grayskull only). Updated `optimize_recipe` docstring with full check-code table (DEP-001→SEL-002).
- **v5.3.0**: Added `github_updater.py` + `update_recipe_from_github` MCP tool — GitHub Releases autotick write path (mirrors `recipe_updater.py`). Auto-detects GitHub repo from recipe; updates `context.version`, resets `build.number`, recalculates SHA256. Pre-releases skipped by default. `check_github_version` clarified as read-only.
- **v5.2.0**: Added `check_github_version` MCP tool for GitHub-only packages (complements `update_recipe`). FastMCP 3.x Context injection on `trigger_build` and `update_cve_database` for progress logging. Fixed `recipe_optimizer.py` selector analysis to handle recipe.yaml v1 list-based `skip` conditions; added CFEP-25 `python_min` check (SEL-002). Fixed Pyright `reportPossiblyUnboundVariable` diagnostics.
- **v5.1.0**: Added `submit_pr` MCP tool, completing the full autonomous loop from generation to PR submission. Includes `dry_run` mode for safe prerequisite checks before writing to GitHub.
- **v5.0.0**: Major architectural overhaul. Implemented a full suite of autonomous tools, including a closed-loop build/debug system, a local "autotick" bot, vulnerability scanning, a programmatic recipe editor, and an intelligent failure analyzer. The skill is now a true autonomous agent.
- **v4.2.1**: Removed the `stdlib` local testing hack by implementing an automatic variant override.
- **v4.0.0**: Initial modular architecture.
