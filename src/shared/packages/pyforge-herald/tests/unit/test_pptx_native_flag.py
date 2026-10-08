"""ON/OFF tests for ``herald deck pptx-native`` (CAP-57, feature-flag-governance Q3)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pyforge.testing_kit.cli_runner import invoke_cli
from pyforge.testing_kit.flags import flagd_tree

from pyforge.herald.cli import main
from pyforge.herald.pptx_native import DECK_EXPORT_NATIVE_FLAG, MODERNIST_DESIGN_SYSTEM_REL


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def _copy_modernist_tokens(dest_root: Path) -> None:
    src = _repo_root() / MODERNIST_DESIGN_SYSTEM_REL
    dst = dest_root / MODERNIST_DESIGN_SYSTEM_REL
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _deck_tree(tmp_path: Path) -> Path:
    slug = "demo-deck"
    marp = tmp_path / "presentations" / slug / "src" / "marp" / f"{slug}-deck-2026-09-01.md"
    marp.parent.mkdir(parents=True, exist_ok=True)
    marp.write_text("# Demo\n\n- bullet\n", encoding="utf-8")
    return tmp_path


def test_pptx_native_flag_off_lists_disabled_and_exits_usage(tmp_path: Path, monkeypatch):
    tree = _deck_tree(tmp_path)
    monkeypatch.chdir(tree)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {DECK_EXPORT_NATIVE_FLAG: "off"})))
    help_out = invoke_cli(main, ["deck", "--help"]).output
    assert "pptx-native" in help_out
    assert "disabled" in help_out.lower()
    result = invoke_cli(main, ["deck", "pptx-native", "demo-deck", "--repo-root", str(tree)])
    assert result.exit_code == 2
    assert "flag" in result.output.lower()
    assert not any((tree / "presentations" / "demo-deck" / "src" / "pptx").glob("*.pptx"))


def test_pptx_native_writes_when_flag_on(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.herald.stamps.write_stamp", lambda *_a, **_k: None)
    if shutil.which("node") is None:
        pytest.skip("node not on PATH")
    prefix = __import__("os").environ.get("CONDA_PREFIX", "")
    if not prefix or not (Path(prefix) / "lib" / "node_modules" / "pptxgenjs-plus").is_dir():
        pytest.skip("pptxgenjs-plus unavailable in this env")
    tree = _deck_tree(tmp_path)
    _copy_modernist_tokens(tree)
    monkeypatch.chdir(tree)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {DECK_EXPORT_NATIVE_FLAG: "on"})))
    code = main(["deck", "pptx-native", "demo-deck", "--repo-root", str(tree)])
    assert code == 0
    out_dir = tree / "presentations" / "demo-deck" / "src" / "pptx"
    assert list(out_dir.glob("demo-deck-deck-native-*.pptx"))
