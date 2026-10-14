"""Pure CI-pause-at-merge record and PR-body rendering (Story 100.1, CAP-292).

Steward's envelope is interpreted here; the subprocess lives in
``adapters/steward_cli.py`` only.
"""

from __future__ import annotations

from typing import Any

LANDING_CI_PAUSES_FLAG_KEY = "pyforge.marshal.landing_ci_pauses"

CI_PAUSES_UNKNOWN_PARSE_FINALIZE = {
    "state": "unknown",
    "reason": "finalize could not parse the landing's record",
}

_REASON_MAX_CHARS = 240


def _bound(text: str) -> str:
    text = text.strip()
    if len(text) <= _REASON_MAX_CHARS:
        return text
    return text[: _REASON_MAX_CHARS - 3] + "..."


def row_counts_as_paused_at_merge(row: dict[str, Any]) -> bool:
    """Whether one steward row belongs in ``surfaces`` at merge time."""
    row_id = str(row.get("id", ""))
    if row_id.startswith("unregistered:") or row_id.startswith("unregistered-workflow:"):
        return False
    declared = str(row.get("declared_state", ""))
    if declared == "paused-manually":
        return True
    if declared in ("opt-in-off", "retired"):
        return False
    live = str(row.get("live_switch_value") or "").strip().lower()
    return live == "true"


def surfaces_from_envelope(envelope: dict[str, Any]) -> list[str]:
    rows = envelope.get("rows")
    if not isinstance(rows, list):
        return []
    ids = [str(row["id"]) for row in rows if isinstance(row, dict) and row_counts_as_paused_at_merge(row)]
    return sorted(ids)


def envelope_is_valid(envelope: object) -> bool:
    if not isinstance(envelope, dict):
        return False
    for key in ("fetched_at", "repo", "rate_limit", "rows"):
        if key not in envelope:
            return False
    if not isinstance(envelope["rows"], list):
        return False
    if not isinstance(envelope["rate_limit"], dict):
        return False
    return True


def record_from_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": "read",
        "surfaces": surfaces_from_envelope(envelope),
        "fetched_at": envelope["fetched_at"],
    }


def unknown_record(reason: str) -> dict[str, str]:
    return {"state": "unknown", "reason": _bound(reason)}


def render_ci_pauses_pr_line(record: dict[str, Any]) -> str:
    state = record.get("state")
    if state == "read":
        surfaces = record.get("surfaces")
        if isinstance(surfaces, list) and len(surfaces) == 0:
            return "CI paused at merge: none"
        if isinstance(surfaces, list):
            return "CI paused at merge: " + ", ".join(str(s) for s in surfaces)
    if state == "unknown":
        reason = record.get("reason", "")
        return f"CI paused at merge: unknown ({reason})"
    return "CI paused at merge: unknown (invalid record)"


def append_ci_pauses_line_to_pr_body(base_body: str, record: dict[str, Any]) -> str:
    line = render_ci_pauses_pr_line(record)
    base = base_body.rstrip()
    return f"{base}\n{line}" if base else line
