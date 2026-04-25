"""Unit tests for cve_manager.py.

The full update fetches a 19k-vuln zip from osv.dev (slow + network). We
test importable behavior in-process and skip the live update by default.
"""
from __future__ import annotations

import pytest


class TestCveManager:
    def test_importable(self, load_module):
        """The module must import without making network calls."""
        mod = load_module("cve_manager.py")
        assert mod is not None

    def test_help(self, script_runner):
        rc, out, _ = script_runner("cve_manager.py", "--help", timeout=30)
        assert rc == 0
        # Just confirm it printed an argparse usage line
        assert "usage" in out.lower()

    @pytest.mark.network
    @pytest.mark.slow
    def test_live_update(self, script_runner, tmp_path, monkeypatch):
        """Live: download and index the OSV PyPI database. ~30s."""
        # Redirect DATA_DIR via environment if the script supports it; if
        # not, this test will write to the real cache (~30 MB).
        rc, out, err = script_runner(
            "cve_manager.py", timeout=180,
        )
        # The real script returns 0 on success
        assert "complete" in out.lower() or "complete" in err.lower(), (out + err)
