"""v8.22.0 — `build` subcommand `--skip` / `--only` phase filtering.

`bootstrap_data.py`'s 4-sub-step orchestrator routes through
`conda_forge_atlas.py build --only PHASE_LIST` (or `--skip`). These
tests verify the filter parses input correctly and selects the right
phase functions to execute.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def atlas_mod():
    return _load("conda_forge_atlas")


class TestParsePhaseList:
    def test_none_returns_empty(self, atlas_mod):
        assert atlas_mod._parse_phase_list(None) == []

    def test_empty_string_returns_empty(self, atlas_mod):
        assert atlas_mod._parse_phase_list("") == []

    def test_single_phase_uppercased(self, atlas_mod):
        assert atlas_mod._parse_phase_list("f") == ["F"]

    def test_multiple_phases_split_on_comma(self, atlas_mod):
        assert atlas_mod._parse_phase_list("F,K,N") == ["F", "K", "N"]

    def test_whitespace_around_tokens_stripped(self, atlas_mod):
        assert atlas_mod._parse_phase_list(" F , K , N ") == ["F", "K", "N"]

    def test_empty_token_skipped(self, atlas_mod):
        assert atlas_mod._parse_phase_list("F,,K") == ["F", "K"]

    def test_unknown_phase_raises(self, atlas_mod):
        with pytest.raises(ValueError, match="unknown phase"):
            atlas_mod._parse_phase_list("F,ZZZ")

    def test_dotted_phase_id_supported(self, atlas_mod):
        # B.5 and similar dotted phases must parse + match.
        assert atlas_mod._parse_phase_list("b.5") == ["B.5"]


class TestBuildPhaseSelection:
    """`cmd_build` selects the right `phases_to_run` from `--skip` /
    `--only`. We stub every phase function to a recorder so we can
    inspect which ones got called."""

    def _stub_phases(self, monkeypatch, atlas_mod):
        """Replace every PHASES entry's function with a recorder that
        returns an empty stats dict. Returns the list of phase IDs
        that get invoked when `cmd_build` runs."""
        invoked: list[str] = []
        new_phases: list[tuple] = []
        for name, _ in atlas_mod.PHASES:
            captured_name = name

            def fake_phase(_conn, _name=captured_name):
                invoked.append(_name)
                return {}

            new_phases.append((captured_name, fake_phase))
        monkeypatch.setattr(atlas_mod, "PHASES", new_phases)
        return invoked

    def _stub_db(self, monkeypatch, tmp_path, atlas_mod):
        """Use a tmpdir DB so the test doesn't touch the real atlas."""
        db_path = tmp_path / "cf_atlas.db"
        monkeypatch.setattr(atlas_mod, "DB_PATH", db_path)

    def test_build_skip_arg_excludes_phases(
        self, monkeypatch, tmp_path, atlas_mod,
    ):
        self._stub_db(monkeypatch, tmp_path, atlas_mod)
        invoked = self._stub_phases(monkeypatch, atlas_mod)
        args = argparse.Namespace(
            dry_run=False, export_json=False,
            skip="F,K,N", only=None,
        )
        rc = atlas_mod.cmd_build(args)
        assert rc == 0
        # F, K, N must not have been invoked; everything else was.
        assert "F" not in invoked
        assert "K" not in invoked
        assert "N" not in invoked
        # And the surviving phases preserve PHASES order.
        all_names = [name for name, _ in atlas_mod.PHASES]
        expected = [n for n in all_names if n not in ("F", "K", "N")]
        assert invoked == expected

    def test_build_only_arg_runs_subset(
        self, monkeypatch, tmp_path, atlas_mod,
    ):
        self._stub_db(monkeypatch, tmp_path, atlas_mod)
        invoked = self._stub_phases(monkeypatch, atlas_mod)
        args = argparse.Namespace(
            dry_run=False, export_json=False,
            skip=None, only="F",
        )
        rc = atlas_mod.cmd_build(args)
        assert rc == 0
        assert invoked == ["F"]

    def test_build_only_multiple_runs_in_listed_order(
        self, monkeypatch, tmp_path, atlas_mod,
    ):
        self._stub_db(monkeypatch, tmp_path, atlas_mod)
        invoked = self._stub_phases(monkeypatch, atlas_mod)
        args = argparse.Namespace(
            dry_run=False, export_json=False,
            skip=None, only="K,F",
        )
        rc = atlas_mod.cmd_build(args)
        assert rc == 0
        # `--only` preserves operator-specified order.
        assert invoked == ["K", "F"]

    def test_build_skip_and_only_mutex(
        self, monkeypatch, tmp_path, atlas_mod, capsys,
    ):
        self._stub_db(monkeypatch, tmp_path, atlas_mod)
        self._stub_phases(monkeypatch, atlas_mod)
        args = argparse.Namespace(
            dry_run=False, export_json=False,
            skip="F", only="K",
        )
        rc = atlas_mod.cmd_build(args)
        assert rc == 2
        err = capsys.readouterr().err
        assert "mutually exclusive" in err

    def test_build_no_flags_runs_every_phase(
        self, monkeypatch, tmp_path, atlas_mod,
    ):
        # Regression guard: bare `build` (no --skip, no --only) must run
        # every phase, matching pre-v8.22.0 behavior.
        self._stub_db(monkeypatch, tmp_path, atlas_mod)
        invoked = self._stub_phases(monkeypatch, atlas_mod)
        args = argparse.Namespace(
            dry_run=False, export_json=False,
            skip=None, only=None,
        )
        rc = atlas_mod.cmd_build(args)
        assert rc == 0
        all_names = [name for name, _ in atlas_mod.PHASES]
        assert invoked == all_names
