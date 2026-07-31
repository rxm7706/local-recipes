"""Bridge-core's designated module (Story 1.4, AD-3/AD-4) -- the one seam
allowed to call a ``DesignTransport`` port method.

``run`` is deliberately almost the whole module: ``return operation(transport)``
is its entire body. The value isn't runtime logic -- it's the contract.
``operation: Callable[[DesignTransport], T]`` hands a CAP function nothing
more concrete than the ``DesignTransport`` protocol (``transport/base.py``);
the annotation itself is a type-checker contract, not a runtime fence --
Python never enforces it, and a function defined elsewhere could still
close over an adapter built elsewhere. What *is* enforced, statically, is
this module's own source: ``test_bridge.py``'s determinism-boundary check
walks the AST -- every import statement and every named identifier -- and
fails on a concrete adapter module (``mcp_transport``, a future
``agent_sdk_transport``), any name an adapter module exports, an
LLM/inference-SDK package, or dynamic-import / dynamic-attribute machinery
(``importlib``, ``__import__``, ``eval``, ``exec``, ``getattr``). So any
CAP function whose body lands here cannot name a concrete adapter or an
inference SDK at all -- which is what AD-3 (bridge-core is
transport-agnostic) and AD-4 (the determinism boundary holds regardless of
active transport) require.

The ``transport.base`` import is ``TYPE_CHECKING``-only: importing the
package at runtime would execute ``transport/__init__.py``, which eagerly
re-exports the concrete ``McpTransport`` -- the boundary should hold in
``sys.modules``, not only in this file's AST.

No CAP function body lives here yet -- each lands with its own story:
``seed`` (1.6), ``pull`` (2.x), ``status`` (3.x), ``watch`` (4.x),
``push_exports`` (5.x). Any ``HeraldError`` an ``operation`` raises
propagates unchanged through ``run`` -- this module never catches one; AD-6
assigns that to ``cli.dispatch``, the CLI boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .transport.base import DesignTransport


def run[T](transport: DesignTransport, operation: Callable[[DesignTransport], T]) -> T:
    """Call ``operation`` with ``transport`` and return its result unchanged.

    This seam hands ``operation`` nothing more concrete than the
    ``DesignTransport`` protocol, so a CAP function cannot reach a concrete
    adapter *through it* (a closure formed elsewhere is that module's
    boundary check to fail, not this one's). Any ``HeraldError``
    ``operation`` raises propagates out of ``run`` unchanged -- this
    function never catches one."""
    return operation(transport)
