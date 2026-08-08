---
title: 'Implement Web Tooltips & Inline Help'
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

**Problem:** Story 7.1's layout ships with sidebar filters and tab-nav links but no in-context
help -- an operator unfamiliar with the date-range format or a first-time visitor to an empty
Progress tab has no guidance beyond the raw controls. Epic 7's second story adds hover/focus
tooltips, a "?" help affordance for the one non-obvious field (date range), and helpful
empty/error-state copy.

**Approach:** Build directly on Story 7.1's component tree (same PR/pass) rather than a separate
library integration. A hand-rolled `Tooltip` component (200ms hover delay via `setTimeout`,
immediate show on focus, hide on blur/mouse-leave, `role="tooltip"` + `aria-describedby` wiring)
wraps each interactive sidebar control and content-tab link. A hand-rolled `HelpIcon` component
(a "?" `<button>` with `aria-expanded`/`aria-controls`) expands an inline explanation next to the
date-range field. `EmptyState` and `ErrorState` components render the AC's worked examples
verbatim (`"No progress yet." "herald progress warden --update"` and the "Station 'unknown' not
found" pattern) rather than a generic "No data" placeholder.

## Boundaries & Constraints

**Always:**
- Every interactive sidebar/tab element (station select, both date inputs, search input, each
  tab-nav item) is wrapped in `Tooltip` with a purpose-describing label.
- Tooltip appears after a 200ms hover delay; appears immediately on keyboard focus (no delay --
  a focused element has already been reached deliberately); disappears on blur/mouse-leave.
- The date-range field has a `HelpIcon` explaining `YYYY-MM-DD` format and open-ended-range
  behavior; clicking (or Enter/Space, since it's a real `<button>`) toggles the explanation.
- Empty state (`ProgressPanel`/`SuccessPanel`/`OperationsPanel` with no filters set) renders a
  specific next-step message + a copy-paste-friendly `herald ...` command, never a bare "No
  data".
- `ErrorState` exists and is ready for a real caller (Epic 8/9/10's data-fetching will raise into
  it) -- explains the problem and suggests a fix, per the AC's "Station 'unknown' not found.
  Available: warden, atlas, ..." example.
- All of the above is keyboard-reachable: `Tab` focuses every wrapped control (tooltip shows on
  focus), `HelpIcon`'s button is a native `<button>` (Enter/Space activates it without extra
  wiring).

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No tooltip/help library dependency (Popper, Tooltip.js) -- the epics doc's implementation
  notes suggest one, but the actual surface area (fixed-position bubble near a wrapped element,
  no collision detection needed at this app's scale) doesn't justify the dependency weight; a
  ~40-line component covers the AC.
- `ErrorState` is not wired to a real error source in this story -- no backend exists yet
  (Epic 8/9/10). It ships as a ready, tested component; a future story supplies the call site.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected |
|---|---|---|
| Hover a wrapped control | mouseenter, <200ms elapsed | no tooltip yet |
| Hover held past 200ms | mouseenter, >=200ms elapsed | `role="tooltip"` element renders with the label text |
| Mouse leaves before 200ms | mouseenter then mouseleave at 100ms | tooltip never appears (pending timer cleared) |
| Mouse leaves after showing | mouseenter, 200ms, mouseleave | tooltip removed immediately |
| Keyboard focus | `Tab` onto a wrapped control | tooltip appears with no delay |
| Keyboard blur | focus then blur | tooltip removed |
| Click the date-range "?" | click / Enter / Space | inline panel expands with the `YYYY-MM-DD` explanation; `aria-expanded` flips `true` |
| Click again | second click | panel collapses; `aria-expanded` flips `false` |
| All sidebar filters empty | no station/date/search set | `EmptyState` renders "No progress yet." + `herald progress warden --update` (per-tab equivalent for Success/Operations) |
| Any filter set | e.g. station selected | `EmptyState` does not render (the panel shows the live filter echo instead, per Story 7.1) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/web/src/components/Tooltip.jsx` -- create -- hover-delay +
  focus/blur tooltip; accepts children as a render-prop so the wrapped element can receive
  `aria-describedby` without an extra wrapper element breaking native form-control semantics
  (e.g. a `<label htmlFor>` -> `<select>` pairing).
- `src/shared/packages/pyforge-herald/web/src/components/HelpIcon.jsx` -- create -- "?" button +
  expand/collapse panel.
- `src/shared/packages/pyforge-herald/web/src/components/EmptyState.jsx`,
  `ErrorState.jsx` -- create -- message + optional command/suggestion.
- `src/shared/packages/pyforge-herald/web/src/components/Sidebar.jsx` -- edit (same pass as
  Story 7.1) -- every filter control wrapped in `Tooltip`; date-range field gets the `HelpIcon`.
- `src/shared/packages/pyforge-herald/web/src/components/TabNav.jsx` -- edit -- every tab item
  (including the external Pitch link) wrapped in `Tooltip`.
- `src/shared/packages/pyforge-herald/web/src/panels/MomentPanel.jsx` -- edit -- renders
  `EmptyState` when no filter is set, with per-panel message/command props supplied by
  `ProgressPanel`/`SuccessPanel`/`OperationsPanel`.
- `src/shared/packages/pyforge-herald/web/src/app.css` -- edit -- `.tooltip-bubble`,
  `.help-icon`/`.help-icon-panel`, `.empty-state`/`.error-state` rules.
- `src/shared/packages/pyforge-herald/web/src/components/Tooltip.test.jsx` -- create -- the
  hover-delay/blur/focus matrix above, using `vi.useFakeTimers()` + React's `act()` to flush the
  `setTimeout`-driven state update.

## Design Notes

**Judgment call: render-prop children (`{(a11yProps) => <select {...a11yProps} />}`) instead of
`React.cloneElement`.** `Tooltip` needs to hand `aria-describedby` (pointing at the tooltip's own
`id`) to whatever it wraps, but the wrapped elements are native form controls, not custom
components with a stable prop contract. `cloneElement` would work too but is more fragile against
a child that's itself a fragment or an already-cloned element; the render-prop form is explicit
about exactly what's being injected and where, at the cost of one extra line per call site.

**Judgment call: `vi.useFakeTimers()` + `act()`, not `waitFor` with real timers.** The 200ms delay
is real production behavior (not a network-flake to be waited out), so asserting the *absence* of
the tooltip at 199ms and its *presence* at 200ms needs deterministic time control -- `waitFor`
polls and would either flake near the boundary or need an artificially wide margin that stops
testing the actual contract. The first pass without `act()` wrapping around
`vi.advanceTimersByTime()` failed with "not wrapped in act" and the assertions couldn't find the
tooltip at all (React's state update from the fake-timer callback wasn't flushed before the
`expect`) -- wrapping each `advanceTimersByTime` call in `act()` fixed it.

**Judgment call: no delay on focus-driven show.** The AC only specifies the 200ms figure for
"hover" (mouse); a keyboard user tabbing through the sidebar would otherwise wait 200ms per field
with no way to skip it, which is worse UX for the exact audience (keyboard-only navigators) this
accessibility feature is supposed to serve. Showing immediately on focus, delayed on hover, was
treated as the AC's evident intent rather than a literal timer applied everywhere.

## Verification

**Commands:**
- `npm run test` (`vitest run`) -- 3 passing tests in `Tooltip.test.jsx` (200ms delay held/appears,
  disappears on mouse-leave, immediate show/hide on focus/blur) + the Story 7.1 suite unaffected
  (9 total across both files).
- `npm run build` -- clean.

**Manual checks (Playwright against `npm run preview`):**
- Clicking the date-range `HelpIcon` button and then hovering the search input in the same
  session: both the expanded help panel (`page.is_visible("text=Enter dates as")`) and the search
  tooltip (`page.is_visible("role=tooltip")`) were `True` simultaneously -- confirms the two
  affordances don't fight over the same region or interaction state. Full-page screenshot
  reviewed visually: help panel text readable, tooltip bubble positioned above the search field
  without obscuring it.

## Spec Change Log

## Review Triage Log

