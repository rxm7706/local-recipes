---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-05-13
author: rxm7706
trigger_type: release-driven
trigger_release: conda-forge-expert v7.9.0
scope: documentation-sync
classification: Minor
mode: Batch
status: approved
approved_by: rxm7706
approved_date: 2026-05-13
input_docs:
  - _bmad-output/projects/local-recipes/planning-artifacts/PRD.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-conda-forge-expert.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-mcp-server.md
  - _bmad-output/projects/local-recipes/planning-artifacts/epics.md
  - _bmad-output/projects/local-recipes/planning-artifacts/source-tree-analysis.md
  - _bmad-output/projects/local-recipes/planning-artifacts/project-parts.json
  - _bmad-output/projects/local-recipes/implementation-artifacts/spec-atlas-pypi-universe-split.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
ground_truth:
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
  - .claude/skills/conda-forge-expert/reference/atlas-phases-overview.md
  - .claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md
  - .claude/skills/conda-forge-expert/config/skill-config.yaml
prior_proposal: sprint-change-proposal-2026-05-12.md
---

# Sprint Change Proposal: v7.9.0 Actionable-Scope Audit Sync

## 1. Issue Summary

The `conda-forge-expert` skill shipped **v7.9.0** on 2026-05-13, closing the
2026-05-13 actionable-scope audit driven by `docs/specs/atlas-pypi-universe-split.md`
via `bmad-quick-dev`. Closed 4 phase-denominator findings + 1 architectural
shift:

- **Phase H denominator one-line fix** — `_phase_h_eligible_pypi_names`
  selector gained `conda_name IS NOT NULL` + active + !archived. Cold-run
  denominator drops 672k → ~12k (56× cut). Closed bug where Phase H
  fetched `pypi.org/pypi/<name>/json` for ~660k `relationship='pypi_only'`
  rows and the downstream `upstream_versions` UPSERT silently discarded
  the results.
- **Schema v20 + `pypi_universe` side table** — new
  `pypi_universe(pypi_name, last_serial, fetched_at)` table separates
  PyPI directory data from the conda-actionable working set. Self-healing
  migration in `init_schema` moves existing `relationship='pypi_only'`
  rows from `packages` to `pypi_universe` idempotently (INSERT OR IGNORE
  + DELETE in one transaction).
- **Phase D split into daily-lean + TTL-gated universe upsert** — three
  helpers (`_phase_d_update_working_set`, `_phase_d_universe_is_fresh`,
  `_phase_d_upsert_universe`); legacy `INSERT INTO packages ... 'pypi_only'`
  branch removed entirely. New env tunables `PHASE_D_DISABLED`,
  `PHASE_D_UNIVERSE_DISABLED`, `PHASE_D_UNIVERSE_TTL_DAYS` (default 7).
- **Phase J + M archived-feedstock filter at write site** — Phase J
  builds an `inactive_feedstocks` skip-set; Phase M's `rows_to_process`
  SELECT gains the canonical triplet. Cleaner `whodepends` +
  `feedstock-health` outputs; no behavior change for read paths.
- **New `pypi-only-candidates` CLI + MCP tool** — surfaces
  `pypi_universe LEFT JOIN packages` so the 📋-open admin "what's on PyPI
  but not on conda-forge" catalog row flips to ✅ shipped.

PRD was already synced via `bmad-edit-prd` earlier in the same session
(v1.1.0 → v1.1.1, source_pin v7.8.1 → v7.9.0, 11 in-place edits + new
`edit_history` frontmatter). This proposal covers the remaining BMAD
planning artifacts.

Evidence:
- `.claude/skills/conda-forge-expert/CHANGELOG.md` § v7.9.0 — full delta
  inventory.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml` —
  `version: 7.9.0`.
- `_bmad-output/projects/local-recipes/implementation-artifacts/spec-atlas-pypi-universe-split.md`
  — status `done`, all 11 tasks `[x]`, baseline_commit recorded.
- `_bmad-output/projects/local-recipes/implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md`
  — streamlined retro per `CLAUDE.md` Rule 2.
- 29 new unit tests + 44 meta-tests pass (`pixi run -e local-recipes
  python -m pytest .claude/skills/conda-forge-expert/tests/unit/test_phase_h_eligible.py
  .claude/skills/conda-forge-expert/tests/unit/test_phase_j_m_archived.py
  .claude/skills/conda-forge-expert/tests/unit/test_schema_v20_migration.py
  .claude/skills/conda-forge-expert/tests/unit/test_phase_d_split.py
  .claude/skills/conda-forge-expert/tests/unit/test_pypi_only_candidates.py
  .claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py`).

## 2. Impact Analysis

### Epic Impact

**None substantive.** The v7.9.0 changes are post-implementation
refactors + one additive CLI; no epic is invalidated, none becomes
obsolete, no new epic is needed. `epics.md` only requires:
- Source-pin bump v7.8.1 → v7.9.0 in frontmatter.
- One new appended note in the "audit cadence" section (or equivalent)
  recording the 2026-05-13 audit as a closed effort, parallel to the
  v7.8.x retro lineage already present.

### Story Impact

**None.** v7.9.0 was shipped as a single bmad-quick-dev spec
(`spec-atlas-pypi-universe-split.md`), not an epic story. No epic
sprint backlog item is touched.

### Artifact Conflicts

**Documentation drift across 11 files.** Three classes:

- **Substantive updates (3 files)** — body content states facts that
  changed in v7.9.0:
  - `architecture-cf-atlas.md` — schema version table (v19 → v20), table
    count (11 → 12), Phase D body (single-branch → split daily-lean +
    TTL-gated universe), Phase H eligible-rows description, Phase J +
    Phase M archived-filter notes, new `pypi-only-candidates` entry in
    the read-side CLI table, new env tunables in the air-gap section.
  - `architecture-mcp-server.md` — tool count (35 → 36),
    `pypi_only_candidates` entry in the atlas-intelligence surface
    table.
  - `architecture-conda-forge-expert.md` — version bump (already touched
    by an earlier session edit; needs additional v7.9.0 entries:
    `pypi-only-candidates` in the daily-use CLI list; `atlas-phases-overview.md`
    + `atlas-actionable-intelligence.md` already in the reference list
    from prior session).

- **Pin-only frontmatter (5 files)** — body content unaffected, only
  `source_pin: v7.8.1` → `v7.9.0`:
  - `index.md`, `project-overview.md`, `integration-architecture.md`,
    `architecture.md` (unified roll-up), `architecture-bmad-infra.md`,
    `deployment-guide.md`, `development-guide.md`,
    `implementation-readiness-report.md`, `validation-report-PRD.md`.

- **Per-user direction, in-scope for this proposal (per `bmad-correct-course`
  invocation)**: `architecture-cf-atlas.md`, `architecture-conda-forge-expert.md`,
  `architecture-mcp-server.md`, `epics.md`. The remaining housekeeping
  pin-only bumps + `source-tree-analysis.md` + `project-parts.json` are
  routed as Minor scope to the Developer agent for direct edit
  (recommendation: bundle into the same commit as the substantive
  updates).

### Technical Impact

- **No code changes required** — v7.9.0 is already shipped, tested
  (29 new unit + 44 meta tests green), and the spec is `status: done`.
- **No re-deployment required** — schema v20 migration self-applies on
  next `init_schema`. Live-DB verification deferred to the next session
  per retro action item A1 (MCP server holds the DB write lock in the
  current session — not blocking, just deferred).
- **Re-validation needed** post-edit:
  - `bmad-validate-prd` re-run after PRD pin bump (already moved to
    v1.1.1; previous validation report verdict APPROVED stands).
  - `bmad-index-docs` re-run after all edits land (refreshes
    cross-references in `index.md`).

## 3. Recommended Approach

**Direct Adjustment.** Apply the documented edits in place. No
rollback, no MVP review needed. Classification: **Minor** (per the
workflow's scope rubric — direct implementation by the Developer
agent / current Claude Code session).

**Rationale:**
- Changes are well-bounded and CHANGELOG-evidenced.
- No epic / story / requirement changes (every change is documentation
  delta to reflect already-shipped + already-tested code).
- New env vars are backward-compatible (`PHASE_D_DISABLED`,
  `PHASE_D_UNIVERSE_DISABLED`, `PHASE_D_UNIVERSE_TTL_DAYS` all opt-in;
  the defaults match the v19 lean-mode behavior except for the universe
  upsert which is bounded by its own TTL).
- The one structural change in v7.9.0 (schema v20 migration moving
  pypi_only rows out of `packages`) is self-healing on first
  `init_schema` and idempotent on re-runs.

**Effort estimate**: ~20 minutes of mechanical edits — pattern is
identical to the 2026-05-12 sync that produced
`sprint-change-proposal-2026-05-12.md`.
**Risk**: Low. The substantive-edit set is 3 files with surgical
changes; the pin-only set is 9 files at one line each.
**Timeline impact**: None — this is housekeeping after a shipped release.

## 4. Detailed Change Proposals

### A. Substantive updates (3 files)

#### A.1 `architecture-cf-atlas.md` — schema + Phase D + new CLI

OLD: schema_version = 19; table count = 11 (packages + 10 supporting);
17 phases listed; Phase D body says "enumerate PyPI universe — inserts
`relationship='pypi_only'` rows"; Phase H eligible-rows description
silent on `conda_name` filter; Phase J + M lack archived-filter mention;
"17 CLIs" / "12 MCP tools" or equivalent counts; no `pypi-only-candidates`
entry.

NEW:
- **Schema**: bump SCHEMA_VERSION = 20; table count = 12 (packages + 11
  supporting incl. new `pypi_universe(pypi_name, last_serial, fetched_at)`).
- **Migration**: add note that v19→v20 self-migrates on next
  `init_schema`: moves `relationship='pypi_only'` rows from `packages`
  to `pypi_universe` via `INSERT OR IGNORE` + `DELETE` in one
  transaction; idempotent.
- **Phase D (refactored)**: now splits into daily-lean (always-on:
  update `pypi_last_serial` on conda-linked rows + name-coincidence
  match discovery) + TTL-gated universe upsert (default 7d). Legacy
  `INSERT INTO packages ... 'pypi_only'` branch removed entirely. New
  env tunables `PHASE_D_DISABLED`, `PHASE_D_UNIVERSE_DISABLED`,
  `PHASE_D_UNIVERSE_TTL_DAYS`.
- **Phase H eligible-rows**: gate now applies the canonical persona-filter
  triplet `conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0`
  (matches F/G/G'/K/L/N). Cold-run denominator drops from ~672k to
  ~12k. Note: in steady state post-v20, the `conda_name IS NOT NULL`
  clause is defense-in-depth — the migration has already removed
  pypi_only rows from `packages`.
- **Phase J**: pre-pass builds `inactive_feedstocks` set from
  `packages WHERE feedstock_archived=1 OR latest_status='inactive'`,
  skip clause inside the cf-graph tarball iteration. New
  `skipped_inactive_feedstocks` stat.
- **Phase M**: `rows_to_process` SELECT gains the canonical triplet at
  the write site (read paths already filter).
- **CLI count / new CLI**: bump count by +1; add `pypi-only-candidates`
  entry under the read-side / atlas-intelligence CLI table with
  description "Lists PyPI projects with no conda-forge equivalent —
  reads `pypi_universe LEFT JOIN packages` ordered by `last_serial DESC`.
  Flags `--limit`, `--min-serial`, `--json`. Empty-universe state
  prints actionable hint to run `atlas-phase D`."
- **Pointer**: ensure cross-link to `reference/atlas-phases-overview.md`
  (the persona-aligned per-phase index, added v7.9.x doc-cycle) is
  present in the cf-atlas doc.

Rationale: the architecture doc would otherwise misdescribe Phase D
(the single biggest behavioral change in v7.9.0) and miss the new
schema/table.

#### A.2 `architecture-mcp-server.md` — tool count + new tool entry

OLD: "35 MCP tools" / "The 35 Tools by Surface".

NEW:
- Bump tool count 35 → 36.
- Section header "The 36 Tools by Surface" (or whatever the analogous
  exact title is).
- Add `pypi_only_candidates(limit: int = 100, min_serial: int = 0)` row
  under the atlas-intelligence surface with description matching the
  PRD's F3.2 acceptance line.

Rationale: PRD F3.2 acceptance now says "36 tools enumerated in
`architecture-mcp-server.md`"; the architecture doc must match.

#### A.3 `architecture-conda-forge-expert.md` — version + CLI list

OLD: source_pin v7.8.1 (or wherever the current architecture doc sits);
daily-use CLI table reflects pre-v7.9.0 surface.

NEW:
- Frontmatter `source_pin: v7.9.0`.
- Daily-use CLI table: add `pypi-only-candidates` row.
- Reference doc list: confirm `reference/atlas-phases-overview.md`
  + `reference/atlas-actionable-intelligence.md` (renamed from
  `actionable-intelligence-catalog.md` earlier this session) are listed.

Rationale: this doc is the entry point for "what does the skill do?";
out-of-date CLI list / reference list misleads downstream readers.

### B. Epic + sprint-tracking changes

#### B.1 `epics.md` — frontmatter pin + audit lineage note

OLD: `source_pin: 'conda-forge-expert v7.8.1'` (or whatever version
the epics file is pinned to).

NEW:
- Frontmatter `source_pin: 'conda-forge-expert v7.9.0'`.
- Add a short lineage note in the "Cadence / version sync" section (or
  equivalent — typically next to where the v7.7 → v7.8.1 sync was
  recorded) stating: "2026-05-13: v7.9.0 actionable-scope audit shipped
  via `bmad-quick-dev`. Closed 4 phase-denominator findings + introduced
  `pypi-only-candidates` CLI + schema v20. Spec at
  `_bmad-output/.../implementation-artifacts/spec-atlas-pypi-universe-split.md`
  (`status: done`). Retro at
  `implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md`.
  No epic scope change; this is recorded as a between-epic audit, not
  a new epic."

Rationale: epics file is the canonical sprint-tracking layer; future
sprint planning reads the cadence/lineage section to understand what
shipped between formal epics.

### C. Out-of-scope-but-recommended bundle (Developer agent handoff)

Routed to the Developer agent in the same commit as A + B (Minor scope;
no additional review needed):

- **`source-tree-analysis.md`** — body-content additions for new files:
  - `.claude/skills/conda-forge-expert/scripts/pypi_only_candidates.py`
    (canonical CLI)
  - `.claude/scripts/conda-forge-expert/pypi_only_candidates.py` (thin
    wrapper)
  - `.claude/skills/conda-forge-expert/tests/unit/test_phase_h_eligible.py`,
    `test_phase_j_m_archived.py`, `test_schema_v20_migration.py`,
    `test_phase_d_split.py`, `test_pypi_only_candidates.py` (5 new test
    files)
  - Updates the entry-count and dependency-tree diagrams.
- **`project-parts.json`** — bump `version_pin: v7.8.1` → `v7.9.0`;
  schema_version field 19 → 20 if present; CLI count if listed; tool
  count 35 → 36; add `pypi-only-candidates` to the CLI inventory list.
- **Pin-only frontmatter bumps (9 files)** —
  `architecture.md` (unified), `architecture-bmad-infra.md`, `index.md`,
  `project-overview.md`, `integration-architecture.md`,
  `development-guide.md`, `deployment-guide.md`,
  `implementation-readiness-report.md`, `validation-report-PRD.md`:
  `source_pin: 'conda-forge-expert v7.8.1'` → `'conda-forge-expert v7.9.0'`.
  No body changes. (The `validation-report-PRD.md` body remains accurate
  since the v1.1.1 PRD passes the same 13-dimension check; only its
  source_pin lineage needs the bump. If a fresh re-validation is
  desired, run `bmad-validate-prd` separately.)

## 5. Implementation Handoff

**Scope classification**: **Minor**
**Recipient**: Developer agent (current Claude Code session)
**Deliverables**:
1. Substantive edits applied to the 3 files in §4.A.
2. `epics.md` frontmatter + lineage note per §4.B.
3. Out-of-scope-but-recommended bundle from §4.C applied in the same
   commit pass (single conceptual change, 12 files touched).
4. `project-context.md` updated separately (per its `maintenance_model`
   frontmatter — the user maintains it by hand, not via this proposal).
5. `bmad-validate-prd` re-run after PRD pin bump — already applied via
   `bmad-edit-prd` this session; the PRD's v1.1.0 → v1.1.1 + source_pin
   v7.8.1 → v7.9.0 changes are in place.
6. `bmad-index-docs` re-run after all edits land (refreshes
   cross-references in `index.md`).

**Success criteria**:
- All `source_pin: 'conda-forge-expert v7.8.1'` mentions in
  `_bmad-output/projects/local-recipes/planning-artifacts/` are either
  (a) bumped to `v7.9.0`, or (b) preserved as historical lineage in
  `edit_history` / cadence sections.
- Architecture docs faithfully describe schema v20 + Phase D split +
  Phase H/J/M denominator fixes + new CLI.
- Tool count (35 → 36) consistent across PRD, architecture-mcp-server,
  and project-parts.json.
- No new behavior risk: all changes are documentation.
