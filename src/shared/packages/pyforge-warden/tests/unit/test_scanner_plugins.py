"""Unit tests for ``pyforge.warden.scanner_plugins`` (Story 9.2).

Covers the intent-contract I/O matrix: default bundle, optional not
required, enable optional, findings ≠ verdict, scan success ≠ gate.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import pytest
from pyforge.core.hooks import ENTRY_POINT_GROUP, PluginError, PluginRegistry, publish_verdict

from pyforge.warden.engines import DeptryEngine, engine_factories, registered_engines
from pyforge.warden.hooks import (
    PR_GATE_SCAN,
    PR_GATE_VERDICT,
    SecondVerdictError,
    invoke_pr_gate,
    publish_pr_gate_verdict,
)
from pyforge.warden.scanner_plugins import (
    DEFAULT_SCAN_PLUGINS,
    OPTIONAL_ABSENT_IS_NOT_FAILURE,
    OPTIONAL_SCANNER_IDS,
    CheckmarxScanPlugin,
    default_engine_factories,
    enabled_optional_from_environ,
    findings_from_plugin_context,
    merge_plugin_findings,
    scanner_plugin_registry,
    select_scanner_plugins,
    stub_finding_dict,
)


def test_default_bundle_wraps_registered_engine_factories():
    selected = select_scanner_plugins()
    assert all(plugin.is_default for plugin in selected)
    assert all(plugin.owner == "warden" for plugin in selected)
    assert all(plugin.hook_spec == PR_GATE_SCAN.name for plugin in selected)
    assert default_engine_factories(selected) == engine_factories()
    assert tuple(cls.factory for cls in DEFAULT_SCAN_PLUGINS) == engine_factories()
    names = {type(engine).__name__ for engine in registered_engines()}
    assert names >= {
        "NullEngine",
        "DeptryEngine",
        "OsvEngine",
        "LicenseEngine",
        "CurrencyEngine",
    }
    assert any(plugin.factory is DeptryEngine for plugin in selected)


def test_optional_scanners_are_omitted_when_not_enabled():
    selected = select_scanner_plugins()
    ids = {getattr(plugin, "scanner_id", plugin.owner) for plugin in selected}
    assert ids.isdisjoint(OPTIONAL_SCANNER_IDS)
    assert OPTIONAL_ABSENT_IS_NOT_FAILURE is True


def test_enabling_checkmarx_adds_plugin_findings():
    default_ctx: dict[str, Any] = {
        "plugin_findings": [],
        "enabled_optional": (),
    }
    enabled_ctx: dict[str, Any] = {
        "plugin_findings": [],
        "enabled_optional": ("checkmarx",),
    }
    selected = select_scanner_plugins(enabled_optional=("checkmarx",))
    registry = PluginRegistry()
    for plugin in selected:
        registry.register(plugin)
    invoke_pr_gate(PR_GATE_SCAN, "around", default_ctx, registry=registry)
    invoke_pr_gate(PR_GATE_SCAN, "around", enabled_ctx, registry=registry)
    assert default_ctx["plugin_findings"] == []
    assert enabled_ctx["plugin_findings"] == [stub_finding_dict("checkmarx")]
    extra = findings_from_plugin_context(enabled_ctx)
    merged = merge_plugin_findings((), extra)
    assert len(merged) > 0
    assert merged[0].id == "indeterminate:checkmarx:plugin"


def test_unknown_optional_id_raises_plugin_error():
    with pytest.raises(PluginError, match="unknown optional scanner id"):
        select_scanner_plugins(enabled_optional=("not-a-scanner",))


def test_missing_enabled_optional_is_omitted_not_an_error():
    registry = PluginRegistry()
    for plugin in scanner_plugin_registry().plugins:
        if getattr(plugin, "scanner_id", None) == "checkmarx":
            continue
        registry.register(plugin)
    selected = select_scanner_plugins(enabled_optional=("checkmarx",), registry=registry)
    ids = {getattr(plugin, "scanner_id", plugin.owner) for plugin in selected}
    assert "checkmarx" not in ids
    assert all(getattr(plugin, "is_default", False) for plugin in selected)


def test_optional_plugin_cannot_publish_pr_gate_verdict():
    plugin = CheckmarxScanPlugin()
    with pytest.raises(SecondVerdictError):
        publish_verdict(PR_GATE_VERDICT, plugin, "stolen")
    assert publish_pr_gate_verdict("ok") == "ok"


def test_optional_around_success_is_not_a_competing_pr_gate():
    plugin = CheckmarxScanPlugin()
    context: MutableMapping[str, Any] = {
        "plugin_findings": [],
        "enabled_optional": ("checkmarx",),
    }
    result = plugin.call("around", context)
    assert result is context
    assert context["plugin_findings"]
    assert publish_pr_gate_verdict("clean") == "clean"


def test_enabled_optional_from_environ_parses_comma_separated_ids():
    assert enabled_optional_from_environ({}) == ()
    assert enabled_optional_from_environ({"WARDEN_OPTIONAL_SCANNERS": "checkmarx, sonar"}) == ("checkmarx", "sonar")


def test_coerce_plugin_finding_missing_keys_is_plugin_error():
    from pyforge.warden.scanner_plugins import coerce_plugin_finding

    with pytest.raises(PluginError, match="plugin finding"):
        coerce_plugin_finding({"axis": "ingestion"})


def test_run_scan_with_checkmarx_enabled_emits_plugin_finding(monkeypatch, tmp_path, capsys):
    import json

    from pyforge.warden.cli import main

    monkeypatch.setenv("WARDEN_OPTIONAL_SCANNERS", "checkmarx")
    rc = main(["scan", str(tmp_path), "--format", "json", "--allow-empty"])
    captured = capsys.readouterr()
    assert rc == 0
    report = json.loads(captured.out)
    ids = [finding["id"] for finding in report["findings"]]
    assert "indeterminate:checkmarx:plugin" in ids
    assert report["status"]["value"] is not None


def test_run_scan_unknown_optional_id_is_typed_config_error(monkeypatch, tmp_path, capsys):
    import json

    from pyforge.warden.cli import main

    monkeypatch.setenv("WARDEN_OPTIONAL_SCANNERS", "not-a-scanner")
    rc = main(["scan", str(tmp_path), "--format", "json", "--allow-empty"])
    captured = capsys.readouterr()
    assert rc != 0
    report = json.loads(captured.out)
    messages = [error["message"] for error in report["errors"]]
    assert any("unknown optional scanner id" in message for message in messages)
    assert "Traceback" not in captured.err


def test_cli_does_not_load_the_shared_entry_point_group():
    from pathlib import Path

    import pyforge.warden.cli as cli

    source = Path(cli.__file__).read_text(encoding="utf-8")
    assert "load_entry_points(" not in source


def test_pyproject_declares_default_and_optional_plugins_on_core_hooks():
    import tomllib
    from pathlib import Path

    import pyforge.warden

    package_file = pyforge.warden.__file__
    assert package_file is not None
    package_dir = Path(package_file).resolve().parent
    pyproject = None
    for candidate in (package_dir, *package_dir.parents):
        path = candidate / "pyproject.toml"
        if path.is_file() and 'name = "pyforge-warden"' in path.read_text(encoding="utf-8"):
            pyproject = path
            break
    assert pyproject is not None
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    group = data["project"]["entry-points"][ENTRY_POINT_GROUP]
    assert "pyforge.warden.hooks" not in data["project"]["entry-points"]
    assert group["warden-null"] == "pyforge.warden.scanner_plugins:NullScanPlugin"
    assert group["warden-checkmarx"] == ("pyforge.warden.scanner_plugins:CheckmarxScanPlugin")
    assert group["warden-profile-local"] == ("pyforge.warden.scanner_plugins:ProfileLocalScanPlugin")
