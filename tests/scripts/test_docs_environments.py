"""Unit tests for ``scripts/docs_environments.py`` (Story 30.3,
spec-pyforge-doctor CAP-84): docs/reference/environments.md generated from
pixi.toml's [environments] table.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _docs_gen_common as common  # noqa: E402
import docs_environments as m  # noqa: E402

_STAMP = {"derived_at": "2026-01-01T00:00:00", "tree": "deadbeef"}

_PIXI_TOML = """\
[environments]
lean = { features = ["python", "lean-feature"], no-default-feature = true }
fat = ["python", "fat-feature"]
"""


def _write_pixi_toml(root: Path) -> None:
    (root / "pixi.toml").write_text(_PIXI_TOML, encoding="utf-8")


def test_render_lists_every_environment_sorted_with_its_features(tmp_path: Path):
    _write_pixi_toml(tmp_path)

    content = m.render(tmp_path, _STAMP)

    fat_idx = content.index("| `fat` |")
    lean_idx = content.index("| `lean` |")
    assert fat_idx < lean_idx  # alphabetical
    assert "`python`, `fat-feature`" in content
    assert "`python`, `lean-feature`" in content


def test_render_marks_no_default_feature(tmp_path: Path):
    _write_pixi_toml(tmp_path)

    content = m.render(tmp_path, _STAMP)

    lean_row = next(line for line in content.splitlines() if line.startswith("| `lean` |"))
    fat_row = next(line for line in content.splitlines() if line.startswith("| `fat` |"))
    assert lean_row.endswith("| yes |")
    assert fat_row.endswith("|  |")


def test_render_is_deterministic(tmp_path: Path):
    _write_pixi_toml(tmp_path)

    assert m.render(tmp_path, _STAMP) == m.render(tmp_path, dict(_STAMP))


def test_main_write_then_check_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_pixi_toml(tmp_path)
    monkeypatch.setattr(common, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(common, "head_stamp", lambda root: dict(_STAMP))

    monkeypatch.setattr(sys, "argv", ["docs_environments.py"])
    assert m.main() == 0

    monkeypatch.setattr(sys, "argv", ["docs_environments.py", "--check"])
    assert m.main() == 0

    # A new environment, not yet regenerated -> --check reds it.
    (tmp_path / "pixi.toml").write_text(_PIXI_TOML + '\nnewenv = ["python"]\n', encoding="utf-8")
    assert m.main() == 1
