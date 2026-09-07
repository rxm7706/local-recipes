"""Unit tests for driver.py's pure helpers -- no `claude -p` or `eval-quality` calls.

Run: pixi run -e local-recipes python -m pytest evals/review-catches-planted-defect/test_driver.py
(plain pytest, no new dependency -- pytest is already in the local-recipes env).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from driver import cites_planted, parse_review_envelope  # noqa: E402


def test_cites_planted_exact_single_line():
    assert cites_planted([{"location": "pkg/discount.py:17"}]) is True


def test_cites_planted_overlapping_range_is_not_a_citation():
    # A wider range that merely overlaps line 17 (e.g. a NaN/infinity concern spanning
    # 15-17) is a different finding, not a citation of the boundary-flip defect --
    # documented in cites_planted's own docstring as the empirically-tuned distinction.
    assert cites_planted([{"location": "pkg/discount.py:15-17"}]) is False


def test_cites_planted_degenerate_single_line_range():
    assert cites_planted([{"location": "pkg/discount.py:17-17"}]) is True


def test_cites_planted_empty_findings():
    assert cites_planted([]) is False


def test_parse_review_envelope_well_formed():
    envelope = json.dumps({
        "total_cost_usd": 0.42,
        "structured_output": {"ok": True, "findings": [{"location": "pkg/discount.py:17",
                                                          "trigger_condition": "x",
                                                          "guard_snippet": "y",
                                                          "potential_consequence": "z"}]},
    })
    findings, cost, parse_ok = parse_review_envelope(envelope)
    assert parse_ok is True
    assert cost == 0.42
    assert findings == [{"location": "pkg/discount.py:17", "trigger_condition": "x",
                          "guard_snippet": "y", "potential_consequence": "z"}]


def test_parse_review_envelope_well_formed_empty_findings():
    envelope = json.dumps({"total_cost_usd": 0.1, "structured_output": {"ok": True, "findings": []}})
    findings, cost, parse_ok = parse_review_envelope(envelope)
    assert parse_ok is True
    assert findings == []


def test_parse_review_envelope_malformed_is_distinguishable():
    # Not JSON at all -- a malformed envelope must report parse_ok=False, distinct from
    # a well-formed envelope that genuinely reports zero findings (both collapse to an
    # empty findings list, but only one is a real "the reviewer found nothing").
    findings, cost, parse_ok = parse_review_envelope("not json")
    assert parse_ok is False
    assert findings == []


def test_parse_review_envelope_unexpected_shape_is_distinguishable():
    # Valid JSON, but structured_output/result is not an object with a findings array.
    envelope = json.dumps({"total_cost_usd": 0.05, "result": "not an object"})
    findings, cost, parse_ok = parse_review_envelope(envelope)
    assert parse_ok is False
    assert findings == []
