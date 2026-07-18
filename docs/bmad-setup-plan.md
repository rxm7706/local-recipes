# BMAD Setup Plan — `local-recipes` (greenfield + brownfield, multi-project, unattended loop)

> **Scope.** This started as a brownfield install guide (Phases 0–8). It now also covers
> **greenfield** projects (new subtrees with no existing code) and the **unattended
> `bmad-loop` + `bmad-dev-auto` workflow** (Phases 9–10). Everything is **multi-project**:
> one BMAD + one loop install drives every project under `_bmad-output/projects/<slug>/`.
>
> **Read this if you're:** adding a new project (greenfield *or* brownfield) to the repo, or
> setting up autonomous story execution so effort runs through the real orchestrator (with
> `.bmad-loop/runs/<id>/` journals) instead of an ad-hoc in-session agent loop.

## Current State Assessment (2026-07-18)

| Item | Status |
|---|---|
| BMAD documentation | ✅ `.claude/docs/bmad-method-llms-full.txt` |
| `bmad-method` CLI | ✅ **v6.10.0+** — pixi-managed (conda-forge) in `local-recipes`; gains `bmad-dev-auto` (was 6.6.0 npx-era) |
| `bmad-loop` orchestrator | ✅ **v0.8.1+** in `pixi.toml` (`[pypi-dependencies]`, git-pinned) — env-resident, run via `pixi run -e local-recipes bmad-loop …` |
| `tmux` (loop spawns agent sessions in it) | ✅ v3.7b+ in the **linux-64 / osx-arm64** target tables (no win-64 — loop is Linux/macOS; Windows via WSL) |
| `uv` (alt. install path for the tool) | ✅ v0.11.29+ (this repo prefers the pixi provisioning; uv-tool is the upstream default) |
| Loop + dev-auto skills | ✅ `.claude/skills/{bmad-dev-auto, bmad-loop-setup, bmad-loop-resolve, bmad-loop-sweep}` |
| `.bmad-loop/` config | ⚠️ `policy.toml` + `bmad_loop_hook.py` exist, **but `.bmad-loop/runs/` was never created** — no `bmad-loop init` / no real run yet (see Phase 9) |
| `_bmad/` + `_bmad-output/` | ✅ Installed; **6-layer resolver + multi-project layout** (Phase 8) |
| Multi-project switcher | ✅ `scripts/bmad-switch <slug>` + `.active-project` marker + `_bmad-output/PROJECTS.md` |
| `CLAUDE.md` project context | ✅ Detailed + current (incl. the two-layer symlink+marker switch warning) |
| **Blocker for atlas loop runs** | ❌ `pyforge-atlas` env absent from `pixi.lock` (DW-A1) → the loop's `--frozen` VERIFY can't materialize it. Fix = workstation re-lock (Phase 9.6). |

---

## Greenfield vs Brownfield — pick the track (do this first)

The BMAD **install** (Phases 0–1) is one-time and shared; you do it once for the whole repo.
Per **project** you then pick a track — it changes only the **planning chain** (Phase 10) and
the **project-context** emphasis (Phase 2), never the loop mechanics (Phase 9, identical for both).

| | **Brownfield** (existing code) | **Greenfield** (new subtree) |
|---|---|---|
| Examples in this repo | `local-recipes` (the recipes), `pyforge-atlas` (migrating the legacy cf_atlas) | a brand-new package with no prior implementation |
| Critical first step | **`bmad-document-project`** → living architecture/source-tree docs the agents must respect | **`bmad-prd` + `bmad-architecture`** → design the system from the spec, no legacy to honor |
| `project-context.md` emphasis | *Preserve* conventions, invariants, existing gotchas (Phase 2.2) | *Establish* conventions + the target stack |
| Planning chain | document → PRD/correct-course → epics/stories (Phase 10.B) | PRD → architecture → epics/stories → readiness (Phase 10.G) |
| Spec-first (`docs/specs/`) | Same for both — a Tier-1 intake spec at `status: ready` before code (repo `AGENTS.md`) |
| Loop execution | Same for both — Phase 9 |

> **The install is project-type-agnostic.** The installer's one-time "Project type: Brownfield"
> prompt (Phase 1) only seeds a default; each project chooses its own track at planning time.
> A repo that hosts both (this one does) installs once and runs both tracks side by side.

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

## Phase 9 — Unattended execution: `bmad-loop` + `bmad-dev-auto` (multi-project)

This is the phase the earlier plan was missing. It turns the manual planning chain into an
**autonomous, journaled** story-execution loop. It is **identical for greenfield and
brownfield** — the only per-project difference is *what* it runs (the verify gate + story feed).

### 9.0 — Mental model (two distinct tools)

| Tool | What it is | Scope |
|---|---|---|
| **`bmad-dev-auto`** | The upstream *unattended DEV primitive* — one skill: clarify-route → plan → implement → **inline review**. Spec-driven ("Ready for Development" criteria). | Runs **one story** |
| **`bmad-loop`** | The deterministic Python *orchestrator*. Spawns fresh **tmux** CLI sessions, each running `bmad-dev-auto` for the DEV pass, then re-invoking it on the `done` spec for a REVIEW pass; runs the **VERIFY** gates; **COMMITs** (squash, branch-per-story worktree). Resumable state machine; journals every run to `.bmad-loop/runs/<id>/`. | Drives the **whole sprint feed**, story by story |

The whole point: replace the ad-hoc *in-session* agent loop (what the pyforge-atlas effort
actually used — no journals) with a durable, gate-enforced orchestrator that **does** leave
`.bmad-loop/runs/<id>/` journals.

### 9.1 — Verify provisioning (already pinned in this repo)

```bash
pixi run -e local-recipes bmad-loop --version    # >= 0.8.1  (pixi-provisioned, git-pinned)
pixi run -e local-recipes tmux -V                # >= 3.7b   (linux-64 / osx-arm64 only)
pixi run -e local-recipes bmad-method --version  # >= 6.10.0 (gains bmad-dev-auto)
```
**Always invoke the loop through pixi** (`pixi run -e local-recipes bmad-loop …`) — it is
env-resident. Do **not** `uv tool install bmad-loop` (the upstream default in the
`bmad-loop-setup` skill): a uv-managed copy would shadow the lockfile-pinned one. The
`bmad-loop-setup` skill is still the right tool for **config/skill** setup — just skip its
"Install the Orchestrator Tool" step on this repo.

### 9.2 — One-time `bmad-loop init` (the step never run here)

```bash
scripts/bmad-switch <slug>                        # pick the active project FIRST
pixi run -e local-recipes bmad-loop init          # lays down Stop hooks + bundled loop skills, reconciles policy.toml, creates .bmad-loop/ runtime dirs
```
**Gate:** `.bmad-loop/` gains its runtime scaffolding (`runs/` appears on first run);
`bmad-loop --help` works; `bmad-loop tui` opens on a no-op.

### 9.3 — Make the policy MULTI-PROJECT (the key change for this repo)

`.bmad-loop/policy.toml` today is hardcoded to two projects. A worktree runs whatever the
policy says regardless of which project you switched to, so **two blocks must track the active
project** before each run:

- **`[verify] commands`** → the **active project's** deterministic gate (its pixi test task).
  Examples: warden → `pixi run --frozen -e pyforge-warden pyforge-warden-test`; atlas →
  `pixi run --frozen -e pyforge-atlas kedro-test` (+ `kedro-catalog-check`). A greenfield
  project supplies its own `-e <env> <test-task>`.
- **`[scm] worktree_seed`** → the literal **gitignored** paths a fresh worktree lacks (a
  worktree checks out tracked files only): the active project's
  `_bmad-output/projects/<slug>/implementation-artifacts` (else the engine crashes reading
  `sprint-status.yaml`) **and** `_bmad/custom/.active-project` (else BMAD config resolution in
  the worktree loses the project layers). Literal paths only — **no globs**.

> **Recommended (small build):** a `scripts/bmad-loop-project <slug>` helper that atomically
> (a) runs `scripts/bmad-switch <slug>`, (b) rewrites `[verify].commands` from a per-project
> table, and (c) rewrites `[scm].worktree_seed` to that slug's paths — so switching projects is
> one command and can't desync. Until it exists, edit `policy.toml` by hand between projects and
> **heed the CLAUDE.md symlink/marker desync warning** (marker + the two `_bmad-output` symlinks
> must always agree — always switch via `scripts/bmad-switch`).

### 9.4 — Graduated autonomy (`[gates] mode`)

| Mode | Behavior | When |
|---|---|---|
| `per-story-spec-approval` | Loop **halts at each story's spec** for human approval | Pilot / contract-freeze / high-risk stories (the current default) |
| `per-epic` | Approve **once per epic**; stories run unattended | Once the VERIFY gate reliably polices the loop |
| `none` | Fully unattended | Only when a conformance harness + VERIFY make false-greens near-impossible |

- **Escalation:** a CRITICAL contradiction pauses the loop → resolve with
  `/bmad-loop-resolve <story-key>` (interactive), then the loop re-drives the corrected spec.
- **Model tiering:** `[adapter.dev|review|triage]` set per-stage models; bump `[adapter.dev]`
  to `opus`/`fable` for hard stories, revert to `sonnet` for mechanical batches.
- **Review pass:** `[review] enabled=true, trigger="recommended"` runs a second-opinion review
  only when dev-auto flags it (`"always"` to force it every story).

### 9.5 — Prepare the story feed

- The loop consumes `sprint-status.yaml` (`development_status` map). Generate it with
  **`bmad-sprint-planning`** from the project's `epics.md`, or hand-author it.
- **Multi-project caveat:** `bmad-dev-auto` upstream expects the standard `{output_folder}`,
  but this repo resolves **per-project** (`planning_artifacts` path). Verify dev-auto honors the
  multi-project path; if not, fix it in dev-auto's **`customize.toml`** layer — **never** by
  forking the skill.

### 9.6 — Known blocker: the atlas `--frozen` VERIFY (DW-A1)

`pyforge-atlas` is **not in `pixi.lock`**, so `pixi run --frozen -e pyforge-atlas kedro-test`
(its VERIFY gate) can't materialize the env inside a worktree → an atlas loop run fails at
VERIFY. **Fix:** a workstation re-lock so `pixi.lock` carries the `pyforge-atlas` env, then the
gate runs frozen. `pyforge-warden` runs work **today** (its env is already locked). Do **not**
drop `--frozen` to work around it — an unfrozen re-solve in a worktree rewrites `pixi.lock` with
worktree-absolute channel paths that the squash-merge would commit.

### 9.7 — Run it

```bash
pixi run -e local-recipes bmad-loop run --story <story-key>   # one story
pixi run -e local-recipes bmad-loop run                       # the whole sprint feed
pixi run -e local-recipes bmad-loop tui                       # live dashboard
```
- **Journals:** `.bmad-loop/runs/<id>/` (gitignored; retention/trim/archive in `[cleanup]`).
- **Isolation:** `[scm] isolation="worktree"`, `branch_per="story"`, `merge_strategy="squash"`
  → each story is one squash commit on its own branch/worktree; a failed attempt is **kept**
  (`keep_failed`) for inspection, main is never touched.
- **Closeout:** wrap the merged stories in a **PR-per-wave**; run operator-invoked
  **`bmad-loop-sweep`** at wave boundaries to triage the deferred-work ledger; a conda-forge
  effort ends with the mandatory **CFE Rule-2 retro** (see `CLAUDE.md`).

---

## Phase 10 — Planning chains: greenfield vs brownfield (both feed Phase 9)

Both tracks are **spec-first** and both **terminate at the loop**. They differ only in how the
planning artifacts under `_bmad-output/projects/<slug>/planning-artifacts/` are produced.

**10.A — Spec-first (mandatory, both tracks).** Before any non-trivial code, a Tier-1 intake
spec must exist at `docs/specs/<name>.md` and reach `status: ready` (see repo `AGENTS.md` for the
frontmatter contract). Create it with `spec-driven-development` or `bmad-create-*`.

**10.B — Brownfield chain** (existing code to respect):

```
scripts/bmad-switch <slug>
bmad-document-project            # → living architecture/source-tree/parts docs (agents MUST honor these)
bmad-generate-project-context    # → project-context.md (preserve conventions + invariants)
bmad-prd                         # (or bmad-correct-course if mid-effort) → PRD
bmad-create-epics-and-stories    # → epics.md + stories
bmad-check-implementation-readiness   # gate — iterate to pass
bmad-sprint-planning             # → sprint-status.yaml (the loop's feed)
# → Phase 9 (bmad-loop run)
```

**10.G — Greenfield chain** (no legacy to honor):

```
scripts/bmad-switch <slug>       # after adding the project subtree (Phase 8.5)
bmad-prd                         # → PRD from the intake spec
bmad-architecture                # → the architecture spine (invariants) — DESIGN the system
bmad-create-epics-and-stories    # → epics.md + stories
bmad-check-implementation-readiness   # gate — iterate to pass
bmad-sprint-planning             # → sprint-status.yaml
# → Phase 9 (bmad-loop run)
```

**Which did pyforge-atlas use?** Brownfield (it migrates the legacy `cf_atlas`), planned via the
10.B chain — but then **executed via the in-session agent loop, not Phase 9**. That's the gap
this update closes: future waves/projects run through Phase 9 and get real `.bmad-loop/runs/`
journals.

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
| `.gitignore` | Extended with BMAD multi-project patterns (Phases 5 + 8); `.bmad-loop/runs/` + `cache/` already ignored (Phase 9) |
| `CLAUDE.md` § "Multi-Project Pattern" | Multi-project layout reference (Phase 8) |
| `CHANGELOG.md` | Tracks BMAD multi-project introduction and other repo-level changes |
| `.bmad-loop/policy.toml` | Loop policy — **make `[verify].commands` + `[scm].worktree_seed` track the active project** (Phase 9.3) |
| `scripts/bmad-loop-project <slug>` | *(recommended, not yet built)* atomic per-project loop switch: `bmad-switch` + rewrite the two policy blocks (Phase 9.3) |
| `docs/specs/<name>.md` | Tier-1 intake spec at `status: ready` before code — greenfield + brownfield (Phase 10.A) |
| pixi env in `pixi.lock` | **Workstation re-lock** so each project's loop-VERIFY env is frozen-materializable (Phase 9.6 / DW-A1) |

---

## Quick reference — set up a new project end to end

```bash
# 0. one-time repo install (Phases 0–1) — already done here
# 1. add the project subtree + config (Phase 8.5)
mkdir -p _bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}
# … write .bmad-config.toml, add a PROJECTS.md row …
scripts/bmad-switch <slug>

# 2. plan  (Phase 10 — pick the track)
#    brownfield: bmad-document-project → bmad-generate-project-context → bmad-prd → …
#    greenfield: bmad-prd → bmad-architecture → …
#    both end at:
bmad-create-epics-and-stories → bmad-check-implementation-readiness → bmad-sprint-planning

# 3. wire the loop for THIS project (Phase 9.3): point [verify].commands + [scm].worktree_seed at <slug>
# 4. run unattended (Phase 9.7)
pixi run -e local-recipes bmad-loop run            # or: run --story <key>
pixi run -e local-recipes bmad-loop tui            # watch; journals land in .bmad-loop/runs/<id>/
```
