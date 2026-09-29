"""``hand_off_candidate`` + ``trending-handoff`` CLI tests (Story 13.5, CAP-5, FR-68).

One test per I/O & Edge-Case Matrix row in the story spec (9 rows) plus a structural
conformance check of the happy-path record against ``HANDOFF_ENVELOPE_SCHEMA``, plus a
handful of CLI-level (``handoff_main.main``) tests proving the NFR-6 exit-code
contract end to end — mirrors ``test_query.py``'s function-level style and
``test_main.py``'s CLI-level style.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys

import pandas as pd
import pytest

from pyforge.atlas.mcp import session as _session_mod
from pyforge.atlas.trending_candidates import handoff, handoff_main


def _row(*, repo_full_name, period, tier, reason, stars_total, **extra) -> dict:
    """A ``trending_candidates_classified``-shaped row (mirrors ``test_query.py``'s
    own ``_row`` helper — not imported, since it is private to that test module)."""
    row = {
        "repo_full_name": repo_full_name,
        "repo_url": f"https://github.com/{repo_full_name}",
        "description": None,
        "language": "Python",
        "stars_total": stars_total,
        "stars_today": None,
        "forks_total": None,
        "period": period,
        "source": "html_scrape",
        "fetched_at": 1_700_000_000,
        "pypi_name": repo_full_name.split("/")[-1],
        "tier": tier,
        "reason": reason,
    }
    row.update(extra)
    return row


_TIER1_REASON = "pure-python packaging shape, OSI-approved license MIT"

_EVIDENCE = {
    "abandonment_signal": "no commits in 2 years, issues unanswered",
    "license_clarity": "MIT, unambiguous SPDX id",
}


@contextlib.contextmanager
def _bootstrap_boom(*args, **kwargs):
    """A session-bootstrap-time failure (the realistic missing-``conf/local/
    credentials.yml`` shape, a real ``KeyError`` from ``CatalogConfigResolver``) —
    raised BEFORE the context manager ever yields, so entering the ``with`` block
    itself raises."""
    raise KeyError("bigquery_adc")
    yield  # pragma: no cover -- never reached, contextmanager needs a yield to parse


# ---------------------------------------------------------------------------
# I/O & Edge-Case Matrix — hand_off_candidate()
# ---------------------------------------------------------------------------


def test_happy_path_emits_one_record_never_a_recipe_or_pr(seed_catalog):
    """Matrix row 1: a tier-1 candidate + a passing health screen with both evidence
    fields populated emits ONE structured record — repo identity, tier/reason, a
    health_screen block, provenance, and an epoch-seconds handed_off_at (FR-68 /
    CAP-5's literal AC: never a recipe, never a PR)."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_catalog(df)

    record = handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)

    assert record["repo_full_name"] == "alice/libfoo"
    assert record["tier"] == "1"
    assert record["reason"] == _TIER1_REASON
    assert record["schema_version"] == handoff.HANDOFF_SCHEMA_VERSION
    assert record["dataset"] == "trending_candidates_classified"
    assert record["health_screen"] == {"verdict": "pass", **_EVIDENCE}
    assert record["provenance"]["kind"] == "unavailable"  # MemoryDataset -> unavailable
    assert isinstance(record["handed_off_at"], int)
    # Never a recipe, never a PR (SPEC.md CAP-5's own non-goal) — the record carries
    # no such keys at all.
    assert "recipe" not in record
    assert "pr_url" not in record


def test_candidate_not_found_raises_value_error_naming_the_repo(seed_catalog):
    """Matrix row 2: ``--repo`` not present in ``trending_candidates_classified`` is
    refused, and the message names the repo that was requested."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="bob/other", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=900),
        ]
    )
    seed_catalog(df)

    with pytest.raises(ValueError, match="alice/libfoo"):
        handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)


def test_tier_skip_raises_value_error_naming_tier_and_reason(seed_catalog):
    """Matrix row 3: a matching row with ``tier="skip"`` is refused — gated on
    ``tier`` DIRECTLY (never on a ``not_on_cf`` boolean, which does not even exist as
    a column on this dataset), and the message names both the tier and the reason."""
    df = pd.DataFrame(
        [
            _row(
                repo_full_name="alice/libfoo", period="weekly", tier="skip", reason="no-pypi-artifact", stars_total=1200
            ),
        ]
    )
    seed_catalog(df)

    with pytest.raises(ValueError, match="tier='skip'") as excinfo:
        handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)
    assert "no-pypi-artifact" in str(excinfo.value)


def test_verdict_fail_raises_value_error_no_catalog_touch():
    """Matrix row 4: ``--verdict fail`` is refused (the screen must PASS). No
    ``seed_catalog`` fixture used: the health-screen gate runs BEFORE any
    session/catalog touch, mirroring ``query_trending_candidates``'s own
    validate-first, fail-fast contract."""
    with pytest.raises(ValueError, match="must PASS"):
        handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="fail", **_EVIDENCE)


@pytest.mark.parametrize(
    ("kwargs", "missing_field"),
    [
        ({"abandonment_signal": "", "license_clarity": "MIT, clear"}, "abandonment_signal"),
        ({"abandonment_signal": "   ", "license_clarity": "MIT, clear"}, "abandonment_signal"),
        ({"abandonment_signal": "no commits in 2 years", "license_clarity": ""}, "license_clarity"),
    ],
)
def test_missing_evidence_field_raises_value_error_naming_the_field(kwargs, missing_field):
    """Matrix row 5: an empty (or whitespace-only, post-``.strip()``) evidence field
    is refused, and the message names WHICH field is missing. No ``seed_catalog``
    fixture: validated before any session/catalog touch (an entirely omitted CLI flag
    is argparse's own ``required=True`` concern, exercised at the ``handoff_main``
    layer instead)."""
    with pytest.raises(ValueError, match=missing_field):
        handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **kwargs)


def test_multi_window_duplicate_dedupes_to_one_record(seed_catalog):
    """Matrix row 6: the same repo trending in more than one window resolves to
    EXACTLY one handoff record, via the same deterministic sort ``query.py`` already
    uses (``stars_total`` desc / ``repo_full_name`` asc / ``period`` asc) — closes the
    deferred-work item CAP-2's own review pass raised against multi-window
    duplicates (see ``deferred-work.md``'s ``spec-13-2-tier-classification.md``
    entry)."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
            _row(repo_full_name="alice/libfoo", period="daily", tier="1", reason=_TIER1_REASON, stars_total=1200),
            _row(repo_full_name="alice/libfoo", period="monthly", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_catalog(df)

    record = handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)

    # All three rows tie on stars_total AND repo_full_name -- period is the third,
    # deterministic tie-break, ascending: "daily" < "monthly" < "weekly".
    assert record["period"] == "daily"


def test_multi_window_duplicate_with_mixed_type_stars_total_does_not_crash(seed_catalog):
    """Review finding: a numeric-looking STRING ``stars_total`` cell survives real
    scraped data (``query.py`` already had to fix the identical column,
    "verified live" per its own docstring) — sorting the raw, uncoerced column
    raises a bare ``TypeError`` when it meets a genuine ``int`` on another
    duplicate-window row. The dedup sort must coerce for ordering purposes without
    crashing, and the tie-break must still prefer the higher (numeric) star count."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total="900"),
            _row(repo_full_name="alice/libfoo", period="daily", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_catalog(df)

    record = handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)

    # The genuinely-higher star count (1200, the "daily" row) wins the tie-break —
    # proving the sort coerced "900" to a comparable number rather than crashing or
    # falling back to an arbitrary/lexicographic order.
    assert record["period"] == "daily"


def test_case_insensitive_repo_match(seed_catalog):
    """Matrix row 7: ``--repo Alice/LibFoo`` vs stored ``alice/libfoo`` matches
    (casefold, mirrors CAP-4's ``load_org_audit_candidates`` dedup precedent) — the
    record reports the STORED casing, not the caller's."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_catalog(df)

    record = handoff.hand_off_candidate(repo_full_name="Alice/LibFoo", verdict="pass", **_EVIDENCE)

    assert record["repo_full_name"] == "alice/libfoo"


def test_case_insensitive_match_with_whitespace_padded_stored_value(seed_catalog):
    """Review finding: the caller's ``--repo`` argument was stripped before
    casefold-comparing, but a STORED ``repo_full_name`` with incidental
    leading/trailing whitespace (a plausible scrape artifact) was not — silently
    failing to match an otherwise-correct, byte-clean ``--repo`` argument."""
    df = pd.DataFrame(
        [
            _row(repo_full_name=" alice/libfoo\n", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_catalog(df)

    record = handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)

    assert record["repo_full_name"] == " alice/libfoo\n"


def test_reserved_envelope_key_collision_raises_value_error(seed_catalog):
    """Review finding: `hand_off_candidate` blind-overwrites `dataset`/
    `health_screen`/`provenance`/`handed_off_at`/`schema_version` on the selected
    row — a future CAP-2 column sharing one of those names would otherwise vanish
    into the envelope's own bookkeeping with no error. A classified row carrying a
    reserved key is refused instead of silently clobbered."""
    df = pd.DataFrame(
        [
            _row(
                repo_full_name="alice/libfoo",
                period="weekly",
                tier="1",
                reason=_TIER1_REASON,
                stars_total=1200,
                provenance="not-a-real-column",
            ),
        ]
    )
    seed_catalog(df)

    with pytest.raises(ValueError, match="provenance"):
        handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)


def test_dataset_not_yet_ingested_raises_value_error(seed_parquet_catalog):
    """Matrix row 8: ``trending_candidates_classified`` has no backing file (the
    realistic "never ingested" shape) — refused, never a crash (indeterminate -> exit
    1, NFR-6). Mirrors ``query.py``'s own ``DatasetError``-degrades-to-empty
    handling: the row lookup then naturally falls through to "not found"."""
    seed_parquet_catalog(None)  # declared entry, backing file absent

    with pytest.raises(ValueError, match="alice/libfoo"):
        handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)


def test_unexpected_bootstrap_failure_is_not_swallowed_as_policy_fail(monkeypatch):
    """Matrix row 9: a session-BOOTSTRAP-time failure (e.g. missing
    ``conf/local/credentials.yml`` — a real ``KeyError`` from
    ``CatalogConfigResolver``) is NOT caught as a policy-fail ``ValueError`` — it
    propagates RAW, so the CLI maps it to NFR-6's exit 2 instead of exit 1. Mirrors
    ``query_trending_candidates``'s own identical unguarded shape for the identical
    reason (a pre-existing, seam-wide gap — see ``deferred-work.md``'s
    ``spec-13-3-trending-candidates-operator-surface.md`` entry on this exact seam)."""
    monkeypatch.setattr(_session_mod, "bootstrapped_session", _bootstrap_boom)

    with pytest.raises(KeyError):
        handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------

_PY_TYPES = {
    "string": str,
    "integer": int,
    "object": dict,
    "array": list,
    "boolean": bool,
    "null": type(None),
}


def _assert_conforms(record: dict, schema: dict) -> None:
    """A minimal, hand-rolled structural walk — NOT a full JSON-Schema validator
    (Design Notes: no new ``jsonschema`` dependency for an XS story). Checks that
    every ``required`` key is present, and that each documented property's ``type``/
    ``enum``/``const``/``minLength`` (when given) matches the record's actual value,
    recursing into nested ``object`` properties (``health_screen``, ``provenance``)."""
    for key in schema.get("required", []):
        assert key in record, f"missing required key: {key}"

    for key, prop in schema.get("properties", {}).items():
        if key not in record:
            continue
        value = record[key]
        if "enum" in prop:
            assert value in prop["enum"], f"{key}={value!r} not in {prop['enum']}"
        if "const" in prop:
            assert value == prop["const"], f"{key}={value!r} != const {prop['const']!r}"
        if "minLength" in prop:
            # Review finding: `HANDOFF_ENVELOPE_SCHEMA` declares `minLength` on the
            # health-screen evidence fields, but nothing checked it — this schema and
            # its own "conformance" test could drift apart on this constraint with no
            # test catching it.
            assert len(value) >= prop["minLength"], f"{key}={value!r} shorter than minLength {prop['minLength']}"
        types = prop.get("type")
        if types is not None:
            types = [types] if isinstance(types, str) else types
            allowed = tuple(_PY_TYPES[t] for t in types if t in _PY_TYPES)
            if allowed:
                assert isinstance(value, allowed), f"{key}={value!r} ({type(value).__name__}) not in {types}"
        if prop.get("type") == "object" and isinstance(value, dict):
            _assert_conforms(value, prop)


def test_happy_path_record_conforms_to_handoff_envelope_schema(seed_catalog):
    """The happy-path record structurally conforms to ``HANDOFF_ENVELOPE_SCHEMA`` —
    the ``documented schema`` half of this story's Design Notes (a plain dict,
    JSON-Schema-draft-2020-12 vocabulary, no external validator dependency)."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_catalog(df)

    record = handoff.hand_off_candidate(repo_full_name="alice/libfoo", verdict="pass", **_EVIDENCE)

    _assert_conforms(record, handoff.HANDOFF_ENVELOPE_SCHEMA)
    # The schema itself must also be genuinely dumpable (a documented artifact an
    # external consumer can read, not merely importable Python).
    json.dumps(handoff.HANDOFF_ENVELOPE_SCHEMA)
    json.dumps(record)


# ---------------------------------------------------------------------------
# CLI (handoff_main.main) — proves the NFR-6 exit-code contract end to end
# ---------------------------------------------------------------------------


def test_cli_happy_path_exits_0_and_prints_one_json_record(seed_catalog, capsys):
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_catalog(df)

    exit_code = handoff_main.main(
        [
            "--repo",
            "alice/libfoo",
            "--verdict",
            "pass",
            "--abandonment-signal",
            _EVIDENCE["abandonment_signal"],
            "--license-clarity",
            _EVIDENCE["license_clarity"],
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    record = json.loads(captured.out)
    assert record["repo_full_name"] == "alice/libfoo"
    assert record["tier"] == "1"


def test_cli_refusal_exits_1_with_stderr_message_naming_the_reason(capsys):
    """No ``seed_catalog``: a failing verdict is validated before any session/catalog
    touch, mirroring ``trending-candidates``'s own bad-filter fail-fast contract."""
    exit_code = handoff_main.main(
        [
            "--repo",
            "alice/libfoo",
            "--verdict",
            "fail",
            "--abandonment-signal",
            _EVIDENCE["abandonment_signal"],
            "--license-clarity",
            _EVIDENCE["license_clarity"],
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "must PASS" in captured.err


def test_cli_unexpected_bootstrap_failure_exits_2_not_1(monkeypatch, capsys):
    """The CLI half of matrix row 9: an unexpected (non-policy-fail) error must not
    be swallowed as exit 1 -- NFR-6 reserves that for `hand_off_candidate`'s own
    documented `ValueError` contract."""
    monkeypatch.setattr(_session_mod, "bootstrapped_session", _bootstrap_boom)

    exit_code = handoff_main.main(
        [
            "--repo",
            "alice/libfoo",
            "--verdict",
            "pass",
            "--abandonment-signal",
            _EVIDENCE["abandonment_signal"],
            "--license-clarity",
            _EVIDENCE["license_clarity"],
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("KeyError: ")


def test_cli_broken_stderr_pipe_while_reporting_a_refusal_still_exits_1(monkeypatch):
    """Review finding: the `except ValueError`/`except Exception` handlers' own
    `print(..., file=sys.stderr)` calls were unguarded, unlike the stdout write path
    -- a broken STDERR pipe (mirrors `test_main.py`'s ``_ClosedPipe`` model for
    stdout) while reporting an error would otherwise raise `BrokenPipeError` FROM
    INSIDE the except block itself, escaping `main()` as a raw traceback instead of
    the documented clean exit code."""

    class _ClosedPipe(io.StringIO):
        def write(self, text):
            if text.strip():
                raise BrokenPipeError(32, "Broken pipe")
            return 0

    monkeypatch.setattr(sys, "stderr", _ClosedPipe())

    exit_code = handoff_main.main(
        [
            "--repo",
            "alice/libfoo",
            "--verdict",
            "fail",
            "--abandonment-signal",
            _EVIDENCE["abandonment_signal"],
            "--license-clarity",
            _EVIDENCE["license_clarity"],
        ]
    )

    assert exit_code == 1
