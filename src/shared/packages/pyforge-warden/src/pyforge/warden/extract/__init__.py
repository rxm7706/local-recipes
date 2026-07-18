"""E1 extractor package — the no-execution zone (Story 1.2, NFR-S1).

Every module in this package parses untrusted input as DATA: ``tomllib`` +
``packaging.requirements`` only; no ``eval``/``exec``/``subprocess``/
``os.system``/``jinja2``, no YAML load — and no NETWORK modules (NFR-S2:
the parse zone has no legitimate egress; ``socket``/``urllib``/``http``/
third-party clients are denied at import). The AST-denylist meta-test
(``tests/meta/test_extract_no_execution.py``) enforces both axes over the
whole package, present and future (a denylist backstop for the "only"
convention stated here — the socket-deny harness covers test-time
behavior; the denylist covers production source).

Error taxonomy ownership: only a GENUINE manifest problem may be labeled
``unparsable-manifest`` — extractors raise ``UnparsableManifestError``
(defined here) for those; any other ``ValueError`` escaping the extract
path is an internal error and the CLI diagnoses it as such, never as a
manifest problem.

Dispatch ownership: ``extractor_for`` maps a manifest-kind token to its
extractor; the kind vocabulary is Story 1.9's — 1.2 knows exactly one kind.
"""

from __future__ import annotations

from ..discovery import (
    CONDA_LOCK_KIND,
    ENVIRONMENT_YAML_KIND,
    ENVIRONMENT_YML_KIND,
    META_YAML_KIND,
    PIXI_LOCK_KIND,
    PIXI_TOML_KIND,
    PYPROJECT_KIND,
    RECIPE_YAML_KIND,
)
from ..interfaces import Extractor, Router


class UnparsableManifestError(ValueError):
    """A genuine manifest problem: the manifest exists but cannot be parsed
    into components (malformed TOML, structurally-corrupt tables). The CLI
    maps EXACTLY this class to ``ErrorRecord(kind=unparsable-manifest)``;
    every other ``ValueError`` is an internal error — misdiagnosing an
    internal bug as a broken user manifest is a lie in the report."""


# Imported AFTER UnparsableManifestError so extractor modules can import the
# class from this (then partially-initialized) package without a cycle.
from .lockfiles import CondaLockExtractor, PixiLockExtractor  # noqa: E402
from .pyproject import PyprojectExtractor  # noqa: E402
from .recipe_v1 import RecipeV1Extractor  # noqa: E402
from .meta_v0 import MetaV0Extractor  # noqa: E402
from .environment_yml import EnvironmentYmlExtractor  # noqa: E402
from .pixi import PixiTomlExtractor  # noqa: E402


def extractor_for(kind: str, router: Router) -> Extractor:
    """The extractor for a manifest-kind token; unknown kinds fail loud.

    The raise is a plain ``ValueError`` (NOT ``UnparsableManifestError``):
    an unknown kind means discovery and dispatch disagree — an internal
    inconsistency, not a broken manifest."""
    if kind == PYPROJECT_KIND:
        return PyprojectExtractor(router)
    if kind == PIXI_LOCK_KIND:
        return PixiLockExtractor(router)
    if kind == CONDA_LOCK_KIND:
        return CondaLockExtractor(router)
    if kind == RECIPE_YAML_KIND:
        return RecipeV1Extractor(router)
    if kind == META_YAML_KIND:
        return MetaV0Extractor(router)
    if kind == ENVIRONMENT_YML_KIND:
        return EnvironmentYmlExtractor(router)
    if kind == ENVIRONMENT_YAML_KIND:
        # Story 1.9: the second environment.yml spelling — shares the SAME
        # extractor class (routing.py's routes distinguish the two kinds).
        return EnvironmentYmlExtractor(router)
    if kind == PIXI_TOML_KIND:
        return PixiTomlExtractor(router)
    raise ValueError(f"no extractor registered for manifest kind {kind!r}")
