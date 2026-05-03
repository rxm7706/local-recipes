# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Behavioral Guidelines

These four principles govern all work in this repo. The `conda-forge-expert` skill specializes them for recipe work; the BMAD skills apply them to planning/dev. Apply them globally.

1. **Think Before Coding** — state assumptions explicitly; for ambiguous requests, present interpretations, don't pick silently.
2. **Simplicity First** — minimum code that solves the problem; nothing speculative.
3. **Surgical Changes** — touch only what the task requires; match existing style.
4. **Goal-Driven Execution** — transform tasks into verifiable goals; loop until verified.

---

## Project Overview

This repository is an **AI-assisted, semi-autonomous packaging factory** for conda-forge recipes. It mirrors the workflow of `conda-forge/staged-recipes` but is supercharged with a suite of custom tools that enable Claude to handle nearly the entire recipe lifecycle, from generation and security scanning to building, debugging, and maintenance.

This is a multi-skill repo: conda-forge recipe work uses the `conda-forge-expert` skill (loads on-demand), and BMAD-driven planning/dev for sibling projects lives under `_bmad-output/projects/`.

**Critical Rule**: Do not mix `meta.yaml` and `recipe.yaml` formats in the same build run. The tooling will reject mixed-mode runs.

## BMAD Method Documentation

The BMAD Method is an AI-driven software development framework used in this project.

- **Local copy** (offline): `.claude/docs/bmad-method-llms-full.txt`
- **Live source**: https://docs.bmad-method.org/llms-full.txt

Fetch the live source for the latest version, or reference the local copy with `@.claude/docs/bmad-method-llms-full.txt` when working offline.

### Multi-Project Pattern (this repo hosts multiple BMAD projects)

This repository uses a single BMAD installation to drive multiple projects. Each project has its own subdirectory under `_bmad-output/projects/<slug>/` containing planning artifacts, implementation artifacts, project context, and project-scoped config overrides. See **`_bmad-output/PROJECTS.md`** for the index and detailed documentation.

**At session start with the user**, ask which project they're working on (or check `scripts/bmad-switch --current`) before invoking BMAD skills that write artifacts. Reading another project's artifacts is fine without switching — read directly from the file path.

**Active-project resolution priority** (used by `_bmad/scripts/resolve_config.py`):
1. `--project <slug>` per-call CLI flag (highest priority).
2. `BMAD_ACTIVE_PROJECT` environment variable.
3. `_bmad/custom/.active-project` marker file (managed by `scripts/bmad-switch`, gitignored).
4. None — only global config layers resolve; skills fall back to repo-root `_bmad-output/`.

**Six-layer config merge** (highest priority last):

| Layer | Path                                                         | Scope                                |
|-------|--------------------------------------------------------------|--------------------------------------|
| 1     | `_bmad/config.toml`                                          | Installer team (regenerated)         |
| 2     | `_bmad/config.user.toml`                                     | Installer user (regenerated)         |
| 3     | `_bmad/custom/config.toml`                                   | Global custom team, all projects     |
| 4     | `_bmad/custom/config.user.toml`                              | Global custom user, all projects     |
| 5     | `_bmad-output/projects/<slug>/.bmad-config.toml`             | Project team, active project only    |
| 6     | `_bmad-output/projects/<slug>/.bmad-config.user.toml`        | Project user, active project only    |

Layers 5 and 6 only load when an active project resolves. To set the active project: `scripts/bmad-switch <slug>`. To list projects: `scripts/bmad-switch --list`.

**Adding a new project:** see `_bmad-output/PROJECTS.md` § "Adding a new project."

## Skill Reference

| Skill | Purpose | When to invoke |
|---|---|---|
| `conda-forge-expert` | Full conda-forge recipe lifecycle (generate → validate → build → submit) | Creating/updating recipes, fixing build failures, any conda packaging |
| `bmad-quick-dev` | Implement story / feature / fix from a spec | Direct implementation requests when the story spec exists |
| `bmad-create-prd` / `-create-architecture` / `-create-epics-and-stories` / `-create-story` | BMAD planning chain | Starting a new product or feature in `_bmad-output/projects/<slug>/` |
| `bmad-document-project` | Brownfield project documentation | "Document this project" requests |
| `bmad-agent-*` (analyst/architect/dev/pm/tech-writer/ux-designer) | Persona-led workflows | "Talk to John/Mary/Winston/…" requests |

For full skill list and disambiguation defaults (which review skill, simplify-vs-code-simplification, schedule-vs-loop, etc.) see auto-memory entry `feedback_skill_disambiguation.md`.

## Project Documentation Reference

For extended architectural context, please reference the centralized `docs/` folder:
- **`docs/mcp-server-architecture.md`** — FastMCP server integration and PyPI name mapping subsystem.
- **`docs/enterprise-deployment.md`** — Air-gapped environments and JFrog Artifactory integration.
- **`docs/developer-guide.md`** — Local testing and general recipe development guidelines.
- **`docs/copilot-to-api.md`** — Five ways to drive a GitHub Copilot subscription as a local model backend (`copilot-api`, `litellm`, `copilot-openai-api`, `copilot-api-proxy`, `c2p`); decision tree, auth flows, configuration reference.
- **`docs/specs/copilot-bridge-vscode-extension.md`** — BMAD-consumable tech-spec for a sideload-only VS Code extension that wraps the bridge pattern. Run via `bmad-quick-dev`.
- **`docs/specs/conda-forge-tracker.md`** — BMAD-consumable tech-spec for a local sibling-directory tracker that mirrors feedstocks I'm involved with and captures follow-ups (outdated upstreams, package requests, stuck PRs, rerender requests, mark-broken/yank) as offline markdown issues with GitHub-Issues-compatible frontmatter. 13 stories, channel-aware migration path. Run via `bmad-quick-dev`.

Skill-internal documentation (loaded on-demand when the skill activates):
- **`.claude/skills/conda-forge-expert/SKILL.md`** — Recipe authoring agent operating principles, 9-step lifecycle loop, build-failure protocol.
- **`.claude/skills/conda-forge-expert/reference/`** — `recipe-yaml-reference.md`, `meta-yaml-reference.md`, `python-min-policy.md`, `mcp-tools.md`, `conda-forge-ecosystem.md`, `pinning-reference.md`, `selectors-reference.md`, `jinja-functions.md`.
- **`.claude/skills/conda-forge-expert/guides/`** — getting-started, migration, ci-troubleshooting, cross-compilation, feedstock-maintenance, testing-recipes.
- **`.claude/skills/conda-forge-expert/quickref/`** — `commands-cheatsheet.md` (incl. project pixi tasks), `bot-commands.md`.

### conda-forge-expert v6.0.0 layout (3-tier)
- **`.claude/skills/conda-forge-expert/scripts/`** — canonical implementation (source of truth). Edit code here.
- **`.claude/scripts/conda-forge-expert/`** — public CLI entrypoint layer (22 thin subprocess wrappers). What `pixi run` calls. README.md at this path documents the wrapper pattern.
- **`.claude/data/conda-forge-expert/`** — mutable runtime state (cf_atlas.db, vdb/, cve/, mappings, caches). Gitignored.

Enterprise routing (JFrog Artifactory, internal mirrors) is **runtime-driven** via `_http.py` (truststore + JFrog/GitHub/.netrc auth chain) — env vars only, never committed config. See `.claude/skills/conda-forge-expert/CHANGELOG.md` v6.0.0 for the full release note.

Repo-wide pointers:
- **`_bmad-output/PROJECTS.md`** — BMAD multi-project index.
- **Auto-memory** — `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/MEMORY.md` indexes accumulated feedback (skill disambiguation, recipe pin-loosening, .bat shim rules, BMAD multi-project pattern) and project context.