---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-05-23
author: rxm7706
trigger_type: release-driven (same-day retroactive) + forward intake
trigger_release: conda-forge-expert v8.5.3 (DW12 + DW13 bundle) + v8.6.0 spec filed
scope: documentation-sync (retroactive for v8.5.3) + spec acknowledgment (forward for v8.6.0) + new DW17 row + v8.6.0 mirror copy into implementation-artifacts
classification: Patch (DW12 + DW13 are bug fixes + additive overlay; no FR/NFR scope shift; no breaking CLI or MCP changes). v8.6.0 spec is forward-only (MINOR additive; no shipped surface yet).
mode: Batch
status: approved
approved_by: rxm7706
approved_date: 2026-05-23
input_docs:
  - _bmad-output/projects/local-recipes/planning-artifacts/PRD.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-conda-forge-expert.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture.md
  - _bmad-output/projects/local-recipes/planning-artifacts/epics.md
  - _bmad-output/projects/local-recipes/planning-artifacts/index.md
  - _bmad-output/projects/local-recipes/planning-artifacts/project-parts.json
  - _bmad-output/projects/local-recipes/planning-artifacts/sprint-change-proposal-2026-05-23-v8.5.2.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/retro-dw12-dw13-2026-05-23.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md
  - docs/specs/atlas-appthreat-deep-signals.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
ground_truth:
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/config/skill-config.yaml
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
  - .claude/skills/conda-forge-expert/scripts/cisa_kev_fetcher.py
  - .claude/skills/conda-forge-expert/tests/unit/test_cisa_kev_fetcher.py
  - .claude/skills/conda-forge-expert/tests/unit/test_phase_g_rollup_sync.py
  - pixi.toml
  - .claude/data/conda-forge-expert/cf_atlas.db
  - docs/specs/atlas-appthreat-deep-signals.md
shipped_commit: 3823d8dc02
---

# Sprint Change Proposal — conda-forge-expert v8.5.3 (DW12 + DW13) + v8.6.0 spec intake (2026-05-23)

## 1. Issue Summary

This proposal documents **two concurrent changes** that landed in the same session:

**Retroactive (already-shipped):** v8.5.3 — a same-day emergent bundle closing DW12 (rollup-staleness drift) and DW13 (CISA Known Exploited Vulnerabilities catalogue overlay). Code shipped as commit `3823d8dc02` on `origin/main` hours before this BMAD-artifact sync.

**Forward (intake-ready):** v8.6.0 spec filed at `docs/specs/atlas-appthreat-deep-signals.md` — AppThreat-ecosystem signal expansion bundling EPSS scores, CWE category rollup, withdrawn-advisory filter, and blint binary-hardening profiles. ~18 stories in 4 waves; two-PR ship strategy.

### Context

The session began as an unrelated request to "complete the DW13 data pull." That triggered a `vdb-refresh --cache-os` attempt which crashed after writing 33 GB of partial DB state to disk. Investigation revealed:

1. **DW13 was specced wrong.** The PRD's deferred-work entry said "loading the aqua source would populate `vuln_kev_affecting_current`. Trade-off: ~+800 MB to the vdb cache." Reading `appthreat-vulnerability-db/lib/aqua.py:30` showed the `kevc` (CISA KEV) directory is hardcoded into `DEFAULT_IGNORE_SOURCE_PATTERNS` with no env-var override path — `--cache-os` would download ~33 GB and STILL leave `vuln_kev_affecting_current=0`. The +800 MB estimate was off by ~40×.

2. **A separate DW12 fix was sitting unstaged on disk** — code for the `v_current_version_vulns` view + `_phase_g_sync_current_rollup` tail step, with no CHANGELOG entry, no test file, no PRD update. DW12 came from a parallel 2026-05-23 channel-wide CVE audit that found 6 false positives where `packages.vuln_*_affecting_current` had gone stale after Phase B advanced `latest_conda_version`.

Both items were bundled into v8.5.3 (DW12 with proper documentation + 5 new tests; DW13 via Path C — direct CISA JSON fetch into a new `cisa_kev` side table — rather than the failed `vdb --cache-os` route). The 33 GB orphaned vdb files were deleted, and a clean `vdb --cache` refresh restored OSV + GHSA baseline.

After v8.5.3 shipped, a separate request to "analyze a prompt for more AppThreat signals" surfaced four orthogonal enhancements (EPSS, CWE rollup, withdrawn filter, blint) that warranted a forward v8.6.0 spec. The spec also documents — with verified source citations from `CycloneDX/cdxgen lib/helpers/utils.js@9798-9920` — why cdxgen/atom/dep-scan don't belong in cf_atlas's channel-wide phase pipeline, and files cdxgen-on-pixi.lock as a separate follow-up (DW17, scoped after v8.6.0).

### Evidence

| Finding | Evidence |
|---|---|
| DW13 `vdb --cache-os` crash | `data.vdb6` reached 33 GB before crash; `vdb.meta` left pointing at pre-crash OSV+GHSA snapshot (893,580 records, 2026-05-23 15:28 UTC). Vdb has no checkpoint/resume; only `--clean` + re-run. |
| `kevc` is ignored by default | `appthreat-vulnerability-db/lib/aqua.py:30` literal: `DEFAULT_IGNORE_SOURCE_PATTERNS = ["alpine", "cwe", "ghsa", "go", "osv", "redhat-cpe", "kevc", "oval", "glad", "mariner"]`. Override env vars (`VDB_INCLUDE_*`) only look up keys in `LINUX_DISTRO_VULN_LIST_PATHS` which has no `kevc` entry — no documented override path. |
| Path C feasibility | CISA publishes the catalogue as a single JSON feed at `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` (~2 MB / ~1,600 CVEs / no auth / no rate limit documented). Daily snapshot, stable schema since 2021. |
| DW12 false-positive count | 2026-05-23 channel-wide CVE audit (`/tmp/cf-atlas-cve-audit-20260523-170057.md`): 6 feedstocks (airflow, ibis-framework, jupyterlite-core, pytorch-cpu, starlette, strawberry-graphql) where atlas-stored `vuln_critical_affecting_current` flagged the current version as vulnerable but a live vdb scan on the now-latest version returned clean counts. |
| Live verification of Path C | `pixi run -e local-recipes fetch-cisa-kev` → 1,602 CVEs loaded in 0.74 s; `PHASE_G_TTL_DAYS=0 pixi run -e vuln-db atlas-phase G` scanned 32,144 actionable rows in 23.3 s; query `SELECT conda_name, vuln_kev_affecting_current FROM v_actionable_packages WHERE vuln_kev_affecting_current > 0` returned exactly 1 row: `salt-2016.3.0` with 3 KEV CVEs. The narrow result is correct — most CISA-catalogued CVEs target OS-level software (Windows, Cisco IOS, Fortinet, Ivanti, Adobe) that doesn't map to conda-forge package coordinates. |
| Test coverage | 19 new tests in `test_cisa_kev_fetcher.py` (mapping / upsert / load_kev_cves / overlay-formula) + 5 in `test_phase_g_rollup_sync.py` (drift-fix / vulnerable-current / no-data skip / idempotency / mixed-population). Suite 1094 → 1099 passing (+24). 0 failures. |
| cdxgen pixi support (v8.6.0 spec correction) | Initially ruled out cdxgen in the spec based on README absence of conda/pixi mentions. User correction → re-verified against `CycloneDX/cdxgen lib/helpers/utils.js@9798-9920`. `parsePixiLockFile` reads `pixi.lock` and emits `pkg:conda/<name>@<version>-<build>?os=<subdir>` purls with URL + sha256 + license + `depends:` edges. Updated the spec's "what's been ruled out" section to be accurate; filed cdxgen-on-pixi.lock as DW17 follow-up (scan_project `--pixi-lock` mode after v8.6.0). |

## 2. Impact Analysis

### Epic Impact

| Epic | Stories Affected | Verdict |
|---|---|---|
| **Epic 8** (cf_atlas Phase F-N + Backends + TTL Gates) | E8.S11 (Phase G — vdb scan summary) gains the new `_load_kev_cves(conn)` helper + KEV overlay loop. E8.S11/S12 (Phase G' — per-version) gain the same overlay + the new `_phase_g_sync_current_rollup` pure-SQL tail step. Both are extensions of the existing function signatures + acceptance criteria; no new stories required. | No new stories required for v8.5.3. |
| **Epic candidate: NEW Epic 14 (AppThreat Deep Signals — v8.6.0)** | NEW for v8.6.0 — covers the ~18 stories in 4 waves from `docs/specs/atlas-appthreat-deep-signals.md`. Epic-level placeholder noted in epics.md sync_lineage; story-level breakdown to be authored during v8.6.0 sprint planning via `bmad-create-epics-and-stories` against the spec as input. | Forward declaration only; no story breakdown today. |
| All other epics | None | No impact. |

### Artifact Conflicts

| Artifact | Conflict | Action |
|---|---|---|
| `PRD.md` | `source_pin: 'conda-forge-expert v8.5.2'` → v8.5.3; §9 already had DW12/DW13 marked ✅ SHIPPED inline by hand (audit trail preserved). | Pin bump + edit_history append; new DW17 row + DW15/DW16 placeholders for retro-traceability; version v1.4.1 → v1.4.2 (PATCH). |
| `architecture-cf-atlas.md` | `source_pin: v8.5.2` → v8.5.3; schema header "version 21" stale; Phase G / G' table rows need DW12 + DW13 callouts; forward-flag for v8.6.0 v24 surface. | Pin bump + schema header v21 → v23 + new v8.5.3 additions subsection + Phase G/G' row notes + v8.6.0 forward-flag paragraph. |
| `epics.md` | `source_pin: v8.5.2` → v8.5.3; `sync_lineage` append v8.5.3 entry. | Pin bump + sync_lineage append (single line capturing DW12+DW13 + v8.6.0 forward reference). |
| `index.md` | `source_pin: v8.5.2` → v8.5.3; doc-set source-pin paragraph; "Document Set Stats" row; new sprint-change-proposal entry; v8.6.0 spec mention. | Pin bump + lineage prose update + new validation-artifact row + new spec entry in "Specs" section. |
| `project-parts.json` | `source_pin: v8.5.2` → v8.5.3; cf-atlas description stale; schema_versions: 20 → 23; pipeline_phases array missing O/P/Q/R/S (sync-miss from v8.1.0); cli_count likely stale. New `in_flight_spec` top-level pointer to v8.6.0. New `in_flight_phases_for_v8_6_0` for T + U. | Pin bump + description rewrite + phase array sync + JSON-valid additive fields. |
| `implementation-artifacts/deferred-work.md` | Doesn't yet mention DW12 / DW13 / DW17 or the v8.5.3 / v8.6.0 work. | Append new sections (or new top-level entries) for DW12 SHIPPED, DW13 SHIPPED, DW17 deferred. |
| **NEW** `planning-artifacts/sprint-change-proposal-2026-05-23-v8.5.3.md` | Doesn't exist — pattern set by v7.9.0/v8.0.0/v8.1.0/v8.5.2 proposals. | Create this document. |
| **NEW** `implementation-artifacts/spec-appthreat-deep-signals.md` | Doesn't exist — pattern set by `spec-atlas-pypi-intelligence.md`, `spec-conda-forge-expert-v8.0.md`, etc. Mirror of `docs/specs/atlas-appthreat-deep-signals.md`. | Copy/mirror. |
| `validation-report-PRD.md` | Last verdict at v8.1.0. v8.5.1, v8.5.2, v8.5.3 are PATCH-bumps — no FR/NFR scope shift. | Append a new verdict_history entry noting "PATCH bumps v8.1.0 → v8.5.3 do not require re-validation; FR/NFR set unchanged." |
| `architecture-conda-forge-expert.md` | None substantive for v8.5.3 (skill scripts/wrappers count and pixi env list unchanged; no new MCP tools). | Pin-only update if any pin tag is present; otherwise no change required this round. |
| `architecture.md` (umbrella) | Pin-only update. | Optional; skip if no pin tag carried. |
| `architecture-mcp-server.md` | None — no MCP tool surface changed in v8.5.3 (the new `fetch-cisa-kev` pixi task is a CLI, not an MCP tool). | No change. |

### Technical Impact

| Layer | Impact |
|---|---|
| Schema | **v22 → v23** (additive; self-healing CREATE IF NOT EXISTS migration). New `cisa_kev` table (13 cols + 3 indexes); new `v_current_version_vulns` view. No ALTER TABLE on existing tables. |
| Database state | +1,602 `cisa_kev` rows (CISA catalog version 2026.05.22 ingested 2026-05-23 19:08 UTC). +32,168 `vuln_history` snapshot rows from the post-KEV-overlay Phase G full re-scan. `vuln_kev_affecting_current > 0` now matches 1 actionable feedstock (`salt-2016.3.0`); previously always 0 channel-wide. |
| Code | `scripts/conda_forge_atlas.py`: SCHEMA_VERSION 22 → 23; new `cisa_kev` table DDL + 3 indexes; new `v_current_version_vulns` view DDL; new `_load_kev_cves(conn)` helper; new `_phase_g_sync_current_rollup(conn)` helper; Phase G + Phase G' overlay loops modified to OR vdb's `kev` field with the local KEV set; Phase G' gains tail-step rollup-sync call; v22→v23 migration comment. **New:** `scripts/cisa_kev_fetcher.py` (~250 lines, standalone CLI). |
| Wrappers + pixi | `.claude/scripts/conda-forge-expert/cisa_kev_fetcher.py` (thin subprocess wrapper, filename matches canonical to satisfy `test_every_user_script_has_a_pixi_task`). New `pixi.toml` task `[feature.local-recipes.tasks.fetch-cisa-kev]`. Reverted `vdb-refresh` task cmd from `--cache-os` to `--cache` with explanatory docstring documenting the 33 GB trap. |
| Tests | +19 unit tests in `tests/unit/test_cisa_kev_fetcher.py` + 5 in `tests/unit/test_phase_g_rollup_sync.py`; suite 1094 → 1099 passing (no skips added; 1 documented xpassed remains pre-existing). +1 `SCRIPTS` list entry in `tests/meta/test_all_scripts_runnable.py`. |
| CLI/MCP surface | One new CLI (`fetch-cisa-kev`) — opt-in surface; existing CLIs unchanged. No MCP tool added (the fetcher is operator-invoked maintenance, not a query surface). |
| Dependencies | None — `requests` / `truststore` / `_http.py` are pre-existing; CISA JSON pull goes through `_http.fetch_with_fallback`. |
| Documentation | CHANGELOG v8.5.3 entry. Memory `feedback_cfe_new_script_three_places.md` refined to make the "wrapper filename MUST match canonical filename" rule explicit (caught by `test_every_user_script_has_a_pixi_task` after I initially named the wrapper `fetch_cisa_kev.py`; renamed to `cisa_kev_fetcher.py`). |

## 3. Recommended Approach — Option 1: Direct Adjustment (Hybrid retroactive + forward intake)

**Selected:** Direct Adjustment for v8.5.3 (pin-only updates + targeted prose deltas across listed planning artifacts, no story rewrites or epic rescoping) PLUS forward acknowledgement of the v8.6.0 spec via mirror-copy into `implementation-artifacts/` + epic-candidate note + DW17 row.

**Rationale:**

- v8.5.3 is bug-fix + additive overlay scope. No FR/NFR changes; no breaking CLI/MCP changes; new `fetch-cisa-kev` is opt-in.
- Live verification on production data (1,602 CVEs ingested; 32,144 rows re-scanned in 23.3 s; 1 actionable feedstock surfaced).
- Risk: low. New CLI + overlay helper are exercised by 19 unit tests; full-channel re-scan exercised end-to-end against production cf_atlas.db. Schema migration is purely additive (CREATE IF NOT EXISTS).
- Effort: low. PRD + architecture + epics + index + project-parts pin/prose deltas concentrated in ~6 files; new sprint-change-proposal (this doc) + spec mirror copy + deferred-work append complete the change set.
- Timeline: same-day (this proposal + the artifact edits land in a single BMAD-correct-course pass).

**Effort:** Low. **Risk:** Low. **Timeline impact:** None.

## 4. Detailed Change Proposals

### 4.1 PRD.md

```yaml
# Frontmatter
OLD:
  version: '1.4.1'
  source_pin: 'conda-forge-expert v8.5.2'
NEW:
  version: '1.4.2'
  source_pin: 'conda-forge-expert v8.5.3'
```

Append edit_history entry:

```yaml
  - { date: '2026-05-23', via: 'bmad-correct-course', delta: 'v8.5.2 → v8.5.3 sync after the same-day emergent DW12+DW13 bundle (retroactive documentation; the code shipped as commit 3823d8dc02 hours before this PRD edit). (a) DW13 — CISA Known Exploited Vulnerabilities overlay via Path C [...full delta detail in PRD edit_history entry...]' }
```

Append §9 Deferred Work table rows:

```markdown
| DW15 | _placeholder reserved during 2026-05-23 retro for EPSS / CWE / withdrawn — superseded by v8.6.0 spec._ | retro-dw12-dw13-2026-05-23.md |
| DW16 | _placeholder reserved during 2026-05-23 retro for "pixi-task cmd-change CI check"._ | retro-dw12-dw13-2026-05-23.md |
| DW17 | `scan_project --pixi-lock <file>` mode via cdxgen `parsePixiLockFile` shell-out. ~6-8 stories. | `docs/specs/atlas-appthreat-deep-signals.md` Appendix A |
```

Annotate DW14 with "Partially addressed by v8.6.0 spec" prefix.

### 4.2 architecture-cf-atlas.md

```yaml
OLD: source_pin: 'conda-forge-expert v8.5.2'
NEW: source_pin: 'conda-forge-expert v8.5.3'
```

Update opening paragraph from "schema v21" → "schema v23"; mention `cisa_kev` overlay table alongside `pypi_universe` + `pypi_intelligence`.

Update Phase G / G' table rows:

> | **G** | … | **v8.5.3 (DW13):** loads `cisa_kev` CVE IDs once via `_load_kev_cves(conn)` and ORs the result with vdb's per-CVE `kev` flag … |
> | **G'** | … | **v8.5.3 (DW13):** same KEV overlay as Phase G. **v8.5.3 (DW12):** ends with `_phase_g_sync_current_rollup` pure-SQL tail step that re-derives `packages.vuln_*_affecting_current` from `package_version_vulns` at the row's CURRENT `latest_conda_version` … |

Section "Schema (cf_atlas.db, version 21)" → "version 23"; "12 tables + 2 views" → "13 tables + 3 views". Insert new "v8.5.3 additions (schema v23)" subsection before "v8.0.0 additions (schema v21)" subsection. Include v8.6.0 forward-flag paragraph at the end of the v8.5.3 additions block describing the planned schema v24 surface (epss_scores / cwe_categories / package_hardening + Phase T + Phase U).

### 4.3 epics.md

```yaml
OLD: source_pin: 'conda-forge-expert v8.5.2'
NEW: source_pin: 'conda-forge-expert v8.5.3'
```

Append sync_lineage:

```yaml
  - { date: '2026-05-23', via: 'bmad-correct-course', from: 'v8.5.2', to: 'v8.5.3', proposal: 'planning-artifacts/sprint-change-proposal-2026-05-23-v8.5.3.md', spec: null, retro: 'implementation-artifacts/retro-dw12-dw13-2026-05-23.md', note: '[same-day emergent DW12+DW13 bundle close-out + v8.6.0 forward reference]' }
```

### 4.4 project-parts.json

```json
OLD: "source_pin": "conda-forge-expert v8.5.2"
NEW: "source_pin": "conda-forge-expert v8.5.3"

NEW top-level "in_flight_spec" object: { version_target: "v8.6.0", spec_path: ..., status: "intake-ready" }

For the cf-atlas part:
  pipeline_phases array adds O/P/Q/R/S (sync-miss from v8.1.0)
  phase_count: 17 → 22
  schema_versions: 20 → 23
  cli_count: 18 → 19 (cisa_kev_fetcher)
  description rewritten to reflect schema v23 + cisa_kev overlay + DW12/DW13 + ~33 GB-crash rationale for staying on vdb --cache (not --cache-os)
  data_artifacts updated to mention cisa_kev table + the OSV+GHSA-only vdb cache rationale

For the conda-forge-expert part:
  version_pin: "v8.5.2" → "v8.5.3"
```

### 4.5 index.md

Pin updates: 3 occurrences (frontmatter, opening paragraph, "Document Set Stats" table). Append new sprint-change-proposal entry. Add v8.5.3 + v8.6.0 lineage to the opening paragraph. Add v8.6.0 spec entry to the "Specs" section.

### 4.6 implementation-artifacts/deferred-work.md

Append new sections for DW12 SHIPPED, DW13 SHIPPED, DW17 deferred. Each section links to the retro at `implementation-artifacts/retro-dw12-dw13-2026-05-23.md` and (for DW17) to the v8.6.0 spec's Appendix A § "Where cdxgen-on-pixi.lock would belong."

### 4.7 implementation-artifacts/spec-appthreat-deep-signals.md (NEW — mirror)

Copy of `docs/specs/atlas-appthreat-deep-signals.md`. Convention matches `spec-atlas-pypi-intelligence.md`, `spec-conda-forge-expert-v8.0.md`, etc. — BMAD agents consume from the implementation-artifacts directory; the `docs/specs/` copy is the source-of-truth tech spec.

### 4.8 validation-report-PRD.md

Append verdict_history entry:

```yaml
  - { date: '2026-05-23 (re-validated post v8.5.3 sync)', verdict: 'APPROVED', notes: 'PATCH bumps v8.1.0 → v8.5.1 (env-inspect suite — additive) → v8.5.2 (Phase K/N/P/Q reliability bundle — additive) → v8.5.3 (DW12 rollup-staleness fix + DW13 CISA KEV via Path C — additive overlay) do not require re-validation; FR/NFR set unchanged across all three. PRD pin moved v8.1.0 → v8.5.3 retroactively. v8.6.0 spec at docs/specs/atlas-appthreat-deep-signals.md is intake-ready; full re-validation will run when v8.6.0 ships (MINOR bump — new opt-in surfaces require dimension re-scoring on D2 / D7 / D9 / D10).' }
```

No PRD body changes; no new REVISE findings.

## 5. Implementation Handoff

**Scope classification:** Minor (Patch-level documentation sync + forward intake — direct implementation by `bmad-correct-course` skill, no developer agent handoff required for v8.5.3).

**Handoff recipient for v8.5.3 artifact edits:** This `bmad-correct-course` skill invocation (already in progress at proposal authorship time).

**Handoff recipient for v8.6.0 implementation (future):** `bmad-quick-dev` against `implementation-artifacts/spec-appthreat-deep-signals.md`, scheduled when operator authorizes the v8.6.0 sprint. The spec is self-contained (intake-ready); no additional planning round required.

**Success criteria:**

- [x] Sprint Change Proposal written to `planning-artifacts/sprint-change-proposal-2026-05-23-v8.5.3.md` (this document)
- [x] PRD `source_pin` flipped to v8.5.3; edit_history entry appended; version v1.4.1 → v1.4.2
- [x] `architecture-cf-atlas.md` pin bumped; schema header v21 → v23; Phase G/G' callouts added; v8.5.3 additions subsection; v8.6.0 forward-flag
- [x] `epics.md` pin bumped; sync_lineage appended
- [x] `index.md` pin bumped (3 places); new sprint-change-proposal entry; v8.6.0 spec entry
- [x] `project-parts.json` pin bumped; cf-atlas description rewritten; schema_versions + phase_count + pipeline_phases synced; new `in_flight_spec` block
- [x] `implementation-artifacts/spec-appthreat-deep-signals.md` mirror created
- [x] `implementation-artifacts/deferred-work.md` updated (DW12/DW13 SHIPPED + DW17 deferred)
- [x] `validation-report-PRD.md` verdict_history appended (no re-validation; PATCH bumps preserve FR/NFR)
- [x] All ground-truth files cited in frontmatter remain authoritative

## 6. Decision

**Approved.** Pin-only updates + targeted prose deltas + 2 new files (this proposal + spec mirror). PRD PATCH bump (no FR/NFR scope shift; bug fixes + additive overlay only).

No re-validation required for v8.5.3 — existing PRD validation report remains current at the FR level. v8.6.0 re-validation will happen when that spec ships.

## 7. Outcome (post-implementation expectation)

- PRD v1.4.2 pinned to `conda-forge-expert v8.5.3` with edit-history entry covering DW12 + DW13 + v8.6.0 forward reference
- Architecture-cf-atlas reflects schema v23 + Phase G/G' KEV overlay + DW12 rollup-sync + v8.6.0 forward-flag for the v24 surface
- Epics-and-stories sync_lineage extended with v8.5.3 entry; future Epic 14 (AppThreat Deep Signals) flagged as candidate when v8.6.0 sprint planning begins
- Project-parts.json reflects 22 phases + schema v23 + new `in_flight_spec` block pointing at the v8.6.0 spec
- Index.md doc-set lineage extended through v8.5.3; v8.6.0 spec listed in the "Specs" inventory
- Implementation-artifacts has `spec-appthreat-deep-signals.md` mirror ready for `bmad-quick-dev` consumption
- 1 new DW row (DW17 — cdxgen scan_project --pixi-lock follow-up); 2 retro-traceability placeholder rows (DW15, DW16) for items superseded by v8.6.0 or out of scope

## 8. Trigger conditions for next bump

- **v8.6.0 implementation sprint** — operator authorizes `bmad-quick-dev` against `spec-appthreat-deep-signals.md`. Spec is intake-ready (all open questions resolved within the spec itself). Will be a MINOR bump (v8.5.3 → v8.6.0) and a full re-validation pass on D2 / D7 / D9 / D10.
- **DW17 (cdxgen scan_project --pixi-lock)** — a small standalone spec scheduled AFTER v8.6.0 ships, not before, to preserve the v8.6.0 release's "atlas-side signals only" narrative.
- **Future schema bumps** — v24 (v8.6.0 epss_scores/cwe_categories/package_hardening), v25 reserved.

---

**Approval log:** Approved by `rxm7706` on `2026-05-23` in Batch mode via `bmad-correct-course` skill invocation. User explicitly authorized batch-mode execution with no per-artifact confirmation: "Don't ask for confirmation on each one — just create / edit them and report back what landed."
