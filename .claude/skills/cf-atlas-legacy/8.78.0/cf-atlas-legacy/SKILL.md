---
name: cf-atlas-legacy
description: >
  Hallucination-free legacy provenance oracle for the cf_atlas-to-Kedro migration
  (BMAD project pyforge-atlas). Models the legacy conda_forge_atlas.py orchestrator
  (8,902 LOC, 23 cataloged phases, schema v29) plus bootstrap_data.py, atlas_phase.py,
  _http.py, the 3 satellite fetchers, mapping_gap.py, and the 23 atlas-relevant MCP
  tools — every claim cited to file:line at grounding commit b18cbb5 (CFE skill pin
  v8.78.0, 2026-07-17). Use when porting phases in Wave-B stories B1/B2/B5/B6 and you
  need the authoritative answer about a phase's registration, TTL gates, cf_atlas.db
  write paths, per-phase engineering contracts, or the spec 3.4 migration boundary.
  Questions outside the modeled universe MUST be answered "not modeled" — never guessed.
---

# cf-atlas-legacy — Legacy Provenance Oracle

## Overview

Queryable model of the legacy cf_atlas data-pipeline for the Kedro migration (spec:
`docs/specs/cfe-atlas-datapipeline-kedro-migration.md` §§ 3.3–3.4). Execution
scaffolding for Wave B (spec § 2.4) — not product surface.

- **Grounding stamp (AD-17):** generated 2026-07-17 · commit `b18cbb5`
  (`b18cbb5e1bfd1e7111d89dff0a4b7e47875f965c`) · CFE skill pin **v8.78.0** ·
  `SCHEMA_VERSION = 29` [SRC:.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py:L139]
- **Modeled universe:** 23 cataloged phases (22 registered + unregistered Phase I),
  checkpoint/TTL machinery, the 6 cf_atlas.db write paths, per-phase engineering
  contracts (spec:250–286), the § 3.4 migration boundary, 19 `_http.py` resolvers,
  23 atlas-relevant MCP tools (of 46 total). 130 provenance-map entries, all T1-low.
- **Sources are READ-ONLY**; this skill is an **advisory snapshot** — re-verify any
  load-bearing claim against the live tree before acting on it (AD-17).
- Conditional Phase T (trendshift Track A): re-checked 2026-07-17 — **NOT shipped**
  (no `github_trending_repos` / schema v30 in the tree); surface stays 23 phases / v29.

## Quick Start

Answer protocol for a provenance query (the Oracle contract, spec § 2.2):

1. Look the symbol up in `provenance-map.json` (`entries[]`, 130 rows) or the Phase
   Registry below. Every entry carries `source_file` + `source_line` at commit `b18cbb5`.
2. Read the cited lines in the live tree to confirm (snapshots are advisory, AD-17).
3. Answer with the `file:line` citation. If line numbers have drifted from `b18cbb5`,
   say so and cite both.
4. **Negative probe (AD-19):** if the question is not covered by the § 3.3 surface or
   the § 3.4 boundary modeled here, answer exactly **"not modeled"** — do not infer,
   do not fall back to training data. Out-of-universe examples: `gemini_server.py`
   (spec:172–177 excludes it), recipe-authoring MCP tools (23 of the 46), the
   `recipes/` tree, BMAD tooling, future Kedro code.

<!-- [MANUAL:additional-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:additional-notes] -->

## Common Workflows

**B1 (conda-side phase port):** Phase Registry row → def line → docstring purpose →
`references/engineering-contracts.md` for the binding contract (e.g. B.5
`_pick_feedstock` attribution, Phase F provenance discipline, Phase K token bucket).

**B2 (PyPI + vuln port):** Phase P cost gates + Phase H serial gate + G/G' overlay
helpers in `references/engineering-contracts.md`; write-path detail for the 3
security fetchers in `references/write-paths-and-checkpoints.md`.

**B5 (external-refresh assets):** the 3 in-scope refresh stores + out-of-scope
declared-input classes in `references/http-and-migration-boundary.md` (§ 3.4 model).

**B6 (seed-gaps pipeline):** the 4 report-only suggesters are terminal report nodes
(spec:380–386); `mapping-gap` is the sole write-back exception — `g10_spelling`
no-clobber UPDATE [SRC:.claude/skills/conda-forge-expert/scripts/mapping_gap.py:L76].

**Any port:** confirm every raw `packages` query passes the `v_actionable_packages`
scope rule, and read vulns ONLY via `v_current_version_vulns` (rollup is report-only)
[SRC:.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py:L732].

## Key API Summary

**The Phase Registry** — all 23 cataloged phases. Registry: `PHASES` list
[SRC:.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py:L8679] (tuples
L8680–8701). TTL-gated set = `_TTL_GATED`
[SRC:.claude/skills/conda-forge-expert/scripts/atlas_phase.py:L44]. Credentialed set
per spec:148–152. File for def-lines: `conda_forge_atlas.py`.

| Phase | Function (def line) | Purpose | Reg. | TTL | Cred. |
|-------|--------------------|---------|------|-----|-------|
| B | `phase_b_conda_enumeration` (L1408) | enumerate cf packages via per-subdir current_repodata | yes | — | — |
| B.5 | `phase_b5_feedstock_outputs` (L1593) | feedstock-outputs archive; `_pick_feedstock` (L1572) | yes | — | — |
| B.6 | `phase_b6_yanked_detection` (L1665) | latest_status from repodata presence (lite) | yes | — | — |
| C | `phase_c_parselmouth_join` (L1744) | parselmouth PyPI-conda join | yes | — | — |
| C.5 | `phase_c5_source_url_match` (L1802) | deferred — folded into Phase E | yes | — | — |
| D | `phase_d_pypi_enumeration` (L1947) | PyPI universe via Simple API v1 | yes | — | — |
| O | `phase_o_serial_snapshots` (L7051) | daily serial snapshots; activity bands | yes | — | — |
| P | `phase_p_pypi_downloads` (L7352) | BigQuery/ClickHouse downloads dispatcher | yes | — | BigQuery ADC; admin-only opt-in |
| Q | `phase_q_cross_channel` (L7847) | cross-channel in_channel BOOLs | yes | — | — |
| R | `phase_r_pypi_json_enrich` (L8330) | per-project JSON enrichment (top-N) | yes | — | — |
| S | `phase_s_computed_scores` (L8546) | readiness + recommended_template | yes | — | — |
| E | `phase_e_enrichment` (L2188) | cf-graph node_attrs enrichment | yes | — | — |
| E.5 | `phase_e5_archived_feedstocks` (L2504) | GraphQL archived feedstocks | yes | — | GitHub token |
| F | `phase_f_downloads` (L3560) | download counts (api/s3/merged) | yes | `downloads_fetched_at` | — |
| G | `phase_g_vdb_summary` (L3771) | vdb risk summary + KEV/EPSS/CWE overlays | yes | `vdb_scanned_at` | vuln-db env |
| G' | `phase_g_prime_per_version_vulns` (L6808) | per-version vuln scoring | yes | row-absence | vuln-db env |
| H | `phase_h_pypi_versions` (L4517) | current PyPI version; serial gate (L4174) | yes | `pypi_version_fetched_at` | — |
| **I** | *(none — side-effect)* | per-version download history table (L316); written by Phase F (L2931, L3402); feeds G'/version-downloads/release-cadence | **NO** | — | — |
| J | `phase_j_dependency_graph` (L6067) | cf-graph requirements → dependencies | yes | — | — |
| K | `phase_k_vcs_versions` (L5039) | VCS latest release/tag; 3 RPS bucket | yes | `github_version_fetched_at` | GitHub token |
| L | `phase_l_extra_registries` (L5841) | npm/CRAN/CPAN/LuaRocks/crates/RubyGems/NuGet | yes | per-source | — |
| M | `phase_m_feedstock_health` (L6263) | cf-graph pr_info health columns | yes | — | — |
| N | `phase_n_github_live` (L6525) | live GitHub CI/issues/PRs | yes | — | GitHub token |

<!-- [MANUAL:phase-notes] -->
<!-- [/MANUAL:phase-notes] -->

## Key Types

- **`phase_state`** — checkpoint table
  [SRC:.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py:L274]:
  `phase_name` PK, `run_started_at`, `last_completed_cursor`, `items_completed`,
  `items_total`, `run_completed_at`, `status`, `last_error`. Written by
  `save_phase_checkpoint` (L4005), read by `load_phase_checkpoint` (L3989).
- **`_TTL_GATED`** — [SRC:.claude/skills/conda-forge-expert/scripts/atlas_phase.py:L44]:
  `F → downloads_fetched_at` (L45), `G → vdb_scanned_at` (L46), `G' → []` row-absence
  (L47), `H → pypi_version_fetched_at` (L48), `K → github_version_fetched_at` (L49),
  `L → []` per-source (L50). Reset = `UPDATE packages SET col = NULL` (L63–66), never DELETE.
- **The 5 views** (conda_forge_atlas.py): `v_actionable_packages` L376 (persona
  triplet L379–381) · `v_pypi_candidates` L585 · `v_pypi_intelligence_valid` L615
  (read-the-view rule L610–614) · `v_packages_enriched` L634 ·
  `v_current_version_vulns` L744 (ONLY query-time-correct vuln source, L732–743).
- **The 6 cf_atlas.db write paths** (spec:200–208): 1. `conda_forge_atlas.py`
  (via `cmd_build` L8757; shared `phase_r_upsert_one` L8198 + `apply_readiness_scores`
  L8484 = the add-handoff single-write-path) · 2. `atlas_phase.py` TTL reset (L54) ·
  3. `mapping_gap.py` g10_spelling writeback (L76) · 4. `cisa_kev_fetcher.py` →
  `cisa_kev` (L103) · 5. `epss_fetcher.py` → `epss_scores` (L124) ·
  6. `cwe_catalog_fetcher.py` → `cwe_categories` (L126).

## Architecture at a Glance

- **Orchestrator:** `conda_forge_atlas.py` (8,902 LOC) — 22 registered phases + schema + views + checkpoints.
- **Sub-step driver:** `bootstrap_data.py` (1,094 LOC) — profiles (maintainer/admin/consumer, L221–290), ordered sub-steps, 1800 s `cf_atlas_core` cap (L166).
- **Phase runner:** `atlas_phase.py` (112 LOC) — single-phase CLI + TTL reset.
- **HTTP layer:** `_http.py` (1,024 LOC) — 19 resolvers, atomic writers, auth chain (JFrog defect at L213–218, FR-1 fixes-not-ports).
- **Security satellites:** cisa_kev / epss / cwe_catalog fetchers — overlaid by G/G' at build time.
- **Mapping satellite:** `mapping_gap.py` — dry-run default, no-clobber writeback.
- **MCP surface:** `conda_forge_server.py` (2,266 LOC) — 46 tools, 23 atlas-relevant.

## CLI

- `conda_forge_atlas.py` subcommands: `build` (L8875, `--skip/--only/--dry-run/--export-json`), `query` (L8890), `stats` (L8894).
- `atlas-phase PHASE_ID [--reset-ttl] [--list]` [SRC:.claude/skills/conda-forge-expert/scripts/atlas_phase.py:L10] — phase ids B, B.5, B.6, C, C.5, D, E, E.5, F, G, G', H, J, K, L, M, N (registered subset).
- `bootstrap-data --profile maintainer|admin|consumer` [SRC:.claude/skills/conda-forge-expert/scripts/bootstrap_data.py:L765].
- 28 read CLIs total per spec:165–171 (17 atlas + 4 seed-gap + 7 cyclonedx) — enumerated in the CFE skill, pointers only here.

## Full Phase Reference

> See `references/phases.md` — all 23 phases with def lines, docstring purposes,
> registration/TTL/credential status, and per-phase spec citations.

## Full Engineering Contracts

> See `references/engineering-contracts.md` — the binding per-phase contracts
> (spec:250–286; the architecture's AD-10 list): Phase P cost gates, Phase K
> scheduler, Phase F provenance, Phase H serial gate, B.5 attribution, KEV/EPSS/CWE
> overlays, view discipline, single-write-path, post-v25 schema — with the two
> code-vs-spec divergences flagged.

## Full Write Paths and Checkpoints

> See `references/write-paths-and-checkpoints.md` — the 6 writers in detail,
> checkpoint machinery, TTL reset, bootstrap profiles/sub-steps/timeouts.

## Full HTTP Layer and Migration Boundary

> See `references/http-and-migration-boundary.md` — 19 resolvers, atomic writers,
> auth chain + the FR-1 JFrog credential defect, and the § 3.4 boundary (3 in-scope
> refresh stores vs declared-input classes) + the "not modeled" list.

## Full MCP Tool Surface

> See `references/mcp-tools.md` — all 46 `@mcp.tool()` line-cited, with the
> 23 atlas-relevant vs 23 recipe-authoring classification.
