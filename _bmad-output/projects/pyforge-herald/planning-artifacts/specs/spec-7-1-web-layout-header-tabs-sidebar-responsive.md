---
title: 'Design & Implement Web Layout (Header, Tabs, Sidebar, Responsive)'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Epic 7 ("Foundation — Web Surface") needs Herald's first web dashboard. Today
`pyforge-herald` is a Python CLI package only (`src/shared/packages/pyforge-herald/`) -- no web
app exists. Operators need one unified surface (header + 4-tab nav + sidebar filters + content
area) instead of a separate web app per Moment (Progress/Success/Operations), responsive across
desktop/tablet/mobile.

**Approach:** A new plain React + Vite app at
`src/shared/packages/pyforge-herald/web/`, mirroring the tooling conventions of the
`presentations/<slug>/` decks (same `@vitejs/plugin-react` + `vite build/preview` scripts,
`base: './'`) but without any of the deck-specific slide/marp/pptx machinery -- this is a
dashboard, not a slide deck. Visual system: the Modernist tokens already established elsewhere in
the repo (Archivo font, `#f3f2f2` background, `#201e1d` ink), lifted verbatim from
`presentations/pyforge-herald/project/PyForge Herald Infographic standalone.html`'s `:root` block
rather than reinvented. Tab state persists via URL hash (`useHashTab`); sidebar filter values
persist via `localStorage` (`useFilters`); viewport classification (`useViewport`) drives the
sidebar's collapse-to-hamburger behavior below 1200px. No router library, no UI framework --
plain hooks + hand-rolled components, per this build's "no heavyweight dependencies" constraint.

## Boundaries & Constraints

**Always:**
- Desktop (`>=1200px`): full sidebar visible, header with branding + 4-tab nav (Pitch [external
  link], Progress, Success, Operations), no horizontal scroll.
- Tablet (`768-1200px`): sidebar collapses behind a hamburger; all interactive elements
  `>=44px` touch targets.
- Mobile (`<768px`): everything stacks vertically (normal flow, not a fixed overlay -- the
  header's own height varies since the tab row wraps under the brand row); body text floor
  16px; no horizontal scroll.
- Tab click updates the content area and highlights the active tab; the choice survives a page
  reload via the URL hash.
- Selecting a station/date-range/search value updates visibly in the active panel (the panels
  render the live filter values) -- actual data-fetching against a backend is explicitly Epic
  8/9/10 scope, out for this story.
- Pitch is an external link (`target="_blank"`), not a content tab -- it does not participate in
  `useHashTab`'s valid-tab set.

**Block If:** N/A -- no spike, no live gate; this is new-app scaffolding with no existing
contract to violate.

**Never:**
- No MUI/Ant/other heavyweight UI framework -- plain CSS + hand-rolled components only.
- No real Progress/Success/Operations data-fetching -- placeholder panels only ("Not yet
  implemented -- Epic N" plus the active filter echo).
- No `sprint-status-ledger.yaml` edits (a supervising session syncs the ledger after review).
- No PR opened from this pass -- a supervising session does a visual review with Playwright
  screenshots first.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| Load at desktop width | viewport `>=1200px` | sidebar visible, no hamburger | `useViewport` classifies `desktop` |
| Load at tablet width | viewport `768-1200px` | sidebar collapsed, hamburger visible | click toggles `sidebar--collapsed` off |
| Load at mobile width | viewport `<768px` | header wraps (brand row + tab row), sidebar collapsed, hamburger visible, no page-level horizontal scroll | verified via Playwright `scrollWidth === clientWidth` |
| Click a content tab | `Success` | panel switches, `aria-current="page"` on the clicked tab, `window.location.hash` becomes `#success` | `Progress` is the default when the hash is empty/invalid |
| Reload with an existing hash | `#operations` | Operations panel renders on first paint | `useHashTab`'s `readHash` |
| Select a station filter | `warden` | active panel's filter echo shows `warden`; value persists in `localStorage` under `herald.filters.v1` | `useFilters` |
| Resize desktop -> tablet | window resize event | sidebar auto-collapses (`sidebarOpen` resets to `false` on leaving desktop) | `App.jsx`'s `useEffect` on `viewport` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/web/package.json`, `vite.config.js`, `index.html`,
  `.gitignore` -- create -- app scaffolding (mirrors `presentations/pyforge-herald/package.json`'s
  script names, minus deck-specific `extract`).
- `src/shared/packages/pyforge-herald/web/src/index.css` -- create -- Modernist token block
  (`--color-bg`/`--color-text`/`--color-accent`/`--font-body`/`--font-heading`) copied from the
  infographic standalone HTML, plus the 16px mobile font floor.
- `src/shared/packages/pyforge-herald/web/src/app.css` -- create -- layout rules: header, tab
  nav, sidebar (incl. the two responsive media-query blocks), moment panels, empty/error states,
  tooltip/help-icon chrome.
- `src/shared/packages/pyforge-herald/web/src/main.jsx`, `App.jsx` -- create -- app entry +
  top-level composition (Header/Sidebar/active panel wiring).
- `src/shared/packages/pyforge-herald/web/src/hooks/useHashTab.js` -- create -- URL-hash tab
  persistence.
- `src/shared/packages/pyforge-herald/web/src/hooks/useFilters.js` -- create --
  `localStorage`-backed sidebar filter state (station/dateRangeStart/dateRangeEnd/search).
- `src/shared/packages/pyforge-herald/web/src/hooks/useViewport.js` -- create -- resize-driven
  desktop/tablet/mobile classification at the 768px/1200px breakpoints.
- `src/shared/packages/pyforge-herald/web/src/components/Header.jsx`, `TabNav.jsx`,
  `Sidebar.jsx` -- create -- the layout shell components; `Sidebar.jsx` owns the three filter
  controls (station `<select>`, two date `<input>`s, search `<input>`).
- `src/shared/packages/pyforge-herald/web/src/panels/MomentPanel.jsx`, `ProgressPanel.jsx`,
  `SuccessPanel.jsx`, `OperationsPanel.jsx` -- create -- the per-tab placeholder content.
- `src/shared/packages/pyforge-herald/web/src/App.test.jsx` -- create -- tab-switching +
  hash-persistence + sidebar-breakpoint-collapse tests (Vitest + Testing Library + jsdom).

## Design Notes

**Judgment call: URL hash, not a router, for tab state.** The epics doc's implementation notes
suggest "React Router or URL hash-based" for tab routing -- both are named as options. A router
was skipped because there's exactly one route-like concept (the active tab, three possible
values) and no nested routes; pulling in `react-router` for that trades a ~1KB hook for a real
dependency, which the repo's Simplicity First principle and this task's own "no heavyweight
dependencies" instruction both push against.

**Judgment call: JS-driven viewport classification (`useViewport` + conditional render), not
pure CSS media-query display toggling.** A pure-CSS approach (both sidebar and hamburger always
in the DOM, toggled via `display: none` in a media query) would avoid a resize listener
entirely, but it's much harder to unit-test with jsdom (jsdom does not evaluate real CSS layout
or `matchMedia`-driven rules against `getComputedStyle` reliably). The JS approach lets tests set
`window.innerWidth` directly and dispatch a `resize` event, then assert on the `sidebar--collapsed`
class -- a DOM-level assertion per this task's "CSS/DOM assertion, not a full visual test"
guidance. CSS media queries are still used for finer layout adjustments (drawer positioning, tab
row wrapping) that don't need to be independently unit-tested.

**Judgment call: mobile sidebar uses normal document flow, not `position: fixed`.** An early pass
used `position: fixed` for the mobile drawer (matching the tablet drawer's overlay style), but the
mobile header's height is variable (the tab row wraps onto its own line under the brand row), so a
hardcoded `top: var(--header-height)` offset either clipped content or left a gap depending on
actual header height. Since mobile already stacks everything in `flex-direction: column`, letting
the sidebar render inline (pushing panel content down when open) sidesteps the offset problem
entirely and matches the AC's "everything stacks vertically" wording more literally than an
overlay would.

## Verification

**Commands:**
- `npm install && npm run build` -- clean production build (Vite, no warnings beyond the
  pre-existing `esbuild` postinstall-script notice common to every Vite app in this repo).
- `npm run test` (`vitest run`) -- 6 passing tests in `App.test.jsx` (tab switch + hash
  persistence + initial-hash read + desktop/tablet/mobile sidebar collapse + filter echo).

**Manual checks (headless-browser, not just static reasoning):**
- `npm run preview` + Playwright (`chromium.launch()`, the interpreter's bundled build under
  `~/.cache/ms-playwright/`) at three viewports (375x900, 900x900, 1400x900):
  `document.documentElement.scrollWidth === clientWidth` at all three (no horizontal scroll);
  all four tab items measured `height: 44` (the touch-target floor) at every width; full-page
  screenshots visually confirm the Modernist palette, header/tab/sidebar/content composition, and
  correct collapse behavior at each breakpoint.
- Clicking the tablet hamburger toggles the sidebar's `sidebar--collapsed` class off and renders
  the filter drawer as an overlay.
- An earlier iteration's headless-Chrome screenshot (non-Playwright, `google-chrome --headless
  --dump-dom`) appeared to show the mobile tab row clipping "Operations" off-screen; Playwright's
  `getBoundingClientRect()` measurements showed this was a font-load timing artifact in that
  specific tool, not a real overflow (`scrollWidth === clientWidth` held throughout) -- documented
  here since it drove one CSS iteration (wrapping the header, not the tab row) before being ruled
  out as a non-issue.

## Spec Change Log

## Review Triage Log

