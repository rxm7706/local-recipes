"""Unit tests for pyforge.scribe.extras.move_list -- the foundry-cutover
move-list scan (Story 6.1). Independent of graphifyy: no fake/mocking
needed, this is a plain text scan.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.scribe.extras.move_list import scan_move_list


def test_scan_finds_all_four_signal_categories(tmp_path: Path) -> None:
    host = tmp_path / "src" / "platform"
    host.mkdir(parents=True)
    (host / "app.py").write_text(
        "import pyforge.core\n"
        "from pyforge.scribe import cli\n"
        "import sys\n"
        "sys.path.append('/opt/foo')\n"
        "# five_tier roots live in pyforge.steward.five_tier\n"
        "# CFE caller: .claude/skills/conda-forge-expert/\n",
        encoding="utf-8",
    )

    findings = scan_move_list(tmp_path)
    categories = {f.category for f in findings}

    assert categories == {"import_pyforge", "sys_path_insert", "five_tier_root", "cfe_caller"}
    assert all(f.path == "src/platform/app.py" for f in findings)


def test_scan_import_pyforge_matches_plain_and_from_import(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        "import pyforge\nimport pyforge.scribe.cli\nfrom pyforge.core import hooks\nimport os\n",
        encoding="utf-8",
    )

    findings = [f for f in scan_move_list(tmp_path) if f.category == "import_pyforge"]

    assert [f.line for f in findings] == [1, 2, 3]


def test_scan_sys_path_insert_matches_both_insert_and_append(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("sys.path.insert(0, 'x')\nsys.path.append('y')\n", encoding="utf-8")

    findings = [f for f in scan_move_list(tmp_path) if f.category == "sys_path_insert"]

    assert [f.line for f in findings] == [1, 2]


def test_scan_excludes_worktree_and_vendor_dirs(tmp_path: Path) -> None:
    noisy = tmp_path / ".worktrees" / "x"
    noisy.mkdir(parents=True)
    (noisy / "dup.py").write_text("import pyforge.core\n", encoding="utf-8")
    real = tmp_path / "real.py"
    real.write_text("import pyforge.core\n", encoding="utf-8")

    findings = scan_move_list(tmp_path)

    assert {f.path for f in findings} == {"real.py"}


def test_empty_repo_returns_no_findings(tmp_path: Path) -> None:
    assert scan_move_list(tmp_path) == []


def test_findings_are_deterministically_sorted(tmp_path: Path) -> None:
    (tmp_path / "b.py").write_text("import pyforge.core\nsys.path.insert(0, 'x')\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("import pyforge.core\n", encoding="utf-8")

    findings = scan_move_list(tmp_path)

    assert [(f.path, f.line, f.category) for f in findings] == [
        ("a.py", 1, "import_pyforge"),
        ("b.py", 1, "import_pyforge"),
        ("b.py", 2, "sys_path_insert"),
    ]
