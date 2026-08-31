---
title: 'Story 14.2: Pluggable widget registry (CAP-3)'
type: 'feature'
created: '2026-08-14'
status: 'done'
baseline_revision: 'e1043d97187ecc36fae8ced895861d36c66f7267'
final_revision: '51587c6c5734ff5654e1e30cf0dea7293742e74b'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 14.1's `render.py::render_rows` hardcodes one Bokeh shape
(`ColumnDataSource`→`DataTable`) directly inline — every `View` renders the same way, and a
future widget type (chart, pivot) would mean editing this shared function itself.

**Approach:** Add a small `widgets.py` module: a `Widget` dataclass (name + a
`static_renderer` callable, plus a `websocket_renderer` slot Story 14.3 fills in later) and a
`WIDGETS` name→`Widget` registry dict. Give `View` a `widget: str` field so each view declares
its widget-type name explicitly; `render_rows` becomes a one-line dispatch through
`get_widget(view.widget)` instead of a hardcoded body. Seed the registry with exactly one
entry, `"grid"` (the DataTable shape moved verbatim out of `render.py`), because a survey of
all 11 mirrored CLIs' query shapes (below) shows every one of today's 6 `STATIC_VIEWS` is
grid-shaped — no view needs a chart/pivot renderer yet, so none is built speculatively.

## Boundaries & Constraints

**Always:** dispatch by `view.widget` NAME through `WIDGETS` — `render_rows`/`render_view`
never construct a Bokeh model type directly (that logic lives only in a widget's
`static_renderer`). Every `STATIC_VIEWS` entry explicitly declares `widget="grid"`.
`Widget.websocket_renderer` defaults to `None` on every entry — Story 14.3 wires interactivity
in later, not this story. Import direction stays a strict line, `registry.py` → `widgets.py` →
`render.py` (never the reverse), so `View` never imports from `widgets.py` — this is why
`get_widget()` validates the widget name at render time (`KeyError` on miss) rather than at
`View` construction time.

**Block If:** making `render_rows` dispatch through the registry cannot be done as a pure,
behavior-preserving extraction of Story 14.1's shipped `tests/views/test_render.py` (i.e. any
of its existing assertions would need to change, not just survive unchanged) — report which
assertion and why.

**Never:** implement a "chart" or "pivot" renderer in this story — no current view needs one;
adding either is a future story's one-entry-plus-one-renderer addition, not this one's.
Never implement Bokeh WebSocket/live-session rendering (Story 14.3). Never modify
`dashboard/` (the separate, untouched Vizro module). Never change any `STATIC_VIEWS` entry's
`columns`/`query_kwargs`/`script` — only add the new `widget` field.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | `get_widget("grid")` | Returns the registered `Widget`; its `static_renderer(view, rows)` reproduces the exact pre-refactor fragment | No error expected |
| UNKNOWN_WIDGET | `get_widget("bogus")` | — | raises `KeyError` naming all known widget-type names, mirroring `registry.py::get_view`'s error style |
| EXTENSIBILITY | a throwaway widget type registered only inside a test (`monkeypatch.setitem(WIDGETS, ...)`) | The 6 existing `STATIC_VIEWS`/`View` entries are unmodified — no edit to `registry.py` was needed | No error expected |
| WEBSOCKET_UNSET | `get_widget("grid").websocket_renderer` | `None` — Story 14.3 fills this in | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/widgets.py` -- NEW: `Widget` dataclass, `WIDGETS` registry dict, `get_widget()`, and the `"grid"` renderer (moved verbatim from `render.py`'s current `render_rows` body)
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/registry.py` -- add `widget: str` field to `View` (positioned after `script`, before `columns`; no default — every `STATIC_VIEWS` entry declares it explicitly)
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/render.py` -- `render_rows` becomes `return get_widget(view.widget).static_renderer(view, rows)`; drop its now-unused `bokeh.embed`/`bokeh.models` imports; `render_view()` body unchanged
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/__init__.py` -- export `Widget`, `WIDGETS`, `get_widget` alongside the existing exports
- `src/shared/packages/pyforge-atlas/tests/views/test_widgets.py` -- NEW: covers the I/O matrix above
- `src/shared/packages/pyforge-atlas/tests/views/test_render.py` -- unchanged; its direct `render_rows(view, rows)` calls must keep passing exactly as-is (the regression proof)
- `src/shared/packages/pyforge-atlas/tests/views/conftest.py` -- reused unmodified (`atlas_db_path`/`empty_atlas_db_path` fixtures)

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/widgets.py` -- add `Widget` (frozen dataclass: `name: str`, `static_renderer: Callable[[View, list[dict[str, Any]]], tuple[str, str]]`, `websocket_renderer: Callable[..., Any] | None = None`), a private grid-rendering function holding the `ColumnDataSource`→`TableColumn`→`DataTable`→`components()` body moved from `render.py`, `WIDGETS: dict[str, Widget] = {"grid": Widget(...)}`, and `get_widget(name) -> Widget` raising `KeyError` naming known types on miss -- the pluggable dispatch surface CAP-3 requires
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/registry.py` -- add `widget: str` to `View`, set `widget="grid"` on all 6 `STATIC_VIEWS` entries -- "a view declares its query plus a widget-type NAME"
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/render.py` -- replace `render_rows`'s hardcoded body with a one-line `get_widget(...)` dispatch; remove the bokeh imports it no longer needs
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/__init__.py` -- export `Widget`, `WIDGETS`, `get_widget`
- [x] `src/shared/packages/pyforge-atlas/tests/views/test_widgets.py` -- new tests for all 4 I/O-matrix rows, plus one asserting `render_rows`'s output is byte-identical before/after the refactor for a sample view

**Acceptance Criteria:**
- Given `pixi run -e pyforge-atlas kedro-test`, when it runs after this story's changes, then the full suite passes, including Story 14.1's unmodified `test_render.py`
- Given `tests/singularity/test_duckdb_sole_engine.py`, when it runs after this story's changes, then it still passes unmodified — no new literal `sqlite3` import anywhere under `src/pyforge/atlas/`
- Given the 6 `STATIC_VIEWS` entries, when this story's diff is inspected, then only the new `widget` field was added to each — `name`/`title`/`script`/`columns`/`query_kwargs` are byte-identical to Story 14.1's shipped values

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 1, low 5)
- defer: 2: (high 0, medium 0, low 2)
- reject: 9: (high 0, medium 0, low 9)
- addressed_findings:
  - `[low]` `[patch]` `widgets.py`'s docstring justified seeding only `"grid"` by citing the
    11-CLI survey in a way that read as a non-sequitur (11 CLIs surveyed vs. 6 STATIC_VIEWS
    entries). Reworded to state the survey's actual finding (8 grid/1 chart/2 pivot across
    all 11) separately from the observation that today's 6 views happen to fall in the grid
    bucket.
  - `[low]` `[patch]` The "import direction is a strict line (`registry` → `widgets` →
    `render`)" docstring wording (in both `widgets.py` and `registry.py`) was ambiguous about
    whether the arrow meant import-statement direction or dependency/layering direction.
    Reworded both to say "layering order (bottom to top)" explicitly.
  - `[medium]` `[patch]` `test_widgets.py`'s byte-identical regression tests monkeypatched
    private, undocumented Bokeh internals (`bokeh.util.serialization._simple_id`,
    `bokeh.embed.util.make_globally_unique_id`/`make_globally_unique_css_safe_id`) to force
    deterministic output — fragile against a routine Bokeh version bump, and duplicated the
    same comparison via two call sites (`widget.static_renderer` vs. `render_rows`) covering
    only 1 of 6 views. Replaced with two independent, non-fragile tests: a dispatch-spy test
    proving `render_rows` calls `get_widget(view.widget).static_renderer(view, rows)` with
    exact args/return value (no Bokeh internals touched), and a structural-assertion test
    (declared columns present, matching `test_render.py`'s own established style) proving
    `get_widget("grid").static_renderer` produces a real, valid fragment. Full behavioral
    coverage across all 6 views remains from Story 14.1's unmodified `test_render.py`.
  - `[low]` `[patch]` `views/__init__.py`'s new re-exports (`Widget`, `WIDGETS`, `get_widget`)
    had no test importing them from the package root, so a typo/omission in `__init__.py`
    would go unnoticed. Added `test_views_package_reexports_widget_registry_symbols`.
  - `[low]` `[defer]` + `[low]` `[defer]` `get_widget`'s bare `KeyError` (extra-quoted message
    via `!r`, no domain-specific wrapper exception) mirrors `get_view`'s identical, already-
    shipped Story 14.1 pattern — fixing only the newer function would make the two nearly-
    identical lookup helpers inconsistent with each other. Filed `DW-FU-14-2` to revisit both
    together if this is ever addressed.
  - Rejected as noise/verified-false/out-of-scope (not re-listed individually): the claim that
    no test validates `view.widget` membership in `WIDGETS` at construction/CI time (false —
    `test_render.py`'s existing `test_no_registered_view_fragment_opens_a_websocket` already
    parametrizes over all 6 `STATIC_VIEWS` and calls `render_rows`, i.e. `get_widget`, for
    every one; a typo would already fail CI); `WIDGETS` being an unprotected mutable dict with
    no thread-safety story (matches this package's own established `a2a/schema.py`
    `_KIND_TO_MODEL` precedent, and making it read-only would break the EXTENSIBILITY test's
    required `monkeypatch.setitem` mechanism); no public `register_widget()` function
    (speculative abstraction beyond CAP-3's actual AC — dict-literal registration matches
    repo convention); the extensibility promise being "unproven" for hypothetical future
    chart/pivot widget needs on `View` (speculative, explicitly out of this story's scope,
    and backward-compatible dataclass field addition wouldn't violate the "zero edits to
    existing view definitions" contract anyway); `websocket_renderer`'s signature being
    unconstrained (deliberately deferred to Story 14.3, per spec's own Never clause); the
    docstring citing sibling-module precedents not present in this diff (verified real and
    accurate in the live codebase — `a2a/schema.py:187`, `orchestration/definitions.py:414`
    — and matches Story 14.1's own precedent-citing docstring style); `get_widget` assuming
    `name` is hashable (unreachable in practice — `view.widget` is always a `str` by
    construction, and `get_widget`'s only caller is the internal `render.py` seam, not a
    public input boundary); `widget: str` having no default being "breaking" for other
    `View(...)` call sites (verified false — `grep`-confirmed all 6 `View(` constructions
    repo-wide live in `registry.py` and were all updated in this same diff; no other site
    exists); and removing `render.py`'s now-unused bokeh imports possibly breaking an
    external importer (no known consumer exists — `render.py`'s prior re-exports of those
    symbols were never a documented public surface, and the reviewer flagged this at low
    confidence itself).

### 2026-08-14 — Review pass (fresh review, post-recovery)
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 0
- reject: 13: (high 0, medium 0, low 13)
- addressed_findings:
  - `[low]` `[patch]` `test_get_widget_extensibility_via_monkeypatch_needs_no_registry_edit`
    asserted `len(STATIC_VIEWS) == 6`, a magic number that would need updating the instant a
    7th view is added even though nothing about extensibility regressed. Replaced with an
    identity snapshot (`views_before = STATIC_VIEWS`, then `assert STATIC_VIEWS is
    views_before`), which proves the tuple was never mutated without hardcoding its length.
  - `[low]` `[patch]` The dispatch test
    (`test_render_rows_dispatches_through_the_registry_with_exact_args_and_return_value`)
    registered its spy under the key `"grid"`, the same name every seeded view already
    declares, so it couldn't distinguish `render_rows` reading `view.widget` dynamically
    from a hypothetical hardcoded `"grid"` literal. Registered the spy under a distinct key
    (`"spy-only"`) and built the test's `view` via `dataclasses.replace(get_view(...),
    widget="spy-only")`, so the test now actually proves the dispatch key comes from
    `view.widget`.
  - Rejected as noise/verified-false/already-covered/out-of-scope (not re-listed
    individually): `Widget.websocket_renderer` being speculative dead code (false -- the
    intent-contract's Boundaries & Constraints explicitly mandates this field, defaulted to
    `None`, as the Story 14.3 slot; it is spec-required forward-compatibility, not
    speculative chart/pivot building, which is separately and explicitly forbidden); no test
    verifying every `STATIC_VIEWS` entry resolves through `get_widget` without raising
    (false -- `test_render.py::test_no_registered_view_fragment_opens_a_websocket` is
    parametrized over all 6 `STATIC_VIEWS` and calls `render_rows`, i.e.
    `get_widget(view.widget)`, for every one; confirmed by reading the live test); `WIDGETS`
    permitting a dict-key/`Widget.name` desync with no `register_widget()` guard (same
    already-accepted tradeoff as the prior pass's "no public `register_widget()` function ...
    dict-literal registration matches repo convention" rejection); `get_widget`'s bare
    `KeyError` not naming the offending `View`/view-name (same underlying gap as the
    already-filed `DW-FU-14-2`, which tracks `get_widget`'s bare-`KeyError` ergonomics for a
    combined future fix, not a new, distinct finding); `widget: str` having no default being
    a positional-argument-misbinding risk (re-verified false -- `grep`-confirmed all 6
    `View(` constructions live only in `registry.py`, all keyword-argument calls, matching
    the prior pass's identical grep-based rejection); the EXTENSIBILITY test being "close to
    vacuous" (it implements the spec's own EXTENSIBILITY I/O-matrix row verbatim --
    `monkeypatch.setitem(WIDGETS, ...)` leaving `STATIC_VIEWS` unmodified is the acceptance
    criterion, not a design flaw); the seed-set survey's "8 grid/1 chart/2 pivot across 11
    CLIs" claim being uncited/unverifiable (documented in this spec's own Design Notes
    section, naming every CLI per bucket, and matches this codebase's established
    precedent-citing docstring style already validated in the prior pass); `get_widget`'s
    error-message claim to mirror `get_view`'s error style being unverifiable from the diff
    alone (re-verified true by reading the live `get_view`: both raise `KeyError` formatted
    as `f"unknown {kind} {name!r}; known {kind}s: {...}"`, an exact style match); mixing
    `typing.Callable`/`typing.Any` with PEP 604 `X | None` union syntax in one field
    declaration (non-issue -- both are required regardless of Python version under `from
    __future__ import annotations`, and this mix is ubiquitous, unrelated to any documented
    repo convention); `Widget` holding raw callables with no runtime arity/signature check
    (speculative validation beyond CAP-3's scope -- no dataclass in this codebase validates
    callable signatures at registration); the seed dict duplicating identity in both its key
    and `Widget.name` (same accepted tradeoff as the no-`register_widget()` rejection above);
    the `atlas_db_path`/`_rows_for` fixture/helper not being shown in the diff (verified
    false -- `_rows_for` is defined directly in `test_widgets.py` in this same diff, and
    `atlas_db_path` is the pre-existing, unmodified `conftest.py` fixture Story 14.1 already
    shipped, named explicitly in this spec's own Code Map as "reused unmodified"); and
    `get_widget` assuming `name` is hashable, so a non-hashable input would raise `TypeError`
    instead of the documented `KeyError` (same already-rejected reachability argument from
    the prior pass -- `view.widget` is always a `str` by construction and `get_widget`'s only
    caller is the internal `render.py` seam, not a public input boundary).

## Design Notes

**Survey informing the seed set (2026-08-14):** of the 11 atlas query CLIs, 8 return a flat
scalar-column grid (`staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`,
`cve-watcher`, `release-cadence`, `adoption-stage`, `find-alternative`); 1
(`version-downloads`, ordered by `upload_unix`/`total_downloads` per package version) is a
per-version download trend suited to a chart; 2 (`detail-cf-atlas`'s single-entity record with
nested build-matrix/vdb sub-sections, `scan-project`'s multi-section grouped dependency
report) are hierarchical/pivot-shaped. Only `"grid"` is seeded because every one of today's 6
`STATIC_VIEWS` entries is grid-shaped — "chart"/"pivot" are each a future one-entry-plus-one-
renderer addition when a story actually introduces a view needing one, not built here
speculatively.

**Import direction avoids a cycle:** `widgets.py` imports `View` from `registry.py` only.
`render.py` imports `get_widget` from `widgets.py`. That keeps the dependency graph a strict
line (`registry` → `widgets` → `render`), so `View` construction never validates `widget`
against `WIDGETS` (that would reverse the line into a cycle); `get_widget()` raises `KeyError`
at render time instead — an acceptable tradeoff mirroring this repo's existing "name-only,
validated at dispatch" convention (`a2a/schema.py`'s `_KIND_TO_MODEL`,
`orchestration/definitions.py`'s profile lookup).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary.** Extracted Story 14.1's hardcoded `render_rows` Bokeh-rendering body into a
pluggable widget-type registry (Story 14.2, Epic 14 CAP-3): a new `pyforge.atlas.views.widgets`
module holds a `Widget` dataclass (`name`, `static_renderer`, and a `websocket_renderer` slot
left `None` for Story 14.3) plus a `WIDGETS` name→`Widget` dict and `get_widget()` lookup.
`View` gained an explicit `widget: str` field; all 6 `STATIC_VIEWS` entries now declare
`widget="grid"`. `render_rows` is now a one-line dispatch (`get_widget(view.widget)
.static_renderer(view, rows)`) instead of constructing a Bokeh model directly. The registry's
sole seed entry (`"grid"`) is backed by a documented survey of all 11 mirrored CLIs' query
shapes (8 grid, 1 chart, 2 pivot) — no chart/pivot renderer was built, since no current view
needs one.

**Files changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/widgets.py` -- NEW: `Widget`
  dataclass, `WIDGETS` registry, `get_widget()`, the `"grid"` renderer (moved from `render.py`)
- `.../views/registry.py` -- added `widget: str` field to `View`; `widget="grid"` on all 6
  `STATIC_VIEWS` entries; docstring clarified (review patch)
- `.../views/render.py` -- `render_rows` now dispatches through the registry; dropped its
  now-unused bokeh imports
- `.../views/__init__.py` -- exports `Widget`, `WIDGETS`, `get_widget`
- `.../tests/views/test_widgets.py` -- NEW: dispatch-spy test, structural-fragment test,
  UNKNOWN_WIDGET, EXTENSIBILITY, WEBSOCKET_UNSET, and package-re-export tests
- `_bmad-output/implementation-artifacts/deferred-work.md` -- appended `DW-FU-14-2`

**Review findings breakdown (pass 1):** 17 total findings from 2 independent reviewers (Blind
Hunter + Edge Case Hunter, no shared context) after dedup — 6 patch (1 medium, 5 low; all
applied), 0 bad_spec, 0 intent_gap, 2 defer (both low; filed as one combined `DW-FU-14-2`
entry), 9 reject (claims verified false against the live codebase/test suite, matched
established repo precedent, or were speculative/out of this story's scope).

**Review findings breakdown (pass 2, fresh review post-recovery — see Residual risks below):**
15 total findings from 2 fresh independent reviewers after dedup — 2 patch (both low; both
`test_widgets.py` test-quality fixes, applied), 0 bad_spec, 0 intent_gap, 0 defer, 13 reject
(all re-verified false, already-accepted design tradeoffs from pass 1, or substantively
duplicates of the already-filed `DW-FU-14-2`). Full detail for both passes in
`## Review Triage Log` above.

**Verification performed:**
- `pixi run -e pyforge-atlas kedro-test` -- 1113 passed, 19 skipped, 0 failed (re-run after
  pass 1 patches, and again after pass 2 patches)
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/singularity -q`
  -- 3 passed (F1 gate still green; `grep` confirmed no literal `sqlite3` import under
  `src/pyforge/atlas/`)
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/views -q`
  -- 40 passed both before and after pass 2's patches (Story 14.1's
  `test_render.py`/`conftest.py` byte-for-byte untouched, confirmed via `git diff --stat`)

**Residual risks:** none blocking. Deferred: `get_widget`'s bare `KeyError` (message-quoting +
missing domain-wrapper type) mirrors `get_view`'s identical Story 14.1 pattern — tracked as
`DW-FU-14-2` for a combined future fix rather than an inconsistent one-sided patch now.

**Process note (this pass):** on entry, this run's branch (`bmad-loop/20260814-202328-e168/
14-2-pluggable-widget-registry`) was found reset to a commit *before* even Story 14.1's merge
— the known bmad-loop stuck-orchestrator-baseline bug (orchestrator bookkeeping drifted while
this worktree's dev session was still running, silently rewinding the branch after pass 1's
commit landed). The spec file survived (it lives outside git, behind the shared
`implementation-artifacts` symlink), so `bmad-dev-auto` routed a `status: done` spec straight
to a fresh review pass per its normal routing rules — but the working tree itself had lost all
of Story 14.1 and 14.2's code. Recovered losslessly via a fast-forward merge from the
orchestrator's own `attempt-preserve/20260814-202328-e168-01027a26` safety-net branch (`git
merge --ff-only`, confirmed a clean fast-forward with `git merge-base --is-ancestor` before
merging) before constructing this pass's diff. No data was lost; both commits (Story 14.1's
merge and Story 14.2's implementation) are intact on the branch as of `final_revision` below.
