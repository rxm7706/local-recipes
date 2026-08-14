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
real `pixi` binary is needed for this file's coverage (AD-16).

Story 3.3 extends this file with `parse_ship_targets`/`plan_ship` coverage:
each of the three vocabulary forms parsed individually and comma-separated
together (order preserved), invalid-token and empty-channel-name rejection,
whitespace tolerance, and `plan_ship`'s dry-run plan content for all three
target kinds against a directly-constructed `PackageBuildResult` fixture --
no engine mock is needed for `plan_ship` itself (it reads an already-built
result and calls neither adapter), proven by
`test_plan_ship_calls_no_engine` below.

Story 3.4 extends this file with `ship_pypi` coverage: missing-credential-
raises-before-build, happy path, no-artifact-built, upload-failure,
structural-error propagation. Story 3.5 extends it again with `ship_channel`
coverage, mirroring `ship_pypi`'s own suite exactly in shape (both engine
adapters mocked at their own call sites, `pyforge.mason.package.pixi.upload`
for the new one, mirroring this suite's "patch on the calling module's own
namespace" convention).

Story 3.7 extends both `ship_pypi`/`ship_channel` suites with idempotence-
by-interrogation coverage: `pyforge.mason.package.pypi_index.version_exists`/
`pyforge.mason.package.pixi.search` are mocked at `package.py`'s own import
namespace (same convention). Every PRE-EXISTING happy-path/upload-failure
test in both suites now also patches the relevant interrogation call to
return `False` ("not yet shipped") so the upload path they were already
exercising still runs unmodified -- interrogation sits strictly between the
artifact-presence check and the upload call (spec Always boundary), so a
`False` there is a no-op for every test written before this story. This
file also adds `build_ship_receipt` coverage."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pyforge.mason.engines.pep517 import Pep517BuildResult
from pyforge.mason.engines.pixi import PixiBuildResult, PixiUploadResult
from pyforge.mason.engines.twine import TwineUploadResult
from pyforge.mason.errors import (
    EngineAbsentError, InvalidShipTargetError, PackageProjectPathError,
    PackageVersionMismatchError, ShipChannelCredentialMissingError, ShipCredentialMissingError,
)
from pyforge.mason.models import (
    PackageBuildResult, ShipReceipt, ShipState, ShipTarget, ShipTargetKind, ShipTargetResult,
)
from pyforge.mason.package import (
    _versions_disagree, build, build_ship_receipt, parse_ship_targets, plan_ship, ship_channel,
    ship_pypi,
)


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


# --- Story 3.3: parse_ship_targets --------------------------------------------

def test_parse_ship_targets_pypi():
    assert parse_ship_targets("pypi") == (
        ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),
    )


def test_parse_ship_targets_conda_forge():
    assert parse_ship_targets("conda-forge") == (
        ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),
    )


def test_parse_ship_targets_channel():
    assert parse_ship_targets("channel:myorg") == (
        ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),
    )


def test_parse_ship_targets_all_three_comma_separated_preserves_order():
    assert parse_ship_targets("pypi,conda-forge,channel:myorg") == (
        ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),
    )


def test_parse_ship_targets_invalid_value_raises_naming_the_original_token():
    with pytest.raises(InvalidShipTargetError) as excinfo:
        parse_ship_targets("pypi,bogus")

    assert excinfo.value.value == "bogus"
    assert "bogus" in str(excinfo.value)


def test_parse_ship_targets_rejects_empty_channel_name():
    with pytest.raises(InvalidShipTargetError) as excinfo:
        parse_ship_targets("channel:")

    assert excinfo.value.value == "channel:"


def test_parse_ship_targets_tolerates_whitespace_around_commas():
    assert parse_ship_targets("pypi, conda-forge") == (
        ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),
    )


def test_parse_ship_targets_strips_whitespace_after_channel_prefix():
    """Review pass, 2026-08-13: `"channel: myorg"`'s leading space after the
    colon must not survive into `channel_name`."""
    assert parse_ship_targets("channel: myorg") == (
        ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),
    )


@pytest.mark.parametrize("value", [",", "pypi,", ",pypi", " ", "pypi,,conda-forge"])
def test_parse_ship_targets_raises_invalid_ship_target_error_not_bare_value_error(value):
    """Review pass, 2026-08-13: an empty token (from a leading/trailing/
    doubled comma, or an all-whitespace value) must raise
    `InvalidShipTargetError` -- this function's own documented contract for
    "any other token" -- never let `InvalidShipTargetError.__init__`'s own
    empty-value guard escape as a bare `ValueError` instead."""
    with pytest.raises(InvalidShipTargetError):
        parse_ship_targets(value)


def test_parse_ship_targets_is_case_sensitive():
    with pytest.raises(InvalidShipTargetError) as excinfo:
        parse_ship_targets("PyPI")

    assert excinfo.value.value == "PyPI"


# --- Story 3.3: plan_ship ------------------------------------------------------

_PLAN_BUILD_RESULT = PackageBuildResult(
    target="library",
    project_path="/proj",
    wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
    sdist_path="/proj/dist/pkg-0.1.0.tar.gz",
    conda_path="/proj/dist-conda/pkg-0.1.0-abc123_0.conda",
    wheel_version="0.1.0",
    conda_version="0.1.0",
    pep517_returncode=0,
    pixi_returncode=0,
    pep517_stdout="",
    pixi_stdout="",
)


def test_plan_ship_all_three_kinds_are_not_attempted_with_no_reference():
    targets = (
        ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),
    )
    results = plan_ship(targets, _PLAN_BUILD_RESULT)

    assert len(results) == 3
    for result in results:
        assert isinstance(result, ShipTargetResult)
        assert result.state == ShipState.NOT_ATTEMPTED
        assert result.reference is None


def test_plan_ship_pypi_message_names_wheel_and_sdist_and_states_irreversibility():
    results = plan_ship(
        (ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),), _PLAN_BUILD_RESULT,
    )

    assert results[0].target == "pypi"
    message = results[0].message
    assert _PLAN_BUILD_RESULT.wheel_path in message
    assert _PLAN_BUILD_RESULT.sdist_path in message
    assert "irreversible" in message.lower()


def test_plan_ship_conda_forge_message_mentions_a_pull_request():
    results = plan_ship(
        (ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),), _PLAN_BUILD_RESULT,
    )

    assert results[0].target == "conda-forge"
    assert "pull request" in results[0].message.lower()


def test_plan_ship_channel_message_names_conda_path_and_channel_name():
    results = plan_ship(
        (ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),), _PLAN_BUILD_RESULT,
    )

    assert results[0].target == "channel:myorg"
    message = results[0].message
    assert _PLAN_BUILD_RESULT.conda_path in message
    assert "myorg" in message


def test_plan_ship_calls_no_engine():
    """`plan_ship()` takes an already-built `PackageBuildResult` and reads
    its fields only -- it must never call an engine adapter itself (spec
    I/O matrix: 'no subprocess/engine call occurs')."""
    targets = (
        ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),
    )
    with patch("pyforge.mason.package.pep517.build") as mock_pep517, \
         patch("pyforge.mason.package.pixi.build") as mock_pixi:
        plan_ship(targets, _PLAN_BUILD_RESULT)

    mock_pep517.assert_not_called()
    mock_pixi.assert_not_called()


def test_plan_ship_never_prints_the_literal_string_none_for_a_failed_artifact():
    """Review pass, 2026-08-13: `wheel_path`/`sdist_path`/`conda_path` are
    `str | None` -- `None` when that engine's own build failed. A bare
    `!r}` interpolation of `None` renders the misleading literal text
    `"None"` into the printed plan; this must instead read as a note that
    no artifact was built."""
    failed_build = PackageBuildResult(
        target="library",
        project_path="/proj",
        wheel_path=None,
        sdist_path=None,
        conda_path=None,
        wheel_version=None,
        conda_version=None,
        pep517_returncode=1,
        pixi_returncode=1,
        pep517_stdout="",
        pixi_stdout="",
    )
    targets = (
        ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),
    )
    results = plan_ship(targets, failed_build)

    for result in results:
        assert "None" not in result.message
        assert "no" in result.message.lower()


# --- Story 3.4: ship_pypi --------------------------------------------------

_SHIP_ENVIRON = {"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": "pypi-secret"}

_SHIP_BUILD_RESULT = PackageBuildResult(
    target="library",
    project_path="/proj",
    wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
    sdist_path="/proj/dist/pkg-0.1.0.tar.gz",
    conda_path=None,
    wheel_version="0.1.0",
    conda_version=None,
    pep517_returncode=0,
    pixi_returncode=1,
    pep517_stdout="Successfully built pkg\n",
    pixi_stdout="",
)


def test_ship_pypi_raises_before_build_or_upload_when_both_credentials_missing():
    with patch("pyforge.mason.package.build") as mock_build, \
         patch("pyforge.mason.package.twine.upload") as mock_upload:
        with pytest.raises(ShipCredentialMissingError) as excinfo:
            ship_pypi("/proj", environ={})

    assert excinfo.value.missing == ("TWINE_USERNAME", "TWINE_PASSWORD")
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_pypi_raises_naming_only_the_missing_credential():
    with patch("pyforge.mason.package.build") as mock_build, \
         patch("pyforge.mason.package.twine.upload") as mock_upload:
        with pytest.raises(ShipCredentialMissingError) as excinfo:
            ship_pypi("/proj", environ={"TWINE_USERNAME": "me"})

    assert excinfo.value.missing == ("TWINE_PASSWORD",)
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_pypi_treats_a_whitespace_only_credential_as_missing():
    with patch("pyforge.mason.package.build") as mock_build, \
         patch("pyforge.mason.package.twine.upload") as mock_upload:
        with pytest.raises(ShipCredentialMissingError) as excinfo:
            ship_pypi("/proj", environ={"TWINE_USERNAME": "   ", "TWINE_PASSWORD": "secret"})

    assert excinfo.value.missing == ("TWINE_USERNAME",)
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_pypi_happy_path_uploads_and_returns_terminal_result():
    upload_result = TwineUploadResult(
        returncode=0, url="https://pypi.org/project/pkg/0.1.0/", stdout="View at:\n...\n",
    )
    with patch(
        "pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT,
    ) as mock_build, patch(
        "pyforge.mason.package.pypi_index.version_exists", return_value=False,
    ) as mock_exists, patch(
        "pyforge.mason.package.twine.upload", return_value=upload_result,
    ) as mock_upload:
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_build.assert_called_once_with("/proj", target="library")
    mock_exists.assert_called_once_with("pkg", "0.1.0")
    mock_upload.assert_called_once_with(
        (_SHIP_BUILD_RESULT.wheel_path, _SHIP_BUILD_RESULT.sdist_path),
    )
    assert result == ShipTargetResult(
        target="pypi",
        state=ShipState.TERMINAL,
        reference="https://pypi.org/project/pkg/0.1.0/",
        message="View at:\n...\n",
    )


def test_ship_pypi_returns_failed_when_build_produces_no_wheel():
    failed_build = PackageBuildResult(
        target="library",
        project_path="/proj",
        wheel_path=None,
        sdist_path=None,
        conda_path=None,
        wheel_version=None,
        conda_version=None,
        pep517_returncode=1,
        pixi_returncode=0,
        pep517_stdout="error: build backend failed\n",
        pixi_stdout="",
    )
    with patch("pyforge.mason.package.build", return_value=failed_build), \
         patch("pyforge.mason.package.twine.upload") as mock_upload:
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_upload.assert_not_called()
    assert result == ShipTargetResult(
        target="pypi",
        state=ShipState.FAILED,
        reference=None,
        message="error: build backend failed\n",
    )


def test_ship_pypi_returns_failed_when_build_produces_a_wheel_but_no_sdist():
    """spec Always boundary: BOTH `wheel_path` and `sdist_path` must be
    non-`None` for `twine.upload` to ever be called."""
    partial_build = PackageBuildResult(
        target="library",
        project_path="/proj",
        wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
        sdist_path=None,
        conda_path=None,
        wheel_version="0.1.0",
        conda_version=None,
        pep517_returncode=0,
        pixi_returncode=0,
        pep517_stdout="only the wheel was discovered\n",
        pixi_stdout="",
    )
    with patch("pyforge.mason.package.build", return_value=partial_build), \
         patch("pyforge.mason.package.twine.upload") as mock_upload:
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_upload.assert_not_called()
    assert result.state == ShipState.FAILED
    assert result.reference is None


def test_ship_pypi_returns_failed_when_upload_returns_nonzero():
    upload_result = TwineUploadResult(returncode=1, url=None, stdout="ERROR HTTPError: 400\n")
    with patch("pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT), \
         patch("pyforge.mason.package.pypi_index.version_exists", return_value=False), \
         patch("pyforge.mason.package.twine.upload", return_value=upload_result):
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    assert result == ShipTargetResult(
        target="pypi", state=ShipState.FAILED, reference=None, message="ERROR HTTPError: 400\n",
    )


def test_ship_pypi_propagates_engine_absent_from_build():
    with patch(
        "pyforge.mason.package.build", side_effect=EngineAbsentError("build", "python-build"),
    ), patch("pyforge.mason.package.twine.upload") as mock_upload:
        with pytest.raises(EngineAbsentError):
            ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_pypi_propagates_package_version_mismatch_from_build():
    with patch(
        "pyforge.mason.package.build",
        side_effect=PackageVersionMismatchError(
            wheel_version="0.1.0",
            conda_version="0.2.0",
            wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
            conda_path="/proj/dist-conda/pkg-0.2.0-abc123_0.conda",
        ),
    ), patch("pyforge.mason.package.twine.upload") as mock_upload:
        with pytest.raises(PackageVersionMismatchError):
            ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_pypi_default_target_is_library():
    upload_result = TwineUploadResult(returncode=0, url=None, stdout="")
    with patch(
        "pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT,
    ) as mock_build, patch(
        "pyforge.mason.package.pypi_index.version_exists", return_value=False,
    ), patch("pyforge.mason.package.twine.upload", return_value=upload_result):
        ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_build.assert_called_once_with("/proj", target="library")


def test_ship_pypi_forwards_an_explicit_target():
    """A value distinct from the default proves `target` is actually
    threaded through to `build()` rather than a hardcoded literal --
    `ship_pypi` itself applies no validation of its own to `target` (that is
    `cli.py`'s `choices=("library",)` job, not wired by this story), so an
    arbitrary string is a valid probe of the plumbing alone (review pass,
    2026-08-14)."""
    upload_result = TwineUploadResult(returncode=0, url=None, stdout="")
    with patch(
        "pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT,
    ) as mock_build, patch(
        "pyforge.mason.package.pypi_index.version_exists", return_value=False,
    ), patch("pyforge.mason.package.twine.upload", return_value=upload_result):
        ship_pypi("/proj", environ=_SHIP_ENVIRON, target="not-the-default")

    mock_build.assert_called_once_with("/proj", target="not-the-default")


# --- Story 3.7: ship_pypi idempotence-by-interrogation --------------------------

def test_ship_pypi_already_shipped_skips_upload_and_returns_terminal():
    """spec I/O matrix: 'PyPI already shipped' -- version_exists -> True ->
    TERMINAL, reference = project URL; twine.upload never called."""
    with patch("pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT), \
         patch(
             "pyforge.mason.package.pypi_index.version_exists", return_value=True,
         ) as mock_exists, patch("pyforge.mason.package.twine.upload") as mock_upload:
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_exists.assert_called_once_with("pkg", "0.1.0")
    mock_upload.assert_not_called()
    assert result.target == "pypi"
    assert result.state == ShipState.TERMINAL
    assert result.reference == "https://pypi.org/project/pkg/0.1.0/"


def test_ship_pypi_undeterminable_interrogation_returns_pending_naming_the_reason():
    """spec I/O matrix: 'PyPI interrogation undeterminable' -- version_exists
    -> None -> PENDING naming the reason; twine.upload never called."""
    with patch("pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT), \
         patch(
             "pyforge.mason.package.pypi_index.version_exists", return_value=None,
         ), patch("pyforge.mason.package.twine.upload") as mock_upload:
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_upload.assert_not_called()
    assert result.target == "pypi"
    assert result.state == ShipState.PENDING
    assert result.reference is None
    assert "pkg" in result.message
    assert "0.1.0" in result.message


def test_ship_pypi_interrogation_runs_after_build_and_before_upload():
    """spec Always boundary: interrogation runs strictly AFTER build()
    (needs the built version) and BEFORE the upload call."""
    call_order = []
    with patch(
        "pyforge.mason.package.build",
        side_effect=lambda *a, **k: (call_order.append("build"), _SHIP_BUILD_RESULT)[1],
    ), patch(
        "pyforge.mason.package.pypi_index.version_exists",
        side_effect=lambda *a, **k: (call_order.append("version_exists"), False)[1],
    ), patch(
        "pyforge.mason.package.twine.upload",
        side_effect=lambda *a, **k: (
            call_order.append("upload"),
            TwineUploadResult(returncode=0, url=None, stdout=""),
        )[1],
    ):
        ship_pypi("/proj", environ=_SHIP_ENVIRON)

    assert call_order == ["build", "version_exists", "upload"]


# --- Story 3.5: ship_channel -----------------------------------------------

_SHIP_CHANNEL_ENVIRON = {"PREFIX_API_KEY": "prefix-secret"}

_SHIP_CHANNEL_BUILD_RESULT = PackageBuildResult(
    target="library",
    project_path="/proj",
    wheel_path=None,
    sdist_path=None,
    conda_path="/proj/dist-conda/pkg-0.1.0-abc123_0.conda",
    wheel_version=None,
    conda_version="0.1.0",
    pep517_returncode=1,
    pixi_returncode=0,
    pep517_stdout="",
    pixi_stdout="Building pkg\n",
)


def test_ship_channel_raises_before_build_or_upload_when_credential_missing():
    with patch("pyforge.mason.package.build") as mock_build, \
         patch("pyforge.mason.package.pixi.upload") as mock_upload:
        with pytest.raises(ShipChannelCredentialMissingError) as excinfo:
            ship_channel("/proj", "myorg", environ={})

    assert excinfo.value.missing == ("PREFIX_API_KEY",)
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_channel_treats_a_whitespace_only_credential_as_missing():
    with patch("pyforge.mason.package.build") as mock_build, \
         patch("pyforge.mason.package.pixi.upload") as mock_upload:
        with pytest.raises(ShipChannelCredentialMissingError) as excinfo:
            ship_channel("/proj", "myorg", environ={"PREFIX_API_KEY": "   "})

    assert excinfo.value.missing == ("PREFIX_API_KEY",)
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_channel_happy_path_uploads_and_returns_terminal_result():
    upload_result = PixiUploadResult(returncode=0, stdout="Uploading...\ndone\n")
    with patch(
        "pyforge.mason.package.build", return_value=_SHIP_CHANNEL_BUILD_RESULT,
    ) as mock_build, patch(
        "pyforge.mason.package.pixi.search", return_value=False,
    ) as mock_search, patch(
        "pyforge.mason.package.pixi.upload", return_value=upload_result,
    ) as mock_upload:
        result = ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_build.assert_called_once_with("/proj", target="library")
    mock_search.assert_called_once_with("pkg", "0.1.0", "myorg")
    mock_upload.assert_called_once_with(_SHIP_CHANNEL_BUILD_RESULT.conda_path, "myorg")
    assert result == ShipTargetResult(
        target="channel:myorg",
        state=ShipState.TERMINAL,
        reference="myorg",
        message="Uploading...\ndone\n",
    )


def test_ship_channel_returns_failed_when_build_produces_no_conda_artifact():
    failed_build = PackageBuildResult(
        target="library",
        project_path="/proj",
        wheel_path=None,
        sdist_path=None,
        conda_path=None,
        wheel_version=None,
        conda_version=None,
        pep517_returncode=0,
        pixi_returncode=1,
        pep517_stdout="",
        pixi_stdout="error: recipe not found\n",
    )
    with patch("pyforge.mason.package.build", return_value=failed_build), \
         patch("pyforge.mason.package.pixi.upload") as mock_upload:
        result = ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_not_called()
    assert result == ShipTargetResult(
        target="channel:myorg",
        state=ShipState.FAILED,
        reference=None,
        message="error: recipe not found\n",
    )


def test_ship_channel_returns_failed_when_upload_returns_nonzero():
    """Proves the channel-rejection path returns data, not a raised
    exception (spec Always boundary) -- `pixi.upload` WAS called, so a
    second call for a different target in the same invocation would be
    unaffected."""
    upload_result = PixiUploadResult(
        returncode=1, stdout="Error:   x no prefix.dev API key provided\n",
    )
    with patch("pyforge.mason.package.build", return_value=_SHIP_CHANNEL_BUILD_RESULT), \
         patch("pyforge.mason.package.pixi.search", return_value=False), \
         patch(
             "pyforge.mason.package.pixi.upload", return_value=upload_result,
         ) as mock_upload:
        result = ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_called_once_with(_SHIP_CHANNEL_BUILD_RESULT.conda_path, "myorg")
    assert result == ShipTargetResult(
        target="channel:myorg",
        state=ShipState.FAILED,
        reference=None,
        message="Error:   x no prefix.dev API key provided\n",
    )


def test_ship_channel_propagates_engine_absent_from_build():
    with patch(
        "pyforge.mason.package.build", side_effect=EngineAbsentError("pixi", "pixi"),
    ), patch("pyforge.mason.package.pixi.upload") as mock_upload:
        with pytest.raises(EngineAbsentError):
            ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_channel_propagates_package_version_mismatch_from_build():
    with patch(
        "pyforge.mason.package.build",
        side_effect=PackageVersionMismatchError(
            wheel_version="0.1.0",
            conda_version="0.2.0",
            wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
            conda_path="/proj/dist-conda/pkg-0.2.0-abc123_0.conda",
        ),
    ), patch("pyforge.mason.package.pixi.upload") as mock_upload:
        with pytest.raises(PackageVersionMismatchError):
            ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_channel_propagates_package_project_path_error_from_build():
    with patch(
        "pyforge.mason.package.build",
        side_effect=PackageProjectPathError(project_path="/proj", reason="boom"),
    ), patch("pyforge.mason.package.pixi.upload") as mock_upload:
        with pytest.raises(PackageProjectPathError):
            ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_channel_default_target_is_library():
    upload_result = PixiUploadResult(returncode=0, stdout="")
    with patch(
        "pyforge.mason.package.build", return_value=_SHIP_CHANNEL_BUILD_RESULT,
    ) as mock_build, patch(
        "pyforge.mason.package.pixi.search", return_value=False,
    ), patch("pyforge.mason.package.pixi.upload", return_value=upload_result):
        ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_build.assert_called_once_with("/proj", target="library")


def test_ship_channel_forwards_an_explicit_target():
    upload_result = PixiUploadResult(returncode=0, stdout="")
    with patch(
        "pyforge.mason.package.build", return_value=_SHIP_CHANNEL_BUILD_RESULT,
    ) as mock_build, patch(
        "pyforge.mason.package.pixi.search", return_value=False,
    ), patch("pyforge.mason.package.pixi.upload", return_value=upload_result):
        ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON, target="not-the-default")

    mock_build.assert_called_once_with("/proj", target="not-the-default")


# --- Story 3.7: ship_channel idempotence-by-interrogation -----------------------

def test_ship_channel_already_shipped_skips_upload_and_returns_terminal():
    """spec I/O matrix: 'Channel already shipped' -- pixi.search -> True ->
    TERMINAL, reference = channel_name; pixi.upload never called."""
    with patch("pyforge.mason.package.build", return_value=_SHIP_CHANNEL_BUILD_RESULT), \
         patch(
             "pyforge.mason.package.pixi.search", return_value=True,
         ) as mock_search, patch("pyforge.mason.package.pixi.upload") as mock_upload:
        result = ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_search.assert_called_once_with("pkg", "0.1.0", "myorg")
    mock_upload.assert_not_called()
    assert result.target == "channel:myorg"
    assert result.state == ShipState.TERMINAL
    assert result.reference == "myorg"


def test_ship_channel_undeterminable_interrogation_returns_pending_naming_the_reason():
    """spec I/O matrix: 'Channel interrogation undeterminable' -- pixi.search
    -> None -> PENDING naming the reason; pixi.upload never called."""
    with patch("pyforge.mason.package.build", return_value=_SHIP_CHANNEL_BUILD_RESULT), \
         patch(
             "pyforge.mason.package.pixi.search", return_value=None,
         ), patch("pyforge.mason.package.pixi.upload") as mock_upload:
        result = ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_not_called()
    assert result.target == "channel:myorg"
    assert result.state == ShipState.PENDING
    assert result.reference is None
    assert "myorg" in result.message


def test_ship_channel_interrogation_runs_after_build_and_before_upload():
    """spec Always boundary: interrogation runs strictly AFTER build() (needs
    the built version) and BEFORE the upload call."""
    call_order = []
    with patch(
        "pyforge.mason.package.build",
        side_effect=lambda *a, **k: (call_order.append("build"), _SHIP_CHANNEL_BUILD_RESULT)[1],
    ), patch(
        "pyforge.mason.package.pixi.search",
        side_effect=lambda *a, **k: (call_order.append("search"), False)[1],
    ), patch(
        "pyforge.mason.package.pixi.upload",
        side_effect=lambda *a, **k: (
            call_order.append("upload"), PixiUploadResult(returncode=0, stdout=""),
        )[1],
    ):
        ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    assert call_order == ["build", "search", "upload"]


# --- Story 3.7: build_ship_receipt -----------------------------------------------

_TERMINAL_PYPI = ShipTargetResult(
    target="pypi", state=ShipState.TERMINAL, reference="https://pypi.org/project/pkg/0.1.0/",
    message="View at:\n...\n",
)
_PENDING_CHANNEL = ShipTargetResult(
    target="channel:myorg", state=ShipState.PENDING, reference=None,
    message="could not determine whether channel already has pkg 0.1.0",
)
_FAILED_PYPI = ShipTargetResult(
    target="pypi", state=ShipState.FAILED, reference=None, message="ERROR HTTPError: 400\n",
)
_NOT_ATTEMPTED_CONDA_FORGE = ShipTargetResult(
    target="conda-forge", state=ShipState.NOT_ATTEMPTED, reference=None, message=None,
)


def test_build_ship_receipt_every_target_carries_its_own_state_and_reference():
    """spec AC1: 'every target carries an explicit state and reference'."""
    receipt = build_ship_receipt((_TERMINAL_PYPI, _PENDING_CHANNEL))

    assert isinstance(receipt, ShipReceipt)
    assert receipt.targets == (_TERMINAL_PYPI, _PENDING_CHANNEL)
    for target in receipt.targets:
        assert target.state is not None
        # `reference` may legitimately be None (spec: "or None when nothing
        # concrete exists yet") -- the field must simply be PRESENT, which
        # a frozen dataclass with no defaults already guarantees.


def test_build_ship_receipt_mixed_terminal_and_pending_is_ok():
    """spec I/O matrix: 'Receipt aggregate, mixed success' -- targets =
    (TERMINAL, PENDING) -> ShipReceipt.ok is True."""
    receipt = build_ship_receipt((_TERMINAL_PYPI, _PENDING_CHANNEL))

    assert receipt.ok is True


def test_build_ship_receipt_any_failure_makes_ok_false():
    """spec I/O matrix: 'Receipt aggregate, one failure' -- targets =
    (TERMINAL, FAILED) -> ShipReceipt.ok is False. AC1: 'ok is False iff any
    target is FAILED'."""
    receipt = build_ship_receipt((_TERMINAL_PYPI, _FAILED_PYPI))

    assert receipt.ok is False


def test_build_ship_receipt_not_attempted_alone_is_ok():
    receipt = build_ship_receipt((_NOT_ATTEMPTED_CONDA_FORGE,))

    assert receipt.ok is True


def test_build_ship_receipt_all_four_states_ok_iff_no_failure():
    all_but_failed = (_TERMINAL_PYPI, _PENDING_CHANNEL, _NOT_ATTEMPTED_CONDA_FORGE)
    assert build_ship_receipt(all_but_failed).ok is True

    with_failed = (*all_but_failed, _FAILED_PYPI)
    assert build_ship_receipt(with_failed).ok is False


def test_build_ship_receipt_empty_results_is_vacuously_ok():
    receipt = build_ship_receipt(())

    assert receipt.targets == ()
    assert receipt.ok is True


def test_build_ship_receipt_preserves_order_and_does_not_deduplicate():
    receipt = build_ship_receipt((_TERMINAL_PYPI, _TERMINAL_PYPI, _PENDING_CHANNEL))

    assert receipt.targets == (_TERMINAL_PYPI, _TERMINAL_PYPI, _PENDING_CHANNEL)


def test_build_ship_receipt_calls_no_engine():
    """`build_ship_receipt` reads already-built `ShipTargetResult`s only --
    it must never call an engine adapter or another ship function itself."""
    with patch("pyforge.mason.package.build") as mock_build, \
         patch("pyforge.mason.package.pep517.build") as mock_pep517, \
         patch("pyforge.mason.package.pixi.build") as mock_pixi:
        build_ship_receipt((_TERMINAL_PYPI, _FAILED_PYPI))

    mock_build.assert_not_called()
    mock_pep517.assert_not_called()
    mock_pixi.assert_not_called()
