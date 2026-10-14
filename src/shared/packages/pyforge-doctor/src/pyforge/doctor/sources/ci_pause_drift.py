"""Story 45.1 (CAP-89 / FR-22): CI pause drift, stuck, and overdue rows.

Reads steward ``ci status --json`` through ``pyforge.core.dispatch`` (never
imports ``pyforge.steward`` or calls ``gh``). Warn-only; a refused or partial
read emits explicit findings instead of silence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .. import cli_bridge
from ..cli_bridge import CliBridgeError
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather",)

_DISPATCH_TIMEOUT = 120.0
_VALID_VERDICTS = frozenset(
    {
        "live",
        "paused",
        "opt-in-off",
        "paused-manually",
        "retired",
        "drift",
        "stuck",
        "overdue",
    }
)


def gather(target: Path) -> tuple[Finding, ...]:
    return degrade_on_exception(
        Source.CI_PAUSE_DRIFT,
        "ci-pause-drift",
        lambda: _gather(target),
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    argv = [
        sys.executable,
        "-m",
        "pyforge.core.dispatch",
        "steward",
        "ci",
        "status",
        "--json",
    ]
    try:
        code, stdout, stderr = cli_bridge.run_argv(
            argv, cwd=target.resolve(), timeout=_DISPATCH_TIMEOUT
        )
    except CliBridgeError as exc:
        return _unobserved(f"cause: {exc}")

    partial = code == 1
    if code == 0:
        payload = _parse_payload(stdout)
    elif partial:
        payload = _parse_payload(stderr)
    else:
        first_line = (stderr or stdout).strip().splitlines()
        hint = first_line[0] if first_line else "(no stderr)"
        return _unobserved(f"exit {code}: {hint}")

    if payload is None:
        stream = stderr if partial else stdout
        return _unobserved(f"exit {code}: unparseable CI status JSON")

    findings = list(_findings_for_rows(payload["rows"]))
    if partial:
        findings.append(
            Finding(
                source=Source.CI_PAUSE_DRIFT,
                check="ci-pause-partial",
                status=DoctorStatus.WARN,
                message="steward ci status --json returned exit 1 (partial read)",
                evidence={"exit_code": 1},
            )
        )
        return tuple(findings)

    if not findings:
        count = len(payload["rows"])
        return (
            Finding(
                source=Source.CI_PAUSE_DRIFT,
                check="ci-pause-drift",
                status=DoctorStatus.OK,
                message=f"judged {count} CI surface row(s); none drifted, stuck, or overdue",
                evidence={"row_count": count},
            ),
        )
    return tuple(findings)


def _parse_payload(text: str) -> dict[str, Any] | None:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    rows = raw.get("rows")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            return None
        if not isinstance(row.get("id"), str):
            return None
        verdict = row.get("verdict")
        if verdict not in _VALID_VERDICTS:
            return None
    return raw


def _findings_for_rows(rows: list[dict[str, Any]]) -> tuple[Finding, ...]:
    out: list[Finding] = []
    for row in rows:
        out.extend(_findings_for_row(row))
    return tuple(out)


def _findings_for_row(row: dict[str, Any]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    row_id = row["id"]
    switch = row.get("switch")
    owner = _owner_label(row.get("owner"))
    verdict = row["verdict"]

    if verdict == "drift":
        msg = f"CI surface {row_id!r} drifted (switch {switch!r}, owner {owner})"
        detail = row.get("detail")
        if isinstance(detail, str) and detail:
            msg = f"{msg}: {detail}"
        findings.append(
            Finding(
                source=Source.CI_PAUSE_DRIFT,
                check="ci-pause-drift",
                status=DoctorStatus.WARN,
                message=msg,
                evidence={"row": dict(row)},
            )
        )
    elif verdict == "stuck":
        last_green = row.get("last_green_run")
        msg = (
            f"CI surface {row_id!r} stuck (switch {switch!r}, owner {owner}, "
            f"last_green_run {last_green!r})"
        )
        findings.append(
            Finding(
                source=Source.CI_PAUSE_DRIFT,
                check="ci-pause-stuck",
                status=DoctorStatus.WARN,
                message=msg,
                evidence={"row": dict(row)},
            )
        )

    days_left = row.get("review_days_left")
    if isinstance(days_left, int) and days_left < 0:
        review_by = row.get("review_by")
        overdue_days = -days_left
        msg = (
            f"CI surface {row_id!r} past review date (switch {switch!r}, owner {owner}, "
            f"review_by {review_by!r}, {overdue_days} day(s) overdue)"
        )
        findings.append(
            Finding(
                source=Source.CI_PAUSE_DRIFT,
                check="ci-pause-overdue",
                status=DoctorStatus.WARN,
                message=msg,
                evidence={"row": dict(row)},
            )
        )

    return tuple(findings)


def _owner_label(owner: object) -> str:
    if owner is None or owner == "":
        return "(none)"
    return str(owner)


def _unobserved(detail: str) -> tuple[Finding, ...]:
    return (
        Finding(
            source=Source.CI_PAUSE_DRIFT,
            check="ci-pause-unobserved",
            status=DoctorStatus.WARN,
            message=f"could not read steward ci status --json ({detail})",
            evidence={"detail": detail},
        ),
    )
