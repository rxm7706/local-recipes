---
title: "35.1: One opt-in switch, and GitHub authenticates"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: '3c9cf29e1f'
flag:
  key: pyforge.atlas.live_vcs_universe            # new; minted by this story, shared by Epic 35's feature stories
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the path this story found: vcs_github_api_raw posts through the GET-only load() and sends nothing; the host and registry stores pass their catalog credentials to APIDataset as before'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/request_datasets.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py
deferred: []
declared_low_risk: false
review_loop_iteration: 1
followup_review_recommended: true
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
   - Deviation from the Epic's Surface line: the switch is read from `os.environ` directly, not through
     `globals.yml`'s `env_or`, which resolves when the catalog is built.
2. **Bearer auth to its own host.** `BearerAuth` is a requests `auth` callable that sets
   `Authorization: Bearer <token>` only on an https request to its host, and never shows the token in `repr`.
   `github_auth` builds it from `github_token` only with the switch on, a usable token (printable ASCII, no space or
   control character inside: a newline would make `http.client` quote the header in its error), and an https URL on
   `api.github.com`; an override to another host or to plain http never receives the token (AD-2). No `requests`
   import (the no-inline-IO scan).
3. **The POST sends.** With auth, a chunk goes through `APIDataset.save(body)`; the response comes back through an
   in-memory `response_dataset`, since `save()`'s return value does not survive kedro's wrapper.
4. **The store says why, and a rejected token is sent once.** Switch off, no token, or another host or scheme:
   nothing is sent and last-good is kept under a marker that names the reason. A 401 is not retried and stops the
   remaining chunks (GitHub can block a client that keeps sending bad credentials). A run where every batch fails
   keeps last-good under a marker that carries the HTTP status, or the GraphQL error of a body with no data (a rate
   limit, a bad query); a missing repository keeps its own GraphQL error in its row. On this path no exception text
   reaches a log, a row or a marker, since it can quote a request header.
5. **The public hosts send no credential.** With the flag on, the GitLab, Codeberg and eight registry stores send no
   catalog credential (legacy Phases K and L read them unauthenticated) and a no-op auth keeps `~/.netrc` out. Their
   batches are empty today; this closes the path before Story 35.2 fills them. Story 35.4 decides which may
   authenticate, and only under the switch.
6. **Flag.** `pyforge.atlas.live_vcs_universe` gates steps 1-5 (dev on, staging and production off). Off, every
   dataset keeps the path this story found.
7. **Test transport.** The atlas suite's root `conftest.py` pins the flag off and unsets the switch for every test,
   and wraps requests' transport so a request carrying a credential header (`Authorization`,
   `Proxy-Authorization`, `PRIVATE-TOKEN`, `X-NuGet-ApiKey`) without the switch fails its test. `fake_transport`
   answers requests without a network, records them and their timeouts, and keeps the guard. A test that patches
   `Session.request` itself bypasses the guard.

**Scope.** This story authenticates GitHub and holds every other VCS credential back. Story 36.1 (Basilisk) and
Story 36.2 (the OpenTeams board and staged-recipes PRs) read the same switch. BigQuery keeps its own
`PHASE_P_ENABLED` gate.

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
  read at save, not at construction (a dataset built with it unset sends once it is set).
- **AC2 — Off sends nothing.** With the flag on and the switch off, `vcs_github_api_raw` sends no request, keeps
  last-good, and marks stale with a reason naming the switch and not the token.
- **AC3 — On authenticates GitHub only.**
  - With the switch on and a token, each chunk is a POST to `api.github.com` with `Authorization: Bearer <token>`,
    and its rows land.
  - A URL on another host or over plain http, or no usable token (empty, missing, a `[user, password]` pair, a space
    or newline inside), sends nothing and marks stale with the reason.
  - `BearerAuth` sets the header only on an https request to its own host and never shows the token.
  - With the flag on, a GitLab request carries no catalog credential.
- **AC4 — Failure degrades.** A rejected token (401) is sent once, stops the remaining chunks, keeps last-good, and the
  marker carries the status, never the token. A GraphQL error body with no data puts its error in the marker.
- **AC5 — The guard bites.** A request carrying a credential header without the switch fails its test, with or without
  `fake_transport` (mutation: dropping the switch check in `github_auth` turns AC2 red).
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
  - **`PYFORGE_ATLAS_CREDENTIALED=1`, first run:** exit 0, 12 s, peak RSS 0.27 GB. Every bearer POST reached
    `api.github.com/graphql` and was answered 401 (4 attempts for each of the 8 batches): the operator's
    `conf/local/credentials.yml` is the bootstrap's placeholder ("Local placeholder credentials for dryrun
    orchestration testing").
  - **After review round 1:** exit 0. One bearer POST, answered 401, then the remaining chunks were skipped. The
    marker reads "every GitHub batch failed (HTTP 401) -- keeping last-good"; the log carries no token.
  - **Not yet shown live:** rows landing from an accepted token. That needs a real `github_token` in
    `conf/local/credentials.yml` (for example `token: ${oc.env:GITHUB_TOKEN}`), an operator step.

## Boundaries & Constraints

**Never:** a credential on a request without the switch; a credential to a host other than its own; a token in a log,
a dataset or a marker; a test or CI job that sets the switch or reaches the network.

**Residual risk:**
- **The live fill is unproven** until the operator supplies a real token (see Verification; `DW-atlas-35-1-1`).
- **Epic 35's "every credentialed dataset reads the one switch"** holds for GitHub here; Basilisk and the identity
  sources join in Stories 36.1 and 36.2.
- **The flag-off path still cannot send** (the GET-only `load()`). It is the state this story found, kept as the
  flag's off state; it goes when the flag is cleaned up.
- **One store mixes upstream repos and feedstocks** (`merge_on = feedstock_name`): Story 35.3 splits them.

## I/O & Edge-Case Matrix

| Situation | Before | After (flag on) |
|---|---|---|
| Switch unset | the POST raised before sending; error rows; "fetch returned no data" | nothing sent; marker names the switch |
| Switch `1`, real token | the POST raised before sending | bearer POST to `api.github.com`; rows land |
| Switch `1`, placeholder token | the POST raised before sending | one POST, 401; the other chunks skipped; marker carries HTTP 401 |
| Switch `1`, `GITHUB_API_BASE_URL` on another host or over http | the POST raised before sending | nothing sent; marker names the host or scheme |
| A GraphQL body of errors and no data | "fetch returned no data" | marker carries the error (`RATE_LIMITED: ...`) |
| Flag on, a GitLab or registry request | the catalog credential passed as auth | no credential; no `~/.netrc` |
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
- 2026-10-18: independent review round 1 FAIL. 2 blockers, 6 should-fix items, nits; 19 mutants, 5 survived.
  - **B1:** the spec carries the `flag:` block (`flag-gate-check` was red).
  - **B2:** a token with a space or control character inside is no token, so `http.client` can never quote it.
  - **Should-fix:**
    - The new failure marker is behind the flag.
    - A test builds the dataset before setting the switch.
    - Bearer auth needs https.
    - A GraphQL error body says why.
    - A 401 is sent once and stops the chunks.
    - The host and registry stores hold their credentials back under the flag.
  - **Nits:** the real flag reader is tested against a tree; the autouse guard is tested without `fake_transport` and
    covers four credential headers; the timeout is asserted; the `env_or` deviation is recorded; an unused parameter
    is gone.
