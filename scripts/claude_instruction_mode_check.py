#!/usr/bin/env python3
"""Advisory currency check: is this host's Claude Code new enough for the
built-in ``agents-md`` mod, and is the mod pinned to the mode this repo relies
on? (scribe Story 19.3, ``spec-pyforge-scribe`` CAP-29.)

Claude Code 2.1.277 (2026-09-18) ships a built-in ``agents-md`` mod. Its
default mode, ``claude-md-or-agents-md``, *stays out of any project that has a
``CLAUDE.md``* -- so in this repo the mod does nothing unless the option
``instructionFiles`` is set to ``claude-md-and-agents-md``, and only then does
a nested ``AGENTS.md`` (``src/shared/packages/pyforge-atlas/AGENTS.md``) ever
reach Claude Code. The option lives in the OPERATOR's settings
(``~/.claude/settings.json`` → ``pluginConfigs."agents-md@builtin".options``,
legacy key ``projectInstructions``) or in ``--settings`` -- never in the
project's ``.claude/settings.json``, which is why this is a host check and not
a repo one. Marshal pins it for dispatched sessions (Story 46.11); this script
tells the operator about their own interactive sessions.

Nothing here gates: the ``@AGENTS.md`` import in ``CLAUDE.md`` is the floor on
every runtime, and a runtime below 2.1.277 (or Bedrock / Vertex / Foundry, where
the mod is unavailable) still reads ``AGENTS.md`` through it.

EXIT
    0  claude is absent (nothing to check -- silent), or ≥ 2.1.277 with the
       pinned mode
    1  claude present but below 2.1.277, or the mode is not the pinned one
       (findings are advisory: the import still works)
    2  ``claude --version`` ran but its output could not be parsed
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `runtime`: reads the host's
# own claude binary and ~/.claude/settings.json, neither of which exists on a
# CI runner, so this never joins `detectors-ci`.
DETECTOR = {"scope": "runtime"}

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

MIN_VERSION = (2, 1, 277)
PINNED_MODE = "claude-md-and-agents-md"
PLUGIN_KEY = "agents-md@builtin"
#: The legacy `projectInstructions` spellings the mod still honours.
LEGACY_MODES = {
    "none": "managed-only",
    "claude": "claude-md",
    "agents-fallback": "claude-md-or-agents-md",
    "both": "claude-md-and-agents-md",
}
_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def parse_version(text: str) -> tuple[int, int, int] | None:
    m = _VERSION_RE.search(text or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def configured_mode(settings: dict) -> str | None:
    """The mode a settings document pins, or ``None`` when it pins nothing
    (the mod then runs in its default ``claude-md-or-agents-md``)."""
    opts = (
        settings.get("pluginConfigs", {}).get(PLUGIN_KEY, {}).get("options", {})
        if isinstance(settings.get("pluginConfigs"), dict)
        else {}
    )
    mode = opts.get("instructionFiles") if isinstance(opts, dict) else None
    if isinstance(mode, str):
        return mode
    legacy = settings.get("projectInstructions")
    if isinstance(legacy, str):
        return LEGACY_MODES.get(legacy, legacy)
    return None


def read_settings(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--settings", type=Path, default=Path.home() / ".claude" / "settings.json")
    parser.add_argument("--claude", default=None, help="claude binary (default: PATH lookup)")
    args = parser.parse_args(argv)

    binary = args.claude or shutil.which("claude")
    if not binary:
        print("[claude-instruction-mode] ok -- no claude binary on this host; nothing to check")
        return 0
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[claude-instruction-mode] could-not-run -- `claude --version` failed: {exc}")
        return 2
    version = parse_version(out)
    if version is None:
        print(f"[claude-instruction-mode] could-not-run -- unparseable `claude --version` output: {out.strip()!r}")
        return 2

    findings = 0
    if version < MIN_VERSION:
        v = ".".join(map(str, version))
        print(
            f"[claude-instruction-mode] warn -- Claude Code {v} predates the built-in agents-md mod "
            f"(2.1.277); AGENTS.md reaches it only through CLAUDE.md's @AGENTS.md import, and nested "
            f"AGENTS.md files (pyforge-atlas) do not load -- upgrade to opt in"
        )
        findings += 1
    mode = configured_mode(read_settings(args.settings))
    if mode != PINNED_MODE:
        shown = mode or "default (claude-md-or-agents-md — stays out of a project with a CLAUDE.md)"
        print(
            f"[claude-instruction-mode] warn -- {args.settings} pins instructionFiles={shown!s}, "
            f"not {PINNED_MODE!r}; interactive sessions will not load nested AGENTS.md files. "
            f'Set pluginConfigs."{PLUGIN_KEY}".options.instructionFiles = "{PINNED_MODE}" '
            f"(or /config → Project instructions). Dispatched sessions are pinned by marshal (Story 46.11)."
        )
        findings += 1
    if findings == 0:
        v = ".".join(map(str, version))
        print(f"[claude-instruction-mode] ok -- Claude Code {v} with instructionFiles={PINNED_MODE}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
