"""Unit tests for ``pyforge.marshal.seed.state.store`` (Stories 10.2 and
8.5) -- covers every row of the spec's I/O & Edge-Case Matrix (round-trip,
never adopted, schema violation, malformed input, invalid state written,
mid-apply failure, guarded path) plus the five acceptance criteria:
FR-103's do-not-hand-edit header, ``StateInvalid``-and-only-``StateInvalid``
on the read path with ``SeedError`` still closed at six leaves, AD-58's
eject reconstruction from ``state.managed`` alone, the module's import
surface (no upward imports, no second atomic-write implementation), and
the untouched ``model-ignores.gitignore.j2`` template.

Imports the module itself (``store``) alongside its public names, and the
``fs`` module rather than its functions, so the mid-apply fault-injection
test can monkeypatch ``fs.atomic_write_bytes`` -- the exact name
``fs.write`` resolves in its own module namespace, which is what
``write_state`` reaches through. It also imports ``pyforge.core``'s
``atomic_write`` itself: the fault-injection test injects its failure
INSIDE the real atomic write (through a ``write_fn`` that populates the
temp file and then raises) rather than replacing the write wholesale, so a
temp file genuinely exists when the fault fires and "no ``.tmp`` residue"
is a fact about ``atomic_write``'s cleanup rather than true by
construction.

Story 8.5 appends the opt-out section at the end of this file, covering
that story's own store rows: the malformed pair (both halves, including a
non-``str`` one), ``opt_out_key_or_none``'s opposite answer, the ``None``
state both mutators refuse by name, idempotence of both mutators,
``opted_out`` kept sorted and deduped so two recording orders write
byte-identical state, the ``managed[]`` claim drop BOTH mutators perform
and its reachable near-misses, both reinstate round trips (recorded and
derived), the ``last_update`` a mutator deliberately does not stamp, and
the eleven-key round trip after a recording. It imports the ``state``
PACKAGE as well, so the re-export list can be asserted rather than assumed.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import re
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator
from pyforge.core import atomic_write as core_atomic_write

import pyforge.marshal.seed.state as state_package
from pyforge.marshal.seed import fs
from pyforge.marshal.seed.errors import InternalError, NeverWriteViolation, SeedError, StateInvalid
from pyforge.marshal.seed.model.manifest import ArtifactClass
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.state import store
from pyforge.marshal.seed.state.store import (
    STATE_KEYS,
    LegacyArtifact,
    ManagedArtifact,
    RegionSpanRecord,
    SeedState,
    clear_opt_out,
    copier_data,
    is_opt_out_key,
    is_opted_out,
    opt_out_key,
    opt_out_key_or_none,
    read_state,
    record_opt_out,
    seed_model_version,
    state_path,
    utc_timestamp,
    write_state,
)

_NO_PATTERNS = fs.NeverWrite(("docs/dreams/*.md",))


def _sample_state(**overrides: Any) -> SeedState:
    """A fully populated, schema-valid ``SeedState``: both managed
    flavours (a whole-file claim and a region claim), a legacy record, and
    a non-empty value in every one of the eleven fields, so a test that
    drops or corrupts one field is exercising a real difference."""
    fields: dict[str, Any] = {
        "model_version": ModelVersion.parse("1.2.3"),
        "seed_model_version": "0.1.0",
        "adopted_at": "2026-08-14T09:15:00Z",
        "last_update": "2026-08-14T11:42:07Z",
        "mode": "init",
        "agents": ("claude-code", "codex-cli"),
        "managed": (
            ManagedArtifact(
                id="agents-md",
                path="AGENTS.md",
                artifact_class="hybrid-managed-region",
                body_sha="0123abcd",
                inserted_region_span=RegionSpanRecord(name="tiers", start=7, end=20),
            ),
            ManagedArtifact(
                id="dream-template",
                path="docs/dreams/example.md",
                artifact_class="copied-seeded",
                body_sha="deadbeef",
                inserted_region_span=None,
            ),
        ),
        "skips": ("docs/legacy/*.md",),
        "legacy": (LegacyArtifact(id="legacy-spec", path="docs/specs/old.md", legacy_of="dream-template"),),
        "migrations_applied": ("1.1.0", "1.2.0"),
        "opted_out": ("agents-md#tiers",),
    }
    fields.update(overrides)
    return SeedState(**fields)


def _write_raw(repo_root: Path, payload: bytes | str) -> Path:
    """Put arbitrary bytes at the state path, bypassing ``write_state``
    entirely -- every read-path test needs a file the writer would have
    refused to produce."""
    path = state_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload.encode("utf-8") if isinstance(payload, str) else payload)
    return path


def _valid_document() -> dict[str, Any]:
    return _sample_state().to_json_dict()


# --- the packaged schema itself ---------------------------------------------


def test_schema_is_itself_a_valid_draft_2020_12_schema():
    Draft202012Validator.check_schema(store._load_schema())


def test_schema_declares_the_house_dialect_id_and_title():
    schema = store._load_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:local-recipes:pyforge-marshal:seed-state.v1"
    assert schema["title"] == "MarshalSeedState"


def test_schema_is_closed_at_every_object_level():
    schema = store._load_schema()
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["managedArtifact"]["additionalProperties"] is False
    assert schema["$defs"]["legacyArtifact"]["additionalProperties"] is False
    span = schema["$defs"]["managedArtifact"]["properties"]["inserted_region_span"]
    assert span["additionalProperties"] is False


def test_schema_requires_exactly_the_eleven_top_level_keys():
    schema = store._load_schema()
    assert tuple(schema["required"]) == STATE_KEYS
    assert tuple(schema["properties"]) == STATE_KEYS
    assert len(STATE_KEYS) == 11


def test_schema_class_enum_matches_artifact_class_exactly():
    """Drift guard for the module's one deliberate duplication: the schema
    hardcodes the wire vocabulary (a schema is a wire contract, not a
    mirror of a Python enum), so this test is what stops the two from
    disagreeing."""
    schema = store._load_schema()
    enum_values = schema["$defs"]["managedArtifact"]["properties"]["class"]["enum"]
    assert set(enum_values) == {member.value for member in ArtifactClass}
    assert len(enum_values) == len(set(enum_values)) == 6


def test_schema_body_sha_pattern_is_hash_contents_shipped_shape():
    schema = store._load_schema()
    pattern = schema["$defs"]["managedArtifact"]["properties"]["body_sha"]["pattern"]
    assert pattern == "^[0-9a-f]{8}(?![\\s\\S])"


def test_schema_mode_enum_is_the_two_materializing_verbs():
    assert store._load_schema()["properties"]["mode"]["enum"] == ["init", "adopt"]


def _schema_patterns(node: Any) -> list[str]:
    """Every ``pattern`` value anywhere in the schema, at any depth."""
    if isinstance(node, dict):
        return [value for key, value in node.items() if key == "pattern" and isinstance(value, str)] + [
            pattern for key, value in node.items() if key != "pattern" for pattern in _schema_patterns(value)
        ]
    if isinstance(node, list):
        return [pattern for item in node for pattern in _schema_patterns(item)]
    return []


def test_no_anchored_schema_pattern_ends_in_a_bare_dollar():
    """jsonschema compiles ``pattern`` with Python's ``re``, whose ``$``
    also matches immediately BEFORE a final newline -- so every ``^...$``
    pattern in this schema silently admitted a trailing-newline value. The
    portable terminator is ``(?![\\s\\S])`` (ECMA-262 has no ``\\Z``), and
    this is the drift guard that keeps a future pattern from reintroducing
    the bare anchor."""
    patterns = _schema_patterns(store._load_schema())
    assert patterns, "expected the schema to carry patterns at all"
    assert [pattern for pattern in patterns if pattern.endswith("$")] == []
    anchored = [pattern for pattern in patterns if pattern.startswith("^")]
    assert len(anchored) >= 7
    assert all(pattern.endswith("(?![\\s\\S])") for pattern in anchored)


def test_schema_couples_the_region_span_to_the_hybrid_class():
    """The iff, stated in the schema itself rather than only in
    ``ManagedArtifact.__post_init__`` -- a hand-edited file is rejected at
    READ time, before any dataclass is constructed."""
    entry = store._load_schema()["$defs"]["managedArtifact"]
    assert entry["if"]["properties"]["class"]["const"] == "hybrid-managed-region"
    assert entry["then"]["properties"]["inserted_region_span"]["type"] == "object"
    assert entry["else"]["properties"]["inserted_region_span"]["type"] == "null"


def test_schema_opt_out_artifact_half_is_as_permissive_as_a_managed_id():
    """``managed[].id`` is a ``nonBlankString`` (``model/manifest.py``
    imposes no kebab rule on entry ids), so the opt-out's artifact half
    must not be stricter -- a legally-named entry with an unrepresentable
    opt-out is the defect this pairing exists to prevent."""
    schema = store._load_schema()
    assert schema["$defs"]["managedArtifact"]["properties"]["id"]["$ref"] == ("#/$defs/nonBlankString")
    pattern = schema["properties"]["opted_out"]["items"]["pattern"]
    for accepted in ("bmad.method#tiers", "AGENTS.md#tiers", "a_b#t", "10.2#region-1"):
        assert re.search(pattern, accepted), accepted
    for rejected in ("agents-md", "agents-md#Tiers", "agents md#tiers", "a#b#c", "#tiers"):
        assert not re.search(pattern, rejected), rejected


# --- the packaged schema's own failure modes (a broken installation) --------


class _UnreadableResource:
    """Stands in for ``importlib.resources.files(...)`` -- ``/`` keeps
    returning itself, and the read raises."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def __truediv__(self, other: str) -> _UnreadableResource:
        return self

    def read_text(self, encoding: str = "utf-8") -> str:
        raise self._error


@pytest.fixture
def _uncached_schema_text():
    """``_schema_text`` is process-cached, so a stub only takes effect with
    the cache cleared on both sides of the test."""
    store._schema_text.cache_clear()
    yield
    store._schema_text.cache_clear()


def test_a_missing_packaged_schema_is_an_internal_error(monkeypatch, _uncached_schema_text):
    """``_load_schema`` runs inside ``read_state``'s ``except
    ValidationError`` scope, so a raw ``FileNotFoundError`` escaped the read
    path entirely -- and a broken installation is exit 10, never invalid
    state (exit 5), which would send an operator to repair a fine file."""
    monkeypatch.setattr(store.resources, "files", lambda package: _UnreadableResource(FileNotFoundError(package)))
    with pytest.raises(InternalError) as excinfo:
        store._load_schema()
    assert excinfo.value.exit_code == 10
    assert excinfo.value.remedy.strip()
    assert "schema.json" in str(excinfo.value)


def test_a_corrupt_packaged_schema_is_an_internal_error(monkeypatch, _uncached_schema_text):
    class _Corrupt(_UnreadableResource):
        def read_text(self, encoding: str = "utf-8") -> str:
            return "{ not json"

    monkeypatch.setattr(store.resources, "files", lambda package: _Corrupt(ValueError()))
    with pytest.raises(InternalError) as excinfo:
        store._load_schema()
    assert excinfo.value.exit_code == 10
    assert excinfo.value.remedy.strip()


@pytest.mark.parametrize(
    "schema",
    [
        pytest.param({"properties": {}}, id="key-gone"),
        pytest.param({"properties": {"opted_out": {"items": {"pattern": "("}}}}, id="uncompilable"),
        pytest.param({"properties": {"opted_out": {"items": []}}}, id="wrong-shape"),
    ],
)
def test_a_schema_that_lost_its_opt_out_pattern_is_an_internal_error(monkeypatch, schema):
    """``_schema_text``/``_load_schema`` wrap both of THEIR failure modes in
    an exit-10 ``InternalError`` with a reinstall remedy; the raw subscript
    chain into ``properties.opted_out.items.pattern`` raised a bare
    ``KeyError``/``TypeError``/``re.error`` instead -- same corrupt install,
    two different exits. It is reachable from ``build_plan`` through
    ``opt_out_key_or_none``, which is documented as degrading rather than
    crashing on a bad pair, so the inconsistency was visible from the plan
    path. ``opted_out.items`` is also one of only two INLINE patterns in a
    schema whose dominant convention is ``$ref``, so a refactor toward that
    convention lands here first."""
    store._opt_out_pattern.cache_clear()
    monkeypatch.setattr(store, "_load_schema", lambda: schema)
    try:
        with pytest.raises(InternalError) as excinfo:
            store._opt_out_pattern()
    finally:
        store._opt_out_pattern.cache_clear()
    assert excinfo.value.exit_code == 10
    assert excinfo.value.remedy.strip()
    assert "opted_out" in str(excinfo.value)


def test_a_broken_packaged_schema_never_escapes_the_read_path(tmp_path, monkeypatch, _uncached_schema_text):
    _write_raw(tmp_path, yaml.safe_dump(_valid_document(), sort_keys=False))
    store._validator.cache_clear()
    monkeypatch.setattr(store.resources, "files", lambda package: _UnreadableResource(FileNotFoundError("gone")))
    try:
        with pytest.raises(InternalError):
            read_state(tmp_path)
    finally:
        store._validator.cache_clear()


def test_load_schema_hands_out_a_fresh_object_every_call():
    """A cached call handed every caller the SAME mutable dict, so one
    caller mutating it silently poisoned every later validation in the
    process. Only the TEXT is cached now."""
    first = store._load_schema()
    second = store._load_schema()
    assert first is not second
    assert first == second
    first["properties"].pop("mode")
    assert "mode" in store._load_schema()["properties"]


# --- dataclass serialization ------------------------------------------------


def test_to_json_dict_emits_the_eleven_keys_in_schema_order():
    assert tuple(_sample_state().to_json_dict()) == STATE_KEYS


def test_state_round_trips_through_its_own_json_form():
    state = _sample_state()
    assert SeedState.from_json_dict(json.loads(json.dumps(state.to_json_dict()))) == state


def test_managed_artifact_serializes_class_under_the_reserved_word_key():
    document = _sample_state().to_json_dict()
    assert document["managed"][0]["class"] == "hybrid-managed-region"
    assert "artifact_class" not in document["managed"][0]


def test_from_json_dict_reports_a_missing_key_as_a_plain_value_error():
    document = _valid_document()
    del document["mode"]
    with pytest.raises(ValueError, match="missing required key 'mode'"):
        SeedState.from_json_dict(document)


def test_from_json_dict_rejects_a_bool_where_a_byte_offset_belongs():
    """`bool` is a subtype of `int` in Python, so `True` would otherwise
    load as the byte offset `1`."""
    with pytest.raises(ValueError, match="expected an int"):
        RegionSpanRecord.from_json_dict({"name": "tiers", "start": True, "end": 20})


# --- frozen means frozen: coercion + the cross-entry invariants -------------


def test_a_sequence_field_given_a_list_round_trips_equal(tmp_path):
    """``frozen=True`` was a half-promise: a ``list`` passed straight
    through, so ``read_state`` returned a NON-equal object and
    ``state.agents.append(...)`` mutated the "frozen" instance."""
    state = _sample_state(agents=["claude-code", "codex-cli"], skips=["docs/legacy/*.md"])
    assert state.agents == ("claude-code", "codex-cli")
    assert isinstance(state.agents, tuple) and isinstance(state.skips, tuple)
    assert state == _sample_state()
    write_state(state, repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert read_state(tmp_path) == state


def test_model_version_given_a_plain_string_is_rejected_at_construction():
    """The same half-promise on the one field a JSON Schema can never
    police: ``to_json_dict`` renders ``model_version`` with ``str(...)``,
    so a plain ``str`` used to serialize identically, validate, and come
    back from ``read_state`` as a ``ModelVersion`` -- silently NON-equal."""
    with pytest.raises(ValueError, match="must be a ModelVersion"):
        _sample_state(model_version="1.0.0")


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        pytest.param("agents", ("claude-code", 7), id="agents-non-str"),
        pytest.param("agents", "claude-code", id="agents-bare-str"),
        pytest.param("skips", [None], id="skips-none"),
        pytest.param("migrations_applied", (1.2,), id="migrations-non-str"),
        pytest.param("opted_out", {"agents-md#tiers"}, id="opted-out-set"),
        pytest.param("managed", ({"id": "x"},), id="managed-raw-dict"),
        pytest.param("legacy", (object(),), id="legacy-wrong-type"),
    ],
)
def test_a_wrong_typed_sequence_item_is_rejected_at_construction(field_name, value):
    """A bare ``str`` is rejected too, even though it is iterable:
    ``tuple("claude")`` would silently become six one-character agents."""
    with pytest.raises(ValueError, match=f"SeedState.{re.escape(field_name)}"):
        _sample_state(**{field_name: value})


def test_two_managed_entries_may_not_claim_the_same_id():
    """``model/manifest.py`` enforces id uniqueness for entries; state must
    too, or the recorded-hash lookup becomes order-dependent."""
    duplicate = dataclasses.replace(_sample_state().managed[0], body_sha="ffffffff")
    with pytest.raises(ValueError, match=r"managed\[\].id"):
        _sample_state(managed=(_sample_state().managed[0], duplicate))


def test_two_managed_entries_may_not_claim_the_same_path():
    first, second = _sample_state().managed
    with pytest.raises(ValueError, match=r"managed\[\].path"):
        _sample_state(managed=(first, dataclasses.replace(second, path=first.path)))


def test_two_legacy_entries_may_not_share_an_id():
    entry = _sample_state().legacy[0]
    with pytest.raises(ValueError, match=r"legacy\[\].id"):
        _sample_state(legacy=(entry, dataclasses.replace(entry, path="docs/specs/other.md")))


def test_migrations_applied_is_unique_by_version_not_by_string():
    """``uniqueItems`` compares strings, but ``ModelVersion`` excludes build
    metadata from equality (SemVer 2.0.0 section 10) -- so these two
    entries name ONE version, and a migration guarded by the list could run
    twice."""
    assert ModelVersion.parse("1.2.0") == ModelVersion.parse("1.2.0+build")
    with pytest.raises(ValueError, match="migrations_applied"):
        _sample_state(migrations_applied=("1.2.0", "1.2.0+build"))


def test_an_inverted_region_span_is_rejected_at_construction():
    """``fs.replace_span`` validates ``0 <= start <= end`` for exactly this
    reason: an eject splice built from an inverted record --
    ``doc[:start] + doc[end:]`` -- DUPLICATES bytes instead of stripping a
    region."""
    with pytest.raises(ValueError, match="0 <= start <= end"):
        RegionSpanRecord(name="tiers", start=100, end=5)


def test_a_negative_region_offset_is_rejected_at_construction():
    with pytest.raises(ValueError, match="0 <= start <= end"):
        RegionSpanRecord(name="tiers", start=-1, end=5)


def test_an_empty_region_body_is_still_a_legal_span():
    assert RegionSpanRecord(name="tiers", start=7, end=7).end == 7


def test_a_hybrid_claim_without_a_span_is_rejected():
    """AD-58's eject needs the byte offsets; a hybrid claim with no span is
    one it cannot withdraw at all."""
    with pytest.raises(ValueError, match="requires an inserted_region_span"):
        ManagedArtifact(
            id="agents-md",
            path="AGENTS.md",
            artifact_class="hybrid-managed-region",
            body_sha="0123abcd",
            inserted_region_span=None,
        )


def test_a_whole_file_claim_carrying_a_span_is_rejected():
    """The other direction: a span on a ``referenced`` claim invites an
    eject to splice a file it was supposed to remove outright."""
    with pytest.raises(ValueError, match="belongs only to class"):
        ManagedArtifact(
            id="agents-md",
            path="AGENTS.md",
            artifact_class="referenced",
            body_sha="0123abcd",
            inserted_region_span=RegionSpanRecord(name="tiers", start=0, end=1),
        )


# --- I/O matrix row 1: round-trip + FR-103's header -------------------------


def test_write_then_read_returns_an_equal_state(tmp_path):
    state = _sample_state()
    write_state(state, repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert read_state(tmp_path) == state


def test_written_file_opens_with_a_do_not_hand_edit_header(tmp_path):
    write_state(_sample_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    text = state_path(tmp_path).read_text(encoding="utf-8")
    first_line = text.splitlines()[0]
    assert first_line.startswith("#")
    assert "DO NOT HAND-EDIT" in first_line
    header = text[: text.index("model_version:")].lower()
    assert "marshal seed" in header
    assert "owned" in header
    assert all(line.startswith("#") or not line.strip() for line in header.splitlines())


def test_the_header_is_ignored_on_read(tmp_path):
    """The header is re-emitted on every write and carries no value -- a
    round-trip through a file that starts with eleven comment lines is the
    proof."""
    state = _sample_state()
    write_state(state, repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert state_path(tmp_path).read_text(encoding="utf-8").startswith("#")
    assert read_state(tmp_path) == state


def test_the_header_does_not_overstate_what_happens_to_a_hand_edit(tmp_path):
    """The header used to promise a hand edit is "either overwritten
    without warning or reported as invalid state (exit 5)" -- but a
    schema-VALID edit is neither: it is silently BELIEVED by every read
    until the next write. Asserted against the behaviour it describes, so
    the wording cannot drift back."""
    write_state(_sample_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    text = state_path(tmp_path).read_text(encoding="utf-8")
    _write_raw(tmp_path, text.replace("mode: init", "mode: adopt"))
    loaded = read_state(tmp_path)
    assert loaded is not None
    assert loaded.mode == "adopt"

    header = text[: text.index("model_version:")]
    assert "believes" in header.lower()
    assert "either overwritten without warning" not in header


def test_state_path_is_the_git_tracked_marshal_file(tmp_path):
    assert state_path(tmp_path) == tmp_path / ".marshal" / "seed-state.yml"


#: A flow sequence carrying at least one item -- ``[`` NOT immediately
#: closed. ``default_flow_style=False`` suppresses those, but it does NOT
#: suppress the EMPTY ``[]`` a ``yaml.safe_dump``ed empty list always emits
#: (confirmed), which is the normal shape of a fresh ``init``'s `skips` /
#: `legacy` / `migrations_applied` / `opted_out`. Asserting a bare ``"["
#: not in text`` therefore only holds for a state with every collection
#: populated -- true, but vacuous about the shape the tool actually writes
#: most often (review finding), so the block-style claim is scoped to
#: NON-empty collections and the empty case is asserted for what it really
#: is, in its own round-trip test below.
_NON_EMPTY_FLOW_SEQUENCE = re.compile(r"\[(?!\])")


def test_written_yaml_is_block_style_and_key_ordered(tmp_path):
    write_state(_sample_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    text = state_path(tmp_path).read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    assert tuple(document) == STATE_KEYS
    assert "{" not in text
    assert _NON_EMPTY_FLOW_SEQUENCE.search(text) is None
    # This state populates every collection, so there is no `[]` either.
    assert "[" not in text


def test_a_state_with_every_collection_empty_round_trips(tmp_path):
    """The shape a fresh ``init`` actually writes: five empty collections,
    which the fully-populated ``_sample_state`` never exercises."""
    empty = _sample_state(
        agents=(),
        managed=(),
        skips=(),
        legacy=(),
        migrations_applied=(),
        opted_out=(),
    )
    write_state(empty, repo_root=tmp_path, never_write=_NO_PATTERNS)
    loaded = read_state(tmp_path)
    assert loaded == empty
    assert loaded is not None
    assert loaded.managed == () and loaded.legacy == ()
    text = state_path(tmp_path).read_text(encoding="utf-8")
    for key in ("agents", "managed", "skips", "legacy", "migrations_applied", "opted_out"):
        assert f"{key}: []" in text
    assert "{" not in text
    assert _NON_EMPTY_FLOW_SEQUENCE.search(text) is None


def test_writing_twice_is_byte_stable(tmp_path):
    state = _sample_state()
    write_state(state, repo_root=tmp_path, never_write=_NO_PATTERNS)
    first = state_path(tmp_path).read_bytes()
    write_state(state, repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert state_path(tmp_path).read_bytes() == first


# --- I/O matrix row 2: never adopted ----------------------------------------


def test_read_state_returns_none_for_a_never_adopted_repo(tmp_path):
    assert read_state(tmp_path) is None


def test_read_state_returns_none_when_marshal_exists_but_state_does_not(tmp_path):
    (tmp_path / ".marshal").mkdir()
    assert read_state(tmp_path) is None


def test_read_state_reports_a_directory_at_the_state_path_as_invalid(tmp_path):
    state_path(tmp_path).mkdir(parents=True)
    with pytest.raises(StateInvalid) as excinfo:
        read_state(tmp_path)
    assert excinfo.value.exit_code == 5


# --- I/O matrix row 3: schema violations ------------------------------------


@pytest.mark.parametrize(
    ("mutate", "expected_fragment"),
    [
        pytest.param(lambda doc: doc.pop("mode"), "mode", id="missing-required-key"),
        pytest.param(lambda doc: doc.update(slug="local-recipes"), "slug", id="unknown-top-level-key"),
        pytest.param(lambda doc: doc["managed"][0].update(body_sha="ZZ"), "body_sha", id="bad-body-sha"),
        pytest.param(lambda doc: doc.update(mode="update"), "mode", id="mode-outside-the-enum"),
        pytest.param(
            lambda doc: doc.update(adopted_at="2026-08-14 09:15"),
            "adopted_at",
            id="non-rfc3339-timestamp",
        ),
        pytest.param(
            lambda doc: doc["managed"][0]["inserted_region_span"].update(start=-1),
            "start",
            id="negative-byte-offset",
        ),
        pytest.param(lambda doc: doc.update(agents=["Claude Code"]), "agents", id="non-kebab-agent-id"),
        pytest.param(lambda doc: doc.update(opted_out=["agents-md"]), "opted_out", id="opt-out-without-region"),
        pytest.param(
            lambda doc: doc.update(migrations_applied=["1.2.0", "1.2.0"]),
            "migrations_applied",
            id="duplicate-migration",
        ),
        pytest.param(lambda doc: doc["managed"][0].update(extra="x"), "extra", id="unknown-managed-key"),
        pytest.param(lambda doc: doc.update(model_version="1.2"), "model_version", id="non-semver-version"),
        pytest.param(
            lambda doc: doc["managed"][0].update(inserted_region_span=None),
            "inserted_region_span",
            id="hybrid-claim-without-a-span",
        ),
        pytest.param(
            lambda doc: doc["managed"][1].update(inserted_region_span={"name": "tiers", "start": 0, "end": 1}),
            "inserted_region_span",
            id="whole-file-claim-carrying-a-span",
        ),
        pytest.param(
            lambda doc: doc["managed"][0]["inserted_region_span"].update(name="Tiers"),
            "name",
            id="non-marker-safe-region-name",
        ),
        pytest.param(
            lambda doc: doc.update(opted_out=["agents-md#Tiers"]),
            "opted_out",
            id="opt-out-with-a-non-marker-safe-region-half",
        ),
        pytest.param(
            lambda doc: doc.update(opted_out=["agents md#tiers"]),
            "opted_out",
            id="opt-out-with-whitespace-in-the-artifact-half",
        ),
    ],
)
def test_schema_violations_raise_state_invalid_naming_the_field(tmp_path, mutate, expected_fragment):
    document = _valid_document()
    mutate(document)
    _write_raw(tmp_path, yaml.safe_dump(document, sort_keys=False))
    with pytest.raises(StateInvalid) as excinfo:
        read_state(tmp_path)
    assert excinfo.value.exit_code == 5
    assert excinfo.value.remedy.strip()
    assert expected_fragment in str(excinfo.value)


@pytest.mark.parametrize(
    ("mutate", "expected_fragment"),
    [
        pytest.param(
            lambda doc: doc["managed"][0].update(body_sha="0123abcd\n"),
            "body_sha",
            id="body-sha",
        ),
        pytest.param(
            lambda doc: doc["managed"][0]["inserted_region_span"].update(name="tiers\n"),
            "name",
            id="region-name",
        ),
        pytest.param(
            lambda doc: doc.update(model_version="1.2.3\n"),
            "model_version",
            id="model-version",
        ),
    ],
)
def test_a_trailing_newline_never_satisfies_an_anchored_pattern(tmp_path, mutate, expected_fragment):
    """Python's ``$`` matches immediately before a final newline, so
    ``"0123abcd\\n"`` passed ``^[0-9a-f]{8}$`` -- falsifying the schema's
    own stated guarantees (DW-FU-9-3's closure, "always round-trips through
    a rendered marker", "can never fail ``ModelVersion.parse``"). Written
    as JSON, which is legal YAML, so the exact string reaches the validator
    without any block-scalar quoting to reason about."""
    document = _valid_document()
    mutate(document)
    _write_raw(tmp_path, json.dumps(document))
    with pytest.raises(StateInvalid) as excinfo:
        read_state(tmp_path)
    assert excinfo.value.exit_code == 5
    assert expected_fragment in str(excinfo.value)


def test_an_opt_out_naming_a_dotted_artifact_id_round_trips(tmp_path):
    """``managed[].id`` is any non-blank string, so the opt-out's artifact
    half must accept one too -- a legally-named entry whose opt-out cannot
    be spelled is the defect."""
    state = _sample_state(opted_out=("bmad.method#tiers", "AGENTS.md#tiers"))
    write_state(state, repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert read_state(tmp_path) == state


# --- I/O matrix row 4: malformed input --------------------------------------


_MALFORMED_PAYLOADS = [
    pytest.param("model_version: [1.2.3\n", id="invalid-yaml"),
    pytest.param("mode: init\nmode: adopt\n", id="duplicate-mapping-key"),
    pytest.param(b"model_version: \xff\xfe\n", id="non-utf8-bytes"),
    pytest.param("- one\n- two\n", id="non-mapping-root"),
    pytest.param("", id="empty-file"),
    pytest.param("<<: *missing\n", id="undefined-merge-anchor"),
    pytest.param("defaults: &d\n  mode: adopt\n<<: *d\n", id="resolvable-merge-key"),
    pytest.param("<<: &shared\n  mode: init\n  mode: adopt\nother: 1\n", id="merged-duplicate"),
    pytest.param('!!map "x"\n', id="non-mapping-node-tagged-as-a-map"),
]


@pytest.mark.parametrize("payload", _MALFORMED_PAYLOADS)
def test_malformed_input_raises_only_state_invalid(tmp_path, payload):
    _write_raw(tmp_path, payload)
    with pytest.raises(StateInvalid) as excinfo:
        read_state(tmp_path)
    assert excinfo.value.exit_code == 5
    assert excinfo.value.remedy.strip()


def test_state_invalid_is_none_of_the_types_it_replaces():
    """FR-104's "never a traceback" stated as the type contract it is:
    catching ``StateInvalid`` cannot accidentally be satisfied by one of
    the underlying library/stdlib types, so the parametrized reads above
    genuinely prove nothing leaks."""
    for leaked in (yaml.YAMLError, UnicodeDecodeError, OSError, ValueError):
        assert not issubclass(StateInvalid, leaked)


@pytest.mark.parametrize("payload", _MALFORMED_PAYLOADS)
def test_no_underlying_exception_type_escapes_the_read_path(tmp_path, payload):
    """The same inputs again, asserted from the other side: an
    ``except`` clause naming any of the four underlying types catches
    nothing, because the only thing in flight is ``StateInvalid``."""
    _write_raw(tmp_path, payload)
    try:
        read_state(tmp_path)
    except (yaml.YAMLError, UnicodeDecodeError, OSError, ValueError) as exc:  # pragma: no cover
        pytest.fail(f"read_state leaked {type(exc).__name__}: {exc}")
    except StateInvalid:
        return
    pytest.fail("read_state accepted a malformed document")


def test_duplicate_key_is_rejected_rather_than_resolved_last_wins(tmp_path):
    """Plain ``SafeLoader`` would load this document clean with
    ``mode: adopt`` winning -- the file a human reviewed in the diff would
    not be the file Genesis loaded."""
    document = _valid_document()
    text = yaml.safe_dump(document, sort_keys=False) + "mode: adopt\n"
    _write_raw(tmp_path, text)
    with pytest.raises(StateInvalid, match="duplicate key"):
        read_state(tmp_path)


def test_a_merge_key_is_refused_outright(tmp_path):
    """The override idiom is refused, not tolerated: ``write_state``
    (``yaml.safe_dump``) emits no anchor, alias, or merge key at all, so a
    ``<<:`` here is always a hand edit -- and tolerating it left the
    duplicate rule bypassable (see the next test)."""
    document = _valid_document()
    text = "defaults: &defaults\n  mode: adopt\n" + yaml.safe_dump(document, sort_keys=False)
    text = text.replace("mode: init\n", "<<: *defaults\nmode: init\n")
    _write_raw(tmp_path, text)
    with pytest.raises(StateInvalid, match="merge key") as excinfo:
        read_state(tmp_path)
    assert excinfo.value.exit_code == 5


def test_a_duplicate_authored_inside_a_merge_anchor_is_not_resolved_last_wins(tmp_path):
    """The bypass the outright refusal closes: ``flatten_mapping()``
    splices the ANCHORED node's pairs into the document without ever
    calling ``construct_mapping`` on it, so this loaded clean as
    ``{'mode': 'adopt', 'other': 1}`` -- the exact last-wins outcome
    ``_StrictLoader`` exists to prevent."""
    _write_raw(tmp_path, "<<: &shared\n  mode: init\n  mode: adopt\nother: 1\n")
    with pytest.raises(StateInvalid, match="merge key"):
        read_state(tmp_path)


def test_a_non_mapping_node_tagged_as_a_map_is_state_invalid(tmp_path):
    """``!!map "x"`` reaches ``construct_mapping`` as a ``ScalarNode``, and
    iterating its ``str`` value raised a bare ``ValueError`` -- not a
    ``yaml.YAMLError`` -- straight past ``read_state``'s handler, breaking
    FR-104's "only ``StateInvalid``" contract."""
    with pytest.raises(yaml.YAMLError):
        yaml.load('!!map "x"\n', Loader=store._StrictLoader)
    _write_raw(tmp_path, '!!map "x"\n')
    with pytest.raises(StateInvalid) as excinfo:
        read_state(tmp_path)
    assert excinfo.value.exit_code == 5


# --- I/O matrix row 2 again: absence vs. a dangling link --------------------


def test_a_dangling_symlink_at_the_state_path_is_invalid_not_absent(tmp_path):
    """``read_bytes()`` on a broken symlink raises the same
    ``FileNotFoundError`` a genuinely absent file does, so the absence
    branch swallowed it -- an adopted repo whose link target is gone looked
    never-adopted, after which ``init`` could re-establish over an existing
    installation."""
    path = state_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.symlink_to(tmp_path / "somewhere-else.yml")
    assert path.is_symlink() and not path.exists()
    with pytest.raises(StateInvalid) as excinfo:
        read_state(tmp_path)
    assert excinfo.value.exit_code == 5
    assert excinfo.value.remedy.strip()
    assert "symlink" in str(excinfo.value)


def test_a_live_symlink_at_the_state_path_still_reads(tmp_path):
    """The complement: only a DANGLING link is invalid -- a link whose
    target exists is an ordinary read."""
    target = tmp_path / "elsewhere.yml"
    write_state(_sample_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    state_path(tmp_path).rename(target)
    state_path(tmp_path).symlink_to(target)
    assert read_state(tmp_path) == _sample_state()


# --- operator-facing messages stay one line ---------------------------------


def test_a_huge_malformed_value_is_truncated_in_the_message(tmp_path):
    """A malformed state document is frequently a LARGE one, and every
    message here ends up in a ``StateInvalid`` an operator reads on one
    terminal line."""
    _write_raw(tmp_path, "- " + "y" * 10_000 + "\n")
    with pytest.raises(StateInvalid) as excinfo:
        read_state(tmp_path)
    assert len(excinfo.value.message) < len(str(state_path(tmp_path))) + 200
    assert excinfo.value.message.endswith("...")


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda: store._require_str_tuple({"x": "y" * 10_000}, context="SeedState.agents"),
            id="require-str-tuple",
        ),
        pytest.param(
            lambda: store._require_object_list(["y" * 10_000], context="SeedState.managed"),
            id="require-object-list",
        ),
        pytest.param(
            lambda: store._require_str(["y" * 10_000], context="SeedState.mode"),
            id="require-str",
        ),
    ],
)
def test_a_shape_complaint_truncates_the_value_it_interpolates(call):
    with pytest.raises(ValueError) as excinfo:
        call()
    assert len(str(excinfo.value)) < 300
    assert str(excinfo.value).endswith("...")


# --- I/O matrix row 5: invalid state written --------------------------------


def test_write_state_refuses_an_invalid_document_before_any_io(tmp_path):
    with pytest.raises(StateInvalid) as excinfo:
        write_state(
            _sample_state(adopted_at="2026-08-14 09:15"),
            repo_root=tmp_path,
            never_write=_NO_PATTERNS,
        )
    assert excinfo.value.exit_code == 5
    assert excinfo.value.remedy.strip()
    assert "adopted_at" in str(excinfo.value)
    assert not (tmp_path / ".marshal").exists()


def test_a_refused_write_leaves_an_existing_state_file_byte_identical(tmp_path):
    write_state(_sample_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    original = state_path(tmp_path).read_bytes()
    with pytest.raises(StateInvalid):
        write_state(_sample_state(mode="update"), repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert state_path(tmp_path).read_bytes() == original


def test_write_state_makes_exactly_one_atomic_replace(tmp_path, monkeypatch):
    """P-08's "one atomic replace", counted rather than asserted in prose."""
    calls: list[Path] = []
    real = fs.atomic_write_bytes

    def counting(path: Path, data: bytes) -> None:
        calls.append(path)
        real(path, data)

    monkeypatch.setattr(fs, "atomic_write_bytes", counting)
    write_state(_sample_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert calls == [state_path(tmp_path)]


# --- I/O matrix row 6: mid-apply failure ------------------------------------


def test_mid_apply_failure_leaves_state_untouched_and_no_tmp_residue(tmp_path, monkeypatch):
    """Four artifact writes land, the state write then fails MID-WRITE: the
    pre-existing state file must be byte-identical and ``.marshal/`` must
    hold no temp-file residue.

    The fault is injected INSIDE the real ``pyforge.core.atomic_write`` --
    a ``write_fn`` that populates the temp file and only then raises -- so
    a temp file genuinely exists in ``.marshal/`` at the moment it fires.
    An earlier version replaced ``fs.atomic_write_bytes`` wholesale and
    raised before the real implementation ran, which meant no temp file was
    ever created and "no ``.tmp`` residue" was true by construction,
    proving nothing about cleanup (review finding)."""
    write_state(_sample_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    original = state_path(tmp_path).read_bytes()

    real_atomic_write = core_atomic_write.atomic_write
    temp_paths: list[Path] = []
    existed_when_the_fault_fired: list[bool] = []

    def failing_inside_the_real_atomic_write(path: Path, data: bytes) -> None:
        def write_fn(tmp: Path) -> None:
            tmp.write_bytes(data)
            temp_paths.append(tmp)
            if path == state_path(tmp_path):
                existed_when_the_fault_fired.append(tmp.exists())
                raise OSError("no space left on device")

        real_atomic_write(path, write_fn)

    monkeypatch.setattr(fs, "atomic_write_bytes", failing_inside_the_real_atomic_write)

    queued = [tmp_path / f"artifact-{index}.md" for index in range(4)]
    with pytest.raises(OSError, match="no space left"):
        for target in queued:
            fs.write(target, b"body\n", repo_root=tmp_path, never_write=_NO_PATTERNS)
        write_state(
            dataclasses.replace(_sample_state(), last_update="2026-08-14T12:00:00Z"),
            repo_root=tmp_path,
            never_write=_NO_PATTERNS,
        )

    assert len(temp_paths) == 5
    state_temp = temp_paths[-1]
    # The fault fired with a real, populated temp file in `.marshal/` ...
    assert existed_when_the_fault_fired == [True]
    assert state_temp.parent == tmp_path / ".marshal"
    # ... which `atomic_write` then cleaned up, leaving the original intact.
    assert not state_temp.exists()
    assert state_path(tmp_path).read_bytes() == original
    assert sorted(p.name for p in (tmp_path / ".marshal").iterdir()) == ["seed-state.yml"]
    assert all(target.read_bytes() == b"body\n" for target in queued)


# --- I/O matrix row 7: guarded path -----------------------------------------


def test_a_never_write_guarded_state_path_raises_never_write_violation(tmp_path):
    never_write = fs.NeverWrite((".marshal/seed-state.yml",))
    with pytest.raises(NeverWriteViolation) as excinfo:
        write_state(_sample_state(), repo_root=tmp_path, never_write=never_write)
    assert excinfo.value.exit_code == 4
    assert not state_path(tmp_path).exists()


def test_an_os_error_from_fs_propagates_unwrapped(tmp_path, monkeypatch):
    """A failed write means the ENVIRONMENT refused, not that state is
    invalid -- so the ``OSError`` reaches the caller as itself."""

    def boom(path: Path, data: bytes) -> None:
        raise PermissionError("read-only file system")

    monkeypatch.setattr(fs, "atomic_write_bytes", boom)
    with pytest.raises(PermissionError):
        write_state(_sample_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)


def test_a_repo_root_that_is_not_a_directory_raises_the_documented_value_error(tmp_path):
    """``fs._guard`` raises a plain ``ValueError`` for a ``repo_root`` that
    does not resolve to an existing directory -- outside the ``SeedError``
    taxonomy and not an ``OSError``, so a caller catching
    ``(SeedError, OSError)`` gets a traceback. Deliberately not converted
    (that would fight ``fs.py``'s contract), so ``write_state``'s docstring
    has to say so."""
    with pytest.raises(ValueError, match="does not resolve to an existing directory"):
        write_state(_sample_state(), repo_root=tmp_path / "never-created", never_write=_NO_PATTERNS)
    assert "ValueError" in write_state.__doc__
    assert "repo_root" in write_state.__doc__


# --- AC: eject reconstruction from state.managed alone (AD-58) --------------


def test_managed_entries_alone_reconstruct_the_removal_set():
    state = _sample_state()
    removal_set = [
        (artifact.path, artifact.artifact_class, artifact.body_sha, artifact.inserted_region_span)
        for artifact in state.managed
    ]
    assert removal_set == [
        ("AGENTS.md", "hybrid-managed-region", "0123abcd", RegionSpanRecord("tiers", 7, 20)),
        ("docs/dreams/example.md", "copied-seeded", "deadbeef", None),
    ]


def test_a_hybrid_entrys_span_strips_its_region_without_touching_the_rest():
    """AD-58's actual requirement: the recorded name + body span are
    enough to withdraw the claim, leaving every byte outside the span
    identical (the same reconstruction identity ``fs.replace_span`` and
    ``regions/parse.py`` already document)."""
    prefix, body, suffix = b"before\n", b"managed body\n", b"after\n"
    document = prefix + body + suffix
    artifact = ManagedArtifact(
        id="agents-md",
        path="AGENTS.md",
        artifact_class="hybrid-managed-region",
        body_sha="0123abcd",
        inserted_region_span=RegionSpanRecord(name="tiers", start=len(prefix), end=len(prefix) + len(body)),
    )
    span = artifact.inserted_region_span
    assert span is not None
    assert document[span.start : span.end] == body
    assert document[: span.start] + document[span.end :] == prefix + suffix
    assert span.name == "tiers"


def test_a_region_span_survives_the_file_round_trip(tmp_path):
    write_state(_sample_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    loaded = read_state(tmp_path)
    assert loaded is not None
    assert loaded.managed[0].inserted_region_span == RegionSpanRecord("tiers", 7, 20)
    assert loaded.managed[1].inserted_region_span is None


# --- AC: the error taxonomy stays closed ------------------------------------


def test_seed_error_still_has_exactly_six_leaves():
    assert len(SeedError.__subclasses__()) == 6


def test_state_invalid_is_exit_code_five():
    assert StateInvalid.exit_code == 5


# --- the two clocks, the timestamp owner, and the Copier projection ---------


def test_seed_model_version_reports_the_installed_distribution():
    version = seed_model_version()
    assert version == metadata.version("pyforge-marshal")
    pattern = store._load_schema()["$defs"]["packageVersion"]["pattern"]
    assert re.fullmatch(pattern, version)


def test_seed_model_version_reports_a_missing_distribution_as_internal_error(monkeypatch):
    def missing(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(store.metadata, "version", missing)
    with pytest.raises(InternalError) as excinfo:
        seed_model_version()
    assert excinfo.value.exit_code == 10
    assert excinfo.value.remedy.strip()


def test_utc_timestamp_emits_the_schemas_exact_shape():
    pattern = store._load_schema()["$defs"]["timestamp"]["pattern"]
    assert re.fullmatch(pattern, utc_timestamp())


def test_utc_timestamp_converts_an_aware_non_utc_moment():
    from datetime import datetime, timedelta, timezone

    moment = datetime(2026, 8, 14, 11, 30, 0, tzinfo=timezone(timedelta(hours=2)))
    assert utc_timestamp(moment) == "2026-08-14T09:30:00Z"


def test_utc_timestamp_rejects_a_naive_datetime():
    from datetime import datetime

    with pytest.raises(ValueError, match="timezone-aware"):
        utc_timestamp(datetime(2026, 8, 14, 11, 30, 0))


def test_utc_timestamp_output_is_accepted_by_the_schema(tmp_path):
    stamp = utc_timestamp()
    state = _sample_state(adopted_at=stamp, last_update=stamp)
    write_state(state, repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert read_state(tmp_path) == state


def test_copier_data_projects_only_what_state_knows():
    assert copier_data(_sample_state()) == {
        "model_version": "1.2.3",
        "seed_model_version": "0.1.0",
        "mode": "init",
        "agents": ["claude-code", "codex-cli"],
    }


def test_copier_data_invents_no_slug_or_answers_map():
    projection = copier_data(_sample_state())
    assert "slug" not in projection
    assert "answers" not in projection


# --- AC: import surface + no second atomic write ----------------------------


def _store_source() -> str:
    return Path(store.__file__).read_text(encoding="utf-8")


def _resolved_marshal_imports() -> set[str]:
    """Every ``pyforge.marshal.*`` module ``store.py`` imports, with
    relative imports resolved against its own package
    (``pyforge.marshal.seed.state``)."""
    package_parts = store.__name__.split(".")[:-1]
    resolved: set[str] = set()
    for node in ast.walk(ast.parse(_store_source())):
        if isinstance(node, ast.Import):
            resolved.update(alias.name for alias in node.names if alias.name.startswith("pyforge.marshal"))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module and node.module.startswith("pyforge.marshal"):
                    resolved.add(node.module)
                continue
            base = ".".join(package_parts[: len(package_parts) - (node.level - 1)])
            prefix = f"{base}.{node.module}" if node.module else base
            resolved.add(prefix)
            resolved.update(f"{prefix}.{alias.name}" for alias in node.names)
    return resolved


def test_store_never_imports_upward():
    forbidden = (
        "pyforge.marshal.seed.detect",
        "pyforge.marshal.seed.plan",
        "pyforge.marshal.seed.apply",
        "pyforge.marshal.seed.verbs",
        "pyforge.marshal.seed.engine",
    )
    offenders = [
        name
        for name in _resolved_marshal_imports()
        for banned in forbidden
        if name == banned or name.startswith(f"{banned}.")
    ]
    assert not offenders, f"store.py imports upward: {offenders}"


def test_store_imports_only_its_declared_marshal_surface():
    assert _resolved_marshal_imports() <= {
        "pyforge.marshal.seed",
        "pyforge.marshal.seed.fs",
        "pyforge.marshal.seed.errors",
        "pyforge.marshal.seed.errors.InternalError",
        "pyforge.marshal.seed.errors.StateInvalid",
        "pyforge.marshal.seed.model.version",
        "pyforge.marshal.seed.model.version.ModelVersion",
    }


#: Call names that would put a second atomic write (or half of one) in this
#: module. Matched as CALLS, never as substrings: the previous grep form
#: would have redded the build for a docstring that merely EXPLAINED why
#: the module avoids `mkstemp`, while missing `os.rename`, `Path.rename`,
#: `shutil.move`, `mkdtemp`, and a bare `open(path, "wb")` entirely
#: (review finding).
_FORBIDDEN_WRITE_CALLS = frozenset({"mkstemp", "mkdtemp", "NamedTemporaryFile", "write_bytes", "write_text", "rename"})


def _is_write_mode_call(node: ast.Call, *, mode_index: int) -> bool:
    """True for ``open(path, "wb")``/``path.open("w")`` -- a write-mode
    open, positional or ``mode=``. A read (``.open()``/``.open("r")``) is
    not a write-mechanics signal. ``mode_index`` differs between the two
    spellings: the builtin takes the path first, the method does not."""
    mode_arg: ast.expr | None = node.args[mode_index] if len(node.args) > mode_index else None
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode_arg = keyword.value
    return isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str) and mode_arg.value.startswith("w")


def _write_mechanics_calls(tree: ast.AST) -> list[str]:
    """Every forbidden write-mechanics CALL in ``tree``, by spelling.

    AST-based, so a string literal, comment, or docstring naming any of
    these is exempt by construction -- the module's own docstring says it
    implements no temp-file or rename mechanics, and saying so must not
    trip the check that proves it."""
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        if isinstance(callee, ast.Attribute):
            owner = callee.value.id if isinstance(callee.value, ast.Name) else None
            name = callee.attr
            if name in _FORBIDDEN_WRITE_CALLS:
                offenders.append(name if owner is None else f"{owner}.{name}")
            elif name == "replace" and owner in {"os", "shutil"}:
                offenders.append(f"{owner}.replace")
            elif name == "move" and owner == "shutil":
                offenders.append("shutil.move")
            elif name == "open" and _is_write_mode_call(node, mode_index=0):
                offenders.append(f"{owner}.open" if owner else ".open")
        elif isinstance(callee, ast.Name):
            if callee.id in _FORBIDDEN_WRITE_CALLS or callee.id in {"replace", "move"}:
                offenders.append(callee.id)
            elif callee.id == "open" and _is_write_mode_call(node, mode_index=1):
                offenders.append("open")
    return offenders


def test_store_implements_no_temp_file_or_rename_mechanics():
    """P-01/P-08 and pyforge-core's CAP-7 guard, asserted locally too: the
    module's own source carries neither half of an atomic write."""
    offenders = _write_mechanics_calls(ast.parse(_store_source()))
    assert not offenders, f"store.py must not implement write mechanics: {offenders}"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("import os\nos.rename(a, b)\n", ["os.rename"], id="os-rename"),
        pytest.param("p.rename(other)\n", ["p.rename"], id="path-rename"),
        pytest.param("import shutil\nshutil.move(a, b)\n", ["shutil.move"], id="shutil-move"),
        pytest.param("import tempfile\ntempfile.mkdtemp()\n", ["tempfile.mkdtemp"], id="mkdtemp"),
        pytest.param('open(path, "wb").write(b"x")\n', ["open"], id="bare-write-open"),
        pytest.param('path.open("w")\n', ["path.open"], id="method-write-open"),
        pytest.param("import os\nos.replace(a, b)\n", ["os.replace"], id="os-replace"),
        pytest.param("import tempfile\ntempfile.mkstemp()\n", ["tempfile.mkstemp"], id="mkstemp"),
        pytest.param("p.write_bytes(b'x')\n", ["p.write_bytes"], id="write-bytes"),
    ],
)
def test_the_write_mechanics_guard_fires_on_each_forbidden_spelling(source, expected):
    """Non-vacuous proof, one case per name the grep form used to miss."""
    assert _write_mechanics_calls(ast.parse(source)) == expected


def test_the_write_mechanics_guard_exempts_prose():
    """The other half of the fix: a docstring or comment EXPLAINING why the
    module avoids these primitives is not an implementation of them, and
    must not red the build."""
    prose = (
        '"""This module never calls mkstemp, os.replace, or shutil.move."""\n'
        "# ... and it does not use tmp.write_bytes / Path.rename either.\n"
        'MESSAGE = "refusing to open(path, \\"wb\\")"\n'
    )
    assert _write_mechanics_calls(ast.parse(prose)) == []
    assert _write_mechanics_calls(ast.parse("x = path.read_bytes()\ny = f.read_text()\n")) == []


def test_store_never_references_the_copier_answers_file():
    """FR-105/AD-52: state is the single source of truth for the answers;
    Genesis never reads, parses, or hand-edits the file Copier writes."""
    assert ".copier-answers" not in _store_source()


# --- AC: the gitignore template stays untouched (FR-107) --------------------


def test_state_file_is_not_git_ignored_by_the_packaged_template():
    template = Path(store.__file__).resolve().parents[1] / "templates" / "files" / "model-ignores.gitignore.j2"
    assert template.is_file()
    rules = [
        line.strip()
        for line in template.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    # The template ships correct and this story does not touch it: the plan
    # artifact is ignored, state is not (FR-107 -- a clone learns what the
    # tool owns here from the tracked file). "seed-state" appears in the
    # template only inside the COMMENT that explains this; a rule naming it
    # would be the regression.
    assert ".marshal/plan.json" in rules
    assert not [rule for rule in rules if "seed-state" in rule]
    assert not [rule for rule in rules if rule.rstrip("/") == ".marshal"]


# --- Story 8.5: the opt-out API ---------------------------------------------
#
# `_sample_state()` already ships an `agents-md` hybrid claim whose recorded
# span is named "tiers", plus `opted_out=("agents-md#tiers",)` -- so the
# fixture below deliberately clears `opted_out` whenever a test needs to
# RECORD something that is not already recorded.


def _clean_state(**overrides: Any) -> SeedState:
    """``_sample_state()`` with nothing opted out yet -- the state a repo is
    in before a maintainer deletes any markers. ``setdefault``, so a caller
    may still supply its own ``opted_out``."""
    overrides.setdefault("opted_out", ())
    return _sample_state(**overrides)


# --- opt_out_key: the wire spelling and its one validation ------------------


def test_opt_out_key_renders_the_artifact_and_region_halves_around_a_hash():
    assert opt_out_key("agents-md", "tiers") == "agents-md#tiers"


@pytest.mark.parametrize(
    "artifact_id",
    ["bmad.method", "AGENTS.md", "a_b", "10.2"],
)
def test_opt_out_key_is_as_permissive_as_a_managed_id_on_the_artifact_half(artifact_id):
    """``managed[].id`` is a ``nonBlankString`` (``model/manifest.py``
    imposes no kebab rule on entry ids), so a legally-named entry must never
    have an UNREPRESENTABLE opt-out -- the one thing this key must not do."""
    assert opt_out_key(artifact_id, "tiers") == f"{artifact_id}#tiers"


@pytest.mark.parametrize(
    ("artifact_id", "region"),
    [
        pytest.param("a b", "tiers", id="artifact-half-carries-whitespace"),
        pytest.param("a\tb", "tiers", id="artifact-half-carries-a-tab"),
        pytest.param("a#b", "tiers", id="artifact-half-carries-the-separator"),
        pytest.param("", "tiers", id="artifact-half-empty"),
        pytest.param("agents-md", "Tiers", id="region-half-not-lowercase"),
        pytest.param("agents-md", "-tiers", id="region-half-starts-with-a-hyphen"),
        pytest.param("agents-md", "two words", id="region-half-carries-whitespace"),
        pytest.param("agents-md", "", id="region-half-empty"),
        pytest.param("agents-md", "tiers\n", id="region-half-carries-a-trailing-newline"),
    ],
)
def test_opt_out_key_raises_value_error_naming_the_offending_pair(artifact_id, region):
    with pytest.raises(ValueError, match="opt_out_key") as excinfo:
        opt_out_key(artifact_id, region)
    message = str(excinfo.value)
    assert repr(artifact_id) in message
    assert repr(region) in message


def test_opt_out_key_validates_against_the_packaged_schemas_own_pattern():
    """Not a second hand-copied regex: the message quotes the pattern the
    schema itself carries, so the runtime check and the wire contract cannot
    drift into two different grammars for one key."""
    pattern = store._load_schema()["properties"]["opted_out"]["items"]["pattern"]
    with pytest.raises(ValueError, match=re.escape(repr(pattern))):
        opt_out_key("a b", "tiers")


def test_every_key_opt_out_key_accepts_is_a_key_write_state_accepts(tmp_path):
    """The pairing stated end to end: a key minted here always survives
    ``write_state``'s own schema validation and reads back identically."""
    keys = tuple(
        sorted(
            opt_out_key(artifact_id, region)
            for artifact_id, region in (
                ("agents-md", "tiers"),
                ("bmad.method", "model-badge"),
                ("AGENTS.md", "r1"),
            )
        )
    )
    state = _clean_state(opted_out=keys)
    write_state(state, repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert read_state(tmp_path) == state


def test_the_compiled_pattern_is_cached_without_sharing_a_mutable_object():
    """``_load_schema`` hands out a fresh dict per call precisely so no
    caller can poison another's validation; caching the COMPILED pattern
    does not reopen that, because a ``re.Pattern`` is immutable."""
    first = store._opt_out_pattern()
    assert first is store._opt_out_pattern()
    assert first.pattern == store._load_schema()["properties"]["opted_out"]["items"]["pattern"]


# --- opt_out_key_or_none: the same grammar, the opposite answer -------------


def test_opt_out_key_or_none_returns_the_key_for_an_admissible_pair():
    assert opt_out_key_or_none("agents-md", "tiers") == "agents-md#tiers"


def test_opt_out_key_or_none_returns_none_exactly_where_opt_out_key_raises():
    assert opt_out_key_or_none("a b", "tiers") is None
    with pytest.raises(ValueError, match="opt_out_key"):
        opt_out_key("a b", "tiers")


def test_opt_out_key_or_none_is_public_so_plan_build_need_not_re_spell_it():
    """``plan/build.py`` asks the "asking, not minting" question once per
    declared region and had grown its own ``try``/``except ValueError``
    around ``opt_out_key`` to answer it -- one rule in two places, in a
    story whose docstrings argue at length against exactly that."""
    assert "opt_out_key_or_none" in state_package.__all__
    assert state_package.opt_out_key_or_none is store.opt_out_key_or_none


# --- is_opt_out_key: the same grammar, asked of an already-rendered key ----


@pytest.mark.parametrize(
    "key",
    [
        pytest.param("agents-md#tiers", id="the-canonical-form"),
        pytest.param("AGENTS.md#tiers", id="artifact-half-is-free-form"),
    ],
)
def test_is_opt_out_key_admits_exactly_what_opt_out_key_mints(key):
    assert is_opt_out_key(key) is True


@pytest.mark.parametrize(
    "key",
    [
        pytest.param("CLAUDE.md#Tiers", id="region-half-is-not-marker-safe"),
        pytest.param("agents md#tiers", id="artifact-half-carries-whitespace"),
        pytest.param("agents-md", id="no-separator-at-all"),
        pytest.param("", id="empty"),
        pytest.param(("agents-md", "tiers"), id="a-pair-rather-than-a-key"),
        pytest.param(None, id="none"),
        pytest.param(b"agents-md#tiers", id="bytes"),
    ],
)
def test_is_opt_out_key_refuses_everything_else_without_raising(key):
    """Review finding, confirmed by execution. ``plan/build.py`` takes a set
    of ALREADY-rendered keys and had no way to check one: its guard tested
    the element TYPE, so a malformed key string sailed through, matched
    nothing, and silently suppressed nothing -- the very failure that guard
    exists to turn loud.

    Takes ``object`` and answers rather than raising, for the reason
    ``opt_out_key_or_none`` does: its whole job is policing input a type
    hint did not."""
    assert is_opt_out_key(key) is False


def test_is_opt_out_key_and_opt_out_key_or_none_are_the_one_grammar():
    """Neither re-spells the pattern; both ask ``_opt_out_pattern``. Asserted
    as an agreement between the two entry points rather than against a
    transcribed literal, so a schema move keeps them equal by construction."""
    for artifact_id, region in (("agents-md", "tiers"), ("a b", "tiers"), ("x", "Tiers")):
        rendered = opt_out_key_or_none(artifact_id, region)
        assert is_opt_out_key(f"{artifact_id}#{region}") is (rendered is not None)


@pytest.mark.parametrize(
    ("artifact_id", "region"),
    [
        pytest.param(None, "tiers", id="artifact-half-is-none"),
        pytest.param(7, "tiers", id="artifact-half-is-an-int"),
        pytest.param(b"agents-md", "tiers", id="artifact-half-is-bytes"),
        pytest.param("agents-md", None, id="region-half-is-none"),
        pytest.param("agents-md", b"tiers", id="region-half-is-bytes"),
    ],
)
def test_a_non_str_half_is_refused_before_it_is_interpolated(artifact_id, region):
    """A type hint is not runtime enforcement, and an f-string renders ANY
    object -- so both halves are ``isinstance``-checked AHEAD of the
    interpolation, where the evidence still exists. All three entry points
    agree: ``or_none`` answers ``None``, ``opt_out_key`` raises, and
    ``is_opted_out`` keeps its "answer, don't raise" contract."""
    assert opt_out_key_or_none(artifact_id, region) is None
    with pytest.raises(ValueError, match="opt_out_key"):
        opt_out_key(artifact_id, region)
    assert is_opted_out(_sample_state(), artifact_id, region) is False


def test_the_key_a_none_half_used_to_render_is_one_the_schema_accepts():
    """Why the guard cannot be delegated to the pattern. ``"None#tiers"``
    MATCHES the schema's ``opted_out`` grammar, so ``opt_out_key(None,
    "tiers")`` minted a perfectly writable key naming an artifact id no
    manifest can ever carry -- a permanent opt-out that no re-insertion and
    no ``--reinstate`` could clear, because nothing would ever name it
    again."""
    assert store._opt_out_pattern().match("None#tiers") is not None


# --- is_opted_out: a read, never a raise ------------------------------------


def test_is_opted_out_is_true_for_a_recorded_pair():
    assert is_opted_out(_sample_state(), "agents-md", "tiers") is True


def test_is_opted_out_is_false_for_an_unrecorded_pair():
    assert is_opted_out(_sample_state(), "agents-md", "model-badge") is False


def test_is_opted_out_is_false_for_a_never_adopted_repo():
    """``read_state`` returns ``None`` for a repo that was never adopted,
    which has recorded no opt-out for anything -- a true answer, not a
    caller error every consumer would have to guard around."""
    assert is_opted_out(None, "agents-md", "tiers") is False


def test_is_opted_out_is_false_rather_than_raising_for_an_unspellable_pair():
    """A key the schema's grammar rejects can never appear in a
    schema-valid ``opted_out`` at all, so "is it recorded?" is answerable
    without minting it -- unlike ``record``/``clear``, which must raise."""
    assert is_opted_out(_sample_state(), "a b", "tiers") is False


# --- record_opt_out: sorted, deduped, and the managed[] claim drop ----------


def test_record_opt_out_adds_the_key():
    state = record_opt_out(_clean_state(), "dream-template", "tiers")
    assert state.opted_out == ("dream-template#tiers",)


def test_record_opt_out_keeps_opted_out_sorted():
    state = _clean_state()
    for region in ("zulu", "alpha", "mike"):
        state = record_opt_out(state, "dream-template", region)
    assert state.opted_out == (
        "dream-template#alpha",
        "dream-template#mike",
        "dream-template#zulu",
    )


def test_two_recording_orders_write_byte_identical_state(tmp_path):
    """The reason ``opted_out`` is sorted rather than appended: two runs
    recording the same pairs in different orders must produce the same
    file, byte for byte, or every state diff carries meaningless churn."""
    forward = _clean_state()
    for region in ("alpha", "mike", "zulu"):
        forward = record_opt_out(forward, "dream-template", region)
    backward = _clean_state()
    for region in ("zulu", "mike", "alpha"):
        backward = record_opt_out(backward, "dream-template", region)

    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()
    write_state(forward, repo_root=one, never_write=_NO_PATTERNS)
    write_state(backward, repo_root=two, never_write=_NO_PATTERNS)

    assert state_path(one).read_bytes() == state_path(two).read_bytes()


def test_record_opt_out_is_idempotent():
    once = record_opt_out(_clean_state(), "dream-template", "tiers")
    assert record_opt_out(once, "dream-template", "tiers") == once


def test_record_opt_out_does_not_mutate_the_state_it_was_given():
    """Pure, via ``dataclasses.replace`` -- never an in-place edit of a
    frozen value object a caller may still be holding."""
    original = _clean_state()
    snapshot = dataclasses.replace(original)
    record_opt_out(original, "dream-template", "tiers")
    assert original == snapshot
    assert original.opted_out == ()


def test_record_opt_out_drops_the_managed_claim_for_that_region():
    """The AC's real mechanism: with the claim retained, "installed once,
    markers now gone" re-derives the opt-out on every later run, so
    ``clear_opt_out`` -- and ``--reinstate`` -- could never take effect."""
    before = _clean_state()
    assert [artifact.id for artifact in before.managed] == ["agents-md", "dream-template"]

    after = record_opt_out(before, "agents-md", "tiers")

    assert [artifact.id for artifact in after.managed] == ["dream-template"]
    assert after.opted_out == ("agents-md#tiers",)


def test_record_opt_out_leaves_a_whole_file_claim_on_a_different_id_untouched():
    after = record_opt_out(_clean_state(), "agents-md", "tiers")
    (survivor,) = after.managed
    assert survivor.id == "dream-template"
    assert survivor.inserted_region_span is None


def test_state_records_at_most_one_region_span_per_artifact():
    """What replaced a VACUOUS test. This slot used to assert that
    ``record_opt_out`` leaves a claim on a DIFFERENT region of the same id
    untouched -- a state ``SeedState`` cannot be built in, so the assertion
    passed by construction and proved nothing about the filter it named.

    The real, now-documented constraint is this one: ``__post_init__``
    rejects duplicate ``managed[].id``, so one artifact carries at most one
    ``ManagedArtifact`` and therefore at most ONE ``inserted_region_span``.
    State can record a single installed region per hybrid artifact however
    many its manifest entry declares -- a pre-existing property of the
    schema S-10.2 shipped, and the reason ``record_opt_out``'s docstring
    calls the span half of its filter defence in depth rather than a
    selective match."""
    region_claim = _sample_state().managed[0]
    assert region_claim.inserted_region_span is not None
    sibling = dataclasses.replace(
        region_claim,
        path="AGENTS-2.md",
        inserted_region_span=RegionSpanRecord(name="model-badge", start=30, end=40),
    )
    with pytest.raises(ValueError, match=r"SeedState\.managed\[\]\.id: must be unique"):
        _clean_state(managed=(region_claim, sibling))


def test_record_opt_out_leaves_a_region_claim_on_a_different_artifact_untouched():
    """The isolation the filter's id half CAN exercise: two artifacts may
    each carry a claim on a region of the same NAME, and opting one of them
    out says nothing about the other."""
    mine = _sample_state().managed[0]
    theirs = dataclasses.replace(mine, id="claude-md", path="CLAUDE.md")
    before = _clean_state(managed=(mine, theirs))

    after = record_opt_out(before, "agents-md", "tiers")

    assert after.managed == (theirs,)
    assert after.opted_out == ("agents-md#tiers",)


def test_record_opt_out_leaves_a_whole_file_claim_on_the_same_id_untouched():
    """A ``managed[]`` entry with no recorded span is a whole-file claim,
    never a region one -- dropping it on a region opt-out would silently
    withdraw Genesis's claim on a whole artifact."""
    whole_file_claim = ManagedArtifact(
        id="agents-md",
        path="AGENTS.md",
        artifact_class="copied-managed",
        body_sha="0123abcd",
        inserted_region_span=None,
    )
    before = _clean_state(managed=(whole_file_claim,))
    after = record_opt_out(before, "agents-md", "tiers")
    assert after.managed == (whole_file_claim,)


def test_record_opt_out_raises_for_a_malformed_pair():
    with pytest.raises(ValueError, match="opt_out_key"):
        record_opt_out(_clean_state(), "a b", "tiers")


# --- both mutators refuse a None state, by name -----------------------------


@pytest.mark.parametrize("mutator", [record_opt_out, clear_opt_out])
def test_a_mutator_handed_a_none_state_raises_a_value_error_naming_itself(mutator):
    """``read_state`` returns ``SeedState | None``, so handing the ``None``
    straight through is a realistic mistake rather than a hypothetical one
    -- and an unguarded ``dataclasses.replace(None, ...)`` reaches the
    operator as ``AttributeError: 'NoneType' object has no attribute
    'managed'``, which names neither the function they called nor what was
    wrong with the call. ``is_opted_out`` is deliberately tolerant of the
    same ``None`` (tested above): it has a true answer to give, and a
    mutator has no state to derive a new one FROM."""
    with pytest.raises(ValueError, match=mutator.__name__) as excinfo:
        mutator(None, "agents-md", "tiers")
    message = str(excinfo.value)
    assert "None" in message
    assert "read_state" in message


# --- clear_opt_out: the reinstate mechanism S-10.6 calls --------------------


def test_clear_opt_out_removes_the_pair():
    recorded = record_opt_out(_clean_state(), "dream-template", "tiers")
    assert clear_opt_out(recorded, "dream-template", "tiers").opted_out == ()


def test_clear_opt_out_is_idempotent_on_a_pair_that_was_never_recorded():
    state = _clean_state()
    assert clear_opt_out(state, "dream-template", "tiers") == state


def test_clear_opt_out_leaves_every_other_recorded_pair_alone():
    state = _clean_state()
    for region in ("alpha", "mike", "zulu"):
        state = record_opt_out(state, "dream-template", region)
    cleared = clear_opt_out(state, "dream-template", "mike")
    assert cleared.opted_out == ("dream-template#alpha", "dream-template#zulu")


def test_clear_opt_out_dedupes_what_it_keeps_exactly_as_record_opt_out_does():
    """Review finding, confirmed by execution. ``SeedState.__post_init__``
    runs ``_reject_duplicates`` on ``managed[].id`` but NOT on
    ``opted_out``, so a hand-built state can carry a repeated key. The two
    mutators disagreed about it -- ``record_opt_out`` normalized through a
    ``set``, ``clear_opt_out`` filtered a tuple -- so clearing an UNRELATED
    pair returned a state whose surviving duplicates then failed
    ``write_state``'s schema ``uniqueItems`` check: a reinstate that could
    not be persisted, reported against a key the caller never touched."""
    state = _sample_state(opted_out=["a#b", "a#b", "c#d"])

    cleared = clear_opt_out(state, "c", "d")

    assert cleared.opted_out == ("a#b",)
    # The same normalization `record_opt_out` performs on the same input.
    assert record_opt_out(state, "e", "f").opted_out == ("a#b", "c#d", "e#f")


def test_clear_opt_out_does_not_reconstruct_the_dropped_managed_claim():
    """A claim records what the tool actually INSTALLED (a real body_sha, a
    real span); a reinstate has none of those facts yet. The next apply
    re-establishes the claim from the write it performs."""
    recorded = record_opt_out(_clean_state(), "agents-md", "tiers")
    cleared = clear_opt_out(recorded, "agents-md", "tiers")
    assert [artifact.id for artifact in cleared.managed] == ["dream-template"]


def test_clear_opt_out_drops_the_region_claim_too():
    """The load-bearing half of ``--reinstate``, against a DERIVED opt-out:
    ``detect/optout.py``'s rung 3 answers ``OPTED_OUT`` from a surviving
    ``managed[]`` claim whose region is no longer in the file, with NOTHING
    recorded in ``opted_out``. There is therefore no key to remove -- so a
    ``clear_opt_out`` that touched only ``opted_out`` would be a no-op, rung
    3 would fire again on the very next run, and the region could never be
    reinstated. Dropping the claim is what makes the withdrawal real."""
    derived = _clean_state()
    assert derived.opted_out == ()
    assert [artifact.id for artifact in derived.managed] == ["agents-md", "dream-template"]

    cleared = clear_opt_out(derived, "agents-md", "tiers")

    assert [artifact.id for artifact in cleared.managed] == ["dream-template"]
    assert cleared.opted_out == ()


def test_the_claim_drop_is_a_no_op_in_the_record_then_clear_sequence():
    """In the ordinary sequence ``record_opt_out`` has already dropped the
    claim, so ``clear_opt_out``'s own drop changes nothing -- it exists for
    the derived case above, where no ``record_opt_out`` ever ran."""
    recorded = record_opt_out(_clean_state(), "agents-md", "tiers")
    assert clear_opt_out(recorded, "agents-md", "tiers").managed == recorded.managed


def test_clear_opt_out_drops_a_live_claim_too_which_is_the_callers_to_prevent():
    """The precondition, pinned rather than left implicit. The claim drop is
    UNCONDITIONAL, and state alone cannot tell "markers deleted, claim
    survives" (must lose the claim) from "markers present, claim survives"
    (must keep it) -- they differ only in the FILE, which this pure function
    never sees, and the frozen ``(state, artifact_id, region)`` signature
    cannot be given. Called on the second, it discards a live claim and with
    it the recorded ``body_sha``, after which
    ``detect/hashes.py::check_managed_region`` reads the region as adopted
    out-of-band forever and ``build_plan`` plans no insertion to rebuild it
    (the region IS present). So the caller must clear only a pair
    ``detect/optout.py`` classifies ``OPTED_OUT``; ``DW-FU-8-5-4`` carries
    that guard to S-10.6, where the verb exists to hold it."""
    live = _clean_state()
    (claim,) = [artifact for artifact in live.managed if artifact.id == "agents-md"]
    assert claim.inserted_region_span is not None
    assert claim.body_sha

    cleared = clear_opt_out(live, "agents-md", "tiers")

    assert [artifact.id for artifact in cleared.managed] == ["dream-template"]


def test_clear_opt_out_leaves_a_whole_file_claim_on_the_same_id_untouched():
    """The same two-condition filter ``record_opt_out`` uses, asserted on
    the mutator that gained it: an entry with no recorded span claims the
    whole FILE, and reinstating a region must never withdraw that."""
    whole_file_claim = ManagedArtifact(
        id="agents-md",
        path="AGENTS.md",
        artifact_class="copied-managed",
        body_sha="0123abcd",
        inserted_region_span=None,
    )
    before = _clean_state(managed=(whole_file_claim,))
    assert clear_opt_out(before, "agents-md", "tiers").managed == (whole_file_claim,)


def test_clear_opt_out_leaves_a_region_claim_on_a_different_artifact_untouched():
    mine = _sample_state().managed[0]
    theirs = dataclasses.replace(mine, id="claude-md", path="CLAUDE.md")

    cleared = clear_opt_out(_clean_state(managed=(mine, theirs)), "agents-md", "tiers")

    assert cleared.managed == (theirs,)


def test_record_then_clear_returns_the_original_minus_the_dropped_claim():
    """The reinstate round trip, stated as an equality against a state built
    without the claim at all."""
    before = _clean_state()
    expected = dataclasses.replace(before, managed=tuple(a for a in before.managed if a.id != "agents-md"))
    round_tripped = clear_opt_out(record_opt_out(before, "agents-md", "tiers"), "agents-md", "tiers")
    assert round_tripped == expected


def test_clear_opt_out_does_not_mutate_the_state_it_was_given():
    original = _sample_state()
    snapshot = dataclasses.replace(original)
    clear_opt_out(original, "agents-md", "tiers")
    assert original == snapshot
    assert original.opted_out == ("agents-md#tiers",)


def test_clear_opt_out_raises_for_a_malformed_pair():
    with pytest.raises(ValueError, match="opt_out_key"):
        clear_opt_out(_sample_state(), "agents-md", "Tiers")


# --- AC: a recording still round-trips through the eleven-key schema --------


def test_state_written_after_record_opt_out_round_trips_with_eleven_keys(tmp_path):
    state = record_opt_out(_clean_state(), "agents-md", "tiers")
    write_state(state, repo_root=tmp_path, never_write=_NO_PATTERNS)

    assert read_state(tmp_path) == state
    document = yaml.safe_load(state_path(tmp_path).read_text(encoding="utf-8"))
    assert tuple(document) == STATE_KEYS
    assert len(document) == 11
    assert document["opted_out"] == ["agents-md#tiers"]


def test_no_opt_out_helper_added_a_twelfth_state_key():
    """The story's own Never bullet, asserted rather than trusted: five pure
    functions over an ALREADY-shipped key, no schema edit, no migration."""
    state = record_opt_out(_clean_state(), "agents-md", "tiers")
    assert tuple(state.to_json_dict()) == STATE_KEYS
    assert tuple(clear_opt_out(state, "agents-md", "tiers").to_json_dict()) == STATE_KEYS


def test_neither_mutator_refreshes_last_update():
    """Stamping the write time belongs to the verb that PERSISTS the state
    -- ``write_state`` does not stamp it either -- so a verb must refresh it
    alongside the mutation. These two are this module's first mutators and
    therefore set that convention; asserted so a later "helpful" stamp here
    is a visible decision rather than a silent one."""
    before = _clean_state()
    recorded = record_opt_out(before, "agents-md", "tiers")
    assert recorded.last_update == before.last_update
    assert clear_opt_out(recorded, "agents-md", "tiers").last_update == before.last_update


def test_the_six_opt_out_helpers_are_re_exported_from_the_state_package():
    for name in (
        "opt_out_key",
        "opt_out_key_or_none",
        "is_opt_out_key",
        "is_opted_out",
        "record_opt_out",
        "clear_opt_out",
    ):
        assert name in state_package.__all__
        assert getattr(state_package, name) is getattr(store, name)
    assert len(set(state_package.__all__)) == len(state_package.__all__)
    # ``__all__``'s established convention here is type names first, then
    # the function names in sorted order -- the group the six join (the
    # four the ``<intent-contract>`` names, plus ``opt_out_key_or_none``
    # and ``is_opt_out_key``, both promoted to public by this story's own
    # review passes for the same consumer and the same reason: a caller
    # that cannot reach the grammar re-implements it).
    functions = [name for name in state_package.__all__ if name[0].islower()]
    assert functions == sorted(functions)
