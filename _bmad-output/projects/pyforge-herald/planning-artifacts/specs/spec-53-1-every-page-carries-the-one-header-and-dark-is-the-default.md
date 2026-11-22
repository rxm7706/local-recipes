---
title: '53.1: Every page carries the one header, and dark is the default'
type: 'feature'
created: '2026-11-22'
status: 'done'
story: 53-1-every-page-carries-the-one-header-and-dark-is-the-default
spec: spec-pyforge-herald
difficulty: 'hard'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.herald.site_shell
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: 'each shell keeps its own header (Starlight''s on the docs, the herald layouts'' own, none on mounted pages) and a reader with no stored theme gets the system scheme'
  cleanup: '90 days after the flag is on in every environment; herald files the removal story'
surface:
  - 'docs-site/src/components/**'
  - 'docs-site/src/layouts/**'
  - 'docs-site/src/lib/**'
  - 'docs-site/src/styles/**'
  - 'docs-site/astro.config.mjs'
  - 'docs-site/scripts/**'
  - 'src/platform/config/flags.json'
  - 'src/platform/config/flag-overlays.json'
  - 'src/shared/packages/pyforge-core/tests/unit/test_flags.py'
  - 'src/platform/tests/test_openfeature_file_flags.py'
  - 'docs/governance/flag-inventory/pyforge-herald.md'
  - 'src/shared/packages/pyforge-herald/tests/**'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The live Pages site is one menu over four shells (UX review, 2026-11-21): the docs carry Starlight's header, the herald pages a header of their own with no search or theme toggle, the mounted Vizro and marketplace pages none. 88 pages have no `<main>` and no skip link, the ten-link menu cuts the title at 1280 px, five of the home's seven doors are a bare word, the docs sidebar opens every group, and a reader with no stored theme gets the system scheme.

**Approach:** One `SiteHeader.astro` (title, the registry's menu grouped by section, search, theme toggle; `data-pf-header`) rendered by the docs shell and both herald layouts, and written at `astro:build:done` into each page another station mounts, with the theme script and a link to the site's theme sheet (pyforge-herald:AD-23, amended 2026-11-22). The theme script's fallback becomes dark. `site.yml` gains `doors`, one line per registry section, which the doors print; sidebar groups start collapsed. All behind `pyforge.herald.site_shell`, read through `docs-site/src/lib/flags.ts`.

Ledger key: `53-1-every-page-carries-the-one-header-and-dark-is-the-default`.

### Living CAP citations

- spec-pyforge-herald CAP-63; FR-15.1 ← CAP-63; pyforge-herald:AD-23 (amended 2026-11-22).

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Register the flag in all four places (`docs/reference/story-spec-flag-block.md`) and in herald's flag inventory.
- Keep the herald pages' display headlines, hero and full-width page.
- Keep every page's CSP valid: a changed inline script changes its hash in the same commit.

**Never:**
- Never copy the menu into a second component, a layout or another station's generator.
- Never rewrite an authored poster or deck twin, and never write to the Kedro-Viz mount.
- Never change the Vizro export's or the marketplace's own markup or colours here (atlas Story 49.1, steward Story 130.2).

## Acceptance Criteria

**Given** the docs carry Starlight's header, the herald pages one of their own with no search or theme toggle, and the mounted Vizro and marketplace pages none, and a reader with no stored theme gets the system scheme
**When** the flag is on and the site is built
**Then** every HTML page the site serves, redirect stubs and authored twins excepted, holds the one header (`data-pf-header`) with the registry's menu grouped by section, the search control and the theme toggle, one `<main>` and a skip link; a page with no stored theme resolves to dark; each door on the home carries its registry description; and sidebar groups other than the current page's start closed
**And** with the flag off the built pages match today's shells, and `pages-check` exits 0 in both states

- **AC1 — The site builds and verifies with the flag on.** Expected: exit 0.

  ```bash
  pixi run --frozen -e site pages-check
  ```

- **AC2 — Herald's live-tree half passes, both flag states.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pyforge-herald-live-test
  ```

- **AC3 — The flag contract holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-core pyforge-core-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-herald CAP-63; FR-15.1 ← CAP-63; pyforge-herald:AD-23 (amended 2026-11-22).
- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-11-22 entry; operator, 2026-11-22: "keep the look, share the header"; dark by default.
- Epic: Epic 53, minted with this story.
- Ledger key: `53-1-every-page-carries-the-one-header-and-dark-is-the-default` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."53"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

**Both flag states:** `src/shared/packages/pyforge-herald/tests/unit/test_site_shell_flag_states.py` runs the flag in
both states (`flag_states`): the build environment, the theme rule and the sidebar groups follow it. The built pages:
`src/shared/packages/pyforge-herald/tests/meta/test_site_shell.py` builds the site with
`pyforge.herald.site_shell` on (the `shell` fixture: the header, `<main>`, skip link, dark default, door lines and
closed groups on every page) and off (`test_53_2_a_reader_page_has_its_h1_with_the_shell_off_too`: no header and no
`pf-shell.js`); `src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py` pins the flag-off shells.

## Review record (2026-11-22)

Independent review of the staged diff against this spec: pass with fixes, all applied in the change. Enter in the
header's search box no longer closes the dialog; a search excerpt is rebuilt as text and `<mark>` nodes, never set as
HTML; Escape returns focus to the group it closes; the header's own search and theme controls are hidden with scripts
off; `aria-current` reads `page` only on the link to the page itself; `withShell` cuts at the last `</body>` of the
page as written; the wider door grid applies only with the flag on.

**Deviation, recorded:** the header is not asked of `herald/artifact/`, `pagefind/` or the Kedro-Viz mount
(`dashboard/kedro-viz/`), beyond the stubs and twins this spec's criteria name. CAP-63's success text is amended to
name them (memlog, 2026-11-22). The menu's Kedro-Viz link lands on upstream's app, which has no way back but the
browser's.

**Door lines moved, recorded:** the lines were first added to `docs/map.yaml` as a `description` per section;
doctor's docs-map schema refuses an unknown key there (`docs-currency` read the map as unreadable), so they live in
herald's own `site.yml` `doors`, keyed by the registry's section keys, and `docs/map.yaml` is unchanged.

**AC1 as written builds with the flag off locally:** set `PYFORGE_SITE_SHELL=1` (as `pages.yml` does through
`python -m pyforge.herald.pages_env`) to run the header check; `tests/meta/test_site_shell.py` does.
