"""Unit tests for ``fix_solver`` (Story 14.1 solver seam)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.warden.fix_solver import (
    FixTargetResolution,
    PixiVersionOutOfRangeError,
    _package_from_finding_id,
    _probe_pixi_toml_floor,
    accepting_solver,
    default_pixi_lock_solver,
    eligible_candidates,
    rejecting_solver,
    resolve_fix_target,
)

if TYPE_CHECKING:
    pass


def test_eligible_candidates_unspecified_and_invalid_versions():
    assert eligible_candidates("vuln:GHSA:x@unspecified", ("1.0.0",)) == ("1.0.0",)
    assert eligible_candidates("vuln:GHSA:x", ("1.0.0",)) == ("1.0.0",)
    assert eligible_candidates("vuln:GHSA:x@1.0.0", ("not-a-version", "1.1.0")) == ("1.1.0",)
    assert eligible_candidates("vuln:GHSA:x@1.0.0", ()) == ()


def test_resolve_fix_target_no_candidates():
    resolution = resolve_fix_target("vuln:GHSA:x@1.0.0", (), dry_run=False, scan_target=Path("."))
    assert resolution.target is None
    assert resolution.solver == "not-run"
    assert resolution.failure_detail is not None


def test_resolve_fix_target_missing_scan_target():
    resolution = resolve_fix_target(
        "vuln:GHSA:x@1.0.0",
        ("1.1.0",),
        dry_run=False,
        scan_target=None,
    )
    assert resolution.solver == "pixi-lock"
    assert resolution.failure_detail is not None


def test_resolve_fix_target_non_directory_scan_target(tmp_path: Path):
    file_path = tmp_path / "not-a-dir"
    file_path.write_text("x", encoding="utf-8")
    resolution = resolve_fix_target(
        "vuln:GHSA:x@1.0.0",
        ("1.1.0",),
        dry_run=False,
        scan_target=file_path,
    )
    assert resolution.target is None


def test_package_from_finding_id():
    assert _package_from_finding_id("vuln:GHSA-test:leftpad@1.2.0") == "leftpad"
    assert _package_from_finding_id("vuln:GHSA-test:leftpad") == "leftpad"
    assert _package_from_finding_id("short:id") == ""


def test_probe_pixi_toml_floor_double_and_single_quotes(tmp_path: Path):
    pixi = tmp_path / "pixi.toml"
    pixi.write_text('dependencies = { python = ">=3.12" }\n"leftpad" = "1.0.0"\n', encoding="utf-8")
    assert _probe_pixi_toml_floor(pixi, "leftpad", "2.0.0") is True
    assert ">=2.0.0" in pixi.read_text(encoding="utf-8")

    pixi.write_text("dependencies = { python = '>=3.12' }\nleftpad = '1.0.0'\n", encoding="utf-8")
    assert _probe_pixi_toml_floor(pixi, "leftpad", "3.0.0") is True


def test_probe_pixi_toml_floor_missing_file_or_package(tmp_path: Path):
    assert _probe_pixi_toml_floor(tmp_path / "missing.toml", "pkg", "1.0.0") is False
    pixi = tmp_path / "pixi.toml"
    pixi.write_text("[project]\n", encoding="utf-8")
    assert _probe_pixi_toml_floor(pixi, "missing-pkg", "1.0.0") is False


def test_stub_solvers():
    assert rejecting_solver(scan_target=Path("."), package="x", floor_version="1.0.0") == "rejected"
    assert accepting_solver(scan_target=Path("."), package="x", floor_version="1.0.0") == "accepted"


def test_fix_target_resolution_to_json_dict():
    payload = FixTargetResolution(
        target="1.0.0",
        candidates=("1.0.0",),
        attempts=(("1.0.0", "accepted"),),
        solver="pixi-lock",
    ).to_json_dict()
    assert payload["target"] == "1.0.0"
    assert payload["attempts"][0]["verdict"] == "accepted"


def test_default_pixi_lock_solver_accepts(monkeypatch, tmp_path: Path):
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "pixi.toml").write_text('"leftpad" = "1.0.0"\n', encoding="utf-8")

    monkeypatch.setattr(
        "pyforge.warden.fix_solver.run_pixi_lock",
        lambda *, cwd: (None, 0),
    )
    assert default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="2.0.0") == "accepted"


def test_default_pixi_lock_solver_rejects_probe_and_exit(monkeypatch, tmp_path: Path):
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "pixi.toml").write_text("[project]\n", encoding="utf-8")
    assert default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="2.0.0") == "rejected"

    (scan / "pixi.toml").write_text('"leftpad" = "1.0.0"\n', encoding="utf-8")
    monkeypatch.setattr(
        "pyforge.warden.fix_solver.run_pixi_lock",
        lambda *, cwd: (None, 1),
    )
    assert default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="2.0.0") == "rejected"


def test_default_pixi_lock_solver_raises_on_pixi_out_of_range(monkeypatch, tmp_path: Path):
    from pyforge.warden.models import ErrorKind, ErrorRecord

    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "pixi.toml").write_text('"leftpad" = "1.0.0"\n', encoding="utf-8")
    record = ErrorRecord(
        kind=ErrorKind.ENGINE_UNAVAILABLE,
        owner="pixi",
        message="pixi version outside range",
    )

    monkeypatch.setattr(
        "pyforge.warden.fix_solver.run_pixi_lock",
        lambda *, cwd: (record, None),
    )
    with pytest.raises(PixiVersionOutOfRangeError):
        default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="2.0.0")


def test_pixi_version_out_of_range_is_pyforge_error():
    assert issubclass(PixiVersionOutOfRangeError, PyforgeError)
