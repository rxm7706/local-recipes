"""Story 16.1: Marp / PPTX / ``.dc.html`` as default deck-export plugins.

Covers the spec I/O matrix: default plugins on ``pyforge.core.hooks``, a
fourth format on the same spec (no parallel group), ``SecondVerdictError``
for a Warden PR-gate publish, and export success as a station result --
never a quality-gate verdict. Injected ``backends`` keep this suite off
marp / Chrome / pixi.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from importlib.metadata import entry_points
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

from pyforge.herald.exporters import (
    DECK_EXPORT_HOOK_SPEC,
    DECK_EXPORT_HOOK_SPEC_NAME,
    DECK_EXPORT_OWNER,
    DEFAULT_EXPORT_FORMATS,
    FORMAT_DC_HTML,
    FORMAT_MARP,
    FORMAT_PPTX,
    DcHtmlExportPlugin,
    MarpExportPlugin,
    PptxExportPlugin,
    export_via_hooks,
    register_default_export_plugins,
)

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _registry_with_defaults() -> PluginRegistry:
    registry = PluginRegistry()
    register_default_export_plugins(registry)
    return registry


def _recording_backends() -> tuple[dict[str, list[str]], dict[str, Any]]:
    ran: dict[str, list[str]] = {"called": []}

    def _backend_for(format_id: str):
        def _backend(context: MutableMapping[str, Any]) -> None:
            del context
            ran["called"].append(format_id)

        return _backend

    backends = {
        FORMAT_MARP: _backend_for(FORMAT_MARP),
        FORMAT_PPTX: _backend_for(FORMAT_PPTX),
        FORMAT_DC_HTML: _backend_for(FORMAT_DC_HTML),
    }
    return ran, backends


def test_default_plugins_register_the_three_format_ids():
    registry = _registry_with_defaults()
    ids = sorted(
        getattr(plugin, "format_id") for plugin in registry.plugins if plugin.hook_spec == DECK_EXPORT_HOOK_SPEC_NAME
    )
    assert ids == sorted(DEFAULT_EXPORT_FORMATS)
    assert all(plugin.owner == "herald" for plugin in registry.plugins)


def test_around_for_one_format_runs_only_the_matching_plugin():
    ran, backends = _recording_backends()
    context: dict[str, Any] = {
        "format": FORMAT_MARP,
        "backends": backends,
        "exported": [],
    }
    _registry_with_defaults().invoke("around", context, spec_name=DECK_EXPORT_HOOK_SPEC_NAME)
    assert ran["called"] == [FORMAT_MARP]
    assert context["exported"] == [FORMAT_MARP]


@pytest.mark.parametrize("format_id", DEFAULT_EXPORT_FORMATS)
def test_each_shipped_format_is_invokable(format_id: str):
    ran, backends = _recording_backends()
    exported = export_via_hooks(
        format_id,
        {"backends": backends, "exported": []},
        registry=_registry_with_defaults(),
    )
    assert ran["called"] == [format_id]
    assert exported == [format_id]


def test_unknown_format_yields_empty_exported_and_no_error():
    ran, backends = _recording_backends()
    exported = export_via_hooks(
        "pdf",
        {"backends": backends, "exported": []},
        registry=_registry_with_defaults(),
    )
    assert ran["called"] == []
    assert exported == []


def test_star_format_runs_all_three_defaults():
    ran, backends = _recording_backends()
    exported = export_via_hooks(
        "*",
        {"backends": backends, "exported": []},
        registry=_registry_with_defaults(),
    )
    assert ran["called"] == list(DEFAULT_EXPORT_FORMATS)
    assert exported == list(DEFAULT_EXPORT_FORMATS)


def test_fourth_plugin_on_the_same_spec_runs_without_a_new_group():
    ran, backends = _recording_backends()
    extra_ran: list[str] = []

    class PdfExportPlugin:
        hook_spec = DECK_EXPORT_HOOK_SPEC_NAME
        owner = "herald"
        format_id = "pdf"

        def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
            if point != "around":
                return context
            if context.get("format") not in (None, "*", "pdf"):
                return context
            extra_ran.append("pdf")
            context.setdefault("exported", []).append("pdf")
            return context

    registry = _registry_with_defaults()
    registry.register(PdfExportPlugin())
    exported = export_via_hooks(
        "pdf",
        {"backends": backends, "exported": []},
        registry=registry,
    )
    assert extra_ran == ["pdf"]
    assert exported == ["pdf"]
    assert ran["called"] == []


def test_pyproject_declares_defaults_on_the_canonical_group_only():
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert '[project.entry-points."pyforge.core.hooks"]' in text
    assert "pyforge.herald.exporters:MarpExportPlugin" in text
    assert "pyforge.herald.exporters:PptxExportPlugin" in text
    assert "pyforge.herald.exporters:DcHtmlExportPlugin" in text
    assert "pyforge.herald.hooks" not in text


def test_installed_entry_points_include_the_three_defaults():
    values = {ep.value for ep in entry_points(group=ENTRY_POINT_GROUP)}
    assert "pyforge.herald.exporters:MarpExportPlugin" in values
    assert "pyforge.herald.exporters:PptxExportPlugin" in values
    assert "pyforge.herald.exporters:DcHtmlExportPlugin" in values


def test_publish_verdict_on_a_warden_pr_gate_raises_second_verdict_error():
    plugin = MarpExportPlugin()
    warden_gate = HookSpec(name="pyforge.warden.pr_gate", owner="warden")
    with pytest.raises(SecondVerdictError):
        publish_verdict(warden_gate, plugin, {"gate": "pass"})


def test_owner_matched_publish_on_the_export_spec_is_allowed():
    plugin = PptxExportPlugin()
    result = publish_verdict(DECK_EXPORT_HOOK_SPEC, plugin, {"exported": [FORMAT_PPTX]})
    assert result == {"exported": [FORMAT_PPTX]}


def test_successful_marp_around_records_export_not_a_warden_verdict():
    ran, backends = _recording_backends()
    context: dict[str, Any] = {
        "format": FORMAT_MARP,
        "backends": backends,
        "exported": [],
    }
    _registry_with_defaults().invoke("around", context, spec_name=DECK_EXPORT_HOOK_SPEC_NAME)
    assert context["exported"] == [FORMAT_MARP]
    assert ran["called"] == [FORMAT_MARP]
    assert "verdict" not in context
    assert "warden" not in context


def test_default_backend_without_slug_does_not_need_in_tree_exporters():
    exported = export_via_hooks(FORMAT_DC_HTML, {"exported": []})
    assert exported == [FORMAT_DC_HTML]


def test_slug_and_repo_root_do_not_spawn_pixi(monkeypatch):
    from pyforge.herald import deck_pipeline

    def _boom(*_args, **_kwargs):
        raise AssertionError("PixiDeckExporter must not run from the default plugin")

    monkeypatch.setattr(deck_pipeline.PixiDeckExporter, "export", _boom)
    exported = export_via_hooks(
        FORMAT_MARP,
        {"exported": [], "slug": "pyforge-herald", "repo_root": Path(".")},
    )
    assert exported == [FORMAT_MARP]


def test_non_callable_injected_backend_raises_plugin_error():
    with pytest.raises(PluginError, match="must be callable"):
        export_via_hooks(
            FORMAT_MARP,
            {"exported": [], "backends": {FORMAT_MARP: "not-a-callable"}},
        )


def test_plugin_classes_are_distinct_format_handlers():
    assert MarpExportPlugin.format_id == FORMAT_MARP
    assert PptxExportPlugin.format_id == FORMAT_PPTX
    assert DcHtmlExportPlugin.format_id == FORMAT_DC_HTML
    assert MarpExportPlugin.hook_spec == DECK_EXPORT_HOOK_SPEC_NAME
    assert PptxExportPlugin.owner == DECK_EXPORT_OWNER
