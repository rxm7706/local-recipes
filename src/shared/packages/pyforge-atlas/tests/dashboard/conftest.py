"""Fixtures for the `dashboard-dryrun` gate (Story D2).

Offline by construction: fixture Parquet written to tmp dirs (round-tripped through DuckDB,
mirroring the D1 semantic conftest) + hand-authored BMAD artifacts. The network is never
touched and no Vizro server is ever launched — the gate builds the Dashboard OBJECT and
exercises the (lazy) data functions directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

MEMBER_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = MEMBER_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

NOW = 1_700_000_000


@pytest.fixture()
def write_parquet(tmp_path):
    """Write a pandas frame to a Parquet file and return its path (str)."""
    counter = {"n": 0}

    def _make(df: pd.DataFrame, name: str) -> str:
        counter["n"] += 1
        path = tmp_path / f"{name}_{counter['n']}.parquet"
        df.to_parquet(path)
        return str(path)

    return _make


@pytest.fixture()
def feedstock_health_parquet(write_parquet) -> str:
    return write_parquet(
        pd.DataFrame(
            {
                "feedstock_name": ["alpha", "beta", "gamma"],
                "ci_status": ["failure", "success", "error"],
                "open_prs": pd.array([0, 3, 1], dtype="Int64"),
                "open_issues": pd.array([2, 0, 0], dtype="Int64"),
            }
        ),
        "core_feedstock_health",
    )


@pytest.fixture()
def package_maintainers_parquet(write_parquet) -> str:
    return write_parquet(
        pd.DataFrame(
            {
                "conda_name": ["a", "a", "b", "c"],
                "maintainer": ["alice", "bob", "alice", "carol"],
            }
        ),
        "vcs_package_maintainers",
    )


@pytest.fixture()
def packages_parquet(write_parquet) -> str:
    """The composed per-package frame build_packages_model binds to (the store gap the
    bsl-shell pages light up on once it lands)."""
    return write_parquet(
        pd.DataFrame(
            {
                "conda_name": ["a", "b", "c"],
                "latest_status": ["active", "active", "inactive"],
                "feedstock_archived": pd.array([0, 0, 0], dtype="Int64"),
                "latest_conda_upload": pd.array([NOW - 86400, NOW - 8 * 86400, NOW], dtype="Int64"),
                "downloads_total": pd.array([100, 200, 300], dtype="Int64"),
                "downloads_30d": pd.array([1, 2, 3], dtype="Int64"),
                "latest_upload_age_days": pd.array([1, 8, 0], dtype="Int64"),
                "releases_30d": pd.array([0, 1, 0], dtype="Int64"),
                "total_versions": pd.array([2, 5, 1], dtype="Int64"),
            }
        ),
        "semantic_packages",
    )


@pytest.fixture()
def bmad_fixture(tmp_path) -> dict:
    """A minimal, well-formed BMAD artifact set for the factory-status page."""
    sprint = tmp_path / "sprint-status.yaml"
    sprint.write_text(
        "development_status:\n"
        "  epic-5: in-progress\n"
        "  d1-define-the-boring-semantic-layer-bsl-models: done\n"
        "  d2-build-the-vizro-dashboard-port-the-28-clis-to-pages: in-progress\n",
        encoding="utf-8",
    )
    epics = tmp_path / "epics.md"
    epics.write_text("---\nstatus: final\n---\n\n# Epics\n", encoding="utf-8")
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "one.md").write_text("---\nstatus: ready\n---\n# One\n", encoding="utf-8")
    (specs / "two.md").write_text("---\nstatus: shipped\n---\n# Two\n", encoding="utf-8")
    (specs / "no-fm.md").write_text("# No frontmatter here\n", encoding="utf-8")
    return {"sprint": str(sprint), "epics": str(epics), "specs": str(specs)}
