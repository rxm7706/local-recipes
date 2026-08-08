# Herald web dashboard

A unified web surface for the Herald CLI: one dashboard with 4-tab navigation
(Pitch, Progress, Success, Operations) instead of separate web apps per
Moment. Implements Epic 7 ("Foundation — Web Surface") of the
`pyforge-herald` PRD — see
`_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-7-1-web-layout-header-tabs-sidebar-responsive.md`
and `spec-7-2-web-tooltips-inline-help.md`.

This is a plain React + Vite app (no router/state library) styled with the
repo's "Modernist" design tokens (Archivo font, `#f3f2f2` background,
`#201e1d` ink) lifted from
`presentations/pyforge-herald/project/PyForge Herald Infographic standalone.html`.

## Run it

```bash
npm install
npm run dev       # dev server with HMR, defaults to http://localhost:5173
```

or build + preview a production bundle:

```bash
npm run build
npm run preview   # serves dist/, defaults to http://localhost:4173
```

`dev`/`build` both run `sync-progress` first (via `predev`/`prebuild`), which
copies the operator's local `.herald/progress.json` (written by `herald
progress <station> --update`, run from the repo root) into
`public/progress.json` -- the static snapshot `ProgressPanel` fetches at
runtime. Run it by hand after recording new progress without a full
dev/build cycle:

```bash
npm run sync-progress
```

## Test it

```bash
npm run test      # vitest run (component tests: tab switching, sidebar
                   # breakpoint collapse, tooltip show/hide)
```

## Structure

- `src/components/Header.jsx`, `TabNav.jsx`, `Sidebar.jsx` — the layout
  shell (Story 7.1).
- `src/components/Tooltip.jsx`, `HelpIcon.jsx` — inline help affordances
  (Story 7.2).
- `src/components/EmptyState.jsx`, `ErrorState.jsx` — helpful empty/error
  copy (Story 7.2).
- `src/panels/ProgressPanel.jsx` — real card-based rendering (Story 8.4):
  the latest record per station as an expandable card (summary: station,
  date, shipped-capability count, total compute hours; expanded: the full
  capability list, cost breakdown, unblock narrative), filtered by the
  sidebar's station/date-range filters. Reads `public/progress.json` (see
  `scripts/sync-progress.mjs` above) -- there is no live REST API in this
  scaled-down pass.
- `src/panels/SuccessPanel.jsx`, `OperationsPanel.jsx` — per-tab
  placeholders. Real data-fetching is Epic 9/10's scope; today they just
  echo the active sidebar filters and show an empty state.
- `src/hooks/useHashTab.js` — persists the active content tab in the URL
  hash (`#progress`/`#success`/`#operations`) so a reload lands on the same
  tab.
- `src/hooks/useFilters.js` — sidebar filter state (station, date range,
  search), persisted to `localStorage`.
- `src/hooks/useViewport.js` — classifies the viewport as
  `desktop`/`tablet`/`mobile` at the 1200px/768px breakpoints so the
  sidebar can collapse behind a hamburger below desktop width.

## Responsive breakpoints

- Desktop (`>=1200px`): full sidebar always visible.
- Tablet (`768-1200px`): sidebar collapses behind a hamburger; opening it
  overlays the content as a drawer.
- Mobile (`<768px`): everything stacks vertically in normal flow (no fixed
  overlay), body text floors at 16px, all interactive targets are
  `>=44px`.

## Deviations from the story text

- The epics doc's implementation notes suggest React Router for tab
  routing; a plain `useHashTab` hook was used instead since there's only
  one route-like concept (the active tab) and no nested routes — pulling
  in a router for that would be the kind of speculative dependency the
  repo's "Simplicity First" principle rules out.
- The epics doc suggests a Popper/Tooltip.js library; `Tooltip.jsx` is a
  ~40-line hand-rolled component (hover delay + focus/blur) instead, to
  avoid adding a UI dependency for something this small (also matches the
  "no heavyweight UI framework" instruction for this build).
