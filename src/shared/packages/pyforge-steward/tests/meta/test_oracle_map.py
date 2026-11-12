"""Story 123.1 (spec-pyforge-steward:CAP-181, FR-55): every capability names its source modules and the tests that
prove it, and every test names a capability.

The map is ``spec-pyforge-steward/oracle-map.md`` beside ``SPEC.md``: one table row per capability or contiguous range
(``CAP-9..CAP-13``), naming the steward source modules that realize it, where its proof runs and the test files or
globs that prove it, a second table for the capabilities of other Specs this package realizes, and an *Unmapped* table
for a test module no capability claims. This module holds the map total and true to the tree, and fails, naming the
row or the file, when:

* a capability id ``SPEC.md`` defines has no row (or two), or a row names an id ``SPEC.md`` does not define;
* a row names a source module, a test path or a glob that matches no file of the checkout (tracked, or new and not
  ignored: the state before the commit that adds it);
* a row's proof values disagree with the named steward test modules: a module under ``tests/unit`` or ``tests/meta``
  marked ``pytestmark = pytest.mark.live_tree`` runs in the live-tree half (``live-tree``), an unmarked one in the
  package half (``package``), and one under ``tests/integration`` only in the attended NKP probes (``attended``); a
  proof value is one of the seven words, and ``none`` stands alone and carries its reason in *Notes*;
* a test module under ``tests/unit``, ``tests/meta`` or ``tests/integration`` is named by no row and is not under
  *Unmapped* with a reason, or is under *Unmapped* while a row names it.

It does not judge whether a test is sufficient for its capability, only that the map is total and true to the tree.
The ``fires`` tests plant one fault each into the live inputs and prove the checker names it. The module reads the
Spec folder and lists the checkout's files, so it is a live-tree test; the repository root is found inside a function,
never at import.
"""

from __future__ import annotations

import ast
import fnmatch
import functools
import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.live_tree

STEWARD_SPEC_DIR = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward"
STEWARD_PACKAGE = "src/shared/packages/pyforge-steward"
SOURCE_ROOT = f"{STEWARD_PACKAGE}/src/pyforge/steward"
TESTS_ROOT = f"{STEWARD_PACKAGE}/tests"
#: The steward test directories whose modules must each be named; a Tests token that starts with one of these is
#: relative to the package's ``tests/``, every other token to the repository root.
TEST_DIRS: tuple[str, ...] = ("unit", "meta", "integration")

PROOF_VALUES: tuple[str, ...] = ("package", "live-tree", "platform", "other-station", "script", "attended", "none")
#: The proof values a steward test module's location and marker decide; the others are read, not derived.
DERIVED_VALUES: frozenset[str] = frozenset({"package", "live-tree"})

SECTION_STEWARD = "Capabilities"
SECTION_OTHER = "Capabilities of other Specs this package realizes"
SECTION_UNMAPPED = "Unmapped"
CAPABILITY_COLUMNS: tuple[str, ...] = ("Capability", "Source modules", "Proof", "Tests", "Notes")
UNMAPPED_COLUMNS: tuple[str, ...] = ("Test module", "Reason")
NOTHING = "—"

_HEADING = re.compile(r"^## (.+?)\s*$")
_TICK = re.compile(r"`([^`]+)`")
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
_SPEC_CAPABILITY = re.compile(r"^- \*\*CAP-(\d+) —", re.MULTILINE)
_STEWARD_ID = re.compile(r"^CAP-(\d+)(?:\.\.CAP-(\d+))?$")
_QUALIFIED_ID = re.compile(r"^spec-[a-z0-9-]+:CAP-\d+$")
_GLOB_CHARS = frozenset("*?[")


# --------------------------------------------------------------------------- where things are


@functools.cache
def _repo_root() -> Path:
    """The checkout this test reads, resolved inside a function and never at import (the live-tree split rule)."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pixi.toml").is_file() and (candidate / SOURCE_ROOT).is_dir():
            return candidate
    raise AssertionError("could not locate the repository root (pixi.toml beside the steward package)")


@functools.cache
def checkout_files() -> frozenset[str]:
    """Every file of the checkout: tracked, or new and not ignored, and present on disk."""
    root = _repo_root()
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return frozenset(path for path in out.split("\0") if path and (root / path).is_file())


@functools.cache
def live_tree_marked(rel: str) -> bool:
    """Does the module carry ``pytestmark = pytest.mark.live_tree`` (alone or in a list) at module level?"""
    try:
        tree = ast.parse((_repo_root() / rel).read_text(encoding="utf-8"))
    except OSError, SyntaxError:
        return False
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "pytestmark" for target in node.targets):
            continue
        return any(
            isinstance(sub, ast.Attribute)
            and sub.attr == "live_tree"
            and isinstance(sub.value, ast.Attribute)
            and sub.value.attr == "mark"
            for sub in ast.walk(node.value)
        )
    return False


# --------------------------------------------------------------------------- reading the map


@dataclass(frozen=True)
class Row:
    """One capability row: its section, its ids as written, and its four checked cells as backticked tokens."""

    section: str
    line: int
    capability: str
    sources: tuple[str, ...]
    proof: tuple[str, ...]
    tests: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class Unmapped:
    line: int
    module: str
    reason: str


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _tables(text: str) -> dict[str, list[tuple[int, dict[str, str]]]]:
    """``##`` heading -> its table rows, each a ``{column: cell}`` map with its 1-based line number."""
    tables: dict[str, list[tuple[int, dict[str, str]]]] = {}
    heading: str | None = None
    header: list[str] | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = _HEADING.match(line)
        if match:
            heading, header = match.group(1), None
            continue
        if heading is None or not line.lstrip().startswith("|"):
            if not line.strip():
                header = None
            continue
        cells = _cells(line)
        if header is None:
            header = cells
            continue
        if all(_SEPARATOR_CELL.match(cell) for cell in cells if cell):
            continue
        tables.setdefault(heading, []).append((number, dict(zip(header, cells, strict=False))))
    return tables


def _tokens(cell: str) -> tuple[str, ...]:
    return tuple(token.strip() for token in _TICK.findall(cell))


def _proof(cell: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in cell.split(",") if value.strip())


def read_map(text: str) -> tuple[list[Row], list[Unmapped], list[str]]:
    """The capability rows of both sections, the *Unmapped* entries, and the map's shape findings."""
    findings: list[str] = []
    tables = _tables(text)
    rows: list[Row] = []
    for section in (SECTION_STEWARD, SECTION_OTHER):
        if section not in tables:
            findings.append(f"oracle-map.md has no `## {section}` table")
            continue
        for number, cells in tables[section]:
            missing = [column for column in CAPABILITY_COLUMNS if column not in cells]
            if missing:
                findings.append(f"line {number}: the `{section}` row lacks the column(s) {missing}")
                continue
            rows.append(
                Row(
                    section=section,
                    line=number,
                    capability=cells["Capability"],
                    sources=_tokens(cells["Source modules"]),
                    proof=_proof(cells["Proof"]),
                    tests=_tokens(cells["Tests"]),
                    notes=cells["Notes"],
                )
            )
    unmapped: list[Unmapped] = []
    for number, cells in tables.get(SECTION_UNMAPPED, []):
        if any(column not in cells for column in UNMAPPED_COLUMNS):
            findings.append(f"line {number}: the `{SECTION_UNMAPPED}` row lacks a column of {list(UNMAPPED_COLUMNS)}")
            continue
        for module in _tokens(cells["Test module"]):
            unmapped.append(Unmapped(number, module, cells["Reason"]))
    return rows, unmapped, findings


def spec_capability_ids(spec_text: str) -> set[int]:
    return {int(number) for number in _SPEC_CAPABILITY.findall(spec_text)}


def _row_ids(row: Row) -> tuple[list[int], str | None]:
    """The steward capability numbers a row of the first section covers, or the reason its id cell is not one."""
    match = _STEWARD_ID.match(row.capability.strip())
    if not match:
        return [], f"`{row.capability}` is not `CAP-n` or `CAP-n..CAP-m`"
    first = int(match.group(1))
    last = int(match.group(2)) if match.group(2) else first
    if last <= first and match.group(2):
        return [], f"`{row.capability}` is not an ascending range"
    return list(range(first, last + 1)), None


# --------------------------------------------------------------------------- resolving a token


def _steward_test_token(token: str) -> bool:
    return token.split("/", 1)[0] in TEST_DIRS


def resolve_source(token: str) -> str:
    return f"{SOURCE_ROOT}/{token}"


def resolve_test(token: str) -> str:
    return f"{TESTS_ROOT}/{token}" if _steward_test_token(token) else token


def matches(pattern: str, files: Iterable[str]) -> list[str]:
    """The files a path, a directory (trailing ``/``) or a glob names."""
    if pattern.endswith("/"):
        return sorted(path for path in files if path.startswith(pattern))
    if _GLOB_CHARS & set(pattern):
        return sorted(path for path in files if fnmatch.fnmatchcase(path, pattern))
    return [pattern] if pattern in files else []


def steward_test_modules(files: Iterable[str]) -> list[str]:
    """Every ``test_*.py`` module under the package's ``tests/unit``, ``tests/meta`` and ``tests/integration``."""
    prefixes = tuple(f"{TESTS_ROOT}/{directory}/" for directory in TEST_DIRS)
    return sorted(
        path
        for path in files
        if path.startswith(prefixes) and Path(path).name.startswith("test_") and path.endswith(".py")
    )


def derived_proof(module: str, live_tree: Callable[[str], bool]) -> str:
    """Where a steward test module runs: the attended probes, the live-tree half or the package half."""
    if module.startswith(f"{TESTS_ROOT}/integration/"):
        return "attended"
    return "live-tree" if live_tree(module) else "package"


# --------------------------------------------------------------------------- the checks


def capability_findings(spec_text: str, rows: list[Row]) -> list[str]:
    """Every id SPEC.md defines has exactly one row; every row's id is defined (or qualified, in the second table)."""
    findings: list[str] = []
    defined = spec_capability_ids(spec_text)
    seen: dict[int, int] = {}
    for row in rows:
        if row.section == SECTION_OTHER:
            for raw in row.capability.split(","):
                if not _QUALIFIED_ID.match(raw.strip()):
                    findings.append(f"line {row.line}: `{raw.strip()}` is not a qualified `spec-<x>:CAP-n` id")
            continue
        ids, problem = _row_ids(row)
        if problem:
            findings.append(f"line {row.line}: {problem}")
        for number in ids:
            if number not in defined:
                findings.append(f"line {row.line}: CAP-{number} has a row but SPEC.md defines no CAP-{number}")
            if number in seen:
                findings.append(f"line {row.line}: CAP-{number} already has a row (line {seen[number]})")
            seen.setdefault(number, row.line)
    for number in sorted(defined - set(seen)):
        findings.append(f"CAP-{number} is defined in SPEC.md and has no row in oracle-map.md")
    return findings


def path_findings(rows: list[Row], unmapped: list[Unmapped], files: frozenset[str]) -> list[str]:
    """Every module, path or glob a row or an *Unmapped* entry names matches a file of the checkout."""
    findings: list[str] = []
    for row in rows:
        for token in row.sources:
            if not matches(resolve_source(token), files):
                findings.append(f"line {row.line} ({row.capability}): source module `{token}` matches no file")
        for token in row.tests:
            if not matches(resolve_test(token), files):
                findings.append(f"line {row.line} ({row.capability}): test path `{token}` matches no file")
    for entry in unmapped:
        if not matches(resolve_test(entry.module), files):
            findings.append(f"line {entry.line} (Unmapped): `{entry.module}` matches no file")
    return findings


def proof_findings(rows: list[Row], files: frozenset[str], live_tree: Callable[[str], bool]) -> list[str]:
    """Each row's proof values are words of the vocabulary, a ``none`` stands alone with its reason, and the
    ``package`` / ``live-tree`` / ``attended`` values agree with the steward test modules the row names."""
    findings: list[str] = []
    test_modules = frozenset(steward_test_modules(files))
    for row in rows:
        label = f"line {row.line} ({row.capability})"
        if not row.proof:
            findings.append(f"{label}: no proof value")
            continue
        unknown = [value for value in row.proof if value not in PROOF_VALUES]
        if unknown:
            findings.append(f"{label}: proof value(s) {unknown} are not in {list(PROOF_VALUES)}")
        if "none" in row.proof:
            if len(row.proof) > 1:
                findings.append(f"{label}: `none` is combined with {[v for v in row.proof if v != 'none']}")
            if not row.notes.strip() or row.notes.strip() == NOTHING:
                findings.append(f"{label}: a `none` row carries no reason in Notes")
        named = sorted(
            {
                module
                for token in row.tests
                if _steward_test_token(token)
                for module in matches(resolve_test(token), files)
                if module in test_modules
            }
        )
        derived = {derived_proof(module, live_tree) for module in named}
        stated = set(row.proof) & DERIVED_VALUES
        if stated != derived & DERIVED_VALUES:
            findings.append(
                f"{label}: proof says {sorted(stated)} but the named steward test modules run in "
                f"{sorted(derived & DERIVED_VALUES)} ({', '.join(m.removeprefix(TESTS_ROOT + '/') for m in named)})"
            )
        if "attended" in derived and "attended" not in row.proof:
            findings.append(f"{label}: names a tests/integration module but its proof does not say `attended`")
    return findings


def coverage_findings(rows: list[Row], unmapped: list[Unmapped], files: frozenset[str]) -> list[str]:
    """Every steward test module is named by a row or under *Unmapped* with a reason, never both."""
    findings: list[str] = []
    modules = steward_test_modules(files)
    named: set[str] = set()
    for row in rows:
        for token in row.tests:
            named.update(matches(resolve_test(token), files))
    listed: dict[str, Unmapped] = {}
    for entry in unmapped:
        for module in matches(resolve_test(entry.module), files):
            listed[module] = entry
        if not entry.reason.strip() or entry.reason.strip() == NOTHING:
            findings.append(f"line {entry.line} (Unmapped): `{entry.module}` carries no reason")
    for module in modules:
        short = module.removeprefix(TESTS_ROOT + "/")
        if module not in named and module not in listed:
            findings.append(f"{short} is named by no row of oracle-map.md and is not under Unmapped")
        if module in named and module in listed:
            findings.append(f"{short} is under Unmapped (line {listed[module].line}) while a row names it")
    return findings


def check(spec_text: str, map_text: str, files: frozenset[str], live_tree: Callable[[str], bool]) -> list[str]:
    """Every finding of the map against the Spec and the tree; an empty list is a total, true map."""
    rows, unmapped, findings = read_map(map_text)
    return [
        *findings,
        *capability_findings(spec_text, rows),
        *path_findings(rows, unmapped, files),
        *proof_findings(rows, files, live_tree),
        *coverage_findings(rows, unmapped, files),
    ]


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def spec_text() -> str:
    return (_repo_root() / STEWARD_SPEC_DIR / "SPEC.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def map_text() -> str:
    return (_repo_root() / STEWARD_SPEC_DIR / "oracle-map.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def files() -> frozenset[str]:
    return checkout_files()


def _report(findings: list[str]) -> str:
    return "oracle-map.md is not total and true to the tree:\n  " + "\n  ".join(findings)


def _plant_row(map_text: str, row: str) -> str:
    """``map_text`` with ``row`` appended to the table of the other Specs' capabilities."""
    rows, _, _ = read_map(map_text)
    last = max(r.line for r in rows if r.section == SECTION_OTHER)
    lines = map_text.splitlines()
    lines.insert(last, row)
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- the live tree


def test_the_map_and_the_tree_are_read_not_empty(spec_text: str, map_text: str, files: frozenset[str]) -> None:
    rows, _, findings = read_map(map_text)
    assert not findings, _report(findings)
    assert len(spec_capability_ids(spec_text)) >= 180
    assert sum(1 for row in rows if row.section == SECTION_STEWARD) >= 60
    assert any(row.section == SECTION_OTHER for row in rows)
    assert len(steward_test_modules(files)) >= 150


def test_every_capability_has_one_row(spec_text: str, map_text: str) -> None:
    rows, _, _ = read_map(map_text)
    findings = capability_findings(spec_text, rows)
    assert not findings, _report(findings)


def test_every_named_module_path_and_glob_matches_a_file(map_text: str, files: frozenset[str]) -> None:
    rows, unmapped, _ = read_map(map_text)
    findings = path_findings(rows, unmapped, files)
    assert not findings, _report(findings)


def test_every_proof_value_agrees_with_the_tree(map_text: str, files: frozenset[str]) -> None:
    rows, _, _ = read_map(map_text)
    findings = proof_findings(rows, files, live_tree_marked)
    assert not findings, _report(findings)


def test_every_steward_test_module_is_named(map_text: str, files: frozenset[str]) -> None:
    rows, unmapped, _ = read_map(map_text)
    findings = coverage_findings(rows, unmapped, files)
    assert not findings, _report(findings)


def test_the_control_plane_modules_are_on_the_cutover_row(map_text: str, files: frozenset[str]) -> None:
    """The ``cutover`` duty's test modules sit on a row of the other Specs' table, never under *Unmapped*."""
    rows, unmapped, _ = read_map(map_text)
    control_plane = [
        module
        for module in steward_test_modules(files)
        if Path(module).name.startswith(("test_cutover", "test_capability_ledger"))
    ]
    assert control_plane, "the cutover duty's test modules were not found"
    other_rows = [row for row in rows if row.section == SECTION_OTHER]
    for module in control_plane:
        assert any(module in matches(resolve_test(t), files) for row in other_rows for t in row.tests), module
        assert not any(module in matches(resolve_test(e.module), files) for e in unmapped), module


# --------------------------------------------------------------------------- the checker fires


def test_fires_on_a_capability_with_no_row(spec_text: str, map_text: str, files: frozenset[str]) -> None:
    planted = spec_text.replace(
        "## Constraints", "- **CAP-999 — planted** ← spec-pyforge-steward CAP-999\n\n## Constraints"
    )
    findings = check(planted, map_text, files, live_tree_marked)
    assert "CAP-999 is defined in SPEC.md and has no row in oracle-map.md" in findings


def test_fires_on_a_row_id_the_spec_does_not_define(spec_text: str, map_text: str) -> None:
    rows, _, _ = read_map(map_text)
    planted = rows + [Row(SECTION_STEWARD, 9999, "CAP-999", (), ("none",), (), "planted")]
    assert any("SPEC.md defines no CAP-999" in finding for finding in capability_findings(spec_text, planted))


def test_fires_on_a_glob_matching_nothing(spec_text: str, map_text: str, files: frozenset[str]) -> None:
    planted = _plant_row(map_text, "| spec-planted:CAP-1 | — | package | `unit/test_no_such_module_*.py` | planted |")
    findings = check(spec_text, planted, files, live_tree_marked)
    assert any("test path `unit/test_no_such_module_*.py` matches no file" in finding for finding in findings)


def test_fires_on_a_source_module_matching_nothing(spec_text: str, map_text: str, files: frozenset[str]) -> None:
    planted = _plant_row(map_text, "| spec-planted:CAP-1 | `no_such_module.py` | none | — | planted |")
    findings = check(spec_text, planted, files, live_tree_marked)
    assert any("source module `no_such_module.py` matches no file" in finding for finding in findings)


def test_fires_on_a_proof_value_against_the_marker(spec_text: str, map_text: str, files: frozenset[str]) -> None:
    package_module = next(
        module.removeprefix(TESTS_ROOT + "/")
        for module in steward_test_modules(files)
        if derived_proof(module, live_tree_marked) == "package"
    )
    planted = _plant_row(map_text, f"| spec-planted:CAP-1 | — | live-tree | `{package_module}` | planted |")
    findings = check(spec_text, planted, files, live_tree_marked)
    assert any(
        "spec-planted:CAP-1" in finding and "proof says ['live-tree']" in finding and "['package']" in finding
        for finding in findings
    ), findings


def test_fires_when_a_module_marker_moves(map_text: str, files: frozenset[str]) -> None:
    """The same rows, judged as if every module were marked ``live_tree``: each package-half row now disagrees."""
    rows, _, _ = read_map(map_text)
    findings = proof_findings(rows, files, lambda _module: True)
    assert any("proof says ['package']" in finding for finding in findings)


def test_fires_on_an_unknown_proof_value_and_a_none_without_reason(
    spec_text: str, map_text: str, files: frozenset[str]
) -> None:
    planted = _plant_row(map_text, "| spec-planted:CAP-1 | — | maybe | — | planted |")
    planted = _plant_row(planted, "| spec-planted:CAP-2 | — | none | — | |")
    findings = check(spec_text, planted, files, live_tree_marked)
    assert any("spec-planted:CAP-1" in f and "['maybe'] are not in" in f for f in findings), findings
    assert any("spec-planted:CAP-2" in f and "carries no reason" in f for f in findings), findings


def test_fires_on_an_unnamed_test_module(spec_text: str, map_text: str, files: frozenset[str]) -> None:
    planted_module = f"{TESTS_ROOT}/unit/test_planted_unnamed_module.py"
    findings = check(spec_text, map_text, files | {planted_module}, live_tree_marked)
    assert (
        "unit/test_planted_unnamed_module.py is named by no row of oracle-map.md and is not under Unmapped" in findings
    )


def test_fires_on_a_module_both_mapped_and_unmapped(map_text: str, files: frozenset[str]) -> None:
    rows, unmapped, _ = read_map(map_text)
    named = next(t for row in rows for t in row.tests if _steward_test_token(t) and not _GLOB_CHARS & set(t))
    findings = coverage_findings(rows, [*unmapped, Unmapped(9999, named, "planted")], files)
    assert any("is under Unmapped (line 9999) while a row names it" in finding for finding in findings)
