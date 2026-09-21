#!/usr/bin/env python3
"""One deny list, one hook -- the Guild session guardrails, enforced not asserted.

(steward Story 63.3, spec-pyforge-steward CAP-5)

WHAT THIS IS. A repo-level `PreToolUse` guard for the ten AGENTS.md/CLAUDE.md
session rules that were previously prose only. Registered on `Bash` and on
`Edit`/`Write`/`NotebookEdit` in `.claude/settings.json` (Claude Code) and on
`beforeShellExecution` / `afterFileEdit` in `.cursor/hooks.json` (Cursor) --
THE SAME FILE serves both harnesses; each hook config just points its own
harness's event(s) at this one script, and this script tells the two apart by
the shape of the JSON on stdin (see `detect()`).

Gemini CLI, GitHub Copilot CLI and Devin have no verified deny surface for
this hook -- for them the ten rules stay instruction-only, as written in
AGENTS.md (see AGENTS.md's own "Session guardrails" section; do not assume
this script runs there).

THE CLOSED LIST. `docs/governance/guild-roster.json`'s `session_denials`
array is the ONE declared source of what this hook denies and the one-line
reason it gives for each -- naming the sanctioned form. Adding a denial is a
governance act on that file, never a bare code change here. `MATCHERS` below
must carry exactly one callable per declared rule id, in both directions --
`load_denial_rules()` asserts that at every run and raises (loud, not a
silent skip) on any drift between the two.

Cursor's `afterFileEdit` has no permission/deny or message-injection output
in its current schema (checked live against https://cursor.com/docs/agent/hooks,
2026-09-20), and Cursor has no "before write" event for file edits at all --
so the file rule there is necessarily a post-hoc WARN: a clear message on
stderr plus a non-zero exit (visible in Cursor's own hook log), not a block.
On Claude Code, by contrast, `Edit`/`Write`/`NotebookEdit` are `PreToolUse`-gated,
so this script denies the edit outright before it lands.

FAIL LOUD, NEVER SILENT SKIP. A governance-file integrity problem (a missing
`session_denials` list, a rule id with no matcher or a matcher with no rule
id) raises and is surfaced via the top-level handler; the tool call itself is
never silently allowed to slip through unexamined for reasons internal to
this script. An unmatched command is not a "skip" -- it is simply not on the
closed list, and prints nothing (the harness's own permission system decides
as it always did).

This file is intentionally stdlib-only (json/re/shlex/subprocess/tomllib) --
it has to run bare via `python3`, outside any pixi environment, on whatever
interpreter launched the agent.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

# --------------------------------------------------------------------------
# Context: the normalized view of "what is this tool call" both harnesses'
# hook payloads collapse into before any rule runs.
# --------------------------------------------------------------------------


@dataclass
class Context:
    harness: str  # "claude" | "cursor"
    kind: str  # "bash" | "edit_write"
    command: Optional[str]
    subcommands: list[list[str]] = field(default_factory=list)
    file_path: Optional[str] = None
    cwd: str = "."
    repo_root: Path = field(default_factory=Path)


def detect(payload: dict[str, Any]) -> tuple[str, str]:
    """Return (harness, kind) for the hook payload on stdin.

    Claude Code's `PreToolUse` wraps everything in `tool_name`/`tool_input`;
    Cursor's `beforeShellExecution`/`afterFileEdit` are flat, keyed off
    `hook_event_name`. `kind` is "other" for anything neither harness's
    session-guardrail surface covers (e.g. Claude's Read, Cursor's
    sessionStart) -- `main()` no-ops on "other" without evaluating any rule.
    """
    event = payload.get("hook_event_name")
    if event == "PreToolUse":
        tool_name = payload.get("tool_name")
        if tool_name == "Bash":
            return "claude", "bash"
        if tool_name in ("Edit", "Write", "NotebookEdit"):
            return "claude", "edit_write"
        return "claude", "other"
    if event == "beforeShellExecution":
        return "cursor", "bash"
    if event == "afterFileEdit":
        return "cursor", "edit_write"
    return "unknown", "other"


def build_context(harness: str, kind: str, payload: dict[str, Any]) -> Context:
    command: Optional[str] = None
    file_path: Optional[str] = None

    if harness == "claude":
        cwd = payload.get("cwd") or os.getcwd()
        tool_input = payload.get("tool_input") or {}
        if kind == "bash":
            command = tool_input.get("command")
        else:
            # Edit/Write carry `file_path`; NotebookEdit carries `notebook_path`.
            file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    else:  # cursor
        roots = payload.get("workspace_roots") or []
        cwd = payload.get("cwd") or (roots[0] if roots else os.getcwd())
        if kind == "bash":
            command = payload.get("command")
        else:
            file_path = payload.get("file_path")

    subcommands = split_subcommands(command) if command else []
    repo_root = find_repo_root(cwd)
    return Context(
        harness=harness,
        kind=kind,
        command=command,
        subcommands=subcommands,
        file_path=file_path,
        cwd=cwd,
        repo_root=repo_root,
    )


# --------------------------------------------------------------------------
# Command tokenization -- heuristic, not a shell. Good enough to recognize
# the ten named forms; not a sandbox and not trying to be one.
# --------------------------------------------------------------------------


def _tokenize(chunk: str) -> list[str]:
    try:
        return shlex.split(chunk)
    except ValueError:
        return chunk.split()


def _split_respecting_quotes(command: str) -> list[str]:
    """Split on `&&`, `||`, `;`, `|` and newlines -- but never inside a
    single- or double-quoted span. A regex-only split (matching on the raw
    characters) shatters a quoted multi-line argument -- e.g. a heredoc
    embedded in `-m "$(cat <<'EOF' ... EOF)"` -- into unrelated fragments,
    which drops the rest of the argument (including an attribution line)
    from the chunk `match_git_commit_guardrail` ever sees.
    """
    parts: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        if in_single:
            buf.append(ch)
            in_single = ch != "'"
            i += 1
            continue
        if in_double:
            if ch == "\\" and i + 1 < n:
                buf.append(ch)
                buf.append(command[i + 1])
                i += 2
                continue
            buf.append(ch)
            if ch == '"':
                in_double = False
            i += 1
            continue
        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue
        if ch == '"':
            in_double = True
            buf.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            buf.append(ch)
            buf.append(command[i + 1])
            i += 2
            continue
        two = command[i : i + 2]
        if two in ("&&", "||"):
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        if ch in (";", "\n", "|"):
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def split_subcommands(command: str) -> list[list[str]]:
    """Split a shell command into per-subcommand token lists.

    Splits on `&&`, `||`, `;`, `|` and newlines (quote-aware -- see
    `_split_respecting_quotes`), then also recurses into `bash -c "..."` /
    `sh -c "..."` / `zsh -c "..."` payloads so a wrapped inner command is
    still visible to the rule matchers.
    """
    chunks = _split_respecting_quotes(command)
    result: list[list[str]] = []
    for chunk in chunks:
        tokens = _tokenize(chunk)
        if not tokens:
            continue
        result.append(tokens)
        if len(tokens) >= 3 and tokens[0] in ("bash", "sh", "zsh") and tokens[1] == "-c":
            result.extend(split_subcommands(tokens[2]))
    return result


def _contains(tokens: list[str], seq: list[str]) -> bool:
    n = len(seq)
    return any(tokens[i : i + n] == seq for i in range(len(tokens) - n + 1))


# --------------------------------------------------------------------------
# Small git/pixi helpers, all defensive: a subprocess failure degrades a
# single check to "no evidence of a match", never a script crash.
# --------------------------------------------------------------------------


def _git(args: list[str], cwd: str) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def find_repo_root(cwd: str) -> Path:
    top = _git(["rev-parse", "--show-toplevel"], cwd)
    if top:
        return Path(top)
    # Fallback: this script lives at <repo_root>/.claude/hooks/pre-shell.py.
    return Path(__file__).resolve().parents[2]


def is_worktree(cwd: str) -> bool:
    common = _git(["rev-parse", "--git-common-dir"], cwd)
    gitdir = _git(["rev-parse", "--git-dir"], cwd)
    if common is None or gitdir is None:
        return False
    common_abs = os.path.normpath(os.path.join(cwd, common))
    gitdir_abs = os.path.normpath(os.path.join(cwd, gitdir))
    return common_abs != gitdir_abs


def get_branch(cwd: str) -> Optional[str]:
    return _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)


def git_checkout_state(cwd: str) -> Optional[tuple[str, bool]]:
    """Return (branch, is_worktree), or None when `cwd` is not a git repo at
    all -- callers must treat None as "unknown", never as "primary
    checkout"."""
    branch = get_branch(cwd)
    if branch is None:
        return None
    return branch, is_worktree(cwd)


def is_tracked(repo_root: Path, path: str) -> bool:
    try:
        out = subprocess.run(
            ["git", "ls-files", "--error-unmatch", path],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0


def get_guild_tasks(repo_root: Path) -> set[str]:
    """The `guild-tasks` set, read live from pixi.toml -- never a copy.

    Raises (fail loud) rather than degrading to an empty set: an empty set
    would silently disable the guild-task-via-local-recipes rule for every
    command instead of surfacing that pixi.toml could not be read.
    """
    pixi_toml = repo_root / "pixi.toml"
    if not pixi_toml.is_file():
        raise RuntimeError(
            f"cannot evaluate the guild-task rule: {pixi_toml} not found"
        )
    data = tomllib.loads(pixi_toml.read_text(encoding="utf-8"))
    tasks = data.get("feature", {}).get("guild-tasks", {}).get("tasks", {})
    if not tasks:
        raise RuntimeError(
            f"cannot evaluate the guild-task rule: no [feature.guild-tasks.tasks] in {pixi_toml}"
        )
    return set(tasks.keys())


_COMMIT_MSG_HOOK_CACHE: dict[Path, Any] = {}


def _commit_msg_hook(repo_root: Path):
    """Dynamically load `scripts/commit_msg_hook.py` from the target repo.

    Reused rather than reimplemented so the two enforcement points (this
    hook, pre-emptive; the `commit-msg` git hook, authoritative) can never
    drift on what counts as an AI-attribution line.
    """
    cached = _COMMIT_MSG_HOOK_CACHE.get(repo_root)
    if cached is not None:
        return cached
    path = repo_root / "scripts" / "commit_msg_hook.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_pre_shell_commit_msg_hook", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _COMMIT_MSG_HOOK_CACHE[repo_root] = module
    return module


_BUNDLED_SHORT_M_RE = re.compile(r"^-[a-zA-Z]*m$")


def _extract_commit_message(tokens: list[str], cwd: str) -> Optional[str]:
    parts: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        # `-m`/`--message`, and a bundled short-option cluster ending in `m`
        # (e.g. `-am`) -- git accepts either, and `-am` is the common form.
        if tok in ("-m", "--message") or _BUNDLED_SHORT_M_RE.fullmatch(tok):
            if i + 1 < len(tokens):
                parts.append(tokens[i + 1])
            i += 2
            continue
        if tok.startswith("--message="):
            parts.append(tok.split("=", 1)[1])
            i += 1
            continue
        if tok in ("-F", "--file"):
            if i + 1 < len(tokens):
                parts.append(_read_message_file(tokens[i + 1], cwd))
            i += 2
            continue
        if tok.startswith("--file="):
            parts.append(_read_message_file(tok.split("=", 1)[1], cwd))
            i += 1
            continue
        i += 1
    parts = [p for p in parts if p]
    return "\n".join(parts) if parts else None


def _read_message_file(name: str, cwd: str) -> str:
    if name == "-":
        return ""
    path = Path(name)
    if not path.is_absolute():
        path = Path(cwd) / path
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# --------------------------------------------------------------------------
# Rule matchers -- one per `session_denials` id, dispatched by id via
# MATCHERS below. Each returns a reason string (naming the sanctioned form)
# on a match, or None.
# --------------------------------------------------------------------------


def _pixi_run_env(tokens: list[str]) -> tuple[Optional[str], list[str]]:
    """For `['pixi', 'run', ...]`, return (environment, other positional tokens)."""
    env: Optional[str] = None
    rest: list[str] = []
    i = 2
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("-e", "--environment"):
            if i + 1 < len(tokens):
                env = tokens[i + 1]
            i += 2
            continue
        if tok.startswith("--environment="):
            env = tok.split("=", 1)[1]
            i += 1
            continue
        if tok.startswith("-e") and len(tok) > 2:
            env = tok[2:]
            i += 1
            continue
        rest.append(tok)
        i += 1
    return env, rest


def match_guild_task_via_local_recipes(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for tokens in ctx.subcommands:
        if len(tokens) < 2 or tokens[0] != "pixi" or tokens[1] != "run":
            continue
        env, rest = _pixi_run_env(tokens)
        if env != "local-recipes":
            continue
        # Only the task-name position (the first non-flag positional token)
        # is checked -- anything after it is an argument TO that task, which
        # can coincidentally equal a Guild task's name (e.g. `resolve-name
        # mypy`) without meaning "run mypy".
        task = next((tok for tok in rest if not tok.startswith("-")), None)
        if task is None:
            continue
        guild_tasks = get_guild_tasks(ctx.repo_root)
        if task in guild_tasks:
            return str(rule["reason"]).format(task=task)
    return None


_PY_INTERPRETER_RE = re.compile(r"python3?(\.\d+)?")


def _has_python_pip_install(tokens: list[str]) -> bool:
    """`python`/`python3`/`python3.14`/... `-m pip install` -- version-tolerant
    so a Python invoked by its exact pinned minor version is still caught."""
    for i in range(len(tokens) - 3):
        if (
            _PY_INTERPRETER_RE.fullmatch(tokens[i])
            and tokens[i + 1] == "-m"
            and tokens[i + 2] == "pip"
            and tokens[i + 3] == "install"
        ):
            return True
    return False


def match_adhoc_package_install(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for tokens in ctx.subcommands:
        # Basename-lowered: `npx` invoked as `/usr/bin/npx` or
        # `./node_modules/.bin/npx` must be recognized the same as bare `npx`.
        low = [Path(t).name.lower() for t in tokens]
        if (
            _contains(low, ["pip", "install"])
            or _contains(low, ["pip3", "install"])
            or _contains(low, ["uv", "pip", "install"])
            or _contains(low, ["conda", "install"])
            or _contains(low, ["mamba", "install"])
            or _contains(low, ["micromamba", "install"])
            or _has_python_pip_install(low)
        ):
            return str(rule["reason"])
        if "npx" in low:
            idx = low.index("npx")
            following = [t for t in low[idx + 1 :] if not t.startswith("-")]
            if following[:2] != ["skills", "add"]:
                return str(rule["reason"])
    return None


def match_pixi_add_or_update(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for tokens in ctx.subcommands:
        if len(tokens) >= 2 and tokens[0] == "pixi" and tokens[1] in ("add", "update"):
            return str(rule["reason"])
    return None


def match_bmad_switch_unsafe(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for tokens in ctx.subcommands:
        hit = any(
            tok == "bmad-switch" or tok.endswith("/bmad-switch") for tok in tokens
        )
        if not hit:
            continue
        if "BMAD_ACTIVE_PROJECT" in os.environ or is_worktree(ctx.cwd):
            return str(rule["reason"])
    return None


def match_git_commit_guardrail(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    reasons = rule["reason"]
    for tokens in ctx.subcommands:
        if len(tokens) < 2 or tokens[0] != "git" or tokens[1] != "commit":
            continue
        state = git_checkout_state(ctx.cwd)
        if state is not None:
            branch, in_worktree = state
            if branch == "main" or not in_worktree:
                return str(reasons["checkout"])
        message = _extract_commit_message(tokens, ctx.cwd)
        if message:
            hook = _commit_msg_hook(ctx.repo_root)
            if hook is not None and hook.offending_lines(message):
                return str(reasons["attribution"])
    return None


def match_gh_pr_merge_squash(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for tokens in ctx.subcommands:
        if _contains(tokens, ["gh", "pr", "merge"]) and (
            "--squash" in tokens or "-s" in tokens
        ):
            return str(rule["reason"])
    return None


def match_gh_pr_create_missing_repo(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for tokens in ctx.subcommands:
        if not _contains(tokens, ["gh", "pr", "create"]):
            continue
        has_repo = False
        for i, tok in enumerate(tokens):
            if tok in ("-R", "--repo") and i + 1 < len(tokens):
                if tokens[i + 1] == "rxm7706/local-recipes":
                    has_repo = True
            elif tok.startswith("--repo="):
                if tok.split("=", 1)[1] == "rxm7706/local-recipes":
                    has_repo = True
        if not has_repo:
            return str(rule["reason"])
    return None


def match_uv_run_outside_repo_root(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for tokens in ctx.subcommands:
        if len(tokens) >= 2 and tokens[0] == "uv" and tokens[1] == "run":
            toplevel = _git(["rev-parse", "--show-toplevel"], ctx.cwd)
            if toplevel is None:
                continue
            # realpath (not abspath): two paths to the same directory reached
            # through different symlinks must compare equal.
            if os.path.realpath(ctx.cwd) != os.path.realpath(toplevel):
                return str(rule["reason"])
    return None


def match_spec_surface_bare_write_baseline(
    ctx: Context, rule: dict[str, Any]
) -> Optional[str]:
    for tokens in ctx.subcommands:
        if not any(
            tok.endswith("spec_surface_check.py")
            or tok in ("spec_surface_check", "scripts.spec_surface_check")
            for tok in tokens
        ):
            continue
        if "--write-baseline" not in tokens:
            continue
        if any(tok == "--spec" or tok.startswith("--spec=") for tok in tokens):
            continue
        return str(rule["reason"])
    return None


def _under_bmad_planning_artifacts(p: Path) -> bool:
    """True if `p` has a `_bmad-output/projects/<slug>/planning-artifacts/...`
    segment anywhere in it -- the shape every governed SPEC.md /
    sprint-status-ledger.yaml lives under. Guards against an unrelated file
    elsewhere in the repo that merely happens to share one of those exact
    basenames."""
    parts = p.parts
    for i in range(len(parts) - 3):
        if (
            parts[i] == "_bmad-output"
            and parts[i + 1] == "projects"
            and parts[i + 3] == "planning-artifacts"
        ):
            return True
    return False


def _resolve_against_cwd(cwd: str, path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else Path(cwd) / p


def match_direct_write_governed_path(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    if ctx.file_path is None:
        return None
    reasons = rule["reason"]
    resolved = _resolve_against_cwd(ctx.cwd, ctx.file_path)
    if resolved.name == "SPEC.md" and _under_bmad_planning_artifacts(resolved):
        return str(reasons["spec_md"])
    if resolved.name == "sprint-status-ledger.yaml" and _under_bmad_planning_artifacts(resolved):
        return str(reasons["ledger"])
    if "implementation-artifacts" in resolved.parts and is_tracked(ctx.repo_root, str(resolved)):
        return str(reasons["implementation_artifacts"])
    return None


MATCHERS: dict[str, Callable[[Context, dict[str, Any]], Optional[str]]] = {
    "guild-task-via-local-recipes": match_guild_task_via_local_recipes,
    "adhoc-package-install": match_adhoc_package_install,
    "pixi-add-or-update": match_pixi_add_or_update,
    "bmad-switch-unsafe": match_bmad_switch_unsafe,
    "git-commit-guardrail": match_git_commit_guardrail,
    "gh-pr-merge-squash": match_gh_pr_merge_squash,
    "gh-pr-create-missing-repo": match_gh_pr_create_missing_repo,
    "uv-run-outside-repo-root": match_uv_run_outside_repo_root,
    "spec-surface-bare-write-baseline": match_spec_surface_bare_write_baseline,
    "direct-write-governed-path": match_direct_write_governed_path,
}


def load_denial_rules(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Load and validate `session_denials` -- the ONE declared source.

    Raises if the file is missing/malformed, or if its declared ids and
    `MATCHERS`'s implemented ids are not exactly the same set: a drift here
    means either a rule is declared but silently unenforced, or enforced but
    ungoverned -- both are the "fail loud, never silent skip" case.
    """
    roster_path = repo_root / "docs" / "governance" / "guild-roster.json"
    data = json.loads(roster_path.read_text(encoding="utf-8"))
    rules = data.get("session_denials")
    if not isinstance(rules, list) or not rules:
        raise RuntimeError(
            f"{roster_path} is missing a non-empty 'session_denials' list"
        )
    by_id: dict[str, dict[str, Any]] = {}
    for rule in rules:
        rid = rule.get("id")
        if not rid:
            raise RuntimeError(f"a session_denials entry in {roster_path} has no 'id'")
        by_id[rid] = rule

    declared = set(by_id)
    implemented = set(MATCHERS)
    if declared != implemented:
        missing_impl = sorted(declared - implemented)
        missing_decl = sorted(implemented - declared)
        raise RuntimeError(
            "session_denials in guild-roster.json and pre-shell.py's MATCHERS have "
            f"drifted: declared-but-unimplemented={missing_impl} "
            f"implemented-but-undeclared={missing_decl}"
        )
    return by_id


# --------------------------------------------------------------------------
# Output -- harness-specific decision format.
# --------------------------------------------------------------------------


def emit_deny(harness: str, kind: str, reason: str) -> None:
    if harness == "claude":
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
        return
    if harness == "cursor" and kind == "bash":
        print(
            json.dumps(
                {
                    "permission": "deny",
                    "user_message": reason,
                    "agent_message": reason,
                }
            )
        )
        return
    # Cursor's afterFileEdit has no deny/message-injection output (see module
    # docstring) -- the best available signal is a loud, visible stderr line
    # plus a non-zero exit, which is why emit_deny is not called for this
    # (harness, kind) pair; see emit_warn.


def emit_warn(reason: str) -> None:
    print(f"[pre-shell guardrail] {reason}", file=sys.stderr)


# --------------------------------------------------------------------------
# Entry point.
# --------------------------------------------------------------------------


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        # Infra-level failure outside this script's control (malformed
        # stdin) -- degrade to allow rather than block every tool call.
        print("[pre-shell guardrail] could not parse hook stdin as JSON", file=sys.stderr)
        return 0

    harness, kind = detect(payload)
    if kind not in ("bash", "edit_write"):
        return 0

    ctx = build_context(harness, kind, payload)
    rules = load_denial_rules(ctx.repo_root)

    for rule_id, matcher in MATCHERS.items():
        rule = rules[rule_id]
        if rule.get("applies_to") != kind:
            continue
        reason = matcher(ctx, rule)
        if not reason:
            continue
        if harness == "cursor" and kind == "edit_write":
            emit_warn(reason)
            return 1
        emit_deny(harness, kind, reason)
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc(file=sys.stderr)
        # Claude Code's PreToolUse contract only blocks the tool call on exit
        # code 2 (any other non-zero exit is non-blocking) -- a governance-file
        # integrity failure must fail loud, not proceed as if nothing happened.
        sys.exit(2)
