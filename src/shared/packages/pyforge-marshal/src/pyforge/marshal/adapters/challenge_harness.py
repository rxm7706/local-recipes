"""The EGM challenger's harness launch (Story 113.1, CAP-298).

One synchronous Claude Code session per challenge: the packaged ``claude``
profile's argv, its ``{model_args}``/``{prompt}``/``{session_id}`` placeholders
substituted, and its ``--settings`` JSON widened with read-only rules on the
EGM plugin cache so a headless session can open the reviewer personas. The
challenger is Claude-only by construction -- EGM is a Claude Code plugin -- so
this adapter never consults a station's ``harness_preference`` (a Cursor-first
station still challenges on Claude).

The session carries no house context, checked at runtime (Story 113.10, CAP-299):
its ``--settings`` turn every hook off (``disableAllHooks``), drop the profile's
``instructionFiles`` plugin config, deny ``Read`` on the repo's instruction files,
memlogs and team memory (the target excepted), and enable ``egm@egm`` in that same
scope; the session runs from a temporary directory outside the repo, so no
``CLAUDE.md``, ``AGENTS.md`` or git status is discovered. Managed (policy)
settings still load.

Marshal reads nothing the session says; the caller reads the JSON report file
the session was told to write (AD-1).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError

from ..core.challenge import EGM_PLUGIN_ID
from ..core.harness_profile import HarnessProfile, load_packaged_profiles, translate_model

_PROFILE_NAME = "claude"
_DEFAULT_TIMEOUT_S = 3600.0
_VERSION_TIMEOUT_S = 30.0
_PLUGIN_CACHE_READ_DIRS: tuple[str, ...] = ("agents", "docs", "resources", "skills")
# The orchestrator session spawns reviewers and writes one report; nothing else (review S5).
ORCHESTRATOR_TOOLS: tuple[str, ...] = ("Agent", "Read", "Grep", "Glob")
DENIED_TOOLS: tuple[str, ...] = ("Bash", "Edit", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch")
_PERMISSION_MODE = "default"  # never the dispatch profile's bypassPermissions: the allow/deny lists must bind
# Story 113.10 (CAP-299): repo-relative globs no reviewer may Read -- the instruction files at the
# root and nested, every memlog and the team memory. ``*/**/`` is one directory deep or more, so the
# root file's rule can be left out for a rules-stage target while the nested rule stays.
FORBIDDEN_READ_GLOBS: tuple[str, ...] = (
    "AGENTS.md",
    "*/**/AGENTS.md",
    "CLAUDE.md",
    "*/**/CLAUDE.md",
    "**/.memlog.md",
    ".claude/memory/**",
)
_INSTRUCTION_FILES_OPTION = "instructionFiles"
# Claude Code loads CLAUDE.md from --add-dir / additionalDirectories only with this set; never for a challenge.
ADDITIONAL_DIRS_CLAUDE_MD_ENV = "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD"
_SESSION_DIR_PREFIX = "marshal-egm-"


class ChallengeHarnessError(PyforgeError, Exception):
    """The challenge session could not be launched."""


def plugin_cache_read_rules(plugins_root: Path) -> list[str]:
    """``Read(...)`` allow rules on the pinned plugin's resource folders, the
    version segment wildcarded so a refresh keeps matching (EGM docs/claude.md)."""
    base = plugins_root / "cache" / "egm" / "egm" / "*"
    return [f"Read(/{base / folder}/**)" for folder in _PLUGIN_CACHE_READ_DIRS]


def forbidden_read_rules(root: Path, target: Path | None = None) -> list[str]:
    """``Read(...)`` deny rules on ``FORBIDDEN_READ_GLOBS`` anchored at the repo ``root``. A glob
    the ``target`` matches is left out, so a rules-stage review can open ``AGENTS.md`` itself."""
    base = Path(os.path.abspath(root))
    relative: PurePosixPath | None = None
    if target is not None:
        try:
            relative = PurePosixPath(Path(os.path.abspath(target)).relative_to(base).as_posix())
        except ValueError:
            relative = None  # a target outside the repo matches no repo-anchored glob
    return [
        f"Read(/{base / glob})" for glob in FORBIDDEN_READ_GLOBS if relative is None or not relative.full_match(glob)
    ]


def _carries_instruction_files(config: object) -> bool:
    options = config.get("options") if isinstance(config, Mapping) else None
    return isinstance(options, Mapping) and _INSTRUCTION_FILES_OPTION in options


def widen_settings(
    settings_json: str,
    read_rules: Sequence[str],
    *,
    run_dir: Path | None = None,
    deny_rules: Sequence[str] = (),
) -> str:
    """Add the orchestrator's permissions to a profile's ``--settings`` JSON: the
    plugin-cache read rules, read-only tools plus ``Agent``, one ``Write`` rule
    confined to the run folder, and an explicit deny list (the tools, then
    ``deny_rules``). Story 113.10: every hook off, no ``instructionFiles`` plugin
    config, and ``egm@egm`` enabled in this scope."""
    try:
        settings = json.loads(settings_json) if settings_json else {}
    except json.JSONDecodeError as exc:
        raise ChallengeHarnessError(f"claude profile --settings is not JSON: {exc}") from exc
    permissions = dict(settings.get("permissions") or {})
    allow = list(permissions.get("allow") or [])
    wanted = [*ORCHESTRATOR_TOOLS, *read_rules, *([f"Write(/{run_dir}/**)"] if run_dir is not None else [])]
    allow.extend(rule for rule in wanted if rule not in allow)
    permissions["allow"] = allow
    deny = list(permissions.get("deny") or [])
    deny.extend(rule for rule in (*DENIED_TOOLS, *deny_rules) if rule not in deny)
    permissions["deny"] = deny
    settings["permissions"] = permissions
    configs = {
        name: config
        for name, config in (settings.get("pluginConfigs") or {}).items()
        if not _carries_instruction_files(config)
    }
    if configs:
        settings["pluginConfigs"] = configs
    else:
        settings.pop("pluginConfigs", None)
    settings["disableAllHooks"] = True
    settings["enabledPlugins"] = {**(settings.get("enabledPlugins") or {}), EGM_PLUGIN_ID: True}
    return json.dumps(settings, separators=(",", ":"))


def render_argv(
    profile: HarnessProfile,
    *,
    prompt: str,
    model: str | None,
    session_id: str,
    read_rules: Sequence[str],
    run_dir: Path | None = None,
    deny_rules: Sequence[str] = (),
) -> list[str]:
    """The challenge session's argv. A profile without ``--settings`` still gets the
    widened settings, so the session never launches without its guards."""
    rendered_model, _omitted = translate_model(profile, model)
    argv: list[str] = []
    tokens = list(profile.argv)
    settings_seen = False
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--settings" and index + 1 < len(tokens):
            argv += [
                "--settings",
                widen_settings(tokens[index + 1], read_rules, run_dir=run_dir, deny_rules=deny_rules),
            ]
            settings_seen = True
            index += 2
            continue
        if token == "--permission-mode" and index + 1 < len(tokens):
            argv += ["--permission-mode", _PERMISSION_MODE]
            index += 2
            continue
        if token == "{model_args}":
            if rendered_model:
                argv += [arg.replace("{model}", rendered_model) for arg in profile.model_args]
        elif token == "{prompt}":
            argv.append(prompt)
        else:
            argv.append(token.replace("{session_id}", session_id))
        index += 1
    if not settings_seen:
        argv = ["--settings", widen_settings("", read_rules, run_dir=run_dir, deny_rules=deny_rules), *argv]
    return argv


def _claude_profile() -> HarnessProfile:
    profile = load_packaged_profiles().get(_PROFILE_NAME)
    if profile is None:
        raise ChallengeHarnessError("no packaged 'claude' harness profile")
    return profile


def session_settings(plugins_root: Path) -> dict[str, object]:
    """The challenge session's ``--settings``, rendered from the packaged claude profile: the
    one scope the session's plugins come from, which ``plugin_refusal`` checks (Story 113.10)."""
    argv = render_argv(
        _claude_profile(),
        prompt="",
        model=None,
        session_id="",
        read_rules=plugin_cache_read_rules(plugins_root),
    )
    settings: dict[str, object] = json.loads(argv[argv.index("--settings") + 1])
    return settings


def _resolve_binary(profile: HarnessProfile) -> str | None:
    found = shutil.which(profile.binary)
    if found:
        return found
    for directory in profile.fallback_bin_dirs:
        candidate = Path(os.path.expanduser(directory)) / profile.binary
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def claude_version() -> str | None:
    """``claude --version``'s stdout from the packaged claude profile's binary, or ``None`` when
    the binary is not found, does not run, or exits non-zero (Story 113.11, CAP-298).
    ``plugin_refusal`` reads it before any spawn; unit tests stub it, never shelling to ``claude``."""
    try:
        profile = _claude_profile()
    except ChallengeHarnessError:
        return None
    binary = _resolve_binary(profile)
    if binary is None:
        return None
    try:
        result = PosixProcess().run(
            [binary, "--version"], cwd=Path(tempfile.gettempdir()), timeout_s=_VERSION_TIMEOUT_S
        )
    except ProcessError:
        return None
    return result.stdout if result.returncode == 0 else None


@dataclass
class ClaudeChallengeRunner:
    """Launches one challenge session and waits for it. Injected in tests."""

    plugins_root: Path
    timeout_s: float = _DEFAULT_TIMEOUT_S

    def run(self, *, prompt: str, model: str | None, root: Path, target: Path | None, log_path: Path) -> int:
        """Run the session on ``root``'s files from a fresh directory outside ``root``."""
        profile = _claude_profile()
        binary = _resolve_binary(profile)
        if binary is None:
            raise ChallengeHarnessError(f"{profile.binary!r} is not on PATH")
        argv = render_argv(
            profile,
            prompt=prompt,
            model=model,
            session_id=str(uuid.uuid4()),
            read_rules=plugin_cache_read_rules(self.plugins_root),
            run_dir=log_path.parent,
            deny_rules=forbidden_read_rules(root, target),
        )
        env = {**os.environ, **dict(profile.env)}
        env.pop(ADDITIONAL_DIRS_CLAUDE_MD_ENV, None)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=_SESSION_DIR_PREFIX) as scratch:
            session_dir = Path(scratch)
            if session_dir.resolve().is_relative_to(root.resolve()):
                raise ChallengeHarnessError(
                    f"the session directory {session_dir} is inside {root}; set TMPDIR outside the repo"
                )
            try:
                result = PosixProcess().run([binary, *argv], cwd=session_dir, timeout_s=self.timeout_s, env=env)
            except ProcessError as exc:
                log_path.write_text(f"challenge session did not complete: {exc}\n", encoding="utf-8")
                raise ChallengeHarnessError(f"challenge session did not complete: {exc}") from exc
        log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
        return result.returncode
