#!/usr/bin/env python3
"""``.pre-commit-config.yaml`` exists at the repo root, installs the
``commit-msg`` and ``pre-push`` hook types by default, and carries the two
local hooks the repo's policy relies on (steward Story 66.2,
``spec-pyforge-steward`` CAP-154):

* ``commit-msg-no-attribution`` -- refuses ``Co-Authored-By:`` and AI-attribution
  trailers (the AGENTS.md policy line, enforced instead of stated)
* ``pre-push-preflight`` -- runs ``pixi run -e pyforge-guild pr-preflight``
  before a push leaves the machine (the 2026-09-20 PR #1551 coverage-floor
  miss is the observed evidence)

``steward setup`` / ``initrepo`` install the file through their existing
hooks step; this check is what keeps the file from silently disappearing.

EXIT  0 clean · 1 findings · 2 could-not-run
"""
from __future__ import annotations

# Registry declaration -- see scripts/detectors.py. Tracked files only.
DETECTOR = {"scope": "repo"}

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".pre-commit-config.yaml"
REQUIRED_HOOK_TYPES = {"commit-msg", "pre-push"}
REQUIRED_HOOKS = {
    "commit-msg-no-attribution": ("commit-msg", "scripts/commit_msg_hook.py"),
    "pre-push-preflight": ("pre-push", "scripts/pre_push_preflight.sh"),
}


def findings(config_path: Path = CONFIG) -> list[str]:
    if not config_path.is_file():
        return [f"{config_path.relative_to(ROOT)} is missing -- `steward setup`'s hooks step installs nothing without it"]
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [f"{config_path.name} is not valid YAML: {exc}"]
    out: list[str] = []
    types = set(data.get("default_install_hook_types") or [])
    missing_types = REQUIRED_HOOK_TYPES - types
    if missing_types:
        out.append(f"default_install_hook_types lacks {sorted(missing_types)} -- a bare `pre-commit install` would not install them")
    hooks: dict[str, dict] = {}
    for repo in data.get("repos") or []:
        for hook in repo.get("hooks") or []:
            if isinstance(hook, dict) and "id" in hook:
                hooks[str(hook["id"])] = hook
    for hook_id, (stage, entry_path) in REQUIRED_HOOKS.items():
        hook = hooks.get(hook_id)
        if hook is None:
            out.append(f"hook `{hook_id}` is missing")
            continue
        stages = hook.get("stages") or []
        if stage not in stages:
            out.append(f"hook `{hook_id}` must run at stage `{stage}` (stages = {stages})")
        entry = str(hook.get("entry", ""))
        if entry_path not in entry:
            out.append(f"hook `{hook_id}` entry must invoke `{entry_path}` (entry = {entry!r})")
        if not (ROOT / entry_path).is_file():
            out.append(f"hook `{hook_id}` entry script `{entry_path}` does not exist")
    return out


def main() -> int:
    found = findings()
    for f in found:
        print(f"[precommit-config] fail -- {f}")
    if found:
        return 1
    print(f"[precommit-config] ok -- {CONFIG.name} declares {sorted(REQUIRED_HOOK_TYPES)} and both policy hooks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
