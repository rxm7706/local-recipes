"""Story 4.1 -- `engines/condalock.py`'s adapter: presence via
`require_engine` (mocked directly on this module's own namespace, mirroring
`test_engines_pep517.py`/`test_engines_twine.py`'s established convention),
and the `lock()` operation itself via a mocked `subprocess.run` -- no real
`conda-lock` binary is needed for this file's coverage (AD-16). The `--mdy`
provenance file is real (`tempfile.mkstemp`/`os.fdopen` are not mocked), so
its JSON content can be asserted from inside a `subprocess.run` side effect
before `lock()`'s own `finally` block removes it.

Story 4.4 adds `check()`'s own coverage below, mirroring `lock()`'s
established conventions exactly: `require_engine`/`subprocess.run` mocked
the same way, and the temporary lockfile copy is real (`tempfile.mkstemp`/
`shutil.copyfile` are not mocked) so its `metadata.content_hash` can be
asserted/rewritten from inside a `subprocess.run` side effect, the same
pattern `_mdy_path`/the `--mdy` tests above already establish for `lock()`'s
own temp file. Review pass, 2026-08-15 adds coverage for the TOCTOU race
(`shutil.copyfile` mocked to raise), a non-zero returncode staying DATA
(never raised) at this layer, and malformed-lockfile-content translation
(`EnvironmentLockfileMalformedError`) for both the before- and after-read."""

from __future__ import annotations

import json
import os
import subprocess
from unittest.mock import patch

import pytest
import yaml

from pyforge.mason.engines import condalock
from pyforge.mason.errors import (
    EngineAbsentError,
    EnvironmentCheckTimeoutError,
    EnvironmentLockfileMalformedError,
    EnvironmentLockfileMissingError,
    EnvironmentLockTimeoutError,
)

_MANIFEST_PATHS = ("environment.yml",)
_OUTPUT_PATH = "conda-lock.yml"


def _fake_completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


def _mdy_path(argv: list[str]) -> str:
    return argv[argv.index("--mdy") + 1]


def _check_lockfile_path(argv: list[str]) -> str:
    return argv[argv.index("--lockfile") + 1]


def _write_lockfile(path, content_hash: dict) -> None:
    """A minimal real lockfile on disk: just enough YAML structure for
    `check()`'s own `["metadata"]["content_hash"]` lookup -- mirrors a real
    conda-lock lockfile's top-level shape without any of its other content,
    which `check()` never reads."""
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump({"metadata": {"content_hash": content_hash}}, handle)


# --- probe() -------------------------------------------------------------------


def test_probe_delegates_to_probe_engine_with_the_conda_lock_binary_name():
    with patch("pyforge.mason.engines.condalock.probe_engine") as mock_probe:
        mock_probe.return_value.version = "conda-lock 4.0.2"
        version = condalock.probe()

    mock_probe.assert_called_once_with("conda-lock", "conda-lock")
    assert version == "conda-lock 4.0.2"


# --- lock(): engine presence gate ------------------------------------------------


def test_lock_raises_engine_absent_before_any_subprocess_spawn_or_tempfile_write():
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            side_effect=EngineAbsentError("conda-lock", "conda-lock"),
        ) as mock_require,
        patch("pyforge.mason.engines.condalock.subprocess.run") as mock_run,
        patch("pyforge.mason.engines.condalock.tempfile.mkstemp") as mock_mkstemp,
    ):
        with pytest.raises(EngineAbsentError):
            condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    mock_require.assert_called_once_with("conda-lock")
    mock_run.assert_not_called()
    mock_mkstemp.assert_not_called()


# --- lock(): invocation shape ----------------------------------------------------


def test_lock_invokes_conda_lock_with_the_documented_argv_and_kwargs():
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
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
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert mock_run.call_args.kwargs["timeout"] == condalock._CONDA_LOCK_TIMEOUT_SECONDS


def test_lock_forwards_an_explicit_timeout():
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH, timeout=45.0)

    assert mock_run.call_args.kwargs["timeout"] == 45.0


# --- lock(): subprocess boundary translation -------------------------------------


def test_lock_translates_timeout_expired_to_environment_lock_timeout_error():
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["conda-lock", "lock"], timeout=600.0),
        ),
    ):
        with pytest.raises(EnvironmentLockTimeoutError) as excinfo:
            condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert excinfo.value.timeout == condalock._CONDA_LOCK_TIMEOUT_SECONDS


def test_lock_removes_the_mdy_metadata_file_even_after_a_timeout():
    captured_paths: list[str] = []

    def _side_effect(argv, **kwargs):
        captured_paths.append(_mdy_path(argv))
        raise subprocess.TimeoutExpired(cmd=argv, timeout=600.0)

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        with pytest.raises(EnvironmentLockTimeoutError):
            condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert len(captured_paths) == 1
    assert not os.path.exists(captured_paths[0])


# --- lock(): I/O & Edge-Case Matrix ----------------------------------------------


def test_lock_happy_path_reports_the_lockfile_path_and_engine_identity():
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(stdout="Locking dependencies...\n"),
        ),
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
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(returncode=1, stdout=""),
        ),
    ):
        result = condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert result.returncode == 1
    assert result.lockfile_path is None
    assert result.engine_name == "conda-lock"
    assert result.engine_version == "conda-lock 4.0.2"


def test_lock_with_no_platforms_carries_zero_dash_p_flags():
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    argv = mock_run.call_args.args[0]
    assert "-p" not in argv


def test_lock_with_multiple_platforms_repeats_dash_p_in_order():
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        condalock.lock(
            _MANIFEST_PATHS,
            _OUTPUT_PATH,
            platforms=("linux-64", "osx-arm64"),
        )

    argv = mock_run.call_args.args[0]
    p_indices = [i for i, token in enumerate(argv) if token == "-p"]
    assert [argv[i + 1] for i in p_indices] == ["linux-64", "osx-arm64"]


def test_lock_with_multiple_manifests_repeats_dash_f_in_order():
    manifests = ("environment.yml", "pyproject.toml")
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        condalock.lock(manifests, _OUTPUT_PATH)

    argv = mock_run.call_args.args[0]
    f_indices = [i for i, token in enumerate(argv) if token == "-f"]
    assert [argv[i + 1] for i in f_indices] == list(manifests)


def test_lock_with_no_manifest_paths_carries_zero_dash_f_flags():
    """Symmetric with the zero-`platforms` case above: an empty
    `manifest_paths` emits no `-f` flags at all, letting `conda-lock` fall
    back to its own manifest auto-discovery rather than Mason inventing one
    (review pass, 2026-08-14)."""
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
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

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value=None,
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
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

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
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

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert not os.path.exists(captured_paths[0])


def test_lock_removes_the_mdy_metadata_file_after_a_failed_solve():
    captured_paths: list[str] = []

    def _side_effect(argv, **kwargs):
        captured_paths.append(_mdy_path(argv))
        return _fake_completed(returncode=1)

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        condalock.lock(_MANIFEST_PATHS, _OUTPUT_PATH)

    assert not os.path.exists(captured_paths[0])


# --- check(): engine presence gate ------------------------------------------------


def test_check_raises_engine_absent_before_any_subprocess_spawn_or_tempfile_copy(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            side_effect=EngineAbsentError("conda-lock", "conda-lock"),
        ) as mock_require,
        patch("pyforge.mason.engines.condalock.subprocess.run") as mock_run,
        patch("pyforge.mason.engines.condalock.tempfile.mkstemp") as mock_mkstemp,
    ):
        with pytest.raises(EngineAbsentError):
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    mock_require.assert_called_once_with("conda-lock")
    mock_run.assert_not_called()
    mock_mkstemp.assert_not_called()


# --- check(): lockfile presence gate ----------------------------------------------


def test_check_raises_lockfile_missing_before_any_subprocess_spawn(tmp_path):
    missing_path = str(tmp_path / "does-not-exist.yml")
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
        ) as mock_run,
        patch(
            "pyforge.mason.engines.condalock.tempfile.mkstemp",
        ) as mock_mkstemp,
    ):
        with pytest.raises(EnvironmentLockfileMissingError) as excinfo:
            condalock.check(missing_path, _MANIFEST_PATHS)

    assert excinfo.value.lockfile_path == missing_path
    mock_run.assert_not_called()
    mock_mkstemp.assert_not_called()


# --- check(): invocation shape ----------------------------------------------------


def test_check_invokes_conda_lock_with_the_documented_argv_and_kwargs(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        condalock.check(str(lockfile), _MANIFEST_PATHS, platforms=("linux-64",))

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv[:3] == ["conda-lock", "lock", "--check-input-hash"]
    assert "-f" in argv and argv[argv.index("-f") + 1] == "environment.yml"
    assert "-p" in argv and argv[argv.index("-p") + 1] == "linux-64"
    assert "--lockfile" in argv
    # The temp copy's path, never the caller's own lockfile path.
    assert _check_lockfile_path(argv) != str(lockfile)
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] is None
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert "timeout" in kwargs


def test_check_with_no_platforms_carries_zero_dash_p_flags(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        condalock.check(str(lockfile), _MANIFEST_PATHS)

    argv = mock_run.call_args.args[0]
    assert "-p" not in argv


def test_check_uses_the_default_timeout_when_none_given(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert mock_run.call_args.kwargs["timeout"] == condalock._CONDA_LOCK_TIMEOUT_SECONDS


def test_check_forwards_an_explicit_timeout(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ) as mock_run,
    ):
        condalock.check(str(lockfile), _MANIFEST_PATHS, timeout=45.0)

    assert mock_run.call_args.kwargs["timeout"] == 45.0


# --- check(): the original lockfile is never mutated -------------------------------


def test_check_never_mutates_the_original_lockfile_on_the_current_path(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    original_bytes = lockfile.read_bytes()

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(),
        ),
    ):
        result = condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert result.stale is False
    assert lockfile.read_bytes() == original_bytes


def test_check_never_mutates_the_original_lockfile_on_the_stale_path(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    original_bytes = lockfile.read_bytes()

    def _side_effect(argv, **kwargs):
        # Simulates conda-lock rewriting the TEMP copy after a real solve --
        # the original path is never opened for writing by check() at all.
        _write_lockfile(_check_lockfile_path(argv), {"linux-64": "changed"})
        return _fake_completed()

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        result = condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert result.stale is True
    assert lockfile.read_bytes() == original_bytes


# --- check(): staleness verdict -----------------------------------------------------


def test_check_reports_stale_false_when_the_temp_copys_content_hash_is_unchanged(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})

    def _side_effect(argv, **kwargs):
        # Installed conda-lock 4.0.2 writes NOTHING on its "nothing changed"
        # branch (module docstring, corrected 2026-08-15 second) -- but if a
        # future version did re-serialize there, only formatting would
        # differ, the parsed dict would be identical, and that must still
        # NOT be reported as stale. That forward-compatibility is exactly
        # what comparing parsed dicts rather than raw bytes buys, so this
        # rewrite stays as the case that proves it.
        _write_lockfile(_check_lockfile_path(argv), {"linux-64": "abc"})
        return _fake_completed()

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        result = condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert result.stale is False


def test_check_reports_stale_true_when_the_temp_copys_content_hash_is_rewritten(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})

    def _side_effect(argv, **kwargs):
        _write_lockfile(_check_lockfile_path(argv), {"linux-64": "different"})
        return _fake_completed()

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        result = condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert result.stale is True


def test_check_happy_path_reports_engine_identity_and_returncode(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(stdout="Nothing to do.\n"),
        ),
    ):
        result = condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert result.returncode == 0
    assert result.engine_name == "conda-lock"
    assert result.engine_version == "conda-lock 4.0.2"
    assert result.stdout == "Nothing to do.\n"


# --- check(): subprocess boundary translation ---------------------------------------


def test_check_translates_timeout_expired_to_environment_check_timeout_error(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["conda-lock", "lock"], timeout=600.0),
        ),
    ):
        with pytest.raises(EnvironmentCheckTimeoutError) as excinfo:
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert excinfo.value.timeout == condalock._CONDA_LOCK_TIMEOUT_SECONDS


def test_check_removes_the_temp_copy_even_after_a_timeout(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    captured_paths: list[str] = []

    def _side_effect(argv, **kwargs):
        captured_paths.append(_check_lockfile_path(argv))
        raise subprocess.TimeoutExpired(cmd=argv, timeout=600.0)

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        with pytest.raises(EnvironmentCheckTimeoutError):
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert len(captured_paths) == 1
    assert not os.path.exists(captured_paths[0])


# --- check(): temp copy cleanup -----------------------------------------------------


def test_check_removes_the_temp_copy_after_a_current_verdict(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    captured_paths: list[str] = []

    def _side_effect(argv, **kwargs):
        path = _check_lockfile_path(argv)
        captured_paths.append(path)
        assert os.path.exists(path)
        return _fake_completed()

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert not os.path.exists(captured_paths[0])


def test_check_removes_the_temp_copy_after_a_stale_verdict(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    captured_paths: list[str] = []

    def _side_effect(argv, **kwargs):
        path = _check_lockfile_path(argv)
        captured_paths.append(path)
        _write_lockfile(path, {"linux-64": "different"})
        return _fake_completed()

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert not os.path.exists(captured_paths[0])


# --- check(): a non-zero returncode is still DATA (AD-4) -----------------------------
# Review pass, 2026-08-15: condalock.check() itself never raises for a failed child --
# cli.py's own dispatch is where a non-zero returncode now also projects to EXIT_FAILED.


def test_check_reports_a_nonzero_returncode_as_data_without_raising(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            return_value=_fake_completed(returncode=1, stdout="solver crashed\n"),
        ),
    ):
        result = condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert result.returncode == 1
    assert result.stdout == "solver crashed\n"
    # The temp copy was never rewritten by the (failed) child, so the
    # before/after hash comparison trivially reports not-stale -- this is
    # exactly why cli.py's dispatch must also inspect `returncode`.
    assert result.stale is False


# --- check(): the TOCTOU race between os.path.isfile and shutil.copyfile -------------


def test_check_translates_a_copy_race_to_lockfile_missing_error(tmp_path):
    """Review pass, 2026-08-15: `os.path.isfile()` can pass and the file can
    still vanish before `shutil.copyfile` runs -- that race must not leak a
    raw `OSError`."""
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.shutil.copyfile",
            side_effect=FileNotFoundError("vanished"),
        ) as mock_copyfile,
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
        ) as mock_run,
    ):
        with pytest.raises(EnvironmentLockfileMissingError) as excinfo:
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert excinfo.value.lockfile_path == str(lockfile)
    mock_copyfile.assert_called_once()
    mock_run.assert_not_called()


def test_check_translates_a_non_vanished_copy_failure_to_lockfile_malformed_error(tmp_path):
    """Review pass, 2026-08-15 second: the race translation above used to
    catch bare `OSError`, so an unreadable lockfile, a full `$TMPDIR`, or an
    I/O error all reported "lockfile does not exist" and prescribed `mason
    environment lock` -- a remedy that cannot help. Only `FileNotFoundError`
    means "vanished"; every other `OSError` carries the OS's own diagnostic
    into `EnvironmentLockfileMalformedError` instead. Both stay typed
    `MasonError`s (NFR-14)."""
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.shutil.copyfile",
            side_effect=PermissionError(13, "Permission denied"),
        ),
        patch("pyforge.mason.engines.condalock.subprocess.run") as mock_run,
    ):
        with pytest.raises(EnvironmentLockfileMalformedError) as excinfo:
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert excinfo.value.lockfile_path == str(lockfile)
    assert "Permission denied" in excinfo.value.reason
    mock_run.assert_not_called()


# --- check(): malformed lockfile content --------------------------------------------


def test_check_raises_lockfile_malformed_error_when_the_file_is_not_utf8(tmp_path):
    """`_read_content_hash` enumerates `UnicodeDecodeError` among the
    failures it translates, but nothing exercised that branch until this
    review pass (2026-08-15 second)."""
    lockfile = tmp_path / "conda-lock.yml"
    lockfile.write_bytes(b"metadata:\n  content_hash:\n    linux-64: \xff\xfe\n")
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch("pyforge.mason.engines.condalock.subprocess.run") as mock_run,
    ):
        with pytest.raises(EnvironmentLockfileMalformedError) as excinfo:
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert excinfo.value.lockfile_path == str(lockfile)
    mock_run.assert_not_called()


def test_check_raises_lockfile_malformed_error_when_metadata_key_missing(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    with open(lockfile, "w", encoding="utf-8") as handle:
        yaml.safe_dump({"version": 1}, handle)
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
        ) as mock_run,
    ):
        with pytest.raises(EnvironmentLockfileMalformedError) as excinfo:
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    # Names the ORIGINAL lockfile path, not the temp copy.
    assert excinfo.value.lockfile_path == str(lockfile)
    mock_run.assert_not_called()


def test_check_raises_lockfile_malformed_error_when_content_hash_key_missing(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    with open(lockfile, "w", encoding="utf-8") as handle:
        yaml.safe_dump({"metadata": {}}, handle)
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch("pyforge.mason.engines.condalock.subprocess.run") as mock_run,
    ):
        with pytest.raises(EnvironmentLockfileMalformedError):
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    mock_run.assert_not_called()


def test_check_raises_lockfile_malformed_error_when_yaml_is_invalid(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    lockfile.write_text(": this is not : valid yaml : [", encoding="utf-8")
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch("pyforge.mason.engines.condalock.subprocess.run") as mock_run,
    ):
        with pytest.raises(EnvironmentLockfileMalformedError):
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    mock_run.assert_not_called()


def test_check_raises_lockfile_malformed_error_when_file_is_empty(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    lockfile.write_text("", encoding="utf-8")
    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch("pyforge.mason.engines.condalock.subprocess.run") as mock_run,
    ):
        with pytest.raises(EnvironmentLockfileMalformedError):
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    mock_run.assert_not_called()


def test_check_raises_lockfile_malformed_error_when_the_after_read_is_malformed(tmp_path):
    """The child ran (returncode 0) but left the temp copy in a state
    `check()` cannot parse -- the after-read must translate just as
    faithfully as the before-read."""
    lockfile = tmp_path / "conda-lock.yml"
    _write_lockfile(lockfile, {"linux-64": "abc"})

    def _side_effect(argv, **kwargs):
        with open(_check_lockfile_path(argv), "w", encoding="utf-8") as handle:
            handle.write("not: [valid")
        return _fake_completed()

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.subprocess.run",
            side_effect=_side_effect,
        ),
    ):
        with pytest.raises(EnvironmentLockfileMalformedError) as excinfo:
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert excinfo.value.lockfile_path == str(lockfile)


def test_check_removes_the_temp_copy_after_a_malformed_lockfile_error(tmp_path):
    lockfile = tmp_path / "conda-lock.yml"
    with open(lockfile, "w", encoding="utf-8") as handle:
        yaml.safe_dump({"version": 1}, handle)
    captured_paths: list[str] = []

    real_mkstemp = condalock.tempfile.mkstemp

    def _capturing_mkstemp(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        captured_paths.append(path)
        return fd, path

    with (
        patch(
            "pyforge.mason.engines.condalock.require_engine",
            return_value="conda-lock 4.0.2",
        ),
        patch(
            "pyforge.mason.engines.condalock.tempfile.mkstemp",
            side_effect=_capturing_mkstemp,
        ),
    ):
        with pytest.raises(EnvironmentLockfileMalformedError):
            condalock.check(str(lockfile), _MANIFEST_PATHS)

    assert len(captured_paths) == 1
    assert not os.path.exists(captured_paths[0])
