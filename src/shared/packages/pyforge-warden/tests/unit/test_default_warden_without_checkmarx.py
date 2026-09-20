"""Default Warden stays green without Checkmarx (Story 9.3).

Pins the CLI process: a registry with only default-bundle plugins and a
default ``warden scan`` (no ``WARDEN_OPTIONAL_SCANNERS``) must not treat
absence of a named optional plugin as a Warden failure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.core.hooks import PluginError, PluginRegistry

from pyforge.warden.cli import main
from pyforge.warden.engines import (
    CurrencyEngine,
    DeptryEngine,
    LicenseEngine,
    NullEngine,
    OsvEngine,
    engine_factories,
)
from pyforge.warden.interfaces import EngineResult
from pyforge.warden.scanner_plugins import (
    OPTIONAL_ABSENT_IS_NOT_FAILURE,
    OPTIONAL_SCANNER_IDS,
    _plugin_for_factory,
    select_scanner_plugins,
)


def _defaults_only_registry() -> PluginRegistry:
    """Plugin registry with only ``engine_factories()`` wrappers."""
    registry = PluginRegistry()
    for factory in engine_factories():
        registry.register(_plugin_for_factory(factory))
    present = {getattr(plugin, "scanner_id", plugin.owner) for plugin in registry.plugins}
    assert present.isdisjoint(OPTIONAL_SCANNER_IDS)
    return registry


def _install_defaults_only_registry(monkeypatch) -> PluginRegistry:
    registry = _defaults_only_registry()
    monkeypatch.delenv("WARDEN_OPTIONAL_SCANNERS", raising=False)
    monkeypatch.setattr(
        "pyforge.warden.scanner_plugins.scanner_plugin_registry",
        lambda: registry,
    )
    return registry


def _mentions_optional_absence(text: str) -> bool:
    lowered = text.lower()
    if any(
        marker in lowered
        for marker in (
            "optional scanner absent",
            "optional absent",
            "missing checkmarx",
            "checkmarx is missing",
            "checkmarx not installed",
            "no checkmarx",
        )
    ):
        return True
    return any(
        scanner_id in lowered and any(token in lowered for token in ("absent", "missing", "not installed", "not found"))
        for scanner_id in OPTIONAL_SCANNER_IDS
    )


def _optional_absence_errors(report: dict) -> list[dict]:
    hits: list[dict] = []
    for error in report.get("errors") or ():
        message = str(error.get("message", ""))
        if _mentions_optional_absence(message):
            hits.append(error)
    return hits


def test_default_scan_is_green_without_commercial_plugins(monkeypatch, tmp_path: Path, capsys):
    registry = _install_defaults_only_registry(monkeypatch)
    selected = select_scanner_plugins(registry=registry)
    ids = {getattr(plugin, "scanner_id", plugin.owner) for plugin in selected}
    assert ids.isdisjoint(OPTIONAL_SCANNER_IDS)

    rc = main(["scan", str(tmp_path), "--format", "json", "--allow-empty"])
    captured = capsys.readouterr()
    assert rc == 0
    report = json.loads(captured.out)
    assert _optional_absence_errors(report) == []
    assert report["status"]["value"] is not None


def test_absence_of_named_optional_is_not_a_warden_failure(monkeypatch, tmp_path: Path, capsys):
    registry = _install_defaults_only_registry(monkeypatch)
    assert OPTIONAL_ABSENT_IS_NOT_FAILURE is True
    try:
        selected = select_scanner_plugins(registry=registry)
    except PluginError as exc:
        pytest.fail(f"absence of a named optional plugin was treated as a Warden failure: {exc}")
    ids = {getattr(plugin, "scanner_id", plugin.owner) for plugin in selected}
    assert ids.isdisjoint(OPTIONAL_SCANNER_IDS)
    assert "checkmarx" not in ids

    rc = main(["scan", str(tmp_path), "--format", "json", "--allow-empty"])
    captured = capsys.readouterr()
    assert rc == 0
    report = json.loads(captured.out)
    absence_errors = _optional_absence_errors(report)
    assert absence_errors == [], (
        f"absence of a named optional plugin was treated as a Warden failure: {absence_errors!r}"
    )
    assert "PluginError" not in captured.err
    assert "Traceback" not in captured.err


def test_live_default_registry_scan_does_not_require_checkmarx(monkeypatch, tmp_path: Path, capsys):
    """Shipped in-tree registry still registers optional stubs; default
    scan must not require Checkmarx to be enabled or 'installed'."""
    monkeypatch.delenv("WARDEN_OPTIONAL_SCANNERS", raising=False)
    selected = select_scanner_plugins()
    ids = {getattr(plugin, "scanner_id", plugin.owner) for plugin in selected}
    assert ids.isdisjoint(OPTIONAL_SCANNER_IDS)

    rc = main(["scan", str(tmp_path), "--format", "json", "--allow-empty"])
    captured = capsys.readouterr()
    assert rc == 0
    report = json.loads(captured.out)
    assert _optional_absence_errors(report) == []
    assert "indeterminate:checkmarx:plugin" not in [finding["id"] for finding in report.get("findings") or ()]


def test_own_engines_may_still_fail_without_optional_absence_errors(monkeypatch, tmp_path: Path, capsys):
    _install_defaults_only_registry(monkeypatch)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\ndependencies = ["requests==2.31.0"]\n',
        encoding="utf-8",
    )

    def _empty_run(self, target, inventory):
        return EngineResult(findings=(), errors=(), coverage=(), axis=self.axis)

    def _fail_run(self, target, inventory):
        raise RuntimeError("forced osv failure for story 9.3")

    monkeypatch.setattr(NullEngine, "run", _empty_run)
    monkeypatch.setattr(DeptryEngine, "run", _empty_run)
    monkeypatch.setattr(LicenseEngine, "run", _empty_run)
    monkeypatch.setattr(CurrencyEngine, "run", _empty_run)
    monkeypatch.setattr(OsvEngine, "run", _fail_run)

    rc = main(["scan", str(tmp_path), "--format", "json"])
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert rc != 0
    assert report["status"]["value"] != "clean"
    assert _optional_absence_errors(report) == []
    messages = [str(error.get("message", "")) for error in report.get("errors") or ()]
    assert any("forced osv failure" in message for message in messages)
    assert not any(_mentions_optional_absence(message) for message in messages)
