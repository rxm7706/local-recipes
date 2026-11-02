"""Story 14.4 (AC5, AC6): the default fix-target solver runs the real ``pixi lock`` once.

Opt-in: ``slow`` keeps it out of the default ``pyforge-warden-test`` loop
(``-m "not slow"``); run it with
``pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/integration/test_fix_solver_real_pixi.py -m slow``.
Hermetic: the fixture repo's only channel is a local ``file://`` channel whose
``repodata.json`` this test writes, so the solve needs no network.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pyforge.warden import engines, fix_solver
from pyforge.warden.fix_solver import default_pixi_lock_solver, resolve_fix_target
from pyforge.warden.manifest_fixup import tree_content_digest

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("pixi") is None, reason="needs the workspace pixi on PATH"),
]

_ROOT_PIXI_LOCK = Path(__file__).resolve().parents[6] / "pixi.lock"


def _write_channel(channel: Path) -> None:
    packages = {
        f"leftpad-{version}-0.tar.bz2": {
            "name": "leftpad",
            "version": version,
            "build": "0",
            "build_number": 0,
            "depends": [],
            "subdir": "noarch",
            "noarch": "generic",
            "md5": "0" * 32,
            "sha256": "0" * 64,
            "size": 1,
        }
        for version in ("1.0.0", "1.2.0", "1.3.0")
    }
    for subdir, entries in (("noarch", packages), ("linux-64", {})):
        (channel / subdir).mkdir(parents=True)
        repodata = {"info": {"subdir": subdir}, "packages": entries, "packages.conda": {}}
        (channel / subdir / "repodata.json").write_text(json.dumps(repodata), encoding="utf-8")


def _write_repo(scan: Path, channel: Path) -> None:
    scan.mkdir()
    (scan / "pixi.toml").write_text(
        "[workspace]\n"
        'name = "warden-fix-solver-fixture"\n'
        f'channels = ["{channel.as_uri()}"]\n'
        'platforms = ["linux-64"]\n'
        "\n"
        "[dependencies]\n"
        'leftpad = ">=1.0"  # vulnerable floor\n',
        encoding="utf-8",
    )


def _root_lock_stamp() -> tuple[int, int] | None:
    if not _ROOT_PIXI_LOCK.is_file():
        return None
    stat = _ROOT_PIXI_LOCK.stat()
    return stat.st_mtime_ns, stat.st_size


def test_real_pixi_lock_resolves_a_candidate_floor_in_the_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    channel = tmp_path / "channel"
    scan = tmp_path / "scan"
    _write_channel(channel)
    _write_repo(scan, channel)
    digest = tree_content_digest(scan)
    locked: list[str] = []

    def _real_lock_then_read(*, cwd: Path, timeout: float):  # noqa: ANN202
        result = engines.run_pixi_lock(cwd=cwd, timeout=timeout)
        lock = cwd / "pixi.lock"
        locked.append(lock.read_text(encoding="utf-8") if lock.is_file() else "")
        return result

    monkeypatch.setattr(fix_solver, "run_pixi_lock", _real_lock_then_read)

    resolution = resolve_fix_target(
        "vuln:GHSA-test:leftpad@1.0.0",
        ("1.3.0",),
        dry_run=False,
        scan_target=scan,
        pixi_lock_timeout_seconds=120.0,
    )

    assert resolution.target == "1.3.0", resolution
    assert resolution.attempts == (("1.3.0", "accepted"),)
    (lock_text,) = locked
    assert "leftpad-1.3.0-0.tar.bz2" in lock_text
    assert tree_content_digest(scan) == digest
    assert not (scan / "pixi.lock").exists()


def test_real_pixi_lock_rejects_an_unsolvable_floor(tmp_path: Path) -> None:
    channel = tmp_path / "channel"
    scan = tmp_path / "scan"
    _write_channel(channel)
    _write_repo(scan, channel)
    digest = tree_content_digest(scan)

    verdict = default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="9.9.9", timeout=120.0)

    assert verdict == "rejected"
    assert tree_content_digest(scan) == digest


def test_real_pixi_lock_never_falls_back_to_the_host_workspace(tmp_path: Path) -> None:
    """A copy with no pixi manifest is refused, not re-solved as the host's
    ``PIXI_PROJECT_MANIFEST`` workspace (``--manifest-path`` pins the copy)."""
    scan = tmp_path / "scan"
    (scan / "recipe").mkdir(parents=True)
    (scan / "recipe" / "recipe.yaml").write_text("requirements:\n  run:\n    - leftpad >=1.0\n", encoding="utf-8")
    before = _root_lock_stamp()

    verdict = default_pixi_lock_solver(scan_target=scan, package="leftpad", floor_version="1.3.0", timeout=120.0)

    assert verdict == "rejected"
    assert _root_lock_stamp() == before
