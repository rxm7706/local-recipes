"""Story 42.2 — `pyforge steward revoke --sub <id>` (red-team A-6 / R-8).

The duty owns the operator grammar and the exit code; the write itself belongs
to the host's `revoke_subject` management command (canopy AD-12: `run_state`
has one writer). So what is provable here is the seam — the argv the duty
builds, and how it projects the command's answer — and that is what these
tests hold.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pyforge.steward.cli import DUTIES, build_parser, main, resolve_duty
from pyforge.steward.interfaces import Duty
from pyforge.steward.revoke import RevokeDuty, revoke_command, run_revoke

EXIT_USAGE = 2

REPORT = {
    "subject": "agent-7",
    "cancelled_runs": 2,
    "run_ids": ["11111111-1111-1111-1111-111111111111"],
    "revoked_tasks": ["task-a", "task-b"],
    "revoke_error": None,
    "ok": True,
}


def _completed(stdout: str, *, returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["manage.py"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _ns(sub: str = "agent-7", python: str | None = None):
    argv = ["revoke", "--sub", sub]
    if python is not None:
        argv += ["--python", python]
    return build_parser().parse_args(argv)


def test_revoke_is_a_registered_duty():
    assert "revoke" in DUTIES
    impl = resolve_duty("revoke")
    assert isinstance(impl, RevokeDuty)
    assert isinstance(impl, Duty)
    assert impl.name == "revoke"


def test_sub_is_required():
    """`revoke` with no subject is a usage error, never a no-op that reports
    success -- an operator reaching for this command is mid-incident.
    """
    assert main(["revoke"]) == EXIT_USAGE


def test_command_names_the_hosts_management_command():
    argv = revoke_command("agent-7", python="/opt/env/bin/python")

    assert argv[0] == "/opt/env/bin/python"
    assert argv[1].endswith(str(Path("src") / "platform" / "manage.py"))
    assert argv[2:] == ["revoke_subject", "--sub", "agent-7", "--json"]


def test_duty_reports_what_the_command_did():
    calls: list[list[str]] = []

    def runner(argv, **_kwargs):
        calls.append(list(argv))
        return _completed(json.dumps(REPORT))

    report = run_revoke("agent-7", runner=runner)

    assert report == REPORT
    assert calls[0][2] == "revoke_subject"


def test_duty_summarises_the_report(monkeypatch):
    monkeypatch.setattr(
        "pyforge.steward.revoke.run_revoke",
        lambda sub, **_kwargs: REPORT,
    )

    result = RevokeDuty().run(_ns())

    assert result.ok is True
    assert "cancelled 2 run(s)" in result.summary
    assert "revoked 2 task(s)" in result.summary
    assert result.details["run_ids"] == REPORT["run_ids"]


def test_a_partial_revoke_is_not_reported_as_success(monkeypatch):
    """The rows were cancelled but the broker was unreachable: the tasks may
    still be held by a worker, so the duty must not exit 0.
    """
    partial = {**REPORT, "ok": False, "revoked_tasks": [], "revoke_error": "boom"}
    monkeypatch.setattr(
        "pyforge.steward.revoke.run_revoke",
        lambda sub, **_kwargs: partial,
    )

    result = RevokeDuty().run(_ns())

    assert result.ok is False
    assert "boom" in result.summary


@pytest.mark.parametrize(
    ("stdout", "returncode"),
    [("not json at all", 0), ("", 1)],
    ids=["unparseable", "nonzero-exit"],
)
def test_a_broken_command_fails_the_duty_instead_of_crashing(
    monkeypatch,
    stdout: str,
    returncode: int,
):
    """AD-8: a duty returns a result. A missing Django, a traceback on stderr
    or a non-zero exit must all land as `ok=False`, never as an exception the
    dispatcher has to project from.
    """
    monkeypatch.setattr(
        "pyforge.steward.revoke.subprocess.run",
        lambda *a, **k: _completed(stdout, returncode=returncode, stderr="trace"),
    )

    result = RevokeDuty().run(_ns())

    assert result.ok is False
    assert "revoke failed for agent-7" in result.summary


def test_a_missing_manage_py_is_named(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("pyforge.steward.revoke.repo_root", lambda: tmp_path)

    result = RevokeDuty().run(_ns())

    assert result.ok is False
    assert "manage.py" in result.summary
