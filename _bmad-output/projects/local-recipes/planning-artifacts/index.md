---
doc_type: master-index
project_name: local-recipes
date: 2026-05-12
repository_type: monorepo
parts: 4
docs_generated: 10
source_pin: 'conda-forge-expert v7.8.1'
---

# `local-recipes` — Master Documentation Index

This index is your **primary entry point** for AI-assisted development on `local-recipes`. When a Brownfield PRD, story breakdown, or BMAD planning workflow needs the architecture and feature inventory of this repo, point them at this file.

The document set was produced 2026-05-12 by `bmad-document-project` (Path 3: hand-authored using existing sources, with the skill's output structure as template). Source pin: **conda-forge-expert v7.8.1** (re-synced from v7.7 on 2026-05-12 via `bmad-correct-course`; see `sprint-change-proposal-2026-05-12.md`).

---

## Project Overview

- **Type:** monorepo with **4 logical parts**
- **Primary language:** Python 3.12
- **Build engine:** Pixi + rattler-build
- **Default pixi env:** `local-recipes` (8 envs total)
- **Recipe corpus:** 1,415 v1 recipes (outputs; NOT part of the rebuild target)
- **Skill version:** v7.7.2 (pinned to v7.7 MINOR)

> See **[project-overview.md](./project-overview.md)** for the full executive summary, technology stack, and four-part decomposition.

---

## Quick Reference by Part

| Part | Display name | Type | Architecture doc |
|---|---|---|---|
| 1 | **conda-forge-expert** skill | library | [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md) |
| 2 | **cf_atlas** data pipeline | data | [architecture-cf-atlas.md](./architecture-cf-atlas.md) |
| 3 | **FastMCP server** | backend | [architecture-mcp-server.md](./architecture-mcp-server.md) |
| 4 | **BMAD infrastructure** | infra | [architecture-bmad-infra.md](./architecture-bmad-infra.md) |

---

## Generated Documentation

| # | Document | What it covers |
|---|---|---|
| 1 | [project-overview.md](./project-overview.md) | System framing, monorepo structure, four-part decomposition, cross-cutting concerns, getting-started orientation |
| 2 | [source-tree-analysis.md](./source-tree-analysis.md) | Annotated directory tree at 5 levels, entry-points table, critical files |
| 3 | [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md) | Part 1: 3-tier scripts/wrappers/data architecture, 10-step autonomous loop, 42 Tier 1 scripts, 41 templates / 13 ecosystems, build failure protocol, Recipe Authoring Gotchas G1-G6 |
| 4 | [architecture-cf-atlas.md](./architecture-cf-atlas.md) | Part 2: 17 pipeline phases, schema v19 (11 tables), TTL gates, S3+cf-graph offline backends, performance characteristics, failure modes |
| 5 | [architecture-mcp-server.md](./architecture-mcp-server.md) | Part 3: 35 MCP tools, thin-subprocess-wrapper pattern, auto-discovery + deferred `.mcp.json`, BMAD-agent invocation flow |
| 6 | [architecture-bmad-infra.md](./architecture-bmad-infra.md) | Part 4: 6-layer config merge, active-project resolution, 65 installed skills, BMAD↔CFE integration rules |
| 7 | [integration-architecture.md](./integration-architecture.md) | 7 integration contracts, cross-cutting `_http.py` auth chain, JFROG leak, vuln-db env separation, end-to-end recipe-authoring flow |
| 8 | [development-guide.md](./development-guide.md) | Pixi tasks cheatsheet (~50 tasks), manual recipe workflow, MCP server invocation, testing, debugging |
| 9 | [deployment-guide.md](./deployment-guide.md) | Air-gap + JFrog setup, env-var overrides, JFROG_API_KEY mitigation patterns, vuln-db env in JFrog environments |
| 10 | [index.md](./index.md) | This file — master navigator |
| — | [project-parts.json](./project-parts.json) | Machine-readable: 4 parts with root paths / key tech / pixi envs / subdirectory inventory, 7 integration points, rebuild build order |

**Validation + change-management artifacts** (produced by BMAD skills as the doc set evolves):

| Document | When written | What it captures |
|---|---|---|
| [validation-report-PRD.md](./validation-report-PRD.md) | `bmad-validate-prd` | 13-dimension PRD validation. Verdict history: REVISE (initial) → APPROVED (post tentative-decisions) → APPROVED (re-validated 2026-05-12 post v7.8.1 sync). |
| [implementation-readiness-report.md](./implementation-readiness-report.md) | `bmad-check-implementation-readiness` | Cross-artifact alignment check across PRD + architecture + epics + project-context. Verdict: READY. |
| [epics.md](./epics.md) | `bmad-create-epics-and-stories` | 13 epics, ~193 stories, 5 waves. |
| [sprint-change-proposal-2026-05-12.md](./sprint-change-proposal-2026-05-12.md) | `bmad-correct-course` (2026-05-12) | Documents the v7.7.2 → v7.8.1 sync — env-var additions, phase architecture changes, `_http.py` surface expansion. Records why this doc set's `source_pin` was bumped and which artifacts received substantive vs pin-only updates. |

---

## Existing Documentation (Inputs to This Set)

The above documents are syntheses of these primary sources. A rebuild should treat each source as authoritative for what it covers; this set is the structural map.

### Repo-wide
- [`CLAUDE.md`](../../../../CLAUDE.md) — repo-wide AI agent guidance, BMAD↔CFE integration rules
- [`README.md`](../../../../README.md) — human-facing intro
- [`pixi.toml`](../../../../pixi.toml) — 8 envs, ~50 pixi tasks, build features

### Project-scoped (this project)
- [`project-context.md`](../project-context.md) — foundational rules every BMAD agent reads on spawn (v7.8.1-pinned, 63 rules)
- [`implementation-artifacts/deferred-work.md`](../implementation-artifacts/deferred-work.md) — cross-spec deferred items
- [`implementation-artifacts/spec-cursor-sdk-local-recipe.md`](../implementation-artifacts/spec-cursor-sdk-local-recipe.md) — cursor-sdk recipe spec
- [`implementation-artifacts/spec-atlas-phase-f-s3-air-gap.md`](../implementation-artifacts/spec-atlas-phase-f-s3-air-gap.md) — Phase F S3 backend spec

### Part 1 (skill)
- [`.claude/skills/conda-forge-expert/SKILL.md`](../../../../.claude/skills/conda-forge-expert/SKILL.md) — primary spine (914 lines)
- [`.claude/skills/conda-forge-expert/INDEX.md`](../../../../.claude/skills/conda-forge-expert/INDEX.md) — task→tool navigator
- [`.claude/skills/conda-forge-expert/CHANGELOG.md`](../../../../.claude/skills/conda-forge-expert/CHANGELOG.md) — release history (canonical drift-detection source)
- [`.claude/skills/conda-forge-expert/reference/`](../../../../.claude/skills/conda-forge-expert/reference/) — 11 deep-reference files
- [`.claude/skills/conda-forge-expert/guides/`](../../../../.claude/skills/conda-forge-expert/guides/) — 8 workflow guides
- [`.claude/skills/conda-forge-expert/quickref/`](../../../../.claude/skills/conda-forge-expert/quickref/) — 2 quick-reference files

### Architecture (existing docs)
- [`docs/mcp-server-architecture.md`](../../../../docs/mcp-server-architecture.md) — MCP server design (preceded Part 3 doc above)
- [`docs/enterprise-deployment.md`](../../../../docs/enterprise-deployment.md) — air-gap + JFrog operational reference
- [`docs/developer-guide.md`](../../../../docs/developer-guide.md) — original developer guide
- [`docs/copilot-to-api.md`](../../../../docs/copilot-to-api.md) — Copilot subscription as local model backend
- [`docs/bmad-setup-plan.md`](../../../../docs/bmad-setup-plan.md) — BMAD installation rationale

### Specs (BMAD-consumable, planned but not all implemented)
- [`docs/specs/atlas-phase-f-s3-backend.md`](../../../../docs/specs/atlas-phase-f-s3-backend.md) — Wave 1 shipped in v7.6.0; Waves 2-3 deferred
- [`docs/specs/conda-forge-tracker.md`](../../../../docs/specs/conda-forge-tracker.md) — 13 stories, channel-aware migration path
- [`docs/specs/copilot-bridge-vscode-extension.md`](../../../../docs/specs/copilot-bridge-vscode-extension.md) — sideload-only VS Code extension
- [`docs/specs/db-gpt-conda-forge.md`](../../../../docs/specs/db-gpt-conda-forge.md) — 13-story DB-GPT packaging plan
- [`docs/specs/claude-team-memory.md`](../../../../docs/specs/claude-team-memory.md) — team-memory subsystem

---

## Getting Started Paths

Pick the path that matches your situation.

### Path A: I'm new to this repo

1. Read [project-overview.md](./project-overview.md) (~10 min)
2. Skim [source-tree-analysis.md](./source-tree-analysis.md) to orient on file locations
3. Read [development-guide.md](./development-guide.md) § Prerequisites + First-time setup
4. Run `pixi run health-check` to verify your environment
5. Optional: skim one architecture doc per part to deepen understanding

### Path B: I'm rebuilding this repo from scratch using BMAD-METHOD

Recommended build order from `project-parts.json`:

1. **First: Part 4 (BMAD infrastructure)** — install BMAD-METHOD, set up 6-layer config, create multi-project layout. See [architecture-bmad-infra.md](./architecture-bmad-infra.md) § Rebuild checklist.
2. **Second: Part 1 (conda-forge-expert skill)** — author the 42 Tier 1 scripts, 34 wrappers, SKILL.md, reference/, guides/, templates/, tests/. See [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md) § Rebuild checklist.
3. **Third: Part 2 (cf_atlas)** — implement the 17 phases inside Part 1's `scripts/`. Schema v19 from the start. See [architecture-cf-atlas.md](./architecture-cf-atlas.md) § Rebuild checklist.
4. **Fourth: Part 3 (MCP server)** — author `conda_forge_server.py` with 35 `@mcp.tool()` thin wrappers over Tier 1. See [architecture-mcp-server.md](./architecture-mcp-server.md) § Rebuild checklist.
5. **Throughout: enforce the integration contracts** — see [integration-architecture.md](./integration-architecture.md) § The 7 Integration Contracts.
6. **Plan with `bmad-create-epics-and-stories`** once oriented — point the skill at this index file. Expect ~10-15 epics and 100-150+ stories.

### Path C: I'm authoring a new recipe right now

1. Confirm active project: `scripts/bmad-switch --current` → `local-recipes`
2. In Claude Code: trigger `conda-forge-expert` skill (or it auto-activates on the keyword)
3. Follow the 10-step autonomous loop; step 8b is your human checkpoint
4. See [development-guide.md](./development-guide.md) § Authoring a New Recipe (Manual Workflow) for the shell-driven version

### Path D: I'm debugging a build failure

1. Get the most recent log: `ls -t build_artifacts/*/bld/rattler-build_<name>_*/work/conda_build.log | head -1`
2. Run `pixi run analyze-failure -- <log>`
3. Check Recipe Authoring Gotchas in [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md) § Recipe Authoring Gotchas
4. See [development-guide.md](./development-guide.md) § Debugging Common Issues

### Path E: I'm setting up an air-gapped / JFrog deployment

1. Read [deployment-guide.md](./deployment-guide.md) end-to-end
2. Pay attention to § "The JFROG_API_KEY Cross-Host Leak (Critical Constraint)"
3. Use the deployment checklist
4. Cross-reference [`docs/enterprise-deployment.md`](../../../../docs/enterprise-deployment.md) for JFrog REST API setup

### Path F: I'm running the atlas pipeline / cf_atlas-intelligence queries

1. Read [architecture-cf-atlas.md](./architecture-cf-atlas.md) for pipeline mechanics
2. Read [`.claude/skills/conda-forge-expert/guides/atlas-operations.md`](../../../../.claude/skills/conda-forge-expert/guides/atlas-operations.md) for operational cadence
3. Common operations:
   - `pixi run -e local-recipes bootstrap-data --status` — current state
   - `pixi run -e local-recipes atlas-phase <ID>` — single-phase refresh
   - `pixi run -e local-recipes staleness-report` — find behind-upstream feedstocks

---

## Critical Facts (Memorize These)

These are surprising or non-obvious facts that AI agents and humans both get wrong. They appear in multiple documents but are consolidated here.

1. **`recipes/` contains 1,415 recipes — they are OUTPUTS, not part of the rebuild target.** The factory rebuilds the factory; recipes are re-authored using the rebuilt factory.

2. **Always use v1 `recipe.yaml`, NEVER `meta.yaml` in new recipes.** Mixing the two formats in a build run is automatically rejected. v0 is only for migration source material.

3. **`JFROG_API_KEY` leaks to every host when set.** Unset before commands that hit external hosts (`submit_pr`, `update_cve_database`, etc.) or use subshell scoping. This is the system's most consequential security constraint.

4. **Step 8b (`prepare_submission_branch`) is the only human checkpoint.** `submit_pr` is ungated; the human must inspect the fork branch URL between 8b and step 9. The autonomous loop will keep going unprompted.

5. **`STD-001` (missing stdlib) is the most common conda-forge auto-rejection.** Any `compiler(...)` requires `stdlib("c")`. Exception: `go-nocgo`.

6. **`noarch: python` requires the LIST form for test python_version**: `[${{ python_min }}.*, "*"]` not a single string (lint code TEST-002).

7. **The MCP server is auto-discovered by path convention.** `.mcp.json` registration is deferred work; not currently present.

8. **17 phases (B through N), not 15.** The atlas pipeline has 17 distinct phase IDs once you count B.5, B.6, C.5, E.5, G'.

9. **8 pixi envs** — `linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes` (default), `vuln-db`.

10. **Every conda-forge BMAD effort runs a `bmad-retrospective` at closeout.** Updates SKILL.md / reference/ / guides / CHANGELOG. Not optional.

11. **Drift-detection contract**: project-context.md re-syncs when skill CHANGELOG MINOR exceeds the pin. PATCH bumps do NOT trigger re-sync.

12. **`tree-sitter-<lang>` PyPI sdists strip `parser.h` inconsistently.** Default to GitHub-tag source for language packages that vendor the C parser library (Gotcha G5).

13. **`get_build_summary` has false negatives** — when it reports "build may have crashed", read `conda_build.log` directly before believing it (Gotcha G6).

14. **Force pushes default to `--force-with-lease`** in `submit_pr` / `prepare_pr`. Errors on divergent remote instead of overwriting silently.

15. **Build-failure loop has no hard cap, but 3 cycles without progress should escalate to user.** Repeated identical failures mean the diagnosis is wrong.

---

## Drift Status (as of 2026-05-12)

| Asset | Pinned to | Current | Drift action |
|---|---|---|---|
| project-context.md | v7.7 (MINOR) | v7.7.2 (PATCH) | None needed — PATCH bumps don't trigger re-sync |
| This doc set | v7.7 (MINOR) | v7.7.2 (PATCH) | None needed |
| MANIFEST.yaml (Part 1 portability) | v7.0.0 | v7.0.0 | None |
| Schema (Part 2 cf_atlas) | v19 | v19 | None |

When the skill ships v7.8.0+: re-verify project-context.md § Recipe Format / MCP Lifecycle / Anti-Patterns, then this doc set.

---

## Verification Recap

This index and its 9 companion documents were produced via the hybrid Path 3 of `bmad-document-project` (skill structure as template, content authored from primary sources). Counts and structural claims were verified against:

- Live filesystem (`find` / `ls` / `wc -l`)
- Source code (`grep` for `@mcp.tool`, `PHASES`, `SCHEMA_VERSION`, etc.)
- Skill CHANGELOG TL;DR (v7.7.2)
- Existing repo docs (`CLAUDE.md`, `project-context.md`, `docs/`)

**Outstanding risks / follow-ups**:

- **G6 doc drift**: `get_build_summary` false-negative gotcha is in CHANGELOG v7.7.1 but not yet promoted to SKILL.md § Recipe Authoring Gotchas — next CFE retro should close this gap.
- **`.mcp.json` deferred**: MCP server discovery relies on path convention; explicit registration is deferred per `docs/specs/claude-team-memory.md` Q13.
- **`_http.py` host-aware refactor deferred**: the JFROG_API_KEY cross-host leak is mitigated by env-var hygiene; long-term fix is in auto-memory `project_http_jfrog_unconditional_injection.md` but not yet implemented.
- **Phase K secondary rate-limit mitigation**: tracked in `project_phase_k_secondary_rate_limit.md` auto-memory; current cron schedule with `--reset-ttl` spreads load but isn't a permanent fix.

**Recommended next steps for the rebuild planning effort**:

1. Run `bmad-create-prd` against this doc set to produce a unified PRD (currently scattered across CLAUDE.md, docs/, and skill files).
2. Run `bmad-create-architecture` to produce the unified architecture doc (currently in 4 parts + 1 integration).
3. Run `bmad-create-epics-and-stories` to produce the implementation work-breakdown (~10-15 epics expected).
4. Begin implementation in dependency order: Part 4 → Part 1 → Part 2 → Part 3.

---

## Brownfield PRD Command

When ready to plan new features against the rebuilt system, run the PRD workflow and provide this index as the architecture reference:

```
# In Claude Code:
"/bmad-create-prd"
# Then point at: _bmad-output/projects/local-recipes/planning-artifacts/index.md
```

---

## Document Set Stats

| Metric | Value |
|---|---|
| Total documents | 10 (9 markdown + 1 JSON) |
| Total markdown lines | ~3,000 |
| Generated | 2026-05-12 |
| Generator | `bmad-document-project` (Path 3 hybrid) |
| Source pin | conda-forge-expert v7.8.1 |
| Verification | live filesystem + source code grep + CHANGELOG cross-reference |
