"""Doctor flag kill-switch actuator (Story 48.5 / R-21)."""

from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pyforge.core.atomic_write import atomic_write_text

if TYPE_CHECKING:
    from prometheus_client import Counter


@dataclass(frozen=True)
class KillSwitchResult:
    flag: str
    path: Path
    previous_state: str
    new_state: str


def disable_flag(path: Path, flag: str) -> KillSwitchResult:
    """Disable one flag in the FILE resolver tree, replacing the file in one step.

    The write lands on the tree's real path (a symlinked tree stays a symlink and its target is replaced) with
    the file's own mode kept. It needs a new file in that directory: an ``OSError`` propagates to the caller,
    the tree untouched. ``kill_switch`` is the caller that also counts the activation.
    """
    tree = json.loads(path.read_text(encoding="utf-8"))
    flags = tree.setdefault("flags", {})
    entry = flags.get(flag)
    if not isinstance(entry, dict):
        msg = f"flag {flag!r} not found in {path}"
        raise KeyError(msg)
    previous = str(entry.get("state", "ENABLED"))
    entry["state"] = "DISABLED"
    # Story 62.1: replaced in one step (tmp file, then os.replace), the file's own mode kept -- a reader never
    # sees a truncated tree and falls back to the flag's default while it is being turned off. The replace lands
    # on the resolved path: os.replace on a symlink would swap the link for a regular file and leave the tree
    # every reader opens still ENABLED.
    target = path.resolve()
    atomic_write_text(target, json.dumps(tree, indent=2) + "\n", mode=stat.S_IMODE(target.stat().st_mode))
    return KillSwitchResult(
        flag=flag,
        path=path,
        previous_state=previous,
        new_state="DISABLED",
    )


_KILL_SWITCH_TOTAL: Counter | None
try:
    from prometheus_client import Counter

    _KILL_SWITCH_TOTAL = Counter(
        "pyforge_doctor_flag_kill_switch_total",
        "Doctor flag kill-switch activations",
        ["flag", "reason"],
    )
except ImportError:  # pragma: no cover -- optional at runtime
    _KILL_SWITCH_TOTAL = None


def record_kill_switch_metric(flag: str, reason: str) -> None:
    """Increment the contract kill-switch counter when prometheus_client is present."""
    if _KILL_SWITCH_TOTAL is not None:
        _KILL_SWITCH_TOTAL.labels(flag=flag, reason=reason).inc()


def kill_switch(path: Path, flag: str, reason: str) -> KillSwitchResult:
    result = disable_flag(path, flag)
    record_kill_switch_metric(flag, reason)
    return result
