"""Unit tests for ``pyforge.core.hooks`` (Story 32.1, FR-43).

Covers the intent-contract I/O matrix: dummy before/after/around invoke,
entry-point load (including a bad target that must not be skipped),
second-verdict ownership, unknown hook point, and the five named
non-plugin surfaces.
"""

from __future__ import annotations

from importlib.metadata import entry_points

import pytest

from pyforge.core.errors import PyforgeError
from pyforge.core.hooks import (
    ENTRY_POINT_GROUP,
    EXAMPLE_HOOK_SPEC,
    HOOK_POINTS,
    NOT_PLUGIN_SURFACES,
    DummyPlugin,
    HookSpec,
    PluginError,
    PluginRegistry,
    SecondVerdictError,
    publish_verdict,
)


def test_hook_points_are_before_after_around():
    assert HOOK_POINTS == frozenset({"before", "after", "around"})


def test_dummy_is_invoked_at_each_named_point():
    dummy = DummyPlugin()
    registry = PluginRegistry()
    registry.register(dummy)
    for point in ("before", "after", "around"):
        registry.invoke(point, {}, spec_name="pyforge.core.example")
    assert dummy.calls == ["before", "after", "around"]


def test_around_may_invoke_context_next():
    dummy = DummyPlugin()
    registry = PluginRegistry()
    registry.register(dummy)
    seen: list[str] = []

    def _next(context: dict) -> str:
        seen.append("next")
        return "continued"

    result = registry.invoke(
        "around",
        {"next": _next},
        spec_name="pyforge.core.example",
    )
    assert dummy.calls == ["around"]
    assert seen == ["next"]
    assert result == ["continued"]


def test_around_is_still_invoked_when_next_is_absent():
    dummy = DummyPlugin()
    registry = PluginRegistry()
    registry.register(dummy)
    result = registry.invoke("around", {}, spec_name="pyforge.core.example")
    assert dummy.calls == ["around"]
    assert result == [{}]


def test_unknown_hook_point_raises_plugin_error():
    registry = PluginRegistry()
    registry.register(DummyPlugin())
    with pytest.raises(PluginError, match="unknown hook point"):
        registry.invoke("during", {}, spec_name="pyforge.core.example")


def test_register_rejects_a_plugin_missing_owner():
    class _NoOwner:
        hook_spec = "pyforge.core.example"

        def call(self, point, context):
            return context

    registry = PluginRegistry()
    with pytest.raises(PluginError, match="missing owner"):
        registry.register(_NoOwner())


def test_register_is_idempotent_for_the_same_plugin_class_and_spec():
    registry = PluginRegistry()
    registry.register(DummyPlugin())
    registry.register(DummyPlugin())
    assert len(registry.plugins) == 1


def test_load_entry_points_is_atomic_when_a_later_target_fails(monkeypatch):
    class _Ok:
        name = "ok"

        def load(self) -> object:
            return DummyPlugin

    class _Broken:
        name = "broken"

        def load(self) -> object:
            raise ImportError("missing module")

    monkeypatch.setattr(
        "pyforge.core.hooks.entry_points",
        lambda group=None: [_Ok(), _Broken()],
    )
    registry = PluginRegistry()
    with pytest.raises(PluginError, match="failed to load"):
        registry.load_entry_points()
    assert registry.plugins == ()


def test_plugin_error_is_a_pyforge_error():
    assert issubclass(PluginError, PyforgeError)
    assert issubclass(SecondVerdictError, PyforgeError)


def test_load_entry_points_registers_the_installed_dummy():
    discovered = list(entry_points(group=ENTRY_POINT_GROUP))
    assert discovered, f"installed distribution must declare group {ENTRY_POINT_GROUP!r}"
    registry = PluginRegistry()
    registry.load_entry_points()
    assert any(isinstance(p, DummyPlugin) for p in registry.plugins)
    dummy = next(p for p in registry.plugins if isinstance(p, DummyPlugin))
    registry.invoke("before", {}, spec_name="pyforge.core.example")
    assert dummy.calls == ["before"]


def test_load_entry_points_raises_plugin_error_on_a_bad_target_and_does_not_skip(
    monkeypatch,
):
    class _Broken:
        name = "broken"

        def load(self) -> object:
            raise ImportError("missing module")

    monkeypatch.setattr(
        "pyforge.core.hooks.entry_points",
        lambda group=None: [_Broken()],
    )
    registry = PluginRegistry()
    with pytest.raises(PluginError, match="failed to load"):
        registry.load_entry_points()
    assert registry.plugins == ()


def test_publish_verdict_allows_owner_matched_dummy():
    dummy = DummyPlugin()
    assert publish_verdict(EXAMPLE_HOOK_SPEC, dummy, "ok") == "ok"


def test_publish_verdict_raises_second_verdict_error_for_a_foreign_spec():
    dummy = DummyPlugin()
    foreign = HookSpec(name="pyforge.warden.gate", owner="warden")
    with pytest.raises(SecondVerdictError):
        publish_verdict(foreign, dummy, "stolen")


def test_publish_verdict_raises_when_owner_does_not_match():
    dummy = DummyPlugin()
    mismatched = HookSpec(name="pyforge.core.example", owner="warden")
    with pytest.raises(SecondVerdictError):
        publish_verdict(mismatched, dummy, "stolen")


def test_not_plugin_surfaces_name_the_five_exclusions():
    blob = " ".join(NOT_PLUGIN_SURFACES).lower()
    required = (
        "pixi task names",
        "golden path artifact identity",
        "parent infra kinds",
        "host import boundary",
        "warden verdict",
    )
    missing = [name for name in required if name not in blob]
    assert not missing, f"NOT_PLUGIN_SURFACES missing {missing}: {NOT_PLUGIN_SURFACES}"
