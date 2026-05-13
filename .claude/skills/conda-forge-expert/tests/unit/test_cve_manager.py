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


class TestOsvVulnsBucketUrl:
    """OSV_VULNS_BUCKET_URL env override + per-ecosystem URL composition."""

    def test_default_is_public_bucket(self, load_module, monkeypatch):
        monkeypatch.delenv("OSV_VULNS_BUCKET_URL", raising=False)
        mod = load_module("cve_manager.py")
        assert mod._osv_vulns_bucket_base() == "https://osv-vulnerabilities.storage.googleapis.com"
        assert mod._osv_ecosystem_zip_url("PyPI") == (
            "https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip"
        )

    def test_env_var_redirect(self, load_module, monkeypatch):
        monkeypatch.setenv("OSV_VULNS_BUCKET_URL", "https://jfrog/api/generic/osv-mirror")
        mod = load_module("cve_manager.py")
        assert mod._osv_vulns_bucket_base() == "https://jfrog/api/generic/osv-mirror"
        assert mod._osv_ecosystem_zip_url("PyPI") == (
            "https://jfrog/api/generic/osv-mirror/PyPI/all.zip"
        )

    def test_trailing_slash_stripped(self, load_module, monkeypatch):
        monkeypatch.setenv("OSV_VULNS_BUCKET_URL", "https://jfrog/osv-mirror/")
        mod = load_module("cve_manager.py")
        assert mod._osv_vulns_bucket_base() == "https://jfrog/osv-mirror"

    def test_empty_env_falls_back_to_public(self, load_module, monkeypatch):
        # Empty string should fall through to the default, not produce a
        # broken URL like "/PyPI/all.zip".
        monkeypatch.setenv("OSV_VULNS_BUCKET_URL", "")
        mod = load_module("cve_manager.py")
        assert mod._osv_vulns_bucket_base() == "https://osv-vulnerabilities.storage.googleapis.com"
