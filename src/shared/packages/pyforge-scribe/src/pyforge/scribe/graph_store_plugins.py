"""GraphStore factory over ``pyforge.core.hooks`` (Story 4.1, CAP-18).

Callers (``compile.py``, CLI recall) obtain a ``GraphStore`` here -- they
never import an engine client. The default plugin is
``FlatFileGraphStorePlugin`` (owner ``scribe``). Owner ``steward`` is
reserved for steward S-28.1's durable driver; this module does not load
or import PostgreSQL / pgvector / SQLite.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.hooks import PluginError, PluginRegistry
from pyforge.scribe.graph_store import (
    GRAPHSTORE_HOOK_SPEC,
    FlatFileGraphStorePlugin,
    GraphStore,
)


def open_graph_store(
    store_path: Path,
    *,
    registry: PluginRegistry | None = None,
    owner: str = GRAPHSTORE_HOOK_SPEC.owner,
) -> GraphStore:
    """Return a ``GraphStore`` from the plugin matching ``owner``.

    ``invoke`` would run every plugin with the same ``spec_name``, so the
    factory selects by ``owner`` and calls that plugin's ``around`` itself.
    Unknown ``owner`` raises ``PluginError``. A missing PostgreSQL class is
    never imported.
    """
    if registry is None:
        registry = PluginRegistry()
        registry.load_entry_points()
    if owner == GRAPHSTORE_HOOK_SPEC.owner and not any(
        plugin.hook_spec == GRAPHSTORE_HOOK_SPEC.name and plugin.owner == owner
        for plugin in registry.plugins
    ):
        registry.register(FlatFileGraphStorePlugin())

    selected = None
    for plugin in registry.plugins:
        if plugin.hook_spec == GRAPHSTORE_HOOK_SPEC.name and plugin.owner == owner:
            selected = plugin
            break
    if selected is None:
        raise PluginError(
            f"no graph-store plugin registered for owner {owner!r} "
            f"(spec {GRAPHSTORE_HOOK_SPEC.name!r})"
        )

    context: dict = {"store_path": store_path}
    selected.call("around", context)
    store = context.get("store")
    if store is None:
        raise PluginError(
            f"graph-store plugin owner={owner!r} did not set context['store']"
        )
    return store
