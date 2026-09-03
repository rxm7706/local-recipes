"""Run the worker-lost sweep once, now (Story 42.4 / BS-8 partial).

The same work ``sweep_lost_runs_task`` does on the beat schedule, reachable
without waiting for the next tick -- the operator's lever after a node loss,
when a board full of ``RUNNING`` rows whose workers are gone is the incident.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand

from django_pyforge.supervisor import sweep_lost_runs


class Command(BaseCommand):
    help = "Mark live run_state rows whose task no worker holds FAILED (worker_lost)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="emit the report as JSON",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        report = sweep_lost_runs()
        if options.get("as_json"):
            self.stdout.write(json.dumps(report))
            return
        self.stdout.write(
            f"swept {report['swept']} of {report['stale']} stale run(s) as worker_lost "
            f"({report['still_held']} still held by a worker; {report['live']} live)",
        )
        if not report["inspected"] and report["stale"]:
            # Never let "nothing swept" read as "nothing was lost".
            self.stdout.write(
                f"workers could not be inspected ({report.get('error', 'no broker')}); "
                f"{report['stale']} stale run(s) left untouched -- run again",
            )
