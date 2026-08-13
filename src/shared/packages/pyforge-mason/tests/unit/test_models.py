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
handling)."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from pyforge.mason.engines import EngineStatus
from pyforge.mason.models import CfeResult, DoctorReport, ShipState, ShipTargetResult


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
    )
    with pytest.raises(FrozenInstanceError):
        report.mason_version = "9.9.9"  # type: ignore[misc]


# --- ShipState -----------------------------------------------------------------

def test_ship_state_has_exactly_the_four_ad9_members():
    assert {member.value for member in ShipState} == {
        "not_attempted", "failed", "pending", "terminal",
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
        target="conda-forge", state=ShipState.PENDING,
        reference="https://github.com/conda-forge/staged-recipes/pull/123",
        message="PR created: https://github.com/conda-forge/staged-recipes/pull/123",
    )
    assert result.target == "conda-forge"
    assert result.state == ShipState.PENDING
    assert result.reference == "https://github.com/conda-forge/staged-recipes/pull/123"
    assert result.message == "PR created: https://github.com/conda-forge/staged-recipes/pull/123"


def test_ship_target_result_reference_and_message_accept_none():
    result = ShipTargetResult(
        target="conda-forge", state=ShipState.NOT_ATTEMPTED, reference=None, message=None,
    )
    assert result.reference is None
    assert result.message is None


def test_ship_target_result_is_frozen():
    result = ShipTargetResult(
        target="conda-forge", state=ShipState.NOT_ATTEMPTED, reference=None, message=None,
    )
    with pytest.raises(FrozenInstanceError):
        result.state = ShipState.PENDING  # type: ignore[misc]


def test_ship_target_result_equality_is_by_value():
    a = ShipTargetResult(target="conda-forge", state=ShipState.FAILED, reference=None, message="x")
    b = ShipTargetResult(target="conda-forge", state=ShipState.FAILED, reference=None, message="x")
    assert a == b
