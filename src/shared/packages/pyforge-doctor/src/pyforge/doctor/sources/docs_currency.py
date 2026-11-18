"""Documentation currency gather (Story 30.2, ``spec-pyforge-doctor`` CAP-84).

Read-only checks over ``docs/map.yaml`` (the machine registry) and
``docs/MAP.md`` (its render). The registry is enforced (2026-11-17): every
check that measured a real defect reads FAIL -- an unstamped authored page, a
stale or missing source, a dead reference, a stale generated page, a stale
MAP.md render. A check that could not measure (no MAP.md to compare, a
generator that cannot run, git or ``pixi.toml`` unreadable, the map itself
unreadable) stays WARN, and ``skill-dir-hygiene`` stays WARN.

* ``map-render`` (``docs-currency-map-render``) -- ``docs/MAP.md``'s
  generated ``## Page registry`` section (bounded by the
  ``docs-map:registry:begin``/``docs-map:registry:end`` markers)
  byte-matches a fresh :func:`render_map_registry` of ``docs/map.yaml``'s
  pages. Markers absent from MAP.md counts as a mismatch too. A mismatch
  is FAIL; a missing MAP.md (nothing to compare) is one WARN.
* ``authored-unstamped`` (``docs-currency-authored-unstamped``) -- every
  ``kind: authored`` page carries a stamp in its OWN frontmatter:
  ``verified:`` (an ISO date) and a non-empty ``sources:`` list of
  repo-relative paths. A page missing either is one FAIL naming the page
  and what is missing. One exemption, declared on the page and never
  here: a page whose currency its own detector owns carries
  ``checked_by: <pixi task name>`` instead (``docs/reference/library-llms-full.md``,
  owned by ``llms-full-check``). The name must be a task ``pixi.toml``
  declares (``[tasks]`` or any ``[feature.<f>.tasks]``); one that is not is
  the same FAIL, saying why. A ``checked_by`` page is not read for stale
  sources; its body still gets the dead-reference scan.
* ``authored-page-stale`` (``docs-currency-authored-stale``) -- for each
  ``kind: authored`` page, one FAIL carrying either or both evidence
  kinds: (a) a ``sources:`` entry whose git last-touch date is LATER than
  ``verified:`` is stale (a source touched on the ``verified:`` date
  itself is current); an entry that does not exist in the tree
  (``reason: "source does not exist"`` -- a typo, or a path that moved),
  one that is not a repo-relative path, and one git has no history for
  (``reason: "source not found in git history"`` -- untracked or ignored,
  so it can never be measured) are flagged too, never silently treated
  as current; (b) the page body is scanned for
  backticked ``bmad-*``/
  ``skf-*`` skill names, ``scripts/``/``_bmad/``-rooted ``.py`` paths, and
  repo-relative paths under a real top-level directory that no longer
  resolve -- mirrors ``scripts/governance_currency_check.py``'s three
  regexes and its ``_resolves_as_identifier``/existence-check logic,
  duplicated here deliberately (``pyforge.doctor`` cannot import from the
  top-level ``scripts/`` tree). A page's body has the SAME
  ``<!-- governance-currency:ignore-start (reason) -->`` /
  ``<!-- governance-currency:ignore-end -->`` escape hatch honored
  (reused verbatim, not a second marker convention -- ``test-charter.md``
  already carries live instances of it for exactly this class of
  deliberate historical citation, predating this story).
* ``generated-page-stale`` (``docs-currency-generated-stale``, Story 30.3,
  ``spec-pyforge-doctor`` CAP-84; generator trust Story 40.2) -- for each
  ``kind: generated`` page that declares a ``generator:`` (a repo-relative
  ``scripts/docs_*.py`` path with no ``..``), runs **Doctor's own checkout
  copy** of that script via :func:`.locate_checkout_script` (Story 40.1's
  pattern -- never ``target / generator``) with ``--check --root <target>``
  so the judged tree supplies only data. The exit code is the verdict: 0
  means current, 1 is one stale FAIL naming the page, and any other exit,
  or an exit 1 whose output carries a Python traceback (a crash), is one
  could-not-run WARN on the same check (Story 30.5; only
  ``scripts/docs_bmad_estate.py`` exits 2 by design, and argparse exits 2
  on a usage error). Declared paths
  outside ``scripts/docs_*.py`` or carrying ``..`` are one WARN and never
  run. When Doctor's checkout lacks the script, one WARN reports it and
  nothing falls back to the target's copy. A page with no ``generator:``
  declared is ALSO one WARN (a registry gap, not silently skipped); a
  missing PAGE (not yet ever generated) is skipped here --
  ``docs-map-hygiene``'s territory.
* ``skill-dir-hygiene`` (``docs-currency-skill-dir-hygiene``) -- a stray
  file inside a managed ``bmad-*``/``pyforge-*``/``skf-*`` skill
  directory. WARN.

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
:func:`.degrade_on_exception` -- never a FAIL, never a crash. The same holds
when git cannot answer for a source's last touch (not a repository, no
commits, a timeout) or ``pixi.toml`` does not parse while a page names a
``checked_by`` task: the gather could not measure, so it reads one WARN
rather than one FAIL per page.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Callable
from datetime import date, datetime
from importlib import resources
from pathlib import Path

import jsonschema
import yaml

from ..cli_bridge import CliBridgeError, run_check_script, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception, locate_checkout_script

__all__ = (
    "gather",
    "load_map_yaml",
    "render_map_registry",
    "splice_registry_section",
)

_CHECK_MAP_RENDER = "docs-currency-map-render"
_CHECK_AUTHORED_STALE = "docs-currency-authored-stale"
_CHECK_AUTHORED_UNSTAMPED = "docs-currency-authored-unstamped"
_CHECK_GENERATED_STALE = "docs-currency-generated-stale"
_CHECK_SKILL_DIR_HYGIENE = "docs-currency-skill-dir-hygiene"
_CHECK_MAP_UNREADABLE = "docs-currency-map-unreadable"
_CHECK_OK = "docs-currency-ok"

_GENERATOR_CHECK_TIMEOUT = 60.0
# An uncaught exception exits 1, the generators' stale code; its traceback tells the crash apart (Story 30.5).
_TRACEBACK = "Traceback (most recent call last)"

_ALLOWED_DOCS_GENERATOR_DIR = "scripts"
_ALLOWED_DOCS_GENERATOR_PREFIX = "docs_"


def _is_allowed_docs_generator_decl(generator: str) -> bool:
    """True when ``generator`` is a repo-relative ``scripts/docs_*.py`` with no ``..``."""
    path = Path(generator)
    if ".." in path.parts or path.is_absolute():
        return False
    if len(path.parts) != 2:
        return False
    if path.parts[0] != _ALLOWED_DOCS_GENERATOR_DIR:
        return False
    name = path.parts[1]
    return name.startswith(_ALLOWED_DOCS_GENERATOR_PREFIX) and name.endswith(".py")


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
_CHECKED_BY_KEY = "checked_by"
_PIXI_TOML_REL = "pixi.toml"

# Mirrors scripts/governance_currency_check.py's three regexes exactly --
# duplicated deliberately (pyforge.doctor cannot import scripts/).
_SKILL_RE = re.compile(r"`((?:bmad|skf)-[a-z0-9][a-z0-9-]*)`")
_SCRIPT_RE = re.compile(r"`((?:scripts|_bmad)/[A-Za-z0-9._/-]+\.py)`")
_PATH_RE = re.compile(r"`((?:docs|src|recipes|_bmad-output|\.github|\.claude)/[A-Za-z0-9._/-]+)`")

# Same escape hatch as scripts/governance_currency_check.py, reused verbatim
# (one marker convention repo-wide, not a second `docs-currency:ignore-*`
# one) -- a deliberate historical citation ("quoted because it was
# removed") wraps in this, never a heuristic.
_IGNORE_START = re.compile(r"<!--\s*governance-currency:ignore-start")
_IGNORE_END = re.compile(r"<!--\s*governance-currency:ignore-end")

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
    schema_text = resources.files("pyforge.doctor").joinpath("data", "docs-map-schema.json").read_text(encoding="utf-8")
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


def _find_registry_bounds(text: str) -> tuple[int, int] | None:
    """Return ``(content_start, content_end)`` -- the index range strictly
    between the begin/end markers -- or ``None`` when either marker is
    absent. The ONE bounds-finder :func:`_extract_registry_section` (read
    side, this module's own ``map-render`` check) and
    :func:`splice_registry_section` (write side,
    ``scripts/docs_map_render.py``) both call, so the two can never
    independently drift on what counts as "the markers"."""
    begin_idx = text.find(_REGISTRY_BEGIN)
    if begin_idx == -1:
        return None
    begin_line_end = text.find("\n", begin_idx)
    if begin_line_end == -1:
        return None
    end_idx = text.find(_REGISTRY_END, begin_line_end)
    if end_idx == -1:
        return None
    return begin_line_end + 1, end_idx


def _extract_registry_section(map_md_text: str) -> str | None:
    """Text strictly between the begin/end markers, or ``None`` when either
    marker is absent -- itself a mismatch, per the story's own I/O matrix."""
    bounds = _find_registry_bounds(map_md_text)
    if bounds is None:
        return None
    start, end = bounds
    return map_md_text[start:end]


def splice_registry_section(map_md_text: str, replacement: str) -> str | None:
    """Replace the text strictly between the begin/end markers with
    ``replacement``; the write side's half of the same marker contract
    :func:`_extract_registry_section` reads. Returns ``None`` when either
    marker is absent -- the caller (``scripts/docs_map_render.py``) treats
    that as an error, never a silent partial write."""
    bounds = _find_registry_bounds(map_md_text)
    if bounds is None:
        return None
    start, end = bounds
    return map_md_text[:start] + replacement + map_md_text[end:]


def _check_map_render(target: Path, pages: list[dict]) -> Finding | None:
    map_md_path = target / _MAP_MD_REL
    rendered = render_map_registry(pages)
    if not map_md_path.is_file():
        return Finding(
            source=Source.DOCS_CURRENCY,
            check=_CHECK_MAP_RENDER,
            status=DoctorStatus.WARN,
            message=(f"{_MAP_MD_REL} is missing -- cannot compare against {_MAP_YAML_REL}'s render"),
            evidence={"path": _MAP_MD_REL},
        )
    current = _extract_registry_section(map_md_path.read_text(encoding="utf-8"))
    if current == rendered:
        return None
    return Finding(
        source=Source.DOCS_CURRENCY,
        check=_CHECK_MAP_RENDER,
        status=DoctorStatus.FAIL,
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
    """The committer date (``YYYY-MM-DD``) of the last commit touching ``rel``, or ``None`` when git has no
    history for it. Raises :class:`CliBridgeError` when git cannot answer at all (not a repository, no commits,
    a timeout): that is could-not-measure, and :func:`gather` degrades it to one WARN."""
    output = run_git(target, ["log", "-1", "--format=%cs", "--", rel])
    return output.strip() or None


def _verified_date(value: object) -> str | None:
    """``verified:`` as an ISO date string, or ``None`` when it is absent or not a date."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()).isoformat()
        except ValueError:
            return None
    return None


def _declared_sources(frontmatter: dict) -> list[str]:
    sources = frontmatter.get("sources")
    if not isinstance(sources, list):
        return []
    return [source for source in sources if isinstance(source, str) and source.strip()]


def _stale_sources(target: Path, sources: list[str], verified: str) -> list[dict]:
    stale: list[dict] = []
    for source in sources:
        path = Path(source)
        if path.is_absolute() or ".." in path.parts:
            stale.append({"source": source, "reason": "source is not a repo-relative path", "verified": verified})
            continue
        if not (target / source).exists():
            # A typo, or a path that moved: a STRONGER signal than mere staleness.
            stale.append({"source": source, "reason": "source does not exist", "verified": verified})
            continue
        touched = _git_last_touch_date(target, source)
        if touched is None:
            # On disk but untracked or ignored: git can never say it moved past the stamp, so it is flagged
            # rather than "we cannot prove it's stale" being read as "it's current".
            stale.append({"source": source, "reason": "source not found in git history", "verified": verified})
        elif touched > verified:
            # Strictly later: a source touched on the verified date itself is current.
            stale.append({"source": source, "source_touched": touched, "verified": verified})
    return stale


def _pixi_task_names(target: Path) -> frozenset[str] | None:
    """Every task ``pixi.toml`` declares (``[tasks]`` and each ``[feature.<f>.tasks]``), or ``None`` when the
    file does not exist. A file that does not parse raises (``tomllib.TOMLDecodeError``): could-not-measure."""
    toml_path = target / _PIXI_TOML_REL
    if not toml_path.is_file():
        return None
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    tables = [data, *(feature for feature in _as_dict(data.get("feature")).values())]
    for table in tables:
        names.update(_as_dict(_as_dict(table).get("tasks")))
    return frozenset(names)


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _checked_by_problem(checked_by: object, task_names: Callable[[], frozenset[str] | None]) -> str | None:
    """Why ``checked_by:`` does not name a pixi task, or ``None`` when it does."""
    if not isinstance(checked_by, str) or not checked_by.strip():
        return f"`{_CHECKED_BY_KEY}: {checked_by!r}` is not a task name"
    names = task_names()
    if names is None:
        return f"`{_CHECKED_BY_KEY}: {checked_by}` cannot resolve -- {_PIXI_TOML_REL} does not exist"
    if checked_by.strip() not in names:
        return f"`{_CHECKED_BY_KEY}: {checked_by}` names no task in {_PIXI_TOML_REL}"
    return None


def _pixi_identifiers(target: Path) -> frozenset[str]:
    """Task names + dependency names declared in ``pixi.toml``, read as
    text (no TOML parse dependency needed) -- mirrors
    ``scripts/governance_currency_check.py``'s own two helpers, merged."""
    toml_path = target / "pixi.toml"
    if not toml_path.is_file():
        return frozenset()
    text = toml_path.read_text(encoding="utf-8", errors="replace")
    tasks = re.findall(r"^\[(?:feature\.[^.]+\.)?tasks\.([A-Za-z0-9._-]+)\]", text, re.M)
    deps = re.findall(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*=", text, re.M)
    return frozenset(tasks) | frozenset(deps)


def _is_git_ignored(target: Path, rel: str, *, directory: bool = False) -> bool:
    """``git check-ignore`` for ``rel``; when the page wrote it with a trailing ``/``, retried as ``rel/``
    (Story 30.5): git cannot tell an absent path is a directory, so a directory-only rule
    (``docs/dashboard/kedro-viz/``) matches only the slashed form. A reference written without the slash is
    not retried, so a deleted file whose name a directory-only rule (``build/``) matches still reads dead."""
    for candidate in (rel, f"{rel}/") if directory else (rel,):
        try:
            run_git(target, ["check-ignore", "-q", candidate])
            return True
        except CliBridgeError:
            continue
    return False


def _resolves_as_identifier(target: Path, name: str, pixi_ids: frozenset[str]) -> bool:
    """A ``bmad-*``/``skf-*`` token names a skill, a script, a pixi task or dependency, or a detector
    whose pixi task is ``<token>-check`` (Story 30.5: ``bmad-output-hygiene`` is a Doctor source)."""
    skill_dir = target / ".claude" / "skills" / name
    if skill_dir.is_dir() and any(skill_dir.rglob("SKILL.md")):
        return True
    if (target / "scripts" / name).exists() or (target / "scripts" / f"{name}.py").exists():
        return True
    return name in pixi_ids or f"{name}-check" in pixi_ids


def _strip_ignored(text: str) -> str:
    """Blank out ``governance-currency:ignore-start/end``-marked regions,
    preserving line count (so offsets stay meaningful) -- verbatim port of
    ``scripts/governance_currency_check.py``'s own helper."""
    out: list[str] = []
    skipping = False
    for line in text.splitlines():
        if _IGNORE_START.search(line):
            skipping = True
            out.append("")
            continue
        if _IGNORE_END.search(line):
            skipping = False
            out.append("")
            continue
        out.append("" if skipping else line)
    return "\n".join(out)


def _dead_references(target: Path, text: str) -> list[str]:
    text = _strip_ignored(text)
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
        written = match.group(1)
        ref = written.rstrip("/")
        if ref in seen or "*" in ref or "<" in ref:
            continue
        if not (target / ref).exists() and not _is_git_ignored(target, ref, directory=written.endswith("/")):
            dead.append(ref)
            seen.add(ref)
    return dead


def _unstamped_finding(rel: str, message: str, evidence: dict) -> Finding:
    return Finding(
        source=Source.DOCS_CURRENCY,
        check=_CHECK_AUTHORED_UNSTAMPED,
        status=DoctorStatus.FAIL,
        message=f"{rel}: {message}",
        evidence={"page": rel, **evidence},
    )


def _check_authored_page(target: Path, page: dict, task_names: Callable[[], frozenset[str] | None]) -> list[Finding]:
    rel = f"docs/{page['path']}"
    page_path = target / rel
    if not page_path.is_file():
        return []  # a missing page is docs-map-hygiene's territory
    text = page_path.read_text(encoding="utf-8")
    frontmatter = _parse_page_frontmatter(text)
    findings: list[Finding] = []
    stale: list[dict] = []

    if _CHECKED_BY_KEY in frontmatter:
        # The page declares its own detector owns its currency: no stamp to read, no source to date.
        problem = _checked_by_problem(frontmatter[_CHECKED_BY_KEY], task_names)
        if problem is not None:
            findings.append(
                _unstamped_finding(
                    rel,
                    f"kind: authored page is unstamped -- {problem}",
                    {"reason": problem, _CHECKED_BY_KEY: str(frontmatter[_CHECKED_BY_KEY])},
                )
            )
    else:
        sources = _declared_sources(frontmatter)
        verified = _verified_date(frontmatter.get("verified"))
        missing = [name for name, held in (("sources", sources), ("verified", verified)) if not held]
        if missing:
            findings.append(
                _unstamped_finding(
                    rel,
                    "kind: authored page is unstamped -- its frontmatter needs a non-empty `sources:` list and "
                    f"an ISO-date `verified:` (missing or malformed: {', '.join(missing)}); verify the page "
                    f"and stamp it, or declare `{_CHECKED_BY_KEY}: <pixi task>` when a detector owns its currency",
                    {"missing": missing},
                )
            )
        if sources and verified:
            stale = _stale_sources(target, sources, verified)

    dead = _dead_references(target, text)
    if stale or dead:
        evidence: dict = {"page": rel}
        parts: list[str] = []
        if stale:
            evidence["stale_sources"] = stale
            parts.append(f"{len(stale)} stale source(s)")
        if dead:
            evidence["dead_references"] = dead
            parts.append(f"{len(dead)} dead reference(s)")
        findings.append(
            Finding(
                source=Source.DOCS_CURRENCY,
                check=_CHECK_AUTHORED_STALE,
                status=DoctorStatus.FAIL,
                message=f"{rel}: " + ", ".join(parts),
                evidence=evidence,
            )
        )
    return findings


def _check_authored_pages(target: Path, pages: list[dict]) -> list[Finding]:
    cache: list[frozenset[str] | None] = []

    def task_names() -> frozenset[str] | None:
        # pixi.toml is parsed once, and only when a page names a `checked_by` task.
        if not cache:
            cache.append(_pixi_task_names(target))
        return cache[0]

    findings: list[Finding] = []
    for page in pages:
        if page["kind"] == "authored":
            findings.extend(_check_authored_page(target, page, task_names))
    return findings


def _check_generated_page(target: Path, page: dict) -> Finding | None:
    rel = f"docs/{page['path']}"
    page_path = target / rel
    if not page_path.is_file():
        return None  # never-yet-generated is docs-map-hygiene's territory

    generator = page.get("generator")
    if not generator:
        return Finding(
            source=Source.DOCS_CURRENCY,
            check=_CHECK_GENERATED_STALE,
            status=DoctorStatus.WARN,
            message=(f"{rel}: kind: generated page declares no `generator:` in {_MAP_YAML_REL}"),
            evidence={"page": rel},
        )
    if not _is_allowed_docs_generator_decl(generator):
        return Finding(
            source=Source.DOCS_CURRENCY,
            check=_CHECK_GENERATED_STALE,
            status=DoctorStatus.WARN,
            message=(f"{rel}: declared generator {generator} is not an allowed scripts/docs_*.py path -- not executed"),
            evidence={"page": rel, "generator": generator},
        )

    script_name = Path(generator).name
    try:
        generator_path = locate_checkout_script(script_name)
    except FileNotFoundError as exc:
        return Finding(
            source=Source.DOCS_CURRENCY,
            check=_CHECK_GENERATED_STALE,
            status=DoctorStatus.WARN,
            message=(f"{rel}: could not run generator {generator} -- {exc}"),
            evidence={"page": rel, "generator": generator},
        )

    checkout_root = generator_path.parent.parent
    try:
        returncode, output = run_check_script(
            generator_path,
            ["--check", "--root", str(target.resolve())],
            cwd=checkout_root,
            timeout=_GENERATOR_CHECK_TIMEOUT,
        )
    except CliBridgeError as exc:
        return Finding(
            source=Source.DOCS_CURRENCY,
            check=_CHECK_GENERATED_STALE,
            status=DoctorStatus.WARN,
            message=(f"{rel}: could not run generator {generator} -- {exc}"),
            evidence={"page": rel, "generator": generator},
        )
    if returncode == 0:
        return None
    crashed = returncode == 1 and _TRACEBACK in output
    if returncode != 1 or crashed:
        # A docs generator exits 1 when its page is stale (Story 30.5). Only scripts/docs_bmad_estate.py exits 2
        # by design (pyforge.scribe missing), argparse exits 2 on a usage error, and an uncaught exception exits
        # 1 with a traceback: each is could-not-run, never a hand edit.
        how = "crashed (exit 1 with a traceback)" if crashed else f"exited {returncode}, not 0 or 1"
        return Finding(
            source=Source.DOCS_CURRENCY,
            check=_CHECK_GENERATED_STALE,
            status=DoctorStatus.WARN,
            message=(f"{rel}: could not run generator {generator} -- its --check {how}"),
            evidence={"page": rel, "generator": generator, "exit": returncode, "output": output[-2000:]},
        )
    return Finding(
        source=Source.DOCS_CURRENCY,
        check=_CHECK_GENERATED_STALE,
        status=DoctorStatus.FAIL,
        message=(
            f"{rel}: stale against its generator ({generator}) -- a hand "
            "edit, or a source it derives from moved past its stamp; "
            f"regenerate with the matching guild-tasks pixi task"
        ),
        evidence={"page": rel, "generator": generator, "output": output[-2000:]},
    )


def _check_generated_pages(target: Path, pages: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    for page in pages:
        if page["kind"] != "generated":
            continue
        finding = _check_generated_page(target, page)
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
        message=(f"{len(stray)} stray non-layout file(s) inside managed bmad-*/pyforge-*/skf-* skill directories"),
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
    findings.extend(_check_generated_pages(target, pages))

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
                "render; every authored page is stamped (or names its "
                "detector) and its declared sources/body references "
                "resolve; every generated page matches its generator; no "
                "stray files in managed skill directories"
            ),
            evidence={"pages_checked": len(pages)},
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Documentation currency gather -- Story 30.2 / spec-pyforge-doctor CAP-84.

    A measured defect is FAIL (module docstring). Fail-open: a
    missing/unreadable/schema-invalid docs/map.yaml, unreadable git or an
    unparseable pixi.toml degrades to exactly one WARN (never FAIL, never
    a crash) via degrade_on_exception.
    """
    return degrade_on_exception(
        Source.DOCS_CURRENCY,
        _CHECK_MAP_UNREADABLE,
        lambda: _gather_all(target),
    )
