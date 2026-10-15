"""The Kedro-Viz mount's build input (herald Story 42.2, spec-pyforge-herald CAP-60).

Atlas's producer (atlas Story 30.1, ``kedro-viz-publish.yml``) uploads the export as the workflow
artifact ``kedro-viz-export``; steward's Pages build downloads the newest one into
``docs/dashboard/kedro-viz/`` (steward Story 102.4), the same gitignored path a local
``pixi run -e pyforge-atlas viz-publish-stage`` stages to. That directory is the one build input of
the mount, read here as data and never edited:

* **present** (the directory holds anything): it must carry ``index.html`` and a ``manifest.json``
  naming ``export_commit`` and ``export_date`` (atlas 30.1's keys; ``kedro_viz_version`` is shown
  when given, extra keys are ignored). It is mounted verbatim at ``/dashboard/kedro-viz/``, the
  ``/kedro-viz/`` redirect is written, and the overview tile and the pipelines page name the commit
  and date the graph was exported from.
* **absent** (no directory, or an empty one): the build carries on with no mount, no redirect, and
  no Kedro-Viz entry in the shared menu or the overview tiles. Skipped, never failed (operator
  ruling 2026-10-13).

``docsite/build.py``, ``assemble_pages.py`` and ``docs-site/scripts/sidebar_from_map.py`` all decide
presence through :func:`is_present`, so the menus, the tiles, the mount and the redirect move together.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

#: Where the export is staged or downloaded, relative to the repository root.
INPUT_REL = "docs/dashboard/kedro-viz"
#: Where it is mounted in the Pages artifact.
MOUNT_REL = "dashboard/kedro-viz"
#: The manifest atlas's ``viz-publish-stage`` writes beside the export's ``index.html``.
MANIFEST_NAME = "manifest.json"
#: The two keys the page names; a manifest without either is refused.
REQUIRED_KEYS = ("export_commit", "export_date")
VERSION_KEY = "kedro_viz_version"
#: A site.yml ``neighbours`` entry carrying ``mount: kedro-viz`` shows only when the export is present.
MOUNT_KEY = "mount"
MOUNT_NAME = "kedro-viz"


class ExportShapeError(ValueError):
    """A present export whose ``index.html`` or ``manifest.json`` is missing or malformed."""


def input_dir(repo_root: Path) -> Path:
    return repo_root / INPUT_REL


def is_present(export_dir: Path) -> bool:
    """True when ``export_dir`` is a directory holding anything; an empty one is an absent export."""
    return export_dir.is_dir() and any(export_dir.iterdir())


def read_manifest(export_dir: Path, *, label: str | None = None) -> dict[str, str]:
    """``{commit, date, version}`` from a present export, or :class:`ExportShapeError` naming the path.

    ``label`` is how the export root is named in the message (default: the path as given)."""
    root = label or str(export_dir)
    if not (export_dir / "index.html").is_file():
        raise ExportShapeError(f"{root}/index.html: missing from the Kedro-Viz export")
    name = f"{root}/{MANIFEST_NAME}"
    path = export_dir / MANIFEST_NAME
    if not path.is_file():
        raise ExportShapeError(f"{name}: missing from the Kedro-Viz export")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportShapeError(f"{name}: not JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise ExportShapeError(f"{name}: not a JSON object")
    for key in REQUIRED_KEYS:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ExportShapeError(f"{name}: lacks {key!r}")
    version = data.get(VERSION_KEY)
    return {
        "commit": data["export_commit"].strip(),
        "date": data["export_date"].strip(),
        "version": version.strip() if isinstance(version, str) else "",
    }


def load(export_dir: Path, *, label: str | None = None) -> dict[str, str] | None:
    """``None`` for an absent export; its manifest for a present one (refusing a malformed one)."""
    if not is_present(export_dir):
        return None
    return read_manifest(export_dir, label=label)


def menu_entries(entries: Iterable[dict[str, Any]], *, present: bool) -> list[dict[str, Any]]:
    """``entries`` without the ones that need the Kedro-Viz mount, when it is absent."""
    return [dict(item) for item in entries if present or item.get(MOUNT_KEY) != MOUNT_NAME]


def neighbours(entries: Iterable[dict[str, Any]] | None, export: dict[str, str] | None) -> list[dict[str, Any]]:
    """site.yml ``neighbours`` for the herald pages: the Kedro-Viz tile only with an export, carrying it."""
    shown = menu_entries(entries or [], present=export is not None)
    for item in shown:
        if item.get(MOUNT_KEY) == MOUNT_NAME:
            item["export"] = export
    return shown
