---
title: '43.3: Astro assembles the artifact: mounts, redirects and search'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
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

- 2026-10-14: specced at mint from Epic 43's Story 43.3 text, `spec-pyforge-herald` CAP-61, FR-12.4 and the Dream's
  2026-10-13 entry (M3), against `assemble_pages.py` and `astro.config.mjs` as they stand on 2026-10-14 (the config
  already carries the `/kedro-viz/` redirect; the 44 legacy paths are written by the assembler).
