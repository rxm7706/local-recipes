---
title: 'Stamp advisory data with its build provenance (AD-17)'
type: 'feature'
created: '2026-07-28'
status: ready-for-dev
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: '90c2792843be8a46c672f0f5ad4eaa24ead37a6c'
---

<intent-contract>

## Intent

**Problem:** The MCP `read_dataset` passthrough returns raw catalog values with no
freshness marker (AUD-ATLAS-043), and 7 of the 8 dashboard pages render no build stamp
at all — only `factory-status` does (AUD-ATLAS-044). AD-17 requires every advisory
surface to let its consumer tell fresh data from stale; today only pipeline triggers
and one dashboard page honor that.

**Approach:** Wrap `read_dataset`'s return in an envelope `{dataset, build_stamp,
value}` (a wall-clock ISO-8601 stamp resolved at call time, mirroring `run_pipeline`'s
existing `triggered_at` receipt in the same module). Thread `build_dashboard`'s
already-resolved `build_stamp` into `_legibility_card` so every page — not just
`factory-status` — carries it.

## Boundaries & Constraints

**Always:**
- The stamp is resolved at call/build time (never at import), matching the existing
  AD-17 convention (`_default_build_stamp` in `validation.py`, `build_dashboard`'s
  wall-clock default) — a real runtime value, never fabricated or cached across calls.
- `read_dataset`'s envelope adds exactly three keys: `dataset` (the requested name),
  `build_stamp` (ISO-8601 string), `value` (the existing coerced return, unchanged).
  No other tool body changes shape (AD-7: no metric logic enters tool bodies).
- An unknown dataset name still raises whatever `catalog.load` raises — the envelope
  wraps only the success path.
- `_legibility_card`'s existing content (title, CLI name, data-gap note) is preserved
  verbatim; the build stamp is an addition, never a replacement.
- Never launder freshness (AD-13): the stamp reflects when the response was built, not
  when the underlying dataset was last materialized (no such per-dataset timestamp
  exists in the catalog today — confirmed by investigation).

**Block If:** none identified — this is a mechanical envelope/threading change with a
precedent already established in three other places in the codebase.

**Never:**
- Do not add a per-dataset materialization-timestamp lookup (Kedro catalog metadata,
  a run manifest, MLflow-style tracking) — none exists today, and inventing one is out
  of scope for this story. The wall-clock-at-emit convention is the established AD-17
  contract.
- Do not touch `_factory_page` / `factory-status`'s existing stamp Card — it already
  satisfies AD-17 and is out of scope.
- Do not change `run_pipeline`'s return shape.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Known dataset, JSON-native value | `read_dataset("demo_ds")` where the catalog holds a dict | `{"dataset": "demo_ds", "build_stamp": "<ISO-8601>", "value": <dict>}` | No error expected |
| Known dataset, DataFrame-backed | `read_dataset("df_ds")` | `value` is the existing coerced `list[row-dict]`; `dataset`/`build_stamp` present | No error expected |
| Unknown dataset name | `read_dataset("no_such_ds")` | Raises (unchanged) — no envelope constructed | Propagates `catalog.load`'s exception |
| Dashboard grounded-data page (e.g. `feedstock-health`) | `build_dashboard(build_stamp=STAMP, ...)` | That page's legibility Card text contains `STAMP` and `AD-17` | No error expected |
| Dashboard no-bsl-shell page (e.g. `behind-upstream`) | same | Card still states the data gap AND contains `STAMP`/`AD-17` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` -- `read_dataset` (lines 72-106) wraps its return in the `{dataset, build_stamp, value}` envelope; module already imports `datetime` and uses `datetime.datetime.now(datetime.UTC).isoformat()` for `run_pipeline`'s `triggered_at` (line 67) — reuse the same call.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` -- `read_atlas_dataset` (line 65-67) docstring says "a thin catalog.load passthrough"; update the one line to note it returns the stamped envelope. No signature change (untyped return).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` -- `_legibility_card` (line 111), `_data_page` (line 121), `_shell_page` (line 133) gain a `build_stamp: str` parameter; `build_dashboard` (line 175) already resolves `build_stamp` once at the top (line 191-192) — thread it into the three `_data_page(...)` and two `_shell_page(...)` call sites (lines 224-247).
- `src/shared/packages/pyforge-atlas/tests/mcp/test_read_surface.py` -- update the 3 existing assertions that treat `read_dataset(...)`'s return as the raw value directly; add one new envelope-shape test.
- `src/shared/packages/pyforge-atlas/tests/mcp/test_kedro_mcp_absent.py` -- line 102 (`assert tools.read_dataset("demo_ds") is sentinel`) needs the same unwrap.
- `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py` -- add a test asserting every non-factory page's legibility Card carries the injected `STAMP` + `"AD-17"`, mirroring the existing `test_factory_status_carries_build_timestamp_ad17` pattern (line ~211).

## Tasks & Acceptance

**Execution:**
- [ ] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` -- change `read_dataset` to compute `stamp = datetime.datetime.now(datetime.UTC).isoformat()` once, then `return {"dataset": name, "build_stamp": stamp, "value": <existing coercion result>}` -- closes AUD-ATLAS-043 / AD-17 for the MCP read surface.
- [ ] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` -- update `read_atlas_dataset`'s docstring to say it returns a `{dataset, build_stamp, value}` envelope -- keeps the doc truthful after the shape change.
- [ ] `src/shared/packages/pyforge-atlas/tests/mcp/test_read_surface.py` -- rewrite `test_read_dataset_is_a_catalog_load_passthrough` to assert `result["value"] is SENTINEL` and `result["dataset"] == "demo_ds"`; update the DataFrame/Series/ndarray/set coercion tests to read `tools.read_dataset(ds)["value"]`; add `test_read_dataset_envelope_carries_build_stamp` asserting `isinstance(result["build_stamp"], str)` and `"T" in result["build_stamp"]` (mirroring `test_run_pipeline_dispatches_through_kedro_session_run`'s `triggered_at` check) -- proves the envelope without over-pinning the exact timestamp.
- [ ] `src/shared/packages/pyforge-atlas/tests/mcp/test_kedro_mcp_absent.py` -- change line 102 to `assert tools.read_dataset("demo_ds")["value"] is sentinel` -- keeps this kedro-mcp-absent smoke test passing under the new shape.
- [ ] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` -- add `build_stamp: str` param to `_legibility_card`, append a line `f"**Build timestamp (AD-17):** \`{build_stamp}\`"` to its markdown after the existing content; add the same param to `_data_page` and `_shell_page`, passing it through to `_legibility_card`; update the 5 call sites inside `build_dashboard` (3× `_data_page`, 2× `_shell_page`) to pass `build_stamp=build_stamp` -- closes AUD-ATLAS-044 / AD-17 for the 7 non-factory pages.
- [ ] `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py` -- add `test_non_factory_pages_carry_build_timestamp_ad17(dashboard)` iterating `dashboard.pages` excluding `factory-status`, asserting each page's `vm.Card` component's `.text` contains `STAMP` and `"AD-17"` -- proves the AC's "dashboard pages carry the same stamp" for the full page set, not just one page.

**Acceptance Criteria:**
- Given the MCP `read_dataset` surface, when a dataset is read, then the response is a dict with `dataset`, `build_stamp`, and `value` keys, and `value` equals exactly what the surface returned before this change.
- Given `read_dataset` is called with an unknown name, when `catalog.load` raises, then the exception propagates unchanged (no envelope swallows it).
- Given the dashboard is built with an injected `build_stamp`, when any of the 8 pages render, then every page's legibility/stamp Card text contains that `build_stamp` and the literal `AD-17`.
- Given the existing `factory-status` page, when the dashboard builds, then its stamp Card is unchanged (still carries `"Build timestamp (AD-17):"` phrasing, still row 0 of the frame).

## Spec Change Log

## Review Triage Log

### 2026-07-28 — Review pass

- intent_gap: 1: (high 1, medium 0, low 0)
- bad_spec: 1: (high 0, medium 1, low 0)
- patch: 4: (high 0, medium 0, low 4)
- defer: 2: (high 0, medium 0, low 2)
- reject: 0
- addressed_findings:
  - none

**intent_gap finding (blocking):** `read_dataset`'s `build_stamp` is computed as
`datetime.datetime.now(datetime.UTC).isoformat()` at the moment of every call — wall-clock-*now*,
not the underlying dataset's actual build/materialization time. This can never distinguish fresh
data from stale (every read of a month-old dataset reports "now"), which directly contradicts:
(1) the AC's own stated purpose ("so that I can tell fresh data from stale"); (2) the epic's
explicit Invariant for this story, AD-13 "republication never launders freshness"; (3) `SPEC.md`'s
canonical AD-17 definition ("payloads feeding authoring decisions carry **their build timestamp**",
i.e. the pipeline's build time, not a read-receipt time); and (4) the codebase's own established
precedent (Wave-H's `CompileCrew` forwards *source* staleness markers into republished output
rather than fabricating a fresh timestamp at republish time). The flaw is not an implementation
slip — it is specified directly in the `<intent-contract>`'s Approach ("a wall-clock ISO-8601 stamp
resolved at call time"), Always ("the stamp reflects when the response was built, not when the
underlying dataset was last materialized"), and Never ("do not add a per-dataset
materialization-timestamp lookup... inventing one is out of scope") sections. A correct approach
needs either a genuine per-dataset freshness source (contradicting the current Never boundary) or
a redefinition of what this field promises — both are approach-level decisions, not one this
unattended pass may make unilaterally.

Related, non-blocking findings surfaced by the same review pass (recorded for the resumed pass,
not acted on this pass per the intent_gap cascade):
- `[medium]` `[bad_spec]` The envelope's breaking return-type change (`Any` → `dict`) has no
  `schema_version` marker (contrast `a2a/schema.py`) and no migration signal for existing
  callers; `planning-artifacts/specs/spec-b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools.md`
  still documents the old bare-passthrough contract and would go stale.
- `[low]` `[patch]` `tools.py`'s module docstring ("exactly ONE of the two allowed shapes") was not
  updated to acknowledge the new envelope-assembly logic.
- `[low]` `[patch]` The stamp was computed after DataFrame/Series/ndarray/set coercion rather than
  immediately after `catalog.load()`, widening the gap between "read" and "stamped" even under the
  wall-clock design.
- `[low]` `[patch]` `test_non_factory_pages_carry_build_timestamp_ad17` located each page's Card via
  `next(...)` with no default — a future Card-less page would raise an opaque `StopIteration`.
- `[low]` `[patch]` `test_kedro_mcp_absent`'s updated assertion checks only the envelope's `value`
  key, dropping coverage that `dataset`/`build_stamp` are also present in the kedro-mcp-absent path.
- `[low]` `[defer]` (pre-existing, extended by this story) `_legibility_card`/`_factory_page`
  interpolate `build_stamp` raw into a markdown backtick span with no escaping; a value containing
  a backtick/newline would corrupt the rendered Card. Low risk today (always internally generated),
  but the pattern was propagated to 7 more call sites by this story's would-be change.
- `[low]` `[defer]` (pre-existing, extended by this story) The dashboard's `build_stamp` is frozen
  at dashboard-object-build time while `AgGrid` data reloads lazily per render — already true for
  `factory-status`; this story's design would have spread the same staleness-of-the-stamp-itself
  quirk to 7 more pages.

All code changes for this pass were reverted to `baseline_revision` (clean diff against
`90c2792843be8a46c672f0f5ad4eaa24ead37a6c`). No files outside `_bmad-output/implementation-artifacts/`
remain modified.

## Design Notes

The envelope key order (`dataset`, `build_stamp`, `value`) matches the audit's original
proposed disposition verbatim (`{dataset, build_stamp, value}`) so the fix matches what
was reviewed, even though the reviewing PR was abandoned and never merged. The stamp
format intentionally follows `run_pipeline`'s existing `datetime.datetime.now(datetime.UTC).isoformat()`
(already in the same file) rather than `validation.py`'s `time.strftime(...)` pattern used
elsewhere — both are valid AD-17 wall-clock stamps, but matching the sibling function in
the same module avoids introducing a second timestamp convention into one file.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` -- expected: all tests pass, including the
  updated/new `tests/mcp/test_read_surface.py`, `tests/mcp/test_kedro_mcp_absent.py`,
  and `tests/dashboard/test_dashboard_dryrun.py` cases (this is the epic's shared
  verify gate; must stay at 787+ passing with zero regressions from I3/10.4's fix).
- `pixi run -e pyforge-atlas kedro-catalog-check` -- expected: unaffected, still green
  (no catalog/IO changes in this story).

