---
title: '43.2: The overview, gallery and deck family pages are Astro pages'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
flag:
  key: pyforge.herald.pages_one_generator        # Story 43.1's; shared across Epic 43 (one flag per CAP, Q6), not minted here
  provider: openfeature-file                     # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                  # v1 is global only
  fallback: 'the Jinja path renders the overview, the gallery and the family pages exactly as it does today and Astro emits none of them'
  cleanup: retired by Story 43.7 with the Jinja path (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-43-1-astro-renders-the-dossier-from-dossier-yml.md
  - docsite/build.py
  - docsite/content/site.yml
  - docsite/templates/page_index.html.j2
  - docsite/templates/page_gallery.html.j2
  - docsite/templates/page_family_index.html.j2
  - docsite/templates/page_family.html.j2
  - docsite/templates/shell_page.html.j2
  - docsite/tools/assemble_pages.py
  - presentations/pyforge-herald/facts.yaml
  - src/shared/packages/pyforge-herald/src/pyforge/herald/deck_versions.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/stamps.py
  - src/shared/packages/pyforge-herald/tests/unit/test_docsite_build.py
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py
  - docs-site/astro.config.mjs
  - docs-site/src/content.config.ts
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `docsite/build.py` renders `herald/index.html` (the overview), `herald/infographics/index.html` (the
gallery and one page per standalone infographic) and one `herald/decks/<slug>/index.html` per deck family (ten on
2026-10-14), each export carrying its etag and tree stamp (`_artifact_stamp`, from the `<path>.stamp.json` sidecar or
the commit and a content hash), from `docsite/content/site.yml`'s include and override lists and each family's
`presentations/<slug>/facts.yaml`. After Story 43.1 the dossier is Astro's and these three page kinds are the rest of
`/herald/` still on Jinja (CAP-35's browsable family, CAP-53's one current version per export, CAP-55's HTML twins).

**Approach:** the three page kinds become Astro pages over the same inputs, read as data.

- **The overview**, `docs-site/src/pages/herald/index.astro`: the station tiles, the neighbours and the doors
  `site.yml` and `facts.yaml` describe today, in the shape of the design preview the operator approved on 2026-10-14
  (the fleet board: eight station rows with bars, an attention block, a snapshot line; the home: four doors Docs /
  Overview / Status / Decks).
- **The gallery**, `docs-site/src/pages/herald/infographics/index.astro`: the ten infographics `site.yml`'s `include`
  list names, in that order, resolved over `presentations/*/project/*Infographic standalone.html` with the `exclude`
  and override lists applied as `build.py` applies them; each with its title and a lazy preview; each standalone twin
  copied verbatim into the artifact as today and wrapped, never edited.
- **The family pages**, `docs-site/src/pages/herald/decks/index.astro` and `decks/[slug].astro`: one page per family
  with a `facts.yaml`; each shows the poster, the Infographic Deck and the Executive Summary in view and offers the
  PPTX and Marp sources as downloads, each stamped as today (the sidecar's `tree` and `etag`, or the commit and a
  content hash when no sidecar exists).
- **Current exports, read as data.** CAP-53 keeps one current version per export kind in the tree and
  `pyforge.herald.deck_versions` is the writers' one definition of current. The loader lists the one dated file per kind
  the tree holds and re-derives nothing: it never chooses a newest date (that would be a second definition, which
  AD-4's 2026-09-28 amendment forbids); when a kind holds more than one dated file the build fails naming them.
- **Parity.** A test compares, per family, the set of links and download names between the Jinja path and the Astro
  path, and the gallery's ordered list of slugs and titles.
- **The backbar.** The infographic pages' back-bar (`BACKBAR`, `FAMILY_VIEW_BACKBAR` in `build.py`) is injected by the
  Astro wrapper page around the copied twin, never written into the twin file.
- **The flag.** `pyforge.herald.pages_one_generator` (Story 43.1's) selects the path for these pages as it does for the
  dossier: on, Astro emits them and the assembler skips the Jinja outputs under the collision rule; off, nothing
  changes.

Ledger key: `43-2-the-overview-gallery-and-deck-family-pages-are-astro-pages`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / 43.1.

### Living CAP citations

- **`spec-pyforge-herald` CAP-61** (FR-12.4): the three page kinds on the one generator. On CAP-35 (the family is
  browsable and downloadable), CAP-53 (one current version per export), CAP-55 (the HTML twin is self-contained and
  published), AD-23 (one generator) and AD-4 as amended 2026-09-28 (one definition of current).
- **CAP-58** (the shared menu): every Astro page renders the one nav list as the Jinja shell does.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M3 ("the gallery and the deck family
  pages as Astro pages over `presentations/` and `facts.yaml`"); `brainstorm-intent.md` § M3 (gallery over
  `import.meta.glob`, family pages as `[slug].astro`); design-thinking § *Target information architecture*, rows
  Overview + Dossier and Infographics, Decks; the design preview the operator approved on 2026-10-14.

## Acceptance Criteria

- **AC1 — The gallery.** Given the flag on, When the site builds, Then `herald/infographics/index.html` is Astro's and
  lists the ten infographics in `site.yml`'s order, each with its title and a preview marked lazy, and each standalone
  twin is present in the artifact byte-identical to its tracked file.
- **AC2 — The family pages.** Given the flag on, Then one `herald/decks/<slug>/index.html` exists per family with a
  `facts.yaml` and a poster (ten on 2026-10-14), showing the poster, the Infographic Deck and the Executive Summary and
  offering the PPTX and Marp sources as downloads, each download named with its stamp (`tree` and `etag` from the
  sidecar, or the commit and content hash) as the Jinja page names it.
- **AC3 — Parity.** A test renders both paths from the same tree and finds, per family, the same set of hrefs and the
  same set of download names, and the same ordered gallery list; a difference fails naming the family and the href.
- **AC4 — Twins are copied, never edited.** For every twin in the artifact, `sha256sum` equals the tracked file's; the
  back-bar appears in the wrapper page and in no twin file.
- **AC5 — One current version.** Given a fixture family with two dated PPTX files, When the site builds with the flag
  on, Then the build fails naming both files; given one per kind, the page lists that one.
- **AC6 — Flag off.** Given the flag off, Then the three page kinds are the Jinja outputs, byte-identical to a build
  without this story, and Astro emits no `herald/index.html`, `herald/infographics/` or `herald/decks/` file.
- **AC7 — The gates.** `pixi run --frozen -e site pages-check` exits 0 in both flag states (the menu check, the link
  walk and the origin check included); `pixi run --frozen -e pyforge-herald pyforge-herald-test` is green.

## Boundaries & Constraints

**Always:**
- Read `site.yml`, `facts.yaml`, the twins and the sidecars as data; import no herald or docsite code from `docs-site/`
  (AD-21, AD-23).
- Copy every twin and export verbatim into the artifact; wrap, never edit (CAP-55).
- Keep every page, loader and component under `docs-site/src/` (AD-23); keep the five vendored files hash-pinned.
- Keep the shared menu (CAP-58) on every Astro herald page, built from the configured base path so it resolves on every
  host.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not define "current export" a second time (AD-4 amended 2026-09-28); list what the tree holds and fail on more than
  one.
- Do not move, rename or delete a twin, an export or a `facts.yaml`; do not change what `build.py` renders with the flag
  off.
- Do not load a third-party origin (AD-21); previews are the artifact's own twins.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flag on, the tracked tree | ten families, ten infographics | Astro overview, gallery and ten family pages; parity test passes | exit 0 |
| a family with no poster | fixture `facts.yaml`, no standalone twin | no family page, as `build.py` skips it today; parity holds | exit 0 |
| a family with no Executive Summary | fixture | the page omits that view, as `build.py` does | exit 0 |
| two dated files of one kind | fixture `src/pptx/` with two files | — | build exit 1, names both files |
| no sidecar | an export without `.stamp.json` | stamp from the commit and a content hash | exit 0 |
| flag off | any | Jinja outputs, byte-identical | exit 0 |
| a twin edited in the artifact | planted diff | — | AC4's hash test fails naming the file |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (FR-12.4), minted 2026-10-14.
- Architecture: AD-23 (adopted 2026-10-14) on AD-21 and AD-4 (amended 2026-09-28).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M3.
- Epic: Epic 43, Story 43.2.
- Ledger key: `43-2-the-overview-gallery-and-deck-family-pages-are-astro-pages`.
- Ledger status at mint: `backlog`.
- Deps: Story 43.1 (the flag, the shell, the collection pattern). `marshal factory dispatch` stamps
  `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."43"`.
- Flag: `pyforge.herald.pages_one_generator` (shared with 43.1; `feature-flag-governance:CAP-1`, Q6).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 43.1 • **FR/AD:** spec-pyforge-herald CAP-61 (FR-12.4), on CAP-35 (the family is browsable and downloadable), CAP-53 (one current version per export), CAP-55 (the HTML twin), AD-23
**Flag:** `pyforge.herald.pages_one_generator` (shared with 43.1)

**Given** `build.py` renders `herald/index.html`, `herald/infographics/index.html` and one
`herald/decks/<slug>/index.html` per family (ten on 2026-10-14) with each export's etag and tree stamp
**When** the site builds with the flag on
**Then** the three page kinds are Astro pages: the gallery lists the ten infographics in `site.yml`'s order with their
titles and lazy previews; each family page shows the poster, the Infographic Deck and the Executive Summary in view and
offers the PPTX and Marp sources as downloads, each stamped as today; a parity test compares the set of links and
download names per family between the two paths
**And** the published twins are copied, never edited (the backbar is injected by the wrapper page, not into the file);
with the flag off nothing changes; `pages-check` and `pyforge-herald-test` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_herald_pages_parity.py -q` — expected: pass (AC1–AC5).
- `pixi run --frozen -e site pages-check` with the flag on and with it off — expected: exit 0 both times (AC6, AC7).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Reorder two entries in a fixture `site.yml` include list on one path only — expected: the gallery parity test fails.
- Drop one download from a fixture family on the Astro path — expected: the parity test names the family and the download.
- Write the back-bar into a copied twin — expected: AC4's hash test fails naming the file.

## Named, not fixed here

- **`publicDir` population** (the twins and the downloaded exports served from `docs-site/public/`), the redirects map
  and the Pagefind index over these pages: Story 43.3.
- **Fonts and the theme** the pages share with the shelf: Story 43.4. **The built-from footer**: Story 43.5.
- **`/facts.json`** (the union of every `facts.yaml`): Story 43.6.
- **The home's four doors** generated from `docs/map.yaml` `sections:` (`pyforge-doctor:CAP-90`): Story 43.7 once
  doctor Story 48.1 has landed the registry; until then the overview reads `site.yml`.
- **The four infographics** under `presentations/` for unrelated projects (`deckcraft`, `presenton-pixi-image`,
  `unity-data-stack`, `wasm-analytics-stack`, each with a `facts.yaml`): excluded by `site.yml`'s include list, as
  today; publishing them is a `site.yml` edit, not this story.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 43's Story 43.2 text, `spec-pyforge-herald` CAP-61, FR-12.4 and the Dream's
  2026-10-13 entry (M3), against `build.py`, `site.yml` and the templates as they stand on 2026-10-14. The
  one-current-version rule (fail on two dated files of a kind, never choose) is the reading of AD-4's 2026-09-28
  amendment this spec binds; the implementing session records it on the Spec memlog.
