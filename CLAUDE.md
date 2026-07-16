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

**The marker is only half the switch — two gitignored symlinks are the other half:**

```
_bmad-output/planning-artifacts       -> projects/<slug>/planning-artifacts
_bmad-output/implementation-artifacts -> projects/<slug>/implementation-artifacts
```

`_bmad/bmm/config.yaml` hard-codes `planning_artifacts: "{project-root}/_bmad-output/planning-artifacts"`, and that key does **NOT** compose with a project's `output_folder` override — so **every BMAD skill that writes planning artifacts resolves through these symlinks**, not through the marker. Marker and symlinks must always agree; when they disagree, a write-skill silently targets the *other* project. **Always switch with `scripts/bmad-switch <slug>`** (since 2026-07-14 it re-points the symlinks atomically and writes the marker last, so a failed re-point can't desync); never hand-edit the marker. `scripts/bmad-switch --current` / `--list` warn on a desync — heed it before running any BMAD write-skill. Live near-miss (2026-07-14): the symlinks sat on `pyforge-warden` while the marker said `local-recipes`, so a local-recipes doc re-sync would have overwritten pyforge-warden's PRD/epics/architecture.

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

### Spec-driven, framework-neutral layout (the three tiers)

This repo is spec-driven and tool-agnostic — the spec is the contract; the agent/framework is interchangeable. **`AGENTS.md`** (repo root) is the cross-tool entry point (thin per-tool pointers: `CLAUDE.md`, `.cursor/rules/specs.mdc`, `GEMINI.md`, `.github/copilot-instructions.md`). Three tiers, never crossed:

| Tier | Location | Purpose | Git |
|---|---|---|---|
| **1 — Intake spec** | `docs/specs/*.md` | The "what to build" contract every tool/framework reads (the `bmad-quick-dev` entry point) | tracked, permanent |
| **2 — Planning** | `_bmad-output/projects/<slug>/planning-artifacts/` | PRD, architecture/API specs, epics+stories list, gate reports | tracked, permanent |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` | story files, sprint YAMLs, test outputs, retros, derived per-effort specs | **gitignored / local-only** |

Rules: an **intake spec belongs in Tier 1 (`docs/specs/`)** — never a Tier-3 output dir; `implementation-artifacts/` is gitignored, so **nothing there may be git-tracked**. `bmad-drift-check` enforces both (HARD `tracked-impl-artifact` finding).

**Spec-first (MANDATORY, always-on):** before implementing any non-trivial effort, a spec MUST exist in `docs/specs/<name>.md` — if none exists, create it first (`spec-driven-development` skill or `bmad-create-*`) and bring it to `status: ready` before writing code. **Keep the spec's `status:` frontmatter current** (`draft → ready → in-progress → shipped`, with `implemented_by:` + `shipped_ref:` when shipped) — it is the framework-neutral source of truth, updated regardless of which agent/tool/human did the work. Full convention + frontmatter contract: **`AGENTS.md`** (repo root). Check status anytime with `pixi run -e local-recipes bmad-drift-check --specs`.

### Keeping BMAD artifacts in sync with the live repo (always-on)

The `_bmad-output/projects/local-recipes/` artifacts (PRD, architecture set, epics, project-context, overview, specs) hard-code volatile facts about the factory (skill version, cf_atlas schema, MCP tool / atlas-phase / pixi-env counts, gotcha range) and drift behind the fast-moving `conda-forge-expert` skill. A **two-layer sync loop** keeps them accurate and able to catch up after *any* out-of-band change (BMAD or not):

- **Detector** (cheap, deterministic): `pixi run -e local-recipes bmad-drift-check` (and `bmad-groundtruth` for live facts as JSON). Reports pin drift, count/phase-list staleness, stale rules, archive-hygiene + stray files (auto-fix with `-- --fix`), coverage completeness (every project file must be classified), and baseline-vs-live surface change. Enforced in the test suite by `.claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py` (integrity only).
- **Reconciler** (correctness): the **BMAD skills themselves** — `bmad-document-project` re-grounds the living architecture/overview/source-tree/parts docs; `bmad-generate-project-context` the rulebook; `bmad-correct-course` + `bmad-create-epics-and-stories` the PRD/epics; `bmad-validate-prd` + `bmad-check-implementation-readiness` the gate reports; `bmad-index-docs` the index. Then re-stamp the baseline (`bmad-drift-check -- --write-baseline`).

**When to run:** after every CFE retro / skill MINOR bump, and whenever the detector reports `surface-changed` (an out-of-band edit to `recipes/`, `.claude/`, `pixi.toml`, or `docs/specs/`). Full procedure + finding→remedy mapping: **`_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md`**. The detector is `scripts/bmad_drift_check.py`.

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
- **`docs/library-llms-full.md`** — LLM/agent-facing catalog of every library and CLI in the pixi environments: capabilities, version pins, import-name gotchas, env membership, and what is deliberately NOT installed. Derived from `pixi.toml` (regeneration prompt in its header) — consult before importing a library or proposing a new dependency. Drift detector: `pixi run -e local-recipes llms-full-check` (exits non-zero when the catalog is stale; reconcile by regenerating).

### Intake specs (`docs/specs/` — Tier 1)

One table row per spec; the **spec file itself is the source of truth** (frontmatter contract + its
`## Current State` block where present) — long-form status detail is deliberately not duplicated here.
List live statuses with `pixi run -e local-recipes bmad-drift-check --specs`. Unless a row says
otherwise, run a spec via `bmad-quick-dev` with the spec path + parameters named in the prompt.

**Active (`in-progress`):**

| Spec | What it is |
|---|---|
| `docs/specs/langflow-conda-forge.md` | langflow-suite multi-output recipe (4 outputs: langflow-sdk+lfx+langflow-base+langflow, v1.10.1) + full ~71-recipe closure submission to staged-recipes. Suite PR #33972 is a fully-green draft; closure PRs in flight. python_min 3.11 (G41). |
| `docs/specs/db-gpt-conda-forge.md` | DB-GPT on conda-forge. **TERMINAL — delivered via external PR #33883 (consume-not-submit, G58); do NOT re-run BMAD on it.** Only § Current State + § Readiness are authoritative; the stories are historical. |
| `docs/specs/flyte-conda-forge.md` | Flyte 2 SDK (PyPI `flyte` ≠ v1 `flytekit`) — 6-recipe closure built GREEN locally; submission blocked on the buf.validate namespace collision (G88). python_min 3.11 (G40/G41). |
| `docs/specs/feedstock-refresh.md` | Two-track bulk refresh of ALL 769 feedstocks rxm7706 can modify (regenerate, v0→v1, platform-expand). Track A (sole, 537): Waves B–F shipped, reopened for Wave H total-coverage (179 remaining). Track B (co, 232): ready; adds co-maintainer etiquette + a no-local-recipe bucket. Delegates per-feedstock work to `feedstock-platform-expansion.md`. |
| `docs/specs/bmad-loop-adoption.md` | BMAD 6.6.0→6.10.0 upgrade (gains `bmad-dev-auto`) + bmad-loop v0.8.1 adoption (deterministic dev-loop orchestrator; pixi-provisioned: conda-forge `bmad-method` + tmux, git-pinned bmad-loop) so pyforge-warden implementation runs loop-driven with graduated gates. W1–W3 done (validate 9/9, sprint feed 20/20); W4 = BMad Method UI dashboards (consume-not-submit mirrors of staged-recipes#33513 → local `bmad-ui` pixi env). Remaining: hooks approval + the 1.1 pilot; Rule-2 CFE retro at closeout (W4 touches recipes/). |

**Ready (backlog, unimplemented):**

| Spec | What it is |
|---|---|
| `docs/specs/trendshift-conda-forge.md` | Two-track upstream-sweep packaging. Track A: cf_atlas **Phase T** GitHub-trending discovery engine (schema v29→v30, `trending-candidates` CLI/MCP tool) + tiered packaging workflow, first batch seeded by `cli-anything-hub` — resume at Wave A. Track B (absorbed `microsoft-conda-forge.md`): the June 2026 `github.com/microsoft/*` org audit — ~10–14 recipes in 3 waves, Q1–Q3 open. |
| `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` | Migrate the cf_atlas orchestrator from hand-rolled phases to a Kedro/Dagster/DuckDB stack (Waves 0 + A–H, 22 FRs incl. FR-19 Basilisk vuln source / FR-20 release velocity / FR-21 migration readiness / FR-22 factory layer; v5.6 analysis-complete (reset, corpus sync, research folds, adversarial review, PRFAQ kill-test, market research) 2026-07-16). Run via `bmad`. |
| `docs/specs/claude-team-memory.md` | `.claude/memory/` team-shared memory layer + `team-memory` skill (10 waved stories). |
| `docs/specs/copilot-bridge-vscode-extension.md` | Sideload-only VS Code extension wrapping the copilot-api bridge pattern (see `docs/copilot-to-api.md`). |
| `docs/specs/pyforge-warden.md` | **Warden** — pluggable multi-axis Python dependency compliance gate (v1 axes: hygiene `deptry`, security `osv-scanner`+CISA-KEV+EPSS gates, license + currency with **flag-activated gates**, baseline & grandfathering, opt-in fix-PR actuator) over Python/Conda/Pixi manifests; one schema-validated `ComplianceReport` + CI exit-code gate. Spec-first since 2026-07-15; v1 re-baselined 2026-07-16 (D12: the former v1.1 bucket is v1) — 6 epics / 31 stories, FR1–FR40. Stories 1.1–1.4 shipped. osv-scanner consumed from the existing conda-forge feedstock (no new recipe). |

**Timeless workflows (`workflow` — parameterized, re-runnable; per-case state appends to their Worked Examples):**

| Spec | What it is |
|---|---|
| `docs/specs/feedstock-platform-expansion.md` | Dual-goal per-feedstock workflow: refresh `recipes/<feedstock>/` to the latest CFE shape at the latest upstream version AND widen the build matrix (osx-arm64 / linux-aarch64) in the same PR. The procedural core both refresh specs delegate to; deep detail in `.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md`. |
| `docs/specs/feedstock-failure-remediation.md` | Red feedstock-PR remediation loop: triage FLAKE / REAL_FIX / BLOCKED (G32 signature catalog), execute-locally-first, maintainer-edit push to the bot fork, rerender-after-push. Worked example: the 2026-06-17/18 12-PR batch (G31–G34). |
| `docs/specs/presentation-deck.md` | Reusable React+Vite slide-deck workflow: turn a Claude Design 1920×1080 `.dc.html` prototype into a self-contained deck via mechanical slide extraction → a small deck engine (fit-to-viewport, keyboard nav, URL-hash routing, overview grid, presenter view w/ notes+timer), a static offline-safe Vite bundle, and Marp + PPTX exports. Parameterized by topic (non-conda-forge). Worked Example 1 = the 45-slide *Agentic AI across the SDLC* / BMAD deck (`presentations/agentic-sdlc/`, PR #50). |

**Shipped (historical record — evidence in each spec's `shipped_ref`):**

| Spec | What it is |
|---|---|
| `docs/specs/lts-registry-gap.md` | `lts-registry-gap` CLI — read-only suggester diffing endoflife.date's product list against `v_actionable_packages` to propose lts-registry.yaml entries (exact/likely tiers; the registry stays hand-curated, git review decides) — SHIPPED 2026-07-06 (CFE v8.74.0). |
| `docs/specs/seed-gap-suggesters.md` | `cwe-seed-gap` + `spdx-schema-gap` + `license-map-gap` — read-only suggesters proposing `cwe_categories_seed.json` / `spdx.schema.json` / in-code `_LICENSE_TO_SPDX` entries (keyword-classified `Other` CWEs; vendored-vs-upstream SPDX diff; unmapped-PyPI-license ranking); the curated maps stay hand-owned, git review decides — SHIPPED 2026-07-06 (CFE v8.75.0 + v8.76.0). |
| `docs/specs/cyclonedx-universe-inventory.md` | CycloneDX inventory of the FULL PyPI + conda-forge universes — SHIPPED 2026-07-06 (Waves A–E + S-retro, CFE v8.73.0): `export-purls`/`mapping-gap` (+v29 view), `universe-sbom` (856,766-component BOM), `inventory-match` (S5a intake incl. pixi.lock; transitive resolver; decision-4 live channeldata; vulns policy gate), `add-handoff`, `library-futures`/`recommend-2027` (2027–2030 tiers, py314 + LTS/endoflife signals). All local live gates PASS — dated Dev Notes in the spec. Do not re-run BMAD on it. |
| `docs/specs/cfe-shipped-releases.md` | Consolidated archive of the 10 shipped intakes (2026-07-02): v7.9.0 pypi-universe-split, v8.0.0 + v8.9.0 CFE bundles, v8.1.0 PyPI intelligence, v8.6.0 AppThreat, v8.14.0 PR-artifact downloader, v8.15.0 Phase P incremental, Phase F Waves 1–3 (v7.6.0→v8.19.0), v8.20.0 Phase K scheduler, + the closed graphifyy osx-arm64 fanout effort. Release notes: skill CHANGELOG. Do not re-run BMAD on any part. |
| `docs/specs/conda-forge-tracker.md` | Sibling repo `~/UserLocal/Projects/Github/rxm7706/conda-forge-tracker/` — markdown-first personal feedstock tracker (13 stories) |

Skill-internal documentation (loaded on-demand when the skill activates):
- **`.claude/skills/conda-forge-expert/SKILL.md`** — Recipe authoring agent operating principles, 10-step lifecycle loop (step 8b: prepare submission branch on fork, step 9: open PR), build-failure protocol.
- **`.claude/skills/conda-forge-expert/reference/`** — `recipe-yaml-reference.md`, `meta-yaml-reference.md`, `python-min-policy.md`, `mcp-tools.md`, `conda-forge-ecosystem.md`, `pinning-reference.md`, `selectors-reference.md`, `jinja-functions.md`, `atlas-phases-overview.md` (consolidated atlas intelligence reference — Part A: persona-mapped catalog of every actionable signal, shipped + open + gap; Part B: phase-indexed overview of each pipeline stage), `atlas-phase-engineering.md` (engineering patterns for writing or refactoring phases — rate limits, GraphQL batching, atomic writes, enterprise routing; § 13: Phase P cost model + operator playbook), `dependency-input-formats.md` (manifest / lock-file / SBOM / container-input support matrix — the canonical "what does scan_project accept?" reference), `conda-forge-yml-reference.md` (high-signal subset of conda-forge.yml keys — staged-recipes per-recipe override + feedstock-level — covers `azure.store_build_artifacts`, `os_version`, `provider`, `bot.version_updates.exclude`, deprecated keys, and common patterns).
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