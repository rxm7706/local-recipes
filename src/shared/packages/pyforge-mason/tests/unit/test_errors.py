"""Story 1.3 — `MasonError` construction, identifier validation, `__str__`.

Story 1.6 extends this file with `CfeImportFloorError` coverage: its
identifier and a message naming every missing module plus the interpreter
path. Story 1.7 extends it again with `CfeUnresolvedError` coverage: its
fixed identifier and message naming all four `resolve.py` step names plus
how to satisfy the first three. Story 2.1 extends it again with
`CfeTimeoutError` coverage: its identifier and a message naming both the
timed-out script's key and the timeout value. Story 3.1 extends it again
with `EngineAbsentError` coverage: its identifier, stored attributes, and a
message naming both the absent engine and its provisioning hint, matching
`CfeImportFloorError`'s existing test shape. Story 3.2 extends it again
with `PackageVersionMismatchError` coverage: its identifier, stored
attributes, and a message naming both the wheel and conda versions,
matching `EngineAbsentError`'s existing two-string-argument test shape
(including its `__reduce__` deepcopy/pickle guard). Story 3.2's review pass
(2026-08-13) extends `PackageVersionMismatchError`'s coverage again to its
new `wheel_path`/`conda_path` arguments (Patch 7), and adds coverage for
two new error classes: `PackageBuildTimeoutError` (Patch 3, mirrors
`CfeTimeoutError`'s shape) and `PackageProjectPathError` (Patch 4, mirrors
`CfeTimeoutError`'s shape with a different pair of fields).

Story 3.3 extends this file again with `InvalidShipTargetError` coverage,
mirroring `PackageProjectPathError`'s suite exactly in shape: identifier,
stored attribute, message content, is-a-`MasonError`, `str()` format,
rejects-empty-value, deepcopy/pickle round-trip.

Story 3.4 extends this file again with `ShipCredentialMissingError`/
`ShipUploadTimeoutError` coverage. Story 3.5 extends it again with
`ShipChannelCredentialMissingError`/`ShipChannelUploadTimeoutError`
coverage, mirroring those two classes' own suites exactly in shape (this
story's two classes are dedicated, not reused, because the PyPI-worded
ones would print a factually wrong message for a channel failure).

Story 3.6 extends this file again with `ShipCondaForgeRecipeMissingError`
(zero-arg, mirrors `CfeUnresolvedError`'s own suite shape) and
`ShipCondaForgeRecipeLocationError` (two-arg, mirrors
`PackageProjectPathError`'s own suite shape) coverage.

Story 3.9 extends `InvalidShipTargetError`'s own message-content test:
`pypi-test` now joins the listed valid forms (FR-24, FR-50, AD-26) -- no
new error class, since `ShipTargetKind.PYPI_TEST` reuses this same
existing class for the exact same failure mode.

Story 4.1 extends this file again with `EnvironmentLockTimeoutError`
coverage, mirroring `ShipUploadTimeoutError`'s own suite exactly in shape
(identifier, stored `timeout`, message content, `MasonError` subclass-ness,
`str()` format, deepcopy/pickle round-trip) -- only `condalock.lock()` ever
raises it, so no second constructor argument is needed.

Story 4.2 extends this file again with `EnvironmentManifestsNotFoundError`
coverage, mirroring `ShipCredentialMissingError`'s own suite shape
(identifier, stored `directory`/`filenames`, message content naming both,
`MasonError` subclass-ness, `str()` format, rejects-empty-`directory`,
rejects-empty-`filenames`, deepcopy/pickle round-trip via `__reduce__`)."""

from __future__ import annotations

import copy
import pickle

import pytest

from pyforge.mason.errors import (
    CfeImportFloorError,
    CfeTimeoutError,
    CfeUnresolvedError,
    EngineAbsentError,
    EnvironmentCheckTimeoutError,
    EnvironmentLockfileMalformedError,
    EnvironmentLockfileMissingError,
    EnvironmentLockTimeoutError,
    EnvironmentManifestsNotFoundError,
    InvalidShipTargetError,
    MasonError,
    PackageBuildTimeoutError,
    PackageProjectPathError,
    PackageVersionMismatchError,
    ShipChannelCredentialMissingError,
    ShipChannelUploadTimeoutError,
    ShipCondaForgeRecipeLocationError,
    ShipCondaForgeRecipeMissingError,
    ShipCredentialMissingError,
    ShipUploadTimeoutError,
)


def test_valid_identifier_constructs_and_stores_attributes():
    exc = MasonError("cfe:unresolved", "the CFE root could not be found")
    assert exc.identifier == "cfe:unresolved"
    assert exc.message == "the CFE root could not be found"


@pytest.mark.parametrize(
    "identifier",
    [
        "cfe:unresolved",
        "ship:credential-missing",
        "engine:absent",
        "a:b",
        "multi-part-name:multi-part-message",
    ],
)
def test_valid_identifiers_from_the_architecture_spine(identifier):
    MasonError(identifier, "message")  # must not raise


@pytest.mark.parametrize(
    "identifier",
    [
        "Bad Id",
        "NoColon",
        "cfe:",
        ":unresolved",
        "cfe:Unresolved",
        "CFE:unresolved",
        "cfe :unresolved",
        "cfe: unresolved",
        "cfe:un_resolved",
        "cfe--bad:unresolved",
        "cfe:unresolved:extra",
        "",
        "cfe:unresolved\n",  # a trailing newline must not slip past `$`-style anchoring
    ],
)
def test_invalid_identifiers_raise_value_error(identifier):
    with pytest.raises(ValueError):
        MasonError(identifier, "msg")


def test_non_string_identifier_raises_value_error_not_type_error():
    """A non-str identifier must fail with the documented ValueError, not an
    incidental TypeError from the regex engine rejecting a non-str input."""
    with pytest.raises(ValueError):
        MasonError(None, "msg")


@pytest.mark.parametrize("message", ["", "   ", "\n", "\t \n"])
def test_empty_or_whitespace_only_message_raises_value_error(message):
    """An empty or all-whitespace message can't state what failed or what to
    do next (NFR-14) — whitespace-only is the same truncated diagnostic as
    empty, one space bar away."""
    with pytest.raises(ValueError):
        MasonError("cfe:unresolved", message)


def test_non_string_message_raises_value_error():
    """A non-str message (int, list, exception object) must fail with the
    documented ValueError — same asymmetry-closing guard as the non-str
    identifier case above."""
    with pytest.raises(ValueError):
        MasonError("cfe:unresolved", 123)


def test_str_format_is_identifier_colon_space_message():
    exc = MasonError("cfe:unresolved", "run `mason doctor` to see why")
    assert str(exc) == "cfe:unresolved: run `mason doctor` to see why"


def test_mason_error_is_an_exception_subclass():
    assert issubclass(MasonError, Exception)
    with pytest.raises(MasonError):
        raise MasonError("cfe:unresolved", "boom")


# --- Story 1.6: CfeImportFloorError -----------------------------------------


def test_cfe_import_floor_error_identifier():
    exc = CfeImportFloorError(missing=("truststore", "ruamel.yaml"), interpreter="/opt/py")
    assert exc.identifier == "cfe:import-floor-missing"


def test_cfe_import_floor_error_stores_attributes():
    exc = CfeImportFloorError(missing=("truststore", "ruamel.yaml"), interpreter="/opt/py")
    assert exc.missing == ("truststore", "ruamel.yaml")
    assert exc.interpreter == "/opt/py"


def test_cfe_import_floor_error_message_names_every_missing_module_and_interpreter():
    exc = CfeImportFloorError(missing=("truststore", "ruamel.yaml"), interpreter="/opt/py")
    assert "truststore" in str(exc)
    assert "ruamel.yaml" in str(exc)
    assert "/opt/py" in str(exc)


def test_cfe_import_floor_error_is_a_mason_error():
    assert issubclass(CfeImportFloorError, MasonError)
    with pytest.raises(MasonError):
        raise CfeImportFloorError(missing=("pyyaml",), interpreter="/opt/py")


def test_cfe_import_floor_error_single_missing_module():
    exc = CfeImportFloorError(missing=("pyyaml",), interpreter="/usr/bin/python3")
    assert "pyyaml" in str(exc)
    assert "/usr/bin/python3" in str(exc)


def test_cfe_import_floor_error_rejects_empty_missing():
    """An import-floor error naming nothing missing is incoherent -- review
    pass (2026-08-09): the constructor now enforces this, matching
    `MasonError`'s own validation rigor rather than only claiming it in
    prose."""
    with pytest.raises(ValueError):
        CfeImportFloorError(missing=(), interpreter="/opt/py")


def test_cfe_import_floor_error_coerces_missing_to_a_tuple():
    """A caller passing a mutable `list` must not silently defeat the
    immutable-shape convention every other dataclass in this story
    follows."""
    exc = CfeImportFloorError(missing=["pyyaml", "requests"], interpreter="/opt/py")
    assert exc.missing == ("pyyaml", "requests")
    assert isinstance(exc.missing, tuple)


# --- Story 1.7: CfeUnresolvedError -------------------------------------------


def test_cfe_unresolved_error_identifier():
    exc = CfeUnresolvedError()
    assert exc.identifier == "cfe:unresolved"


def test_cfe_unresolved_error_message_names_all_four_step_names():
    exc = CfeUnresolvedError()
    for step_name in ("flag", "environment", "cwd-walk", "not-found"):
        assert step_name in str(exc)


def test_cfe_unresolved_error_message_names_how_to_satisfy_the_first_three():
    exc = CfeUnresolvedError()
    message = str(exc)
    assert "--cfe-root" in message
    assert "MASON_CFE_ROOT" in message
    assert ".claude/scripts/conda-forge-expert" in message


def test_cfe_unresolved_error_is_a_mason_error():
    assert issubclass(CfeUnresolvedError, MasonError)
    with pytest.raises(MasonError):
        raise CfeUnresolvedError()


def test_cfe_unresolved_error_takes_no_constructor_arguments():
    with pytest.raises(TypeError):
        CfeUnresolvedError("cfe:unresolved")  # type: ignore[call-arg]


def test_cfe_unresolved_error_str_format_is_identifier_colon_space_message():
    exc = CfeUnresolvedError()
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_cfe_unresolved_error_survives_deepcopy():
    """Review pass (2026-08-09): `Exception.__reduce__` reconstructs via
    `cls(*self.args)`, but `MasonError.__init__` sets `self.args` to a
    two-item tuple while this class's constructor takes zero arguments --
    without the `__reduce__` override, this would raise `TypeError` instead
    of round-tripping."""
    original = CfeUnresolvedError()
    clone = copy.deepcopy(original)
    assert isinstance(clone, CfeUnresolvedError)
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_cfe_unresolved_error_survives_pickle_round_trip():
    original = CfeUnresolvedError()
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, CfeUnresolvedError)
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 2.1: CfeTimeoutError -----------------------------------------------


def test_cfe_timeout_error_identifier():
    exc = CfeTimeoutError(script="validate_recipe", timeout=120.0)
    assert exc.identifier == "cfe:timeout"


def test_cfe_timeout_error_stores_attributes():
    exc = CfeTimeoutError(script="submit_pr", timeout=300.0)
    assert exc.script == "submit_pr"
    assert exc.timeout == 300.0


def test_cfe_timeout_error_message_names_the_script_key_and_timeout_value():
    exc = CfeTimeoutError(script="validate_recipe", timeout=120.0)
    message = str(exc)
    assert "validate_recipe" in message
    assert "120.0" in message


def test_cfe_timeout_error_is_a_mason_error():
    assert issubclass(CfeTimeoutError, MasonError)
    with pytest.raises(MasonError):
        raise CfeTimeoutError(script="submit_pr", timeout=300.0)


def test_cfe_timeout_error_str_format_is_identifier_colon_space_message():
    exc = CfeTimeoutError(script="validate_recipe", timeout=45.5)
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_cfe_timeout_error_survives_deepcopy():
    """Review pass (2026-08-11): unlike `CfeUnresolvedError` (whose
    zero-argument constructor immediately mismatches `self.args`'s two
    items and raises `TypeError` without a `__reduce__` override), this
    class's constructor also takes two arguments -- so without the override
    below, `cls(*self.args)` would NOT raise, but would silently reconstruct
    with `script == "cfe:timeout"` (the identifier) and `timeout` bound to
    the built message string (not a number), corrupting the clone instead
    of failing loudly."""
    original = CfeTimeoutError(script="validate_recipe", timeout=120.0)
    clone = copy.deepcopy(original)
    assert isinstance(clone, CfeTimeoutError)
    assert clone.script == original.script
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_cfe_timeout_error_survives_pickle_round_trip():
    original = CfeTimeoutError(script="submit_pr", timeout=300.0)
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, CfeTimeoutError)
    assert clone.script == original.script
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.1: EngineAbsentError --------------------------------------------


def test_engine_absent_error_identifier():
    exc = EngineAbsentError(name="conda-lock", conda_package="conda-lock")
    assert exc.identifier == "engine:absent"


def test_engine_absent_error_stores_attributes():
    exc = EngineAbsentError(name="build", conda_package="python-build")
    assert exc.name == "build"
    assert exc.conda_package == "python-build"


def test_engine_absent_error_message_names_the_engine_and_its_conda_package():
    exc = EngineAbsentError(name="build", conda_package="python-build")
    message = str(exc)
    assert "build" in message
    assert "python-build" in message


def test_engine_absent_error_is_a_mason_error():
    assert issubclass(EngineAbsentError, MasonError)
    with pytest.raises(MasonError):
        raise EngineAbsentError(name="pixi", conda_package="pixi")


def test_engine_absent_error_str_format_is_identifier_colon_space_message():
    exc = EngineAbsentError(name="twine", conda_package="twine")
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_engine_absent_error_rejects_empty_name():
    with pytest.raises(ValueError):
        EngineAbsentError(name="", conda_package="pixi")


def test_engine_absent_error_rejects_empty_conda_package():
    with pytest.raises(ValueError):
        EngineAbsentError(name="pixi", conda_package="")


def test_engine_absent_error_rejects_whitespace_only_name():
    with pytest.raises(ValueError):
        EngineAbsentError(name="   ", conda_package="pixi")


def test_engine_absent_error_survives_deepcopy():
    """Review pass (2026-08-13): mirrors `CfeTimeoutError`'s own deepcopy
    guard -- without the `__reduce__` override, `cls(*self.args)` would
    reconstruct with `name == "engine:absent"` (the identifier) and
    `conda_package` bound to the built message string, corrupting the
    clone's `.args`/`repr()` instead of failing loudly."""
    original = EngineAbsentError(name="pixi", conda_package="pixi")
    clone = copy.deepcopy(original)
    assert isinstance(clone, EngineAbsentError)
    assert clone.name == original.name
    assert clone.conda_package == original.conda_package
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_engine_absent_error_survives_pickle_round_trip():
    original = EngineAbsentError(name="build", conda_package="python-build")
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, EngineAbsentError)
    assert clone.name == original.name
    assert clone.conda_package == original.conda_package
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.2: PackageVersionMismatchError ----------------------------------

_WHEEL_PATH = "/proj/dist/pkg-0.1.0-py3-none-any.whl"
_CONDA_PATH = "/proj/dist-conda/pkg-0.2.0-abc123_0.conda"


def test_package_version_mismatch_error_identifier():
    exc = PackageVersionMismatchError(
        wheel_version="0.1.0",
        conda_version="0.2.0",
        wheel_path=_WHEEL_PATH,
        conda_path=_CONDA_PATH,
    )
    assert exc.identifier == "package:version-mismatch"


def test_package_version_mismatch_error_stores_attributes():
    exc = PackageVersionMismatchError(
        wheel_version="0.1.0",
        conda_version="0.2.0",
        wheel_path=_WHEEL_PATH,
        conda_path=_CONDA_PATH,
    )
    assert exc.wheel_version == "0.1.0"
    assert exc.conda_version == "0.2.0"
    assert exc.wheel_path == _WHEEL_PATH
    assert exc.conda_path == _CONDA_PATH


def test_package_version_mismatch_error_message_names_both_versions_and_both_paths():
    exc = PackageVersionMismatchError(
        wheel_version="0.1.0",
        conda_version="0.2.0",
        wheel_path=_WHEEL_PATH,
        conda_path=_CONDA_PATH,
    )
    message = str(exc)
    assert "0.1.0" in message
    assert "0.2.0" in message
    assert _WHEEL_PATH in message
    assert _CONDA_PATH in message


def test_package_version_mismatch_error_is_a_mason_error():
    assert issubclass(PackageVersionMismatchError, MasonError)
    with pytest.raises(MasonError):
        raise PackageVersionMismatchError(
            wheel_version="0.1.0",
            conda_version="0.2.0",
            wheel_path=_WHEEL_PATH,
            conda_path=_CONDA_PATH,
        )


def test_package_version_mismatch_error_str_format_is_identifier_colon_space_message():
    exc = PackageVersionMismatchError(
        wheel_version="0.1.0",
        conda_version="0.2.0",
        wheel_path=_WHEEL_PATH,
        conda_path=_CONDA_PATH,
    )
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_package_version_mismatch_error_rejects_empty_wheel_version():
    with pytest.raises(ValueError):
        PackageVersionMismatchError(
            wheel_version="",
            conda_version="0.2.0",
            wheel_path=_WHEEL_PATH,
            conda_path=_CONDA_PATH,
        )


def test_package_version_mismatch_error_rejects_empty_conda_version():
    with pytest.raises(ValueError):
        PackageVersionMismatchError(
            wheel_version="0.1.0",
            conda_version="",
            wheel_path=_WHEEL_PATH,
            conda_path=_CONDA_PATH,
        )


def test_package_version_mismatch_error_rejects_whitespace_only_wheel_version():
    with pytest.raises(ValueError):
        PackageVersionMismatchError(
            wheel_version="   ",
            conda_version="0.2.0",
            wheel_path=_WHEEL_PATH,
            conda_path=_CONDA_PATH,
        )


def test_package_version_mismatch_error_rejects_empty_wheel_path():
    with pytest.raises(ValueError):
        PackageVersionMismatchError(
            wheel_version="0.1.0",
            conda_version="0.2.0",
            wheel_path="",
            conda_path=_CONDA_PATH,
        )


def test_package_version_mismatch_error_rejects_empty_conda_path():
    with pytest.raises(ValueError):
        PackageVersionMismatchError(
            wheel_version="0.1.0",
            conda_version="0.2.0",
            wheel_path=_WHEEL_PATH,
            conda_path="",
        )


def test_package_version_mismatch_error_survives_deepcopy():
    """Mirrors `EngineAbsentError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would reconstruct with
    `wheel_version == "package:version-mismatch"` (the identifier) and
    `conda_version` bound to the built message string, corrupting the
    clone's `.args`/`repr()` instead of failing loudly."""
    original = PackageVersionMismatchError(
        wheel_version="0.1.0",
        conda_version="0.2.0",
        wheel_path=_WHEEL_PATH,
        conda_path=_CONDA_PATH,
    )
    clone = copy.deepcopy(original)
    assert isinstance(clone, PackageVersionMismatchError)
    assert clone.wheel_version == original.wheel_version
    assert clone.conda_version == original.conda_version
    assert clone.wheel_path == original.wheel_path
    assert clone.conda_path == original.conda_path
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_package_version_mismatch_error_survives_pickle_round_trip():
    original = PackageVersionMismatchError(
        wheel_version="0.1.0",
        conda_version="0.2.0",
        wheel_path=_WHEEL_PATH,
        conda_path=_CONDA_PATH,
    )
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, PackageVersionMismatchError)
    assert clone.wheel_version == original.wheel_version
    assert clone.conda_version == original.conda_version
    assert clone.wheel_path == original.wheel_path
    assert clone.conda_path == original.conda_path
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.2 (review pass, 2026-08-13): PackageBuildTimeoutError -----------


def test_package_build_timeout_error_identifier():
    exc = PackageBuildTimeoutError(engine="build", timeout=600.0)
    assert exc.identifier == "package:build-timeout"


def test_package_build_timeout_error_stores_attributes():
    exc = PackageBuildTimeoutError(engine="pixi", timeout=600.0)
    assert exc.engine == "pixi"
    assert exc.timeout == 600.0


def test_package_build_timeout_error_message_names_the_engine_and_timeout_value():
    exc = PackageBuildTimeoutError(engine="build", timeout=600.0)
    message = str(exc)
    assert "build" in message
    assert "600.0" in message


def test_package_build_timeout_error_is_a_mason_error():
    assert issubclass(PackageBuildTimeoutError, MasonError)
    with pytest.raises(MasonError):
        raise PackageBuildTimeoutError(engine="pixi", timeout=600.0)


def test_package_build_timeout_error_str_format_is_identifier_colon_space_message():
    exc = PackageBuildTimeoutError(engine="build", timeout=600.0)
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_package_build_timeout_error_survives_deepcopy():
    """Mirrors `CfeTimeoutError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would reconstruct with
    `engine == "package:build-timeout"` (the identifier) and `timeout`
    bound to the built message string, corrupting the clone instead of
    failing loudly."""
    original = PackageBuildTimeoutError(engine="build", timeout=600.0)
    clone = copy.deepcopy(original)
    assert isinstance(clone, PackageBuildTimeoutError)
    assert clone.engine == original.engine
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_package_build_timeout_error_survives_pickle_round_trip():
    original = PackageBuildTimeoutError(engine="pixi", timeout=600.0)
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, PackageBuildTimeoutError)
    assert clone.engine == original.engine
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.2 (review pass, 2026-08-13): PackageProjectPathError ------------


def test_package_project_path_error_identifier():
    exc = PackageProjectPathError(project_path="/no/such/dir", reason="No such file or directory")
    assert exc.identifier == "package:project-path-invalid"


def test_package_project_path_error_stores_attributes():
    exc = PackageProjectPathError(project_path="/no/such/dir", reason="No such file or directory")
    assert exc.project_path == "/no/such/dir"
    assert exc.reason == "No such file or directory"


def test_package_project_path_error_message_names_the_path_and_reason():
    exc = PackageProjectPathError(project_path="/no/such/dir", reason="No such file or directory")
    message = str(exc)
    assert "/no/such/dir" in message
    assert "No such file or directory" in message


def test_package_project_path_error_is_a_mason_error():
    assert issubclass(PackageProjectPathError, MasonError)
    with pytest.raises(MasonError):
        raise PackageProjectPathError(project_path="/no/such/dir", reason="boom")


def test_package_project_path_error_str_format_is_identifier_colon_space_message():
    exc = PackageProjectPathError(project_path="/no/such/dir", reason="boom")
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_package_project_path_error_rejects_empty_project_path():
    with pytest.raises(ValueError):
        PackageProjectPathError(project_path="", reason="boom")


def test_package_project_path_error_rejects_empty_reason():
    with pytest.raises(ValueError):
        PackageProjectPathError(project_path="/no/such/dir", reason="")


def test_package_project_path_error_rejects_whitespace_only_project_path():
    with pytest.raises(ValueError):
        PackageProjectPathError(project_path="   ", reason="boom")


def test_package_project_path_error_survives_deepcopy():
    """Mirrors `CfeTimeoutError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would reconstruct with
    `project_path == "package:project-path-invalid"` (the identifier) and
    `reason` bound to the built message string, corrupting the clone
    instead of failing loudly."""
    original = PackageProjectPathError(project_path="/no/such/dir", reason="boom")
    clone = copy.deepcopy(original)
    assert isinstance(clone, PackageProjectPathError)
    assert clone.project_path == original.project_path
    assert clone.reason == original.reason
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_package_project_path_error_survives_pickle_round_trip():
    original = PackageProjectPathError(project_path="/no/such/dir", reason="boom")
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, PackageProjectPathError)
    assert clone.project_path == original.project_path
    assert clone.reason == original.reason
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.3: InvalidShipTargetError ----------------------------------------


def test_invalid_ship_target_error_identifier():
    exc = InvalidShipTargetError("bogus")
    assert exc.identifier == "ship:invalid-target"


def test_invalid_ship_target_error_stores_attributes():
    exc = InvalidShipTargetError("bogus")
    assert exc.value == "bogus"


def test_invalid_ship_target_error_message_names_the_value_and_the_four_valid_forms():
    """Story 3.9/FR-50: `pypi-test` joins the listed valid forms."""
    exc = InvalidShipTargetError("bogus")
    message = str(exc)
    assert "bogus" in message
    assert "pypi" in message
    assert "pypi-test" in message
    assert "conda-forge" in message
    assert "channel:<name>" in message


def test_invalid_ship_target_error_is_a_mason_error():
    assert issubclass(InvalidShipTargetError, MasonError)
    with pytest.raises(MasonError):
        raise InvalidShipTargetError("bogus")


def test_invalid_ship_target_error_str_format_is_identifier_colon_space_message():
    exc = InvalidShipTargetError("bogus")
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_invalid_ship_target_error_rejects_empty_value():
    with pytest.raises(ValueError):
        InvalidShipTargetError("")


def test_invalid_ship_target_error_rejects_non_string_value():
    with pytest.raises(ValueError):
        InvalidShipTargetError(None)  # type: ignore[arg-type]


def test_invalid_ship_target_error_rejects_whitespace_only_value():
    with pytest.raises(ValueError):
        InvalidShipTargetError("   ")


def test_invalid_ship_target_error_survives_deepcopy():
    """Mirrors `PackageProjectPathError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would reconstruct with
    `value == "ship:invalid-target"` (the identifier), corrupting the
    clone's `.args`/`repr()` instead of failing loudly."""
    original = InvalidShipTargetError("bogus")
    clone = copy.deepcopy(original)
    assert isinstance(clone, InvalidShipTargetError)
    assert clone.value == original.value
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_invalid_ship_target_error_survives_pickle_round_trip():
    original = InvalidShipTargetError("bogus")
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, InvalidShipTargetError)
    assert clone.value == original.value
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.4: ShipCredentialMissingError ------------------------------------


def test_ship_credential_missing_error_identifier():
    exc = ShipCredentialMissingError(missing=("TWINE_USERNAME", "TWINE_PASSWORD"))
    assert exc.identifier == "ship:credential-missing"


def test_ship_credential_missing_error_stores_attributes():
    exc = ShipCredentialMissingError(missing=("TWINE_PASSWORD",))
    assert exc.missing == ("TWINE_PASSWORD",)


def test_ship_credential_missing_error_message_names_every_missing_entry():
    exc = ShipCredentialMissingError(missing=("TWINE_USERNAME", "TWINE_PASSWORD"))
    message = str(exc)
    assert "TWINE_USERNAME" in message
    assert "TWINE_PASSWORD" in message


def test_ship_credential_missing_error_single_missing_entry():
    exc = ShipCredentialMissingError(missing=("TWINE_PASSWORD",))
    assert "TWINE_PASSWORD" in str(exc)
    assert "TWINE_USERNAME" not in str(exc)


def test_ship_credential_missing_error_message_names_no_specific_repository():
    """Review pass 3: `ship_pypi` raises this identically for a real `pypi`
    ship and a `pypi-test` rehearsal (AD-26), and the message is built
    BEFORE `ship_pypi` knows which -- it must not claim the upload targets
    "pypi" specifically ("PyPI upload credential(s)" as the generic
    credential-type description is fine and unchanged; the directional
    claim "shipping to pypi" was the part that was wrong for a `pypi-test`
    invocation, and is what this test guards)."""
    exc = ShipCredentialMissingError(missing=("TWINE_USERNAME",))
    assert "to pypi" not in str(exc).lower()


def test_ship_credential_missing_error_is_a_mason_error():
    assert issubclass(ShipCredentialMissingError, MasonError)
    with pytest.raises(MasonError):
        raise ShipCredentialMissingError(missing=("TWINE_USERNAME",))


def test_ship_credential_missing_error_str_format_is_identifier_colon_space_message():
    exc = ShipCredentialMissingError(missing=("TWINE_USERNAME",))
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_ship_credential_missing_error_coerces_missing_to_a_tuple():
    exc = ShipCredentialMissingError(missing=["TWINE_USERNAME", "TWINE_PASSWORD"])
    assert exc.missing == ("TWINE_USERNAME", "TWINE_PASSWORD")
    assert isinstance(exc.missing, tuple)


def test_ship_credential_missing_error_rejects_empty_missing():
    with pytest.raises(ValueError):
        ShipCredentialMissingError(missing=())


def test_ship_credential_missing_error_rejects_a_non_str_missing_item():
    with pytest.raises(ValueError):
        ShipCredentialMissingError(missing=(None,))  # type: ignore[list-item]


def test_ship_credential_missing_error_rejects_a_whitespace_only_missing_item():
    with pytest.raises(ValueError):
        ShipCredentialMissingError(missing=("   ",))


def test_ship_credential_missing_error_survives_deepcopy():
    """Mirrors `InvalidShipTargetError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would reconstruct with
    `missing == "ship:credential-missing"` (the identifier), corrupting the
    clone's `.args`/`repr()` instead of failing loudly."""
    original = ShipCredentialMissingError(missing=("TWINE_USERNAME", "TWINE_PASSWORD"))
    clone = copy.deepcopy(original)
    assert isinstance(clone, ShipCredentialMissingError)
    assert clone.missing == original.missing
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_ship_credential_missing_error_survives_pickle_round_trip():
    original = ShipCredentialMissingError(missing=("TWINE_PASSWORD",))
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, ShipCredentialMissingError)
    assert clone.missing == original.missing
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.4: ShipUploadTimeoutError -----------------------------------------


def test_ship_upload_timeout_error_identifier():
    exc = ShipUploadTimeoutError(timeout=300.0)
    assert exc.identifier == "ship:upload-timeout"


def test_ship_upload_timeout_error_stores_attributes():
    exc = ShipUploadTimeoutError(timeout=300.0)
    assert exc.timeout == 300.0


def test_ship_upload_timeout_error_message_names_the_timeout_value():
    exc = ShipUploadTimeoutError(timeout=300.0)
    assert "300.0" in str(exc)


def test_ship_upload_timeout_error_is_a_mason_error():
    assert issubclass(ShipUploadTimeoutError, MasonError)
    with pytest.raises(MasonError):
        raise ShipUploadTimeoutError(timeout=300.0)


def test_ship_upload_timeout_error_str_format_is_identifier_colon_space_message():
    exc = ShipUploadTimeoutError(timeout=45.5)
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_ship_upload_timeout_error_survives_deepcopy():
    """Mirrors `PackageBuildTimeoutError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would reconstruct with
    `timeout == "ship:upload-timeout"` (the identifier), corrupting the
    clone instead of failing loudly."""
    original = ShipUploadTimeoutError(timeout=300.0)
    clone = copy.deepcopy(original)
    assert isinstance(clone, ShipUploadTimeoutError)
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_ship_upload_timeout_error_survives_pickle_round_trip():
    original = ShipUploadTimeoutError(timeout=300.0)
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, ShipUploadTimeoutError)
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.5: ShipChannelCredentialMissingError ------------------------------


def test_ship_channel_credential_missing_error_identifier():
    exc = ShipChannelCredentialMissingError(missing=("PREFIX_API_KEY",))
    assert exc.identifier == "ship:channel-credential-missing"


def test_ship_channel_credential_missing_error_stores_attributes():
    exc = ShipChannelCredentialMissingError(missing=("PREFIX_API_KEY",))
    assert exc.missing == ("PREFIX_API_KEY",)


def test_ship_channel_credential_missing_error_message_names_every_missing_entry():
    exc = ShipChannelCredentialMissingError(missing=("PREFIX_API_KEY",))
    assert "PREFIX_API_KEY" in str(exc)


def test_ship_channel_credential_missing_error_message_names_the_channel_upload():
    exc = ShipChannelCredentialMissingError(missing=("PREFIX_API_KEY",))
    assert "channel" in str(exc).lower()


def test_ship_channel_credential_missing_error_is_a_mason_error():
    assert issubclass(ShipChannelCredentialMissingError, MasonError)
    with pytest.raises(MasonError):
        raise ShipChannelCredentialMissingError(missing=("PREFIX_API_KEY",))


def test_ship_channel_credential_missing_error_str_format_is_identifier_colon_space_message():
    exc = ShipChannelCredentialMissingError(missing=("PREFIX_API_KEY",))
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_ship_channel_credential_missing_error_coerces_missing_to_a_tuple():
    exc = ShipChannelCredentialMissingError(missing=["PREFIX_API_KEY"])
    assert exc.missing == ("PREFIX_API_KEY",)
    assert isinstance(exc.missing, tuple)


def test_ship_channel_credential_missing_error_rejects_empty_missing():
    with pytest.raises(ValueError):
        ShipChannelCredentialMissingError(missing=())


def test_ship_channel_credential_missing_error_rejects_a_non_str_missing_item():
    with pytest.raises(ValueError):
        ShipChannelCredentialMissingError(missing=(None,))  # type: ignore[list-item]


def test_ship_channel_credential_missing_error_rejects_a_whitespace_only_missing_item():
    with pytest.raises(ValueError):
        ShipChannelCredentialMissingError(missing=("   ",))


def test_ship_channel_credential_missing_error_survives_deepcopy():
    """Mirrors `ShipCredentialMissingError`'s own deepcopy guard: without
    the `__reduce__` override, `cls(*self.args)` would reconstruct with
    `missing == "ship:channel-credential-missing"` (the identifier),
    corrupting the clone's `.args`/`repr()` instead of failing loudly."""
    original = ShipChannelCredentialMissingError(missing=("PREFIX_API_KEY",))
    clone = copy.deepcopy(original)
    assert isinstance(clone, ShipChannelCredentialMissingError)
    assert clone.missing == original.missing
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_ship_channel_credential_missing_error_survives_pickle_round_trip():
    original = ShipChannelCredentialMissingError(missing=("PREFIX_API_KEY",))
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, ShipChannelCredentialMissingError)
    assert clone.missing == original.missing
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.5: ShipChannelUploadTimeoutError -----------------------------------


def test_ship_channel_upload_timeout_error_identifier():
    exc = ShipChannelUploadTimeoutError(timeout=300.0)
    assert exc.identifier == "ship:channel-upload-timeout"


def test_ship_channel_upload_timeout_error_stores_attributes():
    exc = ShipChannelUploadTimeoutError(timeout=300.0)
    assert exc.timeout == 300.0


def test_ship_channel_upload_timeout_error_message_names_the_timeout_value():
    exc = ShipChannelUploadTimeoutError(timeout=300.0)
    assert "300.0" in str(exc)


def test_ship_channel_upload_timeout_error_is_a_mason_error():
    assert issubclass(ShipChannelUploadTimeoutError, MasonError)
    with pytest.raises(MasonError):
        raise ShipChannelUploadTimeoutError(timeout=300.0)


def test_ship_channel_upload_timeout_error_str_format_is_identifier_colon_space_message():
    exc = ShipChannelUploadTimeoutError(timeout=45.5)
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_ship_channel_upload_timeout_error_survives_deepcopy():
    """Mirrors `ShipUploadTimeoutError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would reconstruct with
    `timeout == "ship:channel-upload-timeout"` (the identifier), corrupting
    the clone instead of failing loudly."""
    original = ShipChannelUploadTimeoutError(timeout=300.0)
    clone = copy.deepcopy(original)
    assert isinstance(clone, ShipChannelUploadTimeoutError)
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_ship_channel_upload_timeout_error_survives_pickle_round_trip():
    original = ShipChannelUploadTimeoutError(timeout=300.0)
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, ShipChannelUploadTimeoutError)
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.6: ShipCondaForgeRecipeMissingError -------------------------------


def test_ship_conda_forge_recipe_missing_error_identifier():
    exc = ShipCondaForgeRecipeMissingError()
    assert exc.identifier == "ship:conda-forge-recipe-missing"


def test_ship_conda_forge_recipe_missing_error_message_names_mason_recipe_new():
    exc = ShipCondaForgeRecipeMissingError()
    assert "mason recipe new" in str(exc)


def test_ship_conda_forge_recipe_missing_error_is_a_mason_error():
    assert issubclass(ShipCondaForgeRecipeMissingError, MasonError)
    with pytest.raises(MasonError):
        raise ShipCondaForgeRecipeMissingError()


def test_ship_conda_forge_recipe_missing_error_str_format_is_identifier_colon_space_message():
    exc = ShipCondaForgeRecipeMissingError()
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_ship_conda_forge_recipe_missing_error_takes_no_constructor_arguments():
    with pytest.raises(TypeError):
        ShipCondaForgeRecipeMissingError("bogus")  # type: ignore[call-arg]


def test_ship_conda_forge_recipe_missing_error_survives_deepcopy():
    """Mirrors `CfeUnresolvedError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would raise `TypeError` --
    `MasonError.__init__` sets `self.args` to a two-item tuple, but this
    class's constructor takes zero arguments."""
    original = ShipCondaForgeRecipeMissingError()
    clone = copy.deepcopy(original)
    assert isinstance(clone, ShipCondaForgeRecipeMissingError)
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_ship_conda_forge_recipe_missing_error_survives_pickle_round_trip():
    original = ShipCondaForgeRecipeMissingError()
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, ShipCondaForgeRecipeMissingError)
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.6: ShipCondaForgeRecipeLocationError ------------------------------

_RECIPE_PATH = "/some/other/place/foo"
_EXPECTED_PATH = "/fake/cfe/recipes/foo"


def test_ship_conda_forge_recipe_location_error_identifier():
    exc = ShipCondaForgeRecipeLocationError(_RECIPE_PATH, _EXPECTED_PATH)
    assert exc.identifier == "ship:conda-forge-recipe-location"


def test_ship_conda_forge_recipe_location_error_stores_attributes():
    exc = ShipCondaForgeRecipeLocationError(_RECIPE_PATH, _EXPECTED_PATH)
    assert exc.recipe_path == _RECIPE_PATH
    assert exc.expected_path == _EXPECTED_PATH


def test_ship_conda_forge_recipe_location_error_message_names_both_paths():
    exc = ShipCondaForgeRecipeLocationError(_RECIPE_PATH, _EXPECTED_PATH)
    message = str(exc)
    assert _RECIPE_PATH in message
    assert _EXPECTED_PATH in message


def test_ship_conda_forge_recipe_location_error_is_a_mason_error():
    assert issubclass(ShipCondaForgeRecipeLocationError, MasonError)
    with pytest.raises(MasonError):
        raise ShipCondaForgeRecipeLocationError(_RECIPE_PATH, _EXPECTED_PATH)


def test_ship_conda_forge_recipe_location_error_str_format_is_identifier_colon_space_message():
    exc = ShipCondaForgeRecipeLocationError(_RECIPE_PATH, _EXPECTED_PATH)
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_ship_conda_forge_recipe_location_error_rejects_empty_recipe_path():
    with pytest.raises(ValueError):
        ShipCondaForgeRecipeLocationError("", _EXPECTED_PATH)


def test_ship_conda_forge_recipe_location_error_rejects_empty_expected_path():
    with pytest.raises(ValueError):
        ShipCondaForgeRecipeLocationError(_RECIPE_PATH, "")


def test_ship_conda_forge_recipe_location_error_rejects_whitespace_only_recipe_path():
    with pytest.raises(ValueError):
        ShipCondaForgeRecipeLocationError("   ", _EXPECTED_PATH)


def test_ship_conda_forge_recipe_location_error_rejects_whitespace_only_expected_path():
    with pytest.raises(ValueError):
        ShipCondaForgeRecipeLocationError(_RECIPE_PATH, "   ")


def test_ship_conda_forge_recipe_location_error_rejects_non_string_recipe_path():
    with pytest.raises(ValueError):
        ShipCondaForgeRecipeLocationError(None, _EXPECTED_PATH)  # type: ignore[arg-type]


def test_ship_conda_forge_recipe_location_error_rejects_non_string_expected_path():
    with pytest.raises(ValueError):
        ShipCondaForgeRecipeLocationError(_RECIPE_PATH, None)  # type: ignore[arg-type]


def test_ship_conda_forge_recipe_location_error_survives_deepcopy():
    """Mirrors `PackageProjectPathError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would reconstruct with
    `recipe_path == "ship:conda-forge-recipe-location"` (the identifier)
    and `expected_path` bound to the built message string, corrupting the
    clone instead of failing loudly."""
    original = ShipCondaForgeRecipeLocationError(_RECIPE_PATH, _EXPECTED_PATH)
    clone = copy.deepcopy(original)
    assert isinstance(clone, ShipCondaForgeRecipeLocationError)
    assert clone.recipe_path == original.recipe_path
    assert clone.expected_path == original.expected_path
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_ship_conda_forge_recipe_location_error_survives_pickle_round_trip():
    original = ShipCondaForgeRecipeLocationError(_RECIPE_PATH, _EXPECTED_PATH)
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, ShipCondaForgeRecipeLocationError)
    assert clone.recipe_path == original.recipe_path
    assert clone.expected_path == original.expected_path
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 4.1: EnvironmentLockTimeoutError -------------------------------------


def test_environment_lock_timeout_error_identifier():
    exc = EnvironmentLockTimeoutError(timeout=600.0)
    assert exc.identifier == "environment:lock-timeout"


def test_environment_lock_timeout_error_stores_attributes():
    exc = EnvironmentLockTimeoutError(timeout=600.0)
    assert exc.timeout == 600.0


def test_environment_lock_timeout_error_message_names_the_timeout_value():
    exc = EnvironmentLockTimeoutError(timeout=600.0)
    assert "600.0" in str(exc)


def test_environment_lock_timeout_error_is_a_mason_error():
    assert issubclass(EnvironmentLockTimeoutError, MasonError)
    with pytest.raises(MasonError):
        raise EnvironmentLockTimeoutError(timeout=600.0)


def test_environment_lock_timeout_error_str_format_is_identifier_colon_space_message():
    exc = EnvironmentLockTimeoutError(timeout=45.5)
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_environment_lock_timeout_error_survives_deepcopy():
    """Mirrors `ShipUploadTimeoutError`'s own deepcopy guard: without the
    `__reduce__` override, `cls(*self.args)` would reconstruct with
    `timeout == "environment:lock-timeout"` (the identifier), corrupting
    the clone instead of failing loudly."""
    original = EnvironmentLockTimeoutError(timeout=600.0)
    clone = copy.deepcopy(original)
    assert isinstance(clone, EnvironmentLockTimeoutError)
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_environment_lock_timeout_error_survives_pickle_round_trip():
    original = EnvironmentLockTimeoutError(timeout=600.0)
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, EnvironmentLockTimeoutError)
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 4.4: EnvironmentLockfileMissingError -------------------------------


def test_environment_lockfile_missing_error_identifier():
    exc = EnvironmentLockfileMissingError("/no/such/lock.yml")
    assert exc.identifier == "environment:lockfile-missing"


def test_environment_lockfile_missing_error_stores_attributes():
    exc = EnvironmentLockfileMissingError("/no/such/lock.yml")
    assert exc.lockfile_path == "/no/such/lock.yml"


def test_environment_lockfile_missing_error_message_names_the_path():
    exc = EnvironmentLockfileMissingError("/no/such/lock.yml")
    assert "/no/such/lock.yml" in str(exc)


def test_environment_lockfile_missing_error_is_a_mason_error():
    assert issubclass(EnvironmentLockfileMissingError, MasonError)
    with pytest.raises(MasonError):
        raise EnvironmentLockfileMissingError("/no/such/lock.yml")


def test_environment_lockfile_missing_error_str_format_is_identifier_colon_space_message():
    exc = EnvironmentLockfileMissingError("/no/such/lock.yml")
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_environment_lockfile_missing_error_accepts_an_empty_path():
    """Review pass, 2026-08-15: unlike most sibling classes, an empty
    `lockfile_path` is a real, reachable CLI input (`--lockfile ""`), not a
    caller bug -- construction must not raise so this class's own clean
    diagnostic reaches `main()`'s `except MasonError` handler."""
    exc = EnvironmentLockfileMissingError("")
    assert exc.lockfile_path == ""
    assert "no --lockfile path was given" in str(exc)


def test_environment_lockfile_missing_error_names_a_whitespace_only_path():
    """Review pass, 2026-08-15 second: the empty-path branch keyed on
    `.strip()`, so `--lockfile "   "` -- a path the user really did supply --
    was told "no --lockfile path was given". Only the genuinely empty string
    takes that branch."""
    exc = EnvironmentLockfileMissingError("   ")
    assert exc.lockfile_path == "   "
    assert "does not exist or is not a file" in str(exc)
    assert "no --lockfile path was given" not in str(exc)


def test_environment_lockfile_missing_error_rejects_a_non_str_path():
    with pytest.raises(TypeError):
        EnvironmentLockfileMissingError(None)


def test_environment_lockfile_missing_error_survives_deepcopy():
    original = EnvironmentLockfileMissingError("/no/such/lock.yml")
    clone = copy.deepcopy(original)
    assert isinstance(clone, EnvironmentLockfileMissingError)
    assert clone.lockfile_path == original.lockfile_path
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_environment_lockfile_missing_error_survives_pickle_round_trip():
    original = EnvironmentLockfileMissingError("/no/such/lock.yml")
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, EnvironmentLockfileMissingError)
    assert clone.lockfile_path == original.lockfile_path
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 4.4 (review pass, 2026-08-15): EnvironmentLockfileMalformedError ---


def test_environment_lockfile_malformed_error_identifier():
    exc = EnvironmentLockfileMalformedError("lock.yml", "'metadata'")
    assert exc.identifier == "environment:lockfile-malformed"


def test_environment_lockfile_malformed_error_stores_attributes():
    exc = EnvironmentLockfileMalformedError("lock.yml", "'metadata'")
    assert exc.lockfile_path == "lock.yml"
    assert exc.reason == "'metadata'"


def test_environment_lockfile_malformed_error_message_names_the_path_and_reason():
    exc = EnvironmentLockfileMalformedError("lock.yml", "'metadata'")
    message = str(exc)
    assert "lock.yml" in message
    assert "'metadata'" in message


def test_environment_lockfile_malformed_error_is_a_mason_error():
    assert issubclass(EnvironmentLockfileMalformedError, MasonError)
    with pytest.raises(MasonError):
        raise EnvironmentLockfileMalformedError("lock.yml", "boom")


def test_environment_lockfile_malformed_error_str_format_is_identifier_colon_space_message():
    exc = EnvironmentLockfileMalformedError("lock.yml", "boom")
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_environment_lockfile_malformed_error_rejects_empty_lockfile_path():
    with pytest.raises(ValueError):
        EnvironmentLockfileMalformedError("", "boom")


def test_environment_lockfile_malformed_error_rejects_empty_reason():
    with pytest.raises(ValueError):
        EnvironmentLockfileMalformedError("lock.yml", "")


def test_environment_lockfile_malformed_error_survives_deepcopy():
    original = EnvironmentLockfileMalformedError("lock.yml", "boom")
    clone = copy.deepcopy(original)
    assert isinstance(clone, EnvironmentLockfileMalformedError)
    assert clone.lockfile_path == original.lockfile_path
    assert clone.reason == original.reason
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_environment_lockfile_malformed_error_survives_pickle_round_trip():
    original = EnvironmentLockfileMalformedError("lock.yml", "boom")
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, EnvironmentLockfileMalformedError)
    assert clone.lockfile_path == original.lockfile_path
    assert clone.reason == original.reason
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 4.4: EnvironmentCheckTimeoutError ----------------------------------


def test_environment_check_timeout_error_identifier():
    exc = EnvironmentCheckTimeoutError(timeout=600.0)
    assert exc.identifier == "environment:check-timeout"


def test_environment_check_timeout_error_stores_attributes():
    exc = EnvironmentCheckTimeoutError(timeout=600.0)
    assert exc.timeout == 600.0


def test_environment_check_timeout_error_message_names_the_timeout_value():
    exc = EnvironmentCheckTimeoutError(timeout=600.0)
    assert "600.0" in str(exc)


def test_environment_check_timeout_error_is_a_mason_error():
    assert issubclass(EnvironmentCheckTimeoutError, MasonError)
    with pytest.raises(MasonError):
        raise EnvironmentCheckTimeoutError(timeout=600.0)


def test_environment_check_timeout_error_str_format_is_identifier_colon_space_message():
    exc = EnvironmentCheckTimeoutError(timeout=45.5)
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_environment_check_timeout_error_survives_deepcopy():
    original = EnvironmentCheckTimeoutError(timeout=600.0)
    clone = copy.deepcopy(original)
    assert isinstance(clone, EnvironmentCheckTimeoutError)
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_environment_check_timeout_error_survives_pickle_round_trip():
    original = EnvironmentCheckTimeoutError(timeout=600.0)
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, EnvironmentCheckTimeoutError)
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 4.2: EnvironmentManifestsNotFoundError -----------------------------

_FOUR_PATTERNS = ("pyproject.toml", "environment.yml", "requirements*.txt", "pixi.toml")


def test_environment_manifests_not_found_error_identifier():
    exc = EnvironmentManifestsNotFoundError("/proj", _FOUR_PATTERNS)
    assert exc.identifier == "environment:manifests-not-found"


def test_environment_manifests_not_found_error_stores_attributes():
    exc = EnvironmentManifestsNotFoundError("/proj", _FOUR_PATTERNS)
    assert exc.directory == "/proj"
    assert exc.filenames == _FOUR_PATTERNS


def test_environment_manifests_not_found_error_message_names_directory_and_filenames():
    exc = EnvironmentManifestsNotFoundError("/proj", _FOUR_PATTERNS)
    message = str(exc)
    assert "/proj" in message
    for pattern in _FOUR_PATTERNS:
        assert pattern in message


def test_environment_manifests_not_found_error_is_a_mason_error():
    assert issubclass(EnvironmentManifestsNotFoundError, MasonError)
    with pytest.raises(MasonError):
        raise EnvironmentManifestsNotFoundError("/proj", _FOUR_PATTERNS)


def test_environment_manifests_not_found_error_str_format_is_identifier_colon_space_message():
    exc = EnvironmentManifestsNotFoundError("/proj", _FOUR_PATTERNS)
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_environment_manifests_not_found_error_coerces_filenames_to_a_tuple():
    exc = EnvironmentManifestsNotFoundError("/proj", list(_FOUR_PATTERNS))
    assert exc.filenames == _FOUR_PATTERNS
    assert isinstance(exc.filenames, tuple)


def test_environment_manifests_not_found_error_rejects_empty_directory():
    with pytest.raises(ValueError):
        EnvironmentManifestsNotFoundError("", _FOUR_PATTERNS)


def test_environment_manifests_not_found_error_rejects_whitespace_only_directory():
    with pytest.raises(ValueError):
        EnvironmentManifestsNotFoundError("   ", _FOUR_PATTERNS)


def test_environment_manifests_not_found_error_rejects_empty_filenames():
    with pytest.raises(ValueError):
        EnvironmentManifestsNotFoundError("/proj", ())


def test_environment_manifests_not_found_error_rejects_a_blank_filenames_entry():
    """Every `filenames` entry must itself be a non-empty string (review
    pass, 2026-08-15, matching `ShipCredentialMissingError`'s identical
    per-entry check) -- a not-found error naming a blank pattern is exactly
    as incoherent as naming none at all."""
    with pytest.raises(ValueError):
        EnvironmentManifestsNotFoundError("/proj", ("pyproject.toml", ""))
    with pytest.raises(ValueError):
        EnvironmentManifestsNotFoundError("/proj", ("pyproject.toml", "   "))


def test_environment_manifests_not_found_error_survives_deepcopy():
    original = EnvironmentManifestsNotFoundError("/proj", _FOUR_PATTERNS)
    clone = copy.deepcopy(original)
    assert isinstance(clone, EnvironmentManifestsNotFoundError)
    assert clone.directory == original.directory
    assert clone.filenames == original.filenames
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_environment_manifests_not_found_error_survives_pickle_round_trip():
    original = EnvironmentManifestsNotFoundError("/proj", _FOUR_PATTERNS)
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, EnvironmentManifestsNotFoundError)
    assert clone.directory == original.directory
    assert clone.filenames == original.filenames
    assert clone.identifier == original.identifier
    assert clone.message == original.message
