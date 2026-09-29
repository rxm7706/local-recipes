"""scripts/scribe_pg.py moves aside a data dir from another PostgreSQL major (Story 67.1).

scribe-pg moved from PostgreSQL 18 to 17; an existing PG18 cluster cannot start
under PG17 binaries, so `up` moves it aside (never deletes it) and re-initialises,
and refuses outright while an old-major server still holds the port.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "scribe_pg", REPO / "scripts" / "scribe_pg.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["scribe_pg"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def scribe_pg(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "CLUSTER", tmp_path / "var" / "scribe-pg" / "data")
    monkeypatch.setattr(
        module,
        "_run",
        lambda args, **kw: subprocess.CompletedProcess(
            args, 0, "pg_ctl (PostgreSQL) 17.11\n", ""
        ),
    )
    return module


def _cluster(module, major: str) -> None:
    module.CLUSTER.mkdir(parents=True)
    (module.CLUSTER / "PG_VERSION").write_text(f"{major}\n")


def test_other_major_is_moved_aside_not_deleted(scribe_pg, monkeypatch) -> None:
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: False)
    _cluster(scribe_pg, "18")
    assert scribe_pg._move_aside_other_major() == 0
    aside = scribe_pg.CLUSTER.with_name("data.pg18")
    assert (aside / "PG_VERSION").read_text().strip() == "18"
    assert not scribe_pg.CLUSTER.exists()


def test_a_second_move_does_not_overwrite_the_first(scribe_pg, monkeypatch) -> None:
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: False)
    scribe_pg.CLUSTER.with_name("data.pg18").mkdir(parents=True)
    _cluster(scribe_pg, "18")
    assert scribe_pg._move_aside_other_major() == 0
    assert scribe_pg.CLUSTER.with_name("data.pg18.1").is_dir()


def test_same_major_is_left_alone(scribe_pg, monkeypatch) -> None:
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: False)
    _cluster(scribe_pg, "17")
    assert scribe_pg._move_aside_other_major() == 0
    assert (scribe_pg.CLUSTER / "PG_VERSION").is_file()


def test_a_running_old_major_server_is_refused(scribe_pg, monkeypatch, capsys) -> None:
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: True)
    _cluster(scribe_pg, "18")
    assert scribe_pg._move_aside_other_major() == 1
    assert "PostgreSQL 18" in capsys.readouterr().err
    assert (scribe_pg.CLUSTER / "PG_VERSION").is_file()
