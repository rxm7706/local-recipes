"""Unit tests for ``pyforge.marshal.core.egress`` (Story 2.6, AD-34) --
``to_redacted``/``Redacted``/``build_gate_record``/``EGRESS_PORTS`` across
the spec's I/O & Edge-Case Matrix, plus jsonschema validation of a built
gate record against the packaged ``schemas/gate-record.json``.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import jsonschema
import pytest

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.core.egress import EGRESS_PORTS, Redacted, build_gate_record, to_redacted
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
    with pytest.raises(ValueError):
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
    }
