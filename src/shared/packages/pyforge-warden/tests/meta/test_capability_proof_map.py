"""Story 26.2 (spec-pyforge-warden CAP-28, FR-45): every warden capability names the test modules that prove it.

``proof-map.md``, beside ``SPEC.md`` and ``contract.md``, holds one row per capability ``SPEC.md`` defines: the
capability, its lane, the test modules that fail when its success clause is false, and the command that runs that
lane (CHAIN-STANDARD section 2: a success clause names its proof). A clause no module proves is a row under *Gaps*
naming its deferred-work ledger row. This test holds the map to the tree:

* every capability ``SPEC.md`` defines (a ``- **CAP-n — `` line) has a row, and every row names one it defines;
* every cited module exists: a ``tests/...`` path under this package, a ``src/...`` path from the repository root;
  a cell names test modules and nothing finer (no ``::``);
* each row's lane agrees with its module: ``slow`` when the module-level ``pytestmark`` carries ``slow`` (the
  corpus-oracle task, ``-m slow``, runs it whatever else it carries; the live-tree half is
  ``live_tree and not slow``, Story 27.1), else ``live-tree`` when it carries ``live_tree``, else ``platform`` when
  the path starts ``src/platform/``, else ``package``; and each row's command is its lane's command from *Lanes*;
* every *Gaps* row names a capability ``SPEC.md`` defines and a ledger id that exists as a ``### <id>:`` row of
  warden's ``deferred-work-ledger.md``.

The module reads ``SPEC.md``, ``proof-map.md`` and the ledger from the planning tree and the cited modules (under
``src/platform/tests`` too), so it is marked ``live_tree``. The repository root is computed in a fixture, never at
import, so the package half can collect this module from an export of the package. Negative tests use synthetic
tables and synthetic module sources, never a mutated tracked file.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.live_tree

SPEC_REL = "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md"
PROOF_MAP_REL = "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/proof-map.md"
LEDGER_REL = "_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md"

THIS_MODULE = "tests/meta/test_capability_proof_map.py"
CAP_28_GUARDS = ("tests/meta/test_public_contract.py", "tests/meta/test_contract_surface.py", THIS_MODULE)

PACKAGE = "package"
LIVE_TREE = "live-tree"
SLOW = "slow"
PLATFORM = "platform"
LANES = (PACKAGE, LIVE_TREE, SLOW, PLATFORM)

H_LANES = "## Lanes"
H_MAP = "## Proof map"
H_GAPS = "## Gaps"

PLATFORM_PREFIX = "src/platform/"
REPO_PREFIX = "src/"
PACKAGE_PREFIX = "tests/"

_SPEC_CAP = re.compile(r"^- \*\*CAP-(\d+) — ", re.MULTILINE)
_CAP_CELL = re.compile(r"\ACAP-(\d+)\Z")
_TOKEN = re.compile(r"`([^`]+)`")
_LEDGER_ID = re.compile(r"\ADW-[A-Za-z0-9][A-Za-z0-9.-]*\Z")
_LEDGER_HEADING = re.compile(r"^### (DW-[A-Za-z0-9][A-Za-z0-9.-]*):", re.MULTILINE)
_SEPARATOR = re.compile(r"\A\|[-:| ]+\|\Z")

Problems = list[str]


# ---------------------------------------------------------------------------
# Reading SPEC.md and proof-map.md
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    line: int
    cap: int
    lane: str
    modules: tuple[str, ...]
    command: str


@dataclass(frozen=True)
class Gap:
    line: int
    cap: int
    ledger_ids: tuple[str, ...]


@dataclass(frozen=True)
class ProofMap:
    lanes: Mapping[str, str]  # lane -> its command
    rows: tuple[Row, ...]
    gaps: tuple[Gap, ...]
    problems: tuple[str, ...]  # what the map's own shape gets wrong


def spec_capabilities(spec_text: str) -> set[int]:
    """The capabilities ``SPEC.md`` defines, one ``- **CAP-n — `` line each."""
    return {int(number) for number in _SPEC_CAP.findall(spec_text)}


def _section(text: str, heading: str) -> list[tuple[int, str]] | None:
    """The numbered lines under the exact ``heading``, up to the next ``#`` or ``##`` heading; None if absent."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == heading:
            body: list[tuple[int, str]] = []
            for number in range(index + 1, len(lines)):
                following = lines[number]
                if following.startswith(("# ", "## ")):
                    break
                body.append((number + 1, following))
            return body
    return None


def _table_rows(body: Sequence[tuple[int, str]]) -> list[tuple[int, list[str]]]:
    """The data rows of the section's table: the header row and the separator are skipped."""
    rows: list[tuple[int, list[str]]] = []
    header_seen = False
    for number, line in body:
        stripped = line.strip()
        if not stripped.startswith("|") or _SEPARATOR.match(stripped):
            continue
        if not header_seen:
            header_seen = True
            continue
        rows.append((number, [cell.strip() for cell in stripped.strip("|").split("|")]))
    return rows


def _module_problem(token: str) -> str | None:
    if "::" in token:
        return "names something finer than a module"
    if not token.endswith(".py"):
        return "is not a Python module"
    if not token.startswith((PACKAGE_PREFIX, REPO_PREFIX)):
        return f"starts neither {PACKAGE_PREFIX} (this package) nor {REPO_PREFIX} (the repository root)"
    return None


def parse_proof_map(text: str) -> ProofMap:
    problems: Problems = []

    lanes: dict[str, str] = {}
    lanes_body = _section(text, H_LANES)
    if lanes_body is None:
        problems.append(f"no {H_LANES!r} section")
    else:
        for number, cells in _table_rows(lanes_body):
            lane = cells[0].strip("`")
            commands = _TOKEN.findall(cells[-1])
            if lane not in LANES:
                problems.append(f"line {number}: {lane!r} is not a lane ({', '.join(LANES)})")
            elif lane in lanes:
                problems.append(f"line {number}: lane {lane!r} has two rows")
            elif len(commands) != 1:
                problems.append(f"line {number}: lane {lane!r} names {len(commands)} commands, not one")
            else:
                lanes[lane] = commands[0]
        problems.extend(f"{H_LANES}: lane {lane!r} has no row" for lane in LANES if lane not in lanes)

    rows: list[Row] = []
    map_body = _section(text, H_MAP)
    if map_body is None:
        problems.append(f"no {H_MAP!r} section")
    else:
        seen: set[tuple[int, str]] = set()
        for number, cells in _table_rows(map_body):
            if len(cells) != 4:
                problems.append(f"line {number}: {len(cells)} cells, not 4 (CAP, lane, test modules, command)")
                continue
            cap_cell, lane, modules_cell, command_cell = cells
            cap_match = _CAP_CELL.match(cap_cell)
            if cap_match is None:
                problems.append(f"line {number}: {cap_cell!r} is not a CAP-n cell")
                continue
            cap = int(cap_match.group(1))
            if lane not in LANES:
                problems.append(f"line {number}: CAP-{cap} names {lane!r}, which is not a lane")
                continue
            if (cap, lane) in seen:
                problems.append(f"line {number}: CAP-{cap} has two {lane} rows")
            seen.add((cap, lane))
            modules = tuple(_TOKEN.findall(modules_cell))
            if not modules:
                problems.append(f"line {number}: CAP-{cap} cites no test module")
            for token in modules:
                problem = _module_problem(token)
                if problem is not None:
                    problems.append(f"line {number}: CAP-{cap} cites {token!r}, which {problem}")
            commands = _TOKEN.findall(command_cell)
            if len(commands) != 1:
                problems.append(f"line {number}: CAP-{cap} names {len(commands)} commands, not one")
            rows.append(Row(number, cap, lane, modules, commands[0] if commands else ""))

    gaps: list[Gap] = []
    gaps_body = _section(text, H_GAPS)
    if gaps_body is None:
        problems.append(f"no {H_GAPS!r} section")
    else:
        for number, cells in _table_rows(gaps_body):
            cap_match = _CAP_CELL.match(cells[0])
            if cap_match is None or len(cells) != 3:
                problems.append(f"line {number}: a Gaps row is | CAP-n | the clause | the ledger id |")
                continue
            ids = tuple(_TOKEN.findall(cells[2])) or tuple(part for part in cells[2].split() if part)
            gaps.append(Gap(number, int(cap_match.group(1)), ids))

    return ProofMap(lanes, tuple(rows), tuple(gaps), tuple(problems))


# ---------------------------------------------------------------------------
# The checks (pure: the live tests and the synthetic ones share them)
# ---------------------------------------------------------------------------


def module_marks(source: str) -> frozenset[str]:
    """The marks a module's module-level ``pytestmark`` carries (one mark, or a list or tuple of them)."""
    marks: set[str] = set()
    for node in ast.parse(source).body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        if value is None or not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in targets):
            continue
        for sub in ast.walk(value):
            if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Attribute) and sub.value.attr == "mark":
                marks.add(sub.attr)
    return frozenset(marks)


def lane_of(cited: str, source: str | None) -> str:
    """The lane a cited module runs in (the order is the proof map's *Lanes* rule)."""
    marks = module_marks(source) if source is not None else frozenset()
    if "slow" in marks:
        return SLOW
    if "live_tree" in marks:
        return LIVE_TREE
    if cited.startswith(PLATFORM_PREFIX):
        return PLATFORM
    return PACKAGE


def missing_rows(defined: set[int], rows: Sequence[Row]) -> Problems:
    covered = {row.cap for row in rows}
    problems = [
        f"CAP-{cap}: SPEC.md defines it and proof-map.md has no row for it" for cap in sorted(defined - covered)
    ]
    problems.extend(
        f"line {row.line}: CAP-{row.cap} has a row, but SPEC.md defines no CAP-{row.cap}"
        for row in rows
        if row.cap not in defined
    )
    return problems


def dead_paths(rows: Sequence[Row], exists: Mapping[str, bool]) -> Problems:
    return [
        f"line {row.line}: CAP-{row.cap} cites {cited}, which does not exist"
        for row in rows
        for cited in row.modules
        if not exists.get(cited, False)
    ]


def lane_mismatches(rows: Sequence[Row], sources: Mapping[str, str | None]) -> Problems:
    """A module listed under a lane it does not run in. A dead path is ``dead_paths``'s to report."""
    problems: Problems = []
    for row in rows:
        for cited in row.modules:
            source = sources.get(cited)
            if source is None and not cited.startswith(PLATFORM_PREFIX):
                continue
            lane = lane_of(cited, source)
            if lane != row.lane:
                problems.append(f"line {row.line}: CAP-{row.cap} lists {cited} under {row.lane}, but it runs in {lane}")
    return problems


def command_mismatches(lanes: Mapping[str, str], rows: Sequence[Row]) -> Problems:
    return [
        f"line {row.line}: CAP-{row.cap}'s command is not the {row.lane} lane's command in {H_LANES}"
        for row in rows
        if row.lane in lanes and row.command != lanes[row.lane]
    ]


def unknown_gap_ids(gaps: Sequence[Gap], defined: set[int], ledger_text: str) -> Problems:
    ledger_ids = set(_LEDGER_HEADING.findall(ledger_text))
    problems: Problems = []
    for gap in gaps:
        if gap.cap not in defined:
            problems.append(f"line {gap.line}: a gap for CAP-{gap.cap}, which SPEC.md does not define")
        if not gap.ledger_ids:
            problems.append(f"line {gap.line}: the CAP-{gap.cap} gap names no ledger id")
        for ledger_id in gap.ledger_ids:
            if not _LEDGER_ID.match(ledger_id):
                problems.append(f"line {gap.line}: the CAP-{gap.cap} gap names {ledger_id!r}, which is not a DW id")
            elif ledger_id not in ledger_ids:
                problems.append(f"line {gap.line}: the CAP-{gap.cap} gap names {ledger_id}, which has no ledger row")
    return problems


# ---------------------------------------------------------------------------
# The live tree
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def repo_root() -> Path:
    # tests/meta -> tests -> pyforge-warden -> packages -> shared -> src -> repo root (computed here, not at import)
    return Path(__file__).resolve().parents[6]


@pytest.fixture(scope="module")
def package_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def defined(repo_root: Path) -> set[int]:
    return spec_capabilities((repo_root / SPEC_REL).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def proof_map(repo_root: Path) -> ProofMap:
    return parse_proof_map((repo_root / PROOF_MAP_REL).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger_text(repo_root: Path) -> str:
    return (repo_root / LEDGER_REL).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cited_files(repo_root: Path, package_root: Path, proof_map: ProofMap) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for row in proof_map.rows:
        for cited in row.modules:
            files[cited] = repo_root / cited if cited.startswith(REPO_PREFIX) else package_root / cited
    return files


def test_the_proof_map_parses(proof_map: ProofMap):
    assert list(proof_map.problems) == []
    assert set(proof_map.lanes) == set(LANES)
    assert {row.lane for row in proof_map.rows} == set(LANES)


def test_every_capability_spec_md_defines_has_a_proof_row(defined: set[int], proof_map: ProofMap):
    assert defined, f"no '- **CAP-n — ' line in {SPEC_REL}: the derivation went blind"
    assert missing_rows(defined, proof_map.rows) == []


def test_every_cited_module_exists(proof_map: ProofMap, cited_files: dict[str, Path]):
    assert cited_files
    assert dead_paths(proof_map.rows, {cited: path.is_file() for cited, path in cited_files.items()}) == []


def test_every_row_names_the_lane_its_modules_run_in(proof_map: ProofMap, cited_files: dict[str, Path]):
    sources = {
        cited: path.read_text(encoding="utf-8") if path.is_file() else None for cited, path in cited_files.items()
    }
    assert lane_mismatches(proof_map.rows, sources) == []
    assert command_mismatches(proof_map.lanes, proof_map.rows) == []


def test_every_gap_names_a_ledger_row(defined: set[int], proof_map: ProofMap, ledger_text: str):
    assert unknown_gap_ids(proof_map.gaps, defined, ledger_text) == []


def test_cap_28_cites_its_own_guards(proof_map: ProofMap):
    cited = {module for row in proof_map.rows if row.cap == 28 for module in row.modules}
    assert set(CAP_28_GUARDS) <= cited


# ---------------------------------------------------------------------------
# The rule on synthetic tables: each failure is reported, by name
# ---------------------------------------------------------------------------

_LANES_TABLE = """\
## Lanes

| lane | what runs there | command |
| --- | --- | --- |
| package | the package half | `package-command` |
| live-tree | the live-tree half | `live-command` |
| slow | the corpus-oracle task | `slow-command` |
| platform | the platform suite | `platform-command` |
"""

_COMMAND = {PACKAGE: "package-command", LIVE_TREE: "live-command", SLOW: "slow-command", PLATFORM: "platform-command"}

_SOURCES: dict[str, str | None] = {
    "tests/unit/test_synthetic_package.py": "def test_x():\n    pass\n",
    "tests/meta/test_synthetic_live.py": "import pytest\npytestmark = pytest.mark.live_tree\n",
    "tests/integration/test_synthetic_slow.py": "import pytest\npytestmark = pytest.mark.slow\n",
    "tests/integration/test_synthetic_both.py": "import pytest\npytestmark = [pytest.mark.slow, pytest.mark.live_tree]\n",
    "src/platform/tests/test_synthetic_platform.py": "def test_x():\n    pass\n",
}


def _row(cap: int, lane: str, *modules: str, command: str | None = None) -> str:
    cells = ", ".join(f"`{module}`" for module in modules)
    return f"| CAP-{cap} | {lane} | {cells} | `{_COMMAND[lane] if command is None else command}` |\n"


_MAP_HEAD = "\n## Proof map\n\n| CAP | lane | test modules | command |\n| --- | --- | --- | --- |\n"
_GAPS_HEAD = "\n## Gaps\n\n| CAP | clause (quoted short) | deferral |\n| --- | --- | --- |\n"


def _synthetic(rows: str, gaps: str = "", *, with_gaps: bool = True) -> str:
    return _LANES_TABLE + _MAP_HEAD + rows + (_GAPS_HEAD + gaps if with_gaps else "")


def _all_problems(text: str, defined: set[int], ledger: str = "") -> Problems:
    parsed = parse_proof_map(text)
    exists = {cited: cited in _SOURCES for row in parsed.rows for cited in row.modules}
    return [
        *parsed.problems,
        *missing_rows(defined, parsed.rows),
        *dead_paths(parsed.rows, exists),
        *lane_mismatches(parsed.rows, _SOURCES),
        *command_mismatches(parsed.lanes, parsed.rows),
        *unknown_gap_ids(parsed.gaps, defined, ledger),
    ]


_CLEAN_ROWS = (
    _row(1, PACKAGE, "tests/unit/test_synthetic_package.py")
    + _row(1, LIVE_TREE, "tests/meta/test_synthetic_live.py")
    + _row(2, SLOW, "tests/integration/test_synthetic_slow.py", "tests/integration/test_synthetic_both.py")
    + _row(3, PLATFORM, "src/platform/tests/test_synthetic_platform.py")
)
_LEDGER = "### DW-warden-synthetic-1: a synthetic gap\n\n- summary: a synthetic gap\n"
# The line numbers the problems name: a row added after the clean rows, the last clean row, the first gap row.
_ADDED_ROW = len((_LANES_TABLE + _MAP_HEAD + _CLEAN_ROWS).splitlines()) + 1
_LAST_CLEAN_ROW = _ADDED_ROW - 1
_FIRST_GAP = len((_LANES_TABLE + _MAP_HEAD + _CLEAN_ROWS + _GAPS_HEAD).splitlines()) + 1


def test_a_clean_synthetic_map_has_no_problems():
    text = _synthetic(_CLEAN_ROWS, '| CAP-3 | "a clause" | `DW-warden-synthetic-1` |\n')
    assert _all_problems(text, {1, 2, 3}, _LEDGER) == []


def test_spec_capabilities_reads_the_definition_lines_only():
    spec = "- **CAP-1 — one** ← x\n  - **success:** cites CAP-9\n- **CAP-12 — two** ← y\nCAP-4 in prose\n"
    assert spec_capabilities(spec) == {1, 12}


def test_a_dead_path_is_reported():
    rows = _CLEAN_ROWS + _row(4, PACKAGE, "tests/unit/test_synthetic_no_such_module.py")
    problems = _all_problems(_synthetic(rows), {1, 2, 3, 4})
    assert problems == [
        f"line {_ADDED_ROW}: CAP-4 cites tests/unit/test_synthetic_no_such_module.py, which does not exist"
    ]


def test_a_capability_with_no_row_is_reported():
    problems = _all_problems(_synthetic(_CLEAN_ROWS), {1, 2, 3, 4})
    assert problems == ["CAP-4: SPEC.md defines it and proof-map.md has no row for it"]


def test_a_row_for_a_capability_spec_md_does_not_define_is_reported():
    problems = _all_problems(_synthetic(_CLEAN_ROWS), {1, 2})
    assert problems == [f"line {_LAST_CLEAN_ROW}: CAP-3 has a row, but SPEC.md defines no CAP-3"]


@pytest.mark.parametrize(
    ("lane", "module", "runs_in"),
    [
        (PACKAGE, "tests/meta/test_synthetic_live.py", LIVE_TREE),
        (LIVE_TREE, "tests/unit/test_synthetic_package.py", PACKAGE),
        (PACKAGE, "tests/integration/test_synthetic_slow.py", SLOW),
        (LIVE_TREE, "tests/integration/test_synthetic_both.py", SLOW),
        (PACKAGE, "src/platform/tests/test_synthetic_platform.py", PLATFORM),
        (PLATFORM, "tests/unit/test_synthetic_package.py", PACKAGE),
    ],
)
def test_a_lane_mismatch_is_reported(lane: str, module: str, runs_in: str):
    problems = _all_problems(_synthetic(_CLEAN_ROWS + _row(4, lane, module)), {1, 2, 3, 4})
    assert problems == [f"line {_ADDED_ROW}: CAP-4 lists {module} under {lane}, but it runs in {runs_in}"]


def test_a_lane_mismatch_of_the_command_is_reported():
    rows = _CLEAN_ROWS + _row(4, PACKAGE, "tests/unit/test_synthetic_package.py", command="live-command")
    problems = _all_problems(_synthetic(rows), {1, 2, 3, 4})
    assert problems == [f"line {_ADDED_ROW}: CAP-4's command is not the package lane's command in {H_LANES}"]


def test_the_lane_rule_reads_module_level_marks_only():
    assert lane_of("tests/unit/test_x.py", "import pytest\n@pytest.mark.slow\ndef test_x():\n    pass\n") == PACKAGE
    assert lane_of("tests/unit/test_x.py", "import pytest\npytestmark: list = [pytest.mark.live_tree]\n") == LIVE_TREE
    assert lane_of("src/platform/tests/test_x.py", None) == PLATFORM


def test_a_cell_finer_than_a_module_is_reported():
    rows = _CLEAN_ROWS + _row(4, PACKAGE, "tests/unit/test_synthetic_package.py::test_x")
    problems = parse_proof_map(_synthetic(rows)).problems
    assert problems == (
        f"line {_ADDED_ROW}: CAP-4 cites 'tests/unit/test_synthetic_package.py::test_x', which names something finer "
        "than a module",
    )


def test_an_unknown_lane_is_reported():
    text = _synthetic(_CLEAN_ROWS + "| CAP-4 | nightly | `tests/unit/test_synthetic_package.py` | `x` |\n")
    assert parse_proof_map(text).problems == (f"line {_ADDED_ROW}: CAP-4 names 'nightly', which is not a lane",)


def test_a_gap_with_an_unknown_ledger_id_is_reported():
    text = _synthetic(_CLEAN_ROWS, '| CAP-3 | "a clause" | `DW-warden-synthetic-2` |\n')
    problems = _all_problems(text, {1, 2, 3}, _LEDGER)
    assert problems == [f"line {_FIRST_GAP}: the CAP-3 gap names DW-warden-synthetic-2, which has no ledger row"]


def test_a_gap_with_no_ledger_id_is_reported():
    text = _synthetic(_CLEAN_ROWS, '| CAP-3 | "a clause" |  |\n')
    assert _all_problems(text, {1, 2, 3}, _LEDGER) == [f"line {_FIRST_GAP}: the CAP-3 gap names no ledger id"]


def test_a_missing_gaps_section_is_reported():
    assert parse_proof_map(_synthetic(_CLEAN_ROWS, with_gaps=False)).problems == ("no '## Gaps' section",)
