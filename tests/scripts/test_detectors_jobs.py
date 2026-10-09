"""Story 71.5: ``scripts/detectors.py --jobs`` runs script detectors concurrently."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO / "scripts"
_DETECTORS = _SCRIPTS_DIR / "detectors.py"


def _load_detectors():
    spec = importlib.util.spec_from_file_location("detectors", _DETECTORS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_detectors_json(jobs: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(_DETECTORS), "--scope", "repo", "--jobs", jobs, "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(proc.stdout)
    return proc.returncode, payload


def _result_signature(results: list[dict]) -> list[tuple]:
    return [(r["name"], r["status"], r["rc"]) for r in results]


def test_jobs_one_matches_parallel_repo_scope() -> None:
    rc1, out1 = _run_detectors_json("1")
    rc8, out8 = _run_detectors_json("8")
    assert _result_signature(out1["results"]) == _result_signature(out8["results"])
    assert rc1 == rc8


def test_three_sleep_detectors_finish_under_two_seconds_with_jobs_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detectors = _load_detectors()
    sleepers = [
        {"path": f"p{i}", "name": f"sleep{i}", "scope": "repo", "task": "t"}
        for i in range(3)
    ]

    def fake_run_one(det: dict, timeout: int) -> dict:
        started = time.monotonic()
        time.sleep(1)
        return {
            **det,
            "rc": 0,
            "status": "pass",
            "secs": round(time.monotonic() - started, 1),
            "summary": "",
            "output": "",
            "structured_findings": [],
        }

    monkeypatch.setattr(detectors, "run_one", fake_run_one)
    started = time.monotonic()
    results = detectors._run_script_detectors(sleepers, timeout=30, jobs=3)
    elapsed = time.monotonic() - started
    assert elapsed < 2.0
    assert [r["name"] for r in results] == [s["name"] for s in sleepers]


def test_concurrent_run_preserves_timeout_findings_and_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detectors = _load_detectors()
    dets = [
        {"path": "a", "name": "timeout_det", "scope": "repo", "task": "t"},
        {"path": "b", "name": "findings_det", "scope": "repo", "task": "t"},
        {"path": "c", "name": "unknown_det", "scope": "repo", "task": "t"},
    ]

    def fake_run_one(det: dict, timeout: int) -> dict:
        if det["name"] == "timeout_det":
            return {
                **det,
                "rc": 2,
                "status": "unknown",
                "secs": 0.0,
                "summary": f"UNKNOWN: exceeded {timeout}s",
                "output": f"UNKNOWN: exceeded {timeout}s",
                "structured_findings": [],
            }
        if det["name"] == "findings_det":
            return {
                **det,
                "rc": 1,
                "status": "FINDINGS",
                "secs": 0.0,
                "summary": "bad",
                "output": "bad",
                "structured_findings": [],
            }
        return {
            **det,
            "rc": 2,
            "status": "unknown",
            "secs": 0.0,
            "summary": "could not run",
            "output": "",
            "structured_findings": [],
        }

    monkeypatch.setattr(detectors, "run_one", fake_run_one)
    parallel = detectors._run_script_detectors(dets, timeout=5, jobs=3)
    serial = [fake_run_one(d, 5) for d in dets]
    assert _result_signature(parallel) == _result_signature(serial)
