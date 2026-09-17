---
title: 'Story 14.4: Air-gap asset rewriting (CAP-4)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_revision: '51262819e76bde4d19c9511b20925e815b1c0503'
final_revision: '4e32c96772b2e203c35f6579c9253a171ca39bd6'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Neither the static-fragment path (Story 14.1/14.2) nor the WebSocket-app path
(Story 14.3) documents or regression-tests where Bokeh's JS/CSS assets resolve from — a real
air-gap risk stays silent: nothing today would catch a future change (or an operator's
`BOKEH_RESOURCES` misconfiguration) pointing asset loading at `cdn.bokeh.org`.

**Approach:** Investigated empirically (a real `build_live_server` + HTTP fetch): the static
path (`bokeh.embed.components()`) never emits any asset URL, and the live WebSocket app
already resolves BokehJS/CSS from itself (`/static/js/...`, zero external references) by
Bokeh's own server-context default — governed entirely by Bokeh's native `BOKEH_RESOURCES` env
var, which already composes with `_http.py`'s posture (env-vars-only, operator-set, never
committed) with no translation layer needed. This story makes that guarantee explicit
(`views/resources.py`, a read-only introspection module) and regression-tested — no production
rendering code changes, since both paths are already correct.

## Boundaries & Constraints

**Always:** `views/resources.py` only READS `BOKEH_RESOURCES` (via
`bokeh.settings.settings.resources`), never writes/sets it — the render profile stays entirely
operator/environment-controlled, mirroring `_http.py`'s read-only env var posture.
`current_mode()` must call `bokeh.settings.settings.resources(default="server")` — the exact
call and default `bokeh/server/tornado.py` uses internally — so introspection reflects reality,
not a second, possibly-diverging assumption.

**Block If:** none — this story is confirmatory/regression-test work over an already-correct
mechanism; no unattended decision points exist.

**Never:** build a CDN-asset-mirroring/download pipeline (out of scope — `mode="server"`
already serves Bokeh's own bundled assets locally, zero extra infrastructure needed).
Introduce a second, pyforge-specific env var duplicating `BOKEH_RESOURCES` (would violate
"compose with `_http.py`'s posture... never a second config path"). Hardcode
`Resources(mode="cdn")` or any `cdn.bokeh.org` literal anywhere in `views/*.py` production
code. Touch `dashboard/` (the separate, untouched Vizro module). Change any `STATIC_VIEWS` or
`WIDGETS` registry entry. Add a production `pixi run` serve task (still out of scope, per Story
14.3's Never list, unchanged here).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| DEFAULT_PROFILE_LIVE | No `BOKEH_RESOURCES` set; a real `build_live_server` serving one view | The served page's HTML contains zero `cdn.bokeh.org` references — all Bokeh JS/CSS asset URLs are same-origin (`/static/js/...`) | No error expected |
| CDN_PROFILE_NEGATIVE_CONTROL | `BOKEH_RESOURCES=cdn` set; same real live server | The served page's HTML DOES contain `cdn.bokeh.org` — proves DEFAULT_PROFILE_LIVE isn't a tautology | No error expected |
| AIRGAPPED_MODE_INTROSPECTION | `BOKEH_RESOURCES` set to each of `server`/`server-dev`/`inline`/`relative`/`relative-dev`/`absolute`/`absolute-dev` | `resources.is_airgapped()` returns `True` for every one | No error expected |
| CDN_MODE_INTROSPECTION | `BOKEH_RESOURCES=cdn` | `resources.is_airgapped()` returns `False` | No error expected |
| STATIC_FRAGMENT_NO_CDN | Every registered `STATIC_VIEWS` entry, rendered via `render_rows` | Neither `script` nor `div` ever contains `cdn.bokeh.org` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/resources.py` -- NEW:
  `current_mode() -> str` (reads `bokeh.settings.settings.resources(default="server")`) and
  `is_airgapped() -> bool` (`current_mode() != "cdn"`) — the single, read-only, documented
  source of truth for "which render profile is active," composing with Bokeh's own
  `BOKEH_RESOURCES` env var rather than a duplicate pyforge-specific toggle
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/live.py` -- one-sentence module
  docstring addition cross-referencing `resources.py` and explaining the live server's
  already-local default (discoverability only, zero behavior change)
- `src/shared/packages/pyforge-atlas/tests/views/test_render.py` -- add `"cdn.bokeh.org"` to
  the existing `FORBIDDEN_MARKERS` tuple (line 25); the existing
  `test_no_registered_view_fragment_opens_a_websocket` parametrized loop over all
  `STATIC_VIEWS` picks it up with zero new test code
- `src/shared/packages/pyforge-atlas/tests/views/test_live.py` -- add a
  `"cdn.bokeh.org" not in body` assertion to the existing
  `test_asgi_registered_view_embeds_a_server_document_script` test (mirrors its existing
  `ws://`/`wss://` checks)
- `src/shared/packages/pyforge-atlas/tests/views/test_resources.py` -- NEW: unit tests for
  `current_mode()`/`is_airgapped()` across all 8 Bokeh resource modes plus unset, and the two
  real-live-server HTTP-level regression tests (DEFAULT_PROFILE_LIVE,
  CDN_PROFILE_NEGATIVE_CONTROL), reusing `test_live.py`'s `atlas_db_path`-fixture-and-loaded-
  module pattern and its "skip if sandbox forbids a socket bind" escape hatch

## Tasks & Acceptance

**Execution:**
- [x] `views/resources.py` -- new module: `current_mode()`, `is_airgapped()` -- the render-
  profile introspection this story's regression tests and future stories rely on
- [x] `views/live.py` -- one-sentence docstring addition cross-referencing `resources.py` --
  makes the already-correct default behavior discoverable, not accidental
- [x] `tests/views/test_render.py` -- add `"cdn.bokeh.org"` to `FORBIDDEN_MARKERS` -- pins the
  static-fragment half of CAP-4's contract via the existing parametrized gate
- [x] `tests/views/test_live.py` -- add a `cdn.bokeh.org` absence assertion to the existing
  server_document embed test -- pins the ASGI embed script's half of the contract
- [x] `tests/views/test_resources.py` -- new tests covering the full I/O matrix above --
  the live-server HTTP-level proof is the load-bearing regression gate for CAP-4

**Acceptance Criteria:**
- Given `pixi run -e pyforge-atlas kedro-test`, when it runs after this story's changes, then
  the full suite passes, including Story 14.1/14.2/14.3's unmodified behavior
- Given the default (non-air-gapped) profile, when any pre-existing Story 14.1-14.3 test runs,
  then its output is unchanged — no rendering-path production code (`render.py`/`widgets.py`/
  `asgi.py`, and `live.py` beyond its docstring) is modified by this story
- Given a real live server started under the default profile, when its served page HTML is
  grepped for `cdn.bokeh.org`, then there are zero matches — the CAP-4 grep-verifiable contract

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 2, low 2)
- defer: 0
- reject: 9: (high 0, medium 0, low 9)
- addressed_findings:
  - `[medium]` `[patch]` `resources.py::is_airgapped()` was a denylist (`current_mode() !=
    "cdn"`) — an unrecognized or malformed `BOKEH_RESOURCES` value would report `True`
    (air-gap-safe) with zero validation, a false-safe reading on exactly the question the
    function exists to answer (flagged independently by both reviewers). Verified Bokeh's own
    `Resources(mode=...)` rejects an invalid mode with `ValueError` at render time, but
    `is_airgapped()` itself still misreported such a value in isolation. Rewrote as an
    allowlist against Bokeh's 7 known locally-served modes (`_LOCALLY_SERVED_MODES`), so an
    unknown value now conservatively reports `False` (not verified safe) instead of `True`.
  - `[medium]` `[patch]` The `"cdn.bokeh.org"` checks added to `test_render.py`'s
    `FORBIDDEN_MARKERS` and `test_live.py`'s server_document test are structural invariant
    pins that can never fail today (neither `components()` nor `server_document()`'s own
    return value reads `BOKEH_RESOURCES`) — leaving CAP-4's static-fragment half verified only
    coincidentally, under whichever `BOKEH_RESOURCES` value happened to be ambient, with no
    test forcing the one value (`cdn`) that actually changes the live path's behavior. Added
    `test_resources.py::test_static_fragment_stays_cdn_free_even_under_an_explicit_cdn_profile`
    (explicit `BOKEH_RESOURCES=cdn`, real `render_rows()` call) as the dynamic counterpart, and
    added clarifying comments to both pre-existing assertions distinguishing "structural pin"
    from "dynamic profile-dependent test."
  - `[low]` `[patch]` `views/__init__.py` re-exports every other story's public module surface
    (`live.py`, `registry.py`, `widgets.py`, `render.py`) but omitted `resources.py`'s
    `current_mode`/`is_airgapped`, an inconsistency with established convention. Added both to
    the import and `__all__`.
  - `[low]` `[patch]` `resources.py`'s module docstring cited "mirroring `_http.py`'s posture"
    without disclosing that no `_http.py` exists anywhere in this package — it belongs to the
    unrelated conda-forge-expert skill's script directory. Reworded to name the actual path
    and clarify it as a sibling-area precedent, not a local one.
  - `[low]` `[reject]` `resources.py`'s functions are called by no production code today (not
    wired into `live.py`/`asgi.py`'s runtime construction) — by design, per this story's own
    Design Notes: Bokeh's per-request resource resolution means a one-shot runtime override
    would have no lasting effect, and the module's documented purpose is regression-test
    introspection now, consumed by future stories later. The `__init__.py` export patch above
    already closes the one genuine inconsistency (public-surface omission) this finding also
    raised.
  - Rejected as noise/out-of-scope/already-precedented (not re-listed individually): the
    "vacuous" characterization of the two structural-pin assertions as a standalone complaint
    (the real coverage gap it points at was patched above; the pins themselves match this
    file's own pre-existing `FORBIDDEN_MARKERS` convention for `ws://`/`wss://`/etc.);
    `sprint-status-ledger.yaml:35` and `epics.md`'s Story 14.4 entry still reading
    stale/backlog status (neither is touched by any step in this workflow — Stories
    14.1-14.3's "done" entries were evidently set by a downstream, post-merge process, and
    epics.md sync is explicitly the responsibility of separate reconciler skills per this
    repo's documented convention, not dev-auto); no operator-facing health-check/doctor/
    startup-log surface for `resources.py` (a reasonable future enhancement, but outside this
    Effort:S story's explicit scope — the spec's own Code Map named "this story's regression
    tests and future stories" as the intended consumers); `test_resources.py::_loaded_module`
    being a duplicate of `test_live.py`'s identical helper (real, but disproportionate scope
    expansion to fix now — touching `test_live.py`'s already-shipped, already-reviewed code for
    a cosmetic, zero-functional-impact nit); `_fetch_live_page`'s `server.start()` call sitting
    outside its `try/finally` and `thread.join(timeout=5)`'s return going unchecked before
    `server.stop()` (both are the exact pattern already shipped and reviewed twice in
    `test_live.py`'s own `test_live_session_round_trip_via_a_real_websocket_connection` —
    Story 14.3's Review Triage Log pass 1 explicitly rejected the analogous `thread.join`
    finding with "the thread is daemon=True, so it can never block process/test-suite exit
    regardless," which applies identically here); and a suggestion to normalize
    `BOKEH_RESOURCES`'s case/whitespace before comparison (verified this would make
    `is_airgapped()` diverge from Bokeh's own real behavior — `Resources(mode=...)` itself
    rejects a differently-cased value like `"CDN"` with `ValueError` rather than normalizing
    it, so matching Bokeh's actual behavior, not "fixing" it, is correct per this module's own
    "reflects reality" design principle).

## Design Notes

**Bokeh's live server already defaults to `mode="server"`, not `"cdn"` — verified
empirically.** `bokeh/server/tornado.py`'s resource-resolution call is
`settings.resources(default="server")`, not the library-wide `PrioritizedSetting` default of
`"cdn"` — so a `bokeh.server.server.Server`-hosted app (this module's `live.py::
build_live_server`) is air-gap-safe out of the box unless an operator explicitly sets
`BOKEH_RESOURCES=cdn`. Confirmed with a real ephemeral-port server + HTTP fetch: default and
`BOKEH_RESOURCES=server` both produced `<script src="/static/js/bokeh.min.js?v=...">` (no
external host); `BOKEH_RESOURCES=cdn` produced `<script src="https://cdn.bokeh.org/...">`.

**No dedicated pyforge-specific env var.** `_http.py`'s functions only ever *read* env vars,
never write them — operators set them before the process starts. Introducing a
`PYFORGE_ATLAS_AIRGAP`-style var would require this module to write `BOKEH_RESOURCES` or
Bokeh's settings singleton at runtime for it to have any effect (the resource mode is resolved
fresh per-request, long after any one-shot construction-time override would have been unset),
which is more moving parts for zero behavioral gain over just documenting and reading Bokeh's
own already-correct, already-native env var.

**No CDN-mirroring pipeline.** `mode="server"`/`"absolute"` already serve Bokeh's own bundled
JS/CSS (shipped inside the installed `bokeh` package) with no network fetch and no extra
infrastructure — there is nothing to mirror.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` -- expected: full suite green, including
  `tests/views/*`
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/views -q`
  -- expected: all views tests (14.1/14.2/14.3 unmodified + new 14.4 tests) pass

## Auto Run Result

Status: done

**Summary.** Closed CAP-4 for Epic 14: the static-fragment path (`components()`) and the live
WebSocket app (`bokeh.server.server.Server`) were both empirically verified to already be
air-gap-safe by default — Bokeh's own server-context default (`mode="server"`, not the
library-wide `"cdn"` default) means BokehJS/CSS resolve same-origin unless an operator
explicitly sets `BOKEH_RESOURCES=cdn`. This story made that guarantee explicit
(`views/resources.py`: read-only `current_mode()`/`is_airgapped()` introspection, composing
with Bokeh's own native env var rather than a duplicate pyforge-specific toggle) and
regression-tested it with real HTTP-level proof (a genuine `build_live_server` round trip
under both the default and an explicit `BOKEH_RESOURCES=cdn` negative control), plus
static-fragment coverage under the same explicit CDN profile. No production rendering-code
behavior changed — `render.py`/`widgets.py`/`asgi.py` are untouched; `live.py` gained one
documentation sentence.

**Files changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/resources.py` -- NEW:
  `current_mode()`/`is_airgapped()`, read-only render-profile introspection (allowlist-based
  after the review pass)
- `.../views/live.py` -- one-sentence docstring cross-reference to `resources.py`
- `.../views/__init__.py` -- re-exports `current_mode`/`is_airgapped` (review-pass patch,
  matching every other module's public surface)
- `src/shared/packages/pyforge-atlas/tests/views/test_render.py` -- `"cdn.bokeh.org"` added to
  `FORBIDDEN_MARKERS`, plus a clarifying comment (review-pass patch)
- `.../tests/views/test_live.py` -- `cdn.bokeh.org` absence assertion added to the existing
  server_document embed test, plus a clarifying docstring note (review-pass patch)
- `.../tests/views/test_resources.py` -- NEW: full I/O-matrix coverage (8 resource-mode
  introspection cases, 2 real-live-server HTTP round trips) + one review-pass addition proving
  the static path stays CDN-free under an explicit `BOKEH_RESOURCES=cdn` profile

**Review findings breakdown:** 13 total distinct findings from 2 independent reviewers (Blind
Hunter + Edge Case Hunter, no shared context) after dedup — 4 patch (0 high, 2 medium, 2 low;
all applied and verified), 0 bad_spec, 0 intent_gap, 0 defer, 9 reject (0 high, 0 medium, 9
low — verified as by-design, out of this workflow's scope, disproportionate for Effort:S, or
exact duplicates of patterns Story 14.3's own review already precedent-rejected). Full detail
in `## Review Triage Log` above.

**Verification performed:**
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/views -q`
  -- 67 passed (66 pre-patch + 1 new review-pass regression test)
- `pixi run -e pyforge-atlas kedro-test` -- 1141 passed, 19 skipped, 0 failed

**Residual risks:** none blocking. `resources.py`'s `current_mode`/`is_airgapped` are not yet
consumed by any production code path (by design — see Design Notes and the review pass's
rejected "dead code" finding) — a future story that adds operator-facing surfacing (health
check, startup log) would be a reasonable, separately-scoped follow-up, not required here.
