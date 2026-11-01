"""The EGM challenger's harness launch (Story 113.1, CAP-298).

One synchronous Claude Code session per challenge: the packaged ``claude``
profile's argv, its ``{model_args}``/``{prompt}``/``{session_id}`` placeholders
substituted, and its ``--settings`` JSON widened with read-only rules on the
EGM plugin cache so a headless session can open the reviewer personas. The
challenger is Claude-only by construction -- EGM is a Claude Code plugin -- so
this adapter never consults a station's ``harness_preference`` (a Cursor-first
station still challenges on Claude).

Marshal reads nothing the session says; the caller reads the JSON report file
the session was told to write (AD-1).
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError

from ..core.harness_profile import HarnessProfile, load_packaged_profiles, translate_model

_PROFILE_NAME = "claude"
_DEFAULT_TIMEOUT_S = 3600.0
_PLUGIN_CACHE_READ_DIRS: tuple[str, ...] = ("agents", "docs", "resources", "skills")
# The orchestrator session spawns reviewers and writes one report; nothing else (review S5).
ORCHESTRATOR_TOOLS: tuple[str, ...] = ("Agent", "Read", "Grep", "Glob")
DENIED_TOOLS: tuple[str, ...] = ("Bash", "Edit", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch")
_PERMISSION_MODE = "default"  # never the dispatch profile's bypassPermissions: the allow/deny lists must bind


class ChallengeHarnessError(PyforgeError, Exception):
    """The challenge session could not be launched."""


def plugin_cache_read_rules(plugins_root: Path) -> list[str]:
    """``Read(...)`` allow rules on the pinned plugin's resource folders, the
    version segment wildcarded so a refresh keeps matching (EGM docs/claude.md)."""
    base = plugins_root / "cache" / "egm" / "egm" / "*"
    return [f"Read(/{base / folder}/**)" for folder in _PLUGIN_CACHE_READ_DIRS]


def widen_settings(settings_json: str, read_rules: Sequence[str], *, run_dir: Path | None = None) -> str:
    """Add the orchestrator's permissions to a profile's ``--settings`` JSON: the
    plugin-cache read rules, read-only tools plus ``Agent``, one ``Write`` rule
    confined to the run folder, and an explicit deny list."""
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
    deny.extend(tool for tool in DENIED_TOOLS if tool not in deny)
    permissions["deny"] = deny
    settings["permissions"] = permissions
    return json.dumps(settings, separators=(",", ":"))


def render_argv(
    profile: HarnessProfile,
    *,
    prompt: str,
    model: str | None,
    session_id: str,
    read_rules: Sequence[str],
    run_dir: Path | None = None,
) -> list[str]:
    rendered_model, _omitted = translate_model(profile, model)
    argv: list[str] = []
    tokens = list(profile.argv)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--settings" and index + 1 < len(tokens):
            argv += ["--settings", widen_settings(tokens[index + 1], read_rules, run_dir=run_dir)]
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
    return argv


def _resolve_binary(profile: HarnessProfile) -> str | None:
    found = shutil.which(profile.binary)
    if found:
        return found
    for directory in profile.fallback_bin_dirs:
        candidate = Path(os.path.expanduser(directory)) / profile.binary
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


@dataclass
class ClaudeChallengeRunner:
    """Launches one challenge session and waits for it. Injected in tests."""

    plugins_root: Path
    timeout_s: float = _DEFAULT_TIMEOUT_S

    def run(self, *, prompt: str, model: str | None, cwd: Path, log_path: Path) -> int:
        profiles = load_packaged_profiles()
        profile = profiles.get(_PROFILE_NAME)
        if profile is None:
            raise ChallengeHarnessError("no packaged 'claude' harness profile")
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
        )
        env = {**os.environ, **dict(profile.env)}
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = PosixProcess().run([binary, *argv], cwd=cwd, timeout_s=self.timeout_s, env=env)
        except ProcessError as exc:
            log_path.write_text(f"challenge session did not complete: {exc}\n", encoding="utf-8")
            raise ChallengeHarnessError(f"challenge session did not complete: {exc}") from exc
        log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
        return result.returncode
