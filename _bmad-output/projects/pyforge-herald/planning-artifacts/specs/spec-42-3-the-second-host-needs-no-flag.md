---
title: '42.3: The second host needs no flag'
type: 'feature'
created: '2026-10-14'
status: 'done'
flag-exempt: flag-infrastructure   # the story retires a flag, pyforge.herald.pages_second_host (spec-feature-flag-governance Q2)
retires-flag: pyforge.herald.pages_second_host   # read by the flag gate and the flag inventory (scripts/flag_gate_check.py RETIRES_FIELD)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-31-1-the-pages-artifact-builds-for-the-host-that-deploys-it.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-31-2-how-to-deploy-the-docs-site-to-github-enterprise-pages.md
  - docsite/tools/pages_second_host.py
  - docsite/tools/export_pages_host_env.py
  - docsite/tools/assemble_pages.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/pages_host.py
  - src/shared/packages/pyforge-herald/tests/unit/test_pages_host.py
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_second_host.py
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py
  - src/shared/packages/pyforge-core/tests/unit/test_flags.py
  - src/platform/tests/test_openfeature_file_flags.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - docs/governance/flag-inventory/pyforge-herald.md
  - docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - .github/workflows/dashboard.yml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-56 (Story 31.1) made the Pages build take the deploying host's site URL and base path from
`actions/configure-pages`, but only when `pyforge.herald.pages_second_host` is on. The read runs from the Guild env
(`docsite/tools/export_pages_host_env.py` → `pages_second_host.export_host_env_for_ci` →
`pyforge.herald.pages_host.pages_second_host_enabled` → `pyforge.core.flags.read_boolean`) in the workflow step
"Resolve Pages host env", and the GitHub Enterprise how-to tells the enterprise copy to edit `flags.json` to turn the
flag on (its step 4). The operator ruled on 2026-10-13 that `actions/configure-pages` is authoritative on every host:
the air-gapped host runs the same workflow as the public one with nothing to flip, and the flag, its reader and its
how-to step go.

**Approach:** the host inputs apply whenever `configure-pages` provides them; otherwise the public github.io URL.

- **`pages_second_host.py`, unconditional.** `resolve_from_process_environment` returns
  `combine_pages_host(PAGES_HOST_BASE_URL, PAGES_HOST_BASE_PATH)` whenever both variables are set and non-empty, and
  `public_site_url()` otherwise. `ENV_APPLY_HOST`, `second_host_enabled`, `resolve_build_site_url`'s
  `apply_second_host` argument and `export_host_env_for_ci` go. `combine_pages_host`, `public_site_url` and
  `site_origin` (the origin check's input) stay as they are.
- **The reader goes.** `docsite/tools/export_pages_host_env.py` is deleted. `pyforge/herald/pages_host.py` holds only
  the flag reader, so it is deleted with `tests/unit/test_pages_host.py`; `tests/meta/test_pages_second_host.py` loses
  its flag cases and keeps the combine, fallback and origin cases.
- **The flag goes.** `pyforge.herald.pages_second_host` leaves `src/platform/config/flags.json` and every environment of
  `flag-overlays.json`; `pixi run -e pyforge-guild flag-inventory` regenerates
  `docs/governance/flag-inventory/pyforge-herald.md`. The two tests that use the key as an example row
  (`src/shared/packages/pyforge-core/tests/unit/test_flags.py`, `src/platform/tests/test_openfeature_file_flags.py`)
  move to another herald key; they test the tree's reader, not this flag.
- **The how-to.** `docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md` loses step 4 ("Turn
  `pyforge.herald.pages_second_host` on for the enterprise copy") and every sentence that names the flag or
  `export_pages_host_env.py`; steps 1 to 3, 5 and 6 renumber and stand: Settings → Pages → GitHub Actions, the mirror,
  deploy, verify the origin.
- **Ordering.** Steward Story 102.5 removes the "Resolve Pages host env" step and feeds `SITE_URL` from the
  `configure-pages` outputs. Deleting `export_pages_host_env.py` while that step still runs it would break the deploy,
  so this story's PR opens after 102.5 is `done` on `main`; the dependency is named here and in `epics.md`, never as a
  `blocked` row.

Ledger key: `42-3-the-second-host-needs-no-flag`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / steward 102.5 (drops the host-env workflow step and feeds `SITE_URL` from
`configure-pages` outputs).

### Living CAP citations

- **`spec-pyforge-herald` CAP-60** (FR-12.3, amending FR-10.5 / CAP-56): `configure-pages` authoritative on every
  host; the flag, its reader and the how-to step retire. FR-10.5's zero-third-party-origin clause is unchanged. On
  AD-21 (one artifact, N hosts, the 2026-09-28 amendment: one build definition parameterized only by the deploying
  host's site URL and base path).
- **`pyforge-steward:CAP-168`** (Story 102.5): the workflow step and the `SITE_URL` feed. Herald never edits the
  workflow.
- **`spec-feature-flag-governance` Q2 and Q4**: `flag-exempt: flag-infrastructure` (the story retires a flag); the
  owning station files the removal story — this is it.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M2 ("the `pyforge.herald.pages_second_host`
  flag retires and `actions/configure-pages` is authoritative on every host"); `brainstorm-intent.md` § M2, Retired.

## Acceptance Criteria

- **AC1 — Both values set.** Given `PAGES_HOST_BASE_URL=https://pages.ghe.example` and
  `PAGES_HOST_BASE_PATH=/org/local-recipes` in the environment and no flag anywhere, When `pages-check` runs, Then every
  href in the built artifact resolves under `https://pages.ghe.example/org/local-recipes/`, no menu href carries a
  `/local-recipes/` literal from the public host, and CAP-56's origin check passes against that origin.
- **AC2 — The fallback.** Given neither variable, or only one of them, Then the build's `SITE_URL` is the public
  github.io URL (`public_site_url()`), as Story 27.2 built it.
- **AC3 — No flag read.** `grep -rn "pages_second_host\|PYFORGE_PAGES_APPLY_HOST\|read_boolean" docsite/` finds
  nothing; `src/shared/packages/pyforge-herald/src/pyforge/herald/pages_host.py` and
  `docsite/tools/export_pages_host_env.py` do not exist.
- **AC4 — The key is gone.** `python -c "import json,sys; d=json.load(open('src/platform/config/flags.json'));
  sys.exit('pyforge.herald.pages_second_host' in d['flags'])"` exits 0 (reading the tree's own layout for the key
  table); the same over every environment of `flag-overlays.json`; `docs/governance/flag-inventory/pyforge-herald.md`
  is regenerated and names no `pages_second_host`.
- **AC5 — No tracked reference outside the record.** `git grep -l pages_second_host -- . ':!_bmad-output' ':!docs/dreams'
  ':!archive' ':!scripts/.spec-surface-baseline.json'` prints nothing: code, tests, configuration, workflows, the
  how-to and the flag inventory are clean; the planning record (`SPEC.md`, the memlog, the story specs, the PRD, the
  epics) and the Dream keep the history.
- **AC6 — The how-to.** `grep -c "pages_second_host\|export_pages_host_env" docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md`
  prints 0; the page still has the Settings → Pages → GitHub Actions step, the mirror step, the deploy step and the
  origin verification, renumbered.
- **AC7 — The gates.** `pixi run --frozen -e pyforge-herald pyforge-herald-test`, `pixi run --frozen -e pyforge-guild
  flag-gate-check`, `pixi run --frozen -e site pages-check` (public and with AC1's environment) and
  `pixi run --frozen -e site docs-site-validate` exit 0; `pixi run --frozen -e pyforge-core pyforge-core-test` and the
  platform suite's flag tests pass with the example key moved.

## Boundaries & Constraints

**Always:**
- Keep one build definition, parameterized only by the deploying host's site URL and base path (AD-21 amended
  2026-09-28); keep `public_site_url()` as the fallback so the public site builds with no environment at all.
- Keep CAP-56's cross-origin check and its vendored-root exemptions unchanged; the origin it checks against is the
  resolved `SITE_URL`.
- Land after steward Story 102.5 is `done` on `main` (`git merge-base --is-ancestor` on its merge commit is the proof).
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped (`spec-pyforge-herald`;
  `spec-pyforge-core` as co-governor of `src/` and the flag tree's co-governor as the detector names them); the PR
  carries the `maintenance` label.

**Never:**
- Do not edit `pages.yml`, `dashboard.yml` or any workflow step; steward Story 102.5 owns the step removal.
- Do not add a second site-URL source (a repository variable read from herald code, a hardcoded enterprise URL) or a
  second artifact (AD-21).
- Do not leave a dead flag key in `flags.json` or an overlay "for safety"; Q4 says the owning station removes it.
- Do not change `combine_pages_host`'s normalization (the trailing-slash and duplicate-path rules Story 31.1 tested).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| enterprise host | both variables set | `SITE_URL=https://pages.ghe.example/org/local-recipes`; every href under it | exit 0 |
| root base path | `PAGES_HOST_BASE_PATH=/` | `SITE_URL` is the origin alone | exit 0 |
| base URL already carries the path | `base_url` ends in the base path | no duplicated segment (`combine_pages_host` as today) | exit 0 |
| only one variable | `PAGES_HOST_BASE_URL` alone | public github.io URL | exit 0 |
| no variables | local build | public github.io URL | exit 0 |
| a third-party origin on a page | planted | — | `pages-check` exit 1 (CAP-56) |
| the flag key still in `flags.json` | regression | — | AC4's check exits 1 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-60 (FR-12.3, amending FR-10.5 / CAP-56), minted 2026-10-14; works
  with `pyforge-steward:CAP-168`.
- Architecture: AD-21 (the 2026-09-28 amendment, one artifact N hosts, and the 2026-10-14 amendment, the duct's owner).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M2.
- Epic: Epic 42, Story 42.3.
- Ledger key: `42-3-the-second-host-needs-no-flag`.
- Ledger status at mint: `backlog`.
- Deps: steward Story 102.5 `done` on `main` before this story's PR opens (the step it removes runs the file this story
  deletes). Named here and in `epics.md`, never as a `blocked` row; the operator flips a `blocked` key, not a session.
  `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."42"`.
- Flag: none — `flag-exempt: flag-infrastructure` (`spec-feature-flag-governance` Q2); retires
  `pyforge.herald.pages_second_host`.

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** steward 102.5 (drops the host-env workflow step and feeds `SITE_URL` from `configure-pages` outputs) • **FR/AD:** spec-pyforge-herald CAP-60 (FR-12.3, amending FR-10.5 / CAP-56), on AD-21
**Flag:** none — `flag-exempt: flag-infrastructure` (`spec-feature-flag-governance` Q2): the story retires a flag

**Given** CAP-56's build reads `PAGES_HOST_BASE_URL` and `PAGES_HOST_BASE_PATH` only when
`pyforge.herald.pages_second_host` is on, through `export_pages_host_env.py` run from the Guild env, and the how-to
tells the enterprise copy to flip the flag in `flags.json`
**When** steward Story 102.5 has removed the host-env step and this story lands
**Then** `pages_second_host.py` combines the two `configure-pages` values into `SITE_URL` whenever both are set and
falls back to the public github.io URL otherwise, with no flag read; `pages_host.py`'s flag reader,
`export_pages_host_env.py` and the `pyforge.herald.pages_second_host` key in `flags.json` and `flag-overlays.json` are
gone and the flag inventory regenerates; the how-to has no flag step
**And** `pages-check` with `PAGES_HOST_BASE_URL=https://pages.ghe.example PAGES_HOST_BASE_PATH=/org/local-recipes`
builds every href under that base and CAP-56's origin check still passes; `grep -rn pages_second_host` over tracked
files finds nothing; `pyforge-herald-test` and `flag-gate-check` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `git merge-base --is-ancestor <steward 102.5 merge commit> origin/main; echo $?` — expected: 0 before the PR opens.
- `pixi run --frozen -e site pages-check` — expected: exit 0 (public host).
- `PAGES_HOST_BASE_URL=https://pages.ghe.example PAGES_HOST_BASE_PATH=/org/local-recipes pixi run --frozen -e site pages-check` — expected: exit 0, every href under that base (AC1).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0 (the how-to's links after the renumbering).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0, the herald inventory regenerated (AC4).
- `pixi run --frozen -e pyforge-core pyforge-core-test` and `pixi run --frozen -e pyforge-guild platform-ci-local -- --test` — expected: exit 0 (the example key moved, AC7).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and one scoped stamp per Spec the detector names.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Set only `PAGES_HOST_BASE_URL` — expected: the fallback test sees the public URL (AC2).
- Re-add the key to `flags.json` — expected: AC4's check exits 1.

## Named, not fixed here

- **The workflow step** ("Resolve Pages host env") and the `SITE_URL` feed from `configure-pages` outputs: steward
  Story 102.5 (`pyforge-steward:CAP-168`). The same step today also runs `export_ci_surfaces_tile_env.py` (Story 39.1)
  and, after Story 42.1, the status-pages export; what steward keeps of the step is steward's.
- **The release zip** for the air-gapped host (the same artifact as a release asset): steward Epic 102.
- **`spec-31-1`, `spec-31-2` and `spec-31-3`** keep the flag's history as the record of CAP-56 as built; they are not
  rewritten.
- **`SPEC.md`'s CAP-56 text** still names the flag; CAP-60 amends it on the memlog, and the Spec is re-derived by
  script, never hand-edited.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 42's Story 42.3 text, `spec-pyforge-herald` CAP-60, FR-12.3 and the Dream's
  2026-10-13 entry, against `pages_second_host.py`, `pages_host.py` and `export_pages_host_env.py` as they stand on
  2026-10-14. AC5's grep is scoped to code, tests, configuration, workflows and docs because the planning record and the
  Dream keep the flag's history by design.
- 2026-10-15 (built with steward 102.5 in one commit, lane B; status `in-review`). Where the landed code differs:
  - **The module is renamed.** AC3's `grep -rn "pages_second_host" docsite/` cannot pass while `assemble_pages.py`
    imports a module of that name, so `docsite/tools/pages_second_host.py` is now `docsite/tools/pages_site_url.py`
    (same functions: `combine_pages_host`, `public_site_url`, `site_origin`, `resolve_build_site_url` without
    `apply_second_host`, `resolve_from_process_environment` reading the two variables only). The test file keeps its
    name and spells the retired key in pieces. The Surface line in `epics.md` names the new path.
  - **The first flag retirement needed the gate to know about retirements.** With the key gone, `flag-gate-check`
    redded the `done` 31.1 spec (key not in the tree, its deleted test missing), and the regenerated inventory kept
    printing the key from 31.1's flag block (AC4, AC5). This spec now carries `retires-flag:
    pyforge.herald.pages_second_host`. `scripts/flag_gate_check.py` (`RETIRES_FIELD`) leaves a `done` spec whose key
    is declared retired *and* gone from the tree unjudged, and `scripts/flag_inventory.py` prints "none (retired by
    <story>)" instead of the key. A key still in the tree is judged as before. Tests are in
    `tests/scripts/test_flag_gate_check.py` and `test_flag_inventory.py`. This changes the flag governance mechanism
    (spec-feature-flag-governance Q4), so it needs that Spec's review.
  - **The example key.** `test_flags.py` (core) and `test_openfeature_file_flags.py` (platform) list every key the tree
    holds rather than using one as an example, so the key's rows are removed, not moved. The same lists lacked atlas
    30.2's `pyforge.atlas.vizro_static_boards` (red at `73ae4f1180`), which is now added.
  - **AC5 is checked by the spec's command, not by a test.** A herald test that ran `git grep` over the repo root
    would hand the root to code, and steward's station-tests trigger map would then have to fire herald's job on every
    path. AC3 and AC4 are tests.
  - **AC1's enterprise `pages-check` was red on base** on one absolute link to the public host in
    `docs/reference/github-workflows.md` (`<https://rxm7706.github.io/local-recipes/>`, the `pages.yml` row). The row
    now names the host in code and describes 102.5's behaviour.
- 2026-10-15 (the independent review, `review-42-3-102-5`; the 42.3 items are resolved here, where this entry and an
  earlier one disagree, this one holds):
  - **The blocker is not this story's any more.** The flag gate's and the flag inventory's retirement rule
    (`scripts/flag_gate_check.py`, `scripts/flag_inventory.py`, their tests, the `retires-flag:` field and
    `docs/reference/story-spec-flag-block.md`) moved to a new doctor story, built in its own worktree, by operator
    ruling 2026-10-15; the review's should-fix on that rule (a retired key whose reader lives) goes with it. This
    story's `retires-flag:` frontmatter stays as built until that story lands.
  - **A root-hosted site builds for its own origin (should-fix; AC2 and the matrix amended).** `configure-pages` gives
    `base_path: ""` for a site served at its host's root (a custom domain, a root-hosted Pages host), and the old
    "both values, else public" rule built such a host for the public github.io URL; `assemble_pages` then overwrote
    the workflow's correct `SITE_URL` with that. `pages_site_url.resolve_build_site_url` now decides on the base URL
    alone: with one, `combine_pages_host(base_url, base_path)`, which already maps an empty or `/` path to the origin;
    with none, `public_site_url()`. AC2 now reads: given no `PAGES_HOST_BASE_URL` (whatever the base path), the
    build's `SITE_URL` is the public github.io URL; given a base URL with an empty base path, it is that origin. The
    matrix rows "root base path" (`PAGES_HOST_BASE_PATH=""` or `/` → the origin alone) and "only one variable"
    (base URL alone → its origin; base path alone → the public URL) read the same. The `empty-path` case now expects
    `https://pages.ghe.example`, and `custom-domain-root`, `empty-url` and `url-only` cases join it
    (`test_the_base_url_alone_decides_and_an_empty_path_is_the_origin`). The how-to's § 5 sentence says the same.
  - **The test file is renamed and spells the key outright (nit; AC5 amended).** `tests/meta/test_pages_second_host.py`
    is now `tests/meta/test_pages_site_url.py`, after the module it tests; it is AC3's and AC4's absence test, so it
    names `pyforge.herald.pages_second_host` plainly instead of in pieces. AC5's command now excludes it by path, and
    uses git's long pathspec form, because the short form as written fails before searching (`git grep ...
    ':!_bmad-output'` exits 128, "Unimplemented pathspec magic '_'"): `git grep -l pages_second_host -- .
    ':(exclude)_bmad-output' ':(exclude)docs/dreams' ':(exclude)archive' ':(exclude)scripts/.spec-surface-baseline.json'
    ':(exclude)src/shared/packages/pyforge-herald/tests/meta/test_pages_site_url.py'` prints nothing (run 2026-10-15,
    exit 1, no output). The gate script's `*_second_host` comment is the doctor story's file.
  - **The how-to index (should-fix).** `docs/how-to/README.md` describes the page as "`configure-pages` host values +
    the `pages-site` release zip", not "Story 31.1 flag + `pages.yml`".
  - **The surfaces (nit).** `marshal-policy.toml`'s steward "102" surface names `docsite/tools/pages_site_url.py`, and
    herald's "42" comment names it too.
- 2026-10-15 (independent review, lane C): the gate and inventory change this story carried (`RETIRES_FIELD` in
  `scripts/flag_gate_check.py`, the retired cell in `scripts/flag_inventory.py` and their tests) is now owned by doctor
  Story 34.7, under `spec-feature-flag-governance` CAP-2's retirement path (operator ruling 2026-10-15). 34.7 adds the
  owner rule (only a story of the key's owning station retires it) and `flag-retired-still-read` (a reader left on a
  retired key reds). This spec's `retires-flag: pyforge.herald.pages_second_host` line stands: herald owns
  `pyforge.herald.*`, and no reader names the key.
- 2026-10-15 (the lane-B re-review, `rereview-laneb`, surface nit): herald's Epic 42 surface (`marshal-policy.toml`)
  now lists `src/platform/tests/test_openfeature_file_flags.py` and
  `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, the tree-wide flag pins 42.1 and this story edited;
  atlas's Epic 30 surface lists them too (30.2's key).
- 2026-11-01 (EGM fleet audit, marshal Story 113.7; append-only, no AC body edited, no status moved): `epics.md`
  Story 42.3's Then and And lines gain dated in-place notes, as its Surface line: `docs-site/scripts/pages.mts` now
  does what `pages_second_host.py` (renamed `pages_site_url.py`, retired with `docsite/` by Story 43.7) did, and the
  absence check is scoped by inclusion, `git grep -l pages_second_host -- src scripts docs-site .github docs/how-to
  docs/governance/flag-inventory pixi.toml ':(exclude)src/shared/packages/pyforge-herald/tests/meta/test_pages_site_url.py'
  ':(exclude)scripts/.spec-surface-baseline.json'` exiting 1 (verified at `03a7aff5d9`). AC5's body stays the dated
  record. EGM audit HER-D-R5 and HER-D-C4 (clusters HER-K2, HER-K7), residue
  `_bmad-output/projects/pyforge-herald/planning-artifacts/research/egm-audit-2026-11-01.md`.
