"""The local recipes' conda-forge-expert stamps, for the export-purls exceptions (Story 37.8, AD-13)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from kedro.io import AbstractDataset

logger = logging.getLogger(__name__)

COLUMNS = ["dir_name", "conda_name", "status", "upstream_registry", "upstream_name", "parse_error"]


def recipe_extras_row(recipe_path: Path) -> dict[str, Any]:
    """One ``recipes/<dir>/recipe.yaml``'s stamps, as legacy ``export_purls.recipe_exception_lines`` reads them:
    ``extra.cfe-on-conda-forge-status``, the conda name (``extra.cfe-conda-name``, else ``package.name``, else the
    directory), ``extra.cfe-upstream-registry`` and ``extra.cfe-upstream-name``. A file that does not parse is a row
    with ``parse_error`` set and nothing else."""
    dir_name = recipe_path.parent.name
    row: dict[str, Any] = {column: None for column in COLUMNS}
    row.update({"dir_name": dir_name, "parse_error": False})
    try:
        doc = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    except Exception as exc:  # any parse failure: legacy warns and skips
        logger.warning("recipe extras: unparseable %s: %s", recipe_path, exc)
        row["parse_error"] = True
        return row
    if not isinstance(doc, dict):
        return row
    extra = doc.get("extra")
    extra = extra if isinstance(extra, dict) else {}
    package = doc.get("package")
    package = package if isinstance(package, dict) else {}
    row["status"] = str(extra.get("cfe-on-conda-forge-status") or "") or None
    row["conda_name"] = str(extra.get("cfe-conda-name") or package.get("name") or dir_name)
    row["upstream_registry"] = str(extra.get("cfe-upstream-registry") or "") or None
    row["upstream_name"] = str(extra.get("cfe-upstream-name") or "") or None
    return row


class RecipeExtrasDataset(AbstractDataset):
    """Read-only: one row per ``<filepath>/*/recipe.yaml`` (the v1 recipes legacy export-purls scans), in directory
    order. A missing recipes tree gives an empty frame (AD-13)."""

    def __init__(self, *, filepath: str, metadata: dict[str, Any] | None = None) -> None:
        self._filepath = str(filepath)
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        recipes_dir = Path(self._filepath)
        if not recipes_dir.is_dir():
            logger.warning("recipe extras: %s is not a directory", recipes_dir)
            return pd.DataFrame(columns=COLUMNS)
        rows = [recipe_extras_row(path) for path in sorted(recipes_dir.glob("*/recipe.yaml"))]
        frame = pd.DataFrame(rows, columns=COLUMNS)
        frame["parse_error"] = frame["parse_error"].astype("bool")
        return frame

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"filepath": self._filepath}
