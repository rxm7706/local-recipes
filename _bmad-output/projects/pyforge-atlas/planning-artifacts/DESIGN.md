# pyforge-atlas — DESIGN.md (technical/visual spine)

**Produced by:** the CIS Carson/Maya planning pass (Story 20.4, CAP-7), closing `DW-D2-1`. Carson
(`bmad-cis-agent-brainstorming-coach`) ran the divergent EMPATHIZE/IDEATE pass (recorded at
`_bmad-output/brainstorming/brainstorm-atlas-19-page-spine-2026-08-28/`); Maya
(`bmad-cis-agent-design-thinking-coach`) then ran the full `bmad-cis-design-thinking` workflow —
EMPATHIZE through TEST — recorded verbatim at
`_bmad-output/projects/pyforge-atlas/planning-artifacts/design-thinking-atlas-19-pages-2026-08-28.md`,
this document's authoring source.
**Companion:** `EXPERIENCE.md` (behavioral spine — personas, journeys, interaction patterns).
**Scope:** the 19 Vizro pages NOT yet in `dashboard/app.py::PAGE_INVENTORY`, so Story 20.5 has
a technical target to port against.

**Non-scope (per this story's Boundaries):** no page is implemented here; `PAGE_INVENTORY` is
untouched; the query-plane code from Stories 20.1–20.3 is untouched. Everything below is a
design SPEC, not code.

---

## 0. How Carson and Maya derived "19"

The epics.md arithmetic for this story is literal: **28-page target minus the 9 pages
already in `PAGE_INVENTORY` = 19.** Carson's divergent pass took that literally and
enumerated the full 28-CLI read surface first, before letting Maya converge it — because a
spine built on a fuzzy count would fail the AC's "a partial spine that skips pages does not
satisfy the AC" bar.

**Divergent inventory (Carson).** The 28-CLI surface is three buckets (§ 3.3 of
`spec-archive/ATLAS-BMAD-SPECS-CONSOLIDATED.md`):

- **17 atlas read CLIs** (canonical scripts under `.claude/skills/conda-forge-expert/scripts/`):
  `detail_cf_atlas`, `staleness_report`, `feedstock_health`, `whodepends`, `behind_upstream`,
  `my_feedstocks`, `query_atlas` (the ad-hoc-SQL MCP tool — ships without its own CLI wrapper,
  but is one of the 17 read tools; ad-hoc questions were § 3.2's named "Rigid Read Surface"
  gap), `cve_watcher`, `version_downloads`, `release_cadence`, `find_alternative`,
  `adoption_stage`, `scan_project`, `env_inspect`, `platform_breakdown`, `pyver_breakdown`,
  `channel_split`.
- **4 seed-gap suggesters:** `lts_registry_gap`, `cwe_seed_gap`, `spdx_schema_gap`,
  `license_map_gap`.
- **7-CLI cyclonedx suite:** `export_purls`, `mapping_gap`, `universe_sbom`, `inventory_match`,
  `add_handoff`, `library_futures`, `recommend_2027`.

**Already shipped (7 of the 28, matching `PAGE_INVENTORY` 1:1):** `detail-cf-atlas`,
`staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`, `my-feedstocks`,
`query-atlas`. (`PAGE_INVENTORY` also carries `estate-cache` — a CAP-19/Lane-3 page, unrelated
to the 28-CLI migration — and `factory-status` — an observability page, explicitly not a CLI
port per its own `PageDef.cli` docstring "the legacy read CLI this page ports (**or**
`factory-status`)". Both count toward `PAGE_INVENTORY`'s length-9 for the epics.md subtraction,
but neither is one of the 28 CLI questions, so neither reduces the CLI-question backlog.)

**Remaining CLI questions: 28 − 7 = 21.** To land the epics.md-mandated count of exactly 19
pages without dropping a single question (the PARTIAL_PAGE_COVERAGE edge case is explicit:
"do not close DW-D2-1 on partial coverage"), Maya's convergent pass merges the three
per-dimension download-breakdown CLIs — `platform_breakdown`, `pyver_breakdown`,
`channel_split` — into **one** page (§ 4.8 below) behind a dimension selector. They share
identical output shape (a ranked breakdown table + bar chart over a 90-day window) and differ
only in the grouping column; showing them as three separate pages would be three near-identical
screens for one underlying question ("how is my package's traffic distributed?"). That merge
is the **only** consolidation in this spine — every other CLI question keeps its own page.

`21 CLI questions − 2 (three folded into one) = 19 pages.` Every one of the 21 remaining
questions is answered by exactly one of the 19 pages below; none is dropped.

## 1. Architecture constraints every page inherits

- **AD-8 — BSL-only reads.** Every page's data function routes through a declared
  `SemanticModel` (`semantic/models.py` + `semantic/metrics.py`), exactly like the 7 shipped
  pages in `dashboard/data.py`. No raw SQL, no re-implemented metric arithmetic in the page
  loader.
- **Honest-empty, never fabricated.** Missing backing Parquet → the page's loader returns an
  empty typed frame via the `_bsl_query_or_empty` seam (or the no-BSL-model `Card`-only shell
  pattern for pages whose model doesn't exist yet). No page synthesizes rows.
  Same convention DW-D2-2 established.
- **AD-17 — provenance stamp.** Every data page carries the `_provenance_line` build-stamp
  card (the backing Parquet's own mtime, or an honest "unavailable" reason) — never the
  dashboard's own render time.
- **NFR-8 — agent legibility.** Every page keeps the existing `_legibility_card` header
  (semantic markdown, deterministic layout) so browser/scraper agents can navigate without
  hallucinating, per the § 2.1 agent-legibility bar.
- **`PageDef` shape.** Every page below is specified so it drops into the existing
  `PageDef(id, title, cli, kind, note)` dataclass unchanged: `kind` is one of `grounded-data`
  (BSL model + migrated dataset both exist), `bsl-shell` (model exists, dataset not yet
  materialized), `no-bsl-shell` (model doesn't exist yet), `report-artifact` (renders the
  LATEST cached run only — the dashboard never triggers a new run; the 3 FR-9 exceptions,
  § 4.4–4.6), or `live-scan-artifact` (the dashboard itself submits a brand-new per-invocation
  scan on user input — `scan-project` § 3.6 and `env-inspect` § 3.7). `report-artifact` and
  `live-scan-artifact` both render "a report," but the dashboard's relationship to producing it
  is opposite in each case, so Story 20.5 must not collapse them into one kind (Story 20.5 can
  rename either; the shape each describes is what matters). Where a page's entry below reads
  `no-bsl-shell → bsl-shell`, that arrow is a **lifecycle annotation**, not a sixth literal
  value: the page ships today as the left value and becomes the right value once its named BSL
  model lands — assign whichever single value is literally true at merge time.
- **FR-9 exceptions stay CLI-first.** `add-handoff`, `inventory-match`, and `library-futures`
  are NOT full interactive query pages — FR-9 names them structurally-not-dashboard-pages.
  Their pages surface the **latest report artifact only** (read-only, `kind: report-artifact`),
  per § 4.4–4.6.
- **Non-authoritative-badge rule (cross-cutting, stated once).** Every page whose primary
  content is a "likely / hint / report"-tier proposal — the 4 seed-gap suggesters (§ 5.1–5.4),
  `mapping-gap` (§ 4.2), and `library-futures`' operator-override badges (§ 4.6) — renders that
  value with one consistent, non-authoritative visual marker, distinct from a verified/confirmed
  value. This is not repeated per page below; it applies uniformly to all six.

## 2. Per-page template

Each of the 19 pages below is specified with:

- **Ports** — the legacy CLI(s) it replaces.
- **BSL model (NEW)** — the semantic model this page needs; none of these exist yet in
  `semantic/models.py` today (only `build_feedstock_health_model`,
  `build_package_maintainers_model`, `build_packages_model`, `build_estate_cache_model` ship).
  Story 20.5 (or a preceding data-modeling story) adds them.
- **Source dataset** — the cf_atlas table(s)/phase(s) the model would bind to, so the Kedro
  node that materializes the migrated Parquet has a named target.
- **Layout** — Vizro components (`Card`, `AgGrid`, `Graph`, `Filter`), mirroring the existing
  `_data_page`/`_shell_page` factory shapes in `dashboard/app.py`.
- **Key columns** — the dimensions/measures the BSL query declares.
- **`kind` / empty state** — which `PageDef.kind` applies and what the honest-empty render
  looks like.

---

## 3. Atlas-CLI pages (8)

### 3.1 `cve-watcher` — CVE Watch

- **Ports:** `cve_watcher`.
- **BSL model (NEW):** `build_vuln_history_model` — dimensions `conda_name`, `severity`,
  `since_days`; measures `then_count`, `now_count`, `delta`.
- **Source dataset:** Phase G `vuln_history` snapshot table (+ the v8.6.0 EPSS/CWE/KEV
  overlays already in `packages`/`package_version_vulns` for cross-filtering).
- **Layout:** a `Filter` row (maintainer, severity, since-days, `--only-increases` toggle) +
  an `AgGrid` delta table (package / then-count / now-count / +N delta), row-colored by
  delta sign.
- **Key columns:** `conda_name`, `severity`, `then_count`, `now_count`, `delta`,
  `vuln_kev_affecting_current`.
- **`kind`:** `no-bsl-shell` until the model ships, then `bsl-shell` until the snapshot-diff
  dataset materializes.
- **Cross-link:** direct navigation to `library-futures` (§ 4.6) — a security lead deciding
  whether a CVE-flagged package is even worth keeping needs that jump without a `detail-cf-atlas`
  detour.

### 3.2 `version-downloads` — Version Downloads

- **Ports:** `version_downloads`.
- **BSL model (NEW):** `build_version_downloads_model` — dimension `version`, ordered by
  upload date; measure `downloads`.
- **Source dataset:** Phase I per-version download history (side-table of Phase F).
- **Layout:** an `AgGrid` per-version table + a `Graph` (adoption curve, cumulative and
  per-version bars), with a `--by-downloads` sort toggle.
- **Key columns:** `conda_name`, `version`, `upload_date`, `downloads`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

### 3.3 `release-cadence` — Release Cadence

- **Ports:** `release_cadence`.
- **BSL model (NEW):** `build_release_cadence_model` — dimension `window` (30/90/365-day);
  measure `release_count`; derived `trend_label` (accelerating/stable/decelerating/silent).
- **Source dataset:** Phase I rolling-window aggregation.
- **Layout:** a `Card` headline (the trend label, large) + a small multi-window `Graph`
  (bar per window).
- **Key columns:** `conda_name` or `maintainer`, `window`, `release_count`, `trend_label`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

### 3.4 `find-alternative` — Find Alternative

- **Ports:** `find_alternative`.
- **BSL model (NEW):** `build_alternative_candidates_model` — dimensions `archived_name`,
  `candidate_name`; measure `similarity_score` (keyword/summary/dependent/maintainer overlap
  × recency × downloads composite).
- **Source dataset:** Phase E keywords + Phase J dependency similarity (TF-IDF).
- **Layout:** an input `Filter` (archived package name) + a ranked `AgGrid` of candidates with
  a `similarity_score` bar-cell.
- **Key columns:** `archived_name`, `candidate_name`, `similarity_score`, `downloads_total`,
  `adoption_stage`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

### 3.5 `adoption-stage` — Adoption Stage

- **Ports:** `adoption_stage`.
- **BSL model:** re-use `build_packages_model.adoption_stage` (already declared — the
  `staleness-report`/`query-atlas`/`detail-cf-atlas` shells all project it today). This page
  is the dedicated lifecycle-classifier VIEW: a single-dimension breakdown
  (bleeding-edge / stable / mature / declining / silent) across the whole portfolio or one
  maintainer's scope, not a per-package row-list.
- **Source dataset:** the composed `semantic_packages` store (Story 20.3), already
  materializing `adoption_stage`.
- **Layout:** a `Graph` (stage distribution — stacked bar or funnel) + a drill-through
  `AgGrid` filtered to the selected stage.
- **Key columns:** `conda_name`, `adoption_stage`, `maintainer`.
- **`kind`:** `bsl-shell` (model exists; dataset materializes via `kedro run --pipeline
  semantic_packages`, same as the 3 shipped shells).

### 3.6 `scan-project` — Scan Project

- **Ports:** `scan_project`.
- **BSL model (NEW):** `build_scan_result_model` — this is the one page in this spine whose
  primary input is NOT the atlas catalog but a user-supplied artifact (manifest / lock /
  SBOM / container image / live env / GitOps resource), per FR-9's own read on why some CLIs
  are per-invocation. The model wraps the LATEST invocation's result, not a live catalog scan.
- **Source dataset:** `scan_project.py`'s own CycloneDX/SPDX output, cached per-invocation
  (a per-invocation shape, but NOT the FR-9 `add-handoff`/`inventory-match` "surface the latest
  report artifact, never trigger a new run" pattern — see § 4.4–4.6; this page's dashboard DOES
  trigger the scan, hence `kind: live-scan-artifact` below, not `report-artifact`).
- **Layout:** an upload/path `Filter` (or a "most recent scan" `Card` when no fresh input is
  supplied) + an `AgGrid` of per-package CVE/license rows + a summary `Card`
  (Critical/High/KEV counts).
- **Key columns:** `conda_name`, `severity`, `license_spdx`, `fix_available`.
- **`kind`:** `live-scan-artifact` (the dashboard itself submits the new per-invocation scan on
  user input — not a standing catalog query, and not the FR-9 "cached-only" shape either; see
  § 1's `kind` taxonomy). States: no-scan-yet (input-needed) / report-available /
  failed-invalid-run (a malformed manifest or scan error — see `EXPERIENCE.md` § 1.6).

### 3.7 `env-inspect` — Environment Inspect

- **Ports:** `env_inspect`.
- **BSL model (NEW):** `build_env_inspect_model` — same per-invocation shape as `scan-project`
  (live conda/venv environment rollup: license compatibility + CVE rollup + SBOM).
- **Source dataset:** `env_inspect.py`'s own output, cached per-invocation.
- **Layout:** three `Card`s (license summary / CVE summary / SBOM link) + an `AgGrid` detail
  table.
- **Key columns:** `conda_name`, `license_spdx`, `non_permissive_flag`, `vuln_critical`,
  `vuln_high`.
- **`kind`:** `live-scan-artifact` (same per-invocation shape as `scan-project` § 3.6). States:
  no-scan-yet / report-available / failed-invalid-run.

### 3.8 `distribution-breakdown` — Distribution Breakdown (merged: `platform-breakdown` +
`pyver-breakdown` + `channel-split`)

- **Ports:** `platform_breakdown`, `pyver_breakdown`, `channel_split` — ONE page, a
  `Filter` selects the grouping dimension (`platform` / `python-version` / `channel`).
- **BSL model (NEW):** `build_distribution_breakdown_model` — dimension `bucket` (parametrized
  by the selected facet: platform name, Python minor version, or channel name); measure
  `downloads_90d` (Phase F+ Wave 2 per-facet breakdown data).
- **Source dataset:** Phase F+ Wave 2's per-platform/per-Python/per-channel 90-day breakdown
  tables.
- **Layout:** a `Filter` (dimension selector: platform / pyver / channel) driving one shared
  `Graph` (ranked bar) + `AgGrid`; `pyver-breakdown`'s `--policy-check` headline mode
  (declared `python_min` vs. empirical floor, bump-safe sort) renders as a second `Card` +
  table below the shared chart when the `python-version` facet is selected, since it's a
  materially distinct interaction, not just another slice.
- **Key columns:** `conda_name`, `bucket`, `downloads_90d`, (`python-version` facet only)
  `declared_python_min`, `empirical_floor`, `bump_safe`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

## 4. Cyclonedx-suite pages (7)

### 4.1 `export-purls` — Export Purls

- **Ports:** `export_purls`.
- **BSL model (NEW):** `build_purl_export_model` — this is an ARTIFACT-index page (the six
  purl/mapping artifacts are files, regenerated after every atlas rebuild), not a row-query.
- **Source dataset:** `export-purls`'s own six output artifacts (conda purls, versioned purls,
  pypi-universe purls, conda↔pypi TSV, recipe exceptions, non-PyPI upstream TSV).
- **Layout:** a `Card` per artifact (name, row count, last-regenerated stamp, download link)
  in a grid.
- **Key columns:** `artifact_name`, `row_count`, `regenerated_at`.
- **`kind`:** `report-artifact`.

### 4.2 `mapping-gap` — Mapping Gap

- **Ports:** `mapping_gap`.
- **BSL model (NEW):** `build_mapping_gap_model` — dimensions `conda_name`, `classification`
  (verified/likely/unmapped); measure `gap_count`.
- **Source dataset:** the inverse-G10 classification pass over `pypi_universe` +
  corroborators.
- **Layout:** a summary `Card` (counts by classification) + an `AgGrid` of gap rows,
  READ-ONLY (the CLI's `--write` mode is a write path and stays CLI-only — DRY-RUN is the
  dashboard's only mode, per S2's own "DRY-RUN by default" contract).
- **Key columns:** `conda_name`, `classification`, `match_source`, `match_confidence`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

### 4.3 `universe-sbom` — Universe SBOM

- **Ports:** `universe_sbom`.
- **BSL model (NEW):** `build_universe_sbom_summary_model` — this page is a SUMMARY dashboard
  over the ~856k-component BOM, not a full component browser (rendering 856k rows in an
  `AgGrid` is a UX non-starter — see EXPERIENCE.md § 2.3 for the paging/summary rationale).
- **Source dataset:** the full-universe CycloneDX 1.6 BOM (`derived` layer, 14-day freshness
  gate).
- **Layout:** summary `Card`s (total components, actionable/mapped/conda-only/pypi-only
  slice counts, freshness age) + a slice `Filter` that narrows a paginated `AgGrid`.
- **Key columns:** `component_purl`, `slice`, `with_vulns_count`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

### 4.4 `inventory-match` — Inventory Match (FR-9 exception — report-artifact only)

- **Ports:** `inventory_match`.
- **BSL model (NEW):** `build_inventory_match_report_model` — the LATEST invocation's bucket
  breakdown (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN), not a
  live re-match (per-invocation user-supplied manifest, per FR-9).
- **Source dataset:** the CLI's own cached last-run output (sidecar JSON/SBOM), never a
  live catalog query.
- **Layout:** a bucket-count `Card` row + an `AgGrid` of the latest run's per-package rows.
- **Key columns:** `conda_name`, `bucket`, `freshness_percentile`, `match_confidence`.
- **`kind`:** `report-artifact`.

### 4.5 `add-handoff` — Add Handoff (FR-9 exception — report-artifact only)

- **Ports:** `add_handoff`.
- **BSL model (NEW):** `build_add_handoff_report_model` — the latest ADD-bucket packaging
  worklist (a write-path CLI; the dashboard surfaces its last output only).
- **Source dataset:** the CLI's cached last-run worklist.
- **Layout:** an `AgGrid` worklist (package, readiness, template, license-blocker flag).
- **Key columns:** `conda_name`, `readiness`, `license_blocker`.
- **`kind`:** `report-artifact`.
- **Forward-looking note (not implemented now):** the read-only constraint (FR-9) doesn't fully
  solve multi-agent coordination — two packaging agents could both pick up the same worklist row.
  A lightweight claim/lock sidecar (or at minimum a "last regenerated" + "in-progress elsewhere"
  flag) is a legitimate future need, but building it would cross into write-path territory this
  story must not touch; recorded here for a future story to pick up.

### 4.6 `library-futures` — Library Futures (FR-9 exception — report-artifact only)

- **Ports:** `library_futures`.
- **BSL model (NEW):** `build_library_futures_report_model` — `library-futures` is explicitly
  "in-memory / inventory-scoped by design" (no futures DB column) and CLI/pixi-only (not even
  an MCP tool) per `mcp-tools.md`; the dashboard surfaces the latest saved run only.
- **Source dataset:** the CLI's cached last-run scorecard.
- **Layout:** a `Card` per scored package (futures_score, tier badge) in a grid.
- **Key columns:** `package_name`, `futures_score`, `futures_tier`, `py314_readiness`.
- **`kind`:** `report-artifact`.
- **Cross-link:** direct navigation from `cve-watcher` (§ 3.1) — see that entry's cross-link
  note. Operator-override badges follow the non-authoritative-badge rule (§ 1) and carry their
  own timestamp, decoupled from the compute run's timestamp.

### 4.7 `recommend-2027` — Recommend 2027

- **Ports:** `recommend_2027`.
- **BSL model (NEW):** `build_recommend_2027_model` — the S5→S7 scorecard, per-signal
  breakdown.
- **Source dataset:** the annotated BOM the CLI emits (5 `cfe:*` properties).
- **Layout:** a tier-distribution `Card` (keep/watch/plan-migration/replace counts) + an
  `AgGrid` with per-signal drill-down (expandable row or a linked detail panel).
- **Key columns:** `package_name`, `futures_tier`, `futures_score`, `lts_status`, `eol_date`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

## 5. Seed-gap-suggester pages (4)

All four share one shape: a READ-ONLY proposal list against a hand-curated source-of-truth
file; the dashboard never writes the file (git review does). Each gets its own page because
their inputs/outputs are distinct artifacts, even though the shape repeats.

### 5.1 `lts-registry-gap` — LTS Registry Gap

- **Ports:** `lts_registry_gap`.
- **BSL model (NEW):** `build_lts_registry_gap_model` — dimensions `product_name`, `tier`
  (exact/likely); measure `candidate_count`.
- **Source dataset:** the endoflife.date product-list diff against `v_actionable_packages`.
- **Layout:** a tier-count `Card` + an `AgGrid` of proposed entries.
- **Key columns:** `product_name`, `tier`, `matched_conda_name`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

### 5.2 `cwe-seed-gap` — CWE Seed Gap

- **Ports:** `cwe_seed_gap`.
- **BSL model (NEW):** `build_cwe_seed_gap_model` — dimensions `cwe_id`, `tier`
  (strong/weak); measure `package_impact_count`.
- **Source dataset:** keyword-classified `Other`-bucket MITRE CWEs.
- **Layout:** a headline `Card` (Other-bucket package-impact count) + an `AgGrid`.
- **Key columns:** `cwe_id`, `tier`, `suggested_category`, `package_impact_count`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

### 5.3 `spdx-schema-gap` — SPDX Schema Gap

- **Ports:** `spdx_schema_gap`.
- **BSL model (NEW):** `build_spdx_schema_gap_model` — dimensions `license_id`, `tier`
  (add-to-schema/non-standard); measure `package_usage_count`. Supports a `--drift`-only
  staleness view.
- **Source dataset:** vendored SPDX enum diffed against upstream SPDX.
- **Layout:** a drift-age `Card` + an `AgGrid` ranked by real package license usage.
- **Key columns:** `license_id`, `tier`, `package_usage_count`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

### 5.4 `license-map-gap` — License Map Gap

- **Ports:** `license_map_gap`.
- **BSL model (NEW):** `build_license_map_gap_model` — dimensions `license_raw`, `tier`
  (likely/report); measure `package_count`.
- **Source dataset:** `pypi_intelligence.license_raw` rows where `license_spdx IS NULL`.
- **Layout:** a `Card` (unmapped total) + an `AgGrid` ranked by package count, with a
  suggested-SPDX-candidate column.
- **Key columns:** `license_raw`, `tier`, `package_count`, `suggested_spdx`.
- **`kind`:** `no-bsl-shell` → `bsl-shell`.

---

## 6. Page count reconciliation

| Bucket | CLI questions | Pages in this spine |
|---|---:|---:|
| Atlas CLIs (§ 3) | 10 remaining (`cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`, `scan-project`, `env-inspect`, `platform-breakdown`, `pyver-breakdown`, `channel-split`) | 8 (3 merged into `distribution-breakdown`) |
| Cyclonedx suite (§ 4) | 7 | 7 |
| Seed-gap suggesters (§ 5) | 4 | 4 |
| **Total** | **21** | **19** |

Matches the AC exactly: 19 pages, zero of the 21 remaining CLI questions dropped.
