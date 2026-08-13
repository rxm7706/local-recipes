"""Story 3.2 -- `engines/pixi.py`'s adapter. Mirrors `test_engines_pep517.py`'s
own conventions and rationale exactly (see that file's module docstring) --
only the wrapped tool, argv shape, and `.conda` filename-parsing technique
differ."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import patch

import pytest

from pyforge.mason.engines import pixi
from pyforge.mason.errors import EngineAbsentError, PackageBuildTimeoutError, PackageProjectPathError


def _fake_completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


# --- probe() -----------------------------------------------------------------

def test_probe_delegates_to_probe_engine_with_the_pixi_binary_name():
    with patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe:
        mock_probe.return_value.version = "pixi 0.76.2"
        version = pixi.probe()

    mock_probe.assert_called_once_with("pixi", "pixi")
    assert version == "pixi 0.76.2"


# --- build(): engine presence gate --------------------------------------------

def test_build_raises_engine_absent_before_any_subprocess_spawns():
    with patch(
        "pyforge.mason.engines.pixi.require_engine",
        side_effect=EngineAbsentError("pixi", "pixi"),
    ) as mock_require, patch("pyforge.mason.engines.pixi.subprocess.run") as mock_run:
        with pytest.raises(EngineAbsentError):
            pixi.build("/some/project")

    mock_require.assert_called_once_with("pixi")
    mock_run.assert_not_called()


# --- build(): invocation shape -------------------------------------------------

def test_build_invokes_pixi_build_with_the_documented_argv_and_cwd(tmp_path):
    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch(
             "pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed(),
         ) as mock_run:
        pixi.build(str(tmp_path))

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv == ["pixi", "build", "--output-dir", f"{tmp_path}/dist-conda"]
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] is None
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert "timeout" in kwargs


def test_build_uses_the_default_timeout_when_none_given(tmp_path):
    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch(
             "pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed(),
         ) as mock_run:
        pixi.build(str(tmp_path))

    assert mock_run.call_args.kwargs["timeout"] == pixi._PIXI_BUILD_TIMEOUT_SECONDS


def test_build_forwards_an_explicit_timeout(tmp_path):
    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch(
             "pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed(),
         ) as mock_run:
        pixi.build(str(tmp_path), timeout=45.0)

    assert mock_run.call_args.kwargs["timeout"] == 45.0


# --- build(): subprocess boundary translation (review pass, 2026-08-13) -------

def test_build_translates_timeout_expired_to_package_build_timeout_error(tmp_path):
    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch(
             "pyforge.mason.engines.pixi.subprocess.run",
             side_effect=subprocess.TimeoutExpired(cmd=["pixi", "build"], timeout=600.0),
         ):
        with pytest.raises(PackageBuildTimeoutError) as excinfo:
            pixi.build(str(tmp_path))

    assert excinfo.value.engine == "pixi"
    assert excinfo.value.timeout == pixi._PIXI_BUILD_TIMEOUT_SECONDS


def test_build_translates_oserror_from_a_bad_cwd_to_package_project_path_error(tmp_path):
    """`subprocess.run(cwd=project_path)` raises `FileNotFoundError`/
    `NotADirectoryError` (both `OSError` subclasses) BEFORE the wrapped
    tool ever starts when `project_path` does not exist as a directory --
    not the "tool reports its own failure via returncode" case."""
    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch(
             "pyforge.mason.engines.pixi.subprocess.run",
             side_effect=FileNotFoundError("No such file or directory"),
         ):
        with pytest.raises(PackageProjectPathError) as excinfo:
            pixi.build(str(tmp_path))

    assert excinfo.value.project_path == str(tmp_path)


# --- build(): I/O & Edge-Case Matrix -------------------------------------------

def test_build_happy_path_discovers_and_parses_the_conda_artifact(tmp_path):
    dist_conda = tmp_path / "dist-conda"
    dist_conda.mkdir()
    (dist_conda / "pyforge-mason-0.1.0-pyh4616a5c_0.conda").write_bytes(b"")

    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch(
             "pyforge.mason.engines.pixi.subprocess.run",
             return_value=_fake_completed(stdout="Building pyforge-mason\n"),
         ):
        result = pixi.build(str(tmp_path))

    assert result.returncode == 0
    assert result.conda_path == str(dist_conda / "pyforge-mason-0.1.0-pyh4616a5c_0.conda")
    assert result.conda_version == "0.1.0"
    assert result.stdout == "Building pyforge-mason\n"


def test_build_failed_child_reports_no_artifact_even_if_dist_conda_has_stale_files(tmp_path):
    """spec I/O matrix: a non-zero returncode must skip discovery entirely,
    not report a stale artifact left over from an earlier successful
    build."""
    dist_conda = tmp_path / "dist-conda"
    dist_conda.mkdir()
    (dist_conda / "pyforge-mason-9.9.9-abc123_0.conda").write_bytes(b"")

    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch(
             "pyforge.mason.engines.pixi.subprocess.run",
             return_value=_fake_completed(returncode=1, stdout="error: recipe not found\n"),
         ):
        result = pixi.build(str(tmp_path))

    assert result.returncode == 1
    assert result.conda_path is None
    assert result.conda_version is None
    assert result.stdout == "error: recipe not found\n"


def test_build_missing_dist_conda_dir_reports_no_artifact(tmp_path):
    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch("pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed()):
        result = pixi.build(str(tmp_path))

    assert result.conda_path is None
    assert result.conda_version is None


def test_build_picks_the_most_recently_modified_conda_file_when_multiple_exist(tmp_path):
    dist_conda = tmp_path / "dist-conda"
    dist_conda.mkdir()
    old = dist_conda / "pyforge-mason-0.1.0-abc123_0.conda"
    old.write_bytes(b"")
    new = dist_conda / "pyforge-mason-0.2.0-def456_0.conda"
    new.write_bytes(b"")
    os.utime(old, (1_000_000, 1_000_000))
    os.utime(new, (2_000_000, 2_000_000))

    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch("pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed()):
        result = pixi.build(str(tmp_path))

    assert result.conda_path == str(new)
    assert result.conda_version == "0.2.0"


def test_a_conda_filename_that_does_not_rsplit_into_three_parts_is_skipped(tmp_path):
    """A `.conda` filename with too few dashes can't yield name/version/
    build_string via `rsplit('-', 2)` -- must degrade to "not found", never
    raise or misparse."""
    dist_conda = tmp_path / "dist-conda"
    dist_conda.mkdir()
    (dist_conda / "noversion.conda").write_bytes(b"")

    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch("pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed()):
        result = pixi.build(str(tmp_path))

    assert result.conda_path is None
    assert result.conda_version is None


def test_a_conda_filename_with_an_empty_version_segment_is_skipped(tmp_path):
    """Review pass (2026-08-13): `pkg--0_0.conda` rsplits into exactly three
    parts (`["pkg", "", "0_0"]`) -- the `len(parts) == 3` check alone
    accepts the EMPTY string as a valid, non-`None` `conda_version`, which
    can then reach `PackageVersionMismatchError`'s own constructor (which
    raises a bare `ValueError` for an empty string) instead of degrading
    cleanly to "unparseable, same as not found" like every other malformed
    case in this module."""
    dist_conda = tmp_path / "dist-conda"
    dist_conda.mkdir()
    (dist_conda / "pkg--0_0.conda").write_bytes(b"")

    with patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"), \
         patch("pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed()):
        result = pixi.build(str(tmp_path))

    assert result.conda_path is None
    assert result.conda_version is None


def test_conda_version_parsing_handles_a_dashed_project_name():
    """Design Notes: conda's own package/version/build-string fields never
    contain a literal `-`, so `rsplit('-', 2)` is safe even for this
    project's own dashed name (`pyforge-mason`)."""
    stem = "pyforge-mason-0.1.0-pyh4616a5c_0"
    name, version, build_string = stem.rsplit("-", 2)
    assert name == "pyforge-mason"
    assert version == "0.1.0"
    assert build_string == "pyh4616a5c_0"
