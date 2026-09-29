"""Story 10.1 -- mason build-engine hook on ``pyforge.core.hooks``.

Covers the intent-contract I/O matrix: default rattler-build plugin,
in-process alternate register + select by name, quoted entry-point group
(no parallel mason group), ``around`` invoking ``next`` (and still running
when ``next`` is absent), and a mason build result is not a Warden PR-gate
verdict. No real conda-build/rattler-build subprocesses.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest
from pyforge.core.hooks import (
    ENTRY_POINT_GROUP,
    HookSpec,
    PluginError,
    SecondVerdictError,
    publish_verdict,
)

from pyforge.mason.engines.build_hooks import (
    BUILD_ENGINE_HOOK_SPEC,
    DEFAULT_BUILD_ENGINE,
    CondaBuildPlugin,
    RattlerBuildPlugin,
    _BuildEnginePlugin,
    build_engine_registry,
    select_build_engine_plugin,
)
from pyforge.mason.models import BuildResult

_MASON_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


class _SandboxPlugin(_BuildEnginePlugin):
    engine_name = "sandbox"
    is_default = False


def test_default_plugin_is_rattler_build():
    plugin = select_build_engine_plugin()
    assert isinstance(plugin, RattlerBuildPlugin)
    assert plugin.is_default
    assert plugin.engine_name == DEFAULT_BUILD_ENGINE == "rattler-build"
    assert plugin.hook_spec == BUILD_ENGINE_HOOK_SPEC.name
    assert plugin.owner == "mason"


def test_alternate_plugin_registered_in_process_is_selected_by_name_without_forking():
    pid = os.getpid()
    registry = build_engine_registry()
    registry.register(_SandboxPlugin())
    plugin = select_build_engine_plugin(registry, name="sandbox")
    assert isinstance(plugin, _SandboxPlugin)
    seen: list[str] = []

    def _next(context: dict) -> str:
        seen.append(context["engine"])
        return "ran-in-process"

    result = plugin.call("around", {"next": _next})
    assert result == "ran-in-process"
    assert seen == ["sandbox"]
    assert os.getpid() == pid


def test_unknown_engine_name_raises_plugin_error():
    with pytest.raises(PluginError, match="unknown build engine"):
        select_build_engine_plugin(name="does-not-exist")


def test_pyproject_declares_both_plugins_on_the_canonical_hooks_group_only():
    data = tomllib.loads(_MASON_PYPROJECT.read_text(encoding="utf-8"))
    groups = data["project"]["entry-points"]
    assert ENTRY_POINT_GROUP in groups
    names = groups[ENTRY_POINT_GROUP]
    assert names["rattler-build"] == ("pyforge.mason.engines.build_hooks:RattlerBuildPlugin")
    assert names["conda-build"] == ("pyforge.mason.engines.build_hooks:CondaBuildPlugin")
    assert "pyforge.mason.hooks" not in groups
    assert "pyforge.mason.plugins" not in groups


def test_default_around_runs_next_and_stamps_rattler_build_engine():
    plugin = RattlerBuildPlugin()
    seen: list[str] = []

    def _next(context: dict) -> str:
        seen.append(context["engine"])
        return "continued"

    result = plugin.call("around", {"next": _next})
    assert result == "continued"
    assert seen == ["rattler-build"]


def test_around_is_still_invoked_when_next_is_absent():
    plugin = RattlerBuildPlugin()
    context: dict[str, object] = {}
    result = plugin.call("around", context)
    assert result is context
    assert context["engine"] == "rattler-build"


def test_conda_build_plugin_is_registered_as_an_alternate_on_the_same_spec():
    plugin = select_build_engine_plugin(name="conda-build")
    assert isinstance(plugin, CondaBuildPlugin)
    assert plugin.is_default is False
    assert plugin.engine_name == "conda-build"
    assert plugin.hook_spec == BUILD_ENGINE_HOOK_SPEC.name


def test_successful_build_is_not_a_warden_pr_gate_verdict():
    plugin = RattlerBuildPlugin()
    build = BuildResult(
        mode="native",
        config="linux64",
        returncode=0,
        stdout="ok",
        artifact_dir="build_artifacts/linux64",
    )
    warden_spec = HookSpec(name="pyforge.warden.pr_gate", owner="warden")
    with pytest.raises(SecondVerdictError):
        publish_verdict(warden_spec, plugin, build)
    assert publish_verdict(BUILD_ENGINE_HOOK_SPEC, plugin, build) is build


def test_unknown_hook_point_raises_plugin_error():
    with pytest.raises(PluginError, match="unknown hook point"):
        RattlerBuildPlugin().call("during", {})


def test_multiple_default_plugins_raise_plugin_error():
    class _SecondDefault(_BuildEnginePlugin):
        engine_name = "other-default"
        is_default = True

    registry = build_engine_registry()
    registry.register(_SecondDefault())
    with pytest.raises(PluginError, match="multiple default"):
        select_build_engine_plugin(registry)
