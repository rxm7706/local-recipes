"""VCS + registry raw-source datasets (Story B1 gap closure).

GraphQL POST (GitHub) and bare ``api.APIDataset`` entries return ``Response``
objects — seed from post-bootstrap ``cf_atlas.db`` when present; otherwise return
empty node-ready frames so ``vcs_health`` nodes degrade gracefully.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset


def _cf_atlas_db_path() -> Path:
    for key in ("CF_ATLAS_DB", "CF_ATLAS_DB_PATH"):
        raw = os.environ.get(key)
        if raw:
            return Path(raw).expanduser()
    return Path(".claude/data/conda-forge-expert/cf_atlas.db")


def seed_github_from_cf_atlas(db_path: Path | None = None) -> pd.DataFrame:
    """Phase E.5 / K / N GitHub slice from legacy bootstrap ``packages`` rows."""
    path = db_path if db_path is not None else _cf_atlas_db_path()
    cols = [
        "feedstock_name",
        "archived",
        "conda_name",
        "upstream_version",
        "last_error",
        "stars",
        "last_commit",
        "open_issues",
    ]
    if not path.is_file():
        return pd.DataFrame(columns=cols)
    sql = """
        SELECT
          feedstock_name,
          feedstock_archived AS archived,
          conda_name,
          github_current_version AS upstream_version,
          github_version_last_error AS last_error,
          gh_open_issues_count AS open_issues
        FROM packages
        WHERE feedstock_name IS NOT NULL
    """
    with sqlite3.connect(path) as conn:
        df = pd.read_sql_query(sql, conn)
    if df.empty:
        return pd.DataFrame(columns=cols)
    df["stars"] = pd.NA
    df["last_commit"] = pd.NA
    if "archived" in df.columns:
        df["archived"] = df["archived"].fillna(0).astype(bool)
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df[cols].drop_duplicates().reset_index(drop=True)


def seed_vcs_host_from_cf_atlas(host: str, db_path: Path | None = None) -> pd.DataFrame:
    """Phase K GitLab / Codeberg rows from ``upstream_versions``."""
    path = db_path if db_path is not None else _cf_atlas_db_path()
    cols = ["conda_name", "upstream_version", "last_error"]
    if not path.is_file():
        return pd.DataFrame(columns=cols)
    sql = """
        SELECT conda_name, version AS upstream_version, last_error
        FROM upstream_versions
        WHERE source = ?
    """
    with sqlite3.connect(path) as conn:
        df = pd.read_sql_query(sql, conn, params=(host,))
    if df.empty:
        return pd.DataFrame(columns=cols)
    return df[cols].drop_duplicates().reset_index(drop=True)


def seed_registry_from_cf_atlas(registry: str, db_path: Path | None = None) -> pd.DataFrame:
    """Phase L registry row from ``upstream_versions`` (when bootstrap populated it)."""
    path = db_path if db_path is not None else _cf_atlas_db_path()
    cols = ["conda_name", "upstream_version"]
    if not path.is_file():
        return pd.DataFrame(columns=cols)
    sql = """
        SELECT conda_name, version AS upstream_version
        FROM upstream_versions
        WHERE source = ?
    """
    with sqlite3.connect(path) as conn:
        df = pd.read_sql_query(sql, conn, params=(registry,))
    if df.empty:
        return pd.DataFrame(columns=cols)
    return df[cols].drop_duplicates().reset_index(drop=True)


class VcsHostSeedDataset(AbstractDataset):
    """GitLab or Codeberg upstream-version seed (``vcs_gitlab_api_raw`` / ``vcs_codeberg_api_raw``)."""

    def __init__(
        self,
        *,
        url: str,
        host: str,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        _ = (url, kwargs)
        self._host = host
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        return seed_vcs_host_from_cf_atlas(self._host)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"parameterization": type(self).__name__, "host": self._host}


class RegistryUpstreamDataset(AbstractDataset):
    """Cross-ecosystem registry seed (Phase L ``vcs_registry_*_raw`` entries)."""

    def __init__(
        self,
        *,
        url: str,
        registry: str,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        _ = (url, kwargs)
        self._registry = registry
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        return seed_registry_from_cf_atlas(self._registry)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"parameterization": type(self).__name__, "registry": self._registry}
