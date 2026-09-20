"""Unit tests for ``pyforge.warden.hooks`` (Story 9.1, FR-43 consumer).

Covers the intent-contract I/O matrix: hook book ownership, invoke at
named points, unknown point, owner-matched vs competing verdict, empty
registry. Engines stay in-tree (``register_engine``).
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import pytest
from pyforge.core.errors import PyforgeError
from pyforge.core.hooks import (
    ENTRY_POINT_GROUP as CORE_ENTRY_POINT_GROUP,
)
from pyforge.core.hooks import (
    DummyPlugin,
    HookSpec,
    PluginError,
    PluginRegistry,
    SecondVerdictError,
    publish_verdict,
)

from pyforge.warden.engines import registered_engines
from pyforge.warden.hooks import (
    ENTRY_POINT_GROUP,
    PR_GATE_AGGREGATE,
    PR_GATE_HOOK_SPECS,
    PR_GATE_SCAN,
    PR_GATE_VERDICT,
    WardenVerdictOwner,
    invoke_pr_gate,
    pr_gate_registry,
    publish_pr_gate_verdict,
)


class _ScanPlugin:
    """Scanner-shaped plugin: attaches to scan, does not own the verdict."""

    hook_spec: str = PR_GATE_SCAN.name
    owner: str = "checkmarx"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        self.calls.append(point)
        nxt = context.get("next")
        if point == "around" and callable(nxt):
            return nxt(context)
        return context


def test_hook_book_publishes_three_warden_owned_specs():
    names = {spec.name for spec in PR_GATE_HOOK_SPECS}
    assert names == {
        "pyforge.warden.pr_gate.scan",
        "pyforge.warden.pr_gate.aggregate",
        "pyforge.warden.pr_gate.verdict",
    }
    assert PR_GATE_SCAN.owner == "warden"
    assert PR_GATE_AGGREGATE.owner == "warden"
    assert PR_GATE_VERDICT.owner == "warden"
    assert all(spec.owner == "warden" for spec in PR_GATE_HOOK_SPECS)


def test_entry_point_group_is_the_core_canonical_string():
    assert ENTRY_POINT_GROUP == CORE_ENTRY_POINT_GROUP == "pyforge.core.hooks"


def test_invoke_pr_gate_runs_a_registered_scan_plugin_at_each_point():
    plugin = _ScanPlugin()
    registry = PluginRegistry()
    registry.register(plugin)
    for point in ("before", "after", "around"):
        invoke_pr_gate(PR_GATE_SCAN, point, {}, registry=registry)
    assert plugin.calls == ["before", "after", "around"]


def test_scan_plugin_is_not_invoked_for_aggregate_or_verdict():
    plugin = _ScanPlugin()
    registry = PluginRegistry()
    registry.register(plugin)
    assert invoke_pr_gate(PR_GATE_AGGREGATE, "before", {}, registry=registry) == []
    assert invoke_pr_gate(PR_GATE_VERDICT, "after", {}, registry=registry) == []
    assert plugin.calls == []


def test_unknown_hook_point_raises_plugin_error_from_core():
    registry = PluginRegistry()
    registry.register(_ScanPlugin())
    with pytest.raises(PluginError, match="unknown hook point"):
        invoke_pr_gate(PR_GATE_SCAN, "during", {}, registry=registry)


def test_unknown_pr_gate_spec_raises_plugin_error():
    foreign = HookSpec(name="pyforge.core.example", owner="core")
    with pytest.raises(PluginError, match="unknown PR-gate spec"):
        invoke_pr_gate(foreign, "before", {}, registry=PluginRegistry())


def test_empty_registry_returns_empty_list():
    registry = PluginRegistry()
    assert invoke_pr_gate(PR_GATE_SCAN, "before", {}, registry=registry) == []
    assert invoke_pr_gate(PR_GATE_AGGREGATE, "after", {}, registry=registry) == []
    assert invoke_pr_gate(PR_GATE_VERDICT, "around", {}, registry=registry) == []


def test_default_pr_gate_registry_empty_invoke_returns_empty_list():
    assert pr_gate_registry().plugins == ()
    assert invoke_pr_gate(PR_GATE_SCAN, "before", {}) == []


def test_core_dummy_does_not_run_on_the_pr_gate():
    registry = PluginRegistry()
    registry.load_entry_points()
    dummy = next(
        (p for p in registry.plugins if isinstance(p, DummyPlugin)),
        None,
    )
    assert dummy is not None, "core dummy must actually load so [] is not a vacuous empty registry"
    before = list(dummy.calls)
    invoke_pr_gate(PR_GATE_SCAN, "before", {}, registry=registry)
    assert dummy.calls == before


def test_publish_pr_gate_verdict_allows_owner_matched_warden():
    owner = WardenVerdictOwner()
    assert owner.owner == PR_GATE_VERDICT.owner
    assert owner.hook_spec == PR_GATE_VERDICT.name
    assert publish_pr_gate_verdict("ok") == "ok"


def test_competing_verdict_from_foreign_owner_raises_second_verdict_error():
    with pytest.raises(SecondVerdictError):
        publish_verdict(PR_GATE_VERDICT, _ScanPlugin(), "stolen")


def test_competing_verdict_from_wrong_hook_spec_raises_second_verdict_error():
    class _WrongSpec:
        hook_spec = PR_GATE_SCAN.name
        owner = "warden"

        def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
            return context

    with pytest.raises(SecondVerdictError):
        publish_verdict(PR_GATE_VERDICT, _WrongSpec(), "stolen")


def test_second_verdict_error_is_a_plugin_error_and_pyforge_error():
    assert issubclass(SecondVerdictError, PluginError)
    assert issubclass(SecondVerdictError, PyforgeError)


def test_in_tree_engines_remain_registered():
    names = {type(engine).__name__ for engine in registered_engines()}
    assert names >= {
        "NullEngine",
        "DeptryEngine",
        "OsvEngine",
        "LicenseEngine",
        "CurrencyEngine",
    }
