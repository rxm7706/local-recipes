"""Stub node factory.

Every node in the prototype is a pure passthrough: it records its own name and
how many upstream datasets fed it, and returns a small dict so `kedro run`
executes the full DAG with MemoryDatasets. The real migration replaces each
stub with the ported phase logic (spec § 9, Waves A-B).
"""

from typing import Any, Callable


def stub(name: str, n_outputs: int = 1) -> Callable[..., Any]:
    """Return a passthrough function suitable for `kedro.pipeline.node`."""

    def _fn(*inputs: Any) -> Any:
        payload = {"stage": name, "n_inputs": len(inputs)}
        if n_outputs == 1:
            return payload
        return tuple({**payload, "output_index": i} for i in range(n_outputs))

    _fn.__name__ = name
    _fn.__doc__ = f"Stub for `{name}` — replaced by the real port in Wave B."
    return _fn
