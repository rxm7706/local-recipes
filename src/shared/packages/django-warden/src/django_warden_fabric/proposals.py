"""Fleet fix proposal queue (Story 16.3)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone
from pyforge.core.flags import read_boolean

from .fleet import FLEET_FIX_PROPOSALS_FLAG
from .models import FixProposal
from .models import FleetRepoScan
from .models import JobStatus
if TYPE_CHECKING:
    from uuid import UUID


class ProposalRefusedError(Exception):
    """Operator action refused (wrong state or flag off)."""


def _planned_paths_from_outcome(outcome: dict[str, object]) -> list[str]:
    manifest_fix = outcome.get("manifest_fix")
    if not isinstance(manifest_fix, dict):
        return []
    files = manifest_fix.get("files")
    if not isinstance(files, list):
        return []
    paths: list[str] = []
    for entry in files:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            paths.append(entry["path"])
    return sorted(paths)


def queue_proposals_from_scan(scan: FleetRepoScan) -> int:
    """Create queued proposals for each planned actuation outcome."""
    if not read_boolean(FLEET_FIX_PROPOSALS_FLAG, default=False):
        return 0
    if scan.status != JobStatus.SUCCEEDED:
        return 0
    try:
        document = json.loads(scan.report_json or "{}")
    except json.JSONDecodeError:
        return 0
    actuation = document.get("actuation")
    if not isinstance(actuation, dict):
        return 0
    outcomes = actuation.get("outcomes")
    if not isinstance(outcomes, list):
        return 0
    repo_name = scan.fleet_repo.full_name
    created = 0
    for raw in outcomes:
        if not isinstance(raw, dict):
            continue
        if raw.get("status") != "planned":
            continue
        finding_id = raw.get("finding_id")
        action = raw.get("action")
        if not isinstance(finding_id, str) or not isinstance(action, str):
            continue
        subject = raw.get("subject")
        target = subject if isinstance(subject, str) else ""
        paths = _planned_paths_from_outcome(raw)
        _, was_created = FixProposal.objects.get_or_create(
            fleet_repo_scan=scan,
            finding_id=finding_id,
            defaults={
                "repo_full_name": repo_name,
                "action": action,
                "target": target,
                "planned_paths_json": json.dumps(paths),
                "state": FixProposal.State.QUEUED,
            },
        )
        if was_created:
            created += 1
    return created


@transaction.atomic
def approve_proposal(proposal_id: UUID | str, operator: str) -> FixProposal:
    """Mark approved and enqueue the one-shot open task."""
    if not read_boolean(FLEET_FIX_PROPOSALS_FLAG, default=False):
        msg = "fleet fix proposals flag is off"
        raise ProposalRefusedError(msg)
    try:
        proposal = FixProposal.objects.select_for_update().get(pk=proposal_id)
    except FixProposal.DoesNotExist as exc:
        msg = "proposal not found"
        raise ProposalRefusedError(msg) from exc
    if proposal.state == FixProposal.State.OPENED:
        msg = "proposal already opened"
        raise ProposalRefusedError(msg)
    if proposal.state in (
        FixProposal.State.APPROVED,
        FixProposal.State.FAILED,
        FixProposal.State.DISMISSED,
    ):
        msg = f"proposal already {proposal.state}"
        raise ProposalRefusedError(msg)
    proposal.state = FixProposal.State.APPROVED
    proposal.approved_by = operator
    proposal.approved_at = timezone.now()
    proposal.save(update_fields=["state", "approved_by", "approved_at", "updated_at"])
    proposal_pk = str(proposal.pk)
    from .tasks import open_fix_proposal  # noqa: PLC0415 — keys-not-blobs enqueue

    transaction.on_commit(lambda: open_fix_proposal.delay(proposal_pk))
    return proposal


@transaction.atomic
def dismiss_proposal(proposal_id: UUID | str) -> FixProposal:
    """Close a queued proposal without a forge call."""
    try:
        proposal = FixProposal.objects.select_for_update().get(pk=proposal_id)
    except FixProposal.DoesNotExist as exc:
        msg = "proposal not found"
        raise ProposalRefusedError(msg) from exc
    if proposal.state != FixProposal.State.QUEUED:
        msg = f"cannot dismiss proposal in state {proposal.state}"
        raise ProposalRefusedError(msg)
    proposal.state = FixProposal.State.DISMISSED
    proposal.save(update_fields=["state", "updated_at"])
    return proposal
