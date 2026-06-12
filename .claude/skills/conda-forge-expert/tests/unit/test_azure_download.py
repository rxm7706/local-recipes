"""Unit tests for `pr_artifacts.download_artifact`.

The streaming download path delegates to `_http.fetch_to_file_resumable`;
the post-stream Content-Length verification is `download_artifact`'s
responsibility. This file covers the verification gate — short-body
exceptions and successful happy paths — by monkeypatching the resumable
fetcher rather than spinning a real HTTP server.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PR_ARTIFACTS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "pr_artifacts.py"
)
spec = importlib.util.spec_from_file_location("pr_artifacts", _PR_ARTIFACTS_PATH)
assert spec is not None and spec.loader is not None
pra = importlib.util.module_from_spec(spec)
sys.modules["pr_artifacts"] = pra
spec.loader.exec_module(pra)


def _fake_fetch_factory(body: bytes):
    """Return a callable matching `fetch_to_file_resumable`'s signature
    that writes `body` to the target path and returns the path.
    """

    def _fake(target, urls, **kwargs):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        return target

    return _fake


class TestDownloadArtifact:
    def test_size_match_returns_target_path(self, tmp_path, monkeypatch):
        body = b"x" * 1024
        monkeypatch.setattr(pra, "fetch_to_file_resumable", _fake_fetch_factory(body))
        artifact = {
            "name": "conda_pkgs_linux",
            "download_url": "https://example.com/conda_pkgs_linux/content",
            "size": 1024,
            "platform": "linux-64",
            "raw": {},
        }
        out = pra.download_artifact(artifact, tmp_path)
        assert out == tmp_path / "conda_pkgs_linux.zip"
        assert out.read_bytes() == body

    def test_size_mismatch_raises_and_preserves_zip(self, tmp_path, monkeypatch):
        body = b"x" * 500
        monkeypatch.setattr(pra, "fetch_to_file_resumable", _fake_fetch_factory(body))
        artifact = {
            "name": "conda_pkgs_linux",
            "download_url": "https://example.com/conda_pkgs_linux/content",
            "size": 1024,  # lie: server says 1024 but body is 500
            "platform": "linux-64",
            "raw": {},
        }
        with pytest.raises(RuntimeError) as excinfo:
            pra.download_artifact(artifact, tmp_path)
        assert "Size mismatch" in str(excinfo.value)
        # Bad .zip preserved for forensics.
        assert (tmp_path / "conda_pkgs_linux.zip").exists()

    def test_missing_download_url_raises(self, tmp_path):
        artifact = {"name": "broken", "download_url": None, "size": 1, "platform": None, "raw": {}}
        with pytest.raises(ValueError, match="downloadUrl"):
            pra.download_artifact(artifact, tmp_path)

    def test_size_none_skips_verification(self, tmp_path, monkeypatch):
        """When Azure didn't declare a size, we still succeed (best-effort)."""
        monkeypatch.setattr(pra, "fetch_to_file_resumable", _fake_fetch_factory(b"abc"))
        artifact = {
            "name": "conda_pkgs_osx",
            "download_url": "https://example.com/conda_pkgs_osx/content",
            "size": None,
            "platform": "osx-64",
            "raw": {},
        }
        out = pra.download_artifact(artifact, tmp_path)
        assert out.read_bytes() == b"abc"
