---
title: "36.3: The query-plane estate source has a producer"
type: 'feature'
created: '2026-11-11'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
story: '36.3'
spec: pyforge-atlas
flag:
  key: pyforge.atlas.estate_source_producer      # new; joins src/platform/config/flags.json only when this story is built
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: "no node writes `query_plane_estate_source`; `query_plane_cache` stays a named-run-only pipeline (CAP-64, Story 34.14) and a named run exits 1 at that input, as today"
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/conf/base/catalog.yml
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/query_plane_cache/pipeline.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `spec-pyforge-atlas` CAP-68 asks for a named atlas node that writes `query_plane_estate_source`. Steward
Story 34.2 declared that catalog entry (`conf/base/catalog.yml`, a Parquet file under
`${paths.data_root}/raw/query_plane_estate_source/`), and `query_plane_cache`'s `extract_estate_to_cache` reads it
(canopy FR-47 Mode B), but no node writes it. So `pyforge atlas run --pipelines query_plane_cache` exits 1 at that
input on a fresh data root, the estate cache builds only from a test fixture, and `pipeline_registry.py` keeps
`query_plane_cache` out of `__default__` (Story 34.14).

**Blocked.** Atlas never reads platform OLTP directly: the producer reads the platform tables through a steward export
over `pyforge.core.station_port`, and no steward Dream entry, capability or story owns that export
(`DW-steward-egm-2026-11-1`). The operator deferred this story on 2026-10-18 and kept it deferred on 2026-11-01 (EGM
finding ATL-D-R1); unblocking it is a cross-station decision. Under ruling 4 of the 2026-11-10 second addendum
(`docs/dreams/pyforge-unifying-strategy.md` § Realization log) CAP-68 is a capability never built that a live
`blocked` story carries, so its ledger mode is `B-only`, written by the capability ledger's owner.

**Approach (once unblocked):**
- The steward export decides the platform tables and their columns; this story adds one node under
  `pipelines/query_plane_cache/` that reads the export through its catalog entry and writes
  `query_plane_estate_source`, and the node's tests.
- The node runs only with `pyforge.atlas.estate_source_producer` on; the key joins `flags.json` and
  `flag-overlays.json` in this story, never before.
- `query_plane_cache` leaves `NAMED_RUN_ONLY_PIPELINES` in `pipeline_registry.py`, so a plain run reaches it.

Ledger key: `36-3-the-query-plane-estate-source-has-a-producer`.
Type / Effort / Deps: feature / M / none on this station; blocked on a steward export no story owns.

### Living CAP citations

- `spec-pyforge-atlas` CAP-68 (FR-76) — the capability this story realizes; it stays `(ready 2026-10-18)` while this
  story is `blocked`.
- `spec-pyforge-unifying-strategy:CAP-19` — the `query_plane_estate` cache the producer feeds (read, not changed).

## Acceptance Criteria

Each command runs from the repository root; read every verdict from its exit code.

- **AC1 — A plain run builds the estate cache from data.** With `pyforge.atlas.estate_source_producer` on, `pyforge
  atlas run --pipelines query_plane_cache` on a fresh data root exits 0 and writes a non-empty `query_plane_estate`
  built from the steward export's rows, never from a test fixture, an empty frame or the `sku`/`units` model in
  `semantic/models.py`; the estate semantic model answers its declared measures over it.
- **AC2 — Flag off holds today's behaviour.** With the key off no node writes `query_plane_estate_source`, and a named
  run exits 1 at that input exactly as before the story. One test runs the key in both states with
  `pyforge.testing_kit.flags.flag_states`.
- **AC3 — The seam.** No module under `src/pyforge/atlas` imports platform or Django code or reads a platform database:
  the producer reads the steward export through a catalog entry, and `pixi run --frozen -e pyforge-atlas
  kedro-catalog-check` exits 0 with the no-inline-IO scan green.
- **AC4 — The gates.** `pixi run --frozen -e pyforge-atlas kedro-test` and `kedro-catalog-check` exit 0, and
  `python scripts/flag_gate_check.py --spec <this spec>` exits 0 once the key is in the tree.

## Boundaries & Constraints

**Always:**
- Read the platform tables only through the steward export over `pyforge.core.station_port` (AD-1; canopy FR-47).
- Read the key only through `pyforge.core.flags`, spelled literally at the read site.

**Never:**
- Never read platform OLTP, a Django model or a database URL from atlas code.
- Never build the estate frame from a fixture, an empty frame or the `sku`/`units` toy model.
- Never start this story while it is `blocked`: the operator flips the ledger key once the steward export exists.

</intent-contract>

## Binding

- Parent: `spec-pyforge-atlas` CAP-68 (FR-76); canopy FR-47; AD-1.
- Epic: Epic 36 (Basilisk, the OpenTeams identity sources and the estate source), minted 2026-10-18.
- Ledger key: `36-3-the-query-plane-estate-source-has-a-producer` (`blocked`).
- Blocking condition: no steward story exports the platform tables through `pyforge.core.station_port`
  (`DW-steward-egm-2026-11-1`, steward's deferred-work ledger). The operator flips the key.
- Flag: `pyforge.atlas.estate_source_producer` (the block above; Epic 36's Flag line).
- Surface: decided with the steward export (a node under `pipelines/query_plane_cache/`, its catalog entry, tests,
  `pipeline_registry.py`); the export itself is a steward story.

## Verification

**Commands (once unblocked):**
- `pixi run --frozen -e pyforge-atlas kedro-test` — expected: exit 0.
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check` — expected: exit 0.

## Auto Run Result

Status: blocked (written 2026-11-11 by atlas Story 46.1; never dispatched while blocked).

## Spec Change Log

- 2026-11-11: written by atlas Story 46.1 (the cutover readiness audit at main `82a2b18828` found Story 36.3 with no
  story spec); minted `blocked`, with the flag block Epic 36 names for it. The key joins the flag tree when the story
  is built, not before (`flag_gate_check` judges key presence on `done` specs only).

## Review Triage Log

- (none yet)
