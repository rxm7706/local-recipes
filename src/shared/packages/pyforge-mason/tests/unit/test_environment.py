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

Story 4.4 adds `check()`'s own coverage below, mirroring `lock()`'s test
section exactly: the same `--platform` parsing cases (not re-derived, since
`check()`'s own parsing is verbatim-mirrored from `lock()`), plus wrapping
`engines.condalock.check()`'s `CondaLockCheckResult` into `models.
CheckResult`, including `stale` passthrough. `condalock.check` is mocked the
same way, at `pyforge.mason.environment.condalock.check`.

Story 4.2 adds `discover_manifests()`'s own coverage below, mirroring
`test_resolve.py`'s style for this codebase's other pure directory-walking
function: real `tmp_path` trees, no mocking -- this function does no
subprocess/engine work, so there is nothing to patch.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pyforge.mason.engines.condalock import CondaLockCheckResult, CondaLockResult
from pyforge.mason.environment import check, discover_manifests, lock
from pyforge.mason.errors import EnvironmentManifestsNotFoundError
from pyforge.mason.models import CheckResult, LockResult


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
        "pyforge.mason.environment.condalock.lock",
        return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        result = lock(["environment.yml"], "/proj/conda-lock.yml")

    mock_lock.assert_called_once_with(
        ["environment.yml"],
        "/proj/conda-lock.yml",
        platforms=(),
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
        "pyforge.mason.environment.condalock.lock",
        return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        result = lock(["environment.yml", "pyproject.toml"], "/proj/conda-lock.yml")

    mock_lock.assert_called_once_with(
        ["environment.yml", "pyproject.toml"],
        "/proj/conda-lock.yml",
        platforms=(),
    )
    assert result.manifest_paths == ("environment.yml", "pyproject.toml")


def test_lock_splits_comma_separated_platforms():
    with patch(
        "pyforge.mason.environment.condalock.lock",
        return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        result = lock(["environment.yml"], "lock.yml", platforms="linux-64,osx-arm64")

    mock_lock.assert_called_once_with(
        ["environment.yml"],
        "lock.yml",
        platforms=("linux-64", "osx-arm64"),
    )
    assert result.platforms == ("linux-64", "osx-arm64")


def test_lock_strips_whitespace_around_platform_tokens():
    with patch(
        "pyforge.mason.environment.condalock.lock",
        return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        lock(["environment.yml"], "lock.yml", platforms=" linux-64 , osx-arm64 ")

    mock_lock.assert_called_once_with(
        ["environment.yml"],
        "lock.yml",
        platforms=("linux-64", "osx-arm64"),
    )


def test_lock_drops_empty_tokens_between_commas():
    with patch(
        "pyforge.mason.environment.condalock.lock",
        return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        lock(["environment.yml"], "lock.yml", platforms="linux-64,,osx-arm64")

    mock_lock.assert_called_once_with(
        ["environment.yml"],
        "lock.yml",
        platforms=("linux-64", "osx-arm64"),
    )


def test_lock_platforms_none_passes_through_as_empty_tuple():
    with patch(
        "pyforge.mason.environment.condalock.lock",
        return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        result = lock(["environment.yml"], "lock.yml", platforms=None)

    mock_lock.assert_called_once_with(["environment.yml"], "lock.yml", platforms=())
    assert result.platforms == ()


def test_lock_platforms_empty_string_passes_through_as_empty_tuple():
    with patch(
        "pyforge.mason.environment.condalock.lock",
        return_value=_CONDA_LOCK_RESULT,
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


_CONDA_LOCK_CHECK_RESULT_CURRENT = CondaLockCheckResult(
    stale=False,
    returncode=0,
    engine_name="conda-lock",
    engine_version="4.0.2",
    stdout="",
)


def test_check_happy_path_wraps_conda_lock_check_result():
    with patch(
        "pyforge.mason.environment.condalock.check",
        return_value=_CONDA_LOCK_CHECK_RESULT_CURRENT,
    ) as mock_check:
        result = check("/proj/conda-lock.yml", ["environment.yml"])

    mock_check.assert_called_once_with(
        "/proj/conda-lock.yml",
        ["environment.yml"],
        platforms=(),
    )
    assert isinstance(result, CheckResult)
    assert result.lockfile_path == "/proj/conda-lock.yml"
    assert result.manifest_paths == ("environment.yml",)
    assert result.platforms == ()
    assert result.stale is False
    assert result.engine_name == "conda-lock"
    assert result.engine_version == "4.0.2"
    assert result.returncode == 0
    assert result.stdout == ""


def test_check_stale_true_passes_through():
    stale = CondaLockCheckResult(
        stale=True,
        returncode=0,
        engine_name="conda-lock",
        engine_version="4.0.2",
        stdout="",
    )
    with patch("pyforge.mason.environment.condalock.check", return_value=stale):
        result = check("/proj/conda-lock.yml", ["environment.yml"])

    assert result.stale is True


def test_check_passes_multiple_manifest_paths_through_in_order():
    with patch(
        "pyforge.mason.environment.condalock.check",
        return_value=_CONDA_LOCK_CHECK_RESULT_CURRENT,
    ) as mock_check:
        result = check("lock.yml", ["environment.yml", "pyproject.toml"])

    mock_check.assert_called_once_with(
        "lock.yml",
        ["environment.yml", "pyproject.toml"],
        platforms=(),
    )
    assert result.manifest_paths == ("environment.yml", "pyproject.toml")


def test_check_splits_comma_separated_platforms():
    with patch(
        "pyforge.mason.environment.condalock.check",
        return_value=_CONDA_LOCK_CHECK_RESULT_CURRENT,
    ) as mock_check:
        result = check("lock.yml", ["environment.yml"], platforms="linux-64,osx-arm64")

    mock_check.assert_called_once_with(
        "lock.yml",
        ["environment.yml"],
        platforms=("linux-64", "osx-arm64"),
    )
    assert result.platforms == ("linux-64", "osx-arm64")


def test_check_strips_whitespace_around_platform_tokens():
    with patch(
        "pyforge.mason.environment.condalock.check",
        return_value=_CONDA_LOCK_CHECK_RESULT_CURRENT,
    ) as mock_check:
        check("lock.yml", ["environment.yml"], platforms=" linux-64 , osx-arm64 ")

    mock_check.assert_called_once_with(
        "lock.yml",
        ["environment.yml"],
        platforms=("linux-64", "osx-arm64"),
    )


def test_check_drops_empty_tokens_between_commas():
    with patch(
        "pyforge.mason.environment.condalock.check",
        return_value=_CONDA_LOCK_CHECK_RESULT_CURRENT,
    ) as mock_check:
        check("lock.yml", ["environment.yml"], platforms="linux-64,,osx-arm64")

    mock_check.assert_called_once_with(
        "lock.yml",
        ["environment.yml"],
        platforms=("linux-64", "osx-arm64"),
    )


def test_check_platforms_none_passes_through_as_empty_tuple():
    with patch(
        "pyforge.mason.environment.condalock.check",
        return_value=_CONDA_LOCK_CHECK_RESULT_CURRENT,
    ) as mock_check:
        result = check("lock.yml", ["environment.yml"], platforms=None)

    mock_check.assert_called_once_with("lock.yml", ["environment.yml"], platforms=())
    assert result.platforms == ()


def test_check_platforms_empty_string_passes_through_as_empty_tuple():
    with patch(
        "pyforge.mason.environment.condalock.check",
        return_value=_CONDA_LOCK_CHECK_RESULT_CURRENT,
    ) as mock_check:
        check("lock.yml", ["environment.yml"], platforms="")

    mock_check.assert_called_once_with("lock.yml", ["environment.yml"], platforms=())


# --- Story 4.2: discover_manifests -- I/O & Edge-Case Matrix ----------------


def test_discover_manifests_all_four_kinds_present(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "environment.yml").write_text("")
    (tmp_path / "requirements.txt").write_text("")
    (tmp_path / "pixi.toml").write_text("")

    result = discover_manifests(tmp_path)

    assert result == (
        str(tmp_path / "pyproject.toml"),
        str(tmp_path / "environment.yml"),
        str(tmp_path / "requirements.txt"),
        str(tmp_path / "pixi.toml"),
    )


def test_discover_manifests_subset_present_returns_a_one_element_tuple(tmp_path):
    (tmp_path / "pixi.toml").write_text("")

    result = discover_manifests(tmp_path)

    assert result == (str(tmp_path / "pixi.toml"),)


def test_discover_manifests_multiple_requirements_files_sorted_lexically(tmp_path):
    """Both `requirements*.txt` matches are returned, sorted lexically, and
    positioned between `environment.yml` and `pixi.toml` (spec I/O matrix)."""
    (tmp_path / "environment.yml").write_text("")
    (tmp_path / "requirements.txt").write_text("")
    (tmp_path / "requirements-dev.txt").write_text("")
    (tmp_path / "pixi.toml").write_text("")

    result = discover_manifests(tmp_path)

    assert result == (
        str(tmp_path / "environment.yml"),
        str(tmp_path / "requirements-dev.txt"),
        str(tmp_path / "requirements.txt"),
        str(tmp_path / "pixi.toml"),
    )


def test_discover_manifests_ignores_a_directory_matching_the_requirements_glob(tmp_path):
    """A directory (or symlink-to-directory) whose name matches
    `requirements*.txt` is excluded, not silently treated as a manifest
    (review pass, 2026-08-15) -- `.is_file()` applies to every match, not
    just the three literal names."""
    (tmp_path / "requirements-lock.txt").mkdir()
    (tmp_path / "pixi.toml").write_text("")

    result = discover_manifests(tmp_path)

    assert result == (str(tmp_path / "pixi.toml"),)


def test_discover_manifests_empty_directory_raises(tmp_path):
    with pytest.raises(EnvironmentManifestsNotFoundError) as exc_info:
        discover_manifests(tmp_path)

    exc = exc_info.value
    assert exc.directory == str(tmp_path)
    assert exc.filenames == (
        "pyproject.toml",
        "environment.yml",
        "requirements*.txt",
        "pixi.toml",
    )


def test_discover_manifests_ignores_unrelated_files(tmp_path):
    (tmp_path / "pixi.toml").write_text("")
    (tmp_path / "README.md").write_text("")
    (tmp_path / "setup.py").write_text("")

    result = discover_manifests(tmp_path)

    assert result == (str(tmp_path / "pixi.toml"),)
