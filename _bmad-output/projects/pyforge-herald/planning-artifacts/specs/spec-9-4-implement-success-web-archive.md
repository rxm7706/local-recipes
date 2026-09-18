---
title: 'Implement Success Web Archive (Static-JSON-Snapshot Pattern)'
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

**Problem:** Epic 9's original Story 9.4 (`epics-with-stories.md` lines 737-782) specs a
Success tab fetching `GET /api/herald/success?status=published&date_range=...` from a live
REST API backed by the `Claims` database. Epic 7 shipped `SuccessPanel.jsx` as a thin
wrapper around a shared `MomentPanel` placeholder (static "not yet implemented" text) --
there is no API, no server, and (per this repo's Herald architecture) never has been one;
the web app is a plain static Vite bundle.

**Approach:** `SuccessPanel.jsx` fetches a pre-generated static JSON file
(`web/public/success.json`) instead of a REST endpoint -- the "static-JSON-snapshot
pattern" this repo's Epic 8/9/10 scope-down convention calls for. The snapshot is produced
by a new shared exporter, `scripts/export_web_snapshot.py`
(`export_success_snapshot`/`claims.snapshot`), which an operator (or a future build step)
runs after publishing claims. The panel itself: published claims reverse-chronological,
evidence badges (green check/red x/yellow warning), expandable card detail, filtered by
the existing shared sidebar filters (station/date-range/search) -- no separate in-tab
search box.

## Boundaries & Constraints

**Always:**
- `SuccessPanel` fetches `dataUrl` (default `./success.json`, relative -- matches
  `vite.config.js`'s `base: './'` so the build works from any static host or subpath) via
  an injectable `fetcher` prop (default `(url) => fetch(url)`).
- Loading -> `{status: 'loading'}` (no visible UI beyond the heading); success -> claims
  rendered or `EmptyState` ("No published claims.") when the filtered list is empty;
  fetch failure (network error, non-2xx, or even a *synchronous* throw from `fetcher`) ->
  `ErrorState` ("Could not load success claims.").
- Each claim card: project name, thesis (one-liner, truncated via CSS `text-overflow`),
  shipped date, evidence badges. Clicking the summary toggles an expanded detail panel
  (`aria-expanded`/`aria-controls` wired) showing full thesis, evidence links (real
  `<a href>`), edit history, and every date field.
- Evidence badge status, in priority order: `!validated` -> red "broken" (`✗`); `validated
  && is_stale` -> yellow "stale" (`⚠`); else -> green "valid" (`✓`). Each badge is a
  `Tooltip`-wrapped element naming the type, status, `validated_at`/"never validated," and
  the URL -- keyboard-reachable (`tabIndex={0}`, `Tooltip`'s existing focus/blur wiring
  from Story 7.2).
- Filtering (client-side, over the fetched snapshot): `filters.station` matches
  case-insensitively against `project_name` (a heuristic -- see Design Notes);
  `filters.search` matches `project_name`/`thesis`; `filters.dateRangeStart`/`dateRangeEnd`
  match `shipped_date`.
- Mobile (`<768px`): claim card summary fields wrap/stack vertically (existing
  `--touch-target`/breakpoint conventions from Story 7.1, extended, not reinvented).

**Block If:** N/A -- pure client-side rendering, no live network gate in tests (`fetcher`
is always injected).

**Never:**
- No REST API call, no `/api/herald/success` endpoint -- there is nowhere for one to run.
- No separate in-tab search input -- Story 9.4's AC describes "a search box"; this repo's
  app already has one app-wide in the sidebar (`useFilters`/`Sidebar.jsx`, Epic 7). Adding
  a second, tab-local search field would fork "search" into two inconsistent affordances
  for no demonstrated benefit.
- No automatic re-export on `herald success publish` -- generating `success.json` is a
  separate, explicit step (`scripts/export_web_snapshot.py` / the
  `pyforge-herald-web-snapshot` pixi task), mirroring `herald deck push` staying separate
  from `herald deck pull` (documented precedent: `cli.py`'s `_run_deck_push` docstring).

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| No claims in snapshot | `fetcher` resolves `[]` | `EmptyState` "No published claims." | |
| Fetch resolves `ok: false` | e.g. 404 | `ErrorState` "Could not load success claims." | |
| Fetcher throws synchronously | e.g. `fetch is not defined` | same `ErrorState` | routed through `Promise.resolve().then(...)` so the throw never escapes the effect |
| One claim, mixed evidence | one valid + one never-validated link | valid badge green, never-validated badge red (broken takes priority over stale) | |
| Card expand | click summary | `aria-expanded` flips, detail panel with real evidence links + edit history renders | |
| Search filter | `filters.search` matches thesis substring | only matching claims render | |
| Station filter | `filters.station` substring-matches `project_name` | only matching claims render | |
| Date-range filter | `shipped_date` outside `[start, end]` | claim excluded | |
| Exporter, no claims yet | `export_success_snapshot` against an empty/missing `claims.json` | writes `[]` to `success.json`, creates `out_dir` if needed | |
| Exporter, mixed statuses | draft + published claims | only `status="published"` in the snapshot, newest-first by `published_at` | `claims.snapshot` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/web/src/panels/SuccessPanel.jsx` -- rewrite -- was a
  4-line `MomentPanel` wrapper (Epic 7 placeholder); now the full card-based archive
  (`EvidenceBadge`, `ClaimCard`, `claimMatchesFilters`, the fetch effect).
- `src/shared/packages/pyforge-herald/web/src/panels/SuccessPanel.test.jsx` -- create --
  empty/error/render/expand/filter (search, station, date-range)/synchronous-throw
  coverage.
- `src/shared/packages/pyforge-herald/web/src/app.css` -- edit -- `.claim-list`,
  `.claim-card*`, `.evidence-badge*` rules, plus the `<768px` stacking media-query
  addition.
- `src/shared/packages/pyforge-herald/web/src/index.css` -- edit -- `--color-success`,
  `--color-warning` tokens (badge status colors; "broken" reuses the existing
  `--color-accent-700`, already this app's error/danger red).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/claims.py` -- edit -- `snapshot`
  function (every claim matching `status`, newest-first by `published_at`, each entry
  `to_dict()`-shaped).
- `src/shared/packages/pyforge-herald/scripts/export_web_snapshot.py` -- create --
  `export_success_snapshot`, `main` (CLI: `--repo-root`/`--out-dir`); the shared exporter
  this package did not have yet (checked first per this story's own instructions -- none
  existed anywhere in the package when this story landed).
- `src/shared/packages/pyforge-herald/tests/test_export_web_snapshot.py` -- create --
  loads the script via `importlib` (it lives outside the installed package, deliberately --
  see Design Notes) and exercises `export_success_snapshot`/`main`.
- `src/shared/packages/pyforge-herald/tests/test_claims.py` -- edit -- `snapshot` coverage
  (status filter, newest-first ordering, empty-when-no-match).
- `src/shared/packages/pyforge-herald/web/public/success.json` -- create -- checked-in
  empty-array placeholder (`[]`) so `npm run dev`/`npm run build` work out of the box
  before any claim has ever been exported.
- `pixi.toml` (repo root) -- edit -- `pyforge-herald-web-snapshot` task running the
  exporter.

## Design Notes

**Judgment call: static-JSON-snapshot, not a REST API.** Restated from Intent because it
is this story's central deviation: Epic 7's web app has never had a server to answer an
API call from, and there is no plan anywhere in this repo to add one for Herald
specifically (that is exactly `docs/dreams/herald-moments-2-4-live-backend.md`'s open
question). A static snapshot file, regenerated on demand, is the same pattern this repo's
Herald deck-pull/push machinery already uses for Claude-Design-sourced artifacts (pull to a
local file, no live query at render time).

**Judgment call: `filters.station` matches against `project_name` via substring.**
Claims don't carry a first-class `station` field (`project_name` is free text, e.g. "Marshal
S-1.10" or "warden") -- there is no schema change proposed here to add one (out of this
story's scope, and Story 9.1's schema is already shipped). Matching the existing sidebar
station filter against `project_name` case-insensitively is an approximation, not a
guaranteed-accurate filter; documented rather than silently assumed correct.

**Judgment call: the exporter lives outside the installed package (`scripts/`, not
`src/pyforge/herald/`).** It is a build-time/operator tool (writes to `web/public/`, a
path that only makes sense relative to a repo checkout), not runtime library code a
`pip install pyforge-herald` consumer would ever import -- keeping it out of the shipped
package matches this repo's existing convention of build/dev tooling living outside
`src/`.

**Judgment call: `success.json` is not auto-regenerated by `publish`.** Restated from
Boundaries & Constraints -- the precedent (`herald deck push` staying separate from
`herald deck pull`) already exists in this codebase for the identical reason: coupling two
independently-failable operations into one call makes the combined operation's
success/failure story conditional on both, and an operator who wants to re-export without
publishing anything new (e.g. after manually fixing a stale evidence link via `success
validate`) has no way to do that if export is buried inside publish.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 611 passed, 2 skipped
  (whole-package total, includes the Python-side snapshot/exporter tests).
- `npm run test` (in `web/`) -- 21 passed (13 pre-existing + 8 new in
  `SuccessPanel.test.jsx`).
- `npm run build` (in `web/`) -- succeeds, `dist/` produced with no warnings beyond the
  pre-existing baseline.
- `ruff format --check` / `ruff check` -- clean (Python side).

**Manual checks:**
- `pixi run -e pyforge-herald pyforge-herald-web-snapshot` against a scratch
  `.herald/claims.json` with one published claim -- writes `web/public/success.json`
  matching `claims.to_dict()`'s shape.

## Spec Change Log

## Review Triage Log
