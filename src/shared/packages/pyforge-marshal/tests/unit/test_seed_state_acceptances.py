"""The optional ``acceptances`` journal in ``.marshal/seed-state.yml`` (Story 97.1, AC2).

``marshal seed accept`` appends one ``Acceptance`` per re-recorded file or
region. The schema declares the key (so a journaled state validates) but does
NOT require it (so every state written before this story still reads), and the
``model_version`` is never bumped: an older tool reading a state that carries
the key is the cost of an additive change, not a migration.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest
import yaml

from pyforge.marshal.seed import fs
from pyforge.marshal.seed.errors import StateInvalid
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.state import (
    Acceptance,
    ManagedArtifact,
    SeedState,
    read_state,
    state_path,
    write_state,
)
from pyforge.marshal.seed.state.store import STATE_KEYS

_NO_PATTERNS = fs.NeverWrite(())

_SHA_A = "0123abcd"
_SHA_B = "deadbeef"
_HEAD = "a" * 40


def _acceptance(**overrides: Any) -> Acceptance:
    fields: dict[str, Any] = {
        "id": "bmad-switch",
        "region": None,
        "path": "scripts/bmad-switch",
        "previous_sha": _SHA_A,
        "accepted_sha": _SHA_B,
        "accepted_at": "2026-10-12T09:15:00Z",
        "accepted_by": "Test Er <tester@example.com>",
        "head": _HEAD,
        "reason": "keep the local patch",
    }
    fields.update(overrides)
    return Acceptance(**fields)


def _state(**overrides: Any) -> SeedState:
    fields: dict[str, Any] = {
        "model_version": ModelVersion.parse("1.0.0"),
        "seed_model_version": "0.1.0",
        "adopted_at": "2026-10-01T09:15:00Z",
        "last_update": "2026-10-01T09:15:00Z",
        "mode": "adopt",
        "agents": (),
        "managed": (
            ManagedArtifact(
                id="bmad-switch",
                path="scripts/bmad-switch",
                artifact_class="copied-managed",
                body_sha=_SHA_B,
                inserted_region_spans=(),
            ),
        ),
        "skips": (),
        "legacy": (),
        "migrations_applied": (),
        "opted_out": (),
    }
    fields.update(overrides)
    return SeedState(**fields)


def _write_raw(repo_root: Path, document: dict[str, Any]) -> None:
    path = state_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_a_state_without_the_key_reads_as_an_empty_journal(tmp_path):
    write_state(_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    state = read_state(tmp_path)
    assert state is not None
    assert state.acceptances == ()


def test_an_empty_journal_is_never_written(tmp_path):
    """A repo that never accepted anything keeps the eleven-key document it always had."""
    assert tuple(_state().to_json_dict()) == STATE_KEYS
    write_state(_state(acceptances=()), repo_root=tmp_path, never_write=_NO_PATTERNS)
    document = yaml.safe_load(state_path(tmp_path).read_text(encoding="utf-8"))
    assert tuple(document) == STATE_KEYS
    assert "acceptances" not in document


def test_a_journal_round_trips_in_order(tmp_path):
    journal = (
        _acceptance(),
        _acceptance(id="gitignore", region="model-ignores", path=".gitignore", reason="second"),
    )
    write_state(_state(acceptances=journal), repo_root=tmp_path, never_write=_NO_PATTERNS)

    document = yaml.safe_load(state_path(tmp_path).read_text(encoding="utf-8"))
    assert tuple(document) == (*STATE_KEYS, "acceptances")  # appended last, after the eleven
    assert document["model_version"] == "1.0.0"  # never bumped
    state = read_state(tmp_path)
    assert state is not None
    assert state.acceptances == journal


def test_the_journal_is_a_tuple_even_when_given_a_list():
    state = _state(acceptances=[_acceptance()])
    assert isinstance(state.acceptances, tuple)
    with pytest.raises((AttributeError, TypeError)):
        state.acceptances.append(_acceptance())  # type: ignore[attr-defined]


@pytest.mark.parametrize("sha_field", ["previous_sha", "accepted_sha"])
@pytest.mark.parametrize("bad", ["", "XYZ", "0123ABCD", "0123abc", "0123abcd0"])
def test_a_malformed_hash_in_the_journal_is_state_invalid(tmp_path, sha_field, bad):
    document = _state(acceptances=(_acceptance(),)).to_json_dict()
    document["acceptances"][0][sha_field] = bad
    _write_raw(tmp_path, document)
    with pytest.raises(StateInvalid, match=r"acceptances\[0\]"):
        read_state(tmp_path)


@pytest.mark.parametrize("bad", ["", "abc", "A" * 40, "g" * 40, "a" * 39, "a" * 41, "a" * 40 + "\n"])
def test_a_malformed_head_in_the_journal_is_state_invalid(tmp_path, bad):
    document = _state(acceptances=(_acceptance(),)).to_json_dict()
    document["acceptances"][0]["head"] = bad
    _write_raw(tmp_path, document)
    with pytest.raises(StateInvalid, match=r"acceptances\[0\]"):
        read_state(tmp_path)


def test_a_sha256_head_is_a_valid_object_id(tmp_path):
    write_state(
        _state(acceptances=(_acceptance(head="b" * 64),)),
        repo_root=tmp_path,
        never_write=_NO_PATTERNS,
    )
    state = read_state(tmp_path)
    assert state is not None
    assert state.acceptances[0].head == "b" * 64


def test_a_journal_entry_with_an_extra_key_is_state_invalid(tmp_path):
    document = _state(acceptances=(_acceptance(),)).to_json_dict()
    document["acceptances"][0]["note"] = "not in the schema"
    _write_raw(tmp_path, document)
    with pytest.raises(StateInvalid, match=r"acceptances\[0\]"):
        read_state(tmp_path)


@pytest.mark.parametrize(
    "field",
    ["id", "region", "path", "previous_sha", "accepted_sha", "accepted_at", "accepted_by", "head", "reason"],
)
def test_a_journal_entry_missing_a_field_is_state_invalid(tmp_path, field):
    document = _state(acceptances=(_acceptance(),)).to_json_dict()
    del document["acceptances"][0][field]
    _write_raw(tmp_path, document)
    with pytest.raises(StateInvalid):
        read_state(tmp_path)


def test_a_bad_timestamp_in_the_journal_is_state_invalid(tmp_path):
    document = _state(acceptances=(_acceptance(),)).to_json_dict()
    document["acceptances"][0]["accepted_at"] = "yesterday"
    _write_raw(tmp_path, document)
    with pytest.raises(StateInvalid, match=r"acceptances\[0\]"):
        read_state(tmp_path)


def test_an_invalid_journal_is_refused_before_any_write(tmp_path):
    write_state(_state(), repo_root=tmp_path, never_write=_NO_PATTERNS)
    before = state_path(tmp_path).read_bytes()
    bad = dataclasses.replace(_state(), acceptances=(_acceptance(previous_sha="nope"),))
    with pytest.raises(StateInvalid):
        write_state(bad, repo_root=tmp_path, never_write=_NO_PATTERNS)
    assert state_path(tmp_path).read_bytes() == before
