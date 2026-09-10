"""Doctor flag kill-switch actuator (Story 48.5 / R-21)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KillSwitchResult:
    flag: str
    path: Path
    previous_state: str
    new_state: str


def disable_flag(path: Path, flag: str) -> KillSwitchResult:
    """Disable one flag in the FILE resolver tree and record the kill-switch metric."""
    tree = json.loads(path.read_text(encoding="utf-8"))
    flags = tree.setdefault("flags", {})
    entry = flags.get(flag)
    if not isinstance(entry, dict):
        msg = f"flag {flag!r} not found in {path}"
        raise KeyError(msg)
    previous = str(entry.get("state", "ENABLED"))
    entry["state"] = "DISABLED"
    path.write_text(json.dumps(tree, indent=2) + "\n", encoding="utf-8")
    return KillSwitchResult(
        flag=flag,
        path=path,
        previous_state=previous,
        new_state="DISABLED",
    )


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
