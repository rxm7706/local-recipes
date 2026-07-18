# Full Engineering Contracts — the binding per-phase contract list

These are the contracts the ports MUST preserve (spec:250–286 — "Per-phase engineering
contracts"; the architecture SPINE labels this list **AD-10**. NOTE: the string "AD-10"
does not appear in the spec itself — it is the planning-artifact label; the spec's own
binding references are `docs/specs/cfe-shipped-releases.md` + `reference/atlas-phase-engineering.md`,
spec:251–252). All code citations at commit `b18cbb5`. `CFA` = conda_forge_atlas.py.

## Contents

- [Phase P two-layer cost gate](#phase-p-two-layer-cost-gate)
- [Phase K scheduler](#phase-k-scheduler)
- [Phase F provenance discipline](#phase-f-provenance-discipline)
- [Phase H serial gate](#phase-h-serial-gate)
- [Phase B.5 attribution](#phase-b5-attribution)
- [Mapping: g10_spelling no-clobber](#mapping-g10_spelling-no-clobber)
- [KEV overlay + CVSS coercion](#kev-overlay--cvss-coercion)
- [EPSS 0-100 normalization](#epss-0-100-normalization)
- [purl / cfe namespace](#purl--cfe-namespace)
- [View discipline](#view-discipline)
- [Single-write-path (add-handoff)](#single-write-path-add-handoff)
- [Post-v25 schema shape](#post-v25-schema-shape)
- [Code-vs-spec divergences](#code-vs-spec-divergences)

## Phase P two-layer cost gate

Contract (spec:253–261): free dry-run preflight aborts above `PHASE_P_MAX_COST_USD`,
PLUS server-side `maximum_bytes_billed` hard cap and a job timeout; mode machine
(first-pull / incremental / gap-revert / empty-window no-op) and `INSERT OR IGNORE`
idempotency port intact; `test_no_thirty_gb_lie.py` regression-guards cost claims.

Code anchors:
- `PHASE_P_MAX_COST_USD` default 10 — documented [SRC:CFA:L7606], read [SRC:CFA:L7673].
- `PHASE_P_MAX_COST_FIRST_PULL_USD` default 100 — documented L7607, read L7660/L7667; over-cap message L7729–7731.
- Dry-run preflight (`dry_run=True, use_query_cache=False`, returns `total_bytes_processed`) — [SRC:CFA:L7709–7717]; cap comparison `if est_usd > cap_usd:` L7728.
- Hard byte cap `max_bytes = int((cap_usd / usd_per_tb) * 1e12)` L7743 → `maximum_bytes_billed=max_bytes` [SRC:CFA:L7752].
- Job timeout `PHASE_P_JOB_TIMEOUT_MS` default 600000 — documented L7608, read L7687, passed `job_timeout_ms=timeout_ms` L7753.
- Date bounds: **literal `TIMESTAMP` bounds on the `timestamp` column** L7704–7705. See [divergence D1](#code-vs-spec-divergences).
- Dispatcher `phase_p_pypi_downloads` L7352 → `_phase_p_bigquery` L7562 / `_phase_p_clickhouse` L7399 / `_phase_p_skip` L7342; `PHASE_P_FORCE_FIRST_PULL` L7610/L7646.

## Phase K scheduler

Contract (spec:262–266): GitHub's secondary (burst) rate limit is invisible to
`/rate_limit` — single worker with a 3 RPS token bucket by default, host-agnostic
(GitHub/GitLab/Codeberg), `PHASE_K_AGGRESSIVE=1` opt-out; 403s land in
`upstream_versions.last_error` and re-pick via the TTL bypass.

Code anchors:
- `class _RateLimitedScheduler:` [SRC:CFA:L1345]; single-worker default L1344/L1352–1353; ctor `(rps: float, bucket_capacity: int = 10)` L1358; refill `self.bucket + elapsed * self.rps` L1393; wait L1397.
- Default 3.0 RPS ("~3x safety margin") L1333; env `PHASE_K_REQUESTS_PER_SECOND` default "3.0" L5117; fallback L5131.
- `PHASE_K_AGGRESSIVE=1` restores `ThreadPoolExecutor(max_workers=8)` — L1340, L5077, read L5132; non-"1" values do NOT re-arm burst L5114–5115; burst warning L5138; glacial-RPS warning L1372–1376.
- Instantiation `scheduler = _RateLimitedScheduler(rps=rps_default)` L5395.
- `Retry-After` parsing: `_parse_retry_after` [SRC:CFA:L2668], consumed L2732 / L4121 / L8184. (NOT in `_http.py` — _http's only backoff is un-jittered `2 ** attempt`.)

## Phase F provenance discipline

Contract (spec:267–275): `downloads_source` values (`anaconda-api` / `s3-parquet` /
`merged`) correlated-but-distinct, never interchangeable; breakdown tables written
ONLY on the s3-parquet path via DELETE-by-scope-key + INSERT in one transaction;
`downloads_30d` = latest calendar month, NOT a rolling window; one consolidated
pyarrow sweep for all Phase F+ metrics; dirty `pkg_python` column regex-filtered.

Code anchors:
- `downloads_source` column [SRC:CFA:L188] (attribution comment L189; docstring L3593–3595); write sites: api L2925/L2945, s3 L3378/L3390.
- s3-only breakdown tables: `package_platform_downloads` L538 (s3-only comment L530–534), `package_python_downloads` L549, `package_channel_downloads` L572 (comment L570–571 "the API-path fallback never touches").
- DELETE-by-scope-key (chunked at 500 for SQLite's 999-param limit): rationale L3423–3427; DELETEs L3435 / L3440 / L3450 (Wave-3 mirror comment L3444–3448).
- Calendar-month rule: "downloads_30d == single most-recent month (parquet is monthly)." [SRC:CFA:L3162]; schema comment L197–198.

## Phase H serial gate

Contract (spec:276–278): eligibility = never-fetched OR serial moved OR 30-day safety
re-check; the denominator must never re-include pypi-only rows (the pre-v7.9.0
6-hour-cold-run bug).

Code anchors:
- `_phase_h_eligible_pypi_names` [SRC:CFA:L4174]; 3-condition eligibility documented L4177–4189; NULL-safe `pypi_last_serial IS NOT pypi_version_serial_at_fetch` L4223–4231 (rationale L4213–4222).
- `pypi_version_serial_at_fetch` column ("v21: serial-gate") L234; v21 ALTER L1034–1036; stamped on fetch L4293/L4321/L4476.
- pypi-only exclusion MECHANISM: the SQL reads `FROM v_actionable_packages WHERE pypi_name IS NOT NULL` L4224–4225; pypi-only rows were moved to `pypi_universe` by the v20 migration (comment L355–357). The phrase "never re-include pypi-only denominators" is the spec's wording, not a code literal.
- Stats split `_phase_h_eligibility_stats` L4135 (branch SQL L4159/L4163).

## Phase B.5 attribution

Contract (spec:153–157): `_pick_feedstock` umbrella-vs-dedicated semantics
(`dbt-bigquery` → the `dbt-bigquery` feedstock, not `dbt`) — every maintainer-scoped
CLI depends on them; the node port must preserve them (Story B1).

Code anchors: `def _pick_feedstock` [SRC:CFA:L1572]; logic L1586–1590 (empty → None;
`len>1 and pkg_name in feedstocks` → `pkg_name`; else `feedstocks[0]`); docstring
L1573–1584; call site L1632 (comment L1630–1631).

## Mapping: g10_spelling no-clobber

Contract (spec:209–216, 376–378, 388–390): the `g10_spelling` provenance tier +
no-clobber rule must survive any mapping re-implementation; `mapping-gap` is the
seed-gaps pipeline's sole write-back exception.

Code anchors (`MG` = mapping_gap.py):
- `WRITEBACK_SQL` [SRC:MG:L76–82]: writes `packages.pypi_name`, `match_source='g10_spelling'`, `match_confidence`; no-clobber predicate `WHERE conda_name = ? AND (pypi_name IS NULL OR pypi_name = '') AND match_source NOT IN ('parselmouth', 'recipe_source_url')` L79–81.
- DRY-RUN default: writes only under `--write` (flag L588–589) via `write_recoveries` L360–376, `COMMIT_EVERY = 500` L84; dry-run opens DB read-only L605–609.
- Guards beyond the SQL: collision skip L317–324 (claimed-index L257–263, intra-run claim L341); ambiguous → no write L307–312; corroborator-disagrees → triage L299–304; non-bare transform without `verified` corroboration → `uncorroborated`, not written L326–339.
- Confidence tiers: `verified` vs `likely` L315 (policy L23–28); transforms `bare` / `strip-py` / `strip-python` / `strip-python-prefix` L227–237.

## KEV overlay + CVSS coercion

Contract (spec:217–223): KEV-affecting-current must match Phase G's
`vuln_kev_affecting_current`; overlays applied at build time over the fetcher tables.

Code anchors: `_load_kev_cves` [SRC:CFA:L3655] (graceful empty set L3658–3663);
overlay in Phase G L3854 (comment L3849–3853) and G' L6886.
`_coerce_cvss_score` — **defined in `detail_cf_atlas.py:295`** (the v8.76.1 fix), a
file OUTSIDE this skill's include set; Phase G reuses detail_cf_atlas via
`from detail_cf_atlas import fetch_vdb_data` [SRC:CFA:L3829] (comment L3826–3827).
The symbol location is recorded here as a boundary pointer; its internals are not
modeled — answer "not modeled (see detail_cf_atlas.py:295)" for detail questions.

## EPSS 0-100 normalization

Contract (spec:279–280): EPSS percentiles stored normalized 0–100.

Code anchors: normalization happens AT STORE TIME in `epss_fetcher.py` (`upsert_epss_rows`) —
`_normalize_percentile(raw) -> raw * 100.0` [SRC:epss_fetcher.py:L60–62], applied
L141; `epss_score` itself stored raw 0.0–1.0 L140 (docstring L28–29).
`conda_forge_atlas.py` only loads the already-normalized values:
`_load_epss_scores` docstring [SRC:CFA:L3684–3685], load L3692–3697. Aggregation
`_aggregate_v8_6_0_overlays` L3722 (max-EPSS + None-not-0.0 rules L3733–3735),
consumed by G (L3919, write L3929–3930) and G' (L6933; 2-scalar-column note L6936–6937).
CWE categories are loaded by `_load_cwe_categories` [SRC:CFA:L3700] from the
`cwe_categories` table (written by `cwe_catalog_fetcher.py`'s `upsert_cwe_rows`).

## purl / cfe namespace

Contract (spec:279–286 vicinity; SKILL.md v8.68.0/G98): conda purl carries
`?channel=conda-forge`; `cfe:` CycloneDX property namespace.

Code anchor: **NOT constructed in conda_forge_atlas.py** — zero literal matches for
`pkg:conda` / `cfe:` / `?channel=conda-forge` in the file. Phase G delegates purl
derivation to `detail_cf_atlas.fetch_vdb_data` [SRC:CFA:L3826–3829]; the export /
recommend modules own the `cfe:*` properties. Those modules are outside this skill's
include set — answer "not modeled" for their internals; the contract text itself is
bound by spec + CFE SKILL.md G98.

## View discipline

Contract (spec:133–138, 281–283): `v_current_version_vulns` is the ONLY
query-time-correct vuln source (the `packages.vuln_*` rollup is report-only);
`v_pypi_intelligence_valid` consumers must read the view; every raw `packages` query
passes the `v_actionable_packages` scope meta-test (view or `# scope:` justification).

Code anchors: `v_current_version_vulns` [SRC:CFA:L744] with the rule stated verbatim
in comments L732–743 (rollup kept for backward-compat, synced by
`_phase_g_sync_current_rollup` L6990, COALESCE-to-existing L7029–7030);
`v_actionable_packages` L376 (triplet L379–381, meta-test comment L366–375);
`v_pypi_intelligence_valid` L615 (rule L610–614).

## Single-write-path (add-handoff)

Contract (spec:201–203): `phase_r_upsert_one` / `apply_readiness_scores` are shared by
Phase R/S AND the S6 `add-handoff` CLI — the single-write-path property to preserve.

Code anchors: `phase_r_upsert_one` [SRC:CFA:L8198] ("the S6 add-handoff bounded
single-package enrichment both call this" L8208); `_phase_r_fetch_one` L8146 (worker
for both, L8148); `apply_readiness_scores` L8484 (add-handoff re-scoring L8489).

## Post-v25 schema shape

Contract (spec:283–286): the port lands at the post-v25 shape — cancelled
hardening/EPSS-overlay tables (`package_hardening`, `vuln_total_active`, …) were
provisioned then dropped and must not be resurrected.

Code anchors: drop comments [SRC:CFA:L220–221] (packages), L409–410
(package_version_vulns), L725–730 (`package_hardening` dropped — Wave C blint
cancelled); v24→v25 migration block L920 with `DROP COLUMN vuln_total_active`
L940–941/L948–949 and `DROP TABLE IF EXISTS package_hardening` L951–956;
v25→v26 `pypi_downloads_daily` L1069. `SCHEMA_VERSION = 29` L139;
`init_schema` (the single migrator) L817.

## Code-vs-spec divergences

Two places where the CODE (authoritative at commit b18cbb5) diverges from spec/story prose:

- **D1 — `_PARTITIONDATE`:** spec:253–261 says Phase P queries use "`_PARTITIONDATE`
  literal date bounds". The code explicitly REJECTS `_PARTITIONDATE` — the table is
  column-partitioned on `timestamp` and `_PARTITIONDATE` raises
  `Unrecognized name: _PARTITIONDATE` (verified live 2026-06-12) [SRC:CFA:L7690–7697];
  the correct form is literal `TIMESTAMP` bounds on `timestamp` [SRC:CFA:L7704–7705].
  Ports must follow the code, not the spec prose.
- **D2 — "AD-10":** not a spec term (zero matches). It is the architecture SPINE's
  label for the spec:250–286 contract list. Cite spec lines, not "AD-10", when
  answering from the spec.
