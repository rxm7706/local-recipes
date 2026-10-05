"""Pure Cursor config path and attribution helpers (Story 83.25, AD-4)."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

CURSOR_ATTRIBUTION_OFF_FINDING = "MRS-DISP-061"

_RUN_SCOPED_CONFIG_RELPATH = Path(".marshal") / "cursor-config"


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


def attribution_off_config(operator_config: dict[str, Any]) -> dict[str, Any]:
    """Copy ``operator_config`` with both attribution flags forced off."""
    config = deepcopy(operator_config)
    attribution = config.get("attribution")
    if not isinstance(attribution, dict):
        attribution = {}
        config["attribution"] = attribution
    attribution["attributeCommitsToAgent"] = False
    attribution["attributePRsToAgent"] = False
    return config
