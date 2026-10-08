"""Unit coverage for `pyforge.atlas.dashboard.factory_status` (Story 25.1).

The integration `dashboard-dryrun` gate exercises this module too, but that suite
does not count toward the diff-scoped `unit` coverage gate
(`scripts/coverage_gates_ci.py` maps `unit` -> `tests/unit` + `tests/meta` only).
These tests exercise the module directly and offline: real YAML/frontmatter parsing
against files written to `tmp_path`, no network.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from pyforge.atlas.dashboard import factory_status as fs

STAMP = "2026-09-09T00:00:00Z"


def test_default_repo_root_finds_the_real_git_root():
    root = fs.default_repo_root()
    assert (root / ".git").exists() or (root / "_bmad-output").is_dir()


def test_default_paths_shape():
    paths = fs._default_paths()
    assert set(paths) == {"sprint_status_path", "epics_path"}
    assert paths["sprint_status_path"].name == "sprint-status.yaml"
    assert paths["epics_path"].name == "epics.md"


def test_strict_safe_loader_rejects_aliases():
    text = "a: &anchor foo\nb: *anchor\n"
    with pytest.raises(yaml.YAMLError):
        yaml.load(text, Loader=fs._StrictSafeLoader)


def test_strict_safe_loader_rejects_duplicate_keys():
    text = "status: ready\nstatus: shipped\n"
    with pytest.raises(yaml.YAMLError):
        yaml.load(text, Loader=fs._StrictSafeLoader)


def test_strict_safe_loader_accepts_well_formed_yaml():
    text = "status: ready\nother: 1\n"
    assert yaml.load(text, Loader=fs._StrictSafeLoader) == {"status": "ready", "other": 1}


@pytest.mark.parametrize(
    "text",
    [
        "no frontmatter here at all",
        "---\nonly one delimiter",
        "---\na: &x 1\nb: *x\n---\nbody",  # malformed (alias) -> {}
    ],
)
def test_parse_frontmatter_degrades_to_empty(text):
    assert fs._parse_frontmatter(text) == {}


def test_parse_frontmatter_non_dict_yaml_degrades_to_empty():
    text = "---\n- a\n- b\n---\nbody\n"
    assert fs._parse_frontmatter(text) == {}


def test_parse_frontmatter_well_formed():
    text = "---\nstatus: ready\nowner: amelia\n---\n# Body\n"
    assert fs._parse_frontmatter(text) == {"status": "ready", "owner": "amelia"}


def test_read_sprint_status_missing_path_returns_empty():
    assert fs.read_sprint_status(None) == {}
    assert fs.read_sprint_status("/definitely/not/a/real/path.yaml") == {}


def test_read_sprint_status_malformed_yaml_degrades_to_empty(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("development_status: : : [unbalanced\n", encoding="utf-8")
    assert fs.read_sprint_status(str(bad)) == {}


def test_read_sprint_status_non_dict_document_degrades_to_empty(tmp_path: Path):
    path = tmp_path / "list.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    assert fs.read_sprint_status(str(path)) == {}


def test_read_sprint_status_development_status_not_a_mapping_degrades_to_empty(tmp_path: Path):
    path = tmp_path / "scalar.yaml"
    path.write_text("development_status: not-a-mapping\n", encoding="utf-8")
    assert fs.read_sprint_status(str(path)) == {}


def test_read_sprint_status_real_document(tmp_path: Path):
    path = tmp_path / "sprint-status.yaml"
    path.write_text(
        "development_status:\n  epic-1: done\n  epic-2: in-progress\n",
        encoding="utf-8",
    )
    assert fs.read_sprint_status(str(path)) == {"epic-1": "done", "epic-2": "in-progress"}


def test_read_epics_status_missing_path_returns_none():
    assert fs.read_epics_status(None) is None
    assert fs.read_epics_status("/nope/epics.md") is None


def test_read_epics_status_no_status_key_returns_none(tmp_path: Path):
    path = tmp_path / "epics.md"
    path.write_text("---\nowner: amelia\n---\n# Epics\n", encoding="utf-8")
    assert fs.read_epics_status(str(path)) is None


def test_read_epics_status_present(tmp_path: Path):
    path = tmp_path / "epics.md"
    path.write_text("---\nstatus: final\n---\n# Epics\n", encoding="utf-8")
    assert fs.read_epics_status(str(path)) == "final"


def test_build_factory_status_frame_full(tmp_path: Path):
    sprint = tmp_path / "sprint-status.yaml"
    sprint.write_text(
        "development_status:\n  1-1-story-a: done\n  1-2-story-b: in-progress\n",
        encoding="utf-8",
    )
    epics = tmp_path / "epics.md"
    epics.write_text("---\nstatus: final\n---\n# Epics\n", encoding="utf-8")

    frame = fs.build_factory_status_frame(
        build_stamp=STAMP,
        sprint_status_path=sprint,
        epics_path=epics,
    )
    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == fs.FRAME_COLUMNS
    assert frame.iloc[0].to_dict() == {
        "source": "build",
        "artifact": "build_stamp",
        "key": "generated_at",
        "status": STAMP,
    }
    sprint_rows = frame[frame["source"] == "sprint-status.yaml"]
    assert dict(zip(sprint_rows["key"], sprint_rows["status"])) == {
        "1-1-story-a": "done",
        "1-2-story-b": "in-progress",
    }
    assert (frame["source"] == "epics.md").sum() == 1
    assert frame.loc[frame["source"] == "epics.md", "status"].iloc[0] == "final"
    assert (frame["source"] == "docs/specs").sum() == 0


def test_build_factory_status_frame_degrades_on_missing_artifacts(tmp_path: Path):
    frame = fs.build_factory_status_frame(
        build_stamp=STAMP,
        sprint_status_path=tmp_path / "absent.yaml",
        epics_path=tmp_path / "absent.md",
    )
    assert list(frame["source"]) == ["build"]
    assert frame.iloc[0]["status"] == STAMP
    assert "None" not in set(frame["status"])


def test_build_factory_status_frame_uses_default_paths_when_none(monkeypatch, tmp_path: Path):
    """`sprint_status_path`/`epics_path` default to `_default_paths()` when not injected --
    covers the "not provided" branch distinctly from the fixture-injected path above."""
    fake_defaults = {
        "sprint_status_path": tmp_path / "sprint-status.yaml",
        "epics_path": tmp_path / "epics.md",
    }
    monkeypatch.setattr(fs, "_default_paths", lambda: fake_defaults)
    frame = fs.build_factory_status_frame(build_stamp=STAMP)
    assert list(frame["source"]) == ["build"]
