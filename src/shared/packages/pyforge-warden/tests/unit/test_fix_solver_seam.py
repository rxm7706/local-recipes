"""Unit tests for ``fix_solver`` (Story 14.1 solver seam; Story 14.4 shared edit path and bounds)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.warden import fix_solver
from pyforge.warden.engines import PIXI_LOCK_TIMEOUT_SECONDS
from pyforge.warden.fix_solver import (
    MAX_FIX_CANDIDATES,
    FixTargetResolution,
    PixiVersionOutOfRangeError,
    _package_from_finding_id,
    accepting_solver,
    default_pixi_lock_solver,
    eligible_candidates,
    rejecting_solver,
    resolve_fix_target,
)
from pyforge.warden.manifest_edit import edit_requirement_to_floor
from pyforge.warden.manifest_fixup import tree_content_digest


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
        lambda *, cwd, timeout: (None, 0),
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
        lambda *, cwd, timeout: (None, 1),
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
        lambda *, cwd, timeout: (record, None),
    )
    with pytest.raises(PixiVersionOutOfRangeError):
        default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="2.0.0")


def test_pixi_version_out_of_range_is_pyforge_error():
    assert issubclass(PixiVersionOutOfRangeError, PyforgeError)


# --- Story 14.4: the probe shares the fix's edit path, the loop is bounded ---

_DECLARATION_FORMS = (
    ("pixi.toml", '[pypi-dependencies]\nleftpad = ">=1.0"\n', 'leftpad = ">=2.0.0"'),
    ("pixi.toml", '[pypi-dependencies]\n"leftpad" = ">=1.0"\n', '"leftpad" = ">=2.0.0"'),
    ("pyproject.toml", '[project]\nname = "demo"\ndependencies = [\n  "leftpad>=1.0",\n]\n', '"leftpad>=2.0.0"'),
    ("recipe/recipe.yaml", "requirements:\n  run:\n    - leftpad >=1.0\n", "- leftpad >=2.0.0"),
)


@pytest.mark.parametrize(
    ("rel", "content", "expected"),
    _DECLARATION_FORMS,
    ids=["pixi-bare-key", "pixi-quoted-key", "pyproject-dependency", "recipe-requirement"],
)
def test_default_solver_probes_every_declaration_form_through_the_shared_edit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, rel: str, content: str, expected: str
) -> None:
    scan = tmp_path / "scan"
    manifest = scan / rel
    manifest.parent.mkdir(parents=True)
    manifest.write_text(content, encoding="utf-8")
    digest = tree_content_digest(scan)
    edits: list[tuple[Path, bool]] = []
    seen: dict[str, object] = {}

    def _spy_edit(path: Path, *, package: str, floor: str):  # noqa: ANN202
        result = edit_requirement_to_floor(path, package=package, floor=floor)
        edits.append((path, result.ok))
        return result

    def _fake_lock(*, cwd: Path, timeout: float) -> tuple[None, int]:
        seen["cwd"] = cwd
        seen["text"] = (cwd / rel).read_text(encoding="utf-8")
        return None, 0

    monkeypatch.setattr(fix_solver, "edit_requirement_to_floor", _spy_edit)
    monkeypatch.setattr(fix_solver, "run_pixi_lock", _fake_lock)

    verdict = default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="2.0.0")

    assert verdict == "accepted"
    copy_root = seen["cwd"]
    assert isinstance(copy_root, Path)
    assert [(path.relative_to(copy_root).as_posix(), ok) for path, ok in edits] == [(rel, True)]
    text = seen["text"]
    assert isinstance(text, str)
    assert expected in text
    if rel.endswith(".toml"):
        tomllib.loads(text)
    assert tree_content_digest(scan) == digest


def test_resolve_fix_target_default_solver_resolves_a_bare_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "pixi.toml").write_text('[pypi-dependencies]\nleftpad = ">=1.0"\n', encoding="utf-8")
    timeouts: list[float] = []

    def _fake_lock(*, cwd: Path, timeout: float) -> tuple[None, int]:
        timeouts.append(timeout)
        return None, 0

    monkeypatch.setattr(fix_solver, "run_pixi_lock", _fake_lock)
    resolution = resolve_fix_target("vuln:GHSA-test:leftpad@1.2.0", ("1.3.0",), dry_run=False, scan_target=scan)
    assert resolution.target == "1.3.0"
    assert resolution.attempts == (("1.3.0", "accepted"),)
    assert timeouts == [PIXI_LOCK_TIMEOUT_SECONDS]


def test_default_solver_rejects_a_package_declared_in_two_manifests(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "pixi.toml").write_text('[pypi-dependencies]\nleftpad = ">=1.0"\n', encoding="utf-8")
    (scan / "pyproject.toml").write_text('[project]\ndependencies = [\n  "leftpad>=1.0",\n]\n', encoding="utf-8")
    locks: list[Path] = []

    def _fake_lock(*, cwd: Path, timeout: float) -> tuple[None, int]:
        locks.append(cwd)
        return None, 0

    monkeypatch.setattr(fix_solver, "run_pixi_lock", _fake_lock)
    assert default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="2.0.0") == "rejected"
    assert default_pixi_lock_solver(scan_target=scan, package="", floor_version="2.0.0") == "rejected"
    assert locks == []


def test_default_solver_copy_holds_no_pixi_or_git_and_the_scan_tree_is_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scan = tmp_path / "scan"
    (scan / ".pixi" / "envs" / "default").mkdir(parents=True)
    (scan / ".pixi" / "envs" / "default" / "big.bin").write_bytes(b"\0" * 64)
    (scan / ".git" / "objects").mkdir(parents=True)
    (scan / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (scan / "vendor" / "lib").mkdir(parents=True)
    (scan / "vendor" / "lib" / ".git").write_text("gitdir: ../../.git/modules/lib\n", encoding="utf-8")
    (scan / "pixi.toml").write_text('[pypi-dependencies]\nleftpad = ">=1.0"\n', encoding="utf-8")
    digest = tree_content_digest(scan)
    seen: list[str] = []

    def _fake_lock(*, cwd: Path, timeout: float) -> tuple[None, int]:
        seen.extend(sorted(path.relative_to(cwd).as_posix() for path in cwd.rglob("*")))
        return None, 0

    monkeypatch.setattr(fix_solver, "run_pixi_lock", _fake_lock)
    assert default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="2.0.0") == "accepted"
    assert seen == ["pixi.toml", "vendor", "vendor/lib"]
    assert tree_content_digest(scan) == digest
    assert (scan / ".pixi" / "envs" / "default" / "big.bin").is_file()
    assert (scan / "pixi.toml").read_text(encoding="utf-8") == '[pypi-dependencies]\nleftpad = ">=1.0"\n'


def test_resolve_fix_target_stops_at_the_candidate_cap(tmp_path: Path) -> None:
    tried: list[str] = []

    def _rejecting(*, scan_target: Path, package: str, floor_version: str) -> str:
        tried.append(floor_version)
        return "rejected"

    raw = tuple(f"1.{minor}.0" for minor in range(3, 3 + MAX_FIX_CANDIDATES + 2))
    resolution = resolve_fix_target(
        "vuln:GHSA-test:leftpad@1.2.0", raw, dry_run=False, scan_target=tmp_path, solver=_rejecting
    )
    assert tried == list(raw[:MAX_FIX_CANDIDATES])
    assert resolution.target is None
    assert resolution.candidates == raw
    assert resolution.failure_detail == (
        f"candidate cap of {MAX_FIX_CANDIDATES} reached: the solver accepted none of the "
        f"first {MAX_FIX_CANDIDATES} of {len(raw)} candidates"
    )


def test_resolve_fix_target_stops_at_the_solve_budget(tmp_path: Path) -> None:
    now = [0.0]

    def _slow(*, scan_target: Path, package: str, floor_version: str) -> str:
        now[0] += 11.0
        return "rejected"

    resolution = resolve_fix_target(
        "vuln:GHSA-test:leftpad@1.2.0",
        ("1.3.0", "1.4.0", "1.5.0"),
        dry_run=False,
        scan_target=tmp_path,
        solver=_slow,
        solve_budget_seconds=10.0,
        clock=lambda: now[0],
    )
    assert resolution.target is None
    assert resolution.attempts == (("1.3.0", "rejected"),)
    assert resolution.failure_detail == "solve budget of 10s exhausted after 1 of 3 candidate(s)"


def test_default_solver_lock_timeout_never_outruns_the_remaining_budget(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "pixi.toml").write_text('[pypi-dependencies]\nleftpad = ">=1.0"\n', encoding="utf-8")
    now = [0.0]
    timeouts: list[float] = []

    def _fake_lock(*, cwd: Path, timeout: float) -> tuple[None, int]:
        timeouts.append(timeout)
        now[0] += 50.0
        return None, 1

    monkeypatch.setattr(fix_solver, "run_pixi_lock", _fake_lock)
    resolution = resolve_fix_target(
        "vuln:GHSA-test:leftpad@1.2.0",
        ("1.3.0", "1.4.0", "1.5.0"),
        dry_run=False,
        scan_target=scan,
        solve_budget_seconds=120.0,
        pixi_lock_timeout_seconds=60.0,
        clock=lambda: now[0],
    )
    assert timeouts == [60.0, 60.0, 20.0]
    assert resolution.target is None
    assert resolution.failure_detail == "no candidate was accepted by the solver seam"
