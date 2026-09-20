"""``marshal seed explain`` verb logic (Story 11.6, FR-127).

Read-only lookup of one manifest entry by stable artifact id or repo path.
Renders the entry's class, manifest rationale, class update/hand-edit
behavior (via ``model.artifact.describe`` when the class has a contract),
and hybrid region names with anchors. Unknown queries raise ``UsageError``
with near-match suggestions on artifact ids.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any

from ..model.artifact import describe
from ..model.manifest import ArtifactClass, Manifest, ManifestEntry


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def _entry_by_id(manifest: Manifest, artifact_id: str) -> ManifestEntry | None:
    for entry in manifest.entries:
        if entry.id == artifact_id:
            return entry
    return None


def _entry_by_path(manifest: Manifest, query: str) -> ManifestEntry | None:
    normalized = _normalize_path(query)
    for entry in manifest.entries:
        if entry.path == query or _normalize_path(entry.path) == normalized:
            return entry
    return None


def _near_match_ids(manifest: Manifest, query: str, *, limit: int = 5) -> tuple[str, ...]:
    candidates = [entry.id for entry in manifest.entries]
    matches = difflib.get_close_matches(query, candidates, n=limit, cutoff=0.4)
    return tuple(matches)


def resolve_entry(manifest: Manifest, query: str) -> ManifestEntry:
    """Resolve ``query`` to a manifest entry by id or path.

    Raises ``UsageError`` when no entry matches, listing near ids when any
    exist.
    """
    from ..errors import UsageError

    entry = _entry_by_id(manifest, query)
    if entry is None:
        entry = _entry_by_path(manifest, query)
    if entry is not None:
        return entry

    near = _near_match_ids(manifest, query)
    if near:
        suggestion = f" Near matches: {', '.join(near)}."
    else:
        suggestion = ""
    raise UsageError(
        f"unknown artifact {query!r} — not an id or path in the bundled manifest.{suggestion}",
        remedy="pass a manifest artifact id (e.g. agents-md) or its repo path (e.g. AGENTS.md)",
    )


@dataclass(frozen=True)
class ExplainReport:
    """One artifact's explain payload — text and ``--json`` share this shape."""

    artifact_id: str
    path: str
    artifact_class: str
    rationale: str
    update_behavior: str | None
    hand_edit_behavior: str | None
    regions: tuple[dict[str, Any], ...]

    def to_json_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "class": self.artifact_class,
            "rationale": self.rationale,
            "update_behavior": self.update_behavior,
            "hand_edit_behavior": self.hand_edit_behavior,
        }
        if self.regions:
            payload["regions"] = list(self.regions)
        return payload


def _regions_payload(entry: ManifestEntry) -> tuple[dict[str, Any], ...]:
    if entry.artifact_class is not ArtifactClass.HYBRID_MANAGED_REGION:
        return ()
    return tuple({"name": region.name, "anchor": list(region.anchor)} for region in entry.regions)


def run_explain(manifest: Manifest, query: str) -> ExplainReport:
    """Pure read-only explain for one artifact id or path."""
    entry = resolve_entry(manifest, query)

    update_behavior: str | None
    hand_edit_behavior: str | None
    if entry.artifact_class is ArtifactClass.UNCLASSIFIED_DEFERRED:
        update_behavior = None
        hand_edit_behavior = None
    else:
        artifact = describe(entry)
        update_behavior = artifact.behavior.update_behavior
        hand_edit_behavior = artifact.behavior.hand_edit_behavior

    return ExplainReport(
        artifact_id=entry.id,
        path=entry.path,
        artifact_class=entry.artifact_class.value,
        rationale=entry.rationale,
        update_behavior=update_behavior,
        hand_edit_behavior=hand_edit_behavior,
        regions=_regions_payload(entry),
    )


def render_explain_text(report: ExplainReport) -> str:
    lines = [
        f"marshal seed explain -- {report.artifact_id} ({report.path})",
        f"class: {report.artifact_class}",
        f"rationale: {report.rationale}",
    ]
    if report.update_behavior is not None:
        lines.append(f"update: {report.update_behavior}")
        lines.append(f"hand-edit: {report.hand_edit_behavior}")
    else:
        lines.append("update: (no class contract — unclassified-deferred)")
    if report.regions:
        lines.append("regions:")
        for region in report.regions:
            anchor = ", ".join(region["anchor"])
            lines.append(f"  {region['name']}: anchor {anchor}")
    return "\n".join(lines)
