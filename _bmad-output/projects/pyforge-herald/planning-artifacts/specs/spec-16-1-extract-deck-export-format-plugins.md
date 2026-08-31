---
title: Extract deck/export format plugins
type: feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
context:
  - src/shared/packages/pyforge-core/src/pyforge/core/hooks.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_pipeline.py
warnings: []
baseline_revision: e96b852227b36bb28cbc62cd44dd5071057081fe
review_loop_iteration: 0
followup_review_recommended: false
deferred: []
---

<intent-contract>

## Intent

**Problem:** Marp, PPTX, and `.dc.html` export live as in-tree backends. Adding a format would fork Herald instead of registering a plugin on the shared `pyforge.core.hooks` contract (FR-45, canopy AD-21).

**Approach:** Publish Herald's deck-export hook spec on that contract and register today's three exporters as the default plugins. Export success is a station result, never a PR quality-gate / Warden verdict.

## Acceptance Criteria

- Given today's exporters, when the hook spec lands, then Marp, PPTX, and `.dc.html` are the default plugins on `pyforge.core.hooks`.
- Given a new format plugin on the same spec, when it registers, then Herald's process is not forked (no parallel `pyforge.herald.hooks` group).
- Given a successful export, when a plugin would publish a PR quality-gate verdict, then that is forbidden (`SecondVerdictError`).

## Boundaries & Constraints

**Always:** Consume `pyforge.core.hooks` (`HookSpec`, `HookPlugin`, `PluginRegistry`, `publish_verdict`). Canonical group is `pyforge.core.hooks` only. Write under `_bmad-output/projects/pyforge-herald/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-herald`. Existing pull/seed/pptx-fill CLI behavior stays green.

**Block If:** A change would add a station-local plugin loader or `import pluggy`.

**Never:** Warden Epic 9 scanners; competing CI verdict; Lane 1 CMS; rewriting `scripts/deck_export.py`; steward 32.2; peer FR-45 extractions; `scripts/bmad-switch`; bmad-loop.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default plugins | Registry with the three shipped plugins | `invoke("around", {format}, spec_name=pyforge.herald.deck_export)` runs only the matching format; all three format ids are registered | Unknown format with no plugin → empty `exported` list, no error |
| Extra format | Fourth plugin registered on the same spec | `invoke` with that format runs it; no new entry-point group | Parallel group `pyforge.herald.hooks` is a conformance fail (core meta-test) |
| Second verdict | Plugin calls `publish_verdict` on a Warden-owned PR-gate spec | Raise `SecondVerdictError` | Owner-matched publish on Herald's export spec is allowed but is not a quality-gate |
| Export is not a gate | Successful around for `marp` | Context records export; no Warden verdict object published | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — **read-only** shared loader (`ENTRY_POINT_GROUP`, `HookSpec`, `PluginRegistry`, `SecondVerdictError`)
- `src/shared/packages/pyforge-herald/src/pyforge/herald/exporters.py` — **new** `DECK_EXPORT_HOOK_SPEC`, `MarpExportPlugin`, `PptxExportPlugin`, `DcHtmlExportPlugin`, `register_default_export_plugins`, `export_via_hooks`
- `src/shared/packages/pyforge-herald/pyproject.toml` — `[project.entry-points."pyforge.core.hooks"]` for the three defaults (not a parallel group)
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` — `PixiDeckExporter` / pull path **read-only unless** a one-line dispatch to `export_via_hooks` is needed; do not rewrite CAP-1..5
- `src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_pipeline.py` — **read-only** default PPTX backend
- `src/shared/packages/pyforge-herald/tests/test_export_plugins.py` — **new** I/O matrix coverage
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — **read-only**; must still pass (canonical group only)

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/exporters.py` — hook spec + three default plugins + dispatcher
- `src/shared/packages/pyforge-herald/pyproject.toml` — declare the three entry points on `pyforge.core.hooks`
- `src/shared/packages/pyforge-herald/tests/test_export_plugins.py` — cover the I/O matrix

**Acceptance Criteria:**
- Given today's exporters, when the hook spec lands, then they are the default plugins.
- Given a fourth format plugin, when it registers on the same spec, then export works without forking Herald.
- Given export success, when a plugin publishes a Warden PR-gate verdict, then `SecondVerdictError` is raised.

## Design Notes

Hook spec name `pyforge.herald.deck_export`, owner `herald`. Format ids: `marp`, `pptx`, `dc.html`.

`call("around", context)` runs the format only when `context["format"]` is missing/`*` or equals the plugin's `format_id`. Inject a callable `context["backends"][format_id]` to run a real exporter. Without an inject, around is record-only (no pixi / marp / Chrome). A non-callable backends value raises `PluginError` rather than falling through to an in-tree exporter.

`publish_verdict` on Herald's own spec is allowed for a station-local export result. Publishing onto a spec owned by `warden` is the competing quality-gate and must raise.

Do not add `[project.entry-points."pyforge.herald.hooks"]`.

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 0
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` default around is record-only; do not spawn `PixiDeckExporter` / `run_fill` from the plugin (avoids accidental pixi and pull-path recursion)
  - `[low]` `[patch]` non-callable `backends[format_id]` raises `PluginError` instead of falling through

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: Landed Herald deck-export plugins on `pyforge.core.hooks` (spec `pyforge.herald.deck_export`, owner `herald`). Marp, PPTX, and `.dc.html` are the default plugins. Export success is a station result, not a Warden PR-gate verdict.

Files changed:
- `src/shared/packages/pyforge-herald/src/pyforge/herald/exporters.py` — hook spec, three default plugins, `export_via_hooks`
- `src/shared/packages/pyforge-herald/pyproject.toml` — three entry points on `pyforge.core.hooks`
- `src/shared/packages/pyforge-herald/tests/test_export_plugins.py` — I/O matrix
- this spec

Review: 2 patches applied (1 medium, 1 low; follow-up score 4). Rejected live pull rewiring (epic AC is hook-spec + default plugins), swallowing around errors, loading every station entry point into the dispatcher, and parallel-group additions.

Verification: `pytest` of `test_export_plugins.py` + smoke + deck_pipeline + pptx_pipeline — 187 passed.

Residual: `PixiDeckExporter` on pull still shells `deck-export` directly; a later story can route that through `export_via_hooks` without a process fork.
