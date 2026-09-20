"""Mason's replaceable native recipe build-engine hook (Story 10.1, FR-45).

Publishes ``pyforge.mason.build_engine`` (owner ``mason``) on the shared
``pyforge.core.hooks`` surface. Stations consume that loader; this module
does not ship a second entry-point group.

Select **one** plugin, then ``call`` it. Do not ``PluginRegistry.invoke``
every plugin registered on this spec -- that would run rattler-build and
conda-build together. ``engine_name`` is mason-local; FR-43 ``HookPlugin``
stays ``hook_spec`` / ``owner`` / ``call``.

Default ``around`` calls ``context["next"]`` so today's CFE native path
stays the backend. conda-build is registered so an operator can select it
later; this module does not spawn ``conda-build`` or ``rattler-build``.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from pyforge.core.hooks import (
    HOOK_POINTS,
    HookPlugin,
    HookSpec,
    PluginError,
    PluginRegistry,
)

BUILD_ENGINE_HOOK_SPEC = HookSpec(name="pyforge.mason.build_engine", owner="mason")

DEFAULT_BUILD_ENGINE = "rattler-build"


class _BuildEnginePlugin:
    """Shared ``around``: stamp ``engine``, then run ``next`` when present."""

    hook_spec: str = BUILD_ENGINE_HOOK_SPEC.name
    owner: str = BUILD_ENGINE_HOOK_SPEC.owner
    engine_name: str
    is_default: bool = False

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point not in HOOK_POINTS:
            raise PluginError(f"unknown hook point: {point!r}")
        context["engine"] = self.engine_name
        if point == "around":
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context


class RattlerBuildPlugin(_BuildEnginePlugin):
    """Default native backend -- today's CFE ``build_native`` path as ``next``."""

    engine_name: str = DEFAULT_BUILD_ENGINE
    is_default: bool = True


class CondaBuildPlugin(_BuildEnginePlugin):
    """Alternate engine on the same spec. This story does not spawn conda-build."""

    engine_name: str = "conda-build"
    is_default: bool = False


def build_engine_registry() -> PluginRegistry:
    """In-tree registry of both shipped plugins (no entry-point load required)."""
    registry = PluginRegistry()
    registry.register(RattlerBuildPlugin())
    registry.register(CondaBuildPlugin())
    return registry


def select_build_engine_plugin(
    registry: PluginRegistry | None = None,
    *,
    name: str | None = None,
) -> HookPlugin:
    """Return one plugin for ``BUILD_ENGINE_HOOK_SPEC``.

    ``name is None`` selects the default (rattler-build). Unknown ``name``
    raises ``PluginError``.
    """
    registry = registry if registry is not None else build_engine_registry()
    candidates = [plugin for plugin in registry.plugins if plugin.hook_spec == BUILD_ENGINE_HOOK_SPEC.name]
    if name is None:
        defaults = [plugin for plugin in candidates if getattr(plugin, "is_default", False)]
        if not defaults:
            raise PluginError(f"no default build-engine plugin registered for {BUILD_ENGINE_HOOK_SPEC.name!r}")
        if len(defaults) > 1:
            raise PluginError(f"multiple default build-engine plugins registered for {BUILD_ENGINE_HOOK_SPEC.name!r}")
        return defaults[0]
    for plugin in candidates:
        if getattr(plugin, "engine_name", None) == name:
            return plugin
    raise PluginError(f"unknown build engine: {name!r}")
