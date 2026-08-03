"""Unit tests for ``pyforge.marshal.core.gate`` (Story 2.1, AD-4/AD-7) --
the pure per-command classification core, driven entirely by SYNTHETIC
``ProcessResult`` values (no real subprocess -- that lives in
``test_process_posix.py`` and the real end-to-end
``tests/unit/test_cli.py::gate evaluate`` cases).
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import gate
from pyforge.marshal.core.findings import UnregisteredFindingCodeError
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


def test_classify_outcome_signal_termination_is_not_reported_as_an_exit_code():
    """Review finding: ``subprocess`` reports a signal-terminated child as a
    NEGATIVE returncode, so the message read "exited -9" -- an exit status no
    process can return, telling an operator their check FAILED when the OOM
    killer or a CI SIGTERM ended it before it produced any result.

    The classification deliberately stays MRS-GATE-001/GATE_FAILED: the
    command really did run and really did not pass, and re-routing it to
    UNEVALUABLE would move the verdict TOWARD green on an ambiguity."""
    result = ProcessResult(returncode=-9, stdout="", stderr="")
    report, finding = gate.classify_outcome("pytest -q", result)
    assert report["returncode"] == -9
    assert "signal 9" in finding.message
    assert "exited -9" not in finding.message
    assert finding.code == "MRS-GATE-001"
    assert classify(finding.code) is Verdict.GATE_FAILED


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


def test_classify_outcome_rejects_a_result_alongside_a_declared_failure():
    """Review finding: the under-specified direction failed loud, but the
    OVER-specified one was silent -- a caller passing both a ProcessResult
    and a declared failure got a passing report and no finding, silently
    DROPPING the failure. That is the one direction this function must never
    fail quietly in, so it now fails loud symmetrically."""
    result = ProcessResult(returncode=0, stdout="", stderr="")
    with pytest.raises(ValueError):
        gate.classify_outcome("cmd", result, failure_code="MRS-GATE-002")
    with pytest.raises(ValueError):
        gate.classify_outcome("cmd", result, failure_reason="never ran")


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


def test_classify_outcome_rejects_a_failure_code_whose_status_is_ok():
    """The last silent direction in `classify_outcome`. The finding it
    builds is stamped `Severity.ERROR` unconditionally, but AD-39 forbids an
    ok-status envelope from carrying an error-severity finding -- so a
    WARN-classified `failure_code` returned a perfectly ordinary-looking
    report here and then crashed `build_envelope` with a `ValueError`
    `main()` does not catch, several frames from the caller that erred.
    Verified live before the fix (`MRS-GATE-004` -> verdict `warn` ->
    "status 'ok' but at least one finding has severity 'error'")."""
    with pytest.raises(ValueError, match="classifies to 'warn'"):
        gate.classify_outcome(
            "cmd", None, failure_code="MRS-GATE-004", failure_reason="reason"
        )


def test_classify_outcome_rejects_an_unregistered_failure_code():
    """`classify()` raises for a code that is in no registry, so the same
    guard closes the unregistered-code hole too -- failing at the caller
    rather than downstream in `compute_verdict`."""
    with pytest.raises(UnregisteredFindingCodeError):
        gate.classify_outcome(
            "cmd", None, failure_code="MRS-NOPE-999", failure_reason="reason"
        )


def test_classify_outcome_still_accepts_the_two_documented_launch_failures():
    """The guard must not narrow the real contract: both codes `cli/gate.py`
    actually passes still classify normally."""
    for code in ("MRS-GATE-002", "MRS-GATE-003"):
        report, finding = gate.classify_outcome(
            "cmd", None, failure_code=code, failure_reason="reason"
        )
        assert report["resolvable"] is False
        assert finding is not None
        assert finding.code == code
