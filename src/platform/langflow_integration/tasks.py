"""Story 11.3 (pap:CAP-4, AD-17 Pattern A): proves the
registry-driven dispatch shape is symmetric across both integration patterns.
`dbgpt_integration/tasks.py::text_to_sql` proves Pattern-B's shape (a Celery
task that talks to its engine OVER REST, to a sidecar); this module proves
Pattern-A's (a Celery task that talks to its engine IN-PROCESS, no REST hop
-- Langflow already lives inside this same process, mounted by
`langflow_integration/asgi.py`).

Deliberately minimal (Boundaries & Constraints, `Block If`): this is not a
flow-execution feature (no user-supplied flow id, no persistence, no auth).
It builds one deterministic, LLM-free `TextInput` -> `TextOutput` flow --
the exact same pair `langflow_integration/tests.py::_build_text_only_flow_data`
uses for its own AC3 proof -- and runs it via `lfx.processing.process.
run_graph`, Langflow's OWN already-public in-process entry point (the same
function `lfx.graph.graph.base.Graph.arun`'s callers use;
`langflow_integration/tests.py`'s AC3 test instead drives the full ASGI
`/api/v1/run/<flow-id>` HTTP path, which needs a live lifespan + auth
session -- genuine but unnecessary machinery for what this task needs to
prove). No Django ORM, no database, no auth session: `TextInputComponent`/
`TextOutputComponent` (`lfx.components.input_output`) are a pure,
synchronous pass-through, so this task's only real dependency is Langflow's
own already-imported component/graph machinery -- confirmed live (2026-08-21)
against the `python-agent-platform` pixi env's own `lfx` install: `run_graph`
returns a `RunOutputs` whose final `ResultData.outputs["text"]["message"]`
carries the echoed text back out, unchanged.
"""

from __future__ import annotations

import asyncio
from typing import Any

from celery import shared_task


def _run_echo_flow(seed_text: str) -> str:
    """Build and run the deterministic `TextInput` -> `TextOutput` flow,
    in-process, returning the echoed message text.

    Imports are deferred into the task body (not module level) so importing
    this module never requires the `langflow`/`lfx` packages -- matching
    `langflow_integration/asgi.py`'s own "Django settings first" ordering
    concern doesn't apply here (no Django settings are read), but keeping
    Celery's `autodiscover_tasks()` import of this module cheap and free of
    a hard `lfx` dependency at import time still matches this codebase's own
    convention (`langflow_integration/tests.py`'s `pytest.importorskip`).
    """
    from lfx.components.input_output.text import TextInputComponent  # noqa: PLC0415
    from lfx.components.input_output.text_output import (  # noqa: PLC0415
        TextOutputComponent,
    )
    from lfx.graph import Graph  # noqa: PLC0415
    from lfx.processing.process import run_graph  # noqa: PLC0415

    text_input = TextInputComponent()
    text_input.set(input_value=seed_text)
    text_output = TextOutputComponent()
    text_output.set(input_value=text_input.text_response)
    graph = Graph(start=text_input, end=text_output)

    async def _arun() -> str:
        run_outputs = await run_graph(
            graph,
            input_value=seed_text,
            input_type="text",
            output_type="text",
        )
        return run_outputs[0].outputs[0].outputs["text"]["message"]

    return asyncio.run(_arun())


@shared_task()
def run_echo_flow(seed_text: str) -> dict[str, Any]:
    """Pattern-A proof: dispatch this via `.delay()` and it executes
    in-process inside the worker -- Langflow's own graph/component code
    imported and called directly, never a REST hop to a sidecar (AD-17's
    registry marks `"langflow": "A"` in `config/engine_patterns.py`).

    Args:
        seed_text: the text to echo through the flow.

    Returns:
        `{"echoed": <seed_text, round-tripped through a real Langflow
        TextInput->TextOutput graph run>}`.
    """
    return {"echoed": _run_echo_flow(seed_text)}
