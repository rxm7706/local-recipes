"""Unit tests for `pr_artifacts.download_artifact`.

The streaming download path delegates to `_http.fetch_to_file_resumable`;
the post-stream verification is `download_artifact`'s responsibility.
Since v8.14.1 verification is a CRC integrity check via
`zipfile.ZipFile(target).testzip()` rather than a strict size match —
Azure's `artifact["size"]` is the artifact's logical/content size, not
the on-demand ZIP-stream size, so the two routinely diverge on valid
downloads (PR #33693 buildId 1536673 surfaced this).
"""
from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
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


def _valid_zip_bytes(
    member: str = "conda-build_linux/linux-64/foo-1.0-h0.conda",
    data: bytes = b"hello world",
) -> bytes:
    """Build a minimal but real ZIP containing one member."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member, data)
    return buf.getvalue()


class TestDownloadArtifact:
    def test_valid_zip_returns_target_path(self, tmp_path, monkeypatch):
        body = _valid_zip_bytes()
        monkeypatch.setattr(pra, "fetch_to_file_resumable", _fake_fetch_factory(body))
        artifact = {
            "name": "conda_pkgs_linux",
            "download_url": "https://example.com/conda_pkgs_linux/content",
            "size": len(body),
            "platform": "linux-64",
            "raw": {},
        }
        out = pra.download_artifact(artifact, tmp_path)
        assert out == tmp_path / "conda_pkgs_linux.zip"
        assert out.read_bytes() == body

    def test_valid_zip_tolerates_stale_declared_size(self, tmp_path, monkeypatch):
        """Regression for PR #33693 buildId 1536673: Azure's `size` is the
        artifact's logical content size, not the ZIP-stream byte count,
        so a perfectly valid ZIP can ship with a mismatched declared size.
        The v8.14.0 strict-equality check rejected such downloads.
        """
        body = _valid_zip_bytes()
        monkeypatch.setattr(pra, "fetch_to_file_resumable", _fake_fetch_factory(body))
        artifact = {
            "name": "conda_pkgs_win",
            "download_url": "https://example.com/conda_pkgs_win/content",
            # Lie: Azure says 85_000_797, on-disk body is whatever len(body) is.
            "size": 85_000_797,
            "platform": "win-64",
            "raw": {},
        }
        out = pra.download_artifact(artifact, tmp_path)
        assert out.read_bytes() == body

    def test_non_zip_body_raises_and_preserves(self, tmp_path, monkeypatch):
        """Garbage (non-ZIP) bytes — `BadZipFile` on open."""
        monkeypatch.setattr(
            pra, "fetch_to_file_resumable", _fake_fetch_factory(b"not a zip at all")
        )
        artifact = {
            "name": "conda_pkgs_linux",
            "download_url": "https://example.com/conda_pkgs_linux/content",
            "size": 1024,
            "platform": "linux-64",
            "raw": {},
        }
        with pytest.raises(RuntimeError) as excinfo:
            pra.download_artifact(artifact, tmp_path)
        assert "Corrupt ZIP" in str(excinfo.value)
        # Bad .zip preserved for forensics.
        assert (tmp_path / "conda_pkgs_linux.zip").exists()

    def test_corrupt_member_raises_and_preserves(self, tmp_path, monkeypatch):
        """A ZIP that opens cleanly but whose member payload has been
        clobbered — `testzip()` returns the bad member name and we raise.
        """
        body = bytearray(_valid_zip_bytes(data=b"the quick brown fox"))
        # Flip a byte in the deflated payload (well inside the local
        # file header's data section, before the central directory).
        # Local file header is 30 bytes + len(filename); payload follows.
        # Filename length varies; index 60 is safely inside the deflate
        # stream for our test fixture.
        body[60] ^= 0xFF
        monkeypatch.setattr(
            pra, "fetch_to_file_resumable", _fake_fetch_factory(bytes(body))
        )
        artifact = {
            "name": "conda_pkgs_osx",
            "download_url": "https://example.com/conda_pkgs_osx/content",
            "size": len(body),
            "platform": "osx-64",
            "raw": {},
        }
        with pytest.raises(RuntimeError) as excinfo:
            pra.download_artifact(artifact, tmp_path)
        msg = str(excinfo.value)
        # Either testzip returned a bad member (CRC failure) or open
        # itself reported BadZipFile — both are accepted forensic paths.
        assert "CRC failure" in msg or "Corrupt ZIP" in msg
        assert (tmp_path / "conda_pkgs_osx.zip").exists()

    def test_missing_download_url_raises(self, tmp_path):
        artifact = {"name": "broken", "download_url": None, "size": 1, "platform": None, "raw": {}}
        with pytest.raises(ValueError, match="downloadUrl"):
            pra.download_artifact(artifact, tmp_path)

    def test_size_none_still_verifies_zip(self, tmp_path, monkeypatch):
        """When Azure didn't declare a size, we still verify ZIP
        integrity (the gate is no longer size-based, so size: None is
        no longer a verification bypass).
        """
        body = _valid_zip_bytes()
        monkeypatch.setattr(pra, "fetch_to_file_resumable", _fake_fetch_factory(body))
        artifact = {
            "name": "conda_pkgs_osx",
            "download_url": "https://example.com/conda_pkgs_osx/content",
            "size": None,
            "platform": "osx-64",
            "raw": {},
        }
        out = pra.download_artifact(artifact, tmp_path)
        assert out.read_bytes() == body
