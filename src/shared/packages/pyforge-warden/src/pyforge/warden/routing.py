"""FR2 routing seam — per-section ecosystem classification (Story 1.2,
extended 2.6).

1.2 shipped exactly one (manifest-kind, section) pair — ``pyproject.toml``
/ ``[project].dependencies`` — routing to ``Ecosystem.PYPI``. Story 2.6
adds 4 synthetic pairs for the two lockfile kinds (a lockfile's rows are
ecosystem-mixed per file, so the extractor cannot assign ``Ecosystem``
directly — every extractor calls this seam). Unknown pairs raise
``ValueError`` (fail-loud; the typed exception net arrives with Story 1.7).
The kind/section tokens are imported from their owning modules (single
definition sites), never re-spelled here.

This module is pure classification: no I/O, no subprocess, no network.
"""

from __future__ import annotations

from .discovery import CONDA_LOCK_KIND, PIXI_LOCK_KIND, PYPROJECT_KIND
from .extract.lockfiles import (
    CONDA_LOCK_CONDA_SECTION,
    CONDA_LOCK_PYPI_SECTION,
    PIXI_LOCK_CONDA_SECTION,
    PIXI_LOCK_PYPI_SECTION,
)
from .extract.pyproject import PROJECT_DEPENDENCIES_SECTION
from .models import Ecosystem

# (manifest_kind, section) -> Ecosystem, the whole classification table.
_ROUTES: dict[tuple[str, str], Ecosystem] = {
    (PYPROJECT_KIND, PROJECT_DEPENDENCIES_SECTION): Ecosystem.PYPI,
    (PIXI_LOCK_KIND, PIXI_LOCK_CONDA_SECTION): Ecosystem.CONDA,
    (PIXI_LOCK_KIND, PIXI_LOCK_PYPI_SECTION): Ecosystem.PYPI,
    (CONDA_LOCK_KIND, CONDA_LOCK_CONDA_SECTION): Ecosystem.CONDA,
    (CONDA_LOCK_KIND, CONDA_LOCK_PYPI_SECTION): Ecosystem.PYPI,
}


class DefaultRouter:
    """The default ``Router`` implementation (structural: see
    ``interfaces.Router``)."""

    def route(self, manifest_kind: str, section: str) -> Ecosystem:
        ecosystem = _ROUTES.get((manifest_kind, section))
        if ecosystem is None:
            raise ValueError(
                f"no ecosystem route for manifest kind {manifest_kind!r}, "
                f"section {section!r}"
            )
        return ecosystem
