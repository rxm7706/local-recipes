"""Pure last-pulse document shape. No Django, no HTTP, no pyforge."""

from __future__ import annotations

from typing import Any

EMPTY_PULSE: dict[str, Any] = {
    "empty": True,
    "advisory": True,
    "axes": [],
    "summary": None,
    "findings": [],
}


def present_pulse(document: dict[str, Any] | None) -> dict[str, Any]:
    """Project a stored fleet-surface document into portal context."""
    if document is None:
        return dict(EMPTY_PULSE)
    summary = document.get("summary")
    axes = document.get("axes")
    findings = document.get("findings")
    return {
        "empty": not isinstance(summary, dict),
        "advisory": True,
        "axes": axes if isinstance(axes, list) else [],
        "summary": summary if isinstance(summary, dict) else None,
        "findings": findings if isinstance(findings, list) else [],
    }
