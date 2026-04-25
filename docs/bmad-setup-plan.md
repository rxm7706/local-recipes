# BMAD Brownfield Setup Plan — `local-recipes`

## Current State Assessment

| Item | Status |
|---|---|
| BMAD documentation | ✅ `.claude/docs/bmad-method-llms-full.txt` |
| `CLAUDE.md` with project context | ✅ Detailed and current |
| `.claude/` skills/tools/settings | ✅ conda-forge MCP server + skill library |
| `docs/` directory | ✅ Exists but empty |
| `_bmad/` (BMAD config) | ❌ Missing |
| `_bmad-output/` (BMAD artifacts) | ❌ Missing |
| Project context file | ❌ Missing |

---

## Phase 0 — Prerequisites

**0.1 — Verify Node.js is available** (needed for `npx bmad-method install`)
```bash
node --version   # need v18+
npx --version
```
If missing: `pixi global install nodejs` or install via your system package manager.

**0.2 — Verify Git state is clean**
```bash
git status
git stash  # if needed
```
BMAD installation touches `.gitignore` and creates new directories — start clean.

---

## Phase 1 — Install BMAD

**1.1 — Run the installer**

From the project root:
```bash
cd /home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes
npx bmad-method install
```

At the interactive prompts, choose:

| Prompt | Selection | Reason |
|---|---|---|
| AI tool | **Claude Code** | Your environment |
| Primary module | **BMad Method** | Full planning + implementation lifecycle |
| Additional modules | None initially | Add later if needed |
| Project type | **Brownfield** | Existing project |

This creates:
- `_bmad/` — BMAD configuration directory
- `_bmad-output/` — Artifact output directory
- Updates `.gitignore` to exclude personal config and output files

**1.2 — Verify installation**
```bash
ls _bmad/
ls _bmad-output/
```

---

## Phase 2 — Generate Project Context

This is the most critical step for brownfield. BMAD agents need a `project-context.md` to follow your established conventions automatically.

**2.1 — Run the context generator**
```bash
bmad-generate-project-context
```

This scans the repo and produces `_bmad-output/project-context.md`. Review and extend it.

**2.2 — Manually extend `project-context.md`**

After generation, open `_bmad-output/project-context.md` and add the following conda-forge-specific sections that the scanner cannot infer:

```markdown
## Recipe Format
- Standard: recipe.yaml v1 (schema_version: 1), NOT meta.yaml
- Schema validation: rattler-build lint + custom validate_recipe MCP tool
- Context variables use ${{ }} Jinja2-style substitution

## Python Version Policy
- Minimum: python_min = "3.10" (conda-forge floor, August 2025)
- noarch: python packages MUST use CFEP-25 triad (host/run/test pins)
- Compiled packages: python >=3.10 without variable

## Critical Build Rule
- ALL recipes using a compiler (c, cxx, rust) MUST include ${{ stdlib("c") }}

## Autonomous Recipe Lifecycle (MCP Tools)
- generate_recipe_from_pypi → validate_recipe → edit_recipe → scan_for_vulnerabilities
  → optimize_recipe → trigger_build → get_build_summary → analyze_build_failure → submit_pr

## Security
- Vulnerability scanning: scan_for_vulnerabilities() against OSV.dev
- Local CVE database: update_cve_database(force=True) to refresh

## Build Environment
- Build system: pixi + rattler-build (NOT conda-build)
- Build targets: linux-64 (default), osx-arm64, osx-64, win-64
- Builds run inside Docker on Linux
- Config: conda_build_config.yaml + .ci_support/

## Dependency Resolution
- check_dependencies() verifies against conda-forge channel repodata.json
- get_conda_name() resolves PyPI names to conda-forge equivalents
- When a package version is unavailable: loosen pin to available version + TODO comment

## Enterprise Constraints (Air-Gapped & JFrog Artifactory)
- All workflows and FastMCP tools must support operation in an air-gapped environment.
- External tools and packages should be bootstrapped from an internal JFrog Artifactory.
- Default channels must be configured to point to internal mirrors (e.g., via `.pixi/config.toml`).

## PR Submission
- Always submit_pr(recipe_name, dry_run=True) BEFORE the real submit
- Target: conda-forge/staged-recipes fork
```

---

## Phase 3 — Populate `docs/` (✅ Completed)

The `docs/` directory has been populated with the necessary foundation:

- `docs/mcp-server-architecture.md` — Documents the high-level system architecture, how the FastMCP server integrates with Claude, and the recipe lifecycle.
- `docs/developer-guide.md` — Distilled developer guidelines and local testing instructions.

---

## Phase 4 — Configure BMAD for Your Use Cases

**4.1 — Decide your primary BMAD tracks**

For this project, two tracks make sense:

| Track | When to Use |
|---|---|
| `bmad-quick-dev` | Single recipe submissions, version bumps, minor fixes |
| Full BMAD Method | Major infrastructure changes (new MCP tools, new CI pipeline, pixi task additions) |

**4.2 — Create team customization**

Create `_bmad/custom/bmad-agent-pm.toml` to tune the PM agent for your domain:

```toml
[agent]
domain = "conda-forge packaging"
output_format = "recipe-focused stories"

[story_template]
# Each story should map to a single recipe operation
# e.g., "Add package X to conda-forge" or "Update package Y from v1 to v2"
```

**4.3 — Personal preferences (gitignored)**

Create `_bmad/custom/bmad-agent-pm.user.toml` for local overrides (add to `.gitignore`):
```toml
[preferences]
maintainer_github = "rxm7706"
```

---

## Phase 5 — Update `.gitignore`

The BMAD installer likely adds entries, but verify these are covered:

```gitignore
# BMAD personal config and output
_bmad/custom/*.user.toml
_bmad-output/implementation-artifacts/
_bmad-output/sprint-status.yaml

# Keep committed (team artifacts):
# _bmad-output/project-context.md
# _bmad-output/PRD.md
# _bmad-output/architecture.md
# docs/
```

---

## Phase 6 — First BMAD Session

**6.1 — Verify the setup**
```
bmad-help
```
BMAD will inspect your project and confirm it's correctly configured.

**6.2 — Run your first brownfield task**

Try a single recipe submission as a test of the integrated workflow:
```
bmad-quick-dev Add recipe for package "requests-cache" to conda-forge
```

BMAD will:
1. Consult `project-context.md` for your conventions
2. Use the recipe lifecycle steps from your context
3. Generate a story → implement it using your MCP tools → review

---

## Phase 7 — Ongoing Maintenance

| Task | BMAD Command |
|---|---|
| New recipe request | `bmad-quick-dev Add recipe for <package>` |
| Major infra change | Full BMAD Method: PM → Architect → stories |
| Update project conventions | Edit `_bmad-output/project-context.md` |
| Review build patterns | Consult `docs/architecture.md` |

---

## Summary of Files to Create/Modify

| File | Action |
|---|---|
| `_bmad/` | Created by installer (Phase 1) |
| `_bmad-output/` | Created by installer (Phase 1) |
| `_bmad-output/project-context.md` | Generated then extended manually (Phase 2) |
| `docs/mcp-server-architecture.md` | Provides the BMAD agent with architectural context (Completed) |
| `docs/developer-guide.md` | Provides local build and test instructions (Completed) |
| `_bmad/custom/bmad-agent-pm.toml` | Create manually (Phase 4) |
| `_bmad/custom/bmad-agent-pm.user.toml` | Create + add to `.gitignore` (Phase 4) |
| `.gitignore` | Extend with BMAD patterns (Phase 5) |
