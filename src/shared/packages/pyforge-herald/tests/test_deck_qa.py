"""``deck_qa`` -- the gate report schema and ``run()`` entrypoint (Story
14.1). Covers every row of the spec's I/O & Edge-Case Matrix.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.herald import deck_qa
from pyforge.herald.errors import HeraldError


def _ok(context: deck_qa.GateContext) -> deck_qa.GateResult:
    return deck_qa.GateResult(status="ok")


def _with_finding(context: deck_qa.GateContext) -> deck_qa.GateResult:
    return deck_qa.GateResult(
        status="ok",
        findings=[deck_qa.Finding(slide_id="slide-1", message="off-slide text")],
    )


def _raises(context: deck_qa.GateContext) -> deck_qa.GateResult:
    raise RuntimeError("boom: gate exploded")


def test_zero_gates_prints_an_empty_gates_object(tmp_path: Path):
    report = deck_qa.run("x", tmp_path, gates={})
    assert report == deck_qa.DeckQaReport(slug="x", gates={})
    assert deck_qa.to_dict(report) == {"slug": "x", "gates": {}}


def test_two_gates_one_flags_both_keys_present(tmp_path: Path):
    report = deck_qa.run(
        "pyforge-warden", tmp_path, gates={"a": _ok, "b": _with_finding}
    )
    assert set(report.gates) == {"a", "b"}
    assert report.gates["a"].status == "ok"
    assert report.gates["a"].findings == []
    assert report.gates["b"].status == "ok"
    assert report.gates["b"].findings == [
        deck_qa.Finding(slide_id="slide-1", message="off-slide text")
    ]


def test_a_gate_that_raises_becomes_status_error_without_aborting_others(
    tmp_path: Path,
):
    report = deck_qa.run("x", tmp_path, gates={"boom": _raises, "fine": _ok})
    assert report.gates["boom"].status == "error"
    assert report.gates["boom"].error is not None
    assert "boom: gate exploded" in report.gates["boom"].error
    assert report.gates["boom"].findings == []
    assert report.gates["fine"].status == "ok"


def test_run_itself_never_raises_when_a_gate_raises(tmp_path: Path):
    # No pytest.raises wrapper -- the assertion IS that this call returns.
    report = deck_qa.run("x", tmp_path, gates={"boom": _raises})
    assert report.gates["boom"].status == "error"


def test_gate_context_carries_slug_and_repo_root(tmp_path: Path):
    seen = {}

    def _capture(context: deck_qa.GateContext) -> deck_qa.GateResult:
        seen["slug"] = context.slug
        seen["repo_root"] = context.repo_root
        return deck_qa.GateResult(status="ok")

    deck_qa.run("pyforge-warden", tmp_path, gates={"capture": _capture})

    assert seen["slug"] == "pyforge-warden"
    assert seen["repo_root"] == tmp_path


def test_round_trip_equality(tmp_path: Path):
    report = deck_qa.run(
        "pyforge-warden", tmp_path, gates={"a": _ok, "b": _with_finding, "c": _raises}
    )
    round_tripped = deck_qa.parse_report(json.loads(json.dumps(deck_qa.to_dict(report))))
    assert round_tripped == report


def test_round_trip_of_the_empty_report(tmp_path: Path):
    report = deck_qa.run("x", tmp_path, gates={})
    round_tripped = deck_qa.parse_report(json.loads(json.dumps(deck_qa.to_dict(report))))
    assert round_tripped == report


def test_parse_report_rejects_missing_gates_key():
    with pytest.raises(HeraldError, match="gates"):
        deck_qa.parse_report({"slug": "x"})


def test_parse_report_rejects_missing_slug_key():
    with pytest.raises(HeraldError, match="slug"):
        deck_qa.parse_report({"gates": {}})


def test_parse_report_rejects_an_unknown_top_level_key():
    with pytest.raises(HeraldError, match="bogus"):
        deck_qa.parse_report({"slug": "x", "gates": {}, "bogus": 1})


def test_parse_report_rejects_an_unknown_gate_level_key():
    with pytest.raises(HeraldError, match="bogus"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "ok",
                        "findings": [],
                        "artifacts": [],
                        "error": None,
                        "bogus": 1,
                    }
                },
            }
        )


def test_parse_report_rejects_an_unknown_finding_level_key():
    with pytest.raises(HeraldError):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "ok",
                        "findings": [
                            {"slide_id": "s1", "message": "m", "bogus": 1}
                        ],
                        "artifacts": [],
                        "error": None,
                    }
                },
            }
        )


def test_parse_report_rejects_a_bad_status_value():
    with pytest.raises(HeraldError, match="status"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "not-a-real-status",
                        "findings": [],
                        "artifacts": [],
                        "error": None,
                    }
                },
            }
        )


def test_parse_report_rejects_a_non_dict_top_level():
    with pytest.raises(HeraldError):
        deck_qa.parse_report(["not", "a", "dict"])


def test_parse_report_rejects_a_missing_gate_level_field():
    with pytest.raises(HeraldError, match="findings"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {"a": {"status": "ok", "artifacts": [], "error": None}},
            }
        )


def test_parse_report_rejects_ok_status_with_a_non_null_error():
    with pytest.raises(HeraldError, match="status"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "ok",
                        "findings": [],
                        "artifacts": [],
                        "error": "unexpected",
                    }
                },
            }
        )


def test_parse_report_rejects_error_status_with_a_null_error():
    with pytest.raises(HeraldError, match="status"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "error",
                        "findings": [],
                        "artifacts": [],
                        "error": None,
                    }
                },
            }
        )


def test_a_gate_returning_none_becomes_status_error(tmp_path: Path):
    def _forgot_return(context: deck_qa.GateContext) -> deck_qa.GateResult:
        pass  # a gate forgetting its `return` -- yields None, no exception

    report = deck_qa.run("x", tmp_path, gates={"broken": _forgot_return})
    assert report.gates["broken"].status == "error"
    assert report.gates["broken"].error is not None


def test_a_gate_returning_a_bad_status_value_becomes_status_error(tmp_path: Path):
    def _bad_status(context: deck_qa.GateContext) -> deck_qa.GateResult:
        return deck_qa.GateResult(status="not-a-real-status")

    report = deck_qa.run("x", tmp_path, gates={"broken": _bad_status})
    assert report.gates["broken"].status == "error"
    assert report.gates["broken"].error is not None


def test_a_gate_violating_the_status_error_invariant_becomes_status_error(
    tmp_path: Path,
):
    def _inconsistent(context: deck_qa.GateContext) -> deck_qa.GateResult:
        # status "ok" but a non-null error -- self-contradictory.
        return deck_qa.GateResult(status="ok", error="oops")

    report = deck_qa.run("x", tmp_path, gates={"broken": _inconsistent})
    assert report.gates["broken"].status == "error"


def test_run_reads_default_gates_fresh_even_after_reassignment(
    tmp_path: Path, monkeypatch
):
    """The mutable-default-argument footgun this fix avoids: reassigning
    the module attribute (not mutating it in place) must still be picked
    up by a caller that never passes ``gates=`` explicitly."""
    monkeypatch.setattr(deck_qa, "DEFAULT_GATES", {"late": _ok})

    report = deck_qa.run("x", tmp_path)

    assert set(report.gates) == {"late"}


def test_third_gate_added_to_the_same_gates_mapping_needs_zero_production_changes(
    tmp_path: Path,
):
    """Proof, not a production-code change: build a 3-entry ``gates`` dict
    right here in the test and confirm the report gains a third top-level
    key with nothing else touched."""

    def _third(context: deck_qa.GateContext) -> deck_qa.GateResult:
        return deck_qa.GateResult(status="ok")

    gates = {"a": _ok, "b": _with_finding, "third": _third}

    report = deck_qa.run("x", tmp_path, gates=gates)

    assert set(report.gates) == {"a", "b", "third"}
    assert report.gates["third"].status == "ok"
