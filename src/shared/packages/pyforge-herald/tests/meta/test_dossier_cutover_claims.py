"""Story 51.2 (spec-python-foundry-cutover:CAP-14; spec-pyforge-herald:CAP-43, spec-pyforge-herald:CAP-61): each
cutover claim the dossier makes resolves against the tree.

``docs-site/src/content/dossier/dossier.yml`` is the cutover state ``AGENTS.md`` points every reader to. Every row of
the A→B.3 table (the four campaign verbs), each body line of the Operator watch callout (a parallel ``asserts:``
list, one entry per line) and each § 10 row carries ``asserts:``, a list from a closed grammar this module resolves
as data from tracked files -- no ``gh``, no network, no ``pyforge.steward`` import:

* ``story:<station>/<E>-<S>=<status>`` and ``epic:<station>/<E>=<status>``, against that station's tracked
  ``_bmad-output/projects/pyforge-<station>/planning-artifacts/sprint-status-ledger.yaml``;
* ``flag:pyforge.cutover_root=<variant>``, against the default variant in ``src/platform/config/flags.json``;
* ``ledger:mode:<mode>=<n>``, ``ledger:claim:<state>=<n>`` and ``ledger:claim-field=absent|present``, against
  ``docs/foundry/capability-ledger.yaml``.

A claim count over a ledger whose rows carry no claim field is unresolvable, never 0: a row that says nothing is in
effect on B carries ``ledger:claim-field=...`` beside its count, so the day the field arrives or leaves, the row reds
and is restated. Every verdict is true, false or unresolvable, and only true passes.

Two text rules hold the prose to its asserts: a story number or ``Epic <n>`` a claim's text names has an assert in
that claim (a range such as 44.4–44.6 needs one per story), and the eyebrow date, the estate and verified sections'
``measured:`` and ``footer.date`` are one date, the one ``footer.note`` names. The herald section is held to the code:
its ``chips`` block equals the deck parser's verbs, its prose names every top-level command, and its text names the
two MCP tools ``django_herald_portal/mcp_asgi.py`` serves.

The ``planted`` tests run the same resolver over fixture ledgers and a fixture flag tree, so each rule is shown to red.
"""

from __future__ import annotations

import argparse
import ast
import copy
import functools
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from pyforge.herald import cli

# Story 52.1 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-herald-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

#: The capability ledger's claim field. The Spec gave the resolver one constant, ``claim`` (the word the ledger's
#: header used), until control-plane named the field; spec-foundry-capability-ledger ``modes.md`` § Schema v1 names it
#: ``state`` ("``verified-in-foundry`` is a claim on a rebuild row (a ``state``)"; "herald reads ``state``").
CLAIM_FIELD = "state"

TRUE, FALSE, UNRESOLVABLE = "true", "false", "unresolvable"

_STORY = re.compile(r"story:(?P<station>[a-z]+)/(?P<epic>\d+)-(?P<story>\d+)=(?P<value>[a-z-]+)")
_EPIC = re.compile(r"epic:(?P<station>[a-z]+)/(?P<epic>\d+)=(?P<value>[a-z-]+)")
_FLAG = re.compile(r"flag:(?P<key>pyforge\.cutover_root)=(?P<value>[\w.-]+)")
_MODE = re.compile(r"ledger:mode:(?P<mode>[\w-]+)=(?P<count>\d+)")
_CLAIM = re.compile(r"ledger:claim:(?P<state>[\w-]+)=(?P<count>\d+)")
_CLAIM_FIELD = re.compile(r"ledger:claim-field=(?P<value>absent|present)")
_GRAMMAR = "story:, epic:, flag:pyforge.cutover_root=, ledger:mode:, ledger:claim: or ledger:claim-field="

#: A story number in prose (``44.10``), never a version (``3.14.1``) or a token (``py3.14``).
_STORY_REF = re.compile(r"(?<![\w.])(\d{1,3})\.(\d{1,2})(?!\d|\.\d|\w)")
#: A range of stories (``44.4–44.6``, ``44.4 to 44.6``): every story inside it is named.
_STORY_RANGE = re.compile(r"(?<![\w.])(\d{1,3})\.(\d{1,2})\s*(?:–|—|-|to)\s*(?:(\d{1,3})\.)?(\d{1,2})(?!\d|\.\d|\w)")
_EPIC_REF = re.compile(r"\bEpics?\s+(\d+(?:\s*(?:,|and|or|to|–|-)\s*\d+)*)")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUMBER_WORDS = {3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight"}


# ------------------------------------------------------------------ the tree


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate the repository root")


def _sprint_ledger(root: Path, station: str) -> Path:
    return (
        root / "_bmad-output" / "projects" / f"pyforge-{station}" / "planning-artifacts" / "sprint-status-ledger.yaml"
    )


def _flag_tree(root: Path) -> Path:
    return root / "src" / "platform" / "config" / "flags.json"


def _capability_ledger(root: Path) -> Path:
    return root / "docs" / "foundry" / "capability-ledger.yaml"


def _dossier_file(root: Path) -> Path:
    return root / "docs-site" / "src" / "content" / "dossier" / "dossier.yml"


def _mcp_asgi(root: Path) -> Path:
    return root / "src" / "shared" / "packages" / "django-herald" / "src" / "django_herald_portal" / "mcp_asgi.py"


@functools.cache
def _parsed(path: str, stamp: tuple[int, int]) -> Any:
    """One parse per file version (``stamp`` is its mtime and size): the capability ledger is read by several asserts."""
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text) if path.endswith(".json") else yaml.safe_load(text)


def _load(path: Path) -> Any:
    stat = path.stat()
    return _parsed(str(path), (stat.st_mtime_ns, stat.st_size))


# ------------------------------------------------------------------ the resolver


@dataclass(frozen=True)
class Resolution:
    verdict: str  # TRUE, FALSE or UNRESOLVABLE
    detail: str


def _read(path: Path) -> tuple[Any, str | None]:
    try:
        return _load(path), None
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return None, f"{path.name} cannot be read ({type(exc).__name__})"


def _compare(actual: object, expected: str, what: str) -> Resolution:
    if str(actual) == expected:
        return Resolution(TRUE, f"{what} is {actual}")
    return Resolution(FALSE, f"{what} is {actual}, not {expected}")


def _ledger_statuses(root: Path, station: str) -> tuple[dict[str, Any] | None, str | None]:
    data, error = _read(_sprint_ledger(root, station))
    if error:
        return None, f"no tracked sprint ledger for {station}: {error}"
    statuses = data.get("development_status") if isinstance(data, dict) else None
    if not isinstance(statuses, dict):
        return None, f"the {station} sprint ledger has no development_status mapping"
    return statuses, None


def _resolve_story(match: re.Match[str], root: Path) -> Resolution:
    station, number = match["station"], f"{match['epic']}-{match['story']}"
    statuses, error = _ledger_statuses(root, station)
    if statuses is None:
        return Resolution(UNRESOLVABLE, str(error))
    keys = [key for key in statuses if key == number or str(key).startswith(f"{number}-")]
    if len(keys) != 1:
        return Resolution(UNRESOLVABLE, f"the {station} sprint ledger has {len(keys)} keys for story {number}")
    return _compare(statuses[keys[0]], match["value"], f"{station} story {keys[0]}")


def _resolve_epic(match: re.Match[str], root: Path) -> Resolution:
    station, key = match["station"], f"epic-{match['epic']}"
    statuses, error = _ledger_statuses(root, station)
    if statuses is None:
        return Resolution(UNRESOLVABLE, str(error))
    if key not in statuses:
        return Resolution(UNRESOLVABLE, f"the {station} sprint ledger has no key {key}")
    return _compare(statuses[key], match["value"], f"{station} {key}")


def _resolve_flag(match: re.Match[str], root: Path) -> Resolution:
    data, error = _read(_flag_tree(root))
    if error:
        return Resolution(UNRESOLVABLE, error)
    flags = data.get("flags") if isinstance(data, dict) else None
    flag = flags.get(match["key"]) if isinstance(flags, dict) else None
    if not isinstance(flag, dict):
        return Resolution(UNRESOLVABLE, f"the flag tree has no {match['key']}")
    if flag.get("state") != "ENABLED" or flag.get("targeting"):
        return Resolution(
            UNRESOLVABLE, f"{match['key']} is not an enabled flag without targeting, so its default is not its value"
        )
    variants, default = flag.get("variants"), flag.get("defaultVariant")
    if not isinstance(variants, dict) or default not in variants:
        return Resolution(UNRESOLVABLE, f"{match['key']} names no default variant")
    return _compare(variants[default], match["value"], f"{match['key']}'s default variant")


def _capability_rows(root: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None, str | None]:
    data, error = _read(_capability_ledger(root))
    if error:
        return None, None, error
    rows = data.get("capabilities") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None, None, "the capability ledger has no capabilities list"
    return data, [row for row in rows if isinstance(row, dict)], None


def _resolve_mode(match: re.Match[str], root: Path) -> Resolution:
    _, rows, error = _capability_rows(root)
    if rows is None:
        return Resolution(UNRESOLVABLE, str(error))
    count = sum(1 for row in rows if row.get("mode") == match["mode"])
    return _compare(count, match["count"], f"the count of rows with mode {match['mode']}")


def _resolve_claim(match: re.Match[str], root: Path) -> Resolution:
    data, rows, error = _capability_rows(root)
    if rows is None or data is None:
        return Resolution(UNRESOLVABLE, str(error))
    carriers = [row for row in rows if CLAIM_FIELD in row]
    if not carriers:
        return Resolution(
            UNRESOLVABLE, f"no ledger row carries the claim field `{CLAIM_FIELD}`, so a claim count is unknown, never 0"
        )
    states = data.get("states")
    if isinstance(states, list) and match["state"] not in states:
        return Resolution(UNRESOLVABLE, f"{match['state']} is not one of the ledger's states {states}")
    count = sum(1 for row in carriers if row.get(CLAIM_FIELD) == match["state"])
    return _compare(count, match["count"], f"the count of rows whose `{CLAIM_FIELD}` is {match['state']}")


def _resolve_claim_field(match: re.Match[str], root: Path) -> Resolution:
    _, rows, error = _capability_rows(root)
    if rows is None:
        return Resolution(UNRESOLVABLE, str(error))
    carried = sum(1 for row in rows if CLAIM_FIELD in row)
    actual = "present" if carried else "absent"
    return _compare(actual, match["value"], f"the claim field `{CLAIM_FIELD}` ({carried} rows carry it)")


def resolve(assertion: str, root: Path) -> Resolution:
    """One assert's verdict over the tree at ``root``: true, false or unresolvable."""
    if match := _STORY.fullmatch(assertion):
        return _resolve_story(match, root)
    if match := _EPIC.fullmatch(assertion):
        return _resolve_epic(match, root)
    if match := _FLAG.fullmatch(assertion):
        return _resolve_flag(match, root)
    if match := _MODE.fullmatch(assertion):
        return _resolve_mode(match, root)
    if match := _CLAIM.fullmatch(assertion):
        return _resolve_claim(match, root)
    if match := _CLAIM_FIELD.fullmatch(assertion):
        return _resolve_claim_field(match, root)
    return Resolution(UNRESOLVABLE, f"not in the closed grammar ({_GRAMMAR})")


# ------------------------------------------------------------------ the claims


@dataclass(frozen=True)
class Claim:
    where: str
    text: str
    asserts: tuple[str, ...] | None  # None: no ``asserts:`` at all
    required: bool


def _texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [t for v in value.values() for t in _texts(v)]
    if isinstance(value, list):
        return [t for v in value for t in _texts(v)]
    return []


def _collapse(value: Any) -> str:
    return " ".join(" ".join(_texts(value)).split())


def _section(doc: dict[str, Any], section_id: str) -> dict[str, Any]:
    matches = [s for s in doc.get("sections", []) if s.get("id") == section_id]
    assert len(matches) == 1, f"dossier has {len(matches)} sections with id {section_id!r}"
    return matches[0]


def _asserts(value: Any) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return (f"<asserts: is a {type(value).__name__}, not a list>",)
    return tuple(item if isinstance(item, str) else f"<{item!r} is not a string>" for item in value)


def _operator_watch(doc: dict[str, Any]) -> dict[str, Any] | None:
    blocks = [
        b
        for b in _section(doc, "estate")["blocks"]
        if b.get("type") == "callout" and b.get("label") == "Operator watch"
    ]
    return blocks[0] if len(blocks) == 1 else None


def _claims(doc: dict[str, Any]) -> list[Claim]:
    """Every claim that must carry asserts (A→B.3 rows, Operator watch lines, § 10 rows) and every row that does."""
    claims: list[Claim] = []
    heading = ""
    for block in _section(doc, "estate")["blocks"]:
        if block.get("type") == "h3":
            heading = str(block.get("num", ""))
        elif block.get("type") == "table":
            required = heading == "A→B.3"
            for index, row in enumerate(block.get("rows", []), 1):
                if required or "asserts" in row:
                    where = f"{heading} row {index} ({str(row['cells'][0])!r})"
                    claims.append(Claim(where, _collapse(row["cells"]), _asserts(row.get("asserts")), required))
    watch = _operator_watch(doc)
    if watch is not None:
        listed = watch.get("asserts") or []
        for index, line in enumerate(watch.get("body") or [], 1):
            entry = listed[index - 1] if index - 1 < len(listed) else None
            claims.append(Claim(f"Operator watch line {index}", _collapse(line), _asserts(entry), True))
    for block in _section(doc, "verified")["blocks"]:
        if block.get("type") == "table":
            for index, row in enumerate(block.get("rows", []), 1):
                where = f"§ 10 row {index} ({str(row['cells'][0])[:50]!r})"
                claims.append(Claim(where, _collapse(row["cells"]), _asserts(row.get("asserts")), True))
    return claims


def _unasserted(doc: dict[str, Any]) -> list[str]:
    """Every claim that must carry asserts and does not, and a malformed Operator watch list."""
    claims = _claims(doc)
    problems = [f"{c.where} carries no asserts:" for c in claims if c.required and not c.asserts]
    if not any(c.where.startswith("A→B.3 ") for c in claims):
        problems.append("the estate section has no A→B.3 table rows")
    watch = _operator_watch(doc)
    if watch is None:
        problems.append("the estate section has no single Operator watch callout")
    elif len(watch.get("asserts") or []) > len(watch.get("body") or []):
        problems.append("the Operator watch callout has more asserts lists than body lines")
    if not any(c.where.startswith("§ 10 ") for c in claims):
        problems.append("§ 10 has no claim rows")
    return problems


def _named_stories(text: str) -> set[tuple[int, int]]:
    named = {(int(e), int(s)) for e, s in _STORY_REF.findall(text)}
    for start_epic, start, end_epic, end in _STORY_RANGE.findall(text):
        if not end_epic or end_epic == start_epic:
            named |= {(int(start_epic), n) for n in range(int(start), int(end) + 1)}
    return named


def _named_epics(text: str) -> set[int]:
    return {int(n) for group in _EPIC_REF.findall(text) for n in re.findall(r"\d+", group)}


def _text_problems(claims: list[Claim]) -> list[str]:
    """A story number or ``Epic <n>`` a claim names, with no assert for it in that claim."""
    problems = []
    for claim in claims:
        if not claim.required and claim.asserts is None:
            continue
        asserts = claim.asserts or ()
        stories = {(int(m["epic"]), int(m["story"])) for a in asserts if (m := _STORY.fullmatch(a))}
        epics = {int(m["epic"]) for a in asserts if (m := _EPIC.fullmatch(a))}
        for epic, story in sorted(_named_stories(claim.text) - stories):
            problems.append(f"{claim.where} names {epic}.{story} with no story:<station>/{epic}-{story}= assert")
        for epic in sorted(_named_epics(claim.text) - epics):
            problems.append(f"{claim.where} names Epic {epic} with no epic:<station>/{epic}= assert")
    return problems


def _resolution_problems(claims: list[Claim], root: Path) -> list[str]:
    """Every assert whose verdict is not true, named with its claim, its verdict and why."""
    problems = []
    for claim in claims:
        for assertion in claim.asserts or ():
            resolution = resolve(assertion, root)
            if resolution.verdict != TRUE:
                problems.append(f"{claim.where}: `{assertion}` is {resolution.verdict}: {resolution.detail}")
    return problems


def _date_problems(doc: dict[str, Any]) -> list[str]:
    """The eyebrow date, the estate and verified sections' ``measured:`` and ``footer.date`` are one date."""
    eyebrow = _DATE.findall(str(doc.get("eyebrow", "")))
    footer = doc.get("footer") or {}
    dates = {
        "the eyebrow date": eyebrow[-1] if eyebrow else "(none)",
        "the estate section's measured:": str(_section(doc, "estate").get("measured", "(none)")),
        "the verified section's measured:": str(_section(doc, "verified").get("measured", "(none)")),
        "footer.date": str(footer.get("date", "(none)")),
    }
    problems = []
    if len(set(dates.values())) != 1:
        problems.append("the control-plane dates differ: " + "; ".join(f"{k} {v}" for k, v in dates.items()))
    stray = sorted(set(_DATE.findall(str(footer.get("note", "")))) - {dates["footer.date"]})
    if stray:
        problems.append(f"footer.note names {stray}, not footer.date {dates['footer.date']}")
    return problems


def _dossier() -> dict[str, Any]:
    return yaml.safe_load(_dossier_file(_repo_root()).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ the live dossier


def test_every_control_plane_claim_carries_asserts() -> None:
    assert _unasserted(_dossier()) == []


def test_the_claims_are_not_vacuous() -> None:
    claims = _claims(_dossier())
    assert len([c for c in claims if c.where.startswith("A→B.3 ")]) == 4  # noqa: PLR2004 -- the four campaign verbs
    assert [c for c in claims if c.where.startswith("Operator watch ")]
    assert [c for c in claims if c.where.startswith("§ 10 ")]
    assert sum(len(c.asserts or ()) for c in claims) >= len(claims)


def test_every_story_and_epic_a_claim_names_is_asserted() -> None:
    assert _text_problems(_claims(_dossier())) == []


def test_every_assert_resolves_true_against_the_tree() -> None:
    assert _resolution_problems(_claims(_dossier()), _repo_root()) == []


def test_the_control_plane_dates_are_one_date() -> None:
    assert _date_problems(_dossier()) == []


def _herald(doc: dict[str, Any]) -> dict[str, Any]:
    return _section(doc, "herald")


def _deck_verbs() -> list[str]:
    def subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
        actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]  # noqa: SLF001
        assert len(actions) == 1, parser.prog
        return dict(actions[0].choices)

    return list(subcommands(subcommands(cli._build_parser())["deck"]))  # noqa: SLF001


def _portal_tools(path: Path) -> list[str]:
    """The ``start_tool`` and ``get_tool`` the portal hands ``build_station_mcp_asgi``, through its constants."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    constants = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }
    tools = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "build_station_mcp_asgi":
            for keyword in node.keywords:
                if keyword.arg in ("start_tool", "get_tool") and isinstance(keyword.value, ast.Name):
                    tools.append(constants[keyword.value.id])
    return tools


def test_herald_section_chips_equal_the_deck_parser_verbs() -> None:
    chips = [b["chips"] for b in _herald(_dossier())["blocks"] if b.get("type") == "chips"]
    verbs = _deck_verbs()
    assert len(verbs) >= 12  # noqa: PLR2004 -- the parser held 12 deck verbs when Story 51.2 wrote the section
    assert chips == [verbs]


def test_herald_section_names_the_mcp_tools_the_portal_serves() -> None:
    tools = _portal_tools(_mcp_asgi(_repo_root()))
    assert sorted(tools) == ["get_notice", "start_notice"]
    text = _collapse([b.get("body") for b in _herald(_dossier())["blocks"] if b.get("type") in ("prose", "finding")])
    assert "POST /stations/herald/mcp" in text
    for tool in tools:
        assert f"`{tool}`" in text, tool
    assert "django-herald" in text


def test_herald_section_names_every_top_level_command() -> None:
    prose = _collapse([b.get("body") for b in _herald(_dossier())["blocks"] if b.get("type") == "prose"])
    assert prose.startswith(f"{_NUMBER_WORDS[len(cli.TOP_LEVEL_COMMANDS)]} top-level commands")
    for command in cli.TOP_LEVEL_COMMANDS:
        assert f"`{command}`" in prose, command


# ------------------------------------------------------------------ planted: fixture ledgers and a fixture flag tree

_STEWARD = {
    "44-4-fold-the-packages": "blocked",
    "44-9-mason-submits-to-conda-forge": "blocked",
    "44-10-archive-local-recipes": "blocked",
    "epic-44": "in-progress",
}
_PLANNED = [{"id": "x:CAP-1", "mode": "rebuild", "state": "planned"}, {"id": "x:CAP-2", "mode": "retire"}]
_NO_FIELD = [{"id": "x:CAP-1", "mode": "rebuild"}, {"id": "x:CAP-2", "mode": "retire"}]
_ONE_CLAIM = [{"id": "x:CAP-1", "mode": "rebuild", "state": "verified-in-foundry"}, {"id": "x:CAP-2", "mode": "retire"}]


def _plant(
    tmp_path: Path,
    *,
    steward: dict[str, str] | None = None,
    default: str = "local-recipes",
    capabilities: list[dict[str, str]] | None = None,
) -> Path:
    """A fixture tree: a steward sprint ledger, the flag tree and a capability ledger, nothing else."""
    root = tmp_path / "tree"
    ledger = _sprint_ledger(root, "steward")
    ledger.parent.mkdir(parents=True)
    ledger.write_text(yaml.safe_dump({"development_status": steward or _STEWARD}), encoding="utf-8")
    flags = _flag_tree(root)
    flags.parent.mkdir(parents=True)
    cutover = {
        "state": "ENABLED",
        "variants": {"local-recipes": "local-recipes", "foundry": "foundry"},
        "defaultVariant": default,
    }
    flags.write_text(json.dumps({"flags": {"pyforge.cutover_root": cutover}}), encoding="utf-8")
    capability = _capability_ledger(root)
    capability.parent.mkdir(parents=True)
    document = {
        "states": ["planned", "rebuilding", "verified-in-foundry", "cut"],
        "capabilities": _PLANNED if capabilities is None else capabilities,
    }
    capability.write_text(yaml.safe_dump(document), encoding="utf-8")
    return root


def _claim(text: str, *asserts: str) -> Claim:
    return Claim("planted row", text, asserts, True)


def test_planted_a_false_story_status_is_named_false(tmp_path: Path) -> None:
    root = _plant(tmp_path)
    resolution = resolve("story:steward/44-4=backlog", root)
    assert resolution.verdict == FALSE
    assert "blocked" in resolution.detail
    problems = _resolution_problems([_claim("Story 44.4 is parked.", "story:steward/44-4=backlog")], root)
    assert problems == [f"planted row: `story:steward/44-4=backlog` is false: {resolution.detail}"]


def test_planted_a_story_named_without_an_assert_is_named() -> None:
    claim = _claim("Stories 44.4 and 44.9 stay blocked.", "story:steward/44-4=blocked")
    assert _text_problems([claim]) == ["planted row names 44.9 with no story:<station>/44-9= assert"]


def test_planted_an_a_b_3_row_without_asserts_is_named() -> None:
    doc = copy.deepcopy(_dossier())
    table = next(
        block
        for block in _section(doc, "estate")["blocks"]
        if block.get("type") == "table" and block.get("headers", [None])[0] == "Verb"
    )
    del table["rows"][1]["asserts"]
    assert _unasserted(doc) == ["A→B.3 row 2 ('Adopt Frames') carries no asserts:"]


def test_planted_an_operator_watch_line_without_asserts_is_named() -> None:
    doc = copy.deepcopy(_dossier())
    watch = _operator_watch(doc)
    assert watch is not None
    watch["asserts"] = watch["asserts"][:1]
    lines = len(watch["body"])
    assert _unasserted(doc) == [f"Operator watch line {n} carries no asserts:" for n in range(2, lines + 1)]


def test_planted_flag_foundry_is_named_false(tmp_path: Path) -> None:
    root = _plant(tmp_path)
    resolution = resolve("flag:pyforge.cutover_root=foundry", root)
    assert resolution.verdict == FALSE
    assert "local-recipes" in resolution.detail
    assert resolve("flag:pyforge.cutover_root=foundry", _plant(tmp_path / "flipped", default="foundry")).verdict == TRUE


def test_planted_an_eyebrow_date_unlike_the_estate_measured_is_named() -> None:
    doc = copy.deepcopy(_dossier())
    estate = str(_section(doc, "estate")["measured"])
    doc["eyebrow"] = "INTERNAL CONTROL PLANE — A→B CUTOVER — 2026-01-01"
    problems = _date_problems(doc)
    assert len(problems) == 1
    assert "the eyebrow date 2026-01-01" in problems[0]
    assert f"the estate section's measured: {estate}" in problems[0]


def test_planted_a_zero_claim_count_is_false_when_one_row_claims_verified_in_foundry(tmp_path: Path) -> None:
    root = _plant(tmp_path, capabilities=_ONE_CLAIM)
    resolution = resolve("ledger:claim:verified-in-foundry=0", root)
    assert resolution.verdict == FALSE
    assert "is 1, not 0" in resolution.detail
    assert resolve("ledger:claim:verified-in-foundry=1", root).verdict == TRUE


def test_planted_a_claim_count_over_a_ledger_without_the_claim_field_is_unresolvable(tmp_path: Path) -> None:
    root = _plant(tmp_path, capabilities=_NO_FIELD)
    resolution = resolve("ledger:claim:verified-in-foundry=0", root)
    assert resolution.verdict == UNRESOLVABLE
    assert resolution.verdict != TRUE
    problems = _resolution_problems([_claim("Nothing is in effect on B.", "ledger:claim:verified-in-foundry=0")], root)
    assert len(problems) == 1 and "is unresolvable: no ledger row carries the claim field" in problems[0]


def test_planted_claim_field_absent_is_false_once_a_row_carries_the_field(tmp_path: Path) -> None:
    assert resolve("ledger:claim-field=absent", _plant(tmp_path / "bare", capabilities=_NO_FIELD)).verdict == TRUE
    resolution = resolve("ledger:claim-field=absent", _plant(tmp_path / "carried", capabilities=_PLANNED))
    assert resolution.verdict == FALSE
    assert "is present, not absent" in resolution.detail


def test_planted_a_range_needs_one_assert_per_story() -> None:
    claim = _claim("The file moves 44.4–44.6 retired.", "story:steward/44-4=blocked", "story:steward/44-6=blocked")
    assert _text_problems([claim]) == ["planted row names 44.5 with no story:<station>/44-5= assert"]
    spelled = _claim("Stories 44.4 to 44.6 retired.", "story:steward/44-4=blocked")
    assert len(_text_problems([spelled])) == 2  # noqa: PLR2004 -- 44.5 and 44.6


def test_planted_an_epic_named_without_an_assert_is_named() -> None:
    claim = _claim("Steward Epic 46 wires the suite; Epic 60 is the catalog.", "epic:steward/46=done")
    assert _text_problems([claim]) == ["planted row names Epic 60 with no epic:<station>/60= assert"]
    assert _text_problems([_claim("Its floor is py3.14 and its schema 1.1.0; neither is a story.", "epic:x/1=y")]) == []


def test_planted_an_assert_outside_the_grammar_is_unresolvable(tmp_path: Path) -> None:
    root = _plant(tmp_path)
    for assertion in ("ledger:state:verified-in-foundry=0", "story:steward/44.4=blocked", "flag:pyforge.other=x"):
        resolution = resolve(assertion, root)
        assert resolution.verdict == UNRESOLVABLE, assertion
        assert "not in the closed grammar" in resolution.detail


def test_planted_a_story_or_station_the_ledgers_do_not_hold_is_unresolvable(tmp_path: Path) -> None:
    root = _plant(tmp_path)
    assert resolve("story:steward/44-15=blocked", root).verdict == UNRESOLVABLE
    assert resolve("epic:steward/45=done", root).verdict == UNRESOLVABLE
    assert resolve("story:marshal/1-1=done", root).verdict == UNRESOLVABLE


def test_planted_true_asserts_resolve_true_in_every_kind(tmp_path: Path) -> None:
    root = _plant(tmp_path)
    for assertion in (
        "story:steward/44-4=blocked",
        "story:steward/44-10=blocked",
        "epic:steward/44=in-progress",
        "flag:pyforge.cutover_root=local-recipes",
        "ledger:mode:move=0",
        "ledger:mode:retire=1",
        "ledger:claim:verified-in-foundry=0",
        "ledger:claim-field=present",
    ):
        assert resolve(assertion, root).verdict == TRUE, assertion
    assert resolve("ledger:mode:rebuild=0", root).verdict == FALSE
