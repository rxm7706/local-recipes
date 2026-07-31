"""Bridge-core's designated module (Story 1.4, AD-3/AD-4) -- the one seam
allowed to call a ``DesignTransport`` port method.

``run`` is deliberately almost the whole module: ``return operation(transport)``
is its entire body. The value isn't runtime logic -- it's the type signature.
``operation: Callable[[DesignTransport], T]`` makes it structurally
impossible for a future CAP function reached through this seam to close over
a concrete adapter (``McpTransport``, the future ``AgentSdkTransport``) or an
inference SDK: the only thing ``operation`` is ever handed is something typed
to the ``DesignTransport`` protocol (``transport/base.py``), never a concrete
class. This is exactly what AD-3 (bridge-core is transport-agnostic) and AD-4
(the determinism boundary holds regardless of active transport) require, and
what ``test_bridge.py``'s static determinism-boundary check verifies by
inspecting this module's AST -- every import statement and every named
identifier -- for a concrete adapter module (``mcp_transport``, a future
``agent_sdk_transport``), an adapter class name, an LLM/inference-SDK
package, or dynamic-import machinery: none may ever appear here.

No CAP function body lives here yet -- each lands with its own story:
``seed`` (1.6), ``pull`` (2.x), ``status`` (3.x), ``watch`` (4.x),
``push_exports`` (5.x). Any ``HeraldError`` an ``operation`` raises
propagates unchanged through ``run`` -- this module never catches one; AD-6
assigns that to ``cli.dispatch``, the CLI boundary.
"""

from __future__ import annotations

from collections.abc import Callable

from .transport.base import DesignTransport


def run[T](transport: DesignTransport, operation: Callable[[DesignTransport], T]) -> T:
    """Call ``operation`` with ``transport`` and return its result unchanged.

    ``operation``'s parameter is typed to ``DesignTransport`` only, so no
    future CAP function passed here can reach a concrete adapter through
    this seam. Any ``HeraldError`` ``operation`` raises propagates out of
    ``run`` unchanged -- this function never catches one."""
    return operation(transport)
