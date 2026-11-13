"""Story 120.5 (spec-foundry-regenerate-not-fold fnr:CAP-1): the case list counts itself and covers the Launch slice.

``case-list.md`` is the A/B case list of the foundry kernel and the oracle of the Launch slice (operator ruling 3 of
2026-11-10). Its count line said 38 while its table had 40 rows, and nothing checked it. This module holds:

* the count line equal to the rows, slice by slice, every id once (doctor's ``parse_case_list_ids`` reads a set, so a
  repeated id would read short of the count);
* every node id resolving statically: the file exists under the package's ``tests/`` and defines ``def <name>``.
  Nothing is collected or run;
* a case-list row for every step of ``spec-python-foundry-cutover`` ``launch-slice.md`` whose A test exists (its
  nodeid column is not ``oracle gap``). An oracle gap is never filled here (DW-steward-121-4);
* the count check firing: a wrong count planted in a ``tmp_path`` copy is reported, so no tracked file is mutated.

Node ids in the case list are paths under the packages directory; ``…/`` stands for the ``tests/`` directory of the
package the nearest full node id above it names, and a bare file name after ``…/`` sits under ``tests/unit/`` (the
rule the file states and core-kit's acceptance reads). ``launch-slice.md`` names repo-relative node ids.
"""

from __future__ import annotations

import re
import shutil
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-steward-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

# tests/meta -> tests -> pyforge-steward -> packages -> shared -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[6]
SPECS = REPO_ROOT / "_bmad-output" / "projects" / "pyforge-steward" / "planning-artifacts" / "specs"
CASE_LIST = SPECS / "spec-foundry-regenerate-not-fold" / "case-list.md"
LAUNCH_SLICE = SPECS / "spec-python-foundry-cutover" / "launch-slice.md"
PACKAGES = REPO_ROOT / "src" / "shared" / "packages"

# A case row is what doctor's reader counts (pyforge.doctor.sources.capability_ledger._CASE_ID_RE).
CASE_ROW = re.compile(r"^\|\s*(k-[a-z0-9-]+)\s*\|", re.MULTILINE)
COUNT_LINE = re.compile(r"^\*\*Count:\*\* (\d+) rows \(([^)]*)\)\.?$", re.MULTILINE)
SLICE_COUNT = re.compile(r"(\d+) ([a-z]+)")
NODEID = re.compile(r"`([^`\s]+::[^`\s]+)`")
CASE_FULL = re.compile(r"^(pyforge-[a-z]+)/tests/(.+)$")
CASE_SHORT = re.compile(r"^…/(.+)$")
LAUNCH_FULL = re.compile(r"^src/shared/packages/(pyforge-[a-z]+)/tests/(.+)$")


@dataclass(frozen=True)
class CaseRow:
    id: str
    slice: str
    target: str  # the `argv / nodeid` cell


@dataclass(frozen=True)
class NodeRef:
    package: str  # pyforge-<station>
    path: str  # under the package's tests/
    name: str  # the test function


def case_rows(text: str) -> list[CaseRow]:
    rows: list[CaseRow] = []
    for line in text.splitlines():
        if CASE_ROW.match(line):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            rows.append(CaseRow(cells[0], cells[1], cells[2]))
    return rows


def count_problems(text: str) -> list[str]:
    """What is wrong with the count line against the table; empty when it states the rows."""
    lines = COUNT_LINE.findall(text)
    if len(lines) != 1:
        return [f"expected one `**Count:** N rows (...)` line, found {len(lines)}"]
    stated, breakdown = int(lines[0][0]), lines[0][1]
    rows = case_rows(text)
    problems: list[str] = []
    if stated != len(rows):
        problems.append(f"the count line states {stated} rows; the table has {len(rows)}")
    stated_slices: Counter[str] = Counter()
    for number, name in SLICE_COUNT.findall(breakdown):
        stated_slices[name] += int(number)
    if sum(stated_slices.values()) != stated:
        problems.append(f"the count line's slices sum to {sum(stated_slices.values())}, not {stated}")
    table_slices = Counter(row.slice for row in rows)
    if stated_slices != table_slices:
        problems.append(f"the count line states {dict(stated_slices)} by slice; the table has {dict(table_slices)}")
    repeated = sorted(case_id for case_id, n in Counter(row.id for row in rows).items() if n > 1)
    if repeated:
        problems.append(f"ids repeated in the table (doctor's reader counts each once): {repeated}")
    return problems


def case_nodeids(rows: Iterable[CaseRow]) -> tuple[dict[str, NodeRef], list[str]]:
    """The case rows that name a pytest node id, resolved to a package test; rows naming an argv are skipped."""
    refs: dict[str, NodeRef] = {}
    problems: list[str] = []
    package: str | None = None
    for row in rows:
        match = NODEID.search(row.target)
        if match is None:
            continue  # an argv (`pyforge steward --help`) or a check on B, not a node id
        parts = match.group(1).split("::")
        if len(parts) != 2:
            problems.append(f"{row.id}: `{match.group(1)}` is not `<file>::<test function>`")
            continue
        file, name = parts
        full = CASE_FULL.match(file)
        short = CASE_SHORT.match(file)
        if full is not None:
            package, path = full.group(1), full.group(2)
        elif short is not None and package is not None:
            rest = short.group(1)
            path = rest if "/" in rest else f"unit/{rest}"
        else:
            problems.append(f"{row.id}: `{file}` is neither `pyforge-<station>/tests/…` nor `…/` below one")
            continue
        refs[row.id] = NodeRef(package, path, name)
    return refs, problems


def resolve_problems(refs: Mapping[str, NodeRef]) -> list[str]:
    """Static resolution: the file exists and defines the test. Nothing is imported, collected or run."""
    problems: list[str] = []
    for label, ref in refs.items():
        test_file = PACKAGES / ref.package / "tests" / ref.path
        if not test_file.is_file():
            problems.append(f"{label}: {ref.package}/tests/{ref.path} does not exist")
            continue
        defined = re.compile(rf"^[ \t]*(?:async[ \t]+)?def {re.escape(ref.name)}\(", re.MULTILINE)
        if defined.search(test_file.read_text(encoding="utf-8")) is None:
            problems.append(f"{label}: {ref.package}/tests/{ref.path} defines no `def {ref.name}`")
    return problems


def launch_slice_steps(text: str) -> tuple[list[str], int, list[str]]:
    """The steps table's nodeid column: (A test node ids, oracle gaps, cells that are neither)."""
    nodeids: list[str] = []
    gaps = 0
    unread: list[str] = []
    in_table = False
    for line in text.splitlines():
        if not in_table:
            in_table = line.startswith("| step |") and "A test nodeid" in line
            continue
        if not line.startswith("|"):
            break
        if line.startswith("|---"):
            continue
        cell = line.strip().strip("|").split("|")[-1].strip()
        match = NODEID.fullmatch(cell)
        if match is not None:
            nodeids.append(match.group(1))
        elif cell == "oracle gap":
            gaps += 1
        else:
            unread.append(line)
    return nodeids, gaps, unread


def test_the_count_line_equals_the_rows() -> None:
    text = CASE_LIST.read_text(encoding="utf-8")
    assert case_rows(text), "case-list.md has no `| k-` rows: the reader went blind"
    assert count_problems(text) == []


def test_every_case_list_nodeid_resolves() -> None:
    refs, problems = case_nodeids(case_rows(CASE_LIST.read_text(encoding="utf-8")))
    assert refs, "case-list.md names no node id: the reader went blind"
    assert problems + resolve_problems(refs) == []


def test_a_planted_count_is_reported(tmp_path: Path) -> None:
    before = CASE_LIST.read_text(encoding="utf-8")
    planted = tmp_path / "case-list.md"
    shutil.copyfile(CASE_LIST, planted)
    text = planted.read_text(encoding="utf-8")
    match = COUNT_LINE.search(text)
    assert match is not None
    stated = int(match.group(1))
    planted.write_text(text.replace(f"**Count:** {stated} rows", f"**Count:** {stated + 1} rows", 1), encoding="utf-8")
    problems = count_problems(planted.read_text(encoding="utf-8"))
    rows = len(case_rows(text))
    assert f"the count line states {stated + 1} rows; the table has {rows}" in problems
    assert CASE_LIST.read_text(encoding="utf-8") == before, "the check mutated the tracked case list"


def test_every_launch_slice_step_with_an_a_test_has_a_case_row() -> None:
    nodeids, _gaps, unread = launch_slice_steps(LAUNCH_SLICE.read_text(encoding="utf-8"))
    assert unread == [], "launch-slice.md step rows whose nodeid cell is neither a node id nor `oracle gap`"
    assert nodeids, "launch-slice.md's steps table names no A test: the reader went blind"
    launch: dict[str, NodeRef] = {}
    problems: list[str] = []
    for nodeid in nodeids:
        file, _, name = nodeid.partition("::")
        full = LAUNCH_FULL.match(file)
        if full is None:
            problems.append(f"`{nodeid}` is not a node id under a pyforge package's tests/")
            continue
        launch[nodeid] = NodeRef(full.group(1), full.group(2), name)
    problems += resolve_problems(launch)
    case_refs, case_problems = case_nodeids(case_rows(CASE_LIST.read_text(encoding="utf-8")))
    covered = set(case_refs.values())
    problems += case_problems
    problems += [
        f"launch-slice step test `{n}` has no case-list row" for n, ref in launch.items() if ref not in covered
    ]
    assert problems == []
