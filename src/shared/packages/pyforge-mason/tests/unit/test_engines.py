"""Story 1.8 -- `engines/__init__.py`'s probe-only seed: presence via
`shutil.which`, version via `--version`, and every fold-into-`available=True,
version=None` failure path. `shutil.which`/`subprocess.run` are mocked
throughout (AD-16: no test in this suite requires a real engine binary on
PATH), mirroring `test_cfe.py`'s `subprocess.run` mocking pattern.

Story 3.1 extends this file with `EngineAdapter` protocol-shape coverage,
`require_engine` coverage (the I/O & Edge-Case Matrix: present+parses,
present+unparseable, absent), and a `_KNOWN_ENGINES`/`_ENGINE_CONDA_PACKAGES`
key-set sync guard, using the same `shutil.which`/`subprocess.run` mocking
convention.
"""

from __future__ import annotations

import subprocess
import typing
from unittest.mock import patch

import pytest

from pyforge.mason.engines import (
    _ENGINE_CONDA_PACKAGES,
    _KNOWN_ENGINES,
    EngineAdapter,
    EngineStatus,
    probe_engine,
    probe_known_engines,
    require_engine,
)
from pyforge.mason.errors import EngineAbsentError


def _fake_completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# --- I/O & Edge-Case Matrix --------------------------------------------------


def test_engine_present_and_version_parses_from_stdout():
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/pixi") as mock_which,
        patch("pyforge.mason.engines.subprocess.run", return_value=_fake_completed(stdout="pixi 0.72.2\n")) as mock_run,
    ):
        result = probe_engine("pixi", "pixi")

    mock_which.assert_called_once_with("pixi")
    mock_run.assert_called_once()
    assert result == EngineStatus(name="pixi", available=True, version="pixi 0.72.2")


def test_engine_not_on_path_reports_absent_and_never_spawns_a_subprocess():
    with (
        patch("pyforge.mason.engines.shutil.which", return_value=None),
        patch("pyforge.mason.engines.subprocess.run") as mock_run,
    ):
        result = probe_engine("conda-lock", "conda-lock")

    assert result == EngineStatus(name="conda-lock", available=False, version=None)
    mock_run.assert_not_called()


@pytest.mark.parametrize(
    "exc",
    [
        OSError("no such file"),
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad byte"),
        subprocess.TimeoutExpired(cmd=["twine", "--version"], timeout=10.0),
    ],
)
def test_engine_on_path_but_version_probe_errors_or_times_out(exc):
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/twine"),
        patch("pyforge.mason.engines.subprocess.run", side_effect=exc),
    ):
        result = probe_engine("twine", "twine")

    assert result == EngineStatus(name="twine", available=True, version=None)


def test_engine_on_path_but_version_returns_nonzero_with_empty_output():
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/build"),
        patch("pyforge.mason.engines.subprocess.run", return_value=_fake_completed(returncode=1)),
    ):
        result = probe_engine("build", "pyproject-build")

    assert result == EngineStatus(name="build", available=True, version=None)


def test_version_falls_back_to_stderr_when_stdout_is_empty():
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/conda-lock"),
        patch(
            "pyforge.mason.engines.subprocess.run",
            return_value=_fake_completed(stdout="", stderr="conda-lock, version 2.5.7\n"),
        ),
    ):
        result = probe_engine("conda-lock", "conda-lock")

    assert result == EngineStatus(name="conda-lock", available=True, version="conda-lock, version 2.5.7")


def test_version_strips_surrounding_whitespace_but_preserves_interior_lines():
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/pixi"),
        patch(
            "pyforge.mason.engines.subprocess.run",
            return_value=_fake_completed(stdout="\n\npixi 0.72.2\nextra line\n"),
        ),
    ):
        result = probe_engine("pixi", "pixi")

    assert result.version == "pixi 0.72.2\nextra line"


def test_version_preserves_a_real_multiline_wrapped_banner_like_twine():
    """Review finding (2026-08-09): the real `twine --version` banner wraps
    across multiple lines mid-word. Truncating to the first line alone
    reported a version string cut off at `requests-` -- the full stripped
    output must survive intact."""
    banner = (
        "twine version 7.0.0 (readme-renderer: 45.0, requests: 2.34.2, requests-\n"
        "toolbelt: 1.0.0, keyring: 25.7.0, rfc3986: 2.0.0)\n"
    )
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/twine"),
        patch("pyforge.mason.engines.subprocess.run", return_value=_fake_completed(stdout=banner)),
    ):
        result = probe_engine("twine", "twine")

    assert result.version == banner.strip()
    assert "requests-\ntoolbelt" in result.version


# --- Invocation shape (list argv, never shell=True, timeout) ---------------


def test_probe_invokes_subprocess_with_list_argv_no_shell_and_a_timeout():
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/pixi"),
        patch("pyforge.mason.engines.subprocess.run", return_value=_fake_completed(stdout="pixi 0.72.2")) as mock_run,
    ):
        probe_engine("pixi", "pixi")

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv == ["/usr/bin/pixi", "--version"]
    assert kwargs.get("shell", False) is False
    assert "timeout" in kwargs
    assert kwargs.get("check") is False
    assert kwargs.get("capture_output") is True
    assert kwargs.get("text") is True


# --- probe_known_engines() ---------------------------------------------------


def test_probe_known_engines_covers_pixi_twine_conda_lock_build_and_gh():
    """Story 3.7 adds `gh` as the fifth known engine."""
    assert set(_KNOWN_ENGINES) == {"pixi", "twine", "conda-lock", "build", "gh"}
    assert _KNOWN_ENGINES["build"] == "pyproject-build"
    assert _KNOWN_ENGINES["gh"] == "gh"


def test_probe_known_engines_probes_every_known_engine_in_declared_order():
    with patch("pyforge.mason.engines.shutil.which", return_value=None) as mock_which:
        statuses = probe_known_engines()

    assert [status.name for status in statuses] == list(_KNOWN_ENGINES)
    assert all(status.available is False and status.version is None for status in statuses)
    assert mock_which.call_count == len(_KNOWN_ENGINES)


def test_probe_known_engines_never_raises_even_when_every_probe_fails():
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/tool"),
        patch("pyforge.mason.engines.subprocess.run", side_effect=OSError("boom")),
    ):
        statuses = probe_known_engines()

    assert len(statuses) == len(_KNOWN_ENGINES)
    assert all(status.available is True and status.version is None for status in statuses)


# --- Story 3.1: EngineAdapter protocol shape --------------------------------


def test_engine_adapter_protocol_declares_name_and_probe():
    assert typing.Protocol in EngineAdapter.__mro__

    hints = typing.get_type_hints(EngineAdapter)
    assert hints["name"] is str

    probe_hints = typing.get_type_hints(EngineAdapter.probe)
    assert probe_hints["return"] == (str | None)


def test_engine_adapter_protocol_is_runtime_checkable():
    """Review pass (2026-08-13): matches every other structural `Protocol`
    in this codebase's sibling packages (e.g. `pyforge-warden`'s `Engine`)."""

    class _FakeAdapter:
        name = "pixi"

        def probe(self) -> str | None:
            return None

    assert isinstance(_FakeAdapter(), EngineAdapter)
    assert not isinstance(object(), EngineAdapter)


# --- Story 3.1: _KNOWN_ENGINES / _ENGINE_CONDA_PACKAGES stay in sync --------


def test_known_engines_and_conda_packages_share_the_same_key_set():
    """Review pass (2026-08-13): `require_engine` looks `name` up in both
    dicts -- the `_KNOWN_ENGINES` lookup is documented to raise `KeyError`
    for an unknown engine, but the `_ENGINE_CONDA_PACKAGES` lookup (reached
    only once an engine is confirmed absent) has no such contract. Without
    this guard, a future engine added to one dict and not the other would
    make `require_engine` leak a raw `KeyError` for a legitimately-known,
    legitimately-absent engine instead of `EngineAbsentError`."""
    assert set(_KNOWN_ENGINES) == set(_ENGINE_CONDA_PACKAGES)


# --- Story 3.1: require_engine (I/O & Edge-Case Matrix) ---------------------


def test_require_engine_returns_the_version_when_present_and_parseable():
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/twine"),
        patch(
            "pyforge.mason.engines.subprocess.run",
            return_value=_fake_completed(stdout="twine version 7.0.0\n"),
        ),
    ):
        version = require_engine("twine")

    assert version == "twine version 7.0.0"


def test_require_engine_returns_none_when_present_but_version_is_unreadable():
    """Spec I/O matrix: presence, not parseability, is what's required."""
    with (
        patch("pyforge.mason.engines.shutil.which", return_value="/usr/bin/pixi"),
        patch(
            "pyforge.mason.engines.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["pixi", "--version"], timeout=10.0),
        ),
    ):
        version = require_engine("pixi")

    assert version is None


def test_require_engine_raises_engine_absent_error_when_not_on_path():
    with (
        patch("pyforge.mason.engines.shutil.which", return_value=None),
        patch("pyforge.mason.engines.subprocess.run") as mock_run,
    ):
        with pytest.raises(EngineAbsentError) as excinfo:
            require_engine("conda-lock")

    mock_run.assert_not_called()
    exc = excinfo.value
    assert exc.identifier == "engine:absent"
    assert exc.name == "conda-lock"
    assert exc.conda_package == "conda-lock"
    assert "conda-lock" in str(exc)


def test_require_engine_names_the_build_engines_conda_package_not_its_binary_or_display_name():
    """`build`'s conda package is `python-build`, distinct from both its
    display name (`build`) and its PATH binary name (`pyproject-build`)."""
    with patch("pyforge.mason.engines.shutil.which", return_value=None):
        with pytest.raises(EngineAbsentError) as excinfo:
            require_engine("build")

    assert excinfo.value.conda_package == "python-build"
    assert "python-build" in str(excinfo.value)


def test_require_engine_probes_via_the_known_engines_binary_name():
    with patch("pyforge.mason.engines.shutil.which", return_value=None) as mock_which:
        with pytest.raises(EngineAbsentError):
            require_engine("build")

    mock_which.assert_called_once_with("pyproject-build")
