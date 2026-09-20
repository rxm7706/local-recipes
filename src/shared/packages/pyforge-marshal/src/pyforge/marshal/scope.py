"""Active-project scope triangle: ``verify_scope`` + ``ScopeDrift`` (Story 20.6 / FR-190 CAP-1).

never-two-parallel-copies
-------------------------
This module is the **sole** implementation of the marker + both artifact-symlink
vs ``expected_slug`` check. Placement decision (Story 20.6):

* **Home:** ``pyforge.marshal.scope`` (package top-level, **not** ``core/``).
* **Why not ``core/``:** AD-4 forbids I/O under ``core/**``; this primitive does
  three filesystem reads by design.
* **Why import-path (not a Genesis COPIED-MANAGED twin in this repo):** both
  eventual callers live where ``pyforge-marshal`` is importable —
  ``cli/init.py`` already, and ``scripts/bmad-switch`` under the monorepo pixi
  env. One import path; no second check body. The body is **stdlib-only**
  (``dataclasses`` + ``pathlib``) so Genesis *could* later deliver this single
  file as COPIED-MANAGED alongside ``bmad-switch`` without forking logic — but
  that delivery is not a second source here.
* **Story 20.7** wires ``scripts/bmad-switch`` and ``MRS-INIT-003`` to *consume*
  this module and retires the divergent per-caller bodies. This story does not
  replace those guards.

Contract: three reads + string compares; no subprocess; unrecognized symlink
target shapes report the literal ``"unrecognized"`` (never inferred agreement).
The fail-closed token ``UNRECOGNIZED`` is never a successful ``expected_slug``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Fail-closed token for missing / unparseable / foreign-tooling shapes.
# Callers must never treat this as matching ``expected_slug``.
UNRECOGNIZED = "unrecognized"

_MARKER_REL = Path("_bmad") / "custom" / ".active-project"
_DOT_SEGMENTS = frozenset({".", ".."})


@dataclass(frozen=True)
class ScopeDrift:
    """Found-vs-expected disagreement on the active-project triangle.

    Each of ``marker``, ``planning_artifacts``, and ``implementation_artifacts``
    is either a parsed project slug or the literal ``UNRECOGNIZED`` string when
    the corresponding path is missing, not a symlink, or has a target shape
    this parser does not recognize.
    """

    expected: str
    marker: str
    planning_artifacts: str
    implementation_artifacts: str


def _read_marker_slug(root: Path) -> str:
    path = root / _MARKER_REL
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError, UnicodeDecodeError:
        return UNRECOGNIZED
    return text if text else UNRECOGNIZED


def _slug_from_artifact_link(root: Path, name: str) -> str:
    """Parse ``projects/<slug>/<name>`` relative to ``_bmad-output/``.

    Any other shape (missing path, non-symlink, absolute target, wrong depth,
    wrong leaf name, ``.``/``..`` slug) is ``UNRECOGNIZED`` — never ``None`` /
    never inferred agreement (DW-1-4-2 blind spot (1)).
    """
    path = root / "_bmad-output" / name
    try:
        is_link = path.is_symlink()
    except OSError:
        return UNRECOGNIZED
    if not is_link:
        return UNRECOGNIZED
    try:
        target = path.readlink()
    except OSError:
        return UNRECOGNIZED
    parts = target.parts
    if len(parts) == 3 and parts[0] == "projects" and parts[2] == name:
        slug = parts[1]
        if slug and slug not in _DOT_SEGMENTS:
            return slug
    return UNRECOGNIZED


def verify_scope(root: Path, expected_slug: str) -> ScopeDrift | None:
    """Return ``None`` when marker + both artifact symlinks all equal ``expected_slug``.

    Otherwise return a ``ScopeDrift`` naming found-vs-expected for every corner
    of the triangle. A home whose three corners agree with each other on slug B
    but not with ``expected_slug`` ``"A"`` is drift (DW-1-4-2 blind spot (2)).

    ``expected_slug`` equal to the fail-closed token ``UNRECOGNIZED`` never
    counts as agreement — that string is reserved for found-side reporting.
    """
    marker = _read_marker_slug(root)
    planning = _slug_from_artifact_link(root, "planning-artifacts")
    implementation = _slug_from_artifact_link(root, "implementation-artifacts")
    if (
        expected_slug != UNRECOGNIZED
        and marker == expected_slug
        and planning == expected_slug
        and implementation == expected_slug
    ):
        return None
    return ScopeDrift(
        expected=expected_slug,
        marker=marker,
        planning_artifacts=planning,
        implementation_artifacts=implementation,
    )


def format_scope_drift(drift: ScopeDrift) -> str:
    """Human-readable ScopeDrift for stderr / Finding messages."""
    return (
        "scope drift: "
        f"expected {drift.expected!r} but "
        f"marker={drift.marker!r}, "
        f"planning-artifacts={drift.planning_artifacts!r}, "
        f"implementation-artifacts={drift.implementation_artifacts!r}"
    )


__all__ = [
    "UNRECOGNIZED",
    "ScopeDrift",
    "format_scope_drift",
    "verify_scope",
]
