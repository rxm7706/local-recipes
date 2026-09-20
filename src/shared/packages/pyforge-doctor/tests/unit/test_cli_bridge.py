"""Unit tests for ``pyforge.doctor.cli_bridge`` (Story 2.1, AD-5) -- the
sole sanctioned subprocess site. Covers: success, script missing, non-zero
exit, timeout, unparseable JSON, argv-as-a-list (no shell interpretation),
and the ``NO_COLOR=1`` environment contract.

Story 9.2 adds ``run_git``'s ``ok_exit_codes`` param (Story 11.3 is its first
real caller, in sources/chain.py) -- covered against a REAL tmp git
repository (this test file is not restricted to ``cli_bridge.py`` itself; a
test file driving real ``git`` to set up a fixture is fine, mirrors
``test_sources_ledger.py``'s own precedent)."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from pyforge.doctor.cli_bridge import CliBridgeError, run_cli_json, run_git, run_pytest


def _write_script(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "script.py"
    script.write_text(textwrap.dedent(body), encoding="utf-8")
    return script


def test_success_returns_parsed_json(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        import json, sys
        print(json.dumps({"ok": True, "argv": sys.argv[1:]}))
        """,
    )
    result = run_cli_json(script, ["--json", "--limit", "5"], timeout=10)
    assert result == {"ok": True, "argv": ["--json", "--limit", "5"]}


def test_script_missing_raises_cli_bridge_error(tmp_path: Path):
    missing = tmp_path / "does-not-exist.py"
    with pytest.raises(CliBridgeError, match="not found"):
        run_cli_json(missing, ["--json"], timeout=10)


def test_non_zero_exit_raises_cli_bridge_error(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        import sys
        print("boom", file=sys.stderr)
        sys.exit(3)
        """,
    )
    with pytest.raises(CliBridgeError, match="exited 3"):
        run_cli_json(script, ["--json"], timeout=10)


def test_timeout_raises_cli_bridge_error(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        import time
        time.sleep(30)
        """,
    )
    with pytest.raises(CliBridgeError, match="timed out"):
        run_cli_json(script, ["--json"], timeout=0.2)


def test_unparseable_json_raises_cli_bridge_error(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        print("not json at all {{{")
        """,
    )
    with pytest.raises(CliBridgeError, match="unparseable JSON"):
        run_cli_json(script, ["--json"], timeout=10)


def test_argv_is_never_shell_interpreted(tmp_path: Path):
    # A shell-metacharacter-laden argument must arrive at the script
    # LITERALLY -- proof that argv is passed as a list, never through a
    # shell (AD-5's own wording).
    script = _write_script(
        tmp_path,
        """
        import json, sys
        print(json.dumps({"received": sys.argv[1:]}))
        """,
    )
    dangerous = "$(echo pwned); rm -rf /tmp/nonexistent && echo done"
    result = run_cli_json(script, ["--json", dangerous], timeout=10)
    assert result == {"received": ["--json", dangerous]}


def test_no_color_is_set_in_subprocess_environment(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        import json, os
        print(json.dumps({"no_color": os.environ.get("NO_COLOR")}))
        """,
    )
    result = run_cli_json(script, [], timeout=10)
    assert result == {"no_color": "1"}


# --- run_git's ok_exit_codes (Story 9.2) ---------------------------------

# Mirrors test_sources_hygiene.py's own `_isolate_git_env` fixture -- a
# nested worktree's environment (e.g. this very session) can leak any of
# these six vars into a `git` subprocess and point it at the WRONG repo
# instead of the tmp fixture. Review pass 1 found the original three tests
# here only scrubbed 2 of the 6, an inconsistency within this same diff.
_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "doctor-test@example.com"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Doctor Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)


def test_run_git_tolerates_exit_1_when_in_ok_exit_codes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    # `git grep` exits 1 when nothing matches -- must NOT raise here, and the
    # empty stdout must come back rather than being swallowed as an error.
    output = run_git(
        repo,
        ["grep", "-l", "--fixed-strings", "-e", "no-such-string-anywhere"],
        ok_exit_codes=frozenset({0, 1}),
    )
    assert output == ""


def test_run_git_still_raises_for_an_exit_code_outside_the_set(tmp_path: Path) -> None:
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()

    # `git grep` outside any repository exits >=2 -- outside {0, 1}, so this
    # must still raise, exactly like the default (no ok_exit_codes) behavior.
    with pytest.raises(CliBridgeError, match="exited"):
        run_git(
            not_a_repo,
            ["grep", "-l", "--fixed-strings", "-e", "anything"],
            ok_exit_codes=frozenset({0, 1}),
        )


def test_run_git_default_ok_exit_codes_is_unchanged(tmp_path: Path) -> None:
    """Every existing caller (no ``ok_exit_codes`` argument) must keep
    raising on ANY non-zero exit -- the default ``{0}`` preserves that."""
    repo = tmp_path / "empty-repo"
    _init_repo(repo)  # a real repo, but with no commits yet

    with pytest.raises(CliBridgeError, match="exited"):
        run_git(repo, ["rev-parse", "--verify", "--quiet", "HEAD"])


# --- run_pytest (retro action item 3, 2026-09-05) --------------------------


def test_run_pytest_all_passed_returns_zero(tmp_path: Path) -> None:
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    rc, output = run_pytest(Path(sys.executable), tmp_path, ["-q", "-p", "no:cacheprovider"])

    assert rc == 0
    assert "1 passed" in output


def test_run_pytest_some_failed_returns_one_not_raise(tmp_path: Path) -> None:
    (tmp_path / "test_fail.py").write_text("def test_fail():\n    assert False\n", encoding="utf-8")

    rc, output = run_pytest(Path(sys.executable), tmp_path, ["-q", "-p", "no:cacheprovider"])

    assert rc == 1
    assert "1 failed" in output


def test_run_pytest_usage_error_exit_code_raises_cli_bridge_error(tmp_path: Path) -> None:
    # No tests collected at all -> pytest's own exit code 5 -- outside {0, 1}.
    with pytest.raises(CliBridgeError, match="exited 5"):
        run_pytest(Path(sys.executable), tmp_path, ["-q", "-p", "no:cacheprovider"])


def test_run_pytest_launch_failure_raises_cli_bridge_error(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-python"
    with pytest.raises(CliBridgeError, match="failed to launch"):
        run_pytest(missing, tmp_path, ["-q"])
