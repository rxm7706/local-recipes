"""Story 43.5 (spec-pyforge-herald CAP-61): the measurer becomes a producer.

``docs-site/scripts/verify_claims.py --emit`` (Story 43.7 moved it beside the generator and retired its typed-value
compare with the ``site-verify`` advisory) writes what ``measure()`` counts for every ``check:`` key the dossier uses
(AC6), refusing an unknown key or a missing package by name. Story 51.1 (CAP-46 amended 2026-11-10) adds the closed
keys that leave no dossier figure typed -- ``stories_epics`` from a station's sprint ledger, the hero's
``fleet_test_lines``, ``fleet_stories_epics`` and ``stations``, and ``rows`` for a table carrying ``check:
src_lines`` -- each refusal naming what it refuses. Every case measures a fixture tree with known counts, never this
repository."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# Story 52.1 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

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


# --- Story 51.1 (CAP-46 amended 2026-11-10): no dossier figure is typed --------------------------------------------

LEDGER_REL = "_bmad-output/projects/pyforge-{}/planning-artifacts/sprint-status-ledger.yaml"
#: three stories and one epic done, beside what never counts: a backlog and a blocked story, an epic still open, and
#: two retrospective keys (the one at ``done`` would read as a fourth story or a second epic if it were counted)
LEDGER = {
    "development_status": {
        "1-1-first-story": "done",
        "1-2-second-story": "done",
        "1-3-third-story": "done",
        "2-1-open-story": "backlog",
        "2-2-held-story": "blocked",
        "epic-1": "done",
        "epic-2": "in-progress",
        "epic-1-retrospective": "optional",
        "epic-2-retrospective": "done",
    }
}
#: ``pyforge-core``'s fixture package: (source lines, source files)
CORE = (4321, 2)


def _ledger(root: Path, station: str) -> None:
    path = root / LEDGER_REL.format(station)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(LEDGER, sort_keys=False), encoding="utf-8")


def _core(root: Path) -> None:
    src, files = CORE
    for n in range(files):
        path = root / "src" / "shared" / "packages" / "pyforge-core" / "src" / "core" / f"m{n}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("z = 3\n" * (src - files + 1 if n == 0 else 1), encoding="utf-8")


def _counted(tmp_path: Path, *, hero: list[str], atlas: list[str], table: dict | None = None) -> tuple[Path, Path]:
    """The 43.5 fixture tree with both stations' ledgers and ``pyforge-core`` planted, and a dossier whose hero carries
    the ``hero`` keys, whose atlas band carries the ``atlas`` keys, and whose synthesis section holds ``table``."""
    root, content = _tree(tmp_path)
    for station in COUNTS:
        _ledger(root, station)
    _core(root)
    doc = yaml.safe_load(content.read_text(encoding="utf-8"))
    doc["stats"] = [{"value": "0", "label": f"hero {kind}", "check": kind} for kind in hero]
    sections = {section["id"]: section for section in doc["sections"]}
    sections["atlas"]["blocks"][0]["stats"] = [{"value": "0", "label": kind, "check": kind} for kind in atlas]
    sections["synthesis"]["blocks"] = [table] if table else []
    content.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return root, content


def _scale(*rows: dict, check: str = "src_lines") -> dict:
    return {
        "type": "table",
        "check": check,
        "headers": ["Station", "Source lines", "Files", "Shape"],
        "rows": list(rows),
    }


def _row(name: str, section: str | None) -> dict:
    return {"cells": [name, "1", "1", "typed shape"], **({"section": section} if section else {})}


def _emitted(root: Path, content: Path) -> dict:
    done = _run("--emit", "-", "--root", str(root), "--content", str(content))
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_51_1_stories_epics_counts_done_stories_over_done_epics_and_nothing_else(tmp_path: Path) -> None:
    root, content = _counted(tmp_path, hero=[], atlas=["stories_epics"])
    assert _emitted(root, content)["stories_epics"] == {"atlas": {"value": "3 / 1"}}


def test_51_1_a_station_with_no_ledger_exits_2_naming_the_section(tmp_path: Path) -> None:
    root, content = _counted(tmp_path, hero=[], atlas=["stories_epics"])
    (root / LEDGER_REL.format("atlas")).unlink()
    done = _run("--emit", "-", "--root", str(root), "--content", str(content))
    assert done.returncode == 2 and done.stdout == ""
    assert "check 'stories_epics' in section 'atlas': no sprint ledger" in done.stderr


def test_51_1_the_hero_keys_are_emitted_under_fleet(tmp_path: Path) -> None:
    hero = ["stations", "fleet_src_lines", "fleet_test_lines", "fleet_stories_epics"]
    root, content = _counted(tmp_path, hero=hero, atlas=["src_lines", "test_lines", "stories_epics", "python_floor"])
    measured = _emitted(root, content)
    assert measured["stations"] == {"fleet": {"value": "2"}}  # the dossier's two station sections, each measured
    assert measured["fleet_src_lines"] == {"fleet": {"value": "~94K"}}  # 41,234 + 52,345
    assert measured["fleet_test_lines"] == {"fleet": {"value": "~7K"}}  # 400 + 7,000
    assert measured["fleet_stories_epics"] == {"fleet": {"value": "6 / 2"}}  # each station's 3 / 1
    assert measured["python_floor"] == {"atlas": {"value": "py3.13"}, "mason": {"value": "py3.14"}}


def test_51_1_a_checked_table_is_emitted_under_rows_and_core_resolves_to_pyforge_core(tmp_path: Path) -> None:
    table = _scale(_row("Mason", "mason"), _row("Atlas", "atlas"), _row("pyforge-core", "core"))
    root, content = _counted(tmp_path, hero=[], atlas=["src_lines"], table=table)
    rows = _emitted(root, content)["rows"]
    assert rows == {
        "mason": {"value": "52,345", "files": 2},
        "atlas": {"value": "41,234", "files": 3},
        "core": {"value": "4,321", "files": 2},  # pyforge-core's package, the one non-station row
    }


@pytest.mark.parametrize(
    ("table", "named"),
    [
        (_scale(_row("Atlas", "atlas"), _row("Warden", None)), "in section 'synthesis': row 'Warden' has no section:"),
        (_scale(_row("Atlas", "atlas"), check="moons"), "unknown check 'moons' on a table in section 'synthesis'"),
        (_scale(_row("Moon", "moon")), "table row section 'moon' in section 'synthesis': no package"),
    ],
    ids=["row-with-no-section", "unknown-table-key", "unknown-row-section"],
)
def test_51_1_a_checked_table_row_with_no_section_or_an_unknown_key_exits_2_naming_it(
    tmp_path: Path, table: dict, named: str
) -> None:
    root, content = _counted(tmp_path, hero=[], atlas=["src_lines"], table=table)
    done = _run("--emit", "-", "--root", str(root), "--content", str(content))
    assert done.returncode == 2 and done.stdout == ""
    assert named in done.stderr


def test_51_1_an_unknown_hero_key_exits_2_naming_it(tmp_path: Path) -> None:
    root, content = _counted(tmp_path, hero=["moons"], atlas=["src_lines"])
    done = _run("--emit", "-", "--root", str(root), "--content", str(content))
    assert done.returncode == 2 and "unknown check 'moons' in the hero stats" in done.stderr
