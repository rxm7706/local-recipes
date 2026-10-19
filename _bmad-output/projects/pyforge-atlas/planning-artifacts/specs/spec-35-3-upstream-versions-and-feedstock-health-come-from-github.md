---
title: "35.3: Upstream versions and feedstock health come from GitHub"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: '9b35deafc0'
flag:
  key: pyforge.atlas.live_vcs_universe            # minted by Story 35.1, shared by Epic 35's feature stories
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'vcs_github_api_raw asks the identity repos for their health, as before Story 35.1; the three consumers read those rows'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-35-1-one-opt-in-switch-and-github-authenticates.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-35-2-the-vcs-batches-come-from-the-whole-universe.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/request_datasets.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/vcs_health/nodes.py
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the GitHub query asks only for archived state, stars, last push and open issues, so `upstream_version` is
always empty, and it reads upstream repos where Phases N and E.5 need feedstock repos.

Legacy makes three GitHub reads:
- **Phase K** (`_phase_k_github_graphql_batch`, CFA:4695-4920): per upstream repo, the latest release and the latest
  tag (`releases(first:1)`, `refs(refPrefix:"refs/tags/", first:1)`), 100 repos per query, a release before a tag,
  tags normalized (`_normalize_release_tag`, CFA:4608).
- **Phase N** (CFA:6461-6474): per `conda-forge/<name>-feedstock`, the last push, the default branch's CI state and the
  open issues and PRs, 25 per query.
- **Phase E.5** (CFA:2504): the conda-forge organization's archived repositories, 100 per page.

**Approach:**
1. **Three queries,** built by `GitHubRequestDataset` (`build_upstream_query`, `build_feedstock_query`,
   `build_archived_query`), each legacy's fields and batch size; Phase N also asks `isArchived`.
2. **`fetch_github`** runs them in that order for Story 35.2's batches (`upstream_repos`, `feedstocks`), with Story
   35.1's bearer auth, and writes one row per `(kind, key)`:
   - `upstream`, keyed by conda name: the repo and its normalized version, or why there is none ("no tags", the
     repository's own GraphQL error);
   - `feedstock`, keyed by feedstock name: last push, CI state, open issues and PRs, archived;
   - `archived`, keyed by feedstock name: the organization's archived feedstocks and when.
   One repo named by several packages is asked once and written to each.
3. **Refusals.** A 401, 403 or 429 stops the run (Story 35.1), except a 403 or 429 that names its wait
   (`Retry-After`, a secondary rate limit), which is waited and retried. Rows fetched before a stop are kept and the
   store is marked stale.
4. **The store keys on `(kind, key)`.** The rows of the path before this story are `kind="health"`; a store written
   before it is given those keys on the next write, so its rows never collapse onto one empty key.
5. **The consumers pick their kind:** `detect_archived_feedstocks` the `archived` rows (Phase E.5),
   `track_upstream_versions` the `upstream` rows (Phase K), `fetch_live_health` the `feedstock` rows (Phase N, with
   open PRs, CI state and the row's error). A store with none of a kind reads as before.
6. **Budget.** `refresh_vcs_github_store`'s budget is 3,600 s (about 1,400 queries for the universe).
7. **A batch GitHub cannot answer in time is halved.** GitHub ends a GraphQL query after about ten seconds with a 502
   or 504. A batch that still fails that way after its retries is split in two and each half asked, down to one
   repository; a half that still fails gives each of its repositories the failure as its error (legacy Phase K drops
   the whole batch). Each POST stops waiting after 60 s (legacy: 45 s; the default here was 900 s).
8. **The run says what it is doing:** a progress line every 25 batches and a line per retry, with the HTTP status
   only, never the exception's text.
9. **Phase N runs four batches side by side,** as legacy does (`PHASE_N_CONCURRENCY` 4, CFA:6585), its rows in batch
   order; each failed batch names its own failure; a refusal stops every batch not yet sent. Run one at a time, the
   1,176 batches took about two hours on 2026-10-19, past the node's 3,600 s budget.

Ledger key: `35-3-upstream-versions-and-feedstock-health-come-from-github`.
Type / Effort / Deps: feature / L / Story 35.1 (the switch, bearer auth), Story 35.2 (the batches).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-65** (FR-73): VCS fetches cover the full universe, credentialed on opt-in.
- **AD-2** (the credential to its own host), **AD-11** (attended, credentialed runs), **AD-13** (last-good under a
  marker).

## Acceptance Criteria

- **AC1 — Phase K.** The latest release, else the latest tag, normalized as legacy; "no tags" when neither; a missing
  repository keeps its GraphQL error; 100 repos per query, each asked once.
- **AC2 — Phase N.** Each feedstock's last push, CI state, open issues and PRs, 25 per query.
- **AC3 — Phase E.5.** The organization's archived repositories, every page, `-feedstock` stripped, other repos ignored.
- **AC4 — Refusals and timeouts.** A refusal with no wait stops the run; one with `Retry-After` is waited and retried;
  rows before a stop are kept under `stale`. A batch answered 502 or 504 is halved down to one repository, its rows
  renumbered back; another failure is not halved; a POST waits 60 s at most.
- **AC4b — Phase N side by side.** At most four batches at once, rows in order, each batch's own failure on its rows.
- **AC5 — Consumers.** Each reads its own kind; a store without kinds reads as before; a pre-35.3 store's rows survive
  the first write.
- **AC6 — Live.** See Verification. Tolerance against legacy the same day: Phase K versions for at least 95% of the
  packages legacy has a GitHub version for, equal for at least 90% of those; every legacy Phase E.5 feedstock; Phase N
  health for at least 99% of legacy's feedstocks.
- **AC7 — Gates.** `pyforge-atlas-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and mypy in
  `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_github_versions_health.py`
  (and Story 35.1's `test_credentialed_switch.py`, whose flag-on cases now read Phase K's shape).
- **Live, recorded 2026-10-18** — PENDING (a credentialed run with the `gh` CLI's token, operator ruling 2026-10-18).

## Boundaries & Constraints

**Never:** a request without the switch; a token in a log, a row or a marker; a test that reaches the network.

**Residual risk:**
- **An unarchived feedstock stays archived** in the store: the listing adds rows and never removes one.
- **GitHub's rate limit** (5,000 points an hour) bounds a run; legacy's queries cost about one point each.

## I/O & Edge-Case Matrix

| Situation | Before | After (flag on, switch on) |
|---|---|---|
| An upstream repo with a release | `upstream_version` empty | the release's tag, normalized |
| An upstream repo with tags only | empty | the latest tag, normalized |
| A repository GitHub cannot resolve | "repository not found in response" | its own `NOT_FOUND` error |
| A feedstock | its upstream's health, keyed by repo name | its own health, keyed by feedstock |
| An archived feedstock | read from the upstream's `isArchived` | the organization's archived listing |
| A 403 with `Retry-After` | stop | wait, retry |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-65 (FR-73), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 35 / Story 35.3 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-35-3-github-versions-health`, stacked on Story 35.2).
- 2026-10-18: the first credentialed live run sat 45 minutes in its retries with nothing logged (the POST timeout was
  900 s; the first batch, alphabetically the tag-heavy repositories, answered 502 four times). A probe of the same
  batch answered 200 in 5.5 s, so the 502s come and go. Approach 7 and 8 added; the re-run halved batch 1 and
  continued.
