---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-05-12
author: rxm7706
trigger_type: release-driven
trigger_release: conda-forge-expert v7.8.0 + v7.8.1
scope: documentation-sync
classification: Minor
mode: Batch
status: pending-approval
input_docs:
  - _bmad-output/projects/local-recipes/planning-artifacts/PRD.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-conda-forge-expert.md
  - _bmad-output/projects/local-recipes/planning-artifacts/deployment-guide.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
ground_truth:
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md
  - .claude/skills/conda-forge-expert/config/skill-config.yaml
---

# Sprint Change Proposal: v7.8.x BMAD Artifact Sync

## 1. Issue Summary

The conda-forge-expert skill shipped two releases in rapid succession on 2026-05-12:

- **v7.8.0** — "Atlas hardening pass" introducing enterprise-routing parity across 7 additional registries, GraphQL Phase K, Phase F rate-limit safety, per-registry Phase L caps, atomic file writes, and incremental commits across B5/E/E5/M.
- **v7.8.1** — "Audit close-out pass" addressing every remaining HIGH/MEDIUM/LOW finding from the v7.8.0 deep audit: Phase H rate-limit safety, OSV env-var overrides, GitLab/Codeberg/GitHub-API resolvers, Phase E TTL override, Phase N rate-limit detection, `fetch_to_file_resumable` + cve_manager Range/resume.

The BMAD planning artifacts under `_bmad-output/projects/local-recipes/` still pin `source_pin: 'conda-forge-expert v7.7'` and predate these releases. **Net effect:** an AI agent or human reading the planning artifacts to understand current behavior would be misled about (a) which env vars exist, (b) what default concurrencies are, and (c) which architectural patterns are in play.

Evidence:
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — TL;DR sections for v7.8.0 and v7.8.1 carry the full delta inventory.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml` — `version: 7.8.1`.
- 17 files under `_bmad-output/projects/local-recipes/` reference `v7.7`.
- 403 tests pass against the v7.8.1 implementation (was 339 at v7.7.2).

## 2. Impact Analysis

### Epic Impact
**None.** The epics are at the right altitude that v7.8.x changes don't invalidate scope. Every epic remains valid; no epic is obsoleted; no new epics are needed; no reordering or repriority required.

### Story Impact
**None.** v7.8.x is implementation drift, not story scope.

### Artifact Conflicts
**Documentation drift across 16 files.** Broken into two classes:

- **Substantive updates (4 files)** — body content states facts that changed:
  - `deployment-guide.md` — env-var table is missing 15+ new vars; concurrency defaults are stale.
  - `architecture-cf-atlas.md` — Phase K still described as REST fanout; missing _http.py surface expansion.
  - `architecture-conda-forge-expert.md` — missing pointer to new `reference/atlas-phase-engineering.md`.
  - `architecture.md` (unified roll-up) — propagates from above.

- **Pin-only frontmatter (12 files)** — body content unaffected:
  - `PRD.md`, `index.md`, `project-overview.md`, `integration-architecture.md`, `development-guide.md`, `architecture-mcp-server.md`, `architecture-bmad-infra.md`, `epics.md`, `source-tree-analysis.md`, `implementation-readiness-report.md`, `validation-report-PRD.md`, `project-parts.json`.

### Technical Impact
- **No code changes required** — v7.8.x is already shipped and tested.
- **No re-deployment required** — env vars are opt-in; concurrency defaults are runtime tunables.
- **Re-validation needed** post-edit:
  - `bmad-validate-prd` (after PRD frontmatter pin bump).
  - `bmad-index-docs` (after all edits, to refresh index cross-references).

## 3. Recommended Approach

**Direct Adjustment.** Apply the documented edits in place. No rollback, no MVP review needed. Classification: **Minor** (per the workflow's scope rubric — direct implementation by the Developer agent / human-in-the-loop).

**Rationale:**
- Changes are well-bounded and CHANGELOG-evidenced.
- No epic / story / requirement changes.
- All env-var additions are backward-compatible (existing setups work unchanged).
- The one breaking change in v7.8.0 (Phase L return-dict field rename `concurrency` → `per_source_workers`) has no internal consumers.

**Effort estimate**: ~30 minutes of mechanical edits.
**Risk**: Low. The substantive-edit set is limited to 4 files with surgical changes; the other 12 are pin-only bumps.
**Timeline impact**: None — this is housekeeping after a shipped release.

## 4. Detailed Change Proposals

### A. Substantive updates

#### A.1 `deployment-guide.md` — env-var table expansion

OLD: env-var table covers `CONDA_FORGE_BASE_URL`, `PYPI_BASE_URL`, `GITHUB_BASE_URL`, `ANACONDA_API_BASE`, `S3_PARQUET_BASE_URL`, and a handful of phase tunables.

NEW: add 15 new enterprise-routing env vars and 3 operational tunables:
- **Enterprise routing**: `NPM_BASE_URL`, `CRAN_BASE_URL`, `CPAN_BASE_URL`, `LUAROCKS_BASE_URL`, `CRATES_BASE_URL`, `RUBYGEMS_BASE_URL`, `MAVEN_BASE_URL`, `NUGET_BASE_URL`, `GITHUB_API_BASE_URL` (covers REST + GraphQL — GHES set to `https://<ghes>/api`), `GITLAB_API_BASE_URL`, `CODEBERG_API_BASE_URL`, `ANACONDA_API_BASE_URL` (legacy alias `ANACONDA_API_BASE` still honored), `OSV_API_BASE_URL`, `OSV_VULNS_BUCKET_URL`, `ATLAS_CFGRAPH_TTL_DAYS`.
- **Operational tuning**: `PHASE_K_GRAPHQL_DISABLED`, `PHASE_K_GRAPHQL_BATCH_SIZE` (default 100), `PHASE_L_CONCURRENCY_<SOURCE>` per-registry.
- Document the changed defaults: `PHASE_F_CONCURRENCY` 8→3, `PHASE_H_CONCURRENCY` 8→3.
- Cross-reference `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` as the engineering rule book.

Rationale: closes the air-gap deployment gap. Previously some upstream services had no env override; v7.8.x added all of them.

#### A.2 `architecture-cf-atlas.md` — phase architecture updates

OLD: Phase K described as REST fanout with N concurrent workers per repo.

NEW:
- Phase K resolves GitHub via batched GraphQL (`_phase_k_github_graphql_batch`, ~100 repos per POST). GitLab + Codeberg still REST.
- New `_http.py` surface: `auth_headers_for(url)`, `atomic_writer` / `atomic_write_bytes` / `atomic_write_text`, `fetch_to_file_resumable(target, urls, ...)`, plus 10 new `resolve_*_urls` resolvers.
- Phase L: per-registry concurrency caps (npm=4, nuget=4, cran=cpan=luarocks=maven=2, crates=1, rubygems=1); sequential across registries.
- Phase F/H/N: Retry-After parsing + ±25% jitter + rate-limit detection.
- Pointer to `reference/atlas-phase-engineering.md` as the canonical engineering rule book (9 patterns).

Rationale: the architecture doc would otherwise misdescribe the Phase K mechanism (the GraphQL batch is the single biggest behavioral change in v7.8.0).

#### A.3 `architecture-conda-forge-expert.md` — reference doc + surface

OLD: lists existing skill reference docs (recipe-yaml-reference, pinning-reference, etc.).

NEW: add `reference/atlas-phase-engineering.md` to the list with one-line summary. Note `_http.py` is now the canonical shared-utility module (resolvers + auth + atomic IO + resumable streaming fetch).

Rationale: the new reference doc is the on-ramp for anyone authoring or refactoring a phase. It needs an entry point.

#### A.4 `architecture.md` (unified) — roll-up

Propagate the cf-atlas + conda-forge-expert sub-doc changes upward. Bump any `(v7.7)` or `(v7.7.2)` section-version markers.

### B. Pin-only frontmatter bumps (12 files)

For each file: `source_pin: 'conda-forge-expert v7.7'` → `'conda-forge-expert v7.8.1'`. For `project-parts.json`: bump the `source_pin` JSON field equivalently.

No body changes.

## 5. Implementation Handoff

**Scope classification**: **Minor**
**Recipient**: Developer agent (current Claude Code session)
**Deliverables**:
1. Substantive edits applied to the 4 files in §4.A.
2. Pin-only bumps applied to the 12 files in §4.B.
3. `project-context.md` updated separately (hand-edited per its `maintenance_model` frontmatter).
4. `bmad-validate-prd` re-run after PRD pin bump.
5. `bmad-index-docs` re-run after all edits land.
6. Spot-check `implementation-artifacts/spec-atlas-phase-f-s3-air-gap.md` for "shipped / superseded" status.

**Success criteria**:
- Every `_bmad-output/projects/local-recipes/` file shows `source_pin: 'conda-forge-expert v7.8.1'` (or equivalent for JSON).
- `deployment-guide.md` env-var table includes all 15 new enterprise-routing vars.
- `architecture-cf-atlas.md` describes Phase K as GraphQL batch.
- `architecture-conda-forge-expert.md` references `reference/atlas-phase-engineering.md`.
- `bmad-validate-prd` returns clean.
- No spec under `implementation-artifacts/` claims work that v7.8.x has already shipped (status: "shipped" note added if applicable).
