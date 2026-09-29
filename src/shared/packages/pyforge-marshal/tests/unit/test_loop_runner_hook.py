"""Unit tests for Marshal's loop/runner hook (Story 26.1).

Covers the intent-contract I/O matrix: default plugin on
``pyforge.core.hooks``, named before/after/around invoke, alternate
in-process registration without a marshal fork, entry-point group
conformance, second-verdict ownership, and the AST pin that harness
sources never call ``publish_verdict``.
"""

from __future__ import annotations

import ast
import inspect
import tomllib
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import pytest
from pyforge.core.hooks import (
    ENTRY_POINT_GROUP,
    HookSpec,
    PluginError,
    PluginRegistry,
    SecondVerdictError,
    publish_verdict,
)

from pyforge.marshal.adapters.harness_bmadloop import (
    DEFAULT_LOOP_RUNNER_PLUGIN_ID,
    LOOP_RUNNER_HOOK_SPEC,
    BmadLoopHarness,
    resolve_loop_runner,
)

_MARSHAL_ROOT = Path(__file__).resolve().parents[2]
_HARNESS_SOURCE = _MARSHAL_ROOT / "src" / "pyforge" / "marshal" / "adapters" / "harness_bmadloop.py"
_PYPROJECT = _MARSHAL_ROOT / "pyproject.toml"


class _AltRunner:
    hook_spec = LOOP_RUNNER_HOOK_SPEC.name
    owner = LOOP_RUNNER_HOOK_SPEC.owner
    plugin_id = "alt-runner"

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        return context


def test_default_plugin_attributes_and_resolver():
    registry = PluginRegistry()
    runner = resolve_loop_runner(registry=registry)
    assert isinstance(runner, BmadLoopHarness)
    assert runner.hook_spec == "pyforge.marshal.loop_runner"
    assert runner.owner == "marshal"
    assert runner.plugin_id == "bmad-loop"
    assert runner.plugin_id == DEFAULT_LOOP_RUNNER_PLUGIN_ID


def test_resolve_loop_runner_without_registry_returns_bmad_loop_harness():
    runner = resolve_loop_runner()
    assert isinstance(runner, BmadLoopHarness)
    assert runner.hook_spec == LOOP_RUNNER_HOOK_SPEC.name
    assert runner.owner == LOOP_RUNNER_HOOK_SPEC.owner
    assert runner.plugin_id == DEFAULT_LOOP_RUNNER_PLUGIN_ID


def test_named_hook_points_invoke_the_default_plugin():
    plugin = BmadLoopHarness()
    registry = PluginRegistry()
    registry.register(plugin)
    seen: list[str] = []

    def _next(context: dict) -> str:
        seen.append("next")
        return "continued"

    for point in ("before", "after"):
        registry.invoke(point, {}, spec_name=LOOP_RUNNER_HOOK_SPEC.name)
    result = registry.invoke(
        "around",
        {"next": _next},
        spec_name=LOOP_RUNNER_HOOK_SPEC.name,
    )
    assert plugin.calls == ["before", "after", "around"]
    assert seen == ["next"]
    assert result == ["continued"]


def test_unknown_hook_point_raises_plugin_error():
    registry = PluginRegistry()
    registry.register(BmadLoopHarness())
    with pytest.raises(PluginError, match="unknown hook point"):
        registry.invoke("during", {}, spec_name=LOOP_RUNNER_HOOK_SPEC.name)


def test_alternate_plugin_registers_without_forking_marshal():
    registry = PluginRegistry()
    registry.register(BmadLoopHarness())
    alt = _AltRunner()
    registry.register(alt)
    selected = resolve_loop_runner(plugin_id="alt-runner", registry=registry)
    assert selected is alt
    missing = resolve_loop_runner(plugin_id="no-such-runner", registry=registry)
    assert isinstance(missing, BmadLoopHarness)


def test_pyproject_declares_bmad_loop_only_on_core_hooks_group():
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    groups = data.get("project", {}).get("entry-points", {})
    assert ENTRY_POINT_GROUP in groups
    assert groups[ENTRY_POINT_GROUP]["bmad-loop"] == ("pyforge.marshal.adapters.harness_bmadloop:BmadLoopHarness")
    assert "pyforge.marshal.hooks" not in groups


def test_second_verdict_for_warden_pr_gate_is_rejected():
    plugin = BmadLoopHarness()
    warden = HookSpec(name="pyforge.warden.pr_gate", owner="warden")
    with pytest.raises(SecondVerdictError):
        publish_verdict(warden, plugin, "stolen")
    assert publish_verdict(LOOP_RUNNER_HOOK_SPEC, plugin, "ok") == "ok"


def test_harness_sources_never_call_publish_verdict():
    source = _HARNESS_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == "publish_verdict":
                hits.append(f"line {node.lineno}")
    assert not hits, f"harness_bmadloop.py must not call publish_verdict: {hits}"
    assert "publish_verdict" not in inspect.getsource(BmadLoopHarness.call)
