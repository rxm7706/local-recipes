---
title: "35.1: One opt-in switch, and GitHub authenticates"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: '3c9cf29e1f'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/request_datasets.py
deferred: []
declared_low_risk: false
review_loop_iteration: 0
followup_review_recommended: false
---

<intent-contract>

## Intent

**Problem:** no switch separates a credentialed run from a public one, and the GitHub fetch cannot authenticate or
even send.

- Nothing reads `PYFORGE_ATLAS_CREDENTIALED`. The operator's ruling of 2026-10-18 makes it the one opt-in for a run
  whose requests carry a credential (AD-11, attended).
- `vcs_github_api_raw` hands `credentials.yml`'s `github_token` (a `{token: ...}` mapping) to `APIDataset` as
  requests' `auth`. A mapping is neither a pair nor a callable, so requests raises before it sends.
- The batched GraphQL request is a POST, sent through `APIDataset.load()`, which sends only GET ("Only GET method is
  supported for load()"). Every chunk degrades to error rows and the store goes stale. No test covered the default
  path: every test injects a `fetcher`.

**Approach:**
1. **One switch.** `datasets/credentials.py` reads `PYFORGE_ATLAS_CREDENTIALED` when a dataset would fetch, never at
   import (Dagster builds every dataset when it imports the definitions). Only the exact value `1` turns it on.
2. **Bearer auth to its own host.** `BearerAuth` is a requests `auth` callable that sets
   `Authorization: Bearer <token>` only on a request to its host, and never shows the token in `repr`.
   `github_auth` builds it from `github_token` only with the switch on, a usable token, and a URL on `api.github.com`;
   an override to another host never receives the token (AD-2). No `requests` import (the no-inline-IO scan).
3. **The POST sends.** With auth, a chunk goes through `APIDataset.save(body)`; the response comes back through an
   in-memory `response_dataset`, since `save()`'s return value does not survive kedro's wrapper.
4. **The store says why.** Switch off, no token, or another host: nothing is sent and last-good is kept under a
   marker that names the reason. A run where every batch fails keeps last-good under a marker that carries the
   failure (a rejected token reads 401); before, it read "fetch returned no data".
5. **Flag.** `pyforge.atlas.live_vcs_universe` gates steps 1-4 (dev on, staging and production off). Off, the
   dataset keeps the path this story found.
6. **Test transport.** The atlas suite's root `conftest.py` pins the flag off and unsets the switch for every test,
   and wraps requests' transport so a request carrying `Authorization` without the switch fails its test.
   `fake_transport` answers requests without a network and records them.

**Scope.** This story gates GitHub. Story 36.1 (Basilisk) and Story 36.2 (the OpenTeams board and staged-recipes PRs)
read the same switch. GitLab, Codeberg and the eight registries are public in legacy (Phase L sends no credential);
Story 35.4 drops their catalog credentials. BigQuery keeps its own `PHASE_P_ENABLED` gate.

Ledger key: `35-1-one-opt-in-switch-and-github-authenticates`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-65** (FR-73): VCS and registry fetches cover the full universe, credentialed on opt-in.
  This story is its switch and its GitHub authentication.
- **AD-2** (a credential attaches to its own host only), **AD-11** (attended, credentialed runs), **AD-13**
  (last-good under a marker).
- **Rulings.** 2026-10-18: the opt-in `PYFORGE_ATLAS_CREDENTIALED=1`; an agent may set it only on Epic 35's and
  Story 36.2's live verification runs.

## Acceptance Criteria

- **AC1 — The switch.** Only `PYFORGE_ATLAS_CREDENTIALED=1` turns it on (`""`, `0`, `true`, `yes`, ` 1` do not). It is
  read at save, not at construction.
- **AC2 — Off sends nothing.** With the flag on and the switch off, `vcs_github_api_raw` sends no request, keeps
  last-good, and marks stale with a reason naming the switch and not the token.
- **AC3 — On authenticates GitHub only.**
  - With the switch on and a token, each chunk is a POST to `api.github.com` with `Authorization: Bearer <token>`,
    and its rows land.
  - A URL on another host, or no usable token (empty, missing, a `[user, password]` pair), sends nothing and marks
    stale with the reason.
  - `BearerAuth` sets the header only on its own host and never shows the token.
- **AC4 — Failure degrades.** A rejected token (401) is retried, keeps last-good, and the marker carries the status,
  never the token.
- **AC5 — The guard bites.** A request carrying `Authorization` without the switch fails its test (mutation:
  dropping the switch check in `github_auth` turns AC2 red).
- **AC6 — Flag.** `pyforge.atlas.live_vcs_universe` is registered in the flag tree, its overlays, pyforge-core's and
  the platform's flag tables; tested in both states. Off, the path is unchanged.
- **AC7 — Gates.** `pyforge-atlas-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and mypy in
  `pyforge-foundry-full`), `flag-gate-check`, pyforge-core's and the platform's flag tests; governing Specs
  reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_credentialed_switch.py`.
- **Live, recorded 2026-10-18,** `--pipelines vcs_health --nodes refresh_vcs_github_store` on a copy of a
  2026-10-18 data root (its `identity_packages_primary`: 727 GitHub repos, 8 batches), flag on (dev):
  - **Switch unset:** exit 0; no request; the marker reads "credentialed fetch not run: PYFORGE_ATLAS_CREDENTIALED is
    not 1 -- keeping last-good".
  - **`PYFORGE_ATLAS_CREDENTIALED=1`:** exit 0, 12 s, peak RSS 0.27 GB. All 8 bearer POSTs reached
    `api.github.com/graphql` and were answered 401: the operator's `conf/local/credentials.yml` is the bootstrap's
    placeholder ("Local placeholder credentials for dryrun orchestration testing"). The marker reads "every GitHub
    batch failed (... 401 Client Error: Unauthorized ...) -- keeping last-good"; the log carries no token.
  - **Not yet shown live:** rows landing from an accepted token. That needs a real `github_token` in
    `conf/local/credentials.yml` (for example `token: ${oc.env:GITHUB_TOKEN}`), an operator step.

## Boundaries & Constraints

**Never:** a credential on a request without the switch; a credential to a host other than its own; a token in a log,
a dataset or a marker; a test or CI job that sets the switch or reaches the network.

**Residual risk:**
- **The live fill is unproven** until the operator supplies a real token (see Verification).
- **The flag-off path still cannot send** (the GET-only `load()`). It is the state this story found, kept as the
  flag's off state; it goes when the flag is cleaned up.
- **One store mixes upstream repos and feedstocks** (`merge_on = feedstock_name`): Story 35.3 splits them.

## I/O & Edge-Case Matrix

| Situation | Before | After (flag on) |
|---|---|---|
| Switch unset | the POST raised before sending; error rows; "fetch returned no data" | nothing sent; marker names the switch |
| Switch `1`, real token | the POST raised before sending | bearer POST to `api.github.com`; rows land |
| Switch `1`, placeholder token | the POST raised before sending | 401, retried; last-good kept; marker carries the 401 |
| Switch `1`, `GITHUB_API_BASE_URL` on another host | the POST raised before sending | nothing sent; marker names the host |
| A test request with `Authorization` and no switch | sent | the test fails |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-65 (FR-73), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 35 / Story 35.1 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-35-1-credentialed-switch`, cut from `main` at
  `3c9cf29e1f`).
  - The POST fix joined the story: without it no request reaches GitHub, so the header could not be shown.
  - The live run found the local credentials file is the bootstrap placeholder.
