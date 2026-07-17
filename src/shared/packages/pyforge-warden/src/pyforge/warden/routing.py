"""FR2 routing seam — per-section ecosystem classification (Story 1.2,
extended 2.6, 2.2, 1.9).

1.2 shipped exactly one (manifest-kind, section) pair — ``pyproject.toml``
/ ``[project].dependencies`` — routing to ``Ecosystem.PYPI``. Story 2.6
adds 4 synthetic pairs for the two lockfile kinds (a lockfile's rows are
ecosystem-mixed per file, so the extractor cannot assign ``Ecosystem``
directly — every extractor calls this seam). Story 2.2 adds 10 more pairs
for the 4 conda/pixi source-manifest kinds: 1 each for recipe.yaml/
meta.yaml (single-ecosystem formats — conda, regardless of WHICH
requirements section a dep came from), 2 for environment.yml (conda
dependencies + the nested pip: list), and 6 GENERIC tokens for pixi.toml
(base + feature/target dependencies/pypi-dependencies — the feature/target
NAME is never baked into these routing keys, only into
``Provenance.section``). Story 1.9 adds 2 more pairs mirroring
environment.yml's, one per section, for the ``environment.yaml`` spelling
(a first-class discovered kind sharing ``EnvironmentYmlExtractor``).
Unknown pairs raise ``ValueError`` (fail-loud; already caught at
``cli.py``'s extract-stage seam — the ``except (SystemExit, Exception)``
handler around ``extractor.extract(...)`` — and converted to a typed
``internal-error`` record with the report still emitted, ratified by
Story 1.7). The kind/section tokens are imported from their owning modules
(single definition sites), never re-spelled here.

This module is pure classification: no I/O, no subprocess, no network.
"""

from __future__ import annotations

from .discovery import (
    CONDA_LOCK_KIND,
    ENVIRONMENT_YAML_KIND,
    ENVIRONMENT_YML_KIND,
    META_YAML_KIND,
    PIXI_LOCK_KIND,
    PIXI_TOML_KIND,
    PYPROJECT_KIND,
    RECIPE_YAML_KIND,
)
from .extract.environment_yml import (
    ENVIRONMENT_YML_DEPENDENCIES_SECTION,
    ENVIRONMENT_YML_PIP_SECTION,
)
from .extract.lockfiles import (
    CONDA_LOCK_CONDA_SECTION,
    CONDA_LOCK_PYPI_SECTION,
    PIXI_LOCK_CONDA_SECTION,
    PIXI_LOCK_PYPI_SECTION,
)
from .extract.meta_v0 import META_V0_REQUIREMENTS_SECTION
from .extract.pixi import (
    BASE_DEPENDENCIES_SECTION,
    BASE_PYPI_DEPENDENCIES_SECTION,
    FEATURE_DEPENDENCIES_SECTION,
    FEATURE_PYPI_DEPENDENCIES_SECTION,
    TARGET_DEPENDENCIES_SECTION,
    TARGET_PYPI_DEPENDENCIES_SECTION,
)
from .extract.pyproject import PROJECT_DEPENDENCIES_SECTION
from .extract.recipe_v1 import RECIPE_V1_REQUIREMENTS_SECTION
from .models import Ecosystem

# (manifest_kind, section) -> Ecosystem, the whole classification table.
_ROUTES: dict[tuple[str, str], Ecosystem] = {
    (PYPROJECT_KIND, PROJECT_DEPENDENCIES_SECTION): Ecosystem.PYPI,
    (PIXI_LOCK_KIND, PIXI_LOCK_CONDA_SECTION): Ecosystem.CONDA,
    (PIXI_LOCK_KIND, PIXI_LOCK_PYPI_SECTION): Ecosystem.PYPI,
    (CONDA_LOCK_KIND, CONDA_LOCK_CONDA_SECTION): Ecosystem.CONDA,
    (CONDA_LOCK_KIND, CONDA_LOCK_PYPI_SECTION): Ecosystem.PYPI,
    (RECIPE_YAML_KIND, RECIPE_V1_REQUIREMENTS_SECTION): Ecosystem.CONDA,
    (META_YAML_KIND, META_V0_REQUIREMENTS_SECTION): Ecosystem.CONDA,
    (ENVIRONMENT_YML_KIND, ENVIRONMENT_YML_DEPENDENCIES_SECTION): Ecosystem.CONDA,
    (ENVIRONMENT_YML_KIND, ENVIRONMENT_YML_PIP_SECTION): Ecosystem.PYPI,
    (ENVIRONMENT_YAML_KIND, ENVIRONMENT_YML_DEPENDENCIES_SECTION): Ecosystem.CONDA,
    (ENVIRONMENT_YAML_KIND, ENVIRONMENT_YML_PIP_SECTION): Ecosystem.PYPI,
    (PIXI_TOML_KIND, BASE_DEPENDENCIES_SECTION): Ecosystem.CONDA,
    (PIXI_TOML_KIND, BASE_PYPI_DEPENDENCIES_SECTION): Ecosystem.PYPI,
    (PIXI_TOML_KIND, FEATURE_DEPENDENCIES_SECTION): Ecosystem.CONDA,
    (PIXI_TOML_KIND, FEATURE_PYPI_DEPENDENCIES_SECTION): Ecosystem.PYPI,
    (PIXI_TOML_KIND, TARGET_DEPENDENCIES_SECTION): Ecosystem.CONDA,
    (PIXI_TOML_KIND, TARGET_PYPI_DEPENDENCIES_SECTION): Ecosystem.PYPI,
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
