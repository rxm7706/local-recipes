# The PyForge Pages site (local-recipes)

The one generator of the GitHub Pages artifact (herald Story 43.7, spec-pyforge-herald CAP-61; AD-21, AD-23):
Astro + Starlight build the Diátaxis shelf under `docs/` in place via a symlink, herald's dossier, gallery and deck
families under `/herald/`, the status pages under `/status/`, the changes page and the machine surfaces, and mount
the dashboard exports under `/dashboard/` -- one build, `docs-site/build/site/`, deployed by `pages.yml`. Herald's
second generator, `docsite/` (Jinja), retired in Story 43.7; its still-true content is below.

## Upstream vendoring (MIT)

Vendored byte-identically from [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) at commit `561eeedf386bc7cb164c577c423dc4484056a759` (2026-09-27 baseline).

© 2025 BMad Code, LLC — MIT License (see upstream `LICENSE`).

| File | sha256 |
|------|--------|
| `.nvmrc` | `68ca3fba3b7e864770cb61aeb306d4bd4354b68ab4dd38450860c5d823e42a53` |
| `scripts/fix-doc-links.js` | `137086840431f3026352609cd59922483d3a36375df3bb5bbce5f44b45c0eef8` |
| `scripts/validate-doc-links.js` | `116a18e8f8cfbd9695acb07eb1d0833680000aba0de60a312a1f2d46817d2642` |
| `scripts/validate-sidebar-order.js` | `fddb0234166b72340ce994add14ad75cd0fef1824504c6af214563da0d7e4db5` |
| `src/lib/site-url.mjs` | `734c233ba2d1e601771caf05b55a99d3db35576fe0305e8e341e5e18daeb3520` |
| `src/rehype-base-paths.js` | `5460b6e911153c59694d8081949508751d4832a0cf5a7a33df2076ce3cfc5f7b` |
| `src/rehype-markdown-links.js` | `15ece2fa9bebee02fa908d44620fc3d62f569509f5448f6f3aca163c0e7fe534` |

## Local-only files

These files are maintained in this repository and are **not** byte-identical to upstream:

- `package.json` / `package-lock.json` — trimmed scripts; same Astro/Starlight dependency ranges; the five
  `@fontsource` packages the site's faces come from (Story 43.4; OFL-1.1, see *Theme and fonts* below)
- `astro.config.mjs` — `SITE_URL`/`base`, the sidebar from the registry, the `SiteTitle`, `Footer` and
  `MarkdownContent` overrides, no locales, and the `herald-artifact` integration (see *The build* below)
- `src/lib/nav.ts`, `src/lib/site-nav.ts` — **one registry** (Story 43.7, doctor CAP-90): `docs/map.yaml`'s `pages`
  give the docs sidebar its four quadrant groups, and its `sections` give the sidebar, the top menu every page carries
  (`src/components/SiteTitle.astro`, `src/layouts/Herald*.astro`) and the home's doors
  (`src/components/MarkdownContent.astro`) their entries, in `order`. The docs shelf is the root and no row; its entry
  comes first. A section whose `href` is a mounted export (`dashboard/kedro-viz/`, `dashboard/vizro/`) shows only
  when the export is in the build input, and `status` only with `pyforge.herald.status_pages` on. A map without
  `sections` fails the build naming the key; `scripts/nav-check.mts` (`docs-site-validate-sidebar`) checks the map
  against `docs/` without building
- `src/content/` — the generator's content (Story 43.7 moved it here from `docsite/content/`):
  `dossier/dossier.yml` (the dossier, see *Editing the dossier*), `site.yml` (the infographics to publish, the
  overview's tiles, Lane 1's link, the artifact URL; no menu), `ci-status.json` (CAP-59's committed snapshot), and
  the gitignored Guild-step build inputs `fleet-status.json`, `changes.json`, `marshal-status.json` and
  `herald-progress.json` (`PAGES_BUILD_INPUTS_DIR` points elsewhere). `src/content/docs` is the shelf's symlink
- `src/content.config.ts` — the shelf collection and the dossier collection (block types; every section's
  `measured:` date)
- `src/loaders/shelf-docs-loader.ts` — titles from frontmatter or first `#` heading; `README.md` → quadrant index;
  heading deduplication; renders each page's markdown with the project's rehype plugins (Story 44.1: before it, every
  page body rendered empty)
- `src/lib/shelf.mjs` — the one rule for which `docs/` files are pages, read by the loader and the link plugin
- `src/rehype-shelf-links.js` — runs before the two vendored link plugins: points `README.md` links at the directory
  index and sends links to repo files the shelf does not publish (`docs/MAP.md`, `docs/governance/**`, anything
  outside `docs/`) to their repository page
- `src/pages/herald/`, `src/layouts/Herald*.astro`, `src/components/{dossier,herald}/`, `src/lib/herald-pages.ts`,
  `src/loaders/{dossier,herald-pages}-loader.ts` — the herald pages (Epic 43)
- `src/pages/status/`, `src/lib/status.ts` — the fleet board (`/status/`, from `fleet-status.json`), the guild status
  page (`/status/ci/`, from `ci-status.json`) and the runs page (`/status/runs/`), with `pyforge.herald.status_pages`
  on (Stories 42.1, 43.6; ported from the Jinja path by 43.7); `status.ts` also shapes the dossier's CI surfaces tile
  with `pyforge.herald.ci_surfaces_tile` on. A missing or malformed input fails the build naming the file. The
  attention block says "nothing needs attention" only when every station counts 0 blocked and 0 backlog, and names
  each station whose listed rows differ from its own count. Lane 1 is linked only once `site.yml`'s `lane1.href` is an
  absolute URL (herald deferred-work row `DW-herald-42-1-1`)
- `src/lib/flags.ts` — the one reader of the build flags, `PYFORGE_STATUS_PAGES` and `PYFORGE_CI_SURFACES_TILE`,
  which the Guild env exports (`python -m pyforge.herald.pages_env`)
- `src/styles/theme.css`, `src/styles/herald-fonts.css`, `src/styles/herald.css` — the site theme, its faces and the
  herald pages' stylesheet (Story 43.4 and its review; see *Theme and fonts* below); `src/pages/herald/[sheet].css.ts`
  serves the faces at `/herald/fonts.css` (the twins' one link) and the theme at `/herald/theme.css` (the reader pages)
- `src/lib/built-from.ts`, `src/components/Footer.astro` — the line every page carries saying what built it (Story
  43.5): `GITHUB_SHA`'s first seven, the build time (`PAGES_BUILT_AT`, which `pages-build` sets once per build) and
  `GITHUB_RUN_ID`, or `local build`; the docs take it under Starlight's footer, the herald layouts and reader pages
  below the page. Steward's Pages tree hash reads every HTML file without that element's text, so a rebuild of an
  unmoved tree deploys nothing; the markup, steward's `BUILT_FROM_TEXT` and `pages-check` change together. No page
  keeps a date or commit stamp of its own (Story 43.7: a download without a stamp sidecar shows `unstamped` and its
  content hash, never the build's commit)
- `src/loaders/dossier-loader.ts` also runs `scripts/verify_claims.py --emit` (Story 43.5; `$HERALD_PYTHON`, else the
  `python` on `PATH` with PyYAML, as the `site` env provides): every `check:` stat shows the measured value, and each
  section's required `measured:` date renders as "measured on"
- `redirects.json` — the frozen root redirects: the 44 legacy paths and `/kedro-viz/` (Story 43.3; never hand-grown)
- `src/lib/redirects.ts` — writes the legacy redirects into the build, refusing a path the build already holds, and
  fails the build when a route's output is a file `public/` serves (Astro itself only warns)
- `scripts/populate-public.mts` — the only writer of `public/` (gitignored), run at every build's start: the twins,
  the family downloads, every entry of `docs/dashboard/` but its README (an export only when present), the font
  licences and `favicon.svg`
- `src/lib/artifact.ts` — at build end, every page's CSP (see *The build*) and the artifact build of the dossier
- `src/lib/agent-surface.ts`, `src/lib/agent-data.ts` and the pages `src/pages/[llms].txt.ts`, `src/pages/[facts].json.ts`,
  `src/pages/changes/` — herald Story 43.6's machine surfaces: `/llms.txt` and `/llms-full.txt` (`docs/map.yaml`'s
  pages, its `herald` section and every gallery infographic and deck family with its text, Story 43.7),
  `/facts.json` (every `presentations/<slug>/facts.yaml`) and `/changes/` with `/changes/rss.xml`. The changes and
  runs pages read their gitignored build inputs under `src/content/`; an absent input is one line on the page, a
  malformed one fails the build naming the file
- `scripts/pages.mts` — `pages-build` and `pages-check` (see *The build*)
- `scripts/origin_check.py` — `pages-check`'s origin rule (AD-21), run by `scripts/pages.mts`
- `scripts/verify_claims.py` — the dossier's one measurer (CAP-46), moved here from `docsite/tools/` by Story 43.7;
  the bespoke Python under `docs-site/` stays under 300 lines (AD-23)

## The build

```bash
pixi run -e site pages-build   # node scripts/pages.mts build: the artifact at docs-site/build/site/
pixi run -e site pages-check   # pages-build, then node scripts/pages.mts check: the one build check
pixi run -e site docs-site-validate   # the vendored link and sidebar-order validators and the map check
```

`pages-build` resolves the site URL the way `actions/configure-pages` hands it over (`PAGES_HOST_BASE_URL` and
`PAGES_HOST_BASE_PATH`, else the public github.io URL; an empty base path is a root-hosted site), sets
`PAGES_BUILT_AT` once in the build's own environment, and runs `npm run build`. The `herald-artifact` integration
(`astro.config.mjs`) writes `public/` before the build and, after it, the legacy redirects, the artifact build of the
dossier and every page's CSP.

`pages-check` judges the artifact: every path it must hold (`/`, `/herald/` with its dossier, gallery, decks and
artifact build, `/llms.txt`, `/llms-full.txt`, `/facts.json`, `/changes/` and its feed, and `/status/`, `/status/ci/`
and `/status/runs/` exactly with `pyforge.herald.status_pages` on); `dashboard/` exactly the build input's mount, a
mounted Kedro-Viz export with its manifest and its `/kedro-viz/` redirect under the base path, a mounted Vizro export
with its index and manifest; the 44 legacy redirects landing on their targets; one `Content-Security-Policy` meta and
one built-from line on every page, all naming one build; the feed and `facts.json` parsing; every local link of every
page resolving inside the artifact under the base path (the 404 page's links absolute); a non-empty body on every
shelf page; the same menu on every navigable page; every face a file under `_astro/`; and nothing loading from
another origin (`scripts/origin_check.py`; the vendored Kedro-Viz root and the Vizro export's `plotly.min.js` exempt
by name, AD-21 rule 5).

**The CSP of every page** (Story 43.7): the herald layouts and reader pages write `HERALD_CSP` themselves
(`src/lib/herald-pages.ts`'s `cspWith`); every Starlight page -- the shelf, `/changes/`, `/status/**`, the 404 -- gets
the same policy at build end, its own inline scripts allowed by hash and `'wasm-unsafe-eval'` for the Pagefind search
(`src/lib/artifact.ts`). Redirect stubs, the twins, the artifact build and the mounted `dashboard/` tree carry none.

**The artifact build** `herald/artifact/dossier.html` (CAP-47) is the built dossier page made single-file for the
Claude Artifact tool: its title, its stylesheets inlined with the three faces it reads as data URIs, and its body.
The Artifact host supplies `<!doctype>`, `<html>`, `<head>` and `<body>` itself and wraps whatever it is given, so
the file carries none of them. **Session close:** after `pixi run -e site pages-build`, republish **The PyForge
Dossier** in the Artifact tool from `docs-site/build/site/herald/artifact/dossier.html`, so the shared dossier link
(`site.yml`'s `artifact.url`) stays current.

The status pages with the flag on, from the live ledgers (steward Story 102.3 writes the input, then runs
`pages-check`) or from the fixture:

```bash
PYFORGE_STATUS_PAGES=1 pixi run -e pyforge-guild pyforge steward pages build
cp src/shared/packages/pyforge-herald/tests/fixtures/fleet-status-2026-10-14.json docs-site/src/content/fleet-status.json
PYFORGE_STATUS_PAGES=1 pixi run -e site pages-check
```

A PR touching the four Diátaxis quadrants under `docs/`, `docs/index.md`, `docs/404.md`, `docs/map.yaml`,
`docs/dashboard/**`, `docs-site/**`, `presentations/**` or the build's own `scripts/pages_*.py` runs `pages-check` and
`docs-site-validate` in CI (the `build` job of `.github/workflows/pages.yml`); `pixi run -e pyforge-guild
pr-preflight` selects the same two from the same paths.

## Editing the dossier

Open `src/content/dossier/dossier.yml`. It is a list of sections, each a list of typed blocks. To change a sentence,
find the sentence and change it. The dossier's content lives in this file, and everything else is a render of it: the
Pages site and the Claude artifact are both renders, and neither is edited by hand.

Fifteen block types exist — `lede`, `prose`, `h3`, `table`, `callout`, `finding`, `stats`, `quote`, `relations`,
`lattice`, `engines`, `chips`, `note`, `verify`, `ci_surfaces` -- each rendered by one function,
`src/lib/dossier-blocks.ts`, which the site and the artifact build share, so they cannot drift apart.

Text fields take a small inline-Markdown subset (`src/lib/md-inline.ts`):

| Write | Get |
|---|---|
| `` `x` `` | `<code>x</code>` |
| `**x**` | bold |
| `*x*` | italic |
| `[x](url)` | link |
| `<<→>>` | a relation arrow |
| `\*` `` \` `` | a literal `*` or backtick |

That last row matters more than it looks: this repository's prose genuinely contains things like `recipes/**` and
`0*`, and without the backslash they get eaten as Markdown syntax.

**The numbers.** A stat is measured only when it says so, and then it shows what the source tree counts, never its
typed value:

```yaml
- value: "30,847"          # ignored on the page: the measured value shows
  label: Lines · 115 files # the file count is the measured one
  check: src_lines         # src_lines | test_lines | python_floor (fleet_src_lines for the hero's total)
```

Stats without a `check:` key show their typed value: inferring which stats were checkable from their labels was tried
first and got it wrong in both directions ("Pipelines wired to MCP" contains the word "line"; "Lines added since last
pass" is a delta, not a total). Each section's `measured:` date is the day its prose was last checked against the
tree. The refresh is: code changes; the measured numbers follow at the next build; someone updates the prose and the
`measured:` dates in `dossier.yml` (human, or a Claude session pointed at the repo, because the interesting drift is
never only numeric); push, and the workflow rebuilds and deploys.

**The CI surfaces snapshot** (Story 39.1; the operator, with an authenticated `gh` and
`pyforge.steward.ci_pause_control` on for the run):

```bash
pixi run --frozen -e pyforge-guild pyforge steward ci status --json > docs-site/src/content/ci-status.json
```

Commit the file only from an exit-0 run; the dossier tile reads it with `pyforge.herald.ci_surfaces_tile` on, and the
guild status page with `pyforge.herald.status_pages` on.

## Adding or removing an infographic

Edit `infographics.include` in `src/content/site.yml` — a list of globs relative to the repo root. Every matching
`.html` file is published as its own page and listed in the gallery, and each one under `presentations/<slug>/` gets a
deck family page. Titles come from each file's own `<title>` tag; to override a title, add a description or set the
gallery order, add an entry under `infographics.overrides` keyed by the file's repo-relative path. The source files are
**never modified**: each is served as a twin with its Google Fonts links swapped for the site's own faces, framed by a
reader's page that carries the back-bar.

## Theme and fonts

One theme for every page of the site (operator ruling 2026-10-15):

- **The contract is Starlight's theme variables.** `src/styles/theme.css` sets `--sl-font`, `--sl-font-mono`, the
  `--sl-color-accent-*`, `--sl-color-gray-*`, `--sl-color-white` / `--sl-color-black` scales and the orange, green,
  blue, purple and red ones, light under `:root` and dark under `[data-theme='dark']` (the attribute Starlight's theme
  toggle sets; with scripts off the system scheme picks), the dark blocks for the screen only so a page prints light,
  plus this site's one addition, `--sl-font-heading`, the display face for headings. `--sl-color-text-accent` is the
  one accent text colour, every link and the herald's small amber labels alike (the darker amber on light, the amber
  on dark; AA on both). It imports the faces, `src/styles/herald-fonts.css`.
- **Who reads it.** The docs, through Starlight's `customCss` (`astro.config.mjs`); the herald pages, through
  `src/styles/herald.css`, which imports it and declares no font or colour of its own -- the dossier's tokens are
  derived from the `--sl-*` variables; the reader pages, through `/herald/theme.css`. The herald pages read the toggle's
  choice from Starlight's own store (`THEME_SCRIPT`, `src/lib/herald-pages.ts`). The Design twins keep their own design
  and take only the faces (`/herald/fonts.css`).
- **Re-theming the site** is editing or replacing `theme.css`: change its values, keeping the variable names, and the
  docs and the herald pages follow together; a test (`test_docsite_zero_origin.py`) fails if any file under `src/`
  but `theme.css`, `herald-fonts.css` and `content/` names a font or colour of its own -- in a CSS declaration (nested
  rules included), a `<style>` body, a `style` attribute, a colour attribute (SVG `fill` / `stroke` ..., `color`,
  `bgcolor`), a `<font face>` or the `theme-color` meta -- or sets a `--sl-*` variable (`theme.css` is the contract's
  only writer); and `cssVar()` (`src/lib/md-inline.ts`) refuses a YAML colour that is not a theme token. Out of the
  test's reach, so a reviewer reads these: a style built by string concatenation or held in a variable,
  `el.style` / `setAttribute('style', ...)` in a script, `<style set:html>`, an escaped quote inside a TS string, CSS
  escapes and an SVG data URI. To use a Starlight theme plugin instead, add it to `starlight({ plugins: [...] })` for
  the docs and replace `theme.css`'s two blocks with the values the plugin sets: the herald pages do not load
  Starlight's stylesheets, so they read the variables from `theme.css` alone.
- **Fonts.** Big Shoulders Display, IBM Plex Sans, IBM Plex Mono and Archivo (with Archivo Expanded, the 125% width of
  the variable Archivo) come from `@fontsource/big-shoulders-display`, `@fontsource/ibm-plex-sans`,
  `@fontsource/ibm-plex-mono`, `@fontsource/archivo` and `@fontsource-variable/archivo` 5.3.0, latin woff2 files only,
  bundled under `_astro/`. All five are under the SIL Open Font License 1.1: each package's own `LICENSE` ships in the
  artifact at `/fonts/<package>.LICENSE.txt` (`scripts/populate-public.mts` copies it at every build, Story 43.7), the
  licence travelling with the faces and never vendored by hand.

## Layout

```
docs/                          # shelf content (repo root); docs/map.yaml is the one registry
docs-site/
  src/content/docs -> ../../../docs
  src/content/                 # the dossier, site.yml, ci-status.json; the gitignored build inputs
  public/                      # gitignored; written by scripts/populate-public.mts
  build/site/                  # gitignored build output: the Pages artifact
```
