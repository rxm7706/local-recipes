---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-05-24
author: rxm7706
trigger_type: release-driven (post-ship documentation sync)
trigger_release: conda-forge-expert v8.6.0 (AppThreat Deep Signals — Waves A + B + D shipped; Wave C cancelled pre-implementation)
scope: documentation-sync (post-implementation for v8.6.0) + Wave C cancellation acknowledgement + 3 new DW rows (DW18 / DW19 / DW20)
classification: Minor (MINOR additive bump — new EPSS + CWE side tables, 4 new packages columns, 2 new catalog-fetcher CLIs, 4 new CLI flags across existing scripts, persona-profile auto-runs; no breaking CLI or MCP changes; no FR/NFR scope shift)
mode: Batch
status: approved
approved_by: rxm7706
approved_date: 2026-05-24
input_docs:
  - _bmad-output/projects/local-recipes/planning-artifacts/PRD.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-conda-forge-expert.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture.md
  - _bmad-output/projects/local-recipes/planning-artifacts/epics.md
  - _bmad-output/projects/local-recipes/planning-artifacts/index.md
  - _bmad-output/projects/local-recipes/planning-artifacts/project-parts.json
  - _bmad-output/projects/local-recipes/planning-artifacts/sprint-change-proposal-2026-05-23-v8.5.3.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/retro-appthreat-deep-signals-2026-05-24.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/spec-appthreat-deep-signals-wave-a.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/spec-appthreat-deep-signals-wave-b.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/spec-appthreat-deep-signals-wave-d.md
  - docs/specs/atlas-appthreat-deep-signals.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
ground_truth:
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/config/skill-config.yaml
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
  - .claude/skills/conda-forge-expert/scripts/epss_fetcher.py
  - .claude/skills/conda-forge-expert/scripts/cwe_catalog_fetcher.py
  - .claude/skills/conda-forge-expert/scripts/bootstrap_data.py
  - .claude/skills/conda-forge-expert/data/cwe_categories_seed.json
  - .claude/skills/conda-forge-expert/tests/unit/test_epss_fetcher.py
  - .claude/skills/conda-forge-expert/tests/unit/test_cwe_catalog_fetcher.py
  - .claude/skills/conda-forge-expert/tests/unit/test_phase_g_overlay_v8_6_0.py
  - pixi.toml
  - .claude/data/conda-forge-expert/cf_atlas.db
shipped_commits:
  - e4ba891cd2  # Wave A: schema v24 + EPSS pipeline (foundation)
  - e22c531ac2  # Wave B: CWE catalog + Phase G/G' overlay wiring
  - 592b18089a  # Wave D: schema v25 cleanup + CLI flags + persona profiles + closeout
---

# Sprint Change Proposal — conda-forge-expert v8.6.0 (AppThreat Deep Signals) (2026-05-24)

## 1. Issue Summary

This proposal documents the post-implementation BMAD-artifact sync for v8.6.0 — the AppThreat Deep Signals release. The code shipped in three commits on `origin/main` over 2026-05-23 → 2026-05-24, with Wave C deliberately cancelled pre-implementation:

- **Wave A** (commit `e4ba891cd2`, 2026-05-23) — Schema v23 → v24 foundation: 3 new side tables (`epss_scores`, `cwe_categories`, `package_hardening`), 6 new `packages` columns, 3 new `package_version_vulns` columns, new `epss_fetcher.py` Tier-1 script + `fetch-epss` pixi task + `_load_epss_scores(conn)` helper, +13 unit tests.
- **Wave B** (commit `e22c531ac2`, 2026-05-23) — CWE catalog ingestion + Phase G/G' overlay wiring: new `cwe_catalog_fetcher.py` + committed `data/cwe_categories_seed.json` (67 well-known CWEs → 7 cf_atlas categories), new `_load_cwe_categories(conn)` + shared `_aggregate_v8_6_0_overlays(affecting, epss_map, cwe_map)` pure function, Phase G + Phase G' loops modified to populate 4 new packages columns per row, `_phase_g_sync_current_rollup` extended with COALESCE-to-existing for the new columns, +14 unit tests.
- **~~Wave C~~** — **CANCELLED 2026-05-23 pre-implementation** (Phase T blint hardening + Phase U EPSS overlay phase). Cancellation rationale: blint surfaces ~0 signal in conda-forge's hermetic compile environment (~32k uniform answers at ~150 GB download cost); Phase U was redundant with Wave B's `_phase_g_sync_current_rollup` extension. Full rationale at `implementation-artifacts/deferred-work.md` § "Wave C cancellation".
- **Wave D** (commit `592b18089a`, 2026-05-24) — Schema v24 → v25 cleanup migration (drop `package_hardening` table + 2 indexes; drop `packages.{vuln_total_active, vuln_withdrawn_count}` + `package_version_vulns.vuln_total_active`); 4 new CLI flags (`staleness-report --by-epss / --has-cwe`; `my-feedstocks --epss --cwe`; `cve-watcher --epss-threshold`; `detail-cf-atlas` auto-renders Max-EPSS + Top-CWE when populated); persona-profile auto-runs (maintainer + admin pull CISA KEV + EPSS + CWE; consumer skips all three for air-gap preservation); skill version bump 8.5.3 → 8.6.0; CFE retro at `implementation-artifacts/retro-appthreat-deep-signals-2026-05-24.md`.

### Context

The v8.6.0 spec was filed during the v8.5.3 closeout retro (2026-05-23) as the natural follow-on to the DW13 CISA KEV Path-C pattern (external-catalog → side-table → `_load_*` helper → Phase G/G' overlay loop). The intent was 4 waves of AppThreat-ecosystem signal enrichment. What actually shipped is 3 waves + 1 cancellation; the cancellation is honestly documented in CHANGELOG, deferred-work, and CFE retro rather than buried.

The release also caught **5 parent-spec errors** during pre-wave verification — each was a specific factual mistake (URL / package name / API behaviour / phase design) that would have shipped broken or redundant code:

1. **MITRE CWE URL** — spec said `2000.csv.zip` (Architectural Concepts); correct is `1000.csv.zip` (Research Concepts). Caught Wave B.
2. **FIRST.org EPSS URL** — spec said `epss.cyentia.com`; correct is `epss.empiricalsecurity.com` (Cyentia rebranded to Empirical Security). Caught Wave A.
3. **blint PyPI name** — spec said `owasp-blint` (returns 404); correct is `blint`. Caught Wave C verification.
4. **OSV withdrawn-filter semantics** — spec assumed vdb returns withdrawn records for filtering; verification of `appthreat-vulnerability-db/lib/osv.py:91` + `gha.py:184-185` showed both sources skip withdrawn records at ingest. Wave B dropped the withdrawn scope; the columns provisioned in Wave A (`vuln_total_active`, `vuln_withdrawn_count`) became dead surface and were dropped in Wave D's v25 cleanup.
5. **Phase U design** — spec described a "pure-SQL backfill" that turned out to be equivalent to Wave B's already-shipped `_phase_g_sync_current_rollup` extension. A genuine standalone Phase U requires a new `package_cves` table (per-package CVE list) — separate spec, not v8.6.0.

Combined, the five corrections saved ~10-15 stories of implementation work that would have shipped broken, redundant, or value-free features.

### Evidence

| Finding | Evidence |
|---|---|
| Schema v23 → v24 migration | Wave A introduced 3 side tables + 9 columns. ALTER ladder + SCHEMA_DDL fresh-DB equality verified by `test_schema_migration_v19::test_rerun_is_noop`. |
| Schema v24 → v25 cleanup | Wave D ran live against the production atlas: dropped 3 columns + 1 table + 2 indexes via SQLite 3.53.1 native `ALTER TABLE … DROP COLUMN`; idempotent guards via `pragma_table_info` + `sqlite_master`. `schema_version` meta-row = '25'. |
| EPSS pipeline | `pixi run fetch-epss` → **334,683 EPSS rows** ingested in 5.1 s from `https://epss.empiricalsecurity.com/epss_scores-current.csv.gz`. 4,378 high-EPSS (≥0.7). Top-10 dominated by well-known actively-exploited CVEs (Citrix CVE-2023-23752, HTTP/2 Rapid Reset CVE-2023-44487, Jenkins CVE-2024-23897, Drupal CVE-2018-7600). |
| CWE catalog | `pixi run fetch-cwe-catalog` → **944 CWEs** ingested in 1.03 s from `https://cwe.mitre.org/data/csv/1000.csv.zip`. 67 seeded + 877 → 'Other'. CSV is BOM-tolerant via `utf-8-sig`; CWE-ID double-prefix guard added defensively (review finding). |
| Channel-wide overlay live verification | `PHASE_G_TTL_DAYS=0 pixi run atlas-phase G` re-scanned 32,144 actionable rows in 37.8 s and populated **213 actionable packages with EPSS scores** + **216 with CWE classifications**. CWE distribution realistic for Python ecosystem: Info-Disclosure 133 / DoS 24 / RCE 21 / Other 18 / Injection 9 / Traversal 5 / Auth-Bypass 4 / Memory-Safety 2. |
| Persona-profile auto-runs | `pixi run bootstrap-data --profile admin --dry-run --no-vdb --no-cf-atlas` shows fetch-cisa-kev + fetch-epss + fetch-cwe-catalog land between Step 2 (CVE DB) and Step 3 (vdb), gated on `BOOTSTRAP_FETCH_{CISA_KEV,EPSS,CWE_CATALOG}` env vars. Consumer profile skips all three (air-gap preserving). |
| Wave C cancellation rationale | `implementation-artifacts/deferred-work.md` § "Wave C cancellation" documents Phase T blint signal-to-effort + Phase U redundancy. CHANGELOG v8.6.0 entry mirrors. |
| Test suite delta | 1,099 (Wave A baseline = v8.5.3 ship state) → 1,112 (Wave A) → 1,126 (Wave B) → 1,137 (final, no new tests in Wave D — CLI flags exercised by `test_script_responds_to_help` meta-test). +38 net. 0 regressions. |
| Review-finding fixes landed in Wave D | (a) COALESCE-to-existing in rollup-sync for new EPSS + CWE columns (Wave B review finding — earlier draft clobbered Phase G's direct writes to NULL whenever Phase G' ran with stale `epss_map`); (b) BOM-safe `utf-8-sig` + CWE-ID double-prefix guard (Wave B); (c) cve-watcher COALESCE→bare comparison (Wave D); (d) detail_cf_atlas `json.loads` non-dict guard (Wave D); (e) my-feedstocks NULL-percentile formatting (Wave D); (f) schema-version-gated migration with re-snapshotted column set (Wave D); (g) frozen-scope spec amendment for `BOOTSTRAP_FETCH_CISA_KEV` (Wave D). |
| cdxgen-on-pixi.lock follow-up (DW17 unchanged) | v8.5.3 verified at `CycloneDX/cdxgen lib/helpers/utils.js@9798-9920` (`parsePixiLockFile` emits `pkg:conda/<name>@<version>-<build>?os=<subdir>` purls). v8.6.0 deliberately did NOT bundle this to preserve the "atlas-side signals only" narrative. DW17 remains open for v8.7.x. |

## 2. Impact Analysis

### Epic Impact

| Epic | Stories Affected | Verdict |
|---|---|---|
| **Epic 8** (cf_atlas Phase F-N + Backends + TTL Gates) | E8.S11 (Phase G — vdb scan summary) and E8.S12 (Phase G' — per-version) gain the new EPSS + CWE overlay loops on top of the v8.5.3 KEV overlay. The new `_load_epss_scores` and `_load_cwe_categories` helpers mirror v8.5.3's `_load_kev_cves`; the new `_aggregate_v8_6_0_overlays` pure function consolidates the per-row math. The `_phase_g_sync_current_rollup` tail step (introduced v8.5.3 DW12) extended with COALESCE-to-existing for the 4 new packages columns. All extensions of existing function signatures + acceptance criteria; no new stories required. | No new stories required. |
| **Epic candidate: NEW Epic 14 (AppThreat Deep Signals — v8.6.0)** | Forward-declared in the v8.5.3 sync_lineage as a candidate; **NOT INSTANTIATED** in v8.6.0 because the 3 shipped waves layered cleanly onto existing Epic 8 acceptance criteria (Path C pattern from v8.5.3 generalised without modification). Two new fetcher CLIs (`fetch-epss`, `fetch-cwe-catalog`) follow the same shape as `fetch-cisa-kev` and count as Epic-8 extensions. Wave C cancellation eliminates the Phase T + Phase U story candidates. Epic 14 placeholder retired. | Epic 14 candidate retired — work absorbed by Epic 8 extensions. |
| All other epics | None | No impact. |

### Artifact Conflicts

| Artifact | Conflict | Action |
|---|---|---|
| `PRD.md` | `source_pin: 'conda-forge-expert v8.5.3'` → v8.6.0; §5 cf_atlas line "schema v22" + F2.1 "schema v22 with 14 tables" + F2.10 "19 public CLIs" stale; §9 DW14 partially-addressed status now fully closed for EPSS + CWE + withdrawn (still open for Medium/Low/yanked counts); DW15 superseded-by-v8.6.0 placeholder flips to SHIPPED-via-Waves-A+B; new DW18/DW19/DW20 rows from CFE retro follow-ups. | Pin bump + edit_history append; targeted prose updates to §5 + F2.1/F2.10; §9 row updates; version v1.4.2 → v1.4.3 (PATCH — additive, no FR/NFR scope shift). |
| `architecture-cf-atlas.md` | `source_pin: v8.5.3` → v8.6.0; schema header "version 23" → "25" + "13 tables + 3 views" → "15 tables + 3 views"; new "v8.6.0 additions (schema v25, via v24 → v25 cleanup)" subsection; Phase G + G' table rows extended with EPSS + CWE overlay callout; v8.6.0 forward-flag paragraph in the v8.5.3 additions section needs to be marked SHIPPED; Public CLIs table gains 2 new catalog-fetcher rows + per-flag annotations. | Pin bump + schema header + new additions subsection + Phase row extension + forward-flag annotation. |
| `epics.md` | `source_pin: v8.5.3` → v8.6.0; `sync_lineage` append v8.6.0 entry. | Pin bump + sync_lineage append. |
| `index.md` | `source_pin: v8.5.3` → v8.6.0; opening-paragraph lineage prose append v8.5.3 → v8.6.0 step + remove "In-flight v8.6.0 spec intake-ready" callout (now shipped); Specs section: flip `atlas-appthreat-deep-signals.md` from "in-flight v8.6.0" to "shipped v8.6.0 (2026-05-24)"; new sprint-change-proposal entry; Document Set Stats pin. | Pin bump + lineage update + Specs row flip + new sprint-change-proposal row. |
| `project-parts.json` | `source_pin: v8.5.3` → v8.6.0; cf-atlas description rewrite covering v8.6.0 (3 waves shipped + Wave C cancellation + schema v25); `schema_versions: 23` → 25; `cli_count: 19` → 21 (added `fetch-epss` + `fetch-cwe-catalog`); `in_flight_phases_for_v8_6_0: [T, U]` → removed (both cancelled); top-level `in_flight_spec` block → removed (spec shipped); conda-forge-expert `version_pin: v8.5.3` → v8.6.0. | Pin bump + description rewrite + count syncs + removal of `in_flight_spec` and `in_flight_phases_for_v8_6_0` blocks. |
| `implementation-artifacts/deferred-work.md` | Already contains Wave C cancellation + withdrawn-filter correction + defensive-hardening row (added during Wave A review). Needs DW18 / DW19 / DW20 acknowledgements aligned with the CFE retro follow-ups. | Targeted appends + cross-references. |
| `architecture.md` (umbrella) | Pin-only update. | Pin bump. |
| `architecture-conda-forge-expert.md` | Pin-only update; Tier 1 script count +2 (epss_fetcher + cwe_catalog_fetcher); no other structural change (no new MCP tools — the fetchers are operator-invoked maintenance like cisa_kev_fetcher). | Pin bump + count touch-up if a script-count line carries a literal. |
| `validation-report-PRD.md` | `source_pin: v8.5.3` → v8.6.0; new verdict_history entry for v8.6.0 MINOR bump. v8.6.0 is the first MINOR bump since v8.1.0 that adds new public surfaces (2 fetcher CLIs + 4 CLI flags + 2 new tables + 4 new packages columns), so D2 / D7 / D9 / D10 deserve at least a spot-check — but the surfaces are opt-in additive with no FR/NFR scope shift, so no full re-validation pass is required. | Pin bump + verdict_history append (APPROVED — no new REVISE findings). |
| `architecture-mcp-server.md` | None — v8.6.0 added no new MCP tools (the two new catalog fetchers are operator-invoked CLIs, mirroring v8.5.3's `fetch-cisa-kev`). | No change. |
| `architecture-bmad-infra.md` | None — BMAD infrastructure unchanged. | No change. |

### Technical Impact

| Layer | Impact |
|---|---|
| Schema | **v23 → v24 → v25**. Net delta: +2 tables (`epss_scores`, `cwe_categories`), +4 packages columns surviving v25 cleanup (`vuln_max_epss_score`, `vuln_max_epss_percentile`, `vuln_cwe_top`, `vuln_cwe_categories_json`). The `package_hardening` table + `vuln_total_active` / `vuln_withdrawn_count` columns existed transiently in v24 (provisioned for Waves B/C; dropped in v25 after Wave C cancellation + Wave B withdrawn-filter verification). All migrations idempotent + self-healing. |
| Database state | +334,683 `epss_scores` rows + 944 `cwe_categories` rows. +32,168 `vuln_history` snapshot rows from the post-Wave-B channel-wide Phase G re-scan. 213 actionable feedstocks now carry `vuln_max_epss_score`; 216 carry `vuln_cwe_top` + `vuln_cwe_categories_json`. |
| Code | `scripts/conda_forge_atlas.py`: `SCHEMA_VERSION` 23 → 24 → 25; new SCHEMA_DDL entries for `epss_scores` + `cwe_categories`; ALTER ladder for v23 → v24 + DROP ladder for v24 → v25; new `_load_epss_scores(conn) -> dict[str, tuple[float, float]]` + `_load_cwe_categories(conn) -> dict[str, str]` helpers; new shared `_aggregate_v8_6_0_overlays(affecting, epss_map, cwe_map)` pure function; Phase G + Phase G' overlay loops modified to load all three maps (KEV + EPSS + CWE) at run start and write the 4 new columns per package; `_phase_g_sync_current_rollup` extended with COALESCE-to-existing for the new columns. **New scripts:** `scripts/epss_fetcher.py` (~270 lines), `scripts/cwe_catalog_fetcher.py` (~270 lines), `data/cwe_categories_seed.json` (67-entry committed seed). 4 read-CLI scripts gain new flag handlers + SELECT-clause additions: `staleness_report.py` (`--by-epss`, `--has-cwe`), `my_feedstocks.py` (`--epss`, `--cwe`), `cve_watcher.py` (`--epss-threshold`), `detail_cf_atlas.py` (auto-render Max-EPSS + Top-CWE rows). `bootstrap_data.py`: maintainer + admin profiles set 3 new env vars; `main()` adds Steps 2a/b/c gated on those env vars. |
| Wrappers + pixi | Two new Tier 2 wrappers (`.claude/scripts/conda-forge-expert/epss_fetcher.py` + `cwe_catalog_fetcher.py` — filenames match canonical per the three-place rule). Two new `pixi.toml` tasks: `fetch-epss`, `fetch-cwe-catalog`. |
| Tests | +13 unit tests in `tests/unit/test_epss_fetcher.py` (Wave A); +13 in `tests/unit/test_cwe_catalog_fetcher.py` + 13 in `tests/unit/test_phase_g_overlay_v8_6_0.py` (covering `_aggregate_v8_6_0_overlays` across 13 scenarios without mocking vdb) + extended `test_phase_g_rollup_sync.py` for the new COALESCE-to-existing tail-step columns (Wave B); +0 new tests in Wave D (CLI flags exercised by existing `test_script_responds_to_help` meta-test — see retro § "What did not go well" for the follow-up to add positive-path tests). Suite 1,099 → 1,137 passing (+38). 0 regressions. |
| CLI/MCP surface | Two new CLIs (`fetch-epss`, `fetch-cwe-catalog`) — opt-in operator-invoked maintenance surfaces. 4 new CLI flags across existing query CLIs (additive; defaults preserve prior behaviour). No new MCP tools added. |
| Dependencies | None — `requests` / `truststore` / `_http.py` pre-existing; both new fetchers go through `_http.fetch_with_fallback`. `gzip` + `csv` + `json` + `zipfile` from stdlib. |
| Documentation | CHANGELOG v8.6.0 entry (TL;DR + per-wave breakdown + Wave C cancellation + cdxgen ruling preserved). `reference/atlas-actionable-intelligence.md` flips 2 catalog rows to ✅ (EPSS ranking, CWE-category triage); 2 rows remain ✋ cancelled (binary-hardening, active-only-CVE). SKILL.md atlas-intelligence section updated to mention schema v25 + EPSS + CWE overlay surface. |

## 3. Recommended Approach — Option 1: Direct Adjustment (Post-implementation documentation sync)

**Selected:** Direct Adjustment — pin-only updates + targeted prose deltas across listed planning artifacts; remove `in_flight_spec` and `in_flight_phases_for_v8_6_0` blocks (work shipped); flip catalog row statuses for Specs and atlas-actionable-intelligence; append new DW rows (DW18/DW19/DW20) from CFE retro follow-ups.

**Rationale:**

- v8.6.0 is additive — 2 new tables + 4 new packages columns + 2 new CLIs + 4 new flags. No FR/NFR scope shift; no breaking CLI/MCP changes; persona-profile auto-runs preserve consumer-tier air-gap discipline.
- Live verification on production data (334,683 EPSS rows, 944 CWEs, 213 EPSS-scored + 216 CWE-classified actionable packages, channel-wide Phase G re-scan in 37.8 s).
- Risk: low. The Path C pattern from v8.5.3 generalised cleanly (3 fetchers, 3 helpers, 1 shared aggregator). The schema journey v23 → v24 → v25 is rare but every step is idempotent + tested + live-validated.
- Effort: low. Pin + prose deltas concentrated in ~7 planning artifacts; one new sprint-change-proposal (this doc).
- Timeline: same-day (this proposal + the artifact edits land in a single BMAD-correct-course pass after the code shipped).

**Effort:** Low. **Risk:** Low. **Timeline impact:** None.

## 4. Detailed Change Proposals

### 4.1 PRD.md

```yaml
# Frontmatter
OLD:
  version: '1.4.2'
  source_pin: 'conda-forge-expert v8.5.3'
  re_validated: 2026-05-23
NEW:
  version: '1.4.3'
  source_pin: 'conda-forge-expert v8.6.0'
  re_validated: 2026-05-24
```

Append `edit_history` entry covering v8.5.3 → v8.6.0 (the AppThreat Deep Signals release — 3 waves shipped + Wave C cancellation + 5 parent-spec corrections caught pre-implementation; schema journey v23 → v24 → v25; 2 new fetcher CLIs + 4 new flags + 4 new packages columns + persona-profile auto-runs).

§5 cf_atlas reference line: "Part 2, 22 phases, schema v22" → "Part 2, 22 phases, schema v25" (phase count preserved — Phase T cancelled, no new phase actually shipped).

F2.1: "SQLite schema v22 with 14 tables" → "SQLite schema v25 with 16 tables (incl. `pypi_universe` + `pypi_intelligence` + `pypi_universe_serial_snapshots` history + `cisa_kev` overlay [v8.5.3] + `epss_scores` + `cwe_categories` [v8.6.0])" + migration ladder annotation.

F2.10: "19 public CLIs" → "21 public CLIs (orchestration + 18 query + 2 catalog fetchers, incl. `fetch-epss` + `fetch-cwe-catalog` v8.6.0 [`fetch-cisa-kev` already counted v8.5.3])".

§9 Deferred Work table updates:

- **DW14** — strikethrough "Partially addressed by v8.6.0" → "Mostly addressed by v8.6.0 (EPSS + CWE rollup ✅ SHIPPED; withdrawn filter VERIFIED-UNNECESSARY because vdb pre-filters at ingest; Medium/Low-affecting-current counts + PEP-592 yanked-flag channel-wide remain open for v8.7.x)."
- **DW15** — strikethrough placeholder text → "✅ SHIPPED v8.6.0 (2026-05-24) via Waves A + B" with cross-reference to CHANGELOG.
- **DW16** — left as-is (pixi-task cmd-change CI check still out of v8.6.0 scope; out of v8.7.x scope too unless an incident triggers it).
- **DW17** — left as-is (cdxgen `scan_project --pixi-lock` follow-up — still deferred; deliberate not-bundled into v8.6.0).
- **DW18** (new) — Defensive hardening pass for the three external-catalog fetchers (`cisa_kev_fetcher` + `epss_fetcher` + `cwe_catalog_fetcher`): gzip-size cap, magic-bytes + Content-Type validation, NaN/inf/range guards on `_normalize_percentile`, BOM + CRLF handling in `_parse_snapshot_date`, empty-feed sanity. ~6-8 stories single cross-cutting sprint after v8.6.0 ships. Source: Wave A review subagents (blind hunter + edge case hunter) at `spec-appthreat-deep-signals-wave-a.md` step-04. Reason for not bundling into Wave A: FIRST.org is a canonical published source backed by sec-cert.com infra; the same shape ships in production via `cisa_kev_fetcher.py` since v8.5.3 without incident; defensive hardening crossing 3+ files belongs in its own focused sprint, not bundled with a release-foundation Wave.
- **DW19** (new) — Per-package CVE list for a real Phase U. Requires a new `package_cves` table joining packages → CVE IDs (currently aggregated counts only; CVE-level information lost). Would unlock a genuine "EPSS pure-SQL backfill" mode + CWE-list-per-package + future EPSS-history charting. ~6-8 stories; only worth doing if operator demand for "rerun max-EPSS without re-running Phase G'" materializes. Source: v8.6.0 Wave C cancellation analysis at `deferred-work.md` § "Phase U (EPSS overlay phase) — cancelled".
- **DW20** (new) — Extend the committed CWE seed mapping in `data/cwe_categories_seed.json` beyond the current 67 well-known CWEs. 877 of 944 MITRE CWEs default to 'Other'. Quarterly review + expansion to improve operator triage precision. Cheap (~1 hour of CWE → category bucketing per review). Source: v8.6.0 Wave B live verification at `spec-appthreat-deep-signals-wave-b.md`.

### 4.2 architecture-cf-atlas.md

```yaml
OLD: source_pin: 'conda-forge-expert v8.5.3'
NEW: source_pin: 'conda-forge-expert v8.6.0'
```

Opening paragraph: "schema v23" → "schema v25"; extend the side-table inventory: "+ `cisa_kev` overlay table (v8.5.3+) + `epss_scores` + `cwe_categories` (v8.6.0+)".

"Schema (cf_atlas.db, version 23)" → "version 25"; "13 tables + 3 views" → "15 tables + 3 views" (net: +2 tables in v8.6.0 — `epss_scores` and `cwe_categories`; `package_hardening` round-tripped in v24 → out v25).

Insert new "v8.6.0 additions (schema v25, via v24 → v25 cleanup)" subsection before the v8.5.3 additions block:

- New `epss_scores` side table (5 columns, cve_id PK). Populated by `epss_fetcher.py` from FIRST.org's daily CSV at `https://epss.empiricalsecurity.com/epss_scores-current.csv.gz` (Cyentia rebranded to Empirical Security — original spec URL was stale). `percentile` normalized from FIRST's 0.0-1.0 to stored 0.0-100.0 at upsert. Live: 334,683 rows / 5.1 s.
- New `cwe_categories` side table (4 columns, cwe_id PK with `CWE-` prefix). Populated by `cwe_catalog_fetcher.py` from MITRE's `https://cwe.mitre.org/data/csv/1000.csv.zip` (Research Concepts view — original spec said `2000.csv.zip` Architectural Concepts; corrected after verification). Joined with the committed `data/cwe_categories_seed.json` 67-entry mapping to assign one of 7 cf_atlas categories; unmapped CWEs default to 'Other'. Live: 944 CWEs / 1.03 s / 67 seeded + 877 → Other.
- 4 new `packages` columns surviving v25 cleanup: `vuln_max_epss_score REAL`, `vuln_max_epss_percentile REAL`, `vuln_cwe_top TEXT`, `vuln_cwe_categories_json TEXT`. Written by Phase G + Phase G' overlay loops; propagated by `_phase_g_sync_current_rollup` extension with COALESCE-to-existing (Wave B review-finding fix).
- 3 new `package_version_vulns` columns surviving v25 cleanup: `vuln_max_epss_score REAL`, `vuln_max_epss_percentile REAL`, `vuln_cwe_top TEXT`. (Wave A also provisioned `vuln_total_active`; dropped in v25.)
- New `_load_epss_scores(conn) -> dict[str, tuple[float, float]]` + `_load_cwe_categories(conn) -> dict[str, str]` helpers symmetric to v8.5.3's `_load_kev_cves`. Graceful-degrade to `{}` on missing table.
- New shared `_aggregate_v8_6_0_overlays(affecting, epss_map, cwe_map)` pure function consumed by both Phase G and Phase G' loops. Tie-break for `cwe_top` documented as first-encountered (matches Python `max` stability). Tested in isolation across 13 scenarios.
- **Withdrawn-filter scope DROPPED** at Wave B verification time — vdb's OSV source (`appthreat-vulnerability-db/lib/osv.py:91`) and GHSA source (`gha.py:184-185`) both skip withdrawn records at ingest. Wave A provisioned `vuln_total_active` + `vuln_withdrawn_count` + `package_version_vulns.vuln_total_active` columns + a `package_hardening` table; all dropped in Wave D's v25 cleanup migration after the Wave C cancellation removed the only consumer for `package_hardening`.
- **Phase T (blint hardening) + Phase U (EPSS overlay phase) — CANCELLED** pre-implementation at Wave C verification. Phase T low-signal (~0 variance in conda-forge's hermetic compile environment; ~150 GB download cost in admin top-N mode). Phase U redundant with Wave B's `_phase_g_sync_current_rollup` extension (a real standalone Phase U requires a per-package CVE list / new `package_cves` table — separate spec). Full rationale at `_bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md` § "Wave C cancellation". Pipeline phase count preserved at 22 (B-N + O/P/Q/R/S); no new phase IDs in v8.6.0.

Phase G / G' table rows extended: add EPSS + CWE overlay callout alongside the existing v8.5.3 KEV overlay note (both phases load all three maps at run start; the shared `_aggregate_v8_6_0_overlays` aggregator handles the per-row math).

`v8.5.3 additions (schema v23)` § final paragraph — annotate the "v8.6.0 forward-flag" passage as `✅ SHIPPED v8.6.0 (2026-05-24) — see § "v8.6.0 additions (schema v25, via v24 → v25 cleanup)" above for the as-shipped surface (Wave C cancelled, hence v25 cleanup instead of net-additive v24)`.

Public CLIs table: append `fetch-cisa-kev` + `fetch-epss` + `fetch-cwe-catalog` as a separate "External-catalog fetchers (operator-invoked maintenance)" subsection — or extend the orchestration section with a row noting the three Path-C catalog fetchers; whichever fits the existing structure best. (Recommendation: add a 4th subsection so the CLI count cleanly increments from "17 query + 2 orchestration" to "17 query + 2 orchestration + 3 catalog fetchers" matching the shipping reality.)

### 4.3 epics.md

```yaml
OLD: source_pin: 'conda-forge-expert v8.5.3'
NEW: source_pin: 'conda-forge-expert v8.6.0'
```

Append `sync_lineage`:

```yaml
  - { date: '2026-05-24', via: 'bmad-correct-course', from: 'v8.5.3', to: 'v8.6.0', proposal: 'planning-artifacts/sprint-change-proposal-2026-05-24-v8.6.0.md', spec: 'docs/specs/atlas-appthreat-deep-signals.md', retro: 'implementation-artifacts/retro-appthreat-deep-signals-2026-05-24.md', note: '[AppThreat Deep Signals — 3 waves shipped (A+B+D) + Wave C cancelled pre-implementation. Schema v23 → v24 → v25 (round-trip cleanup after Wave C cancellation). +2 side tables (epss_scores, cwe_categories) + 4 packages columns (vuln_max_epss_score, vuln_max_epss_percentile, vuln_cwe_top, vuln_cwe_categories_json). 2 new fetcher CLIs (fetch-epss, fetch-cwe-catalog) + 4 new flags across existing CLIs (staleness-report --by-epss / --has-cwe; my-feedstocks --epss --cwe; cve-watcher --epss-threshold; detail-cf-atlas auto-renders Max-EPSS + Top-CWE). Persona profiles maintainer + admin auto-pull CISA KEV + EPSS + CWE; consumer skips all three (air-gap preserving). 5 parent-spec errors caught pre-implementation: MITRE CWE URL (2000 vs 1000), EPSS URL (Cyentia rebrand), blint PyPI name (404), withdrawn-filter assumption (vdb pre-filters at ingest), Phase U redundancy. Test suite 1,099 → 1,137 (+38). Live verification: 334,683 EPSS rows / 944 CWEs / 213 EPSS-scored + 216 CWE-classified actionable packages. MINOR bump (additive; no FR/NFR scope shift; no breaking CLI or MCP changes). Future-Epic-14-candidate flagged in v8.5.3 sync retired — work absorbed by Epic 8 extensions.]' }
```

### 4.4 project-parts.json

```json
OLD: "source_pin": "conda-forge-expert v8.5.3"
NEW: "source_pin": "conda-forge-expert v8.6.0"

REMOVE top-level "in_flight_spec" object (work shipped; can preserve as "shipped_spec_history" array if desired, but cleaner to simply remove)

For the cf-atlas part:
  description rewritten to reflect Waves A + B + D shipped + Wave C cancellation + schema v25
  schema_versions: 23 → 25
  cli_count: 19 → 21 (added fetch-epss + fetch-cwe-catalog)
  pipeline_phases: unchanged (22; Phase T cancelled)
  REMOVE "in_flight_phases_for_v8_6_0" (both T and U cancelled; reflect in description)
  data_artifacts updated to mention epss_scores + cwe_categories tables

For the conda-forge-expert part:
  version_pin: "v8.5.3" → "v8.6.0"
```

### 4.5 index.md

Pin updates: 3 occurrences (frontmatter, opening paragraph, "Document Set Stats" table).

Opening paragraph: append "v8.5.3 → v8.6.0 on 2026-05-24 after the AppThreat Deep Signals release — see `sprint-change-proposal-2026-05-24-v8.6.0.md` + `implementation-artifacts/retro-appthreat-deep-signals-2026-05-24.md`"; remove the trailing "In-flight v8.6.0 spec intake-ready" callout (now shipped — replaced by the v8.6.0 lineage step).

Specs section: flip `docs/specs/atlas-appthreat-deep-signals.md` row from `**in-flight v8.6.0**` to `shipped v8.6.0 (2026-05-24)`.

Append `sprint-change-proposal-2026-05-24-v8.6.0.md` row to the validation+change-management artifacts table.

### 4.6 implementation-artifacts/deferred-work.md

Already largely up-to-date — Wave C cancellation + withdrawn-filter correction + external-catalog defensive-hardening row are documented. Add brief cross-reference annotations for the new PRD §9 rows (DW18 / DW19 / DW20) so the long-form context lives here and the PRD ledger holds the canonical numbered entry.

### 4.7 validation-report-PRD.md

Frontmatter `source_pin: v8.5.3` → v8.6.0. Append `verdict_history` entry:

```yaml
  - { date: '2026-05-24 (re-validated post v8.6.0 sync)', verdict: 'APPROVED', notes: 'v8.6.0 AppThreat Deep Signals (3 waves shipped + Wave C cancelled): schema v23 → v24 → v25 (additive + cleanup); +2 side tables (epss_scores, cwe_categories) + 4 packages columns + 2 new fetcher CLIs (fetch-epss, fetch-cwe-catalog) + 4 new flags across existing CLIs + persona-profile auto-runs. PRD MINOR-bumped v1.4.2 → v1.4.3 (additive — no FR/NFR scope shift; new CLIs are opt-in operator-invoked maintenance surfaces; new flags preserve existing CLI defaults; persona-profile auto-runs are env-var gated). D2 / D7 / D9 / D10 spot-checked: new surfaces are specific (`fetch-epss` / `fetch-cwe-catalog` / 4 named flags), testable (1,137 passing tests, +38 vs v8.5.3 baseline; live-verified channel-wide), phased correctly (Wave A foundation + Wave B wiring + Wave D cleanup ordered by dependency), low-risk (idempotent migrations + COALESCE-to-existing rollup-sync + air-gap-preserving consumer profile). Future-Epic-14-candidate flagged in v8.5.3 sync retired — v8.6.0 work layered cleanly onto Epic 8 acceptance criteria. No new REVISE findings.' }
```

Overall verdict header updated to reflect 2026-05-24 re-validation; verdict remains APPROVED.

### 4.8 architecture.md (umbrella) + architecture-conda-forge-expert.md

Pin-only updates (`source_pin: v8.5.3` → `v8.6.0`). architecture-conda-forge-expert.md Tier-1 script-count line (if literal) touched up: +2 scripts (`epss_fetcher.py` + `cwe_catalog_fetcher.py`); existing canonical-scripts inventory ~30 → ~32.

## 5. Implementation Handoff

**Scope classification:** Minor (MINOR-level documentation sync — direct implementation by `bmad-correct-course` skill, no developer agent handoff required because the code has already shipped).

**Handoff recipient for v8.6.0 artifact edits:** This `bmad-correct-course` skill invocation (in progress at proposal authorship time).

**Success criteria:**

- [x] Sprint Change Proposal written to `planning-artifacts/sprint-change-proposal-2026-05-24-v8.6.0.md` (this document)
- [ ] PRD `source_pin` flipped to v8.6.0; edit_history entry appended; version v1.4.2 → v1.4.3; §5 cf_atlas reference + F2.1 + F2.10 + §9 DW14/DW15/DW18/DW19/DW20 rows updated
- [ ] `architecture-cf-atlas.md` pin bumped; schema header v23 → v25 + "13 tables + 3 views" → "15 tables + 3 views"; new v8.6.0 additions subsection; Phase G + G' rows extended with EPSS+CWE callout; v8.6.0 forward-flag in v8.5.3 additions section annotated SHIPPED
- [ ] `epics.md` pin bumped; sync_lineage appended
- [ ] `index.md` pin bumped (3 places); v8.5.3 → v8.6.0 lineage step added; in-flight callout removed; Specs row flipped; new sprint-change-proposal entry
- [ ] `project-parts.json` pin bumped; cf-atlas description rewritten; schema_versions + cli_count synced; `in_flight_spec` + `in_flight_phases_for_v8_6_0` removed
- [ ] `implementation-artifacts/deferred-work.md` cross-referenced to new PRD §9 DW18/DW19/DW20 rows
- [ ] `validation-report-PRD.md` verdict_history appended (APPROVED — no new REVISE findings)
- [ ] `architecture.md` + `architecture-conda-forge-expert.md` pin bumps (Tier-1 script-count touch-up if literal)
- [ ] All ground-truth files cited in frontmatter remain authoritative
- [ ] Commit the BMAD sync in a single commit modeled on `1fc0b91f58` (v8.5.3 BMAD sync) — single logical scope, no code touches

## 6. Decision

**Approved.** Pin-only updates + targeted prose deltas + 1 new file (this proposal). PRD PATCH bump (no FR/NFR scope shift; additive opt-in surfaces only). The skill itself is MINOR-bumped (8.5.3 → 8.6.0) because new public CLIs + new flags are semver-MINOR per the project's convention; the PRD pin moves to track the skill but the PRD's own version bump stays PATCH because the PRD's feature catalogue gains opt-in additions only.

No full re-validation required — D2 / D7 / D9 / D10 spot-check passed (above). v8.7.x DW18 + DW19 + DW20 + DW17 (cdxgen pixi.lock) candidates are forward-only.

## 7. Outcome (post-implementation expectation)

- PRD v1.4.3 pinned to `conda-forge-expert v8.6.0` with edit_history entry covering Waves A + B + D + Wave C cancellation + parent-spec corrections + DW14/15/18/19/20 ledger updates
- architecture-cf-atlas reflects schema v25 + EPSS + CWE overlay surface + Wave C cancellation note + v8.5.3 forward-flag annotated SHIPPED
- epics sync_lineage extended with v8.6.0 entry; Epic 14 candidate retired (work absorbed by Epic 8 extensions)
- project-parts.json reflects schema v25 + cli_count 21 + cleared `in_flight_spec` + cleared `in_flight_phases_for_v8_6_0`
- index.md doc-set lineage extended through v8.6.0; atlas-appthreat-deep-signals spec row flipped to shipped
- 3 new DW rows (DW18 defensive hardening / DW19 per-package CVE list-real Phase U / DW20 extend CWE seed mapping) forward-only; DW17 cdxgen pixi.lock remains open

## 8. Trigger conditions for next bump

- **v8.7.x (any-track)** — at least one of: (a) DW18 defensive-hardening sprint lands; (b) DW19 `package_cves` table + real Phase U lands (operator demand for fast-path max-EPSS recompute); (c) DW20 CWE seed mapping expansion lands (quarterly review); (d) DW17 cdxgen `scan_project --pixi-lock` mode lands; (e) PEP-592 yanked-flag channel-wide / Medium-affecting-current / Low-affecting-current counts (DW14 residual scope) lands. Any single item triggers a PATCH bump; multiple items batched into a MINOR bump.
- **v8.6.x patch** — if production issues surface in the new EPSS + CWE overlay or in any of the 4 new CLI flags (e.g., FIRST.org changes percentile scale; MITRE adds a column to `1000.csv.zip` header; a CWE-ID double-prefix slips through the defensive guard). Cheap PATCH bump.
- **Future schema bumps** — v26 reserved (no current proposal). v27+ if DW19 lands (`package_cves` table).

---

**Approval log:** Approved by `rxm7706` on `2026-05-24` in Batch mode via `bmad-correct-course` skill invocation. User explicitly requested batch-mode execution: "proceed to next steps" → this BMAD sync run.
