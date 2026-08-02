"""
Mock story runner for unit tests.

Simulates story execution with deterministic timing and verdicts.
"""

from typing import Optional, Dict, Any, List


class MockRunner:
    """Mock story runner for testing."""

    def __init__(self, story_id: str, execution_time: float = 1.0):
        self.story_id = story_id
        self.execution_time = execution_time  # seconds
        self.executed = False
        self.result_verdict = "PASS"
        self.result_findings: List[Dict[str, Any]] = []

    def run(self) -> bool:
        """Simulate story execution."""
        self.executed = True
        return True

    def get_result(self) -> Dict[str, Any]:
        """Get execution result."""
        return {
            "story_id": self.story_id,
            "executed": self.executed,
            "verdict": self.result_verdict,
            "findings": self.result_findings,
            "execution_time": self.execution_time,
        }

    def set_verdict(self, verdict: str):
        """Set the verdict for this run."""
        valid_verdicts = {"PASS", "WARNING", "ERROR"}
        if verdict not in valid_verdicts:
            raise ValueError(f"Invalid verdict: {verdict}")
        self.result_verdict = verdict

    def add_finding(self, code: str, severity: str, message: str):
        """Add a finding to the result."""
        self.result_findings.append({
            "code": code,
            "severity": severity,
            "message": message,
        })

    def reset(self):
        """Reset the runner for reuse."""
        self.executed = False
        self.result_verdict = "PASS"
        self.result_findings = []
