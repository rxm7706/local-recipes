---
title: 'Enterprise JFROG consumption Parquet — artifactory telemetry rollup (Story 23.2, Epic 23)'
type: 'feature'
created: '2026-08-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'NO_VCS'
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/stories.yaml'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-artifactory-download-intelligence/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-3-priority-rules-in-kedro.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `complete-export-contract.md` §1 specifies a 10-column
`enterprise_jfrog_consumption.parquet` (Artifactory-native telemetry only — `risk_level`/
`vuln_status` are Basilisk-sourced, not stored here; see Never, below), but the shipped
`artifactory_downloads` pipeline (Epic 15, Stories
15.1-15.3: `artifactory/aql_adapter.py`, `artifactory/identity_join.py`,
`pipelines/artifactory_downloads/{nodes,pipeline}.py`) only produces `name`/`version`/
`download_count` rows joined against atlas's PyPI/conda identity space — it has no
`platform_env_count`/`internal_app_count`/
`internal_component_count`/`internal_lob_count` telemetry, no `core_python_package_name`
PEP-503 identity column, and no `enterprise_jfrog_consumption` catalog output at all. Story
23.3 (`spec-23-3-priority-rules-in-kedro.md`, already drafted concurrently with this spec)
already `Block If`-gates on this story's output existing.

**Approach:** Add a NEW telemetry-rollup transport round trip to the existing
`ArtifactoryAqlAdapter` (a `fetch_consumption_rows` method, sibling to the shipped
`fetch_download_rows` — never conflated into one request, matching the adapter's own
"topology, then aggregation, never combined" precedent), a new fetch node
(`fetch_artifactory_consumption`) mirroring `fetch_artifactory_downloads`'s exact
empty-`virtual_repos`-short-circuits-to-zero-construction contract, and one new PURE join node
(`build_enterprise_jfrog_consumption`) that groups the EXISTING `artifactory_downloads_joined`
by PEP-503-normalized `pypi_name` (computing `artifactory_downloads`/`artifactory_version_count`
locally — no new fetch needed for those two columns) and left-joins the new consumption rollup
onto it. `enterprise_conda_maintainers.parquet` (the OTHER Tier-2 enterprise Parquet
`complete-export-contract.md` §1 names) is explicitly Story 21.5's deliverable, not this
story's (Design Notes) — this story produces `enterprise_jfrog_consumption.parquet` only,
mock-first, reusing the SAME injectable-transport seam Story 15.1 established (no new
credential field in package code).

## Boundaries & Constraints

**Always:**
- `fetch_consumption_rows` is a SEPARATE transport round trip from `fetch_download_rows`
  (mirrors `aql_adapter.py`'s existing "topology resolution, then AQL aggregation — two
  separate round trips, never conflated" rule at `aql_adapter.py:24-25` / `:163-169`) — same
  `AqlTransport`/`AqlRequest`/`AqlResponse` seam, same `_unconfigured_transport` refuse-by-
  default behavior, same `ArtifactoryConfig` (base URL only, still no credential field).
- `fetch_artifactory_consumption` mirrors `fetch_artifactory_downloads` EXACTLY
  (`pipelines/artifactory_downloads/nodes.py:66-105`): `params:artifactory.virtual_repos`
  empty → zero `ArtifactoryConfig`/`ArtifactoryAqlAdapter` construction, no live instance
  named/selected/contacted; a non-list/non-tuple `virtual_repos` raises `ValueError`
  immediately; an optional `transport` key in `artifactory_params` is test-only, never present
  in the committed `conf/base/parameters.yml`.
- `build_enterprise_jfrog_consumption` is PURE `DataFrame, DataFrame -> DataFrame` (AC-2
  no-inline-IO gate) — no HTTP/DB import, degrades to an empty correctly-columned frame on
  `None`/empty/malformed inputs, never raises.
- `core_python_package_name` uses the EXACT SAME normalization as `priority.py::pep503`
  (`scripts/conda-forge-packaging-inventory-operations_priority.py:104-109`): lowercase,
  `_`/`.` → `-`, collapse repeated `-`, strip leading/trailing `-`, and — the detail every
  OTHER PEP-503 helper in this codebase (`identity_join.py::_normalize_pypi_name`) omits — a
  result shorter than 2 characters normalizes to `None`/is dropped, never an empty-string PK.
  Reimplemented locally (this codebase's no-cross-module-import convention;
  `scripts/conda-forge-packaging-inventory-operations_priority.py` is also a separate,
  non-importable tree from `pyforge.atlas`, same as `_http.py`/`export_purls.py`).
- `repository_source` is the literal constant `"CDO-ENT-JFROG"` for every row this node
  produces (contract §1's deliverable-A column 1).
- `kedro-catalog-check`, `duckdb-singularity`, and `kedro-test` stay green throughout.

**Block If:** Story 21.5 ("Tier 2 sources — about, curated orgs, Artifactory names";
`stories.yaml` id `21.5`) is not `status: done`. `stories.yaml` declares `depends_on:
["21.5"]` for this story. Investigation note: this story's OWN node graph
(`fetch_artifactory_consumption` → `build_enterprise_jfrog_consumption`) does not actually
read anything 21.5 produces — 21.5's deliverable is `enterprise_conda_maintainers.parquet`
(a SEPARATE Tier-2 Parquet this story does not touch; see Never, below) plus the Tier-2
`discovery_about_maintainers_raw`/artifactory-names catalog work. The declared dependency is
honored per `stories.yaml` regardless — re-verify 21.5's live status before dispatch; if a
review finds the dependency genuinely vacuous for this story's actual code, that is a
`stories.yaml`-level finding to raise upstream, not license to skip the check here.

**Never:**
- Do not build `enterprise_conda_maintainers.parquet` — `complete-export-contract.md` §1
  itself marks it "already cataloged in 18.5" (this codebase's pre-renumbering name for
  Story 21.5); this story's own "Required columns" table does not reference `Role` or any
  conda-maintainer column at all. `spec-23-3-priority-rules-in-kedro.md` (already drafted)
  consumes BOTH `enterprise_jfrog_consumption` (this story) and `enterprise_conda_maintainers`
  (21.5) as two independent inputs — do not merge them into one output here.
- Do not compute `OpenTeams_Cohort` or `openteams_universe_member` — contract §1 marks both
  "Derived on join (not stored on enterprise raw — computed in priority node)" — that is
  Story 23.3's job.
- Do not compute `risk_level`, `vuln_status`, or `jfrog_latest_vuln_count` — contract §1 marks
  the whole Basilisk vuln overlay "not Artifactory-native": Artifactory itself has no
  vulnerability data. All three are a separate join against `vulnerability_basilisk_*` on a
  package's latest version, owned downstream (23.3/23.5), not by this story's Artifactory-only
  rollup. (Corrected 2026-08-30 — the ORIGINAL contract text listed `risk_level`/`vuln_status`
  as required columns on this table, matching parity with today's legacy `CDO-ENT-JFROG`
  workbook tab, which carries them only because an external process had already joined
  Basilisk data in before `priority.py` ever saw it. The Kedro port makes that join explicit
  instead of implicit — see `complete-export-contract.md`'s own dated correction.)
- Do not add a `credentials:` key to any new catalog entry, and do not add a credential
  resolver (env-var or otherwise) to `ArtifactoryConfig`/`ArtifactoryAqlAdapter` — Story 15.1's
  module docstring (`aql_adapter.py:17-22`) is explicit that this would be "exactly the kind
  of second bespoke credential path this story must not add"; a live JFrog transport is a
  LATER, attended, out-of-package-code bring-up (Design Notes resolves the apparent tension
  with `complete-export-contract.md`'s "attended JFrog via `_http.py` truststore chain"
  wording). Adding a `credentials:` entry without also updating `tests/catalog/conftest.py`'s
  `CREDENTIAL_ALLOWLIST` would fail `test_credentials_attach_only_where_the_host_requires_them`
  anyway — widening that allowlist is explicitly out of scope here.
- Do not attempt a live network call against a real Artifactory instance in CI — every test
  injects a mock `transport`, matching `tests/artifactory/test_aql_adapter.py`'s existing
  pattern for `fetch_download_rows`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `virtual_repos` empty (committed default) | `params:artifactory = {virtual_repos: []}` | `fetch_artifactory_consumption` returns an empty, correctly-columned frame; zero `ArtifactoryConfig`/adapter construction | No error, no network |
| Mock transport, non-empty `virtual_repos` | Test injects a mock `transport` serving canned consumption rows | `fetch_artifactory_consumption` returns one row per `(name)` with the 6 telemetry columns | No error |
| Happy-path join | Non-empty `artifactory_downloads_joined` (some rows with `conda_name`, some `is_internal=True`) + non-empty `artifactory_consumption_raw` | `build_enterprise_jfrog_consumption` returns one row per distinct PEP-503-normalized name; `artifactory_downloads`/`artifactory_version_count` aggregated correctly; telemetry columns attached where a consumption row matches | No error |
| Name present in downloads but absent from consumption rollup | A package with download history but no org telemetry row | Row still emitted; `platform_env_count`/`internal_app_count`/`internal_component_count`/`internal_lob_count` default to `0` | No error, no dropped row |
| Name present in consumption rollup but absent from downloads | Org reports telemetry for a package with zero recorded downloads this period | Row still emitted; `artifactory_downloads`/`artifactory_version_count` default to `0` | No error, no dropped row (outer-join semantics) |
| A name normalizes to `<2` chars under `pep503` | A malformed/degenerate raw name | That row is dropped from the output (never an empty-string `core_python_package_name` PK), mirroring `priority.py::pep503`'s own `None`-on-too-short contract | No error, silent drop, not a crash |
| Both inputs empty/`None` | Fresh bootstrap, nothing fetched yet | `build_enterprise_jfrog_consumption` returns an empty, correctly-columned (12-column) frame | Never raises |

</intent-contract>

## Code Map

- `src/pyforge/atlas/artifactory/aql_adapter.py` — `DownloadRow` (`:97-105`),
  `ArtifactoryAqlAdapter._call` (`:126-134`), `resolve_backing_repos` (`:136-146`),
  `fetch_download_rows` (`:163-188`) — the exact sibling pattern to mirror. Add
  `ConsumptionRow` (frozen dataclass: `name: str`, `platform_env_count: int`,
  `internal_app_count: int`,
  `internal_component_count: int`, `internal_lob_count: int`) and
  `ArtifactoryAqlAdapter.fetch_consumption_rows(self, virtual_repo: str) ->
  list[ConsumptionRow]` — resolves backing repos (reuse `resolve_backing_repos`, do not
  re-resolve topology twice per virtual repo across both methods within one pipeline run —
  see Design Notes), then ONE new `self._call("POST", "/api/consumption/rollup", …)` round
  trip (representative mock-servable path; the real endpoint/query is an attended, later
  bring-up detail — Design Notes / Open Questions, mirrors the module's own "no named
  instance" mock-first stance). Malformed rows raise `ArtifactoryAqlError` (mirrors
  `fetch_download_rows`'s `KeyError`/`TypeError`/`ValueError` handling at `:178-182`);
  missing/absent numeric fields on an otherwise-valid row default to `0`
  (`row.get("platform_env_count", 0)` etc.).
- `src/pyforge/atlas/pipelines/artifactory_downloads/nodes.py` — `_RAW_COLS`/
  `fetch_artifactory_downloads` (`:45-105`) is the exact template for the new
  `_CONSUMPTION_COLS = ["name", "platform_env_count", "internal_app_count",
  "internal_component_count", "internal_lob_count"]` +
  `fetch_artifactory_consumption(artifactory_params: dict) -> pd.DataFrame` (same
  empty-`virtual_repos` short-circuit, same optional test-only `transport` key, sums nothing —
  one row per name per virtual repo, last-write-wins or summed across repos consistently with
  how `fetch_artifactory_downloads` sums `download_count` across repos for the SAME
  `(name, version)` key — mirror that summing discipline for the numeric telemetry columns
  too, so multiple virtual repos reporting the same package aggregate rather than clobber).
  `_is_missing` (`:48-63`) — reuse the SAME scalar-safe missing check, reimplemented if this
  new code lands in a way that cannot import it (mirrors the module's own existing
  no-cross-module-import discipline — but `_is_missing` already lives in THIS file, so a
  same-file function may call it directly).
  Add `_JFROG_COLS` (the 12-column contract order) + `build_enterprise_jfrog_consumption(
  artifactory_downloads_joined: pd.DataFrame, artifactory_consumption_raw: pd.DataFrame) ->
  pd.DataFrame`: groups `artifactory_downloads_joined` by PEP-503-normalized `pypi_name`
  (local `_pep503(raw) -> str | None` helper — mirror `priority.py::pep503`'s exact 4-line
  body, Intent above), `artifactory_downloads = sum(download_count)`,
  `artifactory_version_count = nunique(version)`; outer-merges the normalized
  `artifactory_consumption_raw` onto it; sets `repository_source = "CDO-ENT-JFROG"` constant,
  `packaging_tier = None` (no source yet — audit-only per contract, "stored, never used for
  P"), `verification_timestamp_utc` = one wall-clock snapshot captured at node-call time
  (`pd.Timestamp.now(tz="UTC")`, same value applied to every row in the batch, not re-read
  per row).
- `src/pyforge/atlas/pipelines/artifactory_downloads/pipeline.py` — `create_pipeline` (`:28-50`)
  — add `node(func=fetch_artifactory_consumption, inputs="params:artifactory",
  outputs="artifactory_consumption_raw", name="fetch_artifactory_consumption")` and
  `node(func=build_enterprise_jfrog_consumption, inputs=["artifactory_downloads_joined",
  "artifactory_consumption_raw"], outputs="enterprise_jfrog_consumption",
  name="build_enterprise_jfrog_consumption")`.
- `conf/base/catalog.yml:931-941` — `artifactory_downloads_raw`/`artifactory_downloads_joined`
  are the exact template. Add `artifactory_consumption_raw` (layer `raw`, `type:
  pandas.ParquetDataset`, `filepath: data/raw/artifactory_consumption_raw/
  artifactory_consumption_raw.parquet`) and `enterprise_jfrog_consumption` (layer `derived`,
  `type: pandas.ParquetDataset`, `filepath: data/derived/enterprise_jfrog_consumption/
  enterprise_jfrog_consumption.parquet` — this physical layout is what
  `complete-export-contract.md`'s `${PYFORGE_ATLAS_DATA_ROOT}/derived/
  enterprise_jfrog_consumption.parquet` shorthand resolves to under this repo's
  `data/<layer>/<name>/<name>.parquet` structural convention,
  `tests/catalog/test_conventions.py:39-65`). Neither is `IncrementalParquetDataset`/FLIP_LIST
  (both are freshly recomputed every run from already-fetched inputs, mirroring
  `pypi_intelligence_scored`'s plain `pandas.ParquetDataset` treatment at `catalog.yml:325-329`,
  not `pypi_cross_channel_flags`'s TTL-gated treatment).
- `conf/base/parameters.yml:98-107` — the existing `artifactory:` params block
  (`virtual_repos: []`) is reused UNCHANGED for `fetch_artifactory_consumption` — no new
  params block needed (same input, `params:artifactory`).
- `tests/catalog/conftest.py` — `PREFIX_TO_PIPELINE` (`:68-82`): `"artifactory":
  "artifactory_downloads"` already covers `artifactory_consumption_raw`; add
  `"enterprise": "artifactory_downloads"` (a NEW prefix — `enterprise_jfrog_consumption` does
  not start with `artifactory_`). `EXPECTED_PIPELINE_COUNTS["artifactory_downloads"]`
  (`:97`, currently `2`): bump by 2 relative to whatever value is current at implementation
  time (concurrent sibling stories may have already moved it — do not hardcode `2 -> 4`).
  `EXPECTED_TOTAL` (`:101`): bump by 2, same relative-not-absolute caveat.
  `CREDENTIAL_ALLOWLIST`/`STUB_CREDENTIALS` (`:218-227`) — do NOT touch (Never, above); the
  pre-existing `"jfrog": [...]` stub entry in `STUB_CREDENTIALS` is unused by this story and
  stays that way.
- `tests/parity/test_parity_complete.py` / `tests/pipelines/test_dag_resolves.py` — NOT
  touched: `_PIPELINES`/node-count fixtures in both files do not currently track
  `artifactory_downloads` at all (verified 2026-08-30 — `artifactory` does not appear in
  either file), so this story adds no entry to either.
- `tests/artifactory/test_aql_adapter.py` — the existing `fetch_download_rows` test suite is
  the template; add a parallel suite for `fetch_consumption_rows` (mock transport happy path,
  malformed row raises, missing-optional-field defaults, backing-repo resolution reused not
  re-fetched).
- `tests/pipelines/artifactory_downloads/test_nodes.py` — the existing
  `fetch_artifactory_downloads`/`join_artifactory_identity`/`format_artifactory_purl_export`
  tests are the template; add `fetch_artifactory_consumption` (mirrors
  `fetch_artifactory_downloads`'s own test cases exactly) and
  `build_enterprise_jfrog_consumption` (every I/O-matrix row above, plus a dedicated
  `pep503`-parity test asserting THIS module's local `_pep503` produces byte-identical output
  to `scripts/conda-forge-packaging-inventory-operations_priority.py::pep503` on a shared
  fixture list of names — mirrors how `spec-21-2`-era code cross-checks provenance-rank
  tie-breaks against `pypi_intelligence/nodes.py::export_pypi_conda_map`'s established
  precedent).

## Tasks & Acceptance

**Execution:**
- `src/pyforge/atlas/artifactory/aql_adapter.py` — add `ConsumptionRow` +
  `ArtifactoryAqlAdapter.fetch_consumption_rows`, per the Code Map. Reuses
  `resolve_backing_repos` (do not duplicate topology-resolution logic).
- `src/pyforge/atlas/pipelines/artifactory_downloads/nodes.py` — add `_CONSUMPTION_COLS`,
  `fetch_artifactory_consumption`, `_JFROG_COLS`, `_pep503`,
  `build_enterprise_jfrog_consumption`, per the Code Map's exact column/default rules.
- `src/pyforge/atlas/pipelines/artifactory_downloads/pipeline.py` — wire both new nodes.
- `conf/base/catalog.yml` — `artifactory_consumption_raw` (raw) + `enterprise_jfrog_consumption`
  (derived) entries.
- `tests/catalog/conftest.py` — `PREFIX_TO_PIPELINE["enterprise"]`,
  `EXPECTED_PIPELINE_COUNTS["artifactory_downloads"]` +2, `EXPECTED_TOTAL` +2.
- `tests/artifactory/test_aql_adapter.py` — `fetch_consumption_rows` test suite.
- `tests/pipelines/artifactory_downloads/test_nodes.py` — `fetch_artifactory_consumption` +
  `build_enterprise_jfrog_consumption` test suite, including the `pep503`-parity fixture test.
- Verification housekeeping: confirm no `conf/local/` override redefines either new catalog
  entry; `grep -rn "enterprise_jfrog_consumption\|artifactory_consumption_raw"` across
  `_bmad-output/` to confirm `spec-23-3`'s already-drafted expectations (column names, `Block
  If` gate) match what this story actually ships — reconcile via a Spec Change Log entry on
  EITHER file if a mismatch surfaces, not a silent divergence.

**Acceptance Criteria:**
- Given `params:artifactory.virtual_repos` empty (the committed default), when the
  `artifactory_downloads` pipeline runs, then `fetch_artifactory_consumption` returns an
  empty frame with zero `ArtifactoryConfig`/`ArtifactoryAqlAdapter` construction — no live
  instance named, selected, or contacted.
- Given a mock transport serving canned consumption + download rows for the same package
  names, when the pipeline runs, then `enterprise_jfrog_consumption.parquet` carries exactly
  the 10 `complete-export-contract.md` §1 "Required columns", one row per distinct
  PEP-503-normalized name, with `artifactory_downloads`/`artifactory_version_count` correctly
  aggregated and telemetry columns correctly defaulted for any non-matching name on either
  side (outer-join semantics, no dropped rows).
- Given `pixi run -e pyforge-atlas kedro-catalog-check`, when run after this change, then it
  passes (naming/layer/prefix/no-inline-IO/AD-1/credential-allowlist conventions all hold for
  the 2 new catalog entries — in particular, `CREDENTIAL_ALLOWLIST` is UNCHANGED and no entry
  carries a `credentials:` key).
- Given `pixi run -e pyforge-atlas kedro-test`, when run after this change, then all existing
  `artifactory_downloads`/`aql_adapter` tests plus the new consumption-rollup tests pass.
- Given a raw name that PEP-503-normalizes to fewer than 2 characters, when
  `build_enterprise_jfrog_consumption` runs, then that row is silently dropped (never an
  empty-string `core_python_package_name`), matching `priority.py::pep503`'s own contract.

## Design Notes

**Resolving the credential-contract tension (a real conflict found during investigation):**
`complete-export-contract.md` §1's own words are "Credential contract: attended JFrog via
`_http.py` truststore chain; mock-first in CI (same injectable transport as
`spec-artifactory-download-intelligence`)." Read literally, this could suggest importing
`.claude/skills/conda-forge-expert/scripts/_http.py`'s `auth_headers_for`/
`inject_ssl_truststore` helpers into `pyforge.atlas` package code. That is not possible
without violating two established, deliberate boundaries this investigation confirmed: (1)
`_http.py` lives in a completely separate, non-importable tree
(`pipelines/artifactory_downloads/nodes.py`'s own docstring already states this convention
for `export_purls.py`, the sibling CFE-scripts module — "no pipeline package imports another
module's helpers... lives in a completely separate tree... not an importable package from
here"); (2) `ArtifactoryConfig`/`ArtifactoryAqlAdapter` (Story 15.1) deliberately carry NO
credential field and NO env-var resolver, by explicit design (`aql_adapter.py:17-22`) — "any
auth header a live call eventually needs is attached by the real transport, constructed
OUTSIDE package code at the later attended live bring-up." `factory/lasuite.py`'s
`LaSuiteClient` (the adapter's own cited precedent) follows the identical shape: zero
credential logic in package code, a live opener supplied later at an attended bring-up.
Resolution: the contract's phrase describes what the LATER, ATTENDED, out-of-package
transport construction step does when it happens (mirror `_http.py`'s JFROG_API_KEY →
JFROG_USERNAME+PASSWORD → `.netrc` priority chain and its truststore injection, functionally
— not a literal cross-tree import) — it is not an instruction for THIS story's package code.
This story ships mock-only, exactly like Stories 15.1-15.3; no `credentials:` catalog key, no
`CREDENTIAL_ALLOWLIST` change. `tests/catalog/conftest.py::STUB_CREDENTIALS` already carries
an unused `"jfrog": ["stub-user", "stub-key"]` entry (added ahead of need, presumably for
THAT later attended-bring-up story) — this story does not activate it.

**Why `fetch_consumption_rows` reuses `resolve_backing_repos` rather than re-resolving
topology:** `fetch_download_rows` already pays one topology round trip per virtual repo per
pipeline run. If `fetch_artifactory_consumption` independently called
`resolve_backing_repos` again for the same `virtual_repo`, a live run would double the
topology-resolution request volume for no benefit (the backing-repo list does not change
between the two telemetry queries within one run). Both `fetch_artifactory_downloads` and
`fetch_artifactory_consumption` independently construct their own `ArtifactoryAqlAdapter`
instance today (mirroring the existing single-adapter-per-node pattern — no shared adapter
object crosses node boundaries, keeping each node's construction ONLY on its own required
inputs) — so this is a per-node cost only when `virtual_repos` is non-empty (mock/live), never
in the committed empty-default path, and is an accepted, bounded duplication rather than a
correctness bug. A future optimization could fold both fetches into one adapter call sharing
one resolved topology, but that would conflate the two telemetry queries `aql_adapter.py`'s
own established "never conflate resolution and aggregation" rule already argues against doing
casually — left as-is for this story.

**Why the real AQL/Xray query shape for `platform_env_count`/`internal_app_count`/
`internal_component_count`/`internal_lob_count` is not specified
here:** these read as ORG-SPECIFIC custom telemetry/metadata (not standard vanilla-Artifactory
AQL primitives) — plausibly an Xray policy export, a custom properties query, or an internal
CDO system, not something a public Artifactory API reference can pin down generically. The
parent `spec-artifactory-download-intelligence`'s own Open Questions defer "which live
Artifactory instance, and when its attended bring-up happens" entirely — this story inherits
that same boundary for the NEW telemetry columns: the CONTRACT (column names/types/defaults,
verified against a mock transport) is fully specified and testable; the real endpoint path/
query is a later, attended, live-instance-specific detail, consistent with how
`resolve_backing_repos`'s `/api/repositories/{virtual_repo}` and `fetch_download_rows`'s
`/api/search/aql` paths are themselves representative/mock-servable contracts rather than
verified-against-a-real-instance endpoints.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass, 2 new catalog entries
  resolve, `CREDENTIAL_ALLOWLIST` unchanged.
- `pixi run -e pyforge-atlas kedro-test` — expected: all existing
  `artifactory_downloads`/`aql_adapter` tests + new consumption-rollup tests pass.
- `pixi run -e pyforge-atlas duckdb-singularity` — expected: stays green.
- `kedro run --pipelines artifactory_downloads` on an empty data root (committed
  `virtual_repos: []` default) — expected: exit 0; `artifactory_consumption_raw` and
  `enterprise_jfrog_consumption` both materialize as empty, correctly-columned frames; zero
  live network calls.

## Review Triage Log

### 2026-09-01 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` Spec said add `PREFIX_TO_PIPELINE["enterprise"]` but Story 21.5 already owns that prefix for `upstream_discovery`; used longer prefix `enterprise_jfrog_consumption` instead.
  - `[low]` `[patch]` `test_dag_resolves.py` node-count fixture stale at 4 after Story 23.2; updated to 6 nodes.

## Auto Run Result

Status: done

Summary: Shipped enterprise JFROG consumption telemetry rollup — separate `fetch_consumption_rows` transport round trip, `fetch_artifactory_consumption` + `build_enterprise_jfrog_consumption` nodes, two new catalog entries (`artifactory_consumption_raw`, `enterprise_jfrog_consumption`), full test coverage for I/O matrix rows.

Files changed:
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/aql_adapter.py` — `ConsumptionRow`, `fetch_consumption_rows`
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/__init__.py` — export `ConsumptionRow`
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/artifactory_downloads/nodes.py` — fetch/build nodes, `_pep503`
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/artifactory_downloads/pipeline.py` — wire 2 new nodes
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` — 2 catalog entries
- `src/shared/packages/pyforge-atlas/tests/catalog/conftest.py` — prefix map + counts (+2)
- `src/shared/packages/pyforge-atlas/tests/artifactory/test_aql_adapter.py` — consumption adapter tests
- `src/shared/packages/pyforge-atlas/tests/pipelines/artifactory_downloads/test_nodes.py` — node + pep503 tests
- `src/shared/packages/pyforge-atlas/tests/pipelines/test_dag_resolves.py` — pipeline node count 4→6

Review findings breakdown: 2 patches applied (prefix-map deviation, DAG node-count fixture); 0 deferred; 0 rejected.

Follow-up review recommendation: false (patched score: 3×0 + 1×1 = 1 < 5; no high-severity patches).

Verification performed:
- `pixi run -e pyforge-atlas kedro-catalog-check` — PASS (68 passed)
- `pixi run -e pyforge-atlas kedro-test` — PASS (full suite, exit 0)
- `pixi run -e pyforge-atlas duckdb-singularity` — PASS (6 passed)
- Targeted `-k "aql_adapter or artifactory_downloads or test_dag_resolves"` — PASS (68 passed)

Residual risks: Real Artifactory `/api/consumption/rollup` endpoint shape is mock-served only; live attended bring-up remains a later story. `enterprise_jfrog_names` still maps to `upstream_discovery` via the generic `enterprise` prefix (21.5 convention); only `enterprise_jfrog_consumption` maps to `artifactory_downloads`.

