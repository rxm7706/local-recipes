#!/usr/bin/env python3
"""One deny list, one hook -- the Guild session guardrails, enforced not asserted.

(steward Story 63.3, spec-pyforge-steward CAP-5)

WHAT THIS IS. A repo-level `PreToolUse` guard for the seventeen AGENTS.md/CLAUDE.md
session rules that were previously prose only (the seventeenth is the writer
lock's chain-write denial, steward Story 121.4), plus three steward
operator-consent denials. Registered on `Bash` and on
`Edit`/`Write`/`NotebookEdit` in `.claude/settings.json` (Claude Code) and on
`beforeShellExecution` / `afterFileEdit` in `.cursor/hooks.json` (Cursor) --
THE SAME FILE serves both harnesses; each hook config just points its own
harness's event(s) at this one script, and this script tells the two apart by
the shape of the JSON on stdin (see `detect()`).

Gemini CLI, GitHub Copilot CLI and Devin have no verified deny surface for
this hook -- for them those rules and denials stay instruction-only, as written in
AGENTS.md (see AGENTS.md's own "Session guardrails" section; do not assume
this script runs there). Cursor has no before-MCP deny; MCP submission there
stays instruction-only (Story 85.8).

THE CLOSED LIST. `docs/governance/guild-roster.json`'s `session_denials`
array is the ONE declared source of what this hook denies and the one-line
reason it gives for each -- naming the sanctioned form. Adding a denial is a
governance act on that file, never a bare code change here. `MATCHERS` below
must carry exactly one callable per declared rule id, in both directions --
`load_denial_rules()` asserts that at every run and raises (loud, not a
silent skip) on any drift between the two. The roster is read from the tree
the hook script lives in, so the matchers and the roster always come from one
revision whatever the tool call's cwd.

Cursor's `afterFileEdit` has no permission/deny or message-injection output
in its current schema (checked live against https://cursor.com/docs/agent/hooks,
2026-09-20), and Cursor has no "before write" event for file edits at all --
so the file rules there are necessarily a post-hoc WARN: a clear message on
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
interpreter launched the agent. Its one reuse is pyforge-core's stdlib-only
`pyforge.core.cutover_root` (the root of record and each root's forge slug),
installed or loaded from this tree's core source (see `_cutover_root()`).
"""

from __future__ import annotations

import bisect
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
    kind: str  # "bash" | "edit_write" | "mcp"
    command: Optional[str]
    subcommands: list[list[str]] = field(default_factory=list)
    file_path: Optional[str] = None
    cwd: str = "."
    repo_root: Path = field(default_factory=Path)
    mcp_tool_name: Optional[str] = None
    mcp_tool_input: dict[str, Any] = field(default_factory=dict)


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
        if isinstance(tool_name, str) and tool_name.startswith("mcp__"):
            return "claude", "mcp"
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

    subcommands = normalised_subcommands(command) if command else []
    repo_root = find_repo_root(cwd)
    mcp_tool_name: Optional[str] = None
    mcp_tool_input: dict[str, Any] = {}
    if harness == "claude" and kind == "mcp":
        mcp_tool_name = payload.get("tool_name")
        raw_input = payload.get("tool_input")
        if isinstance(raw_input, dict):
            mcp_tool_input = raw_input
    return Context(
        harness=harness,
        kind=kind,
        command=command,
        subcommands=subcommands,
        file_path=file_path,
        cwd=cwd,
        repo_root=repo_root,
        mcp_tool_name=mcp_tool_name,
        mcp_tool_input=mcp_tool_input,
    )


# --------------------------------------------------------------------------
# Command tokenization -- heuristic, not a shell. Good enough to recognize
# the closed session-denial forms; not a sandbox and not trying to be one.
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
        inner = _shell_c_payload(tokens)
        if inner is not None:
            result.extend(split_subcommands(inner))
    return result


_SHELLS = ("bash", "sh", "zsh")
# Prefix commands that run the rest of the line, each with the options that take an argument.
_WRAPPERS: dict[str, tuple[str, ...]] = {
    "env": ("-u", "--unset", "-C", "--chdir", "-S", "--split-string"),
    "timeout": ("-k", "--kill-after", "-s", "--signal"),
    "nice": ("-n", "--adjustment"),
    "nohup": (),
    "sudo": ("-u", "-g", "-C", "-D", "-h", "-p", "-U"),
    "command": (),
    "exec": ("-a",),
}
_SHELL_ARG_OPTS = ("-o", "+o", "-O", "+O", "--rcfile", "--init-file")


def _shell_c_payload(tokens: list[str]) -> Optional[str]:
    """The `-c` payload of `bash -c "..."`, also behind prefix commands (`env`, `timeout N`,
    `nohup`, `nice`, `sudo`, `command`, `exec`), with a bundled option such as `-lc`, and past
    long options and `-o <opt>` (Story 118.8 reviews)."""
    i = 0
    while i < len(tokens):
        name = os.path.basename(tokens[i])
        if name not in _WRAPPERS:
            break
        i += 1
        takes_arg = _WRAPPERS[name]
        while i < len(tokens):
            tok = tokens[i]
            if tok in takes_arg:
                i += 2
            elif tok.startswith("-") or (name == "env" and "=" in tok):
                i += 1
            elif name == "timeout" and tok[:1].isdigit():
                i += 1  # the DURATION operand
                break
            else:
                break
    if i >= len(tokens) or os.path.basename(tokens[i]) not in _SHELLS:
        return None
    j = i + 1
    while j < len(tokens) - 1:
        opt = tokens[j]
        if opt in _SHELL_ARG_OPTS:
            j += 2
            continue
        if opt.startswith("--"):
            j += 1
            continue
        if not opt.startswith(("-", "+")):
            break
        if opt.startswith("-") and "c" in opt[1:]:
            return tokens[j + 1]
        j += 1
    return None


# Steward Story 134.2 (DW-steward-review-2026-11-24-4): every subcommand is also read in
# its normal form, so a rule anchored on the executable is not skipped by what stands
# before it. The normal form is ADDED beside the tokens as written, never put in their
# place: a rule that matched the written form still matches it.
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")
_NORMAL_FORM_WRAPPERS: dict[str, tuple[str, ...]] = {
    **_WRAPPERS,
    "time": ("-f", "--format", "-o", "--output"),
    "builtin": (),
}
_SHELL_LEADERS = frozenset({"(", "{", "!", "if", "then", "elif", "else", "while", "until", "do"})


def _command_tokens(tokens: list[str]) -> list[str]:
    """`tokens` without the environment assignments that stand before the executable."""
    i = 0
    while i < len(tokens) and _ASSIGNMENT_RE.match(tokens[i]):
        i += 1
    return tokens[i:]


def _normal_form(tokens: list[str]) -> list[str]:
    """The assignments a command carries, then the command with its executable reduced to
    a basename: leading assignments, the prefix commands (`env`, `command`, `time`, `nice`,
    `nohup`, `exec`, `timeout`, `sudo`, `builtin`), a subshell or brace opener, `!` and the
    shell keywords that stand before a command are taken off. `[]` when no command is left
    (`env` alone) or the line only looks a command up (`command -v <name>`)."""
    toks = list(tokens)
    assignments: list[str] = []
    opened = False
    for _ in range(len(tokens) + 1):  # each pass takes at least one token off or stops
        if not toks:
            return []
        head = toks[0]
        if head in _SHELL_LEADERS:
            opened = opened or head == "("
            toks = toks[1:]
            continue
        if len(head) > 1 and head[0] in "({" and head.lstrip("({"):
            opened = opened or "(" in head[: len(head) - len(head.lstrip("({"))]
            toks = [head.lstrip("({"), *toks[1:]]
            continue
        if _ASSIGNMENT_RE.match(head):
            assignments.append(head)
            toks = toks[1:]
            continue
        name = os.path.basename(head)
        if name not in _NORMAL_FORM_WRAPPERS:
            break
        takes_arg = _NORMAL_FORM_WRAPPERS[name]
        i = 1
        while i < len(toks):
            tok = toks[i]
            if name == "env" and tok in ("-S", "--split-string") and i + 1 < len(toks):
                toks = [*toks[: i + 1], *_tokenize(toks[i + 1]), *toks[i + 2 :]]
                i += 1
            elif name == "env" and tok.startswith("--split-string="):
                toks = [*toks[:i], "-S", *_tokenize(tok.split("=", 1)[1]), *toks[i + 1 :]]
                i += 1
            elif name == "command" and tok in ("-v", "-V"):
                return []
            elif tok in takes_arg:
                i += 2
            elif tok.startswith("-"):
                i += 1
            elif name == "env" and _ASSIGNMENT_RE.match(tok):
                assignments.append(tok)
                i += 1
            elif name == "timeout" and tok[:1].isdigit():
                i += 1  # the DURATION operand
                break
            else:
                break
        toks = toks[i:]
    if not toks:
        return []
    if opened:
        while toks and toks[-1] in (")", "}"):
            toks = toks[:-1]
        if not toks:
            return []
        toks = [*toks[:-1], toks[-1].rstrip(")") or toks[-1]]
    return [*assignments, os.path.basename(toks[0]) or toks[0], *toks[1:]]


def _background_segments(tokens: list[str]) -> list[list[str]]:
    """`a & b` holds two commands; `_split_respecting_quotes` leaves a lone `&` in place."""
    if "&" not in tokens:
        return []
    segments: list[list[str]] = []
    current: list[str] = []
    for tok in tokens:
        if tok == "&":
            if current:
                segments.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        segments.append(current)
    return segments


def normalised_subcommands(command: str, _depth: int = 0) -> list[list[str]]:
    """`split_subcommands(command)`, each list followed by its normal form where the two
    differ, and by the commands of a `bash -c` payload only the normal form shows."""
    result: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def add(tokens: list[str]) -> None:
        key = tuple(tokens)
        if tokens and key not in seen:
            seen.add(key)
            result.append(tokens)

    for written in split_subcommands(command):
        add(written)
        for tokens in (written, *_background_segments(written)):
            add(tokens)
            normal = _normal_form(tokens)
            if not normal:
                continue
            add(normal)
            if _depth >= 8:
                continue
            # A `bash -c` payload is read whole again, so its own substitutions and normal
            # forms are read too (Story 139.1); `split_subcommands` already added its plain
            # token lists, and `add` keeps each list once.
            inner = _shell_c_payload(tokens)
            if inner is None:
                inner = _shell_c_payload(_command_tokens(normal))
            if inner is not None:
                # `shlex` keeps `\$` and `` \` `` inside double quotes, where bash removes the
                # backslash, so `bash -c "echo \$(cmd)"` runs `cmd`: read that form as well.
                unescaped = inner.replace("\\$", "$").replace("\\`", "`")
                for payload in dict.fromkeys((inner, unescaped)):
                    for sub in normalised_subcommands(payload, _depth + 1):
                        add(sub)
    # Steward Story 139.1: the commands inside a `$(...)`, a backtick pair or a process
    # substitution run too, so every rule reads them beside the outer command. Added,
    # never in place of a token list: tightening only.
    if _depth < 8:
        for body in _substitution_bodies(command):
            for sub in normalised_subcommands(body, _depth + 1):
                add(sub)
    return result


def _contains(tokens: list[str], seq: list[str]) -> bool:
    n = len(seq)
    return any(tokens[i : i + n] == seq for i in range(len(tokens) - n + 1))


def _has_long_flag(tokens: list[str], flag: str) -> bool:
    """`flag`, `flag=...`, or an argparse abbreviation of it (`--ye` for `--yes`): steward's
    parsers keep argparse's allow_abbrev, so an exact-token check is bypassed (Story 118.8 review)."""
    for raw in tokens:
        # `--yes)` in a subshell, `--yes>log` with a redirect glued on (Story 118.8 review)
        tok = re.split(r"[)(;<>|&]", raw, maxsplit=1)[0]
        if tok == flag or tok.startswith(flag + "="):
            return True
        if len(tok) >= 3 and tok.startswith("--") and flag.startswith(tok):
            return True
    return False


def _is_steward_invocation(tokens: list[str]) -> bool:
    """`steward` as a token or a binary path, `pyforge steward ...`, or `python -m pyforge.steward`."""
    return any(
        tok == "steward" or os.path.basename(tok) == "steward" or tok.startswith("pyforge.steward")
        for tok in tokens
    )


# --------------------------------------------------------------------------
# Small git/pixi helpers, all defensive: a subprocess failure degrades a
# single check to "no evidence of a match", never a script crash.
# --------------------------------------------------------------------------


def _git(args: list[str], cwd: str) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5
        )
    # ValueError: a NUL in a `git -C` path; it degrades as a missing directory does.
    except (OSError, ValueError, subprocess.SubprocessError):
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
_BUNDLED_SHORT_F_RE = re.compile(r"^-[a-zA-Z]*F$")
_STDIN_NAMES = ("-", "/dev/stdin", "/dev/fd/0", "/proc/self/fd/0")
_HEREDOC_OPEN_RE = re.compile(
    r"<<(?!<)-?[ \t]*(?P<quote>['\"]?)(?P<tag>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)"
)
_STDIN_WRITERS = frozenset({"echo", "printf"})
_MESSAGE_FILE_LIMIT = 1_000_000  # bytes of a message file read for the attribution check


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
        # `-m<msg>` in one token (`-m"..."` once the shell has joined it); checked from
        # the `commit` verb on, so a global `-m...` before it is never read as a message.
        if tok.startswith("-m") and len(tok) > 2 and "commit" in tokens[:i]:
            parts.append(tok[2:])
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


def _commit_reads_stdin(tokens: list[str]) -> bool:
    """`git commit -F -` in any spelling: the message is whatever stands on stdin."""
    for i, tok in enumerate(tokens):
        if (
            (tok in ("-F", "--file") or _BUNDLED_SHORT_F_RE.fullmatch(tok))
            and i + 1 < len(tokens)
            and tokens[i + 1] in _STDIN_NAMES
        ):
            return True
        if tok.startswith("--file=") and tok.split("=", 1)[1] in _STDIN_NAMES:
            return True
        if tok.startswith("-F") and tok[2:] in _STDIN_NAMES:
            return True
    return False


def _heredoc_body_spans(text: str) -> list[tuple[int, int, bool]]:
    """`(start, end, quoted)` of every here-document body in `text`, in one linear pass
    (Story 134.2; spans, Story 139.1). `quoted` is whether the opener's tag is quoted
    (`<<'EOF'`, `<<"EOF"`): bash expands nothing in such a body.

    A body runs from the line after its `<<TAG` opener to the first later line that is
    TAG alone (blanks and tabs aside). An opener with no terminator runs to the end of
    the text, as bash runs it, and ends the scan: every later body stands inside it. A
    backreferencing regex re-scanned to the end for each unterminated opener, which grew
    with the square of the command length."""
    lines = text.split("\n")
    line_starts: list[int] = []
    offset = 0
    terminators: dict[str, list[int]] = {}  # TAG -> indexes of the lines that are TAG alone
    for index, line in enumerate(lines):
        line_starts.append(offset)
        offset += len(line) + 1
        word = line.strip(" \t")
        if word:
            terminators.setdefault(word, []).append(index)
    spans: list[tuple[int, int, bool]] = []
    pos = 0
    while True:
        opener = _HEREDOC_OPEN_RE.search(text, pos)
        if opener is None:
            break
        line_index = bisect.bisect_right(line_starts, opener.end()) - 1
        if line_index + 1 >= len(lines):  # no newline after the opener: no body
            pos = opener.start() + 1
            continue
        body_line = line_index + 1
        candidates = terminators.get(opener.group("tag"), [])
        found = bisect.bisect_left(candidates, body_line)
        body_start = line_starts[body_line]
        quoted = bool(opener.group("quote"))
        if found == len(candidates):
            spans.append((body_start, len(text), quoted))
            break
        end_line = candidates[found]
        spans.append((body_start, line_starts[end_line], quoted))
        pos = line_starts[end_line] + len(lines[end_line])
    return spans


def _heredoc_bodies(text: str) -> list[str]:
    """The body of every here-document in `text` (Story 134.2)."""
    return [text[start:end] for start, end, _quoted in _heredoc_body_spans(text)]


def _without_heredoc_bodies(text: str) -> tuple[str, list[str]]:
    """`text` with every here-document body cut out at its own position, and the bodies
    bash expands (an unquoted tag). A body is text, not a command line: a commit message or
    PR body that only mentions a command is not read as one (Story 139.1)."""
    spans = _heredoc_body_spans(text)
    expanded = [text[start:end] for start, end, quoted in spans if not quoted]
    for start, end, _quoted in reversed(spans):
        text = text[:start] + text[end:]
    return text, expanded


_COMMENT_AFTER = frozenset(" \t\n;|&()")


def _scan_substitutions(text: str, *, shell_quotes: bool) -> list[str]:
    """The body of each outermost `$(...)`, backtick pair and (outside double quotes)
    `<(...)` / `>(...)` in `text` (Story 139.1). With `shell_quotes`, the text is a
    command line: single-quoted and `$'...'` text expands nothing, a `#` that starts a word
    comments out the rest of its line, and `<(`/`>(` inside double quotes are literal.
    Without it, the text is an unquoted here-document body, where quotes and `#` are
    literal and only `$(...)` and backticks expand."""
    bodies: list[str] = []
    n = len(text)
    i = 0
    in_double = False
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if shell_quotes and not in_double:
            if ch == "#" and (i == 0 or text[i - 1] in _COMMENT_AFTER):
                newline = text.find("\n", i)
                i = n if newline == -1 else newline + 1
                continue
            if text.startswith("$'", i):
                j = i + 2
                while j < n and text[j] != "'":
                    j += 2 if text[j] == "\\" else 1
                i = j + 1
                continue
            if ch == "'":
                close = text.find("'", i + 1)
                i = n if close == -1 else close + 1
                continue
        if shell_quotes and ch == '"':
            in_double = not in_double
            i += 1
            continue
        if ch == "`":
            j = i + 1
            while j < n and text[j] != "`":
                j += 2 if text[j] == "\\" else 1
            body = text[i + 1 : min(j, n)]
            bodies.append(body.replace("\\`", "`").replace("\\$", "$").replace("\\\\", "\\"))
            i = j + 1
            continue
        if text.startswith("$((", i):
            i += 3
            continue
        if text.startswith("$(", i) or (
            shell_quotes and not in_double and text.startswith(("<(", ">("), i)
        ):
            depth = 1
            j = i + 2
            quote = ""
            while j < n and depth:
                c = text[j]
                if quote:
                    if c == "\\" and quote == '"':
                        j += 1
                    elif c == quote:
                        quote = ""
                elif c == "\\":
                    j += 1
                elif c in ("'", '"'):
                    quote = c
                elif c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                j += 1
            end = j - 1 if depth == 0 else n
            bodies.append(text[i + 2 : end])
            i = j
            continue
        i += 1
    return [body for body in bodies if body.strip()]


def _substitution_bodies(command: str) -> list[str]:
    """The body of each outermost command substitution (`$(...)`, backticks) and process
    substitution (`<(...)`, `>(...)`) in `command`, in order (steward Story 139.1): those
    of the command line with every here-document body cut out, then those of each body
    bash expands (an unquoted tag). Parentheses nest and a quote inside a `$(...)` body is
    respected, so `$(echo ')')` closes where bash closes it; an opener with no close takes
    the rest of the text. A nested substitution is the caller's to find, by reading the
    body again. Not read: a `case` pattern's `)` inside a `$(...)` closes it early."""
    line, expanded = _without_heredoc_bodies(command)
    bodies = _scan_substitutions(line, shell_quotes=True)
    for body in expanded:
        bodies.extend(_scan_substitutions(body, shell_quotes=False))
    return bodies


def _stdin_text_in_command(command: str, tokens: list[str], cwd: str) -> str:
    """What the command text itself puts on a commit's stdin (Story 134.2): the body of a
    here-document, a here-string, the arguments of an `echo`/`printf` and a file named by
    `< file` or `cat file`. A message the text does not carry cannot be read before the
    command runs; the `commit-msg` git hook remains the guarantee for it."""
    parts: list[str] = _heredoc_bodies(command)
    for i, tok in enumerate(tokens):
        if tok == "<<<" and i + 1 < len(tokens):
            parts.append(tokens[i + 1])
        elif tok.startswith("<<<") and len(tok) > 3:
            parts.append(tok[3:])
        elif tok == "<" and i + 1 < len(tokens):
            parts.append(_read_message_file(tokens[i + 1], cwd))
        elif tok.startswith("<") and not tok.startswith("<<") and len(tok) > 1:
            parts.append(_read_message_file(tok[1:], cwd))
    for other in split_subcommands(command):
        cmd = _command_tokens(_normal_form(other) or other)
        if not cmd:
            continue
        if cmd[0] in _STDIN_WRITERS:
            for arg in cmd[1:]:
                parts.append(arg.replace("\\n", "\n"))
        elif cmd[0] == "cat":
            for arg in cmd[1:]:
                if not arg.startswith(("-", "<")):
                    parts.append(_read_message_file(arg, cwd))
    return "\n".join(p for p in parts if p)


def _read_message_file(name: str, cwd: str) -> str:
    if name in _STDIN_NAMES:
        return ""
    try:
        path = Path(os.path.expanduser(name))
        if not path.is_absolute():
            path = Path(cwd) / path
        if not path.is_file():  # never a device or a pipe: reading one would not return
            return ""
        with path.open("rb") as handle:
            return handle.read(_MESSAGE_FILE_LIMIT).decode("utf-8", errors="replace")
    except (OSError, ValueError):
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
    for written in ctx.subcommands:
        tokens = _command_tokens(written)
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
    for written in ctx.subcommands:
        tokens = _command_tokens(written)
        if len(tokens) >= 2 and tokens[0] == "pixi" and tokens[1] in ("add", "update"):
            return str(rule["reason"])
    return None


def match_steward_estate_transitive(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for tokens in ctx.subcommands:
        if not _has_long_flag(tokens, "--transitive"):
            continue
        if not _contains(tokens, ["estate", "refresh"]):
            continue
        if not _is_steward_invocation(tokens):
            continue
        return str(rule["reason"])
    return None


def match_steward_estate_realize_yes(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for tokens in ctx.subcommands:
        if not _has_long_flag(tokens, "--yes"):
            continue
        if not _contains(tokens, ["estate", "realize"]):
            continue
        if not _is_steward_invocation(tokens):
            continue
        return str(rule["reason"])
    return None


def match_steward_deploy_nic_up_yes(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    """Story 118.8 (spec-pyforge-steward CAP-176): a `deploy nic up --yes` is the operator's
    consent to a non-local NKP bring-up. kind's local `up` never takes `--yes`."""
    for tokens in ctx.subcommands:
        if not _has_long_flag(tokens, "--yes"):
            continue
        if not _contains(tokens, ["deploy", "nic", "up"]):
            continue
        if not _is_steward_invocation(tokens):
            continue
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
    for written in ctx.subcommands:
        tokens = _command_tokens(written)
        if not tokens or tokens[0] != "git":
            continue
        # `git -c k=v commit`, `git -C dir commit`: one form, read through the helper
        # every other git rule uses; the checkout judged is the one `-C` names.
        sub = _git_subcommand_tokens(tokens)
        if not sub or sub[0] != "commit":
            continue
        git_cwd = _git_commit_cwd(tokens, ctx.cwd)
        state = git_checkout_state(git_cwd)
        if state is not None:
            branch, in_worktree = state
            if branch == "main" or not in_worktree:
                return str(reasons["checkout"])
        message = _extract_commit_message(tokens, git_cwd)
        if _commit_reads_stdin(sub) and ctx.command:
            carried = _stdin_text_in_command(ctx.command, tokens, git_cwd)
            message = "\n".join(p for p in (message, carried) if p)
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
                if tokens[i + 1] == _this_forge_slug():
                    has_repo = True
            elif tok.startswith("--repo="):
                if tok.split("=", 1)[1] == _this_forge_slug():
                    has_repo = True
        if not has_repo:
            return str(rule["reason"])
    return None


def match_uv_run_outside_repo_root(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    for written in ctx.subcommands:
        tokens = _command_tokens(written)
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


_LOOP_HOMES_ROOT = Path.home() / ".bmad-loops"
_PROTECTED_BRANCH_FLOOR = frozenset({"refs/heads/main", "refs/heads/loop/"})
_PROTECTED_BRANCH_KINDS = frozenset({"operational-branch", "legacy"})
_ORIGIN_MAIN = "refs/remotes/origin/main"
_PRESERVE_ARCHIVE_TAG_PREFIXES = ("refs/tags/preserve/", "refs/tags/archive/")


def load_protected_branch_prefixes(repo_root: Path) -> set[str]:
    """Branch refname prefixes (Story 85.1); kept for tests and branch-only callers."""
    return {p for p in load_protected_deletion_prefixes(repo_root) if p.startswith("refs/heads/")}


def load_protected_deletion_prefixes(repo_root: Path) -> set[str]:
    """Full refname prefixes with a roster `deletion` rule, unioned with the branch floor."""
    prefixes = set(_PROTECTED_BRANCH_FLOOR)
    roster_path = repo_root / "docs" / "governance" / "guild-roster.json"
    try:
        data = json.loads(roster_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return prefixes
    entries = data.get("protected_refs")
    if not isinstance(entries, list):
        return prefixes
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        refname = entry.get("refname")
        rules = entry.get("rules")
        if not isinstance(refname, str) or not isinstance(rules, list):
            continue
        if "deletion" not in rules:
            continue
        prefixes.add(refname)
    return prefixes


def _branch_refname(branch: str) -> str:
    branch = branch.strip()
    if branch.startswith("refs/heads/"):
        return branch
    return f"refs/heads/{branch}"


def _tag_refname(tag: str) -> str:
    tag = tag.strip()
    if tag.startswith("refs/tags/"):
        return tag
    return f"refs/tags/{tag}"


def _ref_matches_prefix(refname: str, prefixes: set[str]) -> bool:
    for prefix in prefixes:
        if refname == prefix:
            return True
        if prefix.endswith("/") and refname.startswith(prefix):
            return True
        if not prefix.endswith("/") and refname.startswith(prefix + "/"):
            return True
    return False


def _is_protected_branch_ref(refname: str, prefixes: set[str]) -> bool:
    return _ref_matches_prefix(refname, prefixes)


def _is_protected_ref(refname: str, prefixes: set[str]) -> bool:
    return _ref_matches_prefix(refname, prefixes)


def _git_exit_code(args: list[str], cwd: str) -> Optional[int]:
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5
        )
    # ValueError: a NUL in a `git -C` path; it degrades as a missing directory does.
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return out.returncode


def _is_ancestor(ancestor: str, descendant: str, cwd: str) -> bool:
    code = _git_exit_code(["merge-base", "--is-ancestor", ancestor, descendant], cwd)
    return code == 0


def _tip_covered_by_preserve_or_archive_tag(tip: str, cwd: str) -> bool:
    for prefix in _PRESERVE_ARCHIVE_TAG_PREFIXES:
        listed = _git(["for-each-ref", "--contains", tip, "--format=%(refname)", prefix], cwd)
        if listed:
            return True
    return False


def _resolve_ref_tip(refname: str, cwd: str, *, remote: str = "origin") -> Optional[str]:
    tip = _git(["rev-parse", "--verify", refname], cwd)
    if tip:
        return tip
    if refname.startswith("refs/heads/"):
        short = refname.removeprefix("refs/heads/")
        rtr = f"refs/remotes/{remote}/{short}"
        return _git(["rev-parse", "--verify", rtr], cwd)
    return None


# git's global options that take their value as the next token. `-c <name>=<value>`,
# `--namespace <name>` and `--config-env <name>=<var>` were read as the subcommand
# before Story 134.2, so `git -c k=v push ...` reached no rule.
_GIT_VALUE_OPTIONS = ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env")


def _git_subcommand_tokens(tokens: list[str]) -> Optional[list[str]]:
    i = 0
    while i < len(tokens):
        if tokens[i] != "git":
            i += 1
            continue
        j = i + 1
        while j < len(tokens):
            if tokens[j] in _GIT_VALUE_OPTIONS and j + 1 < len(tokens):
                j += 2
                continue
            if tokens[j].startswith("-C") and len(tokens[j]) > 2:
                j += 1
                continue
            if tokens[j].startswith("--git-dir=") or tokens[j].startswith("--work-tree="):
                j += 1
                continue
            if tokens[j].startswith("-"):
                j += 1
                continue
            return tokens[j:]
        return None
    return None


def _is_short_cluster_with(tok: str, letters: str) -> bool:
    """A short-option token (`-D`, `-Df`, `-fd`) that carries one of `letters`."""
    return bool(re.fullmatch(r"-[A-Za-z]+", tok)) and any(ch in tok[1:] for ch in letters)


def _git_commit_cwd(tokens: list[str], default_cwd: str) -> str:
    """The directory `git ... commit` runs in: the last `-C <dir>` among git's global
    options, each read against the one before it, as git does."""
    cwd = Path(default_cwd)
    try:
        j = tokens.index("git") + 1
    except ValueError:
        return default_cwd
    while j < len(tokens):
        tok = tokens[j]
        if tok == "-C" and j + 1 < len(tokens):
            cwd = cwd / os.path.expanduser(tokens[j + 1])
            j += 2
        elif tok.startswith("-C") and len(tok) > 2:
            cwd = cwd / os.path.expanduser(tok[2:])
            j += 1
        elif tok in _GIT_VALUE_OPTIONS and j + 1 < len(tokens):
            j += 2
        elif tok.startswith("-"):
            j += 1
        else:
            break
    return str(cwd)


def _push_delete_target_ref(tok: str) -> str:
    if tok.startswith("refs/"):
        return tok
    head = tok.split("/", 1)[0]
    if head in ("preserve", "archive", "rescue"):
        return _tag_refname(tok)
    return _branch_refname(tok)


def _ref_deletions_in_push(args: list[str]) -> list[str]:
    """Return full refnames (refs/heads/… or refs/tags/…) targeted for deletion."""
    refs: list[str] = []
    delete_mode = False
    i = 0
    while i < len(args):
        tok = args[i]
        if tok in ("--delete", "-d") or _is_short_cluster_with(tok, "d"):
            delete_mode = True
            i += 1
            continue
        if tok.startswith("--delete="):
            delete_mode = True
            i += 1
            continue
        if tok.startswith("-") and tok not in ("-d",):
            i += 1
            continue
        if delete_mode and not tok.startswith("-"):
            refs.append(_push_delete_target_ref(tok))
            i += 1
            continue
        if ":" in tok:
            left, right = tok.split(":", 1)
            # `:<ref>` deletes, and so does `+:<ref>` (the `+` only forces it)
            if left.lstrip("+") == "" and right:
                if right.startswith("refs/"):
                    refs.append(right)
                elif right.startswith("refs/heads/"):
                    refs.append(right)
                else:
                    refs.append(_branch_refname(right))
        i += 1
    return refs


def _branch_deletions_in_push(args: list[str]) -> list[str]:
    return [
        r.removeprefix("refs/heads/")
        for r in _ref_deletions_in_push(args)
        if r.startswith("refs/heads/")
    ]


def _worktree_remove_target(args: list[str]) -> Optional[Path]:
    for tok in args:
        if tok.startswith("-"):
            continue
        return Path(os.path.expanduser(tok))
    return None


def _is_loop_home(path: Path) -> bool:
    try:
        resolved = Path(os.path.realpath(os.path.expanduser(str(path))))
        root = Path(os.path.realpath(str(_LOOP_HOMES_ROOT)))
    except (OSError, ValueError):  # ValueError: an embedded NUL; unusable, as a missing path
        return False
    return resolved == root or root in resolved.parents


def _gh_api_delete_ref(tokens: list[str]) -> Optional[str]:
    if not _contains(tokens, ["gh", "api"]):
        return None
    method: Optional[str] = None
    endpoint: Optional[str] = None
    for i, tok in enumerate(tokens):
        if tok in ("-X", "--method") and i + 1 < len(tokens):
            method = tokens[i + 1].upper()
        elif tok.startswith("--method="):
            method = tok.split("=", 1)[1].upper()
        elif tok.startswith("-X") and len(tok) > 2:
            method = tok[2:].lstrip("=").upper()
        if "git/refs/heads/" in tok or "git/refs/tags/" in tok:
            endpoint = tok
    if endpoint is None or (method != "DELETE" and "DELETE" not in _gh_api_methods(tokens)):
        return None
    if "git/refs/heads/" in endpoint:
        branch = endpoint.split("git/refs/heads/", 1)[1].strip("/")
        return _branch_refname(branch) if branch else None
    if "git/refs/tags/" in endpoint:
        tag = endpoint.split("git/refs/tags/", 1)[1].strip("/")
        return _tag_refname(tag) if tag else None
    return None


def _push_mirror_origin(rest: list[str]) -> bool:
    if "--mirror" not in rest:
        return False
    remotes = [t for t in rest if not t.startswith("-") and t not in ("--mirror", "push")]
    return not remotes or "origin" in remotes


def _prune_refspec_covers_protected(refspec: str, prefixes: set[str]) -> bool:
    if ":" not in refspec:
        return False
    left, right = refspec.split(":", 1)
    for side in (left.strip(), right.strip()):
        if side.endswith("/*"):
            base = side[:-2]
        else:
            base = side.rstrip("/")
        for prefix in prefixes:
            if side.endswith("/*") and base in ("refs/tags", "refs/heads"):
                if prefix.startswith(base + "/"):
                    return True
            if _ref_matches_prefix(base + "/probe", {prefix}) or _ref_matches_prefix(
                prefix.rstrip("/") + "/probe", {base}
            ):
                return True
            if base == prefix.rstrip("/") or prefix.startswith(base + "/"):
                return True
    return False


def _git_prune_covers_protected(verb: str, rest: list[str], prefixes: set[str]) -> bool:
    if verb == "push" and "--prune" in rest:
        for tok in rest:
            if ":" in tok and _prune_refspec_covers_protected(tok, prefixes):
                return True
    if verb == "fetch" and ("--prune" in rest or any(_is_short_cluster_with(t, "p") for t in rest)):
        if "--prune-tags" not in rest and not any(_is_short_cluster_with(t, "P") for t in rest):
            return False
        for tok in rest:
            if tok.startswith("refs/") and _prune_refspec_covers_protected(tok, prefixes):
                return True
        return any(p.startswith("refs/tags/") for p in prefixes)
    return False


def _rm_removes_loop_home(tokens: list[str]) -> bool:
    low = [Path(t).name.lower() for t in tokens]
    if "rm" not in low:
        return False
    idx = low.index("rm")
    recursive = any(
        t in ("-r", "-rf", "-fr", "-R") or (t.startswith("-") and "r" in t and "f" in t)
        for t in tokens[idx + 1 :]
    )
    if not recursive:
        return False
    for tok in tokens[idx + 1 :]:
        if tok.startswith("-"):
            continue
        if _is_loop_home(Path(os.path.expanduser(tok))):
            return True
    return False


def _gh_pr_merge_deletes_loop_head(tokens: list[str]) -> bool:
    if not _contains(tokens, ["gh", "pr", "merge"]):
        return False
    if "--delete-branch" not in tokens:
        return False
    for i, tok in enumerate(tokens):
        if tok in ("--head", "-H") and i + 1 < len(tokens):
            head = tokens[i + 1]
            if head.startswith("loop/") or head.startswith("refs/heads/loop/"):
                return True
    return False


def _branch_or_tag_deletions(verb: str, rest: list[str]) -> list[str]:
    """Full refnames `git branch`/`git tag`/`git update-ref` delete, with the delete flag
    wherever it stands and in a bundle (`-Df`, `-f -D`, `--no-deref -d`; Story 134.2)."""
    refs: list[str] = []
    if verb == "branch" and any(t == "--delete" or _is_short_cluster_with(t, "dD") for t in rest):
        refs.extend(_branch_refname(t) for t in rest if not t.startswith("-"))
    elif verb == "tag" and any(t == "--delete" or _is_short_cluster_with(t, "d") for t in rest):
        refs.extend(_tag_refname(t) for t in rest if not t.startswith("-"))
    elif verb == "update-ref" and "-d" in rest:
        skip = False
        for tok in rest:
            if skip:
                skip = False
            elif tok == "-m":
                skip = True
            elif not tok.startswith("-"):
                refs.append(tok)
                break
    return refs


def _collect_ref_deletions_from_tokens(tokens: list[str]) -> list[str]:
    refs: list[str] = []
    git_rest = _git_subcommand_tokens(tokens)
    if git_rest:
        verb = git_rest[0]
        rest = git_rest[1:]
        if verb == "push":
            refs.extend(_ref_deletions_in_push(rest))
        else:
            refs.extend(_branch_or_tag_deletions(verb, rest))
    deleted = _gh_api_delete_ref(tokens)
    if deleted:
        refs.append(deleted)
    return refs


def match_protected_ref_deletion(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    reason = str(rule["reason"])
    prefixes = load_protected_deletion_prefixes(_hook_install_repo_root())
    for tokens in ctx.subcommands:
        git_rest = _git_subcommand_tokens(tokens)
        if git_rest:
            verb = git_rest[0]
            rest = git_rest[1:]
            if verb == "push":
                if _push_mirror_origin(rest):
                    return reason
                if _git_prune_covers_protected("push", rest, prefixes):
                    return reason
                for ref in _ref_deletions_in_push(rest):
                    if _is_protected_ref(ref, prefixes):
                        return reason
            elif verb == "fetch" and _git_prune_covers_protected("fetch", rest, prefixes):
                return reason
            elif verb in ("branch", "tag", "update-ref"):
                for ref in _branch_or_tag_deletions(verb, rest):
                    if _is_protected_ref(ref, prefixes):
                        return reason
            elif verb == "worktree" and len(rest) >= 2 and rest[0] == "remove":
                target = _worktree_remove_target(rest[1:])
                if target is not None and _is_loop_home(target):
                    return reason
        deleted = _gh_api_delete_ref(tokens)
        if deleted and _is_protected_ref(deleted, prefixes):
            return reason
        if _rm_removes_loop_home(tokens):
            return reason
        if _gh_pr_merge_deletes_loop_head(tokens):
            return reason
    return None


def match_unreachable_ref_deletion(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    reasons = rule["reason"]
    unreachable = str(reasons["unreachable"])
    fetch_remedy = str(reasons["fetch_remedy"])
    protected = load_protected_deletion_prefixes(_hook_install_repo_root())
    origin_main = _git(["rev-parse", "--verify", _ORIGIN_MAIN], ctx.cwd)
    for tokens in ctx.subcommands:
        for ref in _collect_ref_deletions_from_tokens(tokens):
            if _is_protected_ref(ref, protected):
                continue
            tip = _resolve_ref_tip(ref, ctx.cwd)
            if tip is None and ref.startswith("refs/heads/"):
                return fetch_remedy
            if tip is None:
                continue
            if origin_main and _is_ancestor(tip, origin_main, ctx.cwd):
                continue
            if _tip_covered_by_preserve_or_archive_tag(tip, ctx.cwd):
                continue
            return unreachable
    return None


_GITHUB_SLUG_RE = re.compile(
    r"^(?:https?://(?:[^/@]+@)?github\.com/|git@github\.com:|ssh://(?:[^/@]+@)?github\.com/)([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$",
    re.IGNORECASE,
)
_GH_PR_URL_RE = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+)/pull/\d+",
    re.IGNORECASE,
)
_GH_ISSUE_URL_RE = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+)/issues/\d+",
    re.IGNORECASE,
)
_CONDA_SMITHY_OUTWARD = frozenset(
    {
        "register-github",
        "register-ci",
        "register-feedstock-token",
        "update-anaconda-token",
        "rotate-anaconda-token",
        "update-binstar-token",
        "rotate-binstar-token",
    }
)
_MCP_OUTWARD_TOOLS = frozenset(
    {
        "mcp__conda_forge_server__submit_pr",
        "mcp__conda_forge_server__prepare_submission_branch",
        "mcp__conda_forge_server__migrate_to_v1",
    }
)


def _normalize_repo_slug(text: str) -> Optional[str]:
    raw = text.strip().strip('"').strip("'")
    if not raw:
        return None
    this_slug = _this_forge_slug()
    if raw.lower() == this_slug.lower():
        return this_slug
    if "/" in raw and "://" not in raw and not raw.startswith("git@"):
        owner, repo = raw.split("/", 1)
        repo = repo.removesuffix(".git")
        if owner and repo:
            return f"{owner.lower()}/{repo.lower()}"
    m = _GITHUB_SLUG_RE.match(raw)
    if m:
        return f"{m.group(1).lower()}/{m.group(2).lower()}"
    return None


def _is_local_recipes_slug(slug: Optional[str]) -> bool:
    """True for this checkout's own forge slug, `FORGE_SLUGS[roots.this]`."""
    return slug is not None and slug.lower() == _this_forge_slug().lower()


def _is_local_filesystem_destination(dest: str) -> bool:
    d = dest.strip()
    if not d:
        return False
    if d.startswith("file://"):
        return True
    if d.startswith("./") or d.startswith("../"):
        return True
    if d.startswith("/") and "github.com" not in d.lower():
        return True
    if d.startswith("~"):
        return True
    if "://" not in d and "@" not in d and "/" in d and "github.com" not in d.lower():
        return True
    return False


def _git_effective_cwd(tokens: list[str], default_cwd: str) -> str:
    i = 0
    while i < len(tokens):
        if tokens[i] != "git":
            i += 1
            continue
        j = i + 1
        while j < len(tokens):
            if tokens[j] in ("-C", "--git-dir", "--work-tree") and j + 1 < len(tokens):
                if tokens[j] == "-C":
                    return str(Path(default_cwd) / tokens[j + 1])
                j += 2
                continue
            if tokens[j].startswith("-C") and len(tokens[j]) > 2:
                return str(Path(default_cwd) / tokens[j][2:])
            if tokens[j].startswith("--git-dir=") or tokens[j].startswith("--work-tree="):
                j += 1
                continue
            if tokens[j] in ("-c", "--namespace", "--config-env") and j + 1 < len(tokens):
                j += 2
                continue
            break
        break
    return default_cwd


def _shares_git_common_dir(cwd: str, repo_root: Path) -> bool:
    common_cwd = _git(["rev-parse", "--git-common-dir"], cwd)
    common_root = _git(["rev-parse", "--git-common-dir"], str(repo_root))
    if common_cwd is None or common_root is None:
        return False
    abs_cwd = os.path.realpath(os.path.join(cwd, common_cwd))
    abs_root = os.path.realpath(os.path.join(str(repo_root), common_root))
    return abs_cwd == abs_root


def _hook_install_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_local_recipes_checkout(cwd: str) -> bool:
    """True when cwd is the PyForge checkout or one of its worktrees (shared config)."""
    return _shares_git_common_dir(cwd, _hook_install_repo_root())


def _git_remote_url(name: str, cwd: str, *, push: bool = False) -> Optional[str]:
    args = ["remote", "get-url", name]
    if push:
        args.append("--push")
    return _git(args, cwd)


def _resolve_push_destination(repository: Optional[str], cwd: str) -> tuple[Optional[str], bool]:
    """Return (github_slug_or_none, is_local_path). unresolved remote -> (None, False)."""
    if repository is None:
        branch = get_branch(cwd)
        if branch is None:
            return None, False
        for key in (
            f"branch.{branch}.pushRemote",
            "remote.pushDefault",
            f"branch.{branch}.remote",
        ):
            val = _git(["config", "--get", key], cwd)
            if val:
                repository = val
                break
        if repository is None:
            repository = "origin"
    assert repository is not None
    if _is_local_filesystem_destination(repository):
        return None, True
    slug = _normalize_repo_slug(repository)
    if slug:
        return slug, False
    url = _git_remote_url(repository, cwd, push=True) or _git_remote_url(
        repository, cwd, push=False
    )
    if url is None:
        return None, False
    if _is_local_filesystem_destination(url):
        return None, True
    return _normalize_repo_slug(url), False


def _strip_env_prefix(tokens: list[str]) -> tuple[dict[str, str], list[str]]:
    env: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if "=" in tok and not tok.startswith("-") and not tok.startswith("git"):
            key, _, val = tok.partition("=")
            if key.isidentifier() or key.replace("_", "").isalnum():
                env[key] = val
                i += 1
                continue
        break
    return env, tokens[i:]


def _gh_repo_from_tokens(tokens: list[str], cwd: str) -> Optional[str]:
    env, body = _strip_env_prefix(tokens)
    if "GH_REPO" in env:
        return _normalize_repo_slug(env["GH_REPO"])
    for i, tok in enumerate(body):
        if tok in ("-R", "--repo") and i + 1 < len(body):
            return _normalize_repo_slug(body[i + 1])
        if tok.startswith("--repo="):
            return _normalize_repo_slug(tok.split("=", 1)[1])
    for tok in body:
        if tok.startswith("http://") or tok.startswith("https://"):
            m = _GH_PR_URL_RE.match(tok) or _GH_ISSUE_URL_RE.match(tok)
            if m:
                return f"{m.group(1).lower()}/{m.group(2).lower()}"
    for remote in ("gh-resolved", "upstream", "github", "origin"):
        url = _git_remote_url(remote, cwd, push=False)
        if url:
            slug = _normalize_repo_slug(url)
            if slug:
                return slug
    return None


def _gh_api_endpoint_slug(tokens: list[str]) -> Optional[str]:
    env, body = _strip_env_prefix(tokens)
    i = 0
    endpoint = ""
    while i < len(body):
        tok = body[i]
        if tok in ("-X", "--method") and i + 1 < len(body):
            i += 2
            continue
        if tok.startswith("--method="):
            i += 1
            continue
        if tok.startswith("-"):
            i += 1
            continue
        endpoint = tok
        break
    endpoint = endpoint.strip("/")
    parts = endpoint.split("/")
    if len(parts) >= 2 and parts[0] == "repos":
        if parts[1] in ("{owner}", "OWNER") or parts[2] in ("{repo}", "REPO"):
            return None
        if len(parts) >= 3:
            return f"{parts[1].lower()}/{parts[2].lower()}"
    return None


def _gh_api_http_method(body: list[str]) -> str:
    method = "GET"
    i = 2
    while i < len(body):
        tok = body[i]
        if tok in ("-X", "--method") and i + 1 < len(body):
            method = body[i + 1].upper()
            i += 2
            continue
        if tok.startswith("--method="):
            method = tok.split("=", 1)[1].upper()
            i += 1
            continue
        if tok.startswith("-"):
            i += 1
            continue
        break
    if method == "GET":
        return "GET"
    return method


def _gh_api_endpoint_parts(body: list[str]) -> list[str]:
    i = 2
    while i < len(body):
        tok = body[i]
        if tok in ("-X", "--method") and i + 1 < len(body):
            i += 2
            continue
        if tok.startswith("--method="):
            i += 1
            continue
        if tok.startswith("-"):
            i += 1
            continue
        return body[i].strip("/").split("/")
    return []


def _gh_api_has_explicit_get(body: list[str]) -> bool:
    i = 2
    while i < len(body):
        tok = body[i]
        if tok in ("-X", "--method") and i + 1 < len(body):
            if body[i + 1].upper() == "GET":
                return True
            i += 2
            continue
        if tok.startswith("--method=") and tok.split("=", 1)[1].upper() == "GET":
            return True
        i += 1
    return False


_GH_API_WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


def _gh_api_methods(tokens: list[str]) -> list[str]:
    """Every HTTP method a `gh api` line names, wherever it stands and however it is
    spelled: `-X V`, `-XV`, `-X=V`, `--method V`, `--method=V` (Story 134.2)."""
    methods: list[str] = []
    for i, tok in enumerate(tokens):
        if tok in ("-X", "--method"):
            if i + 1 < len(tokens):
                methods.append(tokens[i + 1].upper())
        elif tok.startswith("--method="):
            methods.append(tok.split("=", 1)[1].upper())
        elif tok.startswith("-X") and len(tok) > 2:
            methods.append(tok[2:].lstrip("=").upper())
    return methods


def _gh_api_is_write(tokens: list[str]) -> bool:
    _, body = _strip_env_prefix(tokens)
    # A write method anywhere on the line is a write, even beside an explicit GET: gh
    # keeps the last value it is given, and a reader cannot tell which one wins.
    if any(m in _GH_API_WRITE_METHODS for m in _gh_api_methods(body[2:])):
        return True
    if _gh_api_has_explicit_get(body):
        return False
    method = _gh_api_http_method(body)
    if method != "GET":
        return method in _GH_API_WRITE_METHODS
    for tok in body[2:]:
        if tok in ("-f", "-F", "--field", "--raw-field", "--input"):
            return True
        if tok.startswith(("-f", "-F")) and len(tok) > 2:
            return True
        if tok.startswith(("--field=", "--raw-field=", "--input=")):
            return True
    return False


def _parse_git_remote_mutation(args: list[str]) -> Optional[str]:
    if not args or args[0] != "remote":
        return None
    if len(args) < 2:
        return None
    sub = args[1]
    if sub == "add" and len(args) >= 4:
        return args[3]
    if sub == "set-url":
        url_idx = 3
        if len(args) >= 4 and args[2] in ("--push", "--add"):
            url_idx = 4
        if len(args) > url_idx:
            return args[url_idx]
    return None


def _parse_git_push_repository(args: list[str]) -> Optional[str]:
    if not args or args[0] != "push":
        return None
    i = 1
    repository: Optional[str] = None
    while i < len(args):
        tok = args[i]
        if tok.startswith("--repo="):
            repository = tok.split("=", 1)[1]
            i += 1
            continue
        if tok in ("--repo",):
            if i + 1 < len(args):
                repository = args[i + 1]
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        repository = tok
        break
    return repository


def match_outward_git_push(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    reason = str(rule["reason"])
    for tokens in ctx.subcommands:
        git_cwd = _git_effective_cwd(tokens, ctx.cwd)
        sub = _git_subcommand_tokens(tokens)
        if sub is None:
            continue
        remote_url = _parse_git_remote_mutation(sub)
        if remote_url is not None and _is_local_recipes_checkout(git_cwd):
            if _is_local_filesystem_destination(remote_url):
                continue
            slug = _normalize_repo_slug(remote_url)
            if slug and not _is_local_recipes_slug(slug):
                return reason
            if slug is None and not _is_local_filesystem_destination(remote_url):
                return reason
        push_repo = _parse_git_push_repository(sub)
        if push_repo is not None or (sub and sub[0] == "push"):
            slug, is_local = _resolve_push_destination(push_repo, git_cwd)
            if is_local:
                continue
            if slug is None:
                return reason
            if not _is_local_recipes_slug(slug):
                return reason
    return None


_GH_WRITE_PR = frozenset(
    {"create", "comment", "review", "edit", "merge", "close", "reopen", "ready"}
)
_GH_WRITE_ISSUE = frozenset(
    {
        "create",
        "comment",
        "edit",
        "close",
        "reopen",
        "delete",
        "transfer",
        "lock",
        "unlock",
        "pin",
        "unpin",
    }
)
_GH_WRITE_RELEASE = frozenset({"create", "upload", "edit", "delete", "delete-asset"})


def match_outward_github_write(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    reason = str(rule["reason"])
    for tokens in ctx.subcommands:
        env, body = _strip_env_prefix(tokens)
        if not body:
            continue
        if body[0] != "gh":
            continue
        if len(body) >= 2 and body[1] == "repo":
            if len(body) >= 3 and body[2] in ("fork", "create"):
                return reason
        if len(body) >= 2 and body[1] == "gist":
            if len(body) >= 3 and body[2] in ("create", "edit", "delete"):
                return reason
        if len(body) >= 3 and body[1] == "api":
            if body[2] == "graphql":
                continue
            if not _gh_api_is_write(body):
                continue
            parts = _gh_api_endpoint_parts(body)
            if parts[:2] == ["user", "repos"]:
                return reason
            if len(parts) >= 3 and parts[0] == "orgs" and parts[2] == "repos":
                return reason
            if parts[:1] == ["gists"]:
                return reason
            if len(parts) >= 4 and parts[0] == "repos" and parts[3] == "forks":
                return reason
            if len(parts) >= 3 and parts[0] == "repos":
                api_slug = f"{parts[1].lower()}/{parts[2].lower()}"
                if _is_local_recipes_slug(api_slug):
                    continue
            return reason
        if len(body) >= 3 and body[1] in ("pr", "issue", "release"):
            family = body[1]
            verb = body[2]
            write_set = (
                _GH_WRITE_PR
                if family == "pr"
                else _GH_WRITE_ISSUE
                if family == "issue"
                else _GH_WRITE_RELEASE
            )
            if verb not in write_set:
                continue
            slug = _gh_repo_from_tokens(tokens, ctx.cwd)
            if slug is None:
                if _is_local_recipes_checkout(ctx.cwd):
                    return reason
                continue
            if not _is_local_recipes_slug(slug):
                return reason
    return None


def _tokens_have_yes(tokens: list[str]) -> bool:
    return any(t == "--yes" or t == "-y" for t in tokens)


def _is_mason_invocation(tokens: list[str]) -> bool:
    low = [Path(t).name for t in _command_tokens(tokens)]
    if not low:
        return False
    if low[:2] == ["pyforge", "mason"]:
        return True
    if low[0] == "mason":
        return True
    if _PY_INTERPRETER_RE.fullmatch(low[0]) and len(low) >= 3 and low[1] == "-m":
        mod = low[2]
        return mod in ("pyforge.mason", "pyforge.mason.cli")
    return False


def _mason_submit_denied(tokens: list[str]) -> bool:
    if not _is_mason_invocation(tokens):
        return False
    low = [Path(t).name for t in tokens]
    if "recipe" in low:
        idx = low.index("recipe")
        if idx + 1 < len(low) and low[idx + 1] == "submit" and _tokens_have_yes(tokens):
            return True
    if "package" in low:
        idx = low.index("package")
        rest = low[idx + 1 :]
        has_ship = any(
            tok == "ship" or tok == "--ship" or tok.startswith("--ship") for tok in rest
        )
        if has_ship and _tokens_have_yes(tokens):
            return True
    return False


def _cfe_submit_denied(tokens: list[str]) -> bool:
    command = _command_tokens(tokens)
    if len(command) >= 2 and command[0] == "pixi" and command[1] == "run":
        env, rest = _pixi_run_env(command)
        task = next((tok for tok in rest if not tok.startswith("-")), None)
        if env == "local-recipes" and task in ("submit-pr", "prepare-pr") and "--dry-run" not in tokens:
            return True
        if env != "local-recipes" and len(command) == len(tokens):
            return False  # as before Story 134.2, for the form with no assignment before it
    for tok in tokens:
        if tok.endswith("submit_pr.sh"):
            return True
        if tok.endswith("submit_pr.py") or tok.endswith("prepare_pr.py"):
            if "--dry-run" not in tokens:
                return True
    return False


def match_outward_package_submission(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    reason = str(rule["reason"])
    for tokens in ctx.subcommands:
        low = [Path(t).name.lower() for t in _command_tokens(tokens)]
        if low and low[0] == "feedrattler":
            if len(low) >= 2 and low[1] in ("--help", "--version", "-h"):
                if len(low) == len(tokens):
                    continue
            else:
                return reason
        if low and low[0] == "conda-smithy" and len(low) >= 2:
            if low[1] in _CONDA_SMITHY_OUTWARD:
                return reason
        if _mason_submit_denied(tokens):
            return reason
        if _cfe_submit_denied(tokens):
            return reason
    return None


def match_outward_mcp_submission(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    reason = str(rule["reason"])
    name = ctx.mcp_tool_name
    if not name or name not in _MCP_OUTWARD_TOOLS:
        return None
    if name == "mcp__conda_forge_server__migrate_to_v1":
        return reason
    dry = ctx.mcp_tool_input.get("dry_run")
    if dry is True:
        return None
    return reason


# --------------------------------------------------------------------------
# This checkout's root and the root of record -- the writer lock (steward
# Story 121.4, fnd:CAP-8, fnd:AD-24).
# --------------------------------------------------------------------------

_CUTOVER_ROOT_MODULE = "pyforge.core.cutover_root"
_CORE_SOURCE = Path("src") / "shared" / "packages" / "pyforge-core" / "src"
_ROOTS_CACHE: dict[str, Any] = {}


def _cutover_root() -> Any:
    """`pyforge.core.cutover_root`: the one home of the root of record and of
    each root's forge slug (`FORGE_SLUGS`; marshal Story 117.2,
    spec-pyforge-core:CAP-13), reused here and never copied.

    The installed module when this interpreter carries pyforge-core; otherwise
    this hook's own tree's core source, put on `sys.path` for the one import
    (the `_commit_msg_hook` precedent: reuse by path). The module is
    stdlib-only, so the bare `python3` that runs this hook imports it. Neither
    is a RuntimeError -- fail loud (exit 2), never a guessed slug or root.
    """
    cached = _ROOTS_CACHE.get("module")
    if cached is not None:
        return cached
    try:
        module = importlib.import_module(_CUTOVER_ROOT_MODULE)
    except ImportError:
        source = _hook_install_repo_root() / _CORE_SOURCE
        if not (source / "pyforge" / "core" / "cutover_root.py").is_file():
            raise RuntimeError(
                f"cannot load {_CUTOVER_ROOT_MODULE}: pyforge-core is not installed "
                f"and {source} holds no core source"
            ) from None
        sys.path.insert(0, str(source))
        try:
            module = importlib.import_module(_CUTOVER_ROOT_MODULE)
        finally:
            sys.path.remove(str(source))
    _ROOTS_CACHE["module"] = module
    return module


def _this_root() -> str:
    """`roots.this` from the hook's own tree's roster: the root this checkout
    is, read as data (the name only; its slug is core's `FORGE_SLUGS`)."""
    cached = _ROOTS_CACHE.get("this")
    if cached is not None:
        return str(cached)
    roster_path = _hook_install_repo_root() / "docs" / "governance" / "guild-roster.json"
    data = json.loads(roster_path.read_text(encoding="utf-8"))
    roots = data.get("roots")
    this = roots.get("this") if isinstance(roots, dict) else None
    if not isinstance(this, str) or not this:
        raise RuntimeError(
            f"{roster_path} declares no 'roots.this': the hook cannot tell which root this checkout is"
        )
    _ROOTS_CACHE["this"] = this
    return this


def _this_forge_slug() -> str:
    """This checkout's forge repository slug: `FORGE_SLUGS[roots.this]`."""
    slugs = _cutover_root().FORGE_SLUGS
    this = _this_root()
    if this not in slugs:
        raise RuntimeError(
            f"roots.this {this!r} has no entry in {_CUTOVER_ROOT_MODULE}.FORGE_SLUGS"
        )
    return str(slugs[this])


def _chain_glob_to_re(pattern: str) -> re.Pattern[str]:
    """One `paths` glob read the way doctor's writer-lock source reads it
    (chain.py's `_glob_to_re`, the branch half, spec-pyforge-doctor:CAP-100):
    `**` spans path separators, `*` and `?` do not, anything else is literal."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern[i : i + 2] == "**":
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _chain_path(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    """The edited file's path relative to its checkout when one of the
    denial's declared `paths` globs matches it, else None."""
    if ctx.file_path is None:
        return None
    globs = rule.get("paths")
    if not isinstance(globs, list) or not globs or not all(isinstance(g, str) and g for g in globs):
        raise RuntimeError(f"session_denials entry {rule.get('id')!r} declares no 'paths' glob list")
    try:
        # realpath raises ValueError on an embedded NUL: an unusable path, judged as one
        # outside the checkout (as `_is_loop_home` judges it a missing one).
        target = os.path.realpath(_resolve_against_cwd(ctx.cwd, ctx.file_path))
        rel = Path(target).relative_to(os.path.realpath(ctx.repo_root)).as_posix()
    except (OSError, ValueError):
        return None
    return rel if any(_chain_glob_to_re(g).match(rel) for g in globs) else None


def _root_of_record_at(repo_root: Path) -> Any:
    """`root_of_record()` as the checkout the write lands in sees it:
    `PYFORGE_FLAGS_PATH` first, else core's walk up from that checkout -- the
    hook process's own cwd is the harness's, not necessarily the tool call's.
    A tree that raises `CutoverRootError` is not caught: it fails loud (exit 2)."""
    module = _cutover_root()
    before = os.getcwd()
    os.chdir(repo_root)
    try:
        return module.root_of_record()
    finally:
        os.chdir(before)


def match_chain_write_off_the_writer(ctx: Context, rule: dict[str, Any]) -> Optional[str]:
    """Steward Story 121.4: the session half of the writer lock. An Edit or
    Write to a chain path is allowed only on the writer -- `root_of_record()`
    read from a flag tree (`source == 'flag-tree'`) names this checkout's
    `roots.this`. A `default` answer proves no writer and denies with its own
    reason. A Bash write is not matched here: doctor's writer-lock source
    (Story 56.5) judges the branch for every harness."""
    if _chain_path(ctx, rule) is None:
        return None
    this = _this_root()
    record = _root_of_record_at(ctx.repo_root)
    reasons = rule["reason"]
    if record.source != "flag-tree":
        return str(reasons["default"]).format(root=record.root, slug=record.forge_slug)
    if record.root == this:
        return None
    return str(reasons["off_writer"]).format(root=record.root, slug=record.forge_slug)


MATCHERS: dict[str, Callable[[Context, dict[str, Any]], Optional[str]]] = {
    "guild-task-via-local-recipes": match_guild_task_via_local_recipes,
    "adhoc-package-install": match_adhoc_package_install,
    "pixi-add-or-update": match_pixi_add_or_update,
    "steward-estate-transitive": match_steward_estate_transitive,
    "steward-estate-realize-yes": match_steward_estate_realize_yes,
    "steward-deploy-nic-up-yes": match_steward_deploy_nic_up_yes,
    "bmad-switch-unsafe": match_bmad_switch_unsafe,
    "git-commit-guardrail": match_git_commit_guardrail,
    "gh-pr-merge-squash": match_gh_pr_merge_squash,
    "gh-pr-create-missing-repo": match_gh_pr_create_missing_repo,
    "uv-run-outside-repo-root": match_uv_run_outside_repo_root,
    "spec-surface-bare-write-baseline": match_spec_surface_bare_write_baseline,
    "direct-write-governed-path": match_direct_write_governed_path,
    "protected-ref-deletion": match_protected_ref_deletion,
    "unreachable-ref-deletion": match_unreachable_ref_deletion,
    "outward-git-push": match_outward_git_push,
    "outward-github-write": match_outward_github_write,
    "outward-package-submission": match_outward_package_submission,
    "outward-mcp-submission": match_outward_mcp_submission,
    "chain-write-off-the-writer": match_chain_write_off_the_writer,
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
    if kind not in ("bash", "edit_write", "mcp"):
        return 0

    ctx = build_context(harness, kind, payload)
    rules = load_denial_rules(_hook_install_repo_root())

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
