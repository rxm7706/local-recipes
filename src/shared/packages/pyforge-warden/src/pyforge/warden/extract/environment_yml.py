"""environment.yml non-rendering extraction (Story 2.2) — direct
``yaml.safe_load``, no template pass at all: this format has no Jinja, no
``context:``/``{% set %}`` mechanism whatsoever, so ``safe_load`` parsing
IS the ground truth (the same no-oracle precedent as ``extract/
pyproject.py`` — neither format has a template/render step). No
``jinja2`` import, no execution primitive (NFR-S1 — the ``extract/``
AST-denylist meta-test covers this file automatically).

Ownership decisions recorded:

* ``dependencies:`` is a MIXED list (unlike ``pyproject.toml``'s
  homogeneous array): plain STRING entries are conda matchspec syntax
  (``extract/_identity.py::split_conda_dep_string`` +
  ``classify_conda_specifier``, mirroring ``pyproject.py::_exact_pin``'s
  discipline); exactly one nested ``{pip: [...]}`` mapping entry's list is
  PEP 508 syntax (``extract/_identity.py::pep508_pypi_component``,
  mirroring ``pyproject.py``'s own component-building shape exactly —
  ``identity_source=NATIVE``). An entry that is neither a string nor a
  recognized ``{pip: [...]}`` mapping (a stray int/bool/list, or an
  unrecognized dict shape) degrades to one conda-ecosystem
  ``RAW_MALFORMED`` component — kept, marked, never dropped, never a
  crash (this is a content-level degeneracy per entry, not treated as a
  whole-manifest structural failure, since the top-level ``dependencies:``
  list is not homogeneous by design).
* A ``pip:`` list entry that is present but not a list of strings (wrong
  TYPE at the ``pip:`` key) IS a structural problem (mirrors
  ``pyproject.py``'s own "the whole array must be strings" precedent) —
  raises ``UnparsableManifestError`` for the whole manifest, since a
  malformed ``pip:`` shape can't be honestly attributed to any one entry.
* Every conda-ecosystem row consults the shared ``extract/_identity.py``
  path: only a ``verified``-confidence conda->pypi map hit sets
  ``pypi_identity``; anything else withholds ``UNMAPPED_ECOSYSTEM``. The
  router's returned ``Ecosystem`` is ASSERTED against the hardcoded
  ``_conda_component`` builder it gates (which takes no ``ecosystem``
  param of its own), not just called for its fail-loud side effect and
  discarded — mirrors ``extract/pixi.py``'s identical Fix 7 (2026-07-16).
* NFR-S5: mirrors ``extract/lockfiles.py::_read_bounded`` via the shared
  ``extract/_identity.py::read_bounded_text``; no compiled pattern here
  carries a nested unbounded quantifier.
* Error taxonomy (mirrors ``extract/pyproject.py``/``extract/
  lockfiles.py``): a structurally corrupt document (not a mapping, a
  ``dependencies:``/``pip:`` field of the wrong type) raises
  ``UnparsableManifestError`` for the WHOLE manifest; a content-degenerate
  single entry degrades to one ``RAW_MALFORMED`` component instead.

This module parses YAML as DATA (``yaml.safe_load`` only): no subprocess,
no network, no exec.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..interfaces import Router
from ..inventory import Component, Provenance
from ..models import Ecosystem, ScannedManifest, WithholdReason
from . import UnparsableManifestError
from ._identity import (
    _conda_component,
    _raw_malformed,
    classify_conda_specifier,
    pep508_pypi_component,
    read_bounded_text,
    split_conda_dep_string,
)

# The 2 synthetic (kind, section) routing tokens this format needs (mirrors
# pyproject.py's PROJECT_DEPENDENCIES_SECTION -- imported into routing.py).
ENVIRONMENT_YML_DEPENDENCIES_SECTION = "dependencies"
ENVIRONMENT_YML_PIP_SECTION = "dependencies[pip]"

_MAX_MANIFEST_BYTES = 5_000_000
_MAX_LINE_BYTES = 8_192


class EnvironmentYmlExtractor:
    """Extract the common-case dependency set from an ``environment.yml``
    (Story 2.2) — direct ``yaml.safe_load``, no template pass."""

    def __init__(self, router: Router) -> None:
        self._router = router

    def extract(
        self, manifest_path: Path, manifest: ScannedManifest
    ) -> tuple[Component, ...]:
        text = read_bounded_text(
            manifest_path,
            manifest,
            max_bytes=_MAX_MANIFEST_BYTES,
            max_line_bytes=_MAX_LINE_BYTES,
        )
        try:
            document = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: {exc}"
            ) from exc
        if document is None:
            return ()
        if not isinstance(document, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: top-level document "
                "is not a mapping"
            )
        dependencies = document.get("dependencies")
        if dependencies is None:
            return ()
        if not isinstance(dependencies, list):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: 'dependencies' must "
                "be a list"
            )
        # fail-loud gate: asserted (not just called for its fail-loud side
        # effect) so a future `_ROUTES` edit is caught HERE rather than
        # silently continuing to hardcode CONDA below via
        # `_conda_component_from_entry`'s success path (`_conda_component`
        # takes no `ecosystem` param of its own) -- mirrors `extract/pixi.py`
        # `_walk_conda_table`'s identical Fix 7 (2026-07-16).
        conda_ecosystem = self._router.route(
            manifest.kind, ENVIRONMENT_YML_DEPENDENCIES_SECTION
        )
        assert conda_ecosystem is Ecosystem.CONDA
        conda_provenance = (
            Provenance(
                manifest=manifest.path, section=ENVIRONMENT_YML_DEPENDENCIES_SECTION
            ),
        )
        pip_provenance = (
            Provenance(manifest=manifest.path, section=ENVIRONMENT_YML_PIP_SECTION),
        )
        components: list[Component] = []
        for entry in dependencies:
            if isinstance(entry, str):
                components.append(
                    self._conda_component_from_entry(
                        entry, conda_provenance, conda_ecosystem
                    )
                )
            elif isinstance(entry, dict) and "pip" in entry:
                components += self._pip_components(
                    entry.get("pip"), pip_provenance, manifest
                )
            else:
                # Neither a plain conda-matchspec string nor a recognized
                # {pip: [...]} mapping: a content-level degeneracy for this
                # ONE entry (the list itself is not homogeneous by design),
                # kept RAW_MALFORMED rather than failing the whole manifest.
                components.append(
                    _raw_malformed(conda_ecosystem, str(entry), conda_provenance)
                )
        return tuple(components)

    def _conda_component_from_entry(
        self, entry: str, provenance: tuple[Provenance, ...], ecosystem: Ecosystem
    ) -> Component:
        split = split_conda_dep_string(entry)
        if split is None:
            return _raw_malformed(ecosystem, entry, provenance)
        name, specifier = split
        exact, reason = classify_conda_specifier(specifier)
        return _conda_component(
            name,
            exact,
            provenance,
            no_version_reason=reason or WithholdReason.NO_VERSION,
        )

    def _pip_components(
        self,
        pip_list: object,
        provenance: tuple[Provenance, ...],
        manifest: ScannedManifest,
    ) -> list[Component]:
        if pip_list is None:
            # A `- pip:` key with nothing under it (a common authoring
            # leftover) parses as a null YAML node: semantically "no pip
            # deps", NOT structural corruption -- treating it as the latter
            # used to discard the whole manifest's conda deps along with it
            # (fixed 2026-07-16). A pip: value of any OTHER wrong type still
            # fails structurally below.
            return []
        if not isinstance(pip_list, list) or not all(
            isinstance(entry, str) for entry in pip_list
        ):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: 'pip' must be a "
                "list of strings"
            )
        return [pep508_pypi_component(entry, provenance) for entry in pip_list]
