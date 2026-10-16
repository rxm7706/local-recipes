"""Story 43.5 (spec-pyforge-herald CAP-61): the measurer becomes a producer.

``docs-site/scripts/verify_claims.py --emit`` (Story 43.7 moved it beside the generator and retired its typed-value
compare with the ``site-verify`` advisory) writes what ``measure()`` counts for every ``check:`` key the dossier uses
(AC6), refusing an unknown key or a missing package by name. Every case measures a fixture tree with known line
counts, never this repository."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]
VERIFY = REPO_ROOT / "docs-site" / "scripts" / "verify_claims.py"

#: station -> (source lines, source files, test lines, Python floor) of its fixture package
COUNTS = {"atlas": (41234, 3, 400, "3.13"), "mason": (52345, 2, 7000, "3.14")}


def _tree(tmp_path: Path, *, atlas_check: str = "src_lines", measured: bool = True) -> tuple[Path, Path]:
    """A fixture tree with two station packages and a dossier whose typed values are stale on purpose."""
    root = tmp_path / "tree"
    for station, (src, files, tests, floor) in COUNTS.items():
        pkg = root / "src" / "shared" / "packages" / f"pyforge-{station}"
        for n in range(files):
            path = pkg / "src" / station / f"m{n}.py"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x = 1\n" * (src - files + 1 if n == 0 else 1), encoding="utf-8")
        (pkg / "tests").mkdir(parents=True)
        (pkg / "tests" / "test_m.py").write_text("y = 2\n" * tests, encoding="utf-8")
        (pkg / "pyproject.toml").write_text(f'[project]\nrequires-python = ">={floor}"\n', encoding="utf-8")

    def section(sid: str, stats: list[dict]) -> dict:
        out = {"id": sid, "kind": "station", "blocks": [{"type": "stats", "stats": stats}]}
        return {**out, "measured": "2026-10-14"} if measured else out

    doc = {
        "title": "Fixture dossier",
        "stats": [
            {"value": "~1K", "label": "Lines of source", "check": "fleet_src_lines"},
            {"value": "8", "label": "Stations"},
        ],
        "sections": [
            section(
                "atlas",
                [
                    {"value": "999", "label": "Lines · 9 files", "check": atlas_check},
                    {"value": "8 / 11", "label": "Pipelines"},
                ],
            ),
            section(
                "mason",
                [
                    {"value": "1", "label": "Source lines · 1 files", "check": "src_lines"},
                    {"value": "2", "label": "Test lines", "check": "test_lines"},
                    {"value": "py3.14", "label": "Floor", "check": "python_floor"},
                ],
            ),
            section("synthesis", [{"value": "17", "label": "Claims"}]),
        ],
    }
    content = tmp_path / "dossier.yml"
    content.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return root, content


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VERIFY), *args], capture_output=True, text=True, check=False)


def test_43_5_ac6_emit_writes_one_key_per_check_key_with_the_measured_values(tmp_path: Path) -> None:
    root, content = _tree(tmp_path)
    out = tmp_path / "measured.json"
    done = _run("--emit", str(out), "--root", str(root), "--content", str(content))
    assert done.returncode == 0, done.stderr
    measured = json.loads(out.read_text(encoding="utf-8"))
    assert set(measured) == {"src_lines", "test_lines", "python_floor", "fleet_src_lines"}
    assert measured["src_lines"] == {
        "atlas": {"value": "41,234", "files": 3},
        "mason": {"value": "52,345", "files": 2},
    }
    assert measured["test_lines"] == {"mason": {"value": "7,000"}}
    assert measured["python_floor"] == {"mason": {"value": "py3.14"}}
    assert measured["fleet_src_lines"] == {"fleet": {"value": "~94K"}}  # 41,234 + 52,345: the station sections' sum
    stdout = _run("--emit", "-", "--root", str(root), "--content", str(content))
    assert stdout.returncode == 0 and json.loads(stdout.stdout) == measured


@pytest.mark.parametrize(
    ("atlas_check", "named"),
    [("moons", "unknown check 'moons' in section 'atlas'"), ("src_lines", "section 'mason': no package")],
)
def test_43_5_ac6_an_unknown_key_or_a_missing_package_fails_naming_it(
    tmp_path: Path, atlas_check: str, named: str
) -> None:
    root, content = _tree(tmp_path, atlas_check=atlas_check)
    if atlas_check == "src_lines":
        for path in sorted((root / "src" / "shared" / "packages" / "pyforge-mason").rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        (root / "src" / "shared" / "packages" / "pyforge-mason").rmdir()
    done = _run("--emit", "-", "--root", str(root), "--content", str(content))
    assert done.returncode == 2 and done.stdout == ""
    assert named in done.stderr


def test_43_7_emit_is_the_one_mode_and_a_bare_run_says_so() -> None:
    done = _run()
    assert done.returncode == 2 and "--emit" in done.stderr
    assert "def check(" not in VERIFY.read_text(encoding="utf-8")  # the typed-value compare retired with site-verify
