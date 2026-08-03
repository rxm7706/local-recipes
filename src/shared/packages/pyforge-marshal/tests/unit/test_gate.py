"""Unit tests for ``pyforge.marshal.core.gate`` (Story 2.1, AD-4/AD-7) --
the pure per-command classification core, driven entirely by SYNTHETIC
``ProcessResult`` values (no real subprocess -- that lives in
``test_process_posix.py`` and the real end-to-end
``tests/unit/test_cli.py::gate evaluate`` cases).
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import gate
from pyforge.marshal.core.model import Finding, Severity, Verdict
from pyforge.marshal.core.verdict import classify
from pyforge.marshal.ports.process import ProcessResult

# --- classify_outcome: a passing command --------------------------------------


def test_classify_outcome_passing_command_has_no_finding():
    result = ProcessResult(returncode=0, stdout="ok\n", stderr="")
    report, finding = gate.classify_outcome("pytest -q", result)
    assert finding is None
    assert report == {
        "command": "pytest -q",
        "resolvable": True,
        "returncode": 0,
        "stdout": "ok\n",
        "stderr": "",
    }


# --- classify_outcome: a failing command (I/O matrix: "one command fails") ---


def test_classify_outcome_failing_command_reports_mrs_gate_001():
    result = ProcessResult(returncode=1, stdout="", stderr="boom\n")
    report, finding = gate.classify_outcome("pytest -q", result)
    assert report == {
        "command": "pytest -q",
        "resolvable": True,
        "returncode": 1,
        "stdout": "",
        "stderr": "boom\n",
    }
    assert finding is not None
    assert finding.code == "MRS-GATE-001"
    assert finding.severity is Severity.ERROR
    assert "pytest -q" in finding.message
    assert "1" in finding.message
    assert classify(finding.code) is Verdict.GATE_FAILED


def test_classify_outcome_failing_command_captures_the_real_exit_code():
    result = ProcessResult(returncode=127, stdout="", stderr="")
    _, finding = gate.classify_outcome("some-command", result)
    assert "127" in finding.message


# --- classify_outcome: result=None, a command that never ran -----------------
# (I/O matrix: "command not resolvable" -> MRS-GATE-002; "malformed command
# string" -> MRS-GATE-003 -- both share the same result=None shape, only the
# failure_code differs, since only the CLI boundary -- which caught the
# specific exception -- knows which one applies.)


def test_classify_outcome_unresolvable_command_reports_mrs_gate_002():
    report, finding = gate.classify_outcome(
        "nonexistent-bin",
        None,
        failure_code="MRS-GATE-002",
        failure_reason="executable not found",
    )
    assert report == {"command": "nonexistent-bin", "resolvable": False, "returncode": None}
    assert finding.code == "MRS-GATE-002"
    assert finding.severity is Severity.ERROR
    assert finding.message == "executable not found"
    assert classify(finding.code) is Verdict.UNEVALUABLE


def test_classify_outcome_malformed_command_reports_mrs_gate_003_no_spawn_shape():
    report, finding = gate.classify_outcome(
        "'unterminated",
        None,
        failure_code="MRS-GATE-003",
        failure_reason="cannot parse: No closing quotation",
    )
    # "no spawn attempted" (I/O matrix): the report carries no returncode/
    # stdout/stderr from a process that was never launched.
    assert report == {"command": "'unterminated", "resolvable": False, "returncode": None}
    assert "stdout" not in report
    assert "stderr" not in report
    assert finding.code == "MRS-GATE-003"
    assert classify(finding.code) is Verdict.UNEVALUABLE


def test_classify_outcome_requires_failure_code_and_reason_when_result_is_none():
    """A caller bug (result=None with no explanation) must fail loud, not
    silently default to some code -- this module has no way to guess WHY the
    command never ran."""
    with pytest.raises(ValueError):
        gate.classify_outcome("cmd", None)
    with pytest.raises(ValueError):
        gate.classify_outcome("cmd", None, failure_code="MRS-GATE-002")
    with pytest.raises(ValueError):
        gate.classify_outcome("cmd", None, failure_reason="whatever")


# --- no_commands_configured_finding (I/O matrix: "zero verify commands") -----


def test_no_commands_configured_finding_is_mrs_gate_004_warn():
    finding = gate.no_commands_configured_finding()
    assert isinstance(finding, Finding)
    assert finding.code == "MRS-GATE-004"
    assert finding.severity is Severity.WARN
    assert classify(finding.code) is Verdict.WARN


def test_no_commands_configured_finding_never_silently_clean():
    """The I/O matrix's own wording: 'never silently clean' -- proven by
    asserting the finding always classifies to a non-CLEAN verdict."""
    finding = gate.no_commands_configured_finding()
    assert classify(finding.code) is not Verdict.CLEAN
