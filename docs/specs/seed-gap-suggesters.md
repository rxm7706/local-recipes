---
doc_type: spec
part_id: seed-gap-suggesters
display_name: seed-gap suggesters (CWE + SPDX)
project_type_id: tooling
date: 2026-07-06
status: shipped
implemented_by: conda-forge-expert v8.75.0
shipped_ref: 6b23022a335bfce317b961937ce52fb2a4699464
spec_updated: 2026-07-06
---

# Spec: seed-gap suggesters — `cwe-seed-gap` + `spdx-schema-gap`

## Goal

Two more git-tracked seed assets under `data/` are hand-curated and grow only
by hand, with no systematic view of what they're missing:

- **`cwe_categories_seed.json`** (67 CWE-ID → cf_atlas-category mappings) —
  every CWE not in the seed defaults to `Other` in the `cwe_categories`
  atlas table, so a genuinely-classifiable weakness silently sits in the
  `Other` bucket forever.
- **`spdx.schema.json`** (811-ID SPDX enum, vendored at v3.28.0) — used by
  `_sbom.normalize_license` + `conda_forge_atlas._normalize_license_to_spdx`.
  It drifts behind the upstream SPDX license list, and real package licenses
  can fall outside it unnoticed.

This effort adds two read-only suggesters in the `mapping-gap` / `lts-registry-gap`
mold — they **propose** additions with confidence tiers; accept/reject stays
with git review. **Neither ever writes its seed.** Both continue the
"push automation further" line (v8.74.0 `lts-registry-gap`) and register two
more external-data-asset maintenance loops for the kedro migration (§ below).

## `cwe-seed-gap` (offline; atlas-grounded)

- **Input**: the `cwe_categories` table (MITRE's full catalog, populated by
  `fetch-cwe-catalog`) + the seed via `cwe_catalog_fetcher._load_seed_mapping`.
- **Discovery**: rows with `cf_atlas_category = 'Other'` whose `cwe_name`
  matches a curated keyword heuristic for the 7 real categories. Two tiers:
  `strong` (a category-defining phrase — `sql injection`, `use after free`,
  `path traversal`) and `weak` (a generic word — `injection`, `memory`,
  `authorization`). First strong hit across a fixed category precedence
  wins; else first weak hit. No match → not proposed (stays `Other`).
- **Impact headline**: count of packages whose `vuln_cwe_categories_json`
  carries a non-zero `Other` bucket — the universe cost of the gap. (Per-CWE
  package attribution isn't recoverable — Phase G/G' aggregates CWE-IDs to
  categories — so the heuristic, not package count, ranks proposals.)
- **Output**: ready-to-paste `"CWE-NNN": "Category"` seed lines grouped by
  tier, each with the matched keyword as justification; `--json`; `--limit`
  per tier. Reads `cwe_categories` only — fully offline.

## `spdx-schema-gap` (atlas-grounded; upstream cross-check)

- **Inputs**: the vendored enum from `spdx.schema.json`; the upstream SPDX
  license list (`spdx/license-list-data` `json/licenses.json` via
  `_http.resolve_github_raw_urls`, `GITHUB_RAW_BASE_URL`-routable; TTL-7d
  cache `spdx_license_list.json` with offline-stale fallback — the
  lts-registry-gap products-cache contract; `--source-file` for offline/test);
  distinct `conda_license` (+ `pypi_intelligence.license_spdx`) from
  `v_actionable_packages` with package counts.
- **Classification** of each distinct atlas license string not in the
  vendored enum (compound SPDX *expressions* — containing `AND`/`OR`/`WITH`/
  parens — are skipped; the enum holds single IDs only):
  - in the upstream SPDX ID set → **add-to-schema** (real staleness: SPDX has
    it, the vendored copy predates it) — ranked by package count.
  - not upstream either → **non-standard** (a normalization candidate,
    report-only — NOT a schema add).
- **`--drift`** (opt-in): upstream IDs entirely absent from the vendored enum,
  independent of atlas usage (the pure staleness count).
- **Output**: ready-to-paste enum-ID additions (the `add-to-schema` tier) +
  the non-standard normalization list; `--json`; `--limit`; `--out`. Never
  writes `spdx.schema.json`.

## Acceptance criteria

- Three-place rule per tool (canonical script + wrapper + pixi task +
  SCRIPTS meta entry); `--help` clean; CLI/pixi-only (no MCP tool).
- Fixture tests per tool: tier classification, seed/enum-covered exclusion,
  no-match/expression exclusion, stale-cache fallback (SPDX), `--json` +
  `--limit` shape, and a **seed-file-untouched** assertion (byte-identical
  across a full CLI run) for each.
- Docs: SKILL.md atlas CLI rows + Version History; CHANGELOG v8.75.0 (MINOR);
  cheatsheet rows. CLAUDE.md spec-table row.
- Kedro reflection (cross-branch follow-up): the migration spec's § 3.4
  (on the in-flight boundary branch) + the kedro-viz prototype (on its own
  branch) gain the three seed-gap loops (lts-registry, cwe, spdx) as
  read-only "seed freshness report" nodes fanned out from the external seed
  datasets — the mapping-gap-writeback analogue for curated seeds. Folded
  into those branches once they land (kept off this main-based branch to
  avoid a § 3.4 collision).
