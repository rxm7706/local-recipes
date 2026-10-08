---
title: '31.3: The public Pages build loads no third-party resource from herald''s own pages'
type: 'fix'
created: '2026-10-08'
status: 'done'
difficulty: 'medium'
baseline_revision: '330351a7133ea44719ebbffbddad99b225d1493d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-31-1-the-pages-artifact-builds-for-the-host-that-deploys-it.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-30-1-a-deck-s-html-twins-are-self-contained-and-published.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md
  - docsite/build.py
  - docsite/README.md
  - docsite/content/site.yml
  - docsite/templates/shell_page.html.j2
  - docsite/templates/shell_artifact.html.j2
  - docsite/assets/_site-chrome.css
  - src/shared/packages/pyforge-herald/src/pyforge/herald/twins.py
  - src/shared/packages/pyforge-herald/tests/unit/test_docsite_build.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every page herald contributes to the public Pages site (`/herald/`) loads Google Fonts, and AD-21 as amended
on 2026-09-28 (CAP-56, FR-10.5) says no stylesheet or font in the artifact may name another origin.

- **Measured on the real artifact.** Story 31.1's cross-origin `pages-check` (on `dispatch/pyforge-herald/31.1`, not on
  `main`) finds 135 references, all under `herald/`, in 45 pages: `herald/index.html`, `herald/dossier/index.html`,
  `herald/artifact/dossier.html`, 11 under `herald/infographics/` and 31 under `herald/decks/`. Each page carries one
  stylesheet from `fonts.googleapis.com` and two `rel="preconnect"` hints, one to `fonts.googleapis.com` and one to
  `fonts.gstatic.com`. That check counts a preconnect as a load, so a page is clean only when all three are gone.
- **Measured locally on `8a2da2c010` (2026-10-08).** `pixi run --frozen -e site python docsite/build.py --out
  <scratch>` writes 45 HTML pages. `pyforge.herald.twins.scan_tree` over that output finds the same 135 references
  (90 to `fonts.googleapis.com`, 45 to `fonts.gstatic.com`) in all 45 pages, and no other origin.
- **Two kinds of source emit them.**
  - *The docsite shells (15 pages).* `docsite/templates/shell_page.html.j2:13-15` (the landing page, the dossier, the
    gallery, the decks index and the ten family pages) and `docsite/templates/shell_artifact.html.j2:6-8`
    (`artifact/dossier.html`) each carry the two preconnects and one stylesheet for Big Shoulders Display (600-900), IBM
    Plex Sans (400-700, italic 400) and IBM Plex Mono (400-600). `docsite/assets/_site-chrome.css` names those
    families (`:20`, `:27`, `:116` and others).
  - *The published Design-twin copies (30 pages).* `publish_infographic` (`build.py:197`) copies each
    `presentations/<slug>/project/*Infographic standalone.html` that `site.yml`'s `infographics.include` names (ten
    posters). `publish_family_views` (`build.py:362`) copies each deck's `* - Infographic Deck.dc.html` and `* -
    Executive Summary.dc.html` (`build.py:316-317`), twenty pages. Each copy keeps its source's own links, the two
    preconnects and one stylesheet for Archivo and Archivo Expanded. Four URL variants occur: one adds IBM Plex Mono,
    and one adds Archivo italics. All 30 source files carry the three references.
- **Why nothing caught it.** `build.py`'s `check()` (`:592`) never looks at origins. Story 30.1's zero-origin scan
  (`tests/meta/test_twins_zero_origin.py`) covers the standalone Marp twins and the React decks, not the docsite
  output. Story 31.1's check is the first to look, and it is not on `main`.
- **What is NOT the problem.** The Starlight site under `docs-site/` names no font origin (`git grep` finds none).
  The Kedro-Viz bundle under `/dashboard/kedro-viz/` does carry Google Fonts, but it is the dashboard producer's
  vendored build, never rewritten; Story 31.1 exempts its path by name. Herald's portal page
  (`src/shared/packages/pyforge-herald/web/index.html:11-14`) is served by the platform, not Pages.

**Approach:** self-host the faces the herald pages use, point every herald page at them, remove every third-party font
link and preconnect, and make "no herald page names another origin" a build check.

- **The faces.** Vendor the woff2 files for the faces the pages actually use under `docsite/assets/fonts/`, with
  each family's OFL-1.1 licence text beside them. The families are Big Shoulders Display, IBM Plex Sans and IBM Plex
  Mono for the shells, and Archivo and Archivo Expanded for the copies. Use the weights and styles the links ask for,
  the latin subset at least. Take them from one recorded source per family, such as the `@fontsource/<family>` npm
  package at an exact version. That is Story 30.1's precedent: the React decks import `@fontsource/archivo` and
  `@fontsource/archivo-expanded` `^5.2.5`. One stylesheet in the same directory (for example
  `docsite/assets/fonts/fonts.css`) declares every `@font-face` with a relative `url()`. `build.py` copies the
  directory to `<out>/assets/fonts/`; `assets` is already in `OWNED_OUTPUTS` (`:49`).
- **Its provenance record.** `docsite/README.md` gains a vendored-fonts table: each file's path, its source
  (package@version or URL), its licence and its sha256. A test pins the hashes, as
  `test_vendored_files_match_readme_sha256` does for `docs-site/README.md`.
- **Drop instead of self-host.** This is allowed per family, when a face is not worth carrying. The family's CSS then
  names a system fallback stack, and the README table records the drop. Either way, no herald page loads that family
  from another origin.
- **The shells.** `shell_page.html.j2` drops its three font lines and links the vendored stylesheet relative to the
  page (`{{ rel }}assets/fonts/fonts.css`), or `build.py` folds the `@font-face` rules into `assets/site.css`.
  `artifact/dossier.html` is a single file built for the Artifact host and cannot reach `../assets/`. It either
  embeds the faces it uses as `data:` URIs or falls back to the declared system stack. It never keeps a Google Fonts
  link.
- **The published copies.** At publish time, `publish_infographic` and `publish_family_views` remove each copy's
  Google Fonts `<link rel="stylesheet">`, both preconnect `<link>`s and any `@import url(https://fonts.googleapis.com/…)`.
  They put one relative link to the vendored stylesheet in their place (`../assets/fonts/fonts.css` from
  `infographics/`, `../../assets/fonts/fonts.css` from `decks/<slug>/`). The source files under `presentations/` are
  Design twins kept by the sync loop. They are never edited, and `site.yml`'s "the source files themselves are never
  modified" stays true. The README's "published unmodified" lines say what the publish now rewrites.
- **The check.** `build.py`'s `check()` gains two problems:
  - *external origin*: a page under the output names another origin in a `src`, an `href` other than a plain `<a
    href>` navigation link, a CSS `url()` or an `@import`. This covers `rel="preconnect"`, `rel="dns-prefetch"` and
    `rel="preload"` links. Mirror `pyforge.herald.twins.scan_text`'s semantics with the standard library: the `site` env
    has no `pyforge`.
  - *unresolved face*: an `@font-face` `url()` that is neither a `data:` URI nor a file inside the output.

  `site-check`, and `pages-check` through `assemble_pages.py`'s `build.py --check` call, then exit 1 on a regression.
  The existing "infographic shrank on publish" problem stays. Compare the published size with the source after the
  font-link rewrite, never delete the check.
- **The herald test.** `src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py` (new) builds the
  real site into `tmp_path` with `docsite/build.py` (jinja2 and PyYAML are in the `pyforge-herald` env) and runs
  `pyforge.herald.twins.scan_tree` over the output. It asserts:
  - zero findings;
  - 45 HTML pages built, or the build's own page count, so a build that publishes nothing cannot pass;
  - every `@font-face` `url()` in the output resolves to a file in the output or is a `data:` URI;
  - every file in `docsite/assets/fonts/` is in the README table, and its sha256 matches.

  `tests/unit/test_docsite_build.py` gains parametrized cases for the two new `check()` problems: a planted
  stylesheet, a planted preconnect, a planted `@import` and a planted `url()` font each produce the external-origin
  problem; a missing font file produces the unresolved-face problem; a plain `<a href="https://…">` produces nothing.

Ledger key: `31-3-the-public-pages-build-loads-no-third-party-resource-from-herald-s-own-pages`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-herald` CAP-56 (FR-10.5; D6): "no script, stylesheet, font, image, fetch or
  XHR names another origin". CAP-52 (FR-8.1) shipped the one Pages artifact, with `docsite/build.py` owning `/herald/`
  (Story 27.2). Herald pages that load Google Fonts are a defect of that shipped behaviour, so this story mints no CAP
  and registers no FR.
- **Architecture.** AD-21 (amended 2026-09-28 (night): one artifact, N hosts, no runtime cross-origin call; rule 1:
  `/herald/` is `docsite/build.py`'s prefix, `/dashboard/` is not). AD-1 and the spine's Design Authoring invariant: a
  `.dc.html` is immutable on the Code side, so the twins are not edited. No AD is amended.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. The change applies to the public build
  as it stands, flag or no flag.
- **Origin.** Story 31.1's cross-origin check on its dispatch branch (2026-10-08); the station Dream's 2026-10-08
  (Pages fonts) entry; operator decision 2026-10-08: this story lands before 31.1.

## Acceptance Criteria

- Given a build of the story's tree (`pixi run --frozen -e site site-check`) When `pyforge.herald.twins.scan_tree`
  runs over the output Then it returns no finding, where `8a2da2c010` returns 135 in 45 pages. No herald page
  carries a stylesheet, a `rel="preconnect"` (or `dns-prefetch` or `preload`) hint, an `@import` or a font load from
  any third-party origin, and `git grep -n -E 'fonts\.(googleapis|gstatic)\.com' -- docsite/` prints nothing.
- Given the assembled Pages artifact with Story 31.1's cross-origin check When `pages-check` runs Then it reports 0
  findings under `herald/`. Only the Kedro-Viz path that 31.1 exempts by name may carry a third-party reference.
- Given the built output When every `@font-face` rule is read Then each `url()` is a `data:` URI or resolves to a file
  under the output, and every face the shells' and copies' CSS names (Big Shoulders Display, IBM Plex Sans, IBM Plex
  Mono, Archivo, Archivo Expanded) is either self-hosted or recorded in `docsite/README.md` as dropped to a fallback
  stack.
- Given `docsite/assets/fonts/` When the new meta test runs Then every file there has a README row with its source,
  licence and sha256, the hashes match, and each family's OFL-1.1 licence text is present.
- Given a planted Google Fonts stylesheet, a planted preconnect, a planted `@import` or a planted `url(https://…)` in
  a built page When `build.py --check` runs Then it exits 1 naming the page and the origin. A plain `<a
  href="https://…">` navigation link passes. A missing vendored face exits 1 naming the `url()`.
- Given `presentations/` When the story's diff is read Then no file under it changed, and the 30 published copies
  differ from their sources only by the back-bar and the font-link rewrite.
- Given the story lands When `pixi run --frozen -e pyforge-herald pyforge-herald-test` and `pixi run --frozen -e site
  site-check` run Then both pass.

## Boundaries & Constraints

**Always:**
- Record each vendored face's source (package@version or URL), licence and sha256 in `docsite/README.md`, and check
  each hash before staging.
- Remove both preconnect hints with the stylesheet. Story 31.1's check counts a preconnect as a load.
- Keep the build offline. `build.py` copies vendored files and fetches nothing. Fetch the faces once while implementing,
  never at build time.
- Reconcile every Spec `spec-surface-check` names, then stamp each one scoped (AGENTS.md pre-PR item 5). Expect
  `spec-pyforge-herald` for `docsite/**` and the tests. Never run a bare `--write-baseline`.
- The PR carries the `maintenance` label. Run `pixi run -e pyforge-guild pr-preflight` before pushing; its
  `site-check` leg builds the site.

**Never:**
- Never edit a file under `presentations/`. The twins are Design's, immutable on the Code side (AD-1). Rewrite only
  the published copy.
- Never touch `docsite/tools/assemble_pages.py`, `docsite/tools/pages_second_host.py` or
  `.github/workflows/dashboard.yml`. They are Story 31.1's surface, in flight on its branch.
- Never touch `docs/dashboard/**` (the Kedro-Viz bundle), `docs-site/**` or `src/shared/packages/pyforge-herald/web/**`.
- Never add a `pixi.toml` dependency, an npm install step to `site-check` or a network call to `build.py`.
- Never weaken or delete an existing `check()` problem, or a test in `test_docsite_build.py` or `test_docs_site.py`.
- Never edit the PRD, the spine or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| shell page | `index.html`, `dossier/`, gallery, decks index, family pages | links the vendored stylesheet; no Google Fonts link or preconnect | — |
| artifact page | `artifact/dossier.html` (single file, no `<head>`) | faces as `data:` URIs or the fallback stack; no relative `../assets/` link | — |
| published poster | `infographics/<slug>.html` | Google Fonts links and preconnects replaced by `../assets/fonts/fonts.css`; back-bar kept | source untouched |
| published family view | `decks/<slug>/infographic-deck.html`, `executive-summary.html` | same rewrite, `../../assets/fonts/fonts.css` | source untouched |
| `@import` form | `@import url('https://fonts.googleapis.com/…')` in a copy | removed at publish | `check()` exits 1 if one survives |
| navigation link | `<a href="https://github.com/…">` | allowed | — |
| preconnect only | `<link rel="preconnect" href="https://fonts.gstatic.com">` | an external-origin problem | exit 1 |
| face missing | `@font-face { src: url(fonts/x.woff2) }`, file absent | an unresolved-face problem | exit 1 |
| dropped family | a family recorded as dropped | CSS names a fallback stack; README row says dropped | — |
| Kedro-Viz | `/dashboard/kedro-viz/**` | not herald's; untouched | exempted by Story 31.1, by path |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-08 (Pages fonts) entry.
- Epic: Epic 31 (`spec-pyforge-herald` CAP-56). The fix joins the epic whose contract it repairs, which is still
  `backlog`.
- Ledger key: `31-3-the-public-pages-build-loads-no-third-party-resource-from-herald-s-own-pages`.
- Ledger status at mint: `backlog`.
- Deps: none. Operator decision 2026-10-08: dispatch and land this story before Story 31.1, so 31.1's `pages-check`
  meets a clean `/herald/` tree. 31.1's `Deps:` line is unchanged here.
- Spec: `spec-pyforge-herald/.memlog.md` records the mint. No contract change; `SPEC.md` is untouched.
- Dispatch note: Epic 31's `[epic_surfaces]` entry already admits `docsite/**`, `docs-site/**`, the herald package and
  its tests, `scripts/.spec-surface-baseline.json` and every Spec memlog. No widening.
- Minted 2026-10-08 in one chain commit with Stories 32.2 and 32.3.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e site site-check` — expected: exit 0, with the two new problems wired into `check()`. (Not a dispatch gate: herald's `verify_commands` is `pyforge-herald-test` only, so naming it under Commands makes MRS-GATE-011 refuse the landing.)
- Build into scratch with `pixi run --frozen -e site python docsite/build.py --out <scratch>`, then run `pixi run
  --frozen -e pyforge-herald python -c "from pathlib import Path; from pyforge.herald import twins; print(len(twins.scan_tree(Path('<scratch>'))))"`
  — expected: `0` (it is `135` on `8a2da2c010`).
- `git grep -n -E 'fonts\.(googleapis|gstatic)\.com' -- docsite/` — expected: exit 1, no output.
- `git diff --stat <baseline>.. -- presentations/` — expected: empty.
- Once Story 31.1 is merged: `pixi run --frozen -e site pages-check` — expected: exit 0, with no cross-origin finding
  under `herald/`.
- Open two built pages (a family page and a poster) in a browser with no network route, and confirm the faces render
  from `assets/fonts/`.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped stamps.

## Spec Change Log

- No change yet.

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (self-review against diff and verification; no subagent layers on auto-checkpoint tree)

## Auto Run Result

Status: done

Summary: Vendored docsite fonts under `docsite/assets/fonts/`, pointed shell and published twin pages at them, inlined shell faces in the artifact build, and extended `docsite/build.py` `check()` with external-origin and unresolved-font guards plus meta/unit tests.

Verification: `pixi run --frozen -e pyforge-herald pyforge-herald-test` (1681 passed); `pixi run --frozen -e site site-check` (checks passed); `python scripts/spec_surface_reconcile.py` (OK); `git grep fonts.googleapis.com -- docsite/` (no matches).

Review: 0 patch/defer/intent findings.

Follow-up review recommended: false
