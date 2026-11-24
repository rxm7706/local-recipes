---
title: '53.3: Kedro-Viz opens under the site header, with a way back'
type: 'feature'
created: '2026-11-22'
status: 'done'
story: 53-3-kedro-viz-opens-under-the-site-header-with-a-way-back
spec: spec-pyforge-herald
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.herald.site_shell
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: 'the menu, the door, the sidebar and the overview tile link the Kedro-Viz app itself, and no framed page is built'
  cleanup: '90 days after the flag is on in every environment (2027-02-20, with Story 53.1); herald files the removal story'
surface:
  - 'docs-site/src/pages/herald/pipelines/**'
  - 'docs-site/src/lib/**'
  - 'docs-site/scripts/pages.mts'
  - 'docs-site/README.md'
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

**Problem:** The menu's Kedro-Viz link lands on upstream's app, mounted verbatim at `dashboard/kedro-viz/`: no site header and no link back (the gap Story 53.1's review recorded). A board steward's `deploy static` mounts under `dashboard/` took no header either, since assembly gave it only to the Vizro export.

**Approach:** A reader's page, `herald/pipelines/index.html`, built like the infographic reader pages: the one header, a back-bar with a link to the app by itself, and the app in a frame filling the rest. `nav.ts` `framedSections` points the Kedro-Viz section at it, after the mount rule has decided the section shows, so the menu, the door and the sidebar follow; the overview's tile does the same. Assembly (`shell.ts`) covers the whole `dashboard/` tree but the Kedro-Viz export, and a page written without `<head>` and `<body>` tags.

Ledger key: `53-3-kedro-viz-opens-under-the-site-header-with-a-way-back`.

### Living CAP citations

- spec-pyforge-herald CAP-63 (amended 2026-11-22); FR-15.1 ← CAP-63; pyforge-herald:AD-23.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep the legacy `/kedro-viz/` redirect landing on the app itself.

**Never:**
- Never write to a file under `dashboard/kedro-viz/` (AD-21 rule 5).
- Never build the framed page, or re-point a link, with the flag off or the export absent.

## Acceptance Criteria

**Given** the menu's Kedro-Viz link lands on upstream's app, which carries no header and no link back to the site, and a board steward's `deploy static` mounts under `dashboard/` gets no header either
**When** the flag is on and the site is built with a Kedro-Viz export in the build input
**Then** `herald/pipelines/index.html` carries the one header, a `<main>`, an `h1` and a skip link, frames `dashboard/kedro-viz/` and links the app by itself; the menu, the home's door, the sidebar and the overview's tile open that page; the export's own files are byte for byte what was mounted; every other page mounted under `dashboard/` carries the header; and `pages-check` names an export mounted with no framed page
**And** with the flag off, or with no export, no framed page is built and the menu is as before; herald's live-tree half passes

- **AC1 — Herald's live-tree half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pyforge-herald-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-herald CAP-63 (amended 2026-11-22); FR-15.1 ← CAP-63.
- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-11-22 entries; operator, 2026-11-22: "add a wrapper page for Kedro-Viz with a back link".
- Epic: Epic 53.
- Ledger key: `53-3-kedro-viz-opens-under-the-site-header-with-a-way-back` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."53"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

**Both flag states:** `src/shared/packages/pyforge-herald/tests/unit/test_site_shell_flag_states.py` runs the flag in both
states (`flag_states`). The built pages: `src/shared/packages/pyforge-herald/tests/meta/test_site_shell.py` builds a
tree holding a Kedro-Viz export with the flag on (the framed page, the links, the untouched export, `pages-check`) and
off (`test_53_3_no_framed_page_without_the_export_or_without_the_shell`).

**Not verified here:** the framed page against a real Kedro-Viz export in a browser (the export is not in a local
build; the tests use a fixture export). Upstream's own first-run popup still shows inside the frame. The app keeps its
view in its own frame's URL, so the framed page's address does not follow it; "Full page" opens the app by itself.

## Review record (2026-11-22)

Independent review of the staged diff against this spec: pass with fixes, all applied. The reader pages no longer
leave the back-bar's 32 px above the header; a page with no `<head>` and `<body>` keeps its `<html>` attributes and its
meta, title, link and style in the head; a board under no section of the menu marks no menu link; the framed page's
description says what it is; the tests compare the mounted export byte for byte and pin the door, the sidebar and
the tile with the flag off.
