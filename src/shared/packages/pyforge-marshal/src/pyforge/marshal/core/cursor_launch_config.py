"""Run-scoped Cursor CLI config for dispatch launches (Story 83.25).

``cursor-agent`` reads ``attribution.attributeCommitsToAgent`` (default
``true``) from ``cli-config.json`` under the effective config directory.
Marshal copies the operator's config into a worktree-local directory with
both attribution flags forced off and points ``CURSOR_CONFIG_DIR`` there.
The operator's own file is never written.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from pyforge.core.errors import PyforgeError

CURSOR_ATTRIBUTION_OFF_FINDING = "MRS-DISP-061"

_RUN_SCOPED_CONFIG_RELPATH = Path(".marshal") / "cursor-config"
_CONFIG_FILENAME = "cli-config.json"


class CursorLaunchConfigError(PyforgeError, Exception):
    """The operator Cursor config could not be read for a dispatch launch."""


def effective_cursor_config_dir(environ: Mapping[str, str]) -> Path:
    """Same resolution order ``cursor-agent`` uses for its config directory."""
    override = environ.get("CURSOR_CONFIG_DIR")
    if override:
        return Path(override)
    xdg = environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "cursor"
    return Path.home() / ".cursor"


def run_scoped_cursor_config_dir(worktree: Path) -> Path:
    """Directory inside ``worktree`` that holds the attribution-off copy."""
    return worktree.resolve() / _RUN_SCOPED_CONFIG_RELPATH


def _load_operator_cli_config(source_dir: Path) -> dict[str, Any]:
    path = source_dir / _CONFIG_FILENAME
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CursorLaunchConfigError(
            f"{CURSOR_ATTRIBUTION_OFF_FINDING}: cannot read operator Cursor "
            f"config {path!s}: {exc}"
        ) from exc
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CursorLaunchConfigError(
            f"{CURSOR_ATTRIBUTION_OFF_FINDING}: operator Cursor config "
            f"{path!s} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise CursorLaunchConfigError(
            f"{CURSOR_ATTRIBUTION_OFF_FINDING}: operator Cursor config "
            f"{path!s} must be a JSON object"
        )
    return parsed


def _attribution_off_config(operator_config: dict[str, Any]) -> dict[str, Any]:
    config = deepcopy(operator_config)
    attribution = config.get("attribution")
    if not isinstance(attribution, dict):
        attribution = {}
        config["attribution"] = attribution
    attribution["attributeCommitsToAgent"] = False
    attribution["attributePRsToAgent"] = False
    return config


def _write_run_scoped_config(config_dir: Path, config: dict[str, Any]) -> None:
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        path = config_dir / _CONFIG_FILENAME
        payload = json.dumps(config, indent=2, ensure_ascii=False)
        if payload and not payload.endswith("\n"):
            payload += "\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(payload)
    except OSError as exc:
        raise CursorLaunchConfigError(
            f"{CURSOR_ATTRIBUTION_OFF_FINDING}: cannot write run-scoped Cursor "
            f"config under {config_dir!s}: {exc}"
        ) from exc


def cursor_launch_env_overlay(
    worktree: Path,
    operator_environ: Mapping[str, str],
) -> dict[str, str]:
    """Build ``CURSOR_CONFIG_DIR`` for one Cursor harness launch.

    Reads the operator config from ``effective_cursor_config_dir(operator_environ)``,
    writes an attribution-off copy under ``worktree/.marshal/cursor-config/``,
    and returns the env overlay. Never mutates the operator's ``cli-config.json``.
    """
    source_dir = effective_cursor_config_dir(operator_environ)
    operator_config = _load_operator_cli_config(source_dir)
    run_dir = run_scoped_cursor_config_dir(worktree)
    _write_run_scoped_config(run_dir, _attribution_off_config(operator_config))
    return {"CURSOR_CONFIG_DIR": str(run_dir)}
