---
title: "34.6: The public discovery stores refresh themselves"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: 'e0e1d9f8f1'
flag:
  key: pyforge.atlas.live_public_sources          # shared with Stories 34.4 (registered it) and 34.5
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # unchanged from 34.4
  scope: global                                   # v1 is global only
  fallback: 'a store with no injected fetcher keeps today''s behaviour: a due refresh marks it stale, "refresh due but no refresher wired"'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
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
deferred: []
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
   returning the response text. A body with no text is a `DatasetError`.
2. Each of the five stores, constructed with no `fetcher` while `public_sources.live()` is on, uses
   `public_sources.fetch_text`. Off: today's behaviour. An injected fetcher still wins. The credentialed identity
   sources (`OpenTeamsBoardDataset`, `StagedRecipesPRDataset`) are untouched: they are CAP-67's, Story 36.2.
3. `parse_about_readme` accepts both header shapes and an optional backtick around the slug.
4. `tools/bootstrap.py`'s fetcher-less list keeps only Basilisk (credentialed, Story 36.1); the AOSS premium and
   Anaconda distribution stores now fetch their own pages.

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
  Both states are tested with `flag_states`. `fetch_text` composes `APIDataset` with a timeout and no credentials,
  and a body with no text raises `DatasetError`.
- **AC2 — The about README.** Both the 2026-07-11 and the 2026-10-18 shapes parse into slug and role rows.
- **AC3 — Live:** see Verification.
- **AC4 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and
  mypy in `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit: `tests/unit/datasets/test_upstream_discovery.py`, `tests/unit/datasets/test_identity_sources.py`,
  `tests/unit/datasets/test_public_sources.py`.
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
  Epic names.

## Boundaries & Constraints

**Never:** a credential on these hosts; a credentialed identity source wired here; an HTTP client import in the
package; a test that touches the network.

**Residual risk:**
- GitHub's trending page and search API are unauthenticated; the search API allows 10 requests a minute per IP.
  The store reads it once per refresh, as a fallback.
- `enterprise_conda_maintainers` holds 871 of the README's 872 slugs: `conda-forge/lance-namespace-urllib3-client-feedstock`
  is not in the scratch root's `core_feedstock_attribution`.

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
