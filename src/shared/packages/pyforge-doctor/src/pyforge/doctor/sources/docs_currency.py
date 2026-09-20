"""Documentation currency gather (Story 30.2, ``spec-pyforge-doctor`` CAP-84).

Three read-only checks over ``docs/map.yaml`` (the new machine registry) and
``docs/MAP.md`` (its render):

* ``map-render`` (``docs-currency-map-render``) -- ``docs/MAP.md``'s
  generated ``## Page registry`` section (bounded by the
  ``docs-map:registry:begin``/``docs-map:registry:end`` markers)
  byte-matches a fresh :func:`render_map_registry` of ``docs/map.yaml``'s
  pages. Markers absent from MAP.md counts as a mismatch too.
* ``authored-page-stale`` (``docs-currency-authored-stale``) -- for each
  ``kind: authored`` page: (a) when the page's OWN frontmatter declares
  ``sources:``/``verified:`` (the convention Story 30.1 seeded on 14
  pages), a named source whose git last-touch date postdates ``verified:``
  is stale; (b) the page body is scanned for backticked ``bmad-*``/
  ``skf-*`` skill names, ``scripts/``/``_bmad/``-rooted ``.py`` paths, and
  repo-relative paths under a real top-level directory that no longer
  resolve -- mirrors ``scripts/governance_currency_check.py``'s three
  regexes and its ``_resolves_as_identifier``/existence-check logic,
  duplicated here deliberately (``pyforge.doctor`` cannot import from the
  top-level ``scripts/`` tree). One Finding per page that triggers
  either/both evidence kinds; a page with neither frontmatter nor a dead
  reference is silently fine (coverage grows incrementally, per the
  story's own Design Notes).
* ``skill-dir-hygiene`` (``docs-currency-skill-dir-hygiene``) -- a stray
  file inside a managed ``bmad-*``/``pyforge-*``/``skf-*`` skill
  directory.

  Design deviation (recorded here, not silently): the story's Code Map
  describes this check's allowed top-level entries as ``{SKILL.md (file),
  scripts/, references/, assets/ (dirs)}``, "anything else -- WARN". The
  LIVE ``.claude/skills/`` tree does not match that shape: every
  ``bmad-*`` directory carries ``customize.toml`` (the sanctioned
  ``bmad-customize`` override file) plus extensive per-skill scaffolding
  (``steps/``, ``templates/``, ``transcripts/``, ``workflow.md``, csv
  reference data, ...) as its NORMAL, legitimate shape -- not drift; every
  ``pyforge-*`` directory is the SKF-exported layout (a versioned
  ``<x.y.z>/`` subdirectory + an ``active`` symlink + ``skill-brief.yaml``
  at the top level, with no top-level ``SKILL.md`` at all). Applying the
  literal allowlist would emit dozens of WARN findings against `main`
  TODAY, directly violating this story's own AC2 ("``docs-currency`` runs
  on `main` after this story lands ... reports OK"). This module instead
  targets the SPECIFIC documented failure class the research doc's
  finding #1 catalogued: a stray ``README.md`` -- a boilerplate note file
  no harness reads, silently orphaned the next time the owning tool
  (the BMAD installer for ``bmad-*``, the SKF exporter for ``pyforge-*``/
  ``skf-*``) regenerates the directory. Verified zero-noise against `main`
  (2026-09-20): no ``README.md`` exists under any managed skill directory
  today.

Fail-open by design (CAP-62): ``docs/map.yaml`` missing, unreadable, or
schema-invalid degrades the WHOLE gather to exactly one WARN via
:func:`.degrade_on_exception` -- never a FAIL, never a crash.
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path

import jsonschema
import yaml

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather", "load_map_yaml", "render_map_registry")

_CHECK_MAP_RENDER = "docs-currency-map-render"
_CHECK_AUTHORED_STALE = "docs-currency-authored-stale"
_CHECK_SKILL_DIR_HYGIENE = "docs-currency-skill-dir-hygiene"
_CHECK_MAP_UNREADABLE = "docs-currency-map-unreadable"
_CHECK_OK = "docs-currency-ok"

_MAP_YAML_REL = "docs/map.yaml"
_MAP_MD_REL = "docs/MAP.md"
_REGISTRY_BEGIN = "<!-- docs-map:registry:begin"
_REGISTRY_END = "<!-- docs-map:registry:end -->"

_QUADRANT_ORDER: tuple[str, ...] = ("tutorials", "how-to", "reference", "explanation")
_QUADRANT_TITLES: dict[str, str] = {
    "tutorials": "Tutorials",
    "how-to": "How-to",
    "reference": "Reference",
    "explanation": "Explanation",
}

_FRONTMATTER_FENCE = "---"

# Mirrors scripts/governance_currency_check.py's three regexes exactly --
# duplicated deliberately (pyforge.doctor cannot import scripts/).
_SKILL_RE = re.compile(r"`((?:bmad|skf)-[a-z0-9][a-z0-9-]*)`")
_SCRIPT_RE = re.compile(r"`((?:scripts|_bmad)/[A-Za-z0-9._/-]+\.py)`")
_PATH_RE = re.compile(
    r"`((?:docs|src|recipes|_bmad-output|\.github|\.claude)/[A-Za-z0-9._/-]+)`"
)

# The externally-regenerated skill-directory prefixes (module docstring).
_MANAGED_SKILL_PREFIXES = ("bmad-", "pyforge-", "skf-")
_SKILL_DIR_STRAY_NAMES = frozenset({"README.md"})


def load_map_yaml(target: Path) -> dict:
    """Load + schema-validate ``docs/map.yaml``.

    Raises ``ValueError`` (file missing), ``yaml.YAMLError`` (malformed
    YAML), or ``jsonschema.ValidationError`` (schema mismatch) -- the
    caller (:func:`gather`) wraps the whole pipeline in
    ``degrade_on_exception`` so any of these becomes exactly one WARN,
    never a crash, never a FAIL.
    """
    path = target / _MAP_YAML_REL
    if not path.is_file():
        raise ValueError(f"{_MAP_YAML_REL} does not exist")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema_text = (
        resources.files("pyforge.doctor")
        .joinpath("data", "docs-map-schema.json")
        .read_text(encoding="utf-8")
    )
    schema = json.loads(schema_text)
    jsonschema.Draft202012Validator(schema).validate(data)
    return data


def render_map_registry(pages: list[dict]) -> str:
    """Pure render of the ``## Page registry`` section's BETWEEN-markers
    content -- one ``### <Quadrant>`` subsection per quadrant (in
    :data:`_QUADRANT_ORDER`), each a ``| Page | Owner | Kind |`` table
    sorted by ``path``. The single source both ``scripts/docs_map_render.py``
    (the write side) and this module's ``map-render`` check (the read
    side) call, so the two can never independently drift from each other.
    """
    blocks: list[str] = []
    for quadrant in _QUADRANT_ORDER:
        quad_pages = sorted(
            (page for page in pages if page["quadrant"] == quadrant),
            key=lambda page: page["path"],
        )
        lines = [
            f"### {_QUADRANT_TITLES[quadrant]}",
            "",
            "| Page | Owner | Kind |",
            "|---|---|---|",
        ]
        for page in quad_pages:
            path = page["path"]
            lines.append(f"| [`{path}`]({path}) | {page['owner']} | {page['kind']} |")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def _extract_registry_section(map_md_text: str) -> str | None:
    """Text strictly between the begin/end markers, or ``None`` when either
    marker is absent -- itself a mismatch, per the story's own I/O matrix."""
    begin_idx = map_md_text.find(_REGISTRY_BEGIN)
    if begin_idx == -1:
        return None
    begin_line_end = map_md_text.find("\n", begin_idx)
    if begin_line_end == -1:
        return None
    end_idx = map_md_text.find(_REGISTRY_END, begin_line_end)
    if end_idx == -1:
        return None
    return map_md_text[begin_line_end + 1 : end_idx]


def _check_map_render(target: Path, pages: list[dict]) -> Finding | None:
    map_md_path = target / _MAP_MD_REL
    rendered = render_map_registry(pages)
    if not map_md_path.is_file():
        return Finding(
            source=Source.DOCS_CURRENCY,
            check=_CHECK_MAP_RENDER,
            status=DoctorStatus.WARN,
            message=(
                f"{_MAP_MD_REL} is missing -- cannot compare against "
                f"{_MAP_YAML_REL}'s render"
            ),
            evidence={"path": _MAP_MD_REL},
        )
    current = _extract_registry_section(map_md_path.read_text(encoding="utf-8"))
    if current == rendered:
        return None
    return Finding(
        source=Source.DOCS_CURRENCY,
        check=_CHECK_MAP_RENDER,
        status=DoctorStatus.WARN,
        message=(
            f"{_MAP_MD_REL}'s '## Page registry' section is stale against a "
            f"fresh render of {_MAP_YAML_REL} -- run `pixi run -e "
            "pyforge-guild docs-map-render`"
        ),
        evidence={"markers_present": current is not None},
    )


def _parse_page_frontmatter(text: str) -> dict:
    """Minimal ``---``-fenced YAML frontmatter reader for an authored docs
    page. Deliberately not ``sources/chain.py``'s private frontmatter
    parser (unexported, Dream/Spec-shaped edge cases this module's simple,
    hand-authored docs pages do not need) -- a self-contained reader per
    the story's own Code Map discretion clause."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return {}
    for index in range(1, len(lines)):
        if lines[index].strip() == _FRONTMATTER_FENCE:
            block = "\n".join(lines[1:index])
            try:
                data = yaml.safe_load(block)
            except yaml.YAMLError:
                return {}
            return data if isinstance(data, dict) else {}
    return {}


def _git_last_touch_date(target: Path, rel: str) -> str | None:
    try:
        output = run_git(target, ["log", "-1", "--format=%cs", "--", rel])
    except CliBridgeError:
        return None
    date = output.strip()
    return date or None


def _stale_sources(target: Path, frontmatter: dict) -> list[dict]:
    verified = frontmatter.get("verified")
    sources = frontmatter.get("sources")
    if not verified or not isinstance(sources, list):
        return []
    verified_s = str(verified)
    stale: list[dict] = []
    for source in sources:
        if not isinstance(source, str):
            continue
        touched = _git_last_touch_date(target, source)
        if touched is not None and touched > verified_s:
            stale.append(
                {"source": source, "source_touched": touched, "verified": verified_s}
            )
    return stale


def _pixi_identifiers(target: Path) -> frozenset[str]:
    """Task names + dependency names declared in ``pixi.toml``, read as
    text (no TOML parse dependency needed) -- mirrors
    ``scripts/governance_currency_check.py``'s own two helpers, merged."""
    toml_path = target / "pixi.toml"
    if not toml_path.is_file():
        return frozenset()
    text = toml_path.read_text(encoding="utf-8", errors="replace")
    tasks = re.findall(
        r"^\[(?:feature\.[^.]+\.)?tasks\.([A-Za-z0-9._-]+)\]", text, re.M
    )
    deps = re.findall(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*=", text, re.M)
    return frozenset(tasks) | frozenset(deps)


def _is_git_ignored(target: Path, rel: str) -> bool:
    try:
        run_git(target, ["check-ignore", "-q", rel])
        return True
    except CliBridgeError:
        return False


def _resolves_as_identifier(target: Path, name: str, pixi_ids: frozenset[str]) -> bool:
    skill_dir = target / ".claude" / "skills" / name
    if skill_dir.is_dir() and any(skill_dir.rglob("SKILL.md")):
        return True
    if (target / "scripts" / name).exists() or (target / "scripts" / f"{name}.py").exists():
        return True
    return name in pixi_ids


def _dead_references(target: Path, text: str) -> list[str]:
    pixi_ids = _pixi_identifiers(target)
    dead: list[str] = []
    seen: set[str] = set()
    for match in _SKILL_RE.finditer(text):
        name = match.group(1)
        if name in seen:
            continue
        if not _resolves_as_identifier(target, name, pixi_ids):
            dead.append(name)
            seen.add(name)
    for match in _SCRIPT_RE.finditer(text):
        ref = match.group(1)
        if ref in seen:
            continue
        if not (target / ref).exists() and not _is_git_ignored(target, ref):
            dead.append(ref)
            seen.add(ref)
    for match in _PATH_RE.finditer(text):
        ref = match.group(1).rstrip("/")
        if ref in seen or "*" in ref or "<" in ref:
            continue
        if not (target / ref).exists() and not _is_git_ignored(target, ref):
            dead.append(ref)
            seen.add(ref)
    return dead


def _check_authored_page(target: Path, page: dict) -> Finding | None:
    rel = f"docs/{page['path']}"
    page_path = target / rel
    if not page_path.is_file():
        return None  # a missing page is docs-map-hygiene's territory
    text = page_path.read_text(encoding="utf-8")
    stale = _stale_sources(target, _parse_page_frontmatter(text))
    dead = _dead_references(target, text)
    if not stale and not dead:
        return None
    evidence: dict = {"page": rel}
    parts: list[str] = []
    if stale:
        evidence["stale_sources"] = stale
        parts.append(f"{len(stale)} stale source(s)")
    if dead:
        evidence["dead_references"] = dead
        parts.append(f"{len(dead)} dead reference(s)")
    return Finding(
        source=Source.DOCS_CURRENCY,
        check=_CHECK_AUTHORED_STALE,
        status=DoctorStatus.WARN,
        message=f"{rel}: " + ", ".join(parts),
        evidence=evidence,
    )


def _check_authored_pages(target: Path, pages: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    for page in pages:
        if page["kind"] != "authored":
            continue
        finding = _check_authored_page(target, page)
        if finding is not None:
            findings.append(finding)
    return findings


def _skill_dir_stray_paths(target: Path) -> list[str]:
    skills_dir = target / ".claude" / "skills"
    if not skills_dir.is_dir():
        return []
    stray: list[str] = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir() or not entry.name.startswith(_MANAGED_SKILL_PREFIXES):
            continue
        for child in sorted(entry.iterdir()):
            if child.name in _SKILL_DIR_STRAY_NAMES:
                stray.append(f".claude/skills/{entry.name}/{child.name}")
    return stray


def _check_skill_dir_hygiene(target: Path) -> Finding | None:
    stray = _skill_dir_stray_paths(target)
    if not stray:
        return None
    return Finding(
        source=Source.DOCS_CURRENCY,
        check=_CHECK_SKILL_DIR_HYGIENE,
        status=DoctorStatus.WARN,
        message=(
            f"{len(stray)} stray non-layout file(s) inside managed "
            "bmad-*/pyforge-*/skf-* skill directories"
        ),
        evidence={"paths": stray},
    )


def _gather_all(target: Path) -> tuple[Finding, ...]:
    map_data = load_map_yaml(target)
    pages = map_data.get("pages", [])

    findings: list[Finding] = []

    render_finding = _check_map_render(target, pages)
    if render_finding is not None:
        findings.append(render_finding)

    findings.extend(_check_authored_pages(target, pages))

    hygiene_finding = _check_skill_dir_hygiene(target)
    if hygiene_finding is not None:
        findings.append(hygiene_finding)

    if findings:
        return tuple(findings)

    return (
        Finding(
            source=Source.DOCS_CURRENCY,
            check=_CHECK_OK,
            status=DoctorStatus.OK,
            message=(
                f"{_MAP_MD_REL}'s Page registry matches {_MAP_YAML_REL}'s "
                "render; every authored page's declared sources/body "
                "references resolve; no stray files in managed skill "
                "directories"
            ),
            evidence={"pages_checked": len(pages)},
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Documentation currency gather -- Story 30.2 / spec-pyforge-doctor CAP-84.

    Fail-open: a missing/unreadable/schema-invalid docs/map.yaml degrades
    to exactly one WARN (never FAIL, never a crash) via
    degrade_on_exception.
    """
    return degrade_on_exception(
        Source.DOCS_CURRENCY,
        _CHECK_MAP_UNREADABLE,
        lambda: _gather_all(target),
    )
