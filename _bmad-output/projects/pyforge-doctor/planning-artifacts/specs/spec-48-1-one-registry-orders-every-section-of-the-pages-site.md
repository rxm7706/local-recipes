---
title: '48.1: One registry orders every section of the Pages site'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
baseline_revision: 'e134549afcbdcc5b55b35f291464ac60d6685243'
flag-exempt: docs-only   # a documentation registry and its hygiene check: registry rows, schema fields and MAP rows are documentation data, and the two hygiene classes are checks that judge; neither half is a runtime capability a flag could gate without recreating a silent-off surface (spec-feature-flag-governance Q2; coordinator assignment, memlog 2026-10-14)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/map.yaml
  - docs/MAP.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/docs-map-schema.json
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_map_hygiene.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py
  - scripts/docs_map_render.py
  - docs-site/scripts/sidebar_from_map.py
  - docsite/content/site.yml
  - docsite/tools/assemble_pages.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the Pages site is ordered by two registries and drawn by one generator. `docs/map.yaml` orders the four
Diátaxis quadrants (68 pages at `e134549afc`: 3 tutorials, 32 how-to, 22 reference, 11 explanation), and herald's
`docsite/content/site.yml` orders the herald menu (a five-entry `nav`: docs, index, dossier, gallery, decks) and the
Kedro-Viz `neighbours` entry; `docs-site/scripts/sidebar_from_map.py` reads both into the Starlight sidebar and the shared
top menu (herald Story 40.1). `docs/MAP.md` § *Outside this map* still says the dossier publishes at the root, which herald
Story 27.2 moved under `/herald/` on 2026-10-08, and its table names neither `docsite/` nor `docs-site/`; of the 28 tracked
top-level directories, the table names four by first segment (`docs`, `_bmad-output`, `.cursor`, `src`). The 2026-10-13
rulings (`brainstorm-intent.md`) make `docs/map.yaml` the one registry of the site, doctor's, and every renderer herald's.

**Approach:** an additive `sections:` list in the registry, two warn-first hygiene classes, and the MAP table corrected.

- **The schema.** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/docs-map-schema.json`
  (`$id: urn:local-recipes:pyforge-doctor:docs-map-schema`) has `additionalProperties: false` at the top level, so today
  `load_map_yaml` refuses any key beside `schema_version` and `pages`. It gains an optional `sections` property: an array of
  `section` objects, each requiring `key` (a slug, `^[a-z][a-z0-9-]*$`), `label` (string), `href` (string), `owner`
  (string, a station slug) and `order` (integer), with an optional `entries` array of `{key, label, href}` objects; both
  objects keep `additionalProperties: false`, and `schema_version` stays 1 (every existing `docs/map.yaml` validates
  unchanged). Descriptions on each property say what the field is for; this is where the shape is documented for a
  machine reader.
- **The registry rows at mint.** `docs/map.yaml` gains:
  `herald` (label `Herald`, href `herald/`, owner `herald`, order 10, entries Overview `herald/`, Dossier
  `herald/dossier/`, Infographics `herald/infographics/`, Decks `herald/decks/`) and `pipelines` (label `Kedro-Viz`, href
  `dashboard/kedro-viz/`, owner `atlas`, order 30). `status`, `dashboards` and `changes` are not added: a row is added when
  its section publishes, by the station that publishes it, through the same surface reconcile that adds a `pages:` row
  (the Publish roots rule). The docs shelf is the site root and is not a row; its menu entry is first by CAP-58 and the
  renderer supplies it. `href` is a site-root-relative directory path so the Starlight build can prefix whichever base
  path the host gives it, the rule `_site_root_path` in `sidebar_from_map.py` already applies to `site.yml` hrefs.
- **The `sections` class.** `docs_map_hygiene.py` loads `docs/map.yaml` through `docs_currency.load_map_yaml` (the one
  loader; the schema has already refused a missing field) and yields one WARN per defect it finds across the list: a `key`
  or `order` that repeats, an `href` that starts with `/`, contains `://` or `..`, or does not end in `/`, in a section or
  in one of its entries; each message names the section key (and the entry key). A map that `load_map_yaml` refuses is
  one WARN naming the error, as `docs-currency` already reports it, never a FAIL and never a crash.
- **The `unnamed-top-level` class.** The source lists the tracked top-level directories of the target (`git ls-files -z`
  through `cli_bridge.run_git`, first path segments of entries that contain a `/`) and yields one WARN naming each
  directory that is none of: `docs` (the map's own root); a dot-directory (harness and CI configuration: `.github`,
  `.claude`, `.cursor`, `.gemini`, `.vscode`, `.junie`, `.ci_support`, `.azure-pipelines`, `.steward`, `.scripts`,
  `.bmad-loop`, `.marshal`, `.pixi` today); one of the closed allow-list `_INFRASTRUCTURE_DIRS = frozenset({"_bmad",
  "_bmad-output", "_skf-learn", "archive", "conf", "evals", "helm", "recipes", "scripts", "src", "tests"})`; or the first
  segment of a backticked path in the `## Outside this map` table of `docs/MAP.md`. When `git ls-files` cannot be read
  the class yields one WARN naming the cause. Measured at `e134549afc` the unnamed set is exactly `docsite`, `docs-site`
  and `presentations`, so the MAP rows below make the class quiet on the story's tree.
- **The MAP.** `docs/MAP.md` is edited by hand outside the `docs-map:registry:begin/end` markers (`scripts/docs_map_render.py`
  renders only the Page registry section and leaves the rest byte-for-byte). The Publish roots row reads today's layout:
  one Pages artifact assembled at `docs-site/build/site/` — the Starlight shelf at `/`, herald's dossier site under
  `/herald/`, Kedro-Viz under `/dashboard/kedro-viz/` copied from `docs/dashboard/kedro-viz/` — deployed by
  `dashboard.yml`, the one `deploy-pages` caller. Three rows are added: `docsite/` (herald's Jinja dossier and
  infographic site, built by `docsite/build.py`; dissolves into `docs-site/` under `pyforge-herald:CAP-61` Story 43.7),
  `docs-site/` (the Starlight shelf and the Pages assembler `docsite/tools/assemble_pages.py`'s output root; never
  renamed) and `presentations/` (herald's deck sources and `facts.yaml`, published under `/herald/`; not documentation).
  A short hand-authored *Sections* paragraph above the Page registry names the `sections:` list, its five fields and the
  Publish roots rule, so a human reader finds the shape without opening the schema.
- **Nothing herald's moves.** `docs-site/scripts/sidebar_from_map.py`, `docsite/content/site.yml` and every file under
  `docsite/` and `docs-site/` are untouched; herald's Story 43.7 (`pyforge-herald:CAP-61`) makes the generator read
  `sections:` and retires `site.yml`'s nav, and its Deps already name this story.

Ledger key: `48-1-one-registry-orders-every-section-of-the-pages-site`.
Type / Effort / Deps: feature / M / none (herald's Story 43.7 depends on this story, not the reverse).

### Living CAP citations

- **`spec-pyforge-doctor` CAP-90** (FR-23): this story builds the whole capability. Extends CAP-84 (`docs/map.yaml` is
  the registry, `docs/MAP.md` its render) and CAP-83 (the map is enforced within its scope) without reopening either.
- **AD-14** (new with this chain): the registry orders, the renderer renders; Doctor owns the registry and its hygiene,
  never a renderer. **AD-5**: the git index read goes through `cli_bridge.run_git`. **AD-3**: no new `Source` member,
  two classes on the existing `docs-map-hygiene` source. **AD-2**: WARN only.
- **`pyforge-herald:CAP-61`** (Story 43.7): the renderer side of AD-14's boundary; reads the list this story defines.
  **`pyforge-herald:CAP-58`** (Story 40.1): the one menu this list will feed; the Docs entry stays first.
- **Flag:** `flag-exempt: docs-only` (coordinator assignment, memlog 2026-10-14). The registry rows, schema fields and
  MAP rows are documentation data; the two hygiene classes are checks that judge, which the roster's `detector-or-gate`
  reason covers equally; a story names one value, and no `pyforge.doctor.*` key is minted.
- **Origin.** `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-13 entry (one registry orders the whole
  site, and a stale site tells on itself); the herald Dream's 2026-10-13 lead entry (M1 hygiene, M3 one nav); the
  intent doc's rulings and hygiene list; the design-thinking doc's *Target information architecture* (one nav from
  `map.yaml`: sections docs, herald, status, pipelines, dashboards, changes).

## Acceptance Criteria

- **AC1 — The schema accepts and refuses.** `load_map_yaml` accepts a fixture map carrying the two mint rows (and one
  with an empty `sections: []`, and one with no `sections` key at all) and raises `jsonschema.ValidationError` for a
  section missing any one of `key`, `label`, `href`, `owner`, `order`, for an `order` that is not an integer, for a
  `key` outside `^[a-z][a-z0-9-]*$`, and for an unknown property on a section or an entry. `schema_version` stays 1 and
  the live `docs/map.yaml` validates before and after the rows are added.
- **AC2 — The `sections` class.** On fixture maps `docs-map-hygiene` yields exactly one WARN naming the offending key
  for: two sections sharing a `key`; two sharing an `order`; an `href` starting with `/`; one containing `://`; one
  containing `..`; one not ending in `/`; the same four `href` defects inside an `entries` item (naming section and
  entry); and none of these for the two mint rows.
- **AC3 — The `unnamed-top-level` class.** On a fixture tree whose git index holds top-level entries `docs/…`,
  `.github/…`, `scripts/…`, `widgets/…` and `docsite/…`, with a MAP table naming `` `docsite/` `` and not `widgets`, the
  source yields exactly one `unnamed-top-level` WARN naming `widgets`; naming `` `widgets/` `` in the table, or adding
  `widgets` to the allow-list under a monkeypatch, clears it; a dot-directory never fires it; a top-level file (no `/`)
  never fires it.
- **AC4 — Never a FAIL, never a crash.** Every finding of the two new classes has status `warn`; a `run_git`
  `CliBridgeError`, a missing `docs/map.yaml` and a map `load_map_yaml` refuses each yield one WARN naming the cause,
  and `python -m pyforge.doctor.sources docs-map-hygiene` exits 0 on each; `missing` and `unmapped` keep their FAIL
  status and their messages (the existing tests in `test_sources_docs_map_hygiene.py` pass unchanged).
- **AC5 — Quiet on the story's tree.** `pixi run --frozen -e pyforge-guild docs-map-hygiene-check` exits 0 and prints
  only the OK row; its evidence carries `sections_count: 2` and `unnamed_top_level: []`.
- **AC6 — The render does not move.** `pixi run --frozen -e pyforge-guild docs-map-render` leaves `docs/MAP.md`
  byte-identical (`git diff --exit-code docs/MAP.md` after the run), and `docs-currency-check`'s `map-render` and
  `authored-page-stale` classes report nothing new.
- **AC7 — The MAP rows.** `docs/MAP.md` § *Outside this map* holds rows whose first column names `docsite/`,
  `docs-site/` and `presentations/`, a Publish roots row that names `/`, `/herald/`, `/dashboard/kedro-viz/` and
  `dashboard.yml`, and no longer says the dossier publishes at the root; a *Sections* paragraph names the five fields.
- **AC8 — Herald's files are untouched.** `git diff --stat <baseline>..HEAD -- docs-site docsite` is empty.
- **AC9 — Mutations.** Each fails a named test: a `sections` or `unnamed-top-level` finding emitted as `fail`; a
  dot-directory reported; a duplicate `order` passed; an `href` without a trailing `/` passed.
- **AC10 — The suites.** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` and
  `pixi run --frozen -e pyforge-guild detectors-ci` exit 0; `doctor check --list` and the speed-budget test are
  unchanged (`docs-map-hygiene` is not in `doctor check`'s default set).

## Boundaries & Constraints

- The registry carries ordering and ownership and nothing a renderer decides: no styling, no template, no page content.
  `sections:` is additive; `schema_version` stays 1.
- Doctor renders no page of the site. `docs/MAP.md`'s generated section is the registry's own human render; everything
  else in `docs/MAP.md` is hand-authored outside the markers, the one sanctioned hand edit (CAP-84).
- No file under `docsite/` or `docs-site/` changes, `sidebar_from_map.py` and `site.yml` included.
- No `sections:` row for a section that does not publish yet (`status`, `dashboards`, `changes`).
- The two new classes are WARN, never FAIL; the two existing classes do not change; the allow-list is a closed constant
  that grows only through a story.
- The git index read is the one subprocess, through `cli_bridge.run_git` (AD-5); `docs_map_hygiene.py` imports no
  `subprocess`.
- No pixi task, `scripts/detectors.py` row or environment change: `docs-map-hygiene` is already registered and already
  in `detectors-ci`.
- Python from the doctor env only; `jsonschema` and PyYAML are already doctor run-deps.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| the two mint rows, 28 tracked top-level dirs, three new MAP rows | one OK finding; `sections_count: 2`, `unnamed_top_level: []` |
| no `sections` key | valid; `sections_count: 0` |
| `sections: []` | valid; `sections_count: 0` |
| a section without `owner` | `load_map_yaml` raises; one WARN naming the schema error |
| two sections with `order: 10` | one `sections` WARN naming both keys |
| `href: /herald/` | one `sections` WARN naming `herald` (leading slash) |
| `href: herald` | one `sections` WARN naming `herald` (no trailing slash) |
| entry `href: ../dashboard/kedro-viz/` | one `sections` WARN naming `herald` and the entry (`..`) |
| tracked `widgets/x.md`, no MAP row | one `unnamed-top-level` WARN naming `widgets` |
| tracked `.foo/x` | nothing |
| tracked top-level file `README.md` | nothing |
| `git ls-files` raises `CliBridgeError` | one WARN naming the cause; exit 0 |
| `docs/MAP.md` missing | the existing FAIL (unchanged) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-doctor` CAP-90 (FR-23), minted 2026-10-14; read by `pyforge-herald:CAP-61`.
- Architecture: AD-14 (added with this chain), AD-5, AD-3, AD-2 (see the spine's § Currency reconciliation —
  2026-10-14 (Pages site)).
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-13 entry (one registry orders the whole site,
  and a stale site tells on itself).
- Epic: Epic 48 (new), Story 48.1. `epic-48` and `epic-48-retrospective` are minted with it.
- Ledger key: `48-1-one-registry-orders-every-section-of-the-pages-site`.
- Ledger status at mint: `backlog`.
- Deps: none. Herald's Story 43.7 lists this story in its Deps; nothing here waits on herald.
- Surface: `marshal-policy.toml` `[epic_surfaces]."48"` (added with this mint). `docs/map.yaml`, `docs/MAP.md` and
  `src/shared/packages/pyforge-doctor/**` are already in `spec-pyforge-doctor`'s `surface:`; reconcile every Spec
  `spec-surface-check` names (`spec-pyforge-core` co-governs station `src/`; `spec-pyforge-herald` is a co-owner of
  `docs/MAP.md`'s herald rows if the detector names it).
- `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Minted 2026-10-14 in one chain commit.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-doctor CAP-90 (FR-23), extending CAP-84 and
CAP-83; AD-14 (new), AD-5; read by `pyforge-herald:CAP-61` Story 43.7 • `flag-exempt: docs-only`

**Given** `docs/map.yaml` with 68 pages and no `sections:`, a schema that refuses the key, `docs-map-hygiene` with its two
classes, and a `docs/MAP.md` whose Publish roots row is stale and whose table names 4 of the 28 tracked top-level
directories
**When** the story lands
**Then** the schema accepts the additive `sections:` list and refuses a malformed entry; `docs-map-hygiene` warns on a
duplicate key or order, a malformed `href`, and a tracked top-level directory the table does not name; both WARN, never
FAIL
**And** on the story's tree `docs-map-hygiene-check` exits 0 with only the OK row, `docs-map-render` leaves `docs/MAP.md`
byte-identical, the MAP names `docsite/`, `docs-site/`, `presentations/` and today's publish roots, herald's files are
untouched, and `pyforge-doctor-test` and `detectors-ci` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass, with AC1–AC4 and AC9's tests (the
  station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py -q` — expected: pass (AC1–AC4, AC9).
- `pixi run --frozen -e pyforge-guild docs-map-hygiene-check` — expected: exit 0, only the OK row (AC5).
- `pixi run --frozen -e pyforge-guild docs-map-render && git diff --exit-code docs/MAP.md` — expected: exit 0 (AC6).
- `pixi run --frozen -e pyforge-guild docs-currency-check` — expected: exit 0 (AC6).
- `git diff --stat <baseline_revision>..HEAD -- docs-site docsite` — expected: empty (AC8).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code (AC10).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0 (`flag-exempt: docs-only` is on the roster's
  closed list).
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- The four mutations of AC9 — expected: each fails its named test. Restore each.

**Manual check:**
- Open `docs/MAP.md` § *Outside this map* and read the Publish roots row against `.github/workflows/dashboard.yml`'s
  header comment and `docsite/tools/assemble_pages.py`'s `HERALD_PREFIX` and `DASHBOARD_PREFIX`: the three mounts and
  the one deploy caller agree.

## Named, not fixed here

- **The renderer.** Reading `sections:` into the sidebar, the top menu and the home tiles, and retiring `site.yml`'s
  nav, is `pyforge-herald:CAP-61` Story 43.7. Until it lands the two registries coexist and `sidebar_from_map.py` keeps
  reading `site.yml`.
- **Rows for `status`, `dashboards` and `changes`.** Added by the herald, steward and atlas stories that publish those
  sections (herald Epic 42 and 43, atlas Epic 30), each through its own surface reconcile.
- **An `href` that resolves to nothing in the built artifact.** Herald's `pages-check` and `docs-site-validate` judge
  the build; this story checks the registry's shape only.
- **`presentations/` as a MAP row rather than an allow-list entry.** Chosen so the Publish roots story is told in one
  table; the operator may move it to the allow-list (Spec open question 3).

## Spec Change Log

- 2026-10-14: minted with CAP-90 / FR-23, AD-14 and Epic 48 from the Dream's 2026-10-13 entry, the herald lead entry,
  the 2026-10-13 rulings and herald's Epic 43 (Story 43.7's Deps). `type: feature`, `flag-exempt: docs-only` by the
  coordinator's assignment (memlog 2026-10-14). The Dream's two stories (the registry in M2, the MAP rows in M1) are this
  one story: same two files, one check that reads both.
