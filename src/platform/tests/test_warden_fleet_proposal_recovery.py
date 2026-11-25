"""Warden Story 29.1: a stale approval can be closed, and a failed open says why.

``dismiss_proposal`` refused every state but QUEUED, so a proposal whose one-shot
open task never recorded an outcome stayed APPROVED forever. One whose approval is
older than ``WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS`` may now be dismissed. It may not
be approved again: the open task refuses any approval of a proposal queued longer
than that same setting, so a second approve could never open a pull request.

A whole-run actuator failure (no outcome names the finding) lands on the proposal
with the cause the actuator recorded, not a fixed string.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone
from django_warden_fabric.fleet import FLEET_APPROVAL_EXPIRY_DEFAULT_SECONDS
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
from django_warden_fabric.tasks import open_fix_proposal

_FLAGS_JSON = Path(__file__).resolve().parents[1] / "config" / "flags.json"
_ORG = "fixture-org"
_FINDING = "vuln:PDOS-FIXTURE-0001:pkg-a@1.0.0"
_DELAY = "django_warden_fabric.tasks.open_fix_proposal.delay"
_ONE_HOUR = 60 * 60
_STALE = FLEET_APPROVAL_EXPIRY_DEFAULT_SECONDS + _ONE_HOUR


@pytest.fixture(autouse=True)
def _proposals_flag_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    for key in (FLEET_SCAN_FLAG, FLEET_FIX_PROPOSALS_FLAG):
        tree["flags"][key]["defaultVariant"] = "on"
    path = tmp_path / "flags-on.json"
    path.write_text(json.dumps(tree), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(path))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")


def _approved(*, seconds_ago: float, state: str = FixProposal.State.APPROVED):
    """A proposal approved ``seconds_ago``, whose open task recorded no outcome."""
    run = FleetRun.objects.create(organisation=_ORG)
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/recovery",
        default_branch="main",
        clone_url="file:///unused",
        archived=False,
    )
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json="{}",
    )
    approved_at = timezone.now() - timedelta(seconds=seconds_ago)
    proposal = FixProposal.objects.create(
        fleet_repo_scan=scan,
        finding_id=_FINDING,
        repo_full_name=repo.full_name,
        action="upgrade",
        state=state,
        approved_by="first-operator",
        approved_at=approved_at,
    )
    # A real proposal is queued before it is approved: here, one minute before.
    FixProposal.objects.filter(pk=proposal.pk).update(
        created_at=approved_at - timedelta(seconds=60),
    )
    proposal.refresh_from_db()
    return proposal


@pytest.mark.django_db
def test_stale_approved_proposal_is_still_refused_on_approve(
    django_capture_on_commit_callbacks,
):
    """A stale approval may only be dismissed: a second approve is refused."""
    proposal = _approved(seconds_ago=_STALE)
    first_approval = proposal.approved_at
    with (
        patch(_DELAY) as delay,
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(ProposalRefusedError, match="already approved"),
    ):
        approve_proposal(proposal.pk, "second-operator")
    proposal.refresh_from_db()
    assert proposal.state == FixProposal.State.APPROVED
    assert proposal.approved_by == "first-operator"
    assert proposal.approved_at == first_approval
    delay.assert_not_called()


@pytest.mark.django_db
def test_stale_approved_proposal_can_be_dismissed():
    proposal = _approved(seconds_ago=_STALE)
    with patch(_DELAY) as delay:
        dismiss_proposal(proposal.pk)
    proposal.refresh_from_db()
    assert proposal.state == FixProposal.State.DISMISSED
    delay.assert_not_called()


@pytest.mark.django_db
def test_fresh_approved_proposal_is_still_refused(django_capture_on_commit_callbacks):
    proposal = _approved(seconds_ago=_ONE_HOUR)
    with (
        patch(_DELAY) as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        with pytest.raises(ProposalRefusedError, match="already approved"):
            approve_proposal(proposal.pk, "second-operator")
        with pytest.raises(ProposalRefusedError, match="cannot dismiss"):
            dismiss_proposal(proposal.pk)
    proposal.refresh_from_db()
    assert proposal.state == FixProposal.State.APPROVED
    assert proposal.approved_by == "first-operator"
    delay.assert_not_called()


@pytest.mark.django_db
def test_the_expiry_setting_decides_what_is_stale(settings):
    settings.WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS = 2 * _ONE_HOUR
    fresh = _approved(seconds_ago=_ONE_HOUR)
    with pytest.raises(ProposalRefusedError, match="cannot dismiss"):
        dismiss_proposal(fresh.pk)
    settings.WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS = _ONE_HOUR // 2
    dismiss_proposal(fresh.pk)
    fresh.refresh_from_db()
    assert fresh.state == FixProposal.State.DISMISSED


@pytest.mark.django_db
@pytest.mark.parametrize(
    "state",
    [FixProposal.State.OPENED, FixProposal.State.FAILED, FixProposal.State.DISMISSED],
)
def test_an_old_closed_proposal_stays_closed(state: str):
    """Staleness reopens an approval that recorded no outcome, never a recorded one."""
    proposal = _approved(seconds_ago=_STALE, state=state)
    with patch(_DELAY) as delay:
        with pytest.raises(ProposalRefusedError):
            approve_proposal(proposal.pk, "second-operator")
        with pytest.raises(ProposalRefusedError, match="cannot dismiss"):
            dismiss_proposal(proposal.pk)
    proposal.refresh_from_db()
    assert proposal.state == state
    delay.assert_not_called()


def _open_with_actuation(
    proposal: FixProposal, tmp_path: Path, outcomes: tuple
) -> None:
    """Run the open task with the clone, the re-scan and the actuator stubbed."""
    clone = tmp_path / "clone"
    clone.mkdir(parents=True)
    with (
        patch("django_warden_fabric.tasks.mkdtemp_clone_dir", return_value=clone),
        patch("django_warden_fabric.tasks.shallow_clone", return_value="abc123"),
        patch("django_warden_fabric.tasks._vanished_finding_reason", return_value=None),
        patch(
            "django_warden_fabric.tasks._run_fix_actuator",
            return_value=SimpleNamespace(outcomes=outcomes),
        ),
    ):
        open_fix_proposal(str(proposal.pk))
    proposal.refresh_from_db()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "detail",
    [
        "fix-target resolution failed: OSError: pixi vanished mid-solve",
        "forge resolution failed: ForgeResolutionError: no forge token",
    ],
)
def test_whole_run_actuator_failure_reaches_the_proposal(tmp_path: Path, detail: str):
    """The whole-run record names no finding; its cause is the proposal's error."""
    proposal = _approved(seconds_ago=_ONE_HOUR)
    whole_run = SimpleNamespace(
        finding_id="", status="failed", detail=detail, pr_url=None
    )
    _open_with_actuation(proposal, tmp_path, (whole_run,))
    assert proposal.state == FixProposal.State.FAILED
    assert proposal.error == detail
    assert proposal.pr_url == ""


@pytest.mark.django_db
def test_an_actuation_with_no_record_at_all_keeps_the_fixed_reason(tmp_path: Path):
    """Another finding's outcome is not this proposal's cause."""
    proposal = _approved(seconds_ago=_ONE_HOUR)
    other = SimpleNamespace(
        finding_id="vuln:OTHER:pkg-b@2.0.0",
        status="failed",
        detail="someone else's failure",
        pr_url=None,
    )
    for outcomes in ((), (other,)):
        FixProposal.objects.filter(pk=proposal.pk).update(
            state=FixProposal.State.APPROVED, error=""
        )
        _open_with_actuation(proposal, tmp_path / str(len(outcomes)), outcomes)
        assert proposal.state == FixProposal.State.FAILED
        assert proposal.error == "actuator produced no outcome for finding"
