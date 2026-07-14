"""Unit tests — deptry-output parsing + the default hygiene->status table
(Story 1.3, E2).

Synthetic deptry JSON in, hygiene ``Finding``s + a ``(Status, StatusDriver)``
mapping out. No subprocess, no network — the parser is pure and the socket
harness stays green.
"""

from __future__ import annotations

import json

import pytest

from python_deptry_osv_scanner.hygiene import (
    DEFAULT_HYGIENE_POLICY,
    UNPARSEABLE_RATE_BASELINE,
    DeptryParse,
    hygiene_rung,
    parse_deptry_output,
    status_for_code,
)
from python_deptry_osv_scanner.models import (
    AXIS_HYGIENE,
    ErrorKind,
    Finding,
    Status,
    StatusDriver,
)


def _record(code: str, module: str, message: str = "msg") -> dict:
    return {
        "error": {"code": code, "message": message},
        "module": module,
        "location": {"file": "pkg/__init__.py", "line": 1, "column": 8},
    }


def _dumps(*records: object) -> str:
    return json.dumps(list(records))


# --- record -> finding mapping -----------------------------------------------


@pytest.mark.parametrize(
    "code,module",
    [
        ("DEP001", "totally_absent_pkg_xyz"),
        ("DEP002", "requests"),
        ("DEP003", "transitive_dep"),
        ("DEP004", "misplaced_dev"),
        ("DEP005", "argparse"),
    ],
)
def test_each_dep_code_maps_to_a_hygiene_finding(code, module):
    parse = parse_deptry_output(_dumps(_record(code, module)))
    assert parse.output_parsed
    (finding,) = parse.findings
    assert finding.id == f"hygiene:{code}:{module}"
    assert finding.axis == AXIS_HYGIENE
    assert finding.subject == module
    assert finding.message == "msg"
    assert parse.records_total == 1
    assert parse.records_unparseable == 0
    assert parse.unparseable_rate == 0.0


def test_clean_output_is_empty_and_decidable():
    parse = parse_deptry_output("[]")
    assert parse.output_parsed
    assert parse.findings == ()
    assert parse.errors == ()
    assert parse.records_total == 0
    assert parse.unparseable_rate == 0.0


# --- the default hygiene policy table ----------------------------------------


def test_default_policy_table_is_exactly_the_five_dep_codes():
    # DEP001 is WARN in 1.3 (its Gap-A block is gated on Story 2.1's
    # name-mapping confidence — follow-up Opus review, 2026-07-14).
    assert DEFAULT_HYGIENE_POLICY == {
        "DEP001": Status.WARN,
        "DEP002": Status.WARN,
        "DEP003": Status.WARN,
        "DEP004": Status.WARN,
        "DEP005": Status.WARN,
    }


@pytest.mark.parametrize(
    "code,expected",
    [
        ("DEP001", Status.WARN),  # gated block deferred to Story 2.1
        ("DEP002", Status.WARN),
        ("DEP003", Status.WARN),
        ("DEP004", Status.WARN),
        ("DEP005", Status.WARN),
    ],
)
def test_status_for_known_code(code, expected):
    assert status_for_code(code) is expected


def test_unknown_code_degrades_to_indeterminate_never_clean():
    """A future/unclassified deptry code must never false-green."""
    assert status_for_code("DEP999") is Status.INDETERMINATE
    assert status_for_code("") is Status.INDETERMINATE


# --- rung derivation ---------------------------------------------------------


def test_hygiene_rung_for_dep001_is_warn():
    # DEP001 warns in 1.3 (Gap-A block gated on Story 2.1's name-mapping
    # confidence; deptry DEP001 false-positives on guarded optional imports
    # would otherwise produce a benign false-red). Follow-up Opus review.
    finding = Finding(
        id="hygiene:DEP001:foo",
        axis=AXIS_HYGIENE,
        message="missing",
        subject="foo",
        severity=None,
    )
    status, driver = hygiene_rung(finding)
    assert status is Status.WARN
    assert driver == StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP001:foo")


def test_hygiene_rung_for_dep002_is_warn():
    finding = Finding(
        id="hygiene:DEP002:foo",
        axis=AXIS_HYGIENE,
        message="unused",
        subject="foo",
        severity=None,
    )
    status, driver = hygiene_rung(finding)
    assert status is Status.WARN
    assert driver.finding_id == "hygiene:DEP002:foo"


def test_hygiene_rung_for_unknown_code_is_indeterminate():
    finding = Finding(
        id="hygiene:DEP042:foo",
        axis=AXIS_HYGIENE,
        message="mystery",
        subject="foo",
        severity=None,
    )
    status, _ = hygiene_rung(finding)
    assert status is Status.INDETERMINATE


def test_hygiene_rung_driver_carries_the_findings_axis():
    """A hygiene-axis finding whose id is NOT hygiene-family (an
    ``indeterminate:`` id) still routes: an unknown code -> indeterminate,
    and the driver mirrors the finding's axis."""
    finding = Finding(
        id="indeterminate:no-version:leftpad",
        axis=AXIS_HYGIENE,
        message="withheld",
        subject="leftpad",
        severity=None,
    )
    status, driver = hygiene_rung(finding)
    assert status is Status.INDETERMINATE
    assert driver.axis == AXIS_HYGIENE
    assert driver.finding_id == "indeterminate:no-version:leftpad"


# --- malformed records are counted, never dropped (C0) -----------------------


def test_missing_error_code_is_counted_and_reported():
    raw = json.dumps([{"module": "requests"}])  # no error.code
    parse = parse_deptry_output(raw)
    assert parse.output_parsed
    assert parse.findings == ()
    assert parse.records_total == 1
    assert parse.records_unparseable == 1
    assert parse.unparseable_rate == 1.0
    (error,) = parse.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNRECOGNIZED
    assert error.owner == "deptry"


def test_missing_module_is_counted_and_reported():
    raw = json.dumps([{"error": {"code": "DEP002", "message": "m"}}])
    parse = parse_deptry_output(raw)
    assert parse.findings == ()
    assert parse.records_unparseable == 1
    (error,) = parse.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNRECOGNIZED


def test_non_dict_record_is_counted_and_reported():
    raw = json.dumps(["not-a-record", 42])
    parse = parse_deptry_output(raw)
    assert parse.findings == ()
    assert parse.records_total == 2
    assert parse.records_unparseable == 2
    assert parse.unparseable_rate == 1.0
    assert all(
        e.kind is ErrorKind.ENGINE_OUTPUT_UNRECOGNIZED for e in parse.errors
    )


def test_mixed_valid_and_malformed_records_partition_correctly():
    raw = json.dumps(
        [
            _record("DEP002", "requests"),
            {"module": "no-code"},  # malformed
            _record("DEP001", "absent"),
        ]
    )
    parse = parse_deptry_output(raw)
    assert [f.id for f in parse.findings] == [
        "hygiene:DEP001:absent",
        "hygiene:DEP002:requests",
    ]
    assert parse.records_total == 3
    assert parse.records_unparseable == 1
    assert parse.unparseable_rate == pytest.approx(1 / 3)
    assert len(parse.errors) == 1


# --- top-level output failures -----------------------------------------------


def test_non_array_output_fails_the_whole_parse():
    parse = parse_deptry_output(json.dumps({"not": "an array"}))
    assert parse.output_parsed is False
    assert parse.findings == ()
    (error,) = parse.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE


def test_undecodable_json_fails_the_whole_parse():
    parse = parse_deptry_output("this is not json {")
    assert parse.output_parsed is False
    (error,) = parse.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE


def test_empty_string_output_fails_the_whole_parse():
    parse = parse_deptry_output("")
    assert parse.output_parsed is False
    assert parse.errors[0].kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE


# --- determinism + sanitization ----------------------------------------------


def test_findings_are_sorted_by_id_regardless_of_input_order():
    raw = json.dumps(
        [
            _record("DEP005", "zeta"),
            _record("DEP001", "alpha"),
            _record("DEP002", "mid"),
        ]
    )
    parse = parse_deptry_output(raw)
    assert [f.id for f in parse.findings] == [
        "hygiene:DEP001:alpha",
        "hygiene:DEP002:mid",
        "hygiene:DEP005:zeta",
    ]


def test_module_name_with_colon_is_sanitized_in_the_id():
    parse = parse_deptry_output(_dumps(_record("DEP001", "odd:name")))
    (finding,) = parse.findings
    assert finding.id == "hygiene:DEP001:odd%3Aname"
    assert finding.subject == "odd:name"  # subject keeps the raw name


def test_module_name_with_newline_does_not_crash_and_sanitizes():
    parse = parse_deptry_output(_dumps(_record("DEP001", "foo\nbar")))
    (finding,) = parse.findings
    assert finding.id == "hygiene:DEP001:foo%0Abar"
    assert finding.subject == "foo\nbar"


def test_code_carrying_a_newline_is_treated_as_unrecognized():
    """A code embedding a newline would violate the single-line finding-id
    grammar (Finding.__post_init__ rejects it) -> counted as unrecognized via
    the defensive try/except, never a construction crash."""
    parse = parse_deptry_output(_dumps(_record("DEP\n01", "foo")))
    assert parse.findings == ()
    assert parse.records_unparseable == 1
    assert parse.errors[0].kind is ErrorKind.ENGINE_OUTPUT_UNRECOGNIZED


# --- ratchet baseline --------------------------------------------------------


def test_unparseable_rate_baseline_is_zero():
    assert UNPARSEABLE_RATE_BASELINE == 0.0


def test_deptry_parse_is_frozen():
    import dataclasses

    parse = parse_deptry_output("[]")
    assert isinstance(parse, DeptryParse)
    with pytest.raises(dataclasses.FrozenInstanceError):
        parse.records_total = 5  # type: ignore[misc]


# --- Follow-up Opus review (2026-07-14) regression suite ---------------------


def _deptry_record(code: str, module: str, message: str = "m") -> dict:
    return {"error": {"code": code, "message": message}, "module": module}


def test_empty_output_is_reported_distinctly_not_as_invalid_json():
    """deptry wrote nothing to its -o file (version/flag skew) — the
    diagnostic must say 'no output', not 'invalid JSON' (which masks the real
    cause)."""
    for raw in ("", "   ", "\n\t "):
        parse = parse_deptry_output(raw)
        assert parse.output_parsed is False
        (err,) = parse.errors
        assert err.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE
        assert "no machine output" in err.message
        assert "not valid JSON" not in err.message


def test_colon_bearing_code_is_unrecognized_not_a_mangled_finding():
    """A code carrying a colon (namespaced fork/future code) would make the
    hygiene:<code>:<module> id non-injective; it is UNRECOGNIZED (counted +
    reported), never a silently-mangled indeterminate finding."""
    parse = parse_deptry_output(json.dumps([_deptry_record("DEP:001", "foo")]))
    assert parse.output_parsed is True
    assert parse.findings == ()
    assert parse.records_unparseable == 1
    (err,) = parse.errors
    assert err.kind is ErrorKind.ENGINE_OUTPUT_UNRECOGNIZED


def test_well_formed_unknown_code_still_becomes_a_graceful_finding():
    """A future well-formed code (DEP006) is grammar-safe, so it is a finding
    that degrades to indeterminate — NOT unrecognized (the graceful path)."""
    parse = parse_deptry_output(json.dumps([_deptry_record("DEP006", "foo")]))
    assert parse.records_unparseable == 0
    (finding,) = parse.findings
    assert finding.id == "hygiene:DEP006:foo"
    status, _ = hygiene_rung(finding)
    assert status is Status.INDETERMINATE


def test_unrecognized_record_message_has_no_array_index():
    """The unrecognized-record error must not bake deptry's array position
    into its message — deptry's ordering is not stable, and an index would
    break twice-run byte-identical (NFR-I3). Two malformed records at
    different positions yield identical error text."""
    raw = json.dumps([{"bad": 1}, _deptry_record("DEP002", "ok"), "not-a-dict"])
    parse = parse_deptry_output(raw)
    assert parse.records_unparseable == 2
    messages = {e.message for e in parse.errors}
    assert len(messages) == 1  # position-free → identical, dedupes to one
    assert not any(ch.isdigit() for ch in next(iter(messages)))
