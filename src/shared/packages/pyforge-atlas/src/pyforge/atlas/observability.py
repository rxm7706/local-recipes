"""OpenLineage + OpenTelemetry instrumentation hooks (Story E2, FR-12).

This module is the **single observability seam** (AD-6/AD-23): it is the ONLY
module in ``pyforge.atlas`` permitted to import ``openlineage`` / ``opentelemetry``
(structurally enforced by
``tests/catalog/test_no_inline_io.py::test_observability_libs_only_in_observability``).
All instrumentation lives here, in a Kedro **Hooks** implementation registered in
``settings.HOOKS`` — so EVERY entry point inherits it once (AD-23): a ``kedro run``
picks up the settings hooks natively, and a Dagster run picks them up too because
C1's :class:`kedro_dagster.KedroProjectTranslator` runs each node through
``KedroSession.run`` (settings hooks included). Nodes stay pure DataFrame→DataFrame
(AD-2/AD-6); no instrumentation ever touches a node body.

What is captured
----------------
- **OpenLineage** — each node run emits a ``RunEvent`` START (before) and
  COMPLETE (after) — or FAIL on error — carrying the node's input/output dataset
  **lineage** (``InputDataset``/``OutputDataset`` by catalog name) plus per-node
  **metrics** (rows / latency / cache-hits) in facets: the standard
  ``OutputStatisticsOutputDatasetFacet.rowCount`` per output dataset, and an
  :class:`AtlasNodeMetricsRunFacet` on the run carrying ``rows`` / ``latency_ms``
  / ``cache_hits``.
- **OpenTelemetry** — the pipeline run is a parent span; each node run is a child
  span; each dataset read/write is a grandchild span named after the dataset
  (the "API call" where the dataset IO happens). Node spans carry the same
  rows/latency/cache-hit attributes.

Offline-by-default & injectable (AD-20)
---------------------------------------
Both backends are injectable and **default to no-op** so the in-container default
path emits nowhere (no network at import or at run):

- ``tracer_provider=None`` → a local :class:`~opentelemetry.sdk.trace.TracerProvider`
  with NO exporter (spans are created but dropped; nothing is set globally).
- ``openlineage_client=None`` → OL emission is skipped entirely.

The **gate** (``tests/observability/``) injects an in-memory OTel span exporter and
a capturing OpenLineage client (:func:`make_capturing_client`) and asserts the
emitted event/span shape — those captured fixtures ARE the gate (AD-20). The LIVE
collector/exporter wiring (a real OTLP endpoint / OpenLineage backend URL, env-driven)
is DEFERRED — see deferred-work ``DW-E2-1``.

``cache_hits`` semantics
------------------------
An in-run memory-cache hit: a node input that was produced by an **upstream node
in the same pipeline run** (served from the catalog's in-memory cache) rather than
loaded fresh from an external source. Deterministic and driver-agnostic — derived
from the set of dataset names already produced this run, not from wall-clock or
dataset internals.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import attr
from kedro.framework.hooks import hook_impl
from openlineage.client import OpenLineageClient
from openlineage.client.event_v2 import (
    InputDataset,
    Job,
    OutputDataset,
    Run,
    RunEvent,
    RunState,
)
from openlineage.client.facet_v2 import (
    error_message_run,
    output_statistics_output_dataset,
)
from openlineage.client.generated.base import RunFacet
from openlineage.client.transport import Transport
from openlineage.client.uuid import generate_new_uuid
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Span, Status, StatusCode

# Producer URI stamped on every emitted OpenLineage facet/event (this project).
PRODUCER = "https://github.com/rxm7706/local-recipes/tree/main/pyforge-atlas"

# Default OpenLineage namespace for the migrated cf_atlas DAG.
DEFAULT_NAMESPACE = "cf_atlas"


@attr.define
class AtlasNodeMetricsRunFacet(RunFacet):
    """Per-node metrics carried on the OpenLineage run (FR-12 rows/latency/cache).

    A custom ``RunFacet`` so the rows / latency / cache-hit measurements travel
    with the node's COMPLETE event alongside the standard output-statistics
    rowCount facet.
    """

    rows: int = 0
    latency_ms: float = 0.0
    cache_hits: int = 0


def make_capturing_client() -> tuple[OpenLineageClient, list[RunEvent]]:
    """An OpenLineage client whose transport captures emitted events in a list.

    Returned as ``(client, events)`` — the gate injects ``client`` into the hook
    and asserts on ``events`` (AD-20: captured events are the gate). Offline; no
    network transport is constructed.
    """
    captured: list[RunEvent] = []

    class _CapturingTransport(Transport):
        kind = "capture"
        name = "capture"

        def __init__(self) -> None:  # noqa: D107 - trivial in-memory sink
            pass

        def emit(self, event: Any) -> None:
            captured.append(event)

    return OpenLineageClient(transport=_CapturingTransport()), captured


@dataclass
class _PipelineFrame:
    """Per-pipeline-run state (a stack frame — supports nested pipelines)."""

    span: Span | None
    produced: set[str] = field(default_factory=set)


@dataclass
class _NodeState:
    """Per-node-run state carried between before/after (or error) node hooks."""

    span: Span
    started: float
    ol_run_id: str
    cache_hits: int
    node: Any = None  # the Kedro node — kept so a pipeline-error can emit its OL FAIL lineage


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rowcount(value: Any) -> int | None:
    """Row count of a TABULAR dataset value (a pandas/polars-style frame with a 2-D
    ``.shape``), degrading to ``None`` for anything else. Bare ``len()`` would report a
    misleading count for the many ``len()``-able non-frames a node can output — a params
    ``dict`` (key count), a path ``str`` (char count), a ``list``/``set`` (element count):
    those are NOT row counts, so they must degrade, not lie (Reviewer-B finding 1). Gate on
    frame-ness (a 2-D ``.shape``) rather than duck-typing ``len()``."""
    shape = getattr(value, "shape", None)
    if isinstance(shape, tuple) and len(shape) == 2:
        return int(shape[0])
    return None


class AtlasObservabilityHooks:
    """Kedro hooks emitting OpenLineage lineage/metrics + OpenTelemetry traces.

    Parameters
    ----------
    tracer_provider:
        OTel tracer provider. ``None`` (default) builds a local ``TracerProvider``
        with no exporter — spans are created but go nowhere (offline). The gate
        injects a provider wired to an in-memory span exporter.
    openlineage_client:
        OpenLineage client. ``None`` (default) skips all OL emission (offline).
        The gate injects a capturing client (:func:`make_capturing_client`).
    namespace:
        OpenLineage dataset/job namespace (default ``cf_atlas``).
    """

    def __init__(
        self,
        *,
        tracer_provider: TracerProvider | None = None,
        openlineage_client: OpenLineageClient | None = None,
        namespace: str = DEFAULT_NAMESPACE,
    ) -> None:
        # The tracer is built LAZILY (see _tracer). A TracerProvider holds a thread
        # lock, and C1's KedroProjectTranslator deep-copies the settings hooks at
        # `to_dagster()` build time — a provider created eagerly here would make the
        # instance un-deepcopyable. Building on first use keeps the freshly-imported
        # instance (the deepcopy source) lock-free. No global side effect either: we
        # never call otel_trace.set_tracer_provider, and the default provider has no
        # span processor, so spans are dropped (offline, no network).
        self._provider = tracer_provider
        self._tracer_cache = None
        self._ol = openlineage_client
        self._namespace = namespace
        self._pipelines: list[_PipelineFrame] = []
        self._nodes: dict[str, _NodeState] = {}

    @property
    def _tracer(self):
        if self._tracer_cache is None:
            provider = self._provider if self._provider is not None else TracerProvider()
            self._tracer_cache = provider.get_tracer("pyforge.atlas.observability")
        return self._tracer_cache

    def __deepcopy__(self, memo: dict[int, Any]) -> "AtlasObservabilityHooks":
        # C1's KedroProjectTranslator DEEP-COPIES the settings HOOKS at to_dagster() build
        # time, so the Dagster plane runs against a copy. Share the injected OTel provider
        # AND the OpenLineage client BY REFERENCE into that copy: both planes must emit to
        # the SAME injected backends. Deep-copying them would (a) fail — an OTel
        # TracerProvider holds a thread lock and is un-deepcopyable — and (b) silently drop
        # ONLY the provider while keeping _ol, an OTel-drops/OL-survives asymmetry that would
        # make the Dagster plane emit OL events but NO spans once a real exporter is injected
        # (Reviewer-A finding 6). Only the built tracer + per-run mutable state are fresh.
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        new._provider = self._provider          # shared by reference (survives; un-deepcopyable)
        new._ol = self._ol                       # shared by reference (same backend, both planes)
        new._namespace = self._namespace
        new._tracer_cache = None                 # rebuilt lazily from the shared provider
        new._pipelines = []                      # fresh per-run span/lineage state
        new._nodes = {}
        return new

    def __getstate__(self) -> dict[str, Any]:
        # Pickle fallback (multiprocess executors). Deep-copy — the C1 path — goes through
        # __deepcopy__ above (which preserves the injected backends). Pickle can NOT carry a
        # live TracerProvider (thread lock) or an in-memory exporter across a process
        # boundary, so the provider is dropped and a child rebuilds from env-driven config;
        # an in-memory captor is inherently single-process anyway.
        state = self.__dict__.copy()
        state["_tracer_cache"] = None
        state["_provider"] = None
        state["_pipelines"] = []
        state["_nodes"] = {}
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)

    # -- OpenLineage helpers ------------------------------------------------ #

    def _emit(self, event: RunEvent) -> None:
        if self._ol is not None:
            self._ol.emit(event)

    def _input_datasets(self, node: Any) -> list[InputDataset]:
        return [InputDataset(namespace=self._namespace, name=n) for n in node.inputs]

    def _output_datasets(
        self, node: Any, outputs: dict[str, Any] | None = None
    ) -> list[OutputDataset]:
        datasets: list[OutputDataset] = []
        for name in node.outputs:
            facets = {}
            if outputs is not None and name in outputs:
                rows = _rowcount(outputs[name])
                if rows is not None:
                    facets["outputStatistics"] = (
                        output_statistics_output_dataset.OutputStatisticsOutputDatasetFacet(
                            rowCount=rows, producer=PRODUCER
                        )
                    )
            datasets.append(
                OutputDataset(namespace=self._namespace, name=name, facets=facets)
            )
        return datasets

    # -- OTel helpers ------------------------------------------------------- #

    def _current_pipeline_span(self) -> Span | None:
        return self._pipelines[-1].span if self._pipelines else None

    def _dataset_span(self, parent: Span, op: str, name: str, rows: int | None) -> None:
        """Emit an instantaneous child span for a dataset read/write ("API call"
        where the dataset IO happens), parented to the node span."""
        ctx = otel_trace.set_span_in_context(parent)
        span = self._tracer.start_span(f"{op} {name}", context=ctx)
        span.set_attribute("pyforge.dataset", name)
        span.set_attribute("pyforge.op", op)
        if rows is not None:
            span.set_attribute("pyforge.rows", rows)
        span.end()

    # -- Pipeline lifecycle ------------------------------------------------- #

    @hook_impl
    def before_pipeline_run(
        self, run_params: dict[str, Any], pipeline: Any, catalog: Any
    ) -> None:
        span = self._tracer.start_span("pipeline_run")
        span.set_attribute("pyforge.pipeline", str(run_params.get("pipeline_name") or "__default__"))
        self._pipelines.append(_PipelineFrame(span=span))

    @hook_impl
    def after_pipeline_run(
        self,
        run_params: dict[str, Any],
        run_result: dict[str, Any],
        pipeline: Any,
        catalog: Any,
    ) -> None:
        self._close_pipeline(StatusCode.OK)

    @hook_impl
    def on_pipeline_error(
        self, error: Exception, run_params: dict[str, Any], pipeline: Any, catalog: Any
    ) -> None:
        # Defensively close any node spans still open (a mid-node crash) so no span leaks,
        # AND emit an OpenLineage FAIL terminal for each in-flight node so an OL consumer
        # never sees a dangling START with no COMPLETE/FAIL (Reviewer-B finding 3). Then
        # close the pipeline span with an error status.
        for state in list(self._nodes.values()):
            state.span.set_status(Status(StatusCode.ERROR))
            state.span.end()
            if state.node is not None:
                self._emit_node_fail(state.node, state.ol_run_id, error)
        self._nodes.clear()
        self._close_pipeline(StatusCode.ERROR, error)

    def _close_pipeline(self, code: StatusCode, error: Exception | None = None) -> None:
        if not self._pipelines:
            return
        frame = self._pipelines.pop()
        if frame.span is not None:
            if code is StatusCode.ERROR:
                frame.span.set_status(Status(StatusCode.ERROR))
                if error is not None:
                    frame.span.record_exception(error)
            frame.span.end()

    # -- Node lifecycle ----------------------------------------------------- #

    @hook_impl
    def before_node_run(
        self,
        node: Any,
        catalog: Any,
        inputs: dict[str, Any],
        is_async: bool,
        run_id: str,
    ) -> None:
        parent = self._current_pipeline_span()
        produced = self._pipelines[-1].produced if self._pipelines else set()
        cache_hits = sum(1 for name in node.inputs if name in produced)

        ctx = otel_trace.set_span_in_context(parent) if parent is not None else None
        span = self._tracer.start_span(f"node:{node.name}", context=ctx)
        span.set_attribute("pyforge.node", node.name)
        span.set_attribute("pyforge.cache_hits", cache_hits)

        # Input-read child spans (the dataset IO / API call for each input).
        for name in node.inputs:
            self._dataset_span(span, "read", name, _rowcount(inputs.get(name)))

        ol_run_id = str(generate_new_uuid())
        self._nodes[node.name] = _NodeState(
            span=span, started=time.perf_counter(), ol_run_id=ol_run_id,
            cache_hits=cache_hits, node=node,
        )

        self._emit(
            RunEvent(
                eventType=RunState.START,
                eventTime=_now_iso(),
                run=Run(runId=ol_run_id),
                job=Job(namespace=self._namespace, name=node.name),
                producer=PRODUCER,
                inputs=self._input_datasets(node),
                outputs=self._output_datasets(node),
            )
        )

    @hook_impl
    def after_node_run(
        self,
        node: Any,
        catalog: Any,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        is_async: bool,
        run_id: str,
    ) -> None:
        state = self._nodes.pop(node.name, None)
        if state is None:
            return
        latency_ms = (time.perf_counter() - state.started) * 1000.0
        total_rows = sum(
            r for r in (_rowcount(v) for v in outputs.values()) if r is not None
        )

        # Output-write child spans (the dataset IO / API call for each output).
        for name in node.outputs:
            self._dataset_span(state.span, "write", name, _rowcount(outputs.get(name)))

        state.span.set_attribute("pyforge.rows", total_rows)
        state.span.set_attribute("pyforge.latency_ms", latency_ms)
        state.span.set_status(Status(StatusCode.OK))
        state.span.end()

        # Record outputs as produced (feeds the cache-hit derivation downstream).
        if self._pipelines:
            self._pipelines[-1].produced.update(node.outputs)

        self._emit(
            RunEvent(
                eventType=RunState.COMPLETE,
                eventTime=_now_iso(),
                run=Run(
                    runId=state.ol_run_id,
                    facets={
                        "atlasNodeMetrics": AtlasNodeMetricsRunFacet(
                            rows=total_rows,
                            latency_ms=latency_ms,
                            cache_hits=state.cache_hits,
                        )
                    },
                ),
                job=Job(namespace=self._namespace, name=node.name),
                producer=PRODUCER,
                inputs=self._input_datasets(node),
                outputs=self._output_datasets(node, outputs),
            )
        )

    @hook_impl
    def on_node_error(
        self,
        error: Exception,
        node: Any,
        catalog: Any,
        inputs: dict[str, Any],
        is_async: bool,
        run_id: str,
    ) -> None:
        state = self._nodes.pop(node.name, None)
        if state is not None:
            state.span.set_status(Status(StatusCode.ERROR))
            state.span.record_exception(error)
            state.span.end()
        self._emit_node_fail(node, state.ol_run_id if state is not None else None, error)

    def _emit_node_fail(self, node: Any, ol_run_id: str | None, error: Exception) -> None:
        """Emit the OpenLineage FAIL terminal for a node run (shared by on_node_error and the
        pipeline-error sweep, so an OL consumer that pairs START↔terminal never sees a
        dangling run — Reviewer-B finding 3)."""
        self._emit(
            RunEvent(
                eventType=RunState.FAIL,
                eventTime=_now_iso(),
                run=Run(
                    runId=ol_run_id if ol_run_id is not None else str(generate_new_uuid()),
                    facets={
                        "errorMessage": error_message_run.ErrorMessageRunFacet(
                            message=str(error),
                            programmingLanguage="python",
                            producer=PRODUCER,
                        )
                    },
                ),
                job=Job(namespace=self._namespace, name=node.name),
                producer=PRODUCER,
                inputs=self._input_datasets(node),
                outputs=self._output_datasets(node),
            )
        )
