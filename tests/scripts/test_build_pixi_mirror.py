"""Tests for `scripts/build-pixi-mirror.py` (Story 12.3,
spec-12-3-air-gap-parity-is-a-failing-check).

Only the two pieces of PURE logic the story's own Tasks & Acceptance names
are covered here: URL-to-mirror-path derivation (`parse_mirror_targets`)
and sha256 verification (`_sha256_of`/`_download_one`). No real network is
used -- `requests.get` is monkeypatched wherever a download is exercised,
matching the story's own "a small fixture lockfile, no real network needed
for the test itself" instruction. The CI job's own live mirror-then-block
proof is NOT exercised here (no sandboxed iptables/kind access -- see the
story spec's Verification section).
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build-pixi-mirror.py"


def _import_build_pixi_mirror():
    """Import the hyphenated `scripts/build-pixi-mirror.py` in-process --
    it is not a valid Python module name, so a plain `import` statement
    cannot reach it. Mirrors the same `spec_from_file_location` pattern
    `tests/scripts/test_deferred_work_promote.py` and
    `_bmad/skf/skf-campaign/scripts/campaign-validate-pins.py`'s own tests
    use for the identical reason."""
    spec = importlib.util.spec_from_file_location("build_pixi_mirror", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_pixi_mirror"] = mod
    spec.loader.exec_module(mod)
    return mod


bpm = _import_build_pixi_mirror()


# A minimal, synthetic pixi.lock (schema v7) fixture: two environments'
# worth of shape aren't needed, just one ("fixture-env") with a linux-64
# package list referencing both a conda-forge and a SelfExplainML URL --
# the exact two-channel shape `pixi.toml`'s real `python-agent-platform`
# feature comment documents (slowapi from SelfExplainML alongside
# conda-forge packages).
GOOD_SHA = "a" * 64
_FIXTURE_LOCKFILE = {
    "environments": {
        "fixture-env": {
            "packages": {
                "linux-64": [
                    {"conda": "https://conda.anaconda.org/conda-forge/linux-64/foo-1.0-0.conda"},
                    {"conda": "https://conda.anaconda.org/SelfExplainML/noarch/bar-2.0-pyh_0.conda"},
                ]
            }
        }
    },
    "packages": [
        {
            "conda": "https://conda.anaconda.org/conda-forge/linux-64/foo-1.0-0.conda",
            "sha256": GOOD_SHA,
        },
        {
            "conda": "https://conda.anaconda.org/SelfExplainML/noarch/bar-2.0-pyh_0.conda",
            "sha256": "b" * 64,
        },
    ],
}


def _fixture_lockfile() -> dict:
    # Deep-enough copy for these tests: callers only ever read this, never
    # mutate the nested dicts/lists in place.
    import copy

    return copy.deepcopy(_FIXTURE_LOCKFILE)


class TestParseMirrorTargets:
    def test_derives_channel_subdir_filename_and_sha256_for_conda_forge(self):
        targets = bpm.parse_mirror_targets(_fixture_lockfile(), "fixture-env", "linux-64")
        foo = next(t for t in targets if t.filename == "foo-1.0-0.conda")

        assert foo.channel == "conda-forge"
        assert foo.subdir == "linux-64"
        assert foo.sha256 == GOOD_SHA
        assert foo.dest_relpath == Path("conda-forge/linux-64/foo-1.0-0.conda")

    def test_derives_channel_for_a_noarch_selfexplainml_package(self):
        targets = bpm.parse_mirror_targets(_fixture_lockfile(), "fixture-env", "linux-64")
        bar = next(t for t in targets if t.filename == "bar-2.0-pyh_0.conda")

        assert bar.channel == "SelfExplainML"
        assert bar.subdir == "noarch"
        assert bar.dest_relpath == Path("SelfExplainML/noarch/bar-2.0-pyh_0.conda")

    def test_returns_exactly_one_target_per_environment_package(self):
        targets = bpm.parse_mirror_targets(_fixture_lockfile(), "fixture-env", "linux-64")
        assert len(targets) == 2

    def test_unknown_environment_raises_mirror_build_error(self):
        with pytest.raises(bpm.MirrorBuildError, match="no resolvable entries"):
            bpm.parse_mirror_targets(_fixture_lockfile(), "does-not-exist", "linux-64")

    def test_unknown_platform_raises_mirror_build_error(self):
        with pytest.raises(bpm.MirrorBuildError, match="no resolvable entries"):
            bpm.parse_mirror_targets(_fixture_lockfile(), "fixture-env", "win-64")

    def test_empty_platform_package_list_raises_mirror_build_error(self):
        lockfile = _fixture_lockfile()
        lockfile["environments"]["fixture-env"]["packages"]["linux-64"] = []
        with pytest.raises(bpm.MirrorBuildError, match="empty"):
            bpm.parse_mirror_targets(lockfile, "fixture-env", "linux-64")

    def test_url_missing_from_top_level_catalog_raises_mirror_build_error(self):
        lockfile = _fixture_lockfile()
        lockfile["packages"] = [
            p for p in lockfile["packages"] if "foo-1.0-0" not in p["conda"]
        ]
        with pytest.raises(bpm.MirrorBuildError, match="missing from pixi.lock"):
            bpm.parse_mirror_targets(lockfile, "fixture-env", "linux-64")

    def test_catalog_entry_missing_sha256_raises_mirror_build_error(self):
        lockfile = _fixture_lockfile()
        lockfile["packages"][0].pop("sha256")
        with pytest.raises(bpm.MirrorBuildError, match="no sha256"):
            bpm.parse_mirror_targets(lockfile, "fixture-env", "linux-64")

    def test_malformed_url_raises_mirror_build_error(self):
        lockfile = _fixture_lockfile()
        lockfile["environments"]["fixture-env"]["packages"]["linux-64"] = [
            {"conda": "https://conda.anaconda.org/too-short.conda"}
        ]
        lockfile["packages"].append(
            {"conda": "https://conda.anaconda.org/too-short.conda", "sha256": GOOD_SHA}
        )
        with pytest.raises(bpm.MirrorBuildError, match="does not look like a conda package URL"):
            bpm.parse_mirror_targets(lockfile, "fixture-env", "linux-64")


def _make_target(url: str = "https://conda.anaconda.org/conda-forge/linux-64/foo-1.0-0.conda"):
    content = b"pretend-conda-package-bytes"
    sha256 = hashlib.sha256(content).hexdigest()
    target = bpm.MirrorTarget(
        url=url, sha256=sha256, channel="conda-forge", subdir="linux-64", filename="foo-1.0-0.conda"
    )
    return target, content


class TestDownloadAndVerify:
    def test_already_valid_file_is_skipped_without_a_network_call(self, tmp_path, monkeypatch):
        target, content = _make_target()
        dest_path = tmp_path / target.dest_relpath
        dest_path.parent.mkdir(parents=True)
        dest_path.write_bytes(content)

        def _fail_if_called(*args, **kwargs):
            raise AssertionError("requests.get must not be called for an already-valid file")

        monkeypatch.setattr(bpm.requests, "get", _fail_if_called)

        result = bpm._download_one(target, tmp_path, timeout=5)

        assert result == "skipped"
        assert dest_path.read_bytes() == content

    def test_stale_or_corrupt_existing_file_is_redownloaded(self, tmp_path, monkeypatch):
        target, content = _make_target()
        dest_path = tmp_path / target.dest_relpath
        dest_path.parent.mkdir(parents=True)
        dest_path.write_bytes(b"stale-wrong-bytes")

        monkeypatch.setattr(bpm.requests, "get", lambda *a, **k: _FakeResponse(content))

        result = bpm._download_one(target, tmp_path, timeout=5)

        assert result == "downloaded"
        assert dest_path.read_bytes() == content

    def test_successful_download_is_verified_and_written_to_the_derived_path(
        self, tmp_path, monkeypatch
    ):
        target, content = _make_target()
        monkeypatch.setattr(bpm.requests, "get", lambda *a, **k: _FakeResponse(content))

        result = bpm._download_one(target, tmp_path, timeout=5)

        dest_path = tmp_path / target.dest_relpath
        assert result == "downloaded"
        assert dest_path.exists()
        assert not dest_path.with_name(dest_path.name + ".part").exists()
        assert hashlib.sha256(dest_path.read_bytes()).hexdigest() == target.sha256

    def test_sha256_mismatch_raises_and_leaves_no_partial_file(self, tmp_path, monkeypatch):
        target, _content = _make_target()
        monkeypatch.setattr(bpm.requests, "get", lambda *a, **k: _FakeResponse(b"wrong-bytes"))

        with pytest.raises(bpm.MirrorBuildError, match="sha256 mismatch"):
            bpm._download_one(target, tmp_path, timeout=5)

        dest_path = tmp_path / target.dest_relpath
        assert not dest_path.exists()
        assert not dest_path.with_name(dest_path.name + ".part").exists()

    def test_request_exception_raises_mirror_build_error(self, tmp_path, monkeypatch):
        target, _content = _make_target()

        def _raise(*args, **kwargs):
            raise bpm.requests.RequestException("connection refused")

        monkeypatch.setattr(bpm.requests, "get", _raise)

        with pytest.raises(bpm.MirrorBuildError, match="download failed"):
            bpm._download_one(target, tmp_path, timeout=5)


class _FakeResponse:
    """Minimal stand-in for `requests.Response` under `stream=True` --
    supports the context-manager + `iter_content` surface `_download_one`
    actually uses, nothing more."""

    def __init__(self, content: bytes):
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size: int):
        yield self._content
