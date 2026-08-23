"""``marshal seed version`` verb logic (Story 11.6, FR-125).

Read-only report of the CLI (package) version, the bundled manifest
``model_version``, and the adopted repo's recorded ``model_version`` when
state is present and readable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import StateInvalid
from ..model.manifest import Manifest
from ..state import read_state, seed_model_version


@dataclass(frozen=True)
class VersionReport:
    """Three-clock version snapshot for text and ``--json`` output."""

    cli_version: str
    bundled_model_version: str
    adopted_model_version: str | None

    def to_json_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "cli_version": self.cli_version,
            "bundled_model_version": self.bundled_model_version,
        }
        if self.adopted_model_version is not None:
            payload["adopted_model_version"] = self.adopted_model_version
        return payload


def run_version(manifest: Manifest, repo_root: Path | None = None) -> VersionReport:
    """Pure read-only version report.

    ``repo_root`` defaults to the current working directory when supplied
    as ``None`` by the CLI layer.
    """
    root = repo_root if repo_root is not None else Path.cwd()
    adopted: str | None = None
    try:
        state = read_state(root)
    except StateInvalid:
        state = None
    if state is not None:
        adopted = str(state.model_version)

    return VersionReport(
        cli_version=seed_model_version(),
        bundled_model_version=str(manifest.model_version),
        adopted_model_version=adopted,
    )


def render_version_text(report: VersionReport) -> str:
    lines = [
        "marshal seed version",
        f"cli_version: {report.cli_version}",
        f"bundled_model_version: {report.bundled_model_version}",
    ]
    if report.adopted_model_version is not None:
        lines.append(f"adopted_model_version: {report.adopted_model_version}")
    else:
        lines.append("adopted_model_version: (not adopted or unreadable state)")
    return "\n".join(lines)
