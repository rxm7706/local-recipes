"""Story 102.2: pages tree hash, build.json, stamp script (CAP-168)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

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


def test_tree_hash_ignores_the_built_from_text_but_not_the_content(tmp_path: Path) -> None:
    """Herald Story 43.5: the built-from line (commit, build time, run id) changes on every build; the hash reads
    each HTML page without its text, so a rebuild of an unmoved tree hashes the same and deploys nothing, while a
    content change, the line's removal, or the same text outside an ``.html`` file still moves the hash."""
    from pyforge.steward.pages import tree_hash

    root = _fixture_tree(tmp_path)
    page = root / "index.html"

    def line(text: str) -> str:
        return f'<html><main>hello</main><p class="built-from" data-pages-built-from data-pagefind-ignore>{text}</p></html>'

    page.write_text(line("Built from 0123456 · 2026-10-15 09:00 UTC · run 1"), encoding="utf-8")
    first = tree_hash(root)
    page.write_text(line("Built from 89abcde · 2026-10-16 11:42 UTC · run 2"), encoding="utf-8")
    assert tree_hash(root) == first
    page.write_text(line("local build"), encoding="utf-8")
    assert tree_hash(root) == first
    page.write_text(line("local build").replace("hello", "hello, world"), encoding="utf-8")
    assert tree_hash(root) != first
    page.write_text("<html><main>hello</main></html>", encoding="utf-8")
    assert tree_hash(root) != first
    page.write_text(line("local build"), encoding="utf-8")
    (root / "assets" / "app.css").write_text("/* data-pages-built-from>x</p> */", encoding="utf-8")
    third = tree_hash(root)
    page.write_text(line("local build") + "<p>more content</p>", encoding="utf-8")  # a change beside the line
    assert tree_hash(root) != third
    page.write_text(line("local build"), encoding="utf-8")
    second = tree_hash(root)
    (root / "assets" / "app.css").write_text("/* data-pages-built-from>y</p> */", encoding="utf-8")
    assert tree_hash(root) != second


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
    # Only the counts herald reads: no `total_stories`, no `next_running` (the live marshal fact).
    assert document["stations"] == [{"station": "pyforge-x", "epics": 1, "total": 2, "done": 1, "backlog": 1}]
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


def test_pages_fleet_status_refuses_an_empty_generated_at(tmp_path: Path) -> None:
    """`--generated-at "$(git log …)"` with a failed git passes "": refuse it, never fall back silently."""
    ledger = tmp_path / "sprint-ledger.json"
    ledger.write_text(json.dumps({"summary": {"stations": {}}}), encoding="utf-8")
    out = tmp_path / "fleet-status.json"
    proc = subprocess.run(
        [sys.executable, str(_FLEET), "--ledger", str(ledger), "--out", str(out), "--generated-at", " "],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "--generated-at is empty" in proc.stderr
    assert not out.exists()


def _stamp_with_live(tmp_path: Path, *, live: dict, built_from: str) -> subprocess.CompletedProcess[str]:
    """Run the stamp script against a `file://` live build.json, with the pages_duty flag on."""
    from pyforge.testing_kit.flags import flagd_tree

    tmp_path.mkdir(parents=True)
    root = _fixture_tree(tmp_path)
    live_path = tmp_path / "live" / "build.json"
    live_path.parent.mkdir()
    live_path.write_text(json.dumps(live), encoding="utf-8")
    env = {
        **os.environ,
        "PYFORGE_FLAGS_PATH": str(flagd_tree(tmp_path, {"pyforge.steward.pages_duty": "on"})),
    }
    env.pop("PYFORGE_ENVIRONMENT", None)
    return subprocess.run(
        [
            sys.executable,
            str(_STAMP),
            "--root",
            str(root),
            "--live-url",
            live_path.as_uri(),
            "--built-from",
            built_from,
            "--run-id",
            "7",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )


def test_pages_build_stamp_wires_the_liveness_branch(tmp_path: Path) -> None:
    """Story 102.3 (from the doctor 48.2 review): the script passes `built_from` and `now`, so an
    identical tree whose live build is over a day old and whose commit moved deploys."""
    from pyforge.steward.pages import tree_hash

    (tmp_path / "probe").mkdir()
    digest = tree_hash(_fixture_tree(tmp_path / "probe"))
    old = {"tree_hash": digest, "built_from": "a" * 40, "run_id": "1", "built_at": "2026-01-01T00:00:00Z"}
    moved = _stamp_with_live(tmp_path / "moved", live=old, built_from="b" * 40)
    assert f"tree_hash={digest}" in moved.stdout
    assert "changed=true" in moved.stdout
    same = _stamp_with_live(tmp_path / "same", live=old, built_from="a" * 40)
    assert "changed=false" in same.stdout


def test_tree_hash_drops_only_the_exact_built_from_element(tmp_path: Path) -> None:
    """Herald Story 43.5's review: only the element herald emits (and ``pages-check`` enforces) loses its text. An
    element that merely mentions the name in a value, carries a longer attribute name, or orders its attributes
    otherwise keeps its text in the hash -- a change there redeploys rather than hiding."""
    from pyforge.steward.pages import tree_hash

    root = _fixture_tree(tmp_path)
    page = root / "index.html"
    shapes = [
        '<a href="#data-pages-built-from">{}</a>',
        '<p title="see data-pages-built-from">{}</p>',
        '<p class="built-from" data-pages-built-from-x data-pagefind-ignore>{}</p>',
        '<p data-pages-built-from class="built-from" data-pagefind-ignore>{}</p>',
        '<span class="built-from" data-pages-built-from data-pagefind-ignore>{}</span>',
    ]
    for shape in shapes:
        page.write_text(f"<html>{shape.format('REAL TEXT')}</html>", encoding="utf-8")
        before = tree_hash(root)
        page.write_text(f"<html>{shape.format('OTHER TEXT')}</html>", encoding="utf-8")
        assert tree_hash(root) != before, shape
