"""Meta-test: `fleet_picture.main()` threads every ATTENTION probe into its output.

Each probe helper has its own isolated test file; none of them proves the
`try/except`-wrapped call site inside `main()` reaches the printed `needs`
(`>>`) or `watch` (`-`) lines. A mis-wired `append`, or an `except` that
swallows a real result, would pass every helper test (doctor Story 41.4,
DW-FU-10-3-3). Here every probe is stubbed -- no subprocess, no network, no
ledger -- and `main()` runs end to end, twice: once with each probe
returning a sentinel, once with each probe raising.

The bmad-core probe returns findings tagged `bmad-channel-drift` and
`bmad-recipe-upstream-drift` (Story 15.2's two ambient checks): this is the
fleet-picture layer naming them, not only the generic warn filter
(DW-FU-15-2-2).
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location(
        "fleet_picture_main_under_test", FLEET_PICTURE
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_main_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class _Completed:
    def __init__(self, stdout: str):
        self.stdout = stdout
        self.returncode = 0


def _finding(check: str, message: str, status: str = "warn", **evidence) -> dict:
    return {"source": "s", "check": check, "status": status, "message": message, "evidence": evidence}


_PROBES = (
    "baseline_drift_findings",
    "loop_home_staleness",
    "primary_checkout_staleness",
    "bmad_core_drift_findings",
    "verification_staleness_findings",
    "dream_chain_gap_findings",
    "sibling_dreams_drift_findings",
    "capability_effect_findings",
    "status_body_consistency_findings",
)


@pytest.fixture
def mod(monkeypatch, tmp_path):
    mod = _load_fleet_picture()
    # No ledgers under an empty REPO: zero station rows, so only the
    # fleet-wide probes below can write to ATTENTION.
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "running_stations", lambda: (set(), {}))
    monkeypatch.setattr(mod, "load_drain_queue_overrides", lambda: {})
    monkeypatch.setattr(mod, "_open_prs_by_head_ref", lambda *a, **k: {})
    return mod


def _attention(capsys) -> tuple[list[str], list[str]]:
    out = capsys.readouterr().out
    block = out.split("\nATTENTION:\n", 1)[1].splitlines()
    needs = [line.strip().removeprefix(">> ") for line in block if line.startswith("  >> ")]
    watch = [line.strip().removeprefix("- ") for line in block if line.startswith("   - ")]
    return needs, watch


def test_every_probe_result_reaches_needs_or_watch(mod, monkeypatch, capsys):
    monkeypatch.setattr(
        mod.subprocess, "run", lambda cmd, **kwargs: _Completed("#7 an open pr\n")
    )
    monkeypatch.setattr(mod, "baseline_drift_findings", lambda: ["sentinel"])
    monkeypatch.setattr(
        mod, "_baseline_drift_needs_lines",
        lambda findings: [f"baseline drift: {findings[0]}"],
    )
    monkeypatch.setattr(mod, "loop_home_staleness", lambda: [("steward", "loop/steward", 3)])
    monkeypatch.setattr(mod, "primary_checkout_staleness", lambda: 2)
    monkeypatch.setattr(
        mod, "bmad_core_drift_findings",
        lambda: [
            _finding("bmad-channel-drift", "channel 1.0 behind recipe 1.1"),
            _finding("bmad-recipe-upstream-drift", "recipe 1.1 behind upstream 1.2"),
        ],
    )
    monkeypatch.setattr(
        mod, "verification_staleness_findings",
        lambda: [_finding("due-for-verification", "3 rows due")],
    )
    monkeypatch.setattr(mod, "dream_chain_gap_findings", lambda: ["gap"])
    monkeypatch.setattr(mod, "_dream_chain_watch_lines", lambda findings: [f"dream chain: {findings[0]}"])
    monkeypatch.setattr(
        mod, "sibling_dreams_drift_findings",
        lambda: [_finding("sibling-dreams-drift", "title X differs")],
    )
    monkeypatch.setattr(
        mod, "capability_effect_findings",
        lambda: [_finding("capability-effect", "CAP-9 has no effect")],
    )
    monkeypatch.setattr(
        mod, "status_body_consistency_findings",
        lambda: [_finding("status-body-consistency", "body says done", precision=0.5)],
    )

    assert mod.main() == 0

    needs, watch = _attention(capsys)
    assert needs[0].startswith("1 PR(s) still OPEN") and "#7 an open pr" in needs[0]
    assert "baseline drift: sentinel" in needs
    assert any(n.startswith("steward: loop home (loop/steward) is 3 commit(s) behind") for n in needs)
    assert any(n.startswith("primary checkout is 2 commit(s) behind") for n in needs)
    assert watch == [
        "bmad-channel-drift: channel 1.0 behind recipe 1.1",
        "bmad-recipe-upstream-drift: recipe 1.1 behind upstream 1.2",
        "3 rows due",
        "dream chain: gap",
        "sibling-dreams-drift: title X differs",
        "capability-effect: CAP-9 has no effect",
        "status-body-consistency: body says done (precision=0.500)",
    ]


def test_bmad_core_fail_finding_reaches_watch(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **kwargs: _Completed(""))
    for probe in _PROBES:
        if probe != "bmad_core_drift_findings":
            monkeypatch.setattr(mod, probe, lambda: [])
    monkeypatch.setattr(
        mod,
        "bmad_core_drift_findings",
        lambda: [
            _finding(
                "bmad-method-version-drift",
                "declared floor behind upstream",
                status="fail",
            )
        ],
    )

    assert mod.main() == 0

    _needs, watch = _attention(capsys)
    assert watch == ["bmad-method-version-drift: declared floor behind upstream"]


def test_every_failing_probe_degrades_to_its_own_watch_line(mod, monkeypatch, capsys):
    def _boom(*args, **kwargs):
        raise RuntimeError("probe down")

    monkeypatch.setattr(mod.subprocess, "run", _boom)
    for probe in _PROBES:
        monkeypatch.setattr(mod, probe, _boom)

    assert mod.main() == 0

    needs, watch = _attention(capsys)
    assert needs == []
    assert watch == [
        "could not query open PRs",
        "could not run baseline-drift-check",
        "could not check loop-home staleness",
        "could not check primary-checkout staleness",
        "could not check bmad-method core version drift",
        "could not check verification staleness",
        "could not check dream-chain gaps",
        "could not check sibling-dreams drift",
        "could not check capability-effect",
        "could not check status-body-consistency",
    ]
