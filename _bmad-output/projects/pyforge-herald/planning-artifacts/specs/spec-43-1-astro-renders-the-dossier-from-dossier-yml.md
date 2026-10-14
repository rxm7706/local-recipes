---
title: '43.1: Astro renders the dossier from dossier.yml'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
flag:
  key: pyforge.herald.pages_one_generator        # new; minted by this story; shared by Stories 43.2-43.6 (one flag per CAP, Q6); retired by 43.7
  provider: openfeature-file                     # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                  # v1 is global only
  fallback: 'the Jinja path renders /herald/dossier/ exactly as it does today and no Astro dossier page is emitted'
  cleanup: retired by Story 43.7 with the Jinja path, or 90 days after ON in every environment, whichever comes first (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-39-1-the-dossier-tile-shows-every-ci-surface-that-is-not-live.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-41-1-the-pages-hygiene-before-the-rework.md
  - docsite/content/dossier.yml
  - docsite/templates/blocks.html.j2
  - docsite/templates/dossier_body.html.j2
  - docsite/build.py
  - docsite/tools/assemble_pages.py
  - docsite/tools/export_ci_surfaces_tile_env.py
  - docsite/README.md
  - docs-site/astro.config.mjs
  - docs-site/src/content.config.ts
  - docs-site/src/loaders/shelf-docs-loader.ts
  - docs-site/package.json
  - docs-site/README.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/ci_surfaces_tile.py
  - src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_tile_flag_states.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - docs/governance/flag-inventory/pyforge-herald.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The Pages artifact is rendered by two generators. The docs shelf is Astro 7.2 with Starlight 0.42
(`docs-site/`), rendering only the four Diátaxis quadrants; the dossier is Jinja (`docsite/build.py` with
`docsite/templates/blocks.html.j2`) over `docsite/content/dossier.yml` (1,434 lines, 12 sections, 14 block types),
glued to the shelf by `assemble_pages.py`. Two generators mean two themes, two searches, two link checkers and the
`docsite` / `docs-site` name clash. The operator ruled on 2026-10-13 (M3) that Astro renders everything and `docsite/`
dissolves; this story is the first page of that move, the dossier, behind a flag that lets both paths build until
Story 43.7 retires the Jinja one.

**Approach:** the dossier becomes an Astro content collection and fourteen components, rendering the same YAML in
place.

- **The collection.** `docs-site/src/content.config.ts` gains a `dossier` collection whose loader reads
  `docsite/content/dossier.yml` in place (Astro's YAML file loader; the brainstorm verified it is available on Astro
  7.2.8), typed by a schema that names the twelve sections and the block types. The file does not move in this story
  (Story 43.7 moves it to `docs-site/src/content/dossier/`).
- **The components.** One Astro component per block type under `docs-site/src/components/dossier/`: `lede`, `prose`,
  `h3`, `table`, `callout`, `finding`, `stats`, `quote`, `relations`, `lattice`, `engines`, `chips`, `note`, `verify`
  — the fourteen Epic 43 names, matching the macros in `blocks.html.j2` one to one.
- **The page.** `docs-site/src/pages/herald/dossier/index.astro` renders the sections and blocks from the collection
  and carries `data-pagefind-body`, so Starlight's Pagefind indexes it.
- **The inline vocabulary.** A TypeScript helper with `md_inline`'s vocabulary — `` `code` ``, `**bold**`, `*em*`,
  `[link](href)`, `<<arrow>>` and backslash escapes — rendering alike, an escape inside a code span included (Story
  41.1's restore loop is the Jinja side of that case).
- **The golden tests.** For every block type a fixture block is rendered through the Jinja macro and through the Astro
  component and compared on text content and block order (a golden DOM comparison per block type). The tests live in
  herald's suite; where they need the Astro build they call `npm run build` in `docs-site/` as `test_docs_site.py`
  already pins (`npm ci`, `npm run build`), against a fixture `dossier.yml`.
- **The flag.** `pyforge.herald.pages_one_generator` lands in `src/platform/config/flags.json` (`defaultVariant` off,
  metadata owner `herald`, story this key) and in `flag-overlays.json` (dev on, staging and production off). Herald's
  package reads it through `pyforge.core.flags.read_boolean` in a module beside `pyforge/herald/ci_surfaces_tile.py`;
  a Guild-env export step (the `export_ci_surfaces_tile_env.py` pattern) hands the build one value, which Astro reads
  at build time and `assemble_pages.py` reads too. On: the Astro page is emitted and the assembler skips the Jinja
  `dossier/` output, so AD-21's collision rule proves exactly one path wrote `herald/dossier/index.html`. Off: the
  Jinja dossier renders as before and no Astro dossier page is emitted. The render takes the flag state as an argument
  so the two-state test drives both values. Stories 43.2 to 43.6 share this flag (one flag per CAP, Q6) and Story
  43.7 retires it with the Jinja path.
- **The second render.** `herald/artifact/dossier.html` (CAP-47, the Claude-artifact twin) stays on the Jinja path
  until Story 43.7; this story changes only `/herald/dossier/`.

Ledger key: `43-1-astro-renders-the-dossier-from-dossier-yml`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / L / 41.1 (the `md_inline` restore loop the golden test's escape case compares against).

### Living CAP citations

- **`spec-pyforge-herald` CAP-61** (FR-12.4): the collection, the fourteen components, the page, the flag. On CAP-44
  (the dossier is the source: one YAML, read in place) and AD-23 (one generator; new content is an Astro page,
  component or collection under `docs-site/src/`). Supersedes CAP-44's and CAP-52's two-generator shape when Epic 43
  completes.
- **CAP-59** (the `ci_surfaces` block): its tile stays on the Jinja path and the `/status/ci/` page (Story 42.1) until
  Epic 43 decides its Astro home; see § *Named, not fixed here*.
- **canopy:AD-11** (one flag tree); `feature-flag-governance:CAP-1` (the flag rule), `CAP-4` (the two-state test), Q6
  (one flag per CAP).
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M3 ("Astro renders the dossier from
  `dossier.yml` through a content collection (the 14 block macros become 14 components)"); `brainstorm-intent.md`
  § M3; design-thinking § *Target information architecture*, row Overview + Dossier; the design preview the operator
  approved on 2026-10-14 (the fleet board: eight station rows with bars, an attention block, a snapshot line; the
  home: four doors Docs / Overview / Status / Decks) sets the look the dossier page shares.

## Acceptance Criteria

- **AC1 — The page.** Given the flag on, When the site builds, Then `herald/dossier/index.html` in the artifact is
  Astro's output (it carries Astro's generator meta and `data-pagefind-body`) and its sections come from the `dossier`
  collection in `dossier.yml`'s order, twelve on 2026-10-14.
- **AC2 — Golden per block type.** For each of the fourteen block types, a test renders one fixture block through the
  Jinja macro and through the Astro component and finds the same text content and the same order of blocks; a fixture
  section with every type renders the same fourteen-block sequence both ways.
- **AC3 — The inline vocabulary.** A test renders, both ways, a prose block holding a code span, bold, em, a link, an
  arrow and a backslash escape, and a code span holding an escape, and finds the same text and the same tag names in
  the same order; no `\x00` in either output.
- **AC4 — Flag off.** Given the flag off, Then `herald/dossier/index.html` is the Jinja output, byte-identical to a
  build without this story, and no file under `docs-site/build/site/herald/dossier/` comes from Astro; the collection
  is not loaded.
- **AC5 — One writer.** Given the flag on, Then the assembler's collision check finds exactly one producer of
  `herald/dossier/index.html` (Astro), and a planted Jinja `dossier/index.html` with the flag on makes `pages-check`
  exit 1 naming the path.
- **AC6 — Two states.** `src/shared/packages/pyforge-herald/tests/unit/test_pages_one_generator_flag_states.py` runs
  the selection with `pyforge.testing_kit.flags.flag_states("pyforge.herald.pages_one_generator")`: on, the Astro
  path is selected for `/herald/dossier/`; off, the Jinja path is.
- **AC7 — The boundary.** The `site` env gains no pyforge dependency (`pixi.toml`'s `site` feature unchanged in its
  dependencies); no `pyforge.steward` import and no `gh` call appears in `docs-site/`, herald's package or
  `docsite/tools/`.
- **AC8 — The gates.** `pixi run --frozen -e site pages-check` exits 0 in both flag states;
  `pixi run --frozen -e site docs-site-validate`, `pixi run --frozen -e pyforge-herald pyforge-herald-test` and
  `pixi run --frozen -e pyforge-guild flag-gate-check` exit 0.

## Boundaries & Constraints

**Always:**
- One source: `docsite/content/dossier.yml`, read in place by both paths; no copy, no second YAML.
- Every new page, component or collection sits under `docs-site/src/` (AD-23); no new template language, renderer or
  copy step; the five vendored upstream files stay byte-identical to their recorded hashes (AD-21 rule 5).
- The flag read goes through `pyforge.core.flags.read_boolean` in herald's package, never a station-local parser, and
  reaches the build as one exported value, as CAP-59's does.
- No third-party origin loads from the Astro dossier page (AD-21); fonts stay as the Jinja path serves them until Story
  43.4.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped (`spec-pyforge-herald` for
  `docsite/**` and `docs-site/**`; the flag tree's co-governor as the detector names it); the PR carries the
  `maintenance` label.

**Never:**
- Do not move `dossier.yml`, delete a Jinja template or retire a pixi task here (Story 43.7).
- Do not change the dossier's text, section order or block data to make a golden test pass; the components follow the
  macros.
- Do not edit the vendored validators or `site-url.mjs`; do not hand-edit `docs-site/src/sidebar.generated.json`.
- Do not import `pyforge.*` from `docs-site/` or add a pyforge dependency to the `site` env.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flag on, full dossier | `dossier.yml` as tracked | Astro `herald/dossier/index.html`, twelve sections, `data-pagefind-body` | exit 0 |
| flag off | any | Jinja `herald/dossier/index.html`, byte-identical to today | exit 0 |
| every block type | a fixture section with fourteen blocks | same text and order both ways | test fails on any diff |
| escape in a code span | `` `/stations/\*/mcp` `` | `<code>/stations/*/mcp</code>` both ways | no `\x00` |
| unknown block type | a fixture block `type: quarantined` | the collection schema refuses it, naming the section and index | `npm run build` exit 1 → `pages-check` exit 1 |
| both paths write the dossier | flag on, Jinja output planted | — | `pages-check` exit 1, names the path |
| the `ci_surfaces` block | CAP-59's tile in the estate section | rendered on the Jinja path; on the Astro path per the decision § *Named, not fixed here* records | — |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (FR-12.4), minted 2026-10-14.
- Architecture: AD-23 (adopted 2026-10-14; one generator) on AD-21.
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M3.
- Epic: Epic 43, Story 43.1.
- Ledger key: `43-1-astro-renders-the-dossier-from-dossier-yml`.
- Ledger status at mint: `backlog`.
- Deps: Story 41.1 (station-local; the golden escape case). `marshal factory dispatch` stamps `baseline_revision`
  with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."43"`.
- Flag: `pyforge.herald.pages_one_generator` (`feature-flag-governance:CAP-1`), minted here, shared by 43.2–43.6,
  retired by 43.7.

## Epic excerpt

**Type:** feature • **Effort:** L • **Deps:** 41.1 • **FR/AD:** spec-pyforge-herald CAP-61 (FR-12.4), on CAP-44 (the dossier is the source), AD-23
**Flag:** `pyforge.herald.pages_one_generator` (new; minted by this story; tree default off, dev on through the overlay; selects the Astro path for `/herald/dossier/` and, as later stories land, the rest of `/herald/`)

**Given** `dossier.yml` (1,434 lines, 12 sections, 14 block types) rendered by `docsite/templates/blocks.html.j2` and
`build.py`, and a docs site on Astro 7.2 / Starlight 0.42 that renders only the four quadrants
**When** the site builds with `pyforge.herald.pages_one_generator` on
**Then** `/herald/dossier/` is an Astro page whose sections and blocks come from the `dossier` collection; for every
block type a golden test renders one fixture block through the Jinja macro and through the Astro component and finds
the same text content and the same block order; the inline vocabulary (`` `code` ``, bold, em, link, `<<arrow>>`,
backslash escapes) renders alike, an escape inside a code span included; the page carries `data-pagefind-body`
**And** with the flag off the Jinja dossier renders as before and no Astro dossier page is emitted; `pages-check` exits
0 in both states; `pyforge-herald-test` is green with the flag test running both states

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/unit/test_pages_one_generator_flag_states.py src/shared/packages/pyforge-herald/tests/meta/test_dossier_golden.py -q` — expected: pass (AC2, AC3, AC6).
- `pixi run --frozen -e site pages-check` with the flag on and with it off — expected: exit 0 both times (AC1, AC4, AC5, AC8).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0 (the new key has a reader under `src/`).
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0, the herald inventory regenerated.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Swap two blocks in a fixture section on one path only — expected: the golden order test fails naming the type.
- Drop the escape handling from the TypeScript helper — expected: AC3's test fails on the code-span case.
- Build with the flag on and the assembler still writing the Jinja dossier — expected: `pages-check` exits 1 naming `herald/dossier/index.html`.

## Named, not fixed here

- **The `ci_surfaces` block** (CAP-59, Story 39.1; the fifteenth type `docsite/README.md` counts, outside Epic 43's
  list of fourteen): its tile renders on the Jinja path today, and Story 42.1 renders the same snapshot at
  `/status/ci/`. The implementing session records on the Spec memlog whether this story adds a fifteenth component or
  Epic 43 lets `/status/ci/` carry the surfaces before Story 43.7 deletes the macro; the golden tests cover the
  fourteen either way.
- **The artifact twin** `herald/artifact/dossier.html` (CAP-47): Jinja until Story 43.7.
- **Computed stats and the measured-on date** per section: Story 43.5. **Fonts and the theme**: Story 43.4. **The
  dossier's move** to `docs-site/src/content/dossier/`, the Jinja path's retirement and the flag's removal: Story 43.7.
- **The overview, gallery and family pages**: Story 43.2; **mounts, redirects and search**: Story 43.3.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 43's Story 43.1 text, `spec-pyforge-herald` CAP-61, FR-12.4, AD-23 and the
  Dream's 2026-10-13 entry (M3), against `dossier.yml`, `blocks.html.j2` and `content.config.ts` as they stand on
  2026-10-14. The flag is minted here and shared by the rest of Epic 43 under Q6.
