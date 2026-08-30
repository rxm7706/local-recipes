---
title: 'Tier 1 catalog sources: SelfExplainML, Anaconda, Basilisk packages, AOSS (Story 21.4, Epic 21)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/epic-21-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `catalog-sources.md`'s Tier 1 table names 6 new raw sources the Phase C
public-index catalog needs (CAP-2) that do not exist in `catalog.yml` today:
SelfExplainML repodata (extend an existing entry), Anaconda main channeldata,
Anaconda Dist 2026.x, Basilisk `/v1/packages`, and Google AOSS free + premium
Python. None is declared; the existing `pypi_cross_channel_repodata_raw` (which
SelfExplainML extends) is also under-hardened (single-subdir-per-channel, no
documented repodata-filename fallback test coverage). Without these, `--live-catalog`
inventory metrics cannot reproduce today's Basilisk/AOSS/Anaconda/cross-channel
columns from Parquet alone (SPEC.md CAP-2 success), and two of the six sources
(AOSS free, Anaconda Dist) have no committed strategy for air-gapped/offline
operation.

**Approach:** Declare all 6 entries in `catalog.yml`, each tagged with one of the
5 documented fetch modes (live / upstream Parquet / external-refresh / tracked
seed / credentialed opt-in — catalog-sources.md's own vocabulary), reusing the
Story 21.2 `_ParquetRefreshStore`/`ExternalRefreshDataset` AD-13 last-good +
staleness-marker pattern for every source whose primary path is a live fetch
(mirrors `TrendingSnapshotDataset`/`VDBStoreDataset` — never a bespoke
persistence shape). SelfExplainML is NOT a new catalog entry — it is a 5th
tuple in `CondaChanneldataDataset`'s sibling `CrossChannelRepodataDataset`'s
`_CROSS_CHANNEL_SPECS`, alongside a hardening pass (broadened per-channel
subdir fallback lists) for the 4 existing channels. Anaconda main channeldata
reuses `CondaChanneldataDataset` UNCHANGED (catalog-sources.md's own "Same
parser as core_channeldata_raw" instruction) — zero new dataset code, one new
catalog entry + one new intermediate materializing node (mirrors how
`core_channeldata_raw` is only ever consumed transiently by
`enumerate_conda_packages`, never itself persisted). Every entry whose `load()`
never populates without a `save()`-triggering pipeline node gets one wired into
its owning pipeline (mirrors `refresh_vcs_github_store`/`refresh_trending_candidates`
— the exact pipeline-dormancy mistake Story 21.2's pass-1 made and had to
amend for). The 2 numeric scale-sanity floors this story owns (AOSS free
≥1,000, Anaconda main ≥5,000) plus Basilisk's qualitative
non-zero-when-healthy floor are asserted by a new offline, fixture-driven
catalog test — sub-threshold fails hard, never warn-only (catalog-sources.md's
own "Scale sanity gates" section).

## Boundaries & Constraints

**Always:**
- Every entry's `type:` resolves offline under `kedro-catalog-check` with stub
  config (no network at `__init__`) — mirrors every existing dataset class in
  `datasets/`.
- Every live-fetch entry (Anaconda Dist, Basilisk packages, AOSS premium)
  subclasses `refresh.py::ExternalRefreshDataset` and gets ONE refresh-trigger
  pipeline node (`inputs="params:ttls"`, `outputs=<catalog entry>`) mirroring
  `refresh_vcs_github_store`/`refresh_trending_candidates` — an entry with a
  `save()`-gated `load()` and no writer node is the exact pipeline-dormancy
  defect Story 21.2 had to revert and amend for (see that spec's Spec Change
  Log). **Split pipelines per SPEC Constraints** (the story's own
  `invoke_dev_with`): SelfExplainML + Anaconda main route through
  `pypi_intelligence` / `core` respectively (their catalog names already carry
  those prefixes); Anaconda Dist + Basilisk packages + AOSS free + AOSS
  premium all carry the NEW `discovery_` prefix and route through
  `upstream_discovery` — see Design Notes for why Anaconda Dist resolves to
  `upstream_discovery`, not `core`, despite catalog-sources.md's own table
  listing "core or upstream_discovery" for that one row.
- Every new `endpoint_bases` key (only 2 needed: `ANACONDA_DIST_BASE_URL`,
  `AOSS_PREMIUM_BASE_URL` — Anaconda main and Basilisk packages reuse existing
  override points) is added to `globals.yml` per its own header convention
  ("New sources add exactly one override point") AND to every pinned count/set
  `tests/catalog/test_override_points.py` and `conftest.py` assert against —
  a new override point that isn't added to the pinned sets fails
  `kedro-catalog-check` by construction, not silently.
- `PREFIX_TO_PIPELINE` (tests/catalog/conftest.py) gains exactly one new entry:
  `"discovery": "upstream_discovery"`. `EXPECTED_PIPELINE_COUNTS` and
  `EXPECTED_TOTAL` are bumped by the exact new-entry delta (5 raw + 1
  materializing intermediate = 6; see Code Map for the per-pipeline split).
- The AOSS free Python tracked seed and the Anaconda Dist 2026.x seed-fallback
  file are git-tracked (under `conf/base/seeds/`, NOT `data/` — the package's
  `data/` root is gitignored wholesale, confirmed via `.gitignore:24` and the
  repo-root `.gitignore:731`), so they survive a fresh clone with zero network
  (the literal "for air-gap" requirement in catalog-sources.md's own Notes
  column).
- `tests/parity/fixtures/pypi_intelligence/flag_cross_channel.json`'s expected
  output rows are updated for the new `in_selfexplainml` column (`_CROSS_CHANNELS`
  in `pypi_intelligence/nodes.py` grows from 4 to 5 values) — `parity-diff`
  stays green.
- The new scale-floor test asserts against **fixture-injected** fetcher
  payloads of realistic size, never a live network call (AD-11/NFR-1 — the
  whole `tests/catalog/` suite is offline and non-credentialed by design;
  "Bootstrap smoke" in catalog-sources.md's own wording is satisfied by an
  offline catalog test, not a live-network pytest).

**Block If:** None — every fetch-mode/pipeline-routing decision below resolves
from catalog-sources.md's own vocabulary + notes, the Story 21.2 AD-13
precedent, and the machine-enforced `PREFIX_TO_PIPELINE` naming-convention
gate; nothing here requires a human judgment call the spec doesn't already
make.

**Never:**
- Do not add `discovery_about_maintainers_raw` or extend `org_audit_candidates`
  with curated-org sweeps — those are Tier 2 (catalog-sources.md's own table)
  and explicitly Story 21.5's scope ("Tier 2 sources: about, curated orgs,
  Artifactory names", epic-21-context.md's story list). SPEC.md's Constraints
  section phrases its "Tier 1 split" sentence as "...Basilisk packages + AOSS
  + about + curated orgs → upstream_discovery", which reads as if "about" and
  "curated orgs" belong to this story too — they do not; that sentence is
  describing pipeline ROUTING for the whole discovery-shaped source family,
  not this story's scope, which is fixed by catalog-sources.md's Tier 1 table
  and the epic's own per-story title.
- Do not touch Tier 0 entries (`core_channeldata_raw`, `pypi_simple_index_raw`,
  `pypi_json_raw`, etc.) or their floors (conda-forge channeldata ~30k+, PyPI
  simple index non-empty) — those are Story 21.3's ("Tier 0 harden and
  `--live-catalog` contract") scope, a different axis from this story's net-new
  Tier 1 sources.
- Do not add a literal Internet Archive / Wayback Machine HTTP integration for
  AOSS premium's "Wayback last-good" note — no dataset in this codebase
  integrates with `web.archive.org`, and Simplicity First favors the reading
  that "Wayback last-good" is descriptive shorthand for the SAME AD-13
  keep-last-good-Parquet degrade every other `ExternalRefreshDataset` subclass
  already has (see Design Notes for the full reasoning + the flag if this
  reading is wrong).
- Do not join, classify, or wire any of these 6 sources into the identity
  export, the metrics runner, or a `--live-catalog` consumer — that is Story
  21.6 (identity join) / 21.7 (quartet thin-out) / 21.8 (end-to-end gate)
  territory. This story's done_checkpoint is exactly three things: the raw
  datasets exist in `catalog.yml`, `kedro-catalog-check` is green, and the
  scale-sanity floors pass — not full pipeline integration.
- Do not fabricate the real AOSS free-tier Python package list, the Anaconda
  Dist 2026.x seed content, or either live endpoint's exact URL/HTML shape
  from training data — see Design Notes' step-03 research items.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh bootstrap, no prior stores | Empty data root | `kedro-catalog-check` resolves all 6 new entries offline; a `kedro run --pipelines core,upstream_discovery,pypi_intelligence` completes with the 3 new refresh-trigger nodes marking stale (no live fetcher wired offline) rather than failing | Never raise; mark stale, AD-13 |
| Anaconda Dist scrape layout breaks (0 rows) | Live fetch succeeds, parser matches nothing | Falls back to the tracked seed file content | WARN-logged, never a crash (mirrors `TrendingSnapshotDataset`'s Search-API-fallback shape) |
| AOSS premium live doc unreachable | Network/4xx/5xx | Keep last-good Parquet + mark stale | Log warning, never clobber last-good with empty |
| AOSS free seed file present (the normal case) | Git-tracked JSON under `conf/base/seeds/` | `TrackedSeedDataset.load()` returns the full seed as a `pypi_name`-column frame, no network | Never raises; a missing/corrupt file (should not happen in a real clone) degrades to an empty frame + a WARN log, not a crash |
| Basilisk `/v1/packages` fetch fails | Endpoint down | Keep last-good + mark stale (mirrors `VDBStoreDataset`) | Never raise |
| SelfExplainML channel absent under `noarch` | Channel only publishes `linux-64` | The hardened per-channel subdir fallback list tries `linux-64` before giving up | WARN-logged "channel unavailable" only if EVERY subdir/filename combo fails |
| Scale-floor test, fixture below documented floor | AOSS free fixture with 500 rows (< 1,000 floor) | Test FAILS (not warn) | Assertion failure, not a log line |
| `core_anaconda_main_channeldata_raw` malformed payload | Non-JSON / non-dict response | `CondaChanneldataDataset.load()` (unchanged, reused as-is) returns the existing empty `conda_name`/`subdirs` frame | Matches `core_channeldata_raw`'s existing degrade — no new code path |

</intent-contract>

## Code Map

- `src/pyforge/atlas/datasets/core_sources.py` — `_CROSS_CHANNEL_SPECS` (~L492):
  add `("selfexplainml", "selfexplainml", ("noarch", "linux-64"))`; broaden the
  4 existing channels' subdir tuples to a 2-subdir fallback list each (the
  "harden ... subdir + repodata fallback" task — `_REPDATA_FILENAMES`'s
  `current_repodata.json`/`repodata.json` fallback already exists and needs no
  change, only the per-channel `subdirs` tuple needs broadening).
  `CondaChanneldataDataset` (~L375) is reused UNCHANGED for
  `core_anaconda_main_channeldata_raw` — zero code change, only a new catalog
  entry pointing its `url:` at a different channel path.
- `src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py` — `_CROSS_CHANNELS`
  (~L35): add `"selfexplainml"` as the 5th value (drives `flag_cross_channel`'s
  `in_selfexplainml` output column automatically — no other code change in
  this file).
- `src/pyforge/atlas/datasets/basilisk.py` — add `BasiliskPackagesDataset`, a
  new `ExternalRefreshDataset` subclass (co-located with
  `BasiliskBatchDataset`/`BasiliskDetailDataset` for cohesion, but built on the
  `refresh.py` base those two do NOT use — `/v1/packages` is a single bulk GET,
  not the ≤1,000-query-chunked batch shape those two own). Mirrors
  `VDBStoreDataset`/`TrendingSnapshotDataset`'s single-refresher shape: one
  injected `fetcher: Callable[[], Any]` calling `GET {BASILISK_BASE_URL}/v1/packages`,
  a pure `parse_basilisk_packages_response(payload) -> pd.DataFrame` parser
  (never raises — malformed/empty payload degrades to an empty frame),
  `_write`/`load()` as Parquet under `filepath`. Resolves through the EXISTING
  `BASILISK_BASE_URL` override point — no new global needed.
- `src/pyforge/atlas/datasets/upstream_discovery.py` — add 3 new classes,
  co-located with `TrendingSnapshotDataset`:
  - `AnacondaDist2026Dataset(ExternalRefreshDataset)` — mirrors
    `TrendingSnapshotDataset._do_refresh`'s "try the live source; if it yields
    zero rows, fall back" shape exactly, but the fallback is a LOCAL read of
    the git-tracked `conf/base/seeds/discovery_anaconda_dist_2026x_seed.json`
    file (not a second HTTP call like the Search API fallback). A pure
    `parse_anaconda_dist_html(html) -> list[dict]` extractor (bs4 +
    `html.parser`, already an accepted dependency via `upstream_discovery.py`'s
    existing import — no new dependency) that never raises on a layout break.
  - `AossPremiumPythonDataset(ExternalRefreshDataset)` — single live-doc fetch
    + pure parser (`parse_aoss_premium_doc(payload) -> list[dict]`, exact
    shape is a step-03 research item, see Design Notes); on failure, the
    INHERITED `ExternalRefreshDataset.save()` keep-last-good + mark-stale
    behavior applies unchanged (no new fallback tier — see Design Notes for
    why this story does NOT add a literal Wayback Machine integration).
  - `TrackedSeedDataset(AbstractDataset)` — a small, generic (~20-line) git-tracked-JSON-array reader, read-only (`save()` raises `NotImplementedError`,
    matching every other read-only dataset in this package), `load()` returns
    a `pypi_name`/`source="tracked_seed"` frame; a missing/corrupt file (should
    never happen in a real clone) degrades to an empty frame + a WARN log
    rather than raising. Backs `discovery_aoss_free_python_raw` directly — no
    refresh-trigger node needed (see Design Notes: a pure tracked-seed entry
    has no `save()`-gated emptiness risk, unlike the 3 external-refresh
    entries above).
- `src/pyforge/atlas/datasets/__init__.py` — import + `__all__` entries for
  `BasiliskPackagesDataset`, `AnacondaDist2026Dataset`, `AossPremiumPythonDataset`,
  `TrackedSeedDataset` (mirrors the existing import/`__all__` pattern for every
  other dataset class).
- `src/pyforge/atlas/pipelines/core/nodes.py` + `pipeline.py` — add
  `enumerate_anaconda_main_packages(core_anaconda_main_channeldata_raw: pd.DataFrame) -> pd.DataFrame`,
  a thin materializer (near-identity — `core_anaconda_main_channeldata_raw`
  already arrives in the exact `conda_name`/`subdirs` shape via the reused
  `channeldata_json_to_rows`; this node validates non-empty and passes
  through, mirroring `attribute_feedstocks`'s minimal-transform style) wired
  `inputs="core_anaconda_main_channeldata_raw"`, `outputs="core_anaconda_main_packages"`
  — WITHOUT this node, the live-mode `core_anaconda_main_channeldata_raw`
  entry is never touched by any `kedro run` (mirrors why `core_channeldata_raw`
  is always consumed by `enumerate_conda_packages`/`detect_latest_status`,
  never left as a bare unconsumed raw entry).
- `src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` + `pipeline.py` —
  add 3 pure refresh-trigger nodes mirroring `refresh_trending_candidates`
  exactly (`params:ttls -> RefreshRequest`, single writer of the named catalog
  entry): `refresh_anaconda_dist_2026x` (outputs
  `discovery_anaconda_dist_2026x_raw`), `refresh_basilisk_packages` (outputs
  `discovery_basilisk_packages_raw`), `refresh_aoss_premium_python` (outputs
  `discovery_aoss_premium_python_raw`). `discovery_aoss_free_python_raw`
  (the `TrackedSeedDataset`-backed entry) gets NO trigger node — see Design
  Notes.
- `conf/base/globals.yml` — add `ANACONDA_DIST_BASE_URL` and
  `AOSS_PREMIUM_BASE_URL` to `endpoint_bases` (both `${env_or:...}` wrapped,
  matching every existing key); update the header's "20 override points"
  accounting comment to reflect the new total (22) — see Design Notes for why
  these do not reuse `extra_overrides` (no legacy `resolve_*_urls` precedent
  either way — they are genuinely new v1 discovery work, so they follow the
  header's own forward-looking "new sources add exactly one override point"
  convention, the same path `BASILISK_BASE_URL` took at Story B8).
- `conf/base/parameters.yml` — add 3 new `ttls:` entries (weekly cadence,
  604800s, matching the sibling `vcs_registry_versions`/`vcs_upstream_versions`
  weekly default for slow-moving package-catalog sources — no legacy
  equivalent to cite, documented as such):
  `discovery_anaconda_dist_2026x`, `discovery_basilisk_packages`,
  `discovery_aoss_premium_python`. `discovery_aoss_free_python` gets NO ttl
  (tracked seed — config, not a live fetch, mirrors `org_audit_candidates`
  having no `ttls:` entry either).
- `conf/base/catalog.yml` — 6 new entries (raw layer for the 5 fetch-backed
  sources + 1 new intermediate `core_anaconda_main_packages`); see the exact
  shapes below. Each new entry gets a one-line `# fetch mode: <mode>` comment
  immediately above it (catalog-sources.md's own top-of-doc requirement,
  "Every new entry documents fetch mode") — the assignment is fixed by this
  spec, not a dev-time choice:

  | Catalog entry | Fetch mode |
  |---|---|
  | `core_anaconda_main_channeldata_raw` | live |
  | `core_anaconda_main_packages` | derived (materializes the live fetch — not itself a fetch-mode entry, no comment needed) |
  | `discovery_anaconda_dist_2026x_raw` | external-refresh (HTML scrape primary; tracked-seed fallback on a scrape layout break; local last-good Parquet fallback thereafter) |
  | `discovery_basilisk_packages_raw` | external-refresh |
  | `discovery_aoss_free_python_raw` | tracked seed |
  | `discovery_aoss_premium_python_raw` | external-refresh (live doc; keep-last-good on failure — see Design Notes' "Wayback" reading) |
  | `pypi_cross_channel_repodata_raw` (extended, not new) | live (unchanged mode — SelfExplainML rides the existing entry) |

  Update the header's stale domain-prefix list comment (~L8-11, currently
  omits `upstream_discovery`/`artifactory_downloads`/`query_plane_cache`/
  `semantic_packages` entirely — a pre-existing hygiene gap, not introduced by
  this story, but touch it while here) to add `discovery`.
- `conf/base/seeds/discovery_aoss_free_python_seed.json` (NEW, git-tracked) —
  a JSON array of AOSS free-tier Python package identifiers; content is a
  step-03 data-acquisition task (Design Notes).
- `conf/base/seeds/discovery_anaconda_dist_2026x_seed.json` (NEW, git-tracked)
  — Anaconda Distribution 2026.x's known package list, used ONLY as
  `AnacondaDist2026Dataset`'s scrape-failure fallback; same data-acquisition
  caveat.
- `tests/catalog/conftest.py` — `PREFIX_TO_PIPELINE` (+`"discovery": "upstream_discovery"`);
  `EXPECTED_PIPELINE_COUNTS["core"]` 16→18, `["upstream_discovery"]` 4→8;
  `EXPECTED_TOTAL` 95→101; `EXPECTED_LIVE_OVERRIDE_POINTS` +2
  (`ANACONDA_DIST_BASE_URL`, `AOSS_PREMIUM_BASE_URL`);
  `EXPECTED_ENV_OVERRIDE_SURFACE` 31→33.
- `tests/catalog/test_override_points.py` — the hardcoded
  `assert len(bases) == 20` (~L45) → `22`; its "19 + 1" comment updated to
  describe the new 19+1+2 structure.
- `tests/catalog/test_scale_floors.py` (NEW) — offline, fixture-injected
  floor assertions for the 3 Tier 1 floors this story owns: Basilisk packages
  non-zero when a fixture fetcher returns data (qualitative), AOSS free
  ≥1,000 rows (against the real committed seed file — `TrackedSeedDataset`
  needs no injected fetcher, so this can assert against the actual file, not
  just a synthetic fixture), Anaconda main ≥5,000 rows (fixture-injected
  channeldata payload). Sub-threshold fails the assertion, never a log-only
  warning.
- `tests/parity/fixtures/pypi_intelligence/flag_cross_channel.json` — add
  `in_selfexplainml: false` to the existing expected output rows (the fixture
  has no selfexplainml input rows, so every existing row's new column is
  `false`); verify via `parity-diff`.
- `tests/datasets/test_core_sources.py` — add `CrossChannelRepodataDataset`
  coverage: selfexplainml resolves via the new spec tuple; a channel whose
  first subdir fails but second succeeds returns data (the hardening's actual
  regression test).
- `tests/datasets/test_basilisk.py` — add `BasiliskPackagesDataset` coverage
  (fetch success, fetch failure keeps last-good + marks stale, first-run no
  last-good, malformed payload parser never raises).
- `tests/datasets/test_upstream_discovery.py` — add coverage for
  `AnacondaDist2026Dataset` (scrape success; scrape-empty falls back to the
  tracked seed; both fail → keep last-good + mark stale),
  `AossPremiumPythonDataset` (fetch success/failure, first-run-no-last-good),
  `TrackedSeedDataset` (loads the real committed seed file; missing/corrupt
  file degrades to empty + WARN, never raises).
- `tests/pipelines/core/` + `tests/pipelines/upstream_discovery/` (node test
  modules, whichever already exist per that pipeline's test layout) — add
  node-level tests for `enumerate_anaconda_main_packages` and the 3 new
  refresh-trigger nodes (mirrors `refresh_trending_candidates`'s own test
  coverage style — `_coerce_cadence` fallback, `RefreshRequest` shape).
- `tests/pipelines/test_dag_resolves.py` — node-count assertions updated for
  the 4 new pipeline nodes (1 in `core`, 3 in `upstream_discovery`).

## Tasks & Acceptance

**Execution:**
- [ ] `core_sources.py` — extend + harden `_CROSS_CHANNEL_SPECS` (add
  selfexplainml `("noarch", "linux-64")`; broaden the 4 existing channels'
  subdir fallback lists).
- [ ] `pypi_intelligence/nodes.py` — extend `_CROSS_CHANNELS` with
  `"selfexplainml"`.
- [ ] `basilisk.py` — add `BasiliskPackagesDataset` + its pure parser,
  resolving through the existing `BASILISK_BASE_URL`.
- [ ] `upstream_discovery.py` — add `AnacondaDist2026Dataset`,
  `AossPremiumPythonDataset`, `TrackedSeedDataset` + their pure parsers.
- [ ] `datasets/__init__.py` — export the 4 new classes.
- [ ] `core/nodes.py` + `pipeline.py` — add `enumerate_anaconda_main_packages`
  wired to the new `core_anaconda_main_channeldata_raw` → `core_anaconda_main_packages`
  pair.
- [ ] `upstream_discovery/nodes.py` + `pipeline.py` — add the 3 refresh-trigger
  nodes (Anaconda Dist, Basilisk packages, AOSS premium), each `params:ttls ->
  RefreshRequest`, single writer of its named entry.
- [ ] `globals.yml` — add `ANACONDA_DIST_BASE_URL` + `AOSS_PREMIUM_BASE_URL`
  to `endpoint_bases`; research + commit each real default URL against its
  live public source (step-03 — do NOT fabricate; see Design Notes).
- [ ] `parameters.yml` — add the 3 new `ttls:` entries (weekly, documented).
- [ ] `catalog.yml` — add the 6 new entries (exact shapes in Code Map), each
  with its `# fetch mode: <mode>` comment per the Code Map table; lightly fix
  the stale header prefix-list comment while here.
- [ ] `conf/base/seeds/discovery_aoss_free_python_seed.json` — source the real
  AOSS free-tier Python package list from Google's published AOSS docs
  (step-03 research/data-acquisition — do NOT fabricate a package list).
- [ ] `conf/base/seeds/discovery_anaconda_dist_2026x_seed.json` — source the
  real Anaconda Distribution 2026.x package list (same caveat).
- [ ] `tests/catalog/conftest.py` — `PREFIX_TO_PIPELINE`, `EXPECTED_PIPELINE_COUNTS`,
  `EXPECTED_TOTAL`, `EXPECTED_LIVE_OVERRIDE_POINTS`, `EXPECTED_ENV_OVERRIDE_SURFACE`
  updates (exact deltas in Code Map).
- [ ] `tests/catalog/test_override_points.py` — bump the hardcoded `== 20`
  assertion + its comment.
- [ ] `tests/catalog/test_scale_floors.py` (new) — the 3 offline, fixture-driven
  floor assertions.
- [ ] `tests/parity/fixtures/pypi_intelligence/flag_cross_channel.json` — add
  `in_selfexplainml: false` to existing rows.
- [ ] `tests/datasets/test_core_sources.py`, `test_basilisk.py`,
  `test_upstream_discovery.py` — new-class + hardening regression coverage
  (per Code Map).
- [ ] Node-level tests for `enumerate_anaconda_main_packages` + the 3 new
  trigger nodes; `test_dag_resolves.py` node-count updates.
- [ ] Verification housekeeping: `grep -rn "discovery_\|core_anaconda_main"`
  across `src/shared/packages/pyforge-atlas/` to confirm every new name is
  referenced consistently (dataset class, catalog entry, node wiring, test);
  check `conf/local/` for any catalog override that might shadow the 6 new
  entries.
- [ ] Run `pixi run -e pyforge-atlas kedro-catalog-check`, `parity-diff`, and
  `kedro-test` — confirm all green (see Verification).

**Acceptance Criteria:**
- Given the updated `catalog.yml`, when `pixi run -e pyforge-atlas kedro-catalog-check`
  runs, then it passes with all 6 new entries (+1 materializing intermediate)
  resolving offline, the 2 new override points present in every pinned
  set/count, and `EXPECTED_TOTAL`/`EXPECTED_PIPELINE_COUNTS` matching the
  actual catalog.
- Given an empty data root and no live network, when
  `kedro run --pipelines core,upstream_discovery,pypi_intelligence` runs, then
  it completes with the 3 new external-refresh entries marked stale (no
  fetcher wired offline) rather than failing, `core_anaconda_main_packages`
  materializes from the (offline-degraded, empty-but-correctly-shaped)
  channeldata frame, and `discovery_aoss_free_python_raw` loads the real
  committed seed file with zero network.
- Given the new scale-floor test with a fixture AOSS-free-seed-equivalent
  payload below 1,000 rows (or Anaconda main channeldata below 5,000 rows),
  when the test runs, then it FAILS (not a warning).
- Given `pixi run -e pyforge-atlas parity-diff`, when run after this story,
  then it stays green including the updated `flag_cross_channel` fixture.
- Given the real committed `conf/base/seeds/discovery_aoss_free_python_seed.json`,
  when `TrackedSeedDataset.load()` reads it, then the resulting frame has
  ≥1,000 rows (the story is not done until this floor is met with REAL
  sourced data, not a placeholder).

## Design Notes

**Why Anaconda Dist resolves to `upstream_discovery`, not `core` (resolving
the SPEC.md vs. catalog-sources.md ambiguity):** catalog-sources.md's own
Tier 1 table lists Anaconda Dist's pipeline as "core or upstream_discovery" —
genuinely undecided in that doc. `tests/catalog/test_conventions.py::test_names_are_snake_case_with_declared_domain_prefix`
and `test_catalog_resolution.py::test_per_pipeline_counts_are_pinned` both
attribute a catalog entry to a pipeline PURELY by its declared name prefix
(`PREFIX_TO_PIPELINE`, longest-prefix match) — not by which `pipeline.py` file
actually wires its node. Since catalog-sources.md's own proposed name is
`discovery_anaconda_dist_2026x_raw` (not `core_anaconda_dist_...`), the
machine-enforced naming gate settles the ambiguity: `upstream_discovery`.
SPEC.md's Constraints section ("Anaconda main/dist → core / pypi_intelligence")
is read as applying cleanly to Anaconda MAIN (which does get a `core_`-prefixed
name) while Anaconda DIST's own catalog-sources.md name overrides SPEC.md's
looser prose for this one entry.

**Why AOSS free needs no refresh-trigger node but the other 3 do:** the 3
`ExternalRefreshDataset` subclasses (Anaconda Dist, Basilisk packages, AOSS
premium) have a `load()` that is a READ-ONLY projection of a persisted store —
that store is EMPTY forever unless some pipeline node's `outputs=` binding
calls `save()` (this is the exact defect Story 21.2's pass-1 shipped for 10 of
12 entries: correct fetch code, but no pipeline node ever triggered it).
`TrackedSeedDataset` has no such gate: its `load()` always reads the
git-tracked file directly, with no `save()`/populate step to be dormant
relative to. A pipeline node consuming it is useful future work (Story
21.6/21.7), but is not required for THIS story's done_checkpoint ("raw
datasets in catalog.yml; kedro-catalog-check green; smoke floors pass" —
none of which require DAG wiring).

**Why "Wayback last-good" is read as ordinary AD-13 keep-last-good, not a
literal Internet Archive integration:** a repo-wide search for `wayback` /
`web.archive.org` across `pyforge-atlas` returns zero hits — no dataset in
this codebase has ever integrated with the Internet Archive. The 5-value
fetch-mode vocabulary catalog-sources.md itself defines ("live | upstream
Parquet | external-refresh | tracked seed | credentialed opt-in") has no
"Wayback" mode either — "Wayback last-good" is prose in the Notes column, not
a fetch-mode declaration. Given Simplicity First and the absence of any
existing precedent to build on, this spec adopts the reading that "Wayback"
is a colloquial gloss for "go back to the last known good" — i.e., the
SAME `ExternalRefreshDataset.save()` keep-last-good-Parquet-and-mark-stale
behavior every other subclass already gets for free. **If the actual intent
was a literal `web.archive.org` fallback fetch** (querying the Wayback Machine's
API for the last-crawled snapshot of the AOSS premium doc URL when BOTH the
live fetch AND the local last-good Parquet are unavailable), that is a
scope addition warranting its own follow-up story — flag at review time if
this reading is wrong; do not silently build it into this story.

**Step-03 research items (NOT open spec questions — the shape below is
fixed; only the concrete values are runtime research, mirroring spec-21-2's
identical precedent for its 10 registry endpoints):**
1. `ANACONDA_DIST_BASE_URL`'s real default value — the exact
   anaconda.com/Anaconda-Distribution page or API this story's "HTML
   extractor" targets for the 2026.x release's package list.
2. `AOSS_PREMIUM_BASE_URL`'s real default value + `parse_aoss_premium_doc`'s
   exact expected payload shape (HTML page vs. a published Google
   Sheet/Doc export vs. a JSON feed) — Google's Assured Open Source
   Software premium-tier Python catalog's actual public surface.
3. `conf/base/seeds/discovery_aoss_free_python_seed.json`'s real content —
   the actual AOSS free-tier Python package identifiers, sourced from
   Google's published AOSS documentation (NOT invented; this is a
   data-acquisition task, not a coding decision — mirrors how
   `org_audit_candidates`'s hand-curated list was sourced from a real
   published document, `org-audit-precedent.md`).
4. `conf/base/seeds/discovery_anaconda_dist_2026x_seed.json`'s real content
   — the actual Anaconda Distribution 2026.x package list (same caveat).

None of these four block writing the dataset classes, the pipeline wiring,
the catalog entries, or the test scaffolding — they block only the FINAL
"real data floor met" acceptance criterion (AOSS free ≥1,000 rows against
the real committed seed) and the two live URLs actually working end-to-end
against a real network. A reviewer should treat a `TODO`-marked placeholder
URL/seed as expected mid-implementation state, not a defect, but the story
is not `done` until items 1-4 are resolved with real sourced values (matching
this repo's "loosen pins for unavailable packages + TODO" convention applied
here to research items instead of pins).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass, all 6 new
  entries + `core_anaconda_main_packages` resolve offline; `EXPECTED_TOTAL`/
  `EXPECTED_PIPELINE_COUNTS`/override-point sets all match.
- `pixi run -e pyforge-atlas kedro-test` (i.e. `pytest tests -q`) — expected:
  full suite green, including the new `test_scale_floors.py` and the extended
  dataset/node test modules.
- `pixi run -e pyforge-atlas parity-diff` — expected: stays green, including
  the updated `flag_cross_channel` fixture.
- `kedro run --pipelines core,pypi_intelligence,upstream_discovery` (offline,
  no `CF_ATLAS_DB`, no live network) — expected: exit 0; the 3 new
  external-refresh entries mark stale (no fetcher wired offline);
  `core_anaconda_main_packages` and `discovery_aoss_free_python_raw` both
  materialize with real (non-network) data.
- Manual: `git diff --stat` shows the 2 new tracked seed files under
  `conf/base/seeds/` (never under `data/`), confirming they survive a fresh
  clone.
