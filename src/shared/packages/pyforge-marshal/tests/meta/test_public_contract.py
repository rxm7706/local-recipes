"""Meta test -- marshal's public contract and its code agree, both ways (Story 114.3, spec-pyforge-marshal:CAP-304).

``contract.md`` beside ``spec-pyforge-marshal``'s ``SPEC.md`` names every way marshal is addressed and every signal it
emits: each CLI verb path and flag, each MCP tool (``marshal-mcp`` and the station face), each feature-flag key and
environment variable it reads, each diagnostic code and each exit code. ``tests/_support/contract_inventory.py``
derives each family from the code that defines it -- this module never types an inventory -- and the comparison below
reports, item by item:

* ``missing_from_the_contract``: the code has the item, ``contract.md`` has no row for it;
* ``stale_in_the_contract``: ``contract.md`` keeps a row the code no longer has;
* ``differs``: a checked cell (a ``marshal-mcp`` tool's *Runs*, a finding code's *Verdict*, a seed finding type's
  *Member*, an exit code's *Meaning* or *Leaf*) disagrees with the code.

What it reads from ``contract.md``: its six ``## `` sections by title (exactly six, in order), the ``### `` headings
that name the tables of the MCP, diagnostic and exit-code sections, and in every table row the first backticked token
(the item) and the checked cell. A CLI row's flags are the backticked tokens of its second cell that start with ``-``.

Each family carries a mutation test both ways: the code gains an item the contract lacks (a parser verb or flag, a
``TOOL_SPECS`` entry, a station-face registration, a flag-key constant, an ``os.environ`` read, a registered code, a
``FindingType`` member, an exit code), and the contract keeps a row the code lacks. ``contract.md`` sits outside the
package, so the module is ``live_tree`` and fails, never skips, when the file is absent; the checkout root is found
when a test runs, never at import.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

pytestmark = pytest.mark.live_tree

_MARSHAL_PACKAGE_RELPATH = Path("src/shared/packages/pyforge-marshal")
_CONTRACT_RELPATH = Path(
    "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/contract.md"
)
_INVENTORY_PATH = Path(__file__).resolve().parents[1] / "_support" / "contract_inventory.py"
_INVENTORY_MODULE = "pyforge_marshal_tests_support_contract_inventory"


def _load_inventory() -> ModuleType:
    """``tests/_support`` is not a package on ``sys.path``; load the module by path, once per process."""
    loaded = sys.modules.get(_INVENTORY_MODULE)
    if loaded is not None:
        return loaded
    spec = importlib.util.spec_from_file_location(_INVENTORY_MODULE, _INVENTORY_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_INVENTORY_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_INVENTORY_MODULE] = module
    spec.loader.exec_module(module)
    return module


ci = _load_inventory()

MISSING = "missing_from_the_contract"
STALE = "stale_in_the_contract"
DIFFERS = "differs"

# The six sections, in order, and the tables the multi-table sections hold (heading -> the inventory's prefix).
SECTIONS: tuple[str, ...] = (
    "CLI verbs and flags",
    "MCP tools",
    "Feature-flag keys",
    "Environment variables",
    "Diagnostic codes",
    "Exit codes",
)
SUBSECTIONS: dict[str, dict[str, str]] = {
    "MCP tools": {
        "`marshal-mcp` (stdio)": ci.MARSHAL_MCP,
        "Station face (`POST /stations/marshal/mcp`)": ci.STATION_FACE,
    },
    "Diagnostic codes": {
        "`MRS-*` finding codes": ci.DIAGNOSTIC_CODE,
        "Seed finding types": ci.SEED_FINDING_TYPE,
    },
    "Exit codes": {
        "Every verb": ci.EVERY_VERB,
        "The `seed` verb group": ci.SEED_GROUP,
    },
}

_TOKEN = re.compile(r"`([^`]+)`")
_SEPARATOR = re.compile(r"\|[\s:|-]+\|")


@dataclass(frozen=True)
class Finding:
    kind: str
    family: str
    item: str
    detail: str = ""

    def __str__(self) -> str:
        suffix = f" ({self.detail})" if self.detail else ""
        return f"{self.kind}: {self.family} `{self.item}`{suffix}"


@dataclass(frozen=True)
class Contract:
    sections: tuple[str, ...]
    items: Mapping[tuple[str, str], str | None]
    problems: tuple[str, ...]


# -- reading contract.md -------------------------------------------------------------------------------------------


def _checkout_root() -> Path:
    """The source checkout this file sits in: the nearest ancestor carrying the package (found at call time)."""
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / _MARSHAL_PACKAGE_RELPATH).is_dir():
            return ancestor
    pytest.fail(f"{__file__} is not inside a source checkout of {_MARSHAL_PACKAGE_RELPATH}")


def _contract_text() -> str:
    path = _checkout_root() / _CONTRACT_RELPATH
    if not path.is_file():
        pytest.fail(f"the live tree has no {_CONTRACT_RELPATH} (this live-tree contract reads it)")
    return path.read_text(encoding="utf-8")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _tokens(cell: str) -> list[str]:
    return _TOKEN.findall(cell)


def _row_items(table: str, cells: list[str]) -> dict[tuple[str, str], str | None]:
    """The ``(family, item) -> detail`` pairs one table row names (see the module docstring)."""
    keys = _tokens(cells[0])
    if not keys:
        raise ValueError("its first cell has no backticked item")
    key = keys[0]
    second = cells[1] if len(cells) > 1 else ""
    second_tokens = _tokens(second)
    if table == "CLI verbs and flags":
        if key != "marshal" and not key.startswith("marshal "):
            raise ValueError(f"{key!r} is not a `marshal` command")
        path = key.removeprefix("marshal").strip()
        items: dict[tuple[str, str], str | None] = {(ci.VERB_PATH, path): None}
        items.update({(ci.FLAG, f"{path} {flag}".strip()): None for flag in second_tokens if flag.startswith("-")})
        return items
    if table == ci.MARSHAL_MCP:
        return {(ci.TOOL, f"{ci.MARSHAL_MCP} {key}"): second_tokens[0] if second_tokens else None}
    if table == ci.STATION_FACE:
        return {(ci.TOOL, f"{ci.STATION_FACE} {key}"): None}
    if table == "Feature-flag keys":
        return {(ci.FLAG_KEY, key): None}
    if table == "Environment variables":
        return {(ci.ENV_VAR, key): None}
    if table in (ci.DIAGNOSTIC_CODE, ci.SEED_FINDING_TYPE):
        return {(table, key): second_tokens[0] if second_tokens else None}
    if table == ci.EVERY_VERB:
        return {(ci.EXIT_CODE, f"{ci.EVERY_VERB} {key}"): ", ".join(sorted(second_tokens))}
    if table == ci.SEED_GROUP:
        return {(ci.EXIT_CODE, f"{ci.SEED_GROUP} {key}"): second_tokens[0] if second_tokens else None}
    raise ValueError(f"no family reads the table {table!r}")


def parse_contract(text: str) -> Contract:
    sections: list[str] = []
    items: dict[tuple[str, str], str | None] = {}
    problems: list[str] = []
    section: str | None = None
    table: str | None = None
    lines = text.splitlines()
    in_table = False
    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            section = line[3:].strip()
            sections.append(section)
            table = None if section in SUBSECTIONS else section
            in_table = False
            continue
        if line.startswith("### "):
            heading = line[4:].strip()
            table = SUBSECTIONS.get(section or "", {}).get(heading)
            if table is None:
                problems.append(f"line {number}: no table of section {section!r} is named {heading!r}")
            in_table = False
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        if not in_table:
            in_table = True  # the header row
            continue
        if _SEPARATOR.fullmatch(line.strip()):
            continue
        if table is None:
            problems.append(f"line {number}: a table row outside any table this test reads")
            continue
        try:
            row = _row_items(table, _cells(line))
        except ValueError as exc:
            problems.append(f"line {number}: {exc}")
            continue
        for item, detail in row.items():
            if item in items:
                problems.append(f"line {number}: {item[0]} `{item[1]}` is listed twice")
            items[item] = detail
    return Contract(tuple(sections), items, tuple(problems))


# -- the comparison ------------------------------------------------------------------------------------------------


def _shown(item: str) -> str:
    return item or "marshal"


def compare(code: Any, contract: Contract) -> list[Finding]:
    """Every item the code and the contract disagree on, both ways."""
    findings: list[Finding] = []
    for key in sorted(code.items.keys() - contract.items.keys()):
        findings.append(Finding(MISSING, key[0], _shown(key[1])))
    for key in sorted(contract.items.keys() - code.items.keys()):
        findings.append(Finding(STALE, key[0], _shown(key[1])))
    for key in sorted(code.items.keys() & contract.items.keys()):
        expected, written = code.items[key], contract.items[key]
        if expected != written:
            findings.append(
                Finding(DIFFERS, key[0], _shown(key[1]), f"the code says {expected!r}, the contract {written!r}")
            )
    return findings


# -- fixtures ------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def contract_text() -> str:
    return _contract_text()


@pytest.fixture(scope="module")
def contract(contract_text: str) -> Contract:
    return parse_contract(contract_text)


@pytest.fixture(scope="module")
def sources() -> dict[str, str]:
    return ci.marshal_sources()


@pytest.fixture(scope="module")
def code(sources: dict[str, str]) -> Any:
    return ci.inventory(sources=sources)


# -- the tree ------------------------------------------------------------------------------------------------------


def test_the_contract_has_its_six_sections_in_order(contract: Contract) -> None:
    assert contract.sections == SECTIONS


def test_the_contract_parses_cleanly(contract: Contract) -> None:
    assert contract.problems == ()


def test_the_contract_and_the_code_agree(code: Any, contract: Contract) -> None:
    findings = compare(code, contract)
    assert findings == [], (
        "contract.md and marshal's code disagree; change contract.md in the same change as the code:\n"
        + "\n".join(str(finding) for finding in findings)
    )


def test_every_family_is_derived_and_non_empty(code: Any) -> None:
    """A family that derives nothing would agree with an empty table; each family must find something."""
    assert {family for family, _ in code.items} == set(ci.FAMILIES)
    assert {item.split()[0] for item in code.family(ci.TOOL)} == {ci.MARSHAL_MCP, ci.STATION_FACE}
    assert {item.split()[0] for item in code.family(ci.EXIT_CODE)} == {ci.EVERY_VERB, ci.SEED_GROUP}


def test_the_root_of_record_key_comes_through_the_seam(sources: dict[str, str]) -> None:
    """``pyforge.cutover_root`` is a flag key though no marshal module holds the string (Story 115.4)."""
    from pyforge.core.cutover_root import CUTOVER_FLAG

    held = {
        relpath
        for relpath, text in sources.items()
        for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.Constant) and node.value == CUTOVER_FLAG
    }
    assert held == set()
    assert (ci.FLAG_KEY, CUTOVER_FLAG) in ci.flag_key_items(sources)
    reader = re.compile(r"^from pyforge\.core\.cutover_root import .*\broot_of_record\b.*$", re.MULTILINE)
    without_the_seam = {relpath: reader.sub("", text) for relpath, text in sources.items()}
    assert (ci.FLAG_KEY, CUTOVER_FLAG) not in ci.flag_key_items(without_the_seam)


def test_a_module_path_is_not_a_flag_key(sources: dict[str, str]) -> None:
    keys = ci.flag_key_items({**sources, "cli/fixture.py": 'MODULE = "pyforge.marshal.supervisor"\n'})
    assert (ci.FLAG_KEY, "pyforge.marshal.supervisor") not in keys


# -- mutations: the code gains an item the contract lacks ----------------------------------------------------------


def _with_verb() -> dict[tuple[str, str], str | None]:
    from pyforge.marshal.cli.main import _build_parser

    parser = _build_parser()
    sub = ci._subparsers(parser)
    assert sub is not None
    sub.add_parser("phantom-verb")
    return ci.cli_items(parser)


def _parser_for(parser: argparse.ArgumentParser, path: str) -> argparse.ArgumentParser:
    for found, sub in ci._walk_parser(parser, ""):
        if found == path:
            return sub
    raise LookupError(path)


def _with_flag() -> dict[tuple[str, str], str | None]:
    from pyforge.marshal.cli.main import _build_parser

    parser = _build_parser()
    _parser_for(parser, "status").add_argument("--phantom-flag", action="store_true", help="fixture")
    return ci.cli_items(parser)


def _with_tool() -> dict[tuple[str, str], str | None]:
    from pyforge.marshal.mcp.tools import TOOL_SPECS

    specs = {**TOOL_SPECS, "marshal_phantom": {"description": "fixture", "cli": ["status", "--format", "json"]}}
    return ci.marshal_mcp_items(specs)


def _with_face_tool() -> dict[tuple[str, str], str | None]:
    face = (ci.packages_dir() / ci._FACE_RELATIVE).read_text(encoding="utf-8")
    phantom = '\n\n@server.tool(name="phantom_face_tool")\ndef phantom_face_tool() -> None:\n    return None\n'
    return ci.station_face_items(face + phantom)


def _with_source(text: str) -> Callable[[dict[str, str]], dict[str, str]]:
    def mutate(sources: dict[str, str]) -> dict[str, str]:
        return {**sources, "cli/phantom_fixture.py": text}

    return mutate


def _with_code() -> dict[tuple[str, str], str | None]:
    from pyforge.marshal.core.findings import REGISTERED_CODES

    return ci.diagnostic_items(REGISTERED_CODES | {"MRS-PHANTOM-001"})


def _with_finding_type() -> dict[tuple[str, str], str | None]:
    from pyforge.marshal.seed.detect.findings import FindingType

    return ci.seed_finding_type_items({**{m.value: m.name for m in FindingType}, "phantom-type": "PHANTOM_TYPE"})


def _with_every_verb_exit() -> dict[tuple[str, str], str | None]:
    from pyforge.marshal.core.verdict import GUARDED_EXIT_CODES

    meanings = ci._every_verb_meanings()
    return ci.exit_code_items(guarded={**{c: meanings.get(c, []) for c in GUARDED_EXIT_CODES}, 99: ["phantom"]})


def _with_seed_exit() -> dict[tuple[str, str], str | None]:
    return ci.exit_code_items(seed={**ci._seed_leaves(), 11: "PhantomFailure"})


GAINS: dict[str, tuple[Callable[[dict[str, str]], dict[tuple[str, str], str | None]], tuple[str, str]]] = {
    "verb-path": (lambda _s: _with_verb(), (ci.VERB_PATH, "phantom-verb")),
    "flag": (lambda _s: _with_flag(), (ci.FLAG, "status --phantom-flag")),
    "marshal-mcp-tool": (lambda _s: _with_tool(), (ci.TOOL, f"{ci.MARSHAL_MCP} marshal_phantom")),
    "station-face-tool": (lambda _s: _with_face_tool(), (ci.TOOL, f"{ci.STATION_FACE} phantom_face_tool")),
    "flag-key": (
        lambda s: ci.flag_key_items(_with_source('PHANTOM_KEY = "pyforge.marshal.phantom_key"\n')(s)),
        (ci.FLAG_KEY, "pyforge.marshal.phantom_key"),
    ),
    "environment-variable": (
        lambda s: ci.env_items(_with_source('import os\n\nVALUE = os.environ.get("MARSHAL_PHANTOM")\n')(s)),
        (ci.ENV_VAR, "MARSHAL_PHANTOM"),
    ),
    "diagnostic-code": (lambda _s: _with_code(), (ci.DIAGNOSTIC_CODE, "MRS-PHANTOM-001")),
    "seed-finding-type": (lambda _s: _with_finding_type(), (ci.SEED_FINDING_TYPE, "phantom-type")),
    "exit-code-every-verb": (lambda _s: _with_every_verb_exit(), (ci.EXIT_CODE, f"{ci.EVERY_VERB} 99")),
    "exit-code-seed": (lambda _s: _with_seed_exit(), (ci.EXIT_CODE, f"{ci.SEED_GROUP} 11")),
}


@pytest.mark.parametrize("family", sorted(GAINS))
def test_an_item_the_code_gains_is_missing_from_the_contract(
    family: str, code: Any, contract: Contract, sources: dict[str, str]
) -> None:
    derive, (kind, item) = GAINS[family]
    gained = ci.Inventory({**code.items, **derive(sources)})
    assert compare(gained, contract) == [Finding(MISSING, kind, item)]


# -- mutations: the contract keeps a row the code lacks -----------------------------------------------------------


def _insert_row(text: str, heading: str, row: str) -> str:
    """``text`` with ``row`` added as the first body row of the table under ``heading`` (a ``##``/``###`` line)."""
    lines = text.splitlines()
    start = lines.index(heading)
    for index in range(start + 1, len(lines)):
        if _SEPARATOR.fullmatch(lines[index].strip()):
            lines.insert(index + 1, row)
            return "\n".join(lines) + "\n"
    raise LookupError(heading)


def _with_extra_flag(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("| `marshal status` |"):
            lines[index] = line.rstrip().removesuffix("|").rstrip() + ", `--phantom-flag` |"
            return "\n".join(lines) + "\n"
    raise LookupError("marshal status")


STALE_ROWS: dict[str, tuple[Callable[[str], str], tuple[str, str]]] = {
    "verb-path": (
        lambda t: _insert_row(t, "## CLI verbs and flags", "| `marshal phantom-verb` | — |"),
        (ci.VERB_PATH, "phantom-verb"),
    ),
    "flag": (_with_extra_flag, (ci.FLAG, "status --phantom-flag")),
    "marshal-mcp-tool": (
        lambda t: _insert_row(t, "### `marshal-mcp` (stdio)", "| `marshal_phantom` | — | fixture |"),
        (ci.TOOL, f"{ci.MARSHAL_MCP} marshal_phantom"),
    ),
    "station-face-tool": (
        lambda t: _insert_row(
            t, "### Station face (`POST /stations/marshal/mcp`)", "| `phantom_face_tool` | fixture |"
        ),
        (ci.TOOL, f"{ci.STATION_FACE} phantom_face_tool"),
    ),
    "flag-key": (
        lambda t: _insert_row(t, "## Feature-flag keys", "| `pyforge.marshal.phantom_key` | fixture |"),
        (ci.FLAG_KEY, "pyforge.marshal.phantom_key"),
    ),
    "environment-variable": (
        lambda t: _insert_row(t, "## Environment variables", "| `MARSHAL_PHANTOM` | fixture |"),
        (ci.ENV_VAR, "MARSHAL_PHANTOM"),
    ),
    "diagnostic-code": (
        lambda t: _insert_row(t, "### `MRS-*` finding codes", "| `MRS-PHANTOM-001` | `error` |"),
        (ci.DIAGNOSTIC_CODE, "MRS-PHANTOM-001"),
    ),
    "seed-finding-type": (
        lambda t: _insert_row(t, "### Seed finding types", "| `phantom-type` | `PHANTOM_TYPE` |"),
        (ci.SEED_FINDING_TYPE, "phantom-type"),
    ),
    "exit-code-every-verb": (
        lambda t: _insert_row(t, "### Every verb", "| `99` | `phantom` | fixture |"),
        (ci.EXIT_CODE, f"{ci.EVERY_VERB} 99"),
    ),
    "exit-code-seed": (
        lambda t: _insert_row(t, "### The `seed` verb group", "| `11` | `PhantomFailure` | fixture |"),
        (ci.EXIT_CODE, f"{ci.SEED_GROUP} 11"),
    ),
}


@pytest.mark.parametrize("family", sorted(STALE_ROWS))
def test_a_row_the_code_lacks_is_stale_in_the_contract(family: str, code: Any, contract_text: str) -> None:
    mutate, (kind, item) = STALE_ROWS[family]
    kept = parse_contract(mutate(contract_text))
    assert kept.problems == ()
    assert compare(code, kept) == [Finding(STALE, kind, item)]


def test_both_mutation_tables_cover_every_family() -> None:
    covered = {kind for _derive, (kind, _item) in GAINS.values()}
    assert covered == set(ci.FAMILIES)
    assert {kind for _mutate, (kind, _item) in STALE_ROWS.values()} == set(ci.FAMILIES)


# -- a checked cell that disagrees ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("before", "after", "kind", "item"),
    [
        (
            "| `marshal_status` | `marshal status --format json` |",
            "| `marshal_status` | `marshal status --format text` |",
            ci.TOOL,
            f"{ci.MARSHAL_MCP} marshal_status",
        ),
        ("| `MRS-GATE-001` | `", "| `MRS-GATE-001` | `x", ci.DIAGNOSTIC_CODE, "MRS-GATE-001"),
        (
            "| `artifact-missing` | `ARTIFACT_MISSING` |",
            "| `artifact-missing` | `OTHER` |",
            ci.SEED_FINDING_TYPE,
            "artifact-missing",
        ),
        ("| `3` | `gate-failed` |", "| `3` | `error` |", ci.EXIT_CODE, f"{ci.EVERY_VERB} 3"),
        ("| `10` | `InternalError` |", "| `10` | `StateInvalid` |", ci.EXIT_CODE, f"{ci.SEED_GROUP} 10"),
    ],
)
def test_a_checked_cell_that_disagrees_differs(
    before: str, after: str, kind: str, item: str, code: Any, contract_text: str
) -> None:
    assert contract_text.count(before) == 1
    edited = parse_contract(contract_text.replace(before, after))
    assert [(f.kind, f.family, f.item) for f in compare(code, edited)] == [(DIFFERS, kind, item)]


# -- the parser refuses what it cannot read ------------------------------------------------------------------------


def test_an_unknown_table_heading_and_a_duplicate_row_are_problems(contract_text: str) -> None:
    unknown = parse_contract(contract_text.replace("### Seed finding types", "### Seed types"))
    assert any("Seed types" in problem for problem in unknown.problems)
    duplicated = parse_contract(_insert_row(contract_text, "## Environment variables", "| `PATH` | again |"))
    assert any("listed twice" in problem for problem in duplicated.problems)
