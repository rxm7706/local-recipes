---
title: '42.4: The status pages pin their snapshot lines'
type: 'fix'
created: '2026-11-01'
status: 'done'
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

Minted: backlog (minted 2026-11-01 by the EGM fleet audit, marshal Story 113.7; mode in-PR).

Status: done (implemented 2026-11-01 in the landing worktree, branch `egm-audit-2026-11`, and committed there in
`bd154aaa17`; the independent review of 2026-11-01 passed it, `in-review` -> `done`, in the Review Triage Log below).

**What changed.** Tests only; no generator edit (every pinned line renders as AC1-AC3 state, so the Change Log
carries no generator entry), `ci-status.json` untouched.

- `src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py`: a `_fetched_at()` helper reads F from
  `docs-site/src/content/ci-status.json` at test time (never a literal date), and two `needs_astro` tests over the
  module's `built` fixture (status pages and tile on, every input present, CI's variables):
  - `test_42_4_ac1_ac2_the_guild_page_names_its_capture_time_and_says_nothing_on_it_is_live` (AC1, AC2):
    `status/ci/index.html` holds `<time datetime="F">F</time>` exactly once, inside the one paragraph that reads
    "Snapshot captured", and "nothing on this page is live" exactly once.
  - `test_42_4_ac3_the_tile_names_its_capture_time_on_the_dossier_and_in_its_artifact_build` (AC3):
    `herald/dossier/index.html` and `herald/artifact/dossier.html` each hold "Snapshot captured at F" exactly once,
    asserted as one dict so a failure names both outputs.
  - The module docstring names Story 42.4.
- AC5: both tests carry the shared `needs_astro` decorator (Story 45.1), so without the install they skip naming
  `docs-site-install`, and under `HERALD_DOCS_SITE_REQUIRED=1` they fail instead. With the install they ran and passed.

**Commands (exit codes read from `$?`).** On this host `/tmp` is tmpfs, so Astro's `rename` into the pytest basetemp
fails with EXDEV. Every build run below used `TMPDIR=$HOME/.cache/pyforge-preflight-tmp/her424` (team memory: full
preflight needs TMPDIR off tmpfs). The first `-k 42_4` run, without that TMPDIR, errored in the fixture on EXDEV,
which is the machine and not the diff.

- `pixi run --frozen -e site docs-site-install`: exit 0.
- `HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py -q -k 42_4`:
  exit 0, 2 passed (none skipped).
- AC4 mutations, each restored byte-for-byte from a scratch copy (sha256 checked):
  - dropping the `<time ...>` element from `docs-site/src/pages/status/ci/[...index].astro`: exit 1, AC1/AC2 test
    fails on the `<time>` count.
  - dropping " A snapshot: nothing on this page is live." from the same page: exit 1, the AC1/AC2 test fails on
    `assert 0 == 1` for the sentence.
  - dropping `<p class="soft-note">Snapshot captured at ...</p>` from the `ci_surfaces` case of
    `docs-site/src/lib/dossier-blocks.ts`: exit 1, the AC3 test fails with both outputs at 0.
- `HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py -q`:
  exit 1, with 31 passed and 1 failed. The failure was
  `test_43_5_two_builds_two_days_runs_and_commits_apart_differ_only_in_the_built_from_line`: three
  `pagefind/` index files had different hashed names between its two builds, about 40 s apart. Parallel agents were
  editing other stations' sources in this worktree during that window, and the dossier measures live `src_lines`.
  The same test passed alone twice (exit 0), and a two-build diff of the same tree, run back to back, showed no
  difference. It also passed inside the full suite below. This change does not touch it.
- `HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald pyforge-herald-test-built` (it runs
  `docs-site-install`, then `pyforge-herald-test`): exit 0, 2190 passed and 5 skipped, then 5 passed.
- `PYFORGE_STATUS_PAGES=1 PYFORGE_CI_SURFACES_TILE=1 pixi run --frozen -e site pages-check`: exit 1, from the build
  input and not the diff. `docs-site/src/content/fleet-status.json` is a Guild-step input that only `pages.yml` writes
  (gitignored, absent locally), and the build refused with "fleet-status input missing". Re-run with
  `PAGES_BUILD_INPUTS_DIR` pointing at the herald fixtures the `built` fixture uses: exit 0, "passes".
- `ruff check` and `ruff format --check` on the changed file (the `pyforge-guild` env's ruff 0.17.0): exit 0 and 0.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0. mypy runs on `-p pyforge.herald` (`src/` only), so
  the test file is outside it.

**Memlog.** One surface-reconcile event appended to `spec-pyforge-herald/.memlog.md` naming
`src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py`. The orchestrator's landing step asked for it so
the governed path's move is reconciled. It is not the CAP-59/CAP-60 re-derive that § Boundaries reserves for the Spec,
and it changes no CAP's success promise, so no second event was written. No scoped stamp was run here; the session
owner does it.

## Spec Change Log

- 2026-11-01: minted `backlog` under Epic 42 from the EGM audit's cluster HER-K4 (findings HER-M-Z4, HER-M-D4,
  HER-M-C4, HER-M-C5, HER-M-D6) and the operator's ruling of the same day: the snapshot stays an operator refresh, and
  the story pins only the rendered lines. The audit's brief proposed a new Epic 50 (Story 50.1); the story joins its
  done Epic 42 instead, under the operator's 2026-10-04 rule that a fix story goes into the epic it belongs to.

## Review Triage Log

- 2026-11-01 (reviewer: independent session) — **PASS**; status moved `in-review` -> `done`. I judged the diff
  against this spec, not against the Auto Run Result. Evidence came from the landing worktree (branch
  `egm-audit-2026-11`), with `TMPDIR` off tmpfs. Every exit code was read from `$?`.
  - **Diff read.** `git diff HEAD` on the three reported files. The only code change is in
    `tests/meta/test_one_generator.py`: the `_fetched_at()` helper, two `needs_astro` tests and one docstring sentence.
    `git status` on `docs-site/` is clean, so the generator is unedited and `ci-status.json` is untouched. No
    `pyforge.steward` import was added, and no flag, task or dependency.
  - **AC1 and AC2 hold.** I read the built `status/ci/index.html`. It holds one
    `<time datetime="2026-10-14T12:09:30.983070+00:00">…</time>` inside `<p class="status-snapshot">Snapshot
    captured …`, and "nothing on this page is live" appears once. The test asserts the exact element once, inside
    the only "Snapshot captured" paragraph, with F read from `ci-status.json` at test time. No date literal is
    pinned.
  - **AC3 holds.** `herald/dossier/index.html` and `herald/artifact/dossier.html` each hold
    `<p class="soft-note">Snapshot captured at F</p>` once. The test asserts a count of 1 on both outputs.
  - **AC4 holds.** I ran the mutations myself, backed the files up to scratch and checked them with `sha256sum -c`
    afterwards. Both files were restored OK and `git status docs-site/` was clean.
    - With the `<time>` element dropped from `[...index].astro`, the `-k 42_4` run exited 1 and the AC1/AC2 test
      failed on the `<time>` count, 0 == 1.
    - With the not-live sentence dropped and the soft note dropped from `dossier-blocks.ts`, the run exited 1. The
      AC1/AC2 test failed on the sentence count, 0 == 1. The AC3 test failed with both outputs at 0.
  - **AC5 holds.** With the install present, `HERALD_DOCS_SITE_REQUIRED=1` and `-k 42_4` exited 0: 2 passed, none
    skipped. With node off `PATH` and the variable unset, the run exited 0 with 2 skipped. The skip reason names
    `pixi run -e site docs-site-install`. With node off `PATH` and the variable set, the run exited 1 with the
    "promises the install" message.
  - **AC6 holds for this diff.** `pyforge-herald-test-built` with `HERALD_DOCS_SITE_REQUIRED=1` (it runs
    `docs-site-install` then `pyforge-herald-test`) exited 0: 2190 passed, 5 skipped, then 5 passed. The full
    `test_one_generator.py` module exited 0 with 32 passed.
    - A first `pyforge-herald-test-built` run exited 1. Its one failure was
      `test_43_5_two_builds_two_days_runs_and_commits_apart_differ_only_in_the_built_from_line`: the two builds had
      different file keys.
    - That test passed alone (exit 0), passed in the module run, and passed in the rerun of the gate. This story's
      tests only read files, so they cannot change a build. The likely cause is other stations' agents editing live
      sources between the two builds, the same flake the implementer recorded.
  - **AC6 lint-types.** `pixi run --frozen -e pyforge-guild lint-types` exited 1. The only finding is in another
    station's uncommitted, in-flight edit: I001 in `pyforge-doctor/tests/unit/test_sources_pages_liveness.py`. The
    `HEAD` version of that file is ruff-clean (exit 0) and the worktree version is not (exit 1). Herald's own legs
    all pass:
    - `ruff`: ok.
    - `lint_types.py ruff-format`: exit 0, herald ok.
    - `lint_types.py mypy`: exit 0, herald ok.
    - `ruff check` and `ruff format --check` on the changed test file (ruff 0.17.0): 0 and 0.
  - **Verification `pages-check`.** Run exactly as written, with both flags on, it exits 1. The cause is
    "fleet-status input missing": `docs-site/src/content/fleet-status.json` is a gitignored Guild-step input that is
    absent locally, so this is not the diff. Re-run with `PAGES_BUILD_INPUTS_DIR` set to the herald fixtures the
    `built` fixture uses, it exits 0 ("passes").
    - Nit, not a failure: the spec's Verification line does not name that input precondition.
  - **Callers and regressions.** `_fetched_at` and the `test_42_4_*` names appear nowhere else in herald's tests.
    The read-only spec-surface verdict (`python -m pyforge.doctor.sources spec-surface`) exited 0.
  - **Boundary deviation, judged non-blocking.** § Boundaries says no memlog text is edited by this story, yet the
    implementer added one surface-reconcile event to `spec-pyforge-herald/.memlog.md`. It names the governed test
    path (`src/shared/packages/pyforge-herald/**` is in the Spec's `surface:`), and the frontmatter still has a
    single `updated:` key. AGENTS.md § Pre-PR item 5 requires that event for a governed file to move. It changes no
    CAP text, so the Boundary's stated purpose holds: the CAP-59/CAP-60 re-derive stays with the Spec.
  - **Failures:** none.
