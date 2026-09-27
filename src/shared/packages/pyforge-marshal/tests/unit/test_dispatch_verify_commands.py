"""`dispatch_verify._run_verify_command` and its shell-syntax guard.

Story 60.1 touched `dispatch_verify.py` (its scope base now names the full ref), which put the
module under the touched-module unit coverage floor at 76.4%; these paths -- a command that
cannot be parsed, one that uses shell syntax, one that cannot be launched, and the quoting rules
the guard honours -- had no test of their own.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.dispatch_verify import _bare_shell_metacharacters, _run_verify_command


class _Process:
    def __init__(self, outcome: ProcessResult | Exception) -> None:
        self.outcome, self.calls = outcome, []

    def run(self, argv, *, cwd, timeout_s=None, env=None):
        self.calls.append(list(argv))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("pytest -q", []),
        ("pytest -q && echo done", ["&", "&"]),
        ("a | b ; c", ["|", ";"]),
        ("echo '<not a redirect>'", []),
        ('echo "a && b"', []),
        ("echo a\\;b", []),
        ("echo (x) > out", ["(", ")", ">"]),
        ("echo 'it''s' \"q\\\"uoted\" | tee", ["|"]),
    ],
)
def test_bare_shell_metacharacters_ignores_quoted_and_escaped_ones(command: str, expected: list[str]) -> None:
    assert _bare_shell_metacharacters(command) == expected


def test_a_passing_command_runs_tokenized_with_no_finding(tmp_path: Path) -> None:
    process = _Process(ProcessResult(returncode=0, stdout="ok\n", stderr=""))
    report, finding = _run_verify_command("pytest -q 'tests/a b'", process=process, worktree=tmp_path)
    assert finding is None and report["resolvable"] is True
    assert process.calls == [["pytest", "-q", "tests/a b"]]


def test_an_unparseable_command_is_refused_before_it_runs(tmp_path: Path) -> None:
    process = _Process(ProcessResult(returncode=0, stdout="", stderr=""))
    report, finding = _run_verify_command('pytest "unterminated', process=process, worktree=tmp_path)
    assert finding is not None and finding.code == "MRS-GATE-003" and "cannot parse" in finding.message
    assert report["resolvable"] is False and process.calls == []


def test_shell_syntax_is_refused_naming_the_characters(tmp_path: Path) -> None:
    process = _Process(ProcessResult(returncode=0, stdout="", stderr=""))
    _report, finding = _run_verify_command(
        "pytest -q | tee log", process=process, worktree=tmp_path, failure_prefix="guard command"
    )
    assert finding is not None and finding.code == "MRS-GATE-003"
    assert (
        "guard command" in finding.message
        and "'|'" in finding.message
        and "never run through a shell" in finding.message
    )
    assert process.calls == []


def test_a_command_that_cannot_be_launched_is_a_gate_error(tmp_path: Path) -> None:
    process = _Process(ProcessError("no such file: pytest"))
    report, finding = _run_verify_command("pytest -q", process=process, worktree=tmp_path)
    assert finding is not None and finding.code == "MRS-GATE-002" and "could not be run" in finding.message
    assert report["resolvable"] is False


def test_a_failing_command_is_reported_with_its_exit(tmp_path: Path) -> None:
    process = _Process(ProcessResult(returncode=1, stdout="", stderr="1 failed"))
    _report, finding = _run_verify_command("pytest -q", process=process, worktree=tmp_path)
    assert finding is not None and finding.code == "MRS-GATE-001"
