---
title: '49.1: The boards'' static pages wear the site''s theme'
type: 'fix'
created: '2026-11-22'
status: 'done'
story: 49-1-the-boards-static-pages-wear-the-site-s-theme
spec: spec-pyforge-atlas
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/static_export.py'
  - 'src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_static_export.py'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/dreams/pyforge-atlas.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The 35 pages `vizro-static-export` writes under `/dashboard/vizro/` are white with browser-default links whatever theme the reader chose. The index prints a path column (`feedstock-health/index.html`), a full ISO stamp per row, a 40-character commit id and "AD-17" in a heading, and `unavailable` the same as a stamp; at 375 px its table runs off the page.

**Approach:** The export's one stylesheet sets every colour as a site theme variable with a fallback (`var(--sl-color-black, #fff)`), light and dark by `data-theme` and by the system scheme when alone. The index becomes board name, what it shows, and the day its data was built (`<time datetime>` holding the full stamp), with a plain "No data yet" mark and no path column; tables scroll inside their own wrapper at 375 px.

Ledger key: `49-1-the-boards-static-pages-wear-the-site-s-theme`.

### Living CAP citations

- spec-pyforge-atlas CAP-63 (amended 2026-11-22); FR-71 ← CAP-63; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep the pages readable opened alone from a file, with no site file loaded.
- Keep each board's full data build stamp on its own page.

**Never:**
- Never copy the site's menu or header into the export (herald Story 53.1 gives it at assembly).
- Never change a board's data, query or chart.
- Never restyle Kedro-Viz.

## Acceptance Criteria

**Given** the 35 exported pages are white with browser-default links whatever theme the reader chose, and the index prints a path column, a full ISO stamp per row and `unavailable` the same as a stamp
**When** `vizro-static-export` writes the tree
**Then** every colour an exported page sets is a site theme variable with a fallback, in light and dark; the index names each board and the day its data was built with the full stamp in `datetime`, marks a board with no data as such, and has no path column; and index and board pages fit 375 px
**And** atlas's package half passes, with tests that fail by name for each

- **AC1 — Atlas's export tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_static_export.py -q
  ```

- **AC2 — Atlas's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-atlas CAP-63 (amended 2026-11-22); FR-71 ← CAP-63; no AD moves.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-11-22 entry; operator, 2026-11-22: all three audiences, dark by default, one PR.
- Epic: Epic 49, minted with this story.
- Ledger key: `49-1-the-boards-static-pages-wear-the-site-s-theme` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."49"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.
