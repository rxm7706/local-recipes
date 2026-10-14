"""Approve one queued fleet fix proposal (Story 16.3)."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from pyforge.core.flags import FlagOff, disabled_help, require

from django_warden_fabric.fleet import FLEET_FIX_PROPOSALS_FLAG
from django_warden_fabric.proposals import ProposalRefusedError, approve_proposal


class Command(BaseCommand):
    help = disabled_help(
        "Approve one queued fleet fix proposal so it opens as a draft PR",
        FLEET_FIX_PROPOSALS_FLAG,
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("proposal_id", help="FixProposal UUID")
        parser.add_argument(
            "--operator",
            default="cli",
            help="Operator identity recorded on the approval",
        )

    def handle(self, *args, **options) -> None:
        try:
            require(FLEET_FIX_PROPOSALS_FLAG)
        except FlagOff as exc:
            self.stderr.write(f"{exc}\n")
            raise SystemExit(2) from exc
        proposal_id = options["proposal_id"]
        operator = options["operator"]
        try:
            proposal = approve_proposal(proposal_id, operator)
        except ProposalRefusedError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(str(proposal.pk))
