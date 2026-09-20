"""Story 53.3 — one tracked track.json per run (hub:CAP-3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.steward.cli import DUTIES, build_parser, main, resolve_duty
from pyforge.steward.track import (
    RETENTION,
    TRACK_FIELDS,
    TrackDuty,
    assemble,
    build_track,
)

_PKG = Path(__file__).resolve().parents[1]
_FIXTURE = _PKG / "fixtures" / "track-run"
_SPARSE = _PKG / "fixtures" / "track-run-sparse"
_SCHEMA = (
    _PKG.parent  # tests/ -> the pyforge-steward package dir (parents[1] pointed at src/shared/packages/)
    / "src"
    / "pyforge"
    / "steward"
    / "data"
    / "track.schema.json"
)


def _repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "pixi.toml").is_file() and (ancestor / "docs").is_dir() and (ancestor / "_bmad-output").is_dir():
            return ancestor
    raise AssertionError("could not locate repo root")


_EXAMPLE = _repo_root() / "docs" / "foundry" / "tracks" / "example-track.json"


def test_frozen_field_list_matches_documented_keys():
    assert TRACK_FIELDS == (
        "run_id",
        "timestamps",
        "tree_revision",
        "guards",
        "gates",
        "model_adapter",
        "human_approvals_overrides",
        "retention",
    )
    assert RETENTION == {"track": "indefinite", "raw_payload_days": 90}


def test_assemble_fixture_has_required_fields_and_stated_retention(tmp_path):
    out = tmp_path / "track.json"
    track = assemble(_FIXTURE, out)
    assert list(track) == list(TRACK_FIELDS)
    assert track["run_id"] == "run-fixture-53-3"
    assert track["timestamps"]["started_at"] == "2026-09-13T16:00:00.000Z"
    assert track["timestamps"]["ended_at"] == "2026-09-13T16:02:00.000Z"
    assert track["tree_revision"] == "50504e52e9161bdb87811420eafde31d72f46a67"
    assert track["retention"] == RETENTION
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written == track


def test_guards_and_gates_are_on_the_record_not_inferred():
    track = build_track(_FIXTURE)
    assert track["guards"] == [
        {
            "stage": "verify",
            "name": "pytest tests/unit/test_track.py",
            "result": {"returncode": 0, "resolvable": True},
        }
    ]
    names = {gate["name"] for gate in track["gates"]}
    assert "confidence" in names
    assert "scope_check" in names
    confidence = next(g for g in track["gates"] if g["name"] == "confidence")
    assert confidence["rule"] == "confidence below 0.80 → human review"
    assert confidence["verdict"] == "pass"
    scope = next(g for g in track["gates"] if g["name"] == "scope_check")
    assert scope["verdict"] == "clean"
    assert scope["rule"] is None


def test_missing_optional_fields_stay_null_not_invented():
    track = build_track(_SPARSE)
    assert track["run_id"] == "run-sparse-53-3"
    assert track["tree_revision"] is None
    assert track["model_adapter"] is None
    assert track["human_approvals_overrides"] == []
    assert track["guards"] == []
    assert track["gates"] == []
    assert track["retention"] == RETENTION
    assert track["timestamps"]["started_at"] == "2026-09-13T17:00:00.000Z"
    assert track["timestamps"]["ended_at"] == "2026-09-13T17:00:00.000Z"


def test_tracked_example_is_assemble_of_the_unit_fixture():
    expected = build_track(_FIXTURE)
    assert _EXAMPLE.is_file(), "docs/foundry/tracks/example-track.json must be tracked"
    example = json.loads(_EXAMPLE.read_text(encoding="utf-8"))
    assert example == expected


def test_schema_accepts_assembled_track():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(build_track(_FIXTURE), schema)
    jsonschema.validate(build_track(_SPARSE), schema)


def test_track_is_a_registered_duty():
    assert "track" in DUTIES
    assert "track" in DUTIES
    impl = resolve_duty("track")
    assert isinstance(impl, TrackDuty)
    assert impl.name == "track"


def test_bare_track_lists_assemble():
    result = TrackDuty().run(build_parser().parse_args(["track"]))
    assert result.ok is True
    assert "assemble" in result.summary


def test_assemble_via_cli(tmp_path, capsys):
    out = tmp_path / "track.json"
    rc = main(["track", "assemble", "--run-dir", str(_FIXTURE), "--out", str(out)])
    assert rc == 0
    assert out.is_file()
    assert "run-fixture-53-3" in capsys.readouterr().out


def test_assemble_missing_run_dir_is_duty_failure(tmp_path):
    rc = main(
        [
            "track",
            "assemble",
            "--run-dir",
            str(tmp_path / "missing"),
            "--out",
            str(tmp_path / "track.json"),
        ]
    )
    assert rc == 1
