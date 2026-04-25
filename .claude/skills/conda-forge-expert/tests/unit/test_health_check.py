"""Unit tests for health_check.py."""
from __future__ import annotations


class TestHealthCheck:
    def test_runs_without_traceback(self, script_runner):
        """Health check is informational; we don't assert PASS/FAIL since the
        result depends on the live env (Docker, OSV API)."""
        rc, out, err = script_runner("health_check.py", timeout=120)
        assert "Traceback" not in (out + err), (out + err)
        assert "Running Development Environment Health Check" in out

    def test_reports_overall_status(self, script_runner):
        rc, out, _ = script_runner("health_check.py", timeout=120)
        assert "Overall Status:" in out
