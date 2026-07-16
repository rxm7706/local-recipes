"""pixi.toml non-rendering extraction (Story 2.2) — direct ``tomllib``, no
template pass at all: this format has no Jinja, so ``tomllib`` parsing IS
the ground truth (the same no-oracle precedent as ``extract/pyproject.py``
— neither format has a template/render step). No ``jinja2`` import, no
execution primitive (NFR-S1 — the ``extract/`` AST-denylist meta-test
covers this file automatically).

Ownership decisions recorded:

* **6 GENERIC static routing tokens** (Boundaries): base
  ``[dependencies]``/``[pypi-dependencies]`` plus ``[feature.<name>.
  dependencies]``/``[feature.<name>.pypi-dependencies]``/``[target.<name>.
  dependencies]``/``[target.<name>.pypi-dependencies]`` for EVERY feature/
  target table present. The feature/target NAME is NEVER baked into the
  routing key (``routing.py``'s ``_ROUTES`` dict stays small/fixed) —
  only into ``Provenance.section`` (e.g. ``f"feature.{name}.
  dependencies"``), mirroring the (kind, section)->ecosystem seam every
  other extractor uses. Nested ``[feature.<name>.target.<name2>.*]``
  tables are OUT of this story's "6 generic tokens" scope (not walked;
  the common case is base + feature + target, not their cross-product).
  ``_walk_conda_table``/``_walk_pypi_table`` ASSERT the router's returned
  ``Ecosystem`` against the hardcoded builder they are about to call
  (``_conda_component``/``pep508_pypi_component``, neither of which takes
  an ``ecosystem`` param of its own) rather than merely calling
  ``route()`` for its fail-loud side effect and discarding the answer —
  the assert is what actually lets the router's answer catch a future
  ``_ROUTES`` edit immediately (fixed 2026-07-16; see also ``extract/
  lockfiles.py``'s own builders, which genuinely branch on the routed
  ``Ecosystem``).
* ``[dependencies]``/``[feature.*.dependencies]``/``[target.*.
  dependencies]`` values are conda matchspec syntax, but pixi.toml's TOML
  TABLE shape already separates name (the TOML key) from specifier (the
  TOML value) — a bare STRING value is the specifier directly; a TABLE
  value (``{ version = "...", channel = "..." }``) contributes its own
  ``version`` sub-key if present and string-typed; any other value shape
  (list/int/bool/missing ``version``) degrades to "no specifier" (bare,
  never a crash, never a guess) — classified via the shared
  ``extract/_identity.py::classify_conda_specifier``.
* ``[pypi-dependencies]``/``[feature.*.pypi-dependencies]``/``[target.*.
  pypi-dependencies]`` values follow the same TOML key=name shape but PEP
  440/508 semantics: a synthetic PEP 508 string (``f"{name}{specifier}"``,
  or bare ``name`` for ``"*"``/absent) is built and handed to the shared
  ``extract/_identity.py::pep508_pypi_component`` (mirrors
  ``pyproject.py``'s own component-building shape exactly). A bare
  (no-operator) version value is pixi.toml's own EXACT-pin shorthand
  (mirrors the conda ``[dependencies]`` table's identical convention) --
  ``_pep508_synthetic_requirement`` prepends ``==`` before building the
  synthetic string so ``Requirement`` parses ``name==version``, never a
  single bogus package literally named ``f"{name}{specifier}"`` (fixed
  2026-07-16 -- live-verified: a bare ``requests = "2.31.0"`` used to
  silently drop the real ``requests`` dependency entirely).
* Every conda-ecosystem row consults the shared ``extract/_identity.py``
  path: only a ``verified``-confidence conda->pypi map hit sets
  ``pypi_identity``; anything else withholds ``UNMAPPED_ECOSYSTEM``.
* NFR-S5: bounds total-file-size + per-line-byte-length BEFORE parsing
  (mirrors ``extract/lockfiles.py::_read_bounded`` via the shared
  ``extract/_identity.py::read_bounded_text``) — deliberately NOT
  ``pyproject.py``'s direct-``tomllib``-on-an-open-file-handle precedent,
  per the Boundaries' explicit call-out (pixi.toml is the one TOML-based
  format Story 2.2 adds its own bound check to).
* Error taxonomy (mirrors ``extract/pyproject.py``): a structurally
  corrupt document (invalid TOML, a ``dependencies``/``pypi-dependencies``/
  ``feature``/``target`` field of the wrong type) raises
  ``UnparsableManifestError`` for the WHOLE manifest.

This module parses TOML as DATA (``tomllib`` only): no subprocess, no
network, no exec.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from ..interfaces import Router
from ..inventory import Component, Provenance
from ..models import Ecosystem, ScannedManifest, WithholdReason
from . import UnparsableManifestError
from ._identity import (
    _conda_component,
    classify_conda_specifier,
    pep508_pypi_component,
    read_bounded_text,
)

# The 6 GENERIC routing tokens (Boundaries) -- the feature/target NAME is
# never baked into these, only into Provenance.section.
BASE_DEPENDENCIES_SECTION = "dependencies"
BASE_PYPI_DEPENDENCIES_SECTION = "pypi-dependencies"
FEATURE_DEPENDENCIES_SECTION = "feature.*.dependencies"
FEATURE_PYPI_DEPENDENCIES_SECTION = "feature.*.pypi-dependencies"
TARGET_DEPENDENCIES_SECTION = "target.*.dependencies"
TARGET_PYPI_DEPENDENCIES_SECTION = "target.*.pypi-dependencies"

_MAX_MANIFEST_BYTES = 5_000_000
_MAX_LINE_BYTES = 8_192


def _conda_specifier_from_value(value: object) -> str | None:
    """A pixi.toml conda-dependency TOML value -> a raw specifier string
    for ``classify_conda_specifier`` -- a bare string is the specifier
    directly; a table contributes its own string-typed ``version`` sub-key
    if present; anything else degrades to "no specifier" (never a crash,
    never a guess)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        version = value.get("version")
        return version if isinstance(version, str) else None
    return None


# The PEP 508 comparison operators a specifier may legitimately start with
# (``str.startswith`` accepts a tuple directly). A bare version carries NONE
# of these -- pixi.toml's own bare-version convention (mirrored from its
# conda `[dependencies]` table: `pkg = "2.31.0"` means `pkg==2.31.0`, not a
# nameless, versionless dependency).
_PEP508_COMPARISON_OPERATORS = ("~=", "==", "!=", "<=", ">=", "<", ">")


def _pep508_synthetic_requirement(name: str, value: object) -> str:
    """A pixi.toml pypi-dependency TOML value -> a synthetic PEP 508
    requirement STRING (``f"{name}{specifier}"``, or bare ``name`` for
    ``"*"``/absent) for ``pep508_pypi_component``. A bare (no-operator)
    version is pixi.toml's own EXACT-pin shorthand -- ``==`` is prepended so
    ``Requirement`` parses ``name==version`` rather than silently misreading
    the whole concatenation as one bogus package literally named
    ``f"{name}{specifier}"`` with no version at all (the real dependency
    would otherwise vanish from the inventory)."""
    if isinstance(value, str):
        specifier = value
    elif isinstance(value, dict):
        version = value.get("version")
        specifier = version if isinstance(version, str) else ""
    else:
        specifier = ""
    specifier = specifier.strip()
    if specifier in ("", "*"):
        return name
    if not specifier.startswith(_PEP508_COMPARISON_OPERATORS):
        specifier = f"=={specifier}"
    return f"{name}{specifier}"


class PixiTomlExtractor:
    """Extract the common-case conda + pypi dependency set from a
    ``pixi.toml`` (Story 2.2) — direct ``tomllib``, no template pass. Walks
    the base ``[dependencies]``/``[pypi-dependencies]`` tables plus every
    present ``[feature.<name>.*]``/``[target.<name>.*]`` table."""

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
            document = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: {exc}"
            ) from exc
        components: list[Component] = []
        components += self._walk_conda_table(
            document.get("dependencies"),
            BASE_DEPENDENCIES_SECTION,
            BASE_DEPENDENCIES_SECTION,
            manifest,
        )
        components += self._walk_pypi_table(
            document.get("pypi-dependencies"),
            BASE_PYPI_DEPENDENCIES_SECTION,
            BASE_PYPI_DEPENDENCIES_SECTION,
            manifest,
        )
        components += self._walk_named_tables(
            document.get("feature"),
            "feature",
            FEATURE_DEPENDENCIES_SECTION,
            FEATURE_PYPI_DEPENDENCIES_SECTION,
            manifest,
        )
        components += self._walk_named_tables(
            document.get("target"),
            "target",
            TARGET_DEPENDENCIES_SECTION,
            TARGET_PYPI_DEPENDENCIES_SECTION,
            manifest,
        )
        return tuple(components)

    def _walk_named_tables(
        self,
        tables: object,
        prefix: str,
        generic_conda_section: str,
        generic_pypi_section: str,
        manifest: ScannedManifest,
    ) -> list[Component]:
        if tables is None:
            return []
        if not isinstance(tables, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: {prefix!r} must be "
                "a table"
            )
        components: list[Component] = []
        for name, table in sorted(tables.items()):
            if not isinstance(table, dict):
                raise UnparsableManifestError(
                    f"unparsable manifest {manifest.path}: {prefix}.{name} "
                    "must be a table"
                )
            components += self._walk_conda_table(
                table.get("dependencies"),
                generic_conda_section,
                f"{prefix}.{name}.dependencies",
                manifest,
            )
            components += self._walk_pypi_table(
                table.get("pypi-dependencies"),
                generic_pypi_section,
                f"{prefix}.{name}.pypi-dependencies",
                manifest,
            )
        return components

    def _walk_conda_table(
        self,
        table: object,
        generic_section: str,
        concrete_section: str,
        manifest: ScannedManifest,
    ) -> list[Component]:
        if table is None:
            return []
        if not isinstance(table, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: {concrete_section} "
                "must be a table"
            )
        # fail-loud gate: `route()`'s return is asserted, not just called for
        # its side effect, so a future `_ROUTES` edit that stops mapping this
        # (kind, section) to CONDA is caught HERE rather than silently
        # continuing to hardcode CONDA below via `_conda_component` (which
        # takes no `ecosystem` param of its own) -- closes the routing-seam
        # gap Fix 7 (2026-07-16) identified.
        ecosystem = self._router.route(manifest.kind, generic_section)
        assert ecosystem is Ecosystem.CONDA
        provenance = (Provenance(manifest=manifest.path, section=concrete_section),)
        components: list[Component] = []
        for name, value in sorted(table.items()):
            specifier = _conda_specifier_from_value(value)
            exact, reason = classify_conda_specifier(specifier)
            components.append(
                _conda_component(
                    name,
                    exact,
                    provenance,
                    no_version_reason=reason or WithholdReason.NO_VERSION,
                )
            )
        return components

    def _walk_pypi_table(
        self,
        table: object,
        generic_section: str,
        concrete_section: str,
        manifest: ScannedManifest,
    ) -> list[Component]:
        if table is None:
            return []
        if not isinstance(table, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: {concrete_section} "
                "must be a table"
            )
        # fail-loud gate: see `_walk_conda_table`'s identical comment.
        ecosystem = self._router.route(manifest.kind, generic_section)
        assert ecosystem is Ecosystem.PYPI
        provenance = (Provenance(manifest=manifest.path, section=concrete_section),)
        components: list[Component] = []
        for name, value in sorted(table.items()):
            synthetic = _pep508_synthetic_requirement(name, value)
            components.append(pep508_pypi_component(synthetic, provenance))
        return components
