"""Story 16.3 — fleet fix proposal queue and operator approval."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test.utils import override_settings
from django_pyforge.flags import evaluate_from_source
from django_warden_fabric.fleet import FLEET_FIX_PROPOSALS_FLAG
from django_warden_fabric.fleet import FLEET_SCAN_FLAG
from django_warden_fabric.models import FixProposal
from django_warden_fabric.models import FleetRepo
from django_warden_fabric.models import FleetRepoScan
from django_warden_fabric.models import FleetRun
from django_warden_fabric.models import JobStatus
from django_warden_fabric.proposals import ProposalRefusedError
from django_warden_fabric.proposals import approve_proposal
from django_warden_fabric.proposals import dismiss_proposal
from django_warden_fabric.tasks import finalize_fleet_run
from django_warden_fabric.tasks import open_fix_proposal
from pyforge.warden.actuator import RemediationProposal
from pyforge.warden.manifest_fixup import ManifestFileChange
from pyforge.warden.manifest_fixup import ManifestFixPlan

from test_warden_fleet_run import _ORG
from test_warden_fleet_run import _init_bare_repo
from test_warden_fleet_run import _seed_inventory

_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_FLAGS_JSON = _PLATFORM_DIR / "config" / "flags.json"
_EXIT_REFUSED = 2
_FINDING_A = "vuln:PDOS-FIXTURE-0001:pkg-a@1.0.0"
_FINDING_B = "hygiene:DEP002:pkg-b"


def _flag_tree(*, fleet_on: bool, proposals_on: bool) -> dict:
    tree = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    tree["flags"][FLEET_SCAN_FLAG]["defaultVariant"] = "on" if fleet_on else "off"
    tree["flags"][FLEET_FIX_PROPOSALS_FLAG]["defaultVariant"] = "on" if proposals_on else "off"
    return tree


def _report_with_planned(*finding_ids: str) -> str:
    outcomes = [
        {
            "finding_id": fid,
            "action": "upgrade" if fid.startswith("vuln:") else "removal",
            "subject": fid.split(":")[-1].split("@")[0],
            "status": "planned",
            "pr_url": None,
            "detail": None,
        }
        for fid in finding_ids
    ]
    findings = [
        {
            "id": fid,
            "axis": "vulnerability" if fid.startswith("vuln:") else "hygiene",
            "message": "fixture",
            "subject": fid.split(":")[-1].split("@")[0],
            "severity": {"tier": "high", "raw": None},
        }
        for fid in finding_ids
    ]
    return json.dumps(
        {
            "schema_version": "1.1.0",
            "status": {"value": "warnings", "driver": {"axis": "vulnerability", "finding_id": finding_ids[0]}},
            "exit_code": 1,
            "findings": findings,
            "actuation": {"dry_run": True, "outcomes": outcomes},
        },
    )


class _RecordingForge:
    repo_slug = "fixture-org/repo-0"
    opens: list[object]

    def __init__(self) -> None:
        self.opens = []

    def existing_open_pr(self, finding_id: str) -> None:
        return None

    def open_pull_request(
        self,
        proposal: RemediationProposal,
        *,
        manifest_fix: ManifestFixPlan | None = None,
        draft: bool = False,
    ) -> str:
        self.opens.append((proposal.finding_id, draft))
        return "https://forge.example/draft/1"


@pytest.fixture
def proposal_flags_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-on.json"
    tree.write_text(json.dumps(_flag_tree(fleet_on=True, proposals_on=True)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert evaluate_from_source(key=FLEET_FIX_PROPOSALS_FLAG, source=tree) is True
    return tree


@pytest.fixture
def proposal_flags_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-off.json"
    tree.write_text(json.dumps(_flag_tree(fleet_on=True, proposals_on=False)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    assert evaluate_from_source(key=FLEET_FIX_PROPOSALS_FLAG, source=tree) is False
    return tree


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_run_complete_queues_two_proposals_zero_forge_writes(
    tmp_path: Path,
    proposal_flags_on: Path,
) -> None:
    repos = _seed_inventory(tmp_path)
    run = FleetRun.objects.create(organisation=_ORG, status=JobStatus.RUNNING)
    scan_a = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repos[0],
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_A, _FINDING_B),
    )
    FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repos[1],
        status=JobStatus.SUCCEEDED,
        report_json='{"actuation": null}',
    )
    forge = _RecordingForge()

    with patch("pyforge.warden.actuator.run_actuator") as mock_actuator:
        finalize_fleet_run([], str(run.pk))
        mock_actuator.assert_not_called()

    assert FixProposal.objects.filter(fleet_repo_scan=scan_a, state=FixProposal.State.QUEUED).count() == 2
    assert forge.opens == []


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_approve_one_opens_draft_other_stays_queued(
    tmp_path: Path,
    proposal_flags_on: Path,
) -> None:
    url = _init_bare_repo(tmp_path, "target")
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/target",
        default_branch="main",
        clone_url=url,
        archived=False,
    )
    run = FleetRun.objects.create(organisation=_ORG)
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_A, _FINDING_B),
    )
    proposals = list(
        FixProposal.objects.filter(fleet_repo_scan=scan).order_by("finding_id"),
    )
    assert len(proposals) == 0
    from django_warden_fabric.proposals import queue_proposals_from_scan

    queue_proposals_from_scan(scan)
    proposals = list(
        FixProposal.objects.filter(fleet_repo_scan=scan).order_by("finding_id"),
    )
    assert len(proposals) == 2
    forge = _RecordingForge()

    with patch("django_warden_fabric.tasks.shallow_clone"), patch(
        "django_warden_fabric.tasks.run_actuator",
    ) as mock_run:
        from pyforge.warden.actuator import PROutcome

        mock_run.return_value = type(
            "Actuation",
            (),
            {
                "outcomes": (
                    PROutcome(
                        finding_id=proposals[0].finding_id,
                        action=proposals[0].action,
                        subject=proposals[0].target,
                        status="opened",
                        pr_url="https://forge.example/draft/1",
                    ),
                ),
            },
        )()
        approve_proposal(proposals[0].pk, "operator@test")
        open_fix_proposal(str(proposals[0].pk))

    proposals[0].refresh_from_db()
    proposals[1].refresh_from_db()
    assert proposals[0].state == FixProposal.State.OPENED
    assert proposals[0].pr_url == "https://forge.example/draft/1"
    assert proposals[1].state == FixProposal.State.QUEUED
    assert forge.opens == []


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_open_failure_records_failed_and_removes_clone(
    tmp_path: Path,
    proposal_flags_on: Path,
) -> None:
    url = _init_bare_repo(tmp_path, "fail")
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/fail",
        default_branch="main",
        clone_url=url,
        archived=False,
    )
    run = FleetRun.objects.create(organisation=_ORG)
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_A),
    )
    from django_warden_fabric.proposals import queue_proposals_from_scan

    queue_proposals_from_scan(scan)
    proposal = FixProposal.objects.get(fleet_repo_scan=scan)
    proposal.state = FixProposal.State.APPROVED
    proposal.save(update_fields=["state"])
    seen: list[Path] = []

    def _track_mkdtemp(prefix: str = "warden-fleet-open-") -> Path:
        from django_warden_fabric.fleet import mkdtemp_clone_dir

        path = mkdtemp_clone_dir(prefix=prefix)
        seen.append(path)
        return path

    with patch("django_warden_fabric.tasks.mkdtemp_clone_dir", side_effect=_track_mkdtemp), patch(
        "django_warden_fabric.tasks.shallow_clone",
        side_effect=RuntimeError("forge 5xx"),
    ):
        open_fix_proposal(str(proposal.pk))

    proposal.refresh_from_db()
    assert proposal.state == FixProposal.State.FAILED
    assert "forge 5xx" in proposal.error
    assert seen and not seen[0].exists()


@pytest.mark.django_db
def test_double_approve_refused(proposal_flags_on: Path) -> None:
    run = FleetRun.objects.create(organisation=_ORG)
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/x",
        default_branch="main",
        clone_url="file:///unused",
        archived=False,
    )
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_A),
    )
    from django_warden_fabric.proposals import queue_proposals_from_scan

    queue_proposals_from_scan(scan)
    proposal = FixProposal.objects.get(fleet_repo_scan=scan)
    approve_proposal(proposal.pk, "op")
    with pytest.raises(ProposalRefusedError, match="already approved"):
        approve_proposal(proposal.pk, "op")


@pytest.mark.django_db
def test_dismiss_without_forge(proposal_flags_on: Path) -> None:
    run = FleetRun.objects.create(organisation=_ORG)
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/y",
        default_branch="main",
        clone_url="file:///unused",
        archived=False,
    )
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_B),
    )
    from django_warden_fabric.proposals import queue_proposals_from_scan

    queue_proposals_from_scan(scan)
    proposal = FixProposal.objects.get(fleet_repo_scan=scan)
    with patch("pyforge.warden.actuator.run_actuator") as mock_actuator:
        dismiss_proposal(proposal.pk)
        mock_actuator.assert_not_called()
    proposal.refresh_from_db()
    assert proposal.state == FixProposal.State.DISMISSED


@pytest.mark.django_db
def test_flag_off_refuses_exit_2(proposal_flags_off: Path) -> None:
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command(
            "warden_fleet_approve",
            "00000000-0000-0000-0000-000000000001",
            stderr=stderr,
        )
    assert exc.value.code == _EXIT_REFUSED
