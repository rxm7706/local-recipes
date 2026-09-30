#!/usr/bin/env python3
"""The per-station flag inventory (doctor Story 34.4, ``spec-feature-flag-governance`` CAP-7).

CAP-7 retrofits the flag rule onto work that predates it: each station's existing capabilities whose
code a user can reach at runtime go behind flags that default ON, and every pre-rule ``type: feature``
story spec gains a ``flag:`` block or a ``flag-exempt:`` value. Each Smith mints its own retrofit
stories, and only after this report lands, so the report is the number they mint against.

A REPORT, never a gate: it writes one checked-in Markdown file per station to
``docs/governance/flag-inventory/pyforge-<station>.md`` and exits 0 unless it cannot run (exit 2).
It is not a detector (no ``DETECTOR`` marker, no ``detectors-ci`` row): it reports, the gate
(``scripts/flag_gate_check.py``) judges.

For each station the report lists

* every CAP declared by an open Spec folder the station hosts (its status is not in the roster's
  ``spec_statuses_ended_acts``), joined to its code the way ``pyforge.doctor.sources.capability_effect``
  already joins them -- the citing story's ``Surface:`` line in ``epics.md``. That join is imported, never
  re-implemented (``_load_join``), and it is the only station-side import here;
* the row's class: ``runtime`` (a resolved code fragment is an entry point of the station's package: a CLI
  verb module, an MCP tool module, a REST route or a portal view), ``module`` (resolved code that is no named
  entry point), ``planning`` (every fragment is a document) or ``unresolved`` (no citing story, no ``Surface:``
  line, or no fragment resolves) -- and, for a ``runtime`` row, what it is reached through;
* the flag key in the one tree that gates it (a tracked story spec of the same station carries a ``flag:``
  block whose key is in ``src/platform/config/flags.json`` and whose text cites the Spec slug and CAP), or ``none``;
* every pre-rule ``type: feature`` story spec the gate warns on, with its key and status. That list is the
  ``flag-pre-rule`` findings of ``flag_gate_check.judge_one``, so the report and the gate cannot disagree.

The header names the SHA the report read and the two counts each Smith's retrofit stories are minted
against: runtime CAPs with no flag, and warned specs. Nothing in a report is dated or timed, so a second
run on the same tree is byte-identical. Station code is read as text with ``ast``, never imported.

Lives in ``scripts/`` and imports no ``pyforge.<station>`` module but Doctor's own join (Charter section 6).

EXIT  0 the reports were written · 2 could-not-run (the roster, baseline, tree, an ``epics.md``, an open
      ``SPEC.md`` or the list of tracked files cannot be read, or Doctor's join cannot be loaded):
      unknown, and nothing is written
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPTS_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import flag_gate_check  # noqa: E402
import flag_rule  # noqa: E402

OUT_REL = Path("docs/governance/flag-inventory")
ROSTER_REL = flag_rule.ROSTER_REL
DOCTOR_SRC_REL = Path("src/shared/packages/pyforge-doctor/src")

RUNTIME = "runtime"
MODULE = "module"
PLANNING = "planning"
UNRESOLVED = "unresolved"
CLASSES = (RUNTIME, MODULE, PLANNING, UNRESOLVED)

CLI = "CLI"
MCP = "MCP"
REST = "REST"
PORTAL = "portal"
_KIND_ORDER = {CLI: 0, MCP: 1, REST: 2, PORTAL: 3}

# Names listed for one entry point before the rest collapse to `(+n more)`.
_NAME_LIMIT = 6

NO_FLAG = "none"
NOT_APPLICABLE = "n/a"
UNKNOWN = "unknown"


class InventoryError(flag_rule.FlagRuleError):
    """An input the inventory needs is unreadable: exit 2, and nothing is written."""


class JoinUnavailable(InventoryError):
    """Doctor's capability join cannot be loaded (the module or one of its eight names is gone)."""


# --- Doctor's join: the one station-side import ---------------------------------------------------

# The eight names of the join, as Doctor spells them. They are underscore-private in Doctor and no script
# imports one today, so they load through this one seam, and a test pins that they all exist.
JOIN_NAMES: Mapping[str, Mapping[str, str]] = {
    "pyforge.doctor.sources.capability_effect": {
        "story_surface_by_cap": "_story_surface_by_cap",
        "caps_cited_on_spec_line": "_caps_cited_on_spec_line",
        "split_surface_fragments": "_split_surface_fragments",
        "is_document_surface_fragment": "_is_document_surface_fragment",
        "strip_surface_annotation": "_strip_surface_annotation",
        "resolve_surface_paths": "_resolve_surface_paths",
    },
    "pyforge.doctor.sources.board": {
        "parse_declared_cap_ids": "_parse_declared_cap_ids",
        "canonical_epics": "_canonical_epics",
    },
}


@dataclass(frozen=True)
class Join:
    story_surface_by_cap: Callable[[str, list[str]], dict[tuple[str, int], str | None]]
    caps_cited_on_spec_line: Callable[[str, str], set[int]]
    split_surface_fragments: Callable[[str], list[str]]
    is_document_surface_fragment: Callable[[str], bool]
    strip_surface_annotation: Callable[[str], str]
    resolve_surface_paths: Callable[..., list[Path]]
    parse_declared_cap_ids: Callable[[str], set[int]]
    canonical_epics: Callable[[Path], Path | None]


def _import_join() -> Join:
    found: dict[str, Any] = {}
    for module_name, names in JOIN_NAMES.items():
        module = importlib.import_module(module_name)
        for field, attribute in names.items():
            found[field] = getattr(module, attribute)
    return Join(**found)


def _load_join() -> Join:
    """Doctor's eight join names. An ImportError (or a renamed name) is exit 2: the join is not re-implemented.

    Doctor is not installed in every environment that runs the scripts suite, so a failed import
    retries once with Doctor's source tree of THIS checkout on ``sys.path`` -- the way ``scripts/detectors.py``
    reads Doctor's registry. The modules are stdlib-only.
    """
    try:
        return _import_join()
    except (ImportError, AttributeError) as first:
        cause: Exception = first
        fallback = REPO_ROOT / DOCTOR_SRC_REL
        if fallback.is_dir() and str(fallback) not in sys.path:
            sys.path.append(str(fallback))
            try:
                return _import_join()
            except (ImportError, AttributeError) as second:
                cause = second
        raise JoinUnavailable(
            f"cannot load Doctor's capability join ({', '.join(JOIN_NAMES)}): {cause.__class__.__name__}: {cause}"
        ) from cause


# --- reading the inputs ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Roster:
    stations: tuple[str, ...]
    ended_statuses: frozenset[str]


def read_roster(root: Path) -> Roster:
    """The station names and the Spec statuses that end a Spec's life, read from the roster now."""
    path = root / ROSTER_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # ValueError covers JSON and UTF-8 decode errors
        raise flag_rule.RosterUnreadable(f"cannot read {ROSTER_REL.as_posix()}: {exc}") from exc
    stations = data.get("stations") if isinstance(data, dict) else None
    ended = data.get("spec_statuses_ended_acts") if isinstance(data, dict) else None
    if not isinstance(stations, list) or not stations or not all(isinstance(s, str) and s for s in stations):
        raise flag_rule.RosterUnreadable(f"{ROSTER_REL.as_posix()} carries no `stations` list of names")
    if not isinstance(ended, list) or not all(isinstance(s, str) for s in ended):
        raise flag_rule.RosterUnreadable(f"{ROSTER_REL.as_posix()} carries no `spec_statuses_ended_acts` list")
    return Roster(tuple(stations), frozenset(ended))


def head_sha(root: Path) -> str:
    """``git rev-parse HEAD`` of ``root``, or ``unknown`` outside a checkout."""
    if not (root / ".git").exists():
        return UNKNOWN
    try:
        proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    except OSError:
        return UNKNOWN
    sha = proc.stdout.strip()
    return sha if proc.returncode == 0 and sha else UNKNOWN


def _read_text(path: Path, root: Path, what: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InventoryError(f"cannot read {what} {flag_rule.repo_relative(path, root)}: {exc}") from exc


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


# --- what a station's code exposes, read as text --------------------------------------------------


def entry_kind(parts: Sequence[str]) -> str | None:
    """How a path inside a station package (its parts below ``src/pyforge/<station>/``) is reached, or None.

    CLI: ``cli.py``, ``cli/**``, ``__main__.py``. MCP: ``mcp/**``. REST: ``dashboard/**/urls*.py``,
    ``dashboard/**/routing.py``, ``dashboard/**/api*.py`` and the package's ``station_api.py``. Portal: any
    other ``dashboard/**``. Nothing else is a named entry point (a top-level ``routing.py`` may be a
    classifier, not a route table).
    """
    if not parts:
        return None
    head, name = parts[0], parts[-1]
    if head == "mcp":
        return MCP
    if head == "cli" or tuple(parts) in {("cli.py",), ("__main__.py",)}:
        return CLI
    if tuple(parts) == ("station_api.py",):
        return REST
    if head == "dashboard":
        if len(parts) > 1 and name.endswith(".py") and (name.startswith(("urls", "api")) or name == "routing.py"):
            return REST
        return PORTAL
    return None


def _str_arg(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return None


def _call_name(func: ast.expr) -> str:
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else ""


def module_names(path: Path) -> dict[str, set[str]]:
    """The names one Python module declares, read with ``ast``: verbs, tools and routes.

    Verbs are ``add_parser("...")`` literals; tools are the keys of a module-level ``TOOL_SPECS`` dict and the
    names of ``.tool``-decorated functions; routes are ``path("...")`` / ``re_path("...")`` literals. A file
    that cannot be read or parsed yields nothing, so the caller names it by its path.
    """
    names: dict[str, set[str]] = {CLI: set(), MCP: set(), REST: set()}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError, RecursionError):
        return names
    for stmt in tree.body:
        value: ast.expr | None = None
        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "TOOL_SPECS" for t in stmt.targets):
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == "TOOL_SPECS":
            value = stmt.value
        if isinstance(value, ast.Dict):
            names[MCP].update(k.value for k in value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            literal = _str_arg(node)
            if literal is None:
                continue
            called = _call_name(node.func)
            if called == "add_parser":
                names[CLI].add(literal)
            elif called in {"path", "re_path"}:
                names[REST].add(literal or "(root)")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                target = decorator.func if isinstance(decorator, ast.Call) else decorator
                if isinstance(target, ast.Attribute) and target.attr == "tool":
                    names[MCP].add(node.name)
    return names


def _python_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".py" else []
    if path.is_dir():
        return sorted(p for p in path.rglob("*.py") if "__pycache__" not in p.parts)
    return []


def _collapse(names: Iterable[str]) -> str:
    ordered = sorted(set(names))
    shown = ordered[:_NAME_LIMIT]
    if len(ordered) > _NAME_LIMIT:
        shown.append(f"(+{len(ordered) - _NAME_LIMIT} more)")
    return ", ".join(shown)


@dataclass(frozen=True)
class Entry:
    kind: str
    rel: str  # posix path below the station package, `/`-terminated for a directory
    names: str  # verbs, tools or routes, already collapsed; empty when the module declares none

    def render(self) -> str:
        label = f"{self.kind} `{self.rel}`"
        return f"{label} ({self.names})" if self.names else label


def _entry(path: Path, rel_parts: tuple[str, ...], kind: str) -> Entry:
    collected: set[str] = set()
    for source in _python_files(path):
        collected.update(module_names(source)[kind if kind in {CLI, MCP} else REST])  # a portal view lists its routes
    rel = "/".join(rel_parts) + ("/" if path.is_dir() else "")
    return Entry(kind, rel, _collapse(collected))


# --- classifying one CAP --------------------------------------------------------------------------


@dataclass(frozen=True)
class CapRow:
    spec: str
    cap: int
    klass: str
    reach: str
    flag: str

    @property
    def unflagged_runtime(self) -> bool:
        return self.klass == RUNTIME and self.flag.startswith(NO_FLAG)


def _norm(path: Path) -> Path:
    return Path(os.path.normpath(path))


def classify_cap(
    join: Join,
    root: Path,
    station: str,
    project: str,
    slug: str,
    cap: int,
    surface_by_cap: Mapping[tuple[str, int], str | None],
) -> tuple[str, str]:
    """(class, reach) for one declared CAP: precedence runtime, module, planning, unresolved."""
    key = (slug, cap)
    if key not in surface_by_cap:
        return UNRESOLVED, "no story in epics.md cites this CAP on a line naming the Spec"
    surface = surface_by_cap[key]
    if surface is None:
        return UNRESOLVED, "the citing story carries no `Surface:` line"
    fragments = join.split_surface_fragments(surface)
    if not fragments:
        return UNRESOLVED, "the citing story's `Surface:` line is empty"
    code = [f for f in fragments if not join.is_document_surface_fragment(join.strip_surface_annotation(f))]
    if not code:
        return PLANNING, "planning documents only"

    resolved: set[Path] = set()
    absent: list[str] = []
    for fragment in code:
        paths = join.resolve_surface_paths(root, fragment, project=project)
        if paths:
            resolved.update(_norm(p) for p in paths)
        else:
            absent.append(join.strip_surface_annotation(fragment).strip().strip("`"))
    # A `:line` suffix hides a document's suffix from the fragment test above, so test what resolved too.
    resolved = {p for p in resolved if not join.is_document_surface_fragment(flag_rule.repo_relative(p, root))}
    if not resolved and not absent:
        return PLANNING, "planning documents only"
    if not resolved:
        return UNRESOLVED, "no `Surface:` code path exists: " + _collapse_paths(absent)

    package = _norm(root / "src" / "shared" / "packages" / project / "src" / "pyforge" / station)
    entries: dict[tuple[str, str], Entry] = {}
    others: list[str] = []
    for path in sorted(resolved):
        kind: str | None = None
        parts: tuple[str, ...] = ()
        if path.is_relative_to(package):
            parts = path.relative_to(package).parts
            kind = entry_kind(parts)
        if kind is None:
            others.append(flag_rule.repo_relative(path, root))
            continue
        entry = _entry(path, parts, kind)
        entries[(kind, entry.rel)] = entry
    if entries:
        ordered = sorted(entries.values(), key=lambda e: (_KIND_ORDER[e.kind], e.rel))
        return RUNTIME, "; ".join(e.render() for e in ordered)
    return MODULE, "code with no entry point: " + _collapse_paths(others)


def _collapse_paths(paths: Iterable[str]) -> str:
    ordered = sorted(set(paths))
    shown = [f"`{p}`" for p in ordered[:_NAME_LIMIT]]
    if len(ordered) > _NAME_LIMIT:
        shown.append(f"(+{len(ordered) - _NAME_LIMIT} more)")
    return ", ".join(shown)


# --- one station ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecBlock:
    slug: str
    status: str
    rows: tuple[CapRow, ...]


@dataclass(frozen=True)
class Warned:
    key: str
    status: str
    path: str


@dataclass(frozen=True)
class StationInventory:
    station: str
    project: str
    sha: str
    specs: tuple[SpecBlock, ...]
    warned: tuple[Warned, ...]

    @property
    def rows(self) -> list[CapRow]:
        return [row for block in self.specs for row in block.rows]

    @property
    def unflagged_runtime_count(self) -> int:
        return sum(1 for row in self.rows if row.unflagged_runtime)


@dataclass(frozen=True)
class Story:
    rel: str
    status: str
    flag_key: str


def story_key(rel: str) -> str:
    """``spec-34-4-a-title.md`` -> ``34-4-a-title`` (the ledger key)."""
    name = PurePosixPath(rel).name.removesuffix(".md")
    return name.removeprefix("spec-")


def _flag_key(frontmatter: Mapping[str, Any] | None) -> str:
    block = frontmatter.get("flag") if frontmatter else None
    key = block.get("key") if isinstance(block, Mapping) else None
    return key.strip() if isinstance(key, str) else ""


def _gating_flags(
    join: Join, root: Path, stories: Sequence[Story], slugs: Sequence[str]
) -> dict[tuple[str, int], set[str]]:
    """``(spec slug, CAP-N)`` -> the keys of the station's flagged story specs whose text cites that Spec and CAP."""
    cited: dict[tuple[str, int], set[str]] = {}
    for story in stories:
        if not story.flag_key:
            continue
        try:
            text = (root / story.rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # the gate read this spec's frontmatter a moment ago; a vanished file gates nothing
        for line in text.splitlines():
            for slug in slugs:
                for cap in join.caps_cited_on_spec_line(line, slug):
                    cited.setdefault((slug, cap), set()).add(story.flag_key)
    return cited


def flag_cell(keys: Iterable[str], tree: Mapping[str, Any]) -> str:
    present = sorted(k for k in set(keys) if k in tree)
    missing = sorted(k for k in set(keys) if k not in tree)
    if present:
        return ", ".join(f"`{k}`" for k in present)
    if missing:
        return f"{NO_FLAG} (key {', '.join(missing)} not in tree)"
    return NO_FLAG


def build_station(
    join: Join,
    root: Path,
    roster: Roster,
    inputs: flag_gate_check.Inputs,
    station: str,
    stories: Sequence[Story],
    warned: Sequence[Warned],
    sha: str,
) -> StationInventory:
    project = f"pyforge-{station}"
    project_dir = root / "_bmad-output" / "projects" / project
    planning = project_dir / "planning-artifacts"

    open_specs: list[tuple[str, str, str]] = []  # (slug, status, SPEC.md text)
    for spec_md in sorted(planning.glob("specs/spec-*/SPEC.md")):
        frontmatter, _why = flag_rule.read_frontmatter(spec_md)
        status = str(frontmatter.get("status", "")).strip() if frontmatter else ""
        if status in roster.ended_statuses:
            continue
        open_specs.append((spec_md.parent.name, status or UNKNOWN, _read_text(spec_md, root, "the Spec")))
    slugs = [slug for slug, _status, _text in open_specs]

    surface_by_cap: dict[tuple[str, int], str | None] = {}
    if open_specs:
        epics = join.canonical_epics(project_dir)
        if epics is None and (planning / "epics.md").exists():
            raise InventoryError(f"cannot read epics {flag_rule.repo_relative(planning / 'epics.md', root)}: not a file")
        if epics is not None:
            surface_by_cap = join.story_surface_by_cap(_read_text(epics, root, "epics"), slugs)
    gating = _gating_flags(join, root, stories, slugs) if open_specs else {}

    blocks: list[SpecBlock] = []
    for slug, status, text in open_specs:
        rows = []
        for cap in sorted(join.parse_declared_cap_ids(text)):
            klass, reach = classify_cap(join, root, station, project, slug, cap, surface_by_cap)
            keys = gating.get((slug, cap), ())
            flag = flag_cell(keys, inputs.tree)
            if klass != RUNTIME and flag == NO_FLAG:
                flag = NOT_APPLICABLE
            rows.append(CapRow(slug, cap, klass, reach, flag))
        blocks.append(SpecBlock(slug, status, tuple(rows)))
    return StationInventory(station, project, sha, tuple(blocks), tuple(sorted(warned, key=lambda w: w.path)))


# --- the report -----------------------------------------------------------------------------------

_LEGEND = (
    "Classes: `runtime` -- a resolved code fragment is an entry point of the station's package (a CLI verb module, "
    "an MCP tool module, a REST route or a portal view); `module` -- resolved code that is no named entry point, "
    "so the inventory cannot show a user reaches it (listed, never counted as unflagged); `planning` -- every "
    "`Surface:` fragment is a document (not reachable at runtime); `unresolved` -- no citing story, no `Surface:` "
    "line, or no code fragment resolves. The join is Doctor's (`pyforge.doctor.sources.capability_effect`): a CAP "
    "is joined to its code through the citing story's `Surface:` line in `epics.md`, and a Spec whose "
    "`## Capabilities` section lists no `- **CAP-N ...**` bullet declares none. The flag column names the key of "
    "a tracked story spec of this station that carries a `flag:` block and cites the Spec and CAP; `n/a` marks a "
    "row that is not `runtime`."
)


def render_station(inv: StationInventory) -> str:
    rows = inv.rows
    counts = {klass: sum(1 for r in rows if r.klass == klass) for klass in CLASSES}
    empty = sorted(b.slug for b in inv.specs if not b.rows)
    lines = [
        f"# Flag inventory: {inv.project}",
        "",
        "<!-- Generated by scripts/flag_inventory.py (doctor Story 34.4, spec-feature-flag-governance CAP-7). "
        "Never edit by hand: rerun `pixi run -e pyforge-guild flag-inventory`. -->",
        "",
        f"- Read at SHA: `{inv.sha}`",
        f"- Runtime CAPs with no flag: {inv.unflagged_runtime_count}",
        f"- Warned specs: {len(inv.warned)}",
        "",
        f"Open Specs read: {len(inv.specs)} ({len(inv.specs) - len(empty)} declare CAPs). "
        f"CAP rows: {len(rows)} ({', '.join(f'{klass} {counts[klass]}' for klass in CLASSES)}).",
        "",
        _LEGEND,
        "",
        "## Capabilities",
    ]
    if not inv.specs:
        lines += ["", "_No open Spec._"]
    for block in inv.specs:
        if not block.rows:
            continue
        lines += [
            "",
            f"### {block.slug} ({block.status})",
            "",
            "| CAP | Class | Reach | Flag |",
            "|---|---|---|---|",
        ]
        lines += [f"| CAP-{r.cap} | {r.klass} | {_cell(r.reach)} | {_cell(r.flag)} |" for r in block.rows]
    if empty:
        lines += ["", "Open Specs declaring no CAP: " + ", ".join(f"`{slug}`" for slug in empty) + "."]
    lines += ["", "## Warned specs", ""]
    if inv.warned:
        lines += [
            "Pre-rule `type: feature` story specs that carry neither a `flag:` block nor a `flag-exempt:` value "
            "(the gate's `flag-pre-rule` warnings for this station).",
            "",
            "| Story key | Status | Path |",
            "|---|---|---|",
        ]
        lines += [f"| {_cell(w.key)} | {_cell(w.status)} | {_cell(w.path)} |" for w in inv.warned]
    else:
        lines.append("_None._")
    return "\n".join(lines) + "\n"


# --- the run --------------------------------------------------------------------------------------


def build_reports(root: Path) -> dict[str, str]:
    """``pyforge-<station>.md`` -> its text, for every roster station. Raises InventoryError / FlagRuleError."""
    inputs = flag_gate_check.load_inputs(root)  # roster exemptions, baseline, tree -- in that order
    roster = read_roster(root)
    join = _load_join()
    sha = head_sha(root)

    stories: dict[str, list[Story]] = {}
    warned: dict[str, list[Warned]] = {}
    for rel in flag_gate_check.story_specs(root):
        station = flag_gate_check.station_of(rel)
        frontmatter, _why = flag_rule.read_frontmatter(rel, repo_root=root)
        status = str(frontmatter.get("status", "")).strip() if frontmatter else ""
        stories.setdefault(station, []).append(Story(rel, status or UNKNOWN, _flag_key(frontmatter)))
        for finding in flag_gate_check.judge_one(root, inputs, rel):
            if finding.kind == flag_gate_check.K_PRE_RULE:
                warned.setdefault(station, []).append(Warned(story_key(rel), status or UNKNOWN, rel))

    reports: dict[str, str] = {}
    for station in roster.stations:
        project = f"pyforge-{station}"
        inventory = build_station(
            join, root, roster, inputs, station, stories.get(project, []), warned.get(project, []), sha
        )
        reports[f"{project}.md"] = render_station(inventory)
    return reports


def write_reports(out_dir: Path, reports: Mapping[str, str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in sorted(reports):
        (out_dir / name).write_text(reports[name], encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/flag_inventory.py",
        description="The per-station flag inventory (doctor Story 34.4, spec-feature-flag-governance CAP-7).",
    )
    parser.add_argument("--root", default=None, help="repo root to read (default: the checkout this script lives in)")
    parser.add_argument(
        "--out-dir", default=None, help=f"where to write the reports (default: <root>/{OUT_REL.as_posix()})"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve() if args.root else REPO_ROOT
    out_dir = Path(args.out_dir) if args.out_dir else root / OUT_REL
    try:
        reports = build_reports(root)
        write_reports(out_dir, reports)
    except flag_rule.FlagRuleError as exc:
        print(f"[flag-inventory] unknown -- {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"[flag-inventory] unknown -- cannot write the reports to {out_dir}: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 -- a crash is unknown, never a partial or a false report
        print(f"[flag-inventory] unknown -- the inventory crashed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"[flag-inventory] wrote {len(reports)} report(s) to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
