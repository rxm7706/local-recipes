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


# Story 102.3: the fleet board's input, written by the workflow from sprint-ledger-query JSON.
_FLEET = REPO_ROOT / "scripts" / "pages_fleet_status.py"


def test_pages_fleet_status_reshapes_ledger_json(tmp_path: Path) -> None:
    ledger = tmp_path / "sprint-ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "generated_at": "2026-10-15T12:00:00+00:00",
                "summary": {
                    "stations": {"pyforge-x": {"station": "pyforge-x", "total_stories": 2, "done": 1, "backlog": 1}}
                },
                "epics": [{"station": "pyforge-x", "epic_id": "1"}],
                "stories": [{"story_id": "1.2", "station": "pyforge-x", "status": "backlog", "title": "t"}],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "content" / "fleet-status.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_FLEET),
            "--ledger",
            str(ledger),
            "--out",
            str(out),
            "--generated-at",
            "2026-10-15T06:00:00+00:00",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["generated_at"] == "2026-10-15T06:00:00+00:00"
    assert document["stations"] == [
        {"station": "pyforge-x", "total_stories": 2, "done": 1, "backlog": 1, "total": 2, "epics": 1}
    ]
    assert document["stories"][0]["story_id"] == "1.2"
    assert "wrote" in proc.stdout


def test_pages_fleet_status_exit_one_on_unusable_ledger_json(tmp_path: Path) -> None:
    ledger = tmp_path / "sprint-ledger.json"
    ledger.write_text("{not json", encoding="utf-8")
    out = tmp_path / "fleet-status.json"
    proc = subprocess.run(
        [sys.executable, str(_FLEET), "--ledger", str(ledger), "--out", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert str(ledger) in proc.stderr
    assert not out.exists()


# Story 102.3 (from the doctor 48.2 review): an identical tree still deploys once a day when its commit moved.
def test_decide_deploy_liveness_branch() -> None:
    from datetime import datetime, timedelta, timezone

    from pyforge.steward.pages import LIVENESS_MAX_AGE, build_json, decide_deploy

    now = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    old = (now - LIVENESS_MAX_AGE - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fresh = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    live_old = json.dumps(build_json("same", "a" * 40, "1", old))
    live_fresh = json.dumps(build_json("same", "a" * 40, "1", fresh))
    # old + the commit moved -> deploy
    assert decide_deploy("same", live_old, flag_on=True, built_from="b" * 40, now=now) is True
    # old + the same commit (full or abbreviated) -> skip
    assert decide_deploy("same", live_old, flag_on=True, built_from="a" * 40, now=now) is False
    assert decide_deploy("same", live_old, flag_on=True, built_from="a" * 7, now=now) is False
    # fresh + the same hash -> skip, whatever the commit
    assert decide_deploy("same", live_fresh, flag_on=True, built_from="b" * 40, now=now) is False
    # without the build's commit or the time the branch does not apply (Story 102.2's behaviour)
    assert decide_deploy("same", live_old, flag_on=True) is False
    # a live document without a readable built_at never triggers the extra deploy
    no_time = json.dumps({"tree_hash": "same", "built_from": "a" * 40})
    assert decide_deploy("same", no_time, flag_on=True, built_from="b" * 40, now=now) is False
    # a changed tree still deploys, and flag off still always deploys
    assert decide_deploy("other", live_fresh, flag_on=True, built_from="a" * 40, now=now) is True
    assert decide_deploy("same", live_fresh, flag_on=False, built_from="a" * 40, now=now) is True
