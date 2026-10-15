---
title: '43.3: Astro assembles the artifact: mounts, redirects and search'
type: 'feature'
created: '2026-10-14'
status: 'in-review'
flag:
  key: pyforge.herald.pages_one_generator        # Story 43.1's; shared across Epic 43 (one flag per CAP, Q6), not minted here
  provider: openfeature-file                     # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                  # v1 is global only
  fallback: 'assemble_pages.py mounts, redirects, walks links and scans origins exactly as it does today'
  cleanup: retired by Story 43.7 with the Jinja path (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-27-2-one-pages-artifact-carries-the-docs-site-the-dossier-and-the-dashboard.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-42-2-the-kedro-viz-mount-is-an-artifact-handoff-that-tolerates-absence.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-43-2-the-overview-gallery-and-deck-family-pages-are-astro-pages.md
  - docsite/tools/assemble_pages.py
  - docsite/tools/pages_second_host.py
  - docs-site/astro.config.mjs
  - docs-site/README.md
  - docs-site/package.json
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `docsite/tools/assemble_pages.py` (720 lines) mounts `/herald/` and `/dashboard/`, writes the 44 legacy
redirect stubs (derived from the `herald/` tree, Story 27.2) and the `/kedro-viz/` redirect, walks every in-artifact
link, scans every HTML, CSS and JS file for a third-party origin with its own parser (`_LinkCollector`, `_css_loads`,
`_js_scan`) and checks the shared menu. Each of those is a thing Astro, Starlight or a short check can do; together
they are the bespoke assembler AD-23 names as the shape to retire. After Stories 43.1 and 43.2 every `/herald/` page is
Astro's with the flag on, so the mounts, redirects and checks are what is left.

**Approach:** mounts, redirects, the origin rule and search become Astro configuration plus one small check.

- **Redirects.** `docs-site/redirects.json` holds the 44 legacy root paths with their `/herald/` targets and
  `/kedro-viz/` → `/dashboard/kedro-viz/` (kept, no sunset: operator ruling 2026-10-13); `docs-site/astro.config.mjs`
  reads it into `redirects`. The file is the frozen record of the paths the 2026-10-05 artifact served at the root,
  written once from the Jinja path's derivation, and a test proves every target exists in the build. A collision
  between a redirect path and a page fails the build naming the path (AD-21 rule 1). The `/kedro-viz/` entry follows
  the export's presence as Story 42.2 made it.
- **Mounts.** The twins (Story 43.2) and the downloaded exports (Story 42.2's `kedro-viz-export`) are served from
  `publicDir` (`docs-site/public/`), populated by one small script from the tracked twins and the build input; a
  duplicate route surfaces as Astro's own build error.
- **Search.** Starlight's Pagefind indexes the whole artifact: herald pages carry `data-pagefind-body` (Story 43.1's
  dossier already does), so one index covers docs and herald pages alike.
- **The origin rule.** One check under 40 lines: every absolute URL in the artifact's HTML, CSS and JS shares the
  configured origin (`site_origin(SITE_URL)`), the vendored Kedro-Viz bundle exempted by name as today; and a
  `Content-Security-Policy` meta on herald pages (`default-src 'self'`, with what the pages need), so a violation also
  shows in the browser. The 300-line scanner goes with the assembler in Story 43.7.
- **The gates.** `pages-check` keeps its name and its exit codes: 1 on a planted twin naming `fonts.googleapis.com`,
  1 on a redirect collision, 1 on a link that does not resolve; `docs-site-validate` (the vendored validators) stays
  green and unchanged.
- **The flag.** With `pyforge.herald.pages_one_generator` off, `assemble_pages.py` does everything it does today;
  on, Astro's configuration and the small check take over and the assembler's corresponding steps are skipped. Story
  43.7 removes the assembler.

Ledger key: `43-3-astro-assembles-the-artifact-mounts-redirects-and-search`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / 43.2, 42.2.

### Living CAP citations

- **`spec-pyforge-herald` CAP-61** (FR-12.4): the redirects map, `publicDir`, Pagefind over herald pages, the origin
  check. On AD-21 (one artifact; zero third-party origins; the 44 legacy redirects stay; a non-HTML file carries no
  redirect) and AD-23 (one generator; no assembler with its own link, origin and redirect logic).
- **CAP-56** (the second host): the origin the check compares against is the resolved `SITE_URL`
  (`pages_second_host.site_origin`), on every host.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M3 ("the design twins and the dashboard
  through `publicDir`, the 44 legacy redirects as an `astro.config` map (kept; no sunset) ... Pagefind indexes the
  whole artifact"); `brainstorm-intent.md` § M3 (redirects from the 44-row JSON; origin check = a 30-line allowlist
  plus a CSP meta) and § *Constraints the Spec must keep*.

## Acceptance Criteria

- **AC1 — Every redirect resolves.** Given the flag on, When the site builds, Then every path in
  `docs-site/redirects.json` (44 legacy paths and `/kedro-viz/`) is a redirect page in the artifact whose target exists
  under `/herald/` or `/dashboard/`; a test reads the JSON and the artifact and fails naming the path otherwise.
- **AC2 — Collision.** Given a redirect path that is also a page (a planted `dossier/index.html` page beside the
  `dossier/` redirect), When the site builds, Then the build fails naming the path.
- **AC3 — `publicDir`.** Given the flag on, Then every standalone twin and every downloaded export in the artifact is
  served from `docs-site/public/`, byte-identical to its source (`sha256sum`), and the population script is the only
  writer under `docs-site/public/`.
- **AC4 — Search.** Given the flag on, Then the Pagefind index under the artifact holds a dossier page and a deck family
  page: a test queries the built index for a dossier section title and a family slug and gets one hit each.
- **AC5 — The origin check.** `wc -l` over the origin-check source is under 40; given a planted twin naming
  `fonts.googleapis.com`, `pages-check` exits 1 naming the file and the URL; given the vendored Kedro-Viz bundle's
  own third-party reference, it exits 0 (exempt by name); every herald page carries one `Content-Security-Policy`
  meta.
- **AC6 — Flag off.** Given the flag off, Then the artifact is byte-identical to a build without this story.
- **AC7 — The gates.** `pixi run --frozen -e site pages-check` exits 0 in both flag states (public host and the CAP-56
  fixture host); `pixi run --frozen -e site docs-site-validate` and `pixi run --frozen -e pyforge-herald
  pyforge-herald-test` exit 0.

## Boundaries & Constraints

**Always:**
- Keep every URL the 2026-10-13 artifact served: the 44 legacy redirects and `/kedro-viz/` stay with no sunset
  (operator ruling 2026-10-13).
- Keep the one-owner rule: a redirect that lands on a page is refused, never silently resolved (AD-21 rule 1).
- Keep the five vendored files byte-identical; the origin check and the population script are local files beside them
  (AD-21 rule 5) and count toward AD-23's 300-line budget.
- Keep the vendored-root exemption named with its reason.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not hand-grow `redirects.json`: it is the frozen legacy set; a new herald page gets no root redirect.
- Do not load a third-party origin or relax the CSP meta to admit one (AD-21).
- Do not commit anything under `docs-site/public/` that the population script writes, or under `docs-site/build/`.
- Do not delete `assemble_pages.py` here (Story 43.7); with the flag off it must run unchanged.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flag on, full build | tracked tree + fixture export | 45 redirect pages (44 + `/kedro-viz/`), twins and exports from `publicDir`, one Pagefind index | exit 0 |
| export absent | no `kedro-viz-export` input | no `/kedro-viz/` redirect, no mount (Story 42.2) | exit 0 |
| redirect target missing | a JSON row whose target is not built | — | AC1's test fails naming the path |
| redirect and page collide | planted page at a redirect path | — | build exit 1, names the path |
| planted Google Fonts link | a twin naming `fonts.googleapis.com` | — | `pages-check` exit 1, names file and URL |
| vendored bundle's own CDN reference | `/dashboard/kedro-viz/` | exempt by name | exit 0 |
| second host | `PAGES_HOST_BASE_URL` + `PAGES_HOST_BASE_PATH` | every absolute URL on that origin | exit 0 |
| flag off | any | today's assembler, byte-identical artifact | exit 0 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (FR-12.4), minted 2026-10-14.
- Architecture: AD-23 (adopted 2026-10-14) on AD-21 (rules 1 and 5; the 2026-09-28 and 2026-10-14 amendments).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M3.
- Epic: Epic 43, Story 43.3.
- Ledger key: `43-3-astro-assembles-the-artifact-mounts-redirects-and-search`.
- Ledger status at mint: `backlog`.
- Deps: Stories 43.2 (the herald pages Astro serves) and 42.2 (the export in the build input and the conditional
  `/kedro-viz/` redirect), both station-local. `marshal factory dispatch` stamps `baseline_revision` with the launch
  commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."43"`.
- Flag: `pyforge.herald.pages_one_generator` (shared with 43.1; `feature-flag-governance:CAP-1`, Q6).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 43.2, 42.2 • **FR/AD:** spec-pyforge-herald CAP-61 (FR-12.4), on AD-21 (zero third-party origins, one artifact) and AD-23
**Flag:** `pyforge.herald.pages_one_generator` (shared with 43.1)

**Given** `assemble_pages.py` mounts `/herald/` and `/dashboard/`, writes 44 redirect stubs and a `/kedro-viz/`
redirect, walks every in-artifact link and scans every HTML, CSS and JS file for a third-party origin
**When** the site builds with the flag on
**Then** every redirect path in `redirects.json` resolves to its `/herald/` or `/dashboard/` target in the built
artifact, a collision between a redirect and a page fails the build naming the path, the twins and exports are served
from `publicDir`, the Pagefind index contains a dossier page and a deck family page, and the origin check (under 40
lines) finds no absolute URL off the configured origin, the vendored Kedro-Viz bundle exempted by name as today
**And** `pages-check` exits 1 when a planted twin names `fonts.googleapis.com`; `docs-site-validate` is green;
`pyforge-herald-test` is green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py -q` — expected: pass (AC1–AC5).
- `pixi run --frozen -e site pages-check` with the flag on and off, and with the CAP-56 fixture host environment — expected: exit 0 each time (AC6, AC7).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `wc -l <the origin check's file>` — expected: under 40 (AC5).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Plant `<link href="https://fonts.googleapis.com/...">` in a copied twin — expected: `pages-check` exits 1 naming the file.
- Add a page at `dossier/index.html` beside the redirect — expected: the build fails naming the path.
- Remove `data-pagefind-body` from the dossier page — expected: AC4's search test finds no dossier hit.

## Verification run (2026-10-15)

- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py -q`
  — exit 0 (the `test_43_3_*` tests: AC1 on a flag-on build of the tracked tree, 44 legacy stubs each landing on its
  target; AC2 through the redirect writer; AC3 on a fixture tree with a Kedro-Viz and a Vizro export; AC4 on the
  built Pagefind fragments; AC5's size, planted-load, exemption, second-host and CSP cases; the two-state test
  `flag_states("pyforge.herald.pages_one_generator")` over what the assembler writes). None skipped here.
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — exit 0, 2015 passed, 5 skipped (the live Design and
  webhook smokes).
- `pages-check`: flag on, public host — exit 0 (`docs-site/public/` holds the 30 twins and 69 downloads; the 44
  legacy stubs come from the Astro build); flag off, public host — exit 0. CAP-56 fixture host
  (`PYFORGE_PAGES_APPLY_HOST=1 PAGES_HOST_BASE_URL=https://pages.example.test PAGES_HOST_BASE_PATH=/local-recipes`) —
  exit 1 in both flag states, and exit 1 on `cbc34a5800` (flag off, `git archive`) with the same finding:
  `reference/github-workflows/index.html` autolinks `https://rxm7706.github.io/local-recipes/` (the `pages.yml` row
  steward 102.3 wrote; lane B's herald 42.3 / steward 102.5 rewrote it as plain text). With lane B's row applied
  locally, the fixture host exits 0 in both flag states; the row was restored and is not edited here (the lanes
  merge before 43.7).
- With a real Vizro export (`vizro_static_export.py` from lane B's atlas 30.2, run with lane B's `pyforge-atlas` env
  into a scratch dir: 34 boards, 37 files; neither worktree changed), copied to `docs/dashboard/vizro/`: `pages-check`
  exit 0 with the flag on (mounted from `docs-site/public/`, judged by the new origin check) and with it off
  (mounted by `_copy_dashboard`, judged by the old scanner: `exempt vendored file dashboard/vizro/assets/plotly.min.js
  ... 1 file(s) not judged, 1 cross-origin reference(s) to https://cdn.jsdelivr.net`); the export was removed
  afterwards. Without the exemption the new check names only `dashboard/vizro/assets/plotly.min.js` (the maplibre
  `.src = \`https://cdn.jsdelivr.net/...\`` template); all 34 pages pass judged.
- AC6: a flag-off `assemble_pages.py` on this tree and on `cbc34a5800` (both `git archive`/copied to scratch with the
  same `node_modules` and `GITHUB_SHA`) — `diff -r` exit 0 over the 361-file artifact.
- The flag-on artifact served under its base path in a browser: no CSP violation on a family page, the dossier or a
  reader page; the preview handler runs (`is-loaded` on every frame); every request is same-origin (the two 404s are
  the `.dc.html` twins' own `./support.js`, as `build.py` documents); a legacy URL redirects to the reader page.
- Mutations, each restored: a Google Fonts link planted in `herald/twins/infographics/atlas.html` — `pages-check`
  (flag on) exit 1 `herald/twins/infographics/atlas.html: loads 'https://fonts.googleapis.com/css2?family=Planted'`;
  a page planted at `src/pages/dossier/index.astro` — the build exits 1 `legacy redirect path(s) already hold a page
  or file (AD-21 rule 1, one owner): dossier/index.html`; `data-pagefind-body` removed from the dossier — AC4's test
  fails with no dossier hit.
- `wc -l docs-site/scripts/origin_check.py` — 39. `pixi run --frozen -e site docs-site-validate` — exit 0.
  `pixi run --frozen -e pyforge-guild lint-types` — exit 0. `pixi run --frozen -e pyforge-guild flag-gate-check` —
  exit 0. Steward's `tests/meta/test_station_tests_trigger_map.py` — exit 0, 45 passed.
- Not run here: the memlog reconcile, the scoped stamps, `detectors-ci` and `pr-preflight` (the coordinating session
  runs them once for the branch).

## Named, not fixed here

- **The assembler's deletion**, the 300-line scanner's removal and the `site-check` task's retirement: Story 43.7.
- **AD-21 rule 1's wording** ("the set is derived from what the producer built, never hand-kept") against a frozen
  tracked `redirects.json`: the spine's 2026-10-14 amendment keeps the 44 legacy redirects; the implementing session
  records on the Spec memlog that the JSON is the frozen legacy set with a test on every target, and the next spine
  re-stamp carries the sentence.
- **The Vizro static boards** under `/dashboard/vizro/` through the same `publicDir` mount: atlas
  (`pyforge-atlas:CAP-63`).
- **`lychee --offline`** over the build (the brainstorm's link-check idea): not in CAP-61; the vendored
  `validate-doc-links.js` and the link walk stay the gate.

## Spec Change Log

- 2026-10-15 (independent review, iteration 1: FAIL, 3 should-fix and 10 nits; resolved on the tree as the lane B and
  lane C merges left it, after Story 43.4):
  - **The origin check catches what the old scanner caught (should-fix 1).** `docs-site/scripts/origin_check.py`
    (39 lines) now reads every loading tag (`link` with a loading `rel`, now `modulepreload` and `prerender` too;
    `script`, `img`, `iframe`, `frame`, `source`, `video`, `audio`, `track`, `embed`, `input`, `object`, and SVG
    `image` and `use`) and judges each `src`, `srcset` candidate, `poster`, `data`, `href` and `xlink:href` on its own,
    so a second attribute or a second candidate behind a same-origin one is judged; attribute values are read with
    HTML entities decoded, quoted `>` no longer ends a tag, the text loads (`url()`, `@import`, `fetch`, XHR `.open`,
    `import()`, `importScripts`, `.src =`, `setAttribute('src')`) are read with entities and JS's `\/` unescaped, and
    a host or port that does not parse is its own origin -- a finding naming the URL, never a traceback. The review's
    probes each have a case in `test_43_3_ac5_pages_check_names_a_planted_load` (13 new). Its new
    `plotly.min.js/x.js` case found one more fault: a directory whose name ends `.js` was read as a file
    (`IsADirectoryError`); the check now reads files only. Still not read, as the review found of both checks:
    `imagesrcset`, string `image-set()`, `<meta http-equiv=refresh>`, a static `import ... from "https://..."` and
    `new Worker(url)`; the CSP meta blocks each of them in the browser.
  - **`/dashboard/` is the whole tracked tree (should-fix 2).** With the flag on, `populate-public.ts` mounts every
    entry of `docs/dashboard/` but its `README.md` -- steward's `deploy static` boards with the two exports, each
    export only when present -- as the flag-off `_copy_dashboard` copies it; the assembler's `_dashboard_entries` is
    the one rule both states read, and a directory mounts only when it holds a file. `fixture_tree(exports=True)`
    gains a board and AC3's expected set holds it.
  - **A mount collision fails the build (should-fix 3), and this spec's Approach was wrong about Astro.** "A duplicate
    route surfaces as Astro's own build error" does not hold in Astro 7.3.2: `checkPublicConflict` logs "Skipping ...
    because a file with the same name exists in the public folder" and the public file wins. The `herald-artifact`
    integration now keeps the files `populatePublic` wrote and, at `astro:build:done`, `refusePublicCollisions`
    (`src/lib/redirects.ts`, node builtins only, beside the redirect writer's own refusal) throws naming every route
    output that is one of them (`test_43_3_a_route_over_a_public_file_fails_the_build`; by hand, a route planted at
    `src/pages/herald/twins/infographics/atlas.html.ts` made the flag-on build exit 1 naming
    `herald/twins/infographics/atlas.html`). With the flag on, `assemble` no longer takes any `dashboard/` as Astro's:
    `_check_astro_dashboard` refuses an entry the input does not mount (another writer) and an input entry Astro did
    not mount, before the herald build runs (`test_43_3_the_flag_on_dashboard_is_the_input_and_nothing_else`,
    `test_43_3_assemble_refuses_a_dashboard_it_did_not_expect`).
  - **Nits resolved.** `_astro_dossier_preexists` is deleted, and with it `pages_one_generator.DOSSIER_ARTIFACT_REL`,
    which nothing else read. The parity test's name reads `..._on_a_fixture_tree` again. Three siblings of the
    exempt `plotly.min.js` (`.js.mjs`, `plotly.min.js/x.js`, `Plotly.min.js`) are judged
    (`test_43_3_ac5_a_sibling_of_the_exempt_file_is_judged`). The built-artifact test now asserts the CSP names no
    host (each source a keyword, a hash or `data:`) and that its hash is the sha256 of the rendered, HTML-unescaped
    preview `onload`. `_check_legacy_redirects` has a synthetic-tree test that runs where docs-site is not installed
    (`test_43_3_pages_check_lands_every_legacy_redirect`). With the flag on the Kedro-Viz export is validated, and
    handed to the herald build's pipelines page, from what Astro mounted (`dashboard/kedro-viz/` in the artifact),
    not from the input.
  - **43.2's back-bar rule needs no new guard (nit 9).** `pages-check` with the flag on reads every twin against its
    tracked file through `_check_herald_parity`'s `_font_vendoring_only`, where a back-bar is a gained line and fails
    it; the always-run `back-bar` case of `test_43_2_the_twin_diff_allows_only_the_font_vendoring` pins that.
  - **Recorded, not changed.** The root `.gitignore` gained `docs-site/public/` in this story: an edit outside Epic
    43's surface (`marshal-policy.toml` `[epic_surfaces]."43"`), for the coordinator's reconcile. Story 43.7's budget
    reads `wc -l docs-site/**/*.py` yet puts "the `publicDir` population script inside the same 300": the script is
    TypeScript (`populate-public.ts`, 86 lines here), so 43.7 either counts it beside the Python or rewords to
    Python only -- its call when it is picked up. Nit 10 (each `needs_astro` test and `astro dev` leave or read a
    stale `docs-site/public/`) and nit 8's build-hook wiring stay manual: no CI lane installs docs-site.
  - **Gates (2026-10-15, on `120fb29f27` plus this change).** The Pages, parity, 43.6, zero-origin, validator, imports,
    site-URL, build and flag-state test files -- exit 0, 249 passed, none skipped (docs-site installed); the herald
    suite -- exit 0, 2124 passed, 5 skipped; `lint-types`, `docs-site-validate`, steward's trigger map -- exit 0;
    `pages-check` with both flags off -- exit 0; with `pyforge.herald.pages_one_generator` and
    `pyforge.herald.status_pages` on and the 42.1 and 43.6 fixtures copied into `docsite/content/` (removed after) --
    exit 0; the CAP-56 host (`PAGES_HOST_BASE_URL=https://pages.example.test`, `PAGES_HOST_BASE_PATH=/local-recipes`,
    both flags on) -- exit 0, the docs-row finding gone with lane B's merge.
- 2026-10-15: implemented (lane A of the one-PR Pages redesign); status `in-review`. Deviations and rulings, each for
  the reviewer and the operator to keep or overturn:
  - **The legacy redirects are written by the build, not Astro's `redirects`.** Astro writes every `redirects` key as
    `<path>/index.html`, and all 44 legacy paths are file names (`infographics/atlas.html`, `decks/<slug>/index.html`,
    `artifact/dossier.html`), so a `redirects` entry would serve `infographics/atlas.html/index.html`. `astro.config.mjs`
    reads `docs-site/redirects.json` into Astro's `redirects` for `/kedro-viz/` (the same value as before, so the
    flag-off stub is unchanged) and, with the flag on, into an integration hook that writes the 44 stubs into the build
    after it (`src/lib/redirects.ts`), in the Jinja assembler's shape with relative targets.
  - **The collision rule is the hook's.** Astro only warns when two routes emit one path (setting
    `prerenderConflictBehavior: 'error'` would also fail the build on the pre-existing Starlight `/404` conflict), and
    a `public/` file silently wins over a route; the hook refuses any legacy path the build already holds, naming it
    (AC2), and writes nothing then.
  - **`redirects.json`** has two keys: `legacy` (the 44, derived once from `_write_dossier_redirects` on the flag-off
    artifact of 2026-10-15; the derivation and the 2026-10-05 set agree at 44) and `kedro-viz`. For the Spec memlog
    (the coordinating session writes it): the JSON is the frozen legacy set, AD-21 rule 1's "derived, never hand-kept"
    sentence wants the next spine re-stamp, and `_check_legacy_redirects` in `pages-check` lands every entry on its
    target with the flag on.
  - **The population script is TypeScript** (`scripts/populate-public.ts`, the only writer of the gitignored
    `docs-site/public/`), run by the same integration at `astro:build:start` and runnable alone; it reuses Story 43.2's
    model (`src/lib/herald-pages.ts`), so no third copy of the gallery and family rules exists. It counts toward no
    Python budget. Twins get the font-link vendoring (Story 43.2's ruling); downloads and exports are byte for byte
    (AC3). `docsite/build.py` with the flag on now writes only the assets and the artifact build (43.2's twin and
    download copy is removed). Each test Astro build rewrites `docs-site/public/` too, as every build does.
  - **The origin check judges loads, not navigation**: every URL an HTML, CSS or JS file loads (src, srcset, poster,
    data, a loading `<link>`, `url()`, `@import`, `fetch`, `import()`, a `.src =` assignment) must be on the configured
    origin, and no `href` may name the public host when building for another (CAP-56). AD-21 allows a plain link
    off-site, and the docs shelf has many; "every absolute URL" read literally would red them. 39 lines.
  - **The CSP meta** is `default-src 'self'` plus `style-src 'unsafe-inline'` (the dossier's accents, the back-bar),
    `img-src`/`font-src` `data:` (the favicon), `frame-src 'self'` and `script-src 'self' 'unsafe-hashes'` with the
    hash of the one inline handler (the preview frame's `onload`, now a constant in `herald-pages.ts`); no origin is
    admitted. It is on every Astro herald page, including the reader pages and 43.1's dossier, and `pages-check`
    checks one per page with the flag on.
  - **Search**: the family pages carry `data-pagefind-body` beside 43.1's dossier; the overview, gallery and decks
    index do not (navigation pages), so a family slug hits one page. AC4's test reads the built Pagefind fragments
    (gzip, `pagefind_dcd` JSON) rather than running the browser client.
  - **Carry-ins from atlas 30.2 (orchestrator ruling 2026-10-15, operator may override):** `/dashboard/vizro/` mounts
    from `docs/dashboard/vizro/` when present (non-empty) -- through `public/` with the flag on, through
    `_copy_dashboard` off (an empty `vizro/` is now skipped there, as an empty `kedro-viz/` was) -- and `pages-check`
    refuses a mounted export without `index.html` or a `manifest.json` object. `VENDORED_ROOTS` gains the exact file
    `dashboard/vizro/assets/plotly.min.js` (herald:AD-21 rule 5, a vendored upstream bundle; a key without a trailing
    `/` is one file), never the tree.
  - **Atlas 30.2 AC7 evidence** (for the coordinator to copy into that spec at the lane merge): a real export from
    30.2's `vizro_static_export.py` (34 boards, 37 files, export_commit `cbc34a5800`) under `docs/dashboard/vizro/`
    -- `pixi run --frozen -e site pages-check` exit 0 with the flag on and with it off; no cross-origin finding under
    `dashboard/vizro/`; the exempt file's one reference is `https://cdn.jsdelivr.net` (maplibre's icon template).
  - **The CAP-56 fixture host** is red on the base for a docs row lane B already rewrote (Verification run); the
    gate holds once the lanes merge.
  - Tests share `tests/meta/pages_astro.py` (the Astro build, the fixture tree with optional exports, the page
    reader); steward's trigger map declares `docs-site/**` for `test_pages_artifact.py`, which now builds Astro. Two
    pinned tests move with the code: `test_pages_second_host.py`'s `VENDORED_ROOTS` list and
    `test_docs_site_menu.py`'s `/kedro-viz/` redirect (now read from `redirects.json`).
  - The bespoke Python under `docs-site/` is 381 lines (`scripts/sidebar_from_map.py` was 342 before this story; the
    origin check adds 39): AD-23's under-300 target is Story 43.7's measure.
- 2026-10-14: specced at mint from Epic 43's Story 43.3 text, `spec-pyforge-herald` CAP-61, FR-12.4 and the Dream's
  2026-10-13 entry (M3), against `assemble_pages.py` and `astro.config.mjs` as they stand on 2026-10-14 (the config
  already carries the `/kedro-viz/` redirect; the 44 legacy paths are written by the assembler).
- 2026-10-15 (the lane-B → lane-A merge, a semantic clash fixed in the merge): `_check_origins` imported
  `public_site_url` from `pages_second_host`, which herald 42.3 (lane B) renamed to `docsite/tools/pages_site_url.py`;
  the merged tree's flag-on `pages-check` would have died on the import. It now imports from `pages_site_url`, as the
  rest of the assembler does.
