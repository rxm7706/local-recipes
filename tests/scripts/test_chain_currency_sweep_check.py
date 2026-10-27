"""``scripts/chain_currency_sweep_check.py`` audits the eight stations in one process
(doctor Story 55.2): the gatherer is a library call, its findings are filtered exactly as
the subprocess form filtered them, and an unimportable Doctor is COULD NOT RUN per station."""

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


def test_audit_is_one_library_call_per_station_and_filters_currency_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load()
    calls: list[tuple[Path, str]] = []

    def gather(target: Path, project: str):
        calls.append((target, project))
        print("[fleet] WARN a human preamble that must not reach the script's stdout")
        return (
            _Finding("chain-audit-checkpoint-staleness", "fail", "spec newer than PRD"),
            _Finding("chain-audit-checkpoint-coherence", "pass"),
            _Finding(
                "chain-audit-checkpoint-layers",
                "fail",
                "a layer gap, not a currency finding",
            ),
        )

    monkeypatch.setattr(module, "_load_gatherer", lambda: gather)
    hits, err = module._audit("pyforge-doctor")
    assert err is None
    assert calls == [(module.REPO_ROOT, "pyforge-doctor")]
    assert hits == [
        {
            "check": "chain-audit-checkpoint-staleness",
            "status": "fail",
            "message": "spec newer than PRD",
            "project": "pyforge-doctor",
        }
    ]


def test_unimportable_doctor_is_could_not_run(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    monkeypatch.setattr(module, "_load_gatherer", lambda: None)
    hits, err = module._audit("pyforge-marshal")
    assert hits == []
    assert err is not None and err.startswith("pyforge-marshal:")


def test_main_json_envelope_and_exit_codes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _load()
    monkeypatch.setattr(module, "_load_gatherer", lambda: lambda target, project: ())
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
