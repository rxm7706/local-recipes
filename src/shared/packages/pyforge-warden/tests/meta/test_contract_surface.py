"""Story 26.3 (spec-pyforge-warden CAP-28, FR-45; decision D1): the rest of warden's caller-visible surface.

``contract.md`` sections 8 to 11 and *Where each capability lives* are this test's (sections 1 to 7 are
``test_public_contract.py``'s, Story 26.1). Each inventory is derived from the code, never from a hand list,
and compared both ways with its ``contract.md`` table: a code item with no row is ``unlisted``, a row naming
something the code no longer has is a ``stale row``.

Derivation rules, stated so the guard is not blind:

* Hook specs: ``hooks.PR_GATE_HOOK_SPECS`` (name and owner).
* Plugin entry points: the package's own ``pyproject.toml``, group ``hooks.ENTRY_POINT_GROUP`` (the only
  group it may declare); each object is imported and instantiated for its ``scanner_id`` and ``is_default``.
* Optional scanner ids: ``scanner_plugins.OPTIONAL_SCANNER_IDS``; each id's entry point (if any) from the
  entry points above, its plugin class from ``scanner_plugins.scanner_plugin_registry()``.
* The report's open slots: the key sets the builders emit. ``advisory`` records from
  ``sast.parse_opengrep_json`` (an opengrep note) and ``tea_advisory.TeaAdvisoryScanPlugin`` driven through
  its ``runner`` seam (a scored run and a run that skipped); ``actuation`` from ``actuator.Actuation`` built
  once with no optional field and once with every one, walked into one record per nested object or list item.
* Engines: every ``engines.*_VERSION_RANGE`` constant (the name, lower-cased with ``-`` for ``_``) plus
  ``tea_advisory.TEA_TEST_REVIEW_BINARY``, which has no range; its agent is ``engines._TEA_DEFAULT_AGENT``.
* Bundled data: the entries of the package's ``data/`` directory; each one's readers are the kernel modules
  holding the entry's name as an exact string constant.
* Refresh scripts: the package's ``scripts/refresh_*.py``.
* Python import surface, by TEXT, not AST, so subprocess source strings are seen: over every tracked text
  file under ``src/`` and ``scripts/`` outside this package (``git ls-files`` from the repo root), the
  regexes ``FROM_IMPORT`` (a parenthesised list read to its closing bracket, a plain list to the end of its
  line, trailing comments dropped) and ``PLAIN_IMPORT``. ``IMPORT_FIXTURE_FILES`` names the files that only
  quote import lines as fixtures or comments, each with a reason; an entry whose file no longer matches, or
  which really imports ``pyforge.warden`` (an AST import statement), fails.
* Where each capability lives: the CAP ids of ``SPEC.md``; every path a row names exists; each path's
  governing Specs are the ones whose ``surface:`` globs cover it, read from every station Spec's
  ``SPEC.md`` with ``scripts/spec_surface_check.py``'s glob rules; a cited ``spec-x:CAP-n`` must be a
  capability of that Spec.

``contract.md`` is read only through the table rows under its exact headings (below), and only through the
backticked tokens and the plain cells this test names. Every outside path is a ``Path(__file__)``-anchored
constant; the import scan hands the repo root to ``git``, which steward's trigger map declares in
``ROOT_HANDOFF_INPUTS`` (globs ``src/**`` and ``scripts/**``). Negative tests use synthetic inventories and
synthetic file text, never a mutated tracked file.
"""

from __future__ import annotations

import ast
import functools
import importlib
import json
import re
import subprocess
import tomllib
import types
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml
from packaging.specifiers import SpecifierSet

from pyforge.warden import (
    actuator,
    currency,
    engines,
    fix_solver,
    hooks,
    manifest_fixup,
    sast,
    scanner_plugins,
    tea_advisory,
)

pytestmark = pytest.mark.live_tree

# tests/meta -> tests -> pyforge-warden -> packages -> shared -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[6]
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SRC = PACKAGE_ROOT / "src"
KERNEL_DIR = PACKAGE_SRC / "pyforge" / "warden"
DATA_DIR = KERNEL_DIR / "data"
REPORT_SCHEMA = DATA_DIR / "report-schema.json"
CONDA_PYPI_MAP = DATA_DIR / "conda_pypi_map.json"
PACKAGE_SCRIPTS = PACKAGE_ROOT / "scripts"
PYPROJECT = PACKAGE_ROOT / "pyproject.toml"
SPEC_DIR = REPO_ROOT / "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden"
CONTRACT = SPEC_DIR / "contract.md"
SPEC = SPEC_DIR / "SPEC.md"
PROJECTS = REPO_ROOT / "_bmad-output" / "projects"
DJANGO_WARDEN_SRC = REPO_ROOT / "src/shared/packages/django-warden/src"
MCP_MODULE = DJANGO_WARDEN_SRC / "django_warden_fabric" / "mcp_asgi.py"
STATION_API = REPO_ROOT / "src/platform/config/station_api.py"

PACKAGE_REL = PACKAGE_ROOT.relative_to(REPO_ROOT).as_posix()
KERNEL_PREFIX = "pyforge/warden/"
DJANGO_PREFIX = "django_warden_fabric/"
SPEC_GLOB = "*/planning-artifacts/specs/spec-*/SPEC.md"
SCANNED_TREES = ("src", "scripts")

H_HOOKS = "### 8.1 Hook specs"
H_ENTRY_POINTS = "### 8.2 Plugin entry points"
H_OPTIONAL = "### 8.3 Optional scanner ids"
H_SLOTS = "## 9. The report's open slots"
H_ENGINES = "### 10.1 Engines and tested ranges"
H_DATA = "### 10.2 Bundled data"
H_REFRESH = "### 10.3 Refresh scripts"
H_IMPORTS = "## 11. Python import surface"
H_WHERE = "## Where each capability lives"
H_POINTERS = "### What warden does not mint"
H_AS_IS = "### Recorded as-is"

FROM_IMPORT = re.compile(r"""from\s+(pyforge\.warden(?:\.\w+)*)\s+import\s+(\(?[^;"')]+)""")
PLAIN_IMPORT = re.compile(r"import\s+(pyforge\.warden(?:\.\w+)*)")
_PLAIN_NAMES = re.compile(r"""[^;"')#\n\\]*""")  # a plain list ends at its line, a comment or an escape

# The tracked files outside the package that only QUOTE an import line (a negative fixture or a comment);
# each is left out of the import surface. An entry whose file no longer matches the regexes, or that really
# imports pyforge.warden, fails (test_import_allowlist_is_live).
IMPORT_FIXTURE_FILES: dict[str, str] = {
    "src/shared/packages/pyforge-doctor/tests/meta/test_no_warden_import.py": (
        "doctor's AD-3 guard that no doctor module imports warden: the import lines are the strings it parses"
    ),
    "src/shared/packages/pyforge-doctor/tests/meta/test_sources_warden_no_subprocess.py": (
        "doctor's AD-1 guard over sources/warden.py: the import lines are fixture strings and comments"
    ),
    "src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py": (
        "core's leaf guard: `from pyforge.warden import ...` is a docstring example and ast.parse fixtures"
    ),
    "src/shared/packages/pyforge-steward/tests/meta/test_first_portal_slice_provision_list.py": (
        "a comment naming a subprocess import oracle; the file imports nothing from warden"
    ),
    "src/shared/packages/pyforge-steward/tests/meta/test_object_store_seam_boundaries.py": (
        "steward's seam-boundary guard: the import lines are synthetic files it writes to tmp_path"
    ),
}

_TOKEN = re.compile(r"`([^`]+)`")
_CAP = re.compile(r"\bCAP-\d+\b")
_CAP_ROW = re.compile(r"\ACAP-\d+\Z")
_CAP_ID = re.compile(r"(?m)^- \*\*(CAP-\d+) ")
_SPEC_CAP = re.compile(r"\A(spec-[a-z0-9-]+):(CAP-\d+)\Z")
_HEADING = re.compile(r"(#+) ")
_SEPARATOR = re.compile(r"\|[-:| ]+\|")
_NONE = "none"

Problems = list[str]
Slots = dict[str, tuple[frozenset[str], frozenset[str]]]  # record -> (always-present keys, optional keys)
Imports = dict[str, dict[str, set[str]]]  # module -> importer -> names

# ---------------------------------------------------------------------------
# Reading contract.md
# ---------------------------------------------------------------------------


def _section(text: str, heading: str) -> str:
    """The body under ``heading``, up to the next heading of the same or a higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(heading):
            body: list[str] = []
            for following in lines[index + 1 :]:
                match = _HEADING.match(following)
                if match and len(match.group(1)) <= level:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"contract.md has no heading {heading!r}; keep the headings exact")


def _rows(block: str) -> list[list[str]]:
    """Every data row of every table in ``block`` (each table's header and separator skipped)."""
    rows: list[list[str]] = []
    in_table = False
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue
        if not in_table:
            in_table = True  # the header row
            continue
        if _SEPARATOR.fullmatch(stripped):
            continue
        rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
    return rows


def _tokens(cell: str) -> list[str]:
    return _TOKEN.findall(cell)


def _plain(cell: str) -> str:
    return cell.replace("`", "").strip()


def _keyed_rows(text: str, heading: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for cells in _rows(_section(text, heading)):
        for token in _tokens(cells[0]):
            out[token] = cells
    return out


def _both_ways(family: str, derived: Iterable[str], listed: Iterable[str]) -> Problems:
    have, rows = set(derived), set(listed)
    unlisted = [
        f"{family}: unlisted {item!r} (the code has it; contract.md has no row)" for item in sorted(have - rows)
    ]
    stale = [f"{family}: stale row {item!r} (contract.md lists it; the code does not)" for item in sorted(rows - have)]
    return unlisted + stale


def _missing_cap(family: str, rows: Mapping[str, list[str]]) -> Problems:
    return [f"{family}: row {key!r} names no CAP" for key, cells in sorted(rows.items()) if not _CAP.search(cells[-1])]


def _inject_row(text: str, heading: str, row: str) -> str:
    """``text`` with ``row`` added as the first data row of the first table under ``heading`` (in memory)."""
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(heading))
    separator = next(index for index in range(start + 1, len(lines)) if _SEPARATOR.fullmatch(lines[index].strip()))
    return "\n".join([*lines[: separator + 1], row, *lines[separator + 1 :]]) + "\n"


def _repo_path(token: str) -> Path:
    """A path token of contract.md: module paths are relative to their package's ``src/``, the rest to the root."""
    if token.startswith(KERNEL_PREFIX):
        return PACKAGE_SRC / token
    if token.startswith(DJANGO_PREFIX):
        return DJANGO_WARDEN_SRC / token
    return REPO_ROOT / token


def _path_tokens(cell: str) -> list[str]:
    """The backticked tokens of ``cell`` that are paths (not a route, a URL or a literal with spaces)."""
    return [
        token for token in _tokens(cell) if "/" in token and not token.startswith("/") and not {" ", ":"} & set(token)
    ]


# ---------------------------------------------------------------------------
# Section 8: hook specs, plugin entry points, optional scanner ids
# ---------------------------------------------------------------------------


def _hooks_derived() -> dict[str, str]:
    return {spec.name: spec.owner for spec in hooks.PR_GATE_HOOK_SPECS}


def _hooks_problems(derived: Mapping[str, str], text: str) -> Problems:
    rows = _keyed_rows(text, H_HOOKS)
    problems = _both_ways("hook spec", derived, rows) + _missing_cap("hook spec", rows)
    for name in sorted(set(derived) & set(rows)):
        if _tokens(rows[name][1]) != [derived[name]]:
            problems.append(f"hook spec {name!r}: owner row {_tokens(rows[name][1])} != code {derived[name]!r}")
    return problems


def _entry_point_groups() -> dict[str, dict[str, str]]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return {group: dict(points) for group, points in data["project"].get("entry-points", {}).items()}


def _load_plugin(target: str) -> Any:
    module, _, attr = target.partition(":")
    return getattr(importlib.import_module(module), attr)()


@functools.cache
def _entry_points_derived() -> dict[str, tuple[str, str, str]]:
    """Entry point -> (object, scanner id, ``default`` or ``optional``)."""
    out: dict[str, tuple[str, str, str]] = {}
    for name, target in _entry_point_groups().get(hooks.ENTRY_POINT_GROUP, {}).items():
        plugin = _load_plugin(target)
        out[name] = (target, str(plugin.scanner_id), "default" if plugin.is_default else "optional")
    return out


def _entry_points_problems(derived: Mapping[str, tuple[str, str, str]], text: str) -> Problems:
    rows = _keyed_rows(text, H_ENTRY_POINTS)
    problems = _both_ways("plugin entry point", derived, rows) + _missing_cap("plugin entry point", rows)
    for name in sorted(set(derived) & set(rows)):
        target, scanner_id, kind = derived[name]
        listed = (_tokens(rows[name][1]), _tokens(rows[name][2]), _plain(rows[name][3]))
        if listed != ([target], [scanner_id], kind):
            problems.append(f"plugin entry point {name!r}: row {listed} != code {([target], [scanner_id], kind)}")
    return problems


@functools.cache
def _optional_derived() -> dict[str, tuple[tuple[str, ...], str]]:
    """Optional scanner id -> (its entry points, its plugin class in the in-tree registry)."""
    registry = {
        str(getattr(plugin, "scanner_id", plugin.owner)): type(plugin).__name__
        for plugin in scanner_plugins.scanner_plugin_registry().plugins
    }
    by_id: dict[str, list[str]] = {}
    for name, (_target, scanner_id, _kind) in _entry_points_derived().items():
        by_id.setdefault(scanner_id, []).append(name)
    return {
        scanner_id: (tuple(sorted(by_id.get(scanner_id, ()))), registry.get(scanner_id, "<not registered>"))
        for scanner_id in scanner_plugins.OPTIONAL_SCANNER_IDS
    }


def _optional_problems(derived: Mapping[str, tuple[tuple[str, ...], str]], text: str) -> Problems:
    rows = _keyed_rows(text, H_OPTIONAL)
    problems = _both_ways("optional scanner id", derived, rows) + _missing_cap("optional scanner id", rows)
    for scanner_id in sorted(set(derived) & set(rows)):
        points, plugin = derived[scanner_id]
        listed = (tuple(sorted(_tokens(rows[scanner_id][1]))), _tokens(rows[scanner_id][2]))
        if listed != (points, [plugin]):
            problems.append(f"optional scanner id {scanner_id!r}: row {listed} != code {(points, [plugin])}")
    return problems


# ---------------------------------------------------------------------------
# Section 9: the report's open slots
# ---------------------------------------------------------------------------


def _key_paths(payload: object, root: str) -> dict[str, set[str]]:
    """One record per object in ``payload``: ``a.b`` for a nested object, ``a.b[]`` for a list's items."""
    out: dict[str, set[str]] = {}

    def walk(value: object, path: str) -> None:
        if isinstance(value, Mapping):
            out.setdefault(path, set()).update(value)
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for item in value:
                walk(item, f"{path}[]")

    walk(payload, root)
    return out


def _slots_from(minimal: Mapping[str, set[str]], full: Mapping[str, set[str]]) -> Slots:
    out: Slots = {}
    for path, keys in full.items():
        always = minimal.get(path, keys)
        out[path] = (frozenset(always), frozenset(keys - always))
    return out


def _actuation_slots() -> Slots:
    def outcome(**optional: object) -> actuator.PROutcome:
        return actuator.PROutcome(
            finding_id="vuln:GHSA-synthetic:pkg@1.0", action="upgrade", subject="pkg", status="planned", **optional
        )

    resolution = fix_solver.FixTargetResolution(
        target="1.1", candidates=("1.1",), attempts=(("1.1", "accepted"),), solver="pixi"
    )
    manifest_fix = manifest_fixup.ManifestFixPlan(
        files=(manifest_fixup.ManifestFileChange(path="pixi.toml", content=""),)
    )
    minimal = actuator.Actuation(dry_run=True, outcomes=(outcome(),)).to_json_dict()
    full = actuator.Actuation(
        dry_run=True,
        outcomes=(outcome(fix_resolution=resolution, manifest_fix=manifest_fix, ecosystem="npm"),),
    ).to_json_dict()
    return _slots_from(_key_paths(minimal, "actuation"), _key_paths(full, "actuation"))


def _scored_tea_run(_target: Path, json_path: Path) -> object:
    json_path.write_text(json.dumps({"qualityScore": 90, "recommendation": "approve"}), encoding="utf-8")
    return types.SimpleNamespace(returncode=0)


def _skipped_tea_run(_target: Path, _json_path: Path) -> object:
    return types.SimpleNamespace(returncode=3)  # an exit outside {0, 1}: started, no trusted verdict


def _advisory_label(note: Mapping[str, object]) -> str:
    return f"advisory[] ({note['tool']}, skipped)" if note.get("skipped") else f"advisory[] ({note['tool']})"


def _advisory_slots() -> Slots:
    opengrep_json = {
        "results": [{"check_id": "rule", "path": "a.py", "start": {"line": 1}, "extra": {"severity": "x"}}]
    }
    notes, error = sast.parse_opengrep_json(json.dumps(opengrep_json))
    assert error is None and notes, "the synthetic opengrep run built no note"
    records: list[Mapping[str, object]] = [notes[0].to_dict()]
    for runner in (_scored_tea_run, _skipped_tea_run):
        context: dict[str, Any] = {"enabled_optional": (tea_advisory.TEA_TEST_REVIEW_BINARY,), "target": Path("t")}
        tea_advisory.TeaAdvisoryScanPlugin(runner=runner).call("around", context)
        records.extend(context["advisory_notes"])
    return {_advisory_label(note): (frozenset(note), frozenset()) for note in records}


@functools.cache
def _live_slots() -> Slots:
    return {**_advisory_slots(), **_actuation_slots()}


def _slots_problems(derived: Mapping[str, tuple[frozenset[str], frozenset[str]]], text: str) -> Problems:
    rows = _keyed_rows(text, H_SLOTS)
    problems = _both_ways("open-slot record", derived, rows)
    for record in sorted(set(derived) & set(rows)):
        always, optional = derived[record]
        listed_always, listed_optional = set(_tokens(rows[record][1])), set(_tokens(rows[record][2]))
        problems += _both_ways(f"open-slot record {record!r} key", always, listed_always)
        problems += _both_ways(f"open-slot record {record!r} optional key", optional, listed_optional)
        if not any(_repo_path(token).is_file() for token in _path_tokens(rows[record][3])):
            problems.append(f"open-slot record {record!r}: its builder cell names no module that exists")
    return problems


# ---------------------------------------------------------------------------
# Section 10: engines, bundled data, refresh scripts
# ---------------------------------------------------------------------------


def _engines_derived() -> dict[str, str | None]:
    out: dict[str, str | None] = {
        name.removesuffix("_VERSION_RANGE").lower().replace("_", "-"): str(value)
        for name, value in vars(engines).items()
        if name.endswith("_VERSION_RANGE") and isinstance(value, SpecifierSet)
    }
    out[tea_advisory.TEA_TEST_REVIEW_BINARY] = None
    return out


def _engines_problems(derived: Mapping[str, str | None], text: str) -> Problems:
    rows = _keyed_rows(text, H_ENGINES)
    problems = _both_ways("engine", derived, rows) + _missing_cap("engine", rows)
    for engine in sorted(set(derived) & set(rows)):
        expected, listed = derived[engine], _tokens(rows[engine][1])
        if expected is None:
            if listed or _plain(rows[engine][1]) != _NONE:
                problems.append(f"engine {engine!r}: the code has no tested range; the row says {rows[engine][1]!r}")
        elif len(listed) != 1 or SpecifierSet(listed[0]) != SpecifierSet(expected):
            problems.append(f"engine {engine!r}: range row {listed} != code {expected!r}")
    return problems


def _data_entries() -> list[str]:
    return sorted(f"{path.name}/" if path.is_dir() else path.name for path in DATA_DIR.iterdir())


def _data_derived(entries: Iterable[str]) -> dict[str, set[str]]:
    """Each bundled data entry -> the kernel modules holding its name as an exact string constant."""
    trees = {
        f"{KERNEL_PREFIX}{path.relative_to(KERNEL_DIR).as_posix()}": ast.parse(path.read_text(encoding="utf-8"))
        for path in sorted(KERNEL_DIR.rglob("*.py"))
    }
    out: dict[str, set[str]] = {}
    for entry in entries:
        name = entry.rstrip("/")
        out[entry] = {
            module
            for module, tree in trees.items()
            if any(isinstance(node, ast.Constant) and node.value == name for node in ast.walk(tree))
        }
    return out


def _data_problems(derived: Mapping[str, set[str]], text: str) -> Problems:
    rows = _keyed_rows(text, H_DATA)
    problems = _both_ways("bundled data", derived, rows) + _missing_cap("bundled data", rows)
    for entry in sorted(set(derived) & set(rows)):
        if set(_tokens(rows[entry][2])) != derived[entry]:
            problems.append(f"bundled data {entry!r}: reader row {sorted(_tokens(rows[entry][2]))} != code")
    return problems


def _refresh_derived() -> set[str]:
    return {path.relative_to(REPO_ROOT).as_posix() for path in PACKAGE_SCRIPTS.glob("refresh_*.py")}


def _refresh_problems(derived: Iterable[str], text: str) -> Problems:
    rows = _keyed_rows(text, H_REFRESH)
    return _both_ways("refresh script", derived, rows) + _missing_cap("refresh script", rows)


# ---------------------------------------------------------------------------
# Section 11: the Python import surface (by text)
# ---------------------------------------------------------------------------


def _from_names(text: str, start: int) -> list[str]:
    """The names a from-import's list names, from its first character at ``start``."""
    if text.startswith("(", start):
        body: list[str] = []
        for line in text[start + 1 :].splitlines():
            code = line.split("#", 1)[0]
            if ")" in code:
                body.append(code.split(")", 1)[0])
                break
            body.append(code)
        listing = ",".join(body)
    else:
        match = _PLAIN_NAMES.match(text, start)
        listing = match.group(0) if match else ""
    names: list[str] = []
    for part in listing.split(","):
        words = part.split()
        if words and (words[0].isidentifier() or words[0] == "*"):
            names.append(words[0])
    return names


def _import_surface(texts: Mapping[str, str]) -> Imports:
    out: Imports = {}
    for rel, text in texts.items():
        position = 0
        while match := FROM_IMPORT.search(text, position):
            out.setdefault(match.group(1), {}).setdefault(rel, set()).update(_from_names(text, match.start(2)))
            position = match.start(2)
        for match in PLAIN_IMPORT.finditer(text):
            out.setdefault(match.group(1), {}).setdefault(rel, set())
    return out


@functools.cache
def _tracked_texts() -> Mapping[str, str]:
    """Every tracked text file under ``src/`` and ``scripts/`` outside the package that names pyforge.warden."""
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--", *SCANNED_TREES], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout
    out: dict[str, str] = {}
    for rel in sorted(filter(None, listing.split("\0"))):
        path = REPO_ROOT / rel
        if rel.startswith(f"{PACKAGE_REL}/") or not path.is_file():
            continue
        raw = path.read_bytes()
        if b"\0" in raw or b"pyforge.warden" not in raw:
            continue
        try:
            out[rel] = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
    return out


def _surface_texts(texts: Mapping[str, str], allowlist: Mapping[str, str]) -> dict[str, str]:
    return {rel: text for rel, text in texts.items() if rel not in allowlist}


def _live_imports() -> Imports:
    return _import_surface(_surface_texts(_tracked_texts(), IMPORT_FIXTURE_FILES))


def _imports_problems(derived: Imports, text: str) -> Problems:
    rows = _keyed_rows(text, H_IMPORTS)
    problems = _both_ways("imported module", derived, rows)
    for module in sorted(set(derived) & set(rows)):
        names = set().union(*derived[module].values())
        problems += _both_ways(f"imported module {module!r} name", names, _tokens(rows[module][1]))
        problems += _both_ways(f"imported module {module!r} importer", derived[module], _tokens(rows[module][2]))
    return problems


def _real_warden_imports(text: str) -> list[int]:
    """Line numbers of real (AST) import statements of pyforge.warden in ``text``; [] when it does not parse."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("pyforge.warden"):
            lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.module == "pyforge":
            lines += [node.lineno for alias in node.names if alias.name == "warden"]
        elif isinstance(node, ast.Import):
            lines += [node.lineno for alias in node.names if alias.name.startswith("pyforge.warden")]
    return sorted(lines)


def _allowlist_problems(texts: Mapping[str, str], allowlist: Mapping[str, str]) -> Problems:
    problems: Problems = []
    for rel, reason in sorted(allowlist.items()):
        if not reason.strip():
            problems.append(f"import allowlist entry {rel!r} carries no reason")
        text = texts.get(rel)
        if text is None:
            problems.append(f"stale allowlist entry {rel!r}: not a tracked text file that names pyforge.warden")
            continue
        if not (FROM_IMPORT.search(text) or PLAIN_IMPORT.search(text)):
            problems.append(f"stale allowlist entry {rel!r}: it no longer quotes a pyforge.warden import line")
        real = _real_warden_imports(text)
        if real:
            problems.append(f"allowlist entry {rel!r} really imports pyforge.warden (lines {real}); give it a row")
    return problems


# ---------------------------------------------------------------------------
# Where each capability lives
# ---------------------------------------------------------------------------


def _glob_to_re(pattern: str) -> re.Pattern[str]:
    """``scripts/spec_surface_check.py``'s ``glob_to_re``, restated (a trailing-slash entry governs its subtree)."""
    if pattern.endswith("/") and not ({"*", "?"} & set(pattern)):
        pattern += "**"
    out, index = [], 0
    while index < len(pattern):
        if pattern[index : index + 2] == "**":
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return re.compile("^" + "".join(out) + "$")


@functools.cache
def _station_specs() -> Mapping[str, tuple[tuple[re.Pattern[str], ...], frozenset[str]]]:
    """Every station Spec: its ``surface:`` globs and its capability ids."""
    out: dict[str, tuple[tuple[re.Pattern[str], ...], frozenset[str]]] = {}
    for path in sorted(PROJECTS.glob(SPEC_GLOB)):
        text = path.read_text(encoding="utf-8")
        front = yaml.safe_load(text.split("---", 2)[1]) if text.startswith("---") else {}
        surface = [str(glob) for glob in (front or {}).get("surface") or []]
        out[path.parent.name] = (tuple(map(_glob_to_re, surface)), frozenset(_CAP_ID.findall(text)))
    return out


def _governors(rel: str, specs: Mapping[str, tuple[tuple[re.Pattern[str], ...], frozenset[str]]]) -> set[str]:
    return {name for name, (globs, _caps) in specs.items() if any(glob.match(rel) for glob in globs)}


def _representative(path: Path) -> Path | None:
    """The path itself, or a file under a named directory (what a surface glob is matched against)."""
    if path.is_file():
        return path
    if path.is_dir():
        return next((child for child in sorted(path.rglob("*")) if child.is_file()), None)
    return None


def _where_rows(text: str) -> dict[str, list[str]]:
    return {_plain(cells[0]): cells for cells in _rows(_section(text, H_WHERE)) if _CAP_ROW.match(_plain(cells[0]))}


def _where_problems(
    caps: Iterable[str],
    specs: Mapping[str, tuple[tuple[re.Pattern[str], ...], frozenset[str]]],
    text: str,
) -> Problems:
    rows = _where_rows(text)
    problems = _both_ways("capability", caps, rows)
    for cap, cells in sorted(rows.items()):
        paths = _path_tokens(cells[1])
        if not paths:
            problems.append(f"capability {cap}: the row names no code path")
        named = {token for token in _tokens(cells[2]) if token.startswith("spec-")}
        none_marked = _NONE in _tokens(cells[2])
        governed: set[str] = set()
        ungoverned: list[str] = []
        for token in paths:
            found = _representative(_repo_path(token))
            if found is None:
                problems.append(f"capability {cap}: dead path {token!r}")
                continue
            owners = _governors(found.relative_to(REPO_ROOT).as_posix(), specs)
            governed |= owners
            if not owners:
                ungoverned.append(token)
            elif not owners & named:
                problems.append(f"capability {cap}: {token!r} is governed by {sorted(owners)}, the row names none")
        problems += [
            f"capability {cap}: stale row governor {name!r} (it governs no path the row names)"
            for name in sorted(named - governed)
        ]
        if ungoverned and not none_marked:
            problems.append(f"capability {cap}: {ungoverned} is on no Spec's surface; the row must say `{_NONE}`")
        if none_marked and not ungoverned:
            problems.append(f"capability {cap}: stale row `{_NONE}` (every path it names is governed)")
    return problems


def _spec_caps() -> set[str]:
    return set(_CAP_ID.findall(SPEC.read_text(encoding="utf-8")))


def _pointer_problems(specs: Mapping[str, tuple[tuple[re.Pattern[str], ...], frozenset[str]]], text: str) -> Problems:
    problems: Problems = []
    rows = _rows(_section(text, H_POINTERS))
    if not rows:
        problems.append("the pointers table is empty")
    for cells in rows:
        cited = [match for token in _tokens(cells[-1]) if (match := _SPEC_CAP.match(token))]
        if not cited:
            problems.append(f"pointer {_plain(cells[0])!r} cites no spec-x:CAP-n")
        for match in cited:
            spec, cap = match.groups()
            if cap not in specs.get(spec, ((), frozenset()))[1]:
                problems.append(f"pointer {_plain(cells[0])!r}: stale row {match.group(0)!r} names no capability")
        for token in _path_tokens(cells[1]):
            if not _repo_path(token).exists():
                problems.append(f"pointer {_plain(cells[0])!r}: dead path {token!r}")
    return problems


def _default_audit_target() -> str:
    for node in ast.parse(MCP_MODULE.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "DEFAULT_AUDIT_TARGET" for target in node.targets
        ):
            assert isinstance(node.value, ast.Constant)
            return str(node.value.value)
    raise AssertionError(f"{MCP_MODULE} defines no DEFAULT_AUDIT_TARGET")


def _as_is_derived() -> set[str]:
    schema_id = str(json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))["$id"])
    route = "/compliance/check"
    literals = {schema_id, f'DEFAULT_AUDIT_TARGET = "{_default_audit_target()}"'}
    if route in STATION_API.read_text(encoding="utf-8"):
        literals.add(route)
    return literals


def _as_is_problems(derived: Iterable[str], text: str) -> Problems:
    rows = _keyed_rows(text, H_AS_IS)
    problems = _both_ways("recorded as-is literal", derived, rows)
    for literal, cells in sorted(rows.items()):
        problems += [
            f"recorded as-is {literal!r}: dead path {token!r}"
            for token in _path_tokens(cells[1])
            if not _repo_path(token).exists()
        ]
    return problems


# ---------------------------------------------------------------------------
# The live checks
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def contract_text() -> str:
    assert CONTRACT.is_file(), f"{CONTRACT} is missing: warden's public contract is one companion (CAP-28)"
    return CONTRACT.read_text(encoding="utf-8")


def test_derivations_are_not_blind() -> None:
    """Each inventory derives something, so a green below is never a scan that found nothing."""
    assert len(_hooks_derived()) == 3
    assert len(_entry_points_derived()) == 10
    assert len(_optional_derived()) == 7
    assert {"advisory[] (opengrep)", "advisory[] (tea-test-review)", "actuation", "actuation.outcomes[]"} <= set(
        _live_slots()
    )
    assert _live_slots()["actuation.outcomes[]"][1], "the full actuation outcome emitted no optional key"
    assert len([range_ for range_ in _engines_derived().values() if range_]) >= 4
    assert {"conda_pypi_map.json", "lts-registry.yaml", "report-schema.json", "sast-rules/"} <= set(_data_entries())
    assert all(_data_derived(_data_entries()).values()), "a bundled data entry has no reader"
    assert len(_refresh_derived()) == 3
    assert len(_tracked_texts()) >= 12
    assert len(_live_imports()) >= 12
    assert len(_spec_caps()) >= 29
    for spec in ("spec-pyforge-warden", "spec-pyforge-unifying-strategy", "spec-pyforge-steward"):
        globs, caps = _station_specs()[spec]
        assert globs and caps, spec


def test_hook_specs_match_contract(contract_text: str) -> None:
    assert _hooks_problems(_hooks_derived(), contract_text) == []


def test_entry_points_are_one_group_and_match_contract(contract_text: str) -> None:
    assert set(_entry_point_groups()) == {hooks.ENTRY_POINT_GROUP}
    assert _entry_points_problems(_entry_points_derived(), contract_text) == []


def test_optional_scanner_ids_match_contract(contract_text: str) -> None:
    assert _optional_problems(_optional_derived(), contract_text) == []


def test_open_slots_match_contract(contract_text: str) -> None:
    assert _slots_problems(_live_slots(), contract_text) == []


def test_the_schema_leaves_both_slots_open() -> None:
    """contract.md section 9 is the slots' only typing: the frozen 1.1.0 schema types neither."""
    properties = json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))["properties"]
    for slot in ("advisory", "actuation"):
        assert slot in properties
        assert not {"properties", "items", "additionalProperties", "$ref"} & set(properties[slot]), slot


def test_engines_match_contract(contract_text: str) -> None:
    assert _engines_problems(_engines_derived(), contract_text) == []


def test_tea_row_names_its_agent(contract_text: str) -> None:
    row = _keyed_rows(contract_text, H_ENGINES)[tea_advisory.TEA_TEST_REVIEW_BINARY]
    assert f"--agent {engines._TEA_DEFAULT_AGENT}" in _tokens(" | ".join(row))


def test_bundled_data_matches_contract(contract_text: str) -> None:
    assert _data_problems(_data_derived(_data_entries()), contract_text) == []


def test_bundled_data_freshness_cells_hold(contract_text: str) -> None:
    rows = _keyed_rows(contract_text, H_DATA)
    assert str(currency._REGISTRY_MAX_AGE_DAYS) in _tokens(rows["lts-registry.yaml"][1])
    mapping = json.loads(CONDA_PYPI_MAP.read_text(encoding="utf-8"))
    assert not {"snapshot_at", "updated", "generated_at"} & set(mapping), "the map now carries a date; say so"


def test_refresh_scripts_match_contract(contract_text: str) -> None:
    assert _refresh_problems(_refresh_derived(), contract_text) == []


def test_import_surface_matches_contract(contract_text: str) -> None:
    assert _imports_problems(_live_imports(), contract_text) == []


def test_import_allowlist_is_live() -> None:
    assert _allowlist_problems(_tracked_texts(), IMPORT_FIXTURE_FILES) == []


def test_where_each_capability_lives_matches_the_spec(contract_text: str) -> None:
    assert _where_problems(_spec_caps(), _station_specs(), contract_text) == []


def test_pointers_cite_live_capabilities(contract_text: str) -> None:
    assert _pointer_problems(_station_specs(), contract_text) == []


def test_recorded_as_is_literals_hold(contract_text: str) -> None:
    assert _as_is_problems(_as_is_derived(), contract_text) == []


# ---------------------------------------------------------------------------
# The import derivation sees what it should
# ---------------------------------------------------------------------------


def test_import_derivation_reads_lists_strings_and_aliases() -> None:
    text = (
        "from pyforge.warden import __version__ as version\n"
        "    from pyforge.warden import models, report  # noqa: X\n"
        "from pyforge.warden.engines import (  # noqa: PLC0415\n"
        "    DeptryEngine,  # a comment\n"
        "    run_doctor_checks as run,\n"
        ")\n"
        'CODE = "from pyforge.warden.discovery import PIXI_LOCK_KIND; print(1)"\n'
        "import pyforge.warden.cli\n"
    )
    surface = _import_surface({"src/x.py": text})
    assert {module: names["src/x.py"] for module, names in surface.items()} == {
        "pyforge.warden": {"__version__", "models", "report"},
        "pyforge.warden.engines": {"DeptryEngine", "run_doctor_checks"},
        "pyforge.warden.discovery": {"PIXI_LOCK_KIND"},
        "pyforge.warden.cli": set(),
    }


# ---------------------------------------------------------------------------
# Synthetic drift, both directions: each inventory names an unlisted item and a stale row
# ---------------------------------------------------------------------------

_SYNTHETIC_IMPORTER = "src/shared/packages/pyforge-synthetic/src/pyforge/synthetic/reader.py"


def _imports_with(text: str) -> Imports:
    texts = {**_surface_texts(_tracked_texts(), IMPORT_FIXTURE_FILES), _SYNTHETIC_IMPORTER: text}
    return _import_surface(texts)


def _imports_without_name(module: str, name: str) -> Imports:
    out = {mod: {rel: set(names) for rel, names in importers.items()} for mod, importers in _live_imports().items()}
    for names in out[module].values():
        names.discard(name)
    return out


def _slots_with_key(record: str, key: str) -> Slots:
    slots = dict(_live_slots())
    always, optional = slots[record]
    slots[record] = (always | {key}, optional)
    return slots


Case = tuple[Callable[[str], Problems], str]

UNLISTED: dict[str, Case] = {
    "hook_spec": (
        lambda text: _hooks_problems({**_hooks_derived(), "pyforge.warden.pr_gate.synthetic": "warden"}, text),
        "pyforge.warden.pr_gate.synthetic",
    ),
    "entry_point": (
        lambda text: _entry_points_problems(
            {**_entry_points_derived(), "warden-synthetic": ("pyforge.warden.x:Y", "synthetic", "optional")}, text
        ),
        "warden-synthetic",
    ),
    "optional_scanner": (
        lambda text: _optional_problems({**_optional_derived(), "synthetic-scanner": ((), "SyntheticPlugin")}, text),
        "synthetic-scanner",
    ),
    "open_slot_record": (
        lambda text: _slots_problems(
            {**_live_slots(), "advisory[] (synthetic)": (frozenset({"tool"}), frozenset())}, text
        ),
        "advisory[] (synthetic)",
    ),
    "open_slot_key": (
        lambda text: _slots_problems(_slots_with_key("actuation", "synthetic_key"), text),
        "synthetic_key",
    ),
    "engine": (
        lambda text: _engines_problems({**_engines_derived(), "synthetic-engine": ">=1.0,<1.1"}, text),
        "synthetic-engine",
    ),
    "bundled_data": (
        lambda text: _data_problems({**_data_derived(_data_entries()), "synthetic.json": set()}, text),
        "synthetic.json",
    ),
    "refresh_script": (
        lambda text: _refresh_problems(_refresh_derived() | {f"{PACKAGE_REL}/scripts/refresh_synthetic.py"}, text),
        "refresh_synthetic.py",
    ),
    "import_module": (
        lambda text: _imports_problems(_imports_with("from pyforge.warden.synthetic import thing\n"), text),
        "pyforge.warden.synthetic",
    ),
    "import_name": (
        lambda text: _imports_problems(_imports_with("from pyforge.warden.engines import synthetic_name\n"), text),
        "synthetic_name",
    ),
    "import_importer": (
        lambda text: _imports_problems(_imports_with("import pyforge.warden.cli\n"), text),
        _SYNTHETIC_IMPORTER,
    ),
    "import_in_a_subprocess_string": (
        lambda text: _imports_problems(
            _imports_with('ARGV = ["python", "-c", "from pyforge.warden.sbom import render; render()"]\n'), text
        ),
        "pyforge.warden.sbom",
    ),
    "capability": (
        lambda text: _where_problems(_spec_caps() | {"CAP-99"}, _station_specs(), text),
        "CAP-99",
    ),
    "as_is_literal": (
        lambda text: _as_is_problems(_as_is_derived() | {'DEFAULT_AUDIT_TARGET = "src/synthetic"'}, text),
        "src/synthetic",
    ),
}

STALE_ROWS: dict[str, Case] = {
    "hook_spec": (
        lambda text: _hooks_problems(
            _hooks_derived(),
            _inject_row(text, H_HOOKS, "| `pyforge.warden.pr_gate.synthetic` | `warden` | x | CAP-27 |"),
        ),
        "pyforge.warden.pr_gate.synthetic",
    ),
    "entry_point": (
        lambda text: _entry_points_problems(
            _entry_points_derived(),
            _inject_row(
                text, H_ENTRY_POINTS, "| `warden-synthetic` | `pyforge.warden.x:Y` | `x` | optional | CAP-27 |"
            ),
        ),
        "warden-synthetic",
    ),
    "optional_scanner": (
        lambda text: _optional_problems(
            _optional_derived(), _inject_row(text, H_OPTIONAL, "| `synthetic-scanner` | none | `X` | x | CAP-27 |")
        ),
        "synthetic-scanner",
    ),
    "open_slot_record": (
        lambda text: _slots_problems(
            _live_slots(), _inject_row(text, H_SLOTS, "| `advisory[] (synthetic)` | `tool` | none | `x` |")
        ),
        "advisory[] (synthetic)",
    ),
    "open_slot_key": (
        lambda text: _slots_problems(
            {**_live_slots(), "actuation": (_live_slots()["actuation"][0] - {"dry_run"}, frozenset())}, text
        ),
        "dry_run",
    ),
    "engine": (
        lambda text: _engines_problems(
            _engines_derived(), _inject_row(text, H_ENGINES, "| `synthetic-engine` | `>=1.0,<1.1` | x | CAP-4 |")
        ),
        "synthetic-engine",
    ),
    "bundled_data": (
        lambda text: _data_problems(
            _data_derived(_data_entries()),
            _inject_row(text, H_DATA, "| `synthetic.json` | x | `pyforge/warden/cli.py` | CAP-2 |"),
        ),
        "synthetic.json",
    ),
    "refresh_script": (
        lambda text: _refresh_problems(
            _refresh_derived(),
            _inject_row(text, H_REFRESH, f"| `{PACKAGE_REL}/scripts/refresh_synthetic.py` | x | CAP-11 |"),
        ),
        "refresh_synthetic.py",
    ),
    "import_module": (
        lambda text: _imports_problems(
            _live_imports(), _inject_row(text, H_IMPORTS, "| `pyforge.warden.synthetic` | `thing` | `src/x.py` |")
        ),
        "pyforge.warden.synthetic",
    ),
    "import_name": (
        lambda text: _imports_problems(_imports_without_name("pyforge.warden.engines", "DeptryEngine"), text),
        "DeptryEngine",
    ),
    "capability": (
        lambda text: _where_problems(
            _spec_caps(),
            _station_specs(),
            _inject_row(text, H_WHERE, "| CAP-99 | `pyforge/warden/cli.py` | `spec-pyforge-warden` |"),
        ),
        "CAP-99",
    ),
    "capability_governor": (
        lambda text: _where_problems(
            _spec_caps(),
            _station_specs(),
            _inject_row(
                text, H_WHERE, "| CAP-99 | `pyforge/warden/cli.py` | `spec-pyforge-warden`, `spec-pyforge-mason` |"
            ),
        ),
        "spec-pyforge-mason",
    ),
    "pointer": (
        lambda text: _pointer_problems(
            _station_specs(),
            _inject_row(text, H_POINTERS, "| synthetic | `pyforge/warden/cli.py` | `spec-pyforge-steward:CAP-999` |"),
        ),
        "spec-pyforge-steward:CAP-999",
    ),
    "as_is_literal": (
        lambda text: _as_is_problems(
            _as_is_derived(), _inject_row(text, H_AS_IS, "| `urn:synthetic` | `pyforge/warden/cli.py` | x |")
        ),
        "urn:synthetic",
    ),
}


@pytest.mark.parametrize("inventory", sorted(UNLISTED))
def test_unlisted_item_is_caught(inventory: str, contract_text: str) -> None:
    run, item = UNLISTED[inventory]
    problems = run(contract_text)
    assert any("unlisted" in problem and item in problem for problem in problems), problems


@pytest.mark.parametrize("inventory", sorted(STALE_ROWS))
def test_stale_row_is_caught(inventory: str, contract_text: str) -> None:
    run, item = STALE_ROWS[inventory]
    problems = run(contract_text)
    assert any("stale row" in problem and item in problem for problem in problems), problems


def test_stale_row_dead_path_is_caught(contract_text: str) -> None:
    mutant = _inject_row(
        contract_text, H_WHERE, "| CAP-99 | `pyforge/warden/synthetic_gone.py` | `spec-pyforge-warden` |"
    )
    problems = _where_problems(_spec_caps(), _station_specs(), mutant)
    assert any("dead path" in problem and "synthetic_gone.py" in problem for problem in problems), problems


def test_ungoverned_path_without_none_is_caught(contract_text: str) -> None:
    specs = {name: ((), caps) for name, (_globs, caps) in _station_specs().items()}  # no Spec governs anything
    problems = _where_problems(_spec_caps(), specs, contract_text)
    assert any("on no Spec's surface" in problem for problem in problems), problems


# ---------------------------------------------------------------------------
# The allowlist: a stale entry, an entry that really imports, an entry with no reason
# ---------------------------------------------------------------------------

_FIXTURE_ONLY = 'SOURCE = "from pyforge.warden.engines import run_doctor_checks\\n"\n'


def test_allowlist_stale_entry_is_caught() -> None:
    texts = {"src/a.py": "X = 1  # mentions pyforge.warden but quotes no import line\n"}
    problems = _allowlist_problems(texts, {"src/a.py": "a fixture", "src/gone.py": "a fixture"})
    assert any("stale allowlist entry 'src/a.py'" in problem for problem in problems), problems
    assert any("stale allowlist entry 'src/gone.py'" in problem for problem in problems), problems


def test_allowlist_entry_that_really_imports_is_caught() -> None:
    texts = {"src/a.py": _FIXTURE_ONLY + "from pyforge.warden import verdict\n"}
    problems = _allowlist_problems(texts, {"src/a.py": "a fixture"})
    assert any("really imports" in problem for problem in problems), problems
    assert _allowlist_problems({"src/a.py": _FIXTURE_ONLY}, {"src/a.py": "a fixture"}) == []


def test_allowlist_entry_without_reason_is_caught() -> None:
    problems = _allowlist_problems({"src/a.py": _FIXTURE_ONLY}, {"src/a.py": " "})
    assert any("carries no reason" in problem for problem in problems), problems


def test_allowlist_leaves_only_its_own_files_out() -> None:
    texts = {"src/a.py": _FIXTURE_ONLY, "src/b.py": _FIXTURE_ONLY}
    surface = _import_surface(_surface_texts(texts, {"src/a.py": "a fixture"}))
    assert surface == {"pyforge.warden.engines": {"src/b.py": {"run_doctor_checks"}}}
