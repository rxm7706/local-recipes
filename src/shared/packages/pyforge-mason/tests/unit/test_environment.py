"""Story 1.7 -- AD-6: `environment.py` must import cleanly with no CFE
anywhere on the filesystem. `test_environment_module_imports_successfully`
below is the entire test surface Story 1.7 owned for it.

Story 4.3 adds real content, `lock()`, and this file's real test surface:
`--platform` string parsing (comma-split/strip, `None`/empty -> `()`,
empty-token dropping), and wrapping `engines.condalock.lock()`'s
`CondaLockResult` into `models.LockResult`. `condalock.lock` is mocked at
its own call site (`pyforge.mason.environment.condalock.lock`, mirroring
`test_package.py`'s "patch on the calling module's own namespace"
convention -- `environment.py` does `from .engines import condalock`,
binding that module object directly into its own namespace) -- no real
`conda-lock` binary is needed for this file's coverage (AD-16).
"""

from __future__ import annotations

from unittest.mock import patch

from pyforge.mason.engines.condalock import CondaLockResult
from pyforge.mason.environment import lock
from pyforge.mason.models import LockResult


def test_environment_module_imports_successfully():
    import pyforge.mason.environment  # noqa: F401


_CONDA_LOCK_RESULT = CondaLockResult(
    returncode=0,
    lockfile_path="/proj/conda-lock.yml",
    engine_name="conda-lock",
    engine_version="4.0.2",
    stdout="",
)


def test_lock_happy_path_wraps_conda_lock_result():
    with patch(
        "pyforge.mason.environment.condalock.lock", return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        result = lock(["environment.yml"], "/proj/conda-lock.yml")

    mock_lock.assert_called_once_with(
        ["environment.yml"], "/proj/conda-lock.yml", platforms=(),
    )
    assert isinstance(result, LockResult)
    assert result.manifest_paths == ("environment.yml",)
    assert result.output_path == "/proj/conda-lock.yml"
    assert result.platforms == ()
    assert result.engine_name == "conda-lock"
    assert result.engine_version == "4.0.2"
    assert result.returncode == 0
    assert result.stdout == ""


def test_lock_passes_multiple_manifest_paths_through_in_order():
    with patch(
        "pyforge.mason.environment.condalock.lock", return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        result = lock(["environment.yml", "pyproject.toml"], "/proj/conda-lock.yml")

    mock_lock.assert_called_once_with(
        ["environment.yml", "pyproject.toml"], "/proj/conda-lock.yml", platforms=(),
    )
    assert result.manifest_paths == ("environment.yml", "pyproject.toml")


def test_lock_splits_comma_separated_platforms():
    with patch(
        "pyforge.mason.environment.condalock.lock", return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        result = lock(["environment.yml"], "lock.yml", platforms="linux-64,osx-arm64")

    mock_lock.assert_called_once_with(
        ["environment.yml"], "lock.yml", platforms=("linux-64", "osx-arm64"),
    )
    assert result.platforms == ("linux-64", "osx-arm64")


def test_lock_strips_whitespace_around_platform_tokens():
    with patch(
        "pyforge.mason.environment.condalock.lock", return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        lock(["environment.yml"], "lock.yml", platforms=" linux-64 , osx-arm64 ")

    mock_lock.assert_called_once_with(
        ["environment.yml"], "lock.yml", platforms=("linux-64", "osx-arm64"),
    )


def test_lock_drops_empty_tokens_between_commas():
    with patch(
        "pyforge.mason.environment.condalock.lock", return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        lock(["environment.yml"], "lock.yml", platforms="linux-64,,osx-arm64")

    mock_lock.assert_called_once_with(
        ["environment.yml"], "lock.yml", platforms=("linux-64", "osx-arm64"),
    )


def test_lock_platforms_none_passes_through_as_empty_tuple():
    with patch(
        "pyforge.mason.environment.condalock.lock", return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        result = lock(["environment.yml"], "lock.yml", platforms=None)

    mock_lock.assert_called_once_with(["environment.yml"], "lock.yml", platforms=())
    assert result.platforms == ()


def test_lock_platforms_empty_string_passes_through_as_empty_tuple():
    with patch(
        "pyforge.mason.environment.condalock.lock", return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        lock(["environment.yml"], "lock.yml", platforms="")

    mock_lock.assert_called_once_with(["environment.yml"], "lock.yml", platforms=())


def test_lock_failed_solve_returncode_is_data_not_raised():
    failed = CondaLockResult(
        returncode=1,
        lockfile_path=None,
        engine_name="conda-lock",
        engine_version="4.0.2",
        stdout="conflict\n",
    )
    with patch("pyforge.mason.environment.condalock.lock", return_value=failed):
        result = lock(["environment.yml"], "lock.yml")

    assert result.returncode == 1
    assert result.engine_name == "conda-lock"
    assert result.stdout == "conflict\n"
