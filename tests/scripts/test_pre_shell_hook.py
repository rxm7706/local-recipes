"""`.claude/hooks/pre-shell.py` -- the Guild session guardrails (steward Story
63.3, spec-pyforge-steward CAP-5).

Runs under `pixi run -e pyforge-ci pyforge-doctor-scripts-test` (`pytest
tests/scripts -q`), the pure-stdlib leg -- the hook itself is stdlib-only by
design, so this is the right home for its tests (the hook is repo-level, not
a station package).

Two layers:
  * in-process, via a dynamically-loaded copy of the module, for the
    governance/closed-list invariant against the REAL repo's
    `docs/governance/guild-roster.json`;
  * subprocess, feeding realistic Claude Code / Cursor hook JSON on stdin
    against a synthetic throwaway git repo, for every rule's actual
    match/no-match behavior (including git branch/worktree state, which the
    real checkout's branch and worktree-ness must not leak into).
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".claude" / "hooks" / "pre-shell.py"
REAL_ROSTER = REPO_ROOT / "docs" / "governance" / "guild-roster.json"


# --------------------------------------------------------------------------
# In-process module load (for the governance invariant only).
# --------------------------------------------------------------------------


def _load_module():
    spec = importlib.util.spec_from_file_location("pre_shell_hook_under_test", HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses needs this in sys.modules to resolve
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hook_module():
    return _load_module()


def test_matchers_match_the_real_declared_session_denials_exactly(hook_module) -> None:
    """The closed list: every declared id has exactly one matcher, and every
    matcher has exactly one declared id -- checked against the REAL repo
    file, not a fixture copy."""
    real = json.loads(REAL_ROSTER.read_text(encoding="utf-8"))
    declared = {rule["id"] for rule in real["session_denials"]}
    assert set(hook_module.MATCHERS) == declared


def test_load_denial_rules_succeeds_against_the_real_repo(hook_module) -> None:
    rules = hook_module.load_denial_rules(REPO_ROOT)
    assert set(rules) == set(hook_module.MATCHERS)


def test_split_subcommands_recurses_into_bash_dash_c(hook_module) -> None:
    chunks = hook_module.split_subcommands('echo hi && bash -c "npx cowsay hi"')
    assert ["echo", "hi"] in chunks
    assert ["bash", "-c", "npx cowsay hi"] in chunks
    assert ["npx", "cowsay", "hi"] in chunks


# --------------------------------------------------------------------------
# Subprocess-level fixtures: a synthetic repo, isolated from the real one.
# --------------------------------------------------------------------------

_PIXI_TOML = """\
[feature.guild-tasks.tasks.detectors-ci]
cmd = "echo detectors-ci"

[feature.guild-tasks.tasks.story-status-check]
cmd = "echo story-status-check"

[feature.guild-tasks.tasks.mypy]
cmd = "echo mypy"

[feature.local-recipes.tasks.recipe-build]
cmd = "echo recipe-build"

[feature.local-recipes.tasks.resolve-name]
cmd = "echo resolve-name"
"""


def _write_fixture_roster(dest: Path) -> None:
    real = json.loads(REAL_ROSTER.read_text(encoding="utf-8"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"session_denials": real["session_denials"]}), encoding="utf-8")


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture()
def fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-q"], repo)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    (repo / "pixi.toml").write_text(_PIXI_TOML, encoding="utf-8")
    _write_fixture_roster(repo / "docs" / "governance" / "guild-roster.json")
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir()
    shutil.copy(REPO_ROOT / "scripts" / "commit_msg_hook.py", scripts_dir / "commit_msg_hook.py")
    (repo / "src").mkdir()
    (repo / "src" / "foo.py").write_text("print('hi')\n", encoding="utf-8")
    (repo / "subdir").mkdir()
    _git(["add", "-A"], repo)
    _git(["commit", "-q", "-m", "init"], repo)
    return repo


@pytest.fixture()
def fake_worktree(fake_repo: Path, tmp_path: Path) -> Path:
    wt = tmp_path / "repo-wt"
    _git(["worktree", "add", "-q", "-b", "feature-x", str(wt)], fake_repo)
    return wt


def _track_file(repo: Path, rel: str, content: str = "x: 1\n") -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(["add", rel], repo)
    _git(["commit", "-q", "-m", f"add {rel}"], repo)
    return path


# --------------------------------------------------------------------------
# Hook invocation helpers.
# --------------------------------------------------------------------------


def _run(payload: dict[str, Any], cwd: Path, env_extra: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("BMAD_ACTIVE_PROJECT", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _claude_bash(command: str, cwd: Path) -> dict[str, Any]:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(cwd),
    }


def _claude_write(file_path: str, cwd: Path) -> dict[str, Any]:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "x"},
        "cwd": str(cwd),
    }


def _cursor_bash(command: str, cwd: Path) -> dict[str, Any]:
    return {"hook_event_name": "beforeShellExecution", "command": command, "cwd": str(cwd)}


def _cursor_after_edit(file_path: str, cwd: Path) -> dict[str, Any]:
    return {
        "hook_event_name": "afterFileEdit",
        "file_path": file_path,
        "edits": [{"old_string": "a", "new_string": "b"}],
        "cwd": str(cwd),
    }


def _claude_deny_reason(result: subprocess.CompletedProcess) -> Optional[str]:
    out = result.stdout.strip()
    if not out:
        return None
    data = json.loads(out)
    hso = data.get("hookSpecificOutput", {})
    return hso.get("permissionDecisionReason") if hso.get("permissionDecision") == "deny" else None


def _cursor_deny_reason(result: subprocess.CompletedProcess) -> Optional[str]:
    out = result.stdout.strip()
    if not out:
        return None
    data = json.loads(out)
    return data.get("user_message") if data.get("permission") == "deny" else None


# --------------------------------------------------------------------------
# Rule 1: guild-task-via-local-recipes
# --------------------------------------------------------------------------


def test_guild_task_via_local_recipes_denied(fake_repo: Path) -> None:
    result = _run(_claude_bash("pixi run -e local-recipes detectors-ci", fake_repo), fake_repo)
    assert result.returncode == 0
    reason = _claude_deny_reason(result)
    assert reason is not None
    assert "pyforge-guild detectors-ci" in reason


def test_guild_task_via_pyforge_guild_allowed(fake_repo: Path) -> None:
    result = _run(_claude_bash("pixi run -e pyforge-guild detectors-ci", fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_non_guild_task_via_local_recipes_allowed(fake_repo: Path) -> None:
    result = _run(_claude_bash("pixi run -e local-recipes recipe-build", fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_guild_task_name_as_argument_not_task_position_allowed(fake_repo: Path) -> None:
    """`resolve-name` is the real local-recipes-only task; `mypy` is just a
    positional argument value that happens to equal a Guild task's name --
    only the task-name position (the first non-flag token) is checked."""
    result = _run(_claude_bash("pixi run -e local-recipes resolve-name mypy", fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# --------------------------------------------------------------------------
# Rule 2: adhoc-package-install
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "pip install requests",
        "uv pip install requests",
        "conda install -y numpy",
        "mamba install -y numpy",
        "micromamba install -y numpy",
        "npx cowsay hi",
        "./node_modules/.bin/npx cowsay hi",
        "/usr/bin/npx cowsay hi",
        "python -m pip install requests",
        "python3.14 -m pip install requests",
    ],
)
def test_adhoc_install_denied(fake_repo: Path, command: str) -> None:
    result = _run(_claude_bash(command, fake_repo), fake_repo)
    assert _claude_deny_reason(result) is not None


def test_npx_skills_add_allowed(fake_repo: Path) -> None:
    result = _run(_claude_bash("npx skills add pyforge-atlas", fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# --------------------------------------------------------------------------
# Rule 3: pixi-add-or-update
# --------------------------------------------------------------------------


@pytest.mark.parametrize("command", ["pixi add numpy", "pixi update"])
def test_pixi_add_or_update_denied(fake_repo: Path, command: str) -> None:
    result = _run(_claude_bash(command, fake_repo), fake_repo)
    assert _claude_deny_reason(result) is not None


def test_pixi_task_add_allowed(fake_repo: Path) -> None:
    result = _run(_claude_bash("pixi task add foo 'echo hi'", fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# --------------------------------------------------------------------------
# Rule 4: bmad-switch-unsafe
# --------------------------------------------------------------------------


def test_bmad_switch_denied_with_active_project_env(fake_repo: Path) -> None:
    result = _run(
        _claude_bash("scripts/bmad-switch pyforge-doctor", fake_repo),
        fake_repo,
        env_extra={"BMAD_ACTIVE_PROJECT": "pyforge-doctor"},
    )
    assert _claude_deny_reason(result) is not None


def test_bmad_switch_denied_in_worktree(fake_worktree: Path) -> None:
    result = _run(_claude_bash("scripts/bmad-switch pyforge-doctor", fake_worktree), fake_worktree)
    assert _claude_deny_reason(result) is not None


def test_bmad_switch_allowed_from_primary_checkout_no_env(fake_repo: Path) -> None:
    result = _run(_claude_bash("scripts/bmad-switch pyforge-doctor", fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_bmad_switch_denied_with_active_project_env_set_but_empty(fake_repo: Path) -> None:
    """`BMAD_ACTIVE_PROJECT=""` is present, not absent -- presence, not
    truthiness, is what matters."""
    result = _run(
        _claude_bash("scripts/bmad-switch pyforge-doctor", fake_repo),
        fake_repo,
        env_extra={"BMAD_ACTIVE_PROJECT": ""},
    )
    assert _claude_deny_reason(result) is not None


# --------------------------------------------------------------------------
# Rule 5: git-commit-guardrail
# --------------------------------------------------------------------------


def test_git_commit_denied_on_primary_checkout(fake_repo: Path) -> None:
    result = _run(_claude_bash('git commit -m "fix: something"', fake_repo), fake_repo)
    reason = _claude_deny_reason(result)
    assert reason is not None
    assert "primary checkout" in reason or "main" in reason


def test_git_commit_allowed_in_worktree_off_main_clean_message(fake_worktree: Path) -> None:
    result = _run(_claude_bash('git commit -m "fix: something"', fake_worktree), fake_worktree)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_git_commit_denied_for_co_authored_by(fake_worktree: Path) -> None:
    command = 'git commit -m "fix: something" -m "Co-Authored-By: Claude <noreply@anthropic.com>"'
    result = _run(_claude_bash(command, fake_worktree), fake_worktree)
    reason = _claude_deny_reason(result)
    assert reason is not None
    assert "Co-Authored-By" in reason or "attribution" in reason


def test_git_commit_denied_for_ai_attribution_line(fake_worktree: Path) -> None:
    command = (
        'git commit -m "fix: something" '
        '-m "Generated with [Claude Code](https://claude.com/claude-code)"'
    )
    result = _run(_claude_bash(command, fake_worktree), fake_worktree)
    assert _claude_deny_reason(result) is not None


def test_git_commit_denied_for_bundled_dash_am_attribution(fake_worktree: Path) -> None:
    """`-am` (bundled `-a` + `-m`) must be recognized the same as bare `-m`."""
    command = (
        'git commit -am "fix: something\n\n'
        'Co-Authored-By: Claude <noreply@anthropic.com>"'
    )
    result = _run(_claude_bash(command, fake_worktree), fake_worktree)
    reason = _claude_deny_reason(result)
    assert reason is not None
    assert "Co-Authored-By" in reason or "attribution" in reason


def test_git_commit_denied_for_heredoc_embedded_attribution(fake_worktree: Path) -> None:
    """A quoted, multi-line `-m` argument (e.g. `-m "$(cat <<'EOF' ... EOF)"`)
    must not be shattered by the `;`/newline separator split before the
    attribution line inside it is ever seen."""
    command = (
        "git commit -m \"$(cat <<'EOF'\n"
        "fix: something\n"
        "\n"
        "Co-Authored-By: Claude <noreply@anthropic.com>\n"
        "EOF\n"
        ')"'
    )
    result = _run(_claude_bash(command, fake_worktree), fake_worktree)
    reason = _claude_deny_reason(result)
    assert reason is not None
    assert "Co-Authored-By" in reason or "attribution" in reason


# --------------------------------------------------------------------------
# Rule 6: gh-pr-merge-squash
# --------------------------------------------------------------------------


def test_gh_pr_merge_squash_denied(fake_repo: Path) -> None:
    result = _run(_claude_bash("gh pr merge 123 --squash", fake_repo), fake_repo)
    assert _claude_deny_reason(result) is not None


def test_gh_pr_merge_dashmerge_allowed(fake_repo: Path) -> None:
    result = _run(_claude_bash("gh pr merge 123 --merge", fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# --------------------------------------------------------------------------
# Rule 7: gh-pr-create-missing-repo
# --------------------------------------------------------------------------


def test_gh_pr_create_without_repo_denied(fake_repo: Path) -> None:
    result = _run(_claude_bash('gh pr create --title x --body y', fake_repo), fake_repo)
    assert _claude_deny_reason(result) is not None


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --repo rxm7706/local-recipes --title x --body y",
        "gh pr create --repo=rxm7706/local-recipes --title x --body y",
    ],
)
def test_gh_pr_create_with_repo_allowed(fake_repo: Path, command: str) -> None:
    result = _run(_claude_bash(command, fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# --------------------------------------------------------------------------
# Rule 8: uv-run-outside-repo-root
# --------------------------------------------------------------------------


def test_uv_run_at_repo_root_allowed(fake_repo: Path) -> None:
    result = _run(_claude_bash("uv run pytest", fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_uv_run_outside_repo_root_denied(fake_repo: Path) -> None:
    subdir = fake_repo / "subdir"
    result = _run(_claude_bash("uv run pytest", subdir), subdir)
    assert _claude_deny_reason(result) is not None


# --------------------------------------------------------------------------
# Rule 9: spec-surface-bare-write-baseline
# --------------------------------------------------------------------------


def test_spec_surface_bare_write_baseline_denied(fake_repo: Path) -> None:
    result = _run(
        _claude_bash("python scripts/spec_surface_check.py --write-baseline", fake_repo),
        fake_repo,
    )
    assert _claude_deny_reason(result) is not None


def test_spec_surface_scoped_write_baseline_allowed(fake_repo: Path) -> None:
    command = (
        "python scripts/spec_surface_check.py --write-baseline "
        "--spec pyforge-steward/spec-63-3-one-deny-list-one-hook"
    )
    result = _run(_claude_bash(command, fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_spec_surface_module_invocation_bare_write_baseline_denied(fake_repo: Path) -> None:
    """`python -m scripts.spec_surface_check` (no `.py` suffix) must be
    recognized the same as the file-path invocation."""
    result = _run(
        _claude_bash("python -m scripts.spec_surface_check --write-baseline", fake_repo),
        fake_repo,
    )
    assert _claude_deny_reason(result) is not None


# --------------------------------------------------------------------------
# Rule 10: direct-write-governed-path (Edit/Write only)
# --------------------------------------------------------------------------


def test_direct_write_to_spec_md_denied(fake_repo: Path) -> None:
    target = str(fake_repo / "_bmad-output" / "projects" / "x" / "planning-artifacts" / "specs" / "spec-y" / "SPEC.md")
    result = _run(_claude_write(target, fake_repo), fake_repo)
    reason = _claude_deny_reason(result)
    assert reason is not None
    assert "memlog.py" in reason


def test_direct_write_to_sprint_status_ledger_denied(fake_repo: Path) -> None:
    target = str(fake_repo / "_bmad-output" / "projects" / "x" / "planning-artifacts" / "sprint-status-ledger.yaml")
    result = _run(_claude_write(target, fake_repo), fake_repo)
    reason = _claude_deny_reason(result)
    assert reason is not None
    assert "sprint-ledger-sync" in reason


def test_direct_write_to_tracked_implementation_artifacts_denied(fake_repo: Path) -> None:
    tracked = _track_file(fake_repo, "_bmad-output/projects/x/implementation-artifacts/note.yaml")
    result = _run(_claude_write(str(tracked), fake_repo), fake_repo)
    reason = _claude_deny_reason(result)
    assert reason is not None
    assert "implementation-artifacts" in reason


def test_direct_write_to_untracked_implementation_artifacts_allowed(fake_repo: Path) -> None:
    target = fake_repo / "_bmad-output" / "projects" / "x" / "implementation-artifacts" / "scratch.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("scratch\n", encoding="utf-8")
    result = _run(_claude_write(str(target), fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_direct_write_to_ordinary_file_allowed(fake_repo: Path) -> None:
    result = _run(_claude_write(str(fake_repo / "src" / "foo.py"), fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_direct_write_to_unrelated_spec_md_allowed(fake_repo: Path) -> None:
    """A file named exactly `SPEC.md` outside the
    `_bmad-output/projects/*/planning-artifacts/` tree is not governed --
    basename alone is not enough."""
    target = str(fake_repo / "src" / "SPEC.md")
    result = _run(_claude_write(target, fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_notebook_edit_to_spec_md_denied(fake_repo: Path) -> None:
    """`NotebookEdit` (carries `notebook_path`, not `file_path`) must be
    covered the same as Edit/Write."""
    target = str(
        fake_repo / "_bmad-output" / "projects" / "x" / "planning-artifacts" / "specs" / "spec-y" / "SPEC.md"
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "NotebookEdit",
        "tool_input": {"notebook_path": target, "new_source": "x", "cell_type": "code"},
        "cwd": str(fake_repo),
    }
    result = _run(payload, fake_repo)
    reason = _claude_deny_reason(result)
    assert reason is not None
    assert "memlog.py" in reason


# --------------------------------------------------------------------------
# Never denies anything not on the list.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "git status",
        "pip show requests",
        "gh pr view 123",
        "pixi run -e pyforge-guild story-status-check",
    ],
)
def test_benign_commands_never_denied(fake_repo: Path, command: str) -> None:
    result = _run(_claude_bash(command, fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_unrelated_claude_tool_is_a_no_op(fake_repo: Path) -> None:
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": str(fake_repo / "src" / "foo.py")},
        "cwd": str(fake_repo),
    }
    result = _run(payload, fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# --------------------------------------------------------------------------
# Cursor wire format.
# --------------------------------------------------------------------------


def test_cursor_before_shell_execution_deny_shape(fake_repo: Path) -> None:
    result = _run(_cursor_bash("pixi add numpy", fake_repo), fake_repo)
    reason = _cursor_deny_reason(result)
    assert reason is not None
    data = json.loads(result.stdout.strip())
    assert set(data) == {"permission", "user_message", "agent_message"}


def test_cursor_before_shell_execution_allow_is_silent(fake_repo: Path) -> None:
    result = _run(_cursor_bash("ls -la", fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_cursor_after_file_edit_warns_not_denies(fake_repo: Path) -> None:
    target = str(fake_repo / "_bmad-output" / "projects" / "x" / "planning-artifacts" / "specs" / "spec-y" / "SPEC.md")
    result = _run(_cursor_after_edit(target, fake_repo), fake_repo)
    # No output-based deny/message capability on afterFileEdit -- the signal
    # is stderr + non-zero exit, never a blocking stdout decision.
    assert result.stdout.strip() == ""
    assert result.returncode == 1
    assert "memlog.py" in result.stderr


def test_cursor_after_file_edit_ordinary_file_is_silent(fake_repo: Path) -> None:
    result = _run(_cursor_after_edit(str(fake_repo / "src" / "foo.py"), fake_repo), fake_repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


# --------------------------------------------------------------------------
# Fail loud, never a silent skip.
# --------------------------------------------------------------------------


def test_missing_session_denials_fails_loud(fake_repo: Path) -> None:
    roster = fake_repo / "docs" / "governance" / "guild-roster.json"
    roster.write_text(json.dumps({"stations": ["marshal"]}), encoding="utf-8")
    result = _run(_claude_bash("ls -la", fake_repo), fake_repo)
    # Exit code 2 specifically -- Claude Code's PreToolUse contract only
    # blocks the tool call on exit 2; any other non-zero exit is non-blocking
    # and the command would proceed despite the governance-file integrity
    # failure.
    assert result.returncode == 2
    assert "session_denials" in result.stderr


def test_drifted_session_denials_fails_loud(fake_repo: Path) -> None:
    real = json.loads(REAL_ROSTER.read_text(encoding="utf-8"))
    denials = [rule for rule in real["session_denials"] if rule["id"] != "pixi-add-or-update"]
    roster = fake_repo / "docs" / "governance" / "guild-roster.json"
    roster.write_text(json.dumps({"session_denials": denials}), encoding="utf-8")
    result = _run(_claude_bash("ls -la", fake_repo), fake_repo)
    assert result.returncode == 2
    assert "drifted" in result.stderr
