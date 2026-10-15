---
title: '43.4: Fonts and theme come from one design system'
type: 'feature'
created: '2026-10-14'
status: 'in-review'
flag:
  key: pyforge.herald.pages_one_generator        # Story 43.1's; shared across Epic 43 (one flag per CAP, Q6), not minted here
  provider: openfeature-file                     # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                  # v1 is global only
  fallback: 'the Jinja path serves its own stylesheet and the vendored woff2 files exactly as it does today'
  cleanup: retired by Story 43.7 with the Jinja path (spec-feature-flag-governance Q4)
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-31-3-the-public-pages-build-loads-no-third-party-resource-from-herald-s-own-pages.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-43-1-astro-renders-the-dossier-from-dossier-yml.md
  - docsite/assets/_dossier.css
  - docsite/assets/_site-chrome.css
  - docsite/assets/fonts
  - docsite/build.py
  - docs-site/package.json
  - docs-site/package-lock.json
  - docs-site/astro.config.mjs
  - docs-site/README.md
  - src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site_validators.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-08 Google Fonts loaded on 45 pages of the artifact; Story 31.3 fixed it by vendoring 25
`woff2` files under `docsite/assets/fonts/` with a hand-written sha256 table, so no herald page loads Google Fonts. The
herald pages carry their own stylesheets (`docsite/assets/_dossier.css`, `_site-chrome.css`) beside Starlight's, so a
reader moving between the docs and the dossier sees two typographies, two colour systems and a dark mode that only the
docs have. The brainstorm named the Google Fonts incident and the dossier-numbers drift as one class, "a check nobody
reads", and the cure as structural: fonts through npm, a CSP meta.

**Approach:** one typography, one colour system and one dark mode across every prefix, with no hand-vendored font file.

- **Fonts through `@fontsource`.** `docs-site/package.json` gains `@fontsource/big-shoulders-display`,
  `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono`, `@fontsource/archivo` and `@fontsource-variable/archivo`;
  the herald pages import the faces they use and Astro bundles them into the artifact, on the configured origin.
- **One theme contract** (amended 2026-10-15 by the operator's ruling; change log). Starlight's theme variables are
  the single contract, filled with the herald look in one file, `docs-site/src/styles/theme.css`: `--sl-font`,
  `--sl-font-mono`, a headings face and the accent, gray, white, black and hue scales, light under `:root` and dark
  under Starlight's `[data-theme='dark']`. The docs take it through Starlight's `customCss`; the herald pages through
  their one stylesheet, which declares no font or colour of its own and derives the dossier's tokens (the custom
  properties `_dossier.css` and `_site-chrome.css` define) from those variables. So the docs and the herald prefixes
  read as one place, follow the toggle the docs header already has, and re-theme together by replacing `theme.css`.
- **Parity with the Jinja path.** The `font-family` the dossier's headings and body resolve to on the Astro path equals
  the Jinja path's (the declarations in `_dossier.css` for the same selectors).
- **What stays and what leaves.** The five vendored upstream files keep their recorded hashes (`docs-site/README.md`).
  `docsite/assets/fonts/` and its sha256 table serve the Jinja path until Story 43.7 retires both; from this story the
  Astro path references nothing under `docsite/assets/`.
- **The origin rule.** No font loads from another origin; Story 43.3's origin check and CSP meta judge the fonts as
  they judge everything else.

Ledger key: `43-4-fonts-and-theme-come-from-one-design-system`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / 43.1.

### Living CAP citations

- **`spec-pyforge-herald` CAP-61** (FR-12.4): fonts through `@fontsource`; one theme across every prefix. On AD-21
  (zero third-party origins; the five vendored files hash-pinned) and the Story 31.3 vendoring it replaces (CAP-56's
  no-third-party rule as built).
- **AD-23**: a stylesheet and font imports under `docs-site/src/`, no copy step.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M3 ("fonts through `@fontsource`");
  `brainstorm-intent.md` § *The finding* (the 2026-10-08 Google Fonts incident) and § M3 ("Starlight theme tokens on
  every page"); design-thinking § *Target information architecture* ("one footer, one theme") and § *Success Metrics*
  (third-party origins: 0, structural: `@fontsource`, CSP meta).

## Acceptance Criteria

- **AC1 — Faces from the bundle.** Given the flag on, When the site builds, Then every `@font-face` the herald pages
  load names a `src` under the artifact's own `_astro/` (or configured assets) path, and `package.json` lists the five
  `@fontsource` packages with `package-lock.json` resolved.
- **AC2 — Same families.** A test reads the `font-family` declarations for the dossier's heading and body selectors in
  the Astro stylesheet and in `docsite/assets/_dossier.css` and finds them equal (since the 2026-10-15 ruling, the
  Astro side resolved through `theme.css`'s variables).
- **AC3 — Dark mode.** The shared stylesheet defines the dossier tokens under the light root and again under
  `[data-theme='dark']`, and the two blocks differ; a herald page built with the flag on carries no inline theme of
  its own. (Since the 2026-10-15 ruling the two blocks are `theme.css`'s, of Starlight's variables, and the dossier
  tokens derive from them once.)
- **AC4 — No vendored font on the Astro path.** `grep -rn "assets/fonts" docs-site/src` finds nothing, and no herald
  page built with the flag on references a `.woff2` under `herald/assets/`.
- **AC5 — The origin rule.** `pages-check`'s origin check finds no font loaded from another origin; a planted
  `fonts.googleapis.com` stylesheet link on a herald page makes it exit 1.
- **AC6 — The five files.** The hash test over the five vendored upstream files (`.nvmrc`, `scripts/fix-doc-links.js`,
  `scripts/validate-doc-links.js`, `scripts/validate-sidebar-order.js`, `src/lib/site-url.mjs`) passes against
  `docs-site/README.md`'s table.
- **AC7 — The gates.** `pixi run --frozen -e site pages-check` exits 0 in both flag states;
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` is green.

## Boundaries & Constraints

**Always:**
- Load every font from the artifact's own origin (AD-21); `@fontsource` through `package.json`, never a URL.
- Fill Starlight's theme variables once (`theme.css`) and read them on every page; never a second toggle, a second
  theme store, a herald-only dark mode, or a font or colour a herald stylesheet names outside `theme.css` (amended
  2026-10-15, the operator's ruling).
- Keep `package-lock.json` resolved and committed with `package.json`; `npm ci` is what `test_docs_site.py` pins.
- Keep the five vendored files byte-identical (AD-21 rule 5).
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not delete `docsite/assets/fonts/` or its sha256 table here (Story 43.7); the Jinja path still serves them.
- Do not add a font the dossier does not use, or change the families the dossier's headings and body use.
- Do not edit Starlight's own stylesheets or the vendored validators.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flag on | herald pages | fonts from the bundle, one stylesheet, dark block present | exit 0 |
| flag off | herald pages | today's `_dossier.css`, `_site-chrome.css` and vendored woff2 | exit 0 |
| docs page | flag on (amended 2026-10-15) | the herald theme through `theme.css`: same fonts, accent and grays as a herald page | exit 0 |
| docs page | flag off | Starlight's stock theme, byte-identical to before | exit 0 |
| planted Google Fonts link | a herald page | — | `pages-check` exit 1 |
| second host | CAP-56 fixture | font `src` under that origin | exit 0 |
| `package.json` without the lock refreshed | regression | — | `npm ci` fails in the build |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (FR-12.4), minted 2026-10-14.
- Architecture: AD-23 (adopted 2026-10-14) on AD-21 (zero third-party origins; rule 5).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M3.
- Epic: Epic 43, Story 43.4.
- Ledger key: `43-4-fonts-and-theme-come-from-one-design-system`.
- Ledger status at mint: `backlog`.
- Deps: Story 43.1 (the Astro dossier page the stylesheet themes). `marshal factory dispatch` stamps
  `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."43"`.
- Flag: `pyforge.herald.pages_one_generator` (shared with 43.1; `feature-flag-governance:CAP-1`, Q6).

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** 43.1 • **FR/AD:** spec-pyforge-herald CAP-61 (FR-12.4), on AD-21 (zero third-party origins) and the Story 31.3 vendoring it replaces
**Flag:** `pyforge.herald.pages_one_generator` (shared with 43.1)

**Given** Story 31.3 vendored 25 `woff2` files with a hand-written sha256 table so no herald page loads Google Fonts,
and the herald pages carry their own stylesheet beside Starlight's
**When** the site builds with the flag on
**Then** every herald page loads its faces from `@fontsource` imports bundled by Astro, the computed `font-family` of
the dossier's headings and body match the Jinja path's, dark mode follows Starlight's theme toggle on herald pages, and
the origin check finds no font loaded from another origin
**And** the five vendored upstream files are byte-identical to their recorded hashes; `pages-check` and
`pyforge-herald-test` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py src/shared/packages/pyforge-herald/tests/meta/test_docs_site_validators.py -q` — expected: pass (AC2–AC6).
- `pixi run --frozen -e site pages-check` with the flag on and off — expected: exit 0 both times (AC1, AC7).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- A screenshot of `/herald/dossier/` and a docs page from the built artifact in light and in dark mode (herald's browser check), showing one typography.

**Mutations (each restored afterwards):**
- Change the body `font-family` on the Astro path only — expected: AC2's test fails.
- Remove the `[data-theme='dark']` block — expected: AC3's test fails.
- Plant a `fonts.googleapis.com` link — expected: `pages-check` exits 1.

## Verification run (2026-10-15)

The latest run is the Spec Change Log's newest **Gates** bullet (the re-review's resolution, below); the bullets that
follow here are the first implementation's run, kept as its record.

- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py src/shared/packages/pyforge-herald/tests/meta/test_docs_site_validators.py -q`
  — exit 0, 14 passed (the `test_43_4_*` tests: AC2 every family the Jinja stylesheets name, body and headings
  included; AC3 the token blocks, the theme script against Starlight's store and the CSP hash; AC4 the grep, the five
  packages in `package.json` and resolved in the lock; AC5 a planted Google Fonts link on a herald page; AC6 every
  row of `docs-site/README.md`'s table, the five named files among them).
- `pixi run --frozen -e pyforge-herald python -m pytest` over `test_pages_artifact.py`, `test_herald_pages_parity.py`,
  `test_docsite_zero_origin.py`, `test_docs_site_validators.py`, `test_docs_site_imports_tracked.py` — exit 0, 109
  passed, none skipped (docs-site installed): AC1/AC3/AC4 on a flag-on Astro build of the tracked tree
  (`test_43_4_ac1_ac3_ac4_the_built_pages_share_one_theme`, renamed at iteration 1) and pages-check's new guard on five
  fixture cases.
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — exit 0, 2042 passed, 5 skipped (the live Design and
  webhook smokes).
- `pixi run --frozen -e site pages-check`: flag on (`PYFORGE_PAGES_ONE_GENERATOR=1`, public host) — exit 0 (the
  design-system guard, the parity over 10 families and 30 twins, the origin check); flag off — exit 0. With the
  flag off the Astro output is byte-identical to `792382d970`'s (`git archive` of the base built with the same
  `node_modules`: `diff -r` exit 0 over 176 files; `_astro/` holds no herald face). CAP-56 fixture host
  (`PYFORGE_PAGES_APPLY_HOST=1 PAGES_HOST_BASE_URL=https://pages.example.test PAGES_HOST_BASE_PATH=/local-recipes`,
  flag on) — exit 1 on the one finding Story 43.3 recorded on its base, `reference/github-workflows/index.html`
  linking the public host (lane B's 42.3 / 102.5 rewrite it); the faces there name `/local-recipes/_astro/...` and
  the design-system guard passes.
- `pixi run --frozen -e site docs-site-validate` — exit 0. `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
  Steward's `tests/meta/test_station_tests_trigger_map.py` — exit 0, 45 passed (no new root-handing test file).
- `grep -rn "assets/fonts" docs-site/src` — exit 1, nothing found.
- Browser (the flag-on artifact served under `/local-recipes/`): `/herald/dossier/` light, then the docs header's
  toggle set to Dark on `/how-to/`, then `/herald/dossier/` and `/herald/infographics/` dark — `data-theme` follows
  the toggle; the dossier's computed `font-family` is `"IBM Plex Sans", system-ui, -apple-system, sans-serif` (body)
  and `"Big Shoulders Display", "IBM Plex Sans", sans-serif` (h1), as on the Jinja path; every font request is
  `/local-recipes/_astro/*.woff2`, none off-origin; no console error (no CSP violation) on the overview, the dossier,
  the gallery or a reader page. A reader page's twin loads Archivo 400–900 and Archivo Expanded (700–900, 125%) from
  `/herald/fonts.css`. The two 404s on a family page are the `.dc.html` twins' own `./support.js`, as `build.py`
  documents. The docs page keeps Starlight's system font (see the change log: the I/O matrix's docs row).
- Mutations, each restored: the body `font-family` changed in `styles/herald.css` only — AC2's test fails
  (`('Archivo', ...) == ('IBM Plex Sans', ...)`); the `[data-theme='dark']` block removed — AC3's test fails
  ("expected one `:root[data-theme='dark']` block, found 0"); a `fonts.googleapis.com` stylesheet link planted in the
  built `herald/dossier/index.html` — `assemble_pages.py --check` (flag on) exit 1, `herald/dossier/index.html: loads
  'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans' from another origin`; restored, exit 0.
- Not run here: the memlog reconcile, the scoped stamps, `detectors-ci` and `pr-preflight` (the coordinating session
  runs them once for the branch).

## Named, not fixed here

- **The retirement** of `docsite/assets/fonts/`, the sha256 table and `_dossier.css` / `_site-chrome.css` with the
  Jinja path: Story 43.7 (CAP-61's success: "no `.woff2` file or sha256 row remains under `docsite/`").
- **The CSP meta** and the under-40-line origin check: Story 43.3.
- **The design system's name and token set** beyond the dossier's (a site-wide palette for `/status/` and `/changes/`):
  Stories 42.1 and 43.6 use the shared stylesheet as this story leaves it. Since the 2026-10-15 ruling `/changes/` and
  `/status/runs/`, Starlight pages, take `theme.css` through `customCss`; the Jinja `/status/` pages move with 43.7.
- **The OFL-1.1 licence text in the artifact.** The five font packages are OFL-1.1 (`docs-site/README.md`); today the
  artifact carries the licence text only through the Jinja path's `herald/assets/fonts/OFL-*.txt`. Story 43.7, which
  retires that directory, carries the licence text into the artifact (each package ships its `LICENSE`).

## Spec Change Log

- 2026-10-15 (re-review, iteration 2: NOT RESOLVED, 3 new should-fix and 9 nits; resolved here, `review_loop_iteration`
  2):
  - **Should-fix 1, print.** `theme.css`'s dark block now sits under `@media screen`, and its scripts-off twin under
    `@media screen and (prefers-color-scheme: dark)`, so no dark value reaches paper: a page printed in dark mode reads
    the light block (on the docs Starlight's print sheet forces light too; its link precedes the bundle, so the light
    block is what prints). AC3's test asserts the light block at the top level and both dark blocks under exactly
    those screen-only queries; the built test reads every linked sheet for `print` (a `media="print"` link only there)
    and asserts no dark rule applies to the docs shelf or the dossier in print, the dossier printing the light block.
    Mutation: the dark block unwrapped -- both tests fail.
  - **Should-fix 2, the no-literal guard** (`test_43_4_no_source_names_a_font_or_colour_outside_the_theme`, replacing
    `..._no_herald_stylesheet_names_...`). It scans every file under `docs-site/src` but `styles/theme.css`,
    `styles/herald-fonts.css` and `content/` (51 files): a stylesheet's rule bodies; elsewhere each `<style>` body and
    each `style` attribute -- double- or single-quoted, a template literal, a string expression or an Astro
    `style={{...}}` object (camelCase keys mapped). In every declaration value it refuses a hex, a colour function
    (`rgb`/`hsl`/`hwb`/`lab`/`lch`/`oklab`/`oklch`/`color`/`light-dark`/`device-cmyk`) and the 148 CSS named colours and
    the system colours in any case (`transparent`, `currentColor`, `inherit` pass; quoted strings and `url()` are not
    colours); in `font-family` and the `font` shorthand every family must be a `var(--sl-...)` whose fallback is one too.
    An interpolation is trusted only through `cssVar()` / `cssTextTone()` (which take a theme token alone, nit 3); any
    other interpolation and a `style={expression}` are findings of their own. A parametrized test plants each of the
    re-review's probes in a copy of the sources and asserts the guard names it (18 cases): `color: red`, `border: 1px
    solid white`, `color: White`, `outline: 2px solid navy`, `teal` inside `--st-atlas`'s `color-mix()`, the `font`
    shorthand, `var(--sl-font-mono), "Comic Sans MS"`, a literal family as a `var()` fallback, ``style={`color:#c00`}``
    in `pages/herald/[...index].astro`, Astro objects with a colour and with a `fontFamily`, a single-quoted style, a
    `style={railStyle}` expression, `style="background:#c00"` and an unvetted `${...}` in `lib/dossier-blocks.ts`, a
    literal family in `lib/herald-pages.ts`'s back-bar, `GrayText` in `components/SiteTitle.astro`, and an `hsl()` in a
    `<style>` string in `lib/md-inline.ts` -- each fails it. AC3's derived-token check uses the same colour matcher.
  - **Should-fix 3, light `--sl-color-gray-3`** is `#58676f` (5.25:1 on the paper, 4.82 on paper-raised, 4.61 on the
    light nav), so the docs' "On this page" links and herald's `--rail` (table heads, stat labels, footer, the back-bar
    title, the rail exit chip) read AA. `--rail` joins AC3's "nearest" set (its light value is no longer the Jinja
    `#62727a`; dark is unchanged), so reading (b) now counts 23 exact aliases.
  - **Orchestrator defaults, 2026-10-15 (the re-review's nits 4 and 5; the operator may overturn them).** (i) **One link
    colour across docs and herald:** the accent the docs use, `--sl-color-text-accent`; `herald.css`'s `a` drops the
    dossier's `--blue`. (ii) **Small amber label text takes the AA-passing darker amber:** every `color: var(--amber)`
    in `herald.css` (the eyebrows, the kicker, section and h3 numbers, callout labels, card eyebrows and the amber
    hovers) and the back-bar's link hover read `--sl-color-text-accent`, and on the lattice's amber exit chip the
    amber is the accent text's (`.rung .exit { --amber: var(--sl-color-text-accent) }`, so `exit_tone: --amber` reads
    6.5:1). The builder's readings, to keep or overturn with these: **(iii)** `--sl-color-text-accent` is the darker
    amber on light (`accent-high`, 6.5:1) and the amber itself on dark (`accent`, 7.6:1), set in both dark blocks --
    Starlight's dark default is `accent-high`, so the docs' dark links move from `#f2cf98` to the herald amber
    `#dd9a3f`, and the herald's dark labels keep their amber rather than turning pale; one accent-text colour per theme
    for every link and label. **(iv)** The same rule for the other hues used as small text: a station colour as text
    (the overview's station pills -- links -- and the dossier's finding labels) and the red and green callout labels
    read the hue mixed 75% toward the ink (`cssTextTone()` in `src/lib/md-inline.ts`; `color-mix()` in `herald.css`),
    which lifts the marshal pill from 3.82 and mason from 4.497 to 5.40 / 6.11 in light and keeps every station
    distinct; the dots, borders and marks keep the pure hue. The station marks (large bold, 3:1) were already AA.
  - **Nits.** 1: the docs heading rule is `:where(h1#_top), .sl-markdown-content :where(h1, h2, h3, h4):not(:where(
    .not-content *))` -- class specificity at most, and a `.not-content` heading keeps Starlight's face. 2: the flag-off
    emptying hook is anchored to this directory's `src/styles/` (`path.join(__dirname, 'src', 'styles')`, posix-
    normalized), so a dependency's `src/styles/*.css` is never emptied. 3: `cssVar()` throws on any value that is not a
    `--custom-property` name (an absent value is still `''`), so a literal colour in `dossier.yml` / `site.yml` fails
    the build naming it; `test_43_4_css_var_takes_a_theme_token_alone` probes `#c00`, `red`, `var(--amber)` and
    `--x;color:red`. 4 and 5: the defaults above. 6: Story 43.7's change log carries the OFL-1.1 licence carry-over.
    7: this frontmatter's `review_loop_iteration` is 2 and § *Verification run* points here. 8: the Spec memlog
    decision is already written (skipped, as the coordinating session directed). 9: Story 43.3's change log carries one
    line for its Approach edit.
  - **Contrast, from the built values** (the flag-on `_astro/herald.*.css` and the docs bundle, `color-mix()` resolved
    in sRGB; light / dark; AA = 4.5, 3 for large bold). Docs: body `gray-2` on bg 8.93 / 9.75; headings 14.74 / 15.08;
    links on bg 6.52 / 7.59, on the nav and sidebar 5.72 / 7.01; sidebar current (`text-invert` on `text-accent`)
    6.52 / 5.66; "On this page" `gray-3` 5.25 / 6.70 (4.61 / 6.19 on the nav); inline code 13.55 / 10.78. Herald: ink
    on paper 14.74 / 15.08; ink-soft on paper 8.93 / 9.75 and on paper-raised 8.21 / 9.01; links and amber labels on
    paper 6.52 / 7.59; callout labels on paper-raised 5.99 / 7.01 (red 7.10 / 6.83, green 5.63 / 8.58); rail on paper
    5.25 / 6.70 and on paper-raised 4.82 / 6.19; code 8.21 / 9.01; station pill and finding-label text 4.97-7.81 /
    6.83-9.51 (lowest: marshal on paper-raised, 4.97); lattice exit chips red 5.91 / 5.76, amber 6.52 / 7.59, rail 5.25
    / 6.70, green 4.53 / 7.82; station marks (large bold) 3.82-6.19 / 5.76-8.07. Every body-text and link pair is at
    least 4.5:1 in both themes.
  - **Gates (2026-10-15, on `bc980633f7` plus this change).** The Pages, parity, 43.6, zero-origin, validator, imports,
    site-URL, build, flag-state and golden test files -- exit 0, 373 passed, none skipped (docs-site installed); the
    herald suite -- exit 0, 2163 passed, 5 skipped (the live Design and webhook smokes); `lint-types`,
    `docs-site-validate`, steward's trigger map (45 passed) -- exit 0; `pages-check` with both flags off -- exit 0; with
    `pyforge.herald.pages_one_generator` and `pyforge.herald.status_pages` on and the 42.1 and 43.6 fixtures in
    `docsite/content/` (removed after) -- exit 0 (10 families, 30 twins); the CAP-56 host
    (`https://pages.example.test/local-recipes`, both flags on) -- exit 0.
  - **Browser** (headless Chromium through the `pyforge-herald` env's Playwright, the CAP-56 artifact served under
    `/local-recipes/`; the docs shelf `/how-to/`, the dossier and the overview, each in light and dark, on screen and
    with print media emulated): screen light and dark read Plex Sans body and Big Shoulders headings on every page, the
    paper / dark backgrounds, links and labels `#7d4b0d` light and `#dd9a3f` dark on docs and herald alike; in print
    every page -- the dark ones included -- resolves `--sl-color-white` `#1a2024` on `#f1f3ef`, the light block; no
    console error; every font request is `/local-recipes/_astro/*.woff2`.
- 2026-10-15 (independent review, iteration 1: FAIL, 2 should-fix and 9 nits; and the operator's ruling on should-fix
  2, the same day):
  - **Operator ruling 2026-10-15 (should-fix 2, typography): one typography and palette across all of GitHub Pages.**
    Starlight's `--sl-*` variables are the single theme contract, filled with the herald look; the coordinating
    session writes the Spec memlog entry at the reconcile. As built, with `pyforge.herald.pages_one_generator` on:
    `docs-site/src/styles/theme.css` sets `--sl-font`, `--sl-font-mono`, the accent, gray (1-7), white and black
    scales and the orange, green, blue, purple and red ones to the herald faces and palette, light under `:root` and
    dark under `[data-theme='dark']`, and imports the faces. Starlight loads it through `customCss`, gated in
    `astro.config.mjs` on the flag through `src/lib/flags.ts`, so the docs adopt it; `herald.css` imports it and
    declares no font or colour of its own -- the dossier's tokens derive from `--sl-*` in one block, so they follow the
    toggle with no dark block of their own; the reader pages link `/herald/theme.css` (the endpoint, renamed
    `[sheet].css.ts`, now serves `fonts.css` and `theme.css`) and their back-bar reads only `--sl-*`; the twins keep
    their own design and take only the faces. Re-theming is replacing `theme.css` (or a Starlight theme plugin with
    `theme.css` carrying its values for the herald pages, which load no Starlight stylesheet): `docs-site/README.md` §
    *Theme and fonts*. The Approach, the Always line, AC2's and AC3's wording and the docs-page I/O row are amended to
    match; the ACs' oracles are unchanged in kind.
  - **Readings of the ruling** (accepted as the defaults by the coordinating session, 2026-10-15; the operator may still overturn them). (a) The headings face is the dossier's, Big
    Shoulders Display, as `--sl-font-heading` -- this site's one addition to the contract, since Starlight has no
    headings variable; `theme.css` applies it to Starlight's page title and content headings (`h1#_top`,
    `.sl-markdown-content` h1-h4), and herald reads it with `--sl-font` as fallback. Archivo Expanded, which the
    coordinator's note named, is the Design twins' display face, and the twins are frozen exports, so it is not
    mapped. (b) Exact values: 24 of the dossier's 34 tokens are plain aliases resolving to the Jinja values in both
    themes; `--rail-faint`, `--code-bg`, `--st-doctor` and `--st-doctor-soft` take the nearest scale entry (a few
    units off); `--st-atlas` (green and blue), `--st-herald` (red and orange) and `--st-steward` (green and orange) are
    `color-mix()`es of two Starlight colours, and their softs a 16% tint over the page -- the eight station accents stay
    distinct (checked in the browser) but three move a little. (c) Light-mode docs links take
    `--sl-color-text-accent: var(--sl-color-accent-high)` (6.5:1 on the paper) because the herald amber reads 3.8:1;
    dark links already take the high accent. (d) `--sl-color-gray-7`, Starlight's light nav background, is the
    dossier's sunken paper, darker than gray-6.
  - **Should-fix 1, the untested matrix rows.** Flag off: `test_ac6_flag_off_astro_emits_none_of_the_three_page_kinds`
    now also asserts no herald stylesheet under `herald/`, no `.woff`/`.woff2` and no `herald*` file under `_astro/`,
    and no theme variable or `@font-face` in any stylesheet (Starlight's stock theme); disabling the emptying hook
    fails it (19 fonts listed). By hand, a flag-off `astro build` of this tree against `627c751b19`'s (`git archive`,
    the same `node_modules`): `diff -r` exit 0 over 177 files. Docs page, flag on: the built test
    (`test_43_4_ac1_ac3_ac4_the_built_pages_share_one_theme`) reads the unlayered `:root` and
    `[data-theme=dark]` rules of every stylesheet a shelf page (`how-to/`) and the dossier link and asserts the same
    `--sl-font*`, accent, gray, white and black values in both themes, and that no herald-only rule (`.station-mark`,
    `.site-nav-inner`, `.hero-eyebrow`, `text-transform:uppercase`) and no `_astro/herald.*.css` reaches the shelf.
  - **Nits.** 3: `_check_one_design_system` also reads each `<style>` body's faces and `@import`s, follows one
    `@import` level in a linked sheet, and reads unquoted `href`/`src`; four new fixture cases. A `style="--x:..."`
    attribute is still not judged (no page writes one). 4: `THEME_SCRIPT` is an IIFE with no global; the CSP hash
    follows the constant. 5: `theme.css` repeats the dark block under `@media (prefers-color-scheme: dark)
    { :root:not([data-theme]) }`, so with scripts off every page follows the system scheme (a test pins the two
    blocks equal). 6: the script re-applies on a system-scheme change and on `pageshow` (a back-forward-cache restore),
    as Starlight's ThemeSelect does; checked in the browser by emulating the scheme with the store on auto. 7: the
    flag-off emptying is keyed on the `src/styles/` directory, so `theme.css` and any later sheet there are emptied
    too. 8: the faces are declared by hand, woff2 only, from each package's `files/` (19 files; no `.woff` is emitted,
    roughly half the earlier weight). 9: `docs-site/README.md` records the five packages as OFL-1.1, and "Named, not
    fixed here" gives the licence text's carry-over to 43.7. 10: the endpoint comment no longer says "rest-shaped".
    11 (no automated base-path build): unchanged; the CAP-56 host `pages-check` exercises `/local-recipes/` faces.
  - **Story 43.3's Approach** carries a one-line pointer to its change-log correction (Astro only warns on a route over
    a public file), folded into this unit at the coordinator's request.
  - **Gates (2026-10-15, on `627c751b19` plus this change).** The Pages, parity, 43.6, zero-origin, validator,
    imports, site-URL, build and flag-state test files -- exit 0, 254 passed, none skipped (docs-site installed); the
    herald suite -- exit 0, 2129 passed, 5 skipped; `lint-types`, `docs-site-validate`, steward's trigger map -- exit
    0; `pages-check` with both flags off -- exit 0; with `pyforge.herald.pages_one_generator` and
    `pyforge.herald.status_pages` on and the 42.1 and 43.6 fixtures in `docsite/content/` (removed after) -- exit 0;
    the CAP-56 host (`https://pages.example.test/local-recipes`, both flags on) -- exit 0. Mutations, each restored: a
    literal colour in `herald.css` fails the no-literal test; `theme.css` without its dark block fails AC3's; the
    dossier body on `--sl-font-mono` fails AC2's; the flag-off emptying hook disabled fails the flag-off test (19
    fonts); a `fonts.googleapis.com` link planted in the built dossier -- `assemble_pages.py --check` exit 1 naming it,
    exit 0 restored. Browser, the flag-on build under `/local-recipes/`: a docs page (`/how-to/`) and the dossier in
    light and dark read Plex Sans body, Big Shoulders headings, the paper or dark background and the amber accent
    (`#b06a13` / `#dd9a3f`) alike; the docs toggle set Dark and the dossier, overview and a reader page followed; with
    the store on auto, emulating the system scheme flipped a reader page live; every font request is
    `/local-recipes/_astro/*.woff2`; no console error on the docs page, the dossier, the overview or a reader page.
- 2026-10-15: implemented (lane A of the one-PR Pages redesign); status `in-review`. Deviations and readings, each for
  the reviewer and the operator to keep or overturn:
  - **The twins and the reader pages take the same faces from one fixed URL.** The twins are static files in
    `public/` and the reader pages are endpoints, so neither can import a stylesheet Astro bundles under a hashed
    name. `src/pages/herald/[fonts].css.ts` serves `styles/herald-fonts.css` as Vite builds it (`?inline`) at
    `/herald/fonts.css`; every face it names is an `@fontsource` file under `_astro/`, the same files the layouts'
    bundle names. The twin's one vendored line (Story 43.2's ruling) now links `../../fonts.css` instead of the
    Jinja path's `assets/fonts/fonts.css`; `assemble_pages._VENDORED_FONT_LINK`, the twin diff's oracle, follows, and
    the old href is now refused (a `jinja-fonts` case). `HERALD_FONTS` in `src/lib/herald-pages.ts` names the path.
  - **"Maps onto Starlight's theme variables" is read as Starlight's theme selector and store, not its `--sl-*`
    values.** The tokens keep the dossier's own palette (AC3 asks for the dossier's tokens in two blocks; the test
    pins them to the Jinja values), defined light under `:root` and dark under `:root[data-theme='dark']`, the
    attribute the docs toggle sets. The herald pages carry no toggle and no store (Boundaries): `THEME_SCRIPT`,
    inline in each layout's head and allowed by its hash in `HERALD_CSP`, reads `localStorage['starlight-theme']`
    and resolves "auto" from the system scheme exactly as Starlight's `ThemeProvider` does. The Jinja path's
    `prefers-color-scheme` block is not ported (the script resolves auto; with scripts off a page is light), and
    each block sets `color-scheme` so form controls and scrollbars follow.
  - **The docs pages keep Starlight's typography and palette (the I/O matrix's docs row, "unchanged Starlight theme;
    fonts unaffected").** So the Approach's "one typography ... across every prefix" and the Verification's "showing
    one typography" screenshot are not reached between the docs and the dossier: the herald prefixes share one face
    set, one stylesheet and the docs' dark mode; the docs body stays Starlight's system stack. Taking the herald faces
    and palette onto the docs is one `customCss` entry pointing at `styles/herald.css`'s tokens, against that matrix
    row — **an open question for the operator**, not done here.
  - **The stylesheet** (`src/styles/herald.css`) is `_dossier.css`, `build.py`'s inline content-model additions and
    `_site-chrome.css` ported as they are, with the token blocks above; the back-bar's rules are left out (the reader
    pages carry their own inline `BACKBAR_STYLE`), and AC2's all-selector parity excludes them by name. Its copy of
    the Jinja CSS lives until Story 43.7 retires the originals.
  - **The faces** are the packages' own latin-subset declarations (`@fontsource/<family>/latin-<weight>`; the
    package export map resolves the specifier without `.css`), so each face also emits its `.woff` fallback: 18 woff2,
    18 woff and the variable wdth woff2 under `_astro/` (with the CSS, 808 KB). Archivo Expanded is the one face
    declared by hand -- npm publishes no package of that name -- from `@fontsource-variable/archivo`'s
    `archivo-latin-wdth-normal.woff2` at `font-stretch: 125%`, as `fonts.css` and Story 30.3's decks declare it. Of the 19
    vendored woff2 files (Story 31.3, from the 5.2.x packages), 16 are byte-identical to the 5.3.0 packages'; the
    three IBM Plex Mono weights differ in bytes (5.2.5 against 5.3.0), same family, weights and subset.
  - **Flag off, nothing changes.** Astro emits a page module's imports whether or not a route renders, so the first
    flag-off build carried 38 unreferenced herald files in `_astro/`; the `herald-artifact` integration now loads the
    two herald stylesheets empty with the flag off (a Vite `load` hook), and the flag-off output is byte-identical
    to the base (Verification run).
  - **`pages-check` enforces AC1, AC3 and AC4 on the real artifact** (`assemble_pages._check_one_design_system`, flag
    on): each `@font-face` in a stylesheet a herald page or twin links names a file under `_astro/`, nothing links
    `herald/assets/`, and no herald page but a twin carries a custom property in a `<style>` of its own. The herald
    lane installs no docs-site, so the Astro-built test skips there, as Story 43.2's review found for the parity.
  - **`docsite/build.py --check` with the flag on judges only its own outputs** (`.nojekyll`, `assets/`, `artifact/`):
    Astro's `herald/fonts.css` names base-absolute `_astro/` URLs the Jinja check cannot resolve (pages-check judges
    them). Flag off it reads every file, as before (`test_43_4_with_one_generator_check_judges_only_its_own_outputs`).
  - **`build.py` still writes `herald/assets/`** (`site.css`, the vendored fonts) with the flag on: the Jinja-rendered
    status and pipelines pages link it (Stories 42.1 and 43.6 move them); no herald page does now (AC4).
  - Smaller: `test_docs_site_imports_tracked.py` drops a Vite query (`?inline`) before resolving an import; AC6's test
    reads every row of `docs-site/README.md`'s table (seven, the five named among them); `docs-site/README.md` lists
    the new local files and the font packages, and `docsite/README.md` notes that the flag-on herald pages no longer
    use `assets/fonts/`.
- 2026-10-14: specced at mint from Epic 43's Story 43.4 text, `spec-pyforge-herald` CAP-61, FR-12.4 and the Dream's
  2026-10-13 entry (M3), against `docsite/assets/` and `docs-site/package.json` as they stand on 2026-10-14. The five
  `@fontsource` package names are Epic 43's.
