"""The bmad-method-version-drift gather filter -- Doctor's verdict on
whether the installed BMAD-METHOD framework version meets ``pixi.toml``'s
own declared floor (Story 10.1, Epic 10/CAP-1).

**Why this module exists, and why it is a dedicated file rather than an
extension of ``sources/factory.py``'s existing ``BMAD_DRIFT``.** ``BMAD_DRIFT``
judges a DIFFERENT artifact class entirely -- ``pyforge-marshal``'s own
project-doc currency (skill version, schema version, MCP tool counts, ...),
ported from ``bmad_drift_check.py`` and tightly coupled to that script's own
HARD/DRIFT/INFO severity mapping. This module has no such origin script and
a single trivial version comparison: ``pixi.toml`` declares
``bmad-method >=X.Y.Z`` in one or more ``[feature.*.dependencies]`` tables,
and ``_bmad/_config/manifest.yaml``'s ``installation.version`` is what was
actually installed. A small dedicated module (mirroring ``sources/ledger.py``)
is simpler to review than overloading an already-dense 1300-line file with an
unrelated artifact class.

**The independence rule.** This module reads two already-tracked files
directly -- ``pixi.toml`` (``tomllib``, stdlib) and
``_bmad/_config/manifest.yaml`` (``yaml.safe_load``, the existing PyYAML
run-dependency ``sources/chain.py`` also uses) -- no subprocess, no network,
no git history. It never imports ``pyforge.marshal``, any other station
package, or ``bmad_loop``; ``tests/meta/test_source_independence.py``
enforces this fleet-wide, same as every sibling source.

**Degrades, never crashes** -- the house rule for every Doctor source. Unlike
``sources/ledger.py``'s bespoke git-error handling, this module has no git
history to reason about, so it mirrors ``sources/chain.py``'s/
``sources/factory.py``'s plain shape instead: ``_parse_version`` and
``_declared_floors`` both RAISE on anything unexpected (a missing file, a
non-``X.Y.Z`` version string, an unrecognized constraint form, ``bmad-method``
absent from every dependencies table) rather than handling it ad hoc inline --
``gather``'s own ``sources.degrade_on_exception`` wrapper is the one outer net
that turns any such exception into a single WARN ``Finding`` naming it.

**Never gates.** Status is always ``ok`` or ``warn``, never ``fail`` -- this
signal informs (mirrors ``Source.DUE_FOR_VERIFICATION``'s own always-warn
discipline); CAP-3's non-gating rule is enforced downstream by
``verdict.exit_code_for``, unaffected by a ``warn`` Finding either way.
"""

from __future__ import annotations

import re
from pathlib import Path

import tomllib
import yaml

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather",)

#: The dependency name as declared in every ``pixi.toml`` dependencies table.
DEPENDENCY_NAME = "bmad-method"

#: Matches a plain ``>=X.Y.Z`` floor constraint -- the only form observed in
#: this repo's own ``pixi.toml`` today (Boundaries: no ``packaging``
#: dependency is warranted for a single constraint shape).
_FLOOR_RE = re.compile(r"^>=(\d+\.\d+\.\d+)$")


def _parse_version(text: str) -> tuple[int, int, int]:
    """``"6.11.0"`` -> ``(6, 11, 0)``. Raises ``ValueError`` on anything that
    is not exactly three dot-separated PLAIN-DIGIT segments -- caught by the
    outer ``degrade_on_exception``, never handled ad hoc inline here.
    ``str.isdigit()``, not a bare ``int()`` call: ``int()`` alone accepts a
    leading ``-`` (``int("-1") == -1``), which would silently parse a
    corrupt/adversarial ``-1.2.3`` into a comparable-but-nonsensical version
    (review finding) -- a real version component is never negative."""
    parts = text.strip().split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"expected X.Y.Z (plain digits), got {text!r}")
    return tuple(int(p) for p in parts)


def _dependency_tables(data: dict) -> list[dict]:
    """Every dependencies table in a ``pixi.toml`` document that could
    plausibly declare ``bmad-method``: the top-level ``[dependencies]``,
    every ``[feature.*.dependencies]``, and every platform-scoped
    ``[target.*.dependencies]`` / ``[feature.*.target.*.dependencies]`` --
    ``pixi.toml`` supports pinning a dependency only for a specific platform
    target, and a floor declared ONLY there would otherwise go silently
    unseen (review finding). No occurrence in this repo's own ``pixi.toml``
    uses a target-scoped table for ``bmad-method`` today, but a source that
    only reads part of what pixi.toml can declare is a coverage gap waiting
    to bite the moment one is added."""
    tables = [data.get("dependencies", {}) or {}]
    for target in (data.get("target", {}) or {}).values():
        tables.append(target.get("dependencies", {}) or {})
    for feature in (data.get("feature", {}) or {}).values():
        tables.append(feature.get("dependencies", {}) or {})
        for target in (feature.get("target", {}) or {}).values():
            tables.append(target.get("dependencies", {}) or {})
    return tables


def _declared_floors(data: dict) -> list[tuple[int, int, int]]:
    """Every declared ``bmad-method`` floor across every dependencies table
    ``_dependency_tables`` finds -- ``pixi.toml`` declares it in more than
    one place today (``feature.python``, ``feature.local-recipes``), so this
    walks every occurrence rather than assuming exactly one line
    (Boundaries).

    Raises ``ValueError`` if ``bmad-method`` is declared nowhere at all, or if
    any declared constraint does not match the plain ``>=X.Y.Z`` form
    ``_FLOOR_RE`` expects (e.g. ``==6.11.0``, ``*``, a git URL) -- both are
    "cannot evaluate", left to the outer ``degrade_on_exception`` to convert
    into one WARN ``Finding`` rather than handled here.
    """
    floors: list[tuple[int, int, int]] = []
    for table in _dependency_tables(data):
        constraint = table.get(DEPENDENCY_NAME)
        if constraint is None:
            continue
        match = _FLOOR_RE.match(str(constraint).strip())
        if not match:
            raise ValueError(
                f"unrecognized {DEPENDENCY_NAME!r} constraint form: {constraint!r}"
            )
        floors.append(_parse_version(match.group(1)))

    if not floors:
        raise ValueError(
            f"{DEPENDENCY_NAME!r} is not declared in any dependencies table"
        )
    return floors


def gather(target: Path) -> tuple[Finding, ...]:
    """Compare ``pixi.toml``'s max declared ``bmad-method`` floor against
    ``_bmad/_config/manifest.yaml``'s installed version -- the library form
    the story's own Intent names. On the success path, ``_gather`` returns
    exactly one Finding: ``warn`` on drift (installed older than the declared
    floor), ``ok`` on agreement; the outer ``degrade_on_exception`` wrapper is
    what guarantees exactly one Finding OVERALL by converting any exception
    from that success path into one WARN instead.

    Read-only: never runs ``npx bmad-method install``, never writes to
    ``_bmad/**`` (Boundaries).
    """
    return degrade_on_exception(
        Source.BMAD_METHOD_VERSION_DRIFT, "bmad-method-version-drift",
        lambda: _gather(target),
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    pixi_data = tomllib.loads((target / "pixi.toml").read_text(encoding="utf-8"))
    declared = max(_declared_floors(pixi_data))

    manifest_path = target / "_bmad" / "_config" / "manifest.yaml"
    manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    installed = _parse_version(str(manifest_data["installation"]["version"]))

    declared_text = ".".join(str(part) for part in declared)
    installed_text = ".".join(str(part) for part in installed)
    evidence = {
        "installed": installed_text,
        "declared_floor": f">={declared_text}",
    }

    if installed < declared:
        return (
            Finding(
                source=Source.BMAD_METHOD_VERSION_DRIFT,
                check="bmad-method-version-drift",
                status=DoctorStatus.WARN,
                message=(
                    f"installed bmad-method {installed_text} is behind "
                    f"pixi.toml's declared floor >={declared_text}"
                ),
                evidence=evidence,
            ),
        )
    return (
        Finding(
            source=Source.BMAD_METHOD_VERSION_DRIFT,
            check="bmad-method-version-drift",
            status=DoctorStatus.OK,
            message=(
                f"installed bmad-method {installed_text} meets pixi.toml's "
                f"declared floor >={declared_text}"
            ),
            evidence=evidence,
        ),
    )
