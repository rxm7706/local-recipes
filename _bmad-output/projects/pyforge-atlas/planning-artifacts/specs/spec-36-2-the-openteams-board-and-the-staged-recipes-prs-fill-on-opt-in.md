---
title: "36.2: The OpenTeams board and the staged-recipes PRs fill on opt-in"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: '24581b35b8'
flag:
  key: pyforge.atlas.identity_live_sources        # new; minted by this story
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'both stores keep the path before this story: no fetcher, last-good under a stale marker'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-35-1-one-opt-in-switch-and-github-authenticates.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/identity_sources.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `openteams_project_1_board_raw` (the OpenTeams project board, GraphQL) and
`discovery_staged_recipes_prs_raw` (the staged-recipes PR list, REST) are built with no fetcher, so
`identity_packages_primary` lacks its board and staged-PR sources and the identity exports and inventory priorities
lack their rows. Both stores accept `credentials: github_token` and never use it.

**Approach:**
1. **A credentialed live refresher for each.** With `pyforge.atlas.identity_live_sources` on, each store builds its
   own refresher at the moment of the refresh: Story 35.1's `github_auth` (the switch, a usable token, https to
   `api.github.com`). The board POSTs its GraphQL query through `APIDataset.save` (Story 35.1's route); the PR list
   GETs each page and each open PR's files. Without the switch or a token the refresher fails with the reason, so the
   store keeps last-good under a marker that names it, and nothing is sent.
   - The board is GraphQL, which GitHub serves only to an authenticated caller; the PR list is about 300 pages,
     beyond GitHub's 60 unauthenticated requests an hour.
2. **One pagination for both fetchers:** `_do_refresh` takes the fetcher as an argument, so the injected fetcher
   (tests) and the live one share it.
3. **A pagination stopped part-way is honest** (`_HonestPagination`, AD-13). Story 21.x kept the pages read before a
   failure and cleared the marker; with a live fetch that let one 502 replace 20,000 PRs with 100, silently.
   - A page answered 502, 503 or 504 is asked again (`max_retries`).
   - A failure part-way, with a store already written, fails the refresh: last-good is kept. With none, the pages
     read are written. Either way the marker names the page and the status, never the exception's text.
   - A 401, 403 or 429 on a PR's files stops every later files request (Story 35.1's stop statuses); the PR rows are
     written and the marker says where it stopped.
   - The first page's failure names its status or the GraphQL error.
4. **The caps cover the whole history.** The PR list reads up to 500 pages (Story 21.x: 200, which stopped at PR
   #14,827) and the files of up to 2,000 open PRs (500, of 1,222 open); about 1,600 requests, inside GitHub's 5,000
   an hour.
5. **Flag.** `pyforge.atlas.identity_live_sources` (dev on, staging and production off); the atlas suite pins it off.

Ledger key: `36-2-the-openteams-board-and-the-staged-recipes-prs-fill-on-opt-in`.
Type / Effort / Deps: feature / M / Story 35.1 (the switch, bearer auth, the POST route), Story 34.6 (the public
identity sources).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-67** (FR-75).
- **AD-2**, **AD-11** (attended, credentialed runs; the operator ruled 2026-10-18 that this story's live verification
  may set the switch, with the `gh` CLI's token).

## Acceptance Criteria

- **AC1 — The board.** Under the flag, the switch and a token: a bearer GraphQL POST per page; its issues land.
- **AC2 — The PRs.** Under the same: a bearer GET per page and per open PR's files; the PRs land.
- **AC3 — Nothing sent otherwise.** No switch, no token (a stub pair included), or another host: nothing sent, last-good
  under a marker that names why, never the token. Flag off: no live refresher.
- **AC3b — A stopped pagination never hides.** A failure part-way keeps a fuller last-good; a refusal stops the files
  requests; the marker names the page and the status; a 5xx page is asked again.
- **AC4 — Flag.** Registered in the flag tree, its overlays, pyforge-core's and the platform's tables; tested in both
  states; the real reader tested against a tree.
- **AC5 — Live.** See Verification: `identity_packages_primary` holds rows from each `identity_source` and carries the
  board's issue URLs and the PRs' URLs; `identity_complete_export` and `inventory_priority_assignments` hold rows.
- **AC6 — Gates.** `pyforge-atlas-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and mypy in
  `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_identity_live_sources.py`.
- **Live, recorded 2026-10-18,** on a scratch data root (dev, flag on), with `PYFORGE_ATLAS_CREDENTIALED=1` and the
  `gh` CLI's token through a scratch `--env verify` (operator ruling); no token in any log:
  - First run, at the caps of Story 21.x: `--pipelines upstream_discovery --nodes refresh_openteams_board,refresh_staged_recipes_prs,build_identity_packages_primary`
    (12 min) exit 0, no marker. The board: 9,814 issues (5,337 open, 4,477 closed). The PRs: 20,000 (1,222 open),
    numbers 14,827 to 35,250, files for 500 open PRs.
  - After review round 1, with the caps lifted: `--nodes refresh_staged_recipes_prs,build_identity_packages_primary`
    (19 min) exit 0, no marker. The PRs: 34,081, numbers 1 to 35,251 (the whole history), 1,223 open, files for
    1,222.
  - **`identity_packages_primary`:** 9,075 rows (8,204 `openteams-board`, 868 `purl-associator`, 3 `inventory`);
    9,057 carry an OpenTeams issue URL and 3,858 a staged-recipes PR URL (2,129 at the old caps).
  - **Downstream,** `--pipelines derived_artifacts` with no switch exit 0: `identity_complete_export` 9,075 rows
    (3,858 with a PR URL), `inventory_priority_assignments` 9,075 rows. Every priority is P10: this root has no JFrog
    consumption.
  - The legacy identity script is retired, so there is no same-day oracle.

## Boundaries & Constraints

**Never:** a credential without the switch; a token in a log, a row or a marker; a test that reaches the network.

**Residual risk:**
- **The operator's own runs** need a real `github_token` in `conf/local/credentials.yml` (Story 35.1's README row).
- **The caps are a ceiling:** 50,000 PRs and 2,000 open PRs' files. Past them the run logs the cap; the feedstock URL
  and the conda PURL outrank a staged PR downstream (`identity_gist.py`, `derived_artifacts/nodes.py`).

## I/O & Edge-Case Matrix

| Situation | Before | After (flag on) |
|---|---|---|
| Switch and token | no fetch; stale | the board and the PRs fetch with the bearer |
| No switch | no fetch; "no refresher wired" | no fetch; the marker names the switch |
| A stub `[user, password]` credential | — | no fetch; "no github_token" |
| Flag off | no fetch | no fetch (unchanged) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-67 (FR-75), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 36 / Story 36.2 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-36-2-identity-sources`, cut from `main` at `24581b35b8`).
- 2026-10-18, review round 1 (FAIL), fixed:
  - B1: `spec-pyforge-marshal` co-governs `pyforge-core/tests/unit/test_flags.py`; reconciled and stamped.
  - B2: a failure part-way replaced a fuller store and cleared the marker; `_HonestPagination` (Approach 3).
  - Should-fix: a refusal stops the files requests; the marker names the status; logs carry the status, never the
    exception's text; tests for the cursor, an open PR's files, another host and plain http, the timeouts, a 5xx
    asked again, the default; the caps lifted (Approach 4) rather than deferred.
  - Nit: the epics Surface line drops `conf/base/catalog.yml`: the catalog already declares `credentials:
    github_token` for both stores, so it did not change.
