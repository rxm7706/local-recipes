"""Warden Story 29.1: the proposals page shows a stale approval, with Dismiss only.

``dismiss_proposal`` accepts an APPROVED proposal whose approval is older than
``WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS``, but the page listed QUEUED proposals
only, so the operator never saw the row or its id. The page now lists those stale
approvals too, each with a Dismiss form and no Approve form: a stale approval is
never approved again.
"""

from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus

import pytest
from django.utils import timezone
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_warden_fabric.fleet import FLEET_APPROVAL_EXPIRY_DEFAULT_SECONDS
from django_warden_fabric.models import FixProposal
from django_warden_fabric.models import FleetRepo
from django_warden_fabric.models import FleetRepoScan
from django_warden_fabric.models import FleetRun
from django_warden_fabric.models import JobStatus

PROPOSALS_URL = "/stations/warden/fleet/proposals/"
WARDEN_ROLE = "pyforge:station:warden"
_ORG = "fixture-org"
_ONE_HOUR = 60 * 60
_STALE = FLEET_APPROVAL_EXPIRY_DEFAULT_SECONDS + _ONE_HOUR


def _authed(client, settings):
    claims = {"sub": "op-1", "groups": [WARDEN_ROLE]}
    settings.IDP_CLAIMS_SNAPSHOT = claims
    session = client.session
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = claims
    session.save()
    return client


def _proposal(name: str, state: str, *, approved_seconds_ago: float | None = None):
    """One proposal on its own repo; an approval is dated ``approved_seconds_ago``."""
    run = FleetRun.objects.create(organisation=_ORG)
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/{name}",
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
    approved_at = None
    if approved_seconds_ago is not None:
        approved_at = timezone.now() - timedelta(seconds=approved_seconds_ago)
    return FixProposal.objects.create(
        fleet_repo_scan=scan,
        finding_id=f"vuln:PDOS-FIXTURE-0001:{name}@1.0.0",
        repo_full_name=repo.full_name,
        action="upgrade",
        state=state,
        approved_by="first-operator" if approved_at else "",
        approved_at=approved_at,
    )


def _approve_url(proposal: FixProposal) -> str:
    return f"{PROPOSALS_URL}{proposal.pk}/approve/"


def _dismiss_url(proposal: FixProposal) -> str:
    return f"{PROPOSALS_URL}{proposal.pk}/dismiss/"


@pytest.mark.django_db
def test_proposals_page_lists_a_stale_approval_with_dismiss_only(client, settings):
    queued = _proposal("queued", FixProposal.State.QUEUED)
    stale = _proposal("stale", FixProposal.State.APPROVED, approved_seconds_ago=_STALE)
    fresh = _proposal(
        "fresh", FixProposal.State.APPROVED, approved_seconds_ago=_ONE_HOUR
    )

    response = _authed(client, settings).get(PROPOSALS_URL)

    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert _approve_url(queued) in body
    assert _dismiss_url(queued) in body
    assert stale.repo_full_name in body
    assert _dismiss_url(stale) in body
    assert _approve_url(stale) not in body
    assert fresh.repo_full_name not in body
    assert _dismiss_url(fresh) not in body


@pytest.mark.django_db
def test_proposals_page_lists_no_recorded_outcome_as_stale(client, settings):
    """Staleness is an approval with no outcome, never an old closed proposal."""
    closed = [
        _proposal(f"closed-{index}", state, approved_seconds_ago=_STALE)
        for index, state in enumerate(
            (
                FixProposal.State.OPENED,
                FixProposal.State.FAILED,
                FixProposal.State.DISMISSED,
            ),
        )
    ]

    body = _authed(client, settings).get(PROPOSALS_URL).content.decode()

    for proposal in closed:
        assert proposal.repo_full_name not in body
        assert _dismiss_url(proposal) not in body


@pytest.mark.django_db
def test_the_expiry_setting_decides_what_the_page_lists(client, settings):
    proposal = _proposal(
        "hour-old", FixProposal.State.APPROVED, approved_seconds_ago=_ONE_HOUR
    )
    authed = _authed(client, settings)

    settings.WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS = 2 * _ONE_HOUR
    assert _dismiss_url(proposal) not in authed.get(PROPOSALS_URL).content.decode()

    settings.WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS = _ONE_HOUR // 2
    assert _dismiss_url(proposal) in authed.get(PROPOSALS_URL).content.decode()


@pytest.mark.django_db
def test_a_stale_approval_is_dismissed_through_the_page(client, settings):
    stale = _proposal("stale", FixProposal.State.APPROVED, approved_seconds_ago=_STALE)
    other = _proposal(
        "other-stale", FixProposal.State.APPROVED, approved_seconds_ago=_STALE
    )

    response = _authed(client, settings).post(_dismiss_url(stale))

    assert response.status_code == HTTPStatus.OK
    stale.refresh_from_db()
    assert stale.state == FixProposal.State.DISMISSED
    body = response.content.decode()
    assert _dismiss_url(stale) not in body
    assert _dismiss_url(other) in body
    other.refresh_from_db()
    assert other.state == FixProposal.State.APPROVED


@pytest.mark.django_db
def test_a_fresh_approval_is_still_refused_through_the_page(client, settings):
    fresh = _proposal(
        "fresh", FixProposal.State.APPROVED, approved_seconds_ago=_ONE_HOUR
    )

    response = _authed(client, settings).post(_dismiss_url(fresh))

    assert response.status_code == HTTPStatus.CONFLICT
    fresh.refresh_from_db()
    assert fresh.state == FixProposal.State.APPROVED
