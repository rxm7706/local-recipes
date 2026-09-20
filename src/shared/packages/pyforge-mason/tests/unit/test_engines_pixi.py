"""Story 3.2 -- `engines/pixi.py`'s adapter. Mirrors `test_engines_pep517.py`'s
own conventions and rationale exactly (see that file's module docstring) --
only the wrapped tool, argv shape, and `.conda` filename-parsing technique
differ.

Story 3.5 extends this file with `upload()` coverage, mirroring
`test_engines_twine.py`'s own conventions exactly (see that file's module
docstring): presence via `require_engine` (mocked directly on this
module's own namespace), and the `upload()` operation itself via a mocked
`subprocess.run` -- no `tmp_path` fixture is needed for `upload()`'s own
tests, unlike `build()`'s: `upload()` does no filesystem-based artifact
discovery, only reports the child's raw `returncode`/merged `stdout`.

Story 3.7 extends this file again with `search()` coverage: unlike
`build()`/`upload()`, `search()` uses `probe_engine` directly (mocked, not
`require_engine`), so its own presence-gate tests assert `None` is
returned and no subprocess spawns, rather than an `EngineAbsentError`."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import patch

import pytest

from pyforge.mason.engines import pixi
from pyforge.mason.errors import (
    EngineAbsentError,
    PackageBuildTimeoutError,
    PackageProjectPathError,
    ShipChannelUploadTimeoutError,
)


def _fake_completed(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


# --- probe() -----------------------------------------------------------------


def test_probe_delegates_to_probe_engine_with_the_pixi_binary_name():
    with patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe:
        mock_probe.return_value.version = "pixi 0.76.2"
        version = pixi.probe()

    mock_probe.assert_called_once_with("pixi", "pixi")
    assert version == "pixi 0.76.2"


# --- build(): engine presence gate --------------------------------------------


def test_build_raises_engine_absent_before_any_subprocess_spawns():
    with (
        patch(
            "pyforge.mason.engines.pixi.require_engine",
            side_effect=EngineAbsentError("pixi", "pixi"),
        ) as mock_require,
        patch("pyforge.mason.engines.pixi.subprocess.run") as mock_run,
    ):
        with pytest.raises(EngineAbsentError):
            pixi.build("/some/project")

    mock_require.assert_called_once_with("pixi")
    mock_run.assert_not_called()


# --- build(): invocation shape -------------------------------------------------


def test_build_invokes_pixi_build_with_the_documented_argv_and_cwd(tmp_path):
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
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
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        pixi.build(str(tmp_path))

    assert mock_run.call_args.kwargs["timeout"] == pixi._PIXI_BUILD_TIMEOUT_SECONDS


def test_build_forwards_an_explicit_timeout(tmp_path):
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        pixi.build(str(tmp_path), timeout=45.0)

    assert mock_run.call_args.kwargs["timeout"] == 45.0


# --- build(): subprocess boundary translation (review pass, 2026-08-13) -------


def test_build_translates_timeout_expired_to_package_build_timeout_error(tmp_path):
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["pixi", "build"], timeout=600.0),
        ),
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
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            side_effect=FileNotFoundError("No such file or directory"),
        ),
    ):
        with pytest.raises(PackageProjectPathError) as excinfo:
            pixi.build(str(tmp_path))

    assert excinfo.value.project_path == str(tmp_path)


# --- build(): I/O & Edge-Case Matrix -------------------------------------------


def test_build_happy_path_discovers_and_parses_the_conda_artifact(tmp_path):
    dist_conda = tmp_path / "dist-conda"
    dist_conda.mkdir()
    (dist_conda / "pyforge-mason-0.1.0-pyh4616a5c_0.conda").write_bytes(b"")

    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(stdout="Building pyforge-mason\n"),
        ),
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

    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(returncode=1, stdout="error: recipe not found\n"),
        ),
    ):
        result = pixi.build(str(tmp_path))

    assert result.returncode == 1
    assert result.conda_path is None
    assert result.conda_version is None
    assert result.stdout == "error: recipe not found\n"


def test_build_missing_dist_conda_dir_reports_no_artifact(tmp_path):
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch("pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed()),
    ):
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

    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch("pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed()),
    ):
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

    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch("pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed()),
    ):
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

    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch("pyforge.mason.engines.pixi.subprocess.run", return_value=_fake_completed()),
    ):
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


# --- upload(): probe() delegation (Story 3.5) -----------------------------------
# already covered above by `test_probe_delegates_to_probe_engine_with_the_pixi_
# binary_name`, unchanged -- `probe()` is shared by both `build()` and `upload()`.


# --- upload(): engine presence gate ---------------------------------------------


def test_upload_raises_engine_absent_before_any_subprocess_spawns():
    with (
        patch(
            "pyforge.mason.engines.pixi.require_engine",
            side_effect=EngineAbsentError("pixi", "pixi"),
        ) as mock_require,
        patch("pyforge.mason.engines.pixi.subprocess.run") as mock_run,
    ):
        with pytest.raises(EngineAbsentError):
            pixi.upload("dist-conda/pkg-0.1.0-abc123_0.conda", "myorg")

    mock_require.assert_called_once_with("pixi")
    mock_run.assert_not_called()


# --- upload(): invocation shape --------------------------------------------------


def test_upload_invokes_pixi_upload_prefix_with_the_documented_argv():
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        pixi.upload("dist-conda/pkg-0.1.0-abc123_0.conda", "myorg")

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv == [
        "pixi",
        "upload",
        "prefix",
        "--channel",
        "myorg",
        "dist-conda/pkg-0.1.0-abc123_0.conda",
    ]
    assert "env" not in kwargs
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.STDOUT
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert "timeout" in kwargs


def test_upload_uses_the_default_timeout_when_none_given():
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        pixi.upload("dist-conda/pkg-0.1.0-abc123_0.conda", "myorg")

    assert mock_run.call_args.kwargs["timeout"] == pixi._PIXI_UPLOAD_TIMEOUT_SECONDS


def test_upload_forwards_an_explicit_timeout():
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        pixi.upload("dist-conda/pkg-0.1.0-abc123_0.conda", "myorg", timeout=45.0)

    assert mock_run.call_args.kwargs["timeout"] == 45.0


# --- upload(): subprocess boundary translation -----------------------------------


def test_upload_translates_timeout_expired_to_ship_channel_upload_timeout_error():
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["pixi", "upload"], timeout=300.0),
        ),
    ):
        with pytest.raises(ShipChannelUploadTimeoutError) as excinfo:
            pixi.upload("dist-conda/pkg-0.1.0-abc123_0.conda", "myorg")

    assert excinfo.value.timeout == pixi._PIXI_UPLOAD_TIMEOUT_SECONDS


def test_upload_translates_oserror_to_engine_absent_error():
    """review pass, 2026-08-13: `upload()` passes no `cwd=`, so an `OSError`
    here can only mean `pixi` itself vanished/lost exec permission between
    `require_engine`'s own probe and this call's separate spawn -- the same
    "engine is not usable" condition `require_engine` itself raises
    `EngineAbsentError` for."""
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            side_effect=FileNotFoundError("No such file or directory"),
        ),
    ):
        with pytest.raises(EngineAbsentError) as excinfo:
            pixi.upload("dist-conda/pkg-0.1.0-abc123_0.conda", "myorg")

    assert excinfo.value.name == "pixi"


# --- upload(): I/O & Edge-Case Matrix ---------------------------------------------


def test_upload_merged_stream_captures_a_stderr_only_failure_diagnostic():
    """Design Notes: a live repro of `pixi upload prefix --channel x
    nonexistent.conda` with no `PREFIX_API_KEY` set wrote its entire error
    text to stderr and nothing to stdout -- `stderr=subprocess.STDOUT`
    merges that diagnostic into `PixiUploadResult.stdout`."""
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(
                returncode=1,
                stdout="Error:   x no prefix.dev API key provided\n",
            ),
        ),
    ):
        result = pixi.upload("dist-conda/pkg-0.1.0-abc123_0.conda", "myorg")

    assert result.returncode == 1
    assert "no prefix.dev API key provided" in result.stdout


def test_upload_zero_returncode_success_has_no_url_or_reference_field():
    """spec Design Notes: no equivalent live-verified success-path output
    shape exists for `pixi upload prefix` -- `PixiUploadResult` reports only
    `returncode`/`stdout`, no `url` field to assert (none exists)."""
    with (
        patch("pyforge.mason.engines.pixi.require_engine", return_value="pixi 0.76.2"),
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(returncode=0, stdout="Uploading...\ndone\n"),
        ),
    ):
        result = pixi.upload("dist-conda/pkg-0.1.0-abc123_0.conda", "myorg")

    assert result.returncode == 0
    assert result.stdout == "Uploading...\ndone\n"
    assert not hasattr(result, "url")
    assert not hasattr(result, "reference")


# --- search(): engine presence gate (Story 3.7) ---------------------------------


def test_search_returns_none_when_pixi_is_absent_and_never_spawns():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch("pyforge.mason.engines.pixi.subprocess.run") as mock_run,
    ):
        mock_probe.return_value.available = False
        result = pixi.search("pkg", "0.1.0", "myorg")

    mock_probe.assert_called_once_with("pixi", "pixi")
    assert result is None
    mock_run.assert_not_called()


# --- search(): invocation shape --------------------------------------------------


def test_search_invokes_pixi_search_with_the_documented_argv():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        mock_probe.return_value.available = True
        pixi.search("pkg", "0.1.0", "myorg")

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv == ["pixi", "search", "--channel", "myorg", "pkg==0.1.0", "--json"]
    assert "env" not in kwargs
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.PIPE
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert "timeout" in kwargs


def test_search_uses_the_default_timeout_when_none_given():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        mock_probe.return_value.available = True
        pixi.search("pkg", "0.1.0", "myorg")

    assert mock_run.call_args.kwargs["timeout"] == pixi._PIXI_SEARCH_TIMEOUT_SECONDS


def test_search_forwards_an_explicit_timeout():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        mock_probe.return_value.available = True
        pixi.search("pkg", "0.1.0", "myorg", timeout=5.0)

    assert mock_run.call_args.kwargs["timeout"] == 5.0


# --- search(): I/O & Edge-Case Matrix ---------------------------------------------


def test_search_returns_true_on_a_zero_returncode():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(stdout='{"noarch": [{}]}'),
        ),
    ):
        mock_probe.return_value.available = True
        result = pixi.search("pkg", "0.1.0", "myorg")

    assert result is True


def test_search_returns_none_on_a_zero_returncode_with_unparseable_json():
    """Review pass (adversarial + edge-case, this story): the returncode
    alone is not trusted -- a body that fails to parse as JSON is exactly as
    undeterminable as a network error, mirroring `engines.gh.find_open_pr`'s
    own body-validation diligence."""
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(stdout="not json"),
        ),
    ):
        mock_probe.return_value.available = True
        result = pixi.search("pkg", "0.1.0", "myorg")

    assert result is None


def test_search_returns_none_on_a_zero_returncode_with_a_non_dict_json_body():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(stdout="[]"),
        ),
    ):
        mock_probe.return_value.available = True
        result = pixi.search("pkg", "0.1.0", "myorg")

    assert result is None


def test_search_returns_none_on_a_zero_returncode_with_only_empty_platform_lists():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(stdout='{"noarch": [], "linux-64": []}'),
        ),
    ):
        mock_probe.return_value.available = True
        result = pixi.search("pkg", "0.1.0", "myorg")

    assert result is None


def test_search_returns_false_when_stderr_names_no_packages_found():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(returncode=1, stderr="Error: No packages found\n"),
        ),
    ):
        mock_probe.return_value.available = True
        result = pixi.search("pkg", "0.1.0", "myorg")

    assert result is False


def test_search_returns_none_on_an_unrecognized_nonzero_failure():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            return_value=_fake_completed(returncode=1, stderr="Error: network unreachable\n"),
        ),
    ):
        mock_probe.return_value.available = True
        result = pixi.search("pkg", "0.1.0", "myorg")

    assert result is None


def test_search_returns_none_on_timeout():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["pixi", "search"], timeout=30.0),
        ),
    ):
        mock_probe.return_value.available = True
        result = pixi.search("pkg", "0.1.0", "myorg")

    assert result is None


def test_search_returns_none_on_a_bare_oserror():
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.pixi.subprocess.run",
            side_effect=FileNotFoundError("No such file or directory"),
        ),
    ):
        mock_probe.return_value.available = True
        result = pixi.search("pkg", "0.1.0", "myorg")

    assert result is None


def test_search_never_raises_for_any_undeterminable_cause():
    """Spec I/O matrix: 'Channel interrogation undeterminable' is data,
    never raised."""
    with (
        patch("pyforge.mason.engines.pixi.probe_engine") as mock_probe,
        patch("pyforge.mason.engines.pixi.subprocess.run", side_effect=OSError("boom")),
    ):
        mock_probe.return_value.available = True
        assert pixi.search("pkg", "0.1.0", "myorg") is None
