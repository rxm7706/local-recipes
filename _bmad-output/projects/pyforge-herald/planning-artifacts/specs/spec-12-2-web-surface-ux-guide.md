---
title: 'Web Surface UX Guide'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** The Epic 12 AC for this story asks for "inline help (tooltips,
?-button modals), field hints and examples, empty state messages with next
steps, error messages with suggestions." Epic 7 already built all of this
(`Tooltip.jsx`, `HelpIcon.jsx`, `EmptyState.jsx`, `ErrorState.jsx`) and
Epics 8-10 wired real panels using them -- but nothing documents it for an
operator, and the package's own `web/README.md` is stale in one important
way (it still describes `SuccessPanel`/`OperationsPanel` as Epic 7
placeholders, which Epics 9/10 replaced with real archives).

**Approach:** write `docs/web-ux-guide.md` reading the actual current
source (`web/src/panels/*.jsx`, `web/src/components/{Sidebar,HelpIcon,
Tooltip,EmptyState,ErrorState}.jsx`, `web/scripts/sync-progress.mjs`,
`scripts/export_web_snapshot.py`, `scripts/export_notices_snapshot.py`)
rather than the epics doc's illustrative text, and leading with the single
most operationally important fact this architecture produces: the
dashboard is a static Vite bundle with no live API, reading a
pre-generated JSON snapshot per Moment that nothing regenerates
automatically after a CLI write. Every empty-state/error-state message
string and every tooltip/help-icon copy quoted in the doc is copied
verbatim from the component source, not paraphrased.

**Judgment call: this story documents the web surface as-built, without
correcting `web/README.md`'s stale Epic-9/10 language.** `web/README.md`
is that package's own dev-facing doc (install/run/test/structure); this
story's scope is the *operator-facing UX* doc under `docs/`, which is
allowed to supersede stale claims in its own text without also patching
every file it cites. Flagging the staleness here for whoever next touches
`web/README.md`, but a Simplicity-First read of "touch only what the task
requires" keeps this story's edit surface to `docs/` plus one two-line
addition to the package `README.md` (shared with Story 12.1, see that
spec's Code Map).

## Boundaries & Constraints

**Always:**
- Every regeneration command (`npm run sync-progress`, `python
  scripts/export_web_snapshot.py`, `python
  scripts/export_notices_snapshot.py`) is given with its real default
  paths/flags, read from the script source, not assumed.
- Every quoted empty/error/loading state string matches the component
  source exactly (verified by direct `Read` of each panel/component file
  during authoring, 2026-08-08).
- States the "no live API, static snapshot" fact once, prominently, before
  any per-tab detail -- this is the fact most likely to save an operator
  real debugging time.

**Block If:** N/A -- no spike gate; pure documentation.

**Never:**
- No claim that any exporter runs automatically outside what its own
  wiring actually does (only `sync-progress` is a `predev`/`prebuild`
  hook; the two Python exporters are manual-only, confirmed by reading
  `web/package.json`'s `scripts` block and both scripts' own docstrings).

## I/O & Edge-Case Matrix

N/A -- documentation-only story. Facts verified against source during
authoring (2026-08-08):

| Claim in the doc | Verified against |
|---|---|
| Progress/Success/Operations each read a distinct static JSON file | `ProgressPanel.jsx`/`SuccessPanel.jsx`/`OperationsPanel.jsx` `fetch()` calls |
| Only Progress's snapshot is auto-synced pre-dev/build | `web/package.json` `predev`/`prebuild` scripts |
| Success snapshot excludes drafts | `scripts/export_web_snapshot.py::export_success_snapshot` (`status="published"`) |
| Operations snapshot excludes drafts | `scripts/export_notices_snapshot.py::export_snapshot` (`if n.status != "draft"`) |
| Evidence badge states (valid/broken/stale) and their tooltip text | `SuccessPanel.jsx`'s `evidenceStatus`/`STATUS_SYMBOL`/`STATUS_TEXT` |
| Pitch tab is an external link, not a panel | `TabNav.jsx`'s `TABS` array (`external:` key on the `pitch` entry only) |
| Sidebar station list | `Sidebar.jsx`'s exported `STATIONS` constant |
| Responsive breakpoints (1200px/768px) | `web/README.md`'s existing "Responsive breakpoints" section (unchanged content, still accurate) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/docs/web-ux-guide.md` -- create --
  the UX guide.
- `src/shared/packages/pyforge-herald/docs/README.md` -- shared with Story
  12.1 (index entry for this file; no separate edit needed if 12.1 already
  created it).
- `src/shared/packages/pyforge-herald/README.md` -- shared with Story
  12.1 (same two-line pointer addition; not duplicated).

No `web/src/` or `scripts/` (production code) changes.

## Design Notes

The doc deliberately orders itself "the one thing to know" (static
snapshot, manual regeneration) before the tab-by-tab tour, rather than
following the epics doc's AC ordering (inline help first). An operator
who reads only the first section still gets the highest-value fact; the
epics doc's AC content (tooltips, empty states, field hints) is still
fully covered, just placed after the operational headline.

## Verification

**Commands:**
- No automated test suite applies to markdown-only changes.
- Every quoted string in the doc was cross-checked against the live
  component/script source via direct file reads during authoring (see the
  I/O matrix above) rather than reconstructed from memory or the epics
  doc's own examples.

## Spec Change Log

## Review Triage Log
