"""Story 3.2 -- `engines/pep517.py`'s adapter: presence via `require_engine`
(mocked directly on this module's own namespace, since `from . import
require_engine` binds that name INTO `pep517.py`'s own globals -- the same
"mock on the calling module's own namespace" convention `test_engines.py`
established for `shutil.which`/`subprocess.run`, extended here to a
higher-level imported function), and the `build()` operation itself via a
mocked `subprocess.run` plus real `tmp_path` fixture files standing in for
the artifacts `pyproject-build` would have produced -- this module
discovers artifacts from the filesystem, never from parsed subprocess
stdout (see `pep517.py`'s own module docstring), so no real `pyproject-
build` binary is needed for this file's coverage (AD-16)."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import patch

import pytest

from pyforge.mason.engines import pep517
from pyforge.mason.errors import EngineAbsentError, PackageBuildTimeoutError, PackageProjectPathError


def _fake_completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


# --- probe() -----------------------------------------------------------------


def test_probe_delegates_to_probe_engine_with_the_pyproject_build_binary_name():
    with patch("pyforge.mason.engines.pep517.probe_engine") as mock_probe:
        mock_probe.return_value.version = "build 1.5.0"
        version = pep517.probe()

    mock_probe.assert_called_once_with("build", "pyproject-build")
    assert version == "build 1.5.0"


# --- build(): engine presence gate --------------------------------------------


def test_build_raises_engine_absent_before_any_subprocess_spawns():
    with (
        patch(
            "pyforge.mason.engines.pep517.require_engine",
            side_effect=EngineAbsentError("build", "python-build"),
        ) as mock_require,
        patch("pyforge.mason.engines.pep517.subprocess.run") as mock_run,
    ):
        with pytest.raises(EngineAbsentError):
            pep517.build("/some/project")

    mock_require.assert_called_once_with("build")
    mock_run.assert_not_called()


# --- build(): invocation shape -------------------------------------------------


def test_build_invokes_pyproject_build_with_the_documented_argv_and_cwd(tmp_path):
    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch(
            "pyforge.mason.engines.pep517.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        pep517.build(str(tmp_path))

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv == ["pyproject-build", "--no-isolation", "--outdir", f"{tmp_path}/dist"]
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] is None
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert "timeout" in kwargs


def test_build_uses_the_default_timeout_when_none_given(tmp_path):
    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch(
            "pyforge.mason.engines.pep517.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        pep517.build(str(tmp_path))

    assert mock_run.call_args.kwargs["timeout"] == pep517._PEP517_BUILD_TIMEOUT_SECONDS


def test_build_forwards_an_explicit_timeout(tmp_path):
    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch(
            "pyforge.mason.engines.pep517.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        pep517.build(str(tmp_path), timeout=45.0)

    assert mock_run.call_args.kwargs["timeout"] == 45.0


# --- build(): subprocess boundary translation (review pass, 2026-08-13) -------


def test_build_translates_timeout_expired_to_package_build_timeout_error(tmp_path):
    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch(
            "pyforge.mason.engines.pep517.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["pyproject-build"], timeout=600.0),
        ),
    ):
        with pytest.raises(PackageBuildTimeoutError) as excinfo:
            pep517.build(str(tmp_path))

    assert excinfo.value.engine == "build"
    assert excinfo.value.timeout == pep517._PEP517_BUILD_TIMEOUT_SECONDS


def test_build_translates_oserror_from_a_bad_cwd_to_package_project_path_error(tmp_path):
    """`subprocess.run(cwd=project_path)` raises `FileNotFoundError`/
    `NotADirectoryError` (both `OSError` subclasses) BEFORE the wrapped
    tool ever starts when `project_path` does not exist as a directory --
    not the "tool reports its own failure via returncode" case."""
    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch(
            "pyforge.mason.engines.pep517.subprocess.run",
            side_effect=FileNotFoundError("No such file or directory"),
        ),
    ):
        with pytest.raises(PackageProjectPathError) as excinfo:
            pep517.build(str(tmp_path))

    assert excinfo.value.project_path == str(tmp_path)


# --- build(): I/O & Edge-Case Matrix -------------------------------------------


def test_build_happy_path_discovers_and_parses_wheel_and_sdist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "pyforge_mason-0.1.0-py3-none-any.whl").write_bytes(b"")
    (dist / "pyforge_mason-0.1.0.tar.gz").write_bytes(b"")

    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch(
            "pyforge.mason.engines.pep517.subprocess.run",
            return_value=_fake_completed(stdout="Successfully built pyforge_mason\n"),
        ),
    ):
        result = pep517.build(str(tmp_path))

    assert result.returncode == 0
    assert result.wheel_path == str(dist / "pyforge_mason-0.1.0-py3-none-any.whl")
    assert result.sdist_path == str(dist / "pyforge_mason-0.1.0.tar.gz")
    assert result.wheel_version == "0.1.0"
    assert result.stdout == "Successfully built pyforge_mason\n"


def test_build_failed_child_reports_no_artifacts_even_if_dist_has_stale_files(tmp_path):
    """spec I/O matrix: 'One engine's build fails' -> that artifact path
    `None` -- a non-zero returncode must skip discovery entirely, not
    report a stale artifact left over from an earlier successful build."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "stale-9.9.9-py3-none-any.whl").write_bytes(b"")

    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch(
            "pyforge.mason.engines.pep517.subprocess.run",
            return_value=_fake_completed(returncode=1, stdout="error: build backend failed\n"),
        ),
    ):
        result = pep517.build(str(tmp_path))

    assert result.returncode == 1
    assert result.wheel_path is None
    assert result.sdist_path is None
    assert result.wheel_version is None
    assert result.stdout == "error: build backend failed\n"


def test_build_missing_dist_dir_reports_no_artifacts(tmp_path):
    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch("pyforge.mason.engines.pep517.subprocess.run", return_value=_fake_completed()),
    ):
        result = pep517.build(str(tmp_path))

    assert result.wheel_path is None
    assert result.sdist_path is None
    assert result.wheel_version is None


def test_build_picks_the_most_recently_modified_wheel_when_multiple_exist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    old = dist / "pyforge_mason-0.1.0-py3-none-any.whl"
    old.write_bytes(b"")
    new = dist / "pyforge_mason-0.2.0-py3-none-any.whl"
    new.write_bytes(b"")
    os.utime(old, (1_000_000, 1_000_000))
    os.utime(new, (2_000_000, 2_000_000))

    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch("pyforge.mason.engines.pep517.subprocess.run", return_value=_fake_completed()),
    ):
        result = pep517.build(str(tmp_path))

    assert result.wheel_path == str(new)
    assert result.wheel_version == "0.2.0"


def test_build_skips_a_wheel_filename_that_does_not_parse(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "not-a-real-wheel-name.whl").write_bytes(b"")

    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch("pyforge.mason.engines.pep517.subprocess.run", return_value=_fake_completed()),
    ):
        result = pep517.build(str(tmp_path))

    assert result.wheel_path is None
    assert result.wheel_version is None


def test_build_skips_an_sdist_filename_that_does_not_parse(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "bogus.tar.gz").write_bytes(b"")

    with (
        patch("pyforge.mason.engines.pep517.require_engine", return_value="build 1.5.0"),
        patch("pyforge.mason.engines.pep517.subprocess.run", return_value=_fake_completed()),
    ):
        result = pep517.build(str(tmp_path))

    assert result.sdist_path is None
