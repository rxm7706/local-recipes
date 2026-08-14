"""Story 4.1 -- `engines/condalock.py`'s adapter: presence via
`require_engine` (mocked directly on this module's own namespace, mirroring
`test_engines_pep517.py`/`test_engines_twine.py`'s established convention),
and the `lock()` operation itself via a mocked `subprocess.run` -- no real
`conda-lock` binary is needed for this file's coverage (AD-16). The `--mdy`
provenance file is real (`tempfile.mkstemp`/`os.fdopen` are not mocked), so
its JSON content can be asserted from inside a `subprocess.run` side effect
before `lock()`'s own `finally` block removes it."""

from __future__ import annotations

import json
import os
import subprocess
from unittest.mock import patch

import pytest

from pyforge.mason.engines import condalock
from pyforge.mason.errors import EngineAbsentError, EnvironmentLockTimeoutError

_MANIFEST_PATHS = ("environment.yml",)
_OUTPUT_PATH = "conda-lock.yml"


def _fake_completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


def _mdy_path(argv: list[str]) -> str:
    return argv[argv.index("--mdy") + 1]


# --- probe() -------------------------------------------------------------------

def test_probe_delegates_to_probe_engine_with_the_conda_lock_binary_name():
    with patch("pyforge.mason.engines.condalock.probe_engine") as mock_probe:
        mock_probe.return_value.version = "conda-lock 4.0.2"
        version = condalock.probe()

    mock_probe.assert_called_once_with("conda-lock", "conda-lock")
    assert version == "conda-lock 4.0.2"


# --- lock(): engine presence gate ------------------------------------------------

def test_lock_raises_engine_absent_before_any_subprocess_spawn_or_tempfile_write():
    with patch(
        "pyforge.mason.engines.condalock.require_engine",
        side_effect=EngineAbsentError("conda-lock", "conda-lock"),
    ) as mock_require, \
         patch("pyforge.mason.engines.condalock.subprocess.run") as mock_run, \
         patch("pyforge.mason.engines.condalock.tempfile.mkstemp") as mock_mkstemp:
        with pytest.raises(EngineAbsentError):
            condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    mock_require.assert_called_once_with("conda-lock")
    mock_run.assert_not_called()
    mock_mkstemp.assert_not_called()


# --- lock(): invocation shape ----------------------------------------------------

def test_lock_invokes_conda_lock_with_the_documented_argv_and_kwargs():
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", return_value=_fake_completed(),
    ) as mock_run:
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH, platforms=("linux-64",))

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv[:2] == ["conda-lock", "lock"]
    assert "-f" in argv and argv[argv.index("-f") + 1] == "environment.yml"
    assert "-p" in argv and argv[argv.index("-p") + 1] == "linux-64"
    assert "--lockfile" in argv and argv[argv.index("--lockfile") + 1] == _OUTPUT_PATH
    assert "--mdy" in argv
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] is None
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert "timeout" in kwargs


def test_lock_uses_the_default_timeout_when_none_given():
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", return_value=_fake_completed(),
    ) as mock_run:
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert mock_run.call_args.kwargs["timeout"] == condalock._CONDA_LOCK_TIMEOUT_SECONDS


def test_lock_forwards_an_explicit_timeout():
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", return_value=_fake_completed(),
    ) as mock_run:
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH, timeout=45.0)

    assert mock_run.call_args.kwargs["timeout"] == 45.0


# --- lock(): subprocess boundary translation -------------------------------------

def test_lock_translates_timeout_expired_to_environment_lock_timeout_error():
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["conda-lock", "lock"], timeout=600.0),
    ):
        with pytest.raises(EnvironmentLockTimeoutError) as excinfo:
            condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert excinfo.value.timeout == condalock._CONDA_LOCK_TIMEOUT_SECONDS


def test_lock_removes_the_mdy_metadata_file_even_after_a_timeout():
    captured_paths: list[str] = []

    def _side_effect(argv, **kwargs):
        captured_paths.append(_mdy_path(argv))
        raise subprocess.TimeoutExpired(cmd=argv, timeout=600.0)

    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", side_effect=_side_effect,
    ):
        with pytest.raises(EnvironmentLockTimeoutError):
            condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert len(captured_paths) == 1
    assert not os.path.exists(captured_paths[0])


# --- lock(): I/O & Edge-Case Matrix ----------------------------------------------

def test_lock_happy_path_reports_the_lockfile_path_and_engine_identity():
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run",
        return_value=_fake_completed(stdout="Locking dependencies...\n"),
    ):
        result = condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert result.returncode == 0
    assert result.lockfile_path == _OUTPUT_PATH
    assert result.engine_name == "conda-lock"
    assert result.engine_version == "conda-lock 4.0.2"
    assert result.stdout == "Locking dependencies...\n"


def test_lock_failed_solve_reports_no_lockfile_but_still_reports_engine_identity():
    """spec I/O matrix: a failed solve is DATA (AD-4) -- `lockfile_path` is
    `None`, but `engine_name`/`engine_version` stay populated."""
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run",
        return_value=_fake_completed(returncode=1, stdout=""),
    ):
        result = condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert result.returncode == 1
    assert result.lockfile_path is None
    assert result.engine_name == "conda-lock"
    assert result.engine_version == "conda-lock 4.0.2"


def test_lock_with_no_platforms_carries_zero_dash_p_flags():
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", return_value=_fake_completed(),
    ) as mock_run:
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    argv = mock_run.call_args.args[0]
    assert "-p" not in argv


def test_lock_with_multiple_platforms_repeats_dash_p_in_order():
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", return_value=_fake_completed(),
    ) as mock_run:
        condalock.lock(
            _MANIFEST_PATHS, _OUTPUT_PATH, platforms=("linux-64", "osx-arm64"),
        )

    argv = mock_run.call_args.args[0]
    p_indices = [i for i, token in enumerate(argv) if token == "-p"]
    assert [argv[i + 1] for i in p_indices] == ["linux-64", "osx-arm64"]


def test_lock_with_multiple_manifests_repeats_dash_f_in_order():
    manifests = ("environment.yml", "pyproject.toml")
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", return_value=_fake_completed(),
    ) as mock_run:
        condalock.lock(manifests, _OUTPUT_PATH)

    argv = mock_run.call_args.args[0]
    f_indices = [i for i, token in enumerate(argv) if token == "-f"]
    assert [argv[i + 1] for i in f_indices] == list(manifests)


def test_lock_with_no_manifest_paths_carries_zero_dash_f_flags():
    """Symmetric with the zero-`platforms` case above: an empty
    `manifest_paths` emits no `-f` flags at all, letting `conda-lock` fall
    back to its own manifest auto-discovery rather than Mason inventing one
    (review pass, 2026-08-14)."""
    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", return_value=_fake_completed(),
    ) as mock_run:
        condalock.lock((), _OUTPUT_PATH)

    argv = mock_run.call_args.args[0]
    assert "-f" not in argv


def test_lock_with_an_unparseable_engine_version_reports_none():
    """`require_engine` can legitimately return `None` for a present-but-
    unparseable binary (`engines/__init__.py::require_engine`'s own
    contract) -- `engine_version` must stay `None` on the result, and the
    `--mdy` JSON write must not crash on a `None` value (review pass,
    2026-08-14)."""
    observed_content: dict = {}

    def _side_effect(argv, **kwargs):
        with open(_mdy_path(argv), encoding="utf-8") as handle:
            observed_content.update(json.load(handle))
        return _fake_completed()

    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value=None,
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", side_effect=_side_effect,
    ):
        result = condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert result.engine_version is None
    assert observed_content == {"mason_engine_name": "conda-lock", "mason_engine_version": None}


# --- lock(): --mdy provenance file -------------------------------------------------

def test_lock_writes_the_mdy_metadata_file_with_engine_identity_before_the_child_runs():
    """Reads the `--mdy` file's path from the captured argv and asserts its
    JSON content from inside the `subprocess.run` side effect -- before
    `lock()`'s own `finally` block removes it."""
    observed_content: dict = {}

    def _side_effect(argv, **kwargs):
        with open(_mdy_path(argv), encoding="utf-8") as handle:
            observed_content.update(json.load(handle))
        return _fake_completed()

    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", side_effect=_side_effect,
    ):
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert observed_content == {
        "mason_engine_name": "conda-lock",
        "mason_engine_version": "conda-lock 4.0.2",
    }


def test_lock_removes_the_mdy_metadata_file_after_a_successful_solve():
    captured_paths: list[str] = []

    def _side_effect(argv, **kwargs):
        captured_paths.append(_mdy_path(argv))
        assert os.path.exists(captured_paths[0])
        return _fake_completed()

    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", side_effect=_side_effect,
    ):
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert not os.path.exists(captured_paths[0])


def test_lock_removes_the_mdy_metadata_file_after_a_failed_solve():
    captured_paths: list[str] = []

    def _side_effect(argv, **kwargs):
        captured_paths.append(_mdy_path(argv))
        return _fake_completed(returncode=1)

    with patch(
        "pyforge.mason.engines.condalock.require_engine", return_value="conda-lock 4.0.2",
    ), patch(
        "pyforge.mason.engines.condalock.subprocess.run", side_effect=_side_effect,
    ):
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert not os.path.exists(captured_paths[0])
