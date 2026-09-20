"""Steward ``revoke`` duty — stop one runaway subject (Story 42.2).

``pyforge steward revoke --sub <id>`` revokes that subject's queued Celery
tasks and marks its live ``run_state`` rows CANCELLED. Red-team A-6 asked for
"one command", and this is it.

The write itself is not performed here. ``run_state`` has exactly one writer
(canopy AD-12, the supervisor), and this package must not import Django, so the
duty drives the host's own management command --
``manage.py revoke_subject --sub <id> --json`` -- and reports what it said. The
same rule already shapes ``restore.py``: steward owns the operator grammar and
the exit code, never a second implementation of the platform's own work.

The interpreter matters: ``sys.executable`` is whatever runs steward, which on
a laptop is the ``pyforge-steward`` environment and has no Django. ``--python``
names the platform interpreter for exactly that reason, and its absence is
reported as a failed duty rather than a crash.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .bootstrap import repo_root
from .interfaces import DutyResult

MANAGE_PY_RELATIVE = ("src", "platform", "manage.py")
COMMAND = "revoke_subject"
# The host command does two things -- a SELECT/UPDATE on `run_state` and a
# Celery broadcast -- and mid-incident is exactly when either may not answer. A
# duty that hangs there gives the operator neither a result nor an exit code.
REVOKE_TIMEOUT_SECONDS = 120

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def manage_py(root: Path | None = None) -> Path:
    return (root or repo_root()).joinpath(*MANAGE_PY_RELATIVE)


def revoke_command(sub: str, *, python: str | None, root: Path | None = None) -> list[str]:
    return [
        python or sys.executable,
        str(manage_py(root)),
        COMMAND,
        "--sub",
        sub,
        "--json",
    ]


def run_revoke(
    sub: str,
    *,
    python: str | None = None,
    root: Path | None = None,
    runner: Runner | None = None,
) -> dict[str, Any]:
    """Invoke the host command and return its JSON report.

    Raises ``RuntimeError`` (never ``SystemExit``) on any failure, so the duty
    boundary below owns the outcome and ``cli.main`` still owns the exit code.
    """
    manage = manage_py(root)
    if not manage.is_file():
        msg = f"platform manage.py not found at {manage}"
        raise RuntimeError(msg)
    call = runner if runner is not None else subprocess.run
    try:
        proc = call(
            revoke_command(sub, python=python, root=root),
            cwd=str(manage.parent),
            capture_output=True,
            text=True,
            check=False,
            timeout=REVOKE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"revoke_subject timed out after {exc.timeout:g}s"
        raise RuntimeError(msg) from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        msg = f"revoke_subject exited {proc.returncode}: {detail}"
        raise RuntimeError(msg)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        msg = f"revoke_subject did not emit JSON: {proc.stdout!r}"
        raise RuntimeError(msg) from exc
    if not isinstance(report, dict):
        msg = f"revoke_subject report is not an object: {report!r}"
        raise RuntimeError(msg)
    return report


class RevokeDuty:
    name = "revoke"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        sub = (getattr(ns, "sub", "") or "").strip()
        if not sub:
            return DutyResult(
                ok=False,
                summary="revoke: --sub is required",
            )
        try:
            report = run_revoke(sub, python=getattr(ns, "python", None))
        except Exception as exc:  # noqa: BLE001 — duty boundary
            return DutyResult(
                ok=False,
                summary=f"revoke failed for {sub}: {exc}",
                details={"error": str(exc), "sub": sub},
            )
        cancelled = report.get("cancelled_runs", 0)
        revoked = len(report.get("revoked_tasks") or ())
        # `ok` is the command's own verdict. A report that lacks it is a broken
        # contract, and a broken contract must not project as a clean revoke.
        ok = report.get("ok") is True
        summary = f"revoke {sub}: cancelled {cancelled} run(s), revoked {revoked} task(s)"
        if not ok:
            summary = f"{summary} — {report.get('revoke_error')}"
        return DutyResult(ok=ok, summary=summary, details=report)
