"""Story 2.1 -- `models.py`: `CfeResult` construction/immutability, and
`DoctorReport`'s relocation-with-re-export sanity (the module now importing
it via `pyforge.mason.doctor` and the module now defining it via
`pyforge.mason.models` must be the identical class object, not two classes
that merely look alike).

Story 2.9 extends this file with `ShipState`/`ShipTargetResult` coverage:
construction/immutability mirroring `CfeResult`'s own tests, plus the one
property unique to `ShipState` -- its `StrEnum` members behave as plain
`str` under `json.dumps`/`str()`/`==` (the exact claim `models.py`'s own
Design Notes make about why `render_json`/`render_text` need no special
handling).

Story 3.3 extends this file again with `ShipTargetKind`/`ShipTarget`
coverage: exactly-three-members plus construction/immutability/equality,
mirroring `ShipTargetResult`'s own test shape.

Story 3.6 extends `DoctorReport`'s two direct construction sites with its
two new `conda_forge_ship_ready`/`conda_forge_ship_blockers` fields.

Story 3.7 extends this file once more with `ShipReceipt` coverage:
construction/immutability/equality mirroring the shapes above, plus the
`ok`-aggregation cases the spec's own I/O & Edge-Case Matrix names ("mixed
success", "one failure").

Story 3.9 extends `ShipTargetKind`'s coverage to its fourth member,
`PYPI_TEST` (FR-24, FR-50, AD-26) -- the "exactly three" test above becomes
"exactly four," mirroring its own established shape."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from pyforge.mason.engines import EngineStatus
from pyforge.mason.models import (
    CfeResult,
    DoctorReport,
    ShipReceipt,
    ShipState,
    ShipTarget,
    ShipTargetKind,
    ShipTargetResult,
)

# --- CfeResult ----------------------------------------------------------------


def test_cfe_result_constructs_with_all_four_fields():
    result = CfeResult(returncode=0, stdout="out", stderr="err", json_body={"ok": True})
    assert result.returncode == 0
    assert result.stdout == "out"
    assert result.stderr == "err"
    assert result.json_body == {"ok": True}


def test_cfe_result_json_body_accepts_none():
    result = CfeResult(returncode=1, stdout="plain text, no json", stderr="", json_body=None)
    assert result.json_body is None


def test_cfe_result_is_frozen():
    result = CfeResult(returncode=0, stdout="", stderr="", json_body=None)
    with pytest.raises(FrozenInstanceError):
        result.returncode = 1  # type: ignore[misc]


def test_cfe_result_equality_is_by_value():
    a = CfeResult(returncode=0, stdout="x", stderr="", json_body={"a": 1})
    b = CfeResult(returncode=0, stdout="x", stderr="", json_body={"a": 1})
    assert a == b


# --- DoctorReport relocation sanity --------------------------------------------


def test_doctor_report_imported_from_doctor_and_models_is_the_same_class_object():
    """`doctor.py` re-exports `DoctorReport` via `from .models import
    DoctorReport` -- it must not become a second, merely-identical class."""
    from pyforge.mason.doctor import DoctorReport as DoctorReport_via_doctor

    assert DoctorReport_via_doctor is DoctorReport


def test_doctor_report_constructs_with_its_original_fields():
    report = DoctorReport(
        mason_version="0.1.0+source",
        cfe_root="/fake/cfe",
        cfe_root_step="cwd-walk",
        cfe_interpreter="/fake/python",
        cfe_interpreter_step="running-interpreter",
        cfe_import_floor_satisfied=True,
        cfe_import_floor_missing=(),
        unavailable_verbs=(),
        engines=(EngineStatus(name="pixi", available=True, version="pixi 0.72.2"),),
        conda_forge_ship_ready=True,
        conda_forge_ship_blockers=(),
    )
    assert report.cfe_root == "/fake/cfe"
    assert report.engines == (EngineStatus(name="pixi", available=True, version="pixi 0.72.2"),)


def test_doctor_report_is_frozen():
    report = DoctorReport(
        mason_version="0.1.0+source",
        cfe_root=None,
        cfe_root_step="not-found",
        cfe_interpreter="/fake/python",
        cfe_interpreter_step="running-interpreter",
        cfe_import_floor_satisfied=False,
        cfe_import_floor_missing=("pyyaml",),
        unavailable_verbs=("recipe",),
        engines=(),
        conda_forge_ship_ready=False,
        conda_forge_ship_blockers=("the CFE root is unresolved",),
    )
    with pytest.raises(FrozenInstanceError):
        report.mason_version = "9.9.9"  # type: ignore[misc]


# --- ShipState -----------------------------------------------------------------


def test_ship_state_has_exactly_the_four_ad9_members():
    assert {member.value for member in ShipState} == {
        "not_attempted",
        "failed",
        "pending",
        "terminal",
    }


def test_ship_state_members_are_real_str_instances():
    """`StrEnum`, not a plain `Enum` (Design Notes): every member must
    already BE a `str`, not merely comparable to one."""
    assert isinstance(ShipState.PENDING, str)
    assert ShipState.PENDING == "pending"


def test_ship_state_str_renders_the_plain_value_not_the_member_repr():
    """The exact property `render_text`'s `f"{data[key]}"` line depends on
    (Design Notes): unlike a bare `(str, Enum)` mixin pre-3.11,
    `StrEnum.__str__` returns the plain value, not `ShipState.PENDING`."""
    assert str(ShipState.PENDING) == "pending"
    assert f"{ShipState.PENDING}" == "pending"


def test_ship_state_serializes_as_a_plain_json_string():
    """The exact property `render_json`'s bare `json.dumps(...)` call (no
    custom encoder) depends on: a plain `Enum` member would raise
    `TypeError` here; `StrEnum` serializes natively."""
    assert json.dumps({"state": ShipState.PENDING}) == '{"state": "pending"}'


# --- ShipTargetResult ------------------------------------------------------


def test_ship_target_result_constructs_with_all_four_fields():
    result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="https://github.com/conda-forge/staged-recipes/pull/123",
        message="PR created: https://github.com/conda-forge/staged-recipes/pull/123",
    )
    assert result.target == "conda-forge"
    assert result.state == ShipState.PENDING
    assert result.reference == "https://github.com/conda-forge/staged-recipes/pull/123"
    assert result.message == "PR created: https://github.com/conda-forge/staged-recipes/pull/123"


def test_ship_target_result_reference_and_message_accept_none():
    result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.NOT_ATTEMPTED,
        reference=None,
        message=None,
    )
    assert result.reference is None
    assert result.message is None


def test_ship_target_result_is_frozen():
    result = ShipTargetResult(
        target="conda-forge",
        state=ShipState.NOT_ATTEMPTED,
        reference=None,
        message=None,
    )
    with pytest.raises(FrozenInstanceError):
        result.state = ShipState.PENDING  # type: ignore[misc]


def test_ship_target_result_equality_is_by_value():
    a = ShipTargetResult(target="conda-forge", state=ShipState.FAILED, reference=None, message="x")
    b = ShipTargetResult(target="conda-forge", state=ShipState.FAILED, reference=None, message="x")
    assert a == b


# --- ShipTargetKind ----------------------------------------------------------


def test_ship_target_kind_has_exactly_the_four_members():
    """Story 3.9 widens this from three members to four -- `PYPI_TEST`
    (FR-24, FR-50, AD-26)."""
    assert {member.value for member in ShipTargetKind} == {
        "pypi",
        "conda-forge",
        "channel",
        "pypi-test",
    }


def test_ship_target_kind_members_are_real_str_instances():
    """`StrEnum`, not a plain `Enum` (docstring): every member must already
    BE a `str`, not merely comparable to one -- mirrors `ShipState`'s own
    test above."""
    assert isinstance(ShipTargetKind.PYPI, str)
    assert ShipTargetKind.CONDA_FORGE == "conda-forge"


def test_ship_target_kind_pypi_test_value():
    """Story 3.9, FR-24/FR-50/AD-26: the TestPyPI rehearsal target's own
    literal value."""
    assert ShipTargetKind.PYPI_TEST.value == "pypi-test"
    assert isinstance(ShipTargetKind.PYPI_TEST, str)


# --- ShipTarget ----------------------------------------------------------------


def test_ship_target_constructs_with_both_fields():
    target = ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg")
    assert target.kind == ShipTargetKind.CHANNEL
    assert target.channel_name == "myorg"


def test_ship_target_channel_name_accepts_none_for_non_channel_kinds():
    pypi_target = ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None)
    conda_forge_target = ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None)
    pypi_test_target = ShipTarget(kind=ShipTargetKind.PYPI_TEST, channel_name=None)
    assert pypi_target.channel_name is None
    assert conda_forge_target.channel_name is None
    assert pypi_test_target.channel_name is None


def test_ship_target_is_frozen():
    target = ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None)
    with pytest.raises(FrozenInstanceError):
        target.kind = ShipTargetKind.CONDA_FORGE  # type: ignore[misc]


def test_ship_target_equality_is_by_value():
    a = ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg")
    b = ShipTarget(kind=ShipTargetKind.CHANNEL, channel_name="myorg")
    assert a == b


# --- ShipReceipt (Story 3.7) ----------------------------------------------------

_TERMINAL_RESULT = ShipTargetResult(
    target="pypi",
    state=ShipState.TERMINAL,
    reference="https://pypi.org/project/pkg/0.1.0/",
    message="View at:\n...\n",
)
_PENDING_RESULT = ShipTargetResult(
    target="channel:myorg",
    state=ShipState.PENDING,
    reference=None,
    message="could not determine whether channel already has pkg",
)
_FAILED_RESULT = ShipTargetResult(
    target="pypi",
    state=ShipState.FAILED,
    reference=None,
    message="ERROR HTTPError: 400\n",
)
_NOT_ATTEMPTED_RESULT = ShipTargetResult(
    target="conda-forge",
    state=ShipState.NOT_ATTEMPTED,
    reference=None,
    message=None,
)


def test_ship_receipt_constructs_with_both_fields():
    receipt = ShipReceipt(targets=(_TERMINAL_RESULT,), ok=True)
    assert receipt.targets == (_TERMINAL_RESULT,)
    assert receipt.ok is True


def test_ship_receipt_is_frozen():
    receipt = ShipReceipt(targets=(), ok=True)
    with pytest.raises(FrozenInstanceError):
        receipt.ok = False  # type: ignore[misc]


def test_ship_receipt_equality_is_by_value():
    a = ShipReceipt(targets=(_TERMINAL_RESULT,), ok=True)
    b = ShipReceipt(targets=(_TERMINAL_RESULT,), ok=True)
    assert a == b


def test_ship_receipt_mixed_not_attempted_and_pending_is_ok():
    """spec I/O matrix: 'Receipt aggregate, mixed success' -- targets =
    (TERMINAL, PENDING) -> ShipReceipt.ok is True."""
    receipt = ShipReceipt(targets=(_TERMINAL_RESULT, _PENDING_RESULT), ok=True)
    assert receipt.ok is True


def test_ship_receipt_any_failed_target_is_not_ok():
    """spec I/O matrix: 'Receipt aggregate, one failure' -- targets =
    (TERMINAL, FAILED) -> ShipReceipt.ok is False."""
    receipt = ShipReceipt(targets=(_TERMINAL_RESULT, _FAILED_RESULT), ok=False)
    assert receipt.ok is False


def test_ship_receipt_not_attempted_alone_is_ok():
    receipt = ShipReceipt(targets=(_NOT_ATTEMPTED_RESULT,), ok=True)
    assert receipt.ok is True
