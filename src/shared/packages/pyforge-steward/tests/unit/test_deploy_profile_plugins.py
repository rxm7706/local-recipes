"""Story 32.2: deploy-profile adapters as plugins on ``pyforge.core.hooks``."""

from __future__ import annotations

import ast
import tomllib
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import pytest
from pyforge.core.hooks import (
    ENTRY_POINT_GROUP,
    HOOK_POINTS,
    HookSpec,
    PluginError,
    PluginRegistry,
    SecondVerdictError,
    publish_verdict,
)

from pyforge.steward.deploy_profiles import (
    DEFAULT_DEPLOY_PROFILE_IDS,
    DEPLOY_PROFILE_HOOK_SPEC,
    DEPLOY_PROFILE_HOOK_SPEC_NAME,
    DEPLOY_PROFILE_OWNER,
    GOLDEN_PATH_PIXI_TASK,
    OPTIONAL_VENDOR_TOKENS,
    PLUGIN_TACHYON,
    TachyonDeployPlugin,
    default_deploy_profile_registry,
    run_golden_path,
    select_deploy_profile_plugin,
)

_PKG_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _PKG_ROOT / "pyproject.toml"
_PROFILES_SRC = _PKG_ROOT / "src" / "pyforge" / "steward" / "deploy_profiles.py"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        pixi = ancestor / "pixi.toml"
        if not pixi.is_file():
            continue
        if (ancestor / "CLAUDE.md").is_file():
            return ancestor
    raise RuntimeError("could not locate repo-root pixi.toml walking up from tests")


_PIXI = _repo_root() / "pixi.toml"


def _registry_with_defaults() -> PluginRegistry:
    return default_deploy_profile_registry()


def test_default_plugins_register_the_six_vendor_ids():
    registry = _registry_with_defaults()
    ids = [
        getattr(plugin, "plugin_id") for plugin in registry.plugins if plugin.hook_spec == DEPLOY_PROFILE_HOOK_SPEC_NAME
    ]
    assert tuple(ids) == DEFAULT_DEPLOY_PROFILE_IDS
    assert all(plugin.owner == DEPLOY_PROFILE_OWNER for plugin in registry.plugins)
    assert all(getattr(plugin, "optional", False) for plugin in registry.plugins)


def test_pyproject_declares_six_plugins_on_canonical_group_only():
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    groups = data["project"]["entry-points"]
    assert ENTRY_POINT_GROUP in groups
    assert "pyforge.steward.hooks" not in groups
    assert "pyforge.steward.plugins" not in groups
    declared = groups[ENTRY_POINT_GROUP]
    assert set(declared) == set(DEFAULT_DEPLOY_PROFILE_IDS)


@pytest.mark.parametrize("plugin_id", DEFAULT_DEPLOY_PROFILE_IDS)
def test_select_each_default_plugin(plugin_id: str):
    plugin = select_deploy_profile_plugin(plugin_id)
    assert plugin.plugin_id == plugin_id
    assert plugin.hook_spec == DEPLOY_PROFILE_HOOK_SPEC_NAME


def test_unknown_plugin_id_raises_plugin_error():
    with pytest.raises(PluginError, match="unknown deploy-profile plugin"):
        select_deploy_profile_plugin("not-a-vendor")


def test_alternate_plugin_registers_on_same_spec_without_fork():
    class AltCdPlugin:
        hook_spec = DEPLOY_PROFILE_HOOK_SPEC_NAME
        owner = DEPLOY_PROFILE_OWNER
        plugin_id = "alt-cd"

        def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
            del point
            context.setdefault("ran", []).append(self.plugin_id)
            return context

    registry = _registry_with_defaults()
    registry.register(AltCdPlugin())
    plugin = select_deploy_profile_plugin("alt-cd", registry=registry)
    ctx: dict[str, Any] = {"ran": []}
    plugin.call("around", ctx)
    assert ctx["ran"] == ["alt-cd"]
    assert select_deploy_profile_plugin("harness", registry=registry).plugin_id == ("harness")


def test_unknown_hook_point_raises_plugin_error():
    plugin = select_deploy_profile_plugin("harness")
    with pytest.raises(PluginError, match="unknown hook point"):
        plugin.call("sideways", {})


@pytest.mark.parametrize("point", sorted(HOOK_POINTS))
def test_named_hook_points_are_invokable(point: str):
    plugin = select_deploy_profile_plugin("jira")
    ctx: dict[str, Any] = {"ran": []}
    plugin.call(point, ctx)
    if point == "around":
        assert ctx["ran"] == ["jira"]
    else:
        assert ctx["ran"] == []


def test_golden_path_succeeds_with_no_optional_vendors_enabled():
    ctx = run_golden_path(enabled=())
    assert ctx["ok"] is True
    assert ctx["ran"] == []


def test_disabling_one_optional_vendor_does_not_fail_golden_path():
    enabled = [pid for pid in DEFAULT_DEPLOY_PROFILE_IDS if pid != "splunk"]
    ctx = run_golden_path(enabled=enabled)
    assert ctx["ok"] is True
    assert "splunk" not in ctx["ran"]
    assert set(ctx["ran"]) == set(enabled)


def test_tachyon_is_not_required_in_ci():
    plugin = TachyonDeployPlugin()
    assert plugin.plugin_id == PLUGIN_TACHYON
    assert plugin.required_in_ci is False
    assert plugin.optional is True
    ctx = run_golden_path()
    assert PLUGIN_TACHYON not in ctx["ran"]
    assert ctx["ok"] is True


def test_publish_verdict_on_warden_pr_gate_raises_second_verdict_error():
    plugin = select_deploy_profile_plugin("harness")
    warden_spec = HookSpec(name="pyforge.warden.pr_gate", owner="warden")
    with pytest.raises(SecondVerdictError):
        publish_verdict(warden_spec, plugin, {"verdict": "pass"})


def test_owner_matched_publish_on_steward_spec_is_allowed():
    plugin = select_deploy_profile_plugin("jira")
    assert publish_verdict(DEPLOY_PROFILE_HOOK_SPEC, plugin, {"ran": True}) == {"ran": True}


def test_deploy_profiles_module_never_calls_publish_verdict():
    tree = ast.parse(_PROFILES_SRC.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id == "publish_verdict":
                hits.append(f"Name:{node.lineno}")
            if isinstance(fn, ast.Attribute) and fn.attr == "publish_verdict":
                hits.append(f"Attribute:{node.lineno}")
    assert hits == []


def _golden_path_task_table() -> dict[str, Any]:
    data = tomllib.loads(_PIXI.read_text(encoding="utf-8"))
    feature = data["feature"]["pyforge-steward"]
    tasks = feature["tasks"]
    assert GOLDEN_PATH_PIXI_TASK in tasks, f"Golden Path Pixi task {GOLDEN_PATH_PIXI_TASK!r} missing"
    return tasks[GOLDEN_PATH_PIXI_TASK]


def test_golden_path_pixi_task_does_not_require_optional_vendors():
    task = _golden_path_task_table()
    blob = " ".join(str(task.get(key, "")) for key in ("cmd", "description", "depends-on")).lower()
    for token in OPTIONAL_VENDOR_TOKENS:
        assert token not in blob, f"Golden Path Pixi task must not require optional vendor {token!r}"
    cmd = str(task.get("cmd", ""))
    assert "pytest" in cmd
    assert "tachyon" not in cmd.lower()


def test_steward_feature_deps_do_not_require_optional_vendors():
    data = tomllib.loads(_PIXI.read_text(encoding="utf-8"))
    deps = data["feature"]["pyforge-steward"]["dependencies"]
    names = {str(name).lower() for name in deps}
    for token in OPTIONAL_VENDOR_TOKENS:
        assert not any(token in name for name in names), (
            f"steward feature deps must not require optional vendor {token!r}: {names}"
        )


def test_non_callable_backend_raises_plugin_error():
    plugin = select_deploy_profile_plugin("harness")
    with pytest.raises(PluginError, match="must be callable"):
        plugin.call("around", {"backends": {"harness": "not-callable"}})


def test_unknown_enabled_plugin_fails_closed():
    with pytest.raises(PluginError, match="unknown deploy-profile plugin"):
        run_golden_path(enabled=("not-a-vendor",))


def test_custom_registry_is_not_seeded_with_defaults():
    class OnlyAlt:
        hook_spec = DEPLOY_PROFILE_HOOK_SPEC_NAME
        owner = DEPLOY_PROFILE_OWNER
        plugin_id = "alt-cd"

        def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
            del point
            context.setdefault("ran", []).append(self.plugin_id)
            return context

    registry = PluginRegistry()
    registry.register(OnlyAlt())
    ctx = run_golden_path(enabled=("alt-cd",), registry=registry)
    assert ctx["ran"] == ["alt-cd"]
    assert ctx["ok"] is True


def test_injected_backend_runs_when_enabled():
    ran: list[str] = []

    def _backend(context: MutableMapping[str, Any]) -> None:
        del context
        ran.append("harness-sdk")

    ctx = run_golden_path(
        enabled=("harness",),
        context={"backends": {"harness": _backend}},
    )
    assert ran == ["harness-sdk"]
    assert ctx["ran"] == ["harness"]
