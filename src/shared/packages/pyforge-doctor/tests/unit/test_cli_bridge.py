"""Unit tests for ``pyforge.doctor.cli_bridge`` (Story 2.1, AD-5) -- the
sole sanctioned subprocess site. Covers: success, script missing, non-zero
exit, timeout, unparseable JSON, argv-as-a-list (no shell interpretation),
the ``NO_COLOR=1`` environment contract, and (Story 11.3) ``run_git``'s
``ok_exit_codes`` parameter."""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

from pyforge.doctor.cli_bridge import CliBridgeError, run_cli_json, run_git

# Story 11.3: the two new run_git tests below drive real git (this test file
# is not subject to the package's sole-subprocess restriction -- only
# pyforge/doctor/cli_bridge.py is), so a contributor's git config (commit
# signing, a global core.hooksPath) or an inherited GIT_DIR must not decide
# whether this suite passes -- mirrors test_sources_marshal_story_status.py's
# own _isolate_git_env/_init_repo pattern.
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


def _init_repo_with_one_commit(target: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "--initial-branch=main"], cwd=target, check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "doctor-test@example.com"],
        cwd=target, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Doctor Test"], cwd=target, check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=target, check=True,
    )
    (target / "file.txt").write_text("hello\n", encoding="utf-8")
    env = dict(os.environ)
    subprocess.run(["git", "add", "file.txt"], cwd=target, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"], cwd=target, env=env, check=True,
    )


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


# --- Story 11.3: run_git's ok_exit_codes parameter --------------------------


def test_run_git_ok_exit_codes_accepts_a_listed_exit_code(tmp_path: Path):
    # `git grep` exits 1 when there are no matches in any file -- a valid,
    # expected outcome, accepted only when explicitly listed.
    _init_repo_with_one_commit(tmp_path)

    out = run_git(
        tmp_path, ["grep", "-n", "-w", "--", "nonexistent_symbol_xyz"],
        ok_exit_codes=frozenset({0, 1}),
    )

    assert out == ""


def test_run_git_still_raises_for_an_unlisted_exit_code(tmp_path: Path):
    # Same call as above, but the default ok_exit_codes ({0}) does not
    # include 1 -- every existing call site's behavior is unaffected by the
    # new parameter's default.
    _init_repo_with_one_commit(tmp_path)

    with pytest.raises(CliBridgeError, match="exited 1"):
        run_git(tmp_path, ["grep", "-n", "-w", "--", "nonexistent_symbol_xyz"])
