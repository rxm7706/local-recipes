---
title: '42.1: The fleet board and guild status pages render at build'
type: 'feature'
created: '2026-10-14'
status: 'in-review'
flag:
  key: pyforge.herald.status_pages               # new; minted by this story
  provider: openfeature-file                     # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                  # v1 is global only
  fallback: 'no /status/ page renders, the fleet-status input is not opened, the menus carry no Status entry, and no other page of the artifact changes'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-39-1-the-dossier-tile-shows-every-ci-surface-that-is-not-live.md
  - docsite/build.py
  - docsite/content/site.yml
  - docsite/content/ci-status.json
  - docsite/tools/ci_surfaces_tile.py
  - docsite/tools/export_ci_surfaces_tile_env.py
  - docsite/tools/assemble_pages.py
  - docsite/templates/shell_page.html.j2
  - src/shared/packages/pyforge-herald/src/pyforge/herald/ci_surfaces_tile.py
  - src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_tile_flag_states.py
  - src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_import_boundary.py
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py
  - scripts/fleet_scan.py
  - scripts/fleet_picture.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - docs/governance/flag-inventory/pyforge-herald.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The holistic view the operator asked for on 2026-10-13 (one Pages site that shows PyForge, the BMAD
layer, the stations and the guild to operators, users and developers) exists today only in a terminal
(`scripts/fleet_picture.py`, `marshal watch`) and on Lane 1. The Pages artifact says nothing about the fleet's
progress or the guild's CI state beyond CAP-59's dossier tile. MyBMAD (`bmad-code-org/bmad-method-ui`) cannot run on
Pages (the placement rule, AD-21 amended 2026-10-14); its Pages twin is a build-time board over the eight tracked
ledgers. On 2026-10-14 those ledgers hold 1,433 stories, 1,410 done.

**Approach:** two pages under a new `/status/` prefix, both build-time snapshots of JSON that already exists, following
the shape CAP-59 established: herald renders what a Guild step of steward's workflow hands the build, imports nothing of
steward's and calls no `gh`.

- **The fleet board, `/status/`.** Rendered from `docsite/content/fleet-status.json`, a gitignored build input written
  by a Guild step of steward's deploy workflow (steward Story 102.2) from `sprint-ledger-query --format json`. The page
  shows one row per station (eight on 2026-10-14): epics, done/total, in progress, backlog, blocked, and a bar whose
  width is the integer percentage of done over total. Below the rows an attention block lists each `blocked` and
  `backlog` key (the ATTENTION block `fleet_picture.py` prints). The page names the snapshot time and carries one
  "live view on Lane 1" link to `/console/`. The counts agree with `fleet_scan.parse_sprint_status` (FR-12.1). The
  board reads `stations` (a list) and, per station, `done` and `total`; the remaining counts and the blocked and
  backlog keys are read under the names steward's JSON gives them (Story 102.2's output), and herald's fixture mirrors
  that output. This is the fleet board of the design preview the operator approved on 2026-10-14 (the fleet board:
  eight station rows with bars, an attention block, a snapshot line; the home: four doors Docs / Overview / Status /
  Decks).
- **The guild status page, `/status/ci/`.** Every row of CAP-59's committed snapshot `docsite/content/ci-status.json`
  — live rows included — with id, verdict, switch, `paused_since`, `review_by`, owner and detail, in the order CAP-59's
  tile uses (`drift`, `stuck`, `overdue`, `paused`, `paused-manually`, `opt-in-off`, `retired`, an unknown verdict
  after them, then `live`, by id within a verdict). The same stdlib function that validates and orders the tile
  (`docsite/tools/ci_surfaces_tile.py`) serves the page, so there is one reading of the snapshot. The page names the
  snapshot's `fetched_at` and links Lane 1.
- **The shape check.** With the flag on, `pages-check` exits 1 naming the file when `fleet-status.json` lacks
  `stations`, when `stations` is not a list, or when a station lacks `done` or `total` (naming the station's index
  and, where it has one, its name). Extra keys are ignored. A missing input with the flag on exits 1 naming the path,
  as CAP-59's snapshot does; the workflow writes the input before every build (Story 102.2), so the case is a
  misconfigured run, not a normal one.
- **The menu.** `docsite/content/site.yml`'s `nav` list gains a `status` entry, so CAP-58's two menus (the docs top
  menu, the Herald sidebar group, herald's own top menu) gain Status with no other edit. The entry renders only with
  the flag on; with it off the menus are as today, so "no other page changes" holds. The `/status/` prefix is
  herald's: `assemble_pages.py` mounts it beside `/herald/`, under the collision rule (AD-21 rule 1).
- **The flag.** `pyforge.herald.status_pages` lands in `src/platform/config/flags.json` (`defaultVariant` off, metadata
  owner `herald`, story this key) and in `flag-overlays.json` (dev on, staging and production off). Herald's package
  reads it through `pyforge.core.flags.read_boolean` in a module beside `pyforge/herald/ci_surfaces_tile.py`; a
  Guild-env export step (the `export_ci_surfaces_tile_env.py` pattern) hands the `site` build the resolved value, and
  the `site` env gains no pyforge dependency. The render takes the flag state as an argument so the two-state test
  drives both values. The workflow step that runs the export is steward's file; this story names the variable and the
  script, never edits `pages.yml`.
- **Two templates**, one per page, in `docsite/templates/`, rendered by `docsite/build.py`, so the Jinja path owns
  the pages until Epic 43 moves them onto the one generator.

Ledger key: `42-1-the-fleet-board-and-guild-status-pages-render-at-build`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / steward 102.2 (the Guild step that writes `fleet-status.json` into the build input).

### Living CAP citations

- **`spec-pyforge-herald` CAP-60** (FR-12.1): the two pages, the input, the shape check, the flag. Extends CAP-59 (the
  `ci-status.json` snapshot and its tile, read once more) and CAP-58 (the shared menu gains Status); on AD-21 amended
  2026-10-14 (the placement rule: static, public, build-time → Pages; nothing on these pages is live).
- **`pyforge-steward:CAP-168`** (Epic 102, Story 102.2): the workflow, its Guild step and the input it writes. Read as
  data, never imported.
- **canopy:AD-11** (one flag tree); `feature-flag-governance:CAP-1` (the flag rule), `feature-flag-governance:CAP-4`
  (the two-state test).
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 (the Pages deployment, redesigned) entry, M2 and
  the placement rule; design-thinking § *Target information architecture*, rows Fleet board and Guild status;
  `brainstorm-intent.md` rulings 1 and 3 of 2026-10-13; the design preview the operator approved on 2026-10-14.

## Acceptance Criteria

- **AC1 — One row per station.** Given a fixture `fleet-status.json` with eight stations carrying the 2026-10-14
  counts, flag on, When the site builds, Then `status/index.html` holds one row per station with its epics, done/total,
  in progress, backlog and blocked counts, and bars whose widths are 99, 100, 100, 99, 98, 100, 95, 100 for atlas,
  doctor, herald, marshal, mason, scribe, steward, warden.
- **AC2 — The attention block.** Given the fixture, Then the page lists every `blocked` and every `backlog` key the
  input carries, each once, and no `done` key.
- **AC3 — Snapshot time and Lane 1.** Given any valid input, Then `status/index.html` names the snapshot time and
  carries exactly one link to `/console/` labelled as the live view.
- **AC4 — The guild page.** Given CAP-59's fixture snapshot with one row per verdict plus an unknown verdict, Then
  `status/ci/index.html` lists every row (the `live` row included) with id, verdict, switch, `paused_since`,
  `review_by`, owner and detail, in the order AC1 of Story 39.1 states with `live` last, and names `fetched_at`.
- **AC5 — Shape refusals.** Given, flag on, an input missing `stations`; one whose `stations` is not a list; one with a
  station missing `done`; one missing `total`; one that is not JSON; and no input at all, When `pages-check` runs, Then
  each exits 1 naming the file, and the station cases name the station's index. Extra keys change nothing.
- **AC6 — The menu.** Given the flag on, Then every docs page and every herald shell page renders the shared menu with
  a Status link that resolves to `status/index.html`, and the docs root's Herald sidebar group links it; `pages-check`'s
  menu check passes with the seven-link list. Given the flag off, the menus are the six links of Story 40.1.
- **AC7 — Flag off.** Given the flag off and any input (valid, malformed or absent), When the site builds, Then no
  `status/` path exists in the artifact, the input is not opened, and every other file of the built artifact is
  identical to a build without this story's templates.
- **AC8 — The boundary.** An import-boundary test finds no `pyforge.steward` import and no `gh` subprocess call in
  herald's package, `docsite/build.py` or `docsite/tools/`.
- **AC9 — Two states.** `src/shared/packages/pyforge-herald/tests/unit/test_status_pages_flag_states.py` runs the
  render with `pyforge.testing_kit.flags.flag_states("pyforge.herald.status_pages")`: on, the fixture renders both
  pages (AC1, AC4); off, nothing renders (AC7).
- **AC10 — The gates.** `pixi run --frozen -e site pages-check` exits 0 on the story's tree in both flag states;
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` and `pixi run --frozen -e pyforge-guild flag-gate-check`
  are green.

## Boundaries & Constraints

**Always:**
- Herald reads steward only as data: the `fleet-status.json` a Guild step writes and the committed `ci-status.json`.
  The verdicts and counts are steward's; herald renders them and re-derives nothing.
- Nothing on either page is live (AD-21, the placement rule). Each page names its snapshot time and links the live
  view on Lane 1 with a plain navigation link; no fetch, script or iframe reaches another origin.
- The flag read goes through `pyforge.core.flags.read_boolean` in herald's package, never a station-local parser, and
  the `site` env gains no pyforge dependency.
- One nav list (`site.yml`); the Status entry is conditional on the flag, so an off build changes no menu.
- Every Spec `spec-surface-check` names is reconciled through its memlog and stamped scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not import `pyforge.steward`, call `gh`, run `sprint-ledger-query` or read another station's ledger from herald
  code or the Pages build; the Guild step does that, in steward's workflow.
- Do not edit `pages.yml` or `dashboard.yml`, any job's `if:` line, `docs/governance/ci-surfaces.yaml` or steward's
  ci-status schema.
- Do not render Tier-3 data, Lane 1 data or warden findings on Pages.
- Do not add a herald CLI verb, a portal page or an MCP tool for this; do not add a second flag file or an
  environment-variable flag provider.
- Do not hand-edit the snapshot, `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| eight stations | the 2026-10-14 fixture, flag on | eight rows, bar widths 99/100/100/99/98/100/95/100 | exit 0 |
| a station with `total: 0` | fixture row | bar width 0, counts shown | exit 0 |
| no blocked or backlog keys | fixture | an attention block saying nothing needs attention | exit 0 |
| guild page, every verdict | CAP-59's fixture | one line per row, `live` last | exit 0 |
| extra keys | a new envelope key and a new station key | ignored | exit 0 |
| no `stations` | envelope without it | — | `pages-check` exit 1, names the file |
| station without `total` | station 3 | — | exit 1, names the file and index 3 |
| input absent | flag on | — | exit 1, names the path |
| flag off | any input or none | no `status/` path, input not opened, six-link menus | exit 0 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-60 (FR-12.1), minted 2026-10-14; works with
  `pyforge-steward:CAP-168`.
- Architecture: AD-21 amended 2026-10-14 (the placement rule, the duct's owner; see the spine's § Currency
  reconciliation — 2026-10-14 (later)).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M2.
- Epic: Epic 42, Story 42.1.
- Ledger key: `42-1-the-fleet-board-and-guild-status-pages-render-at-build`.
- Ledger status at mint: `backlog`.
- Deps: steward Story 102.2 (the Guild step that writes `fleet-status.json`). The story builds and tests on a fixture
  before 102.2 lands; the production flag stays off until the step writes the input. Marshal's `Deps:` parser is
  station-local, so the cross-station dependency is named here and in `epics.md`, never as a `blocked` row.
  `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."42"`.
- Flag: `pyforge.herald.status_pages` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** steward 102.2 (the Guild step that writes `fleet-status.json` into the build input) • **FR/AD:** spec-pyforge-herald CAP-60 (FR-12.1), extending CAP-59 (the `ci-status.json` snapshot and its tile) and CAP-58 (the shared menu), on AD-21 amended
**Flag:** `pyforge.herald.status_pages` (new; minted by this story; tree default off, dev on through the overlay)

**Given** eight tracked `sprint-status-ledger.yaml` files (1,433 stories, 1,410 done on 2026-10-14),
`sprint-ledger-query --format json` (steward) that reads them, and CAP-59's committed `ci-status.json` snapshot
**When** the site builds with `pyforge.herald.status_pages` on and a `fleet-status.json` input present
**Then** `status/index.html` shows one row per station (epics, done/total, in progress, backlog, blocked, a bar whose
width is done over total), an attention block listing each `blocked` and `backlog` key, the snapshot time and a link to
Lane 1 `/console/`; `status/ci/index.html` lists every row of the snapshot with id, verdict, switch, `paused_since`,
`review_by`, owner and detail, ordered as CAP-59's tile orders them; both pages carry the shared top menu, which gains
Status
**And** `pages-check` exits 1 on an input missing `stations` or a station missing `done` or `total`, naming the file;
with the flag off no `/status/` page renders and no other page changes; a fixture with the 2026-10-14 counts renders
the bar widths 99, 100, 100, 99, 98, 100, 95, 100 for atlas, doctor, herald, marshal, mason, scribe, steward, warden;
an import-boundary test finds no `pyforge.steward` import in herald or docsite code; `pyforge-herald-test` is green
with the flag test running both states

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/unit/test_status_pages_flag_states.py -q` — expected: pass (AC1–AC5, AC7, AC9).
- `pixi run --frozen -e site pages-check` in both flag states — expected: exit 0 (AC6, AC10).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0 (the new key has a reader under `src/`).
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0, `docs/governance/flag-inventory/pyforge-herald.md` regenerated.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped stamps (`spec-pyforge-herald`; the flag tree's co-governor as the detector names it).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Drop `total` from one fixture station — expected: `pages-check` exits 1 naming the file and the index.
- Remove the Status entry from `site.yml` with the flag on — expected: the menu test and `pages-check`'s menu check fail.
- Render the board with the flag off — expected: AC7's test finds no `status/` path.

**Operator, after landing:**
- Once steward Story 102.2 writes `fleet-status.json` in the deploy workflow, turn `pyforge.herald.status_pages` on and
  see `/status/` show the eight stations and `/status/ci/` the guild's surfaces, each naming its snapshot time.

## Verification run (2026-10-15)

- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/unit/test_status_pages_flag_states.py -q`
  — exit 0, 51 passed (AC1–AC9; the two-state test runs `flag_states("pyforge.herald.status_pages")`).
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — exit 0, 1979 passed, 5 skipped (the `test_42_1_*`
  artifact tests in `tests/meta/test_pages_artifact.py` build the real herald site with the flag on and off).
- `pixi run --frozen -e site pages-check` — exit 0 with the flag off (no input); exit 0 with
  `PYFORGE_STATUS_PAGES=1` and the fixture copied to `docsite/content/fleet-status.json` (the docs root, every herald
  page and both status pages carry the seven-link menu with Status).
- Mutations, each restored: `total` dropped from station 3 → `pages-check` exit 1
  `docsite/content/fleet-status.json: station 3 (pyforge-marshal) missing total`; no input with the flag on → exit 1
  `...fleet-status.json: fleet-status input missing`; the Status entry removed from `site.yml` with the flag on →
  five story tests fail and `pages-check` exit 1 `...the shared menu has no entry linking status/index.html`;
  the board rendered with the flag off → the AC9 off case and the three AC7 cases fail.
- A flag-off `docsite/build.py` run on this tree and on `d7e52c11f3` (`git archive`) — `diff -r` exit 0.
- `pixi run --frozen -e site docs-site-validate` — exit 0. `pixi run --frozen -e pyforge-guild flag-gate-check` — exit 0.
  `pixi run --frozen -e pyforge-guild flag-inventory` — exit 0 (`pyforge-herald.md` regenerated; CAP-58, CAP-59 and
  CAP-60 now name the key). `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
- The flag tree's readers: `src/shared/packages/pyforge-core/tests/unit/test_flags.py` (162 passed) and
  `src/platform/tests/test_openfeature_file_flags.py` with the policy and chart suites (186 passed);
  `pixi run --frozen -e pyforge-guild platform-ci-local -- --test` — exit 0.
- Not run here: the memlog reconcile, the scoped stamps, `detectors-ci` and `pr-preflight` (the coordinating session
  runs them once for the branch).

## Named, not fixed here

- **The Guild step and the workflow** that write `fleet-status.json` (and the schedule that refreshes it every six
  hours with the no-op skip): steward Story 102.2 (`pyforge-steward:CAP-168`). Herald names the input path and the
  export variable; steward owns `pages.yml`.
- **`/status/runs/`** (marshal runs and herald progress): Story 43.6.
- **The Astro render** of these pages, and the nav moving from `site.yml` to `docs/map.yaml` `sections:`: Epic 43
  (Stories 43.1, 43.7; `pyforge-doctor:CAP-90`).
- **`steward estate status` and the bmad-estate catalog versions** the design-thinking IA lists for `/status/ci/`: not
  in CAP-60; a later entry on the Dream if wanted.
- **The home page's four doors** (Docs, Overview, Status, Decks) from the approved preview: Story 43.2 and 43.7 (the
  home is generated from `map.yaml`; design-thinking IA row Home, M3).

## Spec Change Log

- 2026-10-14: specced at mint from Epic 42's Story 42.1 text, `spec-pyforge-herald` CAP-60, FR-12.1, the Dream's
  2026-10-13 entry and the design preview the operator approved on 2026-10-14. The input's required keys (`stations`,
  `done`, `total`) are the ones the acceptance names; every other field is read as steward's JSON names it, and the
  implementing session reads Story 102.2's landed output first and records the field names on the Spec memlog.
- 2026-10-15 (implemented, in review; one branch with the rest of the Pages redesign chain, operator 2026-10-15).
  Where the landed code differs from the text above, the code is the contract and each difference is recorded here:
  - **No step writes `fleet-status.json` yet.** Steward 102.2 landed (`done`) without a Guild step that writes the
    input: its `pages.yml` exports the host, CI-tile and one-generator env and runs `pages-check`, nothing more, and
    no steward spec (102.2–102.5) names the step. The board is therefore built and tested on a fixture, and the
    production flag stays off until a steward story adds the step and the `export_status_pages_env.py` line to
    `pages.yml` (this story names both and edits neither). The field names below are read from
    `sprint-ledger-query --format json` as landed (`StationProgress`, `WorkPassportItem`), not from a 102.2 output.
  - **The input's shape** (documented in `docsite/tools/status_pages.py`): `generated_at` (the snapshot time,
    steward's envelope key), `stations` (a list; steward's `summary.stations` values) with `station`, `done`,
    `total` (steward's `total_stories`), `epics` (the count of steward's `epics` rows for the station),
    `in_progress`, `backlog`, `blocked`; and `stories` (steward's `stories` rows: `story_id`, `station`, `status`,
    `title`), whose `blocked` then `backlog` rows are the attention block, each `(station, story_id)` once.
    Required: `stations`, `done`, `total`. Optional and absent: a count reads `—`, the snapshot line says the time
    is not recorded, no `stories` means nothing needs attention. Present but unreadable (a non-integer `done` or
    `total`, a `stories` that is not a list of objects carrying `story_id` and `status`) is refused too, naming the
    file and the index: a loose read would draw a wrong bar or a false all-clear. Station indexes are 0-based, as
    CAP-59's row refusals are.
  - **The bar width** is the floored integer percentage (`done * 100 // total`, 0 when `total` is 0): rounding gives
    marshal 100, not AC1's 99. The fixture (`tests/fixtures/fleet-status-2026-10-14.json`) is the eight ledgers at
    `0627eb9077` (2026-10-14T01:56:19Z): 1,433 stories, 1,411 done by steward's counting (every non-`epic-` key);
    no 2026-10-14 tree gives both 1,410 done and steward's 95, so the fixture keeps AC1's widths.
  - **The Lane 1 link** is `site.yml` `lane1` (`href: /console/`, `label: Live view on Lane 1`), one plain link on
    each page. Lane 1 is the platform's host, not Pages, so `pages-check` never resolves that one href inside the
    artifact; a host that serves Lane 1 elsewhere sets an absolute URL there.
  - **The flag gate in the one nav list** is a `flag: pyforge.herald.status_pages` key on the Status entry, read by
    `status_pages.menu_entries` in `docsite/build.py`, `assemble_pages.py` and `sidebar_from_map.py` (an entry gated
    on any other flag is refused). Status sits after Decks, before the Kedro-Viz neighbour. With the flag on,
    `pages-check` also refuses a menu that has no entry linking `status/index.html`, so removing the entry from
    `site.yml` fails the gate rather than building consistently Status-less menus.
  - **The two pages' styles** live in each template (a `head_extra` block the shell gained, empty for every other
    page), so `site.css` and every other file are byte-identical with the flag off: a flag-off `docsite/build.py`
    run on this tree and on `d7e52c11f3` diffs to nothing.
  - **CAP-59's order** gained one tie-break: within an unknown verdict, rows sort by id (they kept input order);
    `ci_surfaces_tile.order_rows` serves both the tile (non-live) and the guild page (all rows, `live` last).
