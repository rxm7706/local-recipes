"""Story 63.4 (spec-pyforge-steward CAP-5): the four session entry points --
`.claude/hooks/session-start.sh`, `.cursor/environment.json`'s `install`,
`.github/workflows/copilot-setup-steps.yml`, and the Marshal dispatch
preamble (`pyforge-marshal/cli/dispatch.py`) -- must call `steward session
check` and nothing else for session preconditions (vocabulary-one-name-one-
job: one mechanism, many surfaces). This scans each file for the exact
invocation, exactly once, so a second ad hoc precondition check can't creep
in beside it unnoticed.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
INVOCATION = "steward session check"


def test_session_start_hook_calls_session_check_once():
    path = REPO_ROOT / ".claude" / "hooks" / "session-start.sh"
    text = path.read_text(encoding="utf-8")
    command = "pixi run --frozen -e pyforge-guild steward session check"
    assert text.count(command) == 1, f"{path} must run {command!r} exactly once"
    # The hook also logs a one-line notice naming the check on failure -- that's
    # prose about the result, not a second invocation, so INVOCATION alone
    # (without "pixi run") legitimately appears twice.
    assert text.count(INVOCATION) == 2, f"{path}: expected the command plus its one failure-notice mention"


def test_cursor_environment_install_calls_session_check_once():
    path = REPO_ROOT / ".cursor" / "environment.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    install = document["install"]
    assert install.count(INVOCATION) == 1, f"{path}'s install command must call {INVOCATION!r} exactly once"


def test_copilot_setup_steps_calls_session_check_once():
    path = REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    text = path.read_text(encoding="utf-8")
    assert text.count(INVOCATION) == 1, f"{path} must call {INVOCATION!r} exactly once"


def test_marshal_dispatch_preamble_calls_session_check_once():
    path = (
        REPO_ROOT
        / "src"
        / "shared"
        / "packages"
        / "pyforge-marshal"
        / "src"
        / "pyforge"
        / "marshal"
        / "cli"
        / "dispatch.py"
    )
    text = path.read_text(encoding="utf-8")
    argv_literal = '"steward", "session", "check", "--json"'
    assert text.count(argv_literal) == 1, f"{path} must shell 'steward session check --json' exactly once"


def test_session_start_hook_never_fatal_on_a_non_ok_session_check(tmp_path: Path) -> None:
    """Story 63.4 review finding (Verification Gap #2): the hook's own
    comment claims a non-ok ``steward session check`` verdict must not
    abort the ``set -euo pipefail`` script -- but nothing actually executed
    it with a failing check to prove that. This runs the real hook with a
    stub ``pixi`` on PATH whose ``run`` subcommand (the session-check call)
    exits non-zero, and asserts the hook itself still exits 0 and still
    reaches its final "ready" line.
    """
    hook = REPO_ROOT / ".claude" / "hooks" / "session-start.sh"

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_pixi = fake_bin / "pixi"
    fake_pixi.write_text(
        "#!/bin/bash\n"
        'case "$1" in\n'
        "  --version) echo 'pixi 0.0.0-fake' ;;\n"
        "  install) exit 0 ;;\n"
        "  run) exit 1 ;;\n"  # the `steward session check` call: simulate a non-ok verdict
        "  *) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_pixi.chmod(fake_pixi.stat().st_mode | stat.S_IEXEC)

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    pixi_home = tmp_path / "pixi-home"

    env = dict(os.environ)
    env["CLAUDE_CODE_REMOTE"] = "true"
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["PIXI_HOME"] = str(pixi_home)
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
    env.pop("CLAUDE_ENV_FILE", None)
    env.pop("CLAUDE_CODE_CA_BUNDLE", None)

    result = subprocess.run(
        ["bash", str(hook)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"hook must never be fatal on a non-ok session check; stderr={result.stderr!r}"
    assert "steward session check reported findings" in result.stderr
    assert "[session-start] ready: envs=pyforge-guild" in result.stdout
