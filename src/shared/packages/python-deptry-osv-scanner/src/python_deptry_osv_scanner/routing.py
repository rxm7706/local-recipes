"""FR2 routing seam — per-section ecosystem classification (Story 1.2).

Trivial by design in 1.2: exactly one (manifest-kind, section) pair exists —
``pyproject.toml`` / ``[project].dependencies`` — and it routes to
``Ecosystem.PYPI``. Unknown pairs raise ``ValueError`` (fail-loud; the typed
exception net arrives with Story 1.7). The kind/section tokens are imported
from their owning modules (single definition sites), never re-spelled here.

This module is pure classification: no I/O, no subprocess, no network.
"""

from __future__ import annotations

from .discovery import PYPROJECT_KIND
from .extract.pyproject import PROJECT_DEPENDENCIES_SECTION
from .models import Ecosystem


class DefaultRouter:
    """The default ``Router`` implementation (structural: see
    ``interfaces.Router``)."""

    def route(self, manifest_kind: str, section: str) -> Ecosystem:
        if (
            manifest_kind == PYPROJECT_KIND
            and section == PROJECT_DEPENDENCIES_SECTION
        ):
            return Ecosystem.PYPI
        raise ValueError(
            f"no ecosystem route for manifest kind {manifest_kind!r}, "
            f"section {section!r}"
        )
