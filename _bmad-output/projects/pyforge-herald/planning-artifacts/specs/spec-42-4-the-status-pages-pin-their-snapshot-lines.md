---
title: '42.4: The status pages pin their snapshot lines'
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-39-1-the-dossier-tile-shows-every-ci-surface-that-is-not-live.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-42-1-the-fleet-board-and-guild-status-pages-render-at-build.md
  - docs-site/src/pages/status/ci/[...index].astro
  - docs-site/src/lib/dossier-blocks.ts
  - docs-site/src/lib/status.ts
  - docs-site/src/lib/artifact.ts
  - docs-site/src/content/ci-status.json
  - src/shared/packages/pyforge-herald/src/pyforge/herald/pages_env.py
  - src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py
  - src/shared/packages/pyforge-herald/tests/meta/pages_astro.py
---

<intent-contract>

## Intent

**Problem:** the Pages site serves an operator-committed CI snapshot and says so only in rendered lines no test reads.
On `main` at `03a7aff5d9`:

- `status/ci/index.html` (Story 42.1, ported to Astro by Story 43.7) renders "Snapshot captured" with a `<time>`
  element holding `ci-status.json`'s `fetched_at`, and the intro sentence "A snapshot: nothing on this page is live."
  (`docs-site/src/pages/status/ci/[...index].astro`).
- The dossier's `ci_surfaces` tile (Story 39.1) renders `Snapshot captured at <fetched_at>` as its soft note
  (`docs-site/src/lib/dossier-blocks.ts`, the `ci_surfaces` case), on the dossier page and in the artifact build that
  `docs-site/src/lib/artifact.ts` cuts from it.
- No built-site test asserts any of the three lines. `test_one_generator.py`'s
  `test_the_status_pages_carry_the_built_from_line_and_no_stamp_of_their_own` counts the guild page's rows and checks
  the built-from line; the tile's unit test (`tests/unit/test_ci_surfaces_tile_flag_states.py`) checks the block's
  `fetched_at` field, not the rendered line. Removing any of the three lines leaves `pages-check` and herald's suite
  green.
- The committed snapshot `docs-site/src/content/ci-status.json` carries `fetched_at` 2026-10-14 (last written in
  `fa6e11d4e4`), while #2247 resumed every CI surface on 2026-10-16: the live dossier and `/status/ci/` show rows as
  stuck or paused that are live. The capture-time line is the only thing that tells a reader so.

The EGM audit of 2026-11-01 (marshal Story 113.7, `spec-pyforge-marshal:CAP-302`) accepted five findings on this
gap, cluster HER-K4: HER-M-Z4 (CAP-60 success checks only that `status/ci/index.html` exists), HER-M-D4 (CAP-59 never
asserts that `fetched_at` renders), HER-M-C4 (CAP-60 success never tests `/status/ci/`), HER-M-C5 (CAP-59's intent
promises checks its success never states) and HER-M-D6 (the flag state `/status/` needs is unstated). Residue:
`_bmad-output/projects/pyforge-herald/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:** add built-site assertions to `src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py` over
its existing module-scoped `built` fixture (the tracked tree built with `status=True, tile=True`, every input present,
under CI's variables): one test for the guild page's capture-time line and not-live sentence, one for the dossier
tile's capture-time line in both outputs. Each reads F, the snapshot's `fetched_at`, from
`docs-site/src/content/ci-status.json` at test time, so an operator refresh of the snapshot never reds them. The
generator is edited only if a pinned line turns out not to render as stated. Operator ruling 2026-11-01:
`ci-status.json` stays an operator refresh at each pause and resume; the story asserts only the rendered lines.

### Living CAP citations

- **Parent.** A fix under `spec-pyforge-herald` CAP-59 (the dossier's CI surfaces tile, FR-11.1) and CAP-60 (the
  guild status page, FR-12.1); no CAP, no FR, no flag (`spec-feature-flag-governance` Q1).
- **Architecture.** herald:AD-21 as amended 2026-10-14 (the placement rule: nothing on a Pages page is live, and each
  status page names its snapshot time).
- **Origin.** The EGM audit of 2026-11-01 (marshal Story 113.7), cluster HER-K4, and the operator's ruling of the same
  day.

## Acceptance Criteria

- **AC1 — The guild page names its capture time.** Given the `built` fixture, When the test reads
  `status/ci/index.html`, Then it holds exactly one `<time datetime="F">F</time>` element, inside the paragraph that
  reads "Snapshot captured", where F is the `fetched_at` of `docs-site/src/content/ci-status.json` read from the file
  (never a literal date).
- **AC2 — The guild page says nothing on it is live.** Given the `built` fixture, Then `status/ci/index.html` holds the
  sentence "nothing on this page is live" exactly once.
- **AC3 — The tile names its capture time in both outputs.** Given the `built` fixture (`PYFORGE_CI_SURFACES_TILE=1`),
  Then `herald/dossier/index.html` and the artifact build `herald/artifact/dossier.html` each hold
  "Snapshot captured at F" exactly once, with F as in AC1.
- **AC4 — The tests guard the lines.** Each mutation below fails its test, and the tree is restored afterwards: the
  `<time>` element dropped from `docs-site/src/pages/status/ci/[...index].astro` (AC1), the not-live sentence dropped
  from it (AC2), the soft-note `Snapshot captured at` paragraph dropped from the `ci_surfaces` case of
  `docs-site/src/lib/dossier-blocks.ts` (AC3).
- **AC5 — The tests run, never skip.** Under `HERALD_DOCS_SITE_REQUIRED=1`, after `docs-site-install`, the new tests
  run and pass; without the install they skip naming it, as every `needs_astro` test does (Story 45.1).
- **AC6 — The gates.** `pixi run --frozen -e pyforge-herald pyforge-herald-test-built` and
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` exit 0; `pixi run --frozen -e pyforge-guild lint-types`
  exits 0.

## Boundaries & Constraints

- Tests only, by intent. A generator edit (`[...index].astro`, `dossier-blocks.ts`) lands only if a pinned line does
  not render as AC1-AC3 state, and is recorded in this spec's Change Log.
- `docs-site/src/content/ci-status.json` is neither refreshed nor edited here: its refresh is the operator's act at
  each pause and resume (ruling 2026-11-01; SPEC.md's open question on a scheduled refresh stays the Spec's).
- The tests read F from the committed file; they never pin a date, a row count or a verdict, so a refreshed snapshot
  keeps them green.
- No flag, no new pixi task, no new dependency; the `site` env gains no pyforge package; no herald module or test
  imports `pyforge.steward` (herald:AD-21, the CAP-59 boundary).
- No `SPEC.md`, PRD, Dream or memlog text is edited by this story: the CAP-59 / CAP-60 re-derive (HER-K1's cascade)
  is the Spec's.

## Binding

- Parent capability: `spec-pyforge-herald` CAP-59 (FR-11.1), the dossier's CI surfaces tile.
- Parent capability: `spec-pyforge-herald` CAP-60 (FR-12.1), the guild status page.

Parent: spec-pyforge-herald CAP-59 and CAP-60 (a fix; no CAP minted)

Surface: `src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py`, `docs-site/src/pages/status/ci/[...index].astro`, `docs-site/src/lib/dossier-blocks.ts`

- Architecture: herald:AD-21 as amended 2026-10-14.
- Audit: EGM audit 2026-11-01, cluster HER-K4; findings HER-M-Z4, HER-M-D4, HER-M-C4, HER-M-C5, HER-M-D6;
  `_bmad-output/projects/pyforge-herald/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 42, Story 42.4 (a fix into the done epic, operator rule of 2026-10-04; doctor Story 41.5 lets `epic-42`
  roll up to `in-progress` for the new backlog story).
- Ledger key: `42-4-the-status-pages-pin-their-snapshot-lines`.
- Ledger status at mint: `backlog`. Mode: in-PR (it may ride the fleet audit's landing PR, branch `egm-audit-2026-11`,
  or follow it).
- Deps: none.
- Epic surface: `marshal-policy.toml` `[epic_surfaces]."42"` (`src/shared/packages/pyforge-herald/**` covers the test).
- Flag: none — a fix (`spec-feature-flag-governance` Q1).

## Epic excerpt

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-herald CAP-59 (FR-11.1) and spec-pyforge-herald
CAP-60 (FR-12.1), on herald:AD-21; a fix, no new CAP
**Flag:** none — a fix (`spec-feature-flag-governance` Q1)

**Given** `main` at `03a7aff5d9`, where the guild page and the dossier tile render their capture-time lines and the
guild page its not-live sentence, but no built-site test asserts any of the three
**When** `test_one_generator.py`'s `built` fixture builds the tracked tree with both flags on
**Then** tests assert the guild page's one `<time>` holding `ci-status.json`'s `fetched_at`, its "nothing on this page
is live" sentence, and "Snapshot captured at F" once on the dossier page and once in its artifact build
**And** each mutation fails its test; `ci-status.json` is not refreshed here; the tests run under
`HERALD_DOCS_SITE_REQUIRED=1`; `pyforge-herald-test-built` exits 0

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e site docs-site-install` — expected: exit 0 (the built-site tests need it).
- `HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py -q` — expected: pass, the new tests run and none skips (AC1-AC3, AC5).
- `pixi run --frozen -e pyforge-herald pyforge-herald-test-built` — expected: exit 0 (AC6).
- `PYFORGE_STATUS_PAGES=1 PYFORGE_CI_SURFACES_TILE=1 pixi run --frozen -e site pages-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Mutations (each restored afterwards; AC4):**
- Drop the `<time …>` element from `docs-site/src/pages/status/ci/[...index].astro` — expected: the AC1 test fails.
- Drop "nothing on this page is live" from the same page's intro — expected: the AC2 test fails.
- Drop the `<p class="soft-note">Snapshot captured at …</p>` from the `ci_surfaces` case of
  `docs-site/src/lib/dossier-blocks.ts` — expected: the AC3 test fails on both outputs.

## Named, not fixed here

- **The CAP-59 / CAP-60 re-derive** (HER-K4's Spec half, folded into HER-K1's single herald re-derive): CAP-59's intent
  (one renderer, `pages.yml` as the deploy caller, `python -m pyforge.herald.pages_env`, the steward schema path
  `src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json`), the refresh rule that closes
  SPEC.md's open question, CAP-60's conditional Lane 1 link and `/status/ci/` clauses, the `fleet-status.json`
  envelope, and the PRD cascade to FR-11.1 and FR-12.1. Those are Spec, memlog and PRD edits.
- **Refreshing `ci-status.json`.** The operator's act at each pause and resume (ruling 2026-11-01).
- **The Lane 1 URL.** Operator row `DW-herald-42-1-1`.

## Auto Run Result

Status: backlog (minted 2026-11-01 by the EGM fleet audit, marshal Story 113.7; mode in-PR).

## Spec Change Log

- 2026-11-01: minted `backlog` under Epic 42 from the EGM audit's cluster HER-K4 (findings HER-M-Z4, HER-M-D4,
  HER-M-C4, HER-M-C5, HER-M-D6) and the operator's ruling of the same day: the snapshot stays an operator refresh, and
  the story pins only the rendered lines. The audit's brief proposed a new Epic 50 (Story 50.1); the story joins its
  done Epic 42 instead, under the operator's 2026-10-04 rule that a fix story goes into the epic it belongs to.

## Review Triage Log

- (none yet)
