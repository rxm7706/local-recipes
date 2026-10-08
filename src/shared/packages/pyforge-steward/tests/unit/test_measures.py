"""Story 62.2 — Build League measure catalog config."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.steward.measures import (
    FIRST_CUT_IDS,
    MeasureConfig,
    MeasureConfigError,
    MeasureDecl,
    MeasureDuty,
    format_list,
    load_config,
    refuse_reuse,
    validate_add_rules,
)

_HEADER = """\
catalog:
  name: test-measures
  companion: companion.md
archived_ids: []
"""


def _write_measures(tmp_path: Path, body: str, *, header: str = _HEADER) -> Path:
    measures_dir = tmp_path / "measures"
    measures_dir.mkdir()
    path = measures_dir / "measures.yaml"
    path.write_text(header + body, encoding="utf-8")
    return path


def test_load_committed_first_cut() -> None:
    from pyforge.steward.measures import default_measures_dir, repo_root

    config = load_config(default_measures_dir(repo_root()) / "measures.yaml")
    assert {m.measure_id for m in config.measures} == FIRST_CUT_IDS
    assert all(m.state == "on" for m in config.measures)


def test_new_measure_must_start_off(tmp_path: Path) -> None:
    body = """\
measures:
  warden-verdict:
    dimension: human
    source: x
    state: on
  new-signal:
    dimension: agent
    source: y
    state: on
"""
    config = load_config(_write_measures(tmp_path, body))
    findings = validate_add_rules(config)
    assert any("new-signal" in f and "off" in f for f in findings)


def test_archived_id_in_tombstone_refuses_reuse(tmp_path: Path) -> None:
    header = """\
catalog:
  name: test-measures
archived_ids:
  - retired-one
measures:
"""
    body = """\
  warden-verdict:
    dimension: human
    source: x
    state: on
"""
    config = load_config(_write_measures(tmp_path, body, header=header))
    assert refuse_reuse("retired-one", config) is not None


def test_archived_state_on_row_refuses_reuse(tmp_path: Path) -> None:
    body = """\
measures:
  retired-one:
    dimension: human
    source: x
    state: archived
"""
    config = load_config(_write_measures(tmp_path, body))
    assert refuse_reuse("retired-one", config) is not None


def test_invalid_state_rejected(tmp_path: Path) -> None:
    body = """\
measures:
  warden-verdict:
    dimension: human
    source: x
    state: maybe
"""
    with pytest.raises(MeasureConfigError, match="state"):
        load_config(_write_measures(tmp_path, body))


def test_archived_ids_overlap_measures_rejected(tmp_path: Path) -> None:
    header = """\
catalog:
  name: test-measures
archived_ids:
  - warden-verdict
measures:
"""
    body = """\
  warden-verdict:
    dimension: human
    source: x
    state: on
"""
    with pytest.raises(MeasureConfigError, match="both 'measures' and 'archived_ids'"):
        load_config(_write_measures(tmp_path, body, header=header))


def test_cli_measure_check_on_committed_config() -> None:
    from pyforge.steward.cli import main

    assert main(["measure", "check"]) == 0


def test_cli_measure_list_json(capsys) -> None:
    from pyforge.steward.cli import main

    assert main(["measure", "list", "--json"]) == 0
    out = capsys.readouterr().out
    assert "warden-verdict" in out
    assert "build-league-measures" in out


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MeasureConfigError, match="not found"):
        load_config(tmp_path / "missing.yaml")


def test_load_config_malformed_yaml(tmp_path: Path) -> None:
    path = tmp_path / "measures.yaml"
    path.write_text("catalog: [\n", encoding="utf-8")
    with pytest.raises(MeasureConfigError, match="malformed YAML"):
        load_config(path)


def test_load_config_unreadable(tmp_path: Path) -> None:
    path = tmp_path / "measures.yaml"
    path.write_text("catalog: {}\n", encoding="utf-8")
    path.chmod(0o000)
    try:
        with pytest.raises(MeasureConfigError, match="unreadable"):
            load_config(path)
    finally:
        path.chmod(0o644)


def test_load_config_top_level_not_mapping(tmp_path: Path) -> None:
    path = tmp_path / "measures.yaml"
    path.write_text("- not-a-mapping\n", encoding="utf-8")
    with pytest.raises(MeasureConfigError, match="must be a mapping"):
        load_config(path)


def test_load_config_unknown_top_level_key(tmp_path: Path) -> None:
    body = """\
extra: true
measures:
  warden-verdict:
    dimension: human
    source: x
    state: on
"""
    with pytest.raises(MeasureConfigError, match="unknown top-level"):
        load_config(_write_measures(tmp_path, body))


def test_load_config_catalog_missing(tmp_path: Path) -> None:
    path = tmp_path / "measures.yaml"
    path.write_text("measures: {}\n", encoding="utf-8")
    with pytest.raises(MeasureConfigError, match="'catalog'"):
        load_config(path)


def test_load_config_catalog_name_required(tmp_path: Path) -> None:
    path = tmp_path / "measures.yaml"
    path.write_text("catalog: {}\nmeasures: {}\n", encoding="utf-8")
    with pytest.raises(MeasureConfigError, match="catalog.name"):
        load_config(path)


def test_load_config_archived_ids_not_list(tmp_path: Path) -> None:
    header = """\
catalog:
  name: test-measures
archived_ids: retired-one
measures: {}
"""
    path = tmp_path / "measures.yaml"
    path.write_text(header, encoding="utf-8")
    with pytest.raises(MeasureConfigError, match="archived_ids"):
        load_config(path)


def test_load_config_archived_ids_entry_invalid(tmp_path: Path) -> None:
    header = """\
catalog:
  name: test-measures
archived_ids:
  - ""
measures: {}
"""
    path = tmp_path / "measures.yaml"
    path.write_text(header, encoding="utf-8")
    with pytest.raises(MeasureConfigError, match="archived_ids\\[0\\]"):
        load_config(path)


def test_load_config_measures_defaults_when_absent(tmp_path: Path) -> None:
    header = """\
catalog:
  name: test-measures
"""
    path = tmp_path / "measures.yaml"
    path.write_text(header, encoding="utf-8")
    config = load_config(path)
    assert config.measures == ()


def test_load_config_measures_not_mapping(tmp_path: Path) -> None:
    header = """\
catalog:
  name: test-measures
measures: []
"""
    path = tmp_path / "measures.yaml"
    path.write_text(header, encoding="utf-8")
    with pytest.raises(MeasureConfigError, match="'measures' section"):
        load_config(path)


def test_load_config_measure_body_not_mapping(tmp_path: Path) -> None:
    body = """\
measures:
  warden-verdict: not-a-mapping
"""
    with pytest.raises(MeasureConfigError, match="must be a mapping"):
        load_config(_write_measures(tmp_path, body))


def test_load_config_bad_dimension(tmp_path: Path) -> None:
    body = """\
measures:
  warden-verdict:
    dimension: machine
    source: x
    state: on
"""
    with pytest.raises(MeasureConfigError, match="dimension"):
        load_config(_write_measures(tmp_path, body))


def test_load_config_missing_source(tmp_path: Path) -> None:
    body = """\
measures:
  warden-verdict:
    dimension: human
    state: on
"""
    with pytest.raises(MeasureConfigError, match="source"):
        load_config(_write_measures(tmp_path, body))


def test_validate_add_rules_archived_id_also_in_measures() -> None:
    decl = MeasureDecl("warden-verdict", "human", "x", "on")
    config = MeasureConfig("n", "", ("warden-verdict",), (decl,))
    findings = validate_add_rules(config)
    assert any("archived_ids and measures" in f for f in findings)


def test_refuse_reuse_existing_and_allowed() -> None:
    decl = MeasureDecl("warden-verdict", "human", "x", "on")
    config = MeasureConfig("n", "", (), (decl,))
    assert refuse_reuse("warden-verdict", config) is not None
    assert refuse_reuse("fresh-id", config) is None


def test_format_list_includes_notes_and_archived_ids() -> None:
    decl = MeasureDecl("z-last", "team", "src", "off", notes="note text")
    config = MeasureConfig("demo", "comp.md", ("gone",), (decl,))
    text = format_list(config)
    assert "note text" in text
    assert "archived_ids (reserved): gone" in text


def test_measure_duty_config_load_error(tmp_path: Path) -> None:
    measures_dir = tmp_path / "measures"
    measures_dir.mkdir()
    duty = MeasureDuty()
    ns = type("NS", (), {"measure_verb": "check", "json": False, "measures_dir": str(measures_dir)})()
    result = duty.run(ns)
    assert not result.ok
    assert "config-load" in str(result.details)
