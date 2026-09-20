"""GraphStore factory over ``pyforge.core.hooks`` (Story 4.1 / 28.1, CAP-18).

Callers (``compile.py``, CLI recall) obtain a ``GraphStore`` here -- they
never import an engine client. The default plugin is
``FlatFileGraphStorePlugin`` (owner ``scribe``). Owner ``steward`` is the
PostgreSQL/pgvector driver (Story 28.1). This module does not import
PostgreSQL / pgvector / SQLite -- the steward plugin is loaded via entry
points.
"""

from __future__ import annotations

import os
from pathlib import Path

from pyforge.core.hooks import PluginError, PluginRegistry

from pyforge.scribe.graph_store import (
    GRAPHSTORE_HOOK_SPEC,
    FlatFileGraphStorePlugin,
    GraphStore,
)

_OWNER_ENV = "PYFORGE_GRAPHSTORE_OWNER"
_DSN_ENV = "SCRIBE_GRAPH_DSN"
_PLANE_PATH_ENV = "QUERY_PLANE_DUCKDB"


def open_graph_store(
    store_path: Path,
    *,
    registry: PluginRegistry | None = None,
    owner: str | None = None,
) -> GraphStore:
    """Return a ``GraphStore`` from the plugin matching ``owner``.

    ``invoke`` would run every plugin with the same ``spec_name``, so the
    factory selects by ``owner`` and calls that plugin's ``around`` itself.
    Unknown ``owner`` raises ``PluginError``. A missing PostgreSQL class is
    never imported here; ``psycopg`` stays in ``graph_store_pg``.
    Default owner is ``scribe`` unless ``PYFORGE_GRAPHSTORE_OWNER`` is set.
    """
    if owner is None:
        owner = os.environ.get(_OWNER_ENV, GRAPHSTORE_HOOK_SPEC.owner)
    if registry is None:
        registry = PluginRegistry()
        registry.load_entry_points()
    if owner == GRAPHSTORE_HOOK_SPEC.owner and not any(
        plugin.hook_spec == GRAPHSTORE_HOOK_SPEC.name and plugin.owner == owner for plugin in registry.plugins
    ):
        registry.register(FlatFileGraphStorePlugin())
    if owner == "atlas" and not any(
        plugin.hook_spec == GRAPHSTORE_HOOK_SPEC.name and plugin.owner == owner for plugin in registry.plugins
    ):
        from pyforge.scribe.graph_store_plane import PlaneGraphStorePlugin

        registry.register(PlaneGraphStorePlugin())

    selected = None
    for plugin in registry.plugins:
        if plugin.hook_spec == GRAPHSTORE_HOOK_SPEC.name and plugin.owner == owner:
            selected = plugin
            break
    if selected is None:
        raise PluginError(f"no graph-store plugin registered for owner {owner!r} (spec {GRAPHSTORE_HOOK_SPEC.name!r})")

    context: dict = {"store_path": store_path}
    dsn = os.environ.get(_DSN_ENV) or os.environ.get("DATABASE_URL")
    if dsn:
        context["dsn"] = dsn.split("?", 1)[0]
    plane = os.environ.get(_PLANE_PATH_ENV)
    if plane:
        context["plane_path"] = plane
    selected.call("around", context)
    store = context.get("store")
    if store is None:
        raise PluginError(f"graph-store plugin owner={owner!r} did not set context['store']")
    return store
