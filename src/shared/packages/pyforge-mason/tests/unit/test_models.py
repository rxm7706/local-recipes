"""Story 2.1 -- `models.py`: `CfeResult` construction/immutability, and
`DoctorReport`'s relocation-with-re-export sanity (the module now importing
it via `pyforge.mason.doctor` and the module now defining it via
`pyforge.mason.models` must be the identical class object, not two classes
that merely look alike)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pyforge.mason.engines import EngineStatus
from pyforge.mason.models import CfeResult, DoctorReport


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
