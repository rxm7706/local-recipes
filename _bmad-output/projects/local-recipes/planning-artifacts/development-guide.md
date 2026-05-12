---
doc_type: development-guide
project_name: local-recipes
date: 2026-05-12
source_pin: 'conda-forge-expert v7.7'
---

# Development Guide

How to set up, build, test, debug, and contribute to `local-recipes` locally. This guide is for **humans** operating the system — agents read `project-context.md` and `SKILL.md` instead. Air-gapped / enterprise setup lives in `deployment-guide.md`.

---

## Prerequisites

| Tool | Minimum version | Why |
|---|---|---|
| Pixi | 0.67.2 (pinned in `pixi.toml: requires-pixi`) | Sole environment manager. No conda, no venv. |
| Python | 3.11+ | Pixi-managed. `_bmad/scripts/*.py` require 3.11 for stdlib `tomllib`. |
| Git | any modern | Repo operations. |
| Docker | any modern | Linux builds run inside Docker via `build-locally.py`. Not required for osx/win native. |
| GitHub CLI (`gh`) | 2.92+ | PR submission (`submit_pr`, `prepare_pr`). Pixi-managed. |
| Claude Code (CLI) | latest | Driving the system interactively. Optional for cron / scripted use. |

Don't install pixi globally with a manager that conflicts with the repo's pin. Use the official installer or your distro's pixi package.

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
pixi run verify-env                     # confirms default-env directive + pixi.toml integrity
pixi run bmad-preflight                 # confirms BMAD installer + active project marker
scripts/bmad-switch --current          # should print: local-recipes
```

---

## Project layout (orientation)

See `source-tree-analysis.md` for the full tree. Quick map:

- **`recipes/`** — 1,415 v1 recipes (outputs of the system)
- **`.claude/skills/conda-forge-expert/`** — Part 1: canonical scripts, references, guides, templates
- **`.claude/scripts/conda-forge-expert/`** — Part 1 Tier 2: 34 CLI wrappers
- **`.claude/tools/`** — Part 3: MCP server
- **`.claude/data/conda-forge-expert/`** — runtime state (gitignored)
- **`_bmad/`** — Part 4: BMAD installer
- **`_bmad-output/projects/local-recipes/`** — your BMAD artifacts for this project
- **`docs/`** — human-facing documentation
- **`scripts/`** — repo-level helpers (`bmad-switch`, `load-env.sh`, mirror utilities)

---

## Pixi Tasks Cheatsheet

All tasks under `[feature.local-recipes.tasks.*]` run in the `local-recipes` env by default. To run in another env: `pixi run -e <env> <task>`. To pass args: `pixi run <task> -- <args>`.

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
| `pixi run lint-optimize -- recipes/<pkg>` | Run 17 optimizer lint codes |
| `pixi run lint -- recipes/<pkg>` | conda-smithy recipe-lint (CI fidelity) |
| `pixi run license-check -- recipes/<pkg>` | Validate `license_file` + SPDX identifier |
| `pixi run version-check -- recipes/<pkg>` | Check upstream GitHub for newer tag |
| `pixi run migrate -- recipes/<pkg>` | v0 meta.yaml → v1 recipe.yaml migration |

### Build

| Task | Platforms | Note |
|---|---|---|
| `pixi run recipe-build -- recipes/<pkg>` | host platform | rattler-build directly |
| `pixi run recipe-build-docker -- recipes/<pkg>` | linux-64 in Docker | `build-locally.py` wrapper |
| `pixi run build-local -- recipes/<pkg>` | linux-64 | Same as above but in alternate flow |
| `pixi run build-local-all -- recipes/<pkg>` | linux-64 + linux-aarch64 | Both Linux subarches |
| `pixi run build-local-check -- recipes/<pkg>` | linux-64 | Validate-then-build dry run |
| `pixi run build-local-setup-sdk` | (one-time) | Extracts macOS SDK from `SDKs/` for cross-compile |

### Atlas

| Task | What it runs |
|---|---|
| `pixi run bootstrap-data` | Full atlas refresh + mapping + CVE + vdb |
| `pixi run bootstrap-data -- --fresh` | Hard reset (preserves `cache/parquet/` by default) |
| `pixi run bootstrap-data -- --status` | Print phase_state + TTL eligibility |
| `pixi run atlas-phase -- <ID>` | Run single phase (B, B.5, B.6, C, …, N) |
| `pixi run atlas-phase -- --list` | Enumerate known phases |
| `pixi run atlas-phase -- F --reset-ttl` | NULL TTL column, then run Phase F |
| `pixi run build-cf-atlas` | Phase B-N only (skips mapping + CVE + vdb) |
| `pixi run query-cf-atlas -- <sql>` | Direct SQL query against cf_atlas.db |
| `pixi run stats-cf-atlas` | High-level atlas statistics summary |
| `pixi run detail-cf-atlas -- <conda-name>` | All atlas data for one package |
| `pixi run detail-cf-atlas-vdb -- <conda-name>` | (in vuln-db env) Same with vdb data |
| `pixi run inventory-channel` | Refresh channel inventory cache |

### Atlas-intelligence queries

| Task | What it runs |
|---|---|
| `pixi run staleness-report -- [filters]` | Behind-upstream + unmaintained feedstocks |
| `pixi run feedstock-health -- <name>` | Health summary for one feedstock |
| `pixi run behind-upstream -- [filters]` | Packages with newer upstream versions |
| `pixi run cve-watcher -- [filters]` | New CVEs in your packages |
| `pixi run release-cadence -- <name>` | Release cadence for one package |
| `pixi run version-downloads -- <name>` | Download trend by version |
| `pixi run find-alternative -- <name>` | Similar packages |
| `pixi run adoption-stage -- <name>` | Maturity / popularity tier |
| `pixi run scan-project -- <path>` | Scan manifest / lock file / SBOM / container |

### Submission

| Task | What it runs |
|---|---|
| `pixi run prepare-pr -- <recipe>` | Step 8b: push to fork, NO PR open |
| `pixi run submit-pr -- <recipe>` | Step 9-10: dry-run, then open PR |
| `pixi run submit-pr -- --dry-run <recipe>` | Just dry-run |
| `pixi run autotick -- <recipe>` | Auto-bump version + SHA |
| `pixi run autotick-github -- <recipe>` | GitHub-only autotick |
| `pixi run autotick-npm -- <recipe>` | npm-only autotick |

### Testing

| Task | Scope |
|---|---|
| `pixi run test` | Offline subset (no `network` / `slow` markers) |
| `pixi run test-all` | Full suite (includes network + slow) |
| `pixi run test-coverage` | Coverage report |
| `pixi run test-recipes` | Test all recipes via rattler-build test |

### Repo maintenance

| Task | What it runs |
|---|---|
| `pixi run sync-upstream-conda-forge` | Pull from conda-forge/staged-recipes upstream |
| `pixi run sync-upstream-public-fork` | Pull from user fork |
| `pixi run update-mapping-cache` | Refresh PyPI→conda mapping |
| `pixi run update-cve-db` | Refresh CVE database (use `-e vuln-db` for AppThreat) |
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

# 4. Scan
pixi run scan-vulnerabilities -- recipes/numpy

# 5. Optimize
pixi run lint-optimize -- recipes/numpy
pixi run lint -- recipes/numpy           # also run conda-smithy lint

# 6. Build
pixi run recipe-build-docker -- recipes/numpy
# Watch logs; on failure, see build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log

# 7-8. Inspect outcome
ls build_artifacts/*/*/numpy-*.conda     # success indicator

# (If failed):
pixi run analyze-failure -- build_artifacts/<config>/bld/rattler-build_numpy_<id>/work/conda_build.log

# 8b. Prepare submission branch (no PR)
pixi run prepare-pr -- numpy
# (returns fork_branch_url; inspect in browser)

# 9-10. Submit
pixi run submit-pr -- --dry-run numpy    # verify gh auth, fork, branch state
pixi run submit-pr -- numpy              # open the PR
```

For an interactive AI-driven workflow, use Claude Code with the `conda-forge-expert` skill — it drives the loop with full context and structured actions.

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

```bash
# Active project (must be local-recipes for this repo's primary work):
scripts/bmad-switch --current
scripts/bmad-switch --list
scripts/bmad-switch local-recipes        # set if not already

# Run a BMAD skill via Claude Code:
# In Claude Code prompt: "/bmad-quick-dev"  (interactive)
# Or programmatically: Skill: bmad-quick-dev (via the Skill tool)

# Common BMAD entry points:
# - bmad-create-prd        — new feature PRD
# - bmad-create-architecture — architecture for a planned feature
# - bmad-create-epics-and-stories — break PRD into work
# - bmad-quick-dev         — implement a story spec
# - bmad-document-project  — produce this doc set
# - bmad-retrospective    — closeout retro (mandatory for conda-forge work)
```

See `architecture-bmad-infra.md` for the full skill catalog.

---

## Testing

The skill's test suite (`.claude/skills/conda-forge-expert/tests/`) uses **real fixtures** + pytest markers (`@pytest.mark.network`, `@pytest.mark.slow`). **Do not mock the network** in these tests — this is a project-context anti-pattern explicitly.

```bash
pixi run test                            # offline subset (no markers)
pixi run test-all                        # full suite
pixi run test-coverage                   # coverage report

# Run specific test file:
pixi run test -- -k test_recipe_yaml_schema_header

# Run with markers:
pixi run test -- -m "network and slow"
```

The **meta-tests** under `tests/meta/` enforce invariants:
- `test_recipe_yaml_schema_header.py` — every `recipes/*/recipe.yaml` has the yaml-language-server directive on line 1
- `test_all_scripts_runnable.py` — three-place rule (canonical script + wrapper + pixi task + SCRIPTS list)

If a meta-test fails, **fix the invariant, not the test**.

---

## Debugging Common Issues

### "MCP tool not found"

The server hasn't registered. Check:
1. `.claude/tools/conda_forge_server.py` exists and is executable
2. Pixi env is `local-recipes` (or wherever Claude Code launched)
3. `fastmcp` is installed: `pixi list -e local-recipes fastmcp`
4. Restart Claude Code

### "pixi run X: command not found"

The task doesn't exist or is in a different feature. Check:
```bash
pixi task list                           # all tasks in current env
grep "tasks.X" pixi.toml                  # find which feature owns the task
pixi run -e <env> X -- <args>             # specify env explicitly
```

### "cf_atlas.db missing schema_version"

The DB is older than v17. Run `bootstrap-data --fresh` or `pixi run atlas-phase B` to trigger a clean rebuild + migration. Migrations are additive and idempotent; running them twice is safe.

### "phase_state table missing"

Same root cause as above — DB predates v7.7. `bootstrap-data --fresh` rebuilds; `--reset-cache` also wipes the parquet cache (rarely needed).

### "Phase H hangs"

Almost certainly the UX bug, not a real hang. Phase H pypi-json fan-out with 770k rows would silently work for 5-11 minutes before printing the first progress line. v7.7.0 added a 60s heartbeat. If you're on an older skill version, just wait.

To skip the wait entirely on cold start: `PHASE_H_SOURCE=cf-graph pixi run atlas-phase H` (uses local cf-graph tarball; 30 seconds total).

### "JFROG_API_KEY leaks to github.com"

Don't export `JFROG_API_KEY` in the same shell that runs `submit_pr` / `prepare_pr` / `generate_recipe_from_pypi`. See `deployment-guide.md` § Cross-host credential leak for mitigation patterns.

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
1. Add `@mcp.tool()` decorator + thin wrapper body to `conda_forge_server.py`
2. Ensure the wrapped Tier 1 script honors the `--json` contract
3. Add `mcp_call.py` integration test (currently sparse — adding one is +ev)

For changes to **BMAD infra**:
1. Skill additions live in `.claude/skills/<name>/`
2. Per-skill customization in `_bmad/custom/<name>.toml`
3. Don't edit `_bmad/config.toml` directly — it's regenerated

For changes that span multiple parts:
1. Plan with `bmad-create-architecture` or `bmad-quick-dev`
2. Use `bmad-checkpoint-preview` to walk a reviewer through the diff
3. Run `bmad-retrospective` at closeout if it touched conda-forge work

---

## CI Pipeline

`azure-pipelines.yml` is the primary CI. It runs:
1. Lint (`conda-smithy recipe-lint`) on changed recipes
2. Build (`rattler-build`) on changed recipes
3. Tests (`pixi run test`) on changes to `.claude/skills/conda-forge-expert/`

Per-platform CI (linux-64 + linux-aarch64 + osx-64 + osx-arm64 + win-64) runs via Azure DevOps. The `.azure-pipelines/` directory has the templates.

GitHub Actions (`.github/workflows/`) handles:
- PyPI mapping sync (`sync-pypi-mappings.yml`) — weekly + on `custom.yaml` change
- Issue templates

---

## Where to look when stuck

| Symptom | First file to read |
|---|---|
| Recipe authoring question | `.claude/skills/conda-forge-expert/SKILL.md` |
| MCP tool signature | `.claude/skills/conda-forge-expert/reference/mcp-tools.md` |
| Build failure pattern | `.claude/skills/conda-forge-expert/guides/ci-troubleshooting.md` |
| Cross-compile question | `.claude/skills/conda-forge-expert/guides/cross-compilation.md` |
| Atlas operations | `.claude/skills/conda-forge-expert/guides/atlas-operations.md` |
| Air-gap setup | `docs/enterprise-deployment.md` (or `deployment-guide.md` in this set) |
| Recipe authoring gotchas | `.claude/skills/conda-forge-expert/SKILL.md` § Recipe Authoring Gotchas (G1-G6) |
| BMAD multi-project | `_bmad-output/PROJECTS.md` |
| Project-specific rules | `_bmad-output/projects/local-recipes/project-context.md` |
| Recent changes | `.claude/skills/conda-forge-expert/CHANGELOG.md` TL;DR |
