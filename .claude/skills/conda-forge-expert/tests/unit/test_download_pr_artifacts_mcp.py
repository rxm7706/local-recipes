"""Unit tests for the `download_pr_artifacts` MCP tool (v8.14.0).

The tool is a thin subprocess wrapper around `pr_artifacts.py --json`.
These tests stub the `_run_script` helper at the conda_forge_server
module boundary so the subprocess never actually runs — covers:
  * happy path: returns parsed manifest dict
  * non-zero exit: result dict carries `error` key, no exception raised
  * args wiring: extract=False, platforms, all_runs, force, build_id,
    check_name all propagate to the right CLI flags.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_cfs():
    """Load conda_forge_server.py with a stubbed fastmcp module so
    @mcp.tool decorators are no-ops.
    """
    if "cfs_under_test" in sys.modules:
        return sys.modules["cfs_under_test"]

    fake = types.ModuleType("fastmcp")

    class _FakeMCP:
        def tool(self, *_a, **_k):
            def deco(fn):
                return fn
            return deco

    fake.FastMCP = lambda *_a, **_k: _FakeMCP()  # type: ignore[attr-defined]
    fake.Context = object  # type: ignore[attr-defined]
    sys.modules["fastmcp"] = fake

    path = Path(__file__).resolve().parents[4] / "tools" / "conda_forge_server.py"
    spec = importlib.util.spec_from_file_location("cfs_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cfs_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cfs():
    return _load_cfs()


_HAPPY_MANIFEST = {
    "pr_ref": "33693",
    "repo": "conda-forge/staged-recipes",
    "runs": [
        {
            "build_id": 1536673,
            "azure_url": "https://dev.azure.com/conda-forge/feedstock-builds/_build/results?buildId=1536673",
            "result": "succeeded",
            "fetched_at": "2026-06-12T12:00:00Z",
            "artifacts": [
                {
                    "name": "conda_pkgs_linux",
                    "platform": "linux-64",
                    "size_bytes": 78641152,
                    "conda_files": ["linux-64/gh-copilot-cli-1.0.61-h00.conda"],
                    "extracted_to": "extracted/linux-64/",
                }
            ],
            "channel_url": "file:///abs/path/build_artifacts/pr/33693/1536673/extracted",
            "skipped_cached": False,
        }
    ],
    "output_dir": "/abs/path/build_artifacts/pr/33693",
    "channel_url": "file:///abs/path/build_artifacts/pr/33693/1536673/extracted",
    "skipped_cached": False,
    "errors": [],
}


class TestDownloadPrArtifactsMcp:
    def test_happy_path_returns_parsed_manifest(self, cfs, monkeypatch):
        captured: dict = {}

        def fake_run_script(script_path, args, timeout=120):
            captured["script_path"] = script_path
            captured["args"] = args
            captured["timeout"] = timeout
            return _HAPPY_MANIFEST

        monkeypatch.setattr(cfs, "_run_script", fake_run_script)
        out = cfs.download_pr_artifacts(pr_ref="33693")
        parsed = json.loads(out)
        assert parsed["pr_ref"] == "33693"
        assert parsed["runs"][0]["build_id"] == 1536673
        assert parsed["channel_url"].startswith("file://")
        # Default args wiring.
        assert "--json" in captured["args"]
        assert "33693" in captured["args"]
        assert "--repo" in captured["args"]
        assert "conda-forge/staged-recipes" in captured["args"]
        # 10 min timeout (multi-platform downloads can take minutes).
        assert captured["timeout"] == 600
        # Script path is the canonical pr_artifacts.py.
        assert str(captured["script_path"]).endswith("/scripts/pr_artifacts.py")

    def test_non_zero_exit_propagates_as_error_key(self, cfs, monkeypatch):
        # _run_script returns this shape on script errors (see line 100-105
        # of conda_forge_server.py).
        error_dict = {
            "error": "Failed to parse JSON output",
            "stdout": "",
            "stderr": "error: No Azure build found on PR 33693",
            "exit_code": 1,
        }
        monkeypatch.setattr(cfs, "_run_script", lambda *_a, **_kw: error_dict)
        out = cfs.download_pr_artifacts(pr_ref="33693")
        parsed = json.loads(out)
        assert parsed["error"] == "Failed to parse JSON output"
        assert parsed["exit_code"] == 1
        # No exception was raised — the tool handles errors gracefully.

    def test_extract_false_passes_no_extract_flag(self, cfs, monkeypatch):
        captured: dict = {}

        def fake_run_script(script_path, args, timeout=120):
            captured["args"] = args
            return _HAPPY_MANIFEST

        monkeypatch.setattr(cfs, "_run_script", fake_run_script)
        cfs.download_pr_artifacts(pr_ref="33693", extract=False)
        assert "--no-extract" in captured["args"]

    def test_pr_ref_passed_after_argparse_terminator(self, cfs, monkeypatch):
        """v8.14.0-post-review: MCP must place pr_ref AFTER a `--` separator
        so a malicious or buggy caller passing e.g. `--evil-flag` as pr_ref
        cannot have it reinterpreted by argparse as an unknown flag."""
        captured: dict = {}

        def fake_run_script(script_path, args, timeout=120):
            captured["args"] = args
            return _HAPPY_MANIFEST

        monkeypatch.setattr(cfs, "_run_script", fake_run_script)
        cfs.download_pr_artifacts(pr_ref="33693")
        a = captured["args"]
        # `--` must appear, and pr_ref must come after it.
        assert "--" in a
        dash_idx = a.index("--")
        assert dash_idx == len(a) - 2
        assert a[-1] == "33693"

    def test_optional_flags_propagate(self, cfs, monkeypatch):
        captured: dict = {}

        def fake_run_script(script_path, args, timeout=120):
            captured["args"] = args
            return _HAPPY_MANIFEST

        monkeypatch.setattr(cfs, "_run_script", fake_run_script)
        cfs.download_pr_artifacts(
            pr_ref="33693",
            build_id=1536673,
            output_dir="/tmp/out",
            platforms=["linux-64", "osx-64"],
            all_runs=True,
            force=True,
            check_name="staged-recipes",
        )
        a = captured["args"]
        assert "--build-id" in a and "1536673" in a
        assert "--output-dir" in a and "/tmp/out" in a
        assert "--platforms" in a and "linux-64,osx-64" in a
        assert "--all-runs" in a
        assert "--force" in a
        assert "--check-name" in a and "staged-recipes" in a
