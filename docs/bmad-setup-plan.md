# BMAD Brownfield Setup Plan — `local-recipes`

## Current State Assessment

| Item | Status |
|---|---|
| BMAD documentation | ✅ `.claude/docs/bmad-method-llms-full.txt` |
| `bmad-method` CLI (v6.6.0) | ✅ Pixi-managed in `local-recipes` env (bundles Node.js 20 + vendored deps) |
| `CLAUDE.md` with project context | ✅ Detailed and current |
| `.claude/` skills/tools/settings | ✅ conda-forge MCP server + skill library |
| `docs/` directory | ✅ Exists but empty |
| `_bmad/` (BMAD config) | ❌ Missing |
| `_bmad-output/` (BMAD artifacts) | ❌ Missing |
| Project context file | ❌ Missing |

---

## Phase 0 — Prerequisites

**0.1 — Verify the pixi env provides `bmad-method`** (the `local-recipes` env ships `bmad-method` 6.6.0 with Node.js 20 + vendored `node_modules` as a conda dependency — no separate Node install or live npm registry required)
```bash
pixi list -e local-recipes | grep -E '^(bmad-method|nodejs)\s'
pixi run -e local-recipes bmad-method --version   # should print 6.6.0+
```
If missing: `pixi install -e local-recipes`.

**0.2 — Verify Git state is clean**
```bash
git status
git stash  # if needed
```
BMAD installation touches `.gitignore` and creates new directories — start clean.

---

## Phase 1 — Install BMAD

**1.1 — Run the installer**

From the project root, using the pixi-managed CLI (functionally identical to `npx bmad-method install`, but offline-capable and version-pinned via the lockfile):
```bash
cd /home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes
pixi run -e local-recipes bmad-method install
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

> **As of Phase 8 (Multi-Project Layout):** the project context now lives at `_bmad-output/projects/<slug>/project-context.md`, not `_bmad-output/project-context.md`. Set the active project before running the generator: `scripts/bmad-switch <slug>` (then run the skill).

```bash
scripts/bmad-switch local-recipes   # or another project slug
bmad-generate-project-context
```

This scans the repo and produces `_bmad-output/projects/<slug>/project-context.md`. Review and extend it.

**2.2 — Manually extend `project-context.md`**

After generation, open `_bmad-output/projects/<slug>/project-context.md` and add the following conda-forge-specific sections that the scanner cannot infer (this section applies to the `local-recipes` project — other projects will have their own conventions):

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
| Update project conventions | Edit `_bmad-output/projects/<slug>/project-context.md` |
| Review build patterns | Consult `docs/mcp-server-architecture.md` |

---

## Phase 8 — Multi-Project Layout (✅ Completed 2026-05-01)

This repository hosts **multiple BMAD projects under a single installation**. Each project has its own `_bmad-output/projects/<slug>/` subtree containing planning artifacts, implementation artifacts, project context, and project-scoped BMAD config overrides. The motivation: the original single shared `_bmad-output/` mixed conda-recipes work with a separate Presenton AI deck-generation repackaging effort, making cross-project tracking unsustainable.

### 8.1 — Layout

```
_bmad-output/
├── PROJECTS.md                                    # index + adding-a-project guide
└── projects/
    ├── local-recipes/                             # primary project — conda recipes
    │   ├── .bmad-config.toml                      # project team config (committed)
    │   ├── .bmad-config.user.toml                 # project user config (gitignored, optional)
    │   ├── project-context.md                     # conda-forge conventions, MCP lifecycle, Python policy
    │   ├── planning-artifacts/                    # PRDs, briefs, ADRs (committed)
    │   └── implementation-artifacts/              # sprint status, stories, reviews (gitignored)
    └── presenton-pixi-image/                      # secondary project — Presenton air-gapped repackaging
        ├── .bmad-config.toml
        ├── planning-artifacts/
        │   └── prd.md                             # PRD (step 3 of 13 complete)
        └── implementation-artifacts/
```

### 8.2 — Six-Layer Config Resolver

`_bmad/scripts/resolve_config.py` was extended from four to six TOML merge layers:

| Layer | Path                                                           | Scope                                  |
|-------|----------------------------------------------------------------|----------------------------------------|
| 1     | `_bmad/config.toml`                                            | Installer team (regenerated)           |
| 2     | `_bmad/config.user.toml`                                       | Installer user (regenerated)           |
| 3     | `_bmad/custom/config.toml`                                     | **Global custom team, all projects**   |
| 4     | `_bmad/custom/config.user.toml`                                | Global custom user, all projects       |
| 5     | `_bmad-output/projects/<slug>/.bmad-config.toml`               | **Project team, active project only**  |
| 6     | `_bmad-output/projects/<slug>/.bmad-config.user.toml`          | Project user, active project only      |

Higher-numbered layers override lower-numbered layers. Layers 5 and 6 only load when an active project resolves.

### 8.3 — Active-Project Resolution

Three mechanisms, in priority order (highest first):

1. **Per-call CLI flag:** `python3 _bmad/scripts/resolve_config.py --project <slug> ...`
2. **Environment variable:** `BMAD_ACTIVE_PROJECT=<slug>` (per-shell or per-subprocess scope)
3. **Marker file:** `_bmad/custom/.active-project` (gitignored, single-line slug, managed by `scripts/bmad-switch`)
4. None — only the four global layers resolve; skills fall back to the global default `output_folder`.

The per-call flag (Mitigation 1, see Phase 8.6) closes the "single active project at a time" limitation for cross-project operations without disturbing global state.

### 8.4 — `scripts/bmad-switch` Helper

```bash
scripts/bmad-switch --list                  # list known projects (annotates active with *)
scripts/bmad-switch --current               # print active project slug
scripts/bmad-switch <slug>                  # set active project (validates dir exists)
scripts/bmad-switch --clear                 # remove marker (no active project)
```

The script writes `_bmad/custom/.active-project` with the slug. It refuses to switch to a project whose directory does not exist under `_bmad-output/projects/`.

### 8.5 — Adding a New Project

```bash
mkdir -p _bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}
cat > _bmad-output/projects/<slug>/.bmad-config.toml <<'EOF'
output_folder = "_bmad-output/projects/<slug>"

[project]
slug = "<slug>"
description = "..."
status = "active"
EOF
scripts/bmad-switch <slug>
# (optionally) bmad-generate-project-context  # to seed project-context.md
```

Then add a row to `_bmad-output/PROJECTS.md` § "Projects".

### 8.6 — Cross-Project Operations

- **Read another project's artifacts** without switching — open the file directly at `_bmad-output/projects/<slug>/...`. No resolver state change needed.
- **Run a skill against a non-active project** for one-off writes — set `BMAD_ACTIVE_PROJECT=<slug>` for the subprocess, or pass `--project <slug>` directly to `resolve_config.py`. The marker file is left untouched; only that invocation sees the override.
- **Mitigation 1** (the per-call `--project` flag on the resolver) is implemented. **Mitigations 2** (per-skill `--project` argument convention) and **3** (namespaced multi-config merge for simultaneous multi-project ops) are deferred — build only if needed.

### 8.7 — Migration Performed on 2026-05-01

| From | To |
|---|---|
| `_bmad-output/planning-artifacts/prd.md` | `_bmad-output/projects/presenton-pixi-image/planning-artifacts/prd.md` |
| `_bmad-output/implementation-artifacts/deferred-work.md` | `_bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md` |
| `_bmad-output/implementation-artifacts/spec-cursor-sdk-local-recipe.md` | `_bmad-output/projects/local-recipes/implementation-artifacts/spec-cursor-sdk-local-recipe.md` |
| `_bmad-output/project-context.md` | `_bmad-output/projects/local-recipes/project-context.md` |

Old top-level `_bmad-output/planning-artifacts/` and `_bmad-output/implementation-artifacts/` directories removed.

`.gitignore` updated:
- `_bmad/custom/.active-project` (per-developer marker)
- `_bmad-output/projects/*/implementation-artifacts/` (per-project, per-developer scratch)
- `_bmad-output/projects/*/.bmad-config.user.toml` (per-developer per-project overrides)

Per-project `planning-artifacts/` remain **committed** as team artifacts.

---

## Summary of Files to Create/Modify

| File | Action |
|---|---|
| `_bmad/` | Created by installer (Phase 1) |
| `_bmad-output/` | Created by installer (Phase 1) |
| `_bmad-output/projects/<slug>/project-context.md` | Generated then extended manually per project (Phase 2 + Phase 8) |
| `_bmad-output/projects/<slug>/.bmad-config.toml` | Per-project committed config (Phase 8) |
| `_bmad-output/PROJECTS.md` | Project index + add-a-project guide (Phase 8) |
| `_bmad/scripts/resolve_config.py` | Extended to 6-layer + per-call `--project` flag (Phase 8) |
| `scripts/bmad-switch` | Active-project switcher script (Phase 8) |
| `docs/mcp-server-architecture.md` | Provides the BMAD agent with architectural context (Completed) |
| `docs/developer-guide.md` | Provides local build and test instructions (Completed) |
| `_bmad/custom/bmad-agent-pm.toml` | Create manually (Phase 4) |
| `_bmad/custom/bmad-agent-pm.user.toml` | Create + add to `.gitignore` (Phase 4) |
| `.gitignore` | Extended with BMAD multi-project patterns (Phases 5 + 8) |
| `CLAUDE.md` § "Multi-Project Pattern" | Multi-project layout reference (Phase 8) |
| `CHANGELOG.md` | Tracks BMAD multi-project introduction and other repo-level changes |
