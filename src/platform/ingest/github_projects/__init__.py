"""GitHub Projects V2 → `github_metrics` dlt ingest (Story 12.8, CAP-5).

Read-only ingestion kin to `spec-jira-github-projects-sync` Mode B — never a
second sync engine. Reuses `pyforge.steward.sync`'s GraphQL transport patterns.
"""

from .pipeline import main, run_pipeline
from .source import github_projects_source

__all__ = ["github_projects_source", "main", "run_pipeline"]
