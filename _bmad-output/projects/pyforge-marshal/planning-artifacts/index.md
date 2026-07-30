---
doc_type: master-index
project_name: local-recipes
date: 2026-07-25
repository_type: monorepo
parts: 5
docs_generated: 12
source_pin: 'conda-forge-expert v8.81.0'
---

# `local-recipes` — Master Documentation Index

> **Re-grounded 2026-07-25** (`source_pin` → **v8.79.1**; full reconciler pass per [SYNC-RUNBOOK.md](../SYNC-RUNBOOK.md), triggered by `surface-changed` pixi_envs 12 → 15). Regenerated **last**, after every other living doc, per the runbook's ordering rule.
>
> **What moved** — all of it *around* the packaging factory, none of it *inside* it: the repo grew a **fifth part** (`pyforge-packages` — five shipping distributions under `src/shared/packages/`); **19 pixi envs** in two families (+3 product envs: `pyforge-doctor`, `pyforge-herald`, `pyforge-scribe`); BMAD went **6.6.0 → 6.10.0** with **93 skill dirs / 89 real skills** across **14 projects** carrying **22 Specs** + **63 tracked story specs**; the **PyForge identity system** landed and is now binding on prose; **26 Dreams**, **14 deck folders**; and a new governance layer (`spec_surface_check.py`, `bmad-loop-worktree`, the HARD parallel-agent rule).
>
> **Re-verified unchanged against live code:** cf_atlas **schema v29**, **46 MCP tools**, **22 executable atlas phases**, gotchas **G1–G107**, the autonomous lifecycle loop.
>
> **This pass corrected 10 dead documentation links, a cancelled pipeline phase presented as in-flight, and a fabricated MCP registration mechanism.** See § *Drift Status*.

---

## Project Overview

- **Type:** monorepo with **5 logical parts**
- **Primary language:** Python (factory 3.12; `pyforge-atlas` / `pyforge-doctor` require ≥3.14)
- **Build engine:** Pixi + rattler-build
- **Default pixi env:** `local-recipes` (**18 envs total** — 9 factory + 8 `no-default-feature` product envs)
- **Recipe corpus:** 1,664 recipe dirs (933 v1 `recipe.yaml` + 1,024 v0 `meta.yaml`; **300 dirs carry both**, the sanctioned transitional shape — outputs, NOT part of the rebuild target)
- **Skill version:** conda-forge-expert **v8.79.1**

> See **[project-overview.md](./project-overview.md)** for the full executive summary, technology stack, and five-part decomposition.

---

## Quick Reference by Part

| Part | Display name | Type | Architecture doc |
|---|---|---|---|
| 1 | **conda-forge-expert** skill | library | [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md) |
| 2 | **cf_atlas** data pipeline | data | [architecture-cf-atlas.md](./architecture-cf-atlas.md) |
| 3 | **FastMCP server** | backend | [architecture-mcp-server.md](./architecture-mcp-server.md) |
| 4 | **BMAD infrastructure** | infra | [architecture-bmad-infra.md](./architecture-bmad-infra.md) |
| 5 | **`pyforge-packages`** (five workspace dists) | library | *no dedicated doc yet* — see [architecture.md](./architecture.md) § 3 and [source-tree-analysis.md](./source-tree-analysis.md) § Part 5 |

Part 5 is `src/shared/packages/pyforge-{atlas,doctor,herald,scribe,warden}/` — five hatchling-built distributions sharing the **PEP 420 implicit namespace** `pyforge` (no `src/pyforge/__init__.py` in any of them, deliberately). Maturity is uneven and worth knowing before you read: warden and atlas are production-grade; herald has a real transport core behind a stub CLI; scribe has one working command; doctor is a scaffold plus a frozen report schema.

---

## Generated Documentation

The tracked living set is **12 documents** (the detector's `tracked:living` class). All twelve exist — there are no pending or unwritten documents in this set.

| # | Document | What it covers |
|---|---|---|
| 1 | [project-overview.md](./project-overview.md) | System framing, monorepo structure, five-part decomposition, cross-cutting concerns, getting-started orientation |
| 2 | [architecture.md](./architecture.md) | Consolidated architecture: system overview, architectural style, the five parts, cross-cutting concerns, data architecture, **ADR-001…ADR-017**, quality attributes, risks, build order, glossary |
| 3 | [source-tree-analysis.md](./source-tree-analysis.md) | Annotated directory tree, entry-points table, critical files, per-part counts |
| 4 | [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md) | Part 1: 3-tier canonical/wrapper/data architecture, 66 canonical scripts, 42 templates / 13 ecosystems, the autonomous loop's 12 gated stages, build-failure protocol, Recipe Authoring Gotchas G1–G107 |
| 5 | [architecture-cf-atlas.md](./architecture-cf-atlas.md) | Part 2: the **22-phase** pipeline (B/B.5/B.6/C/C.5/D/O/P/Q/R/S/E/E.5/F/G/G'/H/J/K/L/M/N), schema v29, 5 SQL views, TTL gates, S3 + cf-graph offline backends, failure modes |
| 6 | [architecture-mcp-server.md](./architecture-mcp-server.md) | Part 3: 46 MCP tools (21 recipe-authoring / 21 atlas / 2 project-scanning / 2 infra), the thin-subprocess-wrapper pattern, stdio transport, `~/.claude.json` registration |
| 7 | [architecture-bmad-infra.md](./architecture-bmad-infra.md) | Part 4: BMAD 6.10.0, six-layer config merge, the two-half active-project switch, 89 skills, 14 projects, the Spec + memlog model, bmad-loop, the governance detectors |
| 8 | [integration-architecture.md](./integration-architecture.md) | 12 integration contracts across the five parts, the `_http.py` auth chain, the JFROG leak, vuln-db env separation, end-to-end flows |
| 9 | [development-guide.md](./development-guide.md) | Prerequisites, the full 106-task `local-recipes` cheatsheet, manual recipe workflow, all three test suites, BMAD workflows, PR CI gates |
| 10 | [deployment-guide.md](./deployment-guide.md) | What actually deploys, air-gap + JFrog setup, the 21 `<HOST>_BASE_URL` overrides, JFROG_API_KEY mitigation, CI/CD |
| 11 | [index.md](./index.md) | This file — master navigator |
| — | [project-parts.json](./project-parts.json) | Machine-readable: 5 parts with root paths / key tech / pixi envs / subdirectory inventory, integration points, rebuild build order |

**Validation + change-management artifacts:**

| Document | When written | What it captures |
|---|---|---|
| [validation-report-PRD.md](./validation-report-PRD.md) | `bmad-prd` (validate) | 13-dimension PRD validation. Dated snapshot — deliberately not pin-forwarded. |
| [implementation-readiness-report.md](./implementation-readiness-report.md) | `bmad-check-implementation-readiness` | Cross-artifact alignment across PRD + architecture + epics + project-context. Dated snapshot. |
| [epics.md](./epics.md) | `bmad-create-epics-and-stories` | **14 epics** (numbered 1–14; Epic 14 is filed between 9 and 10), story IDs in `E<n>.S<n>` form, 5 waves. |
| [PRD.md](./PRD.md) | `bmad-prd` | The rebuild PRD for the factory. |

> **Note (2026-07-25):** `PRD.md` and `epics.md` are `tracked:plan` documents. This pass reconciled the *living* docs only; the plan pair re-syncs structurally via `bmad-correct-course` → `bmad-prd` / `bmad-create-epics-and-stories`, which has **not** been run here. Known plan-side staleness: Epic 10 is titled "Part 3 MCP Server + 42 Tools" (live: 46), and neither doc knows about Part 5.

**Change history** — **9** `bmad-correct-course` proposals under **[`change-history/`](./change-history/)**:

| Document | Sync |
|---|---|
| [sprint-change-proposal-2026-05-12.md](./change-history/sprint-change-proposal-2026-05-12.md) | v7.7.2 → v7.8.1 — env-var additions, phase architecture, `_http.py` surface expansion |
| [sprint-change-proposal-2026-05-13.md](./change-history/sprint-change-proposal-2026-05-13.md) | v7.8.1 → v7.9.0 — actionable-scope audit (`pypi_universe` split, Phase H denominator fix) |
| [sprint-change-proposal-2026-05-13-v8.0.md](./change-history/sprint-change-proposal-2026-05-13-v8.0.md) | v7.9.0 → v8.0.0 — structural-enforcement view + persona-profile bundle |
| [sprint-change-proposal-2026-05-15-v8.1.md](./change-history/sprint-change-proposal-2026-05-15-v8.1.md) | v8.0.x → v8.1.0 — PyPI intelligence layer (phases O/P/Q/R/S) |
| [sprint-change-proposal-2026-05-23-v8.5.2.md](./change-history/sprint-change-proposal-2026-05-23-v8.5.2.md) | v8.5.1 → v8.5.2 — admin-refresh audit close-out + Phase K hang fix |
| [sprint-change-proposal-2026-05-23-v8.5.3.md](./change-history/sprint-change-proposal-2026-05-23-v8.5.3.md) | v8.5.2 → v8.5.3 — DW12 rollup-staleness fix + DW13 CISA KEV via Path C |
| [sprint-change-proposal-2026-05-24-v8.6.0.md](./change-history/sprint-change-proposal-2026-05-24-v8.6.0.md) | v8.5.3 → v8.6.0 — AppThreat Deep Signals (migrations v23 → v24 → v25); Wave C cancelled pre-implementation |
| [sprint-change-proposal-2026-06-07-v8.11.1.md](./change-history/sprint-change-proposal-2026-06-07-v8.11.1.md) | v8.10.0 → v8.11.1 — npm-generator default flipped to per-platform inline build |
| [sprint-change-proposal-2026-06-20-v8.39.0.md](./change-history/sprint-change-proposal-2026-06-20-v8.39.0.md) | v8.11.1 → v8.39.0 — Phase F+ intelligence waves, PR-artifact downloader, Phase P cost refactor |

**Frozen archive** (never re-grounded by the sync loop): [`prfaq-cfe-atlas-kedro-migration.md`](./prfaq-cfe-atlas-kedro-migration.md) + [its distillate](./prfaq-cfe-atlas-kedro-migration-distillate.md), the 4 studies under [`research/`](./research/), and [`campaign-spec-completion-2026-07-25.md`](./campaign-spec-completion-2026-07-25.md).

**The Specs** — this project owns **8** of the portfolio's 22, under [`specs/`](./specs/). Each is a five-field contract (`## Why` · `## Capabilities` · `## Constraints` · `## Non-goals` · `## Success signal`) **derived from an append-only `.memlog.md`, never hand-patched**:

| Spec | Governs |
|---|---|
| [`spec-packaging-factory/`](./specs/spec-packaging-factory/SPEC.md) | the conda-forge-expert skill surface (361 files; drift sentinel = the skill CHANGELOG) |
| [`spec-regenerable-factory/`](./specs/spec-regenerable-factory/SPEC.md) | spec-surface governance itself (+ [`waves.md`](./specs/spec-regenerable-factory/waves.md)) |
| [`spec-fleet-stewardship/`](./specs/spec-fleet-stewardship/SPEC.md) | the recipe/feedstock fleet (2,809 files; drift exempt) |
| [`spec-modernist-identity/`](./specs/spec-modernist-identity/SPEC.md) | the PyForge identity + deck family (693 files) |
| [`spec-factory-console/`](./specs/spec-factory-console/SPEC.md) | the Guildhall console (+ [`console-contract.md`](./specs/spec-factory-console/console-contract.md), [`drill-evidence.md`](./specs/spec-factory-console/drill-evidence.md)) |
| [`spec-multi-loop-isolation/`](./specs/spec-multi-loop-isolation/SPEC.md) | concurrent bmad-loop homes |
| [`spec-enterprise-airgap/`](./specs/spec-enterprise-airgap/SPEC.md) | the air-gap / JFrog routing layer |
| [`spec-pyforge-marshal/`](./specs/spec-pyforge-marshal/SPEC.md) | Marshal's governance surface in this repo (distinct from the `pyforge-marshal` project's product Spec — the collision `spec_surface_check.py` keys around) |

---

## Existing Documentation (Inputs to This Set)

> **All links below were verified to resolve on 2026-07-25.** The previous revision of this index carried **10 dead links** — `docs/` was reorganised into subdirectories and several specs were consolidated, but this index was never updated. See § *Drift Status*.

### Repo-wide
- [`AGENTS.md`](../../../../AGENTS.md) — the cross-tool entry point and the canonical tier table
- [`CLAUDE.md`](../../../../CLAUDE.md) — repo-wide AI agent guidance, BMAD↔CFE integration rules, PR CI gates
- [`README.md`](../../../../README.md) — human-facing intro
- [`pixi.toml`](../../../../pixi.toml) — 18 envs, 17 features, 152 task definitions
- [`docs/dreams/pyforge-charter.md`](../../../../docs/dreams/pyforge-charter.md) — **Tier 0, constitutional**: the mission, the eight Smiths, § Branding and § The Lexicon. No artifact may contradict it.

### Project-scoped (this project)
- [`project-context.md`](../project-context.md) — foundational rules every BMAD agent reads on spawn (v8.79.1-pinned, 74 rules)
- [`SYNC-RUNBOOK.md`](../SYNC-RUNBOOK.md) — the detector/reconciler loop that keeps this doc set honest

### Part 1 (skill)
- [`.claude/skills/conda-forge-expert/SKILL.md`](../../../../.claude/skills/conda-forge-expert/SKILL.md) — primary spine (3,887 lines)
- [`.claude/skills/conda-forge-expert/INDEX.md`](../../../../.claude/skills/conda-forge-expert/INDEX.md) — task→tool navigator
- [`.claude/skills/conda-forge-expert/CHANGELOG.md`](../../../../.claude/skills/conda-forge-expert/CHANGELOG.md) — release history (canonical drift-detection source)
- [`.claude/skills/conda-forge-expert/reference/`](../../../../.claude/skills/conda-forge-expert/reference/) — **15** deep-reference files
- [`.claude/skills/conda-forge-expert/guides/`](../../../../.claude/skills/conda-forge-expert/guides/) — **9** workflow guides
- [`.claude/skills/conda-forge-expert/quickref/`](../../../../.claude/skills/conda-forge-expert/quickref/) — 2 quick-reference files

### Reference docs (`docs/reference/`)
- [`docs/reference/mcp-server-architecture.md`](../../../../docs/reference/mcp-server-architecture.md) — MCP server design + PyPI name-mapping subsystem
- [`docs/reference/enterprise-deployment.md`](../../../../docs/reference/enterprise-deployment.md) — air-gap + JFrog operational reference
- [`docs/reference/developer-guide.md`](../../../../docs/reference/developer-guide.md) — local testing + recipe development
- [`docs/reference/library-llms-full.md`](../../../../docs/reference/library-llms-full.md) — the agent-facing catalog of every library/CLI in the pixi envs (drift detector: `pixi run -e local-recipes llms-full-check`)
- [`docs/reference/pixi-config-jfrog.example.toml`](../../../../docs/reference/pixi-config-jfrog.example.toml) — JFrog channel-routing example

### The spec tiers
- **Tier 0 — Dreams:** [`docs/dreams/`](../../../../docs/dreams/) — **26** Dreams + a README. Every effort starts here.
- **Tier 1 — legacy intake specs:** [`docs/specs/`](../../../../docs/specs/) — **19** files, **phasing out**; author no new ones. Shipped intakes are consolidated in [`cfe-shipped-releases.md`](../../../../docs/specs/cfe-shipped-releases.md).
- **Tier 2 — Specs & planning:** `_bmad-output/projects/<slug>/planning-artifacts/` — the active contract. 22 Specs across 14 projects; 63 tracked story specs.
- **Tier 3 — execution output:** `implementation-artifacts/` — **gitignored; nothing there may ever be git-tracked** (HARD `tracked-impl-artifact`). Story specs are the exception to Tier 3: they are promoted to `planning-artifacts/specs/` and committed once their story merges.

---

## Getting Started Paths

### Path A: I'm new to this repo

1. Read [project-overview.md](./project-overview.md)
2. Read [`docs/dreams/pyforge-charter.md`](../../../../docs/dreams/pyforge-charter.md) § The Lexicon — the vocabulary is binding, not decorative
3. Skim [source-tree-analysis.md](./source-tree-analysis.md) to orient on file locations
4. Read [development-guide.md](./development-guide.md) § Prerequisites + First-time setup
5. Run `pixi run -e local-recipes health-check` to verify your environment
   *(Do **not** run `pixi run bmad-preflight` — it invokes `scripts/ensure-bmad-preflight.sh`, which does not exist.)*

### Path B: I'm rebuilding this repo from scratch using BMAD-METHOD

Build order from `project-parts.json`:

1. **Part 4 (BMAD infrastructure)** — install BMAD-METHOD 6.10.0, the six-layer config, the multi-project layout **and both `_bmad-output/` symlinks**. See [architecture-bmad-infra.md](./architecture-bmad-infra.md) § Rebuild checklist.
2. **Part 1 (conda-forge-expert skill)** — 66 canonical scripts, 57 wrappers, SKILL.md, reference/, guides/, templates/, tests/. See [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md) § Rebuild checklist.
3. **Part 2 (cf_atlas)** — the 22-phase pipeline inside Part 1's `scripts/`. Schema v29 from the start. See [architecture-cf-atlas.md](./architecture-cf-atlas.md) § Rebuild checklist.
4. **Part 3 (MCP server)** — `conda_forge_server.py` with 46 `@mcp.tool()` subprocess wrappers, **plus the `~/.claude.json` registration** (a clone with no registration has zero working tools).
5. **Part 5 (`pyforge-packages`)** — the five workspace dists and their isolated product envs.
6. **Throughout: enforce the integration contracts** — [integration-architecture.md](./integration-architecture.md).
7. **Plan from a Dream**: write the Tier-0 Dream, run `bmad-spec` to produce the Spec, then decompose with `bmad-prd` / `bmad-architecture` / `bmad-create-epics-and-stories`.

### Path C: I'm authoring a new recipe right now

1. Confirm the active project is `local-recipes` — read `_bmad/custom/.active-project` directly. **If you are one of several parallel agents, do not run `scripts/bmad-switch`**; address projects by physical path and pass `BMAD_ACTIVE_PROJECT=local-recipes` per invocation.
2. In Claude Code: invoke the `conda-forge-expert` skill
3. Follow the autonomous loop; **step 8b (`prepare_submission_branch`) is the only human checkpoint** — `submit_pr` is ungated
4. See [development-guide.md](./development-guide.md) § Authoring a New Recipe for the shell-driven version

### Path D: I'm debugging a build failure

1. Get the most recent log: `ls -t build_artifacts/*/bld/rattler-build_<name>_*/work/conda_build.log | head -1`
2. Run `pixi run -e local-recipes analyze-failure -- <log>`
3. Check the Recipe Authoring Gotchas (G1–G107) in [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md)
4. See [development-guide.md](./development-guide.md) § Debugging

### Path E: I'm setting up an air-gapped / JFrog deployment

1. Read [deployment-guide.md](./deployment-guide.md) end-to-end — start with § *What actually deploys*
2. Pay attention to § *The JFROG_API_KEY Cross-Host Leak* — still unresolved in `_http.py`
3. Use the deployment checklist
4. Cross-reference [`docs/reference/enterprise-deployment.md`](../../../../docs/reference/enterprise-deployment.md)

### Path F: I'm running the atlas pipeline / cf_atlas queries

1. Read [architecture-cf-atlas.md](./architecture-cf-atlas.md) for pipeline mechanics
2. Read [`guides/atlas-operations.md`](../../../../.claude/skills/conda-forge-expert/guides/atlas-operations.md) for operational cadence
3. Common operations:
   - `pixi run -e local-recipes bootstrap-data --status` — current state
   - `pixi run -e local-recipes atlas-phase <ID>` — single-phase refresh
   - `pixi run -e local-recipes staleness-report` — find behind-upstream feedstocks

### Path G: I'm working on one of the five `pyforge` distributions

1. Read [architecture.md](./architecture.md) § 3 Part 5 and [source-tree-analysis.md](./source-tree-analysis.md) § Part 5
2. Read that package's Spec under its own project (`_bmad-output/projects/pyforge-<name>/planning-artifacts/specs/`)
3. Use its **isolated** env: `pixi run --frozen -e pyforge-<name> pyforge-<name>-test`. Never mix a product feature into a factory env — the `no-default-feature` isolation is what lets the Python floors diverge.

---

## Critical Facts (Memorize These)

Surprising or non-obvious facts that AI agents and humans both get wrong.

1. **`recipes/` holds 1,664 recipe dirs (933 v1 `recipe.yaml` + 1,024 v0 `meta.yaml`; 300 carry both) — they are OUTPUTS, not part of the rebuild target.** A dir carrying both formats is the sanctioned transitional shape, not a violation: a v0 feedstock keeps `meta.yaml` until its v0→v1 switch completes.

2. **Never mix `recipe.yaml` and `meta.yaml` in the same build run.** The tooling rejects mixed-mode runs.

3. **`JFROG_API_KEY` leaks to every host when set.** `_http.py`'s `auth_headers_for()` checks it before any host inspection. Unset it before commands that hit external hosts, or scope it to a subshell. Still the system's most consequential security constraint.

4. **Step 8b (`prepare_submission_branch`) is the only human checkpoint.** `submit_pr` is ungated; the human must inspect the fork branch URL between them. The branch convention is `add-recipe-<name>`.

5. **`STD-001` (missing `stdlib("c")`) is the most common conda-forge auto-rejection.** Any `compiler(...)` requires it.

6. **`noarch: python` requires the LIST form for the test matrix**: `[${{ python_min }}.*, "*"]`, not a single string (lint code TEST-002).

7. **The MCP server is NOT auto-discovered.** It is registered by hand in **`~/.claude.json`** under `mcpServers.conda_forge_server`, with machine-absolute paths into `.pixi/envs/local-recipes/`. There is no `.mcp.json` in the repo and this is deliberate, not deferred work. **Consequence: a fresh clone gets zero conda-forge MCP tools until someone edits `~/.claude.json`.**

8. **The atlas pipeline is 22 executable phases: B/B.5/B.6/C/C.5/D/O/P/Q/R/S/E/E.5/F/G/G'/H/J/K/L/M/N.** Two traps: (a) **Phase T was CANCELLED** pre-implementation in v8.6.0 Wave C — any "B → T" framing is wrong; (b) `atlas-phases-overview.md` catalogs **23** because it documents a runner-less conceptual "Phase I" side-table (no runner, no `PHASES` entry). **22 executable, 23 cataloged.** *(`bmad-groundtruth` also reported 23 until 2026-07-25, when `phase_count()` was fixed to read the `PHASES` registry instead of regexing `def phase_` — which had also matched `phase_r_upsert_one`, a per-row helper. It now reports 22.)*

9. **19 pixi envs in two families.** Factory (9): `linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes` (default), `vuln-db`, `gcloud`. Product (6, all `no-default-feature`): `pyforge-warden`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-scribe`, `pyforge-herald`, `bmad-ui`.

10. **Two PR CI gates, both always-on.** Any change outside `recipes/` needs the **`maintenance`** label; any `pixi.toml` change needs a regenerated `environment.yaml` (`pixi project export conda-environment -e build > environment.yaml`) — and **that check is ungated by the label**. Also: `gh pr create` must pass `--repo rxm7706/local-recipes`.

11. **Every conda-forge BMAD effort runs a `bmad-retrospective` at closeout.** It updates SKILL.md / reference/ / guides / CHANGELOG and bumps the skill version. Not optional.

12. **Drift-detection contract**: a tracked doc re-syncs when the skill CHANGELOG **MINOR** exceeds its pin. PATCH bumps do not trigger re-sync.

13. **Parallel agents must never call `scripts/bmad-switch`.** The `.active-project` marker *and* the two `_bmad-output/` symlinks are per-working-tree global state — a mutex nobody holds. Address projects by physical path; pass `BMAD_ACTIVE_PROJECT=<slug>` per invocation; verify placement after writing, because the failure is silent.

14. **`pyforge` is a PEP 420 implicit namespace.** No package may add `src/pyforge/__init__.py` — it would shadow the other four.

15. **The Charter's vocabulary is binding.** The eight personas are **Smiths**; the five-field contract is **the Spec** (the word "kernel" is retired); the console is the **Guildhall**; **PyForge** in prose, `pyforge` in code.

16. **Build-failure loop has no hard cap, but 3 cycles without progress should escalate.** Repeated identical failures mean the diagnosis is wrong, not that another iteration is needed.

---

## Drift Status (last reconciled 2026-07-25)

| Asset | Pinned to | Live | Drift action |
|---|---|---|---|
| This living doc set (12) | v8.79.1 | conda-forge-expert v8.80.0 | None — reconciled 2026-07-25 |
| `project-context.md` | v8.79.1 | v8.79.1 | None — reconciled 2026-07-25 |
| `PRD.md` / `epics.md` (plan) | v8.79.0 | v8.79.1 | **Outstanding** — structural re-sync via `bmad-correct-course` not run in this pass |
| Gate snapshots (2) | dated | — | By design: a gate is only meaningful re-run, never number-patched |
| Schema (Part 2 cf_atlas) | v29 | v29 | None |
| `SKILL.md` frontmatter / `MANIFEST.yaml` | v7.0.0 | v8.79.1 canonical | **Live defect** — both still stamp 7.0.0; no meta-test asserts version parity |

### Wrong claims corrected in this pass

Not staleness — statements that were false when written or falsified by an event the docs never absorbed:

- **10 dead documentation links** in this index alone (`docs/` was reorganised into `reference/`; five shipped specs were consolidated into `cfe-shipped-releases.md`).
- **`docs/copilot-to-api.md` was purged** from the repo (secret-leak remediation, 2026-07-24) yet was still linked and described.
- **"The atlas pipeline spans phases B → T … Phase T (in flight)"** — Phase T was cancelled pre-implementation, a fact `project-parts.json` recorded in the same doc set.
- **"The MCP server is auto-discovered by path convention; `.mcp.json` registration is deferred work"** — a fabricated mechanism describing a non-goal as a task.
- **A root `pyproject.toml`, a root `package.json`, an `output/` directory, and a `build.pid`** were all documented; none exists.
- **`.gitignore` "> 13k lines"** — it is 738.
- **`SDKs/` described as a committed binary** — nothing under it is tracked.
- **`bmad-distillator` and `bmad-create-ux-design`** were catalogued as installed skills; neither exists.
- **`_bmad/bmm/{1-analysis,2-plan-workflows,3-solutioning,4-implementation}/`** was described as a real tree a rebuild must recreate; `_bmad/bmm/` holds exactly two files.
- **"Strict AI provenance tracking (FX.8) guarantees an auditable trail"** — `.claude/hooks/post-tool-call.py` exists but **no `PostToolUse` hook is registered anywhere**. It is dead code.
- **Internal contradictions**: `~440 recipes` vs `1,602` in one document; a `v8.41.0` source pin in a body table vs `v8.79.0` in its own frontmatter; and a counts table in `source-tree-analysis.md` that understated the atlas schema by one version, the MCP tool count by four, and overstated the reference-doc count by two — each of the three contradicting the prose block directly above it in the same file.
- **`_http.py`'s own module docstring** contradicts its implementation on auth ordering, and the GitHub scheme is `Bearer`, not `token`.
- **A prior pass mass-clobbered historical schema labels** in `architecture-cf-atlas.md`, rewriting per-release migration headings (`v20→v21`, `v23→v24→v25`) to read "schema v29".

### Known conflicts left unresolved (reported, not adjudicated)

- **25 vs 28 atlas read CLIs** — `SKILL.md`'s table has 25 rows; `pyforge-atlas/semantic/__init__.py` says 28. No single authority.
- **9 vs 10 lifecycle steps** — `SKILL.md` documents 9 numbered steps + 3 lettered sub-steps; `CLAUDE.md` calls it "the 10-step loop".
- **`docs/specs/cfe-atlas-datapipeline-kedro-migration.md`** — frontmatter says `status: shipped`, its § 1 table still says "Remaining: Waves E–H".
- **`scripts/bmad_drift_check.py`'s module docstring lists 7 finding kinds; the code emits 16.**

---

## Verification Recap

This index and its 11 companion documents were reconciled against:

- Live filesystem (`find` / `ls` / `wc -l` / `git ls-files`)
- Source code (`grep` for `@mcp.tool`, `PHASES`, `SCHEMA_VERSION`, `^### G\d+`)
- `pixi.toml` + `pixi task list --machine-readable`
- Skill CHANGELOG (v8.79.1, 2026-07-23)
- `pixi run -e local-recipes bmad-drift-check` / `bmad-groundtruth`
- `scripts/spec_surface_check.py`

**Unverifiable in this checkout (marked in place, not asserted):** everything that depends on a built `cf_atlas.db` — `.claude/data/conda-forge-expert/` does not exist here, so row counts, `phases_run`, and performance tables are documented shapes, not observations. Likewise the Tier-3 retrospective corpus (`implementation-artifacts/retros/`) is gitignored and absent.

**Outstanding risks / follow-ups:**

- **`_http.py` cross-host credential leak** — unresolved. `pyforge-atlas`'s Kedro catalog states the same leak is "FIXED, not ported" (per-dataset credentials); that is the target design for the eventual fix.
- **`SKILL.md` / `MANIFEST.yaml` still stamp `version: 7.0.0`** and no meta-test catches it.
- **`bmad-preflight` is broken** — references a script that does not exist.
- **AI provenance hook is unwired** — one line in `.claude/settings.json` would activate it.
- **`src/sentinel/knowledge/` is largely inert** — `pixi.toml` wires 14 `wiki-*` tasks against 9 crew modules but only `compilation_crew.py` exists, `crews/` has no `__init__.py`, and that module has no `__main__` guard.
- **Plan pair (`PRD.md` / `epics.md`) has not absorbed Part 5.**

**Recommended next steps:**

1. Re-stamp the baseline: `pixi run -e local-recipes bmad-drift-check -- --write-baseline` (SYNC-RUNBOOK Step 3).
2. Run `bmad-correct-course` → `bmad-prd` / `bmad-create-epics-and-stories` to bring the plan pair onto the five-part model.
3. Consider a dedicated `architecture-pyforge-packages.md` for Part 5.

---

## Brownfield PRD Command

```
# In Claude Code:
"/bmad-prd"
# Then point at: _bmad-output/projects/local-recipes/planning-artifacts/index.md
```

> `bmad-create-prd`, `bmad-edit-prd`, `bmad-validate-prd` and `bmad-create-architecture` are **deprecated** thin wrappers slated for removal in v7. Use `bmad-prd` and `bmad-architecture`.

---

## Document Set Stats

| Metric | Value |
|---|---|
| Tracked living docs | **12** (11 markdown + `project-parts.json`) |
| Tracked plan docs | 2 (`PRD.md`, `epics.md`) |
| Dated gate snapshots | 2 (`validation-report-PRD.md`, `implementation-readiness-report.md`) |
| Specs owned by this project | 8 (of 22 across 14 BMAD projects) |
| Change history | 9 sprint-change-proposals under `change-history/` |
| Frozen archive | 2 PRFAQ + 4 research studies + 1 campaign record |
| Total files classified by the detector | 75 |
| Originally generated | 2026-05-12 |
| Last reconciled | **2026-07-25** |
| Generator | `bmad-document-project` → `bmad-generate-project-context` → `bmad-index-docs` |
| Source pin | conda-forge-expert **v8.79.1** |
