---
title: 'Tier 3 bulk OS indexes — homebrew, nixpkgs, spack, debian, fedora (Story 23.1, Epic 23)'
type: 'feature'
created: '2026-08-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'pending-local-verify'
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/stories.yaml'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/epic-21-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `identity_complete_export.parquet`'s Assurance/cross-channel column group
(`complete-export-contract.md` §4) names 15 `in_<source>` BOOLs, but only 4 exist in shipped
code today: `pipelines/pypi_intelligence/nodes.py::flag_cross_channel` pivots
`pypi_cross_channel_repodata_raw` (bioconda/pytorch/nvidia/robostack conda-channel repodata)
into `in_bioconda`/`in_pytorch`/`in_nvidia`/`in_robostack`. The five OS-distro bulk indexes —
homebrew, nixpkgs, spack, debian, fedora — have no catalog entry, no dataset class, and no
flag node anywhere in `src/shared/packages/pyforge-atlas/`. `complete-export-contract.md`
§3.3 names the 5 target catalog entries (`discovery_homebrew_packages_raw` … `discovery_
fedora_packages_raw`) and their output columns (`in_homebrew` … `in_fedora`) but leaves the
per-source fetch/parse shape unspecified — that is this story's job to resolve.

**Approach:** Five new independent dataset classes (one per source; the sources' bulk-index
formats differ too much — JSON blob, JSON-keyed-dict, RFC822 control file, XML repodata — to
share one parameterized class the way the 4 conda channels share `CrossChannelRepodataDataset`)
in a new `datasets/tier3_sources.py` module, each subclassing `refresh.py::ExternalRefreshDataset`
for genuine AD-13 last-good/staleness (a stricter contract than today's `CrossChannelRepodataDataset`,
which only skips a failed channel for the current run with no persisted last-good — Design
Notes). Each gets its own refresh-trigger pipeline node (mirroring `refresh_vdb_store`/
`refresh_trending_candidates`) in `pipelines/pypi_intelligence/`, per `complete-export-contract.md`
§3.3's explicit "Add to `pypi_intelligence` cross-channel family" placement. One new pure node,
`flag_tier3_channels`, pivots the 5 raw frames into `in_homebrew`/`in_nixpkgs`/`in_spack`/
`in_debian`/`in_fedora` BOOLs keyed by PEP-503-normalized `pypi_name` (NOT `conda_name` — Design
Notes explains the deliberate deviation from `flag_cross_channel`'s key), landing in a new
`pypi_tier3_channel_flags` catalog output — the row-count floors from `catalog-sources.md`'s
"Scale sanity gates" table are extended with 5 new order-of-magnitude entries, enforced the
same fail-not-warn way.

## Boundaries & Constraints

**Always:**
- Fetch + parse for all 5 sources lives in `datasets/tier3_sources.py` (AD-2, dataset-owned
  IO); `pipelines/pypi_intelligence/nodes.py`'s 5 new trigger functions stay pure
  `params:ttls -> RefreshRequest` producers with zero HTTP/parse imports, mirroring
  `refresh_pypi_json_store`/`refresh_trending_candidates` exactly.
- Each of the 5 dataset classes subclasses `ExternalRefreshDataset` (`datasets/refresh.py:170`)
  and implements real AD-13 last-good: a fetch failure marks stale and returns/keeps the
  prior persisted Parquet, never an empty/partial clobber (`_mark_stale`/`_write`/
  `_store_exists`/`_store_mtime`, mirroring `VDBStoreDataset` (`refresh.py:383`) or
  `TrendingSnapshotDataset` (`datasets/upstream_discovery.py`, per `spec-13-1`) more closely
  than `CrossChannelRepodataDataset`'s current simpler per-channel skip.
- `flag_tier3_channels` is PURE `DataFrame(s) -> DataFrame` (AC-2 no-inline-IO gate,
  `tests/catalog/test_no_inline_io.py`), mirrors `flag_cross_channel`'s exact shape
  (`pipelines/pypi_intelligence/nodes.py:411-436`) with a 5-source input list instead of one
  combined `channel`-column frame (Design Notes explains why fan-out is per-CATALOG-ENTRY
  here, not per-ROW inside one dataset, unlike the 4 conda channels).
- `kedro-catalog-check` (naming/layer/credential/no-inline-IO/AD-1/pipeline-count/orphan-ttls
  conventions), `duckdb-singularity`, and `kedro-test` all stay green.
- Scale floors are asserted as hard test failures (`catalog-sources.md`: "sub-threshold =
  fail, not warn-only"), not warnings.

**Block If:** Story 21.4 ("Tier 1 catalog sources — SelfExplainML, Anaconda, Basilisk
packages, AOSS"; `stories.yaml` id `21.4`) is not `status: done`. `stories.yaml` declares
`depends_on: ["21.4"]` for this story; 21.4 is the story that hardens
`pypi_cross_channel_repodata_raw`/`CrossChannelRepodataDataset` (subdir + repodata-filename
fallback, per `catalog-sources.md` Tier 1) and establishes the SelfExplainML 5th conda
channel. No `spec-21-4-*.md` exists yet at dispatch-check time for this draft (verified
2026-08-30 against the live `planning-artifacts/specs/` directory and `CrossChannelRepodataDataset`
itself, which still only carries `_CROSS_CHANNEL_SPECS` = bioconda/pytorch/nvidia/robostack —
no SelfExplainML). This story does not itself require 21.4's code (the 5 new sources are
independent of `CrossChannelRepodataDataset`), but `stories.yaml`'s declared ordering is
honored rather than silently overridden — re-verify 21.4's live status before dispatch.

**Never:**
- Do not add the 5 new sources to `CrossChannelRepodataDataset`/`_CROSS_CHANNEL_SPECS` or
  `flag_cross_channel`/`_CROSS_CHANNELS` — those are conda-channel repodata (Phase Q), a
  different fetch shape from OS-distro bulk indexes; this story adds SIBLING catalog entries
  and a SIBLING flag node, never extends the existing 4-channel tuple.
- Do not join the new `in_<source>` BOOLs onto `identity_complete_export.parquet` or
  `inventory_verified_packages.parquet` — those exports are Stories 23.4/23.5's job; this
  story's own deliverable is the flag-bearing `pypi_tier3_channel_flags` output only (exactly
  as `pypi_cross_channel_flags` itself is not yet joined into any export today either).
- Do not attempt a live-network smoke test against the real homebrew/nixpkgs/spack/debian/
  fedora endpoints in CI — every test injects a stubbed `refresher`, matching every other
  `ExternalRefreshDataset` subclass in this codebase (`VDBStoreDataset`, `TrendingSnapshotDataset`).
- Do not invent a cross-source name-normalization heuristic (stripping Debian's `python3-`/
  `python-`, spack's `py-`, or resolving nixpkgs' `python3Packages.<attr>` nesting) — v1 flags
  membership on the PEP-503 fold of each source's raw reported name verbatim; per-source
  prefix-stripping is an explicit Open Question below, not solved here (Simplicity First).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, all 5 sources fetch | Stubbed refreshers return well-formed responses for all 5 | Each `discovery_<source>_packages_raw` persists a non-empty `name`-column Parquet; `flag_tier3_channels` produces one row per distinct normalized `pypi_name` with the corresponding `in_<source>` True | No error |
| One source's fetch fails | 4 of 5 refreshers succeed, 1 raises | The failed source's store keeps last-good (or empty-if-first-run) + marks stale; the other 4 persist normally; `flag_tier3_channels` still runs on whatever 5 raw frames the catalog resolves (a stale-but-present frame, or an empty one on first run) | WARN logged per source, never raises |
| First-ever run, no last-good, fetch also fails | No prior Parquet for that source, refresher raises or unwired (offline `kedro-catalog-check`) | Empty, correctly-columned frame, marked stale — same shape as every other `ExternalRefreshDataset` subclass's degrade | No error, no network |
| Fetch succeeds but yields a suspiciously small row count | e.g. homebrew returns 12 formula names (a truncated/broken response) | The scale-floor catalog test fails loudly (fail, not warn) — this is a TEST-time gate on the persisted store's row count, not an in-dataset gate (the dataset itself still persists whatever it received; AD-13 never rejects non-empty data) | Test failure, not a runtime exception |
| `flag_tier3_channels`, all 5 inputs empty | Fresh bootstrap, nothing fetched yet | Returns an empty, correctly-columned frame (`pypi_name` + 5 `in_<source>` bool columns) | Never raises |
| A raw frame is missing its `name` column (malformed catalog override) | `discovery_homebrew_packages_raw` resolves to a frame without `name` | That source contributes zero flags (skipped, not raised) for this run; other 4 sources still flow through | Never raises |

</intent-contract>

## Code Map

- `src/pyforge/atlas/datasets/refresh.py` — `ExternalRefreshDataset` base (`:170`), `_mark_stale`
  (`:225`), `save()`'s AD-13 orchestration (`:288-328`), `StalenessMarker` (`:150`) — the base
  every one of the 5 new classes subclasses. `VDBStoreDataset` (`:383`) is the closest existing
  template for `_write`/`load`/`_store_exists`/`_store_mtime` shape.
- `src/pyforge/atlas/datasets/upstream_discovery.py` (per `spec-13-1`) — `TrendingSnapshotDataset`
  is a second, slightly newer `ExternalRefreshDataset` subclass template (constructor takes the
  fetch URL(s) + an injectable `fetcher: Callable[[str], str] | None`, wraps it into the bound
  `_do_refresh` passed as `refresher=` to `super().__init__()`) — closer in shape to what each
  of the 5 tier-3 classes needs (one HTTP fetch + one pure parse function) than `VDBStoreDataset`.
- `src/pyforge/atlas/datasets/core_sources.py:492-609` — `_CROSS_CHANNEL_SPECS`,
  `_resolve_anaconda_channel_urls`, `_fetch_repodata_at_url`, `CrossChannelRepodataDataset` —
  the EXISTING Phase Q pattern this story's `stories.yaml` `invoke_dev_with` hint names
  ("pypi_intelligence cross-channel pattern"); mirror its APIDataset-composition IO idiom
  (`_fetch_repodata_at_url` wraps `datasets.api.APIDataset` rather than importing `requests`
  directly) — do NOT extend `_CROSS_CHANNEL_SPECS` itself (Never, above). Note this class's
  own AD-13 gap (Design Notes) — do not copy its skip-and-degrade shape verbatim.
- `src/pyforge/atlas/datasets/tier3_sources.py` (new) — 5 classes: `HomebrewPackagesDataset`,
  `NixpkgsPackagesDataset`, `SpackPackagesDataset`, `DebianPackagesDataset`,
  `FedoraPackagesDataset`. Each: `ExternalRefreshDataset` subclass, constructor takes
  `filepath`, source URL(s), `fetcher: Callable[[], bytes | str] | None = None` (mirrors
  `TrendingSnapshotDataset`'s injection shape), `cadence_seconds`, `metadata`; `_write`
  validates a `name` column is present (reject/never-write otherwise, mirroring
  `VDBStoreDataset._write`'s malformed-column rejection); `load()` degrades to an empty
  `["name"]`-column frame on a missing/corrupt store. One pure parse function per source
  (`parse_homebrew_formulae_json`, `parse_nixpkgs_packages_json`, `parse_spack_packages`,
  `parse_debian_packages_control`, `parse_fedora_packages`) — each takes the raw fetched
  payload and returns `list[dict]`/`list[str]` names, never raising on a malformed payload
  (returns `[]`, mirrors `parse_trending_html`'s zero-match-returns-`[]` contract).
- `src/pyforge/atlas/datasets/__init__.py` — re-export the 5 new dataset classes (and their
  parse functions if `catalog.yml`/tests need to import them directly), mirroring how
  `TrendingSnapshotDataset`/`parse_trending_html` are re-exported today.
- `src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py` — add `_CROSS_CHANNELS` sibling
  constant `_TIER3_CHANNELS = ("homebrew", "nixpkgs", "spack", "debian", "fedora")` (used only
  by `flag_tier3_channels`'s output-column list, kept separate from `_CROSS_CHANNELS` per the
  Never clause above); 5 small trigger functions (`refresh_discovery_homebrew_store`, …
  `refresh_discovery_fedora_store`), each `params:ttls -> RefreshRequest`, sharing one small
  internal `_tier3_refresh_request(ttls: dict, key: str) -> RefreshRequest` helper (mirrors
  `refresh_trending_candidates`/`_coerce_cadence`'s shape, de-duplicated across the 5 the same
  way spec-21-2 de-duplicated `VcsHostSeedDataset`/`RegistryUpstreamDataset`'s shared
  persistence plumbing) to avoid 5 near-identical bodies; `flag_tier3_channels(discovery_
  homebrew_packages_raw, discovery_nixpkgs_packages_raw, discovery_spack_packages_raw,
  discovery_debian_packages_raw, discovery_fedora_packages_raw) -> pd.DataFrame` — pure pivot,
  `pypi_name` PK + 5 `in_<source>` bools, PEP-503-normalized join key (reimplemented locally
  per this codebase's no-cross-module-`nodes.py`-import convention — see
  `artifactory/identity_join.py:57-61`'s `_normalize_pypi_name` for the exact regex to mirror:
  `re.compile(r"[-_.]+")`, lowercase, collapse to `-`).
- `src/pyforge/atlas/pipelines/pypi_intelligence/pipeline.py` — 5 new
  `node(func=refresh_discovery_<source>_store, inputs="params:ttls", outputs="discovery_
  <source>_packages_raw", name="refresh_discovery_<source>_store")` entries (mirrors
  `refresh_pypi_json_store`'s wiring at `pipeline.py:40-45`) + one
  `node(func=flag_tier3_channels, inputs=["discovery_homebrew_packages_raw", …],
  outputs="pypi_tier3_channel_flags", name="flag_tier3_channels")` (mirrors `flag_cross_channel`
  at `pipeline.py:82-87`).
- `conf/base/catalog.yml` — 5 new raw entries (layer `raw`, `type:
  pyforge.atlas.datasets.<Source>PackagesDataset`, `filepath: data/stores/discovery_<source>_
  packages_raw` — per Story 21.2's convention, `ExternalRefreshDataset`-backed stores live
  under `data/stores/…`, a narrower exempt prefix `test_output_filepaths_follow_data_layer_
  name_convention` already carves out, `tests/catalog/test_conventions.py:44-48`); one new
  output entry `pypi_tier3_channel_flags` (layer `primary`, `type: pyforge.atlas.datasets.
  IncrementalParquetDataset`, `filepath: data/primary/pypi_tier3_channel_flags/pypi_tier3_
  channel_flags.parquet`, `# A3: IncrementalParquetDataset` marker comment — mirrors
  `pypi_cross_channel_flags` at `catalog.yml:310-315` exactly).
- `conf/base/parameters.yml` — under `ttls:`'s `# -- pypi_intelligence` sub-section (near
  `:28-35`), add 5 entries (`discovery_homebrew_packages_raw: 604800  # 7 d [future_consumer:
  23.1]`, one per source — mirrors `trending_candidates`'s exact `[future_consumer: 13.1]`
  annotation style at `parameters.yml:53`) plus one FLIP_LIST entry with NO annotation
  (`pypi_tier3_channel_flags: 604800  # 7 d`, mirrors `pypi_cross_channel_flags: 604800` at
  `parameters.yml:32`).
- `tests/catalog/conftest.py` — `PREFIX_TO_PIPELINE` (`:68-82`): add 5 SPECIFIC entries —
  `"discovery_homebrew": "pypi_intelligence"`, `"discovery_nixpkgs": "pypi_intelligence"`,
  `"discovery_spack": "pypi_intelligence"`, `"discovery_debian": "pypi_intelligence"`,
  `"discovery_fedora": "pypi_intelligence"` — NOT a bare `"discovery"` entry (Design Notes:
  this is a deliberate longest-prefix-match resolution against the future generic `"discovery"
  -> "upstream_discovery"` mapping Story 21.4/21.5 is expected to add for the OTHER
  `discovery_*` entries in `catalog-sources.md`'s Tier 1/2 tables). `EXPECTED_PIPELINE_COUNTS`
  (`:88-100`): bump `"pypi_intelligence"` by 6 relative to whatever value is current at
  implementation time (5 raw + 1 output — do not hardcode against this draft's `15`, since
  sibling stories 21.x/22.x are landing concurrently and may have already moved it).
  `EXPECTED_TOTAL` (`:101`): bump by 6, same relative-not-absolute caveat. `FLIP_LIST`
  (`:104-120`): add `"pypi_tier3_channel_flags"`.
- `tests/pipelines/test_dag_resolves.py:89` —
  `test_pypi_intelligence_pipeline_has_eleven_nodes` hardcodes the pipeline's node count in
  its OWN NAME; rename to match the new count (11 + 6 = 17, same relative-count caveat as
  above) and update its body's node-name list/assertions.
- `tests/parity/test_parity_complete.py:18` — `_NODE_COUNTS["pypi_intelligence"]` bump by 6
  (same relative caveat).
- `tests/datasets/` (new files) — `test_tier3_sources.py`: one test class per dataset class,
  covering the I/O matrix rows above (stub `fetcher`/`refresher`, never real network) plus a
  fixture test per parse function (a captured-shape response fixture → expected rows; a
  malformed/empty response → `[]`).
- `tests/pipelines/pypi_intelligence/` (existing dir) — `test_nodes.py`: tests for the 5
  trigger functions (mirror `refresh_trending_candidates`'s trigger-node test style) and for
  `flag_tier3_channels` (happy path, all-empty, malformed-column-skip, PEP-503-fold
  correctness on a mixed-case/underscore/dotted name fixture).
- `tests/catalog/test_conventions.py` / the scale-floor mechanism — extend
  `catalog-sources.md`'s "Scale sanity gates" table with 5 new order-of-magnitude rows
  (Design Notes has the proposed values) and add the corresponding assertion (a
  bootstrap-smoke or catalog-level test reading the persisted row count — follow whatever
  mechanism Story 21.3/21.4 lands for the EXISTING floors, since `catalog-sources.md` names
  this mechanism as already-established policy but this investigation found no `floor`-named
  test today; if 21.3/21.4 have not yet landed a floor-assertion helper by this story's
  dispatch, add one new `tests/catalog/test_scale_floors.py` module covering all floors,
  existing + new, in one place).

## Tasks & Acceptance

**Execution:**
- `src/pyforge/atlas/datasets/tier3_sources.py` (new) — 5 `ExternalRefreshDataset` subclasses
  + 5 pure parse functions, per the Code Map. Each class's `_write` rejects a frame missing
  the `name` column; `load()` degrades to an empty `["name"]` frame on a missing/corrupt
  store; no dataset class imports a denylisted client directly (`requests`/`httpx`/`urllib3`
  — compose via `datasets.api.APIDataset`, mirroring `_fetch_repodata_at_url`'s idiom, or
  accept raw bytes/text through the injected `fetcher` exactly like `TrendingSnapshotDataset`
  does — either is acceptable per source, since Debian/Fedora's bulk indexes are gzip'd
  RFC822/XML, not JSON, and may not fit `APIDataset`'s JSON-decode assumption cleanly).
- `src/pyforge/atlas/datasets/__init__.py` — re-export the 5 new classes (+ parse functions
  if catalog/tests reference them by import).
- `src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py` — `_TIER3_CHANNELS` constant; 5
  trigger functions + shared `_tier3_refresh_request` helper; `flag_tier3_channels` pure pivot
  node (PEP-503-normalized `pypi_name` key, per-source raw `name` verbatim, no prefix-stripping
  heuristics — Never clause).
- `src/pyforge/atlas/pipelines/pypi_intelligence/pipeline.py` — wire the 5 trigger nodes + the
  1 flag node.
- `conf/base/catalog.yml` — 5 raw entries under `data/stores/…` + 1 `pypi_tier3_channel_flags`
  primary-layer `IncrementalParquetDataset` output with its `# A3:` marker.
- `conf/base/parameters.yml` — 5 `ttls:` entries with `[future_consumer: 23.1]` + 1
  `pypi_tier3_channel_flags` `ttls:` entry (FLIP_LIST member, no annotation).
- `tests/catalog/conftest.py` — `PREFIX_TO_PIPELINE` (5 specific `discovery_<source>` keys,
  not a bare `discovery`), `EXPECTED_PIPELINE_COUNTS["pypi_intelligence"]` +6,
  `EXPECTED_TOTAL` +6, `FLIP_LIST` +`pypi_tier3_channel_flags`.
- `tests/pipelines/test_dag_resolves.py`, `tests/parity/test_parity_complete.py` — node-count
  fixture updates (rename the eleven-nodes test, bump `_NODE_COUNTS`).
- `tests/datasets/test_tier3_sources.py` (new), `tests/pipelines/pypi_intelligence/test_nodes.py`
  (extend) — full I/O-matrix + parse-function + flag-node coverage per Code Map.
- Scale-floor assertions for the 5 new sources (Design Notes has proposed order-of-magnitude
  values; re-verify each against the live index's actual current size before hardcoding — the
  existing table's own convention).
- Verification housekeeping: `grep -rn "_CROSS_CHANNELS\b"` to confirm the new
  `_TIER3_CHANNELS` constant is never accidentally merged into the existing tuple; confirm no
  `conf/local/` override redefines any of the 6 new catalog entries.

**Acceptance Criteria:**
- Given stubbed refreshers returning well-formed responses for all 5 sources, when the
  `pypi_intelligence` pipeline runs, then all 5 `discovery_<source>_packages_raw` stores
  persist non-empty, and `pypi_tier3_channel_flags` carries one row per distinct
  PEP-503-normalized name with the correct `in_<source>` flags set.
- Given one source's stubbed refresher raises, when its trigger node's `save()` runs, then
  that source's last-good Parquet (or empty-if-first-run) is preserved and a staleness marker
  is written, while the other 4 sources are unaffected.
- Given `pixi run -e pyforge-atlas kedro-catalog-check`, when run after this change, then it
  passes (naming/layer/no-inline-IO/AD-1/credential-allowlist/orphan-ttls/A3-flip-marker/
  pipeline-count conventions all hold for the 6 new catalog entries).
- Given a persisted `discovery_<source>_packages_raw` store whose row count is below its
  proposed scale floor, when the scale-floor test runs, then it FAILS (not warns).
- Given `pixi run -e pyforge-atlas kedro-test`, when run after this change, then all existing
  tests + the new tier-3 test files pass, and `test_pypi_intelligence_pipeline_has_*_nodes`
  (renamed) reflects the +6 node count.

## Design Notes

**Why 5 separate dataset classes, not one parameterized class like `CrossChannelRepodataDataset`:**
the 4 existing conda channels share ONE `${runtime_params:cross_channel,bioconda}`-templated
URL because they are all the SAME anaconda-channel `current_repodata.json`/`repodata.json`
JSON shape (`core_sources.py:544-564`'s `_fetch_channel_repodata` loop). Homebrew
(`formulae.brew.sh/api/formula.json`, one big JSON array), nixpkgs
(`channels.nixos.org/nixpkgs-unstable/packages.json`, JSON object keyed by attribute path —
exact channel/endpoint choice is a step-03 research task, mirrors spec-21-2's registry-endpoint
precedent), spack (package listing endpoint TBD — lowest-confidence source in this
investigation; step-03 research required before any URL is hardcoded), debian (a `Packages.gz`
control-file from a mirror, RFC822 text format, gzip-compressed — NOT JSON), and fedora
(repodata `primary.xml.gz` or the Fedora Packages API — XML or JSON depending on the chosen
endpoint) are five genuinely different bulk-index shapes. Forcing them into one parameterized
class the way the registries in spec-21-2's `RegistryUpstreamDataset` share `_REGISTRY_SPECS`
would not fit either — that precedent works because all 8 registries are uniform
"REST-GET-one-package, extract-one-field" per-PACKAGE lookups; these 5 are uniform-shape-per-source
BULK index dumps, but NOT uniform-shape ACROSS sources. Five classes is the honest mapping of
one concept ("dataset-owned fan-out") onto five heterogeneous fetch/parse mechanics — the
"fan-out" happens at the PIPELINE level (5 catalog entries, 5 trigger nodes) rather than inside
one dataset's `load()` loop, which is the closest analogue this codebase has to
`CrossChannelRepodataDataset`'s docstring phrase without pretending the 5 sources are uniform
when they are not.

**Why real AD-13 (`ExternalRefreshDataset`), not `CrossChannelRepodataDataset`'s current
shape:** reading `core_sources.py:583-603`, `CrossChannelRepodataDataset.load()` does NOT
persist a last-good Parquet or write a `StalenessMarker` — a failed channel is simply
`logger.warning`'d and skipped FOR THAT RUN; there is no on-disk store to fall back to on the
next run either, and the class's `save()` raises `NotImplementedError` (read-only). This is a
materially weaker contract than `VDBStoreDataset`/`TrendingSnapshotDataset`'s genuine
persisted-last-good-plus-marker AD-13 shape, even though `catalog-sources.md`'s own "Scale
sanity gates" section and this story's `stories.yaml` `invoke_dev_with` hint both invoke
"AD-13 last-good" by name for the Tier 3 sources. Rather than copy the existing gap forward,
this story's 5 new classes implement the STRICTER, genuinely-AD-13-compliant shape (mirroring
`VDBStoreDataset`/`TrendingSnapshotDataset`). Story 21.4 (this story's prerequisite) is
expected to separately harden `CrossChannelRepodataDataset` itself to the same standard — this
story does not do that hardening (Never clause), only builds the 5 new sources correctly from
the start.

**Resolving the `discovery_` prefix collision (a real conflict found during investigation):**
`catalog-sources.md`'s Tier 1/Tier 2 tables already propose `discovery_basilisk_packages_raw`,
`discovery_aoss_free_python_raw`, `discovery_aoss_premium_python_raw`,
`discovery_about_maintainers_raw`, `discovery_anaconda_dist_2026x_raw` — all destined for the
`upstream_discovery` pipeline (Stories 21.4/21.5). `complete-export-contract.md` §3.3 is
equally explicit that THIS story's 5 `discovery_<os-source>_packages_raw` entries belong to
`pypi_intelligence`. `tests/catalog/conftest.py::pipeline_for` resolves a catalog entry's
owning pipeline by LONGEST-PREFIX match against `PREFIX_TO_PIPELINE` (`conftest.py:362-367`)
— a single generic `"discovery": "upstream_discovery"` mapping (which 21.4/21.5 will plausibly
add for their own entries) would silently swallow this story's 5 entries too, contradicting
the contract. Resolution: register the 5 FULL, SPECIFIC prefixes
(`discovery_homebrew`/`discovery_nixpkgs`/`discovery_spack`/`discovery_debian`/`discovery_fedora`)
mapped to `pypi_intelligence` — longest-prefix-match means these always win over a shorter
generic `discovery` fallback, regardless of which story (this one or 21.4/21.5) lands first.
No coordination with 21.4/21.5's authors is required; if 21.4/21.5 also add specific
`discovery_basilisk`/`discovery_aoss_free`/etc. prefixes (the same resolution pattern), there
is no collision either, since every prefix this story adds is already fully specific.

**Proposed scale floors (order of magnitude; re-verify against each live index's actual
current size before hardcoding, per `catalog-sources.md`'s own caveat for the existing 5
floors):**

| Index | Proposed floor | Basis |
|-------|----------------|-------|
| homebrew (`formulae.brew.sh`) | ~5,000+ | homebrew-core carries roughly 6,000-7,000 formulae |
| nixpkgs | ~50,000+ | nixpkgs-unstable carries well over 80,000 packages |
| spack | ~3,000+ | the spack builtin package repo carries several thousand packages; lowest-confidence source, verify at implementation time |
| debian (sid main) | ~20,000+ | Debian sid's main source-package list runs in the tens of thousands |
| fedora (rawhide) | ~15,000+ | Fedora rawhide's source-package count runs in the high five figures... low tens of thousands |

**Open Question — per-source name normalization:** each OS index's raw package-name spelling
often does not match its PyPI project name 1:1 (Debian/Fedora commonly prefix `python3-`/
`python-`, spack prefixes `py-`, nixpkgs nests under a `python3Packages.<attr>` attribute
path). v1 flags `in_<source>` on the PEP-503 fold of the raw reported name only — a real
Python-package match hiding behind one of these prefixes will under-report as `in_<source>=
False`. This is an intentional Simplicity-First v1 boundary, not an oversight; a follow-up
story can add per-source prefix-stripping once the false-negative rate is measured against
real data.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass, 6 new catalog entries
  resolve, no naming/layer/prefix/credential/A3-marker violations.
- `pixi run -e pyforge-atlas kedro-test` — expected: all existing tests + new tier-3 tests
  pass; the renamed pipeline-node-count test reflects +6.
- `pixi run -e pyforge-atlas duckdb-singularity` — expected: stays green (no new sqlite3/
  denylisted-client imports).
- `kedro run --pipelines pypi_intelligence` on an empty data root with stubbed/no refreshers —
  expected: exit 0; all 6 new entries materialize as empty-but-correctly-columned frames,
  each raw source marked stale (offline / no fetcher wired), matching the existing
  `ExternalRefreshDataset` offline contract.

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `in-review` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `86d1cdf3ee 2026-09-17 land atlas fold: one chain — 13 Dreams, 10 Specs, rekey 2026-09-17` — that promotion is the ruling this record now reflects.

Implementation complete (Cursor bmad-build-auto dispatch). Added `datasets/tier3_sources.py`
(five `ExternalRefreshDataset` subclasses + parse functions), `flag_tier3_channels` + five
`refresh_discovery_*_store` trigger nodes, catalog/parameters/conftest updates (+6 catalog
entries, +6 pipeline nodes), scale-floor tests, tier-3 dataset/node tests, and parity harness
fixture for `flag_tier3_channels`. Five new `endpoint_bases` in `globals.yml` route Tier-3
URLs through `${globals:...}` (AD-13).

Verification: initial `kedro-catalog-check` failed on hardcoded URLs (fixed); full re-run of
`kedro-catalog-check`, `kedro-test`, and `duckdb-singularity` pending — shell unavailable in
the completing agent turn. Run locally before merge.

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `22-1-tier-3-bulk-os-indexes: done`).
- Auto Run Result `Status: in-review` → `done` (see the reconcile line under it).
