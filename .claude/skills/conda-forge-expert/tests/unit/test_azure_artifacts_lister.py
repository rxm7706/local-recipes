"""Unit tests for `pr_artifacts.list_azure_artifacts`.

Mocks the Azure DevOps REST response shape captured from the PR #33693
session (`https://dev.azure.com/conda-forge/feedstock-builds/_apis/build/
builds/1536673/artifacts?api-version=7.1`).
"""
from __future__ import annotations

import importlib.util
import json
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


_AZURE_RESPONSE = {
    "count": 4,
    "value": [
        {
            "id": 1,
            "name": "conda_pkgs_linux",
            "resource": {
                "type": "Container",
                "downloadUrl": "https://dev.azure.com/conda-forge/.../conda_pkgs_linux/content?format=zip",
                "properties": {"artifactsize": "78641152"},
            },
        },
        {
            "id": 2,
            "name": "conda_pkgs_osx",
            "resource": {
                "type": "Container",
                "downloadUrl": "https://dev.azure.com/conda-forge/.../conda_pkgs_osx/content?format=zip",
                "properties": {"artifactsize": "82119424"},
            },
        },
        {
            "id": 3,
            "name": "conda_pkgs_win",
            "resource": {
                "type": "Container",
                "downloadUrl": "https://dev.azure.com/conda-forge/.../conda_pkgs_win/content?format=zip",
                "properties": {"artifactsize": "61542400"},
            },
        },
        {
            "id": 4,
            "name": "_build_artifacts.json",
            "resource": {
                "type": "Container",
                "downloadUrl": "https://dev.azure.com/.../json/content?format=zip",
                "properties": {"artifactsize": "412"},
            },
        },
    ],
}


def _mock_response(payload: dict, monkeypatch) -> None:
    """Patch `pr_artifacts.open_url` to return a context manager whose
    file-like body is `payload` encoded as JSON.
    """

    class _Resp:
        def __init__(self, body: bytes):
            self._body = body
            self.status = 200

        def read(self) -> bytes:
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> bool:
            return False

    body = json.dumps(payload).encode("utf-8")
    monkeypatch.setattr(pra, "open_url", lambda _req, timeout=60: _Resp(body))


class TestListAzureArtifacts:
    def test_filters_to_conda_pkgs_by_default(self, monkeypatch):
        _mock_response(_AZURE_RESPONSE, monkeypatch)
        artifacts = pra.list_azure_artifacts(1536673)
        names = [a["name"] for a in artifacts]
        assert names == ["conda_pkgs_linux", "conda_pkgs_osx", "conda_pkgs_win"]
        # platform map populated
        platforms = [a["platform"] for a in artifacts]
        assert platforms == ["linux-64", "osx-64", "win-64"]
        # download_url + size carried through
        assert artifacts[0]["download_url"].endswith("conda_pkgs_linux/content?format=zip")
        assert artifacts[0]["size"] == 78641152

    def test_include_all_returns_every_artifact(self, monkeypatch):
        _mock_response(_AZURE_RESPONSE, monkeypatch)
        artifacts = pra.list_azure_artifacts(1536673, include_all=True)
        names = [a["name"] for a in artifacts]
        assert names == [
            "conda_pkgs_linux",
            "conda_pkgs_osx",
            "conda_pkgs_win",
            "_build_artifacts.json",
        ]
        # Unknown-name artifact: platform falls back to None.
        assert artifacts[3]["platform"] is None

    def test_azure_error_envelope_raises_runtime_error(self, monkeypatch):
        """Azure DevOps anonymous endpoints sometimes return an error
        envelope with HTTP 200 (e.g., retention-purged builds). Surface
        the upstream message rather than silently reporting 'no artifacts'."""
        error_envelope = {
            "$id": "1",
            "innerException": None,
            "message": "Build with ID 99999999 not found.",
            "typeName": "...BuildNotFoundException",
        }
        _mock_response(error_envelope, monkeypatch)
        with pytest.raises(RuntimeError, match="Build with ID 99999999 not found"):
            pra.list_azure_artifacts(99999999)

    def test_uses_skip_auth_to_avoid_cred_leak(self, monkeypatch):
        """The lister MUST pass `skip_auth=True` so JFROG_API_KEY / GITHUB_TOKEN
        env vars don't leak cross-host to dev.azure.com.
        """
        captured: dict = {}

        def fake_make_request(url, extra_headers=None, user_agent=None, skip_auth=False):
            captured["url"] = url
            captured["skip_auth"] = skip_auth
            return object()  # opaque token for open_url

        _mock_response(_AZURE_RESPONSE, monkeypatch)
        monkeypatch.setattr(pra, "make_request", fake_make_request)
        pra.list_azure_artifacts(1536673)
        assert captured["skip_auth"] is True
        assert "dev.azure.com/conda-forge/feedstock-builds" in captured["url"]
        assert "api-version=7.1" in captured["url"]
