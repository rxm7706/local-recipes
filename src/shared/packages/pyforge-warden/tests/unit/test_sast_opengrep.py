"""Story 15.1 — opengrep optional SAST advisory lens."""

from __future__ import annotations

import json
import subprocess
import types
from pathlib import Path
from typing import Any

import pytest
from pyforge.core import flags as core_flags
from pyforge.core.hooks import PluginRegistry

from pyforge.warden.engines import OPENGREP_VERSION_RANGE, build_opengrep_scan_argv, run_opengrep_engine
from pyforge.warden.hooks import PR_GATE_SCAN, invoke_pr_gate
from pyforge.warden.sast import (
    OPENGREP_SCANNER_ID,
    SAST_OPENGREP_FLAG,
    OpengrepScanPlugin,
    bundled_sast_rules_dir,
    opengrep_selectable,
    parse_opengrep_json,
    run_opengrep_advisory,
)
from pyforge.warden.scanner_plugins import OPTIONAL_SCANNER_IDS, enabled_optional_from_environ, select_scanner_plugins

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "projects" / "opengrep_tripped"


def _bool_flag_entry(*, default_variant: str) -> dict[str, object]:
    return {
        "state": "ENABLED",
        "variants": {"on": True, "off": False},
        "defaultVariant": default_variant,
        "metadata": {
            "owner": "warden",
            "story": "15-1-opengrep-is-an-optional-sast-scanner-that-informs-never-publishes-the-verdict",
            "created": "2026-09-28",
            "on_everywhere": "",
            "cleanup_by": "",
        },
    }


def _flag_tree(tmp_path: Path, *, enabled: bool) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    variant = "on" if enabled else "off"
    path = tmp_path / "flags.json"
    path.write_text(
        json.dumps({"flags": {SAST_OPENGREP_FLAG: _bool_flag_entry(default_variant="off")}}),
        encoding="utf-8",
    )
    overlays = {
        "dev": {SAST_OPENGREP_FLAG: variant},
        "staging": {SAST_OPENGREP_FLAG: variant},
        "production": {SAST_OPENGREP_FLAG: "off"},
    }
    (tmp_path / core_flags.OVERLAYS_FILE_NAME).write_text(json.dumps(overlays), encoding="utf-8")
    return path


def test_opengrep_is_listed_as_optional_scanner_id() -> None:
    assert OPENGREP_SCANNER_ID in OPTIONAL_SCANNER_IDS


def test_parse_opengrep_json_maps_a_result_to_advisory_fields() -> None:
    raw = json.dumps(
        {
            "results": [
                {
                    "check_id": "planted-opengrep-match",
                    "path": "sample.py",
                    "start": {"line": 3},
                    "extra": {"severity": "WARNING"},
                }
            ]
        }
    )
    notes, error = parse_opengrep_json(raw)
    assert error is None
    assert len(notes) == 1
    note = notes[0]
    assert note.tool == "opengrep"
    assert note.rule_id == "planted-opengrep-match"
    assert note.path == "sample.py"
    assert note.line == 3
    assert note.severity == "WARNING"


def test_parse_opengrep_json_unparseable_returns_error_message() -> None:
    notes, error = parse_opengrep_json("{not-json")
    assert notes == ()
    assert error is not None


def test_build_opengrep_scan_argv_uses_local_rules_only(tmp_path: Path) -> None:
    rules = bundled_sast_rules_dir()
    argv = build_opengrep_scan_argv(
        binary="opengrep",
        rules_dir=rules,
        target=tmp_path,
        json_output="/tmp/out.json",
    )
    joined = " ".join(argv)
    assert "--config" in argv
    assert str(rules) in argv
    assert "http" not in joined
    assert "semgrep.dev" not in joined
    assert "auto" not in argv


def test_run_opengrep_advisory_absent_binary_is_silent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pyforge.warden.sast.shutil.which", lambda _name: None)
    assert run_opengrep_advisory(tmp_path) == ()


def test_run_opengrep_advisory_version_failure_becomes_advisory_note(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pyforge.warden.sast.shutil.which", lambda _name: "/bin/opengrep")

    def _fake_engine(**_kwargs: object) -> tuple[str | None, object, int | None]:
        from pyforge.warden.models import ErrorKind, ErrorRecord

        return (
            None,
            ErrorRecord(
                kind=ErrorKind.ENGINE_UNAVAILABLE,
                owner="opengrep",
                message=f"opengrep version 9.9.9 is outside tested range {OPENGREP_VERSION_RANGE!s}",
            ),
            None,
        )

    monkeypatch.setattr("pyforge.warden.sast.run_opengrep_engine", _fake_engine)
    notes = run_opengrep_advisory(tmp_path)
    assert len(notes) == 1
    assert "outside tested range" in notes[0].summary


def test_plugin_appends_advisory_note_when_enabled(monkeypatch, tmp_path: Path) -> None:
    tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert opengrep_selectable()

    def fake_runner(_target: Path, _rules: Path, json_path: Path) -> types.SimpleNamespace:
        json_path.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "check_id": "planted-opengrep-match",
                            "path": "sample.py",
                            "start": {"line": 1},
                            "extra": {"severity": "WARNING"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return types.SimpleNamespace(returncode=0)

    plugin = OpengrepScanPlugin(runner=fake_runner)
    context: dict[str, object] = {
        "enabled_optional": ("opengrep",),
        "target": tmp_path,
        "advisory_notes": [],
    }
    registry = PluginRegistry()
    registry.register(plugin)
    invoke_pr_gate(PR_GATE_SCAN, "around", context, registry=registry)
    notes = context["advisory_notes"]
    assert len(notes) == 1
    assert notes[0]["tool"] == "opengrep"
    assert notes[0]["rule_id"] == "planted-opengrep-match"


def test_plugin_flag_off_writes_no_note_even_when_enabled_in_env(monkeypatch, tmp_path: Path) -> None:
    tree = _flag_tree(tmp_path / "flags", enabled=False)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert not opengrep_selectable()

    plugin = OpengrepScanPlugin(
        runner=lambda *_args: types.SimpleNamespace(returncode=0),
    )
    context: dict[str, object] = {
        "enabled_optional": ("opengrep",),
        "target": tmp_path,
        "advisory_notes": [],
    }
    plugin.call("around", context)
    assert context["advisory_notes"] == []


def test_cli_filters_opengrep_when_flag_off(monkeypatch) -> None:
    from pyforge.warden import cli as cli_module

    monkeypatch.setenv("WARDEN_OPTIONAL_SCANNERS", "opengrep")
    monkeypatch.setattr(cli_module, "read_boolean", lambda _key, default=False: False)
    enabled = enabled_optional_from_environ()
    if "opengrep" in enabled and not cli_module.read_boolean(SAST_OPENGREP_FLAG, default=False):
        enabled = tuple(x for x in enabled if x != "opengrep")
    selected = select_scanner_plugins(enabled_optional=enabled)
    assert all(getattr(p, "scanner_id", "") != "opengrep" for p in selected)


def test_opengrep_engine_argv_capture(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if argv[:2] == ["opengrep", "--version"]:
            return subprocess.CompletedProcess(argv, 0, b"1.30.2\n", b"")
        captured["argv"] = list(argv)
        json_out = argv[argv.index("--json-output") + 1]
        Path(json_out).write_text('{"results": []}', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr("pyforge.warden.engines.subprocess.run", fake_run)
    text, error, _code = run_opengrep_engine(
        binary="opengrep",
        rules_dir=bundled_sast_rules_dir(),
        cwd=tmp_path,
    )
    assert error is None
    assert text is not None
    argv = captured["argv"]
    assert "http" not in " ".join(argv)
    assert str(bundled_sast_rules_dir()) in argv


@pytest.mark.parametrize("flag_on", [True, False])
def test_flag_states_do_not_change_default_scan_exit(monkeypatch, tmp_path: Path, flag_on: bool) -> None:
    """Given the same repo, enabled vs disabled optional opengrep must not move exit/status."""
    from pyforge.warden.cli import main as warden_main

    project = tmp_path / "proj"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="x"\nversion="0.0.0"\n', encoding="utf-8")
    (project / "module.py").write_text("x = 1\n", encoding="utf-8")

    tree = _flag_tree(tmp_path / "flags", enabled=flag_on)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    monkeypatch.delenv("WARDEN_OPTIONAL_SCANNERS", raising=False)

    def _deptry_ok(*_args: object, **_kwargs: object) -> tuple[str | None, object, int]:
        return ("[]", None, 0)

    def _osv_ok(*_args: object, **_kwargs: object) -> tuple[str | None, object, int]:
        return ('{"results": []}', None, 0)

    monkeypatch.setattr("pyforge.warden.engines._engine_env", _deptry_ok)
    monkeypatch.setattr("pyforge.warden.engines.run_opengrep_engine", lambda **_k: (None, None, None))

    baseline_code = warden_main(["scan", str(project)])
    monkeypatch.setenv("WARDEN_OPTIONAL_SCANNERS", "opengrep")
    with_flag_code = warden_main(["scan", str(project)])
    assert baseline_code == with_flag_code


def test_fixture_repo_trips_rule_with_injected_runner(tmp_path: Path) -> None:
    target = FIXTURE_ROOT

    def runner(_target: Path, _rules: Path, json_path: Path) -> types.SimpleNamespace:
        json_path.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "check_id": "planted-opengrep-match",
                            "path": "sample.py",
                            "start": {"line": 1},
                            "extra": {"severity": "WARNING"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return types.SimpleNamespace(returncode=1)

    notes = run_opengrep_advisory(target, runner=runner)
    assert any(n.rule_id == "planted-opengrep-match" for n in notes)
