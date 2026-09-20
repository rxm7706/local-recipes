"""Documentation MAP.md alignment gather (Story 30.1, ``spec-pyforge-doctor`` CAP-83).

Parses ``docs/MAP.md`` and walks the four Diátaxis quadrant directories the
map itself governs -- ``docs/tutorials``, ``docs/how-to``, ``docs/reference``,
``docs/explanation`` (recursively) -- and nothing else. Everything MAP.md
§ "Outside this map" excludes (``docs/dreams``, ``docs/specs``,
``docs/governance``, ``docs/intake``, ``docs/dashboard``, ``docs/foundry``,
station READMEs, skill dirs, ``_bmad-output``) is out of scope by
construction, so the detector cannot contradict the map's own scope.

Two checks, one Finding per class:

* ``missing`` -- a ``.md`` link in MAP.md that resolves under ``docs/`` but
  does not exist on disk -> ``FAIL`` (a broken map is never acceptable).
* ``unmapped`` -- a quadrant page not linked from MAP.md -> ``FAIL``
  (promoted from WARN by Story 30.2 / CAP-84: once ``docs/MAP.md`` carries
  the generated ``## Page registry`` section -- one link per
  ``docs/map.yaml`` page -- MAP.md's own link set already equals
  map.yaml's page set, so a quadrant page absent from MAP.md is, by
  construction, also absent from map.yaml; the comparison target in this
  module needed no change).

Section index pages -- a ``README.md`` directly inside a quadrant directory
-- are exempt from ``unmapped``; deeper ``README.md`` files (e.g.
``docs/reference/sync-jira-github-workflow-templates/README.md``) still
count. Links whose ``../`` escapes ``docs/`` are ignored: the map may point
at ``README.md`` / ``AGENTS.md`` / archive paths, which are not its
responsibility to keep alive. When both classes are empty one ``OK`` finding
carries ``mapped_count``.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather",)

_CHECK_ID = "docs-map-hygiene"

# The four Diátaxis quadrants docs/MAP.md governs (its "Four quadrants" table).
_QUADRANTS: tuple[str, ...] = ("tutorials", "how-to", "reference", "explanation")

# Match Markdown links whose target ends in .md: [text](path.md). An optional
# fragment (`#section`) is tolerated and stripped.
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+?\.md)(?:#[^)]*)?\)")


def _mapped_paths(map_path: Path, docs_dir: Path) -> set[str]:
    """Every ``.md`` link in MAP.md that resolves under ``docs/``, as a
    docs-relative posix path. Links escaping ``docs/`` are dropped."""
    docs_resolved = docs_dir.resolve()
    mapped: set[str] = set()
    for match in _MD_LINK_RE.finditer(map_path.read_text(encoding="utf-8")):
        link = match.group(1)
        if "://" in link:
            continue
        try:
            rel = (map_path.parent / link).resolve().relative_to(docs_resolved)
        except ValueError:
            continue  # `../README.md`-style pointer outside docs/ -- not ours
        mapped.add(rel.as_posix())
    return mapped


def _quadrant_pages(docs_dir: Path) -> set[str]:
    """Every ``.md`` page under the four quadrants, docs-relative, minus the
    quadrant-level ``README.md`` index pages."""
    pages: set[str] = set()
    for quadrant in _QUADRANTS:
        qdir = docs_dir / quadrant
        if not qdir.is_dir():
            continue
        for page in qdir.rglob("*.md"):
            if page.parent == qdir and page.name == "README.md":
                continue  # section index page, exempt
            pages.add(page.relative_to(docs_dir).as_posix())
    return pages


def _gather_all(target: Path) -> tuple[Finding, ...]:
    docs_dir = target / "docs"
    map_path = docs_dir / "MAP.md"
    if not map_path.is_file():
        return (
            Finding(
                source=Source.DOCS_MAP_HYGIENE,
                check=_CHECK_ID,
                status=DoctorStatus.FAIL,
                message="docs/MAP.md is missing",
                evidence={"path": "docs/MAP.md"},
            ),
        )

    mapped = _mapped_paths(map_path, docs_dir)
    pages = _quadrant_pages(docs_dir)

    missing = sorted(rel for rel in mapped if not (docs_dir / rel).is_file())
    unmapped = sorted(pages - mapped)

    findings: list[Finding] = []
    if missing:
        findings.append(
            Finding(
                source=Source.DOCS_MAP_HYGIENE,
                check=_CHECK_ID,
                status=DoctorStatus.FAIL,
                message=(
                    f"docs/MAP.md links {len(missing)} .md page(s) that do not"
                    " exist under docs/"
                ),
                evidence={"class": "missing", "paths": missing},
            )
        )
    if unmapped:
        findings.append(
            Finding(
                source=Source.DOCS_MAP_HYGIENE,
                check=_CHECK_ID,
                status=DoctorStatus.FAIL,
                message=(
                    f"{len(unmapped)} quadrant page(s) under docs/ are not"
                    " linked from docs/MAP.md"
                ),
                evidence={"class": "unmapped", "paths": unmapped},
            )
        )
    if findings:
        return tuple(findings)

    return (
        Finding(
            source=Source.DOCS_MAP_HYGIENE,
            check=_CHECK_ID,
            status=DoctorStatus.OK,
            message=(
                "docs/MAP.md links every quadrant page and every link"
                " resolves"
            ),
            evidence={"mapped_count": len(mapped), "page_count": len(pages)},
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Docs MAP.md hygiene gather -- Story 30.1 / spec-pyforge-doctor CAP-83.

    ``missing`` (broken MAP link under ``docs/``) is FAIL; ``unmapped``
    (quadrant page absent from MAP.md) is FAIL (promoted from WARN by
    Story 30.2 / CAP-84 -- see module docstring). Degrades to one WARN on
    any exception rather than crashing the dispatcher.
    """
    return degrade_on_exception(
        Source.DOCS_MAP_HYGIENE,
        _CHECK_ID,
        lambda: _gather_all(target),
    )
