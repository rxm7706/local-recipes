"""Story 18.1 — CAP-18 Kedro → FR-43 audit (collected by kedro-test).

Covers the intent-contract I/O matrix: complete method map, default plugin
load, around no-op, second-verdict, no atlas PR-gate job beside Warden.
Does not rebuild Kedro or require a live Kedro session for plugin ``call``.
"""

from __future__ import annotations

import ast
import inspect
import re
from importlib.metadata import entry_points
from pathlib import Path

import pytest
from kedro.framework.hooks import specs as kedro_hook_specs
from pyforge.core.hooks import (
    ENTRY_POINT_GROUP,
    DummyPlugin,
    HookSpec,
    PluginError,
    PluginRegistry,
    SecondVerdictError,
    publish_verdict,
)

from pyforge.atlas.admission import RunAdmissionHooks
from pyforge.atlas.cap18 import (
    AROUND_NA_REASON,
    ATLAS_HOOK_SPECS,
    ATLAS_OWNER,
    CATALOG_HOOK_SPEC,
    DEFAULT_PLUGIN_CLASSES,
    KEDRO_HOOK_MAP,
    NODE_HOOK_SPEC,
    PIPELINE_HOOK_SPEC,
    SETTINGS_HOOK_BACKENDS,
    CatalogTtlPlugin,
    NodeObservabilityPlugin,
    NodeValidationPlugin,
    PipelineAdmissionPlugin,
    PipelineObservabilityPlugin,
)
from pyforge.atlas.hooks import ProjectHooks
from pyforge.atlas.observability import AtlasObservabilityHooks
from pyforge.atlas.settings import HOOKS
from pyforge.atlas.validation import DataValidationHooks

MEMBER_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = MEMBER_DIR.parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
PIXI_TOML = REPO_ROOT / "pixi.toml"

# Atlas must not add a CI/pixi job that publishes pipeline PR pass/fail beside Warden.
_ATLAS_PR_GATE = re.compile(
    r"(atlas[-_].*(pr[-_]?gate|quality[-_]?gate|pr[-_]?verdict))"
    r"|(pipeline[-_]?pr[-_]?gate)"
    r"|(pyforge[-_]atlas[-_].*verdict)",
    re.IGNORECASE,
)


def _kedro_spec_classes() -> dict[str, type]:
    found: dict[str, type] = {}
    for name, obj in inspect.getmembers(kedro_hook_specs, inspect.isclass):
        if name.endswith("Specs") and obj.__module__ == kedro_hook_specs.__name__:
            found[name] = obj
    return found


def _kedro_spec_methods() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for spec_name, cls in _kedro_spec_classes().items():
        for name, _fn in inspect.getmembers(cls, inspect.isfunction):
            if name.startswith("_"):
                continue
            found.add((spec_name, name))
    return found


def _atlas_hook_impl_methods() -> set[tuple[str, str]]:
    """``(ClassName, method)`` for every ``@hook_impl`` in the atlas package."""
    pkg = MEMBER_DIR / "src" / "pyforge" / "atlas"
    found: set[tuple[str, str]] = set()
    for path in pkg.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                if any(
                    (isinstance(d, ast.Name) and d.id == "hook_impl")
                    or (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "hook_impl")
                    for d in item.decorator_list
                ):
                    found.add((node.name, item.name))
    return found


def test_every_kedro_spec_method_is_mapped_or_na_with_reason():
    mapped = {(row.kedro_spec, row.kedro_method) for row in KEDRO_HOOK_MAP}
    live = _kedro_spec_methods()
    missing = live - mapped
    extra = mapped - live
    assert not missing, f"KEDRO_HOOK_MAP missing Kedro spec methods: {sorted(missing)}"
    assert not extra, f"KEDRO_HOOK_MAP has unknown Kedro spec methods: {sorted(extra)}"
    bad_na = [
        f"{row.kedro_spec}.{row.kedro_method}"
        for row in KEDRO_HOOK_MAP
        if not row.mapped() and not (row.na_reason and row.na_reason.strip())
    ]
    bad_mapped = [
        f"{row.kedro_spec}.{row.kedro_method}"
        for row in KEDRO_HOOK_MAP
        if row.mapped() and (row.fr43_point not in {"before", "after"} or not row.hook_spec or not row.backends)
    ]
    assert not bad_na, f"N/A rows missing a reason: {bad_na}"
    assert not bad_mapped, f"mapped rows incomplete: {bad_mapped}"
    assert _kedro_spec_classes(), "kedro.framework.hooks.specs exported no *Specs classes"


def test_mapped_methods_match_live_settings_hooks_backends():
    live_types = tuple(type(hook) for hook in HOOKS)
    assert live_types == SETTINGS_HOOK_BACKENDS
    assert live_types == (
        ProjectHooks,
        AtlasObservabilityHooks,
        DataValidationHooks,
        RunAdmissionHooks,
    )
    for row in KEDRO_HOOK_MAP:
        if not row.mapped():
            continue
        for backend in row.backends:
            assert backend in live_types, (
                f"{row.kedro_method} maps to {backend.__name__} which is not in settings.HOOKS"
            )


def test_every_atlas_hook_impl_appears_on_the_map():
    impls = _atlas_hook_impl_methods()
    assert impls, "no @hook_impl methods found under pyforge.atlas"
    listed: set[tuple[str, str]] = set()
    for row in KEDRO_HOOK_MAP:
        for backend in row.backends:
            listed.add((backend.__name__, row.kedro_method))
    missing = impls - listed
    extra_backends = listed - impls
    assert not missing, f"@hook_impl not on KEDRO_HOOK_MAP: {sorted(missing)}"
    assert not extra_backends, f"KEDRO_HOOK_MAP backends claim impls that are absent: {sorted(extra_backends)}"
    for row in KEDRO_HOOK_MAP:
        if not row.backends:
            continue
        for backend in row.backends:
            assert hasattr(backend, row.kedro_method), (
                f"{backend.__name__} missing {row.kedro_method} (N/A rows must still name live methods)"
            )


def test_around_is_explicitly_na():
    assert "around" not in {row.fr43_point for row in KEDRO_HOOK_MAP}
    assert "rebuild" in AROUND_NA_REASON.lower() or "Kedro" in AROUND_NA_REASON


def test_default_plugins_load_from_entry_points_and_invoke_before_after():
    discovered = {ep.name: ep.value for ep in entry_points(group=ENTRY_POINT_GROUP)}
    for name, target in (
        ("atlas-catalog-ttl", "pyforge.atlas.cap18:CatalogTtlPlugin"),
        ("atlas-pipeline-observability", "pyforge.atlas.cap18:PipelineObservabilityPlugin"),
        ("atlas-node-observability", "pyforge.atlas.cap18:NodeObservabilityPlugin"),
        ("atlas-node-validation", "pyforge.atlas.cap18:NodeValidationPlugin"),
        ("atlas-pipeline-admission", "pyforge.atlas.cap18:PipelineAdmissionPlugin"),
    ):
        assert discovered.get(name) == target, discovered

    registry = PluginRegistry()
    registry.load_entry_points()
    dummy = next(p for p in registry.plugins if isinstance(p, DummyPlugin))
    atlas_plugins = [p for p in registry.plugins if p.owner == ATLAS_OWNER]
    backend_types = {type(p.backend) for p in atlas_plugins}
    assert backend_types == set(SETTINGS_HOOK_BACKENDS)
    allowed_specs = {spec.name for spec in ATLAS_HOOK_SPECS}
    assert {p.hook_spec for p in atlas_plugins} == allowed_specs
    assert all(p.owner == ATLAS_OWNER for p in atlas_plugins)

    dummy_calls_before = list(dummy.calls)
    for spec in ATLAS_HOOK_SPECS:
        registry.invoke("before", {}, spec_name=spec.name)
        registry.invoke("after", {}, spec_name=spec.name)
    assert dummy.calls == dummy_calls_before

    with pytest.raises(PluginError, match="unknown hook point"):
        registry.invoke("during", {}, spec_name=CATALOG_HOOK_SPEC.name)


def test_around_is_a_noop_and_may_call_context_next():
    plugin = CatalogTtlPlugin()
    registry = PluginRegistry()
    registry.register(plugin)
    seen: list[str] = []

    def _next(context: dict) -> str:
        seen.append("next")
        return "continued"

    result = registry.invoke(
        "around",
        {"next": _next},
        spec_name=CATALOG_HOOK_SPEC.name,
    )
    assert seen == ["next"]
    assert result == ["continued"]
    assert registry.invoke("around", {}, spec_name=CATALOG_HOOK_SPEC.name) == [{}]


def test_second_verdict_raises_for_warden_owned_spec_and_allows_owner_matched():
    plugin = CatalogTtlPlugin()
    warden_spec = HookSpec(name="pyforge.warden.pr-gate", owner="warden")
    with pytest.raises(SecondVerdictError):
        publish_verdict(warden_spec, plugin, "fail")
    assert publish_verdict(CATALOG_HOOK_SPEC, plugin, "ok") == "ok"
    foreign_atlas = HookSpec(name=PIPELINE_HOOK_SPEC.name, owner=ATLAS_OWNER)
    with pytest.raises(SecondVerdictError):
        publish_verdict(foreign_atlas, plugin, "stolen")


def test_observability_uses_two_plugins_for_one_backend_class():
    pipe = PipelineObservabilityPlugin()
    node = NodeObservabilityPlugin()
    assert type(pipe.backend) is AtlasObservabilityHooks
    assert type(node.backend) is AtlasObservabilityHooks
    assert pipe.hook_spec == PIPELINE_HOOK_SPEC.name
    assert node.hook_spec == NODE_HOOK_SPEC.name
    assert pipe.hook_spec != node.hook_spec


def test_default_plugin_classes_wrap_the_four_backends():
    wrapped = {cls.backend_class for cls in DEFAULT_PLUGIN_CLASSES}
    assert wrapped == set(SETTINGS_HOOK_BACKENDS)
    assert CatalogTtlPlugin.backend_class is ProjectHooks
    assert NodeValidationPlugin.backend_class is DataValidationHooks
    assert PipelineAdmissionPlugin.backend_class is RunAdmissionHooks


def _pixi_atlas_task_names(text: str) -> list[str]:
    return re.findall(
        r"^\[feature\.pyforge-atlas\.tasks\.([^\]]+)\]",
        text,
        flags=re.MULTILINE,
    )


def test_no_atlas_job_publishes_a_pr_gate_beside_warden():
    assert WORKFLOWS_DIR.is_dir(), WORKFLOWS_DIR
    hits: list[str] = []
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml")):
        if _ATLAS_PR_GATE.search(path.name):
            hits.append(f"workflow filename {path.name}")
            continue
        text = path.read_text(encoding="utf-8")
        for match in _ATLAS_PR_GATE.finditer(text):
            hits.append(f"{path.name}: {match.group(0)}")
    pixi = PIXI_TOML.read_text(encoding="utf-8")
    for name in _pixi_atlas_task_names(pixi):
        if _ATLAS_PR_GATE.search(name):
            hits.append(f"pixi task {name}")
    assert not hits, "atlas must not publish a pipeline PR pass/fail beside Warden: " + "; ".join(hits)
