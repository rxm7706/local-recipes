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

Story 3.6 extends this file with `ship_conda_forge` coverage: no-recipe-path
raises before any resolution, CFE-root-unresolved raises, wrong-location
raises naming both paths with no CFE subprocess spawned, a pathological
`Path.resolve()` failure returns `FAILED` data rather than raising, a
mocked happy path, and a real end-to-end test against the `fake_cfe_root`
fixture (AD-16, no mocking) mirroring `test_recipe.py`'s own
`test_submit_against_fake_cfe_root_returns_the_fixtures_canned_success`.
`resolve_cfe_root` is patched on `pyforge.mason.package`'s own namespace
(`from .resolve import resolve_cfe_root` binds the name directly there,
mirroring `doctor.py`'s identical precedent); `recipe.submit` is patched on
`pyforge.mason.recipe`'s own namespace, since `package.py` does `from .
import recipe` (lazy) and calls `recipe.submit(...)` -- an attribute lookup
at call time, the same `cfe.probe_import_floor` gotcha `test_doctor.py`
documents for `doctor.py`'s own lazy `cfe` import.

Story 3.7 extends both `ship_pypi`/`ship_channel` suites with idempotence-
by-interrogation coverage: `pyforge.mason.package.pypi_index.version_exists`/
`pyforge.mason.package.pixi.search` are mocked at `package.py`'s own import
namespace (same convention). Every PRE-EXISTING happy-path/upload-failure
test in both suites now also patches the relevant interrogation call to
return `False` ("not yet shipped") so the upload path they were already
exercising still runs unmodified -- interrogation sits strictly between the
artifact-presence check and the upload call (spec Always boundary), so a
`False` there is a no-op for every test written before this story. This
file also adds `build_ship_receipt` coverage.

Story 3.9 extends this file three ways: `parse_ship_targets`/`plan_ship`
gain `pypi-test` coverage (mirroring the existing `pypi`/`conda-forge`/
`channel` shapes exactly); `ship_pypi` gains `repository_url` coverage
(the `"pypi"` vs `"pypi-test"` canonical-target split, and forwarding to a
mocked `twine.upload`); and the new `ship()` dispatcher gets its own test
block covering every I/O-matrix row from the story spec, including the
FR-24/FR-50/AD-26 rehearsal gate -- `ship_pypi`/`ship_channel`/
`ship_conda_forge` are all mocked at their own `pyforge.mason.package.*`
call sites (this suite's established "patch on the calling module's own
namespace" convention) so `ship()`'s own dispatch/gating logic is proven
independent of any one target's real behavior."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.mason.engines.pep517 import Pep517BuildResult
from pyforge.mason.engines.pixi import PixiBuildResult, PixiUploadResult
from pyforge.mason.engines.twine import TwineUploadResult
from pyforge.mason.errors import (
    CfeUnresolvedError,
    EngineAbsentError,
    InvalidShipTargetError,
    PackageProjectPathError,
    PackageVersionMismatchError,
    ShipChannelCredentialMissingError,
    ShipCondaForgeRecipeLocationError,
    ShipCondaForgeRecipeMissingError,
    ShipCredentialMissingError,
)
from pyforge.mason.models import (
    PackageBuildResult,
    ShipReceipt,
    ShipState,
    ShipTarget,
    ShipTargetKind,
    ShipTargetResult,
)
from pyforge.mason.package import (
    _TESTPYPI_REPOSITORY_URL,
    _versions_disagree,
    build,
    build_ship_receipt,
    parse_ship_targets,
    plan_ship,
    ship,
    ship_channel,
    ship_conda_forge,
    ship_pypi,
)
from pyforge.mason.resolve import STEP_CWD_WALK, STEP_FLAG, STEP_NOT_FOUND, ResolvedCfeRoot


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
    with (
        patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT) as mock_pep517,
        patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT) as mock_pixi,
    ):
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
    tmp_path,
    monkeypatch,
):
    """Regression (package.py's own docstring): a relative `project_path`
    combined with `cwd=project_path` on the SAME relative string would
    double up once an engine appends its own `<project_path>/dist(-conda)`
    outdir -- resolving once here, before either adapter runs, is what
    prevents that."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "proj").mkdir()

    with (
        patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT) as mock_pep517,
        patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT) as mock_pixi,
    ):
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
    with (
        patch(
            "pyforge.mason.package.Path.resolve",
            side_effect=OSError("Too many levels of symlinks"),
        ),
        patch("pyforge.mason.package.pep517.build") as mock_pep517,
        patch("pyforge.mason.package.pixi.build") as mock_pixi,
    ):
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
    with (
        patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT),
        patch("pyforge.mason.package.pixi.build", return_value=mismatched_conda),
    ):
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
    with (
        patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT),
        patch("pyforge.mason.package.pixi.build", return_value=equivalent_conda),
    ):
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
    with (
        patch("pyforge.mason.package.pep517.build", return_value=failed_wheel),
        patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT),
    ):
        result = build(str(proj))

    assert result.wheel_version is None
    assert result.conda_version == "0.1.0"
    assert result.pep517_returncode == 1


def test_build_skips_the_mismatch_check_when_the_conda_build_failed(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    failed_conda = PixiBuildResult(
        returncode=1,
        conda_path=None,
        conda_version=None,
        stdout="error: recipe not found\n",
    )
    with (
        patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT),
        patch("pyforge.mason.package.pixi.build", return_value=failed_conda),
    ):
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
    with (
        patch(
            "pyforge.mason.package.pep517.build",
            side_effect=EngineAbsentError("build", "python-build"),
        ) as mock_pep517,
        patch("pyforge.mason.package.pixi.build") as mock_pixi,
    ):
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
    with (
        patch(
            "pyforge.mason.package.pep517.build",
            return_value=_WHEEL_RESULT,
        ) as mock_pep517,
        patch(
            "pyforge.mason.package.pixi.build",
            side_effect=EngineAbsentError("pixi", "pixi"),
        ) as mock_pixi,
    ):
        with pytest.raises(EngineAbsentError):
            build(str(proj))

    mock_pep517.assert_called_once()
    mock_pixi.assert_called_once()


def test_build_default_target_is_library(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    with (
        patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT),
        patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT),
    ):
        result = build(str(proj))

    assert result.target == "library"


def test_build_forwards_an_explicit_target(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    with (
        patch("pyforge.mason.package.pep517.build", return_value=_WHEEL_RESULT),
        patch("pyforge.mason.package.pixi.build", return_value=_CONDA_RESULT),
    ):
        result = build(str(proj), target="library")

    assert result.target == "library"


# --- Story 3.3: parse_ship_targets --------------------------------------------


def test_parse_ship_targets_pypi():
    assert parse_ship_targets("pypi") == (ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),)


def test_parse_ship_targets_pypi_test():
    """Story 3.9/FR-50: `"pypi-test"` mirrors `"pypi"`'s own bare-literal
    handling exactly -- no prefix, no dedup."""
    assert parse_ship_targets("pypi-test") == (ShipTarget(kind=ShipTargetKind.PYPI_TEST, channel_name=None),)


def test_parse_ship_targets_conda_forge():
    assert parse_ship_targets("conda-forge") == (ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),)


def test_parse_ship_targets_channel():
    assert parse_ship_targets("channel:myorg") == (ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),)


def test_parse_ship_targets_all_three_comma_separated_preserves_order():
    assert parse_ship_targets("pypi,conda-forge,channel:myorg") == (
        ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),
    )


def test_parse_ship_targets_all_four_comma_separated_preserves_order():
    """Story 3.9: `pypi-test` joins the comma-separated vocabulary,
    no-reordering precedent unchanged."""
    assert parse_ship_targets("pypi-test,pypi,conda-forge,channel:myorg") == (
        ShipTarget(kind=ShipTargetKind.PYPI_TEST, channel_name=None),
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
    assert parse_ship_targets("channel: myorg") == (ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),)


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


def test_plan_ship_all_four_kinds_are_not_attempted_with_no_reference():
    """Story 3.9 widens this from three targets to four -- `PYPI_TEST`
    joins the vocabulary."""
    targets = (
        ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),
        ShipTarget(kind=ShipTargetKind.PYPI_TEST, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),
        ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),
    )
    results = plan_ship(targets, _PLAN_BUILD_RESULT)

    assert len(results) == 4
    for result in results:
        assert isinstance(result, ShipTargetResult)
        assert result.state == ShipState.NOT_ATTEMPTED
        assert result.reference is None


def test_plan_ship_pypi_message_names_wheel_and_sdist_and_states_irreversibility():
    results = plan_ship(
        (ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None),),
        _PLAN_BUILD_RESULT,
    )

    assert results[0].target == "pypi"
    message = results[0].message
    assert _PLAN_BUILD_RESULT.wheel_path in message
    assert _PLAN_BUILD_RESULT.sdist_path in message
    assert "irreversible" in message.lower()


def test_plan_ship_pypi_test_message_names_wheel_and_sdist_but_never_claims_irreversibility():
    """Story 3.9/FR-50: the `pypi-test` plan message names the same two
    artifacts as `pypi`'s own message, states the destination is TestPyPI,
    but NEVER claims irreversibility -- that claim stays exclusive to the
    real `pypi` target."""
    results = plan_ship(
        (ShipTarget(kind=ShipTargetKind.PYPI_TEST, channel_name=None),),
        _PLAN_BUILD_RESULT,
    )

    assert results[0].target == "pypi-test"
    message = results[0].message
    assert _PLAN_BUILD_RESULT.wheel_path in message
    assert _PLAN_BUILD_RESULT.sdist_path in message
    assert "testpypi" in message.lower()
    assert "irreversible" not in message.lower()


def test_plan_ship_conda_forge_message_mentions_a_pull_request():
    results = plan_ship(
        (ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None),),
        _PLAN_BUILD_RESULT,
    )

    assert results[0].target == "conda-forge"
    assert "pull request" in results[0].message.lower()


def test_plan_ship_channel_message_names_conda_path_and_channel_name():
    results = plan_ship(
        (ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg"),),
        _PLAN_BUILD_RESULT,
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
    with (
        patch("pyforge.mason.package.pep517.build") as mock_pep517,
        patch("pyforge.mason.package.pixi.build") as mock_pixi,
    ):
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
    with patch("pyforge.mason.package.build") as mock_build, patch("pyforge.mason.package.twine.upload") as mock_upload:
        with pytest.raises(ShipCredentialMissingError) as excinfo:
            ship_pypi("/proj", environ={})

    assert excinfo.value.missing == ("TWINE_USERNAME", "TWINE_PASSWORD")
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_pypi_raises_naming_only_the_missing_credential():
    with patch("pyforge.mason.package.build") as mock_build, patch("pyforge.mason.package.twine.upload") as mock_upload:
        with pytest.raises(ShipCredentialMissingError) as excinfo:
            ship_pypi("/proj", environ={"TWINE_USERNAME": "me"})

    assert excinfo.value.missing == ("TWINE_PASSWORD",)
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_pypi_treats_a_whitespace_only_credential_as_missing():
    with patch("pyforge.mason.package.build") as mock_build, patch("pyforge.mason.package.twine.upload") as mock_upload:
        with pytest.raises(ShipCredentialMissingError) as excinfo:
            ship_pypi("/proj", environ={"TWINE_USERNAME": "   ", "TWINE_PASSWORD": "secret"})

    assert excinfo.value.missing == ("TWINE_USERNAME",)
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_pypi_happy_path_uploads_and_returns_terminal_result():
    upload_result = TwineUploadResult(
        returncode=0,
        url="https://pypi.org/project/pkg/0.1.0/",
        stdout="View at:\n...\n",
    )
    with (
        patch(
            "pyforge.mason.package.build",
            return_value=_SHIP_BUILD_RESULT,
        ) as mock_build,
        patch(
            "pyforge.mason.package.pypi_index.version_exists",
            return_value=False,
        ) as mock_exists,
        patch(
            "pyforge.mason.package.twine.upload",
            return_value=upload_result,
        ) as mock_upload,
    ):
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_build.assert_called_once_with("/proj", target="library")
    mock_exists.assert_called_once_with("pkg", "0.1.0")
    mock_upload.assert_called_once_with(
        (_SHIP_BUILD_RESULT.wheel_path, _SHIP_BUILD_RESULT.sdist_path),
        repository_url=None,
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
    with (
        patch("pyforge.mason.package.build", return_value=failed_build),
        patch("pyforge.mason.package.twine.upload") as mock_upload,
    ):
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
    with (
        patch("pyforge.mason.package.build", return_value=partial_build),
        patch("pyforge.mason.package.twine.upload") as mock_upload,
    ):
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_upload.assert_not_called()
    assert result.state == ShipState.FAILED
    assert result.reference is None


def test_ship_pypi_returns_failed_when_upload_returns_nonzero():
    upload_result = TwineUploadResult(returncode=1, url=None, stdout="ERROR HTTPError: 400\n")
    with (
        patch("pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT),
        patch("pyforge.mason.package.pypi_index.version_exists", return_value=False),
        patch("pyforge.mason.package.twine.upload", return_value=upload_result),
    ):
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    assert result == ShipTargetResult(
        target="pypi",
        state=ShipState.FAILED,
        reference=None,
        message="ERROR HTTPError: 400\n",
    )


def test_ship_pypi_propagates_engine_absent_from_build():
    with (
        patch(
            "pyforge.mason.package.build",
            side_effect=EngineAbsentError("build", "python-build"),
        ),
        patch("pyforge.mason.package.twine.upload") as mock_upload,
    ):
        with pytest.raises(EngineAbsentError):
            ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_pypi_propagates_package_version_mismatch_from_build():
    with (
        patch(
            "pyforge.mason.package.build",
            side_effect=PackageVersionMismatchError(
                wheel_version="0.1.0",
                conda_version="0.2.0",
                wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
                conda_path="/proj/dist-conda/pkg-0.2.0-abc123_0.conda",
            ),
        ),
        patch("pyforge.mason.package.twine.upload") as mock_upload,
    ):
        with pytest.raises(PackageVersionMismatchError):
            ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_pypi_default_target_is_library():
    upload_result = TwineUploadResult(returncode=0, url=None, stdout="")
    with (
        patch(
            "pyforge.mason.package.build",
            return_value=_SHIP_BUILD_RESULT,
        ) as mock_build,
        patch(
            "pyforge.mason.package.pypi_index.version_exists",
            return_value=False,
        ),
        patch("pyforge.mason.package.twine.upload", return_value=upload_result),
    ):
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
    with (
        patch(
            "pyforge.mason.package.build",
            return_value=_SHIP_BUILD_RESULT,
        ) as mock_build,
        patch(
            "pyforge.mason.package.pypi_index.version_exists",
            return_value=False,
        ),
        patch("pyforge.mason.package.twine.upload", return_value=upload_result),
    ):
        ship_pypi("/proj", environ=_SHIP_ENVIRON, target="not-the-default")

    mock_build.assert_called_once_with("/proj", target="not-the-default")


# --- Story 3.7: ship_pypi idempotence-by-interrogation --------------------------


def test_ship_pypi_already_shipped_skips_upload_and_returns_terminal():
    """spec I/O matrix: 'PyPI already shipped' -- version_exists -> True ->
    TERMINAL, reference = project URL; twine.upload never called."""
    with (
        patch("pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT),
        patch(
            "pyforge.mason.package.pypi_index.version_exists",
            return_value=True,
        ) as mock_exists,
        patch("pyforge.mason.package.twine.upload") as mock_upload,
    ):
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON)

    mock_exists.assert_called_once_with("pkg", "0.1.0")
    mock_upload.assert_not_called()
    assert result.target == "pypi"
    assert result.state == ShipState.TERMINAL
    assert result.reference == "https://pypi.org/project/pkg/0.1.0/"


def test_ship_pypi_undeterminable_interrogation_returns_pending_naming_the_reason():
    """spec I/O matrix: 'PyPI interrogation undeterminable' -- version_exists
    -> None -> PENDING naming the reason; twine.upload never called."""
    with (
        patch("pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT),
        patch(
            "pyforge.mason.package.pypi_index.version_exists",
            return_value=None,
        ),
        patch("pyforge.mason.package.twine.upload") as mock_upload,
    ):
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
    with (
        patch(
            "pyforge.mason.package.build",
            side_effect=lambda *a, **k: (call_order.append("build"), _SHIP_BUILD_RESULT)[1],
        ),
        patch(
            "pyforge.mason.package.pypi_index.version_exists",
            side_effect=lambda *a, **k: (call_order.append("version_exists"), False)[1],
        ),
        patch(
            "pyforge.mason.package.twine.upload",
            side_effect=lambda *a, **k: (
                call_order.append("upload"),
                TwineUploadResult(returncode=0, url=None, stdout=""),
            )[1],
        ),
    ):
        ship_pypi("/proj", environ=_SHIP_ENVIRON)

    assert call_order == ["build", "version_exists", "upload"]


# --- Story 3.9: ship_pypi's repository_url (TestPyPI rehearsal) ------------

_TESTPYPI_URL = "https://test.pypi.org/legacy/"


def test_ship_pypi_repository_url_sets_target_pypi_test_on_the_terminal_result():
    upload_result = TwineUploadResult(
        returncode=0,
        url="https://test.pypi.org/project/pkg/0.1.0/",
        stdout="View at:\n...\n",
    )
    with (
        patch("pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT),
        patch(
            "pyforge.mason.package.twine.upload",
            return_value=upload_result,
        ) as mock_upload,
    ):
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON, repository_url=_TESTPYPI_URL)

    mock_upload.assert_called_once_with(
        (_SHIP_BUILD_RESULT.wheel_path, _SHIP_BUILD_RESULT.sdist_path),
        repository_url=_TESTPYPI_URL,
    )
    assert result == ShipTargetResult(
        target="pypi-test",
        state=ShipState.TERMINAL,
        reference="https://test.pypi.org/project/pkg/0.1.0/",
        message="View at:\n...\n",
    )


def test_ship_pypi_repository_url_sets_target_pypi_test_on_a_failed_build():
    """`canonical` is computed unconditionally, right after the credential
    check -- it must still read `"pypi-test"` even when no wheel/sdist was
    built at all."""
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
    with (
        patch("pyforge.mason.package.build", return_value=failed_build),
        patch("pyforge.mason.package.twine.upload") as mock_upload,
    ):
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON, repository_url=_TESTPYPI_URL)

    mock_upload.assert_not_called()
    assert result.target == "pypi-test"
    assert result.state == ShipState.FAILED


def test_ship_pypi_repository_url_sets_target_pypi_test_on_upload_failure():
    upload_result = TwineUploadResult(returncode=1, url=None, stdout="ERROR HTTPError: 400\n")
    with (
        patch("pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT),
        patch("pyforge.mason.package.twine.upload", return_value=upload_result),
    ):
        result = ship_pypi("/proj", environ=_SHIP_ENVIRON, repository_url=_TESTPYPI_URL)

    assert result == ShipTargetResult(
        target="pypi-test",
        state=ShipState.FAILED,
        reference=None,
        message="ERROR HTTPError: 400\n",
    )


def test_ship_pypi_without_repository_url_still_forwards_none_to_twine_upload():
    """Regression: `ship_pypi`'s own default (`repository_url=None`) must
    still reach `twine.upload` explicitly -- proven separately from
    `test_ship_pypi_happy_path_uploads_and_returns_terminal_result` above,
    which already asserts this, so a future edit that silently drops the
    keyword is still caught even if that other test's assertion changes."""
    upload_result = TwineUploadResult(returncode=0, url=None, stdout="")
    with (
        patch("pyforge.mason.package.build", return_value=_SHIP_BUILD_RESULT),
        patch(
            "pyforge.mason.package.twine.upload",
            return_value=upload_result,
        ) as mock_upload,
    ):
        ship_pypi("/proj", environ=_SHIP_ENVIRON)

    assert mock_upload.call_args.kwargs["repository_url"] is None


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
    with patch("pyforge.mason.package.build") as mock_build, patch("pyforge.mason.package.pixi.upload") as mock_upload:
        with pytest.raises(ShipChannelCredentialMissingError) as excinfo:
            ship_channel("/proj", "myorg", environ={})

    assert excinfo.value.missing == ("PREFIX_API_KEY",)
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_channel_treats_a_whitespace_only_credential_as_missing():
    with patch("pyforge.mason.package.build") as mock_build, patch("pyforge.mason.package.pixi.upload") as mock_upload:
        with pytest.raises(ShipChannelCredentialMissingError) as excinfo:
            ship_channel("/proj", "myorg", environ={"PREFIX_API_KEY": "   "})

    assert excinfo.value.missing == ("PREFIX_API_KEY",)
    mock_build.assert_not_called()
    mock_upload.assert_not_called()


def test_ship_channel_happy_path_uploads_and_returns_terminal_result():
    upload_result = PixiUploadResult(returncode=0, stdout="Uploading...\ndone\n")
    with (
        patch(
            "pyforge.mason.package.build",
            return_value=_SHIP_CHANNEL_BUILD_RESULT,
        ) as mock_build,
        patch(
            "pyforge.mason.package.pixi.search",
            return_value=False,
        ) as mock_search,
        patch(
            "pyforge.mason.package.pixi.upload",
            return_value=upload_result,
        ) as mock_upload,
    ):
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
    with (
        patch("pyforge.mason.package.build", return_value=failed_build),
        patch("pyforge.mason.package.pixi.upload") as mock_upload,
    ):
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
        returncode=1,
        stdout="Error:   x no prefix.dev API key provided\n",
    )
    with (
        patch("pyforge.mason.package.build", return_value=_SHIP_CHANNEL_BUILD_RESULT),
        patch("pyforge.mason.package.pixi.search", return_value=False),
        patch(
            "pyforge.mason.package.pixi.upload",
            return_value=upload_result,
        ) as mock_upload,
    ):
        result = ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_called_once_with(_SHIP_CHANNEL_BUILD_RESULT.conda_path, "myorg")
    assert result == ShipTargetResult(
        target="channel:myorg",
        state=ShipState.FAILED,
        reference=None,
        message="Error:   x no prefix.dev API key provided\n",
    )


def test_ship_channel_propagates_engine_absent_from_build():
    with (
        patch(
            "pyforge.mason.package.build",
            side_effect=EngineAbsentError("pixi", "pixi"),
        ),
        patch("pyforge.mason.package.pixi.upload") as mock_upload,
    ):
        with pytest.raises(EngineAbsentError):
            ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_channel_propagates_package_version_mismatch_from_build():
    with (
        patch(
            "pyforge.mason.package.build",
            side_effect=PackageVersionMismatchError(
                wheel_version="0.1.0",
                conda_version="0.2.0",
                wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
                conda_path="/proj/dist-conda/pkg-0.2.0-abc123_0.conda",
            ),
        ),
        patch("pyforge.mason.package.pixi.upload") as mock_upload,
    ):
        with pytest.raises(PackageVersionMismatchError):
            ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_channel_propagates_package_project_path_error_from_build():
    with (
        patch(
            "pyforge.mason.package.build",
            side_effect=PackageProjectPathError(project_path="/proj", reason="boom"),
        ),
        patch("pyforge.mason.package.pixi.upload") as mock_upload,
    ):
        with pytest.raises(PackageProjectPathError):
            ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_upload.assert_not_called()


def test_ship_channel_default_target_is_library():
    upload_result = PixiUploadResult(returncode=0, stdout="")
    with (
        patch(
            "pyforge.mason.package.build",
            return_value=_SHIP_CHANNEL_BUILD_RESULT,
        ) as mock_build,
        patch(
            "pyforge.mason.package.pixi.search",
            return_value=False,
        ),
        patch("pyforge.mason.package.pixi.upload", return_value=upload_result),
    ):
        ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_build.assert_called_once_with("/proj", target="library")


def test_ship_channel_forwards_an_explicit_target():
    upload_result = PixiUploadResult(returncode=0, stdout="")
    with (
        patch(
            "pyforge.mason.package.build",
            return_value=_SHIP_CHANNEL_BUILD_RESULT,
        ) as mock_build,
        patch(
            "pyforge.mason.package.pixi.search",
            return_value=False,
        ),
        patch("pyforge.mason.package.pixi.upload", return_value=upload_result),
    ):
        ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON, target="not-the-default")

    mock_build.assert_called_once_with("/proj", target="not-the-default")


# --- Story 3.7: ship_channel idempotence-by-interrogation -----------------------


def test_ship_channel_already_shipped_skips_upload_and_returns_terminal():
    """spec I/O matrix: 'Channel already shipped' -- pixi.search -> True ->
    TERMINAL, reference = channel_name; pixi.upload never called."""
    with (
        patch("pyforge.mason.package.build", return_value=_SHIP_CHANNEL_BUILD_RESULT),
        patch(
            "pyforge.mason.package.pixi.search",
            return_value=True,
        ) as mock_search,
        patch("pyforge.mason.package.pixi.upload") as mock_upload,
    ):
        result = ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    mock_search.assert_called_once_with("pkg", "0.1.0", "myorg")
    mock_upload.assert_not_called()
    assert result.target == "channel:myorg"
    assert result.state == ShipState.TERMINAL
    assert result.reference == "myorg"


def test_ship_channel_undeterminable_interrogation_returns_pending_naming_the_reason():
    """spec I/O matrix: 'Channel interrogation undeterminable' -- pixi.search
    -> None -> PENDING naming the reason; pixi.upload never called."""
    with (
        patch("pyforge.mason.package.build", return_value=_SHIP_CHANNEL_BUILD_RESULT),
        patch(
            "pyforge.mason.package.pixi.search",
            return_value=None,
        ),
        patch("pyforge.mason.package.pixi.upload") as mock_upload,
    ):
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
    with (
        patch(
            "pyforge.mason.package.build",
            side_effect=lambda *a, **k: (call_order.append("build"), _SHIP_CHANNEL_BUILD_RESULT)[1],
        ),
        patch(
            "pyforge.mason.package.pixi.search",
            side_effect=lambda *a, **k: (call_order.append("search"), False)[1],
        ),
        patch(
            "pyforge.mason.package.pixi.upload",
            side_effect=lambda *a, **k: (
                call_order.append("upload"),
                PixiUploadResult(returncode=0, stdout=""),
            )[1],
        ),
    ):
        ship_channel("/proj", "myorg", environ=_SHIP_CHANNEL_ENVIRON)

    assert call_order == ["build", "search", "upload"]


# --- Story 3.6: ship_conda_forge --------------------------------------------


@pytest.mark.parametrize("recipe_path", [None, "", "   "])
def test_ship_conda_forge_raises_recipe_missing_before_any_resolution(recipe_path):
    with (
        patch("pyforge.mason.package.resolve_cfe_root") as mock_resolve,
        patch("pyforge.mason.recipe.submit") as mock_submit,
        patch("pyforge.mason.cfe.subprocess.run") as mock_run,
    ):
        with pytest.raises(ShipCondaForgeRecipeMissingError):
            ship_conda_forge(
                recipe_path,
                environ={},
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                start_directory=Path("/start"),
            )

    mock_resolve.assert_not_called()
    mock_submit.assert_not_called()
    mock_run.assert_not_called()


def test_ship_conda_forge_raises_cfe_unresolved_when_root_is_not_found():
    with (
        patch(
            "pyforge.mason.package.resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ) as mock_resolve,
        patch("pyforge.mason.recipe.submit") as mock_submit,
        patch("pyforge.mason.cfe.subprocess.run") as mock_run,
    ):
        with pytest.raises(CfeUnresolvedError):
            ship_conda_forge(
                "/some/recipe/foo",
                environ={},
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                start_directory=Path("/start"),
            )

    mock_resolve.assert_called_once_with(None, {}, Path("/start"))
    mock_submit.assert_not_called()
    mock_run.assert_not_called()


def test_ship_conda_forge_wrong_location_raises_naming_both_paths_no_subprocess(tmp_path):
    root = tmp_path / "cfe-root"
    recipe_dir = tmp_path / "elsewhere" / "foo"
    with (
        patch(
            "pyforge.mason.package.resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=root, step=STEP_CWD_WALK),
        ),
        patch("pyforge.mason.recipe.submit") as mock_submit,
        patch("pyforge.mason.cfe.subprocess.run") as mock_run,
    ):
        with pytest.raises(ShipCondaForgeRecipeLocationError) as excinfo:
            ship_conda_forge(
                str(recipe_dir),
                environ={},
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                start_directory=tmp_path,
            )

    expected_dir = root / "recipes" / "foo"
    assert excinfo.value.recipe_path == str(recipe_dir.resolve())
    assert excinfo.value.expected_path == str(expected_dir.resolve())
    mock_submit.assert_not_called()
    mock_run.assert_not_called()


def test_ship_conda_forge_accepts_a_recipe_reached_through_a_symlinked_recipes_dir(tmp_path):
    """Follow-up review pass, 2026-08-13: pass 1 added the `.resolve()` on
    `expected_dir` specifically so a symlinked `<root>/recipes` would not
    produce a FALSE mismatch against the independently-resolved
    `recipe_dir` -- and shipped that patch with no test covering the one
    scenario that motivated it. Both sides are compared physically, so a
    recipe reached through the symlink is accepted; without the
    `.resolve()`, `expected_dir` keeps the symlink spelling and this call
    raises instead."""
    root = tmp_path / "cfe-root"
    (root / "store").mkdir(parents=True)
    (root / "recipes").symlink_to(root / "store", target_is_directory=True)
    recipe_dir = root / "store" / "foo"
    recipe_dir.mkdir()
    submit_result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference=None,
        message="ok",
    )

    with (
        patch(
            "pyforge.mason.package.resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=root, step=STEP_CWD_WALK),
        ),
        patch("pyforge.mason.recipe.submit", return_value=submit_result) as mock_submit,
    ):
        result = ship_conda_forge(
            str(recipe_dir),
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert result is submit_result
    assert mock_submit.call_args.args[0] == str(recipe_dir.resolve())


def test_ship_conda_forge_returns_failed_when_path_resolve_raises(tmp_path):
    """spec Always boundary: a `Path.resolve()` `OSError`/`ValueError` on
    either `recipe_path` or the resolved root returns `ShipTargetResult(
    FAILED, message=str(exc))` instead of raising -- mirrors
    `recipe.py::submit()`'s own established precedent for this exact
    resolve-failure mode."""
    with (
        patch(
            "pyforge.mason.package.resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=tmp_path, step=STEP_CWD_WALK),
        ),
        patch(
            "pyforge.mason.package.Path.resolve",
            side_effect=OSError("Too many levels of symlinks"),
        ),
        patch("pyforge.mason.recipe.submit") as mock_submit,
    ):
        result = ship_conda_forge(
            "/some/bad/path",
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert result == ShipTargetResult(
        target="conda-forge",
        state=ShipState.FAILED,
        reference=None,
        message="Too many levels of symlinks",
    )
    mock_submit.assert_not_called()


def test_ship_conda_forge_returns_failed_when_the_recipe_tilde_cannot_expand(tmp_path):
    """Follow-up review pass, 2026-08-13: `Path.expanduser()` raises
    `RuntimeError` -- NOT an `OSError` subclass for this failure -- when a
    leading `~user` names no such user. The original `except (OSError,
    ValueError)` did not catch it, so the function raised instead of
    returning the `FAILED` result its own docstring promises."""
    with (
        patch(
            "pyforge.mason.package.resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=tmp_path, step=STEP_CWD_WALK),
        ),
        patch("pyforge.mason.recipe.submit") as mock_submit,
    ):
        result = ship_conda_forge(
            "~nosuchuser9/recipes/foo",
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert result.target == "conda-forge"
    assert result.state is ShipState.FAILED
    mock_submit.assert_not_called()


def test_ship_conda_forge_returns_failed_when_the_root_tilde_cannot_expand(tmp_path):
    """Follow-up review pass, 2026-08-13: the SAME `RuntimeError` is
    reachable through the resolved ROOT, not only through `recipe_path`.
    `resolve_cfe_root`'s flag/environment steps pass a `--cfe-root
    ~foo/cfe` value through unvalidated, and the root is `.expanduser()`d
    here (and in `doctor.py`) only -- `recipe.py::submit()` never expands a
    root, so this trigger has no pre-existing counterpart there."""
    with (
        patch(
            "pyforge.mason.package.resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=Path("~nosuchuser9/cfe"), step=STEP_FLAG),
        ),
        patch("pyforge.mason.recipe.submit") as mock_submit,
    ):
        result = ship_conda_forge(
            str(tmp_path / "recipes" / "foo"),
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert result.target == "conda-forge"
    assert result.state is ShipState.FAILED
    mock_submit.assert_not_called()


def test_ship_conda_forge_strips_a_recipe_path_before_resolving_it(tmp_path):
    """Follow-up review pass, 2026-08-13: gate #1 already `.strip()`s to
    decide blankness, so `Path()` must strip too. Without it a
    leading-space value is not absolute -- its first path component is the
    spaces themselves -- and silently resolves relative to the cwd,
    producing a location error naming a path the user never supplied."""
    root = tmp_path / "cfe-root"
    recipe_dir = root / "recipes" / "foo"
    submit_result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="ref",
        message="msg",
    )
    with (
        patch(
            "pyforge.mason.package.resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=root, step=STEP_CWD_WALK),
        ),
        patch("pyforge.mason.recipe.submit", return_value=submit_result) as mock_submit,
    ):
        result = ship_conda_forge(
            f"   {recipe_dir}  ",
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert result is submit_result
    assert mock_submit.call_args.args[0] == str(recipe_dir.resolve())


def test_ship_conda_forge_happy_path_returns_recipe_submit_result_unchanged(tmp_path):
    root = tmp_path / "cfe-root"
    recipe_dir = root / "recipes" / "foo"
    submit_result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="https://github.com/conda-forge/staged-recipes/pull/123",
        message="PR created: https://github.com/conda-forge/staged-recipes/pull/123",
    )
    with (
        patch(
            "pyforge.mason.package.resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=root, step=STEP_CWD_WALK),
        ),
        patch("pyforge.mason.recipe.submit", return_value=submit_result) as mock_submit,
    ):
        result = ship_conda_forge(
            str(recipe_dir),
            environ={"FOO": "bar"},
            cfe_root_arg="cfe-root-flag",
            cfe_python_arg="py-flag",
            cfe_timeout_arg=42.0,
            start_directory=tmp_path,
        )

    assert result is submit_result
    mock_submit.assert_called_once_with(
        str(recipe_dir.resolve()),
        confirm=True,
        prepare_only=False,
        cfe_root_arg="cfe-root-flag",
        cfe_python_arg="py-flag",
        cfe_timeout_arg=42.0,
        environ={"FOO": "bar"},
        start_directory=tmp_path,
    )


# --- Real end-to-end against fake_cfe_root (AD-16, no mocking) -------------


def test_ship_conda_forge_against_fake_cfe_root_returns_the_fixtures_canned_success(
    fake_cfe_root,
    monkeypatch,
):
    """Mirrors `test_recipe.py::
    test_submit_against_fake_cfe_root_returns_the_fixtures_canned_success`:
    a recipe path that resolves to exactly `<fake_cfe_root>/recipes/
    example-recipe` satisfies both of `ship_conda_forge`'s own
    preconditions, so the real `recipe.py::submit()` composition runs and
    returns the fixture's canned `PENDING` result unchanged. No `recipes/`
    directory needs to exist on disk -- matches `submit()`'s established
    no-existence-check precedent (path resolution only)."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    result = ship_conda_forge(
        str(fake_cfe_root / "recipes" / "example-recipe"),
        environ={},
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        start_directory=fake_cfe_root,
    )

    assert result == ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="https://github.com/example/example/pull/1",
        message="PR created: https://github.com/example/example/pull/1",
    )


# --- Story 3.9: ship() dispatcher -------------------------------------------
#
# `ship_pypi`/`ship_channel`/`ship_conda_forge` are mocked at their own
# `pyforge.mason.package.*` call sites (this suite's established "patch on
# the calling module's own namespace" convention -- `package.py`'s `ship()`
# calls each of them directly, an attribute lookup at call time), so this
# block proves `ship()`'s own dispatch/gating/exception-catch logic
# independent of any one target's real behavior.


def test_ship_invalid_target_raises_before_any_target_runs(tmp_path):
    """spec I/O matrix: 'Invalid token... whole command fails before any
    target runs.'"""
    with patch("pyforge.mason.package.build") as mock_build, patch("pyforge.mason.package.ship_pypi") as mock_ship_pypi:
        with pytest.raises(InvalidShipTargetError) as excinfo:
            ship(
                "bogus",
                confirm=True,
                environ={},
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                start_directory=tmp_path,
            )

    assert excinfo.value.value == "bogus"
    mock_build.assert_not_called()
    mock_ship_pypi.assert_not_called()


def test_ship_dry_run_calls_build_once_and_returns_the_plan(tmp_path):
    """spec I/O matrix: dry-run default -- one `build()` call, then `plan_
    ship`'s own `NOT_ATTEMPTED` entries; nothing uploaded."""
    with (
        patch(
            "pyforge.mason.package.build",
            return_value=_PLAN_BUILD_RESULT,
        ) as mock_build,
        patch("pyforge.mason.package.ship_pypi") as mock_ship_pypi,
    ):
        results = ship(
            "pypi,conda-forge",
            confirm=False,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_build.assert_called_once_with(str(tmp_path), target="library")
    mock_ship_pypi.assert_not_called()
    assert len(results) == 2
    assert all(r.state == ShipState.NOT_ATTEMPTED for r in results)
    assert results[0].target == "pypi"
    assert "irreversible" in results[0].message.lower()
    assert results[1].target == "conda-forge"


def test_ship_dry_run_calls_build_exactly_once_regardless_of_target_count(tmp_path):
    with patch(
        "pyforge.mason.package.build",
        return_value=_PLAN_BUILD_RESULT,
    ) as mock_build:
        ship(
            "pypi,pypi-test,conda-forge,channel:myorg",
            confirm=False,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_build.assert_called_once()


def test_ship_dry_run_pypi_test_plan_names_testpypi_with_no_irreversibility_claim(tmp_path):
    with patch("pyforge.mason.package.build", return_value=_PLAN_BUILD_RESULT):
        results = ship(
            "pypi-test",
            confirm=False,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert results[0].target == "pypi-test"
    assert results[0].state == ShipState.NOT_ATTEMPTED
    assert "testpypi" in results[0].message.lower()
    assert "irreversible" not in results[0].message.lower()


def test_ship_dry_run_forwards_an_explicit_target_to_build(tmp_path):
    with patch(
        "pyforge.mason.package.build",
        return_value=_PLAN_BUILD_RESULT,
    ) as mock_build:
        ship(
            "pypi",
            confirm=False,
            environ={},
            target="not-the-default",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_build.assert_called_once_with(str(tmp_path), target="not-the-default")


def test_ship_dry_run_with_only_conda_forge_never_calls_build(tmp_path):
    """**New test (review pass 2)**: spec Always boundary -- "A project
    needing only `conda-forge` must not be forced through `pep517`/`pixi`
    build engines it may not even have" applies to the DRY-RUN branch too,
    not just the real-ship path (`test_ship_real_ship_with_only_conda_forge_
    never_calls_build` above already covers the real-ship side). A lone
    `conda-forge` target and a duplicated `conda-forge,conda-forge` target
    set must both skip `build()` entirely and still return a proper
    dry-run `NOT_ATTEMPTED` plan naming a pull request -- not crash with
    `EngineAbsentError` on a host missing pep517/pixi tooling."""
    with patch("pyforge.mason.package.build") as mock_build:
        results = ship(
            "conda-forge",
            confirm=False,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_build.assert_not_called()
    assert len(results) == 1
    assert results[0].target == "conda-forge"
    assert results[0].state == ShipState.NOT_ATTEMPTED
    assert "pull request" in results[0].message.lower()

    with patch("pyforge.mason.package.build") as mock_build:
        results = ship(
            "conda-forge,conda-forge",
            confirm=False,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_build.assert_not_called()
    assert len(results) == 2
    assert all(r.target == "conda-forge" for r in results)
    assert all(r.state == ShipState.NOT_ATTEMPTED for r in results)


def test_ship_dry_run_mixing_conda_forge_with_pypi_still_calls_build_once(tmp_path):
    """**New test (review pass 2)**: confirms the existing coverage the
    spec's own Tasks entry points at -- the `build()` skip applies ONLY
    when EVERY target is `conda-forge`; a dry-run mixing `conda-forge` with
    `pypi` (or `channel:<name>`) still calls `build()` exactly once.
    `test_ship_dry_run_calls_build_once_and_returns_the_plan` above already
    exercises `"pypi,conda-forge"` for this; this test names the same
    guarantee explicitly against a `channel:<name>` mix too, so the
    boundary condition ("at least one non-conda-forge target") is not only
    ever exercised via `pypi`."""
    with patch(
        "pyforge.mason.package.build",
        return_value=_PLAN_BUILD_RESULT,
    ) as mock_build:
        results = ship(
            "conda-forge,channel:myorg",
            confirm=False,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_build.assert_called_once_with(str(tmp_path), target="library")
    assert len(results) == 2
    assert all(r.state == ShipState.NOT_ATTEMPTED for r in results)


def test_ship_dry_run_mixing_conda_forge_with_pypi_test_still_calls_build_once(tmp_path):
    """**New test (review pass 3)**: `pypi-test` (like `pypi`/`channel:<name>`)
    is a non-`conda-forge` target that needs a real `build_result` for
    `plan_ship`'s own `PYPI_TEST` branch -- confirms the `build()`-skip
    boundary condition against `pypi-test` specifically, not only `pypi`/
    `channel:<name>` as the two tests above already cover."""
    with patch(
        "pyforge.mason.package.build",
        return_value=_PLAN_BUILD_RESULT,
    ) as mock_build:
        results = ship(
            "conda-forge,pypi-test",
            confirm=False,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_build.assert_called_once_with(str(tmp_path), target="library")
    assert len(results) == 2
    assert all(r.state == ShipState.NOT_ATTEMPTED for r in results)


def test_ship_real_ship_conda_forge_and_pypi_test_with_no_pypi_sibling_run_independently(
    tmp_path,
):
    """**New test (review pass 3)**: `--to conda-forge,pypi-test` (real
    ship, no plain `pypi` target anywhere in the invocation) exercises
    every target through the ordinary per-target loop -- the FR-24/FR-50
    rehearsal-gate pre-run only ever triggers when a `PYPI` target is ALSO
    present (see `ship()`'s own docstring); with none here, neither target
    should be gated or specially reordered."""
    recipe_dir = tmp_path / "recipes" / "example-recipe"
    recipe_dir.mkdir(parents=True)
    conda_forge_result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="https://github.com/x/pull/1",
        message="opened",
    )
    pypi_test_result = ShipTargetResult(
        target="pypi-test",
        state=ShipState.TERMINAL,
        reference="https://test.pypi.org/x",
        message="ok",
    )
    with (
        patch(
            "pyforge.mason.package.ship_conda_forge",
            return_value=conda_forge_result,
        ) as mock_conda_forge,
        patch(
            "pyforge.mason.package.ship_pypi",
            return_value=pypi_test_result,
        ) as mock_ship_pypi,
    ):
        results = ship(
            "conda-forge,pypi-test",
            confirm=True,
            environ={},
            recipe_path=str(recipe_dir),
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert results == (conda_forge_result, pypi_test_result)
    mock_conda_forge.assert_called_once()
    mock_ship_pypi.assert_called_once()
    assert mock_ship_pypi.call_args.kwargs["repository_url"] == _TESTPYPI_REPOSITORY_URL


def test_ship_canonical_happy_path_pypi_and_channel_both_terminal(tmp_path):
    """spec I/O matrix: canonical happy path -- both `TERMINAL`."""
    pypi_result = ShipTargetResult(
        target="pypi",
        state=ShipState.TERMINAL,
        reference="url",
        message="ok",
    )
    channel_result = ShipTargetResult(
        target="channel:myorg",
        state=ShipState.TERMINAL,
        reference="myorg",
        message="ok",
    )
    with (
        patch(
            "pyforge.mason.package.ship_pypi",
            return_value=pypi_result,
        ) as mock_ship_pypi,
        patch(
            "pyforge.mason.package.ship_channel",
            return_value=channel_result,
        ) as mock_ship_channel,
        patch("pyforge.mason.package.build") as mock_build,
    ):
        results = ship(
            "pypi,channel:myorg",
            confirm=True,
            environ={"X": "Y"},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_build.assert_not_called()
    assert results == (pypi_result, channel_result)
    mock_ship_pypi.assert_called_once_with(str(tmp_path), environ={"X": "Y"}, target="library")
    mock_ship_channel.assert_called_once_with(
        str(tmp_path),
        "myorg",
        environ={"X": "Y"},
        target="library",
    )


def test_ship_pypi_alone_runs_immediately_with_no_gate(tmp_path):
    """spec I/O matrix: 'pypi alone... runs immediately, no gate.'"""
    pypi_result = ShipTargetResult(
        target="pypi",
        state=ShipState.TERMINAL,
        reference="url",
        message="ok",
    )
    with patch("pyforge.mason.package.ship_pypi", return_value=pypi_result) as mock_ship_pypi:
        results = ship(
            "pypi",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_ship_pypi.assert_called_once_with(str(tmp_path), environ={}, target="library")
    assert results == (pypi_result,)


def test_ship_forwards_an_explicit_target_to_ship_pypi(tmp_path):
    pypi_result = ShipTargetResult(
        target="pypi",
        state=ShipState.TERMINAL,
        reference="u",
        message="m",
    )
    with patch("pyforge.mason.package.ship_pypi", return_value=pypi_result) as mock_ship_pypi:
        ship(
            "pypi",
            confirm=True,
            environ={},
            target="not-the-default",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_ship_pypi.assert_called_once_with(str(tmp_path), environ={}, target="not-the-default")


def test_ship_rehearsal_passes_then_pypi_runs_for_real(tmp_path):
    """spec I/O matrix: 'Rehearsal passes... pypi-test TERMINAL, then pypi
    runs for real and is TERMINAL.'"""
    rehearsal_result = ShipTargetResult(
        target="pypi-test",
        state=ShipState.TERMINAL,
        reference="test-url",
        message="ok-test",
    )
    real_result = ShipTargetResult(
        target="pypi",
        state=ShipState.TERMINAL,
        reference="real-url",
        message="ok-real",
    )
    with patch(
        "pyforge.mason.package.ship_pypi",
        side_effect=[rehearsal_result, real_result],
    ) as mock_ship_pypi:
        results = ship(
            "pypi-test,pypi",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert results == (rehearsal_result, real_result)
    assert mock_ship_pypi.call_count == 2
    first_call, second_call = mock_ship_pypi.call_args_list
    assert first_call.kwargs["repository_url"] == _TESTPYPI_URL
    assert "repository_url" not in second_call.kwargs


def test_ship_rehearsal_fails_then_pypi_is_gated_and_never_called(tmp_path):
    """spec I/O matrix: 'Rehearsal fails... pypi-test FAILED; pypi is
    NOT_ATTEMPTED naming the gate, no upload attempted.'"""
    rehearsal_result = ShipTargetResult(
        target="pypi-test",
        state=ShipState.FAILED,
        reference=None,
        message="upload failed",
    )
    with patch(
        "pyforge.mason.package.ship_pypi",
        return_value=rehearsal_result,
    ) as mock_ship_pypi:
        results = ship(
            "pypi-test,pypi",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_ship_pypi.assert_called_once()  # only the rehearsal itself -- pypi's own upload never ran
    assert results[0] == rehearsal_result
    assert results[1].target == "pypi"
    assert results[1].state == ShipState.NOT_ATTEMPTED
    assert "rehearsal" in results[1].message.lower()
    assert "failed" in results[1].message.lower()


def test_ship_rehearsal_runs_first_regardless_of_input_order(tmp_path):
    """spec Always boundary: 'the FIRST pypi-test target always executes
    before the loop's normal per-target pass (regardless of which order
    the user typed them)... reused... at its original position in the
    OUTPUT order.'"""
    call_order = []

    def fake_ship_pypi(project_path, *, environ, target, repository_url=None):
        call_order.append(repository_url)
        if repository_url:
            return ShipTargetResult(
                target="pypi-test",
                state=ShipState.TERMINAL,
                reference="t",
                message="t",
            )
        return ShipTargetResult(target="pypi", state=ShipState.TERMINAL, reference="r", message="r")

    with patch("pyforge.mason.package.ship_pypi", side_effect=fake_ship_pypi):
        results = ship(
            "pypi,pypi-test",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    # The rehearsal (repository_url set) ran FIRST even though "pypi" was
    # typed first in raw_targets...
    assert call_order[0] == _TESTPYPI_URL
    # ...but OUTPUT order still matches INPUT order: pypi at index 0,
    # pypi-test at index 1.
    assert results[0].target == "pypi"
    assert results[1].target == "pypi-test"


def test_ship_multiple_pypi_test_tokens_only_the_first_gates_pypi(tmp_path):
    """Task list: 'multiple pypi-test tokens: only the first gates pypi,
    later ones still execute independently.'"""
    call_log = []

    def fake_ship_pypi(project_path, *, environ, target, repository_url=None):
        call_log.append(repository_url)
        if repository_url:
            return ShipTargetResult(
                target="pypi-test",
                state=ShipState.TERMINAL,
                reference="t",
                message=f"call-{len(call_log)}",
            )
        return ShipTargetResult(target="pypi", state=ShipState.TERMINAL, reference="r", message="r")

    with patch("pyforge.mason.package.ship_pypi", side_effect=fake_ship_pypi):
        results = ship(
            "pypi-test,pypi-test,pypi",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert len(call_log) == 3  # both pypi-test tokens ran independently, plus the real pypi
    assert results[0].target == "pypi-test"
    assert results[1].target == "pypi-test"
    assert results[2].target == "pypi"
    assert results[0].message != results[1].message  # two genuinely independent calls


def test_ship_pypi_with_no_pypi_test_sibling_is_unaffected_by_the_gate(tmp_path):
    """spec Always boundary (D-11): 'A pypi target with no pypi-test
    sibling in the same invocation is unaffected.'"""
    pypi_result = ShipTargetResult(
        target="pypi",
        state=ShipState.TERMINAL,
        reference="u",
        message="m",
    )
    channel_result = ShipTargetResult(
        target="channel:myorg",
        state=ShipState.TERMINAL,
        reference="myorg",
        message="m",
    )
    with (
        patch(
            "pyforge.mason.package.ship_pypi",
            return_value=pypi_result,
        ) as mock_ship_pypi,
        patch(
            "pyforge.mason.package.ship_channel",
            return_value=channel_result,
        ),
    ):
        results = ship(
            "channel:myorg,pypi",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_ship_pypi.assert_called_once_with(str(tmp_path), environ={}, target="library")
    assert results[1] == pypi_result


def test_ship_pypi_test_with_no_pypi_sibling_runs_the_ordinary_loop_not_the_gate(tmp_path):
    """New test, review pass 1: the rehearsal pre-run/gate block above only
    ever triggers `if any(t.kind is ShipTargetKind.PYPI for t in targets)`
    -- a lone `pypi-test` target, with no `pypi` sibling anywhere in the
    same `targets` tuple, must never enter that pre-run block at all and
    must instead be dispatched once per token from the ordinary per-target
    loop, exactly like any other target kind (mirrors `test_ship_pypi_
    with_no_pypi_test_sibling_is_unaffected_by_the_gate` above, the
    opposite-direction case)."""
    pypi_test_result = ShipTargetResult(
        target="pypi-test",
        state=ShipState.TERMINAL,
        reference="test-url",
        message="ok-test",
    )
    with patch(
        "pyforge.mason.package.ship_pypi",
        return_value=pypi_test_result,
    ) as mock_ship_pypi:
        results = ship(
            "pypi-test",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    mock_ship_pypi.assert_called_once_with(
        str(tmp_path),
        environ={},
        target="library",
        repository_url=_TESTPYPI_URL,
    )
    assert results == (pypi_test_result,)


def test_ship_duplicated_pypi_test_with_no_pypi_sibling_calls_ship_pypi_once_per_token(tmp_path):
    """New test, review pass 1: `--to pypi-test,pypi-test` with no `pypi`
    sibling -- neither token is a cached/reused pre-run result (that
    mechanism only exists to gate a `pypi` target), so both must be
    dispatched independently, once each, from the ordinary loop."""
    with patch(
        "pyforge.mason.package.ship_pypi",
        side_effect=[
            ShipTargetResult(
                target="pypi-test",
                state=ShipState.TERMINAL,
                reference="t1",
                message="call-1",
            ),
            ShipTargetResult(
                target="pypi-test",
                state=ShipState.TERMINAL,
                reference="t2",
                message="call-2",
            ),
        ],
    ) as mock_ship_pypi:
        results = ship(
            "pypi-test,pypi-test",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert mock_ship_pypi.call_count == 2
    for call in mock_ship_pypi.call_args_list:
        assert call.kwargs["repository_url"] == _TESTPYPI_URL
    assert len(results) == 2
    assert results[0].message == "call-1"
    assert results[1].message == "call-2"


def test_ship_conda_forge_precondition_failure_alongside_pypi_does_not_block_pypi(tmp_path):
    """spec I/O matrix: 'conda-forge precondition fails alongside
    others... conda-forge alone FAILED naming the precondition; pypi
    completes normally.'"""
    pypi_result = ShipTargetResult(
        target="pypi",
        state=ShipState.TERMINAL,
        reference="url",
        message="ok",
    )
    with (
        patch("pyforge.mason.package.ship_pypi", return_value=pypi_result),
        patch(
            "pyforge.mason.package.ship_conda_forge",
            side_effect=CfeUnresolvedError(),
        ),
    ):
        results = ship(
            "pypi,conda-forge",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert results[0] == pypi_result
    assert results[1].target == "conda-forge"
    assert results[1].state == ShipState.FAILED
    assert results[1].message == str(CfeUnresolvedError())


def test_ship_lone_conda_forge_cfe_unresolved_returns_failed_not_raised(tmp_path):
    """spec Design Notes: `EXIT_CFE_UNAVAILABLE` never surfaces from
    `ship()`, even for a lone `--to conda-forge` with an unresolved CFE
    root -- the per-target catch intercepts `CfeUnresolvedError` before it
    can reach `main()`'s own exception handler. Proven here by NOT wrapping
    the call in `pytest.raises` at all: a raise would fail this test."""
    with patch("pyforge.mason.package.ship_conda_forge", side_effect=CfeUnresolvedError()):
        results = ship(
            "conda-forge",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
        )

    assert results == (
        ShipTargetResult(
            target="conda-forge",
            state=ShipState.FAILED,
            reference=None,
            message=str(CfeUnresolvedError()),
        ),
    )


def test_ship_a_masonerror_from_one_target_does_not_stop_later_targets(tmp_path):
    conda_forge_result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="ref",
        message="ok",
    )
    with (
        patch(
            "pyforge.mason.package.ship_channel",
            side_effect=ShipChannelCredentialMissingError(["PREFIX_API_KEY"]),
        ),
        patch("pyforge.mason.package.ship_conda_forge", return_value=conda_forge_result),
    ):
        results = ship(
            "channel:myorg,conda-forge",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
            recipe_path="/some/recipe",
        )

    assert results[0].target == "channel:myorg"
    assert results[0].state == ShipState.FAILED
    assert results[1] == conda_forge_result


def test_ship_real_ship_with_only_conda_forge_never_calls_build(tmp_path):
    """spec Always boundary: a project shipping only to `conda-forge` must
    never be forced through `pep517`/`pixi` build engines it may not even
    have installed."""
    conda_forge_result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="ref",
        message="ok",
    )
    with (
        patch(
            "pyforge.mason.package.ship_conda_forge",
            return_value=conda_forge_result,
        ),
        patch("pyforge.mason.package.build"),
        patch("pyforge.mason.package.pep517.build"),
        patch("pyforge.mason.package.pixi.build"),
    ):
        results = ship(
            "conda-forge",
            confirm=True,
            environ={},
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=tmp_path,
            recipe_path="/some/recipe",
        )

    assert results == (conda_forge_result,)


def test_ship_forwards_recipe_path_and_cfe_args_to_the_conda_forge_target(tmp_path):
    conda_forge_result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="ref",
        message="ok",
    )
    with patch(
        "pyforge.mason.package.ship_conda_forge",
        return_value=conda_forge_result,
    ) as mock_ship_conda_forge:
        ship(
            "conda-forge",
            confirm=True,
            environ={"E": "V"},
            cfe_root_arg="/root",
            cfe_python_arg="/py",
            cfe_timeout_arg=9.0,
            start_directory=tmp_path,
            recipe_path="/some/recipe",
        )

    mock_ship_conda_forge.assert_called_once_with(
        "/some/recipe",
        environ={"E": "V"},
        cfe_root_arg="/root",
        cfe_python_arg="/py",
        cfe_timeout_arg=9.0,
        start_directory=tmp_path,
    )


# --- Story 3.7: build_ship_receipt -----------------------------------------------

_TERMINAL_PYPI = ShipTargetResult(
    target="pypi",
    state=ShipState.TERMINAL,
    reference="https://pypi.org/project/pkg/0.1.0/",
    message="View at:\n...\n",
)
_PENDING_CHANNEL = ShipTargetResult(
    target="channel:myorg",
    state=ShipState.PENDING,
    reference=None,
    message="could not determine whether channel already has pkg 0.1.0",
)
_FAILED_PYPI = ShipTargetResult(
    target="pypi",
    state=ShipState.FAILED,
    reference=None,
    message="ERROR HTTPError: 400\n",
)
_NOT_ATTEMPTED_CONDA_FORGE = ShipTargetResult(
    target="conda-forge",
    state=ShipState.NOT_ATTEMPTED,
    reference=None,
    message=None,
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
    with (
        patch("pyforge.mason.package.build") as mock_build,
        patch("pyforge.mason.package.pep517.build") as mock_pep517,
        patch("pyforge.mason.package.pixi.build") as mock_pixi,
    ):
        build_ship_receipt((_TERMINAL_PYPI, _FAILED_PYPI))

    mock_build.assert_not_called()
    mock_pep517.assert_not_called()
    mock_pixi.assert_not_called()
