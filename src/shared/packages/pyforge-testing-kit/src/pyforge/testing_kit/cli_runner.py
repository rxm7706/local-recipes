"""CLI-runner mock family.

Seeded from Marshal's ``archive/.../tests/mocks/mock_runner.py`` (MockRunner) —
story / CLI execution with deterministic timing and verdicts. Not rewritten.
"""

from __future__ import annotations

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
