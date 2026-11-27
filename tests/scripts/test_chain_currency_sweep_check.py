"""``scripts/chain_currency_sweep_check.py`` audits the eight stations in one process
(doctor Story 55.2) and, since doctor Story 69.1, in one library call over one fleet
scan: the gatherer is the batch form, its findings are filtered exactly as the subprocess
form filtered them, and an unimportable Doctor, a raising gatherer or a station the
gatherer left out is COULD NOT RUN for that station."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "chain_currency_sweep_check.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("chain_currency_sweep_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Finding:
    def __init__(self, check: str, status: str, message: str = "") -> None:
        self._row = {"check": check, "status": status, "message": message}

    def to_json_dict(self) -> dict[str, object]:
        return dict(self._row)


def test_audit_is_one_library_call_for_every_station_and_filters_currency_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load()
    calls: list[tuple[Path, tuple[str, ...]]] = []

    def gather(target: Path, projects: tuple[str, ...]):
        calls.append((target, tuple(projects)))
        print("[fleet] WARN a human preamble that must not reach the script's stdout")
        return {
            "pyforge-doctor": (
                _Finding(
                    "chain-audit-checkpoint-staleness", "fail", "spec newer than PRD"
                ),
                _Finding("chain-audit-checkpoint-coherence", "pass"),
                _Finding(
                    "chain-audit-checkpoint-layers",
                    "fail",
                    "a layer gap, not a currency finding",
                ),
            ),
            "pyforge-marshal": (_Finding("chain-audit-checkpoint-staleness", "ok"),),
        }

    monkeypatch.setattr(module, "_load_gatherer", lambda: gather)
    audits = module._audit_all(("pyforge-doctor", "pyforge-marshal"))
    assert calls == [(module.REPO_ROOT, ("pyforge-doctor", "pyforge-marshal"))]
    assert audits == {
        "pyforge-doctor": (
            [
                {
                    "check": "chain-audit-checkpoint-staleness",
                    "status": "fail",
                    "message": "spec newer than PRD",
                    "project": "pyforge-doctor",
                }
            ],
            None,
        ),
        "pyforge-marshal": ([], None),
    }


def test_unimportable_doctor_is_could_not_run(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    monkeypatch.setattr(module, "_load_gatherer", lambda: None)
    audits = module._audit_all(("pyforge-marshal", "pyforge-doctor"))
    for slug, (hits, err) in audits.items():
        assert hits == []
        assert err is not None and err.startswith(f"{slug}:")


def test_a_raising_gatherer_is_could_not_run_for_every_station(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load()

    def gather(target: Path, projects: tuple[str, ...]):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "_load_gatherer", lambda: gather)
    audits = module._audit_all(("pyforge-marshal", "pyforge-doctor"))
    for slug, (hits, err) in audits.items():
        assert hits == []
        assert err == f"{slug}: audit raised RuntimeError: boom"


def test_a_station_the_gatherer_left_out_is_could_not_run_never_green(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load()
    monkeypatch.setattr(
        module, "_load_gatherer", lambda: lambda target, projects: {"pyforge-doctor": ()}
    )
    audits = module._audit_all(("pyforge-doctor", "pyforge-marshal"))
    assert audits["pyforge-doctor"] == ([], None)
    hits, err = audits["pyforge-marshal"]
    assert hits == []
    assert err is not None and err.startswith("pyforge-marshal:")


def test_main_json_envelope_and_exit_codes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _load()
    monkeypatch.setattr(
        module,
        "_load_gatherer",
        lambda: lambda target, projects: {p: () for p in projects},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["chain_currency_sweep_check.py", "--json", "--project", "pyforge-steward"],
    )
    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"findings": [], "errors": []}

    monkeypatch.setattr(module, "_load_gatherer", lambda: None)
    assert module.main() == 2
