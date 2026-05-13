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

## BMAD ↔ conda-forge-expert integration

These two rules govern any BMAD-driven effort that touches conda-forge work in this repo. They apply to every BMAD skill (`bmad-quick-dev`, `bmad-agent-dev`, persona agents, planning agents, code-review agents — everything). They are **always-on**; no opt-in.

### Rule 1 — BMAD must invoke `conda-forge-expert` for any conda-forge work

When a BMAD agent's current story, task, or sub-task involves any of:

- creating, editing, validating, optimizing, building, or submitting a conda recipe (`recipe.yaml`, `meta.yaml`, multi-output, patches under `recipes/<name>/patches/`)
- responding to a conda-forge build failure or staged-recipes review comment
- packaging a PyPI / npm / CRAN / CPAN / LuaRocks / GitHub source as a conda artifact
- working with `pin_subpackage`, `compiler()`, `stdlib()`, `noarch: python`, conda-forge selectors, or rattler-build features
- interacting with `pixi run -e local-recipes …` recipe-build / autotick / submit-pr tasks
- reading or modifying anything under `.claude/skills/conda-forge-expert/`, `.claude/scripts/conda-forge-expert/`, `.claude/data/conda-forge-expert/`

…the agent **must** invoke the `conda-forge-expert` skill (via the `Skill` tool with `skill: conda-forge-expert`) before producing recipe code or running recipe-related tooling. The skill's 9-step autonomous loop, Operating Principles, Critical Constraints, and Build Failure Protocol are authoritative — the BMAD story file does not override them.

If a BMAD story's instructions conflict with `conda-forge-expert`'s guidance (e.g., the story says "loosen this pin to `>=1.0`" but conda-forge-expert's pin-loosening convention applies a different rule), the skill wins and the agent updates the story comment to record the deviation.

### Rule 2 — Every conda-forge BMAD effort ends with a retro that improves the skill

When a BMAD effort that did conda-forge work reaches its closeout (final story complete; PR merged or final review-comment resolved; or the user marks the effort done), the agent **must** run a retrospective focused on the `conda-forge-expert` skill itself. The retro:

1. Invokes the `bmad-retrospective` skill (or follows its protocol manually if BMAD is not loaded).
2. Reviews session logs, build failures encountered, recipe diffs, and reviewer comments to identify:
   - **Corrections** — guidance in the skill that turned out to be wrong, stale, or misleading.
   - **Refinements** — guidance that worked but was harder to apply than it should have been (missing examples, ambiguous wording, missing edge cases).
   - **Additions** — patterns, constraints, gotchas, or build-failure recipes encountered for the first time during this effort that future efforts should benefit from.
3. Lands the findings as edits to:
   - `.claude/skills/conda-forge-expert/SKILL.md` (Operating Principles, Critical Constraints, Recipe Authoring Gotchas, Build Failure Protocol)
   - `.claude/skills/conda-forge-expert/reference/*.md` (per-topic deep references)
   - `.claude/skills/conda-forge-expert/guides/*.md` (workflow / troubleshooting guides)
   - `.claude/skills/conda-forge-expert/CHANGELOG.md` (a new version entry summarizing the retro's deltas, dated, with a one-line summary per finding)
4. Bumps the skill version per semver (PATCH for fixes/clarifications, MINOR for new gotchas / new sections, MAJOR only if breaking workflow changes).
5. Saves a corresponding auto-memory feedback entry only if the finding crosses skill boundaries (e.g., affects how BMAD interacts with `conda-forge-expert`); skill-internal findings stay in the skill files, not in auto-memory.

The retro is not optional and not deferrable. An effort is not "done" until the retro lands.

If the effort produced no novel findings (rare — almost every effort surfaces at least one refinement), the retro still runs and produces a CHANGELOG entry stating "no skill changes; verified existing guidance held for: <summary of effort>".

## Project Documentation Reference

For extended architectural context, please reference the centralized `docs/` folder:
- **`docs/mcp-server-architecture.md`** — FastMCP server integration and PyPI name mapping subsystem.
- **`docs/enterprise-deployment.md`** — Air-gapped environments and JFrog Artifactory integration.
- **`docs/developer-guide.md`** — Local testing and general recipe development guidelines.
- **`docs/copilot-to-api.md`** — Five ways to drive a GitHub Copilot subscription as a local model backend (`copilot-api`, `litellm`, `copilot-openai-api`, `copilot-api-proxy`, `c2p`); decision tree, auth flows, configuration reference.
- **`docs/specs/copilot-bridge-vscode-extension.md`** — BMAD-consumable tech-spec for a sideload-only VS Code extension that wraps the bridge pattern. Run via `bmad-quick-dev`.
- **`docs/specs/conda-forge-tracker.md`** — BMAD-consumable tech-spec for a local sibling-directory tracker that mirrors feedstocks I'm involved with and captures follow-ups (outdated upstreams, package requests, stuck PRs, rerender requests, mark-broken/yank) as offline markdown issues with GitHub-Issues-compatible frontmatter. 13 stories, channel-aware migration path. Run via `bmad-quick-dev`.
- **`docs/specs/db-gpt-conda-forge.md`** — BMAD-consumable tech-spec for packaging DB-GPT (`eosphoros-ai/DB-GPT` v0.8.0) on conda-forge as a 7-output multi-output recipe with 7 prerequisite recipes (3 trivial pure-Python, 3 lyric-* itkwasm-pattern noarch with vendored WASM, 1 cocoindex-class `lyric-py` Rust+PyO3). Q1 resolved (`B-full`). 13 stories in 4 waves; S12 documents a `B-six-plus-app-patched` fallback if any lyric-* worker is rejected during review. Run via `bmad-quick-dev`.
- **`docs/specs/atlas-phase-f-s3-backend.md`** — BMAD-consumable tech-spec for an S3/parquet backend that replaces `api.anaconda.org` as Phase F's required data source (the only firewall-blocking dependency in the atlas), adds Phase F+ richer metrics (rolling 30/90-day downloads, trend slope, platform/python/channel breakdowns), and exposes 3 new MCP tools (`platform_breakdown`, `pyver_breakdown`, `channel_split`). 14 stories in 4 waves; Wave 1 ships the air-gap fix as MVP. Run via `bmad-quick-dev`.
- **`docs/specs/atlas-pypi-universe-split.md`** — BMAD-consumable tech-spec for the 2026-05-13 actionable-scope audit. Bundles four findings: (1) Phase H pypi-json denominator one-line fix (672k → 12k packages, 56× cut); (2) Phase J + M archived-feedstock filters; (3) new `pypi_universe` side table (schema v20) extracting the ~660k `pypi_only` rows out of `packages` so the working set stays conda-actionable + Phase D splits into daily-lean + weekly-universe-upsert; (4) new `pypi-only-candidates` CLI + MCP tool surfacing the universe. 11 stories in 4 waves; Wave 1 ships the Phase H fix immediately. Run via `bmad-quick-dev`.

Skill-internal documentation (loaded on-demand when the skill activates):
- **`.claude/skills/conda-forge-expert/SKILL.md`** — Recipe authoring agent operating principles, 10-step lifecycle loop (step 8b: prepare submission branch on fork, step 9: open PR), build-failure protocol.
- **`.claude/skills/conda-forge-expert/reference/`** — `recipe-yaml-reference.md`, `meta-yaml-reference.md`, `python-min-policy.md`, `mcp-tools.md`, `conda-forge-ecosystem.md`, `pinning-reference.md`, `selectors-reference.md`, `jinja-functions.md`, `atlas-actionable-intelligence.md` (persona-mapped catalog of every actionable signal cf_atlas exposes — shipped + open + gap), `atlas-phases-overview.md` (phase-indexed companion: per pipeline stage, what's downloaded, the purpose, and the actionable intelligence it produces), `atlas-phase-engineering.md` (engineering patterns for writing or refactoring phases — rate limits, GraphQL batching, atomic writes, enterprise routing), `dependency-input-formats.md` (manifest / lock-file / SBOM / container-input support matrix — the canonical "what does scan_project accept?" reference), `conda-forge-yml-reference.md` (high-signal subset of conda-forge.yml keys — staged-recipes per-recipe override + feedstock-level — covers `azure.store_build_artifacts`, `os_version`, `provider`, `bot.version_updates.exclude`, deprecated keys, and common patterns).
- **`.claude/skills/conda-forge-expert/guides/`** — getting-started, migration, ci-troubleshooting, cross-compilation, feedstock-maintenance, testing-recipes.
- **`.claude/skills/conda-forge-expert/quickref/`** — `commands-cheatsheet.md` (incl. project pixi tasks), `bot-commands.md`.

### conda-forge-expert v7.0.0 layout (3-tier + MCP layer)
- **`.claude/skills/conda-forge-expert/scripts/`** — canonical implementation (source of truth). Edit code here.
- **`.claude/scripts/conda-forge-expert/`** — public CLI entrypoint layer (~30 thin subprocess wrappers). What `pixi run` calls.
- **`.claude/data/conda-forge-expert/`** — mutable runtime state (cf_atlas.db, vdb/, cve/, mappings, caches). Gitignored.
- **`.claude/tools/conda_forge_server.py`** — FastMCP server exposing 30+ tools across recipe-authoring + atlas-intelligence + project-scanning surfaces. Started by Claude Code at session boot; tool schemas surface at call time.

**Atlas intelligence (v7.0+)** — `cf_atlas.db` ships 16 schema versions, 15 pipeline phases (B → N), and 17 CLIs. Daily-use entrypoints: `detail-cf-atlas`, `staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`, `cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`, `scan-project`. All read-side CLIs are offline-safe. See `.claude/skills/conda-forge-expert/SKILL.md` § "Atlas Intelligence Layer" for the persona-mapped guide.

Enterprise routing (JFrog Artifactory, internal mirrors) is **runtime-driven** via `_http.py` (truststore + JFrog/GitHub/.netrc auth chain) — env vars only, never committed config. See `.claude/skills/conda-forge-expert/CHANGELOG.md` v6.0.0 / v7.0.0 entries for the full release notes.

Repo-wide pointers:
- **`_bmad-output/PROJECTS.md`** — BMAD multi-project index.
- **Auto-memory** — `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/MEMORY.md` indexes accumulated feedback (skill disambiguation, recipe pin-loosening, .bat shim rules, BMAD multi-project pattern) and project context.