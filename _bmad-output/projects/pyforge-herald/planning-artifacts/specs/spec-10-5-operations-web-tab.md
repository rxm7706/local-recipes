---
title: 'Operations Web Tab'
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

**Problem:** the Epic 7 `OperationsPanel.jsx` was a placeholder rendering `MomentPanel` (shared
with Progress/Success) -- "Not yet implemented -- Epic 10", no real data, no category filter, no
notice detail view. Story 10.5 asks for a notice board layout, category filters + date range, and
a notice detail view.

**Approach (static-JSON-snapshot pattern, since Herald has no server):**
`scripts/export_notices_snapshot.py` reads `.herald/notices-index.json` and writes
`web/public/notices.json` (published + closed notices only, drafts excluded -- they never ship to
the public web snapshot). `OperationsPanel.jsx` fetches `./notices.json` once on mount, filters
client-side by a local `category` `<select>` (deprecation/fix/eol) and the existing shared
sidebar date range (`filters.dateRangeStart`/`dateRangeEnd`, Epic 7's `useFilters` hook,
unmodified), and renders a responsive card grid (`notice-board`) where clicking a card expands
its `what`/`why`/`migration`/evidence-link detail in place.

**Judgment call: no shared cross-Moment snapshot exporter existed to extend.** The task named a
possible `scripts/export-web-snapshot.*` convention Epic 8/9's agents might have already
established on `main` before this story started; at the time this story ran, neither had merged
(their commits existed only in their own not-yet-merged worktree branches -- confirmed via `git
log --oneline` on this worktree's own branch history, which did not include them). Writing a
Notices-specific script rather than guessing at a shared shape that might not match what
Progress/Success actually need avoids speculative generalization; the script's own docstring
names this explicitly as a future consolidation candidate once all three Moments' shapes are
settled.

**Judgment call: category filter is local `useState`, not added to the shared `filters` object.**
`useFilters.js`'s `DEFAULT_FILTERS` (`station`/`dateRangeStart`/`dateRangeEnd`/`search`) is shared
state, persisted to `localStorage`, and read by all three Moment panels. `category` has meaning
only for Operations (Progress/Success have no notion of a notice "type") and is not the kind of
cross-cutting concern `station`/date-range are -- adding it to the shared object would have Grown
that hook's scope for a single consumer, and risked a merge collision with Epic 8/9's own agents
touching the same shared files concurrently in their own worktrees.

## Boundaries & Constraints

**Always:**
- The panel renders `<h2 id="Operations-heading">Operations</h2>` unconditionally on first
  render -- `App.test.jsx`'s existing "reads the initial tab from an existing URL hash" test
  asserts this heading is present the moment `#operations` is the active hash, before any fetch
  resolves.
- A fetch failure (`!response.ok` or a network-level rejection) renders `ErrorState`, never an
  uncaught exception -- the `useEffect`'s `.catch` always sets an error state.
- Loading (fetch in flight), empty (`[]` or every notice filtered out), and error states each
  render exactly one of `<p role="status">`/`EmptyState`/`ErrorState` -- never more than one at
  once.
- Category and date-range filters compose with logical AND (a notice must pass both to show).
- A closed notice's card carries `notice-card--closed` (visually deemphasized) and its expanded
  detail shows the close reason when one was recorded.

**Block If:** N/A -- no spike, no live gate; a static JSON fetch against the same origin.

**Never:**
- No polling, no websocket, no live-reload of `notices.json` -- a fresh snapshot requires
  re-running the export script and rebuilding/redeploying, same static-dashboard model Epic 7
  already established for the shell itself.

## I/O & Edge-Case Matrix

| Scenario | Expected |
|---|---|
| Fetch in flight | `<p role="status">Loading notices…</p>` |
| `notices.json` returns `[]` | `EmptyState` with the `herald notice author ...` command hint |
| Fetch rejects / non-2xx status | `ErrorState`, `role="alert"` |
| Notices present, no filters | every notice rendered as a collapsed card |
| Click a card | expands; `aria-expanded` flips `false -> true`; a second click collapses it |
| `--category eol` equivalent (select "eol") | only `type === "eol"` cards remain |
| Sidebar date range narrows past a notice's `created_at` | that notice's card disappears |
| Closed notice expanded | shows `Closed: <reason>` (or `Closed` alone if no reason recorded) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/scripts/export_notices_snapshot.py` -- create -- reads the
  Story 10.1 index via `notices.list_notices(status="all")`, filters out drafts, writes
  `web/public/notices.json`.
- `src/shared/packages/pyforge-herald/web/public/notices.json` -- create -- committed default
  (`[]`) so the app never 404s before the export script has run once.
- `src/shared/packages/pyforge-herald/web/src/panels/OperationsPanel.jsx` -- rewrite (was the
  Epic 7 `MomentPanel` placeholder) -- fetch, category filter, notice-board render, expand/
  collapse detail.
- `src/shared/packages/pyforge-herald/web/src/app.css` -- edit -- `.operations-panel`,
  `.notice-board` (responsive `auto-fill` grid, one column under 768px per Epic 7's own mobile
  breakpoint), `.notice-card` and its sub-elements.
- `src/shared/packages/pyforge-herald/web/src/test/setup.js` -- edit -- a default `fetch` stub
  (resolves `[]`) so every web test gets a safe default without a real network call escaping
  mid-test; overridable per-test via `vi.stubGlobal('fetch', ...)`.
- `src/shared/packages/pyforge-herald/web/src/panels/OperationsPanel.test.jsx` -- create --
  loading/empty/error states, list-and-expand, category filter, date-range filter, closed-reason
  display.

## Design Notes

**Why did `App.test.jsx` need no changes despite `OperationsPanel` now doing a real `fetch`?**
Once `test/setup.js` stubs a default `fetch` (empty array), `App.test.jsx`'s existing assertions
(heading text, tab switching) remain synchronous and unaffected -- the panel's async data-loading
state is invisible to a test that only cares about which heading is on screen. This was verified
by running the whole `web` suite (`npm run test`), not just the new file, specifically to catch
exactly this kind of cross-panel regression.

## Verification

**Commands:**
- `cd src/shared/packages/pyforge-herald/web && npm run test` -- 20 passed (3 files: Tooltip,
  OperationsPanel, App).
- `npm run build` -- succeeds (46 modules, ~153 KB JS / ~6.6 KB CSS before gzip).
- `python3 scripts/export_notices_snapshot.py --repo-root <tmp> --out <tmp>/out.json` -- manual
  smoke test against a freshly authored+published notice; output matches the shape
  `OperationsPanel.jsx` expects.

## Spec Change Log

## Review Triage Log
