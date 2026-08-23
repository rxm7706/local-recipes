"""Steward's machine-bootstrap duty helpers (Epic 17, Story 17.1).

``steward init`` reports host prereqs (pixi/git/gh/podman) with named
remedies; pixi's floor is read from the same ``requires-pixi`` pin that
``scripts/pixi_version_registry.py`` treats as master (AD-1: derive, never
hand-pin a second floor).

``steward shell-init`` emits idempotent shell setup (PATH, env, bash
completions) to stdout for ``eval "$(steward shell-init)"``. Story 17.2
owns ``setup``/``initrepo`` — nothing here clones, installs, or writes rc
files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .interfaces import DutyResult

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_PIXI_TOML_RELATIVE_PATH = Path("pixi.toml")
_REQUIRES_PIXI_RE = re.compile(r'requires-pixi = ">=([^"]+)"')
_SHELL_INIT_MARKER = "# pyforge-steward shell-init"
_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")

_PREREQ_ORDER: tuple[str, ...] = ("pixi", "git", "gh", "podman")

_REMEDIES: dict[str, dict[str, str]] = {
    "pixi": {
        "missing": "install-pixi: curl -fsSL https://pixi.sh/install.sh | bash",
        "below-floor": "upgrade-pixi: pixi self-update (or reinstall from https://pixi.sh)",
    },
    "git": {
        "missing": "install-git: install git via your OS package manager (e.g. apt install git)",
    },
    "gh": {
        "missing": "install-gh: https://github.com/cli/cli#installation (or apt/snap install gh)",
    },
    "podman": {
        "missing": "install-podman: https://podman.io/docs/installation",
    },
}


@dataclass(frozen=True)
class PrereqResult:
    """One prereq row — always carries a remedy name when ``ok`` is False."""

    name: str
    ok: bool
    found: str | None
    required: str | None
    remedy: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "found": self.found,
            "required": self.required,
            "remedy": self.remedy,
        }


def repo_root() -> Path:
    """Walk up to the local-recipes checkout root."""
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _BMAD_LOOP_WORKTREE_RELATIVE_PATH).is_file():
            return ancestor
    raise RuntimeError(
        f"bootstrap.py: could not locate {_BMAD_LOOP_WORKTREE_RELATIVE_PATH} "
        f"by walking up from {here} — this module must live inside a "
        "local-recipes checkout."
    )


def pixi_floor_version(*, root: Path | None = None) -> str:
    """Floor from ``pixi.toml``'s ``requires-pixi`` — same source as the registry."""
    pixi_toml = (root or repo_root()) / _PIXI_TOML_RELATIVE_PATH
    text = pixi_toml.read_text(encoding="utf-8")
    match = _REQUIRES_PIXI_RE.search(text)
    if not match:
        raise RuntimeError("pixi.toml requires-pixi not found — cannot determine pixi floor")
    return match.group(1)


def _parse_version_tuple(version: str) -> tuple[int, ...]:
    cleaned = version.strip().lstrip("v").split("-", 1)[0]
    parts: list[int] = []
    for segment in cleaned.split("."):
        if not segment:
            continue
        digits = "".join(ch for ch in segment if ch.isdigit())
        if digits:
            parts.append(int(digits))
    if not parts:
        raise ValueError(f"unparseable version: {version!r}")
    return tuple(parts)


def _version_gte(found: str, floor: str) -> bool:
    return _parse_version_tuple(found) >= _parse_version_tuple(floor)


def _first_version(text: str) -> str | None:
    match = _VERSION_RE.search(text)
    return match.group(1) if match else None


def _tool_version(name: str, path: str) -> str | None:
    try:
        proc = subprocess.run(
            [path, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return _first_version(proc.stdout) or _first_version(proc.stderr)


def check_prereq(name: str, *, pixi_floor: str) -> PrereqResult:
    """Check one prereq and attach a named remedy on failure."""
    path = shutil.which(name)
    if path is None:
        return PrereqResult(
            name=name,
            ok=False,
            found=None,
            required=pixi_floor if name == "pixi" else None,
            remedy=_REMEDIES[name]["missing"],
        )

    version = _tool_version(name, path)
    if version is None:
        return PrereqResult(
            name=name,
            ok=False,
            found=path,
            required=pixi_floor if name == "pixi" else None,
            remedy=_REMEDIES[name]["missing"],
        )

    if name == "pixi":
        ok = _version_gte(version, pixi_floor)
        return PrereqResult(
            name=name,
            ok=ok,
            found=version,
            required=pixi_floor,
            remedy=None if ok else _REMEDIES["pixi"]["below-floor"],
        )

    return PrereqResult(
        name=name,
        ok=True,
        found=version,
        required=None,
        remedy=None,
    )


def gather_prereqs(*, root: Path | None = None) -> tuple[PrereqResult, ...]:
    floor = pixi_floor_version(root=root)
    return tuple(check_prereq(name, pixi_floor=floor) for name in _PREREQ_ORDER)


def format_init_report(results: tuple[PrereqResult, ...], *, as_json: bool) -> str:
    all_ok = all(r.ok for r in results)
    if as_json:
        payload = {
            "ok": all_ok,
            "prereqs": [r.to_dict() for r in results],
        }
        return json.dumps(payload, indent=2)

    lines = ["steward init: prereq report"]
    for row in results:
        if row.ok:
            detail = f"{row.found}"
            if row.required:
                detail += f" (floor >= {row.required})"
            lines.append(f"  ok   {row.name}: {detail}")
        else:
            lines.append(f"  FAIL {row.name}: {row.remedy}")
    lines.append("steward init: PASS" if all_ok else "steward init: FAIL")
    return "\n".join(lines)


def shell_init_script(*, root: Path | None = None) -> str:
    """Idempotent shell snippet — safe to eval repeatedly."""
    repo = root or repo_root()
    pixi_bin = Path.home() / ".pixi" / "bin"
    lines = [
        _SHELL_INIT_MARKER,
        f'export PYFORGE_REPO_ROOT="{repo}"',
        f'export PATH="{pixi_bin}:$PATH"',
        'if [ -n "${BASH_VERSION:-}" ]; then',
        "  _pyforge_steward_complete() {",
        '    local cur="${COMP_WORDS[COMP_CWORD]}"',
        '  COMPREPLY=( $(compgen -W "keys deploy provision budget sync workspace upgrade suite init shell-init" -- "$cur") )',
        "  }",
        "  complete -o default -F _pyforge_steward_complete steward 2>/dev/null || true",
        "fi",
    ]
    return "\n".join(lines)


def shell_init_payload(*, root: Path | None = None) -> dict[str, object]:
    repo = root or repo_root()
    pixi_bin = str(Path.home() / ".pixi" / "bin")
    script = shell_init_script(root=repo)
    return {
        "path_prepend": [pixi_bin],
        "env": {
            "PYFORGE_REPO_ROOT": str(repo),
            "PATH": f"{pixi_bin}:{os.environ.get('PATH', '')}",
        },
        "completions": "bash",
        "script": script,
    }


def format_shell_init(*, as_json: bool, root: Path | None = None) -> str:
    if as_json:
        return json.dumps(shell_init_payload(root=root), indent=2)
    return shell_init_script(root=root)


class InitDuty:
    """``steward init`` — prereq detection with named remedies."""

    name = "init"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        try:
            results = gather_prereqs()
        except RuntimeError as exc:
            message = f"init: {exc}"
            if ns.json:
                return DutyResult(ok=False, summary=json.dumps({"ok": False, "error": message}, indent=2))
            return DutyResult(ok=False, summary=message)

        all_ok = all(r.ok for r in results)
        return DutyResult(
            ok=all_ok,
            summary=format_init_report(results, as_json=ns.json),
            details={"prereqs": [r.to_dict() for r in results]},
        )


class ShellInitDuty:
    """``steward shell-init`` — emit PATH/completions/env for eval."""

    name = "shell-init"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        try:
            summary = format_shell_init(as_json=ns.json)
        except RuntimeError as exc:
            message = f"shell-init: {exc}"
            if ns.json:
                return DutyResult(ok=False, summary=json.dumps({"ok": False, "error": message}, indent=2))
            return DutyResult(ok=False, summary=message)
        return DutyResult(ok=True, summary=summary)
