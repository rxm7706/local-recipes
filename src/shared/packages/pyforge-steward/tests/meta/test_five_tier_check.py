"""FR-39 / canopy AD-14: five-tier completeness check."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from pyforge.steward.five_tier import (
    DENOMINATOR,
    STATIONS,
    TIERS,
    FiveTierCompleteError,
    WorkItem,
    check,
    report,
)

PROOF_STATION = "scribe"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _write_01_fixture(root: Path) -> WorkItem:
    root.mkdir(parents=True, exist_ok=True)
    (root / "spec.md").write_text("# one-off\n", encoding="utf-8")
    (root / "script.py").write_text("print('ok')\n", encoding="utf-8")
    return WorkItem(
        token="one-off-job",
        work_class="01",
        declared_complete=True,
        present={tier: False for tier in TIERS},
    )


def _write_02_fixture(root: Path) -> WorkItem:
    root.mkdir(parents=True, exist_ok=True)
    (root / "spec.md").write_text("# short-term\n", encoding="utf-8")
    (root / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    return WorkItem(
        token="short-term-skill",
        work_class="02",
        declared_complete=True,
        present={tier: False for tier in TIERS},
    )


def test_check_module_must_exist():
    """Removing the check must fail this suite (FR-39)."""
    from pyforge.steward import five_tier as module

    path = Path(module.__file__).resolve()
    assert path.is_file()
    assert path.name == "five_tier.py"
    assert callable(module.check)
    assert callable(module.report)
    assert module.DENOMINATOR == 40
    assert module.DENOMINATOR == len(STATIONS) * len(TIERS)
    assert TIERS == ("cli", "portal", "service", "skill", "persona")
    assert STATIONS == (
        "atlas",
        "doctor",
        "herald",
        "marshal",
        "mason",
        "scribe",
        "steward",
        "warden",
    )


def test_live_matrix_reports_eight_stations_times_five_tiers():
    result = report(_repo_root())
    assert result.denominator == 40
    assert len(result.matrix) == 8
    assert tuple(row.station for row in result.matrix) == STATIONS
    for row in result.matrix:
        assert set(row.cells) >= set(TIERS)
        for tier in TIERS:
            assert isinstance(row.cells[tier], bool)


def test_live_undeclared_stations_do_not_fail_on_missing_tiers():
    result = check(_repo_root())
    scribe = next(row for row in result.matrix if row.station == PROOF_STATION)
    assert scribe.cells["skill"] is True
    assert scribe.cells["persona"] is True
    missing_any = [row.station for row in result.matrix if row.missing()]
    assert missing_any, "the report must still show holes; do not mint seven personas"


def test_03_declared_complete_with_all_five_passes():
    extra = WorkItem(
        token="proof-complete",
        work_class="03",
        declared_complete=True,
        present={tier: True for tier in TIERS},
    )
    check(_repo_root(), extra=(extra,), declared_complete=())


def test_03_declared_complete_with_missing_tier_fails():
    extra = WorkItem(
        token="atlas",
        work_class="03",
        declared_complete=True,
        present={
            "cli": True,
            "portal": True,
            "service": True,
            "skill": False,
            "persona": False,
        },
    )
    with pytest.raises(FiveTierCompleteError, match="atlas"):
        check(_repo_root(), extra=(extra,), declared_complete=())
    with pytest.raises(FiveTierCompleteError, match="fewer than five"):
        check(_repo_root(), declared_complete=("atlas",))


def test_01_spec_plus_script_complete_does_not_fail(tmp_path: Path):
    item = _write_01_fixture(tmp_path / "01-job")
    assert (tmp_path / "01-job" / "spec.md").is_file()
    assert (tmp_path / "01-job" / "script.py").is_file()
    check(_repo_root(), extra=(item,))


def test_02_spec_plus_skill_complete_does_not_fail(tmp_path: Path):
    item = _write_02_fixture(tmp_path / "02-skill")
    assert (tmp_path / "02-skill" / "spec.md").is_file()
    assert (tmp_path / "02-skill" / "SKILL.md").is_file()
    check(_repo_root(), extra=(item,))


def test_no_pyforge_under_src_platform():
    root = _repo_root()
    has_main = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/main"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if has_main.returncode == 0:
        diff = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "--", "src/platform"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        assert diff.stdout.strip() == "", diff.stdout
    platform = root / "src" / "platform"
    offenders: list[str] = []
    for path in platform.rglob("*.py"):
        if "five_tier" in path.name:
            offenders.append(str(path.relative_to(root)))
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "pyforge.steward.five_tier" or alias.name.endswith(
                        ".five_tier"
                    ):
                        offenders.append(f"{path.relative_to(root)}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "five_tier" in module:
                    offenders.append(f"{path.relative_to(root)}:{node.lineno}")
    assert not offenders, offenders
