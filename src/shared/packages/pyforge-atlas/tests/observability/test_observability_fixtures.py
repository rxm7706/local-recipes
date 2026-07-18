"""Story E2 gate (FR-12, AD-20) — emitted OpenLineage-event / OTel-span fixtures.

Wave E has no NEW named gate, so these captured event/span fixtures ARE the gate
(AD-20 — fixture-verified). Because there is no live collector in-container, we run
a tiny real Kedro pipeline (SequentialRunner, so node/dataset hooks fire in the real
order) with:
  - an **in-memory OTel span exporter** wired to an injected tracer provider, and
  - a **capturing OpenLineage client** (``make_capturing_client``),
then assert the captured events/spans have the right SHAPE — node names, input/output
lineage, the rows/latency/cache-hit facets, and the parent→node→dataset span tree.

Latency is real wall-clock, so we assert PRESENCE/shape (``>= 0``), never an exact
number (determinism); uuid runIds / ISO eventTimes are likewise never value-asserted.

Verified in ``kedro-test`` (this package is collected there).
"""

from __future__ import annotations

import attr
import pandas as pd
import pytest
from kedro.framework.hooks.manager import _create_hook_manager, _register_hooks
from kedro.io import DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner
from openlineage.client.event_v2 import RunState
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from pyforge.atlas.observability import (
    AtlasNodeMetricsRunFacet,
    AtlasObservabilityHooks,
    make_capturing_client,
)


# --------------------------------------------------------------------------- #
# Harness: a real two-node pipeline driven with the hook registered, plus the
# pipeline-level hooks invoked around the run exactly as KedroSession would.
# --------------------------------------------------------------------------- #
def _double(a: pd.DataFrame) -> pd.DataFrame:
    return a.assign(x=a["a"] * 2)


def _tag(mid: pd.DataFrame) -> pd.DataFrame:
    return mid.assign(y="z")


def _build_pipeline() -> Pipeline:
    return Pipeline(
        [
            node(_double, inputs="raw_in", outputs="mid", name="double_it"),
            node(_tag, inputs="mid", outputs="final_out", name="tag_it"),
        ]
    )


@pytest.fixture()
def captured():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    client, events = make_capturing_client()
    hooks = AtlasObservabilityHooks(tracer_provider=provider, openlineage_client=client)

    pipe = _build_pipeline()
    catalog = DataCatalog({"raw_in": MemoryDataset(pd.DataFrame({"a": [1, 2, 3]}))})

    hm = _create_hook_manager()
    _register_hooks(hm, (hooks,))
    # KedroSession fires the pipeline hooks around the runner; replicate that so the
    # parent pipeline span exists (runner.run alone does not call pipeline hooks).
    run_params = {"pipeline_name": "__default__"}
    hooks.before_pipeline_run(run_params, pipe, catalog)
    SequentialRunner().run(pipe, catalog, hook_manager=hm)
    hooks.after_pipeline_run(run_params, {}, pipe, catalog)

    return exporter.get_finished_spans(), events


# --------------------------------------------------------------------------- #
# OpenLineage lineage + metrics facets
# --------------------------------------------------------------------------- #
def test_openlineage_emits_start_and_complete_per_node(captured):
    _, events = captured
    by_node: dict[str, set] = {}
    for e in events:
        by_node.setdefault(e.job.name, set()).add(e.eventType)
    assert by_node["double_it"] == {RunState.START, RunState.COMPLETE}
    assert by_node["tag_it"] == {RunState.START, RunState.COMPLETE}
    # every job is in our namespace
    assert {e.job.namespace for e in events} == {"cf_atlas"}


def test_openlineage_captures_input_output_lineage(captured):
    _, events = captured
    complete = {e.job.name: e for e in events if e.eventType == RunState.COMPLETE}
    d = complete["double_it"]
    assert [i.name for i in d.inputs] == ["raw_in"]
    assert [o.name for o in d.outputs] == ["mid"]
    t = complete["tag_it"]
    assert [i.name for i in t.inputs] == ["mid"]
    assert [o.name for o in t.outputs] == ["final_out"]


def test_start_and_complete_share_a_run_id(captured):
    _, events = captured
    for name in ("double_it", "tag_it"):
        ids = {e.run.runId for e in events if e.job.name == name}
        assert len(ids) == 1, f"{name} START/COMPLETE must share one runId"


def test_output_statistics_rowcount_facet(captured):
    _, events = captured
    complete = {e.job.name: e for e in events if e.eventType == RunState.COMPLETE}
    # 3 input rows survive both transforms → 3 output rows on each output dataset.
    out = complete["double_it"].outputs[0]
    assert out.facets["outputStatistics"].rowCount == 3


def test_node_metrics_run_facet_rows_latency_cache(captured):
    _, events = captured
    complete = {e.job.name: e for e in events if e.eventType == RunState.COMPLETE}
    dm = complete["double_it"].run.facets["atlasNodeMetrics"]
    tm = complete["tag_it"].run.facets["atlasNodeMetrics"]
    assert isinstance(dm, AtlasNodeMetricsRunFacet)
    # rows present + correct; latency present & non-negative (shape, not a value).
    assert dm.rows == 3
    assert dm.latency_ms >= 0.0
    # double_it's input (raw_in) is external → 0 cache hits; tag_it's input (mid)
    # was produced upstream this run → 1 in-run memory-cache hit.
    assert dm.cache_hits == 0
    assert tm.cache_hits == 1


# --------------------------------------------------------------------------- #
# OpenTelemetry span tree (parent → node → dataset-IO)
# --------------------------------------------------------------------------- #
def test_span_tree_is_nested_pipeline_node_dataset(captured):
    spans, _ = captured
    by_name = {s.name: s for s in spans}
    pipeline = by_name["pipeline_run"]
    assert pipeline.parent is None  # root

    node_span = by_name["node:double_it"]
    # node span's parent is the pipeline span (real nesting, not flat).
    assert node_span.parent is not None
    assert node_span.parent.span_id == pipeline.context.span_id

    # dataset-IO ("API call") spans resolve BELOW the node span.
    write_span = by_name["write mid"]
    assert write_span.parent is not None
    assert write_span.parent.span_id == node_span.context.span_id
    read_span = by_name["read raw_in"]
    assert read_span.parent.span_id == node_span.context.span_id


def test_node_span_carries_metric_attributes(captured):
    spans, _ = captured
    node_span = next(s for s in spans if s.name == "node:double_it")
    assert node_span.attributes["pyforge.rows"] == 3
    assert node_span.attributes["pyforge.cache_hits"] == 0
    assert node_span.attributes["pyforge.latency_ms"] >= 0.0


def test_all_spans_belong_to_one_trace(captured):
    spans, _ = captured
    trace_ids = {s.context.trace_id for s in spans}
    assert len(trace_ids) == 1, "spans must share one end-to-end trace"


# --------------------------------------------------------------------------- #
# Edge cases (Reviewer-B surface): errors, no-IO nodes, non-DataFrame, no captor.
# --------------------------------------------------------------------------- #
def _direct_hooks():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    client, events = make_capturing_client()
    return (
        AtlasObservabilityHooks(tracer_provider=provider, openlineage_client=client),
        exporter,
        events,
    )


def test_node_error_emits_fail_and_closes_span():
    hooks, exporter, events = _direct_hooks()
    n = node(_double, inputs="raw_in", outputs="mid", name="double_it")
    hooks.before_pipeline_run({}, None, None)
    hooks.before_node_run(n, None, {"raw_in": pd.DataFrame({"a": [1]})}, False, "r1")
    hooks.on_node_error(ValueError("boom"), n, None, {"raw_in": None}, False, "r1")
    hooks.after_pipeline_run({}, {}, None, None)

    fail = [e for e in events if e.eventType == RunState.FAIL]
    assert len(fail) == 1
    assert fail[0].run.facets["errorMessage"].message == "boom"
    # the node span was closed (no leak) — it appears among finished spans.
    node_spans = [s for s in exporter.get_finished_spans() if s.name == "node:double_it"]
    assert len(node_spans) == 1
    assert node_spans[0].status.status_code.name == "ERROR"


def test_node_with_no_inputs_or_outputs():
    hooks, exporter, events = _direct_hooks()
    n = node(lambda: pd.DataFrame({"a": [1]}), inputs=None, outputs="only_out", name="src")
    hooks.before_pipeline_run({}, None, None)
    hooks.before_node_run(n, None, {}, False, "r1")
    hooks.after_node_run(n, None, {}, {"only_out": pd.DataFrame({"a": [1, 2]})}, False, "r1")
    hooks.after_pipeline_run({}, {}, None, None)
    complete = next(e for e in events if e.eventType == RunState.COMPLETE)
    assert complete.inputs == []
    assert complete.run.facets["atlasNodeMetrics"].rows == 2
    assert complete.run.facets["atlasNodeMetrics"].cache_hits == 0


def test_empty_frame_rows_facet_is_zero():
    hooks, exporter, events = _direct_hooks()
    n = node(_double, inputs="raw_in", outputs="mid", name="double_it")
    hooks.before_pipeline_run({}, None, None)
    empty = pd.DataFrame({"a": []})
    hooks.before_node_run(n, None, {"raw_in": empty}, False, "r1")
    hooks.after_node_run(n, None, {"raw_in": empty}, {"mid": empty}, False, "r1")
    hooks.after_pipeline_run({}, {}, None, None)
    complete = next(e for e in events if e.eventType == RunState.COMPLETE)
    assert complete.run.facets["atlasNodeMetrics"].rows == 0
    assert complete.outputs[0].facets["outputStatistics"].rowCount == 0


def test_non_dataframe_output_degrades_without_crashing():
    hooks, exporter, events = _direct_hooks()
    n = node(_double, inputs="raw_in", outputs="mid", name="double_it")
    hooks.before_pipeline_run({}, None, None)
    hooks.before_node_run(n, None, {"raw_in": 42}, False, "r1")
    # a scalar (non-sized) output must not crash; rowCount facet is simply omitted.
    hooks.after_node_run(n, None, {"raw_in": 42}, {"mid": 42}, False, "r1")
    hooks.after_pipeline_run({}, {}, None, None)
    complete = next(e for e in events if e.eventType == RunState.COMPLETE)
    assert "outputStatistics" not in complete.outputs[0].facets
    assert complete.run.facets["atlasNodeMetrics"].rows == 0


def test_default_path_is_noop_and_does_not_crash():
    # No injected captors → both backends default to no-op/offline; the full
    # lifecycle must run without raising and without emitting anywhere.
    hooks = AtlasObservabilityHooks()
    n = node(_double, inputs="raw_in", outputs="mid", name="double_it")
    df = pd.DataFrame({"a": [1, 2]})
    hooks.before_pipeline_run({}, None, None)
    hooks.before_node_run(n, None, {"raw_in": df}, False, "r1")
    hooks.after_node_run(n, None, {"raw_in": df}, {"mid": df}, False, "r1")
    hooks.after_pipeline_run({}, {}, None, None)
    # error path too
    hooks.before_node_run(n, None, {"raw_in": df}, False, "r2")
    hooks.on_node_error(RuntimeError("x"), n, None, {"raw_in": df}, False, "r2")
    hooks.on_pipeline_error(RuntimeError("x"), {}, None, None)


def test_nested_pipeline_runs_do_not_leak_spans():
    # Re-entrancy: an inner pipeline frame nests under the outer; both close cleanly.
    hooks, exporter, events = _direct_hooks()
    n = node(_double, inputs="raw_in", outputs="mid", name="double_it")
    df = pd.DataFrame({"a": [1]})
    hooks.before_pipeline_run({"pipeline_name": "outer"}, None, None)
    hooks.before_pipeline_run({"pipeline_name": "inner"}, None, None)
    hooks.before_node_run(n, None, {"raw_in": df}, False, "r1")
    hooks.after_node_run(n, None, {"raw_in": df}, {"mid": df}, False, "r1")
    hooks.after_pipeline_run({"pipeline_name": "inner"}, {}, None, None)
    hooks.after_pipeline_run({"pipeline_name": "outer"}, {}, None, None)
    pipeline_spans = [s for s in exporter.get_finished_spans() if s.name == "pipeline_run"]
    assert len(pipeline_spans) == 2  # both frames closed, none leaked


def test_metrics_facet_serializes():
    # the custom facet round-trips to a plain dict (no now()/uuid inside).
    f = AtlasNodeMetricsRunFacet(rows=5, latency_ms=1.5, cache_hits=2)
    d = attr.asdict(f)
    assert d["rows"] == 5 and d["cache_hits"] == 2 and d["latency_ms"] == 1.5


def test_sized_non_dataframe_output_degrades_not_bogus_rowcount():
    """Reviewer-B finding 1: a len()-able NON-frame output (dict / list / str) must DEGRADE
    (no rowCount facet), not report a misleading element/char count. rowCount is a TABULAR
    measure — gated on a 2-D .shape, not bare len()."""
    hooks, exporter, events = _direct_hooks()
    for bad in ({"k": "v", "j": "w"}, [1, 2, 3, 4, 5], "hello"):
        n = node(_double, inputs="raw_in", outputs="mid", name="nd")
        hooks.before_pipeline_run({}, None, None)
        hooks.before_node_run(n, None, {"raw_in": pd.DataFrame({"a": [1]})}, False, "r1")
        hooks.after_node_run(n, None, {"raw_in": pd.DataFrame({"a": [1]})}, {"mid": bad}, False, "r1")
        hooks.after_pipeline_run({}, {}, None, None)
        complete = [e for e in events if e.eventType == RunState.COMPLETE][-1]
        assert "outputStatistics" not in complete.outputs[0].facets, f"bogus rowCount for {type(bad).__name__}"


def test_pipeline_error_emits_ol_fail_for_in_flight_nodes():
    """Reviewer-B finding 3: a node still open when the pipeline errors must get an OL FAIL
    terminal — an OL consumer pairing START↔terminal must not see a dangling START."""
    hooks, exporter, events = _direct_hooks()
    n = node(_double, inputs="raw_in", outputs="mid", name="open_node")
    hooks.before_pipeline_run({}, None, None)
    hooks.before_node_run(n, None, {"raw_in": pd.DataFrame({"a": [1]})}, False, "r1")
    # pipeline errors while `open_node` is still in flight (no after_node_run / on_node_error)
    hooks.on_pipeline_error(RuntimeError("pipeline boom"), {}, None, None)
    starts = [e for e in events if e.eventType == RunState.START]
    fails = [e for e in events if e.eventType == RunState.FAIL]
    assert len(starts) == 1 and len(fails) == 1  # the START has a matching terminal
    assert fails[0].job.name == "open_node"
    assert fails[0].run.runId == starts[0].run.runId  # same run — a real terminal, not a new one


def test_deepcopy_preserves_injected_backends_no_otel_ol_asymmetry():
    """Reviewer-A finding 6: C1's translator DEEP-COPIES the settings hooks. The copy must
    keep BOTH the injected OTel provider and the OL client (by reference) — dropping the
    provider while keeping _ol would silently emit OL events but NO spans on the Dagster
    plane once a real exporter is injected."""
    import copy

    hooks, exporter, events = _direct_hooks()
    dup = copy.deepcopy(hooks)
    assert dup._provider is hooks._provider  # shared by reference (survives the copy)
    assert dup._ol is hooks._ol              # symmetric — both backends survive
    # the copy actually EMITS to the shared injected backends (no silent OTel drop):
    n = node(_double, inputs="raw_in", outputs="mid", name="dup_node")
    dup.before_pipeline_run({}, None, None)
    dup.before_node_run(n, None, {"raw_in": pd.DataFrame({"a": [1]})}, False, "r1")
    dup.after_node_run(n, None, {"raw_in": pd.DataFrame({"a": [1]})}, {"mid": pd.DataFrame({"a": [1, 2]})}, False, "r1")
    dup.after_pipeline_run({}, {}, None, None)
    assert any(e.eventType == RunState.COMPLETE for e in events)  # OL emitted
    assert [s for s in exporter.get_finished_spans() if s.name == "node:dup_node"]  # OTel emitted
