"""Story 93.2 (spec-pyforge-steward CAP-153): the lint gate covers the repository's own scripts in ``_bmad/scripts/``.

``scripts/lint_types.py``'s ruff verbs check every ``*.py`` in ``_bmad/scripts/`` that the BMAD installer's
``_bmad/_config/files-manifest.csv`` does not list (today the TEA generator, ``bmad_tea_playwright.py``), with
``pyforge-marshal``'s ``[tool.ruff]``. The installer's own scripts stay out: an upgrade rewrites them to the hashes
the manifest records. The Lint and types workflow fires on a change to either.
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

# This module reads the live tree outside its package (_bmad/, scripts/, the workflow), so it runs in the station's
# live-tree half (pyforge-steward-live-test) and fires on what it reads (Story 117.4).
pytestmark = pytest.mark.live_tree

ROOT = Path(__file__).resolve().parents[6]
INSTALLER_SCRIPTS = {"config_utils.py", "memlog.py", "render_skill.py", "resolve_config.py", "resolve_customization.py"}


def _lint_types():
    name = "_lint_types_bmad_scripts"
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "lint_types.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _bmad_tree(tmp_path: Path, manifest_paths: list[str], scripts: list[str]) -> Path:
    root = tmp_path / "_bmad"
    (root / "_config").mkdir(parents=True)
    (root / "scripts").mkdir()
    rows = "".join(f'"py","{Path(p).stem}","scripts","{p}","0"\n' for p in manifest_paths)
    (root / "_config" / "files-manifest.csv").write_text("type,name,module,path,hash\n" + rows, encoding="utf-8")
    for name in scripts:
        (root / "scripts" / name).write_text("x = 1\n", encoding="utf-8")
    return root


def test_the_repository_s_own_scripts_are_linted_and_the_installer_s_are_not() -> None:
    names = {p.name for p in _lint_types().bmad_scripts()}
    assert "bmad_tea_playwright.py" in names
    assert not names & INSTALLER_SCRIPTS
    on_disk = {p.name for p in (ROOT / "_bmad" / "scripts").glob("*.py")}
    assert names == on_disk - INSTALLER_SCRIPTS, "a new installer script needs its manifest row, or this set updated"


def test_a_script_the_manifest_lists_is_left_out(tmp_path: Path) -> None:
    root = _bmad_tree(tmp_path, ["scripts/installer.py"], ["installer.py", "ours.py", "also_ours.py"])
    assert [p.name for p in _lint_types().bmad_scripts(root)] == ["also_ours.py", "ours.py"]


def test_a_missing_manifest_raises_so_the_gate_cannot_skip_silently(tmp_path: Path) -> None:
    root = tmp_path / "_bmad"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "ours.py").write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(OSError):
        _lint_types().bmad_scripts(root)


def test_the_scripts_are_checked_with_the_shared_pyforge_rules() -> None:
    mod = _lint_types()
    assert mod.BMAD_SCRIPTS_RUFF_CONFIG == ROOT / "src" / "shared" / "packages" / "pyforge-marshal" / "pyproject.toml"
    tables = {
        p.parent.name: tomllib.loads(p.read_text(encoding="utf-8"))["tool"]["ruff"]
        for p in (ROOT / "src" / "shared" / "packages").glob("pyforge-*/pyproject.toml")
    }
    assert len(tables) == 10

    def rules(table: dict) -> tuple:
        # What a file outside any package is judged by: the target, the line length, and the selected and ignored
        # rules. Per-file ignores name package paths (tests/, __init__.py), which these scripts are not.
        lint = table["lint"]
        return table["target-version"], table["line-length"], lint["select"], lint["ignore"]

    marshal = rules(tables["pyforge-marshal"])
    assert marshal == ("py314", 120, ["E", "F", "W", "I"], ["E501"])
    assert all(rules(table) == marshal for table in tables.values()), "the pyforge-* packages no longer share rules"


def test_the_lint_and_types_workflow_fires_on_the_scripts_and_the_manifest() -> None:
    text = (ROOT / ".github" / "workflows" / "lint-types.yml").read_text(encoding="utf-8")
    assert '- "_bmad/scripts/**"' in text
    assert '- "_bmad/_config/files-manifest.csv"' in text
