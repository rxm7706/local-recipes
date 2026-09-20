"""Unit tests for ``pyforge.doctor.sources.__main__`` (Story 6.9) -- the
target-less ``python -m pyforge.doctor.sources <name> [--json]
[--groundtruth]`` dispatcher every re-pointed pixi task invokes.

Covers the spec's I/O & Edge-Case Matrix: dispatch-by-name (all registered
entries, parametrized -- "one test per dispatch entry"), the unknown-source
usage error, the ``--groundtruth`` scoping error, JSON output shape, and
``verdict.exit_code_for`` exit-code mapping.

Story 11.1 (Epic 11/CAP-1) added ``due-for-verification`` -- the first
genuinely NEW (non-ported) ``DISPATCH`` member, alongside the ten Story 6.9
originally dispatched (the retiring ``scripts/*_check.py`` origins). Story
10.1 (Epic 10/CAP-1) added ``bmad-method-version-drift``, another genuinely
NEW member. The member COUNT is deliberately not in a test's name, per
``test_models.py``'s own documented lesson: a number there goes stale the
next time a story appends an entry.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import (
    bmad_config,
    bmad_method,
    board,
    capability_effect,
    capability_ledger,
    chain,
    deps,
    docs_currency,
    docs_map_hygiene,
    docs_shelf,
    factory,
    frozen_path,
    general_docs_consistency,
    ledger,
    live_proof_surfaces,
    marshal,
    one_chain,
    pixi_currency,
    platform_policy,
    sibling_dreams,
    status_body_consistency,
)

# --- DISPATCH: name -> the exact function the Code Map names ----------------

_EXPECTED_DISPATCH = {
    "ledger-regression": ledger.gather,
    "ledger-direction": ledger.gather_direction,
    "story-status": marshal.gather_story_status,
    "chain-completeness": board.gather_chain_completeness,
    "dashboard-drift": board.gather_dashboard_drift,
    "check-layout": board.gather_check_layout,
    "dream-chain": chain.gather_dream_chain,
    "spec-surface": chain.gather_spec_surface,
    "deferred-work": chain.gather_deferred_work,
    "forward-dependency": deps.gather_forward_dependency,
    "bmad-drift": factory.gather,
    "due-for-verification": chain.gather_due_for_verification,
    "bmad-method-version-drift": bmad_method.gather,
    "sibling-dreams-drift": sibling_dreams.gather,
    "platform-policy-suite": platform_policy.gather,
    "bmad-render-config-ambiguity": bmad_config.gather,
    "frozen-path-changed": frozen_path.gather,
    "capability-effect": capability_effect.gather,
    "status-body-consistency": status_body_consistency.gather,
    "pixi-currency-ledger": pixi_currency.gather,
    "general-docs-consistency": general_docs_consistency.gather,
    "capability-ledger": capability_ledger.gather,
    # Doctor Epic 25 -- both in detectors-ci from day one.
    "chain-sprawl": one_chain.gather_chain_sprawl,
    "fr-without-cap": one_chain.gather_fr_without_cap,
    # Story 30.1 (spec-pyforge-doctor CAP-83): docs/MAP.md hygiene.
    "docs-map-hygiene": docs_map_hygiene.gather,
    # Story 30.2 (spec-pyforge-doctor CAP-84): docs/map.yaml vs its render,
    # authored-page staleness, skill-dir hygiene.
    "docs-currency": docs_currency.gather,
    # Story 23.7 (Epic 23/spec-pyforge-doctor CAP-54) -- leftover-shelf
    # occupancy vs the docs/MAP.md allow-list.
    "docs-shelf-occupancy": docs_shelf.gather,
    # Story 26.1 (spec-pyforge-doctor CAP-77) -- a touched surface
    # catalogued in live-proof-surfaces.md gets an advisory finding naming it.
    "live-proof-surface": live_proof_surfaces.gather,
}


def test_dispatch_covers_exactly_the_registered_sources():
    assert set(dispatch.DISPATCH) == set(_EXPECTED_DISPATCH)


@pytest.mark.parametrize("name", sorted(_EXPECTED_DISPATCH))
def test_dispatch_entry_resolves_to_the_documented_function(name: str):
    assert dispatch.DISPATCH[name] is _EXPECTED_DISPATCH[name]


_STUB_OK = (
    Finding(
        source=Source.LEDGER_REGRESSION,
        check="stub-ok",
        status=DoctorStatus.OK,
        message="stub clean",
        evidence={},
    ),
)
_STUB_FAIL = (
    Finding(
        source=Source.LEDGER_REGRESSION,
        check="stub-fail",
        status=DoctorStatus.FAIL,
        message="stub broken",
        evidence={},
    ),
)


@pytest.mark.parametrize("name", sorted(_EXPECTED_DISPATCH))
def test_main_calls_through_the_dispatch_entry_by_name(
    name: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """A stub swapped into ``DISPATCH[name]`` proves ``main`` actually
    invokes the mapped callable for THIS name, not merely that the dict
    entry exists (the previous two tests already cover that)."""
    calls: list[Path] = []

    def _stub(target: Path) -> tuple[Finding, ...]:
        calls.append(target)
        return _STUB_OK

    monkeypatch.setitem(dispatch.DISPATCH, name, _stub)

    exit_code = dispatch.main([name])

    assert calls == [Path(".")]
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "stub clean" in out


# --- unknown source name -------------------------------------------------------


def test_unknown_source_name_is_a_usage_error_naming_valid_choices(
    capsys: pytest.CaptureFixture[str],
):
    with pytest.raises(SystemExit) as exc:
        dispatch.main(["bogus-name"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "bogus-name" in err
    # argparse's own "invalid choice" message names the valid choices.
    assert "bmad-drift" in err


# --- --groundtruth scoping -----------------------------------------------------


def test_groundtruth_on_bmad_drift_prints_the_ground_truth_dict(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    stub_gt = {
        "skill_version": "8.81.0",
        "schema_version": 29,
        "mcp_tools": 46,
        "atlas_phases": 22,
        "gotcha_max": 107,
        "pixi_envs": 20,
    }
    monkeypatch.setattr(factory, "ground_truth", lambda target: stub_gt)

    exit_code = dispatch.main(["bmad-drift", "--groundtruth"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert json.loads(out) == stub_gt


def test_groundtruth_on_a_non_bmad_drift_source_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
):
    with pytest.raises(SystemExit) as exc:
        dispatch.main(["ledger-regression", "--groundtruth"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--groundtruth" in err
    assert "bmad-drift" in err


# --- --dreams hygiene mode (Story 17.2 / FR-147) --------------------------------


def test_dreams_flag_on_dream_chain_invokes_hygiene_gather(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    hygiene_ok = (
        Finding(
            source=Source.DREAMS_HYGIENE,
            check="dreams-hygiene",
            status=DoctorStatus.OK,
            message="clean",
            evidence={"dreams": 0},
        ),
    )
    monkeypatch.setattr(chain, "gather_dreams_hygiene", lambda target: hygiene_ok)
    # Default gather must NOT run when --dreams is set.
    monkeypatch.setitem(
        dispatch.DISPATCH,
        "dream-chain",
        lambda target: (_ for _ in ()).throw(AssertionError("INV gather ran")),
    )

    exit_code = dispatch.main(["dream-chain", "--dreams", "--json"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == [f.to_json_dict() for f in hygiene_ok]


def test_dreams_flag_on_non_dream_chain_source_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
):
    with pytest.raises(SystemExit) as exc:
        dispatch.main(["ledger-regression", "--dreams"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--dreams" in err
    assert "dream-chain" in err


# --- --json output shape --------------------------------------------------------


def test_json_flag_emits_finding_to_json_dict_shape(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setitem(dispatch.DISPATCH, "ledger-regression", lambda target: _STUB_OK)

    exit_code = dispatch.main(["ledger-regression", "--json"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert json.loads(out) == [f.to_json_dict() for f in _STUB_OK]


# --- exit-code mapping via verdict.exit_code_for --------------------------------


def test_a_fail_finding_exits_non_zero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(dispatch.DISPATCH, "ledger-regression", lambda target: _STUB_FAIL)

    assert dispatch.main(["ledger-regression"]) == 2


def test_only_ok_findings_exit_zero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(dispatch.DISPATCH, "ledger-regression", lambda target: _STUB_OK)

    assert dispatch.main(["ledger-regression"]) == 0


def test_no_findings_exits_zero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(dispatch.DISPATCH, "ledger-regression", lambda target: ())

    assert dispatch.main(["ledger-regression"]) == 0
