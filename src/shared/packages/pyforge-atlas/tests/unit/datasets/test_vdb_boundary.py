"""VDB boundary tests (Story B2, AC-3(b) / Gap G-3).

The ``_coerce_cvss_score`` ScoreType unwrap is preserved at the dataset/BOUNDARY layer
(kept OUT of the pure node body) and fixture-tested here — never a node concern.
"""

from __future__ import annotations

from pyforge.atlas.datasets import coerce_cvss_score


class _RootModel:
    """Mimics vdb 6.6.2's partial-model_dump ScoreType wrapper (a .root attribute)."""

    def __init__(self, root):
        self.root = root


class _ValueModel:
    def __init__(self, value):
        self.value = value


def test_coerce_bare_number():
    assert coerce_cvss_score(9.1) == 9.1
    assert coerce_cvss_score(7) == 7.0


def test_coerce_rootmodel_wrapper():
    assert coerce_cvss_score(_RootModel(8.8)) == 8.8
    assert coerce_cvss_score(_ValueModel(6.5)) == 6.5


def test_coerce_partial_dump_mapping():
    assert coerce_cvss_score({"root": 5.0}) == 5.0
    assert coerce_cvss_score({"value": 4.2}) == 4.2


def test_coerce_nested_wrapper():
    assert coerce_cvss_score(_RootModel(_RootModel(3.3))) == 3.3


def test_coerce_none_and_unknown_are_none_not_zero():
    # AC-3: an absent/unparseable score is UNKNOWN (None), never 0.0 (a false clean).
    assert coerce_cvss_score(None) is None
    assert coerce_cvss_score({}) is None
    assert coerce_cvss_score("not-a-number") is None
    assert coerce_cvss_score(True) is None  # bool is never a CVSS score


def test_coerce_numeric_string():
    assert coerce_cvss_score("9.3") == 9.3


def test_coerce_nan_is_none_not_nan():
    # B2 review-hardening: a NaN float must unwrap to None (unknown), NEVER a spurious
    # NaN score (AC-3 unknown->None; a NaN would violate the None-not-0.0 contract).
    import math

    result = coerce_cvss_score(float("nan"))
    assert result is None
    assert not (isinstance(result, float) and math.isnan(result or 0.0))
