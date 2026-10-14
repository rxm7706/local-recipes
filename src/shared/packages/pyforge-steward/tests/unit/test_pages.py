"""Story 102.2: pages tree hash, build.json, stamp script (CAP-168)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
_STAMP = REPO_ROOT / "scripts" / "pages_build_stamp.py"


def _fixture_tree(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_text("<html>hello</html>", encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "app.css").write_text("body{}", encoding="utf-8")
    return root


def test_tree_hash_stable_and_excludes_build_json(tmp_path: Path) -> None:
    from pyforge.steward.pages import tree_hash

    root = _fixture_tree(tmp_path)
    first = tree_hash(root)
    second = tree_hash(root)
    assert first == second
    (root / "build.json").write_text('{"tree_hash": "other"}\n', encoding="utf-8")
    assert tree_hash(root) == first


def test_decide_deploy_matrix() -> None:
    from pyforge.steward.pages import build_json, decide_deploy

    h = "abc123"
    live = json.dumps(build_json(h, "sha", "1", "2026-10-14T00:00:00Z"))
    assert decide_deploy(h, live, flag_on=True) is False
    assert decide_deploy("other", live, flag_on=True) is True
    assert decide_deploy(h, None, flag_on=True) is True
    assert decide_deploy(h, "not-json", flag_on=True) is True
    assert decide_deploy(h, "{}", flag_on=True) is True
    assert decide_deploy(h, live, flag_on=False) is True


def test_pages_build_stamp_writes_only_build_json(tmp_path: Path) -> None:
    root = _fixture_tree(tmp_path)
    before = {p.name for p in root.iterdir()}
    proc = subprocess.run(
        [
            sys.executable,
            str(_STAMP),
            "--root",
            str(root),
            "--live-url",
            "https://invalid.invalid/build.json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    after = {p.name for p in root.iterdir()}
    assert after - before == {"build.json"}
    assert "tree_hash=" in proc.stdout
    assert "changed=true" in proc.stdout


def test_pages_build_stamp_exit_one_when_root_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    proc = subprocess.run(
        [sys.executable, str(_STAMP), "--root", str(missing), "--live-url", "https://x/y"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
