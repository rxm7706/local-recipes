"""pyforge.core.hooks -- the ONE shared hook-spec and plugin-registration
surface (Story 32.1, FR-43).

Stations consume this loader; they do not ship a second one. Canonical
entry-point group is ``pyforge.core.hooks`` only (stdlib
``importlib.metadata.entry_points``, no pluggy, no setuptools runtime dep).

``around``: a plugin's ``call("around", context)`` may run
``context["next"](context)`` to continue the chain. If ``next`` is absent,
``around`` is still invoked -- that is the documented equivalent.

``publish_verdict`` is allowed only when the plugin owns the spec
(``plugin.hook_spec == spec.name`` and ``plugin.owner == spec.owner``). A
plugin that would publish a second verdict for a process another owner
specified raises ``SecondVerdictError``.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, Protocol

from pyforge.core.errors import PyforgeError

ENTRY_POINT_GROUP = "pyforge.core.hooks"

HOOK_POINTS: frozenset[str] = frozenset({"before", "after", "around"})

# Named exclusions -- these are contract surfaces, not plugin extension
# points. Tests assert each phrase is present; do not drop a name.
NOT_PLUGIN_SURFACES: frozenset[str] = frozenset(
    {
        "Pixi task names",
        "Golden Path artifact identity",
        "parent infra kinds",
        "host import boundary (pyforge.* under src/platform/)",
        "the Warden verdict",
    }
)

EXAMPLE_HOOK_SPEC_NAME = "pyforge.core.example"
EXAMPLE_HOOK_OWNER = "core"


class PluginError(PyforgeError):
    """Raised when a hook point is unknown, an entry-point target is bad,
    or a declared plugin cannot be loaded. Never silently skips a declared
    entry-point name."""


class SecondVerdictError(PluginError):
    """Raised when a plugin would publish a verdict for a ``HookSpec`` it
    does not own (a second verdict for a process another owner specified)."""


@dataclass(frozen=True)
class HookSpec:
    """Published shape of one hook: a unique ``name`` and the process
    ``owner`` allowed to publish a verdict for it."""

    name: str
    owner: str


EXAMPLE_HOOK_SPEC = HookSpec(name=EXAMPLE_HOOK_SPEC_NAME, owner=EXAMPLE_HOOK_OWNER)


class HookPlugin(Protocol):
    """A plugin bound to one hook-spec name and one process owner."""

    hook_spec: str
    owner: str

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        """Run at a named ``before`` / ``after`` / ``around`` point."""
        ...


class DummyPlugin:
    """In-tree dummy declared on ``pyforge.core.hooks`` for the published
    API (spec ``pyforge.core.example``, owner ``core``)."""

    hook_spec: str = EXAMPLE_HOOK_SPEC_NAME
    owner: str = EXAMPLE_HOOK_OWNER

    def __init__(self) -> None:
        self.calls: list[str] = []

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        self.calls.append(point)
        if point == "around":
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context


def _require_plugin(obj: object, *, label: str) -> HookPlugin:
    missing = [attr for attr in ("call", "hook_spec", "owner") if not hasattr(obj, attr)]
    if missing:
        raise PluginError(f"{label} is not a HookPlugin (missing {', '.join(missing)})")
    if not callable(getattr(obj, "call")):
        raise PluginError(f"{label} has a non-callable call attribute")
    return obj  # type: ignore[return-value]


def _as_plugin(loaded: object, *, ep_name: str) -> HookPlugin:
    label = f"entry point {ep_name!r} in group {ENTRY_POINT_GROUP!r}"
    if isinstance(loaded, type):
        try:
            loaded = loaded()
        except Exception as exc:
            raise PluginError(f"{label} could not be instantiated") from exc
    return _require_plugin(loaded, label=label)


def publish_verdict(spec: HookSpec, plugin: HookPlugin, verdict: object) -> object:
    """Record a verdict for ``spec``. Allowed only when ``plugin`` owns
    that spec (name and process owner both match). Owner-matched publish
    returns ``verdict`` unchanged."""
    if plugin.hook_spec != spec.name or plugin.owner != spec.owner:
        raise SecondVerdictError(
            f"plugin hook_spec={plugin.hook_spec!r} owner={plugin.owner!r} "
            f"cannot publish a verdict for spec {spec.name!r} owned by "
            f"{spec.owner!r}"
        )
    return verdict


class PluginRegistry:
    """In-process registry: ``register``, ``load_entry_points``, ``invoke``."""

    def __init__(self) -> None:
        self._plugins: list[HookPlugin] = []

    def register(self, plugin: HookPlugin) -> None:
        plugin = _require_plugin(plugin, label="register()")
        key = (type(plugin), plugin.hook_spec, plugin.owner)
        if any((type(existing), existing.hook_spec, existing.owner) == key for existing in self._plugins):
            return
        self._plugins.append(plugin)

    def load_entry_points(self, group: str = ENTRY_POINT_GROUP) -> None:
        """Load every declared name in ``group``. A bad target raises
        ``PluginError`` -- a declared name is never silently skipped.
        Plugins are committed only after every name loads so a late
        failure does not leave a partial registry."""
        discovered = entry_points(group=group)
        loaded_plugins: list[HookPlugin] = []
        for ep in discovered:
            try:
                loaded = ep.load()
            except Exception as exc:
                raise PluginError(f"entry point {ep.name!r} in group {group!r} failed to load") from exc
            loaded_plugins.append(_as_plugin(loaded, ep_name=ep.name))
        for plugin in loaded_plugins:
            self.register(plugin)

    def invoke(
        self,
        point: str,
        context: MutableMapping[str, Any] | None = None,
        *,
        spec_name: str,
    ) -> list[Any]:
        """Call plugins registered for ``spec_name`` at ``point``.
        ``spec_name`` is required so a station invoke never runs the
        in-tree dummy (or another spec's plugins) by accident.
        Unknown point → ``PluginError``."""
        if point not in HOOK_POINTS:
            raise PluginError(f"unknown hook point: {point!r}")
        ctx: MutableMapping[str, Any] = {} if context is None else context
        results: list[Any] = []
        for plugin in self._plugins:
            if plugin.hook_spec != spec_name:
                continue
            results.append(plugin.call(point, ctx))
        return results

    @property
    def plugins(self) -> tuple[HookPlugin, ...]:
        return tuple(self._plugins)
