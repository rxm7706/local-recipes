"""Story 19.4 — CAP-5 story-id drift gate for test-architecture.md.

Locks FR-193 / testing-charter CAP-5:
* HAPPY_CHECK — matrix covers every epic story id → exit 0
* MISSING_ROW — epic id absent from matrix → exit 1, names station + ids
* REGEN_FILLS — generate cures drift; subsequent --check exits 0
* MISSING_DOC — epics present, no test-architecture.md → exit 1
* Herald + Marshal remain dry-run regenerable without TBD
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

# meta → tests → package → packages → shared → src → repo
REPO_ROOT = Path(__file__).resolve().parents[6]
SCRIPT = REPO_ROOT / "_bmad" / "scripts" / "bmad_tea_playwright.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("bmad_tea_playwright", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tea():
    return _load_generator()


def _station_tree(tmp_path: Path, *, slug: str = "scribe") -> Path:
    """Minimal station tree the generator / check gate can load."""
    project = f"pyforge-{slug}"
    planning = tmp_path / "_bmad-output" / "projects" / project / "planning-artifacts"
    planning.mkdir(parents=True)
    (planning / "epics.md").write_text(
        "\n".join(
            [
                "## Epic 1: Capture",
                "",
                "### Story 1.1: Package scaffold",
                "",
                "As a developer I want capture.",
                "",
                "### Story 1.2: Wiring",
                "",
                "As a developer I want wiring.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    tests = tmp_path / "src" / "shared" / "packages" / project / "tests" / "unit"
    tests.mkdir(parents=True)
    (tests / "test_1_1_scaffold.py").write_text("def test_scaffold():\n    assert True\n", encoding="utf-8")
    return tmp_path


def _strip_matrix_row(document: str, story_id: str) -> str:
    """Remove a single Story Coverage Matrix data row by story id."""
    pattern = re.compile(
        rf"^\|\s*{re.escape(story_id)}\s*\|[^\n]*\n",
        re.MULTILINE,
    )
    updated, n = pattern.subn("", document, count=1)
    assert n == 1, f"expected to strip matrix row for {story_id}"
    return updated


def test_happy_check_exits_zero(tea, tmp_path: Path, capsys):
    """HAPPY_CHECK: on-disk matrix contains every epic story id → exit 0."""
    root = _station_tree(tmp_path)
    tea.generate_station(root, "pyforge-scribe")
    code = tea.main(["--repo-root", str(root), "--project", "pyforge-scribe", "--check"])
    assert code == 0
    out = capsys.readouterr().out
    assert "OK pyforge-scribe" in out


def test_missing_row_exits_nonzero_and_names_ids(tea, tmp_path: Path, capsys):
    """MISSING_ROW: epic has 1.2; matrix lacks 1.2 → exit 1 + names station + id."""
    root = _station_tree(tmp_path)
    result = tea.generate_station(root, "pyforge-scribe")
    drifted = _strip_matrix_row(result.output_path.read_text(encoding="utf-8"), "1.2")
    result.output_path.write_text(drifted, encoding="utf-8")

    code = tea.main(["--repo-root", str(root), "--project", "pyforge-scribe", "--check"])
    assert code == 1
    err = capsys.readouterr().err
    assert "DRIFT pyforge-scribe" in err
    assert "missing story id(s)" in err
    assert "1.2" in err


def test_regen_fills_missing_row_then_check_passes(tea, tmp_path: Path, capsys):
    """REGEN_FILLS: generate restores the row; subsequent --check exits 0."""
    root = _station_tree(tmp_path)
    result = tea.generate_station(root, "pyforge-scribe")
    drifted = _strip_matrix_row(result.output_path.read_text(encoding="utf-8"), "1.2")
    result.output_path.write_text(drifted, encoding="utf-8")
    assert tea.main(["--repo-root", str(root), "--project", "pyforge-scribe", "--check"]) == 1
    capsys.readouterr()

    tea.generate_station(root, "pyforge-scribe")
    text = result.output_path.read_text(encoding="utf-8")
    assert re.search(r"^\|\s*1\.2\s*\|", text, re.MULTILINE)
    code = tea.main(["--repo-root", str(root), "--project", "pyforge-scribe", "--check"])
    assert code == 0


def test_missing_doc_exits_nonzero(tea, tmp_path: Path, capsys):
    """MISSING_DOC: station has epics but no test-architecture.md → exit 1."""
    root = _station_tree(tmp_path)
    out = root / "_bmad-output" / "projects" / "pyforge-scribe" / "planning-artifacts" / "test-architecture.md"
    assert not out.exists()

    code = tea.main(["--repo-root", str(root), "--project", "pyforge-scribe", "--check"])
    assert code == 1
    err = capsys.readouterr().err
    assert "pyforge-scribe" in err
    assert "test-architecture.md" in err or str(out) in err


def test_missing_matrix_section_exits_nonzero(tea, tmp_path: Path, capsys):
    """Doc present but Story Coverage Matrix section removed → exit 1."""
    root = _station_tree(tmp_path)
    result = tea.generate_station(root, "pyforge-scribe")
    text = result.output_path.read_text(encoding="utf-8")
    # Drop the matrix section header + table through Quality Gates
    cut = re.sub(
        r"## Story Coverage Matrix\n.*?(?=\n## Quality Gates\n)",
        "",
        text,
        count=1,
        flags=re.DOTALL,
    )
    result.output_path.write_text(cut, encoding="utf-8")
    code = tea.main(["--repo-root", str(root), "--project", "pyforge-scribe", "--check"])
    assert code == 1
    err = capsys.readouterr().err
    assert "DRIFT pyforge-scribe" in err
    assert "Story Coverage Matrix" in err


def test_tbd_in_on_disk_doc_fails_check(tea, tmp_path: Path, capsys):
    """Always: TBD in on-disk doc is a hard fail under --check."""
    root = _station_tree(tmp_path)
    result = tea.generate_station(root, "pyforge-scribe")
    text = result.output_path.read_text(encoding="utf-8")
    result.output_path.write_text(text + "\n<!-- TBD leftover -->\n", encoding="utf-8")
    code = tea.main(["--repo-root", str(root), "--project", "pyforge-scribe", "--check"])
    assert code == 1
    err = capsys.readouterr().err
    assert "DRIFT pyforge-scribe" in err
    assert "TBD" in err


def test_all_check_fails_when_any_station_drifts(tea, tmp_path: Path, monkeypatch, capsys):
    """Fleet --all --check: one drifted station → exit 1; names that station."""
    root = tmp_path
    for slug in ("scribe", "herald"):
        _station_tree(root, slug=slug)
        tea.generate_station(root, f"pyforge-{slug}")
    # Drift only herald
    herald_out = root / "_bmad-output" / "projects" / "pyforge-herald" / "planning-artifacts" / "test-architecture.md"
    drifted = _strip_matrix_row(herald_out.read_text(encoding="utf-8"), "1.2")
    herald_out.write_text(drifted, encoding="utf-8")

    monkeypatch.setattr(tea, "STATIONS", ("scribe", "herald"))
    code = tea.main(["--repo-root", str(root), "--all", "--check"])
    assert code == 1
    captured = capsys.readouterr()
    assert "OK pyforge-scribe" in captured.out
    assert "DRIFT pyforge-herald" in captured.err
    assert "1.2" in captured.err


def test_idempotent_generate_twice(tea, tmp_path: Path):
    """IDEMPOTENT: unchanged tree; generate twice → byte-identical."""
    root = _station_tree(tmp_path)
    a = tea.generate_station(root, "pyforge-scribe").output_path.read_bytes()
    b = tea.generate_station(root, "pyforge-scribe").output_path.read_bytes()
    assert a == b


@pytest.mark.parametrize("project", ["pyforge-herald", "pyforge-marshal"])
def test_herald_marshal_dry_run_regenerable_without_tbd(tea, project: str):
    """Live smoke: Herald + Marshal dry-run / render without TBD."""
    result = tea.generate_station(REPO_ROOT, project, dry_run=True)
    assert result.story_count >= 1
    station = tea.load_station(REPO_ROOT, project)
    doc = tea.render_document(station, REPO_ROOT)
    tea.assert_no_tbd(doc, project=project)
    assert tea.GENERATOR_VERSION == "2.1.0"


def test_generator_version_is_2_1_0(tea):
    assert tea.GENERATOR_VERSION == "2.1.0"
