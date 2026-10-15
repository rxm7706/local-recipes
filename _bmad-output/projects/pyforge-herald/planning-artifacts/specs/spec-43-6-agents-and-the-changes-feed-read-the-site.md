---
title: '43.6: Agents and the changes feed read the site'
type: 'feature'
created: '2026-10-14'
status: 'done'
flag:
  key: pyforge.herald.pages_one_generator        # Story 43.1's; shared across Epic 43 (one flag per CAP, Q6), not minted here
  provider: openfeature-file                     # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                  # v1 is global only
  fallback: 'no /llms.txt, /llms-full.txt, /facts.json, /changes/ or /status/runs/ is emitted and no input is opened'
  cleanup: retired by Story 43.7 with the Jinja path (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-42-1-the-fleet-board-and-guild-status-pages-render-at-build.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-43-1-astro-renders-the-dossier-from-dossier-yml.md
  - docs-site/astro.config.mjs
  - docs-site/package.json
  - docs-site/src/content.config.ts
  - presentations/pyforge-herald/facts.yaml
  - docs/reference/library-llms-full.md
  - docs/reference/bmad-estate-llms-full.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The site serves people and nothing else. The repository hand-maintains `*-llms-full.md` catalogues
(`docs/reference/library-llms-full.md`, `bmad-estate-llms-full.md`) for agents, but the published site has no
`/llms.txt`; the deck facts (`presentations/<slug>/facts.yaml`) are readable only in git; nothing published says what
landed on `main` or what a run cost. The repository has zero version-shaped tags among 731, so "since the last release"
has no anchor yet. Herald's Moments 2 to 4 (progress, success, notice) have no public surface.

**Approach:** three machine surfaces at the root, a changes page with a feed, and the runs page, each a build-time
render of tracked files or a Guild-step input.

- **`/llms.txt` and `/llms-full.txt`.** `starlight-llms-txt` (or an equivalent Astro integration that emits both)
  over the shelf and the herald pages: `/llms.txt` lists every shelf and herald page with its URL; `/llms-full.txt`
  holds their text.
- **`/facts.json`.** `docs-site/src/pages/facts.json.ts` emits the union of `presentations/*/facts.yaml` as one JSON
  document, one object per deck family keyed by slug (14 `facts.yaml` files on 2026-10-14; the ten published
  families among them).
- **`/changes/` and `/changes/rss.xml`.** `docs-site/src/pages/changes/index.astro` and `rss.xml.ts` (`@astrojs/rss`)
  over a `changes.json` build input written by a Guild step of steward's workflow (Story 102.2): the merge subjects to
  `main` in the last 30 days, each with its date, station and subject, until a CalVer tag exists. The page lists them
  newest first; the feed is RSS 2.0 with the same items.
- **`/status/runs/`.** `docs-site/src/pages/status/runs/index.astro` over two inputs the same Guild step writes:
  `marshal-status.json` (`marshal status --format json`; one row per loop home) and `herald-progress.json`
  (`herald progress --json`; the latest progress record per station). The page names its snapshot time and links the
  live view on Lane 1, as Story 42.1's board does.
- **Absence.** With an input missing the page says so in one line and the build exits 0: these are snapshots, and a
  run before the Guild step has written them is a normal build, not a broken one (unlike Story 42.1's board, whose
  input the workflow always writes; here the operator rules which inputs the schedule carries).
- **Fixtures.** A `changes.json` with five merges renders five items on the page and five in the feed; fixtures for the
  two status inputs render one row per loop home and one record per station.
- **The flag.** With `pyforge.herald.pages_one_generator` off none of these pages or files is emitted and no input is
  opened.

Ledger key: `43-6-agents-and-the-changes-feed-read-the-site`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / 43.1, 42.1, steward 102.2 (the Guild steps that write `changes.json`,
`marshal-status.json` and `herald-progress.json` into the build input).

### Living CAP citations

- **`spec-pyforge-herald` CAP-61** (FR-12.5): the agent surface, the changes feed, the runs page. On CAP-11 (Moment 2:
  progress — shipped, cost, unblocked) and CAP-13 (Moment 3/4: success and the record of what landed), and AD-23
  (every other station's contribution is data the generator reads at build).
- **`pyforge-steward:CAP-168`** (Story 102.2): the Guild steps and the three inputs. **`pyforge-marshal`**'s
  `marshal status --format json` and herald's own `herald progress --json` are read as their JSON, never imported.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M3 ("`/llms.txt`, `/llms-full.txt` and
  `/facts.json` exist ... `/status/runs/` ... and `/changes/` (a 30-day merge-subject window with RSS until a CalVer tag
  exists) land"); design-thinking § *Target information architecture*, rows Runs & progress, Changes and Agents;
  `brainstorm-intent.md` § *Target site map*, IA6 and IA8.

## Acceptance Criteria

- **AC1 — The agent files.** Given the flag on, When the site builds, Then `llms.txt` at the artifact root lists every
  shelf page and every herald page with its URL under the configured base, and `llms-full.txt` holds their text; a test
  counts the shelf pages in `docs/map.yaml` plus the herald pages and finds the same count of entries.
- **AC2 — `facts.json`.** `facts.json` at the root parses as JSON and holds one object per `presentations/*/facts.yaml`,
  keyed by the `deck` slug, each carrying that file's `facts`.
- **AC3 — The changes page.** Given a fixture `changes.json` with five merges, Then `changes/index.html` lists five
  items newest first, each with its date, station and subject.
- **AC4 — The feed.** `changes/rss.xml` parses as XML with `<rss version="2.0">`, one `<channel>` and the same five
  items in the same order, each with `<title>`, `<link>` and `<pubDate>`.
- **AC5 — The runs page.** Given fixture `marshal-status.json` and `herald-progress.json`, Then `status/runs/index.html`
  shows one row per loop home from the first and the latest progress record per station from the second, names each
  snapshot time and links Lane 1 `/console/`.
- **AC6 — Absence.** Given any one of the three inputs missing, Then the build exits 0 and the page that reads it
  carries one line saying the input is absent; given all three missing, all three pages say so and the build exits 0.
- **AC7 — Flag off.** Given the flag off, Then no `llms.txt`, `llms-full.txt`, `facts.json`, `changes/` or
  `status/runs/` exists in the artifact and no input is opened.
- **AC8 — The gates.** `pixi run --frozen -e site pages-check` exits 0 in both flag states and with the inputs absent;
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` is green.

## Boundaries & Constraints

**Always:**
- Read the three inputs as data from the build input directory; call no `gh`, `git log`, `marshal` or `herald` CLI
  from the `site` env (the Guild step runs them).
- Nothing on these pages is live (AD-21, the placement rule); each status page names its snapshot time and links Lane 1
  with a plain navigation link.
- Render only tracked files and Guild-step JSON; no Tier-3 path, Lane 1 data or warden finding reaches Pages.
- Keep every page and endpoint under `docs-site/src/` (AD-23); an integration is a `package.json` dependency with the
  lock refreshed.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not read `_bmad-output/projects/*/implementation-artifacts/` or `~/.bmad-loops/` from the build; the runs page
  shows what `marshal status --format json` published, nothing more.
- Do not replace the hand-maintained `*-llms-full.md` catalogues (`scribe catalog` owns them); `/llms-full.txt` is the
  published site's text, not a second catalogue.
- Do not load a third-party origin (AD-21); the feed's links are the artifact's own.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| five merges | fixture `changes.json` | five items on the page and in the feed, newest first | exit 0 |
| no merges in the window | `[]` | the page says no merges in the last 30 days; an empty channel | exit 0 |
| `changes.json` absent | no input | one line on the page saying so; no feed items | exit 0 |
| malformed input | not JSON | — | build exit 1, names the file |
| runs page | fixture inputs | one row per loop home, one record per station, snapshot times | exit 0 |
| `facts.json` | 14 `facts.yaml` | 14 objects keyed by slug | exit 0 |
| a `facts.yaml` without `deck` | fixture | — | build exit 1, names the file |
| flag off | any | none of the files or pages emitted | exit 0 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (FR-12.5), minted 2026-10-14; works with
  `pyforge-steward:CAP-168`.
- Architecture: AD-23 (adopted 2026-10-14) on AD-21 amended 2026-10-14 (the placement rule; `/changes/` a new prefix).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M3.
- Epic: Epic 43, Story 43.6.
- Ledger key: `43-6-agents-and-the-changes-feed-read-the-site`.
- Ledger status at mint: `backlog`.
- Deps: Stories 43.1 and 42.1 (station-local: the generator path and the `/status/` prefix with its board); steward
  Story 102.2 (the Guild steps that write the three inputs). The story builds and tests on fixtures before 102.2
  writes them; absence is a normal build. Named here and in `epics.md`, never as a `blocked` row. `marshal factory
  dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."43"`.
- Flag: `pyforge.herald.pages_one_generator` (shared with 43.1; `feature-flag-governance:CAP-1`, Q6).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 43.1, 42.1, steward 102.2 (the Guild steps that write `changes.json`, `marshal-status.json` and `herald-progress.json` into the build input) • **FR/AD:** spec-pyforge-herald CAP-61 (FR-12.5), on CAP-11 (progress), CAP-13 (success) and AD-23
**Flag:** `pyforge.herald.pages_one_generator` (shared with 43.1)

**Given** the repo hand-maintains `*-llms-full.md` catalogues, has zero version-shaped tags among 731, and publishes
nothing about what landed or what a run cost
**When** the site builds with the flag on and the three inputs present
**Then** `/llms.txt` lists every shelf and herald page with its URL and `/llms-full.txt` holds their text;
`/facts.json` is valid JSON holding one object per deck family; `/changes/` lists the input's merges newest first with
date, station and subject and `/changes/rss.xml` validates as RSS 2.0 with the same items; `/status/runs/` shows one
row per loop home from `marshal-status.json` and the latest progress record per station from `herald-progress.json`,
each page naming its snapshot time
**And** with an input missing the page says so in one line and the build exits 0; a fixture with five merges renders
five items; `pages-check` and `pyforge-herald-test` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_agent_surface_and_changes.py -q` — expected: pass (AC1–AC6).
- `pixi run --frozen -e site pages-check` with the flag on (inputs present, then absent) and with it off — expected: exit 0 each time (AC7, AC8).
- `python -c "import json; json.load(open('docs-site/build/site/facts.json'))"` and `python -c "import xml.etree.ElementTree as E; r=E.parse('docs-site/build/site/changes/rss.xml').getroot(); assert r.tag=='rss' and r.get('version')=='2.0'"` after a flag-on build — expected: exit 0 (AC2, AC4).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Remove one merge from the fixture — expected: AC3's and AC4's tests count four.
- Delete `marshal-status.json` from the build input — expected: the runs page carries the one-line absence and the build exits 0 (AC6).
- Drop `deck` from a fixture `facts.yaml` — expected: the build exits 1 naming the file.

## Verification run (2026-10-15)

- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_agent_surface_and_changes.py -q`
  — exit 0, 22 passed (AC1–AC7: the model through node, four Astro builds into scratch directories, and the
  assembler's checks); 36 passed after the independent review (five Astro builds; see the Spec Change Log).
- `pixi run --frozen -e site pages-check` — exit 0 in four states: both flags off; `PYFORGE_PAGES_ONE_GENERATOR=1
  PYFORGE_STATUS_PAGES=1` with the 42.1 fleet fixture and the three 43.6 fixtures in `docsite/content/` (all removed
  afterwards); both on with the three inputs absent (each page carries its one-line absence, the feed an empty
  channel); the one-generator flag on with the status flag off (no `status/` path).
- The `facts.json` / `rss.xml` checks of the Commands list are the built-site tests (AC2, AC4): `facts.json` parses
  with 14 decks, `rss.xml` is `<rss version="2.0">` with one channel and five items.
- Mutations, each restored: one merge removed from the fixture — the AC3, AC4 and feed tests fail (3 failed);
  `deck` removed from `presentations/deckcraft/facts.yaml` — the flag-on Astro build exits 1 with
  `BuildInputShapeError: presentations/deckcraft/facts.yaml: no deck slug`; a missing `marshal-status.json` is the
  `one-missing` and `none` builds of AC6.
- Gates as briefed (lighter gates, operator ruling 2026-10-15): the herald suite, `lint-types` and `pages-check`;
  the memlog reconcile, the scoped stamps, `detectors-ci` and `pr-preflight` are the coordinating session's.
- `pixi run --frozen -e site docs-site-validate` — exit 0 (run with the first build and again after the review).

## Named, not fixed here

- **The Guild steps** that write `changes.json` (the 30-day `git log --first-parent` window on `main`),
  `marshal-status.json` and `herald-progress.json`, and the schedule that refreshes them: steward Story 102.2
  (`pyforge-steward:CAP-168`). Herald names the input paths and their minimum keys.
- **The CalVer tag** that would anchor "since the last release" (zero version-shaped tags among 731 today): an operator
  act, not this story's; the 30-day window stands until one exists.
- **A Moment 3/4 notice archive** on Pages (`herald notice`): not in CAP-61; `/changes/` carries merges only.
- **The nav entries** for `/changes/` and `/status/runs/` in `docs/map.yaml` `sections:` (`pyforge-doctor:CAP-90`):
  Story 43.7 reads them from the registry; until then `site.yml`'s list carries them.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 43's Story 43.6 text, `spec-pyforge-herald` CAP-61, FR-12.5 and the Dream's
  2026-10-13 entry (M3). The three inputs' field names are read as steward's Guild steps write them (Story 102.2); the
  implementing session reads the landed output first and records the names on the Spec memlog.
- 2026-10-15 (implemented, in review; lane B of the one-PR Pages redesign chain). Where the landed code differs from
  the text above, the code is the contract and each difference is recorded here:
  - **No new npm dependency (orchestrator ruling 2026-10-15).** `/llms.txt`, `/llms-full.txt` and `/changes/rss.xml`
    are hand-written Astro endpoints over `docs-site/src/lib/agent-surface.ts`, the "equivalent" the Approach allows,
    not `starlight-llms-txt` and `@astrojs/rss`; `package.json` and the lockfile are unchanged. The feed is RSS 2.0
    built and escaped there (`rssXml`, `changesFeed`).
  - **The routes are dynamic so the flag can emit nothing.** A static route always writes its file, so the pages are
    `src/pages/[llms].txt.ts` (`llms`, `llms-full`), `src/pages/[facts].json.ts`, `src/pages/changes/[...index].astro`,
    `src/pages/changes/[feed].xml.ts` (`rss`) and `src/pages/status/runs/[...index].astro`, each with a
    `getStaticPaths` that lists nothing with `pyforge.herald.pages_one_generator` off (Story 43.2's pattern). The
    URLs are the spec's.
  - **The two modules.** `agent-surface.ts` is node builtins only (the tests import it with node's type stripping):
    the input shapes and their refusals, the feed, the facts union, the latest progress per station, the llms text,
    the Lane 1 rule. `agent-data.ts` reads the tracked files and the inputs inside the build (`yaml`,
    `astro:content`).
  - **AC1's herald pages are `docs/map.yaml`'s `herald` section** (Overview, Dossier, Infographics, Decks), the nav
    registry (`pyforge-doctor:CAP-90`); the shelf pages are the map's `pages`. `/llms.txt` lists 68 + 4 page entries on
    2026-10-15 under `## Docs` and `## Herald`, then a `## Data` section (`facts.json`, `/changes/`, the fleet board
    and `/status/runs/` with the status flag on, `llms-full.txt`). `/llms-full.txt` carries each page's text: a shelf
    page's markdown body, the site blurb for the overview, the dossier's prose (Story 43.1's collection, flattened),
    and a pointer line for the gallery and the decks, whose own pages are Jinja-rendered on this lane after the Astro
    build. At the lane merge, Story 43.2's `loadHeraldPages()` (`docs-site/src/loaders/herald-pages-loader.ts`)
    can list the infographic and family pages and their text the same way; that is a merge task, not this story's.
    The hand-maintained `docs/reference/*-llms-full.md` catalogues are untouched (they publish as two shelf pages).
  - **`/facts.json`** is an object keyed by deck slug (14 on 2026-10-15), each value the file's `deck`, `persona`,
    `derived_at`, `tree`, `facts` and its `source` path. A file with no `deck`, a `facts` that is not a list, or a
    second file for one deck fails the build naming the files.
  - **The inputs.** No Guild step writes them yet: steward 102.2 landed without them and no steward story names them,
    so they are steward deferred-work row `DW-steward-43-6-1` (orchestrator ruling), with the shapes below. They are
    read from `docsite/content/` (gitignored beside Story 42.1's `fleet-status.json`; `PAGES_BUILD_INPUTS_DIR`
    overrides it for the tests). `changes.json` is `{generated_at, window_days, merges: [{date, station, subject,
    sha}]}` or the bare merges list (the matrix's `[]`), listed newest first by `date`. `marshal-status.json` is
    marshal's `--format json` envelope (`data.homes`) with a top-level `generated_at` the step adds (the envelope
    carries no time); only `slug`, `branch`, `state`, `current_story`, `elapsed_seconds`, `budget_consumed` and
    `budget_consumed_usd` are read, so the escalation artifact, failed-patch and unpushed-work fields (Tier-3 paths)
    never reach Pages. `herald-progress.json` is `{generated_at, records}`, a JSON list, or the NDJSON `herald progress
    --json` prints; the page shows the latest record per station by `date` then `updated_at`. A snapshot time the
    input does not give reads "not recorded". 43.7, which retires `docsite/`, must move `INPUTS_DIR_REL`.
  - **`/status/runs/` needs both flags.** `/status/` is `pyforge.herald.status_pages`'s prefix, and `pages-check`
    refuses any `status/` path with that flag off, so the runs page is emitted only with both flags on; AC7 holds for
    the one-generator flag (off, no 43.6 file or page). With both on, Astro writes `status/runs/` first and the
    assembler lets the herald build add the board and the guild page beside it (`_astro_runs_only`, as `herald/`
    takes the Astro dossier).
  - **AC5's Lane 1 link** follows Story 42.1's re-review rule: linked only once `site.yml`'s `lane1.href` is an
    absolute URL (`lane1Link`, the TypeScript twin of `status_pages.lane1_link`); with `/console/` today the page
    carries no Lane 1 link. The page links the fleet board and the guild status page instead.
  - **`pages-check`** (`docsite/tools/assemble_pages.py`, `_check_agent_surface`) requires the five files with the
    one-generator flag on (and `status/runs/index.html` with the status flag on too) and refuses any of them, or a
    `changes/` path, with it off. `/changes/` is a Starlight page, so it carries the shared menu and passes the shelf
    body check (its one link, `rss.xml`, resolves).
  - **No nav entry** for `/changes/` or `/status/runs/` (Named, not fixed here: 43.7's `docs/map.yaml` sections).
    `/llms.txt` links both.
  - **Files outside the spec's list**, each forced by the story: `docsite/tools/assemble_pages.py` (the mount and the
    AC7 check), `.gitignore` (the three inputs), `docs-site/README.md`, the steward deferred-work ledger, and herald's
    `marshal-policy.toml` (`.gitignore` and the steward ledger join Epic 43's surface). The tests are
    `tests/meta/test_agent_surface_and_changes.py` and three fixtures under `tests/fixtures/`.
- 2026-10-15 (the independent review, `review-43-6`, verdict FAIL on six should-fix findings; resolved here; where
  this entry and an earlier one disagree, this one holds):
  - **One progress record is one record (F1).** `herald progress --json` prints one JSON object per line, so a store
    holding one record prints one valid JSON object. `parseHeraldProgress` reads an object with a `station` and no
    `records` as `[value]`. Test: the one-line case in
    `test_progress_keeps_the_latest_record_per_station_in_every_input_shape`.
  - **The feed cannot publish malformed (F2).** `parseChanges` refuses a `station` or `subject` holding a character
    XML 1.0 forbids (C0 controls but tab, newline and carriage return; U+FFFE, U+FFFF), naming the file and the merge.
    `pages-check` (`_check_agent_documents`) now parses `changes/rss.xml` as XML (an RSS 2.0 document with one
    channel) and `facts.json` as a JSON object with the flag on, so a broken surface reds instead of publishing
    green. Tests: three control-character cases in `test_a_malformed_changes_input_names_the_file`,
    `test_a_date_only_merge_and_whitespace_controls_still_make_a_well_formed_feed`,
    `test_pages_check_parses_the_feed_and_facts_json` (four cases).
  - **"No input is opened" is tested (AC7, F3).** The flag-off build reads malformed copies of all three inputs, so a
    module-scope read would fail it; proven by a mutation (a module-scope `changesInput()` in the feed route reds
    `test_ac7_the_surfaces_follow_the_flag`'s off case).
  - **The runs page joins the shelf link walk (F4).** `_iter_shelf_pages` takes `status/runs/index.html` (a Starlight
    page with a markdown body), so its `../` and `../ci/` links, and the Lane 1 link once it is absolute, are judged.
    Test: `test_the_runs_page_joins_the_shelf_link_walk`.
  - **The Guild-step contract keeps the deploy skip (F5).** `DW-steward-43-6-1` now says `changes.json`'s
    `generated_at` is HEAD's committer time (`%cI`) and its 30-day window is anchored on that commit date, as the fleet
    input's is; that the two runs-page inputs are live snapshots, so the runs page defeats the scheduled build's
    deploy skip by design (the steward story decides); and that a single NDJSON line is one record.
  - **The AC1 enrichment's owner is herald Story 43.7 (F6; coordinator ruling 2026-10-15).** After the lane merge,
    listing each infographic and deck-family page, with its text, in `/llms.txt` and `/llms-full.txt` through Story
    43.2's `loadHeraldPages()` (`docs-site/src/loaders/herald-pages-loader.ts`) is 43.7's: the coordinator carries it
    into 43.7's brief.
  - **Nits.** A merge `date` is `YYYY-MM-DD` or an ISO date-time with an offset (an offset-less one would be read in
    the build host's zone), `sha` a 7-40 hex id and unique (duplicates gave duplicate anchors and guids); stations sort
    in code-unit order, not by locale; the unused `countPageEntries` is gone; AC1's test asserts each Docs URL is a
    page the build wrote (no longer recomputing the route); a present `[]` merge list has its own build
    (`test_an_empty_merge_list_says_so_and_the_feed_is_an_empty_channel`); `/llms.txt`'s Changes entry reads the
    input's `window_days`; `docs-site-validate` is recorded in the Verification run. Not done here, for the lane merge:
    one `PYFORGE_PAGES_ONE_GENERATOR` reader (`=== '1'` in 43.1's files, `1|true|yes` here and in lane A's loader),
    the review's N8 and M5. Not done: an `<atom:link rel="self">` in the channel (optional, N3) and rewriting
    `llms-full.txt`'s raw relative markdown links (cosmetic, N9).
- 2026-10-15 (the lane-B → lane-A merge, onto herald 43.2-43.4):
  - **The `status/` mount (review M1).** 43.3 rewrote `assemble()`'s collision loop to `existing.exists() and mount not
    in astro_owned` (`herald/` and `dashboard/` with the flag on). 43.6's exemption sits inside it: `status/` may
    pre-exist only when `one_generator and _astro_runs_only(...)`, so a build with both flags on does not exit
    "collision at status/". `check()` keeps `_check_agent_surface` (and its `_check_agent_documents`) beside 43.3's
    and 43.4's checks (review M2).
  - **One flag reader (review M5 and N8).** `docs-site/src/lib/flags.ts` is the docs-site's one reader of
    `PYFORGE_PAGES_ONE_GENERATOR` and `PYFORGE_STATUS_PAGES`: `1`, `true` or `yes` (trimmed, any case) read on, the
    rule `docsite/tools/pages_one_generator.py` and `status_pages.py` apply. 43.2's loader and 43.6's
    `agent-surface.ts` re-export it, and 43.1's `content.config.ts`, `dossier-loader.ts` and
    `pages/herald/dossier/index.astro` (which tested `=== '1'`) call it, so a `true` the assembler passes through no
    longer leaves the dossier collection undefined while `/llms.txt` reads it. Tests:
    `test_one_flag_reader_accepts_the_python_sides_values`, `test_only_the_flag_reader_reads_the_flag_environment`
    (no other docs-site file reads either variable), `test_a_true_spelled_flag_builds_every_surface` (an Astro build
    with `PYFORGE_PAGES_ONE_GENERATOR=true`).
  - **Coexistence.** 43.6's routes (`[llms].txt.ts`, `[facts].json.ts`, `changes/`, `status/runs/`) build beside
    43.2-43.4's `herald/` routes, `populate-public.ts` and the herald font/theme layout; `/changes/` and
    `/status/runs/` carry no CSP meta (43.3's `_check_csp` judges `herald/` only), which herald 43.7 owns.
