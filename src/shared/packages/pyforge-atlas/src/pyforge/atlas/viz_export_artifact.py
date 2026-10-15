"""Kedro-Viz workflow artifact handoff (Story 30.1, CAP-62)."""

from __future__ import annotations

from pyforge.core.flags import read_boolean

FLAG_KEY = "pyforge.atlas.viz_export_artifact"


def export_artifact_enabled(*, flags_path: str | None = None) -> bool:
    """Whether ``viz-publish-stage`` writes ``manifest.json`` and CI uploads the export."""
    return read_boolean(FLAG_KEY, default=False, flags_path=flags_path)
