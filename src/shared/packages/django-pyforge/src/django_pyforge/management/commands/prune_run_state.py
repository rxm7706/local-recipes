"""Run the ``run_state`` retention sweep once, now (Story 42.2).

The same work ``prune_run_state_task`` does on the beat schedule, reachable
without a scheduler: no ``celery beat`` process is deployed by the chart today
(Story 42.4 owns Celery's deployment topology), and a retention policy nothing
can run is not a retention policy. Also the operator's lever after an incident,
when waiting an hour for the next tick is not an option.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand

from django_pyforge.supervisor import prune_run_state


class Command(BaseCommand):
    help = "Prune terminal run_state rows past retention and cap the table."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="emit the report as JSON",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        report = prune_run_state()
        if options.get("as_json"):
            self.stdout.write(json.dumps(report))
            return
        self.stdout.write(
            f"pruned {report['aged_out']} aged + {report['over_cap']} over-cap "
            f"run(s) and {report['expired_handles']} expired handle(s); "
            f"{report['remaining']} remaining (cap {report['max_rows']})",
        )
        if report["truncated"]:
            # Never let a bounded sweep read as "the table is now in policy".
            self.stdout.write(
                f"batch limit {report['batch_limit']} reached — work remains; "
                f"run again (or wait for the next scheduled sweep)",
            )
