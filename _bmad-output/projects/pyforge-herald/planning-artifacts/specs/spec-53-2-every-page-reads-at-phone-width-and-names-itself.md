---
title: '53.2: Every page reads at phone width and names itself'
type: 'fix'
created: '2026-11-22'
status: 'ready-for-dev'
story: 53-2-every-page-reads-at-phone-width-and-names-itself
spec: spec-pyforge-herald
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'docs-site/src/pages/**'
  - 'docs-site/src/components/**'
  - 'docs-site/src/lib/**'
  - 'docs-site/src/styles/**'
  - 'docs/**'
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

**Problem:** On the live site the fleet board's table is 674 px wide in a 343 px column and the CI table the same; snapshot times print as `2026-11-21T10:35:33-06:00`; the ten gallery frames have no `title`; 31 viewer pages have no `h1`; 172 pages have no description; and a sidebar label prints "(steward Story 41.1)".

**Approach:** The status and CI tables reflow below a breakpoint (label and value per row, long keys wrapping); one date formatter prints every time, with the ISO form in `datetime`; `Shot.astro` gives each frame a title; the viewer page template gains a visually present `h1`; the docs loader fills a missing description from the page's first paragraph; and titles that carry a story id lose it.

Ledger key: `53-2-every-page-reads-at-phone-width-and-names-itself`.

### Living CAP citations

- spec-pyforge-herald CAP-63; FR-15.2 ← CAP-63; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Format dates from the input's own offset, never the build host's time zone.
- Keep each table a `<table>` for a screen reader.

**Never:**
- Never hide a column's data at phone width; reflow it.
- Never rewrite an authored poster or deck twin.

## Acceptance Criteria

**Given** the fleet board's table is 674 px wide in a 343 px column, snapshot times print as ISO strings, gallery frames have no `title`, 31 viewer pages have no `h1`, 172 pages have no description, and a sidebar label prints a story id
**When** the site is built
**Then** the status and CI pages fit a 375 px viewport, every `<time>` prints a readable date with the ISO form in `datetime`, every gallery `iframe` has a title, every viewer page an `h1`, every page a `meta name="description"`, and no sidebar label or status badge prints a story id
**And** herald's live-tree half passes, with a test that fails by name for each

- **AC1 — The site builds and verifies.** Expected: exit 0.

  ```bash
  pixi run --frozen -e site pages-check
  ```

- **AC2 — Herald's live-tree half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pyforge-herald-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-herald CAP-63; FR-15.2 ← CAP-63; no AD moves.
- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-11-22 entry; operator, 2026-11-22: all three audiences.
- Epic: Epic 53, minted with this story.
- Ledger key: `53-2-every-page-reads-at-phone-width-and-names-itself` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."53"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.
