"""Story 14.1 — fix-target resolution and the solver seam."""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.warden.actuator import plan_remediations, run_actuator
from pyforge.warden.fix_solver import eligible_candidates, selective_solver
from pyforge.warden.models import Finding, Severity, SeverityTier


class _AcceptAllForge:
    def existing_open_pr(self, finding_id: str) -> None:
        return None

    def open_pull_request(self, proposal):  # noqa: ANN001
        return "https://example.test/pr/1"


def _vuln(pkg: str = "leftpad", version: str = "1.2.0", advisory: str = "GHSA-test") -> Finding:
    return Finding(
        id=f"vuln:{advisory}:{pkg}@{version}",
        axis="vulnerability",
        message=f"{pkg}: {advisory}",
        subject=pkg,
        severity=Severity(tier=SeverityTier.HIGH, raw=None),
    )


def test_eligible_candidates_drop_below_current_and_sort():
    finding_id = "vuln:GHSA-test:leftpad@1.2.0"
    assert eligible_candidates(finding_id, ("1.1.0", "1.3.0", "1.2.3")) == ("1.2.3", "1.3.0")


def test_flag_off_proposal_matches_legacy_body():
    finding = _vuln()
    (legacy,) = plan_remediations([finding])
    (with_flag,) = plan_remediations([finding], target_by_finding_id={})
    assert with_flag.body == legacy.body
    assert with_flag.title == legacy.title


def test_dry_run_names_lowest_candidate_with_solver_not_run():
    finding = _vuln()
    candidates = {finding.id: ("1.2.3", "1.3.0")}
    actuation = run_actuator(
        [finding],
        dry_run=True,
        fix_target_resolution_enabled=True,
        fixed_version_candidates=candidates,
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "planned"
    resolution = outcome.fix_resolution
    assert resolution is not None
    assert resolution.target == "1.2.3"
    assert resolution.solver == "not-run"
    assert resolution.candidates == ("1.2.3", "1.3.0")


def test_real_path_picks_first_solver_accepted_candidate():
    finding = _vuln()
    candidates = {finding.id: ("1.2.3", "1.3.0")}
    solver = selective_solver({"1.2.3"})
    actuation = run_actuator(
        [finding],
        dry_run=False,
        fix_target_resolution_enabled=True,
        fixed_version_candidates=candidates,
        scan_target=Path("."),
        solver=solver,
        client=_AcceptAllForge(),
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "opened"
    assert outcome.fix_resolution is not None
    assert outcome.fix_resolution.target == "1.3.0"
    assert outcome.fix_resolution.attempts == (("1.2.3", "rejected"), ("1.3.0", "accepted"))


def test_no_accepted_candidate_yields_failed_outcome_not_opened():
    finding = _vuln()
    candidates = {finding.id: ("1.2.3", "1.3.0")}
    solver = selective_solver({"1.2.3", "1.3.0"})
    actuation = run_actuator(
        [finding],
        dry_run=False,
        fix_target_resolution_enabled=True,
        fixed_version_candidates=candidates,
        scan_target=Path("."),
        solver=solver,
        client=_AcceptAllForge(),
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "failed"
    assert "no candidate" in (outcome.detail or "")


def test_flag_on_upgrade_body_cites_resolved_target():
    finding = _vuln()
    (proposal,) = plan_remediations(
        [finding],
        target_by_finding_id={finding.id: "1.3.0"},
    )
    assert "1.3.0" in proposal.body
    assert "does not compute" not in proposal.body


def test_actuation_json_includes_fix_resolution():
    finding = _vuln()
    actuation = run_actuator(
        [finding],
        dry_run=True,
        fix_target_resolution_enabled=True,
        fixed_version_candidates={finding.id: ("1.2.3",)},
    )
    payload = actuation.to_json_dict()
    json.loads(json.dumps(payload))
    resolution = payload["outcomes"][0]["fix_resolution"]
    assert resolution["solver"] == "not-run"
    assert resolution["target"] == "1.2.3"
