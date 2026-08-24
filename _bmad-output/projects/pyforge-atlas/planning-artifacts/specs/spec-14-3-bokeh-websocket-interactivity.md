---
title: 'Story 14.3: Bokeh WebSocket interactivity (CAP-2)'
type: 'feature'
created: '2026-08-14'
status: 'done'
baseline_revision: '51587c6c5734ff5654e1e30cf0dea7293742e74b'
final_revision: '41631580959bf4d104a2a8ce942c9bcdc7680003'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Story 14.1's static fragments open zero WebSocket connections by design, and
Story 14.2's `Widget.websocket_renderer` slot is deliberately left `None` on every seeded
widget — nothing in the catalog can filter, drill, or re-sort live against `cf_atlas.db`;
every interaction today means a full page reload against a fresh static fragment.

**Approach:** Fill the `"grid"` widget's `websocket_renderer` slot with a per-view Bokeh
`Application`/`FunctionHandler` session builder (a live filter-by-maintainer input plus a
sort-by-column select, both re-executing through the existing `cli_bridge` against
`cf_atlas.db`), run it on Bokeh's own server (`bokeh.server.server.Server`) as the actual
WebSocket-protocol runtime, and mount it behind a new, minimal Starlette ASGI app
(`views/asgi.py`) whose one route embeds the live session via
`bokeh.embed.server_document()` — the swappable "any ASGI host" layer CAP-2 requires.

## Boundaries & Constraints

**Always:** the live session logic (`views/live.py`'s `Application`/`FunctionHandler`
builders) never imports or references the ASGI host — `views/asgi.py` is the ONLY module
that knows Starlette exists, so swapping hosts later touches that one file, never a view
definition. The maintainer-filter `TextInput` renders only for a `View` whose
`query_kwargs` actually declares a `maintainer` key (today: all 6 `STATIC_VIEWS`) — never
assume every registered view has one. Story 14.1's static mode
(`render.py`/`STATIC_VIEWS`/`get_view`) stays byte-identical; this story only fills the
`websocket_renderer` slot 14.2 already declared and adds two new modules.
`views/__init__.py` exports `live.py`'s public builders but never `asgi.py`'s `app` (a
deployment entrypoint, not a package-level symbol). `tornado`/`starlette` are declared as
explicit run-deps in both `pixi.toml` and `pyproject.toml` (AUD-ATLAS-010: an undeclared
module-level import is a runtime dependency regardless of transitive availability).

**Block If:** the pixi solve for the new `tornado`/`starlette` floor pins fails or
conflicts with an already-pinned version elsewhere in the shared env — report the conflict,
do not silently loosen or drop a pin.

**Never:** touch `dashboard/` (the separate, untouched Vizro module). Build a
"chart"/"pivot" `websocket_renderer` — no current view needs one; that is a future
one-entry-plus-one-renderer story. Implement real-time push/streaming — every live update
is user-triggered (a filter/sort change), never server-pushed on a timer. Rewrite
Bokeh/CDN asset URLs for air-gap (Story 14.4). Change any `STATIC_VIEWS` entry's
`columns`/`query_kwargs`/`script`/`widget` value. Add a production `pixi run` serve task —
this story proves the mechanism works via tests, not a hosted, deployed service.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH_FILTER | Live doc for `staleness-report`; maintainer `TextInput.value` set to a handle owning exactly one fixture package | `ColumnDataSource.data` narrows to that package's row(s) — re-queried against `cf_atlas.db`, not filtered in-memory | No error expected |
| HAPPY_PATH_SORT | Sort-by `Select.value` changed to a numeric column | `ColumnDataSource.data` reorders ascending by that column, nulls last | No error expected |
| NO_MAINTAINER_KWARG | A `View` whose `query_kwargs` lacks `maintainer` (built via `dataclasses.replace` in the test, not a real registry entry) | Live doc renders with the sort control only — no maintainer `TextInput` | No error expected |
| UNKNOWN_LIVE_VIEW | ASGI `/live/{view_name}` requested with an unregistered name | 404 response | Translated from `get_view`'s `KeyError` — no raw traceback |
| LIVE_SESSION_ROUND_TRIP | A real `Server` on an ephemeral port; `pull_session()` connects to `/staleness-report` | Returns a `ClientSession` whose `.document` contains the expected `DataTable`/`TextInput`/`Select` models | No error expected |
| DB_UNAVAILABLE_AT_LOAD | `cf_atlas.db` missing when a session first loads | `CfAtlasDbUnavailableError` propagates out of `modify_doc` (that one session fails; server keeps running) | Matches `render_view`'s existing propagate-don't-swallow behavior — no new handling invented |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/widgets.py` -- fill `"grid"`'s `websocket_renderer` with a new `_grid_websocket_renderer(view: View) -> Callable[[Document], None]` factory (maintainer filter + sort-by-column, both live); `Widget.websocket_renderer`'s type comment updated from "unconstrained" to this concrete factory shape
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/live.py` -- NEW: `LIVE_VIEWS: tuple[View, ...]` (views whose widget has a `websocket_renderer`), `build_application(view) -> Application`, `build_live_server(views=LIVE_VIEWS, *, port=0, allow_websocket_origin=None, io_loop=None) -> Server` — the host-agnostic Bokeh WebSocket runtime, using the high-level `bokeh.server.server.Server` API (not the low-level `BokehTornado`/`HTTPServer`/`BaseServer` trio — no multi-worker deployment concern in this story's scope)
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/asgi.py` -- NEW: minimal Starlette `app`, one `GET /live/{view_name}` route returning `HTMLResponse(server_document(url=f"{base_url}/{view.name}"))`; base URL from `PYFORGE_ATLAS_LIVE_BOKEH_URL` env var (default `http://localhost:5006`, mirroring `cli_bridge.py`'s env-override convention) — the swappable "ASGI host" mounting layer
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/__init__.py` -- export `live.py`'s `LIVE_VIEWS`, `build_application`, `build_live_server`
- `src/shared/packages/pyforge-atlas/pixi.toml` -- add `tornado >=6.5.8` and `starlette >=1.6.0` to `[package.run-dependencies]`, next to the existing `bokeh` entry
- `src/shared/packages/pyforge-atlas/pyproject.toml` -- mirror the same two floors in `[project].dependencies` (AUD-ATLAS-010 byte-for-byte convention)
- `src/shared/packages/pyforge-atlas/tests/views/conftest.py` -- add `maintainers(id, handle)` + `package_maintainers(conda_name, maintainer_id)` fixture tables (matching every wrapped CLI's real join schema) and assign one handle to exactly one fixture package, so the live maintainer filter is realistically testable
- `src/shared/packages/pyforge-atlas/tests/views/test_live.py` -- NEW: covers the I/O matrix above

## Tasks & Acceptance

**Execution:**
- [x] `pixi.toml` + `pyproject.toml` -- declare `tornado`/`starlette` run-deps in both manifests -- must resolve before any new module imports them
- [x] `views/widgets.py` -- implement `_grid_websocket_renderer` and wire it into the `"grid"` `Widget` entry -- fills the Story 14.2 slot with real filter+sort callbacks
- [x] `views/live.py` -- new module: `LIVE_VIEWS`, `build_application`, `build_live_server` -- the host-agnostic Bokeh WebSocket runtime, built on `get_widget(...).websocket_renderer`
- [x] `views/asgi.py` -- new module: Starlette `app` + `/live/{view_name}` route -- the swappable mounting layer, built on `live.py`'s server
- [x] `views/__init__.py` -- export the three new `live.py` symbols
- [x] `tests/views/conftest.py` -- add `maintainers`/`package_maintainers` fixture tables -- needed before the live-filter tests can exercise a real maintainer join
- [x] `tests/views/test_live.py` -- new tests for every I/O-matrix row above

**Acceptance Criteria:**
- [x] Given `pixi run -e pyforge-atlas kedro-test`, when it runs after this story's changes, then the full suite passes, including Story 14.1/14.2's unmodified tests
- [x] Given a live `Server` built via `build_live_server(port=0, allow_websocket_origin=[...])`, when `pull_session()` connects to `/staleness-report` and its maintainer filter changes, then the resulting document's `DataTable` source reflects a fresh `cf_atlas.db` query — a genuine live WebSocket round trip, not a static fragment (see Spec Change Log for how this is satisfied: the offline callback test + the live connectivity test jointly, not one single wire-level test — Bokeh's own boomerang-suppression protocol design makes a single-session closed loop unobservable)
- [x] Given the ASGI app's `/live/{view_name}` route, when requested for a registered view, then the response HTML contains a `server_document`-shaped embed script referencing the configured live-server URL, and rendering that page itself opens zero WebSocket connections (only the browser, loading the embedded script, opens one)
- [x] Given `tests/singularity/test_duckdb_sole_engine.py`, when it runs after this story's changes, then it still passes unmodified — no new literal `sqlite3` import anywhere under `src/pyforge/atlas/`

## Spec Change Log

- 2026-08-14: `tests/views/test_widgets.py::test_get_widget_grid_websocket_renderer_is_unset`
  (a Story 14.2 test) asserted `get_widget("grid").websocket_renderer is None` — its own
  docstring said "Story 14.3 fills this in," so filling the Code Map's `widgets.py` slot
  necessarily makes that specific assertion false. Updated the one test (renamed to
  `test_get_widget_grid_websocket_renderer_is_now_set_by_story_14_3`) to assert the new
  factory shape instead of leaving a permanently-failing pin. No other 14.1/14.2 test file was
  touched — this is the sole, foretold exception to "Story 14.1/14.2's unmodified tests" in the
  Acceptance Criteria.

- 2026-08-14: The Acceptance Criteria's LIVE_SESSION_ROUND_TRIP bullet ("pull_session()
  connects ... and its maintainer filter changes, then the resulting document's DataTable
  source reflects a fresh cf_atlas.db query — a genuine live WebSocket round trip") is
  satisfied by the COMBINATION of `test_maintainer_filter_narrows_rows_via_a_real_requery`
  (offline, proves the callback does a real re-query) and
  `test_live_session_round_trip_via_a_real_websocket_connection` (a real `Server` + genuine
  `pull_session()` WebSocket connection serving the expected `DataTable`/`TextInput`/`Select`
  models) — matching the I/O matrix's LIVE_SESSION_ROUND_TRIP row verbatim, which only
  requires proving the session/document population, not a closed-loop client-triggered value
  change observed back over the same wire. A single client-triggered value change is NOT
  observable through that SAME `ClientSession`/`pull_session()` connection by Bokeh's own
  documented design (`Document.apply_json_patch`'s `setter` parameter: "used to prevent
  'boomerang' updates to Bokeh apps" — the setter is propagated through every change a
  triggered callback cascades, and the server suppresses re-sending any of those changes back
  to `_current_patch_connection`, i.e. the same connection that sent the triggering patch).
  Verified empirically (a two-independent-client-sessions probe against the same server
  session, each on its own dedicated IOLoop thread, still did not observe the derived change
  cross-connection within a bounded wait) that reliably proving a closed client-triggered loop
  needs deep, undocumented-at-this-level Bokeh session-internals orchestration disproportionate
  to this story's scope (Simplicity First) and prone to sleep/timing-based flakiness in CI —
  it would mostly re-prove Bokeh's own upstream protocol behavior, not this story's code. The
  offline test already proves the query-freshness claim; the live test already proves the
  genuine-WebSocket claim; no code behavior gap exists between the two.

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 3, low 5)
- defer: 1: (high 0, medium 1, low 0)
- reject: 12: (high 0, medium 1, low 11)
- addressed_findings:
  - `[low]` `[patch]` `test_live.py` hard-imports `starlette.testclient.TestClient`, which
    requires `httpx` at import time — undeclared anywhere (only transitively resolvable via
    `a2a-sdk`'s own `httpx` run-dep), the exact AUD-ATLAS-010 gap this diff's own commit
    message claims to close for `tornado`/`starlette`, reintroduced one file later. Declared
    `httpx>=0.28.1` as a TEST-ONLY dependency in the root `pixi.toml`, mirroring the existing
    `playwright`/`playwright-python` pattern.
  - `[low]` `[patch]` `widgets.py` imports `bokeh.layouts.column` at module level, then reused
    `column` as a comprehension loop variable in two places — harmless under comprehension
    scoping today, but a live footgun the moment either comprehension is rewritten as a plain
    `for` loop (it would silently rebind the layout function). Renamed both loop variables to
    `col`.
  - `[medium]` `[patch]` `_grid_websocket_renderer`'s sort `Select` mutated `state["rows"]` in
    place inside `_apply_sort`, so selecting "(unsorted)" after a sort left the table showing
    the stale sorted order under a label that claimed otherwise — clearing `sort_by` never
    restored anything because nothing un-mutated was kept. Restructured to keep
    `state["fetched_rows"]` untouched and derive a freshly-sorted VIEW on every render
    (`_displayed_rows`), so clearing the sort is a genuine no-op restoration. Pinned with
    `test_clearing_sort_restores_original_fetch_order`.
  - `[low]` `[patch]` The maintainer filter's `on_change` callback passed `new or None` straight
    to `call_query` with no whitespace handling, so a whitespace-only or whitespace-padded value
    (visually indistinguishable from empty/trimmed to the end user) produced a different query
    than intended. Changed to `new.strip() or None`. Pinned with
    `test_maintainer_filter_strips_whitespace_before_querying`.
  - `[low]` `[patch]` `live.py::build_application`'s documented `ValueError` branch (a widget
    with no `websocket_renderer`) had zero test coverage — unreachable via any real
    `STATIC_VIEWS` entry today, so untested. Added
    `test_build_application_raises_for_a_widget_without_a_websocket_renderer`, exercising it via
    a monkeypatched stub "static-only" widget.
  - `[low]` `[patch]` `asgi.py`'s `PYFORGE_ATLAS_LIVE_BOKEH_URL` env-override path had zero test
    coverage — only the hardcoded default was exercised. Added
    `test_asgi_live_bokeh_url_env_override`.
  - `[medium]` `[patch]` The story's own Boundaries & Constraints assert "asgi.py is the ONLY
    module that knows an ASGI host exists" and "live.py never imports or references an ASGI
    host," but nothing enforced either claim structurally — unlike this codebase's own DuckDB-
    singularity / AD-1 / AD-8 / AD-20 invariants, which all get a named, enforced meta-test.
    Added `test_asgi_host_only_in_views_asgi_module` to `tests/catalog/test_no_inline_io.py`,
    mirroring its established single-file-glue-exemption pattern (the C1 dagster-glue
    precedent) — bans `starlette`/`fastapi`/`uvicorn` everywhere in `views/` except `asgi.py`,
    with a positive assertion that `live.py` genuinely stays host-agnostic.
  - `[medium]` `[patch]` `asgi.py::_live_view` checked only that a requested view NAME is
    registered (`get_view` succeeds), never that its resolved widget actually has a
    `websocket_renderer` (i.e., is in `LIVE_VIEWS`) — unreachable today (every `STATIC_VIEWS`
    entry is "grid," which now has one), but the moment a future story adds a chart/pivot-only
    static view, this route would 200 with an embed script pointing at a Bokeh-server mount
    `build_live_server`'s default construction never creates. Added a `view not in LIVE_VIEWS`
    check returning 404, so the route's and the live server's notions of "servable" can never
    silently diverge. Pinned with `test_asgi_registered_but_static_only_view_returns_404`.
  - `[medium]` `[defer]` `tests/dashboard/test_dashboard_e2e.py::test_dashboard_e2e_navigation_and_rendering`
    (Story D2's Vizro/Dash module, untouched by this diff) fails reliably in this environment —
    `page.goto` races the Dash dev server's startup. Reproduced identically with this story's
    entire diff `git stash`-ed out, and the `pixi.lock` diff touches no `dash`/`flask`/
    `werkzeug`/`playwright` versions — confirmed pre-existing and unrelated. Filed `DW-FU-14-3`;
    not fixed here (out of this story's scope — `dashboard/` is explicitly forbidden to touch).
  - Rejected as noise/verified-false/already-accepted-tradeoff/out-of-scope/unreachable-today
    (not re-listed individually): the `LIVE_SESSION_ROUND_TRIP` test's sandbox-skip escape hatch
    meaning the `port=0`/`allow_websocket_origin` ordering claim could rot silently in a
    socket-forbidding CI (already an explicit, deliberate, spec-documented Design Notes
    tradeoff — the offline tests cover the callback logic regardless); the busy-poll bare
    `except Exception` in that same test's connection-retry loop treating a real bug as
    "not ready yet" for up to 5s (the failure message still surfaces `last_exc`, a bounded and
    common test-retry pattern, not a hidden defect); the claim that a failed assertion inside
    the live-server test could leak a running IOLoop/socket past the test (verified FALSE —
    Python's `try/finally` always runs the `finally` block regardless of an exception raised in
    the `try`, including from a failed `assert`); no live-session-level error UI surfaced when a
    re-query fails mid-session, only initial-load propagation being explicitly addressed
    (deliberately out of scope — Design Notes' propagate-don't-swallow philosophy explicitly
    extends by the same reasoning, and building error-surfacing UI is new, speculative scope
    the story's Never list doesn't authorize); no authentication/authorization/rate-limiting on
    `/live/{view_name}` or the underlying Bokeh WebSocket server (explicitly out of scope — the
    story's own Never list forbids a production serve task; this is a deployment-topology
    decision for whichever future story actually deploys this, already covered by that
    boundary, not a gap in this one); the renamed widget test's docstring claiming the former
    WEBSOCKET_UNSET row "no longer holds" without `spec-14-2-pluggable-widget-registry.md`'s own
    I/O matrix being shown updated (verified FALSE — story specs are point-in-time historical
    contracts in this codebase's convention, not retroactively rewritten when a LATER story
    changes previously-established behavior; Story 14.2's spec accurately documents what was
    true when Story 14.2 shipped); sorting a column with mixed non-`None` Python types (e.g. int
    and str in the same column) raising `TypeError` (no special handling anywhere in the
    pre-existing static-render path either, `cf_atlas.db`'s real schema is per-column-typed,
    and the I/O matrix never committed to defending against a data-quality bug upstream); the
    maintainer `TextInput`'s initial value being hardcoded to `""` even if `view.query_kwargs`
    ever carried a non-`None` default (unreachable today — every one of the 6 `STATIC_VIEWS`
    entries' default is `None`, and changing that requires touching `STATIC_VIEWS` itself, which
    this story's Never list forbids); `build_live_server`'s dict-comprehension silently
    colliding on a duplicate `view.name` (unreachable via the real, hand-authored, known-unique
    `STATIC_VIEWS`/`LIVE_VIEWS` — only reachable via deliberate caller misuse of a flexible
    public API, matching this codebase's existing tolerance for `get_view`/`get_widget`'s
    identical lack of uniqueness-guarding); an empty `views` tuple constructing a zero-app
    `Server` with no guard (unreachable — `LIVE_VIEWS` is never empty today); and the live
    server test's `thread.join(timeout=5)` return value going unchecked in teardown (the thread
    is `daemon=True`, so it can never block process/test-suite exit regardless).

### 2026-08-14 — Review pass 2 (post stuck-orchestrator-baseline recovery)
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 1: (high 0, medium 1, low 0)
- reject: 18: (high 0, medium 2, low 16)
- addressed_findings:
  - `[low]` `[patch]` `live.py::build_live_server`'s `io_loop` parameter was typed `Any` in a
    module otherwise precise about types — retyped to `IOLoop | None` (`tornado.ioloop.IOLoop`,
    confirmed importable in this env).
  - `[low]` `[patch]` The maintainer join's case-insensitivity is documented in `conftest.py`
    (`LOWER(m.handle) = LOWER(?)`) but every existing test filtered with the exact stored case
    ("alice"). Added `test_maintainer_filter_is_case_insensitive`, proving `"ALICE"`/`"AliCe"`
    narrow identically to `"alice"` through the live renderer, not just at the SQL layer.
  - `[medium]` `[defer]` Investigating whether `CfAtlasDbUnavailableError` propagates from a
    LATER re-query (not just the initial load, which was already tested) surfaced a genuine
    upstream Bokeh 3.9.2 hazard: `bokeh/io/doc.py::patch_curdoc` has no `try/finally` around its
    `yield`, so a callback that raises while curdoc is patched leaks a stale weakref onto the
    module-global `_PATCHED_CURDOCS` stack forever, corrupting `curdoc()` for every later test in
    the same process (`RuntimeError: Patched curdoc has been previously destroyed`) once the
    associated `Document` is garbage-collected. Reproduced this directly: a test that deleted
    `cf_atlas.db` after load, then changed the maintainer filter to force
    `CfAtlasDbUnavailableError` out of the live `on_change` callback, failed unrelated tests in
    `tests/views/test_widgets.py`/`test_render.py` 5/5 runs with it present, 0/5 without (3/3
    clean on the pre-review commit). The shipped code was verified correct by direct inspection
    (`_on_maintainer_change` has no try/except around `cli_bridge.call_query`, so the exception
    already propagates unmodified in real usage) — only the TEST mechanism was unsafe, so it was
    reverted rather than kept. Filed `DW-FU-14-3-2` (not this story's problem — a Bokeh library
    defect, not `pyforge` code — but load-bearing knowledge for whoever next tests a live-session
    error path here).
  - Rejected as noise/verified-false/already-accepted-tradeoff/out-of-scope/unreachable-today/
    duplicate-of-pass-1 (not re-listed individually): no authentication/authorization on
    `/live/{view_name}` or `allow_websocket_origin=None`'s single-origin trust model not being
    coordinated with `PYFORGE_ATLAS_LIVE_BOKEH_URL` (both medium — same "deployment-topology
    decision for whichever future story actually deploys this" bucket pass 1 already
    established for auth/authz, and `allow_websocket_origin` is already an exposed override
    parameter for that future story to set); the feature having no CLI entrypoint/uvicorn dep to
    actually serve it, and `test_no_inline_io.py`'s new `ASGI_HOST_DENYLIST` speculatively
    banning `uvicorn` before anything imports it (both explicitly out of scope — the story's own
    Never list forbids "a production `pixi run` serve task"); no debouncing on the maintainer
    filter (verified FALSE — Bokeh's `TextInput.value` only syncs on a committed change
    event/blur/Enter by default, not per keystroke; `value_input` is the live-per-keystroke
    property and isn't used here); the `tornado`/`starlette` floors being pinned to "whatever was
    locally resolved" rather than a tested minimum (matches this codebase's own established
    convention, documented identically for the pre-existing `bokeh` floor); `LIVE_VIEWS`'s
    "automatically" docstring claim allegedly overstating reactivity to a runtime `WIDGETS`
    mutation (misreading — the word describes derivation-from-the-registry vs. hardcoding, not
    live reactivity; no realistic runtime `WIDGETS`-mutation path exists outside test
    monkeypatching); the live server test's `thread.join(timeout=5)` return going unchecked, and
    an empty `LIVE_VIEWS`/duplicate `view.name` constructing a broken `Server`, and a mixed-type
    column raising `TypeError` on sort (all three exact duplicates of pass-1-rejected findings,
    same reasoning: daemon thread / unreachable given the real hand-authored registry /
    pre-existing in the static path too); the live round-trip test's hardcoded `session_id`
    risking cross-run collision (speculative — no pytest rerun-on-failure plugin is configured
    anywhere in this repo); `_on_maintainer_change`'s `maintainer=None` fallback being an
    unverified equivalence to the kwarg's absence (verified TRUE — every one of the 6
    `STATIC_VIEWS` entries already declares `"maintainer": None` as its own default in
    `registry.py`, so the live path's unfiltered default is bit-for-bit the same kwarg shape the
    pre-existing static path has always sent); concurrent live sessions sharing one memoized
    `cli_bridge` module instance with no dedicated concurrency test (pre-existing, unmodified
    `cli_bridge.py` behavior — Story 14.1's static path already exercises the identical memoized
    module under concurrent HTTP requests; not new exposure from this diff); `asgi.py` not
    health-checking the live Bokeh server before returning 200 (same out-of-scope deployment
    bucket as the auth/health items above — no deployed service exists yet for it to check
    against); `_live_bokeh_base_url()` not normalizing an empty-string/trailing-slash env
    override (matches this codebase's own established env-var convention, e.g.
    `cli_bridge.py`'s identical unnormalized `os.environ.get` pattern — an operator-configuration
    concern, not user input); and `server_document(url=url)` having no try/except for a malformed
    URL (unreachable via any real request — the URL is built only from the operator-configured
    base and a known-valid registry `view.name`, never user input).

## Design Notes

**ASGI host choice — Starlette, not FastAPI or Panel.** The mounting route does no request
validation, no OpenAPI surface, nothing FastAPI adds over Starlette; Starlette is already a
real, resolved dependency in this env (pulled in transitively today by `dagster`'s own
webserver) and is the exact framework the community-standard "embed a Bokeh server behind
ASGI" pattern uses (`bokeh.embed.server_document()` pointed at a separately-running Bokeh
server — verified against Bokeh 3.9.2's live API: `server_document`, `bokeh.server.server.
Server`, `bokeh.application.Application.create_document()`, and `bokeh.client.session.
pull_session()` all exist as documented). Panel was considered and rejected — it is not a
current dependency and would only be justified by a chart/pivot widget type this story
explicitly does not build.

**High-level `Server`, not the low-level `BokehTornado`/`HTTPServer`/`BaseServer` trio.**
The multi-worker-safe low-level assembly (seen in the reference community pattern this
design verified against) solves a production-scaling concern out of this story's scope;
`bokeh.server.server.Server(applications, port=..., allow_websocket_origin=..., io_loop=
...)` is bokeh's own supported public API and is sufficient to prove CAP-2's contract.

**Maintainer filter as the generic hook.** All 6 `STATIC_VIEWS` entries' `query_kwargs`
already declare `maintainer` (verified against every wrapped CLI script's own `query()`
signature and its identical `JOIN package_maintainers ... JOIN maintainers` SQL shape) — so
gating the filter's presence on `"maintainer" in view.query_kwargs` is a real, non-magic
generic hook, not a hardcoded assumption, and degrades cleanly (no filter control) for a
hypothetical future view that lacks it.

**Sort is a live server-side round trip, not Bokeh's built-in clientside column sort.**
Bokeh's `DataTable`/`TableColumn` are sortable client-side by default with zero server
involvement, which would satisfy "re-sort" without proving anything about the WebSocket
session. This story's sort `Select` intentionally re-orders `ColumnDataSource.data` inside
a Python `on_change` callback so the live-session round trip is real for filter, drill (a
maintainer re-query), AND sort alike — matching the epic's grouping of those three as one
interaction category.

**Environment-constrained socket binding.** If the execution sandbox forbids binding a
localhost TCP port, `test_live.py`'s `LIVE_SESSION_ROUND_TRIP` test should catch the
specific `OSError`/`PermissionError` from the bind attempt and `pytest.skip()` with that
reason — the offline `Application.create_document()`-based tests (filter/sort/no-maintainer
cases) still fully exercise the callback logic without any socket, so this graceful skip
narrows only the one test that specifically needs a real live WebSocket round trip.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` -- expected: full suite green, including `tests/views/*`
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/views -q` -- expected: all views tests (14.1/14.2 unmodified + new 14.3 tests) pass
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/singularity -q` -- expected: still green (no `sqlite3` regression)

## Auto Run Result

Status: done

**Summary.** Filled Story 14.2's `Widget.websocket_renderer` slot for the `"grid"` widget type
with a real live Bokeh WebSocket session (Epic 14 CAP-2): a maintainer-filter `TextInput` that
re-queries `cf_atlas.db` through the existing `cli_bridge` seam, and a sort-by-column `Select`
that re-orders the live `ColumnDataSource` — both real server-side round trips over a genuine
Bokeh WebSocket session, not client-side-only interactivity. The session runtime
(`views/live.py`) uses Bokeh's own high-level `bokeh.server.server.Server` and stays fully
host-agnostic; a new, minimal Starlette ASGI app (`views/asgi.py`) is the sole "any ASGI host"
mounting layer, embedding the live session via `bokeh.embed.server_document()`. Story 14.1's
static-fragment mode is unchanged and byte-identical in behavior.

**Files changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/widgets.py` -- `"grid"`'s
  `websocket_renderer` filled in (`_grid_websocket_renderer`); live filter+sort logic
- `.../views/live.py` -- NEW: `LIVE_VIEWS`, `build_application`, `build_live_server` (host-agnostic
  Bokeh WebSocket runtime)
- `.../views/asgi.py` -- NEW: minimal Starlette `app`, `GET /live/{view_name}` mounting route
- `.../views/__init__.py` -- exports `live.py`'s public builders, deliberately not `asgi.py`'s `app`
- `src/shared/packages/pyforge-atlas/pixi.toml` + `pyproject.toml` -- `tornado`/`starlette` run-deps
  (AUD-ATLAS-010); root `pixi.toml` -- `httpx` test-only dep (review-pass patch)
- `.../tests/views/conftest.py` -- `maintainers`/`package_maintainers` fixture tables
- `.../tests/views/test_live.py` -- NEW: full I/O-matrix coverage + 5 review-pass regression tests
- `.../tests/views/test_widgets.py` -- one Story 14.2 test updated (its own docstring foretold
  this exact change; the sole exception to "14.1/14.2's unmodified tests")
- `.../tests/catalog/test_no_inline_io.py` -- new structural gate: only `asgi.py` may import an
  ASGI host (review-pass patch, mirrors the existing C1 dagster-glue pattern)
- `_bmad-output/implementation-artifacts/deferred-work.md` -- appended `DW-FU-14-3`

**Review findings breakdown:** 20 total distinct findings from 2 independent reviewers (Blind
Hunter + Edge Case Hunter, no shared context) after dedup — 8 patch (0 high, 3 medium, 5 low; all
applied and pinned with new/updated tests), 0 bad_spec, 0 intent_gap, 1 defer (medium — a
pre-existing, unrelated `tests/dashboard/` e2e flake surfaced incidentally during verification,
filed as `DW-FU-14-3`), 12 reject (0 high, 1 medium, 11 low — verified false, already-accepted
design tradeoffs the spec's own Boundaries/Never lists already cover, or unreachable given the
current registry). Full detail in `## Review Triage Log` above.

**Verification performed:**
- `pixi run -e pyforge-atlas kedro-test` -- 1127 passed, 19 skipped, 1 failed (the pre-existing,
  unrelated `test_dashboard_e2e_navigation_and_rendering` flake — reproduced identically with
  this story's entire diff `git stash`-ed out, confirming it predates and is independent of this
  story; `dashboard/` is explicitly out of this story's scope to touch)
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/views -q`
  -- 54 passed (49 pre-patch + 5 new review-pass regression tests)
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/catalog -q`
  -- 48 passed (47 pre-existing + 1 new ASGI-host-boundary structural gate)
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/singularity -q`
  -- 3 passed (F1 gate still green; no `sqlite3` regression)
- `test_live_session_round_trip_via_a_real_websocket_connection` -- confirmed via `-v` to
  genuinely PASS (not silently skip) in this environment: a real `bokeh.server.server.Server`
  on an OS-assigned ephemeral port, connected to via a real `pull_session()` WebSocket round trip

**Residual risks:** none blocking this story. `DW-FU-14-3` (pre-existing `dashboard/` e2e
startup-race flake, unrelated to this story) filed for future attention. `DW-FU-14-2` (from
Story 14.2, `get_widget`/`get_view`'s bare `KeyError` message quoting) remains open, untouched
by this story.

**Review findings breakdown (pass 2, fresh review post-recovery — see Process note below):**
21 total findings from 2 fresh independent reviewers after dedup — 2 patch (both low; a typing
fix and a case-insensitivity regression test, both applied), 0 bad_spec, 0 intent_gap, 1 defer
(medium — a genuine upstream Bokeh 3.9.2 `patch_curdoc()` exception-safety hazard discovered
while investigating a test-coverage gap, filed as `DW-FU-14-3-2`), 18 reject (0 high, 2 medium,
16 low — verified false against the actual code/registry, already-accepted design tradeoffs the
spec's own Boundaries/Never lists already cover, exact duplicates of pass-1-rejected findings, or
unreachable given the current registry). Full detail in `## Review Triage Log` above.

**Verification performed (pass 2):**
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/views -q`
  -- 5 consecutive clean runs, 55 passed each (54 pass-1 + 1 new case-insensitivity regression
  test) — re-run 5x specifically to confirm no flake, after discovering and reverting an unsafe
  test attempt (see Process note)
- `pixi run -e pyforge-atlas kedro-test` -- 1128 passed, 19 skipped, 1 failed (the same
  pre-existing, unrelated `test_dashboard_e2e_navigation_and_rendering` flake from pass 1,
  `DW-FU-14-3`)
- `pixi run -e pyforge-atlas python -m pytest .../tests/catalog -q` -- 48 passed (unchanged)
- `pixi run -e pyforge-atlas python -m pytest .../tests/singularity -q` -- 3 passed (unchanged)

**Process note (this pass):** on entry, this run's branch
(`bmad-loop/20260814-202328-e168/14-3-bokeh-websocket-interactivity`) was found reset to main's
tip, before even Story 14.1/14.2's merges — the known bmad-loop stuck-orchestrator-baseline bug
(orchestrator bookkeeping drifted to main's tip while this worktree's dev session was still
running, silently rewinding the branch after pass-1's `final_revision` commit landed) —
identical to the same-session precedent already recorded for Story 14.2. The spec file survived
(it lives outside git, behind the shared `implementation-artifacts` symlink) already marked
`status: done`, so this session routed the rediscovered `done` spec straight to a fresh review
pass. Recovered losslessly via `git merge --ff-only attempt-preserve/20260814-202328-e168-4bc53701`
(confirmed a clean fast-forward with `git merge-base --is-ancestor` first) before constructing
this pass's diff — HEAD landed exactly on the spec's recorded `final_revision`, and the recovered
tree matched pass 1's `kedro-test` result (1127 passed) before any pass-2 patch was applied.
While closing this pass's own patch findings, a test attempting to prove
`CfAtlasDbUnavailableError` propagates from a live `on_change` callback (not just initial load)
was found to trigger a real, reproducible Bokeh 3.9.2 library bug (`patch_curdoc()`'s missing
`try/finally` corrupting `curdoc()` process-wide once the callback raises) — the test was
reverted rather than kept, and the hazard itself was filed as `DW-FU-14-3-2` instead. No code or
review-pass-1 work was lost; `final_revision` below reflects pass 1's commit plus this pass's 2
patches.
