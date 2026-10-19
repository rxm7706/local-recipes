---
title: "36.1: The Basilisk population runs"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: '24581b35b8'
flag:
  key: pyforge.atlas.basilisk_population          # new; minted by this story (the advisory drivers)
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the advisory and detail stores keep the attended path (DW-B8-1): no trigger sends anything, load() serves last-good'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-35-1-one-opt-in-switch-and-github-authenticates.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/basilisk.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** no node calls `BasiliskBatchDataset.query_population` or `BasiliskDetailDataset.fetch_details`, and the
package listing (`discovery_basilisk_packages_raw`) has no refresher, so the three Basilisk advisory datasets and the
listing stay empty (`DW-atlas-34-6-2`).

The operator's ruling of 2026-10-18 (CAP-66 amended), after a probe found the advisory endpoints answer 401 with
`www-authenticate: Bearer` while `/v1/packages` answers unauthenticated:
- the listing refreshes unattended;
- the advisories and details run under the opt-in with a Basilisk token, and stay stale until the operator adds one.

**Approach:**
1. **The listing refreshes itself.** With `pyforge.atlas.live_public_sources` on, `BasiliskPackagesDataset` walks
   `/v1/packages` page by page through `public_sources.fetch_text` (a no-op auth keeps `~/.netrc` out); the bootstrap
   no longer lists it as fetcher-less.
2. **Two trigger nodes.** `refresh_basilisk_population` sends one conda PURL per enumerated package (Phase B;
   `pkg:conda/conda-forge/<name>`) to `vulnerability_basilisk_raw`; `refresh_basilisk_details` sends each matched
   advisory id once to `vulnerability_basilisk_detail_raw`. Both are pure.
3. **The stores decide.** With `pyforge.atlas.basilisk_population` on, the batch store POSTs the OSV-compatible
   querybatch (`{"queries": [{"package": {"purl"}}]}`, ≤1,000 per request) and maps each result to its queried package;
   the detail store GETs `/v1/vulns/{id}`; both wait out a 429 or 503 (`Retry-After`, else a backoff). Each sends
   `Authorization: Bearer <token>` only under `PYFORGE_ATLAS_CREDENTIALED=1`, over https to `api.basilisk.prefix.dev`;
   otherwise nothing is sent and last-good is kept under a marker that names why. The POST goes through
   `APIDataset.save` (Story 35.1).
   - Deviation from the catalog's declarative credentials: the token comes from `PYFORGE_ATLAS_BASILISK_TOKEN`, read
     at the fetch. A catalog `credentials: basilisk_token` key would make Kedro's eager resolution fail every run whose
     `conf/local/credentials.yml` lacks it, the operator's included.
4. **Flag.** `pyforge.atlas.basilisk_population` (dev on, staging and production off). Off, the advisory stores keep
   the attended path: no trigger sends anything.

Ledger key: `36-1-the-basilisk-population-runs`.
Type / Effort / Deps: feature / M / Story 35.1 (the switch, bearer auth, the POST route).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-66** (FR-74, amended 2026-10-18 by operator ruling).
- **AD-2** (a credential to its own host), **AD-11** (attended, credentialed runs), **AD-13**, **AD-14** (new signal,
  not parity-gated).
- **Closes** `DW-atlas-34-6-2` (the listing had no story).

## Acceptance Criteria

- **AC1 — The listing.** With live public sources on it walks every page itself; off, it has no refresher.
- **AC2 — The triggers.** One PURL per enumerated package, each advisory id once.
- **AC3 — The querybatch.** Under the flag, the switch and a token: a bearer POST of OSV queries; each result lands on
  its queried package, a PyPI-tagged advisory included; a misaligned answer keeps last-good.
- **AC4 — The details.** A bearer GET per id, its id quoted into the path; a 429's `Retry-After` waited and a 503
  retried, as for a querybatch chunk; the driver output reaches `fetch_basilisk_details` and the rollup.
- **AC5 — Nothing sent otherwise.** Flag off: nothing, no marker. No switch, no token, another host or http: nothing,
  last-good under a marker that names why, never the token.
- **AC6 — Flag.** Registered in the flag tree, its overlays, pyforge-core's and the platform's tables; tested in both
  states.
- **AC7 — Live.** See Verification.
- **AC8 — Gates.** `pyforge-atlas-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and mypy in
  `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_basilisk_population.py`.
- **Live, recorded 2026-10-18,** on a scratch data root (dev, flags on, no switch, no token):
  - **The listing** (`--pipelines upstream_discovery --nodes refresh_basilisk_packages`, 9 min): 34,672 packages
    (Basilisk reported 34,105 on 2026-08-30). Status: 30,178 `no_match`, 2,673 `not_checked`, 1,821 `affected`.
    Ecosystems: 21,050 PyPI, 6,382 GitHub, 3,811 CRAN, 2,697 conda-forge, the rest npm, gem, cpan, git, cargo,
    bitbucket.
  - **The advisory drivers** (`--pipelines vulnerability --nodes refresh_basilisk_population,ingest_basilisk_advisories,refresh_basilisk_details,fetch_basilisk_details`):
    nothing sent; both stores keep last-good (none yet) under the marker "credentialed fetch not run:
    PYFORGE_ATLAS_CREDENTIALED is not 1". The first run found the next node's `load()` replacing that marker with "no
    Basilisk fetcher wired"; fixed (each store keeps the reason its refresh wrote) and re-run.
  - No authorized Basilisk call was made: the advisory datasets stay empty until the operator supplies a token
    (`DW-atlas-36-1-1`).

## Boundaries & Constraints

**Never:** a credential to Basilisk without the switch; a token in a log, a row or a marker; a test that reaches the
network.

**Residual risk:**
- **The advisories stay empty** until the operator supplies a Basilisk token (`DW-atlas-36-1-1`).
- **The querybatch shape is OSV's**, assumed: Basilisk documents itself as OSV-compatible and no authorized call has
  been made. A different shape fails the batch and keeps last-good.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Live public sources on | the listing never refreshed | it walks `/v1/packages` |
| Flag on, switch and token | no node asks | querybatch, then details |
| Flag on, no token | — | nothing sent; the marker names `PYFORGE_ATLAS_BASILISK_TOKEN` |
| Flag off | — | nothing sent (the attended path) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-66 (FR-74), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 36 / Story 36.1 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-36-1-basilisk`, cut from `main` at `24581b35b8`).
- 2026-10-18, review round 1 (FAIL), fixed:
  - B1, B2: the detail store's flag-off gate and its never-populated marker are tested.
  - Should-fix: the Retry-After wait and the 503 retry are proven (and the querybatch now waits them out too); the
    another-host and http markers are tested; the token's name is `PYFORGE_ATLAS_BASILISK_TOKEN` in CAP-66,
    `live-sources.md` and the Epic's And clause (memlog decision); the driver output is fed through
    `fetch_basilisk_details` and `derive_basilisk_vuln_rollup`; stale text in `basilisk.py`, `tools/bootstrap.py` and
    `test_dag_resolves.py` corrected; markers and logs carry the status, never the exception's text.
  - Nits: the advisory id's quoting is tested; the unreachable returns are gone. Not changed: with the flag on,
    `load()` reads last-good without an age check, as every refresh store does; the trigger node's cadence owns age.
- 2026-10-18: the live run found the advisory and detail `load()` overwriting the refresh's marker; each store now
  keeps it, and a store no refresh has reached reads "not yet populated". The suite pins
  `pyforge.atlas.basilisk_population` off in `tests/conftest.py` (dev reads it on), like Story 35.1's flag.
