"""Unit tests for `pr_artifacts.py` CLI front-end + extract + cache.

Mocks the network boundary (`list_azure_artifacts` + `download_artifact`)
so tests stay offline. Covers:
  * `--help` exit 0
  * extract layout (Azure ZIP → `extracted/<platform>/*.conda`)
  * `--keep-zips` default OFF
  * cache: second run with manifest skips network
  * `--force` overrides cache
  * `--json` mode emits parseable manifest summary
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
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


def _make_fixture_zip(zip_path: Path, platform: str, conda_name: str) -> None:
    """Build a fixture ZIP that mirrors the Azure `conda_pkgs_<job>.zip` layout:
    `conda-build_<job>/<platform>/<conda_name>` + a sibling repodata.json.
    """
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w") as zf:
        wrapper = f"conda-build_{platform.replace('-', '_')}"
        zf.writestr(f"{wrapper}/{platform}/{conda_name}", b"fake conda bytes")
        zf.writestr(f"{wrapper}/{platform}/repodata.json", b'{"packages": {}}')


def _stub_network(monkeypatch, tmp_path: Path, build_id: int, platform: str = "linux-64") -> dict:
    """Patch list/download so `fetch_one_build` succeeds without network.
    Tracks call counts via a dict so cache tests can assert no-network on re-run.
    """
    state = {"list_calls": 0, "download_calls": 0}

    artifact_name = "conda_pkgs_linux" if platform == "linux-64" else f"conda_pkgs_{platform.split('-')[0]}"

    def fake_list(bid, include_all=False):
        state["list_calls"] += 1
        return [
            {
                "name": artifact_name,
                "download_url": "https://example.com/fake.zip",
                "size": None,  # skip size verification in fixtures
                "platform": platform,
                "raw": {},
            }
        ]

    def fake_download(artifact, target_dir, **kwargs):
        state["download_calls"] += 1
        zip_target = Path(target_dir) / f"{artifact['name']}.zip"
        _make_fixture_zip(zip_target, platform=platform, conda_name="foo-1.0.0-h00.conda")
        return zip_target

    monkeypatch.setattr(pra, "list_azure_artifacts", fake_list)
    monkeypatch.setattr(pra, "download_artifact", fake_download)
    return state


class TestCli:
    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(_PR_ARTIFACTS_PATH), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Usage" in result.stdout or "usage" in result.stdout

    def test_extract_layout(self, tmp_path, monkeypatch, capsys):
        _stub_network(monkeypatch, tmp_path, build_id=1536673)
        # Stub the gh-CLI boundary.
        monkeypatch.setattr(pra, "resolve_build_ids", lambda pr, **kw: [1536673])
        rc = pra.main([
            "33693",
            "--output-dir", str(tmp_path / "out"),
            "--json",
        ])
        assert rc == 0
        extracted = tmp_path / "out" / "1536673" / "extracted"
        assert (extracted / "linux-64" / "foo-1.0.0-h00.conda").exists()
        assert (extracted / "linux-64" / "repodata.json").exists()

    def test_keep_zips_default_off(self, tmp_path, monkeypatch):
        _stub_network(monkeypatch, tmp_path, build_id=42)
        monkeypatch.setattr(pra, "resolve_build_ids", lambda pr, **kw: [42])
        pra.main(["33693", "--output-dir", str(tmp_path / "out"), "--json"])
        zips = list((tmp_path / "out" / "42").glob("*.zip"))
        assert zips == [], "zips should be removed by default after extract"

    def test_keep_zips_flag_preserves(self, tmp_path, monkeypatch):
        _stub_network(monkeypatch, tmp_path, build_id=42)
        monkeypatch.setattr(pra, "resolve_build_ids", lambda pr, **kw: [42])
        pra.main(["33693", "--output-dir", str(tmp_path / "out"), "--keep-zips", "--json"])
        zips = list((tmp_path / "out" / "42").glob("*.zip"))
        assert len(zips) == 1

    def test_cached_buildid_skips_on_second_run(self, tmp_path, monkeypatch, capsys):
        state = _stub_network(monkeypatch, tmp_path, build_id=999)
        monkeypatch.setattr(pra, "resolve_build_ids", lambda pr, **kw: [999])
        # First run: populates manifest.
        pra.main(["33693", "--output-dir", str(tmp_path / "out"), "--json"])
        capsys.readouterr()  # discard first-run stdout
        assert state["download_calls"] == 1
        assert state["list_calls"] == 1
        # Second run: must skip network — neither list nor download fires.
        pra.main(["33693", "--output-dir", str(tmp_path / "out"), "--json"])
        captured = capsys.readouterr()
        summary = json.loads(captured.out)
        assert state["download_calls"] == 1, "no new download calls on cached run"
        assert state["list_calls"] == 1, "no new list_azure_artifacts calls on cached run"
        assert summary["skipped_cached"] is True
        assert summary["runs"][0]["skipped_cached"] is True

    def test_force_overrides_cache(self, tmp_path, monkeypatch):
        state = _stub_network(monkeypatch, tmp_path, build_id=999)
        monkeypatch.setattr(pra, "resolve_build_ids", lambda pr, **kw: [999])
        pra.main(["33693", "--output-dir", str(tmp_path / "out"), "--json"])
        assert state["download_calls"] == 1
        pra.main(["33693", "--output-dir", str(tmp_path / "out"), "--force", "--json"])
        assert state["download_calls"] == 2, "--force should re-fetch"

    def test_json_mode_emits_parseable_manifest(self, tmp_path, monkeypatch, capsys):
        _stub_network(monkeypatch, tmp_path, build_id=100)
        monkeypatch.setattr(pra, "resolve_build_ids", lambda pr, **kw: [100])
        rc = pra.main(["33693", "--output-dir", str(tmp_path / "out"), "--json"])
        assert rc == 0
        captured = capsys.readouterr()
        summary = json.loads(captured.out)
        assert summary["pr_ref"] == "33693"
        assert summary["repo"] == "conda-forge/staged-recipes"
        assert summary["runs"][0]["build_id"] == 100
        assert summary["runs"][0]["channel_url"].startswith("file://")
        assert summary["runs"][0]["channel_url"].endswith("/100/extracted")

    def test_no_azure_check_returns_rc1(self, tmp_path, monkeypatch, capsys):
        def raise_lookup(pr, **kw):
            raise LookupError(f"No Azure build found on PR {pr} (...); CI may still be pending.")

        monkeypatch.setattr(pra, "resolve_build_ids", raise_lookup)
        rc = pra.main(["33693", "--output-dir", str(tmp_path / "out"), "--json"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "No Azure build found" in err

    def test_build_id_zero_or_negative_errors_out(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as excinfo:
            pra.main(["33693", "--build-id", "0", "--output-dir", str(tmp_path / "out")])
        # argparse parser.error exits with code 2.
        assert excinfo.value.code == 2
        err = capsys.readouterr().err
        assert "positive integer" in err

    def test_platforms_whitespace_only_errors_out(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(pra, "resolve_build_ids", lambda pr, **kw: [42])
        with pytest.raises(SystemExit) as excinfo:
            pra.main([
                "33693",
                "--output-dir", str(tmp_path / "out"),
                "--platforms", "  ,, ,",
                "--json",
            ])
        assert excinfo.value.code == 2
        err = capsys.readouterr().err
        assert "empty list" in err

    def test_corrupt_zip_returns_exit_2(self, tmp_path, monkeypatch, capsys):
        """Spec § I/O Matrix: corrupt ZIP / extract failure → exit 2."""
        import zipfile

        def fake_list(bid, include_all=False):
            return [{
                "name": "conda_pkgs_linux",
                "download_url": "https://example.com/corrupt.zip",
                "size": None,
                "platform": "linux-64",
                "raw": {},
            }]

        def fake_download(artifact, target_dir, **kw):
            # Write a non-ZIP body so extract_zip raises BadZipFile.
            zip_target = Path(target_dir) / f"{artifact['name']}.zip"
            zip_target.parent.mkdir(parents=True, exist_ok=True)
            zip_target.write_bytes(b"not actually a zip file")
            return zip_target

        monkeypatch.setattr(pra, "list_azure_artifacts", fake_list)
        monkeypatch.setattr(pra, "download_artifact", fake_download)
        monkeypatch.setattr(pra, "resolve_build_ids", lambda pr, **kw: [1234])
        rc = pra.main(["33693", "--output-dir", str(tmp_path / "out"), "--json"])
        assert rc == 2
        # Bad ZIP preserved for forensics.
        assert (tmp_path / "out" / "1234" / "conda_pkgs_linux.zip").exists()
        # Manifest NOT written on extract failure.
        assert not (tmp_path / "out" / "1234" / "pr-artifacts.json").exists()

    def test_platforms_filter_drops_unwanted_subdir(self, tmp_path, monkeypatch):
        # Two-artifact stub: linux + osx. Filter to linux only.
        state = {"calls": 0}
        artifacts = [
            {
                "name": "conda_pkgs_linux",
                "download_url": "https://example.com/linux.zip",
                "size": None,
                "platform": "linux-64",
                "raw": {},
            },
            {
                "name": "conda_pkgs_osx",
                "download_url": "https://example.com/osx.zip",
                "size": None,
                "platform": "osx-64",
                "raw": {},
            },
        ]

        def fake_download(artifact, target_dir, **kw):
            zip_target = Path(target_dir) / f"{artifact['name']}.zip"
            _make_fixture_zip(zip_target, platform=artifact["platform"], conda_name="bar-2.0.0-h00.conda")
            return zip_target

        monkeypatch.setattr(pra, "list_azure_artifacts", lambda bid, include_all=False: artifacts)
        monkeypatch.setattr(pra, "download_artifact", fake_download)
        monkeypatch.setattr(pra, "resolve_build_ids", lambda pr, **kw: [55])
        pra.main([
            "33693",
            "--output-dir", str(tmp_path / "out"),
            "--platforms", "linux-64",
            "--json",
        ])
        extracted = tmp_path / "out" / "55" / "extracted"
        assert (extracted / "linux-64" / "bar-2.0.0-h00.conda").exists()
        assert not (extracted / "osx-64").exists(), "osx-64 should be filtered out"


class TestExtractZipSafety:
    """Zip Slip + path-traversal guards. Azure ZIPs originate from
    arbitrary PR builds and must be treated as untrusted."""

    def _build_zip(self, zip_path: Path, members: list[tuple[str, bytes]]) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w") as zf:
            for name, body in members:
                zf.writestr(name, body)

    def test_absolute_path_rejected(self, tmp_path):
        zp = tmp_path / "evil.zip"
        # First segment is the conda-build_<job>/ wrapper that extract_zip
        # strips; after stripping the member is `/etc/passwd` (absolute).
        self._build_zip(zp, [("wrapper//etc/passwd", b"pwned")])
        with pytest.raises(ValueError, match="unsafe path"):
            pra.extract_zip(zp, tmp_path / "out")
        assert not (tmp_path / "etc" / "passwd").exists()

    def test_dot_dot_traversal_rejected(self, tmp_path):
        zp = tmp_path / "evil.zip"
        # After stripping the wrapper, the rel becomes `../../etc/foo` which
        # would escape the destination root.
        self._build_zip(zp, [("wrapper/../../etc/foo", b"pwned")])
        with pytest.raises(ValueError, match="unsafe path|outside destination"):
            pra.extract_zip(zp, tmp_path / "out")

    def test_clean_zip_extracts_normally(self, tmp_path):
        zp = tmp_path / "good.zip"
        self._build_zip(zp, [
            ("conda-build_linux/linux-64/foo-1.0.0-h00.conda", b"bytes"),
            ("conda-build_linux/linux-64/repodata.json", b"{}"),
        ])
        out = tmp_path / "out"
        written = pra.extract_zip(zp, out)
        assert (out / "linux-64" / "foo-1.0.0-h00.conda").exists()
        assert (out / "linux-64" / "repodata.json").exists()
        assert written == ["linux-64/foo-1.0.0-h00.conda"]


class TestCheckNameMatching:
    """Case-insensitive matching + substring fallback removal."""

    def test_staged_recipes_case_insensitive(self):
        assert pra._check_name_matches("Staged-Recipes", "conda-forge/staged-recipes", None)
        assert pra._check_name_matches("staged-recipes", "conda-forge/staged-recipes", None)

    def test_feedstock_case_insensitive(self):
        assert pra._check_name_matches("NumPy-Feedstock", "conda-forge/numpy-feedstock", None)

    def test_override_case_insensitive(self):
        assert pra._check_name_matches("Custom-Build", "owner/repo", "custom-build")

    def test_unknown_repo_returns_false_no_substring_fallback(self):
        """v8.14.0-post-review patch: unknown-shape repos no longer match
        via permissive substring. Caller must pass --check-name."""
        assert not pra._check_name_matches("foo-bar-build", "owner/bar", None)


class TestManifestAtomicWrite:
    def test_atomic_replace_used(self, tmp_path, monkeypatch):
        """write_manifest_atomic must write via .tmp + os.replace, not
        a direct write_text — verifies the .tmp file is gone post-write."""
        manifest = {"build_id": 1, "azure_url": "x", "artifacts": []}
        pra._write_manifest_atomic(tmp_path, manifest)
        assert (tmp_path / "pr-artifacts.json").exists()
        assert not (tmp_path / "pr-artifacts.json.tmp").exists()

    def test_cached_manifest_missing_required_keys_returns_none(self, tmp_path):
        """A corrupted/truncated manifest (missing build_id / artifacts) is
        treated as cache-miss, forcing a clean re-fetch."""
        (tmp_path / "pr-artifacts.json").write_text('{"corrupt": true}')
        assert pra._read_cached_manifest(tmp_path) is None

    def test_cached_manifest_invalid_json_returns_none(self, tmp_path):
        (tmp_path / "pr-artifacts.json").write_text("not json at all {")
        assert pra._read_cached_manifest(tmp_path) is None

    def test_cached_manifest_well_formed_returns_dict(self, tmp_path):
        (tmp_path / "pr-artifacts.json").write_text(
            '{"build_id": 1, "azure_url": "x", "artifacts": []}'
        )
        got = pra._read_cached_manifest(tmp_path)
        assert got == {"build_id": 1, "azure_url": "x", "artifacts": []}
