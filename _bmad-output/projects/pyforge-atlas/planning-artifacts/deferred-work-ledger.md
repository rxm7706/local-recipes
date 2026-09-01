---
doc_type: deferred-work-ledger
project: pyforge-atlas
date: 2026-07-29
status: restored
entries: 60
---

# pyforge-atlas — deferred-work ledger (RESTORED, tracked)

**All 52 real deferrals recorded during the Kedro migration, with full bodies — the
ledger is complete.** The run log's index of "54" double-counted two aliases; see
§ Provenance.

The frontmatter `entries` count is the number of `## DW-` headings in this file and so
runs ahead of that 52 as post-restore work lands: **57** today = the 52 restored + `DW-I4-1`
(promoted 2026-07-29 out of the gitignored Tier-3 ledger) + `DW-AD23-1` and `DW-AD23-2`
(Story 10.6, same date — the first *defining* an id that eight artifacts had been citing
with no entry behind it) + `DW-I5-1` (the 10.6 review-budget follow-up, promoted the same
day) + `DW-AD23-3` (the lock-store default, found by the pass `DW-I5-1` owed; closed
2026-07-30 by PR #140).

*(The count read `55` until 2026-07-30, when the verification campaign recounted the
headings and found 57 — the two Story-10.6 follow-ups had been added without re-stamping
it. Stale counts in a file that declares its own counting rule are exactly what the
campaign exists to catch.)*

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

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED — `bmad-drift-check` no longer reports the `surface-changed` finding this entry was raised for. A live run today ends 'OK: all tracked BMAD artifacts are in sync with the live factory MINOR', with only two INFO `pin-behind` notes (implementation-readiness-report and validation-report-PRD pinned v8.79.0 < live v8.81.0 — a different, non-blocking class). The doc re-sync and baseline re-stamp this entry owed were absorbed by later sync passes.
## DW-B1-1 — parity-diff harness under-checks (HIGH, B4 must resolve before it trusts parity)

Independent B1 follow-up review (2026-07-17) found two harness weaknesses that manufacture false confidence:
1. Fixtures are HAND-AUTHORED "legacy-shaped seeds", not captured from a real legacy run — so the suite proves port==implementer-belief, not port==legacy. B4 MUST recapture fixtures from an actual legacy orchestrator run before consuming parity as the retirement gate (AD-19).
2. harness.py frame-diff under-checks: (a) column set derived from EXPECTED only → a node growing a spurious column passes; (b) check_dtype=False → int64-vs-float64 passes. Tighten to column-set equality + dtype where JSON round-trip allows.
Owner: B4 (parity gate). The must-fix `downloads_source='merged'` bug this review found was itself endorsed by an unfixed fixture — proof the harness needs recapture.

  status: open

  verified: 2026-07-30 — PARTIALLY RESOLVED — part (b) is DONE, part (a) is untouched, so the entry stays open on (a). (b) FIXED: `tests/parity/harness.py:220-223` now carries the tightened diff and names this entry — 'B4 (DW-B1-1 part b): the TIGHTENED diff — column-SET equality both […] that let a spurious column or an int64->float64 regression pass silently'. (a) NOT fixed: every fixture still carries `"provenance": "shape-only-seed-B2-needs-B4-recapture"` (checked across `tests/parity/fixtures/pypi_intelligence/` and `vulnerability/`). So the harness now checks properly, but it still checks against hand-authored seeds — a green `parity-diff` is still NOT legacy parity, exactly as the entry warned.
## DW-B1-2 — RateLimitedScheduler not yet wired to the fetch path (MEDIUM, B2/live-fetch)

`_RequestParameterizedAPIDataset.load()` calls `self._inner.load()` but never `self.scheduler.acquire()` — the token bucket is real but enforced on nothing in B1 (fan-out is documented-deferred). Wire `acquire()` into the live request path when B2/live fetch lands. Also document the scheduler's fake-clock coupling (a frozen clock + no-op sleep makes acquire() infinite-spin) so a future fixture doesn't hang.

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED — the token bucket is now enforced on the real path. `datasets/request_datasets.py:109` and `:120` both call `self.scheduler.acquire()`, and `:54` records the fix in the past tense ('but ``load()`` never called ``self.scheduler.acquire()``'). The scheduler is constructed at `:91` with a real default (`RateLimitedScheduler(rps=rps)`), and `datasets/rate_limit.py:246` is the acquire implementation. The entry's core complaint — 'the token bucket is real but enforced on nothing' — no longer holds.
## DW-B1-3 — enumerate_conda_packages tie-break + B.5 inactive placeholder rows (LOW/MEDIUM, B4 parity)

(a) enumerate_conda_packages uses non-stable sort before groupby-last → arbitrary winner on duplicate-timestamp builds (latent parity risk vs legacy's defined tie-break). (b) Legacy phase_b5 also inserts inactive placeholder rows (relationship='conda_only', latest_status='inactive') for feedstock-outputs entries absent from repodata; the port's attribute_feedstocks omits them — changes downstream v_actionable population. Both are B4 parity-reconcile items.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN by its gate rather than by its code. Both halves are explicitly B4 parity-reconcile items, and B4's credentialed run has not happened (see DW-B4-1 / DW-B4-5, both still open, and `parity/evidence.py:51` `human_sign_off: str | None = None`). SCOPE LIMIT, stated rather than glossed: I could not locate an `enumerate_conda_packages` sort/groupby site to check the tie-break directly in `pipelines/core/nodes.py`, so the (a) half is verified as un-reconciled, not as un-fixed. The reconciliation itself provably has not run.
## DW-B2-1 — DAG-level persistence of operator notes edited on the SCORED output (MEDIUM, persistence boundary)

- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/b2-port-the-pypi-and-vulnerability-pipelines.md`
  summary: AC-5 notes-survive is satisfied at the enriched→scored carry (Phase S reads enriched) + the `apply_readiness_scores(prior_scored=…)` helper path (the add-handoff single-package re-score); a FULL-DAG merge of operator notes edited DIRECTLY on the persisted `pypi_intelligence_scored` output is not wired.
  evidence: `score_pypi_readiness` passes `prior_scored=None` and `pipeline.py` wires only `pypi_intelligence_enriched`; a notes-merging persistence boundary (custom dataset OR a prior-read alias) would satisfy the scored-output-edit case, but that exceeds B2's bounded catalog scope (Task 7: only the 2 FLIPs + conftest edit). Owner: the persistence-boundary story (B4/B5). Adversarial-review (Blind Hunter) 2026-07-17.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the seam is unchanged. `pipelines/pypi_intelligence/nodes.py:547` still signs `prior_scored: pd.DataFrame | None = None` (the single-package helper path), and `:562` guards on `prior_scored is not None`. No full-DAG notes-merging persistence boundary was wired, so an operator note edited directly on the persisted `pypi_intelligence_scored` output still does not survive.
## DW-B2-2 — coerce_cvss_score not on the B2 node data path until B5 wires the vdb boundary (LOW, B5)

- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/b2-port-the-pypi-and-vulnerability-pipelines.md`
  summary: `coerce_cvss_score` (AC-3(b)) is authored + boundary-tested in `datasets/vdb_boundary.py` but not invoked on the B2 node path — the vdb parse+coercion boundary is B5's; `summarize_vdb_vulns`/`per_version_vulns` run `pd.to_numeric(errors="coerce")`, so a raw pydantic `ScoreType` reaching a node before B5 would coerce to NaN (→ None) rather than unwrap.
  evidence: G-3 scoping (B2 consumes the interim vdb PATH; B5 lands the read-only VDB dataset class that parses+coerces). Acceptable under scope; note for B5 to wire `coerce_cvss_score` at its dataset boundary. Adversarial-review (Blind Hunter) 2026-07-17.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `coerce_cvss_score` exists and is exported (`datasets/vdb_boundary.py`, re-exported at `datasets/__init__.py:56` and listed in `__all__` at `:82`) but has ZERO occurrences anywhere under `pipelines/`, so it is still not on the B2 node data path. B5's vdb dataset boundary never wired it.
## DW-B2-3 — vuln_kev_affecting_current in the report-only rollup is package-wide, not version-scoped (LOW, report-only)

- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/b2-port-the-pypi-and-vulnerability-pipelines.md`
  summary: `summarize_vdb_vulns.vuln_kev_affecting_current` sums KEV over ALL vdb rows for a package; the name implies current-version scoping.
  evidence: the rollup is REPORT-ONLY (AC-2) and documented in code as such; the version-accurate KEV-affecting-current is `v_current_version_vulns` (backed by `per_version_vulns`). Low impact; verify against legacy CFA:3854 scoping at B4 parity. Adversarial-review (Blind Hunter) 2026-07-17.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `pipelines/vulnerability/nodes.py:200` still describes the rollup as 'in the KEV set (KEV-affecting, matching Phase G's ``vuln_kev_affecting_current``)', with the same package-wide framing at `:12`. No version scoping was added, and the legacy CFA:3854 comparison it needs is gated on the unrun credentialed parity run.
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

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the catalog routing is unchanged. `conf/base/catalog.yml:198-201` still resolves `pypi_bigquery_downloads_raw` to `type: api.APIDataset` against `${globals:extra_overrides.BIGQUERY_BASE_URL}/projects` with `credentials: bigquery_adc`. `BigQueryDownloadsDataset` — the two-layer cost gate — is still not the catalog target, so a credentialed Phase-P run would still fetch with no cost gate.
## DW-B2-5 — pypi_intelligence pipeline not end-to-end runnable unattended (by design, note-only)

`pypi_json_raw` → `PyPIJsonRequestDataset.load()` raises (directs to load_many, the
attended per-request fan-out — mirrors B1). A default SequentialRunner cannot execute
pypi_intelligence end-to-end; test_dag_resolves checks topology only. Intended for this
migration phase; the concrete DAG-load fan-out is a dataset-owned + attended concern.
No action needed — recorded so nobody expects an unattended full run to work yet.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN and still correct as a note-only entry. The attended per-request fan-out is unchanged, and the sibling deferrals it mirrors (DW-B5-2 refresher injection, DW-B7-2 resolver injection, DW-B8-1 fetcher injection) are all still open too, so no unattended end-to-end `pypi_intelligence` run is possible. No action was ever required.
## DW-B4-1 — the credentialed full parity run (ATTENDED, AD-19) — DEFERRED to the wave-boundary event

B4 built the credentialed-parity comparator (`tests/parity/parity_runner.py`), but the actual
run against a REAL operator `cf_atlas.db` cannot happen in-loop (no credentialed DB; AD-11
credentialed-runs-attended-only). At the event: supply the real `cf_atlas.db` + a
`kedro_frame_provider` that composes each legacy-surface view from its Parquet datasets
(the per-view composition — join keys + the actionable filter — is finalized against the real
schema then), run `run_parity(legacy_db=..., kedro_frame_provider=...)`, and record the
resulting `ParityEvidenceRecord`s per `PARITY_EVIDENCE_TEMPLATE.md`. Owner: B4 attended event.

  status: open

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. `parity/evidence.py:51` still declares `human_sign_off: str | None = None` and `:64` still gates `may_retire_legacy` on `bool(self.human_sign_off)`, so no credentialed evidence was ever recorded. The comparator (`tests/parity/parity_runner.py`) exists and is ready; the run against a real operator `cf_atlas.db` has not occurred.
## DW-B4-2 — human sign-off + marking legacy retirement (FR-4) — DEFERRED (human act)

`may_retire_legacy` returns `allowed=False` in-loop (correct — no credentialed, signed
evidence). Only after DW-B4-1's evidence is recorded AND a human signs (`human_sign_off` set)
does the gate open. The actual `phase_state` removal / `bootstrap-data` retirement (FR-4) is a
separate attended action gated on `allowed=True`. Do NOT mark retirement until then.

  status: open

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. `parity/evidence.py:64` still returns `bool(self.human_sign_off)` and `human_sign_off` still defaults to `None` at `:51` — nobody has signed, so `may_retire_legacy` still returns `allowed=False` and legacy is correctly not marked retired. Its precondition (DW-B4-1) is itself unmet.
## DW-B4-3 — fixture recapture from a real legacy run (DW-B1-1 part a) — tool SHIPPED, recapture DEFERRED

`tests/parity/capture_fixtures.py` is the recapture tool. At the event, back a
`LegacyCaptureSource` with the credentialed `cf_atlas.db` and run `capture_legacy_fixtures`
to replace the B1/B2 shape-only seeds (stamped `credentialed-legacy-capture-<date>`). Until
then the seeds stay flagged `shape-only-seed-...` and a green `parity-diff` is NOT legacy parity.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the recapture never ran. The tool (`tests/parity/capture_fixtures.py`) is present, but every fixture still carries the pre-recapture stamp `"provenance": "shape-only-seed-B2-needs-B4-recapture"` rather than the `credentialed-legacy-capture-<date>` stamp the entry specifies. Same evidence as DW-B1-1(a).
## DW-B4-4 — DW-B2-4 BigQuery-routing pre-flight before any credentialed Phase-P run — DEFERRED (carries DW-B2-4)

Route `pypi_bigquery_downloads_raw` → `BigQueryDownloadsDataset` (the two-layer cost gate)
BEFORE any credentialed Phase-P run at the event. B4 deliberately did NOT route it in-loop:
it would change `conf/base/catalog.yml` and risk the `kedro-catalog-check=38` invariant for a
gate that only bites a credentialed run B4 never performs in-container. Carries DW-B2-4 forward.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — carries DW-B2-4 unchanged. `conf/base/catalog.yml:198-199` still routes `pypi_bigquery_downloads_raw` to `api.APIDataset`, not `BigQueryDownloadsDataset`. The pre-flight the entry mandates before any credentialed Phase-P run has not been done (and no such run has happened — see DW-B4-1).
## DW-B4-5 — parity-reconcile items surfaced at the credentialed run (carries DW-B1-3 / DW-B2-3) — DEFERRED

At the credentialed run, the drift report must reconcile the known legacy-vs-port deltas:
DW-B1-3 (`enumerate_conda_packages` duplicate-timestamp tie-break; Phase B.5 inactive
placeholder rows) and DW-B2-3 (`vuln_kev_affecting_current` package-wide vs version-scoped,
vs legacy CFA:3854), plus the Phase E ~44-feedstock maintainer-universe delta (PARITY_NOTES
"AC-5"). These need real data to reconcile; not doable in-loop.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the reconcile is gated on a run that has not happened. Both carried items are still open on their own entries (DW-B1-3, DW-B2-3), and `parity/evidence.py:51` shows no credentialed evidence was recorded. Nothing here is reconcilable without real data, exactly as recorded.
## DW-B4-6 — credentialed-mode read-path hardening (attended event) — DEFERRED

- source_spec: `b4-verify-dataset-parity-against-the-legacy-orchestrator.md`
  summary: `parity_runner.run_parity` CREDENTIALED mode does not yet harden the real-DB read path — a view missing from the legacy `cf_atlas.db`, a nonexistent `legacy_db` file, a URI-special-char path, or a `kedro_frame_provider` that raises/returns non-DataFrame currently propagate an uncaught error mid-run instead of a per-view "missing/errored" evidence record.
  evidence: Edge-case review (2026-07-17). The credentialed path is ATTENDED-only and exercised in-loop only via a synthetic on-disk/in-memory SQLite fixture + a synthetic provider (fixture mode is the shipped gate), so these are event-time robustness items, not in-loop correctness holes. Harden them alongside DW-B4-1 when the per-view Kedro composition is finalized against the real schema; wrap each per-view read in try/except emitting an errored `ParityEvidenceRecord` (material_drift=True) so one bad view doesn't abort the whole credentialed run.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the credentialed read path is still unhardened. No per-view try/except emitting an errored `ParityEvidenceRecord` was added, and the entry's own precondition (DW-B4-1, finalizing the per-view Kedro composition against the real schema) has not occurred.
## DW-B5-1 — re-point name_resolver.py / recipe-generator.py at Phase C + verify the live authoring read (Q6) — DEFERRED (read-only .claude/**)

- source_spec: `b5-port-the-external-refresh-assets.md`
  summary: Q6 default = consolidate the pypi↔conda mapping on the migrated Phase C. B5 landed the flat-cache EXPORT shim (`export_pypi_conda_map` -> `MappingCacheDataset`, merge onto last-good, g10_spelling + no-clobber preserved WITHIN Phase C). The actual re-point of the authoring-time readers (`name_resolver.py` / `recipe-generator.py` / `mapping_gap.py`) to read Phase C directly + the live verification of whether the standalone flat file is still needed CANNOT be done in-loop (`.claude/skills/conda-forge-expert/scripts/**` is HARD read-only + is the recipe-authoring surface this migration does not touch, spec §12).
  evidence: the flat file is retained as the compatibility shim (byte-format `{pypi_name: conda_name}`); until DW-B5-1 proves the readers can drop it, the shim stays. `g10_spelling` provenance + no-clobber survive regardless (AD-10).

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and structurally blocked as recorded. The re-point targets live under `.claude/skills/conda-forge-expert/scripts/**`, which the migration treats as HARD read-only, so the flat-file compatibility shim necessarily stays until someone works outside that boundary. Nothing in the atlas package changed this.
## DW-B5-2 — C1 wires the Dagster Schedules AND the concrete refresher/fetcher INJECTION (+ store-format fidelity) — DEFERRED (attended/C1)

- source_spec: `b5-port-the-external-refresh-assets.md`
  summary: B5 ships the refresh assets + the DECLARATIVE cadence (`params:refresh_cadences`, == legacy TTLs, fixture-proved) + the retry/observability budget metadata; `dagster` is never imported (AD-1), so the `dagster-dryrun` gate runs once C1 exists. C1 must (a) emit the Dagster Schedules from `params:refresh_cadences`, AND (b) INJECT the concrete refreshers — the vuln-db-env `appthreat-vulnerability-db` build for the vdb, the osv.dev-bucket fetcher for the OSV store — as the Dagster resource. In-loop the refresher defaults to None (offline: a DUE refresh keeps last-good + marks stale; a fresh store is a no-op), mirroring B1/B2's deferred fetch. The injected refresher/fetcher is also responsible for writing the store in the exact format the EXTERNAL consumers read (the operator's appthreat vdb / cve_manager cve/ store) — the in-container `_write` is a lean normalized representation for the gate.
  evidence: catalog constructs `VDBStoreDataset`/`OSVOfflineStoreDataset` with only `filepath` (+`bucket_url`); no refresher kwarg is wired (by design — credentialed/live runs attended-only, AD-11/NFR-2). `save()` honors `RefreshRequest.force` + cadence; `_describe()` carries `retry_budget` + `required_resource` for C1 to consume.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN on both halves. The refresher is still un-injected (the catalog constructs the store datasets with `filepath`/`bucket_url` only — no refresher kwarg), and the Dagster schedules are still not brought up: `orchestration/definitions.py:301` sets `SENSOR_DEFAULT_STATUS = dg.DefaultSensorStatus.STOPPED`, so nothing auto-starts. Both halves wait on the same C1 attended event as DW-C1-1.
## DW-B5-3 — DW-A2-P4 JFrog dynamic per-host credential attachment for enterprise-mirrored refresh stores — DEFERRED (no live surface)

- source_spec: `b5-port-the-external-refresh-assets.md`
  summary: The A2 review-pass P4 assigned the dynamic per-host JFrog credential attachment (attach the jfrog key iff an entry's resolved hostname suffix-matches an Artifactory host) to B5 (external-refresh / enterprise store routing). B5 does NOT implement it: none of the three shipped stores routes to an Artifactory host (vdb = local path; OSV = public osv.dev GCS bucket; mapping = local Phase C export), so the mechanism has no live surface to attach to, and the static credential-scoping gate stays exact.
  evidence: `tests/catalog/test_credential_scoping.py` CREDENTIAL_ALLOWLIST unchanged; no new `credentials:` key added. Revisit when an enterprise-mirrored refresh store (e.g. an Artifactory-hosted vdb/OSV mirror) actually lands.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and still with no live surface to attach to — which is the entry's own stated revisit condition, not a defect. None of the three shipped stores routes to an Artifactory host, so the dynamic per-host JFrog attachment has nothing to bind. Revisit remains correctly deferred to an enterprise-mirrored refresh store landing. (Note: this is the carried-forward body of the `DW-A2-P4` alias — see § Provenance.)
## DW-B5-4 — wire the AD-13 staleness marker into the G/G' consumer read-path (degrade to indeterminate) — DEFERRED (consumer-side, B2 nodes)

- source_spec: `b5-port-the-external-refresh-assets.md`
  summary: B5's `VDBStoreDataset`/`OSVOfflineStoreDataset` SURFACE the AD-13 staleness marker (`is_stale()` / `staleness()`; an air-gapped/missing store returns last-good/empty + a machine-readable marker). But no CONSUMER reads it yet: `summarize_vdb_vulns` / `per_version_vulns` receive an empty frame indistinguishable from a genuinely vuln-free store, so an air-gapped run can produce an empty rollup that reads as a clean pass. AD-13's consumer contract ("degrade the affected axis to indeterminate, never a silent pass") needs the G/G' read-path (B2's nodes) to check the store's staleness and emit an indeterminate signal.
  evidence: Blind-Hunter finding (2026-07-18). B5 owns the refresh-asset staleness SURFACE (AC-5: marker stamped + surfaced, offline load returns last-good — proven by `tests/datasets/test_refresh_assets.py`); the consumer-side degrade-to-indeterminate is a follow-up on the B2 vulnerability nodes.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the consumer is still blind. Grepping the whole `pipelines/` tree for `is_stale` or `staleness()` returns ZERO hits, so `summarize_vdb_vulns` / `per_version_vulns` still cannot distinguish an air-gapped empty store from a genuinely vuln-free one. AD-13's degrade-to-indeterminate contract remains unimplemented on the consumer side.
## DW-B6-1 — spdx-schema-gap atlas-usage ranking needs `conda_license` (not yet produced by core) — DEFERRED

- source_spec: `b6-port-the-seed-gaps-pipeline.md`
  summary: `report_spdx_schema_gap` ranks its add-to-schema / non-standard tiers by how many actionable packages carry each `conda_license` (legacy `v_actionable_packages.conda_license`). The migrated `core_packages_enumerated` carries `conda_name/latest_version/subdirs` but NOT `conda_license` (a B1-scope column not yet ported), so those two tiers are empty in-loop. The node reads `core_packages_enumerated` and extracts `conda_license` gracefully (missing column -> empty atlas usage); the atlas-INDEPENDENT `upstream-drift` tier (upstream SPDX IDs absent from the vendored enum) needs no atlas data and keeps the report non-empty (proven by `test_spdx_drift_nonempty_without_conda_license`).
  evidence: `grep -rn conda_license src/` returns 0 hits in the kedro package; `core.nodes.enumerate_conda_packages` output columns are `conda_name/latest_version/subdirs` only. Re-point the atlas-usage read to a full actionable-packages-with-license dataset when B1/parity produces `conda_license`.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, with one measurement changed since authoring. The entry's evidence said '`grep -rn conda_license src/` returns 0 hits'; it now returns 6 — but all six are in `pipelines/seed_gaps/nodes.py`, the CONSUMER that reads the column gracefully. It is still not PRODUCED: `core_packages_enumerated` carries no `conda_license`, so the add-to-schema and non-standard tiers stay empty in-loop.
## DW-B6-2 — cwe-seed-gap `_other_impact` headline needs the per-package CWE-rollup dataset — DEFERRED

- source_spec: `b6-port-the-seed-gaps-pipeline.md`
  summary: The legacy `cwe-seed-gap` also emits an "Other-bucket affects N packages" headline read from `packages.vuln_cwe_categories_json` (the per-package CWE-categories rollup blob). No migrated kedro dataset carries that column yet (the vulnerability pipeline's per-package CWE rollup), so `report_cwe_seed_gap` ships the proposal rows only (the load-bearing output) and omits the impact headline. Additive summary stat, not a correctness hole — add it when a per-package CWE-categories dataset lands.
  evidence: `vulnerability_cwe_categories` (the migrated CWE catalog table) carries `cwe_id/cwe_name/category` — the catalog rows, not the per-package rollup. The proposals (which CWEs to seed) are fully computed; only the universe-cost headline is deferred.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — no per-package CWE-categories rollup dataset landed. The migrated `vulnerability_cwe_categories` remains the catalog table (`cwe_id`/`cwe_name`/`category`), not the per-package blob the `_other_impact` headline needs. The proposal rows — the load-bearing output — are unaffected.
## DW-B7-1 — the UPDATE-FEEDSTOCK bucket needs an upstream-of-record column (not yet on core_packages_enumerated) — DEFERRED

- source_spec: `b7-extend-the-universal-sbom-intake.md`
  summary: The six-bucket matcher's UPDATE-FEEDSTOCK verdict (conda-forge behind upstream) needs the upstream-of-record version to compare against cf `latest_version`. The migrated `core_packages_enumerated` carries `conda_name/latest_version/subdirs` but NOT `upstream_version` (a B1-scope column not yet ported, sibling of DW-B6-1). `_build_indexes`/`classify_bucket` read `upstream_version` gracefully (`.get`, missing column -> None -> UPDATE-FEEDSTOCK cannot fire from live data); the AC-4 fixture supplies the column so all six buckets are proven. Re-point to a full actionable-packages-with-upstream dataset when B1/parity produces it.
  evidence: `test_all_six_buckets_reproduced_on_a_fixture_inventory` supplies `upstream_version` in its fixture core frame; the matcher's `_build_indexes` guards the column with `if "upstream_version" in core_packages_enumerated.columns`.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `upstream_version` has no producer. It does not appear in `pipelines/core/nodes.py`, so `core_packages_enumerated` still carries only `conda_name`/`latest_version`/`subdirs` and the UPDATE-FEEDSTOCK bucket still cannot fire from live data. Sibling of DW-B6-1, same root cause: a B1-scope column never ported.
## DW-B7-2 — the real transitive resolver (pip --dry-run / py-rattler solve) is injected, not shipped in-package — DEFERRED

- source_spec: `b7-extend-the-universal-sbom-intake.md`
  summary: `TransitiveResolverDataset` owns the resolver IO via an INJECTED `resolver` callable (default None == offline -> `unresolved` marker, AD-13). The concrete resolver needs `subprocess` (pip `--dry-run --report`) or py-rattler, both of which cannot live in the atlas package (`subprocess` is on the A2 no-inline-IO denylist, AST-scanned over the whole package). B7 ships the offline-safe `unresolved` path + the injected-callable seam + a stub-resolver fixture proving the resolved path (depth/fan-out recorded). The concrete resolver + its wiring land with the orchestration wave (C1) / a follow-up — same pattern as the B5 refresher-injection deferral (DW-B5-2).
  evidence: `tests/datasets/test_sbom_intake.py::test_resolver_resolved_records_depth_and_fanout` uses a stub resolver; `test_resolver_offline_returns_unresolved_marker` + `test_resolver_exception_degrades_to_unresolved_never_crashes` prove the offline/never-crash contract; `tests/catalog/test_no_inline_io.py` passes (no `subprocess` import anywhere in the package). Review note (Blind LOW-5): AC-1's "never hang" is guaranteed for the OFFLINE (default None) + exception paths B7 ships; a WEDGED injected resolver has no wall-clock guard — the injected callable's CONTRACT is that it must self-bound (a wall-clock guard lands with the concrete resolver + its orchestration wiring).

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the resolver is still injection-only. The concrete resolver would need `subprocess` or py-rattler, and the A2 no-inline-IO AST scan still bans that import package-wide, so the offline `unresolved` marker remains the shipped path. Lands with the C1 orchestration wiring, which is itself still deferred (DW-C1-1).
## DW-B7-3 — universe-BOM standalone pypi-only completeness (not a scope hole; a widening) — DEFERRED

- source_spec: `b7-extend-the-universal-sbom-intake.md`
  summary: RESOLVED-IN-B7 (Blind HIGH-1): the ADD path now reads the FULL PyPI universe (`pypi_universe`, produced by `pypi_intelligence.enumerate_pypi_universe`, column `pypi_name`) as the authoritative membership signal — VERBATIM legacy `universe_lookup` — so a pypi name on PyPI-but-not-conda-forge correctly buckets ADD (was silently UNKNOWN when membership derived only from the conda mapping). The remaining widening: `build_universe_sbom` emits only conda components + `cfe:pypi_name` on mapped rows (not standalone `pkg:pypi/<name>` universe members), so the universe-BOM ARTIFACT is conda-centric; membership for matching comes from `pypi_universe` directly (correct), and the standalone-pypi-only universe-BOM completeness is a later artifact-shape widening, not a matcher correctness hole.
  evidence: `test_add_membership_comes_from_the_full_pypi_universe_not_the_mapping` (ADD via pypi_universe, unmatched-to-mapping) + `test_unmatched_pypi_not_in_universe_is_unknown_never_add`; `_build_indexes` reads `pypi_universe["pypi_name"]`. The G10 bare-match guard (Blind MEDIUM-3) is now PORTED using `pypi_conda_mapping` (`conda_to_pypifold`) — `test_g10_bare_match_guard_rejects_a_name_coincidence`.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN as a widening, not a hole — the entry's own framing. The matcher correctness half was RESOLVED in B7 (ADD membership reads the full `pypi_universe`); what remains is the artifact shape: `build_universe_sbom` still emits conda components plus `cfe:pypi_name` on mapped rows, with no standalone `pkg:pypi/<name>` universe members.
## DW-B8-1 — the concrete live Basilisk fetcher (querybatch / detail GET) is injected, not shipped in-package — DEFERRED

- source_spec: `b8-basilisk-conda-native-vulnerability-ingestion.md`
  summary: `BasiliskBatchDataset` / `BasiliskDetailDataset` own the fetch IO via an INJECTED `fetcher` (default None == OFFLINE -> keep last-good + mark stale, AD-13). The concrete Basilisk client needs an HTTP client — an A2 no-inline-IO-denylisted import that never lives in the atlas package. B8 ships the offline-safe stale path + the injected-callable seam + a stub fetcher proving the ≤1,000-query chunking, the bounded rate-limit discipline (per-request `acquire()`, `parse_retry_after` + jitter, dedupe), and the resolved paths. The concrete fetcher + its Dagster wiring land at C1 / an attended run — same pattern as the B5 refresher-injection (DW-B5-2) and B7 resolver-injection (DW-B7-2) deferrals. Basilisk is PRE-ANNOUNCEMENT (no public docs/repo as of 2026-07-16; API live-validated 2026-07-15) — NO live Basilisk call in any test (AD-11).
  evidence: `tests/datasets/test_basilisk.py` drives every path against a STUB fetcher; `test_batch_offline_marks_stale_keeps_last_good` + `test_detail_offline_marks_stale` + `test_wired_fetcher_load_marks_stale_when_unpopulated` prove the offline/never-crash contract; `tests/catalog/test_no_inline_io.py` passes (no `subprocess`/HTTP import anywhere in the package incl. `datasets/basilisk.py`).

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — same injected-seam shape as DW-B5-2 and DW-B7-2, and blocked by the same rule: a concrete Basilisk client needs an HTTP import that the A2 no-inline-IO scan bans from the package. The offline stale path plus the stub-driven chunking/rate-limit proofs are what ship; the concrete fetcher waits on C1 or an attended run.
## DW-B8-2 — the no-currency-conflation view's behind-upstream join is fixture-supplied — DEFERRED

- source_spec: `b8-basilisk-conda-native-vulnerability-ingestion.md`
  summary: `v_basilisk_advisories` (the AC-4 read-view transform) joins advisories x per-advisory `fix_available` x a behind-upstream frame supplying `conda_name` + `version_current`. The migrated `vcs_upstream_versions` (Phase K) carries upstream version, but the exact behind-upstream currency column/join re-points when the B-wave upstream-of-record data fully lands (sibling of DW-B7-1). The AC-4 fixture supplies the behind-upstream frame so the no-conflation guard is proven in-loop (version-currency + security-currency kept as distinct columns; neither derives the other).
  evidence: `test_current_package_still_surfaces_its_advisory` + `test_view_does_not_render_security_as_version_currency` supply `behind_upstream` with `version_current`; `v_basilisk_advisories` reads it with `{"conda_name","version_current"} <= set(bu.columns)` (graceful: absent -> None).

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the join is still fixture-supplied, because its upstream data still does not exist. This is the same missing column as DW-B7-1 (`upstream_version` absent from `core_packages_enumerated`), so the behind-upstream re-point cannot happen until the B-wave upstream-of-record data lands.
## DW-B8-3 — the full 21,163-package Basilisk population run is credentialed/attended — DEFERRED

- source_spec: `b8-basilisk-conda-native-vulnerability-ingestion.md`
  summary: The full Python-population batch run is credentialed/attended (NFR-2/AD-11); in-loop the batch is driven by fixtures. Population source is `core_packages_enumerated` (`conda_name`/`latest_version` -> the conda PURL query keys); re-point to a dedicated full-python-population dataset if one lands. The empty-but-successful-fetch -> stale behavior (Blind Hunter MEDIUM, deferred) is inherited from the reused B5 `ExternalRefreshDataset` semantics (a store-level signal can't distinguish "zero advisories" from "unreachable") — re-evaluate if a fresh-empty distinction is needed at the attended run.
  evidence: `chunk_queries`/`query_population` prove the ≤1,000 chunking (2500 -> [1000,1000,500]; 1001 -> [1000,1]) against a stub; the credentialed fan-out is DATASET-owned via `query_population`, called by the attended/Dagster path (DW-B8-1).

  status: open

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. No credentialed Basilisk population run has occurred — the population source would be `core_packages_enumerated`, and the fan-out is dataset-owned via `query_population`, called only by the attended/Dagster path (DW-B8-1), which is itself still deferred. In-loop the batch is still fixture-driven.
## DW-C1-1 — the live Dagster schedule bring-up (ATTENDED, Q2) — DEFERRED to the wave-boundary event

- source_spec: `c1-integrate-kedro-dagster-for-scheduling-execution.md`
  summary: C1 shipped the offline glue (`orchestration/definitions.py`) + the `dagster-dryrun` gate (definitions load, schedules enumerate, jobs resolve, per-op timeout tags, Phase-P admin-only) — all verified with NO live execution. The actual schedule BRING-UP is the attended Q2 boundary: standing up a Dagster daemon (`dagster dev -m pyforge.atlas.orchestration.definitions`), turning the schedules RUNNING (they ship with no `default_status=RUNNING`, so nothing auto-starts), and observing real retries/phase-state in the UI. Do NOT weaken the dryrun gate to unattended-execute (NFR-12).
  evidence: `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline; `tests/orchestration/test_definitions_dryrun.py` (19) + the AD-1 import-ban (`tests/catalog/test_no_inline_io.py`) are the loop-consumable gate. `defs = build_definitions()` builds under blocked sockets (no network IO at import).

  status: open

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. Nothing was turned RUNNING: `orchestration/definitions.py:301` still declares `SENSOR_DEFAULT_STATUS = dg.DefaultSensorStatus.STOPPED`, and `:299` still carries the inline note that turning them running 'against a live feed is the attended' event, citing this very entry (DW-C1-1). `:576` repeats 'Ships STOPPED'. The offline dryrun gate is intact and was not weakened.
## DW-C1-2 — per-op runtime ENFORCEMENT + profile-config run-wiring are bring-up concerns (structural-only in C1)

- source_spec: `c1-integrate-kedro-dagster-for-scheduling-execution.md`
  summary: Two AC surfaces are STRUCTURAL in C1 and become operative only at the live bring-up (both reviewer-flagged, recorded not faked):
    (a) **Per-op timeout ENFORCEMENT.** Each op carries an independent `dagster/max_runtime` tag (the monolith is gone — no job/run-level timeout anywhere), but `dagster/max_runtime` is Dagster's run-monitoring tag, enforced by the DAEMON at bring-up. Today's operative isolation (a Phase-R overrun can't abort F/K/N) comes from JOB SEPARATION — Phase R rides only the weekly `bootstrap_data` job, F/K/N have their own scheduled jobs — not from the tag. Per-op runtime capping arrives with the daemon.
    (b) **Profile precedence run-wiring.** `resolve_profile_config` (maintainer/admin/consumer, precedence: run-config > env > profile default) is a verified pure function but is NOT yet attached to any job as `RunConfig`/`default_config`; a real run does not yet consume it. Wiring the resolved profile config into the job run-config is a bring-up step.
    Also deferred: the kedro-dagster `before/after_pipeline_run` hook ops exist only on the translated base graph and are filtered out of the derived/scheduled jobs — confirm at bring-up whether per-run session hooks are needed on the scheduled jobs or are intentionally base-only.
  evidence: `test_timeouts_are_not_a_single_monolith` + `test_every_op_has_its_own_timeout` prove the structural side; `resolve_profile_config` is exercised only by the gate, and `build_definitions` does not call it (structural-scope, by design for the attended C1 boundary).

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN on the half that matters. `resolve_profile_config` is defined at `orchestration/definitions.py:371` and referenced in the module docstring at `:16`, but it is still attached to no job as `RunConfig`/`default_config` — a real run still does not consume it. Per-op timeout ENFORCEMENT likewise still depends on the daemon that DW-C1-1 has not brought up.
## DW-D2-1 — the full 28-page Vizro inventory is CIS-two-spine deferred

- source_spec: `d2-build-the-vizro-dashboard-port-the-28-clis.md`
  summary: D2 shipped the buildable core — the BSL-driven Vizro app framework, the AC's live-confirmed-first pages (behind-upstream / query-atlas / whodepends / feedstock-health / my-feedstocks / detail-cf-atlas / staleness-report), and the fully-specified factory-status page — all routed through the D1 semantic models (AD-8). The FULL 28-page inventory + each page's detailed design is blocked on the **CIS two-spine specs** (`DESIGN.md` + `EXPERIENCE.md`, § 84) which are NOT yet produced (Spine-Deferred). Producing them (the CIS Carson/Maya planning pass) is the precondition; the remaining pages port against them. Do NOT expand the page set past the live-confirmed core without the CIS spine.
  evidence: D2 AC "Given the D1 BSL models AND the CIS two-spine design specs"; verify-gate note "D2 page inventory detail resolves in the CIS specs (Spine Deferred)". The dashboard-dryrun gate asserts the shipped pages build offline + are BSL-driven; it does not assert 28-page completeness.

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the precondition never arrived. The CIS two-spine specs (`DESIGN.md` + `EXPERIENCE.md`) were not produced, so the full 28-page inventory stays blocked and the page set correctly was not expanded past the live-confirmed core.

  resolution: **CLOSED 2026-08-28 by Story 20.4** (`spec-20-4-the-cis-two-spine-specs-exist.md`,
    CAP-7). Ran `bmad-cis-install` (the `bmad-creative-intelligence-suite` v0.3.1 conda package,
    already resolved in the `local-recipes` env), which copies its full six-persona suite
    (Carson, Dr. Quinn, Maya, Victor, Caravaggio, Sophia) plus all four of its workflow skills
    (design-thinking, innovation-strategy, problem-solving, storytelling) into `.claude/skills/`
    — this story activated two of those: Carson (`bmad-cis-agent-brainstorming-coach`) for the
    divergent EMPATHIZE/IDEATE pass over the full 28-CLI read surface (recorded at
    `_bmad-output/brainstorming/brainstorm-atlas-19-page-spine-2026-08-28/`), then Maya
    (`bmad-cis-agent-design-thinking-coach`) for a genuine, full run of her own
    `bmad-cis-design-thinking` workflow (EMPATHIZE through TEST) against the 21 CLI questions
    still unaddressed by any shipped page (28 total minus the 7 of `PAGE_INVENTORY`'s 9 entries
    that are genuine CLI ports; `estate-cache` is CAP-19/Lane-3 and `factory-status` is an
    observability page, neither a CLI port) — recorded verbatim at
    `_bmad-output/projects/pyforge-atlas/planning-artifacts/design-thinking-atlas-19-pages-2026-08-28.md`.
    The two spine files land at
    `_bmad-output/projects/pyforge-atlas/planning-artifacts/DESIGN.md` (technical/visual — per-page
    BSL model, source dataset, Vizro layout) and `.../EXPERIENCE.md` (behavioral — per-page
    persona, user journey, interaction pattern, success metric), covering all 19 remaining pages
    (one documented consolidation: `platform-breakdown`/`pyver-breakdown`/`channel-split` merge
    into one `distribution-breakdown` page behind a dimension selector, bringing the 21-question
    backlog to exactly 19 pages with zero questions dropped — see `DESIGN.md` § 0 and § 6 for the
    full reconciliation). The full 28-page inventory + each page's detailed design is no longer
    blocked; Story 20.5 ports against these two spines. **Carried forward, not re-litigated
    here:** this story's own spec records a deferred item flagging the 19-vs-21 page mapping as
    a design judgment call Story 20.5's implementer should re-verify before treating "19" as
    fixed — see `spec-20-4-the-cis-two-spine-specs-exist.md` frontmatter `deferred`, second item.

  status: closed
## DW-D2-2 — shell pages await their composed-store materialization (staleness / query-atlas / detail-cf-atlas; behind-upstream / whodepends stay open under DW-D2-1)

- source_spec: `d2-build-the-vizro-dashboard-port-the-28-clis.md`
  summary: Several core pages are BSL-WIRED SHELLS: the loader queries the correct D1 semantic model, but the composed Parquet store that model binds to (e.g. a `semantic_packages` primary output joining the per-metric columns) is not materialized as a single dataset yet, so the page renders empty against the live catalog until that store lands. The loaders are honest (empty BSL query, never fabricated rows). Materializing the composed store (a small kedro node emitting the semantic-input Parquet) wires the live data. Pages backed by an existing single dataset (feedstock-health → core_feedstock_health; my-feedstocks → vcs_package_maintainers) are already live.
  evidence: `dashboard/data.py` shell loaders are grouped under a "BSL-wired SHELL pages (composed store not yet materialized — DW-D2)" banner; each returns an empty typed frame via `_bsl_query_or_empty` when the store is absent.

  resolution: **CLOSED 2026-08-27 by Story 20.3** (`spec-20-3-named-pipeline-derivation-of-the-dashboard-stores.md`,
    CAP-6 / the `query-plane-catalog` operator ruling, 2026-08-26). The named, downstream-only
    `semantic_packages` Kedro pipeline (`pipelines/semantic_packages/`, auto-discovered, zero
    registry edits) composes the `semantic_packages` primary store from the sealed `core` +
    `vcs_health` pipelines' own catalog outputs — `core_packages_enumerated` (population),
    `core_latest_status` (latest_status), `core_feedstock_attribution` ⋈
    `vcs_archived_feedstocks` (feedstock_archived), `core_downloads` (downloads_total /
    downloads_30d) — with zero diff inside the sealed seven. The 4 `metrics.METRIC_PROVENANCE`
    deferred-input columns (`latest_conda_upload` / `latest_upload_age_days` / `releases_30d` /
    `total_versions`) are declared NULL by the node, never fabricated — the honest-empty
    convention holds for the new store. `dashboard/data.py`'s "packages composed store not yet
    materialized — DW-D2" banner is retired (now reads "BSL-wired data pages over the composed
    `semantic_packages` store"). A fresh checkout still renders honestly-empty until an operator
    runs `kedro run --pipeline core`, `--pipeline vcs_health`, then `--pipeline
    semantic_packages` — that operational precondition is documented, not a second code path.
    `behind-upstream` / `whodepends` (named in this entry's title) stay NO-BSL-MODEL shells —
    that gap is DW-D2-1's CIS two-spine scope (Story 20.4/20.5), not this one.

  status: closed

## DW-D2-3 — DEV-AUTO visual verification of the rendered UI (headless container cannot)

- source_spec: `d2-build-the-vizro-dashboard-port-the-28-clis.md`
  summary: D2 is a DEV-AUTO (visual-judgment) story. The dashboard-dryrun gate verifies the Dashboard OBJECT builds offline + structural agent-legibility (stable page id/title, deterministic layout, semantic factory-status table, AD-17 stamp), but the in-container run cannot VISUALLY verify the rendered browser UI (no display, no `app.run()`). The human/visual pass — actual `pixi run dashboard` render, the §2.1 semantic-HTML/ARIA browser-agent navigation check — is the deferred DEV-AUTO verification.
  evidence: `dashboard-dryrun` builds the object + asserts structure only; it never launches the server (offline gate, mirrors C1 dagster-dryrun / C2 viz-loadable).

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the visual pass is inherently out of reach of this verification too. The `dashboard-dryrun` gate still builds the Dashboard OBJECT and asserts structure only, never launching a server, so the browser-rendered UI and the §2.1 semantic-HTML/ARIA check remain unverified by anything.

  evidence-update: 2026-08-26 — the two blockers are now removed and the FIRST visual pass ran. (1) Serve entrypoint exists: `pixi run -e local-recipes dashboard-serve` (`scripts/dashboard_serve.py`, same PYTHONPATH as the dryrun gate; foreground, 127.0.0.1:8050). (2) Operator-session visual verification via headless Chrome screenshots, human-reviewed: `factory-status` fully live (AD-17 build stamp rendered, real sprint-ledger rows in the grid, 9-page nav present, dark theme correct); root page = `feedstock-health` renders the page shell + AD-17 provenance line degrading HONESTLY ("unavailable — backing file not found: data/primary/core_feedstock_health/core_feedstock_health.parquet") with an empty grid — the grounded pages need the atlas Kedro pipeline outputs materialized at the data root before they show data in a fresh checkout. Residual before this entry can close: the §2.1 semantic-HTML/ARIA browser-agent navigation check, and a data-present visual pass after a pipeline run materializes the Parquet tree.

  evidence-update: 2026-08-28 — Story 20.5 (`spec-20-5-port-the-remaining-nineteen-vizro-pages.md`,
    CAP-7) genuinely resolves residual (1) and executes but does NOT resolve residual (2) — this
    entry stays OPEN; do not read the below as a closure. (1) The §2.1 semantic-HTML/ARIA
    browser-agent navigation check: `test_dashboard_28_pages_semantic_nav_and_aria` in
    `tests/dashboard/test_dashboard_e2e.py` drives a real headless-Chrome Playwright session and
    asserts, against the ACTUAL rendered DOM (not assumed): all 28 `PAGE_INVENTORY` pages have a
    real `<a href>` nav link whose accessible name (link text) equals the page title exactly, in
    deterministic order; the nav accordion's interactive control carries a real `aria-expanded`
    ARIA attribute; and every page independently renders a deterministic `<h2 id="page-title">`
    heading plus its own legibility Card, with no client-side error. **A real, honestly-recorded
    gap** (found by driving the actual DOM, not fabricated away): Vizro's shipped page-select
    control is a `<div>`-based accordion, not a native `<nav>`/`role="navigation"` landmark (the
    one literal `<nav>` tag on the page is an empty, hidden top navbar Vizro doesn't use), and page
    content sits in a plain `<div>`, not a `<main>`/`role="main"` landmark — a pre-existing
    Vizro/dash-bootstrap-components framework limitation outside a single page-port story's
    surgical-change scope (patching Vizro's own component templates is a framework-level change).
    Native `<a href>` links + heading elements remain genuinely, independently navigable by a
    browser-agent regardless of this gap; a future effort could file it against Vizro upstream or
    wrap the shell in a custom container if it ever blocks a real consumer. This portion of the
    residual is DONE and real.
    (2) The data-present visual pass is **NOT done** — **STAYS OPEN**. What was actually run
    (`pixi run -e local-recipes dashboard-serve`, headless-Chrome screenshots, operator-reviewed)
    was against a FRESH, EMPTY data root (no `data/` tree exists in this worktree at all) — it
    re-proves the already-known honest-empty behavior (documented before this story started, e.g.
    the 2026-08-26 evidence-update above), not a post-pipeline-run, data-PRESENT state. All 28
    pages render + degrade honestly (the 9 original pages unchanged; all 19 new pages show their
    own "Data gap" note + AD-17 "unavailable — backing file not found: <path>" stamp + the model's
    real declared columns on an empty AG Grid, e.g. `cve-watcher` →
    conda_name/severity/since_days/vuln_kev_affecting_current/then_count/now_count/delta) — that
    is exactly the VISUAL_PASS_NO_DATA edge case's contract, and a legitimate thing to have
    verified, but it is NOT the "data-present visual pass" this entry's 2026-08-26 evidence-update
    named as the residual. Materializing real data requires an ATTENDED operator running `kedro
    run --pipeline core`, `--pipeline vcs_health`, then `--pipeline semantic_packages` (per
    `pipelines/semantic_packages/README.md`) — these pipelines read LIVE external raw sources
    (GitHub API, PyPI/npm/CRAN/etc. registries, conda repodata, S3 download stats; confirmed via
    `conf/base/catalog.yml`), a live-network, potentially credentialed, likely long-running
    sequence that is attended-only per this project's own binding testing contract
    (`project-context.md` § Testing Contract: "Credentialed runs are attended-only (human present
    at execution)") — genuinely out of reach for an unattended dispatch, mirroring the DW-C1-1
    live-Dagster-schedule and DW-D3-1 live-LLM-backend attended bring-ups. `factory-status` still
    renders live (epics.md + docs/specs rows) even against the empty data root; only the gitignored
    Tier-3 `sprint-status.yaml` source is empty in this worktree, an unrelated, pre-existing,
    non-CI-blocking gap (`dashboard-dryrun` is a local pixi task, not wired into
    `.github/workflows/`) — not something this story's scope touches.

  status: open

## DW-D3-1 — the live Vizro-AI NL→chart backend bring-up (ATTENDED, Q3) — DEFERRED to the wave-boundary event

- source_spec: `d3-vizro-ai-nl-interface-query-vizro-ai-mcp-tool.md`
  summary: D3 shipped the buildable-now half — the thin `query_vizro_ai` MCP tool (AD-7), the `pyforge.atlas.nl` seam (backend resolver + BSL-grounded context), its registration (tools.py + server.py + audit.NL_INTERFACE_TOOLS + the mcp package export), and the `vizro-ai-dryrun` gate — all offline with NO live LLM call. The actual live Vizro-AI NL→chart invocation is the **attended Q3 backend event**: it happens only once a model backend is configured through repo model-backend config (`OPENAI_BASE_URL`+`OPENAI_API_KEY` or `ANTHROPIC_BASE_URL`+`ANTHROPIC_API_KEY` — Q3 §11 default, BINDING; never a hardcoded public endpoint). In-container with no backend configured the tool returns a structured `backend-not-configured` advisory; with a backend configured it returns a `backend-configured-live-call-deferred` receipt naming the repo-config endpoint but STILL makes no live call. At the event: configure the backend env, instantiate the Vizro-AI NL agent against the resolved backend + the BSL-grounded context (`build_bsl_context`), invoke NL→chart, and replace the deferred receipt's `chart: None` with the generated chart/insight. The `vizro_ai` top-level `VizroAI` entrypoint is absent in the pinned 0.4.1 (only `vizro_ai.agents.chart_agent`, a pydantic-ai Agent needing a backend), so the live-entrypoint wiring is finalized at the event; the import stays lazy+guarded in `nl/query.py` (AD-1: only `nl/` imports `vizro_ai`). Do NOT weaken the `vizro-ai-dryrun` gate to unattended-execute, and do NOT bake a public endpoint in (NFR-12 / Q3 §11).
  evidence: `tests/nl/test_query_vizro_ai_dryrun.py` proves the tool is registered + callable, the unconfigured path returns the advisory with no network (sockets blocked), a configured `OPENAI_BASE_URL` is the endpoint used, no host-bearing URL literal exists in the resolver (Q3 §11), the tool body is AD-7-thin, and the NL context is BSL-grounded (AD-8). `nl/query.py::query_vizro_ai` returns `chart=None` in both paths; `vizro_ai_available()` is a guarded probe. Mirrors the C1 dagster-schedule bring-up (DW-C1-1) and the B5/B7/B8 injected-fetcher deferrals.

  status: open

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. No backend was configured and no live call was wired: `nl/query.py:28-29` still defines both deferral statuses — `STATUS_UNCONFIGURED = "backend-not-configured"` and `STATUS_DEFERRED = "backend-configured-live-call-deferred"` — and `:91-93` still documents both paths returning receipts rather than charts. The dryrun gate was not weakened.
## DW-D3-2 — the dashboard NL query field (the D2 Vizro dashboard's NL entry point) — DEFERRED (carries DW-D3-1 + the CIS spine)

- source_spec: `d3-vizro-ai-nl-interface-query-vizro-ai-mcp-tool.md`
  summary: D3 delivers the NL interface as an MCP tool (`query_vizro_ai`) — the agent-facing surface. The other NL surface, a natural-language query FIELD embedded in the D2 Vizro dashboard (a user types a question on a page and gets a generated chart), is DEFERRED: it depends on the live Vizro-AI backend (DW-D3-1) AND on the CIS two-spine design specs that gate the dashboard's page design (DW-D2-1). When both land, add the NL field as a dashboard component that calls the same `pyforge.atlas.nl` seam (so the MCP tool and the dashboard field share one backend-routing + BSL-grounding path, never a second execution plane — AD-23). Until then the dashboard ships without an NL field.
  evidence: D3's shipped surface is the MCP tool only (`server.py` `query_vizro_ai` @mcp.tool + `tools.query_vizro_ai`); `dashboard/app.py` is unchanged by D3 (no NL component added). The shared seam (`pyforge.atlas.nl`) is deliberately UI-agnostic so the dashboard field can reuse it at the event.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — and doubly blocked, as recorded. Its two preconditions are both still open on their own entries: the live Vizro-AI backend (DW-D3-1, still returning deferral receipts) and the CIS spine gating dashboard page design (DW-D2-1, specs never produced). The dashboard still ships without an NL field.
## DW-E1-1 — the live cross-process A2A wire (a running fasta2a server / broker) — DEFERRED

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story E1, FR-11)
  summary: E1 shipped the load-bearing, buildable-now half of the A2A surface — the `a2a/` module as the SINGLE payload schema source (AD-20: one discriminated family for both insights and alerts, no second dialect), the AD-17-stamped builders (`build_insight_payload` referencing a BSL metric by `semantic.METRIC_PROVENANCE` id per AD-8 / `build_alert_payload`), the exact payload↔`a2a.types.Message` serialize/deserialize round-trip (canonical JSON inside a real a2a-sdk DataPart — protobuf Struct would floatify ints, so JSON preserves the payload EXACTLY), and the resolved transport: **direct in-process message-passing** (`hand_off` → `AuthoringInbox`) proving the cf_atlas-analytical → conda-forge-expert-authoring direction offline + deterministically. The genuine cross-process wire — standing up a live `fasta2a` (FastAPI-style A2A) server or an A2A broker between two OS processes so the two agents exchange messages over a bound socket — is DEFERRED: it needs a bound socket + a second process, neither of which comes up offline in-container, and faking a broker would be dishonest (mirrors the DW-C1-1 live-Dagster-schedule and DW-D3-1 live-LLM-backend attended bring-ups). Because the message ENVELOPE is already the real a2a-sdk `Message`, the follow-up is a delivery-substrate swap (`inbox.receive(msg)` → an HTTP/broker `send`), not a schema change. Do NOT weaken the offline round-trip/hand-off gate to unattended-execute a live server.
  evidence: `tests/a2a_surface/test_a2a_payloads.py` drives the whole surface against the in-process hand-off — `test_insight_round_trip_is_exact` / `test_alert_round_trip_is_exact` (exact incl. AD-17 stamp, no int→float drift, unicode), `test_analytical_to_authoring_hand_off` (ordered exact delivery to the authoring inbox), the AD-20 single-schema-source scans (`test_ad20_no_competing_payload_schema_outside_a2a`, `test_ad20_only_a2a_schema_subclasses_the_base`) + `tests/catalog/test_no_inline_io.py::test_a2a_sdk_only_in_a2a_layer` (only `a2a/` imports the a2a SDK), AD-17 (`test_ad17_stamp_required_and_injected`, `test_ad17_stamp_on_the_wire_envelope`), AD-8 (`test_ad8_insight_metric_must_be_a_bsl_identifier`), and the degrade-not-crash edges (unknown kind / malformed JSON / non-JSON-native field / missing payload part). No socket is bound and no second process is spawned in any test (AD-11 / offline).

  status: open

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. No cross-process A2A wire exists — no fasta2a server, no broker, no bound socket. The in-process `hand_off` → `AuthoringInbox` transport remains the shipped path, which is the honest offline half the entry describes. Because the envelope is already a real a2a-sdk `Message`, this stays a substrate swap rather than a schema change.
## DW-E2-1 — the live OTel collector + OpenLineage backend wiring (env-driven) — DEFERRED

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story E2, FR-12)
  summary: E2 shipped the load-bearing, buildable-now half of the observability surface — the `observability.py` module as the SINGLE instrumentation seam (AD-6/AD-23: `openlineage`/`opentelemetry` confined there by `test_observability_libs_only_in_observability`), a Kedro Hooks impl (`AtlasObservabilityHooks`) declared ONCE in `settings.HOOKS` so EVERY entry point inherits it (a `kedro run` natively, a Dagster run via C1's `KedroProjectTranslator` → `KedroSession.run`), emitting per-node OpenLineage RunEvents (START/COMPLETE/FAIL) with input/output dataset lineage + the rows/latency/cache-hit metric facets (`OutputStatisticsOutputDatasetFacet.rowCount` + the custom `AtlasNodeMetricsRunFacet`), and an OTel span tree (pipeline → node → per-dataset read/write "API-call" spans). Nodes stay pure DataFrame→DataFrame (AD-2/AD-6) — all instrumentation is in the hook layer. Both backends are INJECTABLE and default to no-op/offline: `tracer_provider=None` → a local `TracerProvider` with no exporter (spans dropped, no network, never set globally); `openlineage_client=None` → OL emission skipped. The ACTUAL live wiring — a real OTLP endpoint (`OTEL_EXPORTER_OTLP_ENDPOINT` + a `BatchSpanProcessor`/`OTLPSpanExporter`) and a real OpenLineage backend URL/transport (`OPENLINEAGE_URL` → an `HttpTransport`) resolved from env at run bring-up — is DEFERRED: no collector/backend comes up offline in-container, and emitting to a fake endpoint would be dishonest (mirrors the DW-C1-1 live-Dagster-schedule and DW-D3-1 live-LLM-backend attended bring-ups). Because the emitters are already injectable, the follow-up is a substrate swap (construct an env-driven provider/client in `settings.py` or a factory and inject it), not an instrumentation change. Do NOT wire a live endpoint into the default path or weaken the offline fixture gate to require a backend.
  evidence: `tests/observability/test_observability_fixtures.py` drives a real two-node SequentialRunner pipeline (plus the pipeline-level hooks, as KedroSession fires them) with an in-memory OTel span exporter + a capturing OpenLineage client (`make_capturing_client`) and asserts the emitted event/span SHAPE — START+COMPLETE per node, input/output lineage edges, shared runId, the rowCount + rows/latency(`>=0`)/cache-hit facets, and the nested pipeline→node→dataset span tree in one trace — these captured fixtures ARE the gate (AD-20). Edge cases proven: `on_node_error` emits FAIL + closes the span (no leak, ERROR status), no-input/output nodes, empty-frame rows=0, non-DataFrame output degrades (rowCount omitted, no crash), the None-captor default path runs the full lifecycle without emitting/crashing, nested pipeline frames close without leaking, and no now()/uuid leaks into any asserted field. `test_no_inline_io.py::test_observability_libs_only_in_observability` pins the single-seam containment. `AtlasObservabilityHooks.__getstate__` drops the un-deepcopyable OTel tracer so C1's translator can deep-copy the settings HOOKS (the copy rebuilds a lazy default tracer). No socket is bound and no exporter reaches a network in any test (offline).

  status: open

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. No live collector or backend was wired. The emitters remain injectable with no-op defaults, and no env-driven `TracerProvider`/OpenLineage client construction was added to `settings.py` or a factory. The offline fixture gate is intact and no fake endpoint was introduced.
## DW-E2-2 — Dagster-plane observability inheritance verification + span-key footgun (bring-up)

- source_spec: `e2-integrate-openlineage-opentelemetry.md`
  summary: The AD-23 claim "the Dagster plane inherits the settings-registered observability hook, nested" is verified for the KEDRO plane (fixture gate) but NOT yet for the Dagster plane — the C1 live bring-up (DW-C1-1) is where a real kedro-dagster run confirms parent→node→dataset span nesting + cache_hits survive the translator's per-run hook deepcopy. The deepcopy asymmetry (a dropped OTel provider) is FIXED in E2 (`__deepcopy__` shares _provider + _ol by reference; regression test `test_deepcopy_preserves_injected_backends_no_otel_ol_asymmetry`), so a future injected exporter reaches both planes — but the end-to-end Dagster-plane assertion still rides on the deferred daemon bring-up. Also latent (Reviewer-B finding 2): `_nodes` is keyed by `node.name`; two in-flight runs of the same node name would overwrite/leak state — impossible under Kedro's unique-names-per-pipeline + DAG-ordered runners today, but a `(node.name, run_id)` key would remove the footgun if a future runner violated that. Not reachable now.
  evidence: E2 gate drives a SequentialRunner + manual before/after_pipeline_run; `dagster definitions validate` passes but does not RUN nodes. Thread-safety: `_nodes`/`produced` are unlocked — correct under SequentialRunner + C1 in_process executor (DAG-ordered), a ThreadRunner/ParallelRunner would need locking.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — and residual (1) of DW-AD23-2 shows why it cannot yet be checked. `observability.py:308-311` still declares `run_result` on `AtlasObservabilityHooks.after_pipeline_run`, which is exactly the signature kedro-dagster omits — so the Dagster after-op still raises there, and the Dagster-plane nesting assertion this entry owes remains unmakeable until both that and the DW-C1-1 daemon bring-up land. The `_nodes`-keyed-by-`node.name` footgun is likewise still unreachable, hence untouched.
## DW-E2-3 — AtlasNodeMetricsRunFacet provenance stamp (cosmetic)

- source_spec: `e2-integrate-openlineage-opentelemetry.md`
  summary: The custom `atlasNodeMetrics` run facet is emitted without an explicit `producer=PRODUCER`, so its `_producer` defaults to the OpenLineage library URI rather than the project PRODUCER every other emitted facet carries (Reviewer-A nice-to-have). Cosmetic — the metric VALUES (rows/latency_ms/cache_hits) are correct; only the facet's provenance-stamp URI differs. Left untouched to avoid perturbing the attrs RunFacet inheritance; revisit if lineage-provenance consistency is ever asserted.
  evidence: `AtlasNodeMetricsRunFacet` construction on the COMPLETE event does not pass producer; the standard rowCount + errorMessage facets do.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — measured: zero `producer=` arguments appear in the `AtlasNodeMetricsRunFacet` construction in `observability.py`, so its `_producer` still defaults to the OpenLineage library URI rather than the project PRODUCER. Cosmetic, as recorded — the metric values are unaffected.
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

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. The benchmark never ran, and its own precondition is unmet: B4 retirement (DW-B4-2) is still blocked on an unsigned `human_sign_off` (`parity/evidence.py:51`). The always-on offline half — the DuckDB-singularity grep gate — is intact.
## DW-F2-1 — the Great Expectations boundary adapter (version-capped at cf 1.18.2) — DEFERRED

- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story F2, FR-10, AD-9)
  summary: F2 shipped the load-bearing, buildable-now half of the data-validation surface — `validation.py` as the SINGLE validation seam: a validator-agnostic `Validator` protocol (a backend REPORTS `ContractViolation`s, never halts itself, so the hook owns the raise+alert in ONE place and a new backend needs ZERO node/hook edits — AC-3), the shipped inline `PanderaValidator` (per-dataset `DataFrameSchema` registry `DEFAULT_CONTRACTS`, declared as DATA never inline in nodes), and `DataValidationHooks` registered ONCE in `settings.HOOKS` (AD-23) so EVERY entry point validates — firing in `after_node_run`, the verified kedro-1.5.0 pre-persist point (`Task._call_node_run` calls `after_node_run` with the full outputs dict BEFORE the runner save loop), raising a native `DataContractViolation` that halts before ANY output persists and, on the way out, emits an `AtlasAlert` on E1's real A2A channel (AD-20, `build_alert_payload` → injected `alert_sink` → `hand_off`/`AuthoringInbox`). The DEFERRED half is the **Great Expectations boundary adapter**: AD-9 caps GX at conda-forge **1.18.2** semantics (no ≥1.19 features), but the in-env GX is **1.19.0** and cannot be *statically guaranteed* to stay within 1.18.2-only features, so — per AD-9's explicit preference — the shipped hook path imports **NO** `great_expectations` at all. `GreatExpectationsBoundaryValidator` is a protocol-conforming STUB (its `check` raises `NotImplementedError` with this DW note) that proves the seam ACCEPTS a GX backend with zero node changes; the real adapter is deferred to an environment where GX is pinned to 1.18.2, at which point the stub is replaced by a 1.18.2-feature-only adapter and slotted into the same `validators=[...]` list — no node/hook change (the point of the seam). The `kedro-great-expectations` / `kedro-pandera` plugins stay BANNED everywhere (the hook is hand-rolled). Do NOT import GX into the shipped path or lift the 1.18.2 cap to unblock this.
  evidence: `tests/validation/test_validation_hook.py` drives a real one-node SequentialRunner pipeline with a persistence-tracking dataset and asserts the F2 behaviours: a malformed payload (PyPI frame missing `version`) HALTS via a native `DataContractViolation` with the output NOT persisted (save loop never ran), emitting an `AtlasAlert` (severity critical + rule `pandera_schema` + evidence naming the column) delivered over the real A2A channel (`hand_off` → `AuthoringInbox`, round-trip-identical); a valid payload passes AND persists (no false halt); a STUB second validator halts the SAME node with zero node edits (AC-3 validator-agnosticism), and a stub-only config proves pandera is not special; the GX boundary stub raises with the 1.18.2 DW note; `test_no_inline_io.py::test_banned_validation_plugins_nowhere` + `test_no_great_expectations_in_shipped_validation_path` pin AD-9. Edge cases proven: no registered contract → pass-through; non-frame output skips gracefully (no crash); empty-frame conformant passes / missing-column halts; a broken validator halts loudly (never silently passes bad data); the default no-op sink and a RAISING sink both never mask the halt; a multi-output node halts before ANY output persists; the default hook is deepcopy-safe (C1 translator copies `settings.HOOKS`); and co-registration with the E2 observability hook still halts order-independently. `DEFAULT_CONTRACTS` ships EMPTY (machinery + seam, nothing speculative) so the settings-armed hook can never false-halt a real run until a contract is declared. No socket is bound and no network is touched in any test (offline).

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and the cap is still correctly held. `validation.py:220-226` still documents that 'The in-env GX is 1.19.0' against the AD-9 1.18.2 cap and that 'this stub is replaced by a 1.18.2-feature-only adapter' only in a pinned environment. No `great_expectations` import was added to the shipped path — the ban held.
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

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and still MOOT for exactly the stated reason. `settings.py:57` still constructs `DataValidationHooks()` with NO `alert_sink`, and `validation.py:74` still declares `DEFAULT_CONTRACTS: dict[str, pa.DataFrameSchema] = {}` — empty, so no violation can fire and no alert can be dropped yet. The gating condition the entry names (F4 registering the first real contract) has not occurred.
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

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `rag/embedding.py` still ships `HashingEmbedder` as the default (described at `:57` as 'Pure + deterministic'), and `rag/__init__.py:4-5` still records that 'The default embedder is deterministic + offline'. No learned model was wired; the `Embedder` Protocol seam is ready and unused.
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

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the split is intact: `rag/store.py::load_vss_offline` still does an offline LOAD or raises `VssNotProvisionedError`, and `provision_vss` remains the only INSTALL, never called by the consumer path (`rag/__init__.py:5` documents `vss` being LOADed from the local cache). The clean-environment provisioning step remains attended.
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

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `wasm/index.html:70` still fetches a single flat Parquet (`fetch("./core_feedstock_health.parquet")`) and renders the query result, with no Pyodide runtime and no Vizro component tree anywhere in the artifact. The query surface the render would sit on is proven; the render itself was never attempted.
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

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and currently live: `wasm/build/` does NOT exist in this checkout (`ls wasm/build` → No such file or directory), so `wasm-smoke` would take exactly the documented not-built skip path right now. No automatic `wasm-build` CI pre-step was wired, so the two-step build→verify flow is still the only way to run the gate.
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

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. No publish code exists to have run: grepping `publish/emitter.py` for `gh-pages`, `github.io` or `push` returns nothing, so the emitter is still host-agnostic by construction and no credential/host/push path was added. The live publish remains one of the five attended boundary events.
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

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the two layouts are still independent. `wasm/index.html:70` still hardcodes `fetch("./core_feedstock_health.parquet")` and contains no reference to `manifest.json` or `chunk_url`, so G1 has not migrated onto the emitter's single-owner published layout. As recorded, this is best done with the DW-G2-1 bring-up.
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

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. The sensors still ship STOPPED — `orchestration/definitions.py:301` `SENSOR_DEFAULT_STATUS = dg.DefaultSensorStatus.STOPPED`, applied at `:492` and `:583`, with `:576` stating 'Ships STOPPED' outright. No daemon was brought up; the definitions and their eval logic remain verified offline only.
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

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. Verified from the code's own statement of fact: `factory/storage.py:6` still reads '**Only the MinIO *Python SDK* is in-env today; the MinIO *server* is NOT provisioned**'. No server provisioning or bring-up has occurred. Also carried as PRD § 6.4 DC-3.
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

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. No agno/LLM synthesis bring-up happened — `factory/__init__.py:11` still describes the agno crews as future work ('adds the agno crews'), and the F3 `vss` production retriever depends on DW-F3-2's attended provisioning, still open. Carried as PRD § 6.4 DC-5/DC-6.
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
    `None` unless BOTH env vars are set. Story 16.1
    (`../implementation-artifacts/spec-16-1-instance-deploy-definition.md`) resolved the parent
    SPEC's deployment-substrate open question: django-lasuite 0.0.26 is confirmed live on the real
    conda-forge channel, Wagtail 7.4.1 has a working recipe in this repo but its upstream feedstock
    status is unconfirmed, no container. It also resolves the DW-H1 dependency question for the
    LOCAL-REHEARSAL scope only — SQLite satisfies Story 16.2's local rehearsal instance; this
    entry's own PostgreSQL/MinIO assumption for the ATTENDED PRODUCTION bring-up above is
    unchanged and still owed to DW-H1. The definition is documentation only — this entry stays
    open until the live bring-up itself runs.

  status: open

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. No live La Suite/Wagtail server, credential or httpx opener was stood up; `factory/__init__.py:11` still lists the CMS sync as H3's future scope. Carried as PRD § 6.4 DC-4.

  annotation: 2026-08-15 (Story 16.2,
    `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-16-2-httpx-opener-and-rehearsal.md`)
    — a real httpx-backed `Opener` builder + CLI entrypoint
    (`src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py`) now exists, plus an offline
    rehearsal (`tests/factory/test_lasuite_live_rehearsal.py`) proving that SAME opener drives the
    mock-proven create/update/idempotent-skip/resume sequence over a loopback HTTP stub. The
    script refuses to report success unless it genuinely reached the CMS (it probes
    `list_documents()` before exiting 0), so the attended run cannot close this entry on a
    hollow pass. The attended DW-H3 bring-up checklist — which will run this exact script against
    a real Wagtail/La Suite server — is documented in that spec's Design Notes. Still ATTENDED,
    still not executed: `status` stays `open`; DW-H3 closes only when the real bring-up runs and
    passes.

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

  verified: 2026-07-30 — This is an ATTENDED wave-boundary event, so verification asks whether the event happened — it has not. The factory-crew daemon was never brought up. Its sensor half ships STOPPED with the rest (`definitions.py:301`/`:583`), and its two data dependencies — the live wiki store (DW-H1) and the agno synthesis (DW-H2) — are both still open. Carried as PRD § 6.4 DC-1.
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

  verified: 2026-07-30 — CLOSURE HOLDS. The subject of the mutation testing exists and is
    covered: `src/pyforge/atlas/provenance.py` is present, and `provenance` is referenced across
    four test modules in the two suites the closure names — `tests/mcp/test_read_surface.py`,
    `tests/mcp/test_no_business_logic_in_tool_bodies.py`, `tests/mcp/test_kedro_mcp_absent.py`
    and `tests/dashboard/test_dashboard_dryrun.py`. The recorded caveat (the reviewer was not
    context-free) stands as written and is not re-litigated here.

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

  verified: 2026-07-30 — CLOSURE HOLDS, checked against the code rather than the label.
    `src/pyforge/atlas/admission.py` ships and uses `filelock` (10 references), and
    `RunAdmissionHooks` is imported at `settings.py:52` and registered as the fourth entry in
    `settings.HOOKS` at `:58` — so the CLI, the MCP `run_*` tools and the Dagster plane all
    inherit it from one registration, as the resolution claims. `settings.py:48` also records
    that the ordering comes from the hook markers, NOT from tuple position.

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

  verified: 2026-07-30 — CONFIRMED STILL OPEN — all four residuals verified individually, and residual (1) is live today. (1) `observability.py:308-311` still declares `run_result: dict[str, Any]` on `AtlasObservabilityHooks.after_pipeline_run`, the exact parameter kedro-dagster omits, so the Dagster after-op still raises `HookCallError` there. (2) `conf/base/dagster.yml:18-19` still declares the `in_process` executor, and `:8` carries the inline warning '`in_process` IS LOAD-BEARING FOR RUN ADMISSION (Story 10.6, AD-23; DW-AD23-2)' — the coupling is documented at the point of change, as the resolution asked. (3) and (4) follow from the same unchanged structure. The load-bearing mitigation is intact: `admission.py` carries 9 `tryfirst` markers, which the entry records as what buys the ordering — not tuple position.

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

  verified: 2026-07-30 — PART (b) IS NOW RESOLVED, in another project's code. The
    `max_followup_reviews` policy question was settled by seeding the value in Marshal's
    `DEFAULT_POLICY`: `pyforge-marshal/src/pyforge/marshal/core/policy.py:150` now declares
    `"max_followup_reviews": 2`, and the ten comment lines at `:141-150` name this exact
    incident as the reason — "A cap of 1 damped five still-recommended follow-up reviews across
    three projects (atlas 10.5/10.6, marshal 1.1, warden 6.3/5.1) into a GITIGNORED ledger".
    Those five damped stories are `DW-I4-1` + this entry + marshal's `DW-FU-1-1` + warden's
    `DW-FU-6-3`/`DW-FU-5-1`. The placement is also the one the review demanded (a repo-wide
    home, not a project layer): marshal's station layers restate it ZERO times. Part (a) stands
    as recorded — closed by mutation testing, with the not-context-free caveat on record.

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

  verified: 2026-08-26 — resolved — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to resolved

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

  verified: 2026-07-30 — CLOSURE HOLDS, and the fix is the sibling placement, not a child.
    `admission.py:133` defines `_STORE_NAME = ".locks"` and `:131-132` documents it being
    "appended to the data root's name to make the sibling `<data_root>.locks` (the default)".
    `default_lock_root` at `:210` carries the same contract at `:225-226`: "the store is the
    data root's SIBLING -- ``<data_root>.locks``, not ``<data_root>/.locks`` (``DW-AD23-3``)".
    `:84-89` narrates the correction and confirms `PYFORGE_ATLAS_LOCK_ROOT` is REFUSED when it
    would place the store back inside the data tree.

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


## DW-FU-13-3 — 13.3 finalized on a spent follow-up-review budget (LOW) — DEFERRED

- source_spec: `spec-13-3-trending-candidates-operator-surface.md`
  found_by: bmad-loop's own damping output, run `20260809-184330-203b`, 2026-08-10
  summary: the follow-up-review damping cap (`limits.max_followup_reviews = 2`) was spent with
    the story finalized (status `done`, verify green) while the review pass still recommended
    an independent follow-up. The work was committed by that run; this entry preserves the
    lingering recommendation for a deliberate later review.
  context: 13.3 ran to the ceiling on both axes — dev attempt 2/2 and review cycle 3/3 — and
    cleared on its LAST cycle rather than escalating, which is the same profile doctor's 6.8
    showed earlier the same night. A story that finishes with zero budget left is exactly the
    one an independent pass is worth spending on.
  promoted: 2026-08-10 — promoted from Tier-3 `implementation-artifacts/deferred-work.md`
    (id `DW-3` there) under the repo-wide `DW-FU-<story>` convention already used by doctor
    (`DW-FU-6-5`/`6-6`/`6-8`), marshal (`DW-FU-1-1`) and warden (`DW-FU-6-3`/`5-1`), and
    already cross-referenced from this ledger. A generic `DW-3` would collide with the next
    damped story. Tier-3 is gitignored, so an entry only there does not survive a clone —
    Marshal FR-175 / Story 4.13 (in flight now) exists to make this promotion an obligation of
    the story rather than archaeology someone performs later.
  severity: low
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-14-2-1: get_widget() and get_view() both raise a bare, unwrapped KeyError with a confusing repr-quoted message on lookup failure
- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/spec-14-2-pluggable-widget-registry.md`
  summary: `views/widgets.py::get_widget` raises a bare `KeyError(f"unknown widget type {name!r}; known widget types: ...")`, which `KeyError.__str__` re-wraps in an extra layer of quotes on display, and which propagates uncaught with no domain-specific exception type even though the same module tree already has one precedent for that (`cli_bridge.py`'s `CfAtlasDbUnavailableError`).
  evidence: Flagged independently by both the Blind Hunter (message-quoting confusion) and the Edge Case Hunter (missing domain wrapper) reviewing Story 14.2's diff (2026-08-14). Not patched in that story because `get_widget` deliberately mirrors `views/registry.py::get_view`'s identical, already-shipped Story 14.1 pattern (`raise KeyError(f"unknown static view {name!r}; known views: ...")`) — fixing only the newer function would make the two nearly-identical lookup helpers inconsistent with each other. If ever addressed, both should change together in the same pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-14-3-1: tests/dashboard/test_dashboard_e2e.py's Playwright navigation races the Dash dev server's startup, reliably failing with net::ERR_CONNECTION_REFUSED
- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/spec-14-3-bokeh-websocket-interactivity.md`
  summary: `test_dashboard_e2e_navigation_and_rendering`'s `page.goto(dashboard_server)` fires before the Dash dev server thread has finished binding its port, so the test reliably fails with `playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED` — pre-existing in `tests/dashboard/` (Story D2's Vizro/Dash module), surfaced incidentally while verifying this story's `kedro-test` acceptance criterion, and explicitly out of this story's scope to fix (Story 14.3's Boundaries & Constraints forbid touching `dashboard/`).
  evidence: Reproduced consistently across 5+ consecutive runs, including with every one of this story's changes fully `git stash`-ed out (i.e. against the exact commit Story 14.3's implementation subagent finished on, before any review-pass patch) — the failure is identical with or without this story's diff. The captured teardown output shows `"Dash is running on http://127.0.0.1:<port>/"` logged AFTER the navigation attempt already failed, confirming a startup-order race, not a port/config mismatch. Confirmed unrelated to this story's dependency changes: the `pixi.lock` diff this story produces touches only `pyforge-atlas`'s own `conda_source` metadata (host-package platform-variant list reordering caused by the new `tornado`/`starlette` run-deps) — zero version changes to `dash`/`flask`/`werkzeug`/`playwright` anywhere in the lock diff. Likely fix: the test needs to poll for server readiness (e.g. retry-connect or hit a health endpoint) before calling `page.goto`, rather than assuming the server thread is already accepting connections immediately after being started — a `dashboard/`-scoped fix, not a `views/` one.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-14-3-2: Bokeh 3.9.2's `patch_curdoc()` context manager has no exception safety — a callback that raises corrupts `curdoc()` for the rest of the pytest process
- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/spec-14-3-bokeh-websocket-interactivity.md`
  summary: `bokeh/io/doc.py::patch_curdoc` pushes a `weakref.ref(doc)` onto the module-global `_PATCHED_CURDOCS` list, `yield`s with no `try/finally`, then pops — so any callback invoked while curdoc is patched that raises leaves the stale weakref on the stack permanently; once that `Document` is later garbage-collected, every subsequent `curdoc()` call in the SAME process raises `RuntimeError: Patched curdoc has been previously destroyed`, corrupting unrelated later tests.
  evidence: Reproduced directly while attempting to close a review-pass-2 finding (the "propagates on any later re-query" docstring claim was untested): a test that set a live session's maintainer `TextInput.value` after deleting the backing `cf_atlas.db` (to assert `CfAtlasDbUnavailableError` propagates out of the `on_change` callback) reliably poisoned the process — `tests/views/test_widgets.py::test_get_widget_grid_static_renderer_produces_a_valid_static_fragment` (and, nondeterministically, several `tests/views/test_render.py` tests) started failing with `RuntimeError: Patched curdoc has been previously destroyed` from `bokeh/io/doc.py:59`, reproducibly across 5/5 runs with the offending test present and 0/5 without it (and 3/3 clean on the unpatched pre-review commit). Root-caused by reading `bokeh/io/doc.py`: `patch_curdoc()` is a bare `@contextmanager` — `_PATCHED_CURDOCS.append(weakref.ref(doc)); del doc; yield; _PATCHED_CURDOCS.pop()` — with no `try/finally`, so an exception during `yield` skips the `pop()` forever. The offending test was reverted rather than kept — this story's own `_grid_websocket_renderer`/`_on_maintainer_change` code has no try/except and does propagate the error correctly by direct code inspection; only the TEST's mechanism was unsafe, not the shipped code. This is a genuine upstream Bokeh hazard, not this story's problem to fix (Bokeh internals, not `pyforge` code), but load-bearing knowledge for whoever next tests a live-session error path in this package: raising inside a live `on_change` callback will poison the rest of the test process.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-3-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-A1-6: The registered `[verify]` command `pixi run --frozen -e pyforge-atlas kedro-test` cannot run until the workstation re-lo
- source_spec: `a1-scaffold-the-kedro-pixi-project-via-nebi.md`
  summary: The registered `[verify]` command `pixi run --frozen -e pyforge-atlas kedro-test` cannot run until the workstation re-lock lands pixi.lock entries for the pyforge-atlas env — until then EVERY bmad-loop story (including pyforge-warden ones) fails at the verify step.
  evidence: `pixi.lock` has zero `pyforge-atlas` occurrences; `--frozen` cannot materialize an env absent from the lock; container re-lock is blocked by the stubbed `build_artifacts` channel (bmad-ui/bmad-dashboard co-solve — see Story A1 Dev Agent Record). Workstation re-lock is the recorded precondition; do not weaken the gate (NFR-12).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-A1-7: `.bmad-loop/policy.toml [scm] worktree_seed` still lists only pyforge-warden's implementation-artifacts path — an atlas 
- source_spec: `a1-scaffold-the-kedro-pixi-project-via-nebi.md`
  summary: `.bmad-loop/policy.toml [scm] worktree_seed` still lists only pyforge-warden's implementation-artifacts path — an atlas loop story's worktree (first: A3) would reproduce the documented missing-artifacts-dir crash until the seed adds `_bmad-output/projects/pyforge-atlas/implementation-artifacts`.
  evidence: policy.toml `worktree_seed = ["_bmad-output/projects/pyforge-warden/implementation-artifacts", "_bmad/custom/.active-project"]` with the adjacent comment citing crash run 20260712-164312; A3 is the designated first loop story (sprint story_meta). A1's scope note: "the worktree bootstrap is A3's to validate, not A1's" (AD-18).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-A1-8: `[verify].commands` is a flat list — every loop story in either package now materializes BOTH the pyforge-warden and pyf
- source_spec: `a1-scaffold-the-kedro-pixi-project-via-nebi.md`
  summary: `[verify].commands` is a flat list — every loop story in either package now materializes BOTH the pyforge-warden and pyforge-atlas envs and runs both suites; a red test in one package blocks the other package's loop, and A3's worktree env-materialization cost measurement will include warden's env. Consider per-project/conditional gating when A3 measures.
  evidence: `.bmad-loop/policy.toml [verify]` runs all commands after every story review; both `pixi run --frozen -e pyforge-warden pyforge-warden-test` and `pixi run --frozen -e pyforge-atlas kedro-test` are now unconditionally listed.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-A1-9: kedro-test import provenance is mixed in the lean env — smokes import the INSTALLED conda build of pyforge-atlas while `
- source_spec: `a1-scaffold-the-kedro-pixi-project-via-nebi.md`
  summary: kedro-test import provenance is mixed in the lean env — smokes import the INSTALLED conda build of pyforge-atlas while `bootstrap_project()` injects the source tree; if a frozen run ever serves a stale built package for a changed source tree, the gate could go green on old code. Verify pixi-build path-dep rebuild semantics under `--frozen` when the lean env first materializes (A3).
  evidence: `tests/test_import_smoke.py` imports `pyforge.atlas` before `bootstrap_project(MEMBER_DIR)` prepends `MEMBER_DIR/src` to sys.path; pixi-build rebuild-on-change behavior under `--frozen` is undocumented for sibling path deps (same ambiguity the warden policy comment records).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-A2-1: Dynamic per-host JFrog credential attachment does NOT exist — credential references are static per-entry catalog config,
- source_spec: `a2-define-the-data-catalog-for-all-sources-outputs.md` (review-pass P4, 2026-07-17)
  summary: Dynamic per-host JFrog credential attachment does NOT exist — credential references are static per-entry catalog config, and overriding a `*_BASE_URL` to an Artifactory mirror yields UNauthenticated requests until `credentials: jfrog` is hand-added to each mirrored entry. The dynamic attachment mechanism (attach the jfrog key iff the entry's resolved hostname suffix-matches an Artifactory host) is assigned to **Story B5** (external-refresh assets / enterprise store routing). Owner rationale per spine AD-2: credentials are catalog/dataset-level per-host config, not a global hook — so the mechanism belongs with the first story that lands a JFrog-routable dataset surface (B5), not a generic A3 hook. The member README was rewritten in the review pass to describe the static reality and name this OPEN item.
  evidence: member README § 3 formerly claimed jfrog attaches to "datasets whose endpoint-base actually resolves to an Artifactory host" — no code implements that; `tests/catalog/test_credential_scoping.py` enforces the static allowlist + suffix-matched hostnames (the guard the future mechanism must satisfy).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-A3-1: No epoch-seconds-vs-milliseconds magnitude guard on the `fetched_at` stamp/read in `IncrementalParquetDataset`. If a fut
- source_spec: `a3-implement-incrementalparquetdataset-for-ttl-gating.md` (review-pass P10, 2026-07-17)
  summary: No epoch-seconds-vs-milliseconds magnitude guard on the `fetched_at` stamp/read in `IncrementalParquetDataset`. If a future producer ever wrote ms-epoch timestamps, `stale_mask` (`fetched_at < now - ttl_seconds`, both in seconds) would silently treat every ms row as far-future-fresh. Deferred as SPECULATIVE — no ms producer exists today; the B1 node contract owns the `fetched_at` unit (Spine timestamp convention = epoch SECONDS). Revisit iff a node is authored that could emit ms.
  evidence: `stale_mask`/`save` operate purely in `int(time.time())` seconds; there is no order-of-magnitude assertion. No B-wave node yet writes these datasets (B1 is the first). Simplicity First — a guard now would be dead code.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-A3-2: `IncrementalParquetDataset` reaches into the composed dataset's PRIVATE internals — `self._inner._describe()` and `self
- source_spec: `a3-implement-incrementalparquetdataset-for-ttl-gating.md` (review-pass P11, 2026-07-17)
  summary: `IncrementalParquetDataset` reaches into the composed dataset's PRIVATE internals — `self._inner._describe()` and `self._inner._exists()` — which are not part of the kedro_datasets public API and could break on a `kedro_datasets` bump. Deferred: verified against **kedro_datasets 9.5.0** (the in-env version); both methods present with the used signatures. Revisit on the next `kedro_datasets` version bump (add a compatibility check or switch to a public accessor if one lands).
  evidence: `incremental_parquet.py` `_describe`/`_exists` delegate to `self._inner._describe()` / `self._inner._exists()`; kedro_datasets exposes no documented public equivalent for the composed-dataset describe/exists at 9.5.0.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-A3-3: One-tick TTL boundary parity is UNVERIFIED against the legacy gate. Legacy `atlas_phase` treated a row as stale when `ag
- source_spec: `a3-implement-incrementalparquetdataset-for-ttl-gating.md` (review-pass, TTL-parity, 2026-07-17)
  summary: One-tick TTL boundary parity is UNVERIFIED against the legacy gate. Legacy `atlas_phase` treated a row as stale when `age >= ttl` (stale at EXACTLY ttl); the new `stale_mask` uses `fetched_at < now - ttl_seconds`, i.e. a row stamped exactly `now - ttl` is FRESH (the current unit test pins boundary=fresh). Whether the off-by-one-tick difference matters is a B1 verification item — B1 (first phase-port that writes these datasets) should confirm the intended edge against legacy parity evidence and adjust the comparison (`<=` vs `<`) if parity requires it.
  evidence: `test_stale_mask_gates_old_stale_recent_fresh` asserts `now - ttl` → fresh; legacy `_TTL_GATED` semantics (cf-atlas-legacy `write-paths-and-checkpoints.md`) gate on `>= ttl`. Non-blocking for A3 (the dataset owns a self-consistent, tested boundary); flagged so B1 makes the parity call deliberately.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-4-1: A future pandera `Column(str)` contract registered in `DEFAULT_CONTRACTS` (`validation.py`) will spuriously halt on a le
- source_spec: `_bmad-output/implementation-artifacts/spec-10-4-preserve-null-identity-under-pandas-3-0.md`
  summary: A future pandera `Column(str)` contract registered in `DEFAULT_CONTRACTS` (`validation.py`) will spuriously halt on a legitimately EMPTY, naturally-`object`-dtype DataFrame — pandera dtype-checks an empty column's literal declared dtype (no values to infer from), and it always expects `string[pyarrow]` there, independent of this package's `future.infer_string` pin.
  evidence: reproduced directly in this worktree's pinned pandas 3.0.3 / pandera env — `PYPI_SCHEMA.validate(pd.DataFrame({"name": pd.Series([], dtype=str)}))` raises `WRONG_DATATYPE: expected string[pyarrow], got object` under the pin, while an identically-constructed NON-empty frame (`pd.DataFrame({"name": ["numpy"]})`, also `object` dtype) validates fine. Confirmed independently by both the Blind Hunter and Edge Case Hunter review passes on this story's diff. Dormant today only because `DEFAULT_CONTRACTS` ships empty; the first real `Column(str)` contract that can see an empty result set will hit this.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-4-2: `pyforge.atlas/__init__.py`'s `future.infer_string` pin is process-wide mutable pandas state, not scoped to this package
- source_spec: `_bmad-output/implementation-artifacts/spec-10-4-preserve-null-identity-under-pandas-3-0.md`
  summary: `pyforge.atlas/__init__.py`'s `future.infer_string` pin is process-wide mutable pandas state, not scoped to this package — any OTHER package sharing the same Python process (e.g. a future shared Dagster/MCP deployment importing multiple `pyforge-*` packages together) inherits the pin the moment `pyforge.atlas` is imported first, with no opt-out; conversely, if some OTHER package's own DataFrame construction runs before `pyforge.atlas` is ever imported in that process, it is NOT covered by the pin.
  evidence: `pd.set_option` mutates global `pandas.options` state with no per-caller scoping; verified the `pyforge-atlas` `kedro-test` task only collects `src/shared/packages/pyforge-atlas/tests` today so this is not currently exercised, but it is a real cross-package coupling risk for the monorepo's future shared-process deployments. Flagged by the Blind Hunter and Edge Case Hunter review passes on this story's diff; worth a scoped (`pd.option_context`) redesign in a future consistency pass if/when `pyforge-*` packages start sharing a process.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-4-3: `ci_red`'s business logic is duplicated as raw SQL outside the declared-once `semantic/metrics.py` definition — `wasm/in
- source_spec: `_bmad-output/implementation-artifacts/spec-10-4-preserve-null-identity-under-pandas-3-0.md`
  summary: `ci_red`'s business logic is duplicated as raw SQL outside the declared-once `semantic/metrics.py` definition — `wasm/index.html` projects `(ci_status IN ('failure','error')) AS ci_red` and `tests/publish/test_emit_range.py` re-encodes it as a `FILTER (WHERE ...)` — and the AUD-ATLAS-012 NULL-coalesce (`.fill_null(False)`) now exists only in the metrics.py copy, so the surfaces agree on a NULL `ci_status` only through downstream accidents.
  evidence: `semantic/metrics.py`'s module discipline (AD-8) says business logic "is declared ONCE here"; the WASM projected column yields SQL NULL for a NULL `ci_status` (rendered not-red only because the row renderer checks `=== true || === 1`), and the publish test's raw FILTER relies on SQL's NULL-excludes behavior. No behavioral divergence today, but the next consumer of the projected `ci_red` column (or an edit to the WASM row-rendering) silently inherits the un-coalesced semantics. Found by the Blind Hunter review pass on story 10-4's diff (2026-07-28, review pass 2).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-5-1: The dashboard's per-page AD-17 provenance is resolved once at `build_dashboard()` time while each page's grid data is a 
- source_spec: `_bmad-output/implementation-artifacts/spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`
  summary: The dashboard's per-page AD-17 provenance is resolved once at `build_dashboard()` time while each page's grid data is a lazily-registered `data_manager` loader re-invoked per render — in a long-running server, the Card's stated provenance can drift out of sync with the (independently, live-reloaded) grid data it describes.
  evidence: `dashboard/app.py::build_dashboard` calls `_provenance.resolve_for_file(...)` synchronously before constructing the page list, while `_data_page`'s `loader` closure genuinely re-reads the backing Parquet on each `data_manager` invocation. This mirrors the SAME pre-existing pattern `factory-status`'s own `build_stamp` already uses (out of scope to change per this story's Never boundary) — this story's own prior (reverted) attempt already triaged the identical finding as `[low][defer]` ("pre-existing, extended by this story"). Independently re-surfaced by both Blind Hunter and Edge Case Hunter on review pass 2.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-5-2: `provenance.py`'s `resolve_for_catalog_dataset` reaches into kedro's underscore-prefixed `_describe()` (`"filepath"`, `"
- source_spec: `_bmad-output/implementation-artifacts/spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`
  summary: `provenance.py`'s `resolve_for_catalog_dataset` reaches into kedro's underscore-prefixed `_describe()` (`"filepath"`, `"fetched_at_column"`) with no fallback if a future `kedro_datasets`/`IncrementalParquetDataset` change restructures that dict, and does not isolate provenance-dispatch failures from an already-successful `catalog.load(name)` — a `_describe()` KeyError or similar would crash the whole `read_dataset` call even though the data load itself succeeded.
  evidence: `_describe()` is a protected, non-semver-guaranteed introspection hook on third-party dataset classes; verified stable under the currently-installed `kedro_datasets` version but with no defensive fallback. Flagged by the Blind Hunter review pass on story 10-5's diff (2026-07-28, review pass 2).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-5-3: `resolve_for_catalog_dataset`'s `ParquetDataset` branch uses `dataset._describe()["filepath"]` unconditionally, which fo
- source_spec: `_bmad-output/implementation-artifacts/spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`
  summary: `resolve_for_catalog_dataset`'s `ParquetDataset` branch uses `dataset._describe()["filepath"]` unconditionally, which for a Kedro-versioned dataset (`versioned: true`) is the un-versioned base path, not the actually-loaded version's file — the reported mtime could describe the wrong file. No current `catalog.yml` entry sets `versioned: true` on a `pandas.ParquetDataset`, so this is latent.
  evidence: Flagged by the Edge Case Hunter review pass on story 10-5's diff (2026-07-28, review pass 2); not reproducible against the live catalog today.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-5-4: The dashboard's `_provenance_line` never renders `ProvenanceInfo.build_stamp_newest`, so a future dashboard page wired t
- source_spec: `_bmad-output/implementation-artifacts/spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`
  summary: The dashboard's `_provenance_line` never renders `ProvenanceInfo.build_stamp_newest`, so a future dashboard page wired to a `row-fetched-at`-kind dataset (none exist today — all 3 grounded/bsl-shell pages resolve via `resolve_for_file`, never `resolve_for_catalog_dataset`) would silently drop the "newest recorded" half of its provenance range from the rendered Card.
  evidence: `app.py::_provenance_line` only formats `provenance.build_stamp`; confirmed no dashboard page currently reaches the `row-fetched-at` kind. Independently flagged by both Blind Hunter and Edge Case Hunter on review pass 2.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-5-5: `resolve_for_catalog_dataset`'s kind dispatch covers 61 of the catalog's 86 entries; 8 of the remaining 25 (7 `json.JSON
- source_spec: `_bmad-output/implementation-artifacts/spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`
  summary: `resolve_for_catalog_dataset`'s kind dispatch covers 61 of the catalog's 86 entries; 8 of the remaining 25 (7 `json.JSONDataset` + 1 `yaml.YAMLDataset`) expose a `filepath` + `protocol` pair in `_describe()` that is byte-identical in shape to what the existing `ParquetDataset` branch already consumes, so genuine file-mtime provenance is available for them and is reported as `unavailable` instead.
  evidence: live type census of `conf/base/catalog.yml` — 24 `api.APIDataset`, 22 `pandas.ParquetDataset`, 15 `IncrementalParquetDataset`, 7 `json.JSONDataset`, 5 `MigrationCategoryDataset`, 1 `yaml.YAMLDataset`, 1 `partitions.PartitionedDataset`, 10 other custom types; `JSONDataset(filepath=...)._describe()` returns `{'filepath': PurePosixPath(...), 'protocol': 'file', 'save_args': ..., 'version': None}`. NOT a defect against the frozen contract — the intent-contract's I/O matrix explicitly specifies `json.JSONDataset` -> `unavailable` — so this is a coverage EXTENSION for a later pass, not a deviation. Flagged by the Blind Hunter review pass on story 10-5's diff (2026-07-29, review pass 4).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-5-6: Three catalog entries (`AnacondaDownloadsDataset`, `GitHubRequestDataset`, `PyPIJsonRequestDataset`) perform a real live
- source_spec: `_bmad-output/implementation-artifacts/spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`
  summary: Three catalog entries (`AnacondaDownloadsDataset`, `GitHubRequestDataset`, `PyPIJsonRequestDataset`) perform a real live HTTP fetch on read but report `provenance_kind="unavailable"`, because they COMPOSE `kedro_datasets.api.APIDataset` rather than subclass it, so the `isinstance(dataset, APIDataset)` live-fetch branch never matches — the one case where "now" is provably correct provenance by this module's own rule.
  evidence: `src/pyforge/atlas/datasets/request_datasets.py` — `_RequestParameterizedAPIDataset(AbstractDataset)` holds `self._inner` (an `APIDataset`) and its `load()` is `self.scheduler.acquire(); return self._inner.load()`. The module already recognises this exact compose-not-subclass shape for `IncrementalParquetDataset` (which likewise composes `ParquetDataset`); the reasoning was simply not carried to the API branch. Contract-valid today (C4 makes `unavailable` + a reason a REQUIRED valid response), so this is a coverage EXTENSION, not a deviation. Flagged by the Blind Hunter review pass on story 10-5's diff (2026-07-29, review pass 4).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-5-7: The dashboard and the MCP read surface resolve the SAME logical dataset's backing file through two independent path mech
- source_spec: `_bmad-output/implementation-artifacts/spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`
  summary: The dashboard and the MCP read surface resolve the SAME logical dataset's backing file through two independent path mechanisms — the dashboard via `dashboard/data.py`'s hand-maintained relpath constants anchored on `default_data_root()` (which walks up to `.git`), the MCP surface via the catalog's bare relative `filepath:` (resolved against the process CWD) — so the two surfaces can stamp different files, or one can report a real mtime while the other reports "backing file not found".
  evidence: `dashboard/data.py:27` already labels its constants a hand-maintained MIRROR of the catalog `filepath`s, and `default_data_root()`'s own docstring records the CWD-relative catalog default (review-pass P9); `conf/base/catalog.yml:157` declares `filepath: data/primary/core_feedstock_health/core_feedstock_health.parquet` with no `${globals:...}` templating. Each surface is INTERNALLY consistent (each stamps the same file it loads), so nothing is wrong today when both run from the repo root — this is the pre-existing mirror divergence made newly VISIBLE by stamping, not a defect introduced by this story. Worth collapsing onto one catalog-driven resolver in a later consistency pass. Flagged by the Blind Hunter review pass on story 10-5's diff (2026-07-29, review pass 4).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-5-8: Reusing `IncrementalParquetDataset._to_epoch_seconds` on the READ path makes its `logger.warning` ("normalizing N ms-mag
- source_spec: `_bmad-output/implementation-artifacts/spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`
  summary: Reusing `IncrementalParquetDataset._to_epoch_seconds` on the READ path makes its `logger.warning` ("normalizing N ms-magnitude fetched_at value(s) …", written for the once-per-`save()` write boundary) fire on EVERY `read_dataset` of a ms-magnitude dataset — log noise proportional to read volume on datasets as large as `core_downloads`.
  evidence: `datasets/incremental_parquet.py:202-209` — the warning is unconditional inside `_to_epoch_seconds`, which has no `warn=` parameter; `provenance.py::_resolve_row_fetched_at` calls it per read. Observed firing during review-pass-4 verification runs. Deliberately NOT patched in-pass: the spec's Design Notes mandate reusing `_to_epoch_seconds` DIRECTLY ("not reimplemented, so the two stay in lockstep by construction"), so the only clean fix adds a `warn: bool = True` parameter to a shared dataset classmethod — a wider blast radius than a review patch should take unilaterally. Flagged by the Blind Hunter review pass on story 10-5's diff (2026-07-29, review pass 4).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-6-1: `AtlasObservabilityHooks.__deepcopy__` (and any hook copying this pattern) hand-copies a fixed list of attributes via `c
- source_spec: `_bmad-output/implementation-artifacts/spec-10-6-make-run-admission-real-or-stop-claiming-it.md`
  summary: `AtlasObservabilityHooks.__deepcopy__` (and any hook copying this pattern) hand-copies a fixed list of attributes via `cls.__new__`, so a future `__init__` field silently vanishes from the Dagster-plane clone and surfaces as an `AttributeError` at run time rather than at build time.
  evidence: `observability.py:210-229` copies exactly `_provider` / `_ol` / `_namespace` / `_tracer_cache` / `_pipelines` / `_nodes`; nothing asserts the copied attribute set matches `__init__`'s. Surfaced while reviewing Story I5's new hook, which necessarily mirrors the same pattern. A single test comparing `vars(hook).keys()` before and after `copy.deepcopy` would cover every hook at once.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-6-2: Run admission is writer-writer exclusion only, and the concurrency it deliberately PERMITS is reader-writer unsafe: `pan
- source_spec: `_bmad-output/implementation-artifacts/spec-10-6-make-run-admission-real-or-stop-claiming-it.md`
  summary: Run admission is writer-writer exclusion only, and the concurrency it deliberately PERMITS is reader-writer unsafe: `pandas.ParquetDataset.save` truncates its target in place (no temp+rename), so a pipeline admitted concurrently because its OUTPUT set is disjoint can read a half-written Parquet another admitted run is rewriting. Not a defect in Story 10.6 — the hazard predates it and the story strictly reduces interleaving — but AD-23's per-dataset-set granularity is now documented as a feature ("genuinely disjoint pipelines still run concurrently"), which makes the reader-writer gap the natural next thing a reader will over-assume.
  evidence: measured against the live registry — the 7 pipelines share no output name (so the granularity claim is literally true) but carry 12 cross-pipeline write→read edges: `core` writes `core_downloads` / `core_packages_enumerated` / `core_version_download_history` which `vcs_health` and `vulnerability` read; `pypi_intelligence` writes `pypi_conda_mapping` / `pypi_intelligence_enriched` which `seed_gaps` reads; `vulnerability`→`seed_gaps`; `derived_artifacts`→`universal_sbom`. `core_packages_enumerated` is a `pandas.ParquetDataset`, whose `save` is `with self._fs.open(save_path, "wb"): data.to_parquet(...)`. Closing it means either atomic writes (temp + rename) at the dataset layer or extending admission to lock a pipeline's INPUT set as a shared/read lock — both wider than an admission story. Flagged by the Blind Hunter review pass on story 10-6's diff (2026-07-29, review pass 3).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-6-3: `observability.py` states, in three places, that "C1's `KedroProjectTranslator` deep-copies the settings hooks at `to_da
- source_spec: `_bmad-output/implementation-artifacts/spec-10-6-make-run-admission-real-or-stop-claiming-it.md`
  summary: `observability.py` states, in three places, that "C1's `KedroProjectTranslator` deep-copies the settings hooks at `to_dagster()` build time" — and the installed kedro-dagster does not. The lazy-`TracerProvider` design at `observability.py:188-195` exists specifically to make the instance deepcopy-able for that build, so its stated justification is unfounded (the design is harmless, but it is carried as a measured constraint when it is not one).
  evidence: measured against the installed `kedro_dagster` 0.7.x in the `pyforge-atlas` env — `translator.py:253,262` pass `hook_manager=self._context._hook_manager` BY REFERENCE, and the only `deepcopy` anywhere in the package is in `datasets/partitioned_dataset.py` (`grep -rn deepcopy` over the installed tree). Pre-existing and untouched by Story 10.6; surfaced because the new `RunAdmissionHooks.__deepcopy__` copied the same claim verbatim (corrected there in review pass 4). Not patched here: `observability.py` is E2-owned and out of this story's scope, and the lazy-tracer construction should not be re-litigated on a review pass. Flagged by the Blind Hunter review pass on story 10-6's diff (2026-07-29, review pass 4).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-1-1: Unconfirmed whether `src/shared/packages/pyforge-atlas/.claude/skills/catalog-config/` — the first nested, directory-sco
- source_spec: `spec-12-1-kedro-skills-audit-then-adopt.md`
  summary: Unconfirmed whether `src/shared/packages/pyforge-atlas/.claude/skills/catalog-config/` — the first nested, directory-scoped `.claude/skills/` tree anywhere in this repo — is actually discovered by a live Claude Code session working inside that subtree, versus this repo's established single-root `.claude/skills/` convention being the only path Claude Code reliably surfaces.
  evidence: `kedro skills install` has no `--target-dir` (confirmed by reading `kedro_skills/utils.py::find_project_root`, which always resolves the nearest Kedro project root) so this is the tool's only possible output location; the Skill tool's own description documents directory-scoped resolution (`apps/web:deploy`-style path prefixes) as a real capability, but this review session's own available-skills listing (generated from the repo root, same worktree) does not surface `catalog-config`, which is at minimum consistent with (though not proof of) the mechanism not statically preloading nested skill trees. Flagged by the Blind Hunter review pass on story 12-1's diff (2026-08-09, review pass 1); re-raised independently by the Blind Hunter pass on review pass 2 with the same evidence.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-1-2: The two upstream-issue texts drafted in `kedro-skills-audit-report.md` (layer-tag nesting; the numbered 8-layer director
- source_spec: `spec-12-1-kedro-skills-audit-then-adopt.md`
  summary: The two upstream-issue texts drafted in `kedro-skills-audit-report.md` (layer-tag nesting; the numbered 8-layer directory table) have no tracked follow-up forcing a human to actually decide whether to file them against `kedro-org/kedro-skills` — they exist only as prose inside the report and could go unnoticed once nobody is actively reading it.
  evidence: The story's own Never clause correctly forbids filing them unattended (verified: `gh api repos/kedro-org/kedro-skills/issues` shows only the 3 pre-existing issues, none from this story), but nothing else tracks the pending human decision. Converged finding — raised independently by both Blind Hunter and Edge Case Hunter on review pass 1, and again by both on review pass 2, with no new counter-evidence either time.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-1-3: The live `sprint-status.yaml`'s `story_meta.depends_on` lists still reference the retired `d1-`/`d2-` key spelling for E
- source_spec: `spec-12-1-kedro-skills-audit-then-adopt.md`
  summary: The live `sprint-status.yaml`'s `story_meta.depends_on` lists still reference the retired `d1-`/`d2-` key spelling for Epic 5's stories (lines ~381, ~394, ~471), even though PR #322 (2026-08-08) renamed the corresponding `development_status` keys to the current `5-1-`/`5-2-` Epic.Story convention — so any future code resolving `depends_on` entries against `development_status` keys would silently fail to match.
  evidence: `grep -n "depends_on:.*d[12]-" _bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml` hits 3 lines still spelling `d1-define-the-boring-semantic-layer-bsl-models` / `d2-build-the-vizro-dashboard-port-the-28-clis-to-pages`, while `development_status` itself now keys the same two stories `5-1-...`/`5-2-...` (confirmed identical between this worktree and the canonical repo checkout). No shipped code currently reads `depends_on` from this file (`grep -rn depends_on src/shared/packages/pyforge-atlas/src/` is empty) so nothing is broken today — inert but drift-prone. Surfaced by the Blind Hunter review pass repairing story 12-1's `kedro-test` verification failure (2026-08-09); out of that repair's scope since `sprint-status.yaml` is a generated, gitignored artifact PR #322 didn't fully sweep.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-2-1: `kedro-viz-publish.yml`'s trigger path filter (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**` only, 
- source_spec: `spec-12-2-publish-the-real-dag-continuously.md`
  summary: `kedro-viz-publish.yml`'s trigger path filter (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**` only, matching the upstream epic-level Spec's literal wording) won't catch a real DAG-shape change made via `pipeline_registry.py`, `settings.py`, or `conf/base/catalog.yml`/`parameters.yml` — none of which live under `pipelines/`, so a change to any of them lands on `main` without triggering a republish.
  evidence: Verified these files exist outside the triggering path glob (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py`, `.../settings.py`, `.../conf/base/catalog.yml`, `.../conf/base/parameters.yml`) and each can independently change what `kedro viz build` renders (registry controls which pipelines exist; catalog controls dataset/layer metadata). Not fixed in this story: the path is a faithful, literal implementation of the upstream `SPEC-kedro-org-tooling-adoption` kernel's own named trigger path (`_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption/SPEC.md`), so widening it unilaterally would be a scope decision belonging to that Spec, not this story. Flagged by the Blind Hunter review pass on story 12-2's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-2-2: `kedro-viz-publish.yml` pushes directly to `main` with the default `GITHUB_TOKEN` and no PR; if branch protection is eve
- source_spec: `spec-12-2-publish-the-real-dag-continuously.md`
  summary: `kedro-viz-publish.yml` pushes directly to `main` with the default `GITHUB_TOKEN` and no PR; if branch protection is ever added to `main` (none exists today), the workflow will start failing silently (a red run, no code change needed to explain it) with nothing in this diff anticipating that dependency.
  evidence: Verified via `gh api repos/rxm7706/local-recipes/branches/main/protection` → 404 (not protected) at spec time. The workflow's own design (mirrors `steward deploy dashboard`'s CLI, built for direct-push use) has no fallback path if that changes. Flagged by the Blind Hunter review pass on story 12-2's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-2-3: A narrow non-fast-forward race exists in `kedro-viz-publish.yml`: if two pipeline-touching pushes to `main` land in quic
- source_spec: `spec-12-2-publish-the-real-dag-continuously.md`
  summary: A narrow non-fast-forward race exists in `kedro-viz-publish.yml`: if two pipeline-touching pushes to `main` land in quick succession, the second (queued, `cancel-in-progress: false`) run's `actions/checkout` pins the SHA from its own (now-stale) trigger, so its later `git push` could be rejected as non-fast-forward against a `main` the first run already advanced.
  evidence: `commit_and_push_dashboard` (`pyforge-steward/src/pyforge/steward/deploy.py`) does a plain `git push origin <branch>` with no rebase/retry; a rejected push surfaces as a `DutyResult(ok=False, ...)` (a failed CI run), not a silent loss, and the SAME run's *next* invocation would pick up the still-uncommitted local diff via `_push_pending_commit_if_ahead`'s stuck-push retry — but only if that run is re-triggered, which a failed push alone does not do. Low-probability (requires two pipeline-touching pushes within the same CI run's duration) and partially self-healing, not fixed in this story. Flagged by the Blind Hunter review pass on story 12-2's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-2-4: No end-to-end GitHub Actions execution of `kedro-viz-publish.yml` was exercised before this story's PR — only the underl
- source_spec: `spec-12-2-publish-the-real-dag-continuously.md`
  summary: No end-to-end GitHub Actions execution of `kedro-viz-publish.yml` was exercised before this story's PR — only the underlying pixi tasks (`viz-build`, `viz-publish-stage`) and the Steward CLI's `--dry-run` path were verified locally/in this sandboxed environment, which cannot run a real `push` event through an actual GitHub Actions runner.
  evidence: This environment has no live GitHub Actions execution capability; the workflow YAML was validated for syntax (`yaml.safe_load`) and its constituent commands were verified to work when run manually in sequence, but the composed CI-specific behavior (real ubuntu-latest runner, real `actions/checkout` detached-HEAD state, real `GITHUB_TOKEN` push) is unverified until the first real run after merge. Flagged by the Blind Hunter review pass on story 12-2's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-2-5: `normalize_viz_build.py`'s `_iter_text_files` silently skips any file under `build/` that isn't valid UTF-8 (via a bare 
- source_spec: `spec-12-2-publish-the-real-dag-continuously.md`
  summary: `normalize_viz_build.py`'s `_iter_text_files` silently skips any file under `build/` that isn't valid UTF-8 (via a bare `except UnicodeDecodeError: continue`) in BOTH the strip pass and the verifying re-scan — a future kedro-viz version that embeds the checkout-anchored path inside a non-UTF-8 file (e.g. a binary source-map or compiled asset) would be invisible to this script's "zero anchor occurrences remain" guarantee.
  evidence: Verified every file under `build/` in this repo's real DAG is UTF-8 JSON/text today (`file` reports "JSON text data" or similar on every `build/api/*` entry; `build/assets/*.js`/`*.css` are plain text) — currently inert, not a live leak, but the code doesn't enforce or check for this property going forward. Flagged by the Edge Case Hunter review pass on story 12-2's diff (2026-08-09, review pass 3).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-2-6: `normalize_viz_build.py`'s anchor-strip uses a literal `str.replace()` substring match with no path-boundary check — a f
- source_spec: `spec-12-2-publish-the-real-dag-continuously.md`
  summary: `normalize_viz_build.py`'s anchor-strip uses a literal `str.replace()` substring match with no path-boundary check — a future sibling directory under `src/shared/packages/` whose name shares the `pyforge-atlas` prefix (e.g. a hypothetical `pyforge-atlas-legacy`) would have its own unrelated absolute paths partially mangled into `<PYFORGE_ATLAS_ROOT>-legacy/...` if it were ever built by the same mechanism.
  evidence: Verified no such sibling exists today (`ls src/shared/packages/ | grep pyforge-atlas` returns only `pyforge-atlas` itself) — currently inert. A boundary-safe fix would need a regex (e.g. `re.escape(anchor) + r'(?=[/"])'`), which reintroduces the exact path-escaping fragility `str.replace()` was deliberately chosen over `sed`/regex to avoid for arbitrary filesystem paths — not fixed here as a result. Flagged by the Blind Hunter review pass on story 12-2's diff (2026-08-09, review pass 3).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-2-7: The live `sprint-status.yaml`'s `story_meta.depends_on` lists still reference the retired `d1-`/`d2-` key spelling for E
- source_spec: `spec-12-2-publish-the-real-dag-continuously.md`
  summary: The live `sprint-status.yaml`'s `story_meta.depends_on` lists still reference the retired `d1-`/`d2-` key spelling for Epic 5's stories, even though PR #322 (2026-08-08) renamed the corresponding `development_status` keys to the current `5-1-`/`5-2-` Epic.Story convention — so any future code resolving `depends_on` entries against `development_status` keys would silently fail to match.
  evidence: Re-confirmed live in this worktree (`grep -n "depends_on:.*d[12]-" .../implementation-artifacts/sprint-status.yaml` still hits 3 lines); no shipped code currently reads `depends_on` (`grep -rn depends_on src/shared/packages/pyforge-atlas/src/` is empty), so nothing is broken today — inert but drift-prone. Same underlying issue already deferred on story 12-1's behalf (2026-08-09); re-flagged here because story 12-2 independently hit and repaired the same `kedro-test` failure this drift was surfaced during, and `sprint-status.yaml` is a generated, gitignored artifact outside both stories' Code Maps — PR #322's sweep is what missed it, not either repair pass. Flagged by the Blind Hunter review pass repairing story 12-2's `kedro-test` verification failure (2026-08-09, review pass 4).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-1-1: The GitHub Search API fallback query (`sort=stars&order=desc`, no date/activity filter) doesn't represent "trending" at 
- source_spec: `spec-13-1-trending-ingest.md`
  summary: The GitHub Search API fallback query (`sort=stars&order=desc`, no date/activity filter) doesn't represent "trending" at all — it's an effectively static top-N all-time-most-starred Python list, so exactly when the primary scrape degrades (the fallback's whole reason to exist), `trending_candidates` silently fills with near-constant "most starred" data under the same dataset name, giving CAP-1's discovery purpose little real signal for that batch.
  evidence: `conf/base/catalog.yml`'s `search_api_url` has no `created:`/`pushed:` window; GitHub's Search API has no "trending" concept, only point-in-time sort. Fixing this requires a product decision on what date-window semantics approximate "trending" for a fallback corroboration source — beyond a trivial patch, and CAP-1's own success criteria (a non-empty snapshot, graceful degradation) still hold regardless. Flagged by the Blind Hunter review pass on story 13.1's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-1-2: `TrendingSnapshotDataset.STORE_FILENAME` is a single fixed filename, so each refresh fully overwrites the prior snapshot
- source_spec: `spec-13-1-trending-ingest.md`
  summary: `TrendingSnapshotDataset.STORE_FILENAME` is a single fixed filename, so each refresh fully overwrites the prior snapshot — no historical retention. If Story 13.2's tier classification ever wants a multi-day trend signal (streak length, day-over-day delta), that signal has already been discarded at the raw layer by CAP-1 as built.
  evidence: `_write` always atomic-writes to the same `trending_candidates.parquet` path; no date-partitioned or append-only variant exists. Deliberately out of CAP-1's stated scope (a "fresh snapshot" is the whole contract) — worth a look at Story 13.2 planning time, not a defect in this story. Flagged by the Blind Hunter review pass on story 13.1's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-1-3: `parse_trending_html`'s `article.find("h2")`/`article.find("p")` grab the FIRST matching tag anywhere in a repo card's s
- source_spec: `spec-13-1-trending-ingest.md`
  summary: `parse_trending_html`'s `article.find("h2")`/`article.find("p")` grab the FIRST matching tag anywhere in a repo card's subtree rather than a scoped selector — an unrelated heading/paragraph earlier in the card (e.g. a future sponsored-listing badge GitHub might add) would silently misattribute `repo_full_name`/`description` rather than failing loudly.
  evidence: No live GitHub markup was fetched to verify current card structure exhaustively (offline dev environment); the risk is real but low-probability given GitHub's trending page has used a stable `article.Box-row` > `h2` > `a` structure for years. Flagged by the Blind Hunter review pass on story 13.1's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-1-4: Row dicts mix Python `int` and `None` for `stars_total`/`stars_today`/`forks_total`; `pd.DataFrame(rows)` upcasts any su
- source_spec: `spec-13-1-trending-ingest.md`
  summary: Row dicts mix Python `int` and `None` for `stars_total`/`stars_today`/`forks_total`; `pd.DataFrame(rows)` upcasts any such column to `float64` the moment one `None` appears in a batch, so the persisted Parquet schema for these count columns can flip between `int64` and `float64` day to day depending on whether every row happened to parse cleanly that run — a downstream consumer (Story 13.2's classifier) reading this column across multiple days could hit an unexpected dtype.
  evidence: `TrendingSnapshotDataset._write` does not coerce dtypes before `frame.to_parquet(...)`; pandas' well-documented int-with-NaN-upcasts-to-float64 behavior applies directly to the `stars_total`/`stars_today`/`forks_total` columns as constructed. A fix (pandas nullable `Int64` extension dtype) is a real but non-trivial design call, not a one-line patch. Flagged by the Blind Hunter review pass on story 13.1's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-1-5: `parse_trending_html`'s `repo_full_name` is built by stripping slashes off the scraped `href`, assuming it is always a r
- source_spec: `spec-13-1-trending-ingest.md`
  summary: `parse_trending_html`'s `repo_full_name` is built by stripping slashes off the scraped `href`, assuming it is always a relative path (`/owner/repo`); an absolute href (`https://github.com/owner/repo`) would double-prefix into a broken `repo_url` (`https://github.com/https://github.com/owner/repo`) with no detection.
  evidence: `repo_full_name = (link.get("href") or "").strip("/").strip()` then `repo_url = f"https://github.com/{repo_full_name}"` unconditionally prepends the host with no absolute-URL guard. Low-probability (GitHub's trending page has used relative hrefs consistently) but undetected if it ever changes. Flagged by the Edge Case Hunter review pass on story 13.1's diff (2026-08-09, review pass 2).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-1-6: `pipelines/upstream_discovery/nodes.py::_coerce_cadence` (post-patch) and the precedent it mirrors, `pipelines/vulnerabi
- source_spec: `spec-13-1-trending-ingest.md`
  summary: `pipelines/upstream_discovery/nodes.py::_coerce_cadence` (post-patch) and the precedent it mirrors, `pipelines/vulnerability/nodes.py::_coerce_cadence`, both accept a config-authored `0` or negative cadence without validation — a `ttls.trending_candidates: 0` typo in `parameters.yml` would make every `save()` call treat a refresh as always-due, defeating the daily-cadence contract, silently.
  evidence: Both functions do `int(raw)` with only `(TypeError, ValueError)` guarded; no positivity check exists anywhere in this codebase's cadence-coercion helpers. Not fixed here: this story's own `_coerce_cadence` faithfully mirrors the established precedent (per the spec's explicit instruction to mirror `refresh_vdb_store`), and fixing only the new copy while leaving the precedent unguarded would be an inconsistent, story-local patch to a codebase-wide pattern. Flagged by the Edge Case Hunter review pass on story 13.1's diff (2026-08-09, review pass 2).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-1-7: `_STARS_DELTA_RE` searches the WHOLE card's concatenated text (`article.get_text(" ", strip=True)`), not a scoped stars-
- source_spec: `spec-13-1-trending-ingest.md`
  summary: `_STARS_DELTA_RE` searches the WHOLE card's concatenated text (`article.get_text(" ", strip=True)`), not a scoped stars-delta element — if a repo's description text ever happens to contain a phrase matching "N stars this week/month/today", `stars_today` would be misattributed from the description rather than the actual stats row.
  evidence: `article_text = article.get_text(" ", strip=True)` then `_STARS_DELTA_RE.search(article_text)` has no element-scoping guard (unlike `stars_tag`/`forks_tag`, which use `article.select_one('a[href$="/stargazers"]')`-style scoped selectors). No fixture in the test suite exercises a description containing that exact phrase shape, so the risk is real but unverified either way. Distinct from the already-deferred first-`<h2>`/first-`<p>` mismatch (that one misattributes `repo_full_name`/`description`; this one misattributes `stars_today`). Flagged by the Edge Case Hunter follow-up review pass on story 13.1's diff (2026-08-09, review pass 3).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-1-8: `_parse_count`'s `_DIGITS_RE = re.compile(r"[\d,]+")` only captures digit/comma runs — an abbreviated count like "1.2k s
- source_spec: `spec-13-1-trending-ingest.md`
  summary: `_parse_count`'s `_DIGITS_RE = re.compile(r"[\d,]+")` only captures digit/comma runs — an abbreviated count like "1.2k stars" (if GitHub's markup ever renders one on the trending page, as it does elsewhere in its UI) would parse as `1` instead of `1200`, silently truncating rather than failing.
  evidence: No live GitHub HTML was fetched to confirm whether the trending page ever renders abbreviated counts (offline dev environment, no live fetcher wired in this story by design); GitHub's own UI does use abbreviated forms elsewhere (e.g. the repo header star badge), so the risk is plausible but unconfirmed for this specific page. Flagged by the Edge Case Hunter follow-up review pass on story 13.1's diff (2026-08-09, review pass 3).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-1-9: `TrendingSnapshotDataset._write`'s malformed-frame guard checks only that `_REQUIRED_COLUMNS` are PRESENT, not that they
- source_spec: `spec-13-1-trending-ingest.md`
  summary: `TrendingSnapshotDataset._write`'s malformed-frame guard checks only that `_REQUIRED_COLUMNS` are PRESENT, not that they contain non-null values row by row — a future refactor that bypassed the parser's own `if not repo_full_name: continue` guards could persist rows with blank identifiers and this check would not catch it.
  evidence: `missing = [c for c in self._REQUIRED_COLUMNS if c not in frame.columns]` is a columns-only check. This exactly mirrors `VDBStoreDataset._write`'s identical column-presence-only pattern in the same module (`refresh.py`) — an established, deliberate precedent this story's `_write` was told to mirror, not a gap unique to this story. Fixing it here alone would leave the sibling class inconsistently guarded; fixing both is a `refresh.py`-wide design decision, not a one-file patch. Flagged by the Blind Hunter follow-up review pass on story 13.1's diff (2026-08-09, review pass 3).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-2-1: `_resolve_pypi_name` is fully implemented and tested but unused in `classify_trending_candidates`'s hot path, which inli
- source_spec: `spec-13-2-tier-classification.md`
  summary: `_resolve_pypi_name` is fully implemented and tested but unused in `classify_trending_candidates`'s hot path, which inlines the same normalize-and-lookup logic against a pre-built index for performance; a future refactor that naively swapped the inline logic for a per-row call to `_resolve_pypi_name` would silently reintroduce an O(rows × universe) index rebuild on every call, since `_resolve_pypi_name` rebuilds the full `pypi_universe` index from scratch each invocation.
  evidence: `_resolve_pypi_name(repo_full_name, pypi_universe)` calls `_normalized_pypi_index(pypi_universe)` internally — correct for a single lookup, but `classify_trending_candidates`'s loop deliberately builds the index ONCE outside the loop instead of calling `_resolve_pypi_name` per row. No current call site exercises the O(n²) path, so this is a latent maintenance risk, not a live bug. Flagged by the Blind Hunter review pass on story 13.2's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-2-2: `trending_candidates_classified` re-materializes only in the WEEKLY `bootstrap_data` job while its own source `trending_
- source_spec: `spec-13-2-tier-classification.md`
  summary: `trending_candidates_classified` re-materializes only in the WEEKLY `bootstrap_data` job while its own source `trending_candidates` refreshes DAILY, so the classification trails the snapshot it describes by up to 6 days; CAP-3 (Story 13.3, the first consumer) must decide the cadence deliberately.
  evidence: `orchestration/definitions.py` SCHEDULED_JOBS entry `("upstream_discovery_trending", ["refresh_trending_candidates"], "0 5 * * *", "daily", ...)` selects the refresh op ALONE; the classifier reaches Dagster only via `bootstrap_ops = sorted(node_ops - set(PHASE_P_OPS))` at `BOOTSTRAP_CRON = "0 2 * * 0"`. Not patched here: the story's intent contract explicitly scoped scheduling ("it only needs a `NODE_TIMEOUTS` entry, not a `SCHEDULED_JOBS` row"), and adding the classifier to the daily job would couple a currently self-contained, uncredentialed daily job to three other pipelines' materialized outputs — a design call, not a one-line patch. The catalog comment that overclaimed "re-materialized whenever trending_candidates or its join signals change" WAS corrected in this pass. Flagged independently by both the Blind Hunter and Edge Case Hunter review passes on story 13.2's diff (2026-08-09, follow-up review pass).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-2-3: The license gate emits the affirmative reason `not-osi-license` for two states that are actually "signal unavailable" — 
- source_spec: `spec-13-2-tier-classification.md`
  summary: The license gate emits the affirmative reason `not-osi-license` for two states that are actually "signal unavailable" — a NULL/unmapped `license_spdx`, and a valid OSI license expressed in a form the 24-entry exact-match allowlist cannot represent (PEP 639 expressions like `MIT OR Apache-2.0`, `Apache-2.0 WITH LLVM-exception`, or OSI IDs outside the curated set such as `Python-2.0`, `Artistic-2.0`, `EUPL-1.2`). Genuinely OSI-licensed candidates are therefore dropped with a factually wrong reason and never escalated to a human.
  evidence: `_classify_row` does `if not isinstance(license_spdx, str) or license_spdx not in _OSI_APPROVED_SPDX_IDS: return "skip", "not-osi-license"`. `tier-taxonomy.md` defines `unclassified-needs-human` as exactly "the classifier's safety valve when a joined signal is unavailable", which fits both states better. NULL `license_spdx` is a known-common state in this codebase — `seed_gaps/nodes.py::report_license_map_gap` exists solely to report "rows the in-code `_LICENSE_TO_SPDX` map missed — i.e. `license_spdx` is NULL"; and `phase_r_fetch_one` carries `license_spdx` through verbatim from the upstream record, so PEP 639 expressions arrive unnormalized. Not patched here: the story's intent contract's I/O matrix explicitly specifies "`license_spdx` absent or not in the OSI allowlist -> `not-osi-license`", so changing it is a contract amendment, not a patch. Flagged independently by both the Blind Hunter and Edge Case Hunter review passes on story 13.2's diff (2026-08-09, follow-up review pass).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-2-4: The repo-name -> PyPI-name heuristic has an undocumented FALSE-POSITIVE direction: an unrelated repo whose name collides
- source_spec: `spec-13-2-tier-classification.md`
  summary: The repo-name -> PyPI-name heuristic has an undocumented FALSE-POSITIVE direction: an unrelated repo whose name collides with a popular PyPI package (e.g. any `someorg/requests`) resolves to that package and inherits ITS `license_spdx`/`packaging_shape`, so a confident tier-1/tier-2 recommendation can be issued for the wrong project entirely. The spec's Design Notes document only the false-NEGATIVE direction (a package published under a name different from its repo).
  evidence: `_resolve_pypi_name` matches the PEP-503-normalized repo segment against `pypi_universe` with nothing corroborating that the resolved package and the repo are the same project. No zero-new-fetch corroboration signal exists today: `pypi_intelligence_enriched`'s columns are `pypi_name, packaging_shape, license_spdx, license_raw, notes` — it carries no `project_urls`/repository field to cross-check the trending row's `repo_url` against, so this cannot be patched inside CAP-2's stated zero-new-fetch constraint. Flagged by the Edge Case Hunter review pass on story 13.2's diff (2026-08-09, follow-up review pass).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-2-5: `pypi_intelligence_enriched` is a bounded top-N enrichment slice, which structurally excludes freshly-trending packages 
- source_spec: `spec-13-2-tier-classification.md`
  summary: `pypi_intelligence_enriched` is a bounded top-N enrichment slice, which structurally excludes freshly-trending packages — exactly CAP-2's input population — so in production the tier-1/tier-2 branches will rarely fire and most resolved rows will degrade to `unclassified-needs-human`. Nothing records the unmatched names as an enrichment backlog, so the gap never closes on its own.
  evidence: `conf/base/catalog.yml` describes `pypi_intelligence_enriched` as the "Phase R top-N enrichment slice" and `pypi_intelligence/nodes.py::enrich_pypi_intelligence` states "Enrich the top-N candidate slice (bounded at dataset level)"; `_classify_row` returns `"skip", "unclassified-needs-human"` whenever `intel is None`. Every tier-1/tier-2 test in `tests/pipelines/upstream_discovery/test_nodes.py` hand-builds an intel row for the exact package under test, so no gate measures the real-world yield. Not a defect of this story's code (it behaves per contract, and the taxonomy's safety valve is the correct degradation) — but the capability's practical yield is unverified and likely low until an enrichment-request path exists. Flagged by the Blind Hunter review pass on story 13.2's diff (2026-08-09, follow-up review pass).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-2-6: A repo trending in more than one window appears up to 3x in `trending_candidates` (once per `daily`/`weekly`/`monthly` p
- source_spec: `spec-13-2-tier-classification.md`
  summary: A repo trending in more than one window appears up to 3x in `trending_candidates` (once per `daily`/`weekly`/`monthly` page), so it is classified and emitted up to 3x in `trending_candidates_classified` — inflating any "how many tier-1 candidates" count and making CAP-3/CAP-5 propose the same package repeatedly.
  evidence: `datasets/upstream_discovery.py::_do_refresh` loops the 3 period URLs doing `rows.extend(period_rows)` with no dedup, and `_write` validates columns only; `tests/datasets/test_upstream_discovery.py` asserts `set(out["period"]) == {"daily", "weekly", "monthly"}`, confirming the multi-period shape is intended. Originates in CAP-1's dataset (Story 13.1), not in this story's classifier, and cannot be fixed inside the classifier without violating its explicit "every input row produces exactly one output row" invariant — the dedup belongs either in the dataset or in CAP-3's read path. Flagged by the Edge Case Hunter review pass on story 13.2's diff (2026-08-09, follow-up review pass).
  resolved_by: Story 13.5 (CAP-5, FR-68, 2026-08-10) — `trending_candidates/handoff.py::_select_candidate_row` dedupes a multi-window duplicate to exactly ONE handoff record at the point a candidate actually leaves the dataflow for a human/downstream consumer, via the same deterministic sort `query_trending_candidates` already uses (`stars_total` desc / `repo_full_name` asc / `period` asc, first row wins). This resolves the concrete harm named above (CAP-5 proposing the same package repeatedly) WITHOUT touching CAP-1's dataset or CAP-3's own read path — `query_trending_candidates`/`trending-candidates` still returns every window's row un-deduped by design (`--period all`'s documented purpose is to surface those duplicates), so this is a handoff-time resolution, not a dataset-level or CAP-3-display-level fix. See `tier-taxonomy.md`'s "Downstream handoff (CAP-5)" As-built note.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-3-1: `query_trending_candidates`'s `with _session.bootstrapped_session(...) as s: catalog = _session.loaded_catalog(s)` is NO
- source_spec: `spec-13-3-trending-candidates-operator-surface.md`
  summary: `query_trending_candidates`'s `with _session.bootstrapped_session(...) as s: catalog = _session.loaded_catalog(s)` is NOT guarded against a session-bootstrap-time failure (e.g. a missing/incomplete `conf/local/credentials.yml` — `KeyError` from `CatalogConfigResolver` eagerly resolving every catalog entry's credentials at bootstrap) — only the subsequent `load_with_provenance` call is guarded, against `DatasetError`. A bootstrap failure crashes uncaught: the CLI's broadened `except Exception` (added this same story, patch) turns it into a clean stderr message + exit 1 instead of a raw traceback, but the MCP tool still propagates it raw, and neither degrades to the documented `count: 0` "missing dataset" shape.
  evidence: Confirmed live during this story's own implementation — a fresh worktree with no `conf/local/credentials.yml` makes ANY real (non-mocked) `bootstrapped_session` call, for ANY dataset, fail with `KeyError: 'bigquery_adc'`. This is a PRE-EXISTING gap in the shared `_session` seam, not introduced by this story: `mcp/tools.py::read_dataset` has the identical unguarded `with _session.bootstrapped_session(...) as s: catalog = _session.loaded_catalog(s)` shape with no try/except around it either, and `query_trending_candidates` deliberately mirrors that exact seam usage (Design Notes: "the exact seam `mcp/tools.py::read_dataset` already uses"). Fixing it here alone would leave `read_dataset`/`list_datasets` inconsistently guarded — a `_session`-seam-wide design decision, not a one-file patch. Flagged by the Edge Case Hunter review pass on story 13.3's diff (2026-08-09, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-3-2: CAP-3's literal success signal in `spec-upstream-discovery/SPEC.md` is "JSON output validates against a documented schem
- source_spec: `spec-13-3-trending-candidates-operator-surface.md`
  summary: CAP-3's literal success signal in `spec-upstream-discovery/SPEC.md` is "JSON output validates against a documented schema", but no schema artifact for the `query_trending_candidates` envelope exists anywhere in the repo — and the envelope's own `schema_version` is borrowed from `_provenance.SCHEMA_VERSION` (the PROVENANCE envelope's version), so a breaking change to the candidate payload cannot be signalled to a consumer at all.
  evidence: A repo-wide search finds the sentence in SPEC.md and no corresponding JSON-Schema/pydantic artifact. The `candidates` array is whatever columns `trending_candidates_classified` happens to carry at read time, so its shape changes silently whenever CAP-2's classifier adds or renames a column — with `schema_version` pinned to an unrelated module's constant, nothing moves when it does. The follow-up review pass DID make the output strictly RFC-8259-valid (the `NaN` leak is fixed and pinned by a `parse_constant`-rejecting test), so "valid JSON" now holds; "validates against a documented schema" still does not. Authoring that schema is a new deliverable beyond this story's Code Map and touches CAP-5's consumer contract, so it belongs to whichever story owns the Mason handoff. Flagged independently by both the Blind Hunter and the Edge Case Hunter on story 13.3's diff (2026-08-09, follow-up review pass).
  resolved_by: Story 13.5 (CAP-5, FR-68, 2026-08-10) — landed the repo's first documented candidate-envelope schema, `trending_candidates/handoff.py::HANDOFF_ENVELOPE_SCHEMA` (a plain dict, JSON-Schema-draft-2020-12 vocabulary; no new `jsonschema` pixi dependency), versioned independently via `HANDOFF_SCHEMA_VERSION` (an int, deliberately NOT `_provenance.SCHEMA_VERSION` — the exact borrowed-constant gap this entry names). PARTIAL, scoped honestly: this documents the CAP-5 HANDOFF envelope (`hand_off_candidate`'s single-record output), not CAP-3's own `query_trending_candidates` envelope (the `candidates` array's shape) — that surface's `schema_version` is still borrowed from `_provenance.SCHEMA_VERSION`, and its shape still changes silently whenever CAP-2's classifier adds/renames a column. The two envelopes overlap heavily (the handoff record IS a selected `query_trending_candidates` row plus the handoff-specific fields), and this story establishes the schema-artifact PRECEDENT + pattern (a plain dict, hand-rolled structural conformance test, no external validator) a future CAP-3 story can apply directly to close the remaining half.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-3-3: `build_stamp_newest` is `null` in every real `query_trending_candidates` response, because `provenance.py` populates it 
- source_spec: `spec-13-3-trending-candidates-operator-surface.md`
  summary: `build_stamp_newest` is `null` in every real `query_trending_candidates` response, because `provenance.py` populates it only on the `row-fetched-at` code path and `trending_candidates_classified` is a plain `ParquetDataset` (which resolves to `file-mtime`) — so the AD-17 staleness envelope this surface advertises is half-populated by construction, not by circumstance.
  evidence: Confirmed live — a real `ParquetDataset`-backed query returns `provenance_kind: "file-mtime"`, a correct `build_stamp`, and `build_stamp_newest: null`. This is pre-existing behaviour in the shared `pyforge.atlas.provenance` seam that `mcp/tools.py::read_dataset` has had since AD-17 landed, not something story 13.3 introduced; 13.3 only surfaces the field. The catalog.yml cadence comment and the CLI's new table header both name `build_stamp`/`build_stamp_newest` together, so either provenance should derive a newest-row stamp for file-backed datasets or the pairing should stop being advertised for dataset types that cannot produce it. A `provenance`-seam-wide decision, not a one-file patch in this story. Flagged by the Blind Hunter on story 13.3's diff (2026-08-09, follow-up review pass).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-3-4: The default `--not-on-cf` filter excludes only the exact reason `already-on-conda-forge`, but CAP-2 also emits `unclassi
- source_spec: `spec-13-3-trending-candidates-operator-surface.md`
  summary: The default `--not-on-cf` filter excludes only the exact reason `already-on-conda-forge`, but CAP-2 also emits `unclassified-needs-human` for the state "the conda-forge mapping was unusable, so on-cf could NOT be determined" — so a repo that IS on conda-forge can be returned as a not-yet-on-conda-forge candidate whenever `--tier all`/`--tier skip` is used.
  evidence: Confirmed live — running the real `classify_trending_candidates` with an empty `pypi_conda_mapping` (the fresh-atlas state) classified `psf/requests` as `reason="unclassified-needs-human"`, and `query_trending_candidates(tier="all")` then returned it with `filters.not_on_cf: true`. `nodes.py::_classify_row` returns that reason from `if not mapping_usable:` — i.e. BEFORE the `if on_cf:` branch is even reachable — so the reason genuinely means "unknown", not "not on cf". NOT patched here: the story's `<intent-contract>` states the rule explicitly ("`--not-on-cf` filters out `reason == \"already-on-conda-forge\"` ... ALWAYS derived from `reason`"), so widening the exclusion set is a contract amendment, not a patch. It is also unreachable under the DEFAULT `--tier 1,2` (every `unclassified-needs-human` row is tier `skip`), and both surfaces display the `reason` column, so today's operator sees the ambiguity rather than being misled silently. The exposure becomes real when CAP-5's Mason handoff (Story 13.5) consumes this surface programmatically on `not_on_cf` alone — that story should decide whether "unknown" belongs in a not-on-cf result set. Flagged independently by both the Blind Hunter and the Edge Case Hunter on story 13.3's diff (2026-08-09, second follow-up review pass).
  resolved_by: Story 13.5 (CAP-5, FR-68, 2026-08-10) — answered the question this entry left open ("that story should decide whether 'unknown' belongs in a not-on-cf result set") by NOT consuming `query_trending_candidates`'s `not_on_cf` filter programmatically at all. `hand_off_candidate` gates eligibility on the candidate row's `tier` directly (`tier in {"1","2"}`), never on a `not_on_cf`/`--not-on-cf` boolean — `_classify_row` (nodes.py) only ever pairs tier `"1"`/`"2"` with a resolved OSI-license reason, so `"already-on-conda-forge"` AND `"unclassified-needs-human"` are BOTH always tier `"skip"` and BOTH excluded by construction. This closes the exposure this entry named at the exact seam it named it against (CAP-5's Mason handoff) without widening `--not-on-cf`'s own reason-based exclusion set inside `query_trending_candidates` — the contract-amendment concern the original finding also flagged as out of scope for a patch. `query_trending_candidates`'s own `--not-on-cf`/`--tier all` combination still has the documented ambiguity for any OTHER programmatic consumer; only CAP-5's handoff path is closed. See `tier-taxonomy.md`'s "Downstream handoff (CAP-5)" As-built note.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-3-5: Every MCP tool that bootstraps a Kedro session (`read_dataset`, `list_datasets`, and now `query_trending_candidates`) in
- source_spec: `spec-13-3-trending-candidates-operator-surface.md`
  summary: Every MCP tool that bootstraps a Kedro session (`read_dataset`, `list_datasets`, and now `query_trending_candidates`) inherits kedro's rich logging handler, which sits on the ROOT logger and writes to STDOUT — the same channel FastMCP's default stdio transport uses for JSON-RPC, so a stdio-launched server would interleave kedro log lines into the protocol stream.
  evidence: That the handler is on the root logger and writes to stdout was established live during this story (it is exactly why `__main__.py`'s `--json` path needs a process-global `logging.disable` floor at CRITICAL: an INFO-only floor let kedro's own "Credentials not found in your Kedro project config." WARNING print into the envelope and `json.loads(stdout)` fail). The CLI half is fixed and pinned by a test; the MCP half has no equivalent. Marked plausible rather than confirmed: `build_server()` is only a factory and no stdio launcher exists in-repo, so the exposure depends on a deployment that does not exist yet. Pre-existing and seam-wide — `read_dataset`/`list_datasets` have carried it since B3, and it is fixed once at the server-construction seam (redirect root handlers to stderr when serving over stdio), not per tool. Flagged by the Blind Hunter on story 13.3's diff (2026-08-09, second follow-up review pass).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-3-6: `mcp/tools.py::read_dataset` — the seam `query_trending_candidates` was modelled on — returns `result.to_dict(orient="re
- source_spec: `spec-13-3-trending-candidates-operator-surface.md`
  summary: `mcp/tools.py::read_dataset` — the seam `query_trending_candidates` was modelled on — returns `result.to_dict(orient="records")` with NO NaN/±inf masking, so every MCP read of a Parquet-backed dataset carrying a null in a numeric column emits the bare, non-RFC-8259 `NaN`/`Infinity` tokens that two separate review passes classed as `high` defects when story 13.3's own path had them.
  evidence: Confirmed by construction and live — `pd.DataFrame({'a':[1.0,None]}).to_dict(orient='records')` yields `{'a': nan}` and `json.dumps` renders it `{"a": NaN}` (run in the pyforge-atlas env, pandas 3.0.5); `tools.py`'s coercion block duck-types DataFrame/Series/ndarray/set into JSON-native SHAPES but never touches cell VALUES. Nulls in numeric columns are the norm across the atlas catalog, not an edge case. NOT patched here: `read_dataset` is deliberately pandas-free to satisfy the AD-7 no-business-logic AST gate, so the fix belongs either in `provenance.py` (a shared json-safe coercion the whole read surface calls) or in an equivalent duck-typed masking step — a seam-wide decision touching every MCP read tool, not a one-file patch in this story. Pre-existing since B3; 13.3's own surface is already immune (its `query.py` masks both NaN and ±inf and pins it with a `parse_constant`-rejecting round-trip). Flagged during the third follow-up review pass on story 13.3's diff (2026-08-10).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-4-1: `classify_trending_candidates` can only ever reach a tier via a resolved PyPI name, so a genuinely PyPI-less candidate (
- source_spec: `spec-13-4-fixed-source-audit-track.md`
  summary: `classify_trending_candidates` can only ever reach a tier via a resolved PyPI name, so a genuinely PyPI-less candidate (a pure Rust/Go CLI, or a C++ library with no Python bindings) can never reach the Tier-2 outcome `tier-taxonomy.md`'s own definition allows for ("Rust/Go CLI, native/compiled" is listed as Tier-2-eligible with no PyPI-published precondition, unlike Tier-1's explicit "PyPI-published AND" requirement) — it permanently classifies as `no-pypi-artifact`/`unclassified-needs-human` instead.
  evidence: `_classify_row`'s decision tree (Story 13.2) gates every branch on a resolved `pypi_name`; step 1 returns `skip`/`no-pypi-artifact` (or `unclassified-needs-human`) whenever `_resolve_pypi_name` returns `None`, with no path to tier `"2"` from an unresolved name regardless of shape. Two of this story's own nine seeded org-audit candidates (`microsoft/edit`, a Rust CLI; `microsoft/SEAL`, C++/CMake) are plausibly this exact shape. Pre-existing in the Story 13.2 classifier — CAP-4 reuses it unchanged (`<intent-contract>` Never: "No change to classify_trending_candidates's signature, decision tree, helpers") — but newly consequential because a fixed-source org audit is precisely the kind of batch where compiled/no-PyPI candidates are common, unlike the trending feed CAP-2 was originally tuned against. Flagged by the Blind Hunter on story 13.4's diff (2026-08-10, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-4-2: The exact-normalized-repo-segment PyPI-name resolution heuristic (`_resolve_pypi_name`, Story 13.2, already an accepted 
- source_spec: `spec-13-4-fixed-source-audit-track.md`
  summary: The exact-normalized-repo-segment PyPI-name resolution heuristic (`_resolve_pypi_name`, Story 13.2, already an accepted v1 limitation) false-negatives whenever a repo's real PyPI package name differs from its own repo name — `org-audit-precedent.md`'s own data demonstrates this directly: `agent-framework-core` is listed as already shipped at audit time under the "Already shipped" bucket, while `microsoft/agent-framework` (the repo this story seeds) sits in "Material gaps" as a distinct, separately-tracked entry.
  evidence: `_resolve_pypi_name` normalizes only the bare repo segment (`agent-framework`) and exact-matches it against `pypi_universe.pypi_name` — it has no mechanism to associate a repo with a differently-named PyPI package such as `agent-framework-core`. If the real not-yet-packaged PyPI artifact for `microsoft/agent-framework` is named anything other than exactly `agent-framework`, this story's seeded candidate false-negatives to `no-pypi-artifact` regardless of actual packaging readiness. Pre-existing in the Story 13.2 classifier (its own Design Notes already accepted this v1 limitation and explicitly named "Story 13.4 (org-audit, reusing this classifier)" as a story that might need to revisit it); not introduced by this diff, but the first case where the precedent doc's own evidence demonstrates it concretely rather than hypothetically. Flagged by the Blind Hunter on story 13.4's diff (2026-08-10, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-5-1: The two CLI entrypoints now living in `trending_candidates/` enforce incompatible exit-code contracts for the same failu
- source_spec: `spec-13-5-downstream-handoff-to-mason.md`
  summary: The two CLI entrypoints now living in `trending_candidates/` enforce incompatible exit-code contracts for the same failure classes — `__main__.py` (Story 13.3, untouched by this diff) maps EVERY failure (a bad filter, `BrokenPipeError`, any other exception) to exit 1 with no distinct "unexpected error" code and no explicit 130 for `KeyboardInterrupt`, while `handoff_main.py` (this story) introduces the NFR-6 0/1/2/130 scheme and specifically maps `BrokenPipeError` to 2 where `__main__.py` maps the identical condition to 1.
  evidence: Confirmed by direct comparison of the two files' `except` blocks. `handoff_main.py` is the MORE correct of the two against `project-context.md`'s own binding NFR-6 convention ("Exit code 1 = policy fail... 2 = error... 130 = interrupted... never use other exit codes"); `__main__.py` predates that convention's application here and was out of this story's scope to change (Never list: no touches to `query.py`/`__main__.py`'s own filter/exit semantics). A consumer (Mason, or any script) gating uniformly on `pyforge.atlas.trending_candidates`'s CLI exit codes across BOTH entrypoints would get different answers from the two for the same failure class today. Flagged by the Blind Hunter on story 13.5's diff (2026-08-10, review pass 1).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-5-2: `scripts/spec_surface_check.py`'s `--write-baseline` has no structural safeguard against stamping a stale or incomplete 
- source_spec: `spec-13-5-downstream-handoff-to-mason.md` (repair pass, 2026-08-10)
  summary: `scripts/spec_surface_check.py`'s `--write-baseline` has no structural safeguard against stamping a stale or incomplete baseline — it hashes working-tree bytes rather than the committed git blob, never asserts every currently-governed file for the target spec is actually captured, never cross-checks that the spec's `.memlog.md` names the files being newly baselined, and (per a multi-owner surface) only refreshes the ONE named `--spec`'s entry even when a file is also governed by another spec's glob — and no test pins any of this. This exact failure class (code committed, baseline never re-stamped because the write happened before the new files were `git add`-ed) is what broke this story's deterministic verification and can recur on any future story.
  evidence: Reproduced directly on this story: the previous session's `.memlog.md` entry already documented the 3 new files, but `scripts/.spec-surface-baseline.json`'s `pyforge-atlas/spec-pyforge-atlas` entry never captured their hashes, producing 3 hard `[drift]` findings this repair pass had to fix with a bare re-run of `--write-baseline --spec pyforge-atlas/spec-pyforge-atlas`. Flagged independently by both the Blind Hunter and the Edge Case Hunter reviewing this repair pass's diff (2026-08-10) — Blind Hunter: "the root cause... has no structural preventer... nothing... stops the identical failure from recurring on the very next story"; Edge Case Hunter: sha1 should read `git show HEAD:<path>` not working-tree bytes, and the write path never checks the memlog names the files it is about to baseline. Both empirically checked and NOT live today (a full pre-fix run showed exactly the 3 expected findings and nothing else; a full post-fix run showed 0 findings across all 54 specs) — this defers the missing guardrail, not a live defect.

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-5-3: `scripts/spec_surface_check.py --write-baseline` does an unlocked read-modify-write of `scripts/.spec-surface-baseline.j
- source_spec: `spec-13-5-downstream-handoff-to-mason.md` (repair pass, 2026-08-10)
  summary: `scripts/spec_surface_check.py --write-baseline` does an unlocked read-modify-write of `scripts/.spec-surface-baseline.json` — two concurrent invocations for different `--spec` targets (plausible under this repo's own documented parallel-BMAD-agent pattern) can race, and the second writer's read (based on the pre-first-writer file) silently drops the first writer's just-stamped entry.
  evidence: `main()`'s `--write-baseline` path (`scripts/spec_surface_check.py` merge block) reads `BASELINE.read_text()` into `merged`, mutates only `args.spec`'s key(s), then does one `BASELINE.write_text(...)` with no file lock or compare-and-swap — a classic last-writer-wins race. Flagged by the Edge Case Hunter reviewing this repair pass's diff (2026-08-10). Not exercised by this repair (single sequential invocation) but plausible given `CLAUDE.md`'s own documented incidents of concurrent BMAD/loop agents mutating shared per-worktree state (e.g. the 2026-07-25 `bmad-switch` symlink race).

  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (previously un-headed / no id there, bmad-dev-auto step-04 defer append) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-5-9: Follow-up review still recommended for 10-5-stamp-advisory-data-with-its-build-provenance after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 1) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260728-201438-15bd; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-1` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-10-6-4: Follow-up review still recommended for 10-6-make-run-admission-real-or-stop-claiming-it after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-10-6-make-run-admission-real-or-stop-claiming-it.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 1) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260729-112237-3139; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-2` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-13-3-7: Follow-up review still recommended for 13-3-trending-candidates-operator-surface after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-13-3-trending-candidates-operator-surface.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260809-184330-203b; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-3` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-17-1: CAP-1's "a clean run reproduces the inventory" success bar is not freshly re-verified by this story — no quartet runtime code was executed end to end during this change.

- source_spec: `planning-artifacts/specs/spec-17-1-the-from-scratch-run-is-a-chartered-capability.md`
  summary: CAP-1's "a clean run reproduces the inventory" success bar is not freshly re-verified by this story — no quartet runtime code was executed end to end during this change.
  evidence: This diff touches zero lines in the quartet's four scripts; no cached external sources (/tmp/ext-src/*) or live OPENTEAMS_IDENTITY_GIST_ID credentials exist in this environment to run a from-scratch pass unattended. The claim is evidenced by the pre-existing identity-2026-08-20 dated tab (2 days old at story time), produced by this same toolchain before this story began — not by fresh execution in this diff. Flagged by the intent-alignment review pass: epics.md's Given/Then for 16.1 is compound (a behavioral regeneration clause plus a governance clause), and only the governance clause is built and verified here.
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py
  origin: spec-deferred 1254df4e850a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-17-2: No rate-limiting/backoff for bulk gh issue create / gh project item-add calls when --create-issues runs live against many missing names.

- source_spec: `planning-artifacts/specs/spec-17-2-handoffs-are-execution-ready.md`
  summary: No rate-limiting/backoff for bulk gh issue create / gh project item-add calls when --create-issues runs live against many missing names.
  evidence: This repo has already hit GitHub secondary rate limits under lighter concurrent load (Phase K, 8 workers -> 15% 403s). create_missing_issues fires one issue-create + one project item-add per missing name in a tight loop with no backoff. Gated behind an opt-in flag that requires deliberate attended execution with real credentials -- defer to the first real attended --create-issues run.
  location: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:create_missing_issues
  origin: spec-deferred a416fa142f5f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-17-2-2: CANVAS_DIR is a hardcoded absolute path under the operator's home directory, so the canvas writers only work on this machine/account.

- source_spec: `planning-artifacts/specs/spec-17-2-handoffs-are-execution-ready.md`
  summary: CANVAS_DIR is a hardcoded absolute path under the operator's home directory, so the canvas writers only work on this machine/account.
  evidence: Pre-existing convention, not introduced by this story: priority.py's own --canvas argparse default already hardcodes the identical "/home/rxm7706/.cursor/projects/.../canvases" path for the Catalog canvas. This story's two new canvas writers follow that same established (if machine-specific) pattern rather than inventing a new one.
  location: scripts/openteams_identity_dashboards.py:CANVAS_DIR
  origin: spec-deferred 5ceaa51ab915 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-17-2-3: write_ops_canvas: records whose P/Work falls back to the "?" sentinel are counted in the total but invisible in every per-bucket breakdown table; build_by_type silently drops recipe types outside the fixed RECIPE_TYPE_ORDER list.

- source_spec: `planning-artifacts/specs/spec-17-2-handoffs-are-execution-ready.md`
  summary: write_ops_canvas: records whose P/Work falls back to the "?" sentinel are counted in the total but invisible in every per-bucket breakdown table; build_by_type silently drops recipe types outside the fixed RECIPE_TYPE_ORDER list.
  evidence: Mirrors a pre-existing pattern already present in this same file's render() function (verified against the live file, not just the diff). Cosmetic, dashboard-only impact; neither this canvas nor its sibling has any live-rendering verification yet in this environment.
  location: scripts/openteams_identity_dashboards.py:write_ops_canvas
  origin: spec-deferred 5682282eafff — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-17-2-4: write_workbook_canvas: a pep503-name dict collision keeps only the last matching record, and jfrog_by.setdefault drops duplicate JFrog rows without counting them toward the skip total.

- source_spec: `planning-artifacts/specs/spec-17-2-handoffs-are-execution-ready.md`
  summary: write_workbook_canvas: a pep503-name dict collision keeps only the last matching record, and jfrog_by.setdefault drops duplicate JFrog rows without counting them toward the skip total.
  evidence: Same pre-existing-pattern, cosmetic-dashboard rationale as the write_ops_canvas sentinel/order-filtering item above.
  location: scripts/openteams_identity_dashboards.py:write_workbook_canvas
  origin: spec-deferred fbab2ab4966a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: closed
  closed: 2026-09-01
  closed_by: Story 23.9 (`spec-23-9-quartet-workbook-retirement.md`) — `write_workbook_canvas` rewritten to read `enterprise_jfrog_consumption.parquet` via `load_jfrog_by()`; the openpyxl/`load_workbook`/`jfrog_by.setdefault` collision path deleted (`scripts/openteams_identity_dashboards.py`).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-17-2-5: write_workbook_canvas's "Needs a staged-recipes PR" bucket excludes JFrog names with no identity match at all, inconsistent with the neither_rows bucket in the same function which does include them.

- source_spec: `planning-artifacts/specs/spec-17-2-handoffs-are-execution-ready.md`
  summary: write_workbook_canvas's "Needs a staged-recipes PR" bucket excludes JFrog names with no identity match at all, inconsistent with the neither_rows bucket in the same function which does include them.
  evidence: `if ident_row and not on_cf and not has_pr` requires a truthy ident_row, so a JFrog name with zero identity-tab match -- arguably the strongest "needs packaging" signal -- never appears in need_pr, while neither_rows counts exactly that case.
  location: scripts/openteams_identity_dashboards.py:write_workbook_canvas
  origin: spec-deferred 8597dceacf93 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: closed
  closed: 2026-09-01
  closed_by: Story 23.9 — function deleted and replaced; the staged-recipes gap logic now lives only in the export-driven `load_jfrog_by` + identity join path shared with `render()` (`scripts/openteams_identity_dashboards.py`).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-17-2-6: No try/finally around the second load_workbook() call in write_workbook_canvas -- a mid-loop exception skips wb.close() and leaks the file handle.

- source_spec: `planning-artifacts/specs/spec-17-2-handoffs-are-execution-ready.md`
  summary: No try/finally around the second load_workbook() call in write_workbook_canvas -- a mid-loop exception skips wb.close() and leaks the file handle.
  evidence: Minor resource leak in a short-lived CLI process; real but low real-world impact.
  location: scripts/openteams_identity_dashboards.py:write_workbook_canvas
  origin: spec-deferred 7e75cc105aef — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: closed
  closed: 2026-09-01
  closed_by: Story 23.9 — `load_workbook` removed from `write_workbook_canvas`; catalog source counts read from `inventory_universe.parquet` instead (`scripts/openteams_identity_dashboards.py`).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-17-2-7: _CANVAS_PREFIX is duplicated as a separate string literal in openteams_identity_dashboards.py instead of being imported from priority.py, where the original copy lives.

- source_spec: `planning-artifacts/specs/spec-17-2-handoffs-are-execution-ready.md`
  summary: _CANVAS_PREFIX is duplicated as a separate string literal in openteams_identity_dashboards.py instead of being imported from priority.py, where the original copy lives.
  evidence: Drift risk between the two copies; mitigated but not eliminated by a new test (test_write_ops_canvas_empty_records_is_valid_and_schema_shaped) that asserts the two are byte-identical.
  location: scripts/openteams_identity_dashboards.py:_CANVAS_PREFIX
  origin: spec-deferred 8b4c28559f93 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

## DW-CANOPY-2026-08-24 — Phase 5 Canopy obligations recorded (atlas station); `lane1-serves-dw-h3` answered no (2026-08-25)

- source_spec: `docs/dreams/pyforge-unifying-strategy.md` Phase 5; `sprint-change-proposal-2026-08-24-canopy.md`
  summary: Headless/express `bmad-correct-course` for station **pyforge-atlas** records how atlas
    relates to the Platform Canopy (`src/platform/`) without re-scoping steward Epics 18–30. Atlas
    Epics 1–17 stand; **no atlas Epic 18** copies steward work. Five obligations are bound in
    `epics.md` § *Canopy obligations (2026-08-24)* and summarized here.
  obligations:
    - mcp: atlas `build_server()` is mounted by steward Story 21.2 — atlas does not build a second server
    - cap7-boards: host boards use `pyforge.steward.dashboard` only; Vizro CLI boards stay outside the host (non-goal)
    - bs5-duckdb: single-writer + `read_only=True` is atlas-local; steward Story 25.2 owns the absence-test — cooperate, do not duplicate
    - five-tier: CLI exists; steward Epics 19/21/29 supply portal `/stations/atlas/`, MCP face, SKF skill, persona — no second chrome or extra public port in atlas
  joint_open_question:
    id: lane1-serves-dw-h3
    status: answered-no
    answered: 2026-08-25
    parties: [pyforge-steward, pyforge-atlas]
    question: Whether Canopy Lane 1 (Guildhall Wagtail) serves, replaces, or merely coexists with
      the Epic 16 / `spec-wagtail-corporate-brain` narrow DW-H3 contract (`LaSuiteClient` frozen REST —
      `POST /api/v1/documents/` etc.).
    answer: **No.** Host Wagtail is `/cms/` (admin, documents, images, pages). Those routes are not
      the La Suite Docs REST client. Lane 1 does not satisfy DW-H3. Constraint unchanged: Canopy
      Lane 1 must **not** absorb or re-mint `spec-wagtail-corporate-brain`.
  dw_h3: DW-H3 (live server that speaks `LaSuiteClient` REST + credential + httpx opener bring-up)
    remains **open** — unchanged by this answer; closes only when the attended bring-up runs and
    passes per Epic 16 / DW-H3.
  evidence: steward `spec-pyforge-unifying-strategy/SPEC.md` Open Questions 2026-08-25;
    `src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py`
  status: open
  verified: 2026-08-25 — `lane1-serves-dw-h3` answered **no**; DW-H3 still open; canopy MCP/board/DuckDB
    obligations unchanged.

## DW-OM-2026-08-24 — Operating-model obligations (all eight stations)

- source_spec: cross-cutting (pyforge-unifying-strategy Grounding Q1–Q8; steward SCP operating-model, §6 revisited)
  summary: Estate OM + CAP-18: shared hook-spec in pyforge-core; Warden Epic 9 is the PR-gate retrofit; this station extracts one process hook spec (today's backend = default plugin).
  owner: station planning (this file) + steward (Canopy FRs) + warden (PR-gate hook specs)
  status: open
  recorded: 2026-08-24
  close_when: steward S-32.1 done; atlas S-18.1 done (Kedro hooks mapped to shared contract; no pipeline PR-gate); no competing CI verdict

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-19-2: Host chrome does not load an HTMX runtime, so hx-* poll attributes are markup-only.

- source_spec: `planning-artifacts/specs/spec-19-2-first-portal-slice-inventory-row.md`
  summary: Host chrome does not load an HTMX runtime, so hx-* poll attributes are markup-only.
  evidence: django_pyforge/base.html is read-only for this story and has no htmx script. First paint is server-rendered and satisfies the GET AC without JS.
  location: src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/base.html
  origin: spec-deferred 039beea183ee — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-1: Stack-up PlaneBoot.library is a lock token whose query methods raise raw duckdb closed-connection errors once the connection yields to the HTTP face; consider a typed yielded-state guard, and/or the server-on-:memory: + exec-API ATTACH-read-only design (with autoinstall/autoload_known_extensions=false) as a route to two concurrently usable faces.

- source_spec: `planning-artifacts/specs/spec-20-1-one-boot-script-raises-both-plane-faces.md`
  summary: Stack-up PlaneBoot.library is a lock token whose query methods raise raw duckdb closed-connection errors once the connection yields to the HTTP face; consider a typed yielded-state guard, and/or the server-on-:memory: + exec-API ATTACH-read-only design (with autoinstall/autoload_known_extensions=false) as a route to two concurrently usable faces.
  evidence: duckdb 1.5.5 refuses any second cross-process open while a read-write connection is held (verified live 2026-08-27), so the boot yields the in-process connection before launching duckdb-server (recorded handling, Design Notes); a caller using boot.library after the yield gets an untyped closed-connection error, and connect_reader from other processes also fails while the HTTP face lives. Surfaced by the 2026-08-27 review pass (intent-alignment + edge-case reviewers); concurrent-usability proof is Story 20.2's face-parity scope per the intent's Never clause.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_boot.py
  origin: spec-deferred b1c23c7b7c85 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-2: epics.md still shows Story 20.2 (and 20.1) as "Status: backlog" even though the spec/ledger have progressed past that.

- source_spec: `planning-artifacts/specs/spec-20-2-face-parity-is-part-of-done.md`
  summary: epics.md still shows Story 20.2 (and 20.1) as "Status: backlog" even though the spec/ledger have progressed past that.
  evidence: Confirmed by grep: epics.md:1801 reads "Status: backlog" for Story 20.2, and 20.1's entry (epics.md:1791) shows the same staleness despite 20.1 being fully done (sprint-status-ledger.yaml + its spec file both say done). This story's own commits don't touch epics.md's Status field either -- that field is evidently synced on a separate, coarser cadence than per-story implementation work.
  location: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md:1791,1801
  origin: spec-deferred 989c90524998 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-2-2: The parity fixture only exercises INTEGER/VARCHAR/DOUBLE columns, not the data types most prone to silently diverging across the HTTP face's JSON wire format (NULL, DATE/TIMESTAMP, DECIMAL, BLOB).

- source_spec: `planning-artifacts/specs/spec-20-2-face-parity-is-part-of-done.md`
  summary: The parity fixture only exercises INTEGER/VARCHAR/DOUBLE columns, not the data types most prone to silently diverging across the HTTP face's JSON wire format (NULL, DATE/TIMESTAMP, DECIMAL, BLOB).
  evidence: FIXTURE_TABLE in tests/query_plane/test_face_parity.py is `(id INTEGER, label VARCHAR, amount DOUBLE)` with three non-null rows. The story's own Problem statement is specifically about the HTTP face silently diverging from the library face without anyone noticing -- NULL/date/decimal round-tripping through JSON is a classic source of exactly that kind of silent divergence, and the current fixture can't exercise it. The gate's core mechanism (seeded-divergence detection) is still proven correct via the DOUBLE column, so this is a thoroughness gap, not a correctness defect.
  location: src/shared/packages/pyforge-atlas/tests/query_plane/test_face_parity.py:49-67
  origin: spec-deferred 960735f131e6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-2-3: A TOCTOU race exists between `_port_is_free(DEFAULT_PORT)` and `boot_query_plane`'s actual bind of that same hard-coded port.

- source_spec: `planning-artifacts/specs/spec-20-2-face-parity-is-part-of-done.md`
  summary: A TOCTOU race exists between `_port_is_free(DEFAULT_PORT)` and `boot_query_plane`'s actual bind of that same hard-coded port.
  evidence: If something else grabs port 3000 in the window between the pre-check and the real duckdb-server launch, the failure surfaces as an opaque `pytest.fail("duckdb-server exited at startup...")` rather than a clear "port was stolen" diagnostic. This mirrors the same pre-existing pattern already accepted in tests/test_query_plane_boot.py (Story 20.1) -- not introduced uniquely by this diff, and low-probability given tests run against ephemeral tmp_path DBs.
  location: src/shared/packages/pyforge-atlas/tests/query_plane/test_face_parity.py:228-229
  origin: spec-deferred 47b29c1a278d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-3: dashboard/app.py's PAGE_INVENTORY notes, dashboard/__init__.py's module docstring, and a provenance comment at app.py:243 still describe the packages-backed pages as "renders empty until the composed store lands (DW-D2)", now stale relative to DW-D2-2's closure by this story.

- source_spec: `planning-artifacts/specs/spec-20-3-named-pipeline-derivation-of-the-dashboard-stores.md`
  summary: dashboard/app.py's PAGE_INVENTORY notes, dashboard/__init__.py's module docstring, and a provenance comment at app.py:243 still describe the packages-backed pages as "renders empty until the composed store lands (DW-D2)", now stale relative to DW-D2-2's closure by this story.
  evidence: This story's spec explicitly forbids modifying dashboard/app.py's page set or PAGE_INVENTORY ("Never" clause) -- that is reserved for Story 20.5, which is explicitly gated on this story. dashboard/__init__.py's docstring carries the same "BSL-wired SHELL" framing but is not covered by an explicit Never clause; left unchanged here for consistency with the same page-inventory documentation set Story 20.5 will touch. Purely comment/docstring text, no functional impact.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py:13-19,68-90,243; src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/__init__.py:10-13
  origin: spec-deferred fff73eb6b482 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-3-2: README.md's "Status" line ("8 Kedro pipelines live") already omitted the pre-existing artifactory_downloads and query_plane_cache pipelines before this story; this story adds a 9th/10th pipeline (semantic_packages) without correcting that inventory.

- source_spec: `planning-artifacts/specs/spec-20-3-named-pipeline-derivation-of-the-dashboard-stores.md`
  summary: README.md's "Status" line ("8 Kedro pipelines live") already omitted the pre-existing artifactory_downloads and query_plane_cache pipelines before this story; this story adds a 9th/10th pipeline (semantic_packages) without correcting that inventory.
  evidence: Pre-existing drift, not introduced by this story -- confirmed the README already undercounted by 2 before this diff. Worsened by one more omission. No functional impact; a documentation-completeness item best fixed as one pass across all undercounted pipelines rather than piecemeal per-story.
  location: src/shared/packages/pyforge-atlas/README.md:14-17
  origin: spec-deferred d245c8cb57f9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-3-3: test_nodes.py's duplicate-key test (test_duplicate_conda_name_across_joined_inputs_does_not_fan_out_the_population) only exercises duplicate keys in core_packages_enumerated/core_latest_status, not in core_downloads, core_feedstock_attribution, or vcs_archived_feedstocks.

- source_spec: `planning-artifacts/specs/spec-20-3-named-pipeline-derivation-of-the-dashboard-stores.md`
  summary: test_nodes.py's duplicate-key test (test_duplicate_conda_name_across_joined_inputs_does_not_fan_out_the_population) only exercises duplicate keys in core_packages_enumerated/core_latest_status, not in core_downloads, core_feedstock_attribution, or vcs_archived_feedstocks.
  evidence: A thoroughness gap, not a correctness defect: nodes.py already calls .drop_duplicates("conda_name") on every one of those three inputs before merging, so the fan-out guard exists in code: the gap is only in explicit test coverage proving it for the other three inputs.
  location: src/shared/packages/pyforge-atlas/tests/pipelines/semantic_packages/test_nodes.py
  origin: spec-deferred 867782247fa3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-4: epics.md still shows Story 20.4 (and 20.5) as "Status: backlog" even though the spec/ledger have progressed past that -- the same known epics.md-staleness pattern recorded by Stories 20.2/20.3's own specs.

- source_spec: `planning-artifacts/specs/spec-20-4-the-cis-two-spine-specs-exist.md`
  summary: epics.md still shows Story 20.4 (and 20.5) as "Status: backlog" even though the spec/ledger have progressed past that -- the same known epics.md-staleness pattern recorded by Stories 20.2/20.3's own specs.
  evidence: epics.md's own convention (per Stories 20.2/20.3) is that per-story "Status:" lines are regenerated by bmad-create-epics-and-stories, not hand-edited by a single-story dispatch; this story follows the same precedent rather than hand-patching epics.md.
  location: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md:1821,1830
  origin: spec-deferred 70d7500fc66d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-4-2: The "19 unshipped pages" enumeration required deriving which of the 28 legacy CLI questions are still unaddressed and reconciling that against the literal epics.md arithmetic (28 minus PAGE_INVENTORY's length of 9) -- the two numbers do not trivially agree because 2 of PAGE_INVENTORY's 9 entries (estate-cache, factory-status) are not CLI ports, leaving 21 genuinely-unaddressed CLI questions, not 19. DESIGN.md documents the derivation and the one consolidation (platform-breakdown + pyver-breakdow

- source_spec: `planning-artifacts/specs/spec-20-4-the-cis-two-spine-specs-exist.md`
  summary: The "19 unshipped pages" enumeration required deriving which of the 28 legacy CLI questions are still unaddressed and reconciling that against the literal epics.md arithmetic (28 minus PAGE_INVENTORY's length of 9) -- the two numbers do not trivially agree because 2 of PAGE_INVENTORY's 9 entries (estate-cache, factory-status) are not CLI ports, leaving 21 genuinely-unaddressed CLI questions, not 19. DESIGN.md documents the derivation and the one consolidation (platform-breakdown + pyver-breakdow
  evidence: See DESIGN.md § 0 and § 6 (page-count reconciliation table) for the full derivation and citations (canonical script list, mcp-tools.md, atlas-phases-overview.md § 3.3).
  location: _bmad-output/projects/pyforge-atlas/planning-artifacts/DESIGN.md#0-how-carson-and-maya-derived-19
  origin: spec-deferred 3ef01fe75c87 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-4-3: The vendored `bmad-cis-design-thinking/template.md` (copied into `.claude/skills/` by `bmad-cis-install`, part of the `bmad-creative-intelligence-suite` v0.3.1 conda package) renders a `{{project_name}}` title placeholder that no step of the skill's own SKILL.md ever resolves -- Step 4 "Load Config" only resolves `output_folder`/`user_name`/ `communication_language`/`date`, unlike the sibling CIS workflows (`innovation-strategy`'s `{{company_name}}`, `problem-solving`'s `{{problem_title}}`) whic

- source_spec: `planning-artifacts/specs/spec-20-4-the-cis-two-spine-specs-exist.md`
  summary: The vendored `bmad-cis-design-thinking/template.md` (copied into `.claude/skills/` by `bmad-cis-install`, part of the `bmad-creative-intelligence-suite` v0.3.1 conda package) renders a `{{project_name}}` title placeholder that no step of the skill's own SKILL.md ever resolves -- Step 4 "Load Config" only resolves `output_folder`/`user_name`/ `communication_language`/`date`, unlike the sibling CIS workflows (`innovation-strategy`'s `{{company_name}}`, `problem-solving`'s `{{problem_title}}`) whic
  evidence: `.claude/skills/bmad-cis-design-thinking/template.md` line 1 (`{{project_name}}`) against `.claude/skills/bmad-cis-design-thinking/SKILL.md` Step 4 "Load Config", which never resolves that key; confirmed the skill files are byte-identical to `.pixi/envs/local-recipes/share/bmad-creative-intelligence-suite/skills/bmad-cis-design-thinking/`, i.e. the bug is upstream in the conda package, not introduced by this story's install step.
  location: .claude/skills/bmad-cis-design-thinking/template.md:1
  origin: spec-deferred 9ac040d8d84d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-4-4: No automated check in this repo verifies that a `sprint-status-ledger.yaml` `done` value or a `deferred-work-ledger.md` `resolution:` closure claim is actually backed by the artifact it cites -- a future single-story dispatch could mark a planning story "done" and close its DW entry on a false self-report (e.g. claiming N pages covered when fewer actually landed) and nothing in `pyforge-doctor`'s ledger source or `fleet_scan.py`'s `scan_deferred`/`parse_sprint_status` would catch it; both only c

- source_spec: `planning-artifacts/specs/spec-20-4-the-cis-two-spine-specs-exist.md`
  summary: No automated check in this repo verifies that a `sprint-status-ledger.yaml` `done` value or a `deferred-work-ledger.md` `resolution:` closure claim is actually backed by the artifact it cites -- a future single-story dispatch could mark a planning story "done" and close its DW entry on a false self-report (e.g. claiming N pages covered when fewer actually landed) and nothing in `pyforge-doctor`'s ledger source or `fleet_scan.py`'s `scan_deferred`/`parse_sprint_status` would catch it; both only c
  evidence: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py::gather` (lines 149-261) only flags a key that was `TERMINAL` at baseline and drops out of `TERMINAL` at head; a `backlog -> done` transition never enters that check. `scripts/fleet_scan.py`'s `scan_deferred` only requires a `resolution:`/`verified:` line to exist to count an entry `triaged`/`closed` -- it never greps the cited artifact paths for matching content.
  location: src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py:149
  origin: spec-deferred 130f6c75a3c1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-5: All 19 new pages use the SAME minimal Card+AgGrid shape as the original 9 pages (`_data_page`/`_shell_page`, per the Code Map's "the exact pattern every new page must follow"), not DESIGN.md/EXPERIENCE.md's richer per-page interactive layouts (visible Filter rows, Graph charts, a distribution-breakdown dimension-selector radio control, click-to-filter chart segments, expand-in-place per-signal breakdowns, staged upload/submit controls). This is the single largest scope judgment call in this stor

- source_spec: `planning-artifacts/specs/spec-20-5-port-the-remaining-nineteen-vizro-pages.md`
  summary: All 19 new pages use the SAME minimal Card+AgGrid shape as the original 9 pages (`_data_page`/`_shell_page`, per the Code Map's "the exact pattern every new page must follow"), not DESIGN.md/EXPERIENCE.md's richer per-page interactive layouts (visible Filter rows, Graph charts, a distribution-breakdown dimension-selector radio control, click-to-filter chart segments, expand-in-place per-signal breakdowns, staged upload/submit controls). This is the single largest scope judgment call in this stor
  evidence: dashboard/app.py's docstring + Code Map § "the exact pattern every new page must follow"; every new PageDef's `note` cites its DESIGN.md section for the deferred richer layout (e.g. distribution-breakdown's dimension-selector, universe-sbom's pagination, scan-project/env-inspect's upload controls).
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py (all 19 new `_data_page` calls)
  origin: spec-deferred 17aab2c827dd — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-5-2: The 2 live-scan-artifact pages (scan-project, env-inspect) read the LATEST cached per-invocation result via the same honest-empty BSL seam as every other shell page, but do NOT wire an actual in-dashboard submit control that triggers a new scan (a Dash callback invoking scan_project.py/env_inspect.py as a subprocess). DESIGN.md / EXPERIENCE.md describe an upload/path input as the primary interaction; building that live-invocation wiring is a materially larger, separate engineering effort (a new

- source_spec: `planning-artifacts/specs/spec-20-5-port-the-remaining-nineteen-vizro-pages.md`
  summary: The 2 live-scan-artifact pages (scan-project, env-inspect) read the LATEST cached per-invocation result via the same honest-empty BSL seam as every other shell page, but do NOT wire an actual in-dashboard submit control that triggers a new scan (a Dash callback invoking scan_project.py/env_inspect.py as a subprocess). DESIGN.md / EXPERIENCE.md describe an upload/path input as the primary interaction; building that live-invocation wiring is a materially larger, separate engineering effort (a new
  evidence: dashboard/data.py::load_scan_project / load_env_inspect docstrings state this explicitly; PageDef notes for both pages in app.py carry the same "forward-looking work, not wired here" language, mirroring DESIGN.md's own precedent for add-handoff / library-futures' deferred multi-agent claim/lock coordination.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py (load_scan_project, load_env_inspect); dashboard/app.py PAGE_INVENTORY notes for scan-project/env-inspect
  origin: spec-deferred d17a66db7038 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-5-3: The §2.1 semantic-HTML/ARIA browser-agent navigation check found a REAL, pre-existing accessibility gap while driving the actual rendered DOM: Vizro's shipped page-select control is a `<div>`-based accordion, not a native `<nav>`/`role="navigation"` landmark (the one literal `<nav>` tag on the page is an empty, hidden top navbar Vizro doesn't use), and page content sits in a plain `<div>`, not a `<main>`/`role="main"` landmark. Native `<a href>` links + heading elements remain genuinely, indepen

- source_spec: `planning-artifacts/specs/spec-20-5-port-the-remaining-nineteen-vizro-pages.md`
  summary: The §2.1 semantic-HTML/ARIA browser-agent navigation check found a REAL, pre-existing accessibility gap while driving the actual rendered DOM: Vizro's shipped page-select control is a `<div>`-based accordion, not a native `<nav>`/`role="navigation"` landmark (the one literal `<nav>` tag on the page is an empty, hidden top navbar Vizro doesn't use), and page content sits in a plain `<div>`, not a `<main>`/`role="main"` landmark. Native `<a href>` links + heading elements remain genuinely, indepen
  evidence: tests/dashboard/test_dashboard_e2e.py::test_dashboard_28_pages_semantic_nav_and_aria docstring records exactly this; confirmed by hand against Playwright-captured DOM dumps of the rendered dashboard (`page.locator("nav").count()` == 1, matching only the empty top navbar; `role="navigation"`/`role="main"` counts == 0).
  location: src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_e2e.py; deferred-work-ledger.md DW-D2-3 resolution
  origin: spec-deferred c4988094d094 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-5-4: DW-D2-3 STAYS OPEN, not closed -- corrected after review. Only the §2.1 ARIA navigation-check residual is genuinely done; the "data-present visual pass" residual DW-D2-3's own 2026-08-26 evidence-update named is NOT done. The visual pass actually run in this story (`pixi run -e local-recipes dashboard-serve`, headless-Chrome screenshots) was against a FRESH, EMPTY data root -- it re-proves the already-known honest-empty behavior, not a post-pipeline-run, data-present state. Materializing real da

- source_spec: `planning-artifacts/specs/spec-20-5-port-the-remaining-nineteen-vizro-pages.md`
  summary: DW-D2-3 STAYS OPEN, not closed -- corrected after review. Only the §2.1 ARIA navigation-check residual is genuinely done; the "data-present visual pass" residual DW-D2-3's own 2026-08-26 evidence-update named is NOT done. The visual pass actually run in this story (`pixi run -e local-recipes dashboard-serve`, headless-Chrome screenshots) was against a FRESH, EMPTY data root -- it re-proves the already-known honest-empty behavior, not a post-pipeline-run, data-present state. Materializing real da
  evidence: deferred-work-ledger.md DW-D2-3's `status: open` (not closed) + its 2026-08-28 evidence-update spells out exactly this split; `ls data/` in this worktree shows no `data/` tree exists at all (nothing was or could have been materialized without a live, credentialed pipeline run).
  location: _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md (DW-D2-3)
  origin: spec-deferred 787059d3db2f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-5-5: A handful of DESIGN.md's per-page measures are genuinely multi-signal composite scores computed by algorithms that need row-to-row comparison or set operations over the full catalog (e.g. find-alternative's similarity_score is find_alternative.py's own weighted-Jaccard composite across keyword/summary/dependent/maintainer overlap x recency x downloads) -- not expressible as a per-row Ibis/DuckDB expression without reimplementing a substantial search algorithm in SQL. These are modeled as PRE-COM

- source_spec: `planning-artifacts/specs/spec-20-5-port-the-remaining-nineteen-vizro-pages.md`
  summary: A handful of DESIGN.md's per-page measures are genuinely multi-signal composite scores computed by algorithms that need row-to-row comparison or set operations over the full catalog (e.g. find-alternative's similarity_score is find_alternative.py's own weighted-Jaccard composite across keyword/summary/dependent/maintainer overlap x recency x downloads) -- not expressible as a per-row Ibis/DuckDB expression without reimplementing a substantial search algorithm in SQL. These are modeled as PRE-COM
  evidence: semantic/models.py::build_alternative_candidates_model docstring states this explicitly; semantic/metrics.py's 2 new provenance entries (release_trend_label, python_min_bump_status) cite their legacy_source verbatim.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/models.py (build_alternative_candidates_model and the other "BSL model (NEW)" composite-score pages: mapping-gap match_confidence, universe
  origin: spec-deferred 94f216576c1e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-5-6: test_dashboard_dryrun.py::test_factory_status_reads_the_real_sprint_status fails in THIS worktree, verified pre-existing (identical failure on baseline main HEAD via `git stash`) and unrelated to this story's diff: it reads the real, gitignored Tier-3 `_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml`, which is absent in a fresh worktree/checkout (only the main checkout's local runtime state has it, from a prior session's bmad-loop/marshal run). Not a PR-CI gate: g

- source_spec: `planning-artifacts/specs/spec-20-5-port-the-remaining-nineteen-vizro-pages.md`
  summary: test_dashboard_dryrun.py::test_factory_status_reads_the_real_sprint_status fails in THIS worktree, verified pre-existing (identical failure on baseline main HEAD via `git stash`) and unrelated to this story's diff: it reads the real, gitignored Tier-3 `_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml`, which is absent in a fresh worktree/checkout (only the main checkout's local runtime state has it, from a prior session's bmad-loop/marshal run). Not a PR-CI gate: g
  evidence: `git stash` + re-running the single test reproduces the identical AssertionError on unmodified main HEAD; `ls _bmad-output/projects/pyforge-atlas/implementation-artifacts/` in this worktree shows only `epic-20-context.md`, no `sprint-status.yaml`, while the sibling main checkout has one (dated 2026-08-26, from prior session state never synced to this worktree, by design -- gitignored Tier-3).
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/factory_status.py (_default_paths); tests/dashboard/test_dashboard_dryrun.py::test_factory_status_reads_the_real_sprint_status
  origin: spec-deferred 865b12049f93 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-5-7: No test verifies that a given page's `_provenance.resolve_for_file(...)` call in `build_dashboard()` is paired to THAT SAME page's own Parquet path constant -- only the generic "backing file not found" substring is checked (by `test_shell_pages_state_unavailable_provenance_honestly`), never that e.g. `cve_watcher_provenance` is actually built from `VULN_HISTORY_PARQUET` and not some other page's constant. A future edit swapping two of the 18 near-identical per-page provenance declarations would

- source_spec: `planning-artifacts/specs/spec-20-5-port-the-remaining-nineteen-vizro-pages.md`
  summary: No test verifies that a given page's `_provenance.resolve_for_file(...)` call in `build_dashboard()` is paired to THAT SAME page's own Parquet path constant -- only the generic "backing file not found" substring is checked (by `test_shell_pages_state_unavailable_provenance_honestly`), never that e.g. `cve_watcher_provenance` is actually built from `VULN_HISTORY_PARQUET` and not some other page's constant. A future edit swapping two of the 18 near-identical per-page provenance declarations would
  evidence: Reviewer (2026-08-28 pass) Blind Hunter finding, `[low]` `[defer]`; manually cross-checked `build_dashboard()`'s 18 new `_provenance.resolve_for_file(root / _data.X_PARQUET)` lines against their paired `_data_page(...)` loader calls -- all 18 pairings are correct as shipped.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py (build_dashboard, the provenance-resolution block)
  origin: spec-deferred 90563d160b78 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-1: Epic 15's spec-artifactory-download-intelligence SPEC.md declares a `surface:` glob that matches zero real tracked files, leaving the whole epic invisible to the repo's spec-surface drift/coverage gate.

- source_spec: `spec-15-1-injectable-aql-adapter.md`
  summary: Epic 15's spec-artifactory-download-intelligence SPEC.md declares a `surface:` glob that matches zero real tracked files, leaving the whole epic invisible to the repo's spec-surface drift/coverage gate.
  evidence: SPEC.md's frontmatter declares `surface: - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/` — a bare directory path with a trailing slash and no `*`/`**`. `scripts/spec_surface_check.py::glob_to_re` (verified directly, lines 56-72) only expands wildcards on literal `*`/`**` characters; every other character is `re.escape`d and the whole pattern is anchored `^...$`. A pattern with no wildcard therefore compiles to a regex that can only match the exact literal string `".../pipelines/"` itself — never a real file path (`git ls-files` never lists a bare directory), so this spec's surface currently governs nothing, unlike every sibling spec checked for comparison (`spec-wagtail-corporate-brain`, `spec-pyforge-atlas`), which use either exact file paths or a trailing `/**`. Compounding this: even a corrected glob would need to account for this story's deliberate choice to place Story 15.1's code at `pyforge/atlas/artifactory/` (a new top-level sibling package, not under `pipelines/`) — a documented, load-bearing decision (see this story's own spec Boundaries & Constraints: placing it under `pipelines/<name>/` would have broken Kedro's `find_pipelines(raise_errors=True)`), so a future fix to this SPEC.md's surface should reflect the code's real location, not just widen the existing glob. Neither the glob-anchoring behavior in `spec_surface_check.py` nor SPEC.md's `surface:` field was touched by this story's diff — both pre-exist it. Flagged by the Blind Hunter reviewing this story's diff (2026-08-15); the `glob_to_re` behavior was independently confirmed by reading the script directly rather than trusting the reviewer's claim.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

### DW-FU-15-3: `tests/catalog/conftest.py::PREFIX_TO_PIPELINE` attributes the `derived_purl_exports` catalog entry to the `derived_artifacts` pipeline by naming-prefix convention, but this story's `format_artifactory_purl_export` is that entry's first-ever real producer node, and it lives in the unrelated `artifactory_downloads` pipeline — nothing enforces that the prefix-derived "owning pipeline" bucket matches the real Kedro DAG wiring, so this can silently diverge further with each future story that adds another partition producer to the same shared catalog entry.

- source_spec: `spec-15-3-kedro-pipeline-surfacing.md`
  summary: `tests/catalog/conftest.py::PREFIX_TO_PIPELINE` attributes the `derived_purl_exports` catalog entry to the `derived_artifacts` pipeline by naming-prefix convention, but this story's `format_artifactory_purl_export` is that entry's first-ever real producer node, and it lives in the unrelated `artifactory_downloads` pipeline — nothing enforces that the prefix-derived "owning pipeline" bucket matches the real Kedro DAG wiring, so this can silently diverge further with each future story that adds another partition producer to the same shared catalog entry.
  evidence: Confirmed directly: `derived_artifacts/pipeline.py` only ever produces `derived_universe_sbom` (its sole node, `build_universe_sbom`); `derived_purl_exports` has never had a real producer before this story (its own package docstring: "the catalog entry stays declared-but-unproduced"), yet `PREFIX_TO_PIPELINE`'s `"derived": "derived_artifacts"` rule already counted it toward `derived_artifacts`'s `EXPECTED_PIPELINE_COUNTS` bucket before this diff touched anything. This story does not fix that pre-existing mis-bucketing (out of scope — the mapping is a naming-prefix heuristic across the whole catalog, not something this story's own entries need to correct), but it is the first case where the divergence between "who the naming convention says owns this entry" and "who the DAG actually shows produces it" becomes concretely observable rather than latent. Flagged by the Blind Hunter reviewing this story's diff (2026-08-15); verified directly against `derived_artifacts/pipeline.py` and `derived_artifacts/__init__.py` rather than trusting the reviewer's claim.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

### DW-FU-16-1: `spec-wagtail-corporate-brain/SPEC.md`'s `open_questions` (frontmatter comment + prose) and the `deferred-work-ledger.md` DW-H3 entry both now cite `spec-16-1-instance-deploy-definition.md` by relative path, but that file exists only in this run's gitignored `implementation-artifacts/` (Tier-3 scratch) — until it is promoted into the tracked `planning-artifacts/specs/` subdir and committed per this repo's own "story specs are durable" convention, both citations resolve to a file that does not exist in any fresh clone or other worktree.

- source_spec: `spec-16-1-instance-deploy-definition.md`
  summary: `spec-wagtail-corporate-brain/SPEC.md`'s `open_questions` (frontmatter comment + prose) and the `deferred-work-ledger.md` DW-H3 entry both now cite `spec-16-1-instance-deploy-definition.md` by relative path, but that file exists only in this run's gitignored `implementation-artifacts/` (Tier-3 scratch) — until it is promoted into the tracked `planning-artifacts/specs/` subdir and committed per this repo's own "story specs are durable" convention, both citations resolve to a file that does not exist in any fresh clone or other worktree.
  evidence: Flagged independently by both the Blind Hunter and the Edge Case Hunter reviewing this story's diff (2026-08-15); the Edge Case Hunter additionally cited `docs/dashboard/generate.py`'s own docstring precedent and CLAUDE.md's documented incident history (13/31 pyforge-warden specs and 30/32 pyforge-atlas specs lost this exact way before the "story specs are durable" convention existed) as evidence this is a real, recurring failure mode, not a one-off. Not fixable within this story: CLAUDE.md's own convention states promotion happens "after the story merges" — i.e. after this bmad-loop run's branch lands, which is outside this workflow's scope. Whoever lands Story 16.1 must promote `spec-16-1-instance-deploy-definition.md` into `planning-artifacts/specs/spec-16-1-instance-deploy-definition.md` and commit it in the same PR (or immediately after merge) so these two cross-references resolve.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

### DW-FU-16-2: The injected opener seam cannot convey response headers, so header-dependent failures are undiagnosable by any caller.

- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/spec-16-2-httpx-opener-and-rehearsal.md`
  summary: The injected opener seam cannot convey response headers, so header-dependent failures are undiagnosable by any caller.
  evidence: `factory/lasuite.py:79-81` defines `Response` as exactly `status_code: int` + `body: Any` — no headers field. Every opener therefore discards the response headers before `LaSuiteClient` sees them, so a 3xx surfaces as `HTTP 301: ''` with `Location` already gone, a 429 loses `Retry-After`, a 401 loses `WWW-Authenticate`, and non-JSON bodies cannot be distinguished by `Content-Type`. Pre-existing since Story 9.3 (the seam's original shape), independent of any particular opener — Story 16.2 only made it visible by building the first real HTTP opener against it. Not fixable in 16.2: that story's intent contract freezes `factory/lasuite.py` at zero diff. Story 16.2 works around the redirect case with `follow_redirects=True`, which does not help the other three. Widening `Response` with an optional `headers` mapping is source-compatible (a defaulted field) but touches the frozen seam and its mock, so it needs its own story.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

### DW-FU-16-2-2: Two independent mock Wagtails now encode the same four-route contract with no shared source, so they can drift apart silently.

- source_spec: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/spec-16-2-httpx-opener-and-rehearsal.md`
  summary: Two independent mock Wagtails now encode the same four-route contract with no shared source, so they can drift apart silently.
  evidence: `tests/factory/test_lasuite.py`'s in-memory `MockWagtail` and `tests/factory/test_lasuite_live_rehearsal.py`'s loopback stub both implement the same four routes (create/get/list/patch under Bearer auth), independently. They already match differently — `MockWagtail` routes on `request.url.split("/api/v1")[-1]`, the stub prefix-matches full paths — so a future route change in `factory/lasuite.py` can leave one green and the other red, or leave both green against subtly different contracts. This is real duplication rather than churn (the earlier review pass rejected only the narrower suggestion to restyle the stub's matching to look like the mock's, which changes no behavior). Story 16.2 could not consolidate them: its intent contract makes `tests/factory/test_lasuite.py` read-only at zero diff, so extracting a shared route table is structurally out of reach there and needs its own story.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

### DW-FU-21-2: pyforge-atlas-bootstrap pixi task fails on seed_gaps: seed_root resolves relative to the Kedro member dir (src/shared/packages/pyforge-atlas) instead of REPO_ROOT, so cwe_categories_seed.json is not found.

- source_spec: `planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md`
  summary: pyforge-atlas-bootstrap pixi task fails on seed_gaps: seed_root resolves relative to the Kedro member dir (src/shared/packages/pyforge-atlas) instead of REPO_ROOT, so cwe_categories_seed.json is not found.
  evidence: Reproduces identically on baseline_revision f71b388ab783f9b584f9e90f2d6d6c67d96c2ba8 with none of this story's changes applied -- pre-existing, unrelated to the 3 target files (core_sources.py, request_datasets.py, vcs_sources.py).
  location: src/shared/packages/pyforge-atlas (seed_gaps pipeline / kedro-catalog-check path-containment assertion, likely a Story 21.1 gap)
  origin: spec-deferred 6706c5adfb66 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-30 — ingested from spec frontmatter by scripts/deferred_work_intake.py

  resolution: **CLOSED 2026-08-31 by Story 21.8** (`spec-21-8-end-to-end-verification-gate.md`).
    Root cause was narrower than "REPO_ROOT vs. member-dir CWD": Kedro's own
    `_convert_paths_to_absolute_posix` absolutizes every relative `filepath:`/`path`
    catalog value against `project_path` (the Kedro member dir) regardless of process
    CWD — never an assumed repo-root CWD, which `globals.yml`'s P9 comment incorrectly
    claimed. Fixed by changing `globals.yml`'s `seed_root` default from the repo-root-
    relative `.claude/skills/conda-forge-expert/data` to the member-dir-relative escape
    `../../../../.claude/skills/conda-forge-expert/data` (four levels: pyforge-atlas ->
    packages -> shared -> src -> repo root), and correcting the one pre-existing test
    (`tests/catalog/test_override_points.py::test_path_defaults_resolve_inside_the_repo_root`)
    that encoded the same wrong REPO_ROOT-anchored premise, to anchor on `MEMBER_DIR`
    instead (the real Kedro resolution point) while still requiring containment within
    `REPO_ROOT` overall. Verified: `kedro-catalog-check` (61 passed) and full `kedro-test`
    (1595 passed, 24 skipped, 0 failures) green after the fix; a live end-to-end
    `pyforge-atlas-bootstrap` run on a genuinely empty `PYFORGE_ATLAS_DATA_ROOT` with no
    `CF_ATLAS_DB` completed all 62/62 tasks, exit 0, in ~199s (previously failed at task
    42/62 on this exact bug, reproduced first to confirm the diagnosis before patching).

  status: closed

### DW-FU-21-2-2: 11 of 13 new catalog entries (GitHub, GitLab, Codeberg, 8 registries) have their refresh- trigger nodes wired into the DAG correctly, but call their fetch methods with an empty identifier batch by design -- no real data flows until a conda_name -> upstream-identity mapping is wired in.

- source_spec: `planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md`
  summary: 11 of 13 new catalog entries (GitHub, GitLab, Codeberg, 8 registries) have their refresh- trigger nodes wired into the DAG correctly, but call their fetch methods with an empty identifier batch by design -- no real data flows until a conda_name -> upstream-identity mapping is wired in.
  evidence: Confirmed by the Intent Alignment auditor (pass 2): `enrich_maintainers(core_cf_graph_raw)` in the same pipelines/vcs_health/nodes.py already reads identifier-bearing data one node up, but none of the 3 new trigger nodes take it as input. Explicitly out of THIS story's scope per the verbatim intent ("Checklist in identity-contract.md not in scope") -- identifier resolution is Story 21.6's ("upstream_discovery identity join") territory.
  location: src/pyforge/atlas/pipelines/vcs_health/nodes.py (refresh_vcs_github_store, refresh_vcs_host_stores, refresh_vcs_registry_stores); owning follow-up: Story 21.6
  origin: spec-deferred 6cd9ca77f8dd — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-30 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-2-3: _ttl_cadence has no validation/clamping for a zero or negative configured cadence value in params:ttls, which could cause excessive live-fetch frequency once real identifiers are wired (Story 21.6).

- source_spec: `planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md`
  summary: _ttl_cadence has no validation/clamping for a zero or negative configured cadence value in params:ttls, which could cause excessive live-fetch frequency once real identifiers are wired (Story 21.6).
  evidence: Not exercised today since every current trigger call uses an empty identifier batch (see the identifier-source-gap entry above); becomes live risk only once that gap is closed.
  location: src/pyforge/atlas/pipelines/vcs_health/nodes.py (_ttl_cadence)
  origin: spec-deferred 4930f71255e3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-30 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-2-4: A batch containing at least one fetch success overwrites the ENTIRE persisted store with only that batch's rows, rather than merging onto existing rows for names/identifiers outside the batch -- a latent data-loss gap in the AD-13 persistence model this story introduced.

- source_spec: `planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md`
  summary: A batch containing at least one fetch success overwrites the ENTIRE persisted store with only that batch's rows, rather than merging onto existing rows for names/identifiers outside the batch -- a latent data-loss gap in the AD-13 persistence model this story introduced.
  evidence: Not reachable today (every current caller passes an empty batch), but will matter as soon as Story 21.6 wires a real, possibly-partial identifier batch per refresh cycle.
  location: src/pyforge/atlas/datasets/vcs_sources.py (_ParquetRefreshStore._persist), src/pyforge/atlas/datasets/request_datasets.py (GitHubRequestDataset.fetch_repo_health persistence)
  origin: spec-deferred 0d2251687650 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-30 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-2-5: fetch_one's retry-with-scheduler-and-backoff logic is still duplicated near-verbatim between VcsHostSeedDataset and RegistryUpstreamDataset -- only the persistence/staleness plumbing was hoisted into the shared _ParquetRefreshStore mixin.

- source_spec: `planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md`
  summary: fetch_one's retry-with-scheduler-and-backoff logic is still duplicated near-verbatim between VcsHostSeedDataset and RegistryUpstreamDataset -- only the persistence/staleness plumbing was hoisted into the shared _ParquetRefreshStore mixin.
  evidence: Confirmed by 2 independent reviewers on the pass-2 diff; non-blocking code-organization nit, not a correctness issue.
  location: src/pyforge/atlas/datasets/vcs_sources.py
  origin: spec-deferred 8308c3e7cd86 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-30 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-2-6: _ParquetRefreshStore (the shared AD-13 persistence mixin) is defined in vcs_sources.py but imported cross-module into request_datasets.py -- arguably belongs in refresh.py alongside StalenessMarker/RefreshRequest instead.

- source_spec: `planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md`
  summary: _ParquetRefreshStore (the shared AD-13 persistence mixin) is defined in vcs_sources.py but imported cross-module into request_datasets.py -- arguably belongs in refresh.py alongside StalenessMarker/RefreshRequest instead.
  evidence: Code-organization suggestion from the Blind Hunter review; not a correctness issue.
  location: src/pyforge/atlas/datasets/vcs_sources.py, src/pyforge/atlas/datasets/request_datasets.py
  origin: spec-deferred 113618547533 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-30 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-2-7: No credentials: wired for GitLab/Codeberg/registries in catalog.yml -- for registries with meaningful anonymous rate limits (npm, crates.io, RubyGems, NuGet) there is no path to raise the ceiling via an API token without further catalog changes.

- source_spec: `planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md`
  summary: No credentials: wired for GitLab/Codeberg/registries in catalog.yml -- for registries with meaningful anonymous rate limits (npm, crates.io, RubyGems, NuGet) there is no path to raise the ceiling via an API token without further catalog changes.
  evidence: Reviewer itself notes this may be deliberate for a v1; flagging so it is a documented choice, not a silent gap.
  location: src/shared/packages/pyforge-atlas/conf/base/catalog.yml (vcs_gitlab_api_raw, vcs_codeberg_api_raw, vcs_registry_*_raw)
  origin: spec-deferred 17952db39aec — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-30 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-2-8: PyPIJsonFanOutDataset's candidate selection is sorted(names)[:limit] every run -- with a bounded default limit against a ~20k-package universe, packages later in the alphabet are never live-fetched, indefinitely, with no rotation/offset state between refresh cycles.

- source_spec: `planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md`
  summary: PyPIJsonFanOutDataset's candidate selection is sorted(names)[:limit] every run -- with a bounded default limit against a ~20k-package universe, packages later in the alphabet are never live-fetched, indefinitely, with no rotation/offset state between refresh cycles.
  evidence: Real data-quality concern flagged by Blind Hunter; not required by this story's AC (no cf_atlas.db default, safe degrade) and adds meaningful stateful-rotation complexity beyond this story's scope.
  location: src/pyforge/atlas/datasets/request_datasets.py (PyPIJsonFanOutDataset.load)
  origin: spec-deferred 1b65e2207963 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-30 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3: pypi_conda_mapping.parquet's conda_name restriction to enumerated conda packages (map_pypi_conda) is not re-applied by match_source_urls()'s recipe_source_url tier, so "conda_name is a subset of cf_packages" is not strictly true for every row of the final persisted dataset.

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: pypi_conda_mapping.parquet's conda_name restriction to enumerated conda packages (map_pypi_conda) is not re-applied by match_source_urls()'s recipe_source_url tier, so "conda_name is a subset of cf_packages" is not strictly true for every row of the final persisted dataset.
  evidence: Read src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py L96-136 (match_source_urls): recipe_source_url-tier rows are appended from pypi_json_raw without re-checking core_packages_enumerated membership. Doesn't change the pypi_name-column decision (independently justified by load_parselmouth_pypi_names' pre-existing semantics and the intent's own downstream-unchanged-shape requirement), but the code comment justifying that decision should not overclaim the subset property universally.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py:96-136
  origin: spec-deferred d6cf8714558a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-2: When --live-catalog degrades pypi_index to empty (no -only) and --verify-mode strict is set, main() falls through to the pre-existing per-package pypi_exists() live-HTTP path, in tension with --live-catalog's "no duplicate HTTP clients" framing; cf_packages' degrade path has no equivalent live-HTTP fallback, so the I/O matrix's "mirrors the conda-forge row exactly" claim doesn't fully hold at the downstream-consumption level.

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: When --live-catalog degrades pypi_index to empty (no -only) and --verify-mode strict is set, main() falls through to the pre-existing per-package pypi_exists() live-HTTP path, in tension with --live-catalog's "no duplicate HTTP clients" framing; cf_packages' degrade path has no equivalent live-HTTP fallback, so the I/O matrix's "mirrors the conda-forge row exactly" claim doesn't fully hold at the downstream-consumption level.
  evidence: Pre-existing mechanism (scripts/conda-forge-packaging-inventory-operations_metrics.py, the `if pypi_index: ... elif args.verify_mode == "strict": pypi_exists(...)` block), not modified by this story, but --live-catalog is a new way to reach it. Confirmed independently by three review layers (blind hunter, edge case hunter, intent-alignment auditor).
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (pypi_verified loop)
  origin: spec-deferred d80d9dd10d68 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-3: --strict-fetch has no effect on the three --live-catalog-acquired sets (they bypass try_source entirely); --live-catalog-only is the intentional analog for this path, but the interaction is undocumented.

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: --strict-fetch has no effect on the three --live-catalog-acquired sets (they bypass try_source entirely); --live-catalog-only is the intentional analog for this path, but the interaction is undocumented.
  evidence: Confirmed --strict-fetch exists (argparse) and is checked inside try_source() and one other call site, but load_live_catalog()'s three acquisitions never call try_source and never check args.strict_fetch.
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (main(), live_catalog branch)
  origin: spec-deferred 96602f1588ca — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-4: load_live_catalog()'s except Exception blocks store only str(exc), no traceback -- a genuine bug (e.g. a future Kedro column rename) would look identical in the printed warning to an expected degrade (missing file / sub-floor count).

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: load_live_catalog()'s except Exception blocks store only str(exc), no traceback -- a genuine bug (e.g. a future Kedro column rename) would look identical in the printed warning to an expected degrade (missing file / sub-floor count).
  evidence: Direct read of the (reverted, to-be-re-derived) loader's exception handling shape; applies to whatever the re-derived equivalent looks like.
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (load_live_catalog)
  origin: spec-deferred e630c7349d75 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-5: --help/replay wording says "missing, unreadable, or below its scale floor" applies uniformly to "the three required datasets," but pypi_conda_mapping has no floor -- could mislead debugging of a --live-catalog-only failure on that dataset.

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: --help/replay wording says "missing, unreadable, or below its scale floor" applies uniformly to "the three required datasets," but pypi_conda_mapping has no floor -- could mislead debugging of a --live-catalog-only failure on that dataset.
  evidence: Boundaries & Constraints (this spec) explicitly documents no floor for pypi_conda_mapping; the planned --help/replay phrasing doesn't distinguish it from the two floored datasets.
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (--help text)
  origin: spec-deferred 0e99ca6ac1f8 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-6: --live-catalog's --help text names internal Python variables (cf_packages/pypi_index/parselmouth_pypi) rather than the user-facing concepts (conda-forge names / PyPI names / Parselmouth mapping) used elsewhere in the CLI's own output columns.

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: --live-catalog's --help text names internal Python variables (cf_packages/pypi_index/parselmouth_pypi) rather than the user-facing concepts (conda-forge names / PyPI names / Parselmouth mapping) used elsewhere in the CLI's own output columns.
  evidence: Direct read of the planned --help description text vs. the CSV's PyPI_Verified/CondaForge_Verified column names. Note (review pass 2): the re-derived --help text already uses user-facing concepts, not internal variable names -- this item appears already resolved as a side effect of the re-derivation, left here as historical record rather than pruned (no un-defer mechanism in this workflow).
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (--help text)
  origin: spec-deferred 943cb282fe78 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-7: --live-catalog degrading cf_packages to empty (missing/sub-floor core_packages_enumerated.parquet, run without --live-catalog-only) makes every already-on-conda-forge AOSS package look "not on conda-forge" (cf_or_pm membership test), which poisons the AOSS-Free Mason-facing queue output (write_aoss_free_queue) -- documented elsewhere as a live/irreversible signal. Not a new code path (the aoss_free_candidates gate is pre-existing and unmodified by this story) and matches the story's own explicit

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: --live-catalog degrading cf_packages to empty (missing/sub-floor core_packages_enumerated.parquet, run without --live-catalog-only) makes every already-on-conda-forge AOSS package look "not on conda-forge" (cf_or_pm membership test), which poisons the AOSS-Free Mason-facing queue output (write_aoss_free_queue) -- documented elsewhere as a live/irreversible signal. Not a new code path (the aoss_free_candidates gate is pre-existing and unmodified by this story) and matches the story's own explicit
  evidence: Read scripts/conda-forge-packaging-inventory-operations_metrics.py's aoss_free_candidates construction (gated on `pkg not in cf_or_pm`) and write_aoss_free_queue's own "live and irreversible" framing. Confirmed independently by one review layer (blind hunter, pass 2); not corroborated by other layers, but the underlying mechanism (cf_or_pm membership) is directly verifiable in the diff.
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (aoss_free_candidates / write_aoss_free_queue)
  origin: spec-deferred f0a48ab7d22e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-8: load_live_catalog()'s scale-floor check counts distinct raw pre-normalization values (non_null.nunique()), while the set actually returned and consumed downstream is deduplicated post-norm_pkg() -- a column with many raw variants collapsing to the same normalized name could theoretically pass the floor with a materially smaller final set. Low real-world likelihood: conda-forge/PyPI catalog names are already close to normalized in the source Parquet.

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: load_live_catalog()'s scale-floor check counts distinct raw pre-normalization values (non_null.nunique()), while the set actually returned and consumed downstream is deduplicated post-norm_pkg() -- a column with many raw variants collapsing to the same normalized name could theoretically pass the floor with a materially smaller final set. Low real-world likelihood: conda-forge/PyPI catalog names are already close to normalized in the source Parquet.
  evidence: Direct read of load_live_catalog(): `distinct = non_null.nunique()` computed before `values = {norm_pkg(str(v)) for v in non_null}`. Corroborated by two independent review layers (blind hunter and intent-alignment auditor, pass 2), both rating it low-severity/likely inert.
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (load_live_catalog)
  origin: spec-deferred 6bac90fa7f5f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-9: The `subdirs = [s.strip() for s in args.repodata_subdirs.split(",") ...]` line was relocated (not behaviorally changed) by this story's diff and appears unused elsewhere in the file -- pre-existing dead/unused code unrelated to this story's purpose, surfaced incidentally by touching nearby lines.

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: The `subdirs = [s.strip() for s in args.repodata_subdirs.split(",") ...]` line was relocated (not behaviorally changed) by this story's diff and appears unused elsewhere in the file -- pre-existing dead/unused code unrelated to this story's purpose, surfaced incidentally by touching nearby lines.
  evidence: Blind hunter (review pass 2) noted the line is directly touched (moved) by this diff but never referenced elsewhere in the file; not independently re-verified beyond that report.
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (main(), subdirs)
  origin: spec-deferred 7224f5e3c707 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-10: Nothing validates or warns when --live-catalog is set without --cf-channeldata, even though replay.md documents --cf-channeldata as still required (it independently drives has_src/the 10k-tab-drop filter). A user following only --help, not the replay doc, gets no signal that --cf-channeldata's default (`/tmp/ext-src/cf-channeldata.json`, almost certainly absent) silently changes which 10k-tab rows are kept.

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: Nothing validates or warns when --live-catalog is set without --cf-channeldata, even though replay.md documents --cf-channeldata as still required (it independently drives has_src/the 10k-tab-drop filter). A user following only --help, not the replay doc, gets no signal that --cf-channeldata's default (`/tmp/ext-src/cf-channeldata.json`, almost certainly absent) silently changes which 10k-tab rows are kept.
  evidence: Confirmed no code path checks args.cf_channeldata when args.live_catalog is set; args.cf_channeldata's default-path fallback behavior itself pre-dates this story and is unchanged by it. Found by review pass 3's blind hunter.
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (main(), has_src)
  origin: spec-deferred f9ec9c3d62cf — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-3-11: load_live_catalog()'s pd.read_parquet call has no timeout guard, unlike every HTTP-based acquisition path elsewhere in this file (which all take an explicit timeout argument) -- a read against a slow/unresponsive network-mounted PYFORGE_ATLAS_DATA_ROOT would hang indefinitely.

- source_spec: `planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md`
  summary: load_live_catalog()'s pd.read_parquet call has no timeout guard, unlike every HTTP-based acquisition path elsewhere in this file (which all take an explicit timeout argument) -- a read against a slow/unresponsive network-mounted PYFORGE_ATLAS_DATA_ROOT would hang indefinitely.
  evidence: Direct read of load_live_catalog(): the try/except wraps path.exists() and pd.read_parquet() but neither is time-bounded. Low real-world likelihood given the documented usage pattern (a local post-bootstrap data root). Found by review pass 3's edge case hunter.
  location: scripts/conda-forge-packaging-inventory-operations_metrics.py (load_live_catalog)
  origin: spec-deferred 0a9f7d8344c9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-4: An offline `kedro run --pipelines core,…` cannot complete with no network because `CondaChanneldataDataset.load()` (reused UNCHANGED per the contract) lets the composed APIDataset's transport error propagate — the pre-existing Tier-0 live contract that also governs `core_channeldata_raw`; Story 21.3's axis, not fixable here without touching a Tier-0 class the Never bullet fences off.

- source_spec: `planning-artifacts/specs/spec-21-4-tier-1-catalog-sources.md`
  summary: An offline `kedro run --pipelines core,…` cannot complete with no network because `CondaChanneldataDataset.load()` (reused UNCHANGED per the contract) lets the composed APIDataset's transport error propagate — the pre-existing Tier-0 live contract that also governs `core_channeldata_raw`; Story 21.3's axis, not fixable here without touching a Tier-0 class the Never bullet fences off.
  evidence: Reproduced 2026-08-30: `ANACONDA_CHANNEL_BASE_URL=http://127.0.0.1:9 kedro run --nodes enumerate_anaconda_main_packages` -> ConnectionRefusedError, exit 1. The story's second AC therefore holds only for the upstream_discovery half (3 `.staleness.json` markers, exit 0) and the zero-network seed load (1,474 rows); the `core` half was verified LIVE instead (5,401 rows).
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py:393
  origin: spec-deferred c432a3b3f1e9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-4-2: `tests/pipelines/test_refresh_single_writer.py` (the declared home of the single-writer invariant) omits the `upstream_discovery` pipeline from `_all_nodes()` and its store map lacks `trending_candidates` (pre-existing) and the three Tier-1 stores; the invariant is pinned for them only by `test_tier_1_external_refresh_stores_have_exactly_one_writer_each` in `test_dag_resolves.py`.

- source_spec: `planning-artifacts/specs/spec-21-4-tier-1-catalog-sources.md`
  summary: `tests/pipelines/test_refresh_single_writer.py` (the declared home of the single-writer invariant) omits the `upstream_discovery` pipeline from `_all_nodes()` and its store map lacks `trending_candidates` (pre-existing) and the three Tier-1 stores; the invariant is pinned for them only by `test_tier_1_external_refresh_stores_have_exactly_one_writer_each` in `test_dag_resolves.py`.
  evidence: Verification-gap + blind reviewers both read `_STORE_TO_REFRESH_ASSET` and `_all_nodes()` in that module; `trending_candidates` (Story 13.1) was already missing before this story, so this is a pre-existing coverage gap the story extended rather than caused.
  location: src/shared/packages/pyforge-atlas/tests/pipelines/test_refresh_single_writer.py
  origin: spec-deferred dc248b290195 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-4-3: `_fetch_channel_repodata`'s worst case when hosts black-hole (timeouts, not 404s) is now 5 channels x 2 subdirs x 2 filenames x 2 mirrors = 40 sequential timeout-bound attempts (was 16) against `flag_cross_channel`'s 300 s NODE_TIMEOUTS budget; `_fetch_repodata_at_url` folds every exception into `None`, so a connection-level failure cannot short-circuit a dead mirror.

- source_spec: `planning-artifacts/specs/spec-21-4-tier-1-catalog-sources.md`
  summary: `_fetch_channel_repodata`'s worst case when hosts black-hole (timeouts, not 404s) is now 5 channels x 2 subdirs x 2 filenames x 2 mirrors = 40 sequential timeout-bound attempts (was 16) against `flag_cross_channel`'s 300 s NODE_TIMEOUTS budget; `_fetch_repodata_at_url` folds every exception into `None`, so a connection-level failure cannot short-circuit a dead mirror.
  evidence: Edge-case reviewer, from the loop at core_sources.py::_fetch_channel_repodata and the `except Exception -> None` in `_fetch_repodata_at_url`. Pre-existing loop shape; the hardening doubled the combo count. Offline runs fail fast (refused/DNS) so the practical impact is limited to black-holed networks.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py:556
  origin: spec-deferred 14293eb46cc4 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-4-4: `NODE_TIMEOUTS` has no completeness assertion — `test_every_op_has_its_own_timeout` only checks that a tag exists, and the fallback always supplies one — so an unmapped op silently gets `DEFAULT_TIMEOUT=600`; five pre-existing nodes are already unmapped (assemble_and_gate, compose_semantic_packages, extract_estate_to_cache, refresh_pypi_json_store, run_dependency_hygiene).

- source_spec: `planning-artifacts/specs/spec-21-4-tier-1-catalog-sources.md`
  summary: `NODE_TIMEOUTS` has no completeness assertion — `test_every_op_has_its_own_timeout` only checks that a tag exists, and the fallback always supplies one — so an unmapped op silently gets `DEFAULT_TIMEOUT=600`; five pre-existing nodes are already unmapped (assemble_and_gate, compose_semantic_packages, extract_estate_to_cache, refresh_pypi_json_store, run_dependency_hygiene).
  evidence: Checked 2026-08-30 via register_pipelines() vs D.NODE_TIMEOUTS: 59 nodes, 54 mapped, 5 missing (all pre-existing). The 4 Story 21.4 nodes ARE mapped. Adding the completeness test now would fail on the pre-existing five, so it is deferred rather than patched.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py:219
  origin: spec-deferred 17a48e05262b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-5: A malformed conf/base/curated_groups.json (invalid JSON) raises a DatasetError at the Kedro catalog layer and aborts the whole upstream_discovery pipeline run, rather than degrading to zero rows as the Boundaries text promises for "a malformed/missing seed file."

- source_spec: `planning-artifacts/specs/spec-21-5-tier-2-sources.md`
  summary: A malformed conf/base/curated_groups.json (invalid JSON) raises a DatasetError at the Kedro catalog layer and aborts the whole upstream_discovery pipeline run, rather than degrading to zero rows as the Boundaries text promises for "a malformed/missing seed file."
  evidence: Confirmed empirically: writing invalid JSON to the file and loading the discovery_curated_groups_seed catalog entry through pyforge.atlas.mcp.session.bootstrapped_session() raised `DatasetError: discovery_curated_groups_seed: ... Failed while loading data from dataset ... JSONDataset`. This happens before load_org_audit_candidates's own never-raise/degrade logic ever runs, so that node-level contract can't help. However this exact exposure (bare `type: json.JSONDataset` for a git-tracked, hand-curated seed, with no degrade wrapper) already exists for the pre-existing `seed_cwe_categories` and `seed_spdx_schema` catalog entries — this story faithfully follows established precedent rather than introducing a new pattern, so it is fleet-wide pre-existing debt, not a regression unique to this story.
  location: src/shared/packages/pyforge-atlas/conf/base/catalog.yml (discovery_curated_groups_seed entry)
  origin: spec-deferred ed4e6c98baf8 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-5-2: catalog-sources.md's Tier 2 table (the planning doc the Problem statement cites as establishing this story's requirement) names a different catalog entry/pipeline ("artifactory_downloads_raw" under artifactory_downloads) for the Artifactory/CDO-names row than what was actually built (enterprise_jfrog_names, bucketed under upstream_discovery in PREFIX_TO_PIPELINE) — the intent-contract's own Approach section directed the as-built naming, but the companion planning doc was never reconciled to matc

- source_spec: `planning-artifacts/specs/spec-21-5-tier-2-sources.md`
  summary: catalog-sources.md's Tier 2 table (the planning doc the Problem statement cites as establishing this story's requirement) names a different catalog entry/pipeline ("artifactory_downloads_raw" under artifactory_downloads) for the Artifactory/CDO-names row than what was actually built (enterprise_jfrog_names, bucketed under upstream_discovery in PREFIX_TO_PIPELINE) — the intent-contract's own Approach section directed the as-built naming, but the companion planning doc was never reconciled to matc
  evidence: Confirmed by direct comparison of catalog-sources.md's Tier 2 table against this story's own intent-contract Approach/Code Map text and the actual catalog.yml/conftest.py changes. Not a code defect — the diff correctly implements the intent-contract's explicit direction — but the companion doc is now stale relative to what shipped.
  location: _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md
  origin: spec-deferred 13d230071bb9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-5-3: spec-21-5's own Verification section claims "kedro run --pipelines upstream_discovery,artifactory_downloads on a fresh data root" exits 0, but join_enterprise_conda_maintainers's new dependency on core_feedstock_attribution (produced by the separate `core` pipeline, not included in that --pipelines list) makes a genuinely fresh data root raise a DatasetError (file not found) before the node ever runs.

- source_spec: `planning-artifacts/specs/spec-21-5-tier-2-sources.md`
  summary: spec-21-5's own Verification section claims "kedro run --pipelines upstream_discovery,artifactory_downloads on a fresh data root" exits 0, but join_enterprise_conda_maintainers's new dependency on core_feedstock_attribution (produced by the separate `core` pipeline, not included in that --pipelines list) makes a genuinely fresh data root raise a DatasetError (file not found) before the node ever runs.
  evidence: Confirmed empirically: moving core_feedstock_attribution.parquet aside and re-running `kedro run --pipelines upstream_discovery,artifactory_downloads` raised `DatasetError: core_feedstock_attribution: ... No such file or directory`. However this is a pre-existing, fleet-wide pattern, not a regression this story introduces: classify_trending_candidates (Story 13.2, already shipped) has the identical characteristic — a plain pandas.ParquetDataset input produced by a different pipeline (pypi_conda_mapping), with no missing-file tolerance. This story's own unit tests DO correctly verify join_enterprise_conda_maintainers's behavior when given None/empty input directly (the function-level contract in the I/O matrix), which is a different, narrower claim than "the full kedro run survives a truly empty data root" — the latter has never actually been true for any cross-pipeline dependency in this codebase, this story included.
  location: _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-5-tier-2-sources.md (## Verification section)
  origin: spec-deferred 7db7e06d1eb3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-7: Verification_Timestamp_UTC diverges between the persisted xlsx tab/CSV and the published gist on every non-`--skip-gist` run.

- source_spec: `planning-artifacts/specs/spec-21-7-quartet-thin-out-and-gist-wrapper.md`
  summary: Verification_Timestamp_UTC diverges between the persisted xlsx tab/CSV and the published gist on every non-`--skip-gist` run.
  evidence: write_gist_markdown has always unconditionally re-stamped Verification_Timestamp_UTC to a fresh datetime.now(...) for the gist -- confirmed unchanged at baseline commit 07da273ba7, so this pre-dates Story 21.7 and is not caused by it. main()/write_xlsx_tab/write_csv persist whatever the Parquet (or, before this story, the single per-run construction-time timestamp) carried instead.
  location: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:672-674
  origin: spec-deferred 7dc984b08114 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-7-2: read_identity_export_records() has no try/except around pd.read_parquet, so a corrupt or unreadable Parquet crashes uncaught instead of producing a hard, named error.

- source_spec: `planning-artifacts/specs/spec-21-7-quartet-thin-out-and-gist-wrapper.md`
  summary: read_identity_export_records() has no try/except around pd.read_parquet, so a corrupt or unreadable Parquet crashes uncaught instead of producing a hard, named error.
  evidence: The I/O & Edge-Case Matrix only enumerates "Parquet present" and "Parquet missing"; a present-but-corrupt Parquet is an unstated edge case. The missing-file path already returns a clean, named stderr error + None -- a malformed-but-present file should plausibly follow the same pattern, but that's an inference, not something the matrix states.
  location: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:read_identity_export_records
  origin: spec-deferred 9c5773f6f416 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-7-3: RANKING_MERGE_COLUMNS (this script) and the Atlas-side gist-export column list are two independently hand-maintained copies of the same GIST_SCHEMA contract, with no test enforcing they stay aligned.

- source_spec: `planning-artifacts/specs/spec-21-7-quartet-thin-out-and-gist-wrapper.md`
  summary: RANKING_MERGE_COLUMNS (this script) and the Atlas-side gist-export column list are two independently hand-maintained copies of the same GIST_SCHEMA contract, with no test enforcing they stay aligned.
  evidence: RANKING_MERGE_COLUMNS is derived from GIST_COLUMNS, so it self-updates on this side when GIST_SCHEMA changes -- but the pyforge-atlas upstream_discovery pipeline that produces identity_export_parquet lists its own export columns separately. Touching that file is out of this story's scope (Never: "Implement identity_export_parquet or the Atlas Phase D node").
  location: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:132 vs. src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/nodes.py
  origin: spec-deferred 56173593f2cd — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-7-4: No test exercises the real, Atlas-pipeline-produced identity_export_parquet -- every test builds its own hand-authored, already-conforming fixture.

- source_spec: `planning-artifacts/specs/spec-21-7-quartet-thin-out-and-gist-wrapper.md`
  summary: No test exercises the real, Atlas-pipeline-produced identity_export_parquet -- every test builds its own hand-authored, already-conforming fixture.
  evidence: A genuine schema-parity check between this script's COLUMNS/GIST_SCHEMA expectations and what the real Story 21.6 Phase D join actually emits doesn't exist on either side of the contract. This is a cross-cutting testing-strategy gap, not something one story should absorb -- a fixture captured from a real pipeline run (matching pyforge-atlas's own Wave B parity-diff pattern) would be the natural shape for it.
  location: tests/packaging/test_openteams_handoffs.py
  origin: spec-deferred d22114b0f077 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-7-5: merge_ranking_columns merges ~12 secondary ranking/JFROG columns with a bare membership check and no warning if one is absent from the ranked tab.

- source_spec: `planning-artifacts/specs/spec-21-7-quartet-thin-out-and-gist-wrapper.md`
  summary: merge_ranking_columns merges ~12 secondary ranking/JFROG columns with a bare membership check and no warning if one is absent from the ranked tab.
  evidence: Only the primary P/Rank/Score/Work columns get an explicit missing-columns error in publish_gist_from_tab; the remaining RANKING_MERGE_COLUMNS entries (Platforms, Downloads, JFROG fields, etc.) are copied with `if col in ranking_row`, so an older or hand-edited ranked tab missing one silently produces a blank cell with no observability.
  location: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:merge_ranking_columns
  origin: spec-deferred 385d1badefdd — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-7-6: A Parquet column holding a list/array value crashes pd.isna() in read_identity_export_records with an ambiguous-truth-value ValueError.

- source_spec: `planning-artifacts/specs/spec-21-7-quartet-thin-out-and-gist-wrapper.md`
  summary: A Parquet column holding a list/array value crashes pd.isna() in read_identity_export_records with an ambiguous-truth-value ValueError.
  evidence: read_identity_export_records's per-cell stringify does `"" if pd.isna(v) else str(v).strip()` without first checking for a non-scalar value; pandas raises ValueError on pd.isna() for an array/list input rather than returning a scalar boolean.
  location: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:read_identity_export_records
  origin: spec-deferred 78432b3f020b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-7-7: Two ranked-tab rows normalizing to the same pep503 name silently discard the earlier row in merge_ranking_columns, with no warning (unlike the miss case).

- source_spec: `planning-artifacts/specs/spec-21-7-quartet-thin-out-and-gist-wrapper.md`
  summary: Two ranked-tab rows normalizing to the same pep503 name silently discard the earlier row in merge_ranking_columns, with no warning (unlike the miss case).
  evidence: ranking_by_name is built as a dict keyed by pep503_name(Core_Python_Package_Name); a later duplicate overwrites an earlier one with no diagnostic, asymmetric with the explicit stderr warning merge_ranking_columns emits on a no-match miss.
  location: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:merge_ranking_columns
  origin: spec-deferred e851d68d42a5 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-7-8: PYFORGE_ATLAS_DATA_ROOT="" (empty string) is falsy and silently resolves to the default path instead of being treated as an explicit-but-invalid override.

- source_spec: `planning-artifacts/specs/spec-21-7-quartet-thin-out-and-gist-wrapper.md`
  summary: PYFORGE_ATLAS_DATA_ROOT="" (empty string) is falsy and silently resolves to the default path instead of being treated as an explicit-but-invalid override.
  evidence: identity_export_parquet_path() does `os.environ.get(PYFORGE_ATLAS_DATA_ROOT_ENV, "data")`, so an explicitly-set-but-empty env var (as opposed to unset) is indistinguishable from the unset default -- a narrow operator-error edge case, not currently triggered by any documented invocation.
  location: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:identity_export_parquet_path
  origin: spec-deferred 30c6310fb55b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-8: PYFORGE_ATLAS_LOCAL_RECIPES_DIR's default (`recipes`) is repo-root-relative like seed_root's pre-fix default, but pyforge-atlas-bootstrap's `kedro run` resolves it against the Kedro member dir -- the identity join's `discovery_local_recipes_raw` silently scans an empty/non-existent directory on a default bootstrap run instead of the repo's real `recipes/` tree.

- source_spec: `planning-artifacts/specs/spec-21-8-end-to-end-verification-gate.md`
  summary: PYFORGE_ATLAS_LOCAL_RECIPES_DIR's default (`recipes`) is repo-root-relative like seed_root's pre-fix default, but pyforge-atlas-bootstrap's `kedro run` resolves it against the Kedro member dir -- the identity join's `discovery_local_recipes_raw` silently scans an empty/non-existent directory on a default bootstrap run instead of the repo's real `recipes/` tree.
  evidence: Confirmed by static read of `LocalRecipesOverlayDataset.load()` (`datasets/identity_sources.py`): degrades to an empty frame when `recipes_dir.is_dir()` is False rather than raising, so the bootstrap AC's exit-0 requirement is unaffected, but `Local_Recipes_URL`/`Local_Build_Status` stay empty on a real bootstrap unless `PYFORGE_ATLAS_LOCAL_RECIPES_DIR` is set to an absolute (or correctly member-dir-escaped) path. Same root cause as DW-FU-21-2 (globals.yml's now-corrected repo-root-CWD premise), fixed there for `seed_root` only per this story's narrow authorization ("that one bug only"); not fixed here (Story 21.6 territory, done per the tracked sprint-status ledger, though its own spec frontmatter still reads `in-review`).
  location: src/shared/packages/pyforge-atlas/conf/base/globals.yml paths.local_recipes_dir; src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/identity_sources.py LocalRecipesOverlayDataset
  origin: spec-deferred bf8cf6e650c6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-8-2: PYFORGE_ATLAS_DATA_ROOT does not control the majority of pipeline outputs -- 53 of 96 `catalog.yml` `filepath:` entries (every intermediate/primary/derived-layer entry, e.g. `core_packages_enumerated`, `pypi_universe`, `pypi_conda_mapping`, `inventory_universe`, `identity_export_parquet`) hardcode a literal `data/...` string instead of `${globals:paths.data_root}/...`, so Kedro always resolves them under the member dir (`src/shared/packages/pyforge-atlas/data/`) regardless of the env override; only the 3 legacy external-refresh stores plus ~27 raw-layer entries (mostly Story 21.3-21.6 additions) actually honor it.

- source_spec: `planning-artifacts/specs/spec-21-8-end-to-end-verification-gate.md`
  summary: PYFORGE_ATLAS_DATA_ROOT does not control the majority of pipeline outputs -- 53 of 96 `catalog.yml` `filepath:` entries (every intermediate/primary/derived-layer entry, e.g. `core_packages_enumerated`, `pypi_universe`, `pypi_conda_mapping`, `inventory_universe`, `identity_export_parquet`) hardcode a literal `data/...` string instead of `${globals:paths.data_root}/...`, so Kedro always resolves them under the member dir (`src/shared/packages/pyforge-atlas/data/`) regardless of the env override; only the 3 legacy external-refresh stores plus ~27 raw-layer entries (mostly Story 21.3-21.6 additions) actually honor it.
  evidence: `git blame` on `catalog.yml`'s `core_packages_enumerated` filepath line dates the hardcoded pattern to commit `9ce95912dc5` (2026-07-17, Wave A1/A2 scaffold), predating Epic 21 by six weeks -- pre-existing and unrelated. Reproduced live: a Story 21.8 end-to-end bootstrap run with `PYFORGE_ATLAS_DATA_ROOT=/tmp/atlas-e2e-verify-21.8` (a genuinely empty dir, `CF_ATLAS_DB` unset) exited 0, but `core_packages_enumerated.parquet` / `pypi_universe.parquet` / `pypi_conda_mapping.parquet` / `inventory_universe.parquet` / `identity_export_parquet` all landed under `src/shared/packages/pyforge-atlas/data/` instead of the override root -- confirmed by `grep -c '^\s*filepath:\s*\${globals:paths\.data_root}'` (27) vs. `grep -cE '^\s*filepath:\s*data/'` (53) over `catalog.yml`, and by direct `find` over both directories after the run. Does not block this story's bootstrap-exit-0 AC (both locations start empty on a genuinely fresh clone), but materially contradicts the README/globals.yml claim that "every store/output path resolves under" `PYFORGE_ATLAS_DATA_ROOT` for an operator who explicitly relies on the override to relocate ALL data (e.g. a CI job with a scratch data root, or two concurrent local runs). Not fixed here -- 53 catalog `filepath:` edits is far beyond a narrow surgical fix and CAP-1 is proven read-only by this story, not extended.
  location: src/shared/packages/pyforge-atlas/conf/base/catalog.yml (53 filepath: entries, layer: intermediate|primary|derived)
  origin: spec-deferred b48252c51686 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-8-3: `discovery_basilisk_packages_raw` / `discovery_aoss_premium_python_raw` / `discovery_anaconda_dist_2026x_raw` never populate real data through the plain `kedro run` the literal `pyforge-atlas-bootstrap` pixi task executes -- their dataset classes default `fetcher=None` by design, so even though their refresh-trigger nodes fire, `save()` always degrades to "refresh due but no refresher wired (offline / unattended run)" and the store never gets its first real write. `discovery_aoss_free_python_raw` (`TrackedSeedDataset`, no refresh trigger needed) is unaffected.

- source_spec: `planning-artifacts/specs/spec-21-8-end-to-end-verification-gate.md`
  summary: `discovery_basilisk_packages_raw` / `discovery_aoss_premium_python_raw` / `discovery_anaconda_dist_2026x_raw` never populate real data through the plain `kedro run` the literal `pyforge-atlas-bootstrap` pixi task executes -- their dataset classes default `fetcher=None` by design, so even though their refresh-trigger nodes fire, `save()` always degrades to "refresh due but no refresher wired (offline / unattended run)" and the store never gets its first real write. `discovery_aoss_free_python_raw` (`TrackedSeedDataset`, no refresh trigger needed) is unaffected.
  evidence: Reproduced live on this story's full end-to-end bootstrap run: all three staleness markers under the bootstrapped root read `{"stale": true, "reason": "refresh due but no refresher wired (offline / unattended run)", "last_good_exists": false}` with no `.parquet` ever written, while sibling Anaconda-Main (`core_anaconda_main_channeldata_raw`, an always-fetch dataset) and GAOSS-Free populated correctly (5,386 and 1,474 packages respectively, per the `--live-catalog` MD report's Per-Worksheet-Tab matrix). Confirmed by source read: `BasiliskPackagesDataset`/`AossPremiumPythonDataset`/`AnacondaDist2026Dataset` all bind `refresher=self._do_refresh if fetcher is not None else None` in `__init__`, and their shipped `catalog.yml` entries supply no `fetcher:` key -- `BasiliskPackagesDataset`'s own docstring documents this as intentional: "Injected IO (None == offline) -- NEVER imported here; supplied by the Dagster resource / an attended run (DW-B8-1)". This is the documented, intentional degrade path, not a code defect -- but the `pyforge-atlas-bootstrap` pixi task's own description names only "live GitHub/BigQuery fan-out" as its credentialed-only degrade category; this third category (Dagster-resource-only fetchers, dating to Story 21.4) is real but undocumented there. This story's AC #2 (verification-matrix.md field parity) is still satisfied for these three fields via the dedicated offline fixture test (`scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py::test_parity_workbook_vs_live_catalog_universe`), which proves field-level reproduction given the data exists -- independent of whether a live, unattended bootstrap run can populate that data today.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/basilisk.py BasiliskPackagesDataset; src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/upstream_discovery.py AossPremiumPythonDataset, AnacondaDist2026Dataset
  origin: spec-deferred 7ee5f76414ad — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-8-4: PYFORGE_ATLAS_LOCAL_RECIPES_DIR's default (`recipes`) is repo-root-relative like seed_root's pre-fix default, but pyforge-atlas-bootstrap's `kedro run` resolves it against the Kedro member dir -- the identity join's `discovery_local_recipes_raw` silently scans an empty/non-existent directory on a default bootstrap run instead of the repo's real `recipes/` tree.

- source_spec: `planning-artifacts/specs/spec-21-8-end-to-end-verification-gate.md`
  summary: PYFORGE_ATLAS_LOCAL_RECIPES_DIR's default (`recipes`) is repo-root-relative like seed_root's pre-fix default, but pyforge-atlas-bootstrap's `kedro run` resolves it against the Kedro member dir -- the identity join's `discovery_local_recipes_raw` silently scans an empty/non-existent directory on a default bootstrap run instead of the repo's real `recipes/` tree.
  evidence: Confirmed by static read of `LocalRecipesOverlayDataset.load()` (`datasets/identity_sources.py`): degrades to an empty frame when `recipes_dir.is_dir()` is False rather than raising, so the bootstrap AC's exit-0 requirement is unaffected, but `Local_Recipes_URL`/`Local_Build_Status` stay empty on a real bootstrap unless `PYFORGE_ATLAS_LOCAL_RECIPES_DIR` is set to an absolute (or correctly member-dir-escaped) path. Same root cause as DW-FU-21-2 (globals.yml's now-corrected repo-root-CWD premise), fixed there for `seed_root` only per this story's narrow authorization ("that one bug only"); not fixed here (Story 21.6 territory, done per the tracked sprint-status ledger, though its own spec frontmatter still reads `in-review`).
  location: src/shared/packages/pyforge-atlas/conf/base/globals.yml paths.local_recipes_dir; src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/identity_sources.py LocalRecipesOverlayDataset
  origin: spec-deferred e6fc2da0fe6c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-8-5: `discovery_basilisk_packages_raw` / `discovery_aoss_premium_python_raw` / `discovery_anaconda_dist_2026x_raw` never populate real data through the plain `kedro run` the literal `pyforge-atlas-bootstrap` pixi task executes -- their dataset classes default `fetcher=None` by design, so even though their refresh-trigger nodes fire, `save()` always degrades to "refresh due but no refresher wired (offline / unattended run)" and the store never gets its first real write. `discovery_aoss_free_python_raw

- source_spec: `planning-artifacts/specs/spec-21-8-end-to-end-verification-gate.md`
  summary: `discovery_basilisk_packages_raw` / `discovery_aoss_premium_python_raw` / `discovery_anaconda_dist_2026x_raw` never populate real data through the plain `kedro run` the literal `pyforge-atlas-bootstrap` pixi task executes -- their dataset classes default `fetcher=None` by design, so even though their refresh-trigger nodes fire, `save()` always degrades to "refresh due but no refresher wired (offline / unattended run)" and the store never gets its first real write. `discovery_aoss_free_python_raw
  evidence: Reproduced live on this story's full end-to-end bootstrap run: all three staleness markers under the bootstrapped root read `{"stale": true, "reason": "refresh due but no refresher wired (offline / unattended run)", "last_good_exists": false}` with no `.parquet` ever written, while sibling Anaconda-Main (`core_anaconda_main_channeldata_raw`, an always-fetch dataset) and GAOSS-Free populated correctly (5,386 and 1,474 packages respectively, per the `--live-catalog` MD report's Per-Worksheet-Tab matrix). Confirmed by source read: `BasiliskPackagesDataset`/`AossPremiumPythonDataset`/`AnacondaDist2026Dataset` all bind `refresher=self._do_refresh if fetcher is not None else None` in `__init__`, and their shipped `catalog.yml` entries supply no `fetcher:` key -- `BasiliskPackagesDataset`'s own docstring documents this as intentional: "Injected IO (None == offline) -- NEVER imported here; supplied by the Dagster resource / an attended run (DW-B8-1)". This is the documented, intentional degrade path, not a code defect -- but the `pyforge-atlas-bootstrap` pixi task's own description names only "live GitHub/BigQuery fan-out" as its credentialed-only degrade category; this third category (Dagster-resource-only fetchers, dating to Story 21.4) is real but undocumented there. This story's AC #2 (verification-matrix.md field parity) is still satisfied for these three fields via the dedicated offline fixture test (`scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py::test_parity_workbook_vs_live_catalog_universe`), which proves field-level reproduction given the data exists -- independent of whether a live, unattended bootstrap run can populate that data today.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/basilisk.py BasiliskPackagesDataset; src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/upstream_discovery.py AossPremiumPythonDa
  origin: spec-deferred 7f6b777274fa — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-8-6: `_flatten_deferred_scalar()` in pyforge-doctor's intake tool silently hard-truncates any `summary`/heading text at exactly 500 characters with no ellipsis or marker, corrupting mid-sentence rather than degrading gracefully -- found and hand-fixed for this story's own two affected entries (`DW-FU-21-8-2`, `DW-FU-21-8-3`) during review, but the same defect still affects other already-promoted ledger entries from the caught-up backlog (e.g. `DW-FU-21-3-7`, `DW-FU-21-5-2`) and will keep corrupting f

- source_spec: `planning-artifacts/specs/spec-21-8-end-to-end-verification-gate.md`
  summary: `_flatten_deferred_scalar()` in pyforge-doctor's intake tool silently hard-truncates any `summary`/heading text at exactly 500 characters with no ellipsis or marker, corrupting mid-sentence rather than degrading gracefully -- found and hand-fixed for this story's own two affected entries (`DW-FU-21-8-2`, `DW-FU-21-8-3`) during review, but the same defect still affects other already-promoted ledger entries from the caught-up backlog (e.g. `DW-FU-21-3-7`, `DW-FU-21-5-2`) and will keep corrupting f
  evidence: Confirmed via review pass 1 (blind hunter): `DW-FU-21-8-2`/`DW-FU-21-8-3`'s ledger heading + `summary:` were both cut off at exactly 500 chars mid-word/mid-sentence, while the untruncated source text was intact in this spec's own frontmatter `deferred:` block -- confirmed by direct length/content comparison and by reading `_SUMMARY_LIMIT = 500` and the blind `[:limit]` slice in `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:2615,2647-2650`. Hand-corrected this story's own two entries in both the spec frontmatter and the ledger (review pass 1 patch); did not touch the tool itself (out of this narrow story's authorized surface) or re-derive the other backlog entries' full text (would require locating each source spec's own frontmatter individually).
  location: src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:2615,2647-2650 (_flatten_deferred_scalar, _SUMMARY_LIMIT)
  origin: spec-deferred 31528b66d9fc — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-8-7: `deferred-work-ledger.md`'s own "Why this file exists"/Provenance narrative prose (near the top, "All 52 real deferrals...") is now several generations stale after this story's ledger-wide catch-up run (`## DW-` heading count unchanged at 60, but `### DW-` sub-entry count jumped from 104 to 133 in one pass) -- the frontmatter `entries:` line was corrected (review pass 1 patch) but the prose describing a much smaller, "52 real deferrals" ledger was not reconciled to the current size.

- source_spec: `planning-artifacts/specs/spec-21-8-end-to-end-verification-gate.md`
  summary: `deferred-work-ledger.md`'s own "Why this file exists"/Provenance narrative prose (near the top, "All 52 real deferrals...") is now several generations stale after this story's ledger-wide catch-up run (`## DW-` heading count unchanged at 60, but `### DW-` sub-entry count jumped from 104 to 133 in one pass) -- the frontmatter `entries:` line was corrected (review pass 1 patch) but the prose describing a much smaller, "52 real deferrals" ledger was not reconciled to the current size.
  evidence: Confirmed via review pass 1 (blind hunter): the ledger's own Provenance section still narrates "All 52 real deferrals recorded during the Kedro migration... the ledger is complete" while `grep -c "^### DW-"` = 133 after this story's catch-up run (up from 104 at baseline). The file's own text elsewhere acknowledges this is a recurring pattern ("Stale counts in a file that declares its own counting rule are exactly what [periodic verification campaigns catch]"), so this is consistent with existing practice, not a new failure mode -- but reconciling the full narrative prose is a larger rewrite than this narrow verification-gate story's authorized surface.
  location: _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md (Provenance section, near top)
  origin: spec-deferred 1f4ed5e45458 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-8-8: No GitHub Actions workflow runs `kedro-catalog-check` or `kedro-test` for `pyforge-atlas` on PRs, so this story's own `seed_root` regression fix (DW-FU-21-2) has no CI safety net -- a future PR that reintroduces the bug would show fully green CI, since nothing in `.github/workflows/` touches the affected code path.

- source_spec: `planning-artifacts/specs/spec-21-8-end-to-end-verification-gate.md`
  summary: No GitHub Actions workflow runs `kedro-catalog-check` or `kedro-test` for `pyforge-atlas` on PRs, so this story's own `seed_root` regression fix (DW-FU-21-2) has no CI safety net -- a future PR that reintroduces the bug would show fully green CI, since nothing in `.github/workflows/` touches the affected code path.
  evidence: Confirmed via review pass 1 (verification-gap reviewer): `grep -rl "pyforge-atlas" .github/workflows/` matches only `kedro-viz-publish.yml`, which triggers on `push` to `main` only (never `pull_request`), path-filters on `pipelines/**` only (would not fire on a `conf/base/globals.yml` or `catalog.yml` change), and runs `kedro viz build` (DAG introspection only, no dataset `.load()`, no pytest). No `.github/workflows/pyforge-atlas.yml` exists, unlike sibling stations (`pyforge-core.yml`, `pyforge-steward-five-tier.yml`, `pyforge-steward-fresh-clone.yml`). This is a pre-existing, project-wide CI gap (predates this story), not something a narrow verification-gate story should take on -- flagged here since this story's own fix is exactly the kind of regression it would have silently let back in.
  location: .github/workflows/ (missing pyforge-atlas.yml)
  origin: spec-deferred 2778753746de — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-6: No Atlas dataset yet carries a per-package source_repository_url, so from_inventory's git-purl fallback branch never fires against real production data (only against synthetic parity-fixture values).

- source_spec: `planning-artifacts/specs/spec-21-6-upstream-discovery-identity-join-and-export-parquet.md`
  summary: No Atlas dataset yet carries a per-package source_repository_url, so from_inventory's git-purl fallback branch never fires against real production data (only against synthetic parity-fixture values).
  evidence: _id_universe_frame (nodes.py) hardcodes source_repository_url="" for every row because no catalog entry supplies it today; the git-purl transform logic (_id_git_purl, _id_from_inventory) is ported and unit-tested but structurally unreachable through the real build_identity_packages_primary entry point until a future story adds that column to some Atlas source.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/nodes.py:_id_universe_frame
  origin: spec-deferred a74f6192c65d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-6-2: StagedRecipesPRDataset's per-open-PR files() fetch only reads the first 100 changed files per PR, so the file-path ranking tier is incomplete for PRs with more than 100 files.

- source_spec: `planning-artifacts/specs/spec-21-6-upstream-discovery-identity-join-and-export-parquet.md`
  summary: StagedRecipesPRDataset's per-open-PR files() fetch only reads the first 100 changed files per PR, so the file-path ranking tier is incomplete for PRs with more than 100 files.
  evidence: _do_refresh's files-fanout loop issues one GET per open PR (`.../pulls/{number}/files?per_page=100`) with no pagination loop, unlike the PR-listing fetch above it which does paginate. Most single-recipe PRs have far fewer than 100 files, so this is a narrow, currently-cold edge (bulk/mass staged-recipes PRs), not a general regression.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/identity_sources.py:StagedRecipesPRDataset._do_refresh
  origin: spec-deferred ff96931ad5a2 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-6-3: discovery_local_recipes_raw's Local_Recipes_URL always points at github.com/rxm7706/local-recipes regardless of the new PYFORGE_ATLAS_LOCAL_RECIPES_DIR override, so pointing the override at a different checkout would still generate URLs into this repo.

- source_spec: `planning-artifacts/specs/spec-21-6-upstream-discovery-identity-join-and-export-parquet.md`
  summary: discovery_local_recipes_raw's Local_Recipes_URL always points at github.com/rxm7706/local-recipes regardless of the new PYFORGE_ATLAS_LOCAL_RECIPES_DIR override, so pointing the override at a different checkout would still generate URLs into this repo.
  evidence: _LOCAL_RECIPES_TREE_URL_TEMPLATE is a module-level constant hardcoding the repo slug; only the scanned filesystem path is configurable. Narrow in practice — the override is documented for pointing at an alternate path within this same repo (e.g. test fixtures), not a different GitHub repo.
  location: src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/identity_sources.py:_LOCAL_RECIPES_TREE_URL_TEMPLATE
  origin: spec-deferred e78c546ea659 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-6-4: spec Code Map's instruction to update tests/parity/test_parity_complete.py node counts does not apply — that file's _PIPELINES tuple never included upstream_discovery to begin with, in this story or any prior one.

- source_spec: `planning-artifacts/specs/spec-21-6-upstream-discovery-identity-join-and-export-parquet.md`
  summary: spec Code Map's instruction to update tests/parity/test_parity_complete.py node counts does not apply — that file's _PIPELINES tuple never included upstream_discovery to begin with, in this story or any prior one.
  evidence: Verified by reading tests/parity/test_parity_complete.py: _PIPELINES = ("core", "vcs_health", "pypi_intelligence", "vulnerability"). This is a pre-existing inaccuracy in the spec's own Code Map, not something this story's diff broke or needs to fix.
  location: src/shared/packages/pyforge-atlas/tests/parity/test_parity_complete.py
  origin: spec-deferred e0b18322d3d6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-31 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-23-5: End-to-end kedro run of derived_artifacts with materialized upstream Parquet not exercised in CI unit tests.

- source_spec: `planning-artifacts/specs/spec-23-5-identity-complete-export-parquet.md`
  summary: End-to-end kedro run of derived_artifacts with materialized upstream Parquet not exercised in CI unit tests.
  evidence: Spec Verification lists `kedro run --pipelines derived_artifacts` as a manual gate; test_identity_complete_export.py covers the node in isolation only.
  location: src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/test_identity_complete_export.py
  origin: spec-deferred 968c973f0396 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-01 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open
