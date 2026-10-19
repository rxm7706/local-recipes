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
review_loop_iteration: 0
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
2. **The pagination is unchanged:** `_do_refresh` takes the fetcher as an argument, so the injected fetcher (tests)
   and the live one share it.
3. **Flag.** `pyforge.atlas.identity_live_sources` (dev on, staging and production off); the atlas suite pins it off.

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
- **AC4 — Flag.** Registered in the flag tree, its overlays, pyforge-core's and the platform's tables; tested in both
  states; the real reader tested against a tree.
- **AC5 — Live.** See Verification: `identity_packages_primary` holds rows from each `identity_source` and carries the
  board's issue URLs and the PRs' URLs; `identity_complete_export` and `inventory_priority_assignments` hold rows.
- **AC6 — Gates.** `pyforge-atlas-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and mypy in
  `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_identity_live_sources.py`.
- **Live, recorded 2026-10-18,** on a scratch data root (dev, flag on), with `PYFORGE_ATLAS_CREDENTIALED=1` and the
  `gh` CLI's token through a scratch `--env verify` (operator ruling); no token in the log:
  - `--pipelines upstream_discovery --nodes refresh_openteams_board,refresh_staged_recipes_prs,build_identity_packages_primary`
    (12 min) exit 0, no marker.
  - **The board:** 9,814 issues (5,337 open, 4,477 closed).
  - **The PRs:** 20,000 PRs (1,222 open), numbers 14,827 to 35,250; the files of 500 open PRs.
  - **`identity_packages_primary`:** 9,075 rows (8,204 `openteams-board`, 868 `purl-associator`, 3 `inventory`);
    9,057 carry an OpenTeams issue URL, 2,129 a staged-recipes PR URL.
  - **Downstream,** `--pipelines derived_artifacts` with no switch exit 0: `identity_complete_export` 9,075 rows,
    `inventory_priority_assignments` 9,075 rows. Every priority is P10: this root has no JFrog consumption.
  - The legacy identity script is retired, so there is no same-day oracle.

## Boundaries & Constraints

**Never:** a credential without the switch; a token in a log, a row or a marker; a test that reaches the network.

**Residual risk:**
- **The operator's own runs** need a real `github_token` in `conf/local/credentials.yml` (Story 35.1's README row).
- **Two caps that predate this story stay:** the PR list stops at 200 pages (20,000 PRs; staged-recipes has about 35,000, so
  PRs before #14,827 are not read), and the file-path tier reads the first 500 open PRs (1,222 were open). The
  feedstock URL outranks a staged PR for a merged package, so the oldest PRs matter least.

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
