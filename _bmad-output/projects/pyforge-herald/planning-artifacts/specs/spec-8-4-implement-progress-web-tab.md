---
title: 'Implement Progress Web Tab'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** `epics-with-stories.md`'s Story 8.4 (lines 492-537) specs a `ProgressTab.jsx` reading
`REST API /api/herald/progress?station=<name>&date_range=<start>..<end>` -- a live backend Epic
7/8's actual architecture (a static Vite dashboard talking only to Claude Design's MCP surface) has
no way to serve. Epic 7 had already shipped `ProgressPanel.jsx` as a shared `MomentPanel`
placeholder (echoing the active sidebar filters, showing an empty state) pending Epic 8's real
data.

**Approach (scaled-down, 2026-08-08 scope decision, consistent with spec-8-1/8-2/8-3):**
`ProgressPanel.jsx` becomes its own component (no longer wrapping `MomentPanel`), fetching a
*static* `progress.json` snapshot at `fetch(\`${import.meta.env.BASE_URL}progress.json\`)` instead
of a live REST endpoint. That snapshot is written by a new `npm run sync-progress` script
(`web/scripts/sync-progress.mjs`), wired as a `predev`/`prebuild` hook, which copies the operator's
local `.herald/progress.json` (spec-8-1's storage file, written by spec-8-2/8-3's `--update`
command) into `web/public/progress.json` -- Vite's own static-asset convention for anything under
`public/` being served as-is and copied into `dist/` on build. A missing source file (no
`--update` run yet) is not an error: the script writes `[]` so the app still builds and renders its
empty state.

The card UI itself keeps the AC's shape faithfully: the latest record per station as a summary card
(station, date, shipped-capability count, total compute hours), expandable via a real `<button
aria-expanded>` (native Enter/Space keyboard activation, screen-reader friendly with no extra ARIA
plumbing needed) to show the full capability list, a cost breakdown (compute hours / token spend /
wall-clock hours), and the unblock narrative. Filtering by the sidebar's station/date-range filters
(already shared infrastructure from Epic 7) narrows which records are considered before computing
"latest per station."

**Explicit scope boundary:** the AC's "Trigger update" button (which would call the `--update` CLI
command from the browser) is not a live control -- there is no server-side process a static
dashboard can invoke. It is rendered as a copy-paste `herald progress <station> --update` command,
reusing Epic 7's own established `EmptyState`/`empty-state__command` convention for exactly this
kind of "here's the command to run" affordance, both in the empty state and inside an expanded
card's detail. The AC's optional "chart (pie chart of compute vs. tokens vs. wall_clock)" is
skipped entirely -- explicitly marked optional in the epics doc, and no charting library is
otherwise present in this package (adding one for a single optional chart would be exactly the kind
of speculative dependency "Simplicity First" rules out).

## Boundaries & Constraints

**Always:**
- `ProgressPanel.jsx` fetches `progress.json` on mount (`useEffect`), tracking `loading` / `ready`
  / `error` state; a non-`ok` response or a fetch rejection renders `ErrorState` (Epic 7's existing
  component) rather than crashing or silently showing an empty list.
- Cards show the *latest* record per station (by `date`), computed client-side from every fetched
  record, sorted newest-first.
- Sidebar `station`/`dateRangeStart`/`dateRangeEnd` filters narrow the record set *before* the
  latest-per-station reduction, so a date-range filter can genuinely change which record is
  "latest" for a station (not just hide/show whole cards).
- An empty filtered result renders `EmptyState` with a station-aware message (`No progress recorded
  for <station>.` when a station filter is active, `No progress recorded yet.` otherwise) and the
  `herald progress <station-or-placeholder> --update` command.
- Each card's summary is a real `<button aria-expanded="true|false">` -- keyboard-activatable via
  native Enter/Space, no custom key handling needed.
- `npm run sync-progress` (also `predev`/`prebuild`) copies `.herald/progress.json` (resolved
  against the cwd the script is invoked from, or an explicit override via `HERALD_PROGRESS_PATH`/
  first CLI arg) to `web/public/progress.json`; a missing source writes `[]` rather than failing
  the build.
- Responsive: `.progress-cards` is a CSS grid (`repeat(auto-fill, minmax(280px, 1fr))`) that
  collapses to a single column under the existing 767px mobile breakpoint, matching every other
  panel's stacking convention from Epic 7.

**Block If:** N/A -- no spike, no live gate (static asset + client-side fetch only).

**Never:**
- No live REST API call, no `/api/herald/progress` route, no server process of any kind.
- No pie chart / charting library dependency.
- No functional "Trigger update" button that shells out or calls a backend -- copy-paste command
  text only, per the explicit scope boundary above.
- `web/public/progress.json` itself is never git-tracked (gitignored) -- it is generated data, not
  source, regenerated by `sync-progress` on every `dev`/`build`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fetch succeeds, no records | `progress.json` is `[]` | `EmptyState`: "No progress recorded yet." + command | No error |
| Fetch succeeds, station filter active, no records for it | filters.station set | `EmptyState`: "No progress recorded for `<station>`." + station-specific command | No error |
| Fetch succeeds, one record | -- | one card, summary shows station/date/capability count/compute hours | No error |
| Fetch fails (non-2xx or network error) | -- | `ErrorState` (Epic 7 component), suggests `sync-progress` + reload | No error surfaced to console beyond the caught rejection |
| Card summary clicked/`Enter`/`Space` | expanded toggle | detail shows full capability list, cost breakdown, narrative, command | No error |
| Several records for one station | different dates | only the max-`date` record renders as a card | No error |
| Station filter set | -- | only that station's card(s) considered | No error |
| Date-range filter set, no records in range | -- | falls back to the same-shaped empty state | No error |
| `sync-progress`, source file present | `.herald/progress.json` exists and is valid JSON | copied verbatim to `public/progress.json` | Parses source with `JSON.parse` first -- fails loud on corrupt source rather than shipping bad data |
| `sync-progress`, source file missing | no `--update` has been run yet | `public/progress.json` written as `[]`, warning logged, exit 0 | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/web/src/panels/ProgressPanel.jsx` -- edit -- replaces the
  `MomentPanel`-wrapping placeholder with real fetch/state/card rendering
  (`ProgressCards`/`ProgressCard` helper components, `latestPerStation`).
- `src/shared/packages/pyforge-herald/web/src/panels/MomentPanel.jsx` -- edit -- docstring updated
  to note `ProgressPanel` no longer uses it (`SuccessPanel`/`OperationsPanel` still do).
- `src/shared/packages/pyforge-herald/web/src/app.css` -- edit -- `.progress-cards`/`.progress-
  card*` rules (grid layout, mobile single-column collapse, expandable-detail styling), reusing
  existing Modernist tokens.
- `src/shared/packages/pyforge-herald/web/scripts/sync-progress.mjs` -- create -- the snapshot-copy
  script.
- `src/shared/packages/pyforge-herald/web/package.json` -- edit -- `sync-progress`/`predev`/
  `prebuild` scripts.
- `src/shared/packages/pyforge-herald/web/.gitignore` -- edit -- `public/progress.json` ignored.
- `src/shared/packages/pyforge-herald/web/README.md` -- edit -- documents the `sync-progress` step
  and `ProgressPanel`'s real behavior.
- `src/shared/packages/pyforge-herald/web/src/test/setup.js` -- edit -- a default `fetch` mock
  (`beforeEach`/`afterEach` via `vi.stubGlobal`/`vi.unstubAllGlobals`) so every test gets a
  deterministic empty `progress.json` response unless it stubs its own -- needed because
  `ProgressPanel` now fetches on every mount, including in tests (`App.test.jsx`) that never
  cared about progress data before.
- `src/shared/packages/pyforge-herald/web/src/panels/ProgressPanel.test.jsx` -- create -- the I/O
  matrix above (9 tests: empty state × 2, error state, card summary, expand/collapse, keyboard
  expand, latest-per-station reduction, station filter, date-range filter).
- `src/shared/packages/pyforge-herald/web/src/App.test.jsx` -- edit -- the two Progress-tab
  assertions that depended on the old bare-filter-echo placeholder text updated for real content
  (substring matches against the new empty-state message rather than an exact match on a lone
  `<dd>warden</dd>`); three previously-synchronous tests made `async` and switched to `findBy*` so
  `ProgressPanel`'s async fetch settles inside `act()` before the test ends (was producing an
  `act()` warning, not a failure).

## Design Notes

**Why a `predev`/`prebuild` npm hook rather than a manual step the operator must remember.** npm's
own `pre<script>` convention runs automatically before `dev`/`build` with zero operator action --
the sync step could not be forgotten the way a documented-but-manual step could be. It is still
runnable standalone (`npm run sync-progress`) for an operator who wants to refresh the snapshot
without a full dev/build cycle.

**Why the "Trigger update" affordance is copy-paste text, not a button that shells out.** A static
Vite dashboard has no process to shell out from -- any "button" that appeared to trigger an update
would be misleading. Epic 7's `EmptyState` component already established the "show the exact
command to copy-paste" pattern for precisely this situation (a read-only surface pointing at a CLI
action); reusing it here (both for the empty state and the expanded-card detail) keeps one
convention across the whole app rather than inventing a second "looks clickable, isn't" pattern.

**Why the default `fetch` mock lives in `test/setup.js`, not per-test-file.** `App.test.jsx`
exercises the whole app shell, including whichever tab happens to be active -- Progress is the
default tab, so nearly every `App.test.jsx` test now mounts `ProgressPanel` and triggers its fetch
whether or not that test cares about progress data. A shared `beforeEach` default (empty,
successful response) means only `ProgressPanel.test.jsx`'s own tests need to override the mock with
meaningful data; every other test gets a deterministic, silent default.

## Verification

**Commands:**
- `npm run test` (from `web/`) -- full suite green: baseline **13 passed** (2 files) before this
  story; **22 passed** (3 files) after (+9 new in `ProgressPanel.test.jsx`; `App.test.jsx` stayed
  at 9, content updated).
- `npm run build` -- succeeds; `dist/progress.json` present (copied from `public/progress.json` by
  Vite's static-asset handling), containing `[]` when no `.herald/progress.json` source exists.
- No `act()` warnings in the `npm run test` output (verified after the `App.test.jsx` `findBy*`
  fix -- prior to it, four tests warned, though none failed).

## Spec Change Log

## Review Triage Log
