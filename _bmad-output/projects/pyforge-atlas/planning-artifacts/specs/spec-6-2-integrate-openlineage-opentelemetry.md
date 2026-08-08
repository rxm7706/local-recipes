---
title: 'Story E2 (6.2): Integrate OpenLineage + OpenTelemetry'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #91 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/6-2-e2.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story E2 (6.2): Integrate OpenLineage + OpenTelemetry

As the operator,
I want Kedro nodes, Dagster runs, and DuckDB queries instrumented with OpenLineage and OTel,
So that lineage, per-node metrics, and end-to-end traces are observable down to specific API calls.

**Acceptance Criteria:** (spec § 9 Story E2, binding)

**Given** the compiled DAG and hooks layer
**When** instrumentation lands
**Then** lineage + per-node metrics (rows, latency, cache hits) are captured via OpenLineage
**And** end-to-end distributed traces are visible via OTel down to specific API calls
**And** emitted-event/span fixtures are this story's gate assets (AD-20 — fixture-verified, since Wave E has no new named gate).

- **FRs:** FR-12.
- **Invariants:** AD-20, AD-6 (hooks declared in run config — every entry point inherits them, AD-23).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** existing gates + emitted-event/span fixtures in `kedro-test`.
- **Depends on:** C1 (Dagster runs to instrument).

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] lineage + per-node metrics (rows, latency, cache hits) are captured via OpenLineage
- [x] end-to-end distributed traces are visible via OTel down to specific API calls
- [x] emitted-event/span fixtures are this story's gate assets (AD-20 — fixture-verified, since Wave E has no new named gate).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-12.
- **Invariants:** AD-20, AD-6 (hooks declared in run config — every entry point inherits them, AD-23).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** existing gates + emitted-event/span fixtures in `kedro-test`.
- **Depends on:** C1 (Dagster runs to instrument).

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #91). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**One module owns both vendors.** The observability hooks module is the *only* module in
`pyforge.atlas` permitted to import `openlineage` or `opentelemetry` (AD-1). Instrumentation
is glue, and glue stays containable.

**Two complementary shapes, deliberately not merged.**
- **OpenLineage** — each node run emits a `RunEvent` START (before) and a completion event
  (after), carrying **lineage** as `InputDataset`/`OutputDataset` *by catalog name* plus
  per-node metrics. Lineage is expressed in the catalog's vocabulary, so it lines up with
  the dataset contract rather than with file paths.
- **OpenTelemetry** — a three-level span tree: the pipeline run is a parent span, each node
  run a child, and **each dataset read/write a grandchild span named after the dataset**.
  That deepest level is what makes the kernel's "every run is traceable *to the API call*"
  claim literally true — the dataset span is where the IO happens.

**Custom facet for the FR-12 numbers.** `AtlasNodeMetricsRunFacet` carries rows, latency, and
cache hits on the OpenLineage run, rather than smuggling them into a generic field.

**Nested pipelines were designed for.** `_PipelineFrame` is a **stack frame**, not a
singleton, and `_NodeState` carries per-node state between the before/after (and error)
hooks. A nested pipeline run therefore nests correctly instead of corrupting the parent's
span.

**The default path emits nowhere — provably.** With no exporter configured, spans are
created and dropped and *nothing is set globally*; with `openlineage_client=None`, emission
is skipped entirely. There is no network access at import or at run. This is what lets a
heavyweight observability stack ship inside an offline-by-default package.

**The captured fixtures are the gate (AD-20).** `tests/observability/` injects an in-memory
OTel span exporter and a capturing OpenLineage client (`make_capturing_client`, whose
transport appends events to a list) and asserts the emitted event and span *shape*. Live
collector wiring — a real OTLP endpoint or OpenLineage backend URL — is env-driven and
deferred; see the DW ledger section below.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-E2]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-E2]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#91** — story(E2): OpenLineage + OpenTelemetry instrumentation via the hook layer (FR-12) |
| Merged | 2026-07-18 |
| Diff | 5 files, +837 / -1 |
| Test files touched | 3 |

**Commits**

- `153a5ad` story(E2): OpenLineage + OpenTelemetry instrumentation via the hook l…

**File list** *(exact, from the merged diff)*

```
  465 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/observability.py
  332 +     0 -  src/shared/packages/pyforge-atlas/tests/observability/test_observability_fixtures.py
   31 +     0 -  src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py
    9 +     1 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/settings.py
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/observability/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `153a5ad`** — story(E2): OpenLineage + OpenTelemetry instrumentation via the hook layer (FR-12)
  - Closes Wave E. Adds observability.py (AtlasObservabilityHooks) — registered in
  - settings HOOKS beside ProjectHooks, so EVERY entry point inherits it (AD-6/
  - AD-23: a `kedro run` and the C1 Dagster plane, which runs nodes through
  - KedroSession, both get instrumented from ONE declaration). Nodes stay pure
  - DataFrame->DataFrame — all instrumentation is in the hook layer.
  - - OpenLineage: each node run emits a RunEvent START + terminal (COMPLETE/FAIL)
  - with input/output LINEAGE and the FR-12 metric facets — standard
  - outputStatistics.rowCount per output + a custom atlasNodeMetrics run facet
  - carrying rows / latency_ms / cache_hits.
  - - OpenTelemetry: a parent pipeline span + nested per-node child spans + per-input
  - dataset-IO ("API call") child spans; one trace per run.
  - - Offline + injectable (AD-20): both backends default to no-op (no span
  - processor / OL skipped) so the in-container default emits nowhere with no
  - network; the gate injects an InMemorySpanExporter + a capturing OL client and
  - asserts the emitted events/spans (the fixture-verified gate, since Wave E has
  - no new named gate). Live collector/OTLP wiring is env-driven + DEFERRED (DW-E2-1).
  - - AD-6/AD-23 import-ban: only observability.py imports openlineage/opentelemetry
  - (AST guard extended in tests/catalog/test_no_inline_io.py).
  - Reviewer fixes applied (both in-loop reviewers):
  - - rowCount now gates on a 2-D .shape (was bare len(), which reported a bogus
  - count for a dict/list/str output — the atlas has dict-returning nodes).
  - - a node still open when the pipeline errors now gets an OL FAIL terminal (was a
  - dangling START with no COMPLETE/FAIL for OL consumers).
  - - __deepcopy__ shares the injected OTel provider AND OL client by reference, so
  - the C1 translator's per-run hook deepcopy can't silently drop the provider
  - while keeping the OL client (an OTel-drops/OL-survives asymmetry that would
  - make the Dagster plane emit events but no spans once a real exporter lands).
  - Dagster-plane inheritance verification + the facet provenance stamp are recorded
  - DW-E2-2/-3. +19 tests. 620 passed.

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#91`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #91: story(E2): OpenLineage + OpenTelemetry instrumentation via the hook layer (FR-12)

## Deferred Work (DW ledger)

### DW-E2-1 — the live OTel collector + OpenLineage backend wiring (env-driven) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story E2, FR-12)
  summary: E2 shipped the load-bearing, buildable-now half of the observability surface — the `observability.py` module as the SINGLE instrumentation seam (AD-6/AD-23: `openlineage`/`opentelemetry` confined there by `test_observability_libs_only_in_observability`), a Kedro Hooks impl (`AtlasObservabilityHooks`) declared ONCE in `settings.HOOKS` so EVERY entry point inherits it (a `kedro run` natively, a Dagster run via C1's `KedroProjectTranslator` → `KedroSession.run`), emitting per-node OpenLineage RunEvents (START/COMPLETE/FAIL) with input/output dataset lineage + the rows/latency/cache-hit metric facets (`OutputStatisticsOutputDatasetFacet.rowCount` + the custom `AtlasNodeMetricsRunFacet`), and an OTel span tree (pipeline → node → per-dataset read/write "API-call" spans). Nodes stay pure DataFrame→DataFrame (AD-2/AD-6) — all instrumentation is in the hook layer. Both backends are INJECTABLE and default to no-op/offline: `tracer_provider=None` → a local `TracerProvider` with no exporter (spans dropped, no network, never set globally); `openlineage_client=None` → OL emission skipped. The ACTUAL live wiring — a real OTLP endpoint (`OTEL_EXPORTER_OTLP_ENDPOINT` + a `BatchSpanProcessor`/`OTLPSpanExporter`) and a real OpenLineage backend URL/transport (`OPENLINEAGE_URL` → an `HttpTransport`) resolved from env at run bring-up — is DEFERRED: no collector/backend comes up offline in-container, and emitting to a fake endpoint would be dishonest (mirrors the DW-C1-1 live-Dagster-schedule and DW-D3-1 live-LLM-backend attended bring-ups). Because the emitters are already injectable, the follow-up is a substrate swap (construct an env-driven provider/client in `settings.py` or a factory and inject it), not an instrumentation change. Do NOT wire a live endpoint into the default path or weaken the offline fixture gate to require a backend.
  evidence: `tests/observability/test_observability_fixtures.py` drives a real two-node SequentialRunner pipeline (plus the pipeline-level hooks, as KedroSession fires them) with an in-memory OTel span exporter + a capturing OpenLineage client (`make_capturing_client`) and asserts the emitted event/span SHAPE — START+COMPLETE per node, input/output lineage edges, shared runId, the rowCount + rows/latency(`>=0`)/cache-hit facets, and the nested pipeline→node→dataset span tree in one trace — these captured fixtures ARE the gate (AD-20). Edge cases proven: `on_node_error` emits FAIL + closes the span (no leak, ERROR status), no-input/output nodes, empty-frame rows=0, non-DataFrame output degrades (rowCount omitted, no crash), the None-captor default path runs the full lifecycle without emitting/crashing, nested pipeline frames close without leaking, and no now()/uuid leaks into any asserted field. `test_no_inline_io.py::test_observability_libs_only_in_observability` pins the single-seam containment. `AtlasObservabilityHooks.__getstate__` drops the un-deepcopyable OTel tracer so C1's translator can deep-copy the settings HOOKS (the copy rebuilds a lazy default tracer). No socket is bound and no exporter reaches a network in any test (offline).

### DW-E2-2 — Dagster-plane observability inheritance verification + span-key footgun (bring-up)
- source_spec: `e2-integrate-openlineage-opentelemetry.md`
  summary: The AD-23 claim "the Dagster plane inherits the settings-registered observability hook, nested" is verified for the KEDRO plane (fixture gate) but NOT yet for the Dagster plane — the C1 live bring-up (DW-C1-1) is where a real kedro-dagster run confirms parent→node→dataset span nesting + cache_hits survive the translator's per-run hook deepcopy. The deepcopy asymmetry (a dropped OTel provider) is FIXED in E2 (`__deepcopy__` shares _provider + _ol by reference; regression test `test_deepcopy_preserves_injected_backends_no_otel_ol_asymmetry`), so a future injected exporter reaches both planes — but the end-to-end Dagster-plane assertion still rides on the deferred daemon bring-up. Also latent (Reviewer-B finding 2): `_nodes` is keyed by `node.name`; two in-flight runs of the same node name would overwrite/leak state — impossible under Kedro's unique-names-per-pipeline + DAG-ordered runners today, but a `(node.name, run_id)` key would remove the footgun if a future runner violated that. Not reachable now.
  evidence: E2 gate drives a SequentialRunner + manual before/after_pipeline_run; `dagster definitions validate` passes but does not RUN nodes. Thread-safety: `_nodes`/`produced` are unlocked — correct under SequentialRunner + C1 in_process executor (DAG-ordered), a ThreadRunner/ParallelRunner would need locking.

### DW-E2-3 — AtlasNodeMetricsRunFacet provenance stamp (cosmetic)
- source_spec: `e2-integrate-openlineage-opentelemetry.md`
  summary: The custom `atlasNodeMetrics` run facet is emitted without an explicit `producer=PRODUCER`, so its `_producer` defaults to the OpenLineage library URI rather than the project PRODUCER every other emitted facet carries (Reviewer-A nice-to-have). Cosmetic — the metric VALUES (rows/latency_ms/cache_hits) are correct; only the facet's provenance-stamp URI differs. Left untouched to avoid perturbing the attrs RunFacet inheritance; revisit if lineage-provenance consistency is ever asserted.
  evidence: `AtlasNodeMetricsRunFacet` construction on the COMPLETE event does not pass producer; the standard rowCount + errorMessage facets do.
