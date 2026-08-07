"""jsonschema validation of a ``core.conformance.build_matrix_row`` output
against the packaged ``schemas/conformance.json`` (Story 6.6, FR-45).
Mirrors ``tests/unit/test_egress.py``'s own gate-record schema-validation
convention."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from pyforge.marshal.core.conformance import (
    STATUS_MATRIX_FAIL,
    STATUS_MATRIX_NOT_ATTEMPTED,
    STATUS_MATRIX_PASS,
    STATUS_SMOKE_FAIL,
    STATUS_SMOKE_PASS,
    build_matrix_row,
)

_NOW = datetime(2026, 8, 7, tzinfo=timezone.utc)


def _schema() -> dict:
    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "pyforge"
        / "marshal"
        / "schemas"
        / "conformance.json"
    )
    return json.loads(path.read_text())


def _as_dict(row) -> dict:
    return dataclasses.asdict(row)


def test_not_attempted_row_validates():
    row = build_matrix_row("claude", smoke_record=None, probe_record=None, now=_NOW, stale_after_days=30)
    jsonschema.validate(instance=_as_dict(row), schema=_schema())


def test_pass_row_validates():
    row = build_matrix_row(
        "claude",
        smoke_record={
            "status": STATUS_SMOKE_PASS,
            "failing_stage": None,
            "harness_version": "0.9.0",
            "recorded_at": "2026-08-06T00:00:00+00:00",
        },
        probe_record={"binary_version": "1.0.0"},
        now=_NOW,
        stale_after_days=30,
    )
    instance = _as_dict(row)
    assert instance["status"] == STATUS_MATRIX_PASS
    jsonschema.validate(instance=instance, schema=_schema())


def test_fail_row_validates():
    row = build_matrix_row(
        "claude",
        smoke_record={
            "status": STATUS_SMOKE_FAIL,
            "failing_stage": "verify",
            "harness_version": "0.9.0",
            "recorded_at": "2026-08-06T00:00:00+00:00",
        },
        probe_record=None,
        now=_NOW,
        stale_after_days=30,
    )
    instance = _as_dict(row)
    assert instance["status"] == STATUS_MATRIX_FAIL
    jsonschema.validate(instance=instance, schema=_schema())


def test_unknown_status_rejected():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={
                "adapter": "claude",
                "status": "bogus",
                "adapter_version": None,
                "harness_version": None,
                "date": None,
                "failing_stage": None,
                "stale": False,
            },
            schema=_schema(),
        )


def test_extra_property_rejected():
    row = build_matrix_row("claude", smoke_record=None, probe_record=None, now=_NOW, stale_after_days=30)
    instance = _as_dict(row)
    instance["unexpected"] = "field"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=_schema())


def test_not_attempted_status_never_stale():
    row = build_matrix_row("claude", smoke_record=None, probe_record=None, now=_NOW, stale_after_days=30)
    assert row.status == STATUS_MATRIX_NOT_ATTEMPTED
    assert row.stale is False
