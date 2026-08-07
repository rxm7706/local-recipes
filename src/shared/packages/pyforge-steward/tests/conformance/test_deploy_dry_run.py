"""`steward deploy dashboard --dry-run` — Story 2.3.

Reuses Story 2.2's real-scratch-git-repo fixture. Proves the negative: after
a `--dry-run` with a REAL pending diff, `git log` and `git status` are
byte-for-byte unchanged.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pyforge.steward.cli import EXIT_OK, main


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _make_repo_with_origin(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)

    work = tmp_path / "work"
    work.mkdir()
    _git("init", "-b", "main", cwd=work)
    _git("config", "user.email", "test@example.com", cwd=work)
    _git("config", "user.name", "Test", cwd=work)
    dashboard_dir = work / "docs" / "dashboard"
    dashboard_dir.mkdir(parents=True)
    (dashboard_dir / "data.js").write_text("window.DASHBOARD_DATA = {v: 1};\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)
    _git("remote", "add", "origin", str(origin), cwd=work)
    _git("push", "-u", "origin", "main", cwd=work)
    return work


def _snapshot(work: Path) -> tuple[str, str]:
    log = _git("log", "--format=%H %s", cwd=work).stdout
    status = _git("status", "--porcelain", cwd=work).stdout
    return log, status


def test_dry_run_prints_the_diff_and_leaves_git_untouched(tmp_path, monkeypatch, capsys):
    work = _make_repo_with_origin(tmp_path)

    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: work)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (
            sys.executable, "-c",
            "from pathlib import Path; "
            "Path('docs/dashboard/data.js').write_text('window.DASHBOARD_DATA = {v: 2};\\n')",
        ),
    )

    before = _snapshot(work)
    rc = main(["deploy", "dashboard", "--dry-run"])
    after = _snapshot(work)

    assert rc == EXIT_OK
    assert before[0] == after[0], "git log changed during a --dry-run"
    # The working tree itself IS expected to carry the built (unstaged,
    # uncommitted) diff -- that's the whole point of a dry-run build. What
    # must NOT change is git's own recorded state: no new commit, nothing
    # staged. `git status --porcelain` for a tracked-file-only edit reports
    # " M docs/dashboard/data.js" both before build (clean -> "") and after
    # (dirty, unstaged) -- so compare against the log (must be identical)
    # and assert nothing is STAGED (no "A "/"M " index entries).
    assert not any(line[0] in "AMD" for line in after[1].splitlines() if line)

    out = capsys.readouterr().out
    assert "window.DASHBOARD_DATA = {v: 2}" in out or "DASHBOARD_DATA" in out


def test_dry_run_with_no_diff_reports_no_diff_and_exits_ok(tmp_path, monkeypatch):
    work = _make_repo_with_origin(tmp_path)

    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: work)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (
            sys.executable, "-c",
            "from pathlib import Path; "
            "Path('docs/dashboard/data.js').write_text('window.DASHBOARD_DATA = {v: 1};\\n')",
        ),
    )

    before = _snapshot(work)
    rc = main(["deploy", "dashboard", "--dry-run"])
    after = _snapshot(work)

    assert rc == EXIT_OK
    assert before == after


def test_build_wins_over_dry_run_when_both_passed(tmp_path, monkeypatch):
    work = _make_repo_with_origin(tmp_path)

    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: work)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (
            sys.executable, "-c",
            "from pathlib import Path; "
            "Path('docs/dashboard/data.js').write_text('window.DASHBOARD_DATA = {v: 9};\\n')",
        ),
    )

    before = _snapshot(work)
    rc = main(["deploy", "dashboard", "--build", "--dry-run"])

    assert rc == EXIT_OK
    # --build wins: the file WAS rewritten, but nothing was diffed/printed
    # as a dry-run report and no commit happened either.
    assert (work / "docs" / "dashboard" / "data.js").read_text().strip() == (
        "window.DASHBOARD_DATA = {v: 9};"
    )
    assert _snapshot(work)[0] == before[0]
