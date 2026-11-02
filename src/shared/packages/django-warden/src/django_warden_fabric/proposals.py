"""Fleet fix proposal queue (Story 16.3)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone
from pyforge.core.flags import read_boolean

from .fleet import FLEET_FIX_PROPOSALS_FLAG
from .models import FixProposal, FleetRepoScan, JobStatus

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


def _resolved_target_from_outcome(outcome: dict[str, object]) -> str:
    """The dry-run ``fix_resolution`` target (Story 16.6) -- a version, never the package name."""
    resolution = outcome.get("fix_resolution")
    if not isinstance(resolution, dict):
        return ""
    target = resolution.get("target")
    return target if isinstance(target, str) else ""


# Operator ruling 2026-11-01 (Story 16.8): only a finding on a PyPI or conda
# component queues a proposal. Warden names the ecosystem on the outcome of a
# native non-Python lockfile's finding (npm, Go, Cargo, ...); the fleet's edit set
# (pixi.toml, pyproject.toml, recipes) cannot fix one, so it stays in the report only.
_QUEUEABLE_ECOSYSTEMS = frozenset({"pypi", "conda"})


def _is_non_python_outcome(outcome: dict[str, object]) -> bool:
    return "ecosystem" in outcome and outcome["ecosystem"] not in _QUEUEABLE_ECOSYSTEMS


def queue_proposals_from_scan(scan: FleetRepoScan) -> int:
    """Create queued proposals for each planned actuation outcome.

    Story 16.6: the proposal records the dry-run target only; the candidates
    stay in the scan's stored ``report_json`` and no diff is stored -- the
    approve re-solves on a fresh clone (``tasks._run_fix_actuator``).

    Story 16.8: an outcome whose finding is on a non-PyPI, non-conda component
    queues nothing; its finding stays in the stored report."""
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
        if raw.get("status") != "planned" or _is_non_python_outcome(raw):
            continue
        finding_id = raw.get("finding_id")
        action = raw.get("action")
        if not isinstance(finding_id, str) or not isinstance(action, str):
            continue
        target = _resolved_target_from_outcome(raw)
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
