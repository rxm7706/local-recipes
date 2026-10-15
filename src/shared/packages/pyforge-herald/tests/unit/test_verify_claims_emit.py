"""Story 43.5 (spec-pyforge-herald CAP-61): the measurer becomes a producer.

``docsite/tools/verify_claims.py --emit`` writes what ``measure()`` counts for every ``check:`` key the dossier
uses (AC6), refusing an unknown key or a missing package by name; with ``--page`` the compare judges the stats a
built dossier shows rather than the YAML's typed values (AC5), keeping its exit 1 on drift. Every case measures a
fixture tree with known line counts, never this repository."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]
VERIFY = REPO_ROOT / "docsite" / "tools" / "verify_claims.py"

#: station -> (source lines, source files, test lines, Python floor) of its fixture package; the floors differ, so
#: the compare's fleet-wide floor-gap check has nothing to report
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
    """The script on the fixture only: with the flag unset, a bare compare reads ``--content``, never a built page."""
    env = {k: v for k, v in os.environ.items() if k != "PYFORGE_PAGES_ONE_GENERATOR"}
    return subprocess.run([sys.executable, str(VERIFY), *args], capture_output=True, text=True, check=False, env=env)


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


def _page(values: dict[str, list[tuple[str, str]]]) -> str:
    """A built dossier as DossierBody.astro renders it: the hero, then one section per id."""
    hero = "".join(
        f'<div class="hero-stat"> <span class="n">{v}</span> <span class="l">{lab}</span> </div>'
        for v, lab in values[""]
    )
    sections = "".join(
        f'<section id="{sid}"><div class="stat-row">'
        + "".join(f'<div class="s"><b>{v}</b><span>{lab}</span></div>' for v, lab in stats)
        + "</div></section>"
        for sid, stats in values.items()
        if sid
    )
    return f'<html><body><div class="hero-stats">{hero}</div><main>{sections}</main></body></html>'


def test_43_5_ac5_the_compare_judges_the_built_page_and_keeps_exit_1_on_drift(tmp_path: Path) -> None:
    root, content = _tree(tmp_path)
    measured = {
        "": [("~94K", "Lines of source"), ("8", "Stations")],
        "atlas": [("41,234", "Lines · 3 files"), ("8 / 11", "Pipelines")],
        "mason": [("52,345", "Source lines · 2 files"), ("7,000", "Test lines"), ("py3.14", "Floor")],
        "synthesis": [("17", "Claims")],
    }
    page = tmp_path / "index.html"
    page.write_text(_page(measured), encoding="utf-8")
    assert _run("--root", str(root), "--content", str(content)).returncode == 1  # the YAML's typed values drift
    clean = _run("--page", str(page), "--root", str(root), "--content", str(content))
    assert clean.returncode == 0 and "All checked claims match" in clean.stdout, clean.stdout + clean.stderr

    stale = {**measured, "atlas": [("999", "Lines · 3 files"), ("8 / 11", "Pipelines")]}  # a page showing a typed value
    page.write_text(_page(stale), encoding="utf-8")
    drift = _run("--page", str(page), "--root", str(root), "--content", str(content), "--format", "github")
    assert drift.returncode == 1
    assert "::warning file=docsite/content/dossier.yml::atlas: Lines · 3 files — dossier says 999" in drift.stdout

    short = {**measured, "mason": measured["mason"][:2]}
    page.write_text(_page(short), encoding="utf-8")
    refused = _run("--page", str(page), "--root", str(root), "--content", str(content))
    assert refused.returncode == 2 and "section 'mason': the page shows 2 stats, dossier.yml has 3" in refused.stderr
    missing = _run("--page", str(tmp_path / "absent.html"), "--root", str(root), "--content", str(content))
    assert missing.returncode == 2 and "pages-build writes it" in missing.stderr
