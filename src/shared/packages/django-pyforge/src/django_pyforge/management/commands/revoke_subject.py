"""Revoke one runaway subject: its queued tasks and its live runs.

The Django side of ``pyforge steward revoke --sub <id>`` (Story 42.2, red-team
A-6). Steward owns the operator grammar; the write lives here because
``run_state`` has one writer (AD-12) and the steward package neither imports
Django nor may reach into the host's models.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from django_pyforge.supervisor import revoke_subject


class Command(BaseCommand):
    help = "Revoke a subject's queued Celery tasks and cancel its live runs."
    # Injectable Celery control face, mirroring `list_event_dlq`'s `client`:
    # a test drives the real command instead of a re-implementation of it.
    stealth_options = ("control",)

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--sub",
            required=True,
            help="the assertion `sub` claim whose runs are revoked",
        )
        parser.add_argument(
            "--reason",
            default="revoked by operator",
            help="recorded on each cancelled run",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="emit the report as JSON",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            report = revoke_subject(
                options["sub"],
                control=options.get("control"),
                reason=options["reason"],
            )
        except ValueError as exc:
            # The guard lives in the writer; this only projects it to argv.
            raise CommandError(str(exc)) from exc
        if options.get("as_json"):
            self.stdout.write(json.dumps(report))
            return
        self.stdout.write(
            f"{report['subject']}: cancelled {report['cancelled_runs']} run(s), "
            f"revoked {len(report['revoked_tasks'])} task(s)",
        )
        if report["revoke_error"]:
            self.stderr.write(f"revoke error: {report['revoke_error']}")
