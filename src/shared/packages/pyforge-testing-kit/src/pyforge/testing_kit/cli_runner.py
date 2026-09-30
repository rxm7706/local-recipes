"""CLI-runner mock family.

Seeded from Marshal's ``archive/.../tests/mocks/mock_runner.py`` (MockRunner) —
story / CLI execution with deterministic timing and verdicts. Not rewritten.

``invoke_cli`` / ``CliResult`` are the family's real-CLI invoker: run a station's
``main(argv)`` in-process and get back its exit code and everything it printed
(marshal Story 74.1; ``pyforge.testing_kit.flags`` builds its OFF-verb helper on it).
"""

from __future__ import annotations

import contextlib
import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any


class MockRunner:
    """Mock story / CLI runner for testing (seeded from Marshal MockRunner)."""

    def __init__(self, story_id: str, execution_time: float = 1.0):
        self.story_id = story_id
        self.execution_time = execution_time  # seconds
        self.executed = False
        self.result_verdict = "PASS"
        self.result_findings: list[dict[str, Any]] = []

    def run(self) -> bool:
        """Simulate story / CLI execution."""
        self.executed = True
        return True

    def get_result(self) -> dict[str, Any]:
        """Get execution result."""
        return {
            "story_id": self.story_id,
            "executed": self.executed,
            "verdict": self.result_verdict,
            "findings": self.result_findings,
            "execution_time": self.execution_time,
        }

    def set_verdict(self, verdict: str) -> None:
        """Set the verdict for this run."""
        valid_verdicts = {"PASS", "WARNING", "ERROR"}
        if verdict not in valid_verdicts:
            raise ValueError(f"Invalid verdict: {verdict}")
        self.result_verdict = verdict

    def add_finding(self, code: str, severity: str, message: str) -> None:
        """Add a finding to the result."""
        self.result_findings.append(
            {
                "code": code,
                "severity": severity,
                "message": message,
            }
        )

    def reset(self) -> None:
        """Reset the runner for reuse."""
        self.executed = False
        self.result_verdict = "PASS"
        self.result_findings = []


# Family-facing alias used by stations that want the CLI-runner name.
CliRunner = MockRunner


@dataclass(frozen=True)
class CliResult:
    """What a CLI did: its exit code and everything it printed (stdout, then stderr)."""

    exit_code: int
    output: str


def _exit_code(value: object, stderr: io.StringIO) -> int:
    """``sys.exit``'s own reading of a return value or ``SystemExit.code``.

    ``None`` is 0, an int is itself, anything else is a message printed to stderr with exit code 1.
    """
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    stderr.write(f"{value}\n")
    return 1


def invoke_cli(main: Callable[[list[str]], int | None], argv: Sequence[str]) -> CliResult:
    """Run ``main(list(argv))`` in-process, capturing stdout and stderr.

    The exit code is ``main``'s return value or, when it raises ``SystemExit`` (argparse's
    ``--help`` and usage errors do), that exit's code. Any other exception propagates.
    """
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = _exit_code(main(list(argv)), stderr)
        except SystemExit as raised:
            code = _exit_code(raised.code, stderr)
    return CliResult(exit_code=code, output=stdout.getvalue() + stderr.getvalue())
