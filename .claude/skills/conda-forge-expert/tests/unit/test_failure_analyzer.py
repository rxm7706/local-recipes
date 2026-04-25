"""Unit tests for failure_analyzer.py."""
from __future__ import annotations

import json


class TestFailureAnalyzer:
    def test_unmatched_log_returns_structured_no_match(
        self, script_runner, error_logs_dir
    ):
        rc, out, _ = script_runner(
            "failure_analyzer.py", str(error_logs_dir / "unmatched.log")
        )
        # Exit non-zero per docs ("1 = no match or error")
        result = json.loads(out)
        assert result["success"] is False
        assert "ERROR_LIBRARY contains" in result.get("hint", "") + result.get("error", "")

    def test_first_only_flag_runs(self, script_runner, error_logs_dir):
        """Smoke: --first-only should still produce JSON (no crash)."""
        rc, out, err = script_runner(
            "failure_analyzer.py", "--first-only",
            str(error_logs_dir / "unmatched.log"),
        )
        # Either matched (exit 0) or unmatched (exit 1) — either way, JSON
        try:
            json.loads(out)
        except json.JSONDecodeError:
            raise AssertionError(
                f"failure_analyzer didn't emit JSON. out={out}\nerr={err}"
            )

    def test_stdin_mode(self, script_runner):
        """The '-' logfile arg reads stdin."""
        rc, out, _ = script_runner(
            "failure_analyzer.py", "-",
            input_text="some unstructured text\n",
        )
        # Either match (rc=0) or no-match (rc=1); must produce JSON
        json.loads(out)
