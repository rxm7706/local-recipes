"""Unit tests for dependency-checker.py (hyphenated → script_runner only)."""
from __future__ import annotations

import pytest


@pytest.mark.network
class TestDependencyCheckerLive:
    """Live network test — verifies real conda-forge resolution still works."""

    def test_v1_noarch_deps_resolve(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "dependency-checker.py", str(recipes_dir / "v1-noarch"),
            timeout=120,
        )
        assert "All dependencies found" in out, f"out={out}\nerr={err}"


class TestDependencyChecker:
    def test_smoke_help(self, script_runner):
        rc, out, _ = script_runner("dependency-checker.py", "--help")
        assert rc == 0
        assert "usage" in out.lower()

    def test_runs_on_v1_noarch(self, script_runner, recipes_dir):
        """Just verify it doesn't crash; deps may or may not resolve based on
        cache state."""
        rc, out, err = script_runner(
            "dependency-checker.py", str(recipes_dir / "v1-noarch"),
            timeout=120,
        )
        # Even if it can't reach conda-forge, the script should produce
        # structured output without raising
        combined = out + err
        assert "Dependencies" in combined or "dependencies" in combined
