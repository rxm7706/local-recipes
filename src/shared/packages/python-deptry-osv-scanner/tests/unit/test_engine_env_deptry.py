"""Unit tests — the ``_engine_env`` subprocess-normalization seam + the
``DeptryEngine`` runner (Story 1.3), exercised with INJECTED FAKES only.

``subprocess.run`` is monkeypatched: no real deptry, no real network, no real
sleep. The seam's load-bearing invariants (argv list, temp-file output in
system temp, ``NO_COLOR=1``, ``stdin=DEVNULL``, cleanup, typed errors for
timeout / unavailable / undecodable) are all proven against fakes.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import types
from pathlib import Path

import pytest

from python_deptry_osv_scanner.engines import (
    DEPTRY_TIMEOUT_SECONDS,
    DeptryEngine,
    _engine_env,
)
from python_deptry_osv_scanner.inventory import ResolvedInventory, merge_components
from python_deptry_osv_scanner.models import (
    AXIS_HYGIENE,
    ErrorKind,
    ScannedManifest,
)

MANIFEST = ScannedManifest(path="pyproject.toml", kind="pyproject.toml")


def DEPTRY_ARGV(output_path: str) -> list[str]:
    return ["deptry", ".", "-o", output_path, "--no-ansi"]


def make_inventory(*components) -> ResolvedInventory:
    return ResolvedInventory(
        components=merge_components(components),
        resolved_scan_set=(MANIFEST,),
    )


def _fake_run_writing(content, captured: dict, *, returncode: int = 1):
    """A ``subprocess.run`` stand-in that writes ``content`` (str or bytes) to
    the ``-o`` path and records the call."""

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        out_path = argv[argv.index("-o") + 1]
        captured["out_path"] = out_path
        if isinstance(content, bytes):
            Path(out_path).write_bytes(content)
        else:
            Path(out_path).write_text(content, encoding="utf-8")
        return types.SimpleNamespace(returncode=returncode, stdout=b"", stderr=b"")

    return fake_run


# --- _engine_env normalization invariants ------------------------------------


def test_engine_env_uses_argv_list_temp_file_no_color_and_devnull(
    monkeypatch, tmp_path
):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    text, error = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)

    assert error is None
    assert text == "[]"
    argv = captured["argv"]
    assert isinstance(argv, list)
    assert argv[0] == "deptry"
    assert argv[1] == "."
    assert "--no-ansi" in argv
    assert "-o" in argv
    kwargs = captured["kwargs"]
    # argv-only: never a shell.
    assert kwargs.get("shell", False) is False
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["env"]["NO_COLOR"] == "1"
    assert kwargs["cwd"] == str(tmp_path)
    # exit code is content: check=False (or absent), never raising on non-zero.
    assert kwargs.get("check", False) is False


def test_engine_env_output_file_is_in_system_temp_not_the_scanned_tree(
    monkeypatch, tmp_path
):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)

    out_path = Path(captured["out_path"])
    assert out_path.parent == Path(tempfile.gettempdir())
    # Never inside the scanned tree (NFR-S4).
    assert tmp_path not in out_path.parents


def test_engine_env_cleans_up_the_temp_file_on_success(monkeypatch, tmp_path):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert not os.path.exists(captured["out_path"])


def test_engine_env_passes_the_configured_timeout(monkeypatch, tmp_path):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert captured["kwargs"]["timeout"] == DEPTRY_TIMEOUT_SECONDS


# --- typed failure paths (injected, never a real sleep/binary) ---------------


def test_engine_env_timeout_is_a_typed_engine_timeout(monkeypatch, tmp_path):
    captured: dict = {}

    def fake_run(argv, **kwargs):
        captured["out_path"] = argv[argv.index("-o") + 1]
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)
    text, error = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert text is None
    assert error is not None
    assert error.kind is ErrorKind.ENGINE_TIMEOUT
    assert error.owner == "deptry"
    # cleaned up even on the failure path.
    assert not os.path.exists(captured["out_path"])


def test_engine_env_missing_binary_is_engine_unavailable(monkeypatch, tmp_path):
    captured: dict = {}

    def fake_run(argv, **kwargs):
        captured["out_path"] = argv[argv.index("-o") + 1]
        raise FileNotFoundError("deptry")

    monkeypatch.setattr(subprocess, "run", fake_run)
    text, error = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert text is None
    assert error.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert error.owner == "deptry"
    assert not os.path.exists(captured["out_path"])


def test_engine_env_vanished_cwd_is_not_misreported_as_missing_binary(
    monkeypatch, tmp_path
):
    """subprocess raises FileNotFoundError for BOTH a missing binary AND a
    missing cwd (failed pre-exec chdir). A target dir that vanished after
    discovery (TOCTOU) must report engine-execution-failed, NOT
    engine-unavailable ('binary not found on PATH') — the seam Story 1.5's
    osv runner reuses. Follow-up Opus review, 2026-07-14."""
    gone = tmp_path / "vanished"  # never created

    def fake_run(argv, **kwargs):
        raise FileNotFoundError(gone)

    monkeypatch.setattr(subprocess, "run", fake_run)
    text, error = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=gone)
    assert text is None
    assert error.kind is ErrorKind.ENGINE_EXECUTION_FAILED
    assert "not an existing directory" in error.message
    assert "not found on PATH" not in error.message


def test_engine_env_undecodable_output_is_output_unparseable(
    monkeypatch, tmp_path
):
    captured: dict = {}
    # Invalid UTF-8 bytes written to the machine-output file.
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing(b"\xff\xfe\x00garbage", captured)
    )
    text, error = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert text is None
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE
    assert not os.path.exists(captured["out_path"])


# --- DeptryEngine wiring on top of _engine_env -------------------------------


def test_deptry_engine_maps_valid_output_to_findings_and_coverage(
    monkeypatch, tmp_path, component_factory
):
    captured: dict = {}
    record = {
        "error": {"code": "DEP001", "message": "'absent' imported but missing"},
        "module": "absent",
        "location": {"file": "pkg/__init__.py", "line": 1, "column": 8},
    }
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing(json.dumps([record]), captured)
    )
    inventory = make_inventory(
        component_factory(name="requests", version="2.31.0"),
        component_factory(name="packaging", version="24.0"),
    )
    result = DeptryEngine().run(tmp_path, inventory)

    assert [f.id for f in result.findings] == ["hygiene:DEP001:absent"]
    assert result.findings[0].axis == AXIS_HYGIENE
    assert result.errors == ()
    (coverage,) = result.coverage
    assert coverage.axis == AXIS_HYGIENE
    assert coverage.deps_assessed == inventory.count == 2


def test_deptry_engine_ignores_the_exit_code(monkeypatch, tmp_path):
    """deptry exits 1 when issues are found; a clean ``[]`` with returncode 1
    is still clean (exit code is content, never the gate)."""
    captured: dict = {}
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing("[]", captured, returncode=1)
    )
    result = DeptryEngine().run(tmp_path, make_inventory())
    assert result.findings == ()
    assert result.errors == ()
    assert len(result.coverage) == 1  # a coverage claim on a successful run


def test_deptry_engine_unavailable_binary_yields_typed_error_no_coverage(
    monkeypatch, tmp_path
):
    def fake_run(argv, **kwargs):
        raise FileNotFoundError("deptry")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DeptryEngine().run(tmp_path, make_inventory())
    assert result.findings == ()
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert result.coverage == ()  # no coverage claim when nothing was assessed


def test_deptry_engine_timeout_yields_typed_error(monkeypatch, tmp_path):
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DeptryEngine().run(tmp_path, make_inventory())
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_TIMEOUT
    assert result.coverage == ()


def test_deptry_engine_non_array_output_is_output_unparseable(
    monkeypatch, tmp_path
):
    captured: dict = {}
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing(json.dumps({"not": "array"}), captured)
    )
    result = DeptryEngine().run(tmp_path, make_inventory())
    assert result.findings == ()
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE
    assert result.coverage == ()


def test_deptry_engine_malformed_record_is_counted_and_reported(
    monkeypatch, tmp_path, component_factory
):
    """A structurally-broken record inside a valid array is surfaced as an
    engine-output-unrecognized error (never dropped) while valid records
    still become findings."""
    captured: dict = {}
    payload = [
        {"error": {"code": "DEP002", "message": "unused"}, "module": "requests"},
        {"module": "no-code"},  # malformed
    ]
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing(json.dumps(payload), captured)
    )
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    result = DeptryEngine().run(tmp_path, inventory)
    assert [f.id for f in result.findings] == ["hygiene:DEP002:requests"]
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNRECOGNIZED
