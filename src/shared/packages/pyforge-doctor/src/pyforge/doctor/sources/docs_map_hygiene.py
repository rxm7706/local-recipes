"""Documentation MAP.md alignment gather (Story 30.1, ``spec-pyforge-doctor`` CAP-83).

Parses ``docs/MAP.md`` and walks the four Diátaxis quadrant directories the
map itself governs -- ``docs/tutorials``, ``docs/how-to``, ``docs/reference``,
``docs/explanation`` (recursively) -- and nothing else. Everything MAP.md
§ "Outside this map" excludes (``docs/dreams``, ``docs/specs``,
``docs/governance``, ``docs/intake``, ``docs/dashboard``, ``docs/foundry``,
station READMEs, skill dirs, ``_bmad-output``) is out of scope by
construction, so the detector cannot contradict the map's own scope.

Checks:

* ``missing`` -- a ``.md`` link in MAP.md that resolves under ``docs/`` but
  does not exist on disk -> ``FAIL`` (a broken map is never acceptable).
* ``unmapped`` -- a quadrant page not linked from MAP.md -> ``FAIL``
  (promoted from WARN by Story 30.2 / CAP-84: once ``docs/MAP.md`` carries
  the generated ``## Page registry`` section -- one link per
  ``docs/map.yaml`` page -- MAP.md's own link set already equals
  map.yaml's page set, so a quadrant page absent from MAP.md is, by
  construction, also absent from map.yaml; the comparison target in this
  module needed no change).
* ``sections`` (Story 48.1 / CAP-90) -- duplicate ``key``/``order``, malformed
  ``href`` on a section or entry -> ``WARN`` (one finding per defect).
* ``unnamed-top-level`` (Story 48.1) -- tracked top-level directory neither
  allow-listed nor named in MAP.md § Outside this map -> ``WARN``.

Section index pages -- a ``README.md`` directly inside a quadrant directory
-- are exempt from ``unmapped``; deeper ``README.md`` files (e.g.
``docs/reference/sync-jira-github-workflow-templates/README.md``) still
count. Links whose ``../`` escapes ``docs/`` are ignored: the map may point
at ``README.md`` / ``AGENTS.md`` / archive paths, which are not its
responsibility to keep alive. When every class is quiet one ``OK`` finding
carries ``mapped_count``, ``sections_count``, and ``unnamed_top_level``.
"""

from __future__ import annotations

import re
from pathlib import Path

import jsonschema

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception
from .docs_currency import load_map_yaml

__all__ = ("gather",)

_CHECK_ID = "docs-map-hygiene"

# The four Diátaxis quadrants docs/MAP.md governs (its "Four quadrants" table).
_QUADRANTS: tuple[str, ...] = ("tutorials", "how-to", "reference", "explanation")

# Match Markdown links whose target ends in .md: [text](path.md). An optional
# fragment (`#section`) is tolerated and stripped.
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+?\.md)(?:#[^)]*)?\)")

_OUTSIDE_MAP_HEADING_RE = re.compile(r"^## Outside this map\b", re.MULTILINE)
_BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")

_INFRASTRUCTURE_DIRS = frozenset(
    {
        "_bmad",
        "_bmad-output",
        "_skf-learn",
        "archive",
        "conf",
        "evals",
        "helm",
        "recipes",
        "scripts",
        "src",
        "tests",
    }
)


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


def _href_defect_messages(href: str) -> list[str]:
    """Human-readable defect phrases for a site-root-relative ``href``."""
    defects: list[str] = []
    if href.startswith("/"):
        defects.append("leading slash")
    if "://" in href:
        defects.append("absolute URL")
    if ".." in href:
        defects.append("parent segment (..)")
    if not href.endswith("/"):
        defects.append("missing trailing slash")
    return defects


def _sections_warnings(target: Path) -> tuple[list[Finding], int]:
    """WARN findings for ``sections:`` hygiene; returns (findings, sections_count)."""
    try:
        map_data = load_map_yaml(target)
    except (ValueError, jsonschema.ValidationError) as exc:
        return (
            [
                Finding(
                    source=Source.DOCS_MAP_HYGIENE,
                    check=_CHECK_ID,
                    status=DoctorStatus.WARN,
                    message=f"docs/map.yaml schema error: {exc}",
                    evidence={"class": "sections", "error": str(exc)},
                )
            ],
            0,
        )

    sections: list[dict] = map_data.get("sections") or []
    findings: list[Finding] = []

    seen_keys: dict[str, int] = {}
    seen_orders: dict[int, list[str]] = {}
    for section in sections:
        key = section["key"]
        if key in seen_keys:
            findings.append(
                Finding(
                    source=Source.DOCS_MAP_HYGIENE,
                    check=_CHECK_ID,
                    status=DoctorStatus.WARN,
                    message=(f"sections: duplicate key {key!r}"),
                    evidence={"class": "sections", "key": key, "defect": "duplicate-key"},
                )
            )
        seen_keys[key] = seen_keys.get(key, 0) + 1

        order = section["order"]
        seen_orders.setdefault(order, []).append(key)

        for defect in _href_defect_messages(section["href"]):
            findings.append(
                Finding(
                    source=Source.DOCS_MAP_HYGIENE,
                    check=_CHECK_ID,
                    status=DoctorStatus.WARN,
                    message=(f"sections: section {key!r} href {section['href']!r}: {defect}"),
                    evidence={
                        "class": "sections",
                        "section_key": key,
                        "href": section["href"],
                        "defect": defect,
                    },
                )
            )

        for entry in section.get("entries") or []:
            entry_key = entry["key"]
            for defect in _href_defect_messages(entry["href"]):
                findings.append(
                    Finding(
                        source=Source.DOCS_MAP_HYGIENE,
                        check=_CHECK_ID,
                        status=DoctorStatus.WARN,
                        message=(f"sections: section {key!r} entry {entry_key!r} href {entry['href']!r}: {defect}"),
                        evidence={
                            "class": "sections",
                            "section_key": key,
                            "entry_key": entry_key,
                            "href": entry["href"],
                            "defect": defect,
                        },
                    )
                )

    for order, keys in seen_orders.items():
        if len(keys) > 1:
            findings.append(
                Finding(
                    source=Source.DOCS_MAP_HYGIENE,
                    check=_CHECK_ID,
                    status=DoctorStatus.WARN,
                    message=(f"sections: duplicate order {order} for keys {keys!r}"),
                    evidence={
                        "class": "sections",
                        "order": order,
                        "keys": keys,
                        "defect": "duplicate-order",
                    },
                )
            )

    return findings, len(sections)


def _outside_map_named_segments(map_path: Path) -> set[str]:
    """First path segment of each backticked path under § Outside this map."""
    text = map_path.read_text(encoding="utf-8")
    match = _OUTSIDE_MAP_HEADING_RE.search(text)
    if match is None:
        return set()
    rest = text[match.start() :]
    # Stop at the next ## heading (same or higher level).
    next_heading = re.search(r"\n## [^#]", rest[len(match.group(0)) :])
    section_text = rest if next_heading is None else rest[: len(match.group(0)) + next_heading.start()]

    named: set[str] = set()
    for path in _BACKTICK_PATH_RE.findall(section_text):
        path = path.strip()
        if "/" not in path:
            continue
        segment = path.split("/", 1)[0]
        if segment:
            named.add(segment)
    return named


def _tracked_top_level_dirs(target: Path) -> tuple[list[str] | None, str | None]:
    """Top-level directory names from ``git ls-files -z``, or (None, error)."""
    try:
        listing = run_git(target, ["-c", "core.quotePath=false", "ls-files", "-z"])
    except CliBridgeError as exc:
        return None, str(exc)

    dirs: set[str] = set()
    for entry in listing.split("\0"):
        if not entry or "/" not in entry:
            continue
        dirs.add(entry.split("/", 1)[0])
    return sorted(dirs), None


def _unnamed_top_level_warnings(
    target: Path,
    map_path: Path,
    *,
    infrastructure_dirs: frozenset[str] | None = None,
) -> tuple[list[Finding], list[str]]:
    """WARN findings for tracked top-level dirs not named in MAP or allow-list."""
    allow = infrastructure_dirs if infrastructure_dirs is not None else _INFRASTRUCTURE_DIRS
    dirs, error = _tracked_top_level_dirs(target)
    if error is not None or dirs is None:
        return (
            [
                Finding(
                    source=Source.DOCS_MAP_HYGIENE,
                    check=_CHECK_ID,
                    status=DoctorStatus.WARN,
                    message=f"unnamed-top-level: cannot read git index: {error or 'no directories'}",
                    evidence={"class": "unnamed-top-level", "error": error or "no directories"},
                )
            ],
            [],
        )

    named_in_map = _outside_map_named_segments(map_path)
    unnamed: list[str] = []
    findings: list[Finding] = []
    for name in dirs:
        if name == "docs":
            continue
        if name.startswith("."):
            continue
        if name in allow:
            continue
        if name in named_in_map:
            continue
        unnamed.append(name)
        findings.append(
            Finding(
                source=Source.DOCS_MAP_HYGIENE,
                check=_CHECK_ID,
                status=DoctorStatus.WARN,
                message=(f"unnamed-top-level: tracked directory {name!r} is not named in docs/MAP.md"),
                evidence={"class": "unnamed-top-level", "directory": name},
            )
        )
    return findings, unnamed


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
                message=(f"docs/MAP.md links {len(missing)} .md page(s) that do not exist under docs/"),
                evidence={"class": "missing", "paths": missing},
            )
        )
    if unmapped:
        findings.append(
            Finding(
                source=Source.DOCS_MAP_HYGIENE,
                check=_CHECK_ID,
                status=DoctorStatus.FAIL,
                message=(f"{len(unmapped)} quadrant page(s) under docs/ are not linked from docs/MAP.md"),
                evidence={"class": "unmapped", "paths": unmapped},
            )
        )
    if findings:
        return tuple(findings)

    section_warns, sections_count = _sections_warnings(target)
    unnamed_warns, unnamed_dirs = _unnamed_top_level_warnings(target, map_path)
    extra_warns = section_warns + unnamed_warns
    if extra_warns:
        return tuple(extra_warns)

    return (
        Finding(
            source=Source.DOCS_MAP_HYGIENE,
            check=_CHECK_ID,
            status=DoctorStatus.OK,
            message=("docs/MAP.md links every quadrant page and every link resolves"),
            evidence={
                "mapped_count": len(mapped),
                "page_count": len(pages),
                "sections_count": sections_count,
                "unnamed_top_level": unnamed_dirs,
            },
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
