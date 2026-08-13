"""Story 1.7 -- AD-6: `package.py` must import cleanly with no CFE anywhere
on the filesystem (`test_package_module_imports_successfully` below is the
entire test surface Story 1.7 owned for it).

Story 3.2 adds real content, `build()`, and this file's real test surface:
composing `engines.pep517.build()` and `engines.pixi.build()` into one
`models.PackageBuildResult`, comparing `wheel_version`/`conda_version` and
raising `PackageVersionMismatchError` on a real disagreement (FR-22). Both
engine adapters are mocked at their own call sites (`pyforge.mason.package.
pep517.build`/`pyforge.mason.package.pixi.build`, mirroring this suite's
"patch on the calling module's own namespace" convention -- `package.py`
does `from .engines import pep517, pixi`, binding those two module objects
directly into its own namespace) -- neither a real `pyproject-build` nor a
real `pixi` binary is needed for this file's coverage (AD-16)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pyforge.mason.engines.pep517 import Pep517BuildResult
from pyforge.mason.engines.pixi import PixiBuildResult
from pyforge.mason.errors import (
    EngineAbsentError, PackageProjectPathError, PackageVersionMismatchError,
)
from pyforge.mason.models import PackageBuildResult
from pyforge.mason.package import _versions_disagree, build


def test_package_module_imports_successfully():
    import pyforge.mason.package  # noqa: F401


_WHEEL_RESULT = Pep517BuildResult(
    returncode=0,
    wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
    sdist_path="/proj/dist/pkg-0.1.0.tar.gz",
    wheel_version="0.1.0",
    stdout="Successfully built pkg\n",
)
_CONDA_RESULT = PixiBuildResult(
    returncode=0,
    conda_path="/proj/dist-conda/pkg-0.1.0-abc123_0.conda",
    conda_version="0.1.0",
    stdout="Building pkg\n",
)


def test_build_happy_path_composes_both_engines_into_one_result(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    with patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT) as mock_pep517, \
         patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT) as mock_pixi:
        result = build(str(proj))

    mock_pep517.assert_called_once()
    mock_pixi.assert_called_once()
    assert isinstance(result, PackageBuildResult)
    assert result.target == "library"
    assert result.wheel_path == _WHEEL_RESULT.wheel_path
    assert result.sdist_path == _WHEEL_RESULT.sdist_path
    assert result.conda_path == _CONDA_RESULT.conda_path
    assert result.wheel_version == "0.1.0"
    assert result.conda_version == "0.1.0"
    assert result.pep517_returncode == 0
    assert result.pixi_returncode == 0
    assert result.pep517_stdout == _WHEEL_RESULT.stdout
    assert result.pixi_stdout == _CONDA_RESULT.stdout


def test_build_resolves_project_path_to_an_absolute_string_before_calling_either_engine(
    tmp_path, monkeypatch,
):
    """Regression (package.py's own docstring): a relative `project_path`
    combined with `cwd=project_path` on the SAME relative string would
    double up once an engine appends its own `<project_path>/dist(-conda)`
    outdir -- resolving once here, before either adapter runs, is what
    prevents that."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "proj").mkdir()

    with patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT) as mock_pep517, \
         patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT) as mock_pixi:
        result = build("proj")

    expected = str((tmp_path / "proj").resolve())
    assert mock_pep517.call_args.args[0] == expected
    assert mock_pixi.call_args.args[0] == expected
    assert result.project_path == expected


def test_build_raises_package_project_path_error_when_resolve_fails():
    """Patch 4 (review pass, 2026-08-13): `Path(project_path).expanduser().
    resolve()` itself can raise `OSError`/`ValueError` for a pathological
    input (a null byte, an unreadable parent directory hit during symlink
    resolution) -- before either engine adapter is ever called. The
    ORIGINAL caller-supplied `project_path` must name the error, since the
    resolved form was never successfully computed."""
    with patch(
        "pyforge.mason.package.Path.resolve", side_effect=OSError("Too many levels of symlinks"),
    ), patch("pyforge.mason.package.pep517.build") as mock_pep517, \
         patch("pyforge.mason.package.pixi.build") as mock_pixi:
        with pytest.raises(PackageProjectPathError) as excinfo:
            build("/some/bad/path")

    assert excinfo.value.project_path == "/some/bad/path"
    mock_pep517.assert_not_called()
    mock_pixi.assert_not_called()


def test_build_version_mismatch_raises_before_returning(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    mismatched_conda = PixiBuildResult(
        returncode=0,
        conda_path="/proj/dist-conda/pkg-0.2.0-abc123_0.conda",
        conda_version="0.2.0",
        stdout="Building pkg\n",
    )
    with patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT), \
         patch("pyforge.mason.package.pixi.build", return_value=mismatched_conda):
        with pytest.raises(PackageVersionMismatchError) as excinfo:
            build(str(proj))

    assert excinfo.value.wheel_version == "0.1.0"
    assert excinfo.value.conda_version == "0.2.0"
    assert excinfo.value.wheel_path == _WHEEL_RESULT.wheel_path
    assert excinfo.value.conda_path == mismatched_conda.conda_path


def test_build_version_mismatch_does_not_raise_for_equal_versions_in_different_formats():
    """Patch 1 (review pass, 2026-08-13): `wheel_version` is already
    PEP-440-canonicalized, but `conda_version` is the RAW `.conda` filename
    segment (`engines.pixi`'s own deliberate design) -- a raw string
    compare can false-positive on formatting differences that mean the same
    version. `packaging.version.Version("1.0.0") == Version("1.0")` (an
    implicit trailing-zero release segment), so this must NOT raise."""
    assert _versions_disagree("1.0.0", "1.0") is False
    assert _versions_disagree("1.0.0", "1.0.1") is True


def test_build_version_mismatch_falls_back_to_string_comparison_on_unparseable_version():
    """Conda version strings are not guaranteed to be strict PEP 440 -- a
    parse failure must degrade to raw string comparison, never crash the
    comparison itself."""
    assert _versions_disagree("not-a-version", "not-a-version") is False
    assert _versions_disagree("not-a-version", "also-not-a-version") is True


def test_build_does_not_raise_when_versions_are_equal_but_differently_formatted(tmp_path):
    """End-to-end proof of Patch 1 through `build()` itself: `_WHEEL_RESULT`'s
    canonicalized `"0.1.0"` and a raw `.conda` version segment of `"0.1"`
    describe the same release (an implicit trailing-zero release segment)
    and must not raise `PackageVersionMismatchError`."""
    proj = tmp_path / "proj"
    proj.mkdir()
    equivalent_conda = PixiBuildResult(
        returncode=0,
        conda_path="/proj/dist-conda/pkg-0.1-abc123_0.conda",
        conda_version="0.1",
        stdout="Building pkg\n",
    )
    with patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT), \
         patch("pyforge.mason.package.pixi.build", return_value=equivalent_conda):
        result = build(str(proj))

    assert result.wheel_version == "0.1.0"
    assert result.conda_version == "0.1"


def test_build_skips_the_mismatch_check_when_the_wheel_build_failed(tmp_path):
    """spec I/O matrix: 'One engine's build fails' reports data, never
    raises -- a `None` version on one side must never be compared."""
    proj = tmp_path / "proj"
    proj.mkdir()
    failed_wheel = Pep517BuildResult(
        returncode=1,
        wheel_path=None,
        sdist_path=None,
        wheel_version=None,
        stdout="error: build backend failed\n",
    )
    with patch("pyforge.mason.package.pep517.build", return_value=failed_wheel), \
         patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT):
        result = build(str(proj))

    assert result.wheel_version is None
    assert result.conda_version == "0.1.0"
    assert result.pep517_returncode == 1


def test_build_skips_the_mismatch_check_when_the_conda_build_failed(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    failed_conda = PixiBuildResult(
        returncode=1, conda_path=None, conda_version=None, stdout="error: recipe not found\n",
    )
    with patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT), \
         patch("pyforge.mason.package.pixi.build", return_value=failed_conda):
        result = build(str(proj))

    assert result.wheel_version == "0.1.0"
    assert result.conda_version is None
    assert result.pixi_returncode == 1


def test_build_engine_build_absent_propagates_and_never_calls_pixi(tmp_path):
    """spec I/O matrix: `build` not on PATH -> nothing built,
    `EngineAbsentError` propagates. `pep517.build()` is called first
    (package.py's own docstring documents the sequential, non-joint-gated
    ordering) -- its own `require_engine` gate raises before `pixi.build()`
    is ever reached."""
    proj = tmp_path / "proj"
    proj.mkdir()
    with patch(
        "pyforge.mason.package.pep517.build",
        side_effect=EngineAbsentError("build", "python-build"),
    ) as mock_pep517, patch("pyforge.mason.package.pixi.build") as mock_pixi:
        with pytest.raises(EngineAbsentError):
            build(str(proj))

    mock_pep517.assert_called_once()
    mock_pixi.assert_not_called()


def test_build_engine_pixi_absent_still_runs_pep517_first_but_the_error_propagates(tmp_path):
    """The reverse ordering case: `build` present, `pixi` absent --
    `pep517.build()` still runs (its own gate passed) before `pixi.build()`'s
    own gate raises; the overall command still fails with
    `EngineAbsentError` (spec I/O matrix)."""
    proj = tmp_path / "proj"
    proj.mkdir()
    with patch(
        "pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT,
    ) as mock_pep517, patch(
        "pyforge.mason.package.pixi.build",
        side_effect=EngineAbsentError("pixi", "pixi"),
    ) as mock_pixi:
        with pytest.raises(EngineAbsentError):
            build(str(proj))

    mock_pep517.assert_called_once()
    mock_pixi.assert_called_once()


def test_build_default_target_is_library(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    with patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT), \
         patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT):
        result = build(str(proj))

    assert result.target == "library"


def test_build_forwards_an_explicit_target(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    with patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT), \
         patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT):
        result = build(str(proj), target="library")

    assert result.target == "library"
