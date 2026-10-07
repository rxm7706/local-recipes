"""Upsert ``DeckExport`` from ``herald deck exports --json`` (CAP-54 D3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django_pyforge.assertion.client import PortalClient
from django_pyforge.flags import evaluate_boolean
from django_pyforge.roles import prefixed_station

from django_herald_portal.deck_export_sync import sync_slug_exports
from django_herald_portal.portal_runner import InvokeRunner
from django_herald_portal.portal_runner import deck_exports_json_runner
DECK_PUBLISH_FLAG = "pyforge.herald.deck_publish"

_REFRESH_SUB = "deck-export-refresh"
_REFRESH_ROLES = [prefixed_station("herald")]


def _presentation_slugs(root: Path) -> list[str]:
    presentations = root / "presentations"
    if not presentations.is_dir():
        return []
    return sorted(
        path.name
        for path in presentations.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


class Command(BaseCommand):
    help = "Refresh the DeckExport projection from herald deck exports --json."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--slug",
            action="append",
            dest="slugs",
            help="Refresh one deck slug (repeatable). Default: every presentations/ child.",
        )
        parser.add_argument(
            "--repo-root",
            type=Path,
            default=Path.cwd(),
            help="Repo root whose presentations/ directory names deck slugs.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not evaluate_boolean(DECK_PUBLISH_FLAG, default=False):
            self.stdout.write("deck publish flag is off; wrote nothing")
            return
        slugs: list[str] = options.get("slugs") or _presentation_slugs(options["repo_root"])
        if not slugs:
            self.stdout.write("no deck slugs to refresh")
            return
        runner: InvokeRunner = deck_exports_json_runner
        client = PortalClient()
        total = 0
        for slug in slugs:
            argv = ["deck", "exports", slug, "--json"]
            result = client.invoke(
                _REFRESH_SUB,
                _REFRESH_ROLES,
                "herald",
                argv,
                runner=runner,
            )
            total += sync_slug_exports(slug, result["stdout"])
        self.stdout.write(f"refreshed {total} export row(s) across {len(slugs)} deck(s)")
