# The PyForge site

The dossier and the standalone infographics, published together as one
GitHub Pages site — and rebuilt from this repository every time either changes.

```
docsite/
  content/
    dossier.yml        ← the dossier itself. This is the source of truth.
    site.yml           ← which infographics to publish, nav, artifact URL
  templates/           ← Jinja2: one macro per content block type
  assets/              ← the dossier stylesheet + the site-only chrome
  tools/
    verify_claims.py   ← checks the dossier's numbers against the source tree
    import_artifact.py ← one-time migration from the published artifact
  build.py             ← renders everything
```

## The one idea

**The dossier's content lives in `content/dossier.yml`, and everything else is a
render of it.** The GitHub Pages site is a render. The standalone Claude artifact
is a render. Neither is edited by hand.

Before this, the dossier lived only inside a published artifact — which meant
"update the dossier" and "update the site" were two separate acts of copying,
and they drifted. Now there is one file to edit and one command to run.

## Rebuilding

```bash
pixi run site          # build into dist/
pixi run site-check    # build + verify the output
pixi run site-verify   # check the dossier's numbers against the source tree
pixi run site-serve    # build and serve at http://localhost:8000
```

The GitHub Pages deploy assembles one artifact (Story 27.2):

```bash
pixi run -e site pages-build   # Starlight + mount under herald/ + dashboard/ + legacy redirects
pixi run -e site pages-check   # pages-build + verify redirects and in-artifact links
```

Published layout: Starlight docs at `/`, the dossier site at `/herald/…`, Kedro-Viz at
`/dashboard/kedro-viz/`, and HTML redirect stubs at the old dossier root paths (for example
`/dossier/` → `/herald/dossier/`).

A PR touching `docs/**`, `docs-site/**`, `docsite/**`, `docs/dashboard/**`, `presentations/**`
or `pixi.toml` runs `pages-check` in CI (`.github/workflows/docsite-check.yml`);
`pixi run -e pyforge-guild pr-preflight` still runs the local `dist/` `site-check` leg unchanged.

Or without pixi:

```bash
python docsite/build.py --check
```

Outputs land in `dist/` (gitignored):

| Path | What it is |
|---|---|
| `index.html` | Landing page |
| `dossier/index.html` | The full dossier |
| `infographics/index.html` | Gallery, with lazy-loaded live previews |
| `infographics/<slug>.html` | Each infographic, published with the gallery back-bar and vendored font links (sources under `presentations/` are never edited) |
| `decks/index.html` | Index of every deck family page, with lazy-loaded live previews |
| `decks/<slug>/index.html` | One family page per registered deck: poster, Infographic Deck and Executive Summary in view; PPTX(s) and Marp sources as downloads |
| `artifact/dossier.html` | Single-file build for the Claude Artifact tool |
| `assets/site.css` | Shared stylesheet |
| `assets/fonts/` | Self-hosted `@font-face` bundle (`fonts.css` plus woff2 files) |

## Vendored fonts (`assets/fonts/`)

Every face the shells and published Design-twin copies use is self-hosted here. The build
copies this directory into `dist/assets/fonts/` and never fetches at build time.

| File | Source | Licence | sha256 |
|------|--------|---------|--------|
| `assets/fonts/big-shoulders-display-latin-600-normal.woff2` | `@fontsource/big-shoulders-display@5.2.5` | OFL-1.1 | `448000586ef3a91726a8de46e2948e7426d693d57a568a188006407d24409845` |
| `assets/fonts/big-shoulders-display-latin-700-normal.woff2` | `@fontsource/big-shoulders-display@5.2.5` | OFL-1.1 | `d2d55115d0d7047ce956d4eb8f2fbfe7915552cf4fabb294a5979705ec9687ac` |
| `assets/fonts/big-shoulders-display-latin-800-normal.woff2` | `@fontsource/big-shoulders-display@5.2.5` | OFL-1.1 | `088f423f09136bc96b5a7cc7232d671a1ad06a5ff1cf90cd1e24a8d9809d471c` |
| `assets/fonts/big-shoulders-display-latin-900-normal.woff2` | `@fontsource/big-shoulders-display@5.2.5` | OFL-1.1 | `65f2c368034258382e77672f083d9f42e805d23d557432517a1b5a4f75c21f1a` |
| `assets/fonts/ibm-plex-sans-latin-400-normal.woff2` | `@fontsource/ibm-plex-sans@5.2.6` | OFL-1.1 | `3b646991d30055a93a4ecc499713d4347953a74a947ecab435ab72070cbdab0e` |
| `assets/fonts/ibm-plex-sans-latin-500-normal.woff2` | `@fontsource/ibm-plex-sans@5.2.6` | OFL-1.1 | `0717336fb31fcdcde4b8deb3675bb4a0f7f6d484864afcd6751ac29975962203` |
| `assets/fonts/ibm-plex-sans-latin-600-normal.woff2` | `@fontsource/ibm-plex-sans@5.2.6` | OFL-1.1 | `8960851d691c054ed38e259bdcf1a6190d157b4203ed5bb32c632a863fb8ec2f` |
| `assets/fonts/ibm-plex-sans-latin-700-normal.woff2` | `@fontsource/ibm-plex-sans@5.2.6` | OFL-1.1 | `42e7b0c143c19df9d99fd896e76b48f846edf0902d200bc29796b34d12c33aa7` |
| `assets/fonts/ibm-plex-sans-latin-400-italic.woff2` | `@fontsource/ibm-plex-sans@5.2.6` | OFL-1.1 | `6de912e531b6c98084f1b2d5e5a91bad77be4e68bc4e396e43c46fc435e5f3d9` |
| `assets/fonts/ibm-plex-mono-latin-400-normal.woff2` | `@fontsource/ibm-plex-mono@5.2.5` | OFL-1.1 | `3c5a451f9ec27a354b0c2bcca636c6ec17a651281aabf29f8427e210a1d31e85` |
| `assets/fonts/ibm-plex-mono-latin-500-normal.woff2` | `@fontsource/ibm-plex-mono@5.2.5` | OFL-1.1 | `756026ff72eb76fd971ac4b7504cec55eef62109d2684c2cad8da32170b80b37` |
| `assets/fonts/ibm-plex-mono-latin-600-normal.woff2` | `@fontsource/ibm-plex-mono@5.2.5` | OFL-1.1 | `c4d3deb734a27e6d0dc7a6b464779f70ba1c272e26287860a14e35e85acb5b76` |
| `assets/fonts/archivo-latin-400-normal.woff2` | `@fontsource/archivo@5.2.6` | OFL-1.1 | `07f9160163da2ec0f6376ef9d27a2bb8163f98019ba798da4baafb154e30056e` |
| `assets/fonts/archivo-latin-500-normal.woff2` | `@fontsource/archivo@5.2.6` | OFL-1.1 | `ab74eca5ad115fe4cfec82ba641e5d37e4d92c58dfb1bfc1e464e9039c9d17cf` |
| `assets/fonts/archivo-latin-600-normal.woff2` | `@fontsource/archivo@5.2.6` | OFL-1.1 | `d9e8c29fdd348edde2a4f9aae438e569dd165bbbdebda78495824a2d9aaa67e8` |
| `assets/fonts/archivo-latin-700-normal.woff2` | `@fontsource/archivo@5.2.6` | OFL-1.1 | `abada6cd4c92a9a706f6d7ed3189f322ff43dd78b9402c7d1137465b861d2a04` |
| `assets/fonts/archivo-latin-800-normal.woff2` | `@fontsource/archivo@5.2.6` | OFL-1.1 | `c26cda2400b374eb1adb6e0973c86f455e2df17ca57c6755eb37d7bde47663fb` |
| `assets/fonts/archivo-latin-900-normal.woff2` | `@fontsource/archivo@5.2.6` | OFL-1.1 | `e915040a27c5310623be7ae57b6e4c508e8800206dcc37abe99984510e74a66d` |
| `assets/fonts/archivo-expanded-latin-wdth-normal.woff2` | `@fontsource-variable/archivo@5.2.6` (wdth axis, `font-stretch: 125%` → **Archivo Expanded**) | OFL-1.1 | `e3a28eade21a900c7155a247757f4b2834c07bb7ef07ad7efa55cebaac1e8f5e` |
| `assets/fonts/fonts.css` | generated `@font-face` bundle | — | `a59dcd183c2cb0d9270d17662d70344e684ea2796c16cee6fbefab63163a053e` |
| `assets/fonts/OFL-big-shoulders-display.txt` | `@fontsource/big-shoulders-display@5.2.5` (`LICENSE`) | OFL-1.1 | `18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3` |
| `assets/fonts/OFL-ibm-plex-sans.txt` | `@fontsource/ibm-plex-sans@5.2.6` (`LICENSE`) | OFL-1.1 | `18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3` |
| `assets/fonts/OFL-ibm-plex-mono.txt` | `@fontsource/ibm-plex-mono@5.2.5` (`LICENSE`) | OFL-1.1 | `18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3` |
| `assets/fonts/OFL-archivo.txt` | `@fontsource/archivo@5.2.6` (`LICENSE`) | OFL-1.1 | `18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3` |
| `assets/fonts/OFL-archivo-expanded.txt` | `@fontsource-variable/archivo@5.2.6` (`LICENSE`) | OFL-1.1 | `18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3` |

## Editing the dossier

Open `content/dossier.yml`. It is a list of sections, each a list of typed
blocks. To change a sentence, find the sentence and change it.

Fourteen block types exist — `lede`, `prose`, `h3`, `table`, `callout`,
`finding`, `stats`, `quote`, `relations`, `lattice`, `engines`, `chips`,
`note`, `verify`. Each has exactly one macro in
`templates/blocks.html.j2`, used by both the site and the artifact, so they
cannot drift apart.

Text fields take a small inline-Markdown subset:

| Write | Get |
|---|---|
| `` `x` `` | `<code>x</code>` |
| `**x**` | bold |
| `*x*` | italic |
| `[x](url)` | link |
| `<<→>>` | a relation arrow |
| `\*` `` \` `` | a literal `*` or backtick |

That last row matters more than it looks: this repository's prose genuinely
contains things like `recipes/**` and `0*`, and without the backslash they get
eaten as Markdown syntax.

## Adding or removing an infographic

Edit `infographics.include` in `content/site.yml` — a list of globs relative to
the repo root. Every matching `.html` file is published as its own page and
listed in the gallery.

Titles come from each file's own `<title>` tag. To override a title, add a
description, or set the gallery order, add an entry under
`infographics.overrides` keyed by the file's repo-relative path.

The source files are **never modified**. The only thing the build adds is a
small fixed back-link bar injected after `<body>`.

## Keeping the numbers honest

`tools/verify_claims.py` measures the source tree — lines, files, test ratios,
Python floors — and compares it against the stat rows in `dossier.yml`. It
reports anything that has drifted more than 5%.

A stat is only checked if it says so:

```yaml
- value: "30,847"
  label: Lines · 115 files
  check: src_lines      # src_lines | test_lines | python_floor
```

Stats without a `check:` key are ignored. That is deliberate — inferring which
stats were checkable from their labels was tried first and got it wrong in both
directions ("Pipelines wired to MCP" contains the word "line"; "Lines added
since last pass" is a delta, not a total).

The check runs in CI on every push as an **advisory** step. It annotates and
never blocks a deploy, because deciding what a number should *say* is
editorial — but noticing that it is wrong no longer depends on anyone
remembering to look.

## How a refresh actually happens

1. **Code changes.** Someone ships a story; the stations grow.
2. **`verify_claims.py` notices** on the next push and annotates the run with
   every figure that has drifted.
3. **Someone updates `dossier.yml`** — the prose as well as the numbers. This
   step is human (or a Claude session pointed at the repo), because the
   interesting drift is never only numeric. The 2026-09-13 pass found that a
   whole dashboard code path had been deleted and that a second station had
   started hosting an MCP server. No script infers that.
4. **Push.** The Action rebuilds and deploys the site.
5. **Republish the artifact** from `dist/artifact/dossier.html` if the shared
   dossier link should move in step.

Steps 1, 2, 4 are automatic. Step 3 is the judgment call, and it is supposed
to be.

## Why the artifact build has no `<html>` tag

The Claude Artifact host supplies `<!doctype>`, `<html>`, `<head>` and `<body>`
itself and wraps whatever you give it. `templates/shell_artifact.html.j2`
therefore emits only a `<title>`, the font links, an inlined `<style>`, and the
body content. `build.py --check` asserts this, because getting it wrong
produces a page that renders subtly wrong rather than failing loudly.
