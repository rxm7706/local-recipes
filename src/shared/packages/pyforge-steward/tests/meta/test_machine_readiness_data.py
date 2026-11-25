"""Stories 135.1 and 135.2 (spec-pyforge-steward CAP-183): the tracked machine-readiness file is held to the tree.

``docs/governance/machine-readiness.yaml`` is data ``steward init`` trusts, so this module fails, naming the row, when
the file breaks its schema; when a row names an environment ``pixi.toml`` lacks, a realization-register package or a
session finding that does not exist, a ``needs`` id or a profile that is not defined, or a remedy without ``who``;
and when a floor or a list a row carries differs from the tracked file its ``declared_in`` names (the pixi floor, the
kind pin of ``platform-ci.yml``, the crc baseline of the OpenShift how-to, the environments ``platform-ci-local.sh``
asks for, the hook types ``precommit_config_check.py`` requires, the inotify limit of the Nebari how-to, the compose
secret). The ``fires`` tests plant one defect each and prove the checker names it.

It also proves the read-only promise over the real rows: with every probe answered by a fake, every command the
verb launches inside an environment is ``pixi run --as-is``, none installs, signs in or starts anything, and only a
``--deep`` run starts a container. A live-tree test: the repository root is found inside a fixture, never at import.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml

from pyforge.steward import bootstrap, machine, session
from pyforge.steward.machine import MachineDeps

pytestmark = pytest.mark.live_tree

REGISTER = "docs/governance/realization-register.yaml"
PROFILES = ("desktop", "container", "pod", "ocp", "nkp")
DESKTOP_ROWS = (
    "pixi", "git", "gh", "gh-auth", "git-identity", "git-hooks", "locale-utf8", "env-guild", "env-preflight-lanes",
    "env-yaml-sync", "bmad-method", "station-clis", "station-clis-own-env", "warden-doctor", "mason-recipe",
    "token-kit", "scribe-pg", "platform-servers", "playwright-chromium", "manticore-studio", "estate-verified",
)  # fmt: skip
OTHER_ROWS = {
    "container": (
        "engine",
        "engine-daemon",
        "engine-runs-amd64",
        "compose",
        "compose-langflow-secret",
        "env-container-stages",
    ),
    "pod": ("kind", "kubectl-helm", "chart-renders", "cluster-reachable"),
    "ocp": ("crc", "oc", "crc-pull-secret", "crc-running"),
    "nkp": ("nic", "nkp-docker"),
}
#: Words that would make a probe a write: no row's command may carry one as its verb.
WRITE_VERBS = frozenset(
    {
        "install",
        "add",
        "update",
        "upgrade",
        "login",
        "start",
        "stop",
        "create",
        "delete",
        "up",
        "down",
        "init",
        "setup",
        "apply",
        "push",
        "pull",
    }
)


@pytest.fixture(scope="module")
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "scripts" / "bmad-loop-worktree").is_file():
            return ancestor
    pytest.fail("could not locate the repository root from the test file location")


@pytest.fixture(scope="module")
def doc(repo_root: Path) -> dict[str, Any]:
    loaded = yaml.safe_load((repo_root / machine.DATA_REL).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def schema(repo_root: Path) -> dict[str, Any]:
    loaded = json.loads((repo_root / machine.SCHEMA_REL).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _probes(row: dict[str, Any]) -> list[dict[str, Any]]:
    probe = row["probe"]
    return list(probe) if isinstance(probe, list) else [probe]


def _row(doc: dict[str, Any], row_id: str) -> dict[str, Any]:
    return next(row for row in doc["checks"] if row["id"] == row_id)


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def reference_findings(doc: dict[str, Any], root: Path) -> list[str]:
    """Each name a row carries that the tree does not define."""
    findings: list[str] = []
    environments = set(tomllib.loads(_read(root, "pixi.toml"))["environments"])
    register = {str(row["package"]): row for row in yaml.safe_load(_read(root, REGISTER))["rows"]}
    for row in doc["checks"]:
        where = f"check {row['id']}"
        for probe in _probes(row):
            named = [probe["env"]] if probe.get("env") else []
            named += probe.get("names") or [] if probe["kind"] == "environments" else []
            findings += [f"{where}: pixi.toml has no environment {env}" for env in named if env not in environments]
            if probe["kind"] == "register-probe":
                if probe["package"] not in register:
                    findings.append(f"{where}: the realization register has no row {probe['package']}")
                elif register[probe["package"]].get("env") not in environments:
                    findings.append(
                        f"{where}: the register row {probe['package']} names an environment pixi.toml lacks"
                    )
            if probe["kind"] == "session-finding" and probe["name"] not in session.MACHINE_FINDING_NAMES:
                findings.append(f"{where}: session.py has no finding {probe['name']}")
        for key in ("declared_in",):
            if key in row and not (root / row[key]).is_file():
                findings.append(f"{where}: `{key}` names {row[key]}, which is not a file")
        doc_path = row["remedy"].get("doc")
        if doc_path and not (root / doc_path.split("#", 1)[0]).is_file():
            findings.append(f"{where}: the remedy's page {doc_path} does not exist")
        if any("literal" in (probe.get("floor") or {}) for probe in _probes(row)) and "declared_in" not in row:
            findings.append(f"{where}: a literal floor needs `declared_in`")
    return findings


def _floor(row: dict[str, Any]) -> dict[str, Any]:
    return next(probe for probe in _probes(row) if probe["kind"] == "tool").get("floor") or {}


def declared_findings(doc: dict[str, Any], root: Path) -> list[str]:
    """Each floor or list a row carries that differs from the tracked file it is declared in."""
    findings: list[str] = []

    def expect(row_id: str, what: str, found: object, source: object, path: str) -> None:
        if _row(doc, row_id).get("declared_in") != path:
            findings.append(f"check {row_id}: `declared_in` is {path}")
        if found != source:
            findings.append(f"check {row_id}: {what} is {found!r} here and {source!r} in {path}")

    if _floor(_row(doc, "pixi")) != {"pixi-requires": True}:
        findings.append("check pixi: the floor is pixi.toml's requires-pixi, never a literal")
    expect("pixi", "the floor source", "pixi.toml", "pixi.toml", "pixi.toml")

    workflow = ".github/workflows/platform-ci.yml"
    pins = set(re.findall(r"kind\.sigs\.k8s\.io/dl/v(\d+\.\d+\.\d+)/", _read(root, workflow)))
    expect("kind", "the floor", {_floor(_row(doc, "kind")).get("literal")}, pins, workflow)

    how_to = "docs/how-to/ocp-cluster-bringup.md"
    baseline = re.search(r"\*\*Baseline:\*\* CRC \*\*(\d+\.\d+\.\d+)\*\*", _read(root, how_to))
    expect("crc", "the floor", _floor(_row(doc, "crc")).get("literal"), baseline.group(1) if baseline else None, how_to)

    script = "scripts/platform-ci-local.sh"
    ordered = re.search(r"ordered=\(([^)]*)\)", _read(root, script))
    stages = next(probe for probe in _probes(_row(doc, "env-container-stages")) if probe["kind"] == "environments")
    expect(
        "env-container-stages",
        "the environments",
        stages["names"],
        ordered.group(1).split() if ordered else None,
        script,
    )

    hooks = "scripts/precommit_config_check.py"
    required = re.search(r"^REQUIRED_HOOK_TYPES = \{([^}]*)\}", _read(root, hooks), re.MULTILINE)
    types = sorted(re.findall(r'"([a-z-]+)"', required.group(1))) if required else None
    expect("git-hooks", "the hook types", sorted(_probes(_row(doc, "git-hooks"))[0]["types"]), types, hooks)

    nebari = "docs/how-to/host-nebari.md"
    limit = re.search(r"fs\.inotify\.max_user_instances=(\d+)", _read(root, nebari))
    sysctl = next(probe for probe in _probes(_row(doc, "nkp-docker")) if probe["kind"] == "sysctl")
    expect("nkp-docker", "the inotify floor", sysctl["min"], int(limit.group(1)) if limit else None, nebari)

    compose = "src/platform/compose/compose.yml"
    secret = _probes(_row(doc, "compose-langflow-secret"))[0]
    names = set(re.findall(r"\$\{([A-Z_]+):\?", _read(root, compose)))
    expect("compose-langflow-secret", "the variable", secret["var"] in names, True, compose)
    if not (root / secret["file"]).parent.is_dir():
        findings.append(f"check compose-langflow-secret: {secret['file']} is not beside a tracked compose file")
    return findings


# ── the file as it is ───────────────────────────────────────────────────────────────────────────────────────────


def test_the_data_file_holds_to_its_schema(doc: dict[str, Any], schema: dict[str, Any]) -> None:
    assert schema["$id"] == "urn:local-recipes:governance:machine-readiness"
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc), key=lambda error: list(error.path))
    assert not errors, [f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors]


def test_the_loader_accepts_it_and_names_every_profile_and_row(repo_root: Path, doc: dict[str, Any]) -> None:
    assert machine.validate_data(doc) == []
    assert machine.load_data(repo_root) == doc
    assert tuple(doc["profiles"]) == PROFILES
    assert doc["profiles"]["nkp"]["platforms"] == ["linux-64"]
    assert [doc["profiles"][name]["requires"] for name in PROFILES] == [
        [],
        ["desktop"],
        ["container"],
        ["container"],
        ["container"],
    ]
    by_profile: dict[str, list[str]] = {}
    for row in doc["checks"]:
        by_profile.setdefault(row["profile"], []).append(row["id"])
    assert tuple(by_profile["desktop"]) == DESKTOP_ROWS
    assert {name: tuple(rows) for name, rows in by_profile.items() if name != "desktop"} == OTHER_ROWS


def test_every_name_a_row_carries_exists_in_the_tree(doc: dict[str, Any], repo_root: Path) -> None:
    assert reference_findings(doc, repo_root) == []


def test_every_floor_and_list_matches_the_file_it_is_declared_in(doc: dict[str, Any], repo_root: Path) -> None:
    assert declared_findings(doc, repo_root) == []


def test_every_remedy_says_who_and_an_installer_or_a_sign_in_is_the_operators(doc: dict[str, Any]) -> None:
    for row in doc["checks"]:
        remedy = row["remedy"]
        assert remedy["who"] in ("agent", "operator"), row["id"]
        command = remedy["command"]
        if re.search(
            r"\b(curl|brew|sudo|login|crc setup|crc start|kind create|global install|git config --global)\b", command
        ):
            assert remedy["who"] == "operator", f"check {row['id']}: `{command}` is the operator's"
    assert _row(doc, "git-hooks")["remedy"]["where"] == "primary-checkout", (
        "hooks are never installed from a linked worktree"
    )


def test_the_schema_and_the_loader_refuse_the_same_documents(doc: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = jsonschema.Draft202012Validator(schema)

    def broken(change: Any) -> dict[str, Any]:
        planted = copy.deepcopy(doc)
        change(planted)
        return planted

    cases = {
        "an unknown top-level key": lambda d: d.update(extra=1),
        "a second version": lambda d: d.update(version=2),
        "a remedy without who": lambda d: d["checks"][0]["remedy"].pop("who"),
        "a remedy without a command": lambda d: d["checks"][0]["remedy"].pop("command"),
        "an unknown class": lambda d: d["checks"][0].update({"class": "hardware"}),
        "an unknown severity": lambda d: d["checks"][0].update(severity="sometimes"),
        "an unknown probe kind": lambda d: d["checks"][0].update(probe={"kind": "telepathy"}),
        "a probe with a foreign key": lambda d: d["checks"][0]["probe"].update(argv=["x"]),
        "an unknown row key": lambda d: d["checks"][0].update(colour="red"),
        "an unknown platform": lambda d: d["profiles"]["nkp"].update(platforms=["amiga"]),
        "an id that is not kebab-case": lambda d: d["checks"][0].update(id="Pixi Check"),
        "an unknown session finding": lambda d: _row(d, "gh-auth").update(
            probe={"kind": "session-finding", "name": "mood"}
        ),
        "a floor that is not a version": lambda d: _row(d, "kind")["probe"].update(floor={"literal": "new"}),
        "an empty needs": lambda d: _row(d, "gh-auth").update(needs=[]),
        "a miss_note without a stdout_match": lambda d: _row(d, "mason-recipe")["probe"].pop("stdout_match"),
        "a version_argv beside any_of": lambda d: _row(d, "engine")["probe"].update(version_argv=["docker", "-v"]),
        "a list as a needs item": lambda d: _row(d, "gh-auth").update(needs=[["gh"]]),
        "a mapping as a needs item": lambda d: _row(d, "gh-auth").update(needs=[{"gh": 1}]),
        "a list as a requires item": lambda d: d["profiles"]["container"].update(requires=[["desktop"]]),
        "a mapping as a requires item": lambda d: d["profiles"]["container"].update(requires=[{"desktop": 1}]),
        "a list as a row's profile": lambda d: d["checks"][0].update(profile=["desktop"]),
        "a mapping as a row's profile": lambda d: d["checks"][0].update(profile={"desktop": 1}),
        "a list as a probe's kind": lambda d: _row(d, "gh-auth")["probe"].update(kind=["session-finding"]),
        "a mapping as a probe's kind": lambda d: _row(d, "gh-auth")["probe"].update(kind={"tool": 1}),
    }
    for name, change in cases.items():
        planted = broken(change)
        assert machine.validate_data(planted), f"the loader accepts {name}"
        assert list(validator.iter_errors(planted)), f"the schema accepts {name}"


#: Schema keywords that only route to other keywords: they hold no rule of their own.
_ROUTING = frozenset(
    {"$schema", "$id", "title", "description", "properties", "items", "$ref", "$defs", "propertyNames"}
)
#: A value of the wrong type for each JSON type a schema node may ask for.
_WRONG_TYPE: dict[str, object] = {"object": "x", "array": "x", "string": 12, "integer": "1", "number": "1"}
_NO_MATCH = "Not A Match!"
_UNKNOWN_KEY = "zz-unknown"


def schema_rules(schema: dict[str, Any]) -> list[str]:
    """Every rule the schema states, as ``<node path>:<keyword>`` (``oneOf`` is routing: its branches hold the rules)."""
    rules: list[str] = []

    def walk(node: object, path: str) -> None:
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key in ("$defs", "properties"):
                for name, sub in value.items():
                    walk(sub, f"{path}/{key}/{name}")
            elif key in ("items", "propertyNames"):
                walk(value, f"{path}/{key}")
            elif key == "oneOf":
                for index, sub in enumerate(value):
                    walk(sub, f"{path}/oneOf/{index}")
            elif key == "additionalProperties" and isinstance(value, dict):
                walk(value, f"{path}/additionalProperties")
            elif key not in _ROUTING:
                rules.append(f"{path}:{key}")

    walk(schema, "#")
    return rules


def schema_sites(schema: dict[str, Any], doc: object) -> dict[str, list[tuple[tuple[Any, ...], bool]]]:
    """Each schema node's instances in ``doc``: the path to the value, and whether the value is a mapping's KEY."""
    sites: dict[str, list[tuple[tuple[Any, ...], bool]]] = {}

    def matches(branch: dict[str, Any], value: object) -> bool:
        return jsonschema.Draft202012Validator({**branch, "$defs": schema["$defs"]}).is_valid(value)

    def visit(node: dict[str, Any], path: str, value: object, where: tuple[Any, ...], is_key: bool) -> None:
        if "$ref" in node:
            target = str(node["$ref"]).removeprefix("#/$defs/")
            visit(schema["$defs"][target], f"#/$defs/{target}", value, where, is_key)
            return
        sites.setdefault(path, []).append((where, is_key))
        if is_key:
            return
        properties = node.get("properties") or {}
        if isinstance(value, dict):
            for name, sub in properties.items():
                if name in value:
                    visit(sub, f"{path}/properties/{name}", value[name], (*where, name), False)
            extra = node.get("additionalProperties")
            if isinstance(extra, dict):
                for name in value:
                    if name not in properties:
                        visit(extra, f"{path}/additionalProperties", value[name], (*where, name), False)
            if isinstance(node.get("propertyNames"), dict):
                for name in value:
                    visit(node["propertyNames"], f"{path}/propertyNames", name, (*where, name), True)
        if isinstance(value, list) and isinstance(node.get("items"), dict):
            for index, item in enumerate(value):
                visit(node["items"], f"{path}/items", item, (*where, index), False)
        for index, branch in enumerate(node.get("oneOf") or []):
            if matches(branch, value):
                visit(branch, f"{path}/oneOf/{index}", value, where, is_key)

    visit(schema, "#", doc, (), False)
    return sites


def _schema_node(schema: dict[str, Any], path: str) -> dict[str, Any]:
    node: Any = schema
    for part in path.removeprefix("#").strip("/").split("/"):
        if part:
            node = node[int(part)] if isinstance(node, list) else node[part]
    assert isinstance(node, dict)
    return node


def violations(node: dict[str, Any], keyword: str, value: object) -> list[tuple[str, object]]:
    """Values that break exactly ``keyword`` of ``node`` where ``value`` stood, each with a description."""
    rule = node[keyword]
    if keyword == "type":
        return [(f"a {type(_WRONG_TYPE[rule]).__name__} where a {rule} goes", _WRONG_TYPE[rule])]
    if keyword in ("const", "enum"):
        return [("a value outside the allowed ones", 2 if rule == 1 else (not rule if rule is True else "zz-other"))]
    if keyword == "pattern":
        return [(f"{_NO_MATCH!r} (outside /{rule}/)", _NO_MATCH)]
    if keyword == "minLength":
        return [("an empty string", "")]
    if keyword == "minItems":
        return [("an empty list", [])]
    if keyword == "minProperties":
        return [("an empty mapping", {})]
    if keyword == "uniqueItems" and isinstance(value, list) and value:
        return [("a list with an item twice", [*value, value[0]])]
    if keyword == "minimum":
        return [(f"{rule - 1}, below the minimum {rule}", rule - 1)]
    if keyword == "exclusiveMinimum":
        return [(f"{rule}, not above {rule}", rule)]
    if keyword == "additionalProperties" and rule is False and isinstance(value, dict):
        return [(f"the unknown key `{_UNKNOWN_KEY}`", {**value, _UNKNOWN_KEY: "x"})]
    if keyword == "required" and isinstance(value, dict):
        return [
            (f"no `{name}`", {key: item for key, item in value.items() if key != name})
            for name in rule
            if name in value
        ]
    if keyword == "dependentRequired" and isinstance(value, dict):
        return [
            (f"`{name}` without `{need}`", {key: item for key, item in value.items() if key != need})
            for name, needs in rule.items()
            if name in value
            for need in needs
            if need in value
        ]
    return []


def _set(doc: Any, where: tuple[Any, ...], value: object, *, is_key: bool) -> None:
    parent = doc
    for step in where[:-1]:
        parent = parent[step]
    if is_key:
        parent[value] = parent.pop(where[-1])
    else:
        parent[where[-1]] = value


#: Valid values the tracked file happens not to use, planted so that every schema rule has an instance to break.
def _with_every_optional_key(doc: dict[str, Any]) -> dict[str, Any]:
    planted = copy.deepcopy(doc)
    _row(planted, "compose-langflow-secret")["probe"]["key"] = "LANGFLOW_SUPERUSER_PASSWORD"
    _row(planted, "gh")["probe"]["found_note"] = "gh answers"
    _row(planted, "station-clis")["probe"][0]["expect_exit"] = 0
    return planted


def loader_gaps(schema: dict[str, Any], doc: dict[str, Any]) -> list[str]:
    """Each schema rule the loader does not hold: no instance to break, or a broken instance the loader accepts."""
    validator = jsonschema.Draft202012Validator(schema)
    base = _with_every_optional_key(doc)
    assert not list(validator.iter_errors(base)), "the planted optional keys break the schema"
    sites = schema_sites(schema, base)
    gaps: list[str] = []
    for rule in schema_rules(schema):
        path, keyword = rule.rsplit(":", 1)
        node = _schema_node(schema, path)
        broke = False
        for where, is_key in sites.get(path, []):
            current: Any = base
            for step in where:
                current = current[step]
            for described, bad in violations(node, keyword, where[-1] if is_key else current):
                holder = {"doc": copy.deepcopy(base)}
                _set(holder, ("doc", *where), bad, is_key=is_key)
                planted = holder["doc"]
                if not list(validator.iter_errors(planted)):
                    continue
                broke = True
                if not machine.validate_data(planted):
                    shown = "/".join(map(str, where)) or "the document"
                    gaps.append(f"{rule}: the loader accepts {described} at {shown}, which the schema refuses")
                break
            if broke:
                break
        if not broke:
            gaps.append(f"{rule}: no instance in the data file to break (plant one in _with_every_optional_key)")
    return gaps


def test_the_loader_refuses_everything_the_schema_refuses_rule_by_rule(
    doc: dict[str, Any], schema: dict[str, Any]
) -> None:
    """Each rule the schema states is broken once, in the real file, and the loader must refuse the result.

    A rule added to the schema and not to ``machine.validate_data`` fails here by its schema path; a schema-invalid file
    the loader accepted would be judged instead of refused with exit 3.
    """
    assert loader_gaps(schema, doc) == []


def test_fires_on_a_schema_rule_the_loader_lacks(doc: dict[str, Any], schema: dict[str, Any]) -> None:
    widened = copy.deepcopy(schema)
    widened["$defs"]["check"]["properties"]["what"]["maxLength"] = 1000
    widened["$defs"]["check"]["properties"]["what"]["pattern"] = "^[^!]*$"
    gaps = loader_gaps(widened, doc)
    assert any(gap.startswith("#/$defs/check/properties/what:pattern: the loader accepts") for gap in gaps), gaps
    assert any(gap.startswith("#/$defs/check/properties/what:maxLength: no instance") for gap in gaps), gaps


def test_a_schema_invalid_data_file_exits_3(tmp_path: Path, repo_root: Path, doc: dict[str, Any]) -> None:
    planted, row = _planted(doc, "gh-auth")
    row["needs"] = ["gh", "gh"]
    (tmp_path / "docs" / "governance").mkdir(parents=True)
    (tmp_path / machine.DATA_REL).write_text(yaml.safe_dump(planted, sort_keys=False), encoding="utf-8")
    result = machine.run_init(_ns(json=False, profile=None, repo=str(tmp_path)))
    assert (result.ok, result.details["exit_code"]) == (False, 3)
    assert "check gh-auth: `needs` names 'gh' twice" in result.summary


def pixi_need_findings(doc: dict[str, Any]) -> list[str]:
    """Each row that runs through pixi (an ``env``, a register probe, an environment list) whose needs never reach pixi.

    Without that need a machine with no pixi FAILs such a row with an agent remedy that cannot run, where it should be
    BLOCKED behind the one operator step that installs pixi.
    """
    by_id = {row["id"]: row for row in doc["checks"]}

    def closure(row_id: str) -> set[str]:
        reached: set[str] = set()
        frontier = list(by_id[row_id].get("needs") or [])
        while frontier:
            need = frontier.pop()
            if need not in reached:
                reached.add(need)
                frontier += by_id[need].get("needs") or []
        return reached

    findings: list[str] = []
    for row in doc["checks"]:
        through_pixi = [
            probe["kind"]
            for probe in _probes(row)
            if probe.get("env") or probe["kind"] in ("register-probe", "environments")
        ]
        if row["id"] != "pixi" and through_pixi and "pixi" not in closure(row["id"]):
            findings.append(
                f"check {row['id']}: a {through_pixi[0]} probe runs through pixi, and its needs never reach pixi"
            )
    return findings


def test_every_row_that_runs_through_pixi_needs_pixi(doc: dict[str, Any]) -> None:
    assert pixi_need_findings(doc) == []


def test_fires_on_a_row_that_runs_through_pixi_without_needing_it(doc: dict[str, Any]) -> None:
    planted, row = _planted(doc, "scribe-pg")
    row.pop("needs", None)
    assert pixi_need_findings(planted) == [
        "check scribe-pg: a command probe runs through pixi, and its needs never reach pixi"
    ]
    planted, row = _planted(doc, "chart-renders")
    _row(planted, "kubectl-helm").pop("needs", None)
    assert (
        "check chart-renders: a command probe runs through pixi, and its needs never reach pixi"
        in pixi_need_findings(planted)
    )


def test_the_two_session_finding_lists_are_one(schema: dict[str, Any]) -> None:
    assert machine.SESSION_FINDINGS == session.MACHINE_FINDING_NAMES
    kinds = [branch["properties"]["kind"]["const"] for branch in schema["$defs"]["probe"]["oneOf"]]
    assert set(kinds) == set(machine.PROBE_KINDS), "the schema and machine.py name the same closed set of probe kinds"
    finding = next(
        b for b in schema["$defs"]["probe"]["oneOf"] if b["properties"]["kind"]["const"] == "session-finding"
    )
    assert tuple(finding["properties"]["name"]["enum"]) == machine.SESSION_FINDINGS
    assert tuple(schema["$defs"]["platform"]["enum"]) == machine.PLATFORMS


def test_the_bootstrap_fallback_is_the_desktop_software_rows(repo_root: Path) -> None:
    assert machine.desktop_software_tools(repo_root) == bootstrap._PREREQ_ORDER == ("pixi", "git", "gh")
    assert bootstrap.prereq_names(repo_root) == ("pixi", "git", "gh")


def test_validate_fast_and_initrepo_print_the_remedy_init_prints(repo_root: Path, doc: dict[str, Any]) -> None:
    """One source of remedies: each prerequisite's remedy is its desktop row's command, never a second copy."""
    remedies = bootstrap.prereq_remedies(repo_root)
    for name in ("pixi", "git", "gh"):
        assert remedies[name]["missing"] == f"install-{name}: {_row(doc, name)['remedy']['command']}", name
    assert remedies["pixi"]["below-floor"] == f"upgrade-pixi: {_row(doc, 'pixi')['remedy']['note']}"


# ── it fires ────────────────────────────────────────────────────────────────────────────────────────────────────


def _planted(doc: dict[str, Any], row_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    planted = copy.deepcopy(doc)
    return planted, _row(planted, row_id)


def test_fires_on_an_environment_pixi_toml_lacks(doc: dict[str, Any], repo_root: Path) -> None:
    planted, row = _planted(doc, "env-guild")
    row["probe"]["names"] = ["pyforge-gild"]
    assert "check env-guild: pixi.toml has no environment pyforge-gild" in reference_findings(planted, repo_root)
    planted, row = _planted(doc, "scribe-pg")
    row["probe"]["env"] = "pyforge-scribe-postgres"
    assert "check scribe-pg: pixi.toml has no environment pyforge-scribe-postgres" in reference_findings(
        planted, repo_root
    )


def test_fires_on_a_register_package_and_a_session_finding_that_do_not_exist(
    doc: dict[str, Any], repo_root: Path
) -> None:
    planted, row = _planted(doc, "playwright-chromium")
    row["probe"]["package"] = "playwrong"
    assert "check playwright-chromium: the realization register has no row playwrong" in reference_findings(
        planted, repo_root
    )
    planted, row = _planted(doc, "gh-auth")
    row["probe"]["name"] = "tier3-feed"
    assert "check gh-auth: session.py has no finding tier3-feed" in reference_findings(planted, repo_root)
    assert any("unknown session finding 'tier3-feed'" in problem for problem in machine.validate_data(planted))


def test_fires_on_an_undefined_need_an_undefined_profile_and_a_remedy_without_who(doc: dict[str, Any]) -> None:
    planted, row = _planted(doc, "gh-auth")
    row["needs"] = ["github-cli"]
    assert "check gh-auth: needs 'github-cli', which is not an earlier check" in machine.validate_data(planted)
    planted, row = _planted(doc, "kind")
    row["profile"] = "pods"
    assert "check kind: names the undefined profile 'pods'" in machine.validate_data(planted)
    planted, row = _planted(doc, "engine")
    del row["remedy"]["who"]
    assert "check engine: remedy lacks `who` (agent or operator)" in machine.validate_data(planted)


def test_fires_on_a_missing_page_and_a_literal_floor_without_its_source(doc: dict[str, Any], repo_root: Path) -> None:
    planted, row = _planted(doc, "crc")
    row["remedy"]["doc"] = "docs/how-to/no-such-page.md"
    del row["declared_in"]
    findings = reference_findings(planted, repo_root)
    assert "check crc: the remedy's page docs/how-to/no-such-page.md does not exist" in findings
    assert "check crc: a literal floor needs `declared_in`" in findings
    planted, row = _planted(doc, "kind")
    row["declared_in"] = ".github/workflows/no-such.yml"
    assert "check kind: `declared_in` names .github/workflows/no-such.yml, which is not a file" in reference_findings(
        planted, repo_root
    )


@pytest.mark.parametrize(
    ("row_id", "change", "expected"),
    [
        (
            "kind",
            lambda row: row["probe"].update(floor={"literal": "0.31.0"}),
            "check kind: the floor is {'0.31.0'} here",
        ),
        (
            "crc",
            lambda row: row["probe"].update(floor={"literal": "2.62.0"}),
            "check crc: the floor is '2.62.0' here and '2.63.0' in",
        ),
        (
            "pixi",
            lambda row: row["probe"].update(floor={"literal": "0.80.0"}),
            "check pixi: the floor is pixi.toml's requires-pixi",
        ),
        (
            "env-container-stages",
            lambda row: row["probe"].update(names=["platform-dev"]),
            "check env-container-stages: the environments is ['platform-dev'] here",
        ),
        (
            "git-hooks",
            lambda row: row["probe"].update(types=["commit-msg"]),
            "check git-hooks: the hook types is ['commit-msg'] here",
        ),
        (
            "nkp-docker",
            lambda row: row["probe"][1].update(min=512),
            "check nkp-docker: the inotify floor is 512 here and 1024 in",
        ),
        (
            "compose-langflow-secret",
            lambda row: row["probe"].update(var="LANGFLOW_PASSWORD"),
            "check compose-langflow-secret: the variable is False here",
        ),
        (
            "kind",
            lambda row: row.update(declared_in="pixi.toml"),
            "check kind: `declared_in` is .github/workflows/platform-ci.yml",
        ),
    ],
)
def test_fires_when_a_floor_or_a_list_leaves_its_source(
    doc: dict[str, Any], repo_root: Path, row_id: str, change: Any, expected: str
) -> None:
    planted, row = _planted(doc, row_id)
    change(row)
    assert any(finding.startswith(expected) for finding in declared_findings(planted, repo_root)), declared_findings(
        planted, repo_root
    )


# ── the read-only promise, over the real rows ───────────────────────────────────────────────────────────────────


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
        words = [Path(argv[0]).name, *argv[1:]]
        self.calls.append(words)
        out = (
            "tool version 99.0.0\n[scribe-pg] listening on 127.0.0.1:5433\nRunning\n1024\n"
            '"cfe_import_floor_satisfied": true\n'
            "linux-64: lock_sha=0 verdict=confirmed\nosx-arm64: lock_sha=0 verdict=confirmed\n"
        )
        if words[:2] == ["git", "rev-parse"]:
            out = str(cwd / ".git") + "\n"
        if words[0] == "sysctl":
            out = "1024\n"
        return subprocess.CompletedProcess(list(argv), 0, stdout=out, stderr="")


def _everything_present(
    tmp_path: Path, repo_root: Path, doc: dict[str, Any], platform: str
) -> tuple[MachineDeps, _Recorder]:
    """A checkout holding the real data file where every tool, environment, hook and file a row asks for exists."""
    (tmp_path / "docs" / "governance").mkdir(parents=True)
    (tmp_path / machine.DATA_REL).write_text(_read(repo_root, machine.DATA_REL.as_posix()), encoding="utf-8")
    environments = sorted(tomllib.loads(_read(repo_root, "pixi.toml"))["environments"])
    lock = {
        "version": 7,
        "platforms": [{"name": platform}],
        "environments": {env: {"packages": {platform: []}} for env in environments},
    }
    (tmp_path / "pixi.lock").write_text(yaml.safe_dump(lock), encoding="utf-8")
    for env in environments:
        marker = tmp_path / ".pixi" / "envs" / env / "conda-meta" / "pixi"
        marker.parent.mkdir(parents=True)
        marker.write_text("{}", encoding="utf-8")
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)
    for kind in ("commit-msg", "pre-push"):
        (hooks / kind).write_text("#!/bin/sh\n", encoding="utf-8")
    pull = tmp_path / "home" / ".config" / "openshift" / "pull-secret.json"
    pull.parent.mkdir(parents=True)
    pull.write_text("{}", encoding="utf-8")
    register = {str(row["package"]): row for row in yaml.safe_load(_read(repo_root, REGISTER))["rows"]}
    recorder = _Recorder()
    deps = MachineDeps(
        root=tmp_path,
        runner=recorder,
        which=lambda name: f"/bin/{name}",
        platform=platform,
        environ={"LANG": "en_US.UTF-8", "LANGFLOW_SUPERUSER_PASSWORD": "set"},
        home=tmp_path / "home",
        session_findings=lambda _root, names: {name: (True, f"{name} ok") for name in names},
        register_row=lambda _root, package: register.get(package),
        register_probe=lambda *_args: "live",
        env_sync=lambda _root: (True, "in sync"),
        lane_environments=lambda _root: {"pyforge-guild": ["lint-types"]},
        pixi_floor=lambda _root: "0.80.0",
    )
    return deps, recorder


def _ns(**kwargs: Any) -> argparse.Namespace:
    base: dict[str, Any] = {
        "json": True,
        "profile": ["all"],
        "check_class": None,
        "deep": False,
        "list": False,
        "repo": None,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_every_profile_is_ready_on_a_linux_64_machine_that_has_everything(
    tmp_path: Path, repo_root: Path, doc: dict[str, Any]
) -> None:
    deps, _recorder = _everything_present(tmp_path, repo_root, doc, "linux-64")
    result = machine.run_init(_ns(deep=True), deps=deps)
    payload = json.loads(result.summary)
    assert result.ok, [
        (check["id"], check["status"], check["detail"]) for check in payload["checks"] if check["status"] != "ok"
    ]
    assert [(profile["id"], profile["ready"]) for profile in payload["profiles"]] == [(name, True) for name in PROFILES]
    assert {check["status"] for check in payload["checks"]} == {"ok"}
    engine = next(check for check in payload["checks"] if check["id"] == "engine")
    assert (
        "pass `--engine docker` to scripts/platform-ci-local.sh, or set PLATFORM_CI_LOCAL_ENGINE=docker"
        in engine["detail"]
    )


def test_off_linux_64_nkp_is_unsupported_and_the_rest_is_judged(
    tmp_path: Path, repo_root: Path, doc: dict[str, Any]
) -> None:
    deps, _recorder = _everything_present(tmp_path, repo_root, doc, "osx-arm64")
    result = machine.run_init(_ns(), deps=deps)
    payload = json.loads(result.summary)
    verdicts = {profile["id"]: profile for profile in payload["profiles"]}
    assert result.ok is False
    assert [verdicts[name]["ready"] for name in PROFILES] == [True, True, True, True, False]
    assert (verdicts["nkp"]["supported"], verdicts["nkp"]["counts"]["na"]) == (False, 2)
    assert verdicts["nkp"]["reason"].startswith("unsupported here: the nkp profile needs linux-64")
    skipped = {check["id"] for check in payload["checks"] if check["status"] == "skipped"}
    assert skipped == {"engine-runs-amd64", "cluster-reachable", "crc-running"}, "the deep rows, and nothing else"


def test_no_row_installs_signs_in_or_starts_anything_and_only_deep_runs_a_container(
    tmp_path: Path, repo_root: Path, doc: dict[str, Any]
) -> None:
    deps, recorder = _everything_present(tmp_path, repo_root, doc, "linux-64")
    machine.run_init(_ns(), deps=deps)
    shallow = list(recorder.calls)
    recorder.calls.clear()
    machine.run_init(_ns(deep=True), deps=deps)
    deep = list(recorder.calls)

    def verb(call: list[str]) -> list[str]:
        """The words of the command itself, after pixi's own `run --as-is -x -e <env>`."""
        return call[6:] if call[:2] == ["pixi", "run"] else call

    for call in deep:
        if call[0] == "pixi" and call != ["pixi", "--version"]:
            assert call[:5] == ["pixi", "run", "--as-is", "-x", "-e"], (
                f"an in-environment probe that is not --as-is: {call}"
            )
        words = verb(call)
        if words[:2] in (["docker", "run"], ["podman", "run"]):
            assert "--rm" in words and call not in shallow, (
                f"a container starts only with --deep, and is removed: {call}"
            )
            continue
        if words[0] == "pyforge" and "deploy" in words:
            assert words[-3:-2] == ["validate"], f"`deploy nic` is only ever validated: {call}"
            continue
        assert not WRITE_VERBS & set(words[1:3]), f"a probe that writes: {call}"
    assert [call for call in deep if call not in shallow] == [
        ["docker", "run", "--rm", "--platform", "linux/amd64", "busybox", "true"],
        ["pixi", "run", "--as-is", "-x", "-e", "platform-dev", "kubectl", "cluster-info"],
        ["crc", "status"],
        ["oc", "whoami"],
    ]


def test_the_listing_names_all_five_profiles_and_probes_nothing(repo_root: Path) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("--list reached a probe")

    deps = MachineDeps(root=repo_root, runner=refuse, which=refuse)
    result = machine.run_init(_ns(json=False, profile=None, list=True), deps=deps)
    assert result.ok
    for name in PROFILES:
        assert f"\n{name} - " in result.summary
    assert "nkp - `steward deploy nic` on kind (requires container; only on linux-64)" in result.summary
