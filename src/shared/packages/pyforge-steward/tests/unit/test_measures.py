"""Story 62.2 — Build League measure catalog config."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.steward.measures import (
    FIRST_CUT_IDS,
    MeasureConfigError,
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
