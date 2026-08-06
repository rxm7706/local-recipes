"""Unit tests for ``pyforge.marshal.core.egress`` (Story 2.6, AD-34) --
``to_redacted``/``Redacted``/``build_gate_record``/``EGRESS_PORTS`` across
the spec's I/O & Edge-Case Matrix, plus jsonschema validation of a built
gate record against the packaged ``schemas/gate-record.json``.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timedelta
from pathlib import Path

import jsonschema
import pytest

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.core.egress import (
    _TIMESTAMP_PATTERN,
    EGRESS_PORTS,
    Redacted,
    build_gate_record,
    to_redacted,
)
from pyforge.marshal.core.identity import MalformedStoryKeyError
from pyforge.marshal.core.model import Verdict
from pyforge.marshal.core.policy import REDACTED_SENTINEL

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "pyforge"
    / "marshal"
    / "schemas"
    / "gate-record.json"
)


def _schema() -> dict[str, object]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


# --- Redacted ----------------------------------------------------------------


def test_redacted_wraps_text():
    wrapped = Redacted(text="{}")
    assert wrapped.text == "{}"


def test_redacted_rejects_non_str_text():
    """TypeError, not ValueError (review finding): the other two type guards
    in the same three-call egress pipeline (`to_redacted`'s non-Mapping
    payload, `write_redacted_atomic`'s non-`Redacted`/non-`Path` arguments)
    both raise TypeError for this identical category."""
    with pytest.raises(TypeError):
        Redacted(text=123)  # type: ignore[arg-type]


def test_redacted_is_frozen():
    wrapped = Redacted(text="{}")
    # The specific type, not a bare `Exception` (review finding): a bare
    # `pytest.raises(Exception)` passes on ANY exception, including an
    # unrelated AttributeError from a typo in the test body -- so it would
    # keep passing even if the dataclass stopped being frozen.
    with pytest.raises(dataclasses.FrozenInstanceError):
        wrapped.text = "other"  # type: ignore[misc]


# --- to_redacted(): the I/O & Edge-Case Matrix --------------------------------


def test_secret_shaped_key_is_redacted():
    redacted = to_redacted({"API_TOKEN": "x"})
    assert json.loads(redacted.text) == {"API_TOKEN": REDACTED_SENTINEL}


def test_known_token_shape_in_an_ordinary_field_is_redacted():
    leaked = "leak " + "ghp_" + "a" * 36
    redacted = to_redacted({"note": leaked})
    document = json.loads(redacted.text)
    assert document == {"note": f"leak {REDACTED_SENTINEL}"}
    assert "ghp_" not in document["note"]


def test_ordinary_data_passes_through_unchanged():
    redacted = to_redacted({"command": "pytest -x"})
    assert json.loads(redacted.text) == {"command": "pytest -x"}


def test_non_redacted_control_proves_no_over_redaction():
    """A field whose name is NOT secret-shaped and whose value contains NO
    known token shape must survive byte-for-byte -- the control half of the
    fixture, proving the mechanism doesn't over-redact ordinary content."""
    payload = {"label": "acme", "revision": "abc123", "count": 2, "ok": True}
    redacted = to_redacted(payload)
    assert json.loads(redacted.text) == payload


def test_to_redacted_rejects_non_mapping_payload():
    with pytest.raises(TypeError):
        to_redacted("bare str")  # type: ignore[arg-type]


def test_to_redacted_rejects_a_list_payload():
    with pytest.raises(TypeError):
        to_redacted(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_to_redacted_output_is_sorted_key_json():
    redacted = to_redacted({"b": 1, "a": 2})
    assert redacted.text == '{"a": 2, "b": 1}'


def test_to_redacted_recurses_into_nested_mappings_and_lists():
    payload = {
        "outer": {
            "API_KEY": "super-secret",
            "notes": ["fine", "leak " + "AKIA" + "0" * 16],
        }
    }
    redacted = to_redacted(payload)
    document = json.loads(redacted.text)
    assert document["outer"]["API_KEY"] == REDACTED_SENTINEL
    assert document["outer"]["notes"][0] == "fine"
    assert "AKIA" not in document["outer"]["notes"][1]


@pytest.mark.parametrize(
    "leaked",
    [
        "ghp_" + "a" * 36,
        "github_pat_" + "b" * 25,
        "AKIA" + "0123456789ABCDEF",
        "sk-" + "c" * 25,
    ],
    ids=["github-pat", "github-fine-grained-pat", "aws-access-key", "generic-sk-prefix"],
)
def test_every_known_token_shape_is_redacted(leaked):
    redacted = to_redacted({"field": f"prefix {leaked} suffix"})
    document = json.loads(redacted.text)
    assert leaked not in document["field"]
    assert REDACTED_SENTINEL in document["field"]


def test_non_string_scalars_pass_through_unchanged():
    payload = {"count": 3, "ratio": 1.5, "ok": True, "missing": None}
    redacted = to_redacted(payload)
    assert json.loads(redacted.text) == payload


def test_token_longer_than_the_hardcoded_length_is_fully_redacted():
    """Regression (review finding, verified live): a fixed-length
    quantifier (`{36}`) only consumed exactly 36 characters, so a real
    token longer than that left a trailing fragment in plaintext
    (`"***REDACTED***aaaa"`). The open-ended `{36,}` fix must consume the
    WHOLE contiguous alnum run instead."""
    leaked = "ghp_" + "a" * 40
    redacted = to_redacted({"note": leaked})
    document = json.loads(redacted.text)
    assert document["note"] == REDACTED_SENTINEL
    assert "a" * 4 not in document["note"]


def test_ordinary_word_containing_a_token_prefix_mid_word_is_not_redacted():
    """Regression (review finding, verified live): `sk-` (and `ghp_`/`AKIA`)
    matched mid-word with no boundary check, so an ordinary value like
    `"risk-8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4c"` had its trailing hex mangled
    as if `sk-...` were a leaked secret. A leading negative-lookbehind
    boundary must block this."""
    ordinary = "risk-8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4c"
    redacted = to_redacted({"tree_revision": ordinary})
    assert json.loads(redacted.text) == {"tree_revision": ordinary}


@pytest.mark.parametrize(
    "leaked",
    [
        "sk-proj-" + "a" * 48 + "T3BlbkFJ" + "b" * 48,
        "sk-ant-api03-" + "A" * 40 + "-" + "B" * 40,
    ],
    ids=["openai-project-key", "anthropic-api-key"],
)
def test_real_provider_key_formats_with_internal_separators_are_redacted(leaked):
    """Regression (follow-up review finding, verified live): the original
    `sk-[A-Za-z0-9]{20,}` needed 20 CONTIGUOUS alnum characters after `sk-`,
    which neither dominant real-world key format has -- both put a `-` within
    the first 8 characters, so both passed through in FULL PLAINTEXT. This is
    the credential shape a Marshal gate record is most likely to capture,
    since Marshal's own agent sessions authenticate with one."""
    document = json.loads(to_redacted({"stdout": f"auth: {leaked}"}).text)
    assert leaked not in document["stdout"]
    assert "sk-" not in document["stdout"]
    assert document["stdout"] == f"auth: {REDACTED_SENTINEL}"


def test_separated_token_does_not_leak_its_tail():
    """Regression (follow-up review finding, verified live): a token whose
    contiguous run ended at a separator had only that first run redacted,
    leaving the remainder in plaintext behind a sentinel that made the record
    LOOK redacted -- `"***REDACTED***-ddddddddd..."`."""
    leaked = "sk-" + "c" * 25 + "-" + "d" * 25
    document = json.loads(to_redacted({"note": leaked}).text)
    assert document["note"] == REDACTED_SENTINEL
    assert "d" * 25 not in document["note"]


def test_short_hyphenated_value_starting_with_sk_is_not_over_redacted():
    """The separator-tolerant pattern's 40-character floor exists so an
    ordinary hyphenated value that merely STARTS with `sk-` survives."""
    ordinary = "sk-test-selector"
    assert json.loads(to_redacted({"command": f"pytest -k {ordinary}"}).text) == {
        "command": f"pytest -k {ordinary}"
    }


def test_token_shaped_mapping_key_is_redacted():
    """Regression (follow-up review finding, verified live): only VALUES were
    shape-scanned, so a token-shaped KEY -- the natural shape of a captured
    environment or header map -- was written verbatim."""
    leaked = "ghp_" + "a" * 36
    document = json.loads(to_redacted({leaked: "v"}).text)
    assert leaked not in document
    assert document == {REDACTED_SENTINEL: "v"}


def test_secret_shaped_key_keeps_its_name_and_only_loses_its_value():
    """Key-scanning must not rename a secret-shaped key: the NAME is not the
    secret, and the record stays readable only if the field is still findable."""
    assert json.loads(to_redacted({"API_TOKEN": "x"}).text) == {"API_TOKEN": REDACTED_SENTINEL}


def test_ordinary_mapping_keys_are_untouched():
    payload = {"command": "pytest -x", "nested": {"revision": "abc123"}}
    assert json.loads(to_redacted(payload).text) == payload


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_to_redacted_rejects_non_finite_floats(value):
    """Regression (follow-up review finding, verified live): json.dumps
    defaults to allow_nan=True, so a non-finite float was written as a bare
    `NaN`/`Infinity` token -- not valid RFC-8259 JSON, unreadable by any
    strict parser -- silently, instead of the documented TypeError."""
    with pytest.raises(TypeError, match="non-JSON-serializable"):
        to_redacted({"ratio": value})


def test_to_redacted_raises_type_error_for_a_non_json_serializable_value():
    """Regression (review finding, verified live): a nested `set` crashed
    with json.dumps's own unannotated `TypeError` ("Object of type set is
    not JSON serializable") instead of a documented failure mode."""
    with pytest.raises(TypeError, match="non-JSON-serializable"):
        to_redacted({"tags": {"a", "b"}})


# --- build_gate_record(): the I/O & Edge-Case Matrix --------------------------


def _valid_commands() -> list[dict[str, object]]:
    return [
        {"command": "pytest -q", "resolvable": True, "returncode": 0, "stdout": "", "stderr": ""},
        {"command": "ruff check .", "resolvable": False, "returncode": None},
    ]


def test_build_gate_record_valid_input_canonicalizes_story_key():
    record = build_gate_record(
        story_key="2-6",
        commands=_valid_commands(),
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00+00:00",
    )
    assert record["story"] == "2.6"
    assert record["commands"] == _valid_commands()
    assert record["scope_check_verdict"] is None
    assert record["tree_revision"] == "abc123"
    assert record["timestamp"] == "2026-08-03T00:00:00+00:00"


def test_build_gate_record_accepts_z_suffixed_utc_timestamp():
    record = build_gate_record(
        story_key="2.6",
        commands=[],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00Z",
    )
    assert record["timestamp"] == "2026-08-03T00:00:00Z"


@pytest.mark.parametrize("verdict", list(Verdict))
def test_build_gate_record_accepts_every_real_verdict_value(verdict):
    record = build_gate_record(
        story_key="2.6",
        commands=[],
        scope_check_verdict=verdict.value,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00+00:00",
    )
    assert record["scope_check_verdict"] == verdict.value


def test_build_gate_record_rejects_unknown_scope_check_verdict():
    with pytest.raises(ValueError):
        build_gate_record(
            story_key="2.6",
            commands=[],
            scope_check_verdict="not-a-real-verdict",
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00+00:00",
        )


def test_build_gate_record_rejects_malformed_timestamp():
    with pytest.raises(ValueError):
        build_gate_record(
            story_key="2.6",
            commands=[],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="not-a-date",
        )


def test_build_gate_record_rejects_non_utc_timestamp_with_offset_specific_message():
    """Regression (review finding): a timestamp WITH a non-zero offset must
    get a distinct message from a timestamp with NO timezone at all -- the
    two are different mistakes with different fixes."""
    with pytest.raises(ValueError, match=r"must be UTC \(zero tz offset\)"):
        build_gate_record(
            story_key="2.6",
            commands=[],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00+05:00",
        )


def test_build_gate_record_rejects_naive_timestamp_with_missing_timezone_message():
    """Regression (review finding): the prior single "must be UTC (zero tz
    offset)" message was misleading for the most likely real-world mistake
    -- forgetting to attach any timezone at all."""
    with pytest.raises(ValueError, match="must include a UTC timezone"):
        build_gate_record(
            story_key="2.6",
            commands=[],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00",
        )


def test_build_gate_record_rejects_malformed_story_key():
    with pytest.raises(MalformedStoryKeyError):
        build_gate_record(
            story_key="!!",
            commands=[],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00+00:00",
        )


def test_build_gate_record_rejects_empty_tree_revision():
    with pytest.raises(ValueError):
        build_gate_record(
            story_key="2.6",
            commands=[],
            scope_check_verdict=None,
            tree_revision="",
            timestamp="2026-08-03T00:00:00+00:00",
        )


def test_build_gate_record_rejects_bare_str_commands():
    with pytest.raises(ValueError):
        build_gate_record(
            story_key="2.6",
            commands="pytest -q",  # type: ignore[arg-type]
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00+00:00",
        )


@pytest.mark.parametrize(
    "entry",
    [
        {"command": "pytest -q", "resolvable": True},
        {"resolvable": True, "returncode": 0},
        {"command": "pytest -q", "returncode": 0},
        "not-a-mapping",
        {"command": "", "resolvable": True, "returncode": 0},
        {"command": "pytest -q", "resolvable": "yes", "returncode": 0},
        {"command": "pytest -q", "resolvable": True, "returncode": "0"},
        # unknown key -- review finding: previously passed silently, only
        # failing later (and only in a test) against the schema's own
        # additionalProperties: false.
        {"command": "pytest -q", "resolvable": True, "returncode": 0, "bogus": "x"},
        # stdout/stderr present but not str -- review finding.
        {"command": "pytest -q", "resolvable": True, "returncode": 0, "stdout": 123},
        {"command": "pytest -q", "resolvable": True, "returncode": 0, "stderr": None},
    ],
)
def test_build_gate_record_rejects_malformed_command_entries(entry):
    with pytest.raises(ValueError):
        build_gate_record(
            story_key="2.6",
            commands=[entry],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00+00:00",
        )


@pytest.mark.parametrize(
    "entry",
    [
        # unresolvable but carrying a returncode -- "never ran" AND "exited 0"
        {"command": "pytest -q", "resolvable": False, "returncode": 0},
        # unresolvable but carrying captured output
        {"command": "pytest -q", "resolvable": False, "returncode": None, "stdout": "hi"},
        {"command": "pytest -q", "resolvable": False, "returncode": None, "stderr": "hi"},
        # resolvable but with no returncode -- ran, yet no exit code
        {"command": "pytest -q", "resolvable": True, "returncode": None},
    ],
    ids=["unresolvable-with-returncode", "unresolvable-stdout", "unresolvable-stderr",
         "resolvable-without-returncode"],
)
def test_build_gate_record_rejects_self_contradictory_command_entries(entry):
    """Regression (follow-up review finding, verified live): the schema
    DOCUMENTS both invariants in prose but nothing enforced them, so a report
    asserting a command both never ran and exited 0 with captured output was
    accepted here AND validated clean against the schema. For a record whose
    purpose is proving what was checked, an internally false entry is worse
    than a rejected one."""
    with pytest.raises(ValueError):
        build_gate_record(
            story_key="2.6",
            commands=[entry],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00+00:00",
        )


def test_build_gate_record_accepts_classify_outcome_s_own_two_shapes():
    """The sole real producer of this shape (`core.gate.classify_outcome`)
    emits exactly these two entries -- the new consistency check must not
    reject its own upstream."""
    record = build_gate_record(
        story_key="2.6",
        commands=_valid_commands(),
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00+00:00",
    )
    assert record["commands"] == _valid_commands()


@pytest.mark.parametrize(
    "bogus", ["yesterday afternoon", "2026-08-03T00:00:00+05:00", "2026-08-03"]
)
def test_schema_rejects_a_timestamp_build_gate_record_would_reject(bogus):
    """Regression (follow-up review finding, verified live): `timestamp` was a
    bare `"type": "string"`, so the durable, $id-bearing contract green-lit
    records `build_gate_record` itself rejects -- while `story`,
    `tree_revision` and `command` all carried constraints."""
    record = build_gate_record(
        story_key="2.6",
        commands=[],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00+00:00",
    )
    record["timestamp"] = bogus
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=record, schema=_schema())


@pytest.mark.parametrize(
    "good", ["2026-08-03T00:00:00Z", "2026-08-03T00:00:00+00:00", "2026-08-03T00:00:00.123456Z"]
)
def test_schema_accepts_every_utc_form_build_gate_record_accepts(good):
    record = build_gate_record(
        story_key="2.6",
        commands=[],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp=good,
    )
    jsonschema.validate(instance=record, schema=_schema())


def test_build_gate_record_command_reports_are_copies_not_aliases():
    source = {"command": "pytest -q", "resolvable": True, "returncode": 0}
    record = build_gate_record(
        story_key="2.6",
        commands=[source],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00+00:00",
    )
    source["returncode"] = 99
    assert record["commands"][0]["returncode"] == 0


# --- schema validation ---------------------------------------------------------


def test_build_gate_record_matches_the_packaged_schema():
    record = build_gate_record(
        story_key="2-6",
        commands=_valid_commands(),
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00+00:00",
    )
    jsonschema.validate(instance=record, schema=_schema())


def test_schema_rejects_a_record_missing_a_required_field():
    record = build_gate_record(
        story_key="2.6",
        commands=[],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00+00:00",
    )
    del record["tree_revision"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=record, schema=_schema())


def test_schema_rejects_an_unknown_top_level_property():
    record = build_gate_record(
        story_key="2.6",
        commands=[],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00+00:00",
    )
    record["bogus"] = "nope"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=record, schema=_schema())


def test_schema_rejects_a_command_missing_a_required_key():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"command": "pytest -q", "resolvable": True},
            schema=_schema()["$defs"]["commandReport"],
        )


# --- end-to-end pipeline (review finding: the 3 pieces were only ever ------
# unit-tested in isolation; this proves the composed path a future cli/gate.py
# caller will actually use) --------------------------------------------------


def test_end_to_end_pipeline_redacts_a_leaked_token_and_writes_a_schema_valid_file(tmp_path):
    """``build_gate_record`` -> ``to_redacted`` -> ``RecordPort.
    write_redacted_atomic`` composed exactly as a future real caller would,
    with a leaked token embedded in a command's captured ``stdout`` --
    proving the written file is BOTH schema-valid and genuinely redacted."""
    record = build_gate_record(
        story_key="2-6",
        commands=[
            {
                "command": "pytest -q",
                "resolvable": True,
                "returncode": 1,
                "stdout": "auth failed: token=" + "ghp_" + "a" * 36,
                "stderr": "",
            }
        ],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00Z",
    )
    jsonschema.validate(instance=record, schema=_schema())

    redacted = to_redacted(record)
    target = tmp_path / "gate-record.json"
    LocalFs().write_redacted_atomic(target, redacted)

    written = json.loads(target.read_text(encoding="utf-8"))
    assert written["story"] == "2.6"
    stdout = written["commands"][0]["stdout"]
    assert "ghp_" not in stdout
    assert REDACTED_SENTINEL in stdout


# --- EGRESS_PORTS --------------------------------------------------------------


def test_egress_ports_registry_contents():
    assert dict(EGRESS_PORTS) == {
        "ProcessPort": False,
        "FsPort": False,
        "HarnessPort": False,
        "VcsPort": False,
        "RecordPort": True,
        "ClockPort": False,
        "SessionObserverPort": False,
        "NotifyPort": True,
        "ForgePort": True,
    }


# --- review pass 3: token-run tail, producer<->schema agreement ----------------


@pytest.mark.parametrize("tail_length", [1, 5, 12, 20, 36])
def test_separated_token_leaks_no_tail_below_the_tolerant_floor(tail_length):
    """Regression (review finding, verified live). The tolerant
    `sk-[A-Za-z0-9_-]{40,}` pattern only fires at 40+ characters, so a
    SHORTER separated token fell through to the contiguous
    `sk-[A-Za-z0-9]{20,}`, which redacted the leading run and left the
    remainder in plaintext: `"sk-" + "c"*25 + "-" + "d"*12` became
    `"***REDACTED***-dddddddddddd"`. The previous pass's regression test
    happened to pick a 51-character run, clearing the floor and never
    exercising the gap."""
    tail = "d" * tail_length
    leaked = "sk-" + "c" * 25 + "-" + tail
    document = json.loads(to_redacted({"note": leaked}).text)
    assert document["note"] == REDACTED_SENTINEL
    assert tail not in document["note"]


def test_adjacent_tokens_leak_no_tail():
    """Regression (review finding, verified live): `ghp_[A-Za-z0-9]{36,}`
    greedily consumed the `sk` of an immediately following token, destroying
    the `sk-` prefix the next pattern needed to match the remainder --
    `"***REDACTED***-bbbb..."`."""
    leaked = "ghp_" + "a" * 36 + "sk-" + "b" * 45
    document = json.loads(to_redacted({"note": leaked}).text)
    assert document["note"] == REDACTED_SENTINEL
    assert "b" not in document["note"]


def test_secret_shaped_key_that_also_contains_a_token_is_redacted_in_its_name():
    """Regression (review finding, verified live): the `is_secret_key` branch
    replaced the VALUE and `continue`d before the key ever reached
    `_redact_string`, so a key that was BOTH secret-shaped and token-shaped
    had the credential in its own name emitted verbatim as a JSON key --
    the one case `_redact`'s own docstring claims is rewritten."""
    token = "ghp_" + "a" * 36
    document = json.loads(to_redacted({f"{token}_TOKEN": "v"}).text)
    assert token not in json.dumps(document)
    assert list(document) == [REDACTED_SENTINEL]


def test_ordinary_secret_shaped_key_keeps_its_name():
    """Control for the regression above: a key with no token shape in it must
    still keep its NAME (the name is not the secret) so records stay
    findable -- only its value is replaced."""
    document = json.loads(to_redacted({"API_TOKEN": "hunter2"}).text)
    assert document == {"API_TOKEN": REDACTED_SENTINEL}


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-08-03T00:00+00:00",  # no seconds
        "2026-08-03T00:00:00+0000",  # compact offset
        "2026-08-03T00:00:00+00",  # abbreviated offset
        "20260803T000000Z",  # basic ISO form
    ],
)
def test_build_gate_record_rejects_iso_forms_its_own_schema_rejects(timestamp):
    """Regression (review finding, verified live): `datetime.fromisoformat`
    accepts these four legitimate UTC ISO-8601 spellings, the packaged
    schema's `timestamp` pattern rejects all four, and `build_gate_record`
    checked only the former -- so a well-behaved caller wrote a durable,
    `$id`-bearing record no consumer validating against the shipped contract
    would accept."""
    assert datetime.fromisoformat(timestamp).utcoffset() == timedelta(0)
    with pytest.raises(ValueError, match="canonical UTC ISO-8601 spelling"):
        build_gate_record(
            story_key="2.6",
            commands=[],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp=timestamp,
        )


@pytest.mark.parametrize(
    "timestamp",
    ["2026-08-03T00:00:00Z", "2026-08-03T00:00:00+00:00", "2026-08-03T00:00:00.123456Z"],
)
def test_every_timestamp_the_producer_accepts_validates_against_the_schema(timestamp):
    """The accept direction of the same agreement -- the previous pass only
    pinned the reject direction."""
    record = build_gate_record(
        story_key="2.6",
        commands=[],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp=timestamp,
    )
    jsonschema.validate(record, _schema())


def test_producer_and_schema_share_one_timestamp_pattern():
    """Pins the two spellings character-for-character, so the asymmetry
    cannot silently reopen."""
    assert _TIMESTAMP_PATTERN.pattern == _schema()["properties"]["timestamp"]["pattern"]


def test_schema_scope_check_verdict_enum_matches_the_verdict_vocabulary():
    """Review finding: the schema hand-duplicates `core.model.Verdict`'s six
    values with nothing keeping the two in sync, so adding a seventh Verdict
    member would ship a producer emitting schema-invalid records with the
    whole suite green (`build_gate_record` validates against `Verdict`, the
    schema against its own frozen list)."""
    enum_values = _schema()["properties"]["scope_check_verdict"]["enum"]
    assert None in enum_values
    assert sorted(v for v in enum_values if v is not None) == sorted(
        member.value for member in Verdict
    )


@pytest.mark.parametrize(
    "entry",
    [
        {"command": "pytest", "returncode": 0, "resolvable": False},
        {"command": "pytest", "returncode": None, "resolvable": False, "stdout": "all good"},
        {"command": "pytest", "returncode": None, "resolvable": True},
    ],
)
def test_schema_rejects_the_self_contradictory_entries_the_producer_rejects(entry):
    """Review finding, verified live: `_validate_command_report` enforces both
    cross-field invariants since the previous pass, but the SCHEMA -- the
    durable contract a non-Python consumer reads -- documented them only in
    prose, so a hand-written self-contradictory entry validated clean."""
    with pytest.raises(ValueError):
        build_gate_record(
            story_key="2.6",
            commands=[entry],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00Z",
        )

    record = {
        "story": "2.6",
        "commands": [entry],
        "scope_check_verdict": None,
        "tree_revision": "abc123",
        "timestamp": "2026-08-03T00:00:00Z",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(record, _schema())


@pytest.mark.parametrize(
    "entry",
    [
        {"command": "pytest", "returncode": None, "resolvable": False},
        {"command": "pytest", "returncode": 0, "resolvable": True, "stdout": "", "stderr": ""},
        {"command": "pytest", "returncode": 1, "resolvable": True},
    ],
)
def test_schema_still_accepts_every_consistent_entry(entry):
    """The tightened schema must not reject what `classify_outcome` really
    emits -- both directions, producer and contract."""
    record = build_gate_record(
        story_key="2.6",
        commands=[entry],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00Z",
    )
    jsonschema.validate(record, _schema())


def test_unknown_command_report_keys_of_mixed_types_still_raise_value_error():
    """Review finding, verified live: the diagnostic did `sorted(unknown)`,
    which raises its own bare `TypeError` for a Mapping with both `str` and
    non-`str` keys -- masking the `ValueError` this validator documents for
    every malformed-input case."""
    with pytest.raises(ValueError, match="unknown key"):
        build_gate_record(
            story_key="2.6",
            commands=[{"command": "x", "returncode": 0, "resolvable": True, "bogus": 1, 7: "z"}],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00Z",
        )


# --- follow-up review pass #3: vocabulary completeness, diagnostic leakage, --
# component ranges, blank values ---------------------------------------------


@pytest.mark.parametrize(
    "leaked",
    [
        "ghp_" + "a" * 36,
        "ghs_" + "a" * 36,
        "gho_" + "a" * 36,
        "ghu_" + "a" * 36,
        "ghr_" + "a" * 36,
    ],
    ids=["classic-pat", "app-installation", "oauth-user", "user-to-server", "refresh"],
)
def test_every_github_token_prefix_in_the_family_is_redacted(leaked):
    """Review finding, verified live: only `ghp_` (the classic USER PAT) was
    covered, so the four sibling prefixes sharing the identical 36-character
    body passed through in FULL PLAINTEXT while `ghp_` redacted. `ghs_` is
    the likeliest of all to reach a gate record -- it is what `GITHUB_TOKEN`
    and `gh` carry, and what `git` echoes back inside the remote URL of a
    failed push, straight into a verify command's captured stderr."""
    document = json.loads(to_redacted({"stderr": f"remote: {leaked}"}).text)
    assert leaked not in document["stderr"]
    assert document["stderr"] == f"remote: {REDACTED_SENTINEL}"


def test_github_app_token_inside_a_push_url_is_redacted():
    """The concrete shape the finding was verified against."""
    leaked = "ghs_" + "A" * 36
    url = f"https://x-access-token:{leaked}@github.com/o/r.git"
    document = json.loads(to_redacted({"stderr": url}).text)
    assert leaked not in document["stderr"]
    assert "ghs_" not in document["stderr"]


@pytest.mark.parametrize("prefix", ["AKIA", "ASIA"], ids=["long-term", "sts-temporary"])
def test_both_aws_access_key_prefixes_are_redacted(prefix):
    """Review finding, verified live: `ASIA` (the AWS STS TEMPORARY access
    key ID) is byte-identical in shape to `AKIA` and is what anything
    assuming a role actually uses, yet was absent from the vocabulary."""
    leaked = prefix + "IOSFODNN7EXAMPLE"
    document = json.loads(to_redacted({"stdout": leaked}).text)
    assert document["stdout"] == REDACTED_SENTINEL


def test_token_preceded_by_an_underscore_is_redacted():
    """Review finding, verified live: the lookbehind blocked `_`, the most
    common token-ADJACENT separator in env-var-shaped text, so
    `"GITHUB_TOKEN_ghp_" + "a"*36` passed through in full plaintext."""
    leaked = "ghp_" + "a" * 36
    document = json.loads(to_redacted({"note": f"GITHUB_TOKEN_{leaked}"}).text)
    assert leaked not in document["note"]


def test_dropping_underscore_from_the_lookbehind_keeps_every_over_redaction_control():
    """The previous pass rejected the finding above as "the same knob pulled
    in opposite directions -- either fix re-opens the other". It does not:
    every control the lookbehind was added for has an ALNUM character before
    the prefix, so `(?<![A-Za-z0-9])` still blocks all of them."""
    controls = {
        "tree_revision": "risk-8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4c",
        "command": "pytest -k sk-test-selector",
        "branch": "feature/sk-thing",
        "prose": "AKIA is a prefix",
        "note": "an ordinary task-list entry",
    }
    assert json.loads(to_redacted(controls).text) == controls


def test_non_mapping_payload_diagnostic_does_not_echo_the_payload():
    """Review finding, verified live: `to_redacted("token=sk-ant-api03-...")`
    raised `TypeError: payload must be a Mapping, got 'token=sk-ant-...'`,
    printing the credential from the ONE module whose stated purpose is
    keeping credentials out of a sink. `cli/main.py` catches only
    SystemExit/KeyboardInterrupt, so it escapes as a raw traceback the
    harness logs."""
    secret = "sk-ant-api03-" + "A" * 40 + "-" + "B" * 40
    with pytest.raises(TypeError) as excinfo:
        to_redacted(f"token={secret}")
    assert secret not in str(excinfo.value)
    assert "str" in str(excinfo.value)


def test_redacted_text_type_diagnostic_does_not_echo_the_value():
    with pytest.raises(TypeError) as excinfo:
        Redacted(text=["ghp_" + "a" * 36])
    assert "ghp_" not in str(excinfo.value)
    assert "list" in str(excinfo.value)


def test_command_report_diagnostics_do_not_echo_captured_output():
    """Review finding, verified live: `_validate_command_report`'s `{entry!r}`
    echoed the whole report -- including its captured `stdout` -- into a
    ValueError message."""
    leaked = "ghp_" + "a" * 36
    with pytest.raises(ValueError) as excinfo:
        build_gate_record(
            story_key="2.6",
            commands=[
                {
                    "command": "pytest -q",
                    "returncode": 0,
                    "resolvable": True,
                    "stdout": f"leaked {leaked}",
                    "bogus": 1,
                }
            ],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00Z",
        )
    assert leaked not in str(excinfo.value)
    assert "bogus" in str(excinfo.value)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-08-03T24:00:00Z",
        "2026-13-03T00:00:00Z",
        "2026-08-45T00:00:00Z",
        "2026-08-03T00:99:00Z",
        "2026-08-03T00:00:99Z",
    ],
    ids=["hour-24", "month-13", "day-45", "minute-99", "second-99"],
)
def test_out_of_range_timestamp_components_are_rejected_by_producer_and_schema(timestamp):
    """Review finding, verified live: with bare `[0-9]{2}` groups the shared
    pattern green-lit `2026-13-45T99:99:99Z`, and `2026-08-03T24:00:00Z`
    passed BOTH the schema and the producer while `datetime.fromisoformat`
    silently resolves hour 24 to the NEXT day -- a durable evidence record
    whose stored text and meaning disagree."""
    with pytest.raises(ValueError):
        build_gate_record(
            story_key="2.6",
            commands=[],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp=timestamp,
        )
    instance = {
        "story": "2.6",
        "commands": [],
        "scope_check_verdict": None,
        "tree_revision": "abc123",
        "timestamp": timestamp,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=_schema())


def test_calendar_invalid_timestamp_is_the_one_stated_producer_schema_asymmetry():
    """A regex cannot express calendar validity, so Feb 30 matches the shared
    pattern while the producer rejects it via `fromisoformat`. This is the
    ONE remaining asymmetry, and the schema's description now states it
    instead of claiming it away -- pinned here so the claim cannot silently
    become wrong in either direction."""
    timestamp = "2026-02-30T12:00:00Z"
    with pytest.raises(ValueError):
        build_gate_record(
            story_key="2.6",
            commands=[],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp=timestamp,
        )
    jsonschema.validate(
        instance={
            "story": "2.6",
            "commands": [],
            "scope_check_verdict": None,
            "tree_revision": "abc123",
            "timestamp": timestamp,
        },
        schema=_schema(),
    )
    assert "calendar validity" in _schema()["properties"]["timestamp"]["description"]


@pytest.mark.parametrize("blank", ["   ", "\t", "\n"])
def test_blank_tree_revision_is_rejected_by_producer_and_schema(blank):
    """Review finding, verified live: `== ""` admitted a whitespace-only
    value, so the record identified the evaluated tree state as `"   "`."""
    with pytest.raises(ValueError, match="tree_revision must be a non-blank str"):
        build_gate_record(
            story_key="2.6",
            commands=[],
            scope_check_verdict=None,
            tree_revision=blank,
            timestamp="2026-08-03T00:00:00Z",
        )
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={
                "story": "2.6",
                "commands": [],
                "scope_check_verdict": None,
                "tree_revision": blank,
                "timestamp": "2026-08-03T00:00:00Z",
            },
            schema=_schema(),
        )


def test_blank_command_is_rejected_by_producer_and_schema():
    with pytest.raises(ValueError, match=r"must be a non-blank str"):
        build_gate_record(
            story_key="2.6",
            commands=[{"command": "   ", "returncode": 0, "resolvable": True}],
            scope_check_verdict=None,
            tree_revision="abc123",
            timestamp="2026-08-03T00:00:00Z",
        )
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"command": "   ", "returncode": 0, "resolvable": True},
            schema=_schema()["$defs"]["commandReport"],
        )


def test_a_redacted_gate_record_still_validates_against_the_schema(tmp_path):
    """The schema's description stakes the pre-/post-redaction relationship on
    exactly this ("a redacted gate record still validates against this same
    schema") and nothing tested it (review finding) -- the end-to-end test
    validated only the PRE-redaction dict."""
    record = build_gate_record(
        story_key="2-6",
        commands=[
            {
                "command": "pytest -q",
                "resolvable": True,
                "returncode": 1,
                "stdout": "auth failed: ghs_" + "a" * 36,
                "stderr": "",
            }
        ],
        scope_check_verdict=None,
        tree_revision="abc123",
        timestamp="2026-08-03T00:00:00Z",
    )
    written = json.loads(to_redacted(record).text)
    jsonschema.validate(instance=written, schema=_schema())
    assert written["commands"][0]["stdout"] == f"auth failed: {REDACTED_SENTINEL}"
    assert written["story"] == "2.6"
