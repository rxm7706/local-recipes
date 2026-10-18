---
title: "34.6: The public discovery stores refresh themselves"
type: 'feature'
created: '2026-10-18'
status: 'done'
baseline_revision: '5908e99603'
flag:
  key: pyforge.atlas.live_public_sources          # shared with Stories 34.4 (registered it) and 34.5
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # unchanged from 34.4
  scope: global                                   # v1 is global only
  fallback: 'a store with no injected fetcher keeps today''s behaviour: a due refresh marks it stale, "refresh due but no refresher wired"'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-4-the-download-tables-fill-from-anaconda-s-monthly-parquet.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/public_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/upstream_discovery.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/identity_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/nodes.py
deferred: ['DW-atlas-34-6-1', 'DW-atlas-34-6-2']
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** GitHub trending, the about-maintainers list, the purl associator, the Anaconda distribution 2026.x list
and the AOSS premium list were empty after the unattended refresh of 2026-10-17 (R4). So were
`trending_candidates_classified`, `enterprise_conda_maintainers` and `identity_packages_primary`.

- All five stores (`TrendingSnapshotDataset`, `AboutMaintainersDataset`, `AnacondaDist2026Dataset`,
  `AossPremiumPythonDataset`, `PurlAssociatorMappingsDataset`) take a per-URL `fetcher(url) -> text`, and the catalog
  wires none. Every due refresh marked them stale: "refresh due but no refresher wired".
- All five URLs answer 200, probed 2026-10-18:
  - GitHub's trending pages and search API, unauthenticated
  - `raw.githubusercontent.com/rxm7706/about/main/README.md`
  - `prefix-dev.github.io/purl-associator/mappings-index.json` (27.7 MB)
  - anaconda.com's 2026.x release page
  - `docs.cloud.google.com`'s AOSS premium page
- **Found by the live run: the about README changed shape.** It now heads its lists `### Sole maintainer (606)` and
  `### Co-maintainer (266)` and backticks each slug (`` 1. `conda-forge/a2a-sdk-feedstock` ``). The parser knew only
  the 2026-07-11 headers (`List Of FeedStocks - As Maintainer`), so it read 0 rows, and the store marked stale
  ("refresh returned no data").
- No other code reads that README, legacy included.

**Approach:**
1. `public_sources.fetch_text(url, timeout=300)`: one unauthenticated GET over a composed `APIDataset` (AD-2),
   through `public_sources.request_args`, a timeout and a no-op auth, so requests never reads `~/.netrc`. It decodes
   by the declared charset, else UTF-8. A non-bytes body is a `DatasetError`.
2. Each of the five stores built with no `fetcher` implements Story 34.5's `_live_refresher()` hook. At each refresh,
   never at construction (a Dagster code location constructs at import), it asks `public_sources.live()`; on, it
   refreshes through `public_sources.fetch_text`. The refresh body takes the fetch callable as an argument
   (`_refresh_with`). Off: today's behaviour. An injected fetcher still wins. The credentialed identity
   sources (`OpenTeamsBoardDataset`, `StagedRecipesPRDataset`) are untouched: they are CAP-67's, Story 36.2.
3. `parse_about_readme` accepts both header shapes and an optional backtick around the slug.
4. `tools/bootstrap.py` lists the fetcher-less stores by the flag: Basilisk's package listing always, and the AOSS
   premium and Anaconda distribution stores while live public sources are off. The README says the same. The
   `pyforge-atlas-bootstrap` task description in `pixi.toml` still names all three: fifteen Specs govern
   `pixi.toml`, and a description-only edit would move all fifteen memlogs. It is ledgered as
   `DW-atlas-34-6-1` for the next `pixi.toml` change.

Ledger key: `34-6-the-public-discovery-stores-refresh-themselves`.
Type / Effort / Deps: feature / M / Story 34.4 (the flag and `public_sources`).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md`, R4): a feature behind `pyforge.atlas.live_public_sources`.
- **AD-2**, **AD-6** (amended 2026-10-18), **AD-13**, **AD-11** (every test's responses are in memory; the suite
  pins the flag off).
- **Origin.** Dream entry 2026-10-18 (atlas fills its own data), R4.

## Acceptance Criteria

- **AC1 — The refreshers.** Flag on with no injected fetcher, each of the five stores requests its own URL(s)
  through `public_sources.fetch_text` with no credential and holds rows. Flag off: nothing requested, today's marker.
  Both states are tested with `flag_states`. `fetch_text` composes `APIDataset` with a timeout and a no-op auth (no
  `~/.netrc` credential), decodes by the declared charset (UTF-8 when none is declared or the declared one is
  unknown), and a body that is not bytes raises `DatasetError`.
- **AC2 — The about README.** Both the 2026-07-11 and the 2026-10-18 shapes parse into slug and role rows.
- **AC3 — Live:** see Verification.
- **AC4 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and
  mypy in `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, each named from the repo root:
  - `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_upstream_discovery.py`
  - `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_identity_sources.py`
  - `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_public_sources.py`
- Live (AC3), recorded 2026-10-18: fresh scratch data root, flag on (dev), `--pipelines upstream_discovery --nodes
  refresh_trending_candidates,classify_trending_candidates,refresh_anaconda_dist_2026x,refresh_aoss_premium_python,
  refresh_about_maintainers,join_enterprise_conda_maintainers,refresh_purl_associator_mappings,
  build_identity_packages_primary,build_identity_export_parquet`. Exit 0, 16 s, peak RSS 662 MB, no marker on any
  store. Before, every store and downstream table read 0.

  | Dataset | Rows after |
  |---|---|
  | `trending_candidates` | 46 |
  | `trending_candidates_classified` | 46 |
  | `discovery_anaconda_dist_2026x_raw` | 639 |
  | `discovery_aoss_premium_python_raw` | 2,154 |
  | `discovery_about_maintainers_raw` | 872 (606 sole, 266 co; the README's own counts) |
  | `enterprise_conda_maintainers` | 871 |
  | `purl_associator_mappings_raw` | 34,666 |
  | `identity_packages_primary` / `identity_export_parquet` | 871 each |

  The identity join's universe is the maintainer list here, because `enterprise_jfrog_names` (Artifactory), the
  OpenTeams board and the staged-recipes PRs are credentialed (Epic 35 and Story 36.2). This is the public half the
  Epic names. Of the 871 identity rows, 868 come from the purl associator.

  Re-run after review round 1 on a copy of the 2026-10-17 data root, with Story 34.2's refreshed
  `pypi_conda_mapping` (10,968 rows) and `pypi_intelligence_enriched` copied in. It gave the same counts in 19 s,
  peak RSS 661 MB. `trending_candidates_classified`'s 46 rows are all `tier=skip`:
  - 17 have no PyPI artifact (`no-pypi-artifact`).
  - 29 are `unclassified-needs-human`. Their PyPI names (`comfyui`, `tradingagents`, ...) are not in the 200-name
    enrichment slice (`pypi_intelligence_enriched`), so the classifier has no signal to tier them. That is the
    classifier's own contract, not a fetch gap. Story 34.10's wider Phase H coverage does not change it, because the
    tiers read Phase R enrichment.

## Boundaries & Constraints

**Never:** a credential on these hosts; a credentialed identity source wired here; an HTTP client import in the
package; a test that touches the network.

**Residual risk:**
- GitHub's trending page and search API are unauthenticated; the search API allows 10 requests a minute per IP.
  The store reads it once per refresh, as a fallback.
- `enterprise_conda_maintainers` holds 871 of the README's 872 slugs. `conda-forge/lance-namespace-urllib3-client-feedstock`
  joins nothing: its package is attributed to the `lance-namespace` feedstock in `core_feedstock_attribution`, and
  legacy agrees. This is a join-key limit, not missing data.
- **netrc on a redirect:** a redirect to another host still consults `~/.netrc` for that host (requests'
  `rebuild_auth`). None of the five URLs redirects today.
- **A truncated README** writes fewer rows with no marker; the parser does not cross-check the declared "(606)" and
  "(266)" counts.
- **The Basilisk package listing** (`discovery_basilisk_packages_raw`, `GET /v1/packages`) answers unauthenticated,
  but stays fetcher-less until the operator rules on Basilisk (the Spec's open question on CAP-66). Story 36.1 covers
  only the `vulnerability_basilisk_*` datasets, so the ruling also decides which story owns this store
  (`DW-atlas-34-6-2`).

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Live run, flag on | five stores stale, downstream empty | each holds rows; the three downstream tables fill |
| Flag off | "no refresher wired" | unchanged |
| A page unreachable | — | last-good kept, marker |
| About README in its 2026-10-18 shape | 0 rows, "refresh returned no data" | 872 rows |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data), R4.
- Epic 34 / Story 34.6 in `planning-artifacts/epics.md`.
- Flag: `pyforge.atlas.live_public_sources` (`feature-flag-governance:CAP-1`), registered by Story 34.4.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-6-discovery-refreshers`, cut from 34.5's branch).
  The README's shape change was found by the first live run.
- 2026-10-18: independent review FAIL (no blocker, 5 should-fix, 8 nits). Resolved:
  - **S1:** `fetch_text` sent a `~/.netrc` credential when one existed for the host; it now passes
    `public_sources.request_args` (34.4).
  - **S2:** the bootstrap list follows the flag, and the Basilisk comment and the README are corrected. The task
    description in `pixi.toml` is ledgered (`DW-atlas-34-6-1`): fifteen Specs govern that file.
  - **S3:** the injected fetcher winning is tested for every store.
  - **S4:** the README decoy is well formed, and a trailing-text case pins the line anchor.
  - **S5:** Verification records the classifier tiers and the copied inputs.
  - **Nits:** charset (UTF-8 unless declared); the flag is read at the refresh (34.5's blocker, applied here too);
    the missing slug's wording; residual risks. `fetch_shard` is no longer live, because it uses only an injected
    fetcher.
- 2026-10-18: re-review round 2 PASS. All 34 hand mutants were killed, and every gate exits 0. Its nits:
  - An unknown declared charset now reads as UTF-8 instead of raising `LookupError`.
  - AC1's wording is fixed.
  - The rest are recorded as accepted:
    - a Latin-1 page with no declared charset decodes with replacements;
    - the injected-fetcher test sets the attributes directly;
    - `_describe()` reports `refresher_wired` False for a live store (34.5's base);
    - the bootstrap function has no test (`tools/` is not coverage-gated);
    - an earlier memlog entry names `docs/map.yaml`, whose edit was reverted.
  Promoted to `done`.
