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


class TestPickFeedstock:
    """`_pick_feedstock` resolves the 1:N feedstock-outputs mapping: prefer the
    dedicated feedstock (name == output) over the historical umbrella when an
    output lists more than one — the dbt-* adapter-family collapse fix."""

    def test_empty_returns_none(self, atlas_mod):
        assert atlas_mod._pick_feedstock("anything", []) is None

    def test_single_entry_passes_through(self, atlas_mod):
        # common 1:1 case + naming-divergence / genuine multi-output feedstocks
        assert atlas_mod._pick_feedstock("numpy", ["numpy"]) == "numpy"
        assert atlas_mod._pick_feedstock(
            "cookiecutter-django", ["cookiecutter-django-core"]
        ) == "cookiecutter-django-core"
        # dbt-core is published only by the umbrella dbt feedstock
        assert atlas_mod._pick_feedstock("dbt-core", ["dbt"]) == "dbt"

    def test_multi_prefers_dedicated_matching_name(self, atlas_mod):
        # dbt adapter family: dedicated feedstock wins over the 'dbt' umbrella
        assert atlas_mod._pick_feedstock(
            "dbt-bigquery", ["dbt", "dbt-bigquery"]
        ) == "dbt-bigquery"
        assert atlas_mod._pick_feedstock(
            "dbt-snowflake", ["dbt", "dbt-snowflake"]
        ) == "dbt-snowflake"

    def test_multi_no_name_match_falls_back_to_first(self, atlas_mod):
        # genuinely ambiguous: output not named after any listed feedstock
        assert atlas_mod._pick_feedstock("foo", ["bar", "baz"]) == "bar"

    def test_dedicated_pick_is_order_independent(self, atlas_mod):
        assert atlas_mod._pick_feedstock(
            "dbt-postgres", ["dbt-postgres", "dbt"]
        ) == "dbt-postgres"


class TestMergePhasesRun:
    """`_merge_phases_run` unions existing + new phases in canonical PHASES
    order — lets the v8.22.0 bootstrap split accumulate core/F/K/N instead of
    each `build --only` sub-step clobbering `phases_run`."""

    def test_union_dedups(self, atlas_mod):
        assert atlas_mod._merge_phases_run(["B", "C"], ["C", "F"]) == ["B", "C", "F"]

    def test_orders_by_canonical_phases_not_insertion(self, atlas_mod):
        # F comes after C in PHASES even though it's supplied first/second
        assert atlas_mod._merge_phases_run(["F"], ["C", "B"]) == ["B", "C", "F"]

    def test_empty_new_preserves_existing(self, atlas_mod):
        assert atlas_mod._merge_phases_run(["N"], []) == ["N"]

    def test_split_accumulation_reaches_full_set(self, atlas_mod):
        # Simulate the split: core stamps B..M, then F / K / N each merge in.
        core = ["B", "B.5", "B.6", "C", "C.5", "D", "O", "P", "Q", "R", "S",
                "E", "E.5", "G", "G'", "H", "J", "L", "M"]
        after_f = atlas_mod._merge_phases_run(core, ["F"])
        after_k = atlas_mod._merge_phases_run(after_f, ["K"])
        after_n = atlas_mod._merge_phases_run(after_k, ["N"])
        full = [name for name, _ in atlas_mod.PHASES]
        assert after_n == full  # every phase present, in canonical order
        assert "F" in after_n and "K" in after_n and "N" in after_n

    def test_unknown_phase_sorted_after_known(self, atlas_mod):
        assert atlas_mod._merge_phases_run(["B"], ["ZZ"]) == ["B", "ZZ"]

    def test_read_meta_phases_run_roundtrip(self, atlas_mod):
        import json as _json, sqlite3 as _sq
        conn = _sq.connect(":memory:")
        conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
        # absent -> []
        assert atlas_mod._read_meta_phases_run(conn) == []
        conn.execute("INSERT INTO meta(key, value) VALUES ('phases_run', ?)",
                     (_json.dumps(["B", "F", "N"]),))
        assert atlas_mod._read_meta_phases_run(conn) == ["B", "F", "N"]
