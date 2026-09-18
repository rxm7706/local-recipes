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
| `infographics/<slug>.html` | Each infographic, published unmodified |
| `decks/index.html` | Index of every deck family page, with lazy-loaded live previews |
| `decks/<slug>/index.html` | One family page per registered deck: poster, Infographic Deck and Executive Summary in view; PPTX(s) and Marp sources as downloads |
| `artifact/dossier.html` | Single-file build for the Claude Artifact tool |
| `assets/site.css` | Shared stylesheet |

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
