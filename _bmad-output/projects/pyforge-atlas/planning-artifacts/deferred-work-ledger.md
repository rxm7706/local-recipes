---
doc_type: deferred-work-ledger
project: pyforge-atlas
date: 2026-07-29
status: restored
entries: 55
---

# pyforge-atlas — deferred-work ledger (RESTORED, tracked)

**All 52 real deferrals recorded during the Kedro migration, with full bodies — the
ledger is complete.** The run log's index of "54" double-counted two aliases; see
§ Provenance.

The frontmatter `entries` count is the number of `## DW-` headings in this file and so
runs ahead of that 52 as post-restore work lands: **55** today = the 52 restored + `DW-I4-1`
(promoted 2026-07-29 out of the gitignored Tier-3 ledger) + `DW-AD23-1` and `DW-AD23-2`
(Story 10.6, same date — the first *defining* an id that eight artifacts had been citing
with no entry behind it).

## Why this file exists

The live ledger, `implementation-artifacts/deferred-work.md`, is **truncated to 9
entries** — it stops dead after `DW-B2-5`, collateral of the 2026-07-19 copy
failure — and that directory is **gitignored**, so it carries no durable copy.

It was briefly believed the other 45 were lost. **They were not.** They survive
with full bodies in `../spec-archive/ATLAS-BMAD-SPECS-CONSOLIDATED.md`, which is
git-tracked. This file consolidates both sources into one durable ledger in
Tier-2 `planning-artifacts/`, where it cannot be lost to a Tier-3 accident again.

## Provenance

- 43 entries recovered from `../spec-archive/ATLAS-BMAD-SPECS-CONSOLIDATED.md`
- 9 entries from the surviving `implementation-artifacts/deferred-work.md`
  (where both had an entry, the longer body won)
- **0 lost.** `DW-A2-P4` and `DW-D2` were previously recorded here as "the only
  genuine loss." **That was wrong, and is corrected as of 2026-07-27: both are
  aliases the run log's index counted a second time, and both bodies are present
  in this ledger under their carried-forward IDs.**
  - **`DW-A2-P4`** — the A2 review-pass P4 finding (dynamic per-host JFrog
    credential attachment). It was *assigned to B5* and carried forward under a new
    ID; its body is **`DW-B5-3`**, which opens with the alias in its own title
    ("DW-A2-P4 JFrog dynamic per-host credential attachment …"). Never a separate
    deferral.
  - **`DW-D2`** — shorthand for **`DW-D2-2`** (shell pages awaiting composed-store
    materialization), used as the in-code banner at
    `src/pyforge/atlas/dashboard/data.py:126` — "BSL-wired SHELL pages (composed
    store not yet materialized — DW-D2)". The index read that banner as a distinct
    entry alongside `DW-D2-1/2/3`.

  The real count is **52**, and 52 is what this file holds. Nothing from the
  migration's deferred work is missing.

Six of these are also re-stated as contract-level capabilities **DC-1…DC-6** in
the PRD § 6.4, because they outlived the migration: `DW-C1-1`/`DW-G3`/`DW-H4`
(live daemon), `DW-H1` (MinIO/PostgreSQL), `DW-H2` (agno synthesis + `vss`),
`DW-H3` (live Wagtail).

---

## DW-A1-5 — local-recipes doc re-sync + drift baseline re-stamp (surface-changed)

The A1 env addition flipped `bmad-drift-check` to `1 currency: [surface-changed] pixi_envs 11 -> 12`.
Per CLAUDE.md sync loop / SYNC-RUNBOOK: run the local-recipes reconciler pass
(bmad-document-project et al. for the count-bearing artifacts) then
`pixi run -e local-recipes bmad-drift-check -- --write-baseline`.
Non-blocking (integrity clean); owed before the next local-recipes doc-sync PR.

  status: open
## DW-B1-1 — parity-diff harness under-checks (HIGH, B4 must resolve before it trusts parity)

Independent B1 follow-up review (2026-07-17) found two harness weaknesses that manufacture false confidence:
1. Fixtures are HAND-AUTHORED "legacy-shaped seeds", not captured from a real legacy run — so the suite proves port==implementer-belief, not port==legacy. B4 MUST recapture fixtures from an actual legacy orchestrator run before consuming parity as the retirement gate (AD-19).
2. harness.py frame-diff under-checks: (a) column set derived from EXPECTED only → a node growing a spurious column passes; (b) check_dtype=False → int64-vs-float64 passes. Tighten to column-set equality + dtype where JSON round-trip allows.
Owner: B4 (parity gate). The must-fix `downloads_source='merged'` bug this review found was itself endorsed by an unfixed fixture — proof the harness needs recapture.

  status: open
## DW-B1-2 — RateLimitedScheduler not yet wired to the fetch path (MEDIUM, B2/live-fetch)

`_RequestParameterizedAPIDataset.load()` calls `self._inner.load()` but never `self.scheduler.acquire()` — the token bucket is real but enforced on nothing in B1 (fan-out is documented-deferred). Wire `acquire()` into the live request path when B2/live fetch lands. Also document the scheduler's fake-clock coupling (a frozen clock + no-op sleep makes acquire() infinite-spin) so a future fixture doesn't hang.

  status: open
## DW-B1-3 — enumerate_conda_packages tie-break + B.5 inactive placeholder rows (LOW/MEDIUM, B4 parity)

(a) enumerate_conda_packages uses non-stable sort before groupby-last → arbitrary winner on duplicate-timestamp builds (latent parity risk vs legacy's defined tie-break). (b) Legacy phase_b5 also inserts inactive placeholder rows (relationship='conda_only', latest_status='inactive') for feedstock-outputs entries absent from repodata; the port's attribute_feedstocks omits them — changes downstream v_actionable population. Both are B4 parity-reconcile items.

  status: open
## DW-B2-1 — DAG-level persistence of operator notes edited on the SCORED output (MEDIUM, persistence boundary)

- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/b2-port-the-pypi-and-vulnerability-pipelines.md`
  summary: AC-5 notes-survive is satisfied at the enriched→scored carry (Phase S reads enriched) + the `apply_readiness_scores(prior_scored=…)` helper path (the add-handoff single-package re-score); a FULL-DAG merge of operator notes edited DIRECTLY on the persisted `pypi_intelligence_scored` output is not wired.
  evidence: `score_pypi_readiness` passes `prior_scored=None` and `pipeline.py` wires only `pypi_intelligence_enriched`; a notes-merging persistence boundary (custom dataset OR a prior-read alias) would satisfy the scored-output-edit case, but that exceeds B2's bounded catalog scope (Task 7: only the 2 FLIPs + conftest edit). Owner: the persistence-boundary story (B4/B5). Adversarial-review (Blind Hunter) 2026-07-17.

  status: open
## DW-B2-2 — coerce_cvss_score not on the B2 node data path until B5 wires the vdb boundary (LOW, B5)

- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/b2-port-the-pypi-and-vulnerability-pipelines.md`
  summary: `coerce_cvss_score` (AC-3(b)) is authored + boundary-tested in `datasets/vdb_boundary.py` but not invoked on the B2 node path — the vdb parse+coercion boundary is B5's; `summarize_vdb_vulns`/`per_version_vulns` run `pd.to_numeric(errors="coerce")`, so a raw pydantic `ScoreType` reaching a node before B5 would coerce to NaN (→ None) rather than unwrap.
  evidence: G-3 scoping (B2 consumes the interim vdb PATH; B5 lands the read-only VDB dataset class that parses+coerces). Acceptable under scope; note for B5 to wire `coerce_cvss_score` at its dataset boundary. Adversarial-review (Blind Hunter) 2026-07-17.

  status: open
## DW-B2-3 — vuln_kev_affecting_current in the report-only rollup is package-wide, not version-scoped (LOW, report-only)

- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/b2-port-the-pypi-and-vulnerability-pipelines.md`
  summary: `summarize_vdb_vulns.vuln_kev_affecting_current` sums KEV over ALL vdb rows for a package; the name implies current-version scoping.
  evidence: the rollup is REPORT-ONLY (AC-2) and documented in code as such; the version-accurate KEV-affecting-current is `v_current_version_vulns` (backed by `per_version_vulns`). Low impact; verify against legacy CFA:3854 scoping at B4 parity. Adversarial-review (Blind Hunter) 2026-07-17.

  status: open
## DW-B2-4 — Phase P cost-gate class not yet wired into the catalog (B3/B4 pre-flight, MEDIUM)

Independent B2 follow-up review (2026-07-17): `BigQueryDownloadsDataset` (the two-layer
cost gate) is implemented + tested but the catalog entry `pypi_bigquery_downloads_raw`
(conf/base/catalog.yml) still resolves to the interim `api.APIDataset`
(${BIGQUERY_BASE_URL}/projects, bigquery_adc creds) — the gate class appears only in a
comment. So the AD-6 no-op + cost cap protect the CLASS, not a default `kedro run`:
a live Phase P pointed at the interim APIDataset would attempt a network fetch with no
cost gate. This is a DOCUMENTED deferral (credentialed Phase-P materialization is
attended B3/B4, mirroring B1's fan-out deferral) — NOT a B2 regression. **B3/B4 MUST
route pypi_bigquery_downloads_raw to BigQueryDownloadsDataset before any credentialed
Phase-P run** so the gate actually guards the live query. Owner: B3 (MCP/credentialed
surface) or B4 (parity).

  status: open
## DW-B2-5 — pypi_intelligence pipeline not end-to-end runnable unattended (by design, note-only)

`pypi_json_raw` → `PyPIJsonRequestDataset.load()` raises (directs to load_many, the
attended per-request fan-out — mirrors B1). A default SequentialRunner cannot execute
pypi_intelligence end-to-end; test_dag_resolves checks topology only. Intended for this
migration phase; the concrete DAG-load fan-out is a dataset-owned + attended concern.
No action needed — recorded so nobody expects an unattended full run to work yet.

  status: open
## DW-B4-1 — the credentialed full parity run (ATTENDED, AD-19) — DEFERRED to the wave-boundary event

B4 built the credentialed-parity comparator (`tests/parity/parity_runner.py`), but the actual
run against a REAL operator `cf_atlas.db` cannot happen in-loop (no credentialed DB; AD-11
credentialed-runs-attended-only). At the event: supply the real `cf_atlas.db` + a
`kedro_frame_provider` that composes each legacy-surface view from its Parquet datasets
(the per-view composition — join keys + the actionable filter — is finalized against the real
schema then), run `run_parity(legacy_db=..., kedro_frame_provider=...)`, and record the
resulting `ParityEvidenceRecord`s per `PARITY_EVIDENCE_TEMPLATE.md`. Owner: B4 attended event.

  status: open
## DW-B4-2 — human sign-off + marking legacy retirement (FR-4) — DEFERRED (human act)

`may_retire_legacy` returns `allowed=False` in-loop (correct — no credentialed, signed
evidence). Only after DW-B4-1's evidence is recorded AND a human signs (`human_sign_off` set)
does the gate open. The actual `phase_state` removal / `bootstrap-data` retirement (FR-4) is a
separate attended action gated on `allowed=True`. Do NOT mark retirement until then.

  status: open
## DW-B4-3 — fixture recapture from a real legacy run (DW-B1-1 part a) — tool SHIPPED, recapture DEFERRED

`tests/parity/capture_fixtures.py` is the recapture tool. At the event, back a
`LegacyCaptureSource` with the credentialed `cf_atlas.db` and run `capture_legacy_fixtures`
to replace the B1/B2 shape-only seeds (stamped `credentialed-legacy-capture-<date>`). Until
then the seeds stay flagged `shape-only-seed-...` and a green `parity-diff` is NOT legacy parity.

  status: open
## DW-B4-4 — DW-B2-4 BigQuery-routing pre-flight before any credentialed Phase-P run — DEFERRED (carries DW-B2-4)

Route `pypi_bigquery_downloads_raw` → `BigQueryDownloadsDataset` (the two-layer cost gate)
BEFORE any credentialed Phase-P run at the event. B4 deliberately did NOT route it in-loop:
it would change `conf/base/catalog.yml` and risk the `kedro-catalog-check=38` invariant for a
gate that only bites a credentialed run B4 never performs in-container. Carries DW-B2-4 forward.

  status: open
## DW-B4-5 — parity-reconcile items surfaced at the credentialed run (carries DW-B1-3 / DW-B2-3) — DEFERRED

At the credentialed run, the drift report must reconcile the known legacy-vs-port deltas:
DW-B1-3 (`enumerate_conda_packages` duplicate-timestamp tie-break; Phase B.5 inactive
placeholder rows) and DW-B2-3 (`vuln_kev_affecting_current` package-wide vs version-scoped,
vs legacy CFA:3854), plus the Phase E ~44-feedstock maintainer-universe delta (PARITY_NOTES
"AC-5"). These need real data to reconcile; not doable in-loop.

  status: open
## DW-B4-6 — credentialed-mode read-path hardening (attended event) — DEFERRED

- source_spec: `b4-verify-dataset-parity-against-the-legacy-orchestrator.md`
  summary: `parity_runner.run_parity` CREDENTIALED mode does not yet harden the real-DB read path — a view missing from the legacy `cf_atlas.db`, a nonexistent `legacy_db` file, a URI-special-char path, or a `kedro_frame_provider` that raises/returns non-DataFrame currently propagate an uncaught error mid-run instead of a per-view "missing/errored" evidence record.
  evidence: Edge-case review (2026-07-17). The credentialed path is ATTENDED-only and exercised in-loop only via a synthetic on-disk/in-memory SQLite fixture + a synthetic provider (fixture mode is the shipped gate), so these are event-time robustness items, not in-loop correctness holes. Harden them alongside DW-B4-1 when the per-view Kedro composition is finalized against the real schema; wrap each per-view read in try/except emitting an errored `ParityEvidenceRecord` (material_drift=True) so one bad view doesn't abort the whole credentialed run.

  status: open
## DW-B5-1 — re-point name_resolver.py / recipe-generator.py at Phase C + verify the live authoring read (Q6) — DEFERRED (read-only .claude/**)

- source_spec: `b5-port-the-external-refresh-assets.md`
  summary: Q6 default = consolidate the pypi↔conda mapping on the migrated Phase C. B5 landed the flat-cache EXPORT shim (`export_pypi_conda_map` -> `MappingCacheDataset`, merge onto last-good, g10_spelling + no-clobber preserved WITHIN Phase C). The actual re-point of the authoring-time readers (`name_resolver.py` / `recipe-generator.py` / `mapping_gap.py`) to read Phase C directly + the live verification of whether the standalone flat file is still needed CANNOT be done in-loop (`.claude/skills/conda-forge-expert/scripts/**` is HARD read-only + is the recipe-authoring surface this migration does not touch, spec §12).
  evidence: the flat file is retained as the compatibility shim (byte-format `{pypi_name: conda_name}`); until DW-B5-1 proves the readers can drop it, the shim stays. `g10_spelling` provenance + no-clobber survive regardless (AD-10).

  status: open
## DW-B5-2 — C1 wires the Dagster Schedules AND the concrete refresher/fetcher INJECTION (+ store-format fidelity) — DEFERRED (attended/C1)

- source_spec: `b5-port-the-external-refresh-assets.md`
  summary: B5 ships the refresh assets + the DECLARATIVE cadence (`params:refresh_cadences`, == legacy TTLs, fixture-proved) + the retry/observability budget metadata; `dagster` is never imported (AD-1), so the `dagster-dryrun` gate runs once C1 exists. C1 must (a) emit the Dagster Schedules from `params:refresh_cadences`, AND (b) INJECT the concrete refreshers — the vuln-db-env `appthreat-vulnerability-db` build for the vdb, the osv.dev-bucket fetcher for the OSV store — as the Dagster resource. In-loop the refresher defaults to None (offline: a DUE refresh keeps last-good + marks stale; a fresh store is a no-op), mirroring B1/B2's deferred fetch. The injected refresher/fetcher is also responsible for writing the store in the exact format the EXTERNAL consumers read (the operator's appthreat vdb / cve_manager cve/ store) — the in-container `_write` is a lean normalized representation for the gate.
  evidence: catalog constructs `VDBStoreDataset`/`OSVOfflineStoreDataset` with only `filepath` (+`bucket_url`); no refresher kwarg is wired (by design — credentialed/live runs attended-only, AD-11/NFR-2). `save()` honors `RefreshRequest.force` + cadence; `_describe()` carries `retry_budget` + `required_resource` for C1 to consume.

  status: open
## DW-B5-3 — DW-A2-P4 JFrog dynamic per-host credential attachment for enterprise-mirrored refresh stores — DEFERRED (no live surface)

- source_spec: `b5-port-the-external-refresh-assets.md`
  summary: The A2 review-pass P4 assigned the dynamic per-host JFrog credential attachment (attach the jfrog key iff an entry's resolved hostname suffix-matches an Artifactory host) to B5 (external-refresh / enterprise store routing). B5 does NOT implement it: none of the three shipped stores routes to an Artifactory host (vdb = local path; OSV = public osv.dev GCS bucket; mapping = local Phase C export), so the mechanism has no live surface to attach to, and the static credential-scoping gate stays exact.
  evidence: `tests/catalog/test_credential_scoping.py` CREDENTIAL_ALLOWLIST unchanged; no new `credentials:` key added. Revisit when an enterprise-mirrored refresh store (e.g. an Artifactory-hosted vdb/OSV mirror) actually lands.

  status: open
## DW-B5-4 — wire the AD-13 staleness marker into the G/G' consumer read-path (degrade to indeterminate) — DEFERRED (consumer-side, B2 nodes)

- source_spec: `b5-port-the-external-refresh-assets.md`
  summary: B5's `VDBStoreDataset`/`OSVOfflineStoreDataset` SURFACE the AD-13 staleness marker (`is_stale()` / `staleness()`; an air-gapped/missing store returns last-good/empty + a machine-readable marker). But no CONSUMER reads it yet: `summarize_vdb_vulns` / `per_version_vulns` receive an empty frame indistinguishable from a genuinely vuln-free store, so an air-gapped run can produce an empty rollup that reads as a clean pass. AD-13's consumer contract ("degrade the affected axis to indeterminate, never a silent pass") needs the G/G' read-path (B2's nodes) to check the store's staleness and emit an indeterminate signal.
  evidence: Blind-Hunter finding (2026-07-18). B5 owns the refresh-asset staleness SURFACE (AC-5: marker stamped + surfaced, offline load returns last-good — proven by `tests/datasets/test_refresh_assets.py`); the consumer-side degrade-to-indeterminate is a follow-up on the B2 vulnerability nodes.

  status: open
## DW-B6-1 — spdx-schema-gap atlas-usage ranking needs `conda_license` (not yet produced by core) — DEFERRED

- source_spec: `b6-port-the-seed-gaps-pipeline.md`
  summary: `report_spdx_schema_gap` ranks its add-to-schema / non-standard tiers by how many actionable packages carry each `conda_license` (legacy `v_actionable_packages.conda_license`). The migrated `core_packages_enumerated` carries `conda_name/latest_version/subdirs` but NOT `conda_license` (a B1-scope column not yet ported), so those two tiers are empty in-loop. The node reads `core_packages_enumerated` and extracts `conda_license` gracefully (missing column -> empty atlas usage); the atlas-INDEPENDENT `upstream-drift` tier (upstream SPDX IDs absent from the vendored enum) needs no atlas data and keeps the report non-empty (proven by `test_spdx_drift_nonempty_without_conda_license`).
  evidence: `grep -rn conda_license src/` returns 0 hits in the kedro package; `core.nodes.enumerate_conda_packages` output columns are `conda_name/latest_version/subdirs` only. Re-point the atlas-usage read to a full actionable-packages-with-license dataset when B1/parity produces `conda_license`.

  status: open
## DW-B6-2 — cwe-seed-gap `_other_impact` headline needs the per-package CWE-rollup dataset — DEFERRED

- source_spec: `b6-port-the-seed-gaps-pipeline.md`
  summary: The legacy `cwe-seed-gap` also emits an "Other-bucket affects N packages" headline read from `packages.vuln_cwe_categories_json` (the per-package CWE-categories rollup blob). No migrated kedro dataset carries that column yet (the vulnerability pipeline's per-package CWE rollup), so `report_cwe_seed_gap` ships the proposal rows only (the load-bearing output) and omits the impact headline. Additive summary stat, not a correctness hole — add it when a per-package CWE-categories dataset lands.
  evidence: `vulnerability_cwe_categories` (the migrated CWE catalog table) carries `cwe_id/cwe_name/category` — the catalog rows, not the per-package rollup. The proposals (which CWEs to seed) are fully computed; only the universe-cost headline is deferred.

  status: open
## DW-B7-1 — the UPDATE-FEEDSTOCK bucket needs an upstream-of-record column (not yet on core_packages_enumerated) — DEFERRED

- source_spec: `b7-extend-the-universal-sbom-intake.md`
  summary: The six-bucket matcher's UPDATE-FEEDSTOCK verdict (conda-forge behind upstream) needs the upstream-of-record version to compare against cf `latest_version`. The migrated `core_packages_enumerated` carries `conda_name/latest_version/subdirs` but NOT `upstream_version` (a B1-scope column not yet ported, sibling of DW-B6-1). `_build_indexes`/`classify_bucket` read `upstream_version` gracefully (`.get`, missing column -> None -> UPDATE-FEEDSTOCK cannot fire from live data); the AC-4 fixture supplies the column so all six buckets are proven. Re-point to a full actionable-packages-with-upstream dataset when B1/parity produces it.
  evidence: `test_all_six_buckets_reproduced_on_a_fixture_inventory` supplies `upstream_version` in its fixture core frame; the matcher's `_build_indexes` guards the column with `if "upstream_version" in core_packages_enumerated.columns`.

  status: open
## DW-B7-2 — the real transitive resolver (pip --dry-run / py-rattler solve) is injected, not shipped in-package — DEFERRED

- source_spec: `b7-extend-the-universal-sbom-intake.md`
  summary: `TransitiveResolverDataset` owns the resolver IO via an INJECTED `resolver` callable (default None == offline -> `unresolved` marker, AD-13). The concrete resolver needs `subprocess` (pip `--dry-run --report`) or py-rattler, both of which cannot live in the atlas package (`subprocess` is on the A2 no-inline-IO denylist, AST-scanned over the whole package). B7 ships the offline-safe `unresolved` path + the injected-callable seam + a stub-resolver fixture proving the resolved path (depth/fan-out recorded). The concrete resolver + its wiring land with the orchestration wave (C1) / a follow-up — same pattern as the B5 refresher-injection deferral (DW-B5-2).
  evidence: `tests/datasets/test_sbom_intake.py::test_resolver_resolved_records_depth_and_fanout` uses a stub resolver; `test_resolver_offline_returns_unresolved_marker` + `test_resolver_exception_degrades_to_unresolved_never_crashes` prove the offline/never-crash contract; `tests/catalog/test_no_inline_io.py` passes (no `subprocess` import anywhere in the package). Review note (Blind LOW-5): AC-1's "never hang" is guaranteed for the OFFLINE (default None) + exception paths B7 ships; a WEDGED injected resolver has no wall-clock guard — the injected callable's CONTRACT is that it must self-bound (a wall-clock guard lands with the concrete resolver + its orchestration wiring).

  status: open
## DW-B7-3 — universe-BOM standalone pypi-only completeness (not a scope hole; a widening) — DEFERRED

- source_spec: `b7-extend-the-universal-sbom-intake.md`
  summary: RESOLVED-IN-B7 (Blind HIGH-1): the ADD path now reads the FULL PyPI universe (`pypi_universe`, produced by `pypi_intelligence.enumerate_pypi_universe`, column `pypi_name`) as the authoritative membership signal — VERBATIM legacy `universe_lookup` — so a pypi name on PyPI-but-not-conda-forge correctly buckets ADD (was silently UNKNOWN when membership derived only from the conda mapping). The remaining widening: `build_universe_sbom` emits only conda components + `cfe:pypi_name` on mapped rows (not standalone `pkg:pypi/<name>` universe members), so the universe-BOM ARTIFACT is conda-centric; membership for matching comes from `pypi_universe` directly (correct), and the standalone-pypi-only universe-BOM completeness is a later artifact-shape widening, not a matcher correctness hole.
  evidence: `test_add_membership_comes_from_the_full_pypi_universe_not_the_mapping` (ADD via pypi_universe, unmatched-to-mapping) + `test_unmatched_pypi_not_in_universe_is_unknown_never_add`; `_build_indexes` reads `pypi_universe["pypi_name"]`. The G10 bare-match guard (Blind MEDIUM-3) is now PORTED using `pypi_conda_mapping` (`conda_to_pypifold`) — `test_g10_bare_match_guard_rejects_a_name_coincidence`.

  status: open
## DW-B8-1 — the concrete live Basilisk fetcher (querybatch / detail GET) is injected, not shipped in-package — DEFERRED

- source_spec: `b8-basilisk-conda-native-vulnerability-ingestion.md`
  summary: `BasiliskBatchDataset` / `BasiliskDetailDataset` own the fetch IO via an INJECTED `fetcher` (default None == OFFLINE -> keep last-good + mark stale, AD-13). The concrete Basilisk client needs an HTTP client — an A2 no-inline-IO-denylisted import that never lives in the atlas package. B8 ships the offline-safe stale path + the injected-callable seam + a stub fetcher proving the ≤1,000-query chunking, the bounded rate-limit discipline (per-request `acquire()`, `parse_retry_after` + jitter, dedupe), and the resolved paths. The concrete fetcher + its Dagster wiring land at C1 / an attended run — same pattern as the B5 refresher-injection (DW-B5-2) and B7 resolver-injection (DW-B7-2) deferrals. Basilisk is PRE-ANNOUNCEMENT (no public docs/repo as of 2026-07-16; API live-validated 2026-07-15) — NO live Basilisk call in any test (AD-11).
  evidence: `tests/datasets/test_basilisk.py` drives every path against a STUB fetcher; `test_batch_offline_marks_stale_keeps_last_good` + `test_detail_offline_marks_stale` + `test_wired_fetcher_load_marks_stale_when_unpopulated` prove the offline/never-crash contract; `tests/catalog/test_no_inline_io.py` passes (no `subprocess`/HTTP import anywhere in the package incl. `datasets/basilisk.py`).

  status: open
## DW-B8-2 — the no-currency-conflation view's behind-upstream join is fixture-supplied — DEFERRED

- source_spec: `b8-basilisk-conda-native-vulnerability-ingestion.md`
  summary: `v_basilisk_advisories` (the AC-4 read-view transform) joins advisories x per-advisory `fix_available` x a behind-upstream frame supplying `conda_name` + `version_current`. The migrated `vcs_upstream_versions` (Phase K) carries upstream version, but the exact behind-upstream currency column/join re-points when the B-wave upstream-of-record data fully lands (sibling of DW-B7-1). The AC-4 fixture supplies the behind-upstream frame so the no-conflation guard is proven in-loop (version-currency + security-currency kept as distinct columns; neither derives the other).
  evidence: `test_current_package_still_surfaces_its_advisory` + `test_view_does_not_render_security_as_version_currency` supply `behind_upstream` with `version_current`; `v_basilisk_advisories` reads it with `{"conda_name","version_current"} <= set(bu.columns)` (graceful: absent -> None).

  status: open
## DW-B8-3 — the full 21,163-package Basilisk population run is credentialed/attended — DEFERRED

- source_spec: `b8-basilisk-conda-native-vulnerability-ingestion.md`
  summary: The full Python-population batch run is credentialed/attended (NFR-2/AD-11); in-loop the batch is driven by fixtures. Population source is `core_packages_enumerated` (`conda_name`/`latest_version` -> the conda PURL query keys); re-point to a dedicated full-python-population dataset if one lands. The empty-but-successful-fetch -> stale behavior (Blind Hunter MEDIUM, deferred) is inherited from the reused B5 `ExternalRefreshDataset` semantics (a store-level signal can't distinguish "zero advisories" from "unreachable") — re-evaluate if a fresh-empty distinction is needed at the attended run.
  evidence: `chunk_queries`/`query_population` prove the ≤1,000 chunking (2500 -> [1000,1000,500]; 1001 -> [1000,1]) against a stub; the credentialed fan-out is DATASET-owned via `query_population`, called by the attended/Dagster path (DW-B8-1).

  status: open
## DW-C1-1 — the live Dagster schedule bring-up (ATTENDED, Q2) — DEFERRED to the wave-boundary event

- source_spec: `c1-integrate-kedro-dagster-for-scheduling-execution.md`
  summary: C1 shipped the offline glue (`orchestration/definitions.py`) + the `dagster-dryrun` gate (definitions load, schedules enumerate, jobs resolve, per-op timeout tags, Phase-P admin-only) — all verified with NO live execution. The actual schedule BRING-UP is the attended Q2 boundary: standing up a Dagster daemon (`dagster dev -m pyforge.atlas.orchestration.definitions`), turning the schedules RUNNING (they ship with no `default_status=RUNNING`, so nothing auto-starts), and observing real retries/phase-state in the UI. Do NOT weaken the dryrun gate to unattended-execute (NFR-12).
  evidence: `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline; `tests/orchestration/test_definitions_dryrun.py` (19) + the AD-1 import-ban (`tests/catalog/test_no_inline_io.py`) are the loop-consumable gate. `defs = build_definitions()` builds under blocked sockets (no network IO at import).

  status: open
## DW-C1-2 — per-op runtime ENFORCEMENT + profile-config run-wiring are bring-up concerns (structural-only in C1)

- source_spec: `c1-integrate-kedro-dagster-for-scheduling-execution.md`
  summary: Two AC surfaces are STRUCTURAL in C1 and become operative only at the live bring-up (both reviewer-flagged, recorded not faked):
    (a) **Per-op timeout ENFORCEMENT.** Each op carries an independent `dagster/max_runtime` tag (the monolith is gone — no job/run-level timeout anywhere), but `dagster/max_runtime` is Dagster's run-monitoring tag, enforced by the DAEMON at bring-up. Today's operative isolation (a Phase-R overrun can't abort F/K/N) comes from JOB SEPARATION — Phase R rides only the weekly `bootstrap_data` job, F/K/N have their own scheduled jobs — not from the tag. Per-op runtime capping arrives with the daemon.
    (b) **Profile precedence run-wiring.** `resolve_profile_config` (maintainer/admin/consumer, precedence: run-config > env > profile default) is a verified pure function but is NOT yet attached to any job as `RunConfig`/`default_config`; a real run does not yet consume it. Wiring the resolved profile config into the job run-config is a bring-up step.
    Also deferred: the kedro-dagster `before/after_pipeline_run` hook ops exist only on the translated base graph and are filtered out of the derived/scheduled jobs — confirm at bring-up whether per-run session hooks are needed on the scheduled jobs or are intentionally base-only.
  evidence: `test_timeouts_are_not_a_single_monolith` + `test_every_op_has_its_own_timeout` prove the structural side; `resolve_profile_config` is exercised only by the gate, and `build_definitions` does not call it (structural-scope, by design for the attended C1 boundary).

  status: open
## DW-D2-1 — the full 28-page Vizro inventory is CIS-two-spine deferred

- source_spec: `d2-build-the-vizro-dashboard-port-the-28-clis.md`
  summary: D2 shipped the buildable core — the BSL-driven Vizro app framework, the AC's live-confirmed-first pages (behind-upstream / query-atlas / whodepends / feedstock-health / my-feedstocks / detail-cf-atlas / staleness-report), and the fully-specified factory-status page — all routed through the D1 semantic models (AD-8). The FULL 28-page inventory + each page's detailed design is blocked on the **CIS two-spine specs** (`DESIGN.md` + `EXPERIENCE.md`, § 84) which are NOT yet produced (Spine-Deferred). Producing them (the CIS Carson/Maya planning pass) is the precondition; the remaining pages port against them. Do NOT expand the page set past the live-confirmed core without the CIS spine.
  evidence: D2 AC "Given the D1 BSL models AND the CIS two-spine design specs"; verify-gate note "D2 page inventory detail resolves in the CIS specs (Spine Deferred)". The dashboard-dryrun gate asserts the shipped pages build offline + are BSL-driven; it does not assert 28-page completeness.

  status: open
## DW-D2-2 — shell pages await their composed-store materialization (staleness / query-atlas / detail-cf-atlas / behind-upstream / whodepends)

- source_spec: `d2-build-the-vizro-dashboard-port-the-28-clis.md`
  summary: Several core pages are BSL-WIRED SHELLS: the loader queries the correct D1 semantic model, but the composed Parquet store that model binds to (e.g. a `semantic_packages` primary output joining the per-metric columns) is not materialized as a single dataset yet, so the page renders empty against the live catalog until that store lands. The loaders are honest (empty BSL query, never fabricated rows). Materializing the composed store (a small kedro node emitting the semantic-input Parquet) wires the live data. Pages backed by an existing single dataset (feedstock-health → core_feedstock_health; my-feedstocks → vcs_package_maintainers) are already live.
  evidence: `dashboard/data.py` shell loaders are grouped under a "BSL-wired SHELL pages (composed store not yet materialized — DW-D2)" banner; each returns an empty typed frame via `_bsl_query_or_empty` when the store is absent.

  status: open
## DW-D2-3 — DEV-AUTO visual verification of the rendered UI (headless container cannot)

- source_spec: `d2-build-the-vizro-dashboard-port-the-28-clis.md`
  summary: D2 is a DEV-AUTO (visual-judgment) story. The dashboard-dryrun gate verifies the Dashboard OBJECT builds offline + structural agent-legibility (stable page id/title, deterministic layout, semantic factory-status table, AD-17 stamp), but the in-container run cannot VISUALLY verify the rendered browser UI (no display, no `app.run()`). The human/visual pass — actual `pixi run dashboard` render, the §2.1 semantic-HTML/ARIA browser-agent navigation check — is the deferred DEV-AUTO verification.
  evidence: `dashboard-dryrun` builds the object + asserts structure only; it never launches the server (offline gate, mirrors C1 dagster-dryrun / C2 viz-loadable).

  status: open
## DW-D3-1 — the live Vizro-AI NL→chart backend bring-up (ATTENDED, Q3) — DEFERRED to the wave-boundary event

- source_spec: `d3-vizro-ai-nl-interface-query-vizro-ai-mcp-tool.md`
  summary: D3 shipped the buildable-now half — the thin `query_vizro_ai` MCP tool (AD-7), the `pyforge.atlas.nl` seam (backend resolver + BSL-grounded context), its registration (tools.py + server.py + audit.NL_INTERFACE_TOOLS + the mcp package export), and the `vizro-ai-dryrun` gate — all offline with NO live LLM call. The actual live Vizro-AI NL→chart invocation is the **attended Q3 backend event**: it happens only once a model backend is configured through repo model-backend config (`OPENAI_BASE_URL`+`OPENAI_API_KEY` or `ANTHROPIC_BASE_URL`+`ANTHROPIC_API_KEY` — Q3 §11 default, BINDING; never a hardcoded public endpoint). In-container with no backend configured the tool returns a structured `backend-not-configured` advisory; with a backend configured it returns a `backend-configured-live-call-deferred` receipt naming the repo-config endpoint but STILL makes no live call. At the event: configure the backend env, instantiate the Vizro-AI NL agent against the resolved backend + the BSL-grounded context (`build_bsl_context`), invoke NL→chart, and replace the deferred receipt's `chart: None` with the generated chart/insight. The `vizro_ai` top-level `VizroAI` entrypoint is absent in the pinned 0.4.1 (only `vizro_ai.agents.chart_agent`, a pydantic-ai Agent needing a backend), so the live-entrypoint wiring is finalized at the event; the import stays lazy+guarded in `nl/query.py` (AD-1: only `nl/` imports `vizro_ai`). Do NOT weaken the `vizro-ai-dryrun` gate to unattended-execute, and do NOT bake a public endpoint in (NFR-12 / Q3 §11).
  evidence: `tests/nl/test_query_vizro_ai_dryrun.py` proves the tool is registered + callable, the unconfigured path returns the advisory with no network (sockets blocked), a configured `OPENAI_BASE_URL` is the endpoint used, no host-bearing URL literal exists in the resolver (Q3 §11), the tool body is AD-7-thin, and the NL context is BSL-grounded (AD-8). `nl/query.py::query_vizro_ai` returns `chart=None` in both paths; `vizro_ai_available()` is a guarded probe. Mirrors the C1 dagster-schedule bring-up (DW-C1-1) and the B5/B7/B8 injected-fetcher deferrals.

  status: open
## DW-D3-2 — the dashboard NL query field (the D2 Vizro dashboard's NL entry point) — DEFERRED (carries DW-D3-1 + the CIS spine)

- source_spec: `d3-vizro-ai-nl-interface-query-vizro-ai-mcp-tool.md`
  summary: D3 delivers the NL interface as an MCP tool (`query_vizro_ai`) — the agent-facing surface. The other NL surface, a natural-language query FIELD embedded in the D2 Vizro dashboard (a user types a question on a page and gets a generated chart), is DEFERRED: it depends on the live Vizro-AI backend (DW-D3-1) AND on the CIS two-spine design specs that gate the dashboard's page design (DW-D2-1). When both land, add the NL field as a dashboard component that calls the same `pyforge.atlas.nl` seam (so the MCP tool and the dashboard field share one backend-routing + BSL-grounding path, never a second execution plane — AD-23). Until then the dashboard ships without an NL field.
  evidence: D3's shipped surface is the MCP tool only (`server.py` `query_vizro_ai` @mcp.tool + `tools.query_vizro_ai`); `dashboard/app.py` is unchanged by D3 (no NL component added). The shared seam (`pyforge.atlas.nl`) is deliberately UI-agnostic so the dashboard field can reuse it at the event.

  status: open
## DW-E1-1 — the live cross-process A2A wire (a running fasta2a server / broker) — DEFERRED

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story E1, FR-11)
  summary: E1 shipped the load-bearing, buildable-now half of the A2A surface — the `a2a/` module as the SINGLE payload schema source (AD-20: one discriminated family for both insights and alerts, no second dialect), the AD-17-stamped builders (`build_insight_payload` referencing a BSL metric by `semantic.METRIC_PROVENANCE` id per AD-8 / `build_alert_payload`), the exact payload↔`a2a.types.Message` serialize/deserialize round-trip (canonical JSON inside a real a2a-sdk DataPart — protobuf Struct would floatify ints, so JSON preserves the payload EXACTLY), and the resolved transport: **direct in-process message-passing** (`hand_off` → `AuthoringInbox`) proving the cf_atlas-analytical → conda-forge-expert-authoring direction offline + deterministically. The genuine cross-process wire — standing up a live `fasta2a` (FastAPI-style A2A) server or an A2A broker between two OS processes so the two agents exchange messages over a bound socket — is DEFERRED: it needs a bound socket + a second process, neither of which comes up offline in-container, and faking a broker would be dishonest (mirrors the DW-C1-1 live-Dagster-schedule and DW-D3-1 live-LLM-backend attended bring-ups). Because the message ENVELOPE is already the real a2a-sdk `Message`, the follow-up is a delivery-substrate swap (`inbox.receive(msg)` → an HTTP/broker `send`), not a schema change. Do NOT weaken the offline round-trip/hand-off gate to unattended-execute a live server.
  evidence: `tests/a2a_surface/test_a2a_payloads.py` drives the whole surface against the in-process hand-off — `test_insight_round_trip_is_exact` / `test_alert_round_trip_is_exact` (exact incl. AD-17 stamp, no int→float drift, unicode), `test_analytical_to_authoring_hand_off` (ordered exact delivery to the authoring inbox), the AD-20 single-schema-source scans (`test_ad20_no_competing_payload_schema_outside_a2a`, `test_ad20_only_a2a_schema_subclasses_the_base`) + `tests/catalog/test_no_inline_io.py::test_a2a_sdk_only_in_a2a_layer` (only `a2a/` imports the a2a SDK), AD-17 (`test_ad17_stamp_required_and_injected`, `test_ad17_stamp_on_the_wire_envelope`), AD-8 (`test_ad8_insight_metric_must_be_a_bsl_identifier`), and the degrade-not-crash edges (unknown kind / malformed JSON / non-JSON-native field / missing payload part). No socket is bound and no second process is spawned in any test (AD-11 / offline).

  status: open
## DW-E2-1 — the live OTel collector + OpenLineage backend wiring (env-driven) — DEFERRED

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story E2, FR-12)
  summary: E2 shipped the load-bearing, buildable-now half of the observability surface — the `observability.py` module as the SINGLE instrumentation seam (AD-6/AD-23: `openlineage`/`opentelemetry` confined there by `test_observability_libs_only_in_observability`), a Kedro Hooks impl (`AtlasObservabilityHooks`) declared ONCE in `settings.HOOKS` so EVERY entry point inherits it (a `kedro run` natively, a Dagster run via C1's `KedroProjectTranslator` → `KedroSession.run`), emitting per-node OpenLineage RunEvents (START/COMPLETE/FAIL) with input/output dataset lineage + the rows/latency/cache-hit metric facets (`OutputStatisticsOutputDatasetFacet.rowCount` + the custom `AtlasNodeMetricsRunFacet`), and an OTel span tree (pipeline → node → per-dataset read/write "API-call" spans). Nodes stay pure DataFrame→DataFrame (AD-2/AD-6) — all instrumentation is in the hook layer. Both backends are INJECTABLE and default to no-op/offline: `tracer_provider=None` → a local `TracerProvider` with no exporter (spans dropped, no network, never set globally); `openlineage_client=None` → OL emission skipped. The ACTUAL live wiring — a real OTLP endpoint (`OTEL_EXPORTER_OTLP_ENDPOINT` + a `BatchSpanProcessor`/`OTLPSpanExporter`) and a real OpenLineage backend URL/transport (`OPENLINEAGE_URL` → an `HttpTransport`) resolved from env at run bring-up — is DEFERRED: no collector/backend comes up offline in-container, and emitting to a fake endpoint would be dishonest (mirrors the DW-C1-1 live-Dagster-schedule and DW-D3-1 live-LLM-backend attended bring-ups). Because the emitters are already injectable, the follow-up is a substrate swap (construct an env-driven provider/client in `settings.py` or a factory and inject it), not an instrumentation change. Do NOT wire a live endpoint into the default path or weaken the offline fixture gate to require a backend.
  evidence: `tests/observability/test_observability_fixtures.py` drives a real two-node SequentialRunner pipeline (plus the pipeline-level hooks, as KedroSession fires them) with an in-memory OTel span exporter + a capturing OpenLineage client (`make_capturing_client`) and asserts the emitted event/span SHAPE — START+COMPLETE per node, input/output lineage edges, shared runId, the rowCount + rows/latency(`>=0`)/cache-hit facets, and the nested pipeline→node→dataset span tree in one trace — these captured fixtures ARE the gate (AD-20). Edge cases proven: `on_node_error` emits FAIL + closes the span (no leak, ERROR status), no-input/output nodes, empty-frame rows=0, non-DataFrame output degrades (rowCount omitted, no crash), the None-captor default path runs the full lifecycle without emitting/crashing, nested pipeline frames close without leaking, and no now()/uuid leaks into any asserted field. `test_no_inline_io.py::test_observability_libs_only_in_observability` pins the single-seam containment. `AtlasObservabilityHooks.__getstate__` drops the un-deepcopyable OTel tracer so C1's translator can deep-copy the settings HOOKS (the copy rebuilds a lazy default tracer). No socket is bound and no exporter reaches a network in any test (offline).

  status: open
## DW-E2-2 — Dagster-plane observability inheritance verification + span-key footgun (bring-up)

- source_spec: `e2-integrate-openlineage-opentelemetry.md`
  summary: The AD-23 claim "the Dagster plane inherits the settings-registered observability hook, nested" is verified for the KEDRO plane (fixture gate) but NOT yet for the Dagster plane — the C1 live bring-up (DW-C1-1) is where a real kedro-dagster run confirms parent→node→dataset span nesting + cache_hits survive the translator's per-run hook deepcopy. The deepcopy asymmetry (a dropped OTel provider) is FIXED in E2 (`__deepcopy__` shares _provider + _ol by reference; regression test `test_deepcopy_preserves_injected_backends_no_otel_ol_asymmetry`), so a future injected exporter reaches both planes — but the end-to-end Dagster-plane assertion still rides on the deferred daemon bring-up. Also latent (Reviewer-B finding 2): `_nodes` is keyed by `node.name`; two in-flight runs of the same node name would overwrite/leak state — impossible under Kedro's unique-names-per-pipeline + DAG-ordered runners today, but a `(node.name, run_id)` key would remove the footgun if a future runner violated that. Not reachable now.
  evidence: E2 gate drives a SequentialRunner + manual before/after_pipeline_run; `dagster definitions validate` passes but does not RUN nodes. Thread-safety: `_nodes`/`produced` are unlocked — correct under SequentialRunner + C1 in_process executor (DAG-ordered), a ThreadRunner/ParallelRunner would need locking.

  status: open
## DW-E2-3 — AtlasNodeMetricsRunFacet provenance stamp (cosmetic)

- source_spec: `e2-integrate-openlineage-opentelemetry.md`
  summary: The custom `atlasNodeMetrics` run facet is emitted without an explicit `producer=PRODUCER`, so its `_producer` defaults to the OpenLineage library URI rather than the project PRODUCER every other emitted facet carries (Reviewer-A nice-to-have). Cosmetic — the metric VALUES (rows/latency_ms/cache_hits) are correct; only the facet's provenance-stamp URI differs. Left untouched to avoid perturbing the attrs RunFacet inheritance; revisit if lineage-provenance consistency is ever asserted.
  evidence: `AtlasNodeMetricsRunFacet` construction on the COMPLETE event does not pass producer; the standard rowCount + errorMessage facets do.

  status: open
## DW-F1-1 — the cold-start / warm-incremental benchmark (ATTENDED, SM-3) — DEFERRED

- source_spec: `f1-complete-the-duckdb-consolidation-prove-the-cold-start-claim.md`
  summary: F1 shipped the always-on offline half — the DuckDB-singularity grep gate
    (`tests/singularity`, pixi `duckdb-singularity`): NO sqlite3 path in the migrated
    surface (FR-5/AD-4), the one legacy-SQLite reader pinned to tests/ (the B4 credentialed
    comparator reading the OLD store to retire it). The PERFORMANCE half — the attended
    benchmark recording (a) the warm incremental refresh headline (only affected nodes
    re-run) and (b) the cold full-build wall-clock vs the legacy 3-4 h network-bound baseline
    — is the ATTENDED boundary event (one of the five § 2.5 attended events). Per SM-3 the
    pass THRESHOLD must be fixed in this story's spec BEFORE the benchmark runs, and pass is
    adjudicated by operator sign-off (AD-19). Do NOT chase cold-start (SM-C1 — the headline is
    warm-incremental; cold is network-bound and not the win). Keystone-story pre-flight
    (budget + dev_stall_grace_s raise) applies at the attended run, not in-loop.
  evidence: the grep gate is green offline; there is no in-container way to run a credentialed
    full cold build (no operator runtime data, AD-11). B4 retirement (DW-B4-2) is the
    precondition — legacy is not marked retired until its credentialed parity + sign-off land.

  status: open
## DW-F2-1 — the Great Expectations boundary adapter (version-capped at cf 1.18.2) — DEFERRED

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story F2, FR-10, AD-9)
  summary: F2 shipped the load-bearing, buildable-now half of the data-validation surface — `validation.py` as the SINGLE validation seam: a validator-agnostic `Validator` protocol (a backend REPORTS `ContractViolation`s, never halts itself, so the hook owns the raise+alert in ONE place and a new backend needs ZERO node/hook edits — AC-3), the shipped inline `PanderaValidator` (per-dataset `DataFrameSchema` registry `DEFAULT_CONTRACTS`, declared as DATA never inline in nodes), and `DataValidationHooks` registered ONCE in `settings.HOOKS` (AD-23) so EVERY entry point validates — firing in `after_node_run`, the verified kedro-1.5.0 pre-persist point (`Task._call_node_run` calls `after_node_run` with the full outputs dict BEFORE the runner save loop), raising a native `DataContractViolation` that halts before ANY output persists and, on the way out, emits an `AtlasAlert` on E1's real A2A channel (AD-20, `build_alert_payload` → injected `alert_sink` → `hand_off`/`AuthoringInbox`). The DEFERRED half is the **Great Expectations boundary adapter**: AD-9 caps GX at conda-forge **1.18.2** semantics (no ≥1.19 features), but the in-env GX is **1.19.0** and cannot be *statically guaranteed* to stay within 1.18.2-only features, so — per AD-9's explicit preference — the shipped hook path imports **NO** `great_expectations` at all. `GreatExpectationsBoundaryValidator` is a protocol-conforming STUB (its `check` raises `NotImplementedError` with this DW note) that proves the seam ACCEPTS a GX backend with zero node changes; the real adapter is deferred to an environment where GX is pinned to 1.18.2, at which point the stub is replaced by a 1.18.2-feature-only adapter and slotted into the same `validators=[...]` list — no node/hook change (the point of the seam). The `kedro-great-expectations` / `kedro-pandera` plugins stay BANNED everywhere (the hook is hand-rolled). Do NOT import GX into the shipped path or lift the 1.18.2 cap to unblock this.
  evidence: `tests/validation/test_validation_hook.py` drives a real one-node SequentialRunner pipeline with a persistence-tracking dataset and asserts the F2 behaviours: a malformed payload (PyPI frame missing `version`) HALTS via a native `DataContractViolation` with the output NOT persisted (save loop never ran), emitting an `AtlasAlert` (severity critical + rule `pandera_schema` + evidence naming the column) delivered over the real A2A channel (`hand_off` → `AuthoringInbox`, round-trip-identical); a valid payload passes AND persists (no false halt); a STUB second validator halts the SAME node with zero node edits (AC-3 validator-agnosticism), and a stub-only config proves pandera is not special; the GX boundary stub raises with the 1.18.2 DW note; `test_no_inline_io.py::test_banned_validation_plugins_nowhere` + `test_no_great_expectations_in_shipped_validation_path` pin AD-9. Edge cases proven: no registered contract → pass-through; non-frame output skips gracefully (no crash); empty-frame conformant passes / missing-column halts; a broken validator halts loudly (never silently passes bad data); the default no-op sink and a RAISING sink both never mask the halt; a multi-output node halts before ANY output persists; the default hook is deepcopy-safe (C1 translator copies `settings.HOOKS`); and co-registration with the E2 observability hook still halts order-independently. `DEFAULT_CONTRACTS` ships EMPTY (machinery + seam, nothing speculative) so the settings-armed hook can never false-halt a real run until a contract is declared. No socket is bound and no network is touched in any test (offline).

  status: open
## DW-F2-2 — wire a real A2A alert_sink into the shipped validation hook (gated on F4's first contract)

- source_spec: `f2-data-validation-hook-inline-pandera-contracts.md`
  summary: F2's `settings.HOOKS` constructs `DataValidationHooks()` with NO `alert_sink`, so a
    production contract violation halts correctly (data never persists) and BUILDS the AtlasAlert
    (carried on the raised `DataContractViolation.alert`) but does NOT DELIVER it on the A2A
    channel — delivery is proven only in the gate via an injected sink. This is MOOT today
    (`DEFAULT_CONTRACTS` is empty — no violation can fire), but the moment F4 registers the first
    real pandera contract, a production halt would drop the AD-20 alert. Wiring an offline-safe
    default sink (e.g. an AuthoringInbox-backed hand_off, NOT a networked sink — that would break
    the AD offline-import guarantee) into `settings.HOOKS` is therefore a GATING step of F4 (its
    ComplianceReport/policy-breach path raises "identical failure semantics to an FR-10
    violation"). Reviewer-A S1.
  evidence: `DataValidationHooks.__init__(alert_sink=None)` → `_halt` skips delivery when
    `_sink is None`; the raised exception carries `.alert`, so nothing is lost at the raise site,
    only unconsumed. Both reviewers flagged; the _build_alert robustness fix (JSON-native evidence
    + rule fallback) landed in F2 so a real sink can't be crashed by a third-party backend.

  status: open
## DW-F3-1 — a real learned embedding model (upgrade from the deterministic default)

- source_spec: `f3-implement-vector-similarity-search-rag-via-duckdb-vss.md`
  summary: F3's default embedder is a deterministic, offline, dependency-light feature-hash
    (hashing-trick) vectorizer — it proves the DuckDB `vss` RANKING mechanism (which is what F3
    ships) with no model download and no network, and is stable across processes/machines
    (hashlib, never Python's salted hash()). A real LEARNED embedding model (e.g.
    sentence-transformers) is the semantic-quality upgrade: it is heavy and may need a
    model download / network, so it is DEFERRED. The seam is ready — `DuckdbVssRagStore(embedder=…)`
    accepts any object with an int `dim` + `embed(text)->list[float]`; the ranking still runs in
    DuckDB regardless of embedder, so the upgrade requires NO store/query change. Wire it when a
    conda-forge-provisioned model + an embedding-provisioning story lands.
  evidence: `rag/embedding.py::HashingEmbedder` is the default; `Embedder` is a Protocol; the
    gate proves ranked results are deterministic under the hash embedder (a learned model would
    change the vectors, not the ranking mechanism).

  status: open
## DW-F3-2 — live `vss` extension provisioning (the one-time network INSTALL)

- source_spec: `f3-implement-vector-similarity-search-rag-via-duckdb-vss.md`
  summary: The consumer path is offline: it only `LOAD`s `vss` from the pre-provisioned local
    extension cache and raises `VssNotProvisionedError` (naming the provisioning step) if absent
    — never a silent network `INSTALL` (AD-13). The one-time `INSTALL vss` (network) lives ONLY
    in the explicit, attended `rag.provision_vss(connection)`, which the consumer path never
    calls. In THIS container vss is already cached (v1.5.4), so the offline LOAD works; a fresh
    air-gapped/enterprise environment must run `provision_vss` (or ship the vendored extension
    to the DuckDB extension dir) once, attended, before the RAG surface is usable. That
    provisioning-in-a-clean-environment step is the deferred/attended piece.
  evidence: `rag/store.py::load_vss_offline` (offline LOAD or VssNotProvisionedError) vs
    `provision_vss` (the only INSTALL); the rag gate proves the consumer path makes no network call.

  status: open
## DW-G1-1 — full Vizro-AI dashboard RENDERED inside Pyodide (the heavy read-surface half)

- source_spec: `g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md`
  summary: G1 ships the LOAD-BEARING half of the acceptance criterion — the intelligence read
    surface's query runs CLIENT-SIDE in the browser with NO backend, on a GENUINE DuckDB-WASM
    engine reading a statically-hosted Parquet file (proven by the `wasm-smoke` Playwright gate).
    What is DEFERRED is compiling the full D2 Vizro-AI DASHBOARD (its Dash/Plotly page tree, the
    28-page inventory, the D3 NL query field) to run inside PYODIDE in the same page. That is the
    heaviest piece (Pyodide runtime + the vizro/dash/plotly wheel stack loaded in-browser) and is
    an attended bring-up: the in-container artifact exposes the BSL/DuckDB QUERY surface (the
    D1 `feedstock-health` semantics, `ci_red = ci_status IN ('failure','error')`), not the
    rendered Vizro component tree. Wire the Pyodide-hosted Vizro render when the browser wheel
    stack + a static-host budget (DW-G1-2) land; the query surface it will sit on is already proven.
  evidence: `wasm/index.html` runs a DuckDB-WASM `read_parquet` query and renders a plain HTML
    table (the query result), not a Vizro `Dashboard`; `tests/wasm/test_wasm_smoke.py` asserts the
    client-side query result, not a Vizro component tree. The D2 dashboard OBJECT itself is built +
    asserted OFFLINE by the separate `dashboard-dryrun` gate (server-side, Python) — G1 is the
    browser/no-backend half.

  status: open
## DW-G1-2 — heavy WASM build assets are gitignored; CI must run `wasm-build` before `wasm-smoke`

- source_spec: `g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md`
  summary: The runtime artifact (`wasm/build/`) carries a ~40 MB DuckDB `.wasm` module, the
    esbuild bundle, the vendored parquet extension (~3 MB), and the demo Parquet — far too heavy to
    commit, so `wasm/build/` + `node_modules/` are gitignored. The `wasm-smoke` gate SKIPS with a
    "run `wasm-build` first" message when `wasm/build/` is absent (a legitimate not-built skip,
    DISTINCT from the browser-ran-but-failed case, which always FAILS). Consequence: a fresh
    clone / CI must run `pixi run -e local-recipes wasm-build` (BUILD-TIME network: npm + the
    DuckDB extension host) before `wasm-smoke`. Wiring `wasm-build` as an automatic CI pre-step
    (or hosting the pre-built artifact as a CI cache / G2 static-host output) is deferred to G2
    (Parquet-to-static-host), which owns the published-artifact surface. Until then the two-step
    build→verify is the documented local/CI flow.
  evidence: `wasm/.gitignore` ignores `build/` + `node_modules/`; `wasm/build.py` is the build
    step; `tests/wasm/test_wasm_smoke.py` `static_server` fixture `pytest.skip`s when
    `build/index.html` is absent. `wasm-build` uses the network (npm + `extensions.duckdb.org`
    via curl); `wasm-smoke` is offline (loopback static host + asserted zero external requests).

  status: open
## DW-G2-1 — the LIVE GitHub Pages publish is the ATTENDED boundary event (not automated)

- source_spec: `g2-emit-parquet-artifacts-to-a-static-web-host.md`
  summary: G2 ships the host-agnostic EMITTER (`pyforge.atlas.publish.emit_static_site`) — it
    writes the chunked-Parquet + single-owner `manifest.json` LAYOUT to a target directory ("the
    static host filesystem"), and the `publish-range` gate PROVES that layout is consumed via HTTP
    Range (206 partial reads, footer + row groups only) by a DuckDB httpfs client over a loopback
    host. What is DEFERRED is the LIVE publish: pushing the emitted directory to a real static host
    (Q4 default: GitHub Pages `gh-pages` / an enterprise mirror) is one of the five § 2.5 ATTENDED
    boundary events — it needs credentials + a chosen host + a human at the wheel, so it is never
    run in-loop. The emitter is host-agnostic by construction (target is a PATH; the base URL is a
    runtime arg to `chunk_url`, no `github.io` anywhere in the emit logic — AD-2), so the attended
    step is purely "serve/push this directory" with zero code change to substitute a mirror.
    Wiring the browser G1 page to consume the emitted manifest layout over Range (today it fetches
    a single whole Parquet via `fetch().arrayBuffer()`) is the same attended event's follow-on.
  evidence: `src/pyforge/atlas/publish/emitter.py` (`emit_static_site` writes to a dir, relative
    manifest paths, `chunk_url(base_url, path)` composes the runtime host); `python -m
    pyforge.atlas.publish` emits to a gitignored `_site/`; `tests/publish/test_emit_range.py`
    fixture-hosts on loopback and asserts NO live publish. No push/credential/host code exists.

  status: open
## DW-G2-2 — migrate the G1 wasm/ runtime to consume the emitter's manifest (single-owner completion)

- source_spec: `g2-emit-parquet-artifacts-to-a-static-web-host.md`
  summary: G2's emitter is the single owner of the PUBLISHED-site layout (chunked Parquet +
    manifest.json), READ by the publish Range gate. But G1's wasm/ runtime shipped first and
    fetches a FLAT `./core_feedstock_health.parquet` (its own build.py produces that flat file) —
    it does NOT read manifest.json / chunk_url yet, so it is a SECOND, independent layout for the
    same data (Reviewer-A). Completing the single-owner invariant = migrating G1's index.html to
    load the manifest + compose chunk URLs via chunk_url (and having build.py emit via the
    emitter). Deferred because it re-touches the G1 WASM artifact + its ~41 MB bundle rebuild
    (DW-G1-2 CI build step) and is best done with the live-publish bring-up (DW-G2-1). Until then
    the emitter/gate own the published layout; G1 remains an independent dev artifact.
  evidence: `wasm/index.html` hardcodes `fetch("./core_feedstock_health.parquet")`;
    `wasm/build.py::_csv_to_parquet` produces the flat file; the emitter produces
    `core_feedstock_health/core_feedstock_health-0000.parquet` + `manifest.json`. The publish gate
    IS a manifest consumer (proves the layout); G1 is not yet.

  status: open
## DW-G3 — the live Dagster sensor DAEMON bring-up (ATTENDED, Q2) — DEFERRED to the wave-boundary event

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story G3, § 5.9, FR-6)
  summary: G3 shipped the BUILDABLE half of event-driven ingestion — the sensor DEFINITIONS +
    their eval logic, wired into C1's `defs`, all verified with NO live execution and NO network.
    `orchestration/event_source.py` (dagster-free event parse + monotonic-`seq` cursor dedupe +
    run/skip DECISION, so AD-1's "only definitions.py imports dagster" rule holds) + `UPSTREAM_SENSORS`
    / `build_upstream_sensor` in `orchestration/definitions.py` add two sensors to
    `dg.Definitions(..., sensors=[...])`: `pypi_release_sensor` → the existing `phase_h_pypi_versions`
    job, `vcs_release_sensor` → the existing `phase_k_vcs_upstream` job (AD-23 — each yields a
    `RunRequest` for a job C1 already built; NO second execution plane), both targeting the two
    upstream surfaces A3 flipped to `IncrementalParquetDataset` (AD-5 — the sensor only TRIGGERS;
    the run re-fetches only TTL-stale rows). Event source = **RSS/poll cursor (resolved over webhooks
    — a webhook needs an always-on bound public ingress, the Q2 daemon-footprint cost, and can't be
    exercised offline); the source is INJECTABLE and defaults to an offline no-op (`offline_event_source`
    → `[]`)**, so a built `defs` carries NO network dependency. Sensors ship `default_status=STOPPED` —
    nothing auto-starts. The ACTUAL bring-up is the attended Q2 boundary: standing up a
    `dagster-daemon`, turning the sensors RUNNING, injecting the LIVE RSS/poll feed readers
    (PyPI `updates.xml`, per-repo `releases.atom`) in place of the offline no-op, and observing real
    incremental runs fire. Do NOT weaken the dryrun gate to unattended-execute a live daemon or bind a
    socket (NFR-12). Mirrors DW-C1-1 (live schedule bring-up) and DW-D3-1 (live LLM backend).
  evidence: `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline;
    `tests/orchestration/test_definitions_dryrun.py` (+12: sensors enumerate + target real jobs, a
    simulated event via `build_sensor_context` + an injected fixture source → one `RunRequest` for the
    right incremental job with the cursor advancing, no-event/duplicate/malformed/raising → `SkipReason`,
    `default_status=STOPPED`, offline-default-is-no-op) + the AD-1 import-ban (`tests/catalog/test_no_inline_io.py`,
    now covering `orchestration/event_source.py` via rglob — it imports no dagster). The live feed
    readers do not exist in-package (injected, mirroring the B5/B7/B8 injected-fetcher deferrals).

  status: open
## DW-H1 — the MinIO/PostgreSQL SERVER provisioning + bring-up (ATTENDED) — DEFERRED to the H1 precondition event

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H1, § 7.4, FR-22(a))
  summary: H1 shipped the BUILDABLE half of the Karpathy-wiki storage layer — the layout contract
    (`factory/wiki.py`: `WIKI_STAGES` + `WikiLayout` + `scaffold_wiki`, the SINGLE owner of the
    `raw/ → compiled/ → outputs/` tree), the five § 2.2 personas + their BMAD customization-layer
    resolution (`factory/personas.py`), and the storage-backend RESOLVER (`factory/storage.py`),
    all offline. The architecture (ARCHITECTURE-SPINE § "Factory layer") records that **only the
    MinIO Python SDK is in-env today — the MinIO/PostgreSQL SERVERS are not provisioned**, and calls
    that server bring-up the H1 precondition (Spine "Deferred"). H1's code therefore DEFAULTS to the
    plain local filesystem (`resolve_storage_config()` → `backend="filesystem"` when
    `ATLAS_WIKI_S3_ENDPOINT` is empty/unset) and never opens a connection; a MinIO backend is
    selected ONLY when an endpoint is explicitly configured (host-agnostic, AD-2 — no host is
    hardcoded). The ACTUAL deferred bring-up: provision the conda-forge MinIO + PostgreSQL servers
    (precedent: MyBMAD's per-user PostgreSQL in the `bmad-ui` env), create the wiki bucket, wire the
    live `minio` SDK client from the resolved config, and run the crews against the object store
    instead of the local dir. Do NOT weaken any gate to stand up a server unattended or bind a
    socket (NFR-12). Mirrors DW-C1-1 / DW-G3 (live daemon bring-up) and DW-D3-1 (live backend).
  evidence: `factory/storage.py::resolve_storage_config` returns `filesystem` with no network
    touch when the endpoint env is absent (`tests/factory/test_personas.py` storage cases:
    default-is-filesystem, empty-env-is-unset, configured-endpoint-selects-minio,
    both-keys-required-for-credentials). Only `minio` the SDK is importable in-env; no server
    process runs. The AD-16 pixi.toml line ships `minio >=7.2.20` (SDK) + `psycopg2 >=2.9.12`
    (driver) — the SDKs, not the servers.

  status: open
## DW-H2 — the live `agno`-Agent / LLM synthesis + F3-vss production retriever bring-up (ATTENDED) — DEFERRED

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H2, § 7.3, FR-22(b))
  summary: H2 shipped the three wiki crews (`factory/crews.py`: `CompileCrew`, `LintCrew`,
    `QACrew`) with their DETERMINISTIC cores running fully offline on a fixture wiki — the real
    raw→compiled→answer flow, staleness propagation, and lint rules all exercised with NO network
    and NO model. Two production seams are INJECTABLE and default to the offline path, so the
    live bring-up is the attended deferral (mirrors DW-D3-1 LLM backend + DW-F3-2 vss provisioning):
    (1) **the `agno`-Agent / LLM synthesis** — `CompileCrew`'s `enricher` and `QACrew`'s
    `synthesizer` default to offline determinism (identity enrich; extractive answer). Standing up
    a real `agno` Agent over a resolved model backend (`pyforge.atlas.nl.backend.resolve_backend`
    — repo model-backend routing, env-driven, never a hardcoded endpoint) and running the crews
    through it is the deferred generative path; (2) **the F3 vss production retriever** —
    `QACrew`'s `retriever` defaults to the offline deterministic keyword-overlap ranker; the
    production retriever is `rag.store.DuckdbVssRagStore.similarity_search` (AD-4 single engine)
    wrapped to the `Retriever` signature, which needs the vss extension provisioned (DW-F3-2). Do
    NOT weaken the H2 gate to call a live model or bind a socket (NFR-12).
  evidence: `factory/crews.py` imports only `yaml` + stdlib + `.wiki` (AD-1 import-ban green over
    the new module); `tests/factory/test_crews.py` exercises compile/lint/Q&A + staleness
    propagation offline (26 crew tests). `Enricher`/`Synthesizer`/`Retriever` are the injectable
    seams; their defaults (`_identity_enricher`, `_extractive_synthesizer`, `keyword_retriever`)
    are offline. No `agno` Agent is constructed and no model/vss is loaded in-package.

  status: open
## DW-H3 — the live La Suite/Wagtail SERVER + credential + httpx opener bring-up (ATTENDED) — DEFERRED

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H3, § 7.1, FR-22(c))
  summary: H3 shipped the BUILDABLE half of the CMS sync — `factory/lasuite.py`: `LaSuiteClient`
    (create/update/get/list over the Wagtail/Django REST shape) + `WikiSyncer` (idempotent
    compiled-wiki → CMS push keyed by content digest: new→create, changed→update,
    unchanged→SKIP-with-no-remote-call, § 2.1 idempotent-first), verified end-to-end against an
    IN-MEMORY mock Wagtail (push / update / idempotent re-push round-trip, mapping-resume) with NO
    network. The transport is the injected `opener` seam — package code holds NO HTTP client (AC-2,
    enforced by the no-inline-IO gate), exactly like the B5/B7/B8 dataset `refresher`/`fetcher`
    injection. The ACTUAL bring-up is attended: provision the conda-forge Wagtail + django-lasuite
    server (+ PostgreSQL/MinIO from DW-H1), mint an API token, construct the live httpx-backed
    `opener` OUTSIDE package code (a script / the C1 Dagster resource), set `LASUITE_BASE_URL` +
    `LASUITE_API_TOKEN` (host-agnostic, AD-2 — never hardcoded), and run `WikiSyncer.sync_all()`
    against the real CMS. Do NOT weaken the gate to import httpx into package code or bind a socket
    (AC-2 / NFR-12). Mirrors DW-D3-1 (live LLM backend) and DW-C1-1 (live daemon).
  evidence: `factory/lasuite.py` imports only stdlib + `.crews`/`.wiki` (no httpx — the
    no-inline-IO gate `tests/catalog/test_no_inline_io.py` is green over it); the default
    `_unconfigured_opener` raises a clear "no CMS transport injected … inject the live httpx opener
    at the attended bring-up (DW-H3)" rather than reaching for the network.
    `tests/factory/test_lasuite.py` proves the round-trip + idempotency (zero remote calls on an
    unchanged re-push) + mapping-resume against the mock opener. `resolve_lasuite_config` returns
    `None` unless BOTH env vars are set.

  status: open
## DW-H4 — the live factory-crew daemon bring-up (sensor RUNNING + weekly lint + live wiki store) (ATTENDED) — DEFERRED

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H4, § 7.2, FR-22(d)/FR-6)
  summary: H4 shipped the BUILDABLE half of the factory orchestration — the crew ASSETS
    (`compiled_wiki`, `wiki_lint_report`), their asset-jobs (`wiki_compile_job`, `wiki_lint_job`),
    the weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`), and the new-raw-file compile
    SENSOR (`wiki_raw_file_sensor`) — all wired into C1's `defs` on the SAME Dagster plane
    (AD-6/AD-23; no second scheduler) and verified OFFLINE: `dagster definitions validate` passes,
    the assets enumerate, and a simulated new-raw-file event (injected `raw_lister` +
    `build_sensor_context`) yields one `RunRequest` for the compile job (dedupe/degrade covered).
    The raw-scan DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds;
    only `definitions.py` imports dagster). The ACTUAL bring-up is the attended Q2/daemon event:
    stand up a `dagster-daemon`, turn `wiki_raw_file_sensor` RUNNING against the LIVE wiki store
    (the DW-H1 MinIO/PostgreSQL + `ATLAS_WIKI_ROOT`), let the weekly lint schedule fire, and observe
    real compile/lint crew runs materialize the assets. The sensor ships `default_status=STOPPED`
    (nothing auto-starts). Do NOT weaken the dryrun gate to unattended-execute a live daemon or bind
    a socket (NFR-12). Mirrors DW-C1-1 (live schedule) + DW-G3 (live sensor daemon).
  evidence: `orchestration/wiki_events.py` imports only stdlib (AD-1 import-ban green over it);
    `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline;
    `tests/orchestration/test_definitions_dryrun.py` H4 section (+12: assets enumerate, crew jobs
    resolve, weekly lint schedule, sensor targets the compile job, simulated new-raw-file →
    RunRequest, no-new-file/already-seen → SkipReason, lister-error degrades, ships STOPPED, +
    wiki_events unit tests). The live wiki store is DW-H1; the crews' agno/LLM synthesis is DW-H2.

---

  status: open
## DW-I4-1 — 10.5 finalized on a spent review budget, not on convergence (LOW) — DEFERRED

- source_spec: `spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md` (Epic 10 / Story I4, AUD-ATLAS-043/044)
  origin: review-budget-followup (bmad-loop run `20260728-201438-15bd`)
  summary: The story finalized `done` with the verify gate GREEN (kedro-test 803 passed,
    kedro-catalog-check 47) — but the review pass was still RECOMMENDING an independent
    follow-up when `limits.max_followup_reviews = 1` was spent. The story therefore closed
    on a BUDGET CAP, not because its reviewer was satisfied. That distinction matters here
    more than usual: this same story's FIRST drive produced a faithful implementation of a
    wrong contract and had to be reverted, so "the reviewer still wanted another look" is
    not a formality. C1-C6 were independently verified in the shipped code afterwards
    (per-kind resolution, `provenance_kind` vocabulary, oldest/newest range, null+reason,
    `SCHEMA_VERSION`, dashboard stamps), which is why this is LOW rather than open risk —
    but the recommended pass itself never ran.
  resolution: run one independent review of `provenance.py` + the `read_dataset` envelope
    against C1-C6, ideally fresh-context (the pyforge-atlas retro A1 finding: in-loop
    reviewers inherit the implementation's assumptions; the INDEPENDENT pass is what caught
    B1/B2/B5/B7/G2). Not a blocker for I5.
  status: review PERFORMED 2026-07-29 — CLOSED with no findings.
    The owed independent pass ran as adversarial MUTATION testing of `provenance.py`. Three
    mutants injected, each CAUGHT by tests/mcp + tests/dashboard: (1) `file-mtime` made to
    report the READ time — i.e. AUD-ATLAS-043 itself, reintroduced — 2 tests failed;
    (2) the same substitution on the `row-fetched-at` path, 4 failed; (3) C3 violated by
    reporting the NEWEST `fetched_at` as the oldest, 3 failed. The gate therefore pins the
    actual property ("a persisted dataset reports its own recorded time, not the read time")
    and not merely "a stamp is present", which is what the reverted first implementation
    passed. Caveat on record: the reviewer was not context-free — mutation evidence stands in
    for a fresh reading.
  promoted: 2026-07-29 from the gitignored Tier-3 `implementation-artifacts/deferred-work.md`,
    where it was recorded as the generic id `DW-1`. Renamed to `DW-I4-1` to match this
    ledger's `DW-<story>-<n>` convention and to stop a bare `DW-1` colliding with the next
    run that emits one.

---

## DW-AD23-1 — Run admission was asserted but never implemented (HIGH) — CLOSED

- source_spec: `spec-c1-integrate-kedro-dagster-for-scheduling-execution.md` (Epic 4 / Story C1, AD-23, audit `AUD-ATLAS-046`)
  origin: audit-retraction (`sprint-change-proposal-2026-07-27.md`), closed by Story 10.6
  summary: `ARCHITECTURE-SPINE.md` AD-23 and `orchestration/definitions.py` both asserted
    "a dataset has one writing run at a time — run admission serializes on the target dataset
    set". **Nothing implemented it.** The `in_process` Dagster executor in
    `conf/base/dagster.yml` serializes ops *within* one run and provides no cross-run or
    cross-process admission; there was no lock or queue anywhere in the package. Two MCP
    `run_*` triggers, or an MCP trigger racing a `kedro run`, could interleave writes to the
    same Parquet file. The 2026-07-27 sprint-change proposal retracted the claim and DEMOTED
    AD-23, citing this id — which, until now, **eight artifacts referenced and no ledger
    entry defined**.
  resolution: **CLOSED 2026-07-29 by Story 10.6** (`spec-10-6-make-run-admission-real-or-stop-claiming-it.md`).
    `pyforge/atlas/admission.py` ships the mechanism and `RunAdmissionHooks()` is the fourth
    entry in `settings.HOOKS`, so the CLI, the seven MCP `run_*` tools and the Dagster plane
    all inherit it from one registration (it rides the kedro HOOK MANAGER — not
    `KedroSession.run`, which the Dagster plane does not use). One `filelock` OS file lock per
    dataset in `pipeline.all_outputs()`, acquired in sorted order in `before_pipeline_run`,
    released in BOTH `after_pipeline_run` and `on_pipeline_error`. Reject-fast by default with
    a typed `RunAdmissionRejected` naming the conflicting dataset, the holder's run id, PID and
    hold start; a bounded wait is opt-in via `--params admission_wait_seconds=<n>` and is
    enforced as ONE deadline shared across all locks. A dead holder never wedges the factory
    (the kernel drops its flock; the surviving sidecar is reclaimed and logged). The lock root
    is PROJECT-anchored, never CWD-relative — a first implementation got this wrong and was
    reverted, because kedro resolves catalog filepaths under the project root while the MCP
    server and the repo's pixi tasks run from different CWDs.
    Gate, re-run against the tree on 2026-07-29 after review pass 4 (not transcribed):
    `kedro-test` **901 passed / 19 skipped** (baseline before the story: 803 / 19;
    `tests/test_admission.py` contributes **98**, including a two-process contention gate that
    spawns a real second OS process — no threads, no mocks); `kedro-catalog-check` **47**;
    `dagster-dryrun` **58**.
    AD-23 was re-promoted to its full form in the spine on the strength of that gate, with the
    single-machine (NFS `flock`) and Dagster-release boundaries carried explicitly.
  status: closed

---

## DW-AD23-2 — Run-admission release residuals: Dagster-plane process-locality, `in_process` coupling, and the hook-ordering strand window (MEDIUM) — DEFERRED

- source_spec: `spec-10-6-make-run-admission-real-or-stop-claiming-it.md` (Epic 10 / Story I5, AD-23)
  origin: implementation boundary recorded while closing `DW-AD23-1`
  summary: FOUR residuals, all out of Story 10.6's scope. (1), (2) and (4) are Dagster-plane;
    (3) is NOT — it affects the long-lived MCP server today, so do not scope this entry as
    Dagster-only work.
    (1) **`run_result` signature.** kedro-dagster's after-op calls
    `after_pipeline_run(run_results=None, ...)` — it omits kedro's `run_result` entirely.
    pluggy's missing-argument check is per-IMPL, not per-call, so any impl declaring
    `run_result` raises `HookCallError`. `AtlasObservabilityHooks.after_pipeline_run` still
    declares it, so the Dagster after-op still fails there. Admission is unharmed only because
    it is dispatched FIRST and its subset signature lets it release BEFORE the E2 impl raises.
    That ordering is load-bearing, and it is bought by `@hook_impl(tryfirst=True)` on all three
    admission hooks — **not** by tuple position. Tuple position is NOT sufficient, and was
    measured to be wrong: `KedroSession.__init__` registers `settings.HOOKS` and *then*
    `_register_hooks_entry_points(...)`, so an installed plugin registers later and, under
    pluggy's LIFO, dispatches earlier — this env's `kedro-viz` `PipelineRunStatusHook` took all
    three hooks ahead of admission until the markers were added (review pass 3). Not fixed
    here: the `run_result` signature is E2-owned and touches 10 positional call sites in
    `tests/observability/`, which this story is scoped out of.
    (2) **`in_process` coupling.** Acquisition happens inside the
    `before_pipeline_run_hook_<job>` op. An OS file lock belongs to the open file description
    of the process that took it, so under a MULTIPROCESS Dagster executor that op's subprocess
    would exit and the kernel would drop every lock before the first node ran — admission would
    silently become a no-op on this plane while still reporting success. It is safe today ONLY
    because `conf/base/dagster.yml` declares `in_process`.
    (3) **Later before-hooks can strand admission's locks.** Kedro calls BOTH
    `before_pipeline_run` and `after_pipeline_run` OUTSIDE its `try` block, and it catches
    `Exception` — so only `Exception` subclasses raised by `runner.run` reach
    `on_pipeline_error`, and a `KeyboardInterrupt` or `SystemExit` out of the runner fires
    NEITHER hook. Admission is dispatched FIRST (`tryfirst`), so
    every other before-hook runs after the locks are taken: if one raises — e.g.
    `AtlasObservabilityHooks.before_pipeline_run` opening an OTel span against a live exporter,
    or any installed plugin's — kedro fires no error hook and the locks are held until the
    process exits. Harmless for a CLI run; for the long-lived MCP server it wedges that dataset
    set until restart. It is an AVAILABILITY boundary, not a correctness hole (no second writer
    is ever admitted), and it is NOT fixable by releasing other runs' tickets — that would be
    actively wrong inside a concurrently-serving process. The symmetric *release*-side window
    (a hook raising in `after_pipeline_run` before admission got to run) is CLOSED by
    `tryfirst`, and only by it.
    (4) **A FAILED Dagster run releases nothing in-process.** kedro-dagster's after-op is
    SKIPPED when an upstream op fails, and it fires `on_pipeline_error` from a
    `@dg.run_failure_sensor` that executes in the Dagster DAEMON process — where `_tickets` is
    empty, so `_release_for` is a no-op. On that plane a failed run's locks are therefore freed
    only by the run worker's process exit. Survivable today only because Dagster launches run
    workers as separate short-lived processes: an undeclared coupling of exactly the same kind
    as the `in_process` one in (2), and recorded here for the same reason. Nothing on the CLI
    or MCP planes is affected — kedro fires `on_pipeline_error` in-process there.
  resolution: (1) drop the unused `run_result` parameter from
    `AtlasObservabilityHooks.after_pipeline_run` (or make it defaulted) and update its
    positional call sites, then assert both planes in `tests/observability/`. (2) Before
    `DW-C1-1`'s daemon bring-up reaches for a real executor, move admission acquisition out of
    the hook op (e.g. onto a run-scoped Dagster resource whose lifetime spans the run) — or
    accept `in_process` as a hard constraint and gate on it. `conf/base/dagster.yml` and
    `admission.py` both carry the warning inline so the coupling is discovered at the point of
    change, not after a silent regression. (3) needs a hook-manager-level guarantee kedro does not
    currently offer; the honest interim is that it is recorded on AD-23 and in `SPEC.md` as the
    third boundary rather than left for an operator to discover during an incident. (4) resolves
    with the same move as (2) — a run-scoped Dagster resource whose teardown runs in the run
    process would release on both the success and the failure path, replacing two undeclared
    process-lifetime couplings with one explicit lifetime.
  status: open

## DW-I5-1 — 10.6 also finalized on a spent review budget (LOW) — DEFERRED

- source_spec: `spec-10-6-make-run-admission-real-or-stop-claiming-it.md` (Epic 10 / Story I5, AUD-ATLAS-046 / DW-AD23-1)
  origin: review-budget-followup (bmad-loop run `20260729-112237-3139`)
  summary: Identical shape to `DW-I4-1`, and that repetition is the finding. The story
    finalized `done` with gates green (kedro-test 901 passed, kedro-catalog-check 47) while
    the review pass was STILL recommending an independent follow-up and
    `limits.max_followup_reviews = 1` was spent. Two consecutive stories have now closed on
    a BUDGET CAP rather than on reviewer convergence — so the cap, not the reviewer, is
    deciding when atlas stories are done. D1-D6 were independently verified in the shipped
    code afterwards (filelock per output dataset in sorted order; `tryfirst` hook in
    settings.HOOKS releasing on both after_pipeline_run and on_pipeline_error;
    `RunAdmissionRejected` carrying holder_run_id + held_since; PID-based stale reclamation;
    AD-23 re-promoted WITH four stated boundaries), which is why this is LOW.
  resolution: (a) one independent fresh-context review of `admission.py` + `test_admission.py`
    against D1-D6; and (b) treat the repeat as a POLICY question for the retro — per the
    loop policy's own A4 rule, a deferral appearing a second time in a different story stops
    being story-level and becomes contract-level. Either raise `max_followup_reviews` or
    record that finalizing on a spent cap is accepted, deliberately.
  status: review PERFORMED 2026-07-29 — part (a) done, part (b) still open.
    The owed independent pass ran as adversarial MUTATION testing rather than a re-read:
    cross-process exclusion removed, stale-PID reclamation disabled, and the true
    acquisition order reversed were each injected into `admission.py` and each was CAUGHT
    by the suite (the two-process gate is NOT vacuous). One finding: `DW-AD23-3`. Caveat
    on record — the reviewer was not context-free, which is the whole point of an
    independent pass, so mutation evidence was used in place of a fresh reading.
    Part (b), the max_followup_reviews POLICY question, is untouched and belongs to the retro.
  promoted: 2026-07-29 from the gitignored Tier-3 `deferred-work.md` (recorded there as the
    generic `DW-2`); renamed to match this ledger's `DW-<story>-<n>` convention.

## DW-AD23-3 — the lock store's DEFAULT location is the hazardous one (MEDIUM) — CLOSED

- source_spec: `spec-10-6-make-run-admission-real-or-stop-claiming-it.md` (Story I5, D1/D4)
  found_by: independent follow-up review of `admission.py`, 2026-07-29 (the pass `DW-I5-1` owed)
  summary: `admission.py` documents this itself, honestly, and then ships the unsafe default.
    The lock root resolves to `<data_root>/.locks`, i.e. INSIDE the tree the locks guard.
    `rm -rf data/` is a routine "force a rebuild" move, and deleting a lock file out from
    under a live holder does NOT free that holder's flock — it unlinks the inode the flock
    belongs to, so the next acquirer creates a FRESH file at the same path, flocks that, and
    **two writers proceed**. That is a direct violation of the AD-23 invariant this very story
    re-promoted, reachable by an ordinary operator action, with no guard and no test.
    The escape hatch exists (`PYFORGE_ATLAS_LOCK_ROOT` pointed outside the data tree) but the
    DEFAULT is the configuration that can break, and the only warning lives in a module
    docstring. The other three declared boundaries are correctly classified as AVAILABILITY
    limits (locks held to process exit → later runs are REJECTED, never admitted alongside);
    this one is the sole CORRECTNESS exposure among them.
  resolution: move the default lock root OUTSIDE `data_root` (a project-anchored sibling, not
    a child of the tree being cleared) so the safe configuration is the one you get by doing
    nothing; keep `PYFORGE_ATLAS_LOCK_ROOT` as the override. Add a regression test that
    unlinks a held lock file mid-hold and asserts a second acquirer is still refused. If the
    default is kept deliberately, the warning belongs somewhere an operator will actually read
    it (the pixi task, or a refusal when the lock root is a descendant of data_root), not only
    in a docstring.
  status: CLOSED 2026-07-30. Both branches of the resolution were taken, because the first
    alone leaves the defect reachable through the override door — the same reasoning that made
    a relative `lock_root=` a refusal rather than a warning.
    (1) **The default store is now the data tree's SIBLING**, `<data_root>.locks`, not its
    child `<data_root>/.locks`. `rm -rf data/` can no longer reach it, so the safe placement
    is the one an operator gets by doing nothing. It stays DERIVED FROM the data root rather
    than pinned to the project (`<project>/.locks` was considered and rejected): two checkouts
    sharing one `PYFORGE_ATLAS_DATA_ROOT` write the same Parquet and must contend, and a
    project-pinned store would have given them one store each — the same silent voiding of
    admission that CWD-anchoring caused, through a different door. Pinned by
    `test_one_shared_data_root_yields_one_store_across_two_project_roots`.
    (2) **`PYFORGE_ATLAS_LOCK_ROOT` is REFUSED when it resolves inside the data root**
    (`AdmissionConfigError`, raised before any lock is taken). Its `<value>/.locks` child
    placement is otherwise unchanged — the operator named that directory. The check is
    advisory-if-unresolvable by necessity: an installed layout with no `conf/base/catalog.yml`
    is exactly the case an absolute `PYFORGE_ATLAS_LOCK_ROOT` exists to serve, so a data root
    that cannot be resolved must not turn that escape hatch back off
    (`_data_root_if_resolvable`).
    What this does NOT fix, stated so it is not mistaken for closed: unlinking a lock file
    out from under its holder still admits a second writer. That is a property of `flock` —
    the lock belongs to the inode — and no placement can prevent it. The fix removes the
    ROUTINE way to trigger it, nothing more. Pinned as a characterization test
    (`test_unlinking_the_lock_file_itself_still_admits_a_second_writer`) so a future change
    claiming to have fixed it has to red that test first.
    Tests: 5 new functions / 8 cases in `tests/test_admission.py` under the `DW-AD23-3`
    section, including the operator-action regression the resolution asked for
    (`test_clearing_the_data_tree_leaves_a_held_lock_still_excluding` — acquire at the shipped
    default, `shutil.rmtree` the data root, assert a second acquirer is still refused). Nine
    existing `default_lock_root` expectations were restated for the sibling path; none were
    weakened. The member `.gitignore` gains `data.locks/`, since the `data/**` rule no longer
    covers the store. Gate: `kedro-test` **911 passed / 19 skipped** (was 903/19 — +8, exactly
    the new cases); `kedro-catalog-check` 47; `dagster-dryrun` 58.

## 24. Sprint status

> **Tier:** Tier 3 · **Source:** `_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml`

```yaml
# generated: 2026-07-17T02:37:36Z
# last_updated: 2026-07-17T15:10:00Z
# project: pyforge-atlas (BMAD project under local-recipes)
# project_key: NOKEY
# tracking_system: file-system
# story_location: _bmad-output/implementation-artifacts
#
# Source epics: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
#   (9 epics = spec § 9 waves 0 + A-H; 32 frozen-ID stories; epics.md D-2: spec IDs are
#   the primary story keys — the Epic.Story alias is informational only.)
# Binding spec: docs/specs/cfe-atlas-datapipeline-kedro-migration.md (v5.6 — §§ 2.5, 9, 11, 14)
# Regenerate: re-run the bmad-sprint-planning skill for project pyforge-atlas
#   (after scripts/bmad-switch pyforge-atlas).
#
# UNATTENDED-RUN ASSUMPTIONS (recorded inline, 2026-07-17):
#   A-1: No pre-existing sprint-status.yaml and no story files in implementation-artifacts,
#        so all epics/stories initialize at backlog; nothing to preserve or upgrade.
#   A-2: Story keys = kebab-case of "<spec-id>-<title>" (D-2). bmad-create-story must name
#        story files "<story-key>.md" for auto-detection to upgrade status to ready-for-dev.
#   A-3: pixi unavailable in this environment — the verify-gate tasks referenced in story_meta
#        (kedro-test, kedro-catalog-check, parity-diff, dagster-dryrun, bsl-metric-check,
#        wasm-smoke, test-all, llms-full-check) are ENVIRONMENT-DEFERRED here: they are carried
#        as feed metadata only; execution belongs to the dev/loop sessions. Most gates do not
#        exist yet — they are built by the stories flagged builds_gate below.
#   A-4: F4 carried at LOOP-S per epics.md D-6 [ASSUMPTION]; if the § 13.4 drivability map
#        names a different 11th spec-approval story, update story_meta and re-note here.
#   A-5: Mode totals per epics.md D-7: 6 ATTENDED / 4 DEV-AUTO / 11 LOOP-S / 11 LOOP-E
#        (22 loop-drivable, within § 2.5 "~21" tolerance).
#
# STATUS DEFINITIONS:
# ==================
# Epic Status:
#   - backlog: Epic not yet started
#   - in-progress: Epic actively being worked on
#   - done: All stories in epic completed
#
# Epic Status Transitions:
#   - backlog → in-progress: Automatically when first story is created (via create-story)
#   - in-progress → done: Manually when all stories reach 'done' status
#
# Story Status:
#   - backlog: Story only exists in epic file
#   - ready-for-dev: Story file created in stories folder
#   - in-progress: Developer actively working on implementation
#   - review: Ready for code review (via Dev's code-review workflow)
#   - done: Story completed
#
# Retrospective Status:
#   - optional: Can be completed but not required
#   - done: Retrospective has been completed
#
# Action Item Status:
#   - open: Committed during a retrospective, not yet addressed
#   - in-progress: Actively being worked on
#   - done: Completed
#
# WORKFLOW NOTES:
# ===============
# - Epic transitions to 'in-progress' automatically when first story is created
# - Stories can be worked in parallel if team capacity allows — BUT this effort's loop
#   execution is sequential (max_parallel = 1, NFR-12); honor story_meta.depends_on
# - Developer typically creates next story after previous one is 'done' to incorporate learnings
# - Dev moves story to 'review', then runs code-review (fresh context, different LLM recommended)
# - Retrospective appends its action items to action_items; sprint-status surfaces open ones
# - Wave order is the delivery order: Epic 1 (W0) → 2 (A) → 3 (B) → 4 (C) → 5 (D) → 6 (E)
#   → 7 (F) → 8 (G) → 9 (H); each wave ends standalone-valuable with its own gate + PR (§ 14)
# - ATTENDED stories are wave-boundary events — never loop-driven; Q-gates in
#   story_meta.q_gate must be drained BEFORE the story starts (§ 11 defaults adopted, D-5)
# - Effort closeout: CFE Rule-2 retrospective (CLAUDE.md) after epic-9-retrospective

generated: 2026-07-17T02:37:36Z
last_updated: 2026-07-18T00:00:00Z
project: pyforge-atlas
project_key: NOKEY
tracking_system: file-system
story_location: _bmad-output/implementation-artifacts

development_status:
  # ---- Epic 1 / Wave 0 — Legacy Translation via Skill Forge ----
  epic-1: done  # story 0.1 signed off 2026-07-17 (attended) — Wave 0 complete
  0-1-generate-legacy-contextual-skill: done  # attended sign-off 2026-07-17; artifact .claude/skills/cf-atlas-legacy@8.78.0 (commit 6658049)
  epic-1-retrospective: optional

  # ---- Epic 2 / Wave A — nebi Scaffold & Catalog ----
  epic-2: done  # Wave A complete 2026-07-17 (A1+A2+A3 signed off)
  a1-scaffold-the-kedro-pixi-project-via-nebi: done  # closed 2026-07-17 (owner); commit 188c6ef; lean-env re-lock = workstation TODO (deferred-work.md)
  a2-define-the-data-catalog-for-all-sources-outputs: done  # closed 2026-07-17 (owner); commits ba62959+8d180a5; lean-env re-lock = workstation TODO
  a3-implement-incrementalparquetdataset-for-ttl-gating: done  # closed 2026-07-17 (owner); commit 744492e; Wave A complete; worktree-smoke + lean-env re-lock = workstation TODO
  epic-2-retrospective: optional

  # ---- Epic 3 / Wave B — Pipeline Node Porting & MCP Integration ----
  # § 14 order: B1/B2 → B3 → B4 (parity, attended) → B5 (Q6 first) → B6 → B7
  # → B8 (Q7 first) → B9 → B10. B8/B9/B10 additive — NOT parity-gated (AD-14).
  # Autonomous run 2026-07-18 (user mandate "finish Wave D without stopping"): B3→D3
  # orchestrator-verified + self-merged. Each story: draft/impl agent → 2 in-loop
  # adversarial reviewers → an INDEPENDENT fresh-eyes review → closer verification →
  # commit → PR → self-merge → branch restart. PRs #76–#88.
  epic-3: done  # Wave B complete 2026-07-18 (B1–B10 all merged)
  b1-port-the-conda-side-backbone-phases-into-kedro-nodes: done  # closed 2026-07-17 (owner); commits c90a44e+8878ba4; parity-diff harness begun (B4 consumes); 3 mediums -> DW-B1-1/2/3
  b2-port-the-pypi-and-vulnerability-pipelines: done  # closed 2026-07-17 (owner); commits 2bee4cb+121b8e6; independent review SOUND; 5 defers -> DW-B2-1..5
  b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools: done  # autonomous run 2026-07-17; orchestrator-verified + self-merged (PR #76; read_dataset JSON-coercion HIGH fixed)
  b4-verify-dataset-parity-against-the-legacy-orchestrator: done  # PR #77; BUILD-NOW gated green; credentialed run + sign-off DEFERRED (DW-B4-*)
  b5-port-the-external-refresh-assets: done  # PR #78; 3 refresh assets single-writer + AD-13 keep-last-good; UnicodeDecodeError HIGH fixed (independent review); Dagster injection DEFERRED (DW-B5-2)
  b6-port-the-seed-gaps-pipeline: done  # PR #79; 4 read-only gap suggesters, byte-identical seeds
  b7-extend-the-universal-sbom-intake: done  # PR #80; resolver + §4.10 SbomIntakeDataset + universe BOM + six-bucket; _REQ_RE extras HIGH fixed (independent review); DW-B7-1/2/3
  b8-basilisk-conda-native-vulnerability-ingestion: done  # PR #81; 2 Basilisk nodes (AD-2/AD-13) + tri-state fix_available + match-by-name; AD-14 rename ->_advisories (EXCLUDED len==3); Q7=Kedro-nodes; AD-13 _persist serialize-fail MED fixed (independent review); DW-B8-1/2/3
  b9-release-to-availability-velocity-columns: done  # PR #82; release_lag_hours/_qualifies on vcs_health (AD-3); first-avail=MIN repodata ts (never latest_conda_upload) + 90d gate; malformed-ts qualifies=False + typed-empty fixed (Edge Case Hunter)
  b10-migration-readiness-datasets-classification-node: done  # PR #83; conda-forge-bot-data status/ datasets (partitioned, zero-code-change) + 4-way readiness split; not-in-tracker=inferred; version_status.v2.json excluded; conda_noarch derived from subdirs; inferred-label test hardened (F1)
  epic-3-retrospective: optional

  # ---- Epic 4 / Wave C — Orchestration & Visualization ----
  epic-4: done  # Wave C complete 2026-07-18
  c1-integrate-kedro-dagster-for-scheduling-execution: done  # PR #84; kedro-dagster glue + dagster-dryrun gate (per-op timeouts retire the 1800s monolith, Phase-P admin-only, cadence schedules, profiles). ATTENDED live bring-up DEFERRED (DW-C1-1/-2). AD-1 kedro_mcp-in-glue + fragile _hook_ infix fixed (reviewers)
  c2-integrate-kedro-viz-expose-a-pixi-task: done  # PR #85; `pixi run viz` + offline viz-loadable smoke (load_data: 8 pipelines/40 nodes/114 datasets); AD-1 kedro_viz test-only
  epic-4-retrospective: optional

  # ---- Epic 5 / Wave D — Semantic Layer & Dashboards ----
  epic-5: done  # Wave D complete 2026-07-18 — the autonomous mandate's finish line
  d1-define-the-boring-semantic-layer-bsl-models: done  # PR #86; BSL metrics as pure Ibis->DuckDB (AD-4) + maintainer ⋈ first-class (AC-2) + bsl-metric-check (independent legacy-formula anchors, DW-B1-1 trap excluded); 3 coverage NITs applied
  d2-build-the-vizro-dashboard-port-the-28-clis-to-pages: done  # PR #87; BSL-driven Vizro app (AD-8) + live-confirmed-first pages + factory-status (AD-17 stamp); full 28-page inventory CIS-two-spine DEFERRED (DW-D2); S1 (no fabricated "None" status) + S2 (untyped-Parquet degrade) fixed
  d3-integrate-vizro-ai-expose-the-nl-interface-as-an-mcp-tool: done  # PR #88; query_vizro_ai MCP tool (AD-7-thin) + backend routed through repo model-backend env config (Q3, never a hardcoded endpoint); live LLM backend DEFERRED (DW-D3); scheme-only-URL false-configured receipt fixed (Reviewer-B)
  epic-5-retrospective: optional

  # ---- Epic 6 / Wave E — A2A, Lineage & Observability (no new named gate, D-8) ----
  epic-6: backlog
  e1-implement-the-a2a-communication-interfaces: backlog
  e2-integrate-openlineage-opentelemetry: backlog
  epic-6-retrospective: optional

  # ---- Epic 7 / Wave F — The DuckDB Singularity ----
  epic-7: backlog
  f1-complete-the-duckdb-consolidation-prove-the-cold-start-claim: backlog
  f2-implement-the-data-validation-hook-and-inline-pandera-contracts: backlog
  f3-implement-vector-similarity-search-rag-via-duckdb-vss: backlog
  f4-dependency-hygiene-node-unified-ci-policy-gate: backlog
  epic-7-retrospective: optional

  # ---- Epic 8 / Wave G — WASM Portability & Sensors ----
  epic-8: done  # Wave G complete 2026-07-18 (PRs #96/#97/#98)
  g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm: done  # PR #96; real DuckDB-WASM offline smoke, loopback-only gate
  g2-emit-parquet-artifacts-to-a-static-web-host: done  # PR #97; host-agnostic chunked-Parquet emitter + manifest, path-traversal guard; live publish DEFERRED (DW-G2)
  g3-implement-dagster-sensors-for-near-real-time-ingestion: done  # PR #98; 2 sensors → existing incremental jobs (AD-23/AD-5), dagster-free event source; live daemon DEFERRED (DW-G3)
  epic-8-retrospective: optional

  # ---- Epic 9 / Wave H — AI Software Factory & Karpathy Wiki ----
  epic-9: in-progress
  h1-scaffold-the-karpathy-wiki-folder-structure-and-agent-personas: done  # PR #99; factory/ package: single-owner wiki layout + AD-22 traversal guard, 5 personas + customization-layer resolution, offline storage resolver; MinIO server DEFERRED (DW-H1)
  h2-implement-agno-compilation-linting-and-qa-crews: done  # PR pending; factory/crews.py compile/lint/Q&A crews, offline-first, staleness propagation (AD-13/AD-22); agno/LLM + F3-vss retriever DEFERRED (DW-H2); independent review MUST-FIX x2 (inline-staleness laundering, crash-on-malformed) + SHOULD-FIX x1 fixed
  h3-integrate-la-suite-docs-rest-api-sync: done  # PR pending; factory/lasuite.py LaSuiteClient + WikiSyncer, content-digest idempotency (unchanged re-push = 0 remote calls), injected transport (no HTTP client in pkg — AC-2), AD-22-safe mapping sidecar; live Wagtail server + httpx opener DEFERRED (DW-H3)
  h4-orchestrate-crews-via-dagster: done  # PR pending; crew assets (compiled_wiki/wiki_lint_report) + wiki_compile/lint asset-jobs + weekly wiki_lint_schedule + new-raw-file wiki_raw_file_sensor, all on C1's single Dagster plane (AD-6/AD-23); dagster-free wiki_events.py (AD-1); dagster definitions validate green; live daemon DEFERRED (DW-H4)
  epic-9-retrospective: required  # CFE Rule-2 retro — effort closeout (Wave H touched recipes/-adjacent tooling)

# ============================================================================
# story_meta — loop/dev-auto consumption feed (additive; bmad-sprint-status
# readers that only understand development_status can ignore this section).
# Fields per story:
#   spec_id      — frozen spec § 9 ID (primary key, epics.md D-2)
#   epic / wave  — epic number and spec wave letter
#   mode         — ATTENDED | DEV-AUTO | LOOP-S | LOOP-E (spec § 2.5)
#   verify_gate  — gate(s) the story must pass; "builds:" = the story creates
#                  that gate as a deliverable; "consumes:" = pre-existing gate
#   q_gate       — open question that must be drained BEFORE the story runs
#                  (§ 11 default already adopted per epics.md D-5)
#   depends_on   — story keys that must be done first (§ 14 edges)
#   notes        — execution flags (keystone budget raises, attended events,
#                  additive/not-parity-gated, etc.)
# ============================================================================
story_meta:
  0-1-generate-legacy-contextual-skill:
    spec_id: "0.1"
    epic: 1
    wave: "0"
    mode: ATTENDED
    verify_gate: "none (pre-harness; acceptance = queryable SKF skill artifact)"
    q_gate: null
    depends_on: []
    notes: >-
      First story of the effort. Wave-0 preconditions run alongside: one-time
      hooks approval, live bmad-groundtruth re-check, worktree symlink
      bootstrap, heaviest-story budget review (AD-18). Re-check conditional
      Phase T (trendshift Track A) at execution start (D-15).

  a1-scaffold-the-kedro-pixi-project-via-nebi:
    spec_id: A1
    epic: 2
    wave: A
    mode: DEV-AUTO
    verify_gate: "builds: kedro-test"
    q_gate: null
    depends_on: [0-1-generate-legacy-contextual-skill]
    notes: >-
      nebi scaffold; physical naming resolves in this story's spec (Spine
      Deferred). llms-full-check must pass after dependency changes
      (environment-deferred here — pixi unavailable in the planning session).

  a2-define-the-data-catalog-for-all-sources-outputs:
    spec_id: A2
    epic: 2
    wave: A
    mode: DEV-AUTO
    verify_gate: "builds: kedro-catalog-check (incl. AD-1 import-direction meta-test)"
    q_gate: null
    depends_on: [a1-scaffold-the-kedro-pixi-project-via-nebi]
    notes: "Per-host credential scoping; all 20 resolve_*_urls override points survive."

  a3-implement-incrementalparquetdataset-for-ttl-gating:
    spec_id: A3
    epic: 2
    wave: A
    mode: LOOP-S
    verify_gate: "consumes: kedro-test"
    q_gate: null
    depends_on: [a1-scaffold-the-kedro-pixi-project-via-nebi, a2-define-the-data-catalog-for-all-sources-outputs]
    notes: >-
      Designated FIRST loop-driven story and worktree smoke (§ 2.5); validates
      the symlink bootstrap and measures worktree env-materialization cost.

  b1-port-the-conda-side-backbone-phases-into-kedro-nodes:
    spec_id: B1
    epic: 3
    wave: B
    mode: LOOP-S
    verify_gate: "consumes: kedro-test; builds: parity-diff (begins, B1-B3)"
    q_gate: null
    depends_on: [a1-scaffold-the-kedro-pixi-project-via-nebi, a2-define-the-data-catalog-for-all-sources-outputs, a3-implement-incrementalparquetdataset-for-ttl-gating]
    notes: "KEYSTONE — pre-flight budget raise (AD-18). TEA atdd red-phase fixtures."

  b2-port-the-pypi-and-vulnerability-pipelines:
    spec_id: B2
    epic: 3
    wave: B
    mode: LOOP-S
    verify_gate: "consumes: kedro-test; builds: parity-diff (building)"
    q_gate: null
    depends_on: [b1-port-the-conda-side-backbone-phases-into-kedro-nodes]
    notes: "KEYSTONE — pre-flight budget raise (AD-18)."

  b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools:
    spec_id: B3
    epic: 3
    wave: B
    mode: LOOP-S
    verify_gate: "consumes: kedro-test; builds: parity-diff (build completes at B3)"
    q_gate: null
    depends_on: [b1-port-the-conda-side-backbone-phases-into-kedro-nodes, b2-port-the-pypi-and-vulnerability-pipelines]
    notes: "kedro-mcp never load-bearing (AD-1); MCP bodies passthrough-only (AD-7)."

  b4-verify-dataset-parity-against-the-legacy-orchestrator:
    spec_id: B4
    epic: 3
    wave: B
    mode: ATTENDED
    verify_gate: "consumes: parity-diff (fixture mode in-loop; credentialed full run at the event)"
    q_gate: "Q1 — parity tolerance (default adopted: exact row-count + value parity on v_actionable_packages-family views; benign diffs documented). Drained at the B4 event."
    depends_on: [b1-port-the-conda-side-backbone-phases-into-kedro-nodes, b2-port-the-pypi-and-vulnerability-pipelines, b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools]
    notes: >-
      Attended parity boundary event; credentialed runs attended-only (AD-11).
      Human sign-off gates legacy-orchestrator retirement (AD-19). Compares
      legacy-surface outputs only — B8/B9/B10 out of parity scope (AD-14).

  b5-port-the-external-refresh-assets:
    spec_id: B5
    epic: 3
    wave: B
    mode: LOOP-S
    verify_gate: "consumes: kedro-test (+ dagster-dryrun once C1 exists; schedule assertions as fixtures here)"
    q_gate: "Q6 — mapping-source consolidation (default adopted: consolidate on migrated Phase C). MUST be recorded BEFORE this story's mapping-asset work."
    depends_on: [b4-verify-dataset-parity-against-the-legacy-orchestrator]
    notes: "§ 14 position after B4; substance depends only on B1/B2 + Q6 (D-10)."

  b6-port-the-seed-gaps-pipeline:
    spec_id: B6
    epic: 3
    wave: B
    mode: LOOP-S
    verify_gate: "consumes: kedro-test (byte-identical-seed fixture + report-node fixtures)"
    q_gate: null
    depends_on: [b5-port-the-external-refresh-assets]
    notes: "Read-only report nodes (AD-15); mapping-gap stays in PyPI Intelligence pipeline."

  b7-extend-the-universal-sbom-intake:
    spec_id: B7
    epic: 3
    wave: B
    mode: LOOP-S
    verify_gate: "consumes: kedro-test (format fixtures, six-bucket fixture, NBSP fixture)"
    q_gate: null
    depends_on: [b6-port-the-seed-gaps-pipeline]
    notes: "cfe:* namespace + ?channel=conda-forge qualifier never stripped (AD-10)."

  b8-basilisk-conda-native-vulnerability-ingestion:
    spec_id: B8
    epic: 3
    wave: B
    mode: LOOP-S
    verify_gate: "consumes: kedro-test (three binding-constraint fixtures + offline-skip fixture)"
    q_gate: "Q7 — Basilisk landing point (default adopted: build once as Kedro nodes in Wave B). Recorded BEFORE implementation."
    depends_on: [b2-port-the-pypi-and-vulnerability-pipelines]
    notes: "ADDITIVE rider — NOT gated on B4 parity (AD-14)."

  b9-release-to-availability-velocity-columns:
    spec_id: B9
    epic: 3
    wave: B
    mode: LOOP-S
    verify_gate: "consumes: kedro-test (both failure-mode fixtures)"
    q_gate: null
    depends_on: [b2-port-the-pypi-and-vulnerability-pipelines]
    notes: "ADDITIVE — NOT parity-gated (AD-14); never latest_conda_upload."

  b10-migration-readiness-datasets-classification-node:
    spec_id: B10
    epic: 3
    wave: B
    mode: LOOP-S
    verify_gate: "consumes: kedro-test (zero-code-change partitioning fixture + inferred-label fixture)"
    q_gate: null
    depends_on: [b1-port-the-conda-side-backbone-phases-into-kedro-nodes, b2-port-the-pypi-and-vulnerability-pipelines]
    notes: "ADDITIVE — NOT parity-gated (AD-14)."

  c1-integrate-kedro-dagster-for-scheduling-execution:
    spec_id: C1
    epic: 4
    wave: C
    mode: ATTENDED
    verify_gate: "builds: dagster-dryrun"
    q_gate: "Q2 — Dagster footprint/acquisition health (default adopted: on-demand/scheduled local, no persistent daemon). Re-verified at wave start."
    depends_on: [b10-migration-readiness-datasets-classification-node]  # Epic 3 complete (all B stories done)
    notes: >-
      Attended bring-up boundary event (D-9); the dagster-dryrun gate it ships
      is loop-consumable thereafter. Phase P stays admin-config-only (AD-6).

  c2-integrate-kedro-viz-expose-a-pixi-task:
    spec_id: C2
    epic: 4
    wave: C
    mode: LOOP-E
    verify_gate: "consumes: dagster-dryrun + kedro-test"
    q_gate: null
    depends_on: [c1-integrate-kedro-dagster-for-scheduling-execution]
    notes: "Q2 drained at C1."

  d1-define-the-boring-semantic-layer-bsl-models:
    spec_id: D1
    epic: 5
    wave: D
    mode: LOOP-E
    verify_gate: "builds: bsl-metric-check (metric-parity fixtures vs legacy CLI outputs)"
    q_gate: null
    depends_on: [c2-integrate-kedro-viz-expose-a-pixi-task, b4-verify-dataset-parity-against-the-legacy-orchestrator]  # Epic 4 complete + canonical Parquet store
    notes: "Ibis → DuckDB only (AD-8/AD-4)."

  d2-build-the-vizro-dashboard-port-the-28-clis-to-pages:
    spec_id: D2
    epic: 5
    wave: D
    mode: DEV-AUTO
    verify_gate: "consumes: bsl-metric-check + kedro-test"
    q_gate: null
    depends_on: [d1-define-the-boring-semantic-layer-bsl-models]
    notes: >-
      PRECONDITION: CIS two-spine specs (DESIGN.md + EXPERIENCE.md) before
      frontend work (§ 2.4, D-11). Visual judgment → DEV-AUTO (§ 9 preamble).
      Agent-legibility bar NFR-8.

  d3-integrate-vizro-ai-expose-the-nl-interface-as-an-mcp-tool:
    spec_id: D3
    epic: 5
    wave: D
    mode: ATTENDED
    verify_gate: "consumes: bsl-metric-check (NL path verified at the attended event)"
    q_gate: "Q3 — Vizro-AI LLM backend (default adopted: repo model-backend routing; no hardcoded endpoint; no litellm; llama.cpp/ollama/mlx-lm in-env). Drained at the D3 event."
    depends_on: [d1-define-the-boring-semantic-layer-bsl-models, d2-build-the-vizro-dashboard-port-the-28-clis-to-pages]
    notes: "Attended backend boundary event."

  e1-implement-the-a2a-communication-interfaces:
    spec_id: E1
    epic: 6
    wave: E
    mode: LOOP-E
    verify_gate: "consumes: existing gates + payload round-trip fixture in kedro-test"
    q_gate: null
    depends_on: [b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools, d3-integrate-vizro-ai-expose-the-nl-interface-as-an-mcp-tool]  # MCP surface + Epic 5 complete
    notes: "A2A transport resolves in this story's spec (Spine Deferred), not a Q-gate. Wave E has no new named gate (D-8)."

  e2-integrate-openlineage-opentelemetry:
    spec_id: E2
    epic: 6
    wave: E
    mode: LOOP-E
    verify_gate: "consumes: existing gates + emitted-event/span fixtures in kedro-test"
    q_gate: null
    depends_on: [c1-integrate-kedro-dagster-for-scheduling-execution, e1-implement-the-a2a-communication-interfaces]
    notes: "Hooks declared in run config — every entry point inherits (AD-23)."

  f1-complete-the-duckdb-consolidation-prove-the-cold-start-claim:
    spec_id: F1
    epic: 7
    wave: F
    mode: ATTENDED
    verify_gate: "consumes: grep gate (no sqlite3 outside retired legacy tree) + kedro-test; benchmark evidence at the event; wave-boundary test-all"
    q_gate: null
    depends_on: [b4-verify-dataset-parity-against-the-legacy-orchestrator, e2-integrate-openlineage-opentelemetry]  # retirement decided + Epics 4-6 complete
    notes: >-
      KEYSTONE — pre-flight budget raise + dev_stall_grace_s raise (AD-18).
      Attended benchmark boundary event; pass threshold fixed in the story
      spec BEFORE the benchmark runs (SM-3); do not chase cold-start (SM-C1).

  f2-implement-the-data-validation-hook-and-inline-pandera-contracts:
    spec_id: F2
    epic: 7
    wave: F
    mode: LOOP-E
    verify_gate: "consumes: kedro-test (halt fixture + stub-validator fixture)"
    q_gate: null
    depends_on: [e1-implement-the-a2a-communication-interfaces, c1-integrate-kedro-dagster-for-scheduling-execution]
    notes: "GX capped 1.18.2; kedro-great-expectations/kedro-pandera plugins banned (AD-9)."

  f3-implement-vector-similarity-search-rag-via-duckdb-vss:
    spec_id: F3
    epic: 7
    wave: F
    mode: LOOP-E
    verify_gate: "consumes: kedro-test (ranked-results fixture)"
    q_gate: null
    depends_on: [f1-complete-the-duckdb-consolidation-prove-the-cold-start-claim]
    notes: "Embedding model + offline vss provisioning resolve in this story's spec (Spine Deferred; AD-13 tension must resolve)."

  f4-dependency-hygiene-node-unified-ci-policy-gate:
    spec_id: F4
    epic: 7
    wave: F
    mode: LOOP-S
    verify_gate: "consumes: kedro-test (schema fixtures + exit-code fixtures + not-applicable fixture)"
    q_gate: null
    depends_on: [b7-extend-the-universal-sbom-intake, f2-implement-the-data-validation-hook-and-inline-pandera-contracts]
    notes: >-
      LOOP-S per D-6 [ASSUMPTION] — 11th spec-approval slot (frozen exit-code
      flip + ComplianceReport single producer, AD-12); § 13.4 drivability map
      is the reconciliation authority. INVENTORY_MATCH_LEGACY_EXIT=1 one-release
      window. Schema matches pyforge-warden.md ComplianceReport.

  g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm:
    spec_id: G1
    epic: 8
    wave: G
    mode: LOOP-E
    verify_gate: "builds: wasm-smoke (Playwright headless load-and-query)"
    q_gate: null
    depends_on: [d2-build-the-vizro-dashboard-port-the-28-clis-to-pages, f1-complete-the-duckdb-consolidation-prove-the-cold-start-claim]
    notes: "CIS two-spine precondition applies to G1 frontend work (D-11)."

  g2-emit-parquet-artifacts-to-a-static-web-host:
    spec_id: G2
    epic: 8
    wave: G
    mode: ATTENDED
    verify_gate: "consumes: wasm-smoke (published artifact at the event; fixture-hosted in-loop)"
    q_gate: "Q4 — WASM artifact host (default adopted: GitHub Pages; host-agnostic emitter). Drained at the G2 event."
    depends_on: [g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm]
    notes: "Attended publish boundary event (D-9 pattern)."

  g3-implement-dagster-sensors-for-near-real-time-ingestion:
    spec_id: G3
    epic: 8
    wave: G
    mode: LOOP-E
    verify_gate: "consumes: dagster-dryrun (sensors enumerate) + simulated-event fixture in kedro-test"
    q_gate: "Q2 revisit condition only (daemon footprint — resolves here if sensors require it; not blocking)."
    depends_on: [c1-integrate-kedro-dagster-for-scheduling-execution, g2-emit-parquet-artifacts-to-a-static-web-host]
    notes: "Event-source choice (webhooks vs RSS) resolves in this story's spec (Spine Deferred)."

  h1-scaffold-the-karpathy-wiki-folder-structure-and-agent-personas:
    spec_id: H1
    epic: 9
    wave: H
    mode: LOOP-E
    verify_gate: "consumes: kedro-test (scaffold-layout test + persona-resolution test)"
    q_gate: null
    depends_on: [g3-implement-dagster-sensors-for-near-real-time-ingestion]  # Epic 8 complete (wave order)
    notes: "MinIO server provisioning resolved as this story's precondition (Spine Deferred). Factory layer writes only wiki/CMS (AD-22)."

  h2-implement-agno-compilation-linting-and-qa-crews:
    spec_id: H2
    epic: 9
    wave: H
    mode: DEV-AUTO
    verify_gate: "consumes: kedro-test (crews-on-fixture-wiki tests)"
    q_gate: null
    depends_on: [h1-scaffold-the-karpathy-wiki-folder-structure-and-agent-personas]
    notes: "Spec-explicit DEV-AUTO (crew design needs judgment). Staleness markers carried forward (AD-13/AD-22)."

  h3-integrate-la-suite-docs-rest-api-sync:
    spec_id: H3
    epic: 9
    wave: H
    mode: LOOP-E
    verify_gate: "consumes: kedro-test (mock-Wagtail round-trip fixture: push, update, idempotent re-push)"
    q_gate: null
    depends_on: [h1-scaffold-the-karpathy-wiki-folder-structure-and-agent-personas, h2-implement-agno-compilation-linting-and-qa-crews]
    notes: null

  h4-orchestrate-crews-via-dagster:
    spec_id: H4
    epic: 9
    wave: H
    mode: LOOP-E
    verify_gate: "consumes: dagster-dryrun (crew assets enumerate) + simulated-trigger fixture"
    q_gate: null
    depends_on: [h1-scaffold-the-karpathy-wiki-folder-structure-and-agent-personas, h2-implement-agno-compilation-linting-and-qa-crews, h3-integrate-la-suite-docs-rest-api-sync, c1-integrate-kedro-dagster-for-scheduling-execution]
    notes: >-
      Final story. After epic-9 closes, run the CFE Rule-2 retrospective
      (CLAUDE.md — effort closeout requirement, AD-18 execution seam).
```

---

## Appendix — process artifacts (not inlined)

PRD/architecture review, validation, rubric, and `.memlog` files — process
evidence rather than specs. Listed here with paths; read them in place.

| Artifact | Path | Bytes |
|---|---|---|
| validation-report.md | `_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/validation-report.md` | 7,463 |
| review-adversarial-general.md | `_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/review-adversarial-general.md` | 16,429 |
| review-rubric.md | `_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/review-rubric.md` | 14,981 |
| .memlog.md | `_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/.memlog.md` | 2,878 |
| reconcile-inputs.md | `_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/reviews/reconcile-inputs.md` | 11,980 |
| review-adversarial-two-units.md | `_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/reviews/review-adversarial-two-units.md` | 22,683 |
| review-rubric-walker.md | `_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/reviews/review-rubric-walker.md` | 19,720 |
| review-version-verification.md | `_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/reviews/review-version-verification.md` | 14,668 |
| .memlog.md | `_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/.memlog.md` | 10,262 |

Also excluded: `forge-data/` (Skill-Forge outputs for the `cf-atlas-legacy` contextual skill) under the implementation-artifacts dir.

