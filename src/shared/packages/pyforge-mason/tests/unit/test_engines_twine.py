"""Story 3.4 -- `engines/twine.py`'s adapter: presence via `require_engine`
(mocked directly on this module's own namespace, mirroring
`test_engines_pep517.py`/`test_engines_pixi.py`'s established convention),
and the `upload()` operation itself via a mocked `subprocess.run` -- no
`tmp_path` fixture is needed here, unlike the two build adapters: `upload()`
does no filesystem-based artifact discovery, only ANSI-stripped stdout
parsing (see `twine.py`'s own module docstring), so no real `twine` binary
is needed for this file's coverage (AD-16).

Story 3.9 extends this file with `repository_url` coverage (FR-24, FR-50,
AD-26): present -> `--repository-url <url>` lands in argv immediately
before the paths; omitted/`None` -> argv is byte-identical to every
pre-3.9 assertion above (unchanged)."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from pyforge.mason.engines import twine
from pyforge.mason.errors import EngineAbsentError, ShipUploadTimeoutError

_PATHS = ("dist/pkg-0.1.0-py3-none-any.whl", "dist/pkg-0.1.0.tar.gz")


def _fake_completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


# --- probe() -------------------------------------------------------------------


def test_probe_delegates_to_probe_engine_with_the_twine_binary_name():
    with patch("pyforge.mason.engines.twine.probe_engine") as mock_probe:
        mock_probe.return_value.version = "twine version 7.0.0"
        version = twine.probe()

    mock_probe.assert_called_once_with("twine", "twine")
    assert version == "twine version 7.0.0"


# --- upload(): engine presence gate --------------------------------------------


def test_upload_raises_engine_absent_before_any_subprocess_spawns():
    with (
        patch(
            "pyforge.mason.engines.twine.require_engine",
            side_effect=EngineAbsentError("twine", "twine"),
        ) as mock_require,
        patch("pyforge.mason.engines.twine.subprocess.run") as mock_run,
    ):
        with pytest.raises(EngineAbsentError):
            twine.upload(_PATHS)

    mock_require.assert_called_once_with("twine")
    mock_run.assert_not_called()


# --- upload(): invocation shape -------------------------------------------------


def test_upload_invokes_twine_with_the_documented_argv():
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        twine.upload(_PATHS)

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv == [
        "twine",
        "upload",
        "--non-interactive",
        "--disable-progress-bar",
        *_PATHS,
    ]
    assert "env" not in kwargs
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] is None
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert "timeout" in kwargs


def test_upload_uses_the_default_timeout_when_none_given():
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        twine.upload(_PATHS)

    assert mock_run.call_args.kwargs["timeout"] == twine._TWINE_UPLOAD_TIMEOUT_SECONDS


def test_upload_forwards_an_explicit_timeout():
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        twine.upload(_PATHS, timeout=45.0)

    assert mock_run.call_args.kwargs["timeout"] == 45.0


# --- upload(): subprocess boundary translation ----------------------------------


def test_upload_translates_timeout_expired_to_ship_upload_timeout_error():
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["twine", "upload"], timeout=300.0),
        ),
    ):
        with pytest.raises(ShipUploadTimeoutError) as excinfo:
            twine.upload(_PATHS)

    assert excinfo.value.timeout == twine._TWINE_UPLOAD_TIMEOUT_SECONDS


# --- upload(): I/O & Edge-Case Matrix --------------------------------------------


def test_upload_strips_ansi_and_extracts_the_view_at_url_on_success():
    raw_stdout = (
        "Uploading pkg-0.1.0-py3-none-any.whl\n"
        "\x1b[32m100%\x1b[0m\n"
        "\n\x1b[32mView at:\x1b[0m\n"
        "https://pypi.org/project/pkg/0.1.0/\n"
    )
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            return_value=_fake_completed(stdout=raw_stdout),
        ),
    ):
        result = twine.upload(_PATHS)

    assert result.returncode == 0
    assert result.url == "https://pypi.org/project/pkg/0.1.0/"
    assert "\x1b[" not in result.stdout
    assert "View at:" in result.stdout


def test_upload_url_is_none_on_a_zero_returncode_stdout_with_no_view_at_block():
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            return_value=_fake_completed(stdout="Uploading pkg\n100%\n"),
        ),
    ):
        result = twine.upload(_PATHS)

    assert result.returncode == 0
    assert result.url is None


def test_upload_failure_leaves_url_none_and_preserves_ansi_stripped_stdout():
    raw_stdout = "\x1b[31mERROR   \x1b[0m HTTPError: 400 Bad Request\n"
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            return_value=_fake_completed(returncode=1, stdout=raw_stdout),
        ),
    ):
        result = twine.upload(_PATHS)

    assert result.returncode == 1
    assert result.url is None
    assert "\x1b[" not in result.stdout
    assert "ERROR" in result.stdout
    assert "HTTPError: 400 Bad Request" in result.stdout


def test_upload_never_scans_for_a_view_at_url_on_failure_even_if_present():
    """spec Always boundary: the URL scan only runs on `returncode == 0` --
    a nonzero returncode must report `url=None` even if the (ANSI-stripped)
    stdout happens to contain a `"View at:"`-shaped block."""
    raw_stdout = "View at:\nhttps://pypi.org/project/pkg/0.1.0/\nERROR after the fact\n"
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            return_value=_fake_completed(returncode=1, stdout=raw_stdout),
        ),
    ):
        result = twine.upload(_PATHS)

    assert result.returncode == 1
    assert result.url is None


# --- upload(): Story 3.9 `repository_url` -------------------------------------


def test_upload_appends_repository_url_flag_immediately_before_the_paths():
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        twine.upload(_PATHS, repository_url="https://test.pypi.org/legacy/")

    argv = mock_run.call_args.args[0]
    assert argv == [
        "twine",
        "upload",
        "--non-interactive",
        "--disable-progress-bar",
        "--repository-url",
        "https://test.pypi.org/legacy/",
        *_PATHS,
    ]


def test_upload_omits_repository_url_flag_when_none():
    """Regression: the pre-3.9 argv shape must be unchanged when
    `repository_url` is not given -- mirrors
    `test_upload_invokes_twine_with_the_documented_argv` above but asserts
    it directly against the `repository_url=None` default."""
    with (
        patch("pyforge.mason.engines.twine.require_engine", return_value="twine 7.0.0"),
        patch(
            "pyforge.mason.engines.twine.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        twine.upload(_PATHS, repository_url=None)

    argv = mock_run.call_args.args[0]
    assert argv == ["twine", "upload", "--non-interactive", "--disable-progress-bar", *_PATHS]
    assert "--repository-url" not in argv
