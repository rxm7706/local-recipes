---
title: "34.5: The five OS-distro indexes refresh themselves"
type: 'feature'
created: '2026-10-18'
status: 'done'
baseline_revision: '8c04b291e5'
flag:
  key: pyforge.atlas.live_public_sources          # shared with Story 34.4, which registered it
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
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/tier3_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/public_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py
deferred: ['DW-atlas-34-5-1']
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the Homebrew, nixpkgs, Spack, Debian and Fedora stores, and with them `pypi_tier3_channel_flags`, were
empty after the unattended refresh of 2026-10-17 (R4).

- `_Tier3PackagesDatasetBase` is constructed with no `fetcher` in the catalog, so every due refresh marked the store
  stale: "refresh due but no refresher wired".
- **Three of the five catalog URLs are dead** (probed 2026-10-18):
  - `channels.nixos.org/nixpkgs-unstable/packages.json` is 404. The index is `packages.json.br`: it redirects (302) to
    `releases.nixos.org` and is served with `Content-Encoding: br`. It is 10.3 MB compressed and 403 MB of JSON
    decoded: `{"version": 2, "packages": {attr: {"pname", ...}}}`.
  - `raw.githubusercontent.com/spack/spack/develop/var/spack/repos/builtin/package_index.json` is 404, because the
    builtin repo left `spack/spack`. Spack's own index is `packages.spack.io/data/packages.json` (2.1 MB,
    `[{"name", "description"}, ...]`).
  - `src.fedoraproject.org/rest/projects/` is 404. `src.fedoraproject.org/extras/pagure_owner_alias.json` (3.0 MB)
    maps every namespace to its packages; `rpms` is the package list.
  - The other two work: Homebrew's `formula.json` (32 MB) and Debian sid's `Packages.gz` (15 MB).
- **The parsers did not fit the live shapes.** nixpkgs reported the attribute keys of a flat object, but the live
  index nests them under `packages`, where the key (`python313Packages.numpy`) is not the package's name (`numpy`).
  Spack turned each `{"name": ...}` record into its `str()`, and Fedora read no `rpms` map.
- **Legacy reference:** legacy Phase Q lists these five ecosystems as stretch goals and implements none. The
  `pypi_intelligence.in_homebrew` … `in_fedora` columns are NULL on all 918,223 rows of `cf_atlas.db`. So there is no parity
  oracle; the measure is that each store holds the index it names.
- The Epic's Given says `tools/bootstrap.py` lists these five as expected stale. It does not: its
  `_FETCHER_LESS_DISCOVERY_STORES` names Basilisk, AOSS premium and Anaconda distribution, which are Story 34.6's.
  Nothing there changes here.

**Approach:**
1. With no injected `fetcher`, a store asks `public_sources.live()` (Story 34.4's one reader of
   `pyforge.atlas.live_public_sources`) at the moment of each refresh, through a new `ExternalRefreshDataset` hook,
   `_live_refresher()`, which `save()` calls when no refresher is injected. It is never asked at construction,
   which a Dagster code location runs at import. On, the store fetches its URL through a composed `APIDataset` with
   `public_sources.request_args(request_timeout_seconds)`: a 300 s request timeout and a no-op auth, so requests
   never reads `~/.netrc`. `timeout_seconds` stays the whole-asset budget the orchestrator reads. A non-bytes body is
   a fetch failure. Off, the store keeps today's behaviour. An injected fetcher still wins.
2. The refresh writes one row per name: Debian's `Packages` repeats a name across stanzas.
3. Parsers:
   - **nixpkgs:** reports each package's `pname`, once, whether the payload is bytes (a byte-level scan; 403 MB is
     never `json.loads`ed) or the decoded object. When the scan finds nothing, a still-compressed brotli body is
     decoded through a lazily imported `brotli`, whatever its first byte. An attr-keyed object falls back to its keys.
     If the body is brotli and no `brotli` module is installed, the store's marker says so.
   - **Spack:** reads `{"name"}` records.
   - **Fedora:** reads the `rpms` map.
4. The catalog points at the three working indexes. The Spack override point `SPACK_RAW_BASE_URL` is renamed
   `SPACK_PACKAGES_BASE_URL` (default `https://packages.spack.io`), so the count of override points is unchanged.

Ledger key: `34-5-the-five-os-distro-indexes-refresh-themselves`.
Type / Effort / Deps: feature / M / Story 34.4 (the flag and `public_sources`).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md`, R4): a feature behind `pyforge.atlas.live_public_sources`.
- **AD-2** (dataset-owned IO over a composed `APIDataset`), **AD-6** (amended 2026-10-18: the store owns its public
  refresher), **AD-13**, **AD-11** (every test's responses are built in memory; the suite pins the flag off).
- **Origin.** Dream entry 2026-10-18 (atlas fills its own data), R4.

## Acceptance Criteria

- **AC1 — Parsers.** The live shapes parse: nixpkgs `pname`s once each, escapes decoded, from a decoded or
  still-brotli body; Spack `{"name"}` records; Fedora's `rpms` map. A garbage body returns `[]`.
- **AC2 — The refresher.** Flag on with no injected fetcher, each store requests its URL with its request timeout
  and no credential, and holds the parsed names, one row per name. A non-bytes body keeps last-good under the
  marker, and an injected fetcher wins. Flag off: nothing requested, today's "no refresher wired" marker. Both states
  are tested with `flag_states`, and the flag is read at the refresh: a store built while the flag was on does not
  fetch once it is off, and the converse.
- **AC3 — Live:** see Verification.
- **AC4 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and
  mypy in `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, each named from the repo root:
  - `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_tier3_sources.py`
  - `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_override_points.py`
- Live (AC3), recorded 2026-10-18: fresh scratch data root, flag on (dev), `--pipelines pypi_intelligence --nodes
  refresh_discovery_{homebrew,nixpkgs,spack,debian,fedora}_store,flag_tier3_channels`. Exit 0, 23 s, peak RSS
  1.07 GB, no marker on any store.
  - **Before:** every store empty; `pypi_tier3_channel_flags` 0 rows.
  - **After, distinct names per store:** Homebrew 8,663; nixpkgs 115,024; Spack 9,135; Debian 76,316; Fedora 42,364.
  - **`pypi_tier3_channel_flags`:** 226,148 rows. Per column: `in_homebrew` 8,663, `in_nixpkgs` 114,181, `in_spack`
    9,135, `in_debian` 76,314, `in_fedora` 42,296.
  - **Legacy:** NULL on all five columns, because it never implemented them.
  - **Data root:** a copy of the 2026-10-17 data root, in which only these five stores and the flags table were
    empty; the counts depend on nothing else.

## Boundaries & Constraints

**Never:** a credential on these hosts; an HTTP client import in the package; a test that touches the network.

**Residual risk:**
- `flag_tier3_channels` keys every source's names verbatim through PEP 503 (its v1 contract, Story 23.1). Debian's
  `python3-numpy` and Spack's `py-numpy` therefore never meet PyPI's `numpy`; nixpkgs' `pname` and Homebrew's names
  do. A per-source name mapping is a later story under CAP-64's success clause, not this one.
- **brotli:** the nixpkgs index needs it, either in the HTTP stack (`Content-Encoding: br`) or for the parser's
  fallback. The atlas env has `brotli` 1.2.0 only transitively, through conda-forge's `urllib3`, which depends on
  `brotli-python`; PyPI's `urllib3` makes it an extra. Without it the store marks stale and says why. Declaring it
  touches `pyproject.toml`, atlas's chain-currency code stage, so that belongs with the next atlas retro
  (`DW-atlas-34-5-1`).
- **Name matching:** nixpkgs `pname`s and Homebrew names now meet PyPI names verbatim, including non-Python packages
  that happen to share one.
- **Spack:** a non-string item in a name list is now dropped, where it was `str()`-ed; the live index has none.
- **The `pname` scan** matches at any depth. Every live match is a top-level package's (150,922 of 150,922); a
  nested one would add a name.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Live run, flag on | five stores stale and empty | each holds its index; the flags table fills |
| Flag off | "no refresher wired" | unchanged |
| An index unreachable or not bytes | — | last-good kept, marker |
| nixpkgs | dead URL; attr keys | `.br` index; `pname` |
| Spack, Fedora | dead URLs | `packages.spack.io`; `pagure_owner_alias.json` `rpms` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data), R4.
- Epic 34 / Story 34.5 in `planning-artifacts/epics.md`.
- Flag: `pyforge.atlas.live_public_sources` (`feature-flag-governance:CAP-1`), registered by Story 34.4.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-5-tier3-refreshers`, cut from 34.4's branch for the
  flag and `public_sources`).
- 2026-10-18: independent review FAIL (1 blocker, 4 should-fix, 8 nits). Resolved:
  - **B1:** the flag was read at construction, and a Dagster code location constructs its stores at import, so a
    store kept fetching after the flag went off. It is now read at each refresh, through the base
    `_live_refresher()` hook, with tests both ways.
  - **S1:** a non-default request timeout is tested.
  - **S2:** bad-escape and empty `pname` are tested.
  - **S3:** the decoded-object path reports `pname`s too.
  - **S4:** a brotli body with no brotli module now says so in the marker; declaring brotli is recorded as
    residual risk.
  - **N1:** stale docs.
  - **N2, N7:** a separate request timeout replaces the duplicated asset timeout.
  - **N3:** decompression is tried whatever the first byte.
  - **N4:** the scan's depth is documented.
  - **N5, N6, N8:** the spec wording.
  - **Also:** `public_sources.request_args()` keeps `~/.netrc` out of the GET (from Story 34.6's review).
- 2026-10-18: re-review round 2 PASS. Its nits were fixed:
  - Tests cover the missing-brotli marker's guards with brotli present, and the dict path's empty-`pname` filter.
  - The brotli deferral is ledgered as `DW-atlas-34-5-1`.
  - The test hygiene items: a no-op line was dropped, and `find_spec` is narrowed to the `brotli` name.
  - `_describe` names `public_index` without reading the flag.
  - Verification names its tests from the repo root, and the two-state test spells the flag key.
  Promoted to `done`.
