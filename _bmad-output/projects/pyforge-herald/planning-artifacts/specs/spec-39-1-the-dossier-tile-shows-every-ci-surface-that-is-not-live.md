---
title: '39.1: The dossier tile shows every CI surface that is not live'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
baseline_revision: '8d0452077065cbbe805551804a1ad3fe8b3dba14'
flag:
  key: pyforge.herald.ci_surfaces_tile          # new; minted by this story
  provider: openfeature-file                    # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                 # v1 is global only
  fallback: 'the dossier renders exactly as it does today, with no CI surfaces tile, and the snapshot is not read'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md
  - docsite/README.md
  - docsite/build.py
  - docsite/content/dossier.yml
  - docsite/templates/blocks.html.j2
  - docsite/tools/pages_second_host.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/pages_host.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - .github/workflows/dashboard.yml
  - src/platform/config/flags.json
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Steward's CI pause control plane (`pyforge-steward:CAP-166`) now answers "which CI surfaces are off, since
when, until when" in one command, `pyforge steward ci status --json` (steward Story 99.3, landed 2026-10-13), but a
reader of the dossier still sees nothing about the pipeline that lands the cutover. Two container-build pauses, six
hand-disabled workflows and a Pages deploy stuck for six days (2026-10-06 to 2026-10-12) were visible nowhere a reader
looks (`docsite/content/dossier.yml` has no CI content; the plan's § 1.4).

**Approach:** One new dossier block, rendered from a committed copy of steward's JSON.

- **The snapshot.** `docsite/content/ci-status.json` is the stdout of `pixi run --frozen -e pyforge-guild pyforge
  steward ci status --json`, captured from an exit-0 run and committed as printed. Nobody edits it by hand. Its shape
  is steward's frozen envelope (`$id: urn:local-recipes:pyforge-steward:ci-status-schema`, additive changes only):
  `{fetched_at, repo, rate_limit: {core_limit, core_remaining}, rows: [...]}`, each row
  `{id, switch, declared_state, live_switch_value, paused_since, review_by, review_days_left, owner, last_green_run,
  verdict, detail?}`, where `verdict` is one of `live`, `paused`, `opt-in-off`, `paused-manually`, `retired`, `drift`,
  `stuck`, `overdue` (`ci.py` `VERDICTS`). Steward also emits synthetic rows with ids `unregistered:<NAME>` and
  `unregistered-workflow:<file>` (verdict `drift`, a `detail`, nulls elsewhere); the tile treats them like any row.
- **The tile.** A `ci_surfaces` block in the estate section (A→B, the control plane), after the A→B.4 block, renders
  its own heading (A→B.5, CI surfaces) and the snapshot's `fetched_at`. One line per row whose verdict is not `live`:
  id, verdict, switch, `paused_since`, `review_by` with steward's `review_days_left` read as days left (or days overdue
  when negative) at capture, owner, and `detail` when present. A null field prints as an em dash. Lines run `drift`,
  `stuck`, `overdue`, `paused`, `paused-manually`, `opt-in-off`, `retired`, by id within a verdict. A verdict outside
  that list still shows, after them, under its own name; it is never dropped and never read as live. When no row is
  non-live, one all-live line. One macro in `docsite/templates/blocks.html.j2`, so the site page and the artifact build
  render it alike (CAP-43, CAP-47); `docsite/README.md` counts fifteen block types and names the refresh command.
- **The shape check.** With the flag on, the build reads the snapshot and refuses it, so `site-check` exits 1 naming
  the file (and the row index and id where there is one), when the file is missing or not JSON, the envelope lacks
  `fetched_at` or `rows`, `rows` is not a list, or a row lacks `id` or `verdict`. Keys it does not use are ignored,
  since steward's schema grows only by addition. The row logic (validate, select, order) is a stdlib-only function
  that the herald suite can load by path, as `test_pages_second_host.py` loads `docsite/tools/pages_second_host.py`.
- **The flag.** `pyforge.herald.ci_surfaces_tile` lands in `src/platform/config/flags.json` (`defaultVariant` off,
  metadata owner `herald`, story this key) and in `flag-overlays.json` (dev on, staging and production off). Herald's
  package reads it through `pyforge.core.flags.read_boolean` in a small module beside `pyforge/herald/pages_host.py`;
  the flag gate counts only readers under `src/` or `scripts/`, so the read cannot live in `docsite/`. The `site`
  build learns the state the way CAP-56's host inputs reach it: a Guild-env step (the `export_pages_host_env.py`
  pattern) resolves it and hands the `site` build a value; the `site` env gains no pyforge dependency. With the flag
  off, the block renders nothing, the snapshot is not opened, and no other block changes. The render function takes
  the flag state as an argument, so the two-state test drives both values.
- **The workflows.** If `dashboard.yml` or `docsite-check.yml` must hand the flag to the build, the change is one step
  beside the existing `export_pages_host_env.py` call; no job's `if:` line changes (steward's ci-surface gate checker
  judges those, `pyforge-steward:CAP-166`).

Ledger key: `39-1-the-dossier-tile-shows-every-ci-surface-that-is-not-live`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / — (steward Story 99.3 is `done` on `main`, merge `7ec2ea85f3`).

### Living CAP citations

- **`spec-pyforge-herald` CAP-59** (FR-11.1): the tile, the snapshot, the shape check, the flag. Extends CAP-11
  (Moment 2: factory motion is visible); works with CAP-43 (the dossier YAML is the one source) and CAP-47 (the
  artifact build renders the same templates); AD-21 (one Pages artifact, one deploy caller; `/herald/` is docsite's).
- **`pyforge-steward:CAP-166`** (steward Epic 99, Story 99.3): the command, its frozen schema, its verdicts. Read, never
  imported.
- **canopy:AD-11** (one flag tree); `feature-flag-governance:CAP-1` (the flag rule), `feature-flag-governance:CAP-4`
  (the two-state test).
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-12 and 2026-10-14 (ci surfaces on the dossier)
  entries; the plan's § 4.4 and § 6 (row herald 39.1); operator rulings Q1–Q8 of 2026-10-12; the operator's order of
  2026-10-13 to mint the readers once 99.3 landed.

## Acceptance Criteria

- **AC1 — Lines per verdict.** Given a fixture snapshot with one row per steward verdict plus one row with an unknown
  verdict, flag on, When the dossier builds, Then the built dossier page and the artifact build each carry the tile
  with exactly one line per non-`live` row, in the order `drift`, `stuck`, `overdue`, `paused`, `paused-manually`,
  `opt-in-off`, `retired`, then the unknown verdict, each line showing id, verdict, switch, `paused_since`,
  `review_by`, days left or overdue, owner and (where present) `detail`, and no line for the `live` row.
- **AC2 — All live.** Given a fixture snapshot whose rows are all `live`, flag on, Then the tile shows the one all-live
  line and the snapshot's `fetched_at`.
- **AC3 — Capture time.** Given any valid snapshot, flag on, Then the tile names its `fetched_at`.
- **AC4 — Shape refusals.** Given, flag on, a snapshot missing `fetched_at`; one missing `rows`; one whose `rows` is not
  a list; one with a row missing `id`; one with a row missing `verdict`; one that is not JSON; and no snapshot at all,
  When `site-check` runs, Then each exits 1 and names the file, and the row case names the row's index (and id when it
  has one). Extra keys in the envelope and in a row change nothing.
- **AC5 — Flag off.** Given the flag off and any snapshot (valid, malformed or absent), When the dossier builds, Then no
  tile renders, the snapshot is not opened, and every other block of the built dossier is identical to a build without
  the block.
- **AC6 — The contract.** A test reads `src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json`
  as JSON data and fails when its row `verdict` enum differs from the tile's known verdicts (the seven non-live ones
  plus `live`), and when a fixture row carries a key the schema's row does not define.
- **AC7 — The boundary.** An import-boundary test finds no `pyforge.steward` import, and no `gh` subprocess call, in
  herald's package, `docsite/build.py` or `docsite/tools/`.
- **AC8 — Two states.** `src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_tile_flag_states.py` runs the
  render with `pyforge.testing_kit.flags.flag_states("pyforge.herald.ci_surfaces_tile")`: on, a fixture snapshot
  renders the tile (AC1); off, it renders nothing (AC5).
- **AC9 — The gates.** `pixi run --frozen -e site site-check` and `pixi run --frozen -e site pages-check` exit 0 on the
  story's tree; `pixi run --frozen -e pyforge-herald pyforge-herald-test` and `flag-gate-check` are green.

## Boundaries & Constraints

**Always:**
- Herald reads steward only through `ci status --json` stdout, as the committed snapshot. Steward's schema file may be
  read as data by a test (AC6); nothing else of steward's is read.
- The verdict is steward's. The tile renders it and never re-derives `drift`, `stuck` or `overdue`, and never
  recomputes `review_days_left` against the build date.
- The flag read goes through `pyforge.core.flags.read_boolean` in herald's package, never a station-local parser of the
  tree, and the `site` env gains no pyforge dependency.
- One block type and one macro, used by the site and the artifact build.
- The snapshot is captured only from an exit-0 run of the steward command. A refusal (exit 3: flag off,
  unauthenticated `gh`, or a 0/60 rate limit) prints no JSON, and a partial read exits non-zero; neither is committed.
- Every Spec `spec-surface-check` names is reconciled through its memlog and stamped scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not import `pyforge.steward`, call `gh`, or add a token or a secret to any herald code or Pages workflow step.
- Do not edit `docs/governance/ci-surfaces.yaml`, the ci-status schema, steward's `ci` duty, or any job's `if:` line.
- Do not add a herald CLI verb, a portal page or an MCP tool for this.
- Do not add a second deploy caller, a second flag file, or a flag read from an environment variable as a provider
  (the Guild step hands the build a resolved value, as CAP-56's does).
- Do not hand-edit the snapshot, `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| every verdict | one row each, plus `live`, flag on | seven lines in order, none for `live` | exit 0 |
| unknown verdict | a row with `verdict: quarantined` | its line after `retired`, under its own name | exit 0 |
| all live | every row `live` | one all-live line | exit 0 |
| synthetic drift | `unregistered:PAUSE_X`, nulls, `detail` | a `drift` line with the detail, nulls as em dashes | exit 0 |
| overdue | `review_days_left: -3` | "3 days overdue" (steward's number, at capture) | exit 0 |
| due today | `review_days_left: 0` | "due today", not overdue | exit 0 |
| extra keys | a new envelope key and a new row key | ignored | exit 0 |
| no `fetched_at` | envelope without it | — | `site-check` exit 1, names the file |
| row without `verdict` | row 4, id `dashboard.deploy` | — | exit 1, names the file, index 4 and the id |
| no snapshot | file absent, flag on | — | exit 1, names the path |
| flag off | any snapshot or none | no tile, file not opened | exit 0 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-59 (FR-11.1), minted 2026-10-14; reads `pyforge-steward:CAP-166`.
- Architecture: AD-21 (unamended; see the spine's § Currency reconciliation — 2026-10-14).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-12 (ci surfaces on the dossier) seed and the
  2026-10-14 (ci surfaces on the dossier, specced) entry.
- Epic: Epic 39, Story 39.1.
- Ledger key: `39-1-the-dossier-tile-shows-every-ci-surface-that-is-not-live`.
- Ledger status at mint: `backlog`.
- Deps: none inside herald; steward Story 99.3 is `done` on `main` (no blocked gate). `marshal factory dispatch` stamps
  `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."39"`.
- Flag: `pyforge.herald.ci_surfaces_tile` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-herald CAP-59 (FR-11.1), extending CAP-11, on CAP-43, CAP-47 and AD-21; reads `pyforge-steward:CAP-166` • flag: `pyforge.herald.ci_surfaces_tile`

**Given** steward Story 99.3's `pyforge steward ci status --json` and a dossier whose estate section says nothing about
the pipeline that lands it
**When** the dossier builds with the flag on, from a committed snapshot of that output at `docsite/content/ci-status.json`
**Then** `site-check` exits 0 and the built dossier holds one tile line per non-`live` surface, in the stated order,
with an all-live line when there is none and the snapshot's `fetched_at` named
**And** a malformed or (flag on) missing snapshot makes `site-check` exit 1 naming it; with the flag off nothing
changes; `pages-check` exits 0; the contract and import-boundary tests pass; `pyforge-herald-test` is green with the
flag test run in both states

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; it runs
  `src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_tile_flag_states.py`, which runs the key
  `pyforge.herald.ci_surfaces_tile` in both states with `pyforge.testing_kit.flags.flag_states`, and the contract and
  import-boundary tests, AC6 and AC7).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_tile_flag_states.py -q` — expected: pass (AC1–AC5, AC8).
- `pixi run --frozen -e site site-check` and `pixi run --frozen -e site pages-check` — expected: exit 0 (AC9).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped
  stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Operator, after landing (an authenticated read, never a session's write):**
- With `gh` signed in and `pyforge.steward.ci_pause_control` on for the run:
  `pixi run --frozen -e pyforge-guild pyforge steward ci status --json > docsite/content/ci-status.json` — expected:
  exit 0; commit the file through a PR, then turn `pyforge.herald.ci_surfaces_tile` on and see the tile list the two
  live container-build pauses.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 39's Story 39.1 text, `spec-pyforge-herald` CAP-59 and the landed steward code
  (`ci.py`, `ci-status-schema.json`). The data route (a committed snapshot, not a build-time call) is the 2026-10-14
  decision on the Spec's memlog. The implementing session reads the landed steward command first and follows it where
  it differs from the shape quoted here.
