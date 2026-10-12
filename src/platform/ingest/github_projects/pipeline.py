"""Run the GitHub Projects V2 → Postgres `github_metrics` dlt pipeline."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Callable

import dlt
from pyforge.steward.keys import HostScopedCredential
from pyforge.steward.sync import TransportFn, _default_transport

from .graphql import DEFAULT_PAGE_SIZE, ProjectSnapshotPage
from .source import github_projects_source


def _credential_from_env() -> HostScopedCredential:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")
    if not token or not token.strip():
        raise SystemExit(
            "GITHUB_TOKEN (classic PAT with read:project) is required — "
            "fine-grained PATs cannot reach user-owned projects"
        )
    os.environ.setdefault("GITHUB_TOKEN", token.strip())
    return HostScopedCredential(hosts=("api.github.com",))


def run_pipeline(
    project_id: str,
    *,
    postgres_url: str | None = None,
    credential: HostScopedCredential | None = None,
    transport: TransportFn | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
    dry_run: bool = False,
    on_page: Callable[[ProjectSnapshotPage, int], None] | None = None,
) -> dlt.pipeline.Pipeline:
    """Load Projects V2 data into the `github_metrics` dataset."""
    credential = credential or _credential_from_env()
    transport = transport or _default_transport

    source = github_projects_source(
        project_id,
        credential=credential,
        transport=transport,
        page_size=page_size,
        max_pages=max_pages,
        on_page=on_page,
    )

    if dry_run:
        pipeline = dlt.pipeline(
            pipeline_name="github_projects_metrics",
            destination="duckdb",
            dataset_name="github_metrics",
            dev_mode=True,
        )
        pipeline.run(source)
        return pipeline

    destination_url = postgres_url or os.environ.get("GITHUB_METRICS_DATABASE_URL")
    if not destination_url:
        raise SystemExit(
            "GITHUB_METRICS_DATABASE_URL (postgresql://…) is required unless --dry-run"
        )

    pipeline = dlt.pipeline(
        pipeline_name="github_projects_metrics",
        destination=dlt.destinations.postgres(destination_url),
        dataset_name="github_metrics",
    )
    pipeline.run(source)
    return pipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Load GitHub Projects V2 board data into github_metrics via dlt",
    )
    parser.add_argument("project_id", help="GitHub ProjectV2 node ID (PVT_…)")
    parser.add_argument(
        "--postgres-url",
        default=os.environ.get("GITHUB_METRICS_DATABASE_URL"),
        help="postgresql:// URL (cluster Postgres via port-forward)",
    )
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Cap pagination for dry-runs / budget testing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract + normalize only; no Postgres write",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.page_size < 1 or args.page_size > DEFAULT_PAGE_SIZE:
        print(f"--page-size must be 1..{DEFAULT_PAGE_SIZE}", file=sys.stderr)
        return 2
    run_pipeline(
        args.project_id,
        postgres_url=args.postgres_url,
        page_size=args.page_size,
        max_pages=args.max_pages,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
