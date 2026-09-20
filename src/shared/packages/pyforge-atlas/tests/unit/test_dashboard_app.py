"""Unit coverage for `pyforge.atlas.dashboard.app` (Story 25.1).

The `dashboard-dryrun` gate (`tests/integration/dashboard/test_dashboard_dryrun.py`)
already builds this same offline Dashboard object extensively -- but it lives under
`tests/integration`, which the diff-scoped `unit` coverage gate
(`scripts/coverage_gates_ci.py`) never measures. These tests exercise `build_dashboard`
and its private page-assembly helpers directly from `tests/unit` so the module's real
behavior (not a mock) counts toward the gate.
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path

import pandas as pd
import vizro.models as vm
from vizro import Vizro
from vizro.managers import data_manager

from pyforge.atlas.dashboard import app
from pyforge.atlas.dashboard import data as _data
from pyforge.atlas.provenance import ProvenanceInfo

NOW = 1_700_000_000
STAMP = "2026-09-09T00:00:00Z"


def _dm_get(key: str):
    try:
        return data_manager[key]
    except KeyError:
        return None


# --------------------------------------------------------------------------- #
# build_dashboard -- offline build, default (all-missing) data root
# --------------------------------------------------------------------------- #


def test_build_dashboard_offline_with_missing_data_root():
    d = app.build_dashboard(build_stamp=STAMP, data_root="/nonexistent-data-root", now=NOW)
    assert isinstance(d, vm.Dashboard)
    assert d.id == app.DASHBOARD_ID
    got_ids = {p.id for p in d.pages}
    expected_ids = {p.id for p in app.PAGE_INVENTORY}
    assert got_ids == expected_ids


def test_build_dashboard_no_bsl_shell_pages_register_no_data_function():
    d = app.build_dashboard(build_stamp=STAMP, data_root="/nonexistent-data-root", now=NOW)
    for pid in ("behind-upstream", "whodepends"):
        page = next(p for p in d.pages if p.id == pid)
        assert _dm_get(f"data::{pid}") is None
        card = page.components[0]
        assert "unavailable" in card.text
        assert "no data function registered" in card.text
        assert "AD-17" in card.text


def test_build_dashboard_shell_pages_state_backing_file_not_found():
    d = app.build_dashboard(build_stamp=STAMP, data_root="/nonexistent-data-root", now=NOW)
    page = next(p for p in d.pages if p.id == "staleness-report")
    card = next(c for c in page.components if isinstance(c, vm.Card))
    assert "unavailable" in card.text
    assert "backing file not found" in card.text


def test_build_dashboard_identity_ops_registers_four_panes():
    d = app.build_dashboard(build_stamp=STAMP, data_root="/nonexistent-data-root", now=NOW)
    page = next(p for p in d.pages if p.id == "identity-ops")
    for pane in ("priority", "issues", "builds", "census"):
        obj = _dm_get(f"data::identity-ops::{pane}")
        assert obj is not None
        assert isinstance(obj.load(), pd.DataFrame)
    assert any(isinstance(c, vm.AgGrid) for c in page.components)


def test_build_dashboard_factory_status_carries_build_stamp():
    d = app.build_dashboard(build_stamp=STAMP, data_root="/nonexistent-data-root", now=NOW)
    page = next(p for p in d.pages if p.id == "factory-status")
    stamp_card = next(c for c in page.components if isinstance(c, vm.Card))
    assert STAMP in stamp_card.text
    assert "AD-17" in stamp_card.text
    grid = next(c for c in page.components if isinstance(c, vm.AgGrid))
    assert grid.figure["defaultColDef"]["cellDataType"] == "text"


def test_build_dashboard_defaults_build_stamp_and_now_and_data_root_when_omitted():
    """Every wall-clock-defaulted arg (`build_stamp`, `now`, `data_root`) resolves ONCE
    inside the function when not injected -- covers the `is None` branches distinctly
    from every other test here, which always injects them."""
    d = app.build_dashboard()
    assert isinstance(d, vm.Dashboard)
    page = next(p for p in d.pages if p.id == "factory-status")
    stamp_card = next(c for c in page.components if isinstance(c, vm.Card))
    # A real ISO-ish timestamp landed in the card, not a literal "None".
    assert "Build timestamp (AD-17):" in stamp_card.text
    assert "None" not in stamp_card.text


def test_build_dashboard_reset_false_still_builds_when_manager_already_clean():
    """`reset=False` skips the internal `Vizro._reset()` call -- proven here by
    resetting manually first (so the second build does not collide with the
    first build's still-registered model ids) and confirming the object still
    builds correctly."""
    Vizro._reset()
    d1 = app.build_dashboard(build_stamp=STAMP, data_root="/nope", now=NOW)
    assert isinstance(d1, vm.Dashboard)
    Vizro._reset()
    d2 = app.build_dashboard(build_stamp=STAMP, data_root="/nope", now=NOW, reset=False)
    assert isinstance(d2, vm.Dashboard)
    assert {p.id for p in d2.pages} == {p.id for p in app.PAGE_INVENTORY}


# --------------------------------------------------------------------------- #
# build_dashboard -- a grounded page's file-mtime provenance (the non-"unavailable"
# `_provenance_line` branch, and the `_legibility_card` "grounded" branch)
# --------------------------------------------------------------------------- #


def test_grounded_page_carries_real_file_mtime_provenance(tmp_path: Path):
    parquet = tmp_path / _data.FEEDSTOCK_HEALTH_PARQUET
    parquet.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"feedstock_name": ["alpha"]}).to_parquet(parquet)
    old_ts = 1_600_000_000
    os.utime(parquet, (old_ts, old_ts))

    d = app.build_dashboard(build_stamp=STAMP, data_root=tmp_path, now=NOW)
    page = next(p for p in d.pages if p.id == "feedstock-health")
    card = next(c for c in page.components if isinstance(c, vm.Card))

    expected_stamp = datetime.datetime.fromtimestamp(old_ts, tz=datetime.UTC).isoformat()
    assert expected_stamp in card.text
    assert "AD-17" in card.text
    assert "unavailable" not in card.text
    assert "**Data:** live" in card.text


# --------------------------------------------------------------------------- #
# _identity_workbook_page -- both files present -> no gap message -> the
# `elif page.note:` branch (vs. the default missing-files `if gap_message:` branch
# already exercised by test_build_dashboard_offline_with_missing_data_root above)
# --------------------------------------------------------------------------- #


def test_identity_workbook_page_falls_back_to_page_note_when_both_files_present(
    tmp_path: Path,
):
    complete = tmp_path / _data.IDENTITY_COMPLETE_EXPORT_PARQUET
    enterprise = tmp_path / _data.ENTERPRISE_JFROG_CONSUMPTION_PARQUET
    complete.parent.mkdir(parents=True, exist_ok=True)
    enterprise.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"Core_Python_Package_Name": ["a"]}).to_parquet(complete)
    pd.DataFrame({"core_python_package_name": ["a"]}).to_parquet(enterprise)

    d = app.build_dashboard(build_stamp=STAMP, data_root=tmp_path, now=NOW)
    page = next(p for p in d.pages if p.id == "identity-workbook")
    about_card = next(c for c in page.components if isinstance(c, vm.Card) and c.id.endswith("--about"))
    by_id = {p.id: p for p in app.PAGE_INVENTORY}
    assert by_id["identity-workbook"].note in about_card.text
    external_card = next(c for c in page.components if isinstance(c, vm.Card) and c.id.endswith("--external"))
    assert "External source counts" in external_card.text
    assert _dm_get("data::identity-workbook") is not None


# --------------------------------------------------------------------------- #
# _resolve_two_file_provenance -- all four branches, directly
# --------------------------------------------------------------------------- #


def test_resolve_two_file_provenance_both_missing_returns_ranked_unavailable(tmp_path: Path):
    got = app._resolve_two_file_provenance(tmp_path / "ranked.parquet", tmp_path / "ent.parquet")
    assert got.kind == "unavailable"
    assert "ranked.parquet" in got.reason


def test_resolve_two_file_provenance_only_enterprise_missing(tmp_path: Path):
    ranked = tmp_path / "ranked.parquet"
    ranked.write_bytes(b"x")
    got = app._resolve_two_file_provenance(ranked, tmp_path / "ent.parquet")
    assert got.kind == "unavailable"
    assert "ent.parquet" in got.reason


def test_resolve_two_file_provenance_ranked_older_wins(tmp_path: Path):
    ranked = tmp_path / "ranked.parquet"
    enterprise = tmp_path / "ent.parquet"
    ranked.write_bytes(b"x")
    enterprise.write_bytes(b"x")
    os.utime(ranked, (1_000_000_000, 1_000_000_000))
    os.utime(enterprise, (2_000_000_000, 2_000_000_000))
    got = app._resolve_two_file_provenance(ranked, enterprise)
    assert got.kind == "file-mtime"
    assert got.build_stamp == datetime.datetime.fromtimestamp(1_000_000_000, tz=datetime.UTC).isoformat()


def test_resolve_two_file_provenance_enterprise_older_wins(tmp_path: Path):
    ranked = tmp_path / "ranked.parquet"
    enterprise = tmp_path / "ent.parquet"
    ranked.write_bytes(b"x")
    enterprise.write_bytes(b"x")
    os.utime(ranked, (2_000_000_000, 2_000_000_000))
    os.utime(enterprise, (1_000_000_000, 1_000_000_000))
    got = app._resolve_two_file_provenance(ranked, enterprise)
    assert got.kind == "file-mtime"
    assert got.build_stamp == datetime.datetime.fromtimestamp(1_000_000_000, tz=datetime.UTC).isoformat()


# --------------------------------------------------------------------------- #
# _provenance_line / _legibility_card -- directly, both provenance kinds
# --------------------------------------------------------------------------- #


def test_provenance_line_unavailable_states_the_reason():
    info = ProvenanceInfo(kind="unavailable", build_stamp=None, reason="backing file not found: x")
    line = app._provenance_line(info)
    assert "unavailable" in line
    assert "backing file not found: x" in line
    assert "AD-17" in line


def test_provenance_line_known_kind_states_the_stamp():
    info = ProvenanceInfo(kind="file-mtime", build_stamp="2026-01-01T00:00:00+00:00")
    line = app._provenance_line(info)
    assert "2026-01-01T00:00:00+00:00" in line
    assert "file-mtime" in line


def test_legibility_card_includes_note_when_present():
    page = app.PageDef("some-page", "Some Page", "some-cli", "bsl-shell", note="a data gap note")
    info = ProvenanceInfo(kind="unavailable", build_stamp=None, reason="nope")
    card = app._legibility_card(page, grounded=False, provenance=info)
    assert isinstance(card, vm.Card)
    assert "Some Page" in card.text
    assert "Data gap" in card.text
    assert "a data gap note" in card.text
    assert "**Data:** live" not in card.text


def test_page_def_note_defaults_to_empty_string():
    page = app.PageDef("x", "X", "x-cli", "grounded-data")
    assert page.note == ""
