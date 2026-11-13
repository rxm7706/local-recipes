"""Story 47.2 (spec-pyforge-atlas:CAP-73, its catalog and gate half; spec-pyforge-atlas:CAP-1, spec-pyforge-atlas:CAP-2;
FR-78): the catalog and gate companions name every dataset and gate the code has.

Two families, each DERIVED here, never declared:

- datasets: every top-level entry of ``conf/base/catalog.yml`` (a ``_``-prefixed key is a YAML anchor, not an entry),
  assigned to a pipeline by the longest-prefix map ``PREFIX_TO_PIPELINE`` of ``tests/unit/catalog/conftest.py``. That
  conftest is read by AST, never imported. ``catalog-contract.md`` names each entry once, as a code token under its
  pipeline's ``### `<pipeline>` `` heading, and its pipeline table states the conftest's ``EXPECTED_PIPELINE_COUNTS``
  and ``EXPECTED_TOTAL``;
- gates: every root ``pixi.toml`` task, in any feature, whose command runs pytest over this package's tests.
  ``gate-contract.md`` has one table row per task (the task in the first cell), naming its feature and every package
  test path its command names, all as code tokens. Every row, and every task the "Tasks that run no pytest" list
  names, is a task its stated feature holds.

Every ``tests/...`` path the four companions cite must exist in the package.

Each family has one negative case (``-k absent``) that adds a synthetic name to the derived set and expects the
comparison to fail. The module reads the Spec folder and the root ``pixi.toml``, so it runs in the live-tree half.
"""

from __future__ import annotations

import ast
import re
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.live_tree

_COMPANIONS_RELATIVE = Path("_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas")
_COMPANIONS = ("catalog-contract.md", "gate-contract.md", "signals.md", "degradation-contract.md")
_CONFTEST_LITERALS = ("PREFIX_TO_PIPELINE", "EXPECTED_PIPELINE_COUNTS", "EXPECTED_TOTAL")
_CODE_TOKEN = re.compile(r"`([^`\n]+)`")
_HEADING = re.compile(r"^(#{1,6}) (.*)$")
_CITED_TEST_PATH = re.compile(r"`(tests/[\w/.-]+)")
_SEPARATOR_CELL = re.compile(r":?-+:?")
_NO_PYTEST_HEADING = "## Tasks that run no pytest"

# One gate as derived from pixi.toml: (task, feature, the package test paths its command names).
Gate = tuple[str, str, tuple[str, ...]]


# --------------------------------------------------------------------------- paths (computed, never at import)


def _member_root() -> Path:
    """The atlas member (``src/shared/packages/pyforge-atlas``): tests/meta/<this file> -> parents[2]."""
    return Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    for candidate in _member_root().parents:
        if (candidate / "pixi.toml").is_file() and (candidate / _COMPANIONS_RELATIVE).is_dir():
            return candidate
    raise AssertionError(f"no repository root above {_member_root()} holds pixi.toml and the atlas Spec folder")


def _companion(name: str) -> str:
    return (_repo_root() / _COMPANIONS_RELATIVE / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- the derived sets


def _catalog_names() -> list[str]:
    raw = yaml.safe_load((_member_root() / "conf" / "base" / "catalog.yml").read_text(encoding="utf-8"))
    return [name for name in raw if not str(name).startswith("_")]


def _conftest_literals() -> dict[str, object]:
    """``PREFIX_TO_PIPELINE``, ``EXPECTED_PIPELINE_COUNTS`` and ``EXPECTED_TOTAL`` from the catalog gate's conftest."""
    source = (_member_root() / "tests" / "unit" / "catalog" / "conftest.py").read_text(encoding="utf-8")
    found: dict[str, object] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id in _CONFTEST_LITERALS:
            found[target.id] = ast.literal_eval(value)
    missing = sorted(set(_CONFTEST_LITERALS) - found.keys())
    assert not missing, f"tests/unit/catalog/conftest.py no longer declares {missing} as literals"
    return found


def _pipeline_for(name: str, prefixes: Mapping[str, str]) -> str | None:
    """The conftest's longest-prefix match (``pipeline_for``), over the map it declares."""
    for prefix in sorted(prefixes, key=len, reverse=True):
        if name == prefix or name.startswith(prefix + "_"):
            return prefixes[prefix]
    return None


def _gate_tasks(manifest: Mapping[str, object]) -> list[Gate]:
    """Every feature task whose command runs pytest over a path under this package's ``tests``."""
    member = _member_root().relative_to(_repo_root()).as_posix()
    test_path = re.compile(re.escape(member) + r"/(tests(?:/[\w.-]+)*)")
    gates: list[Gate] = []
    features = manifest.get("feature") or {}
    assert isinstance(features, Mapping)
    for feature, body in features.items():
        for task, spec in ((body or {}).get("tasks") or {}).items():
            cmd = spec.get("cmd", "") if isinstance(spec, Mapping) else spec
            command = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            paths = tuple(sorted(set(test_path.findall(command))))
            if "pytest" in command and paths:
                gates.append((task, feature, paths))
    return sorted(gates)


def _feature_tasks(manifest: Mapping[str, object]) -> dict[str, set[str]]:
    """Feature name -> the tasks it holds."""
    features = manifest.get("feature") or {}
    assert isinstance(features, Mapping)
    return {feature: set(((body or {}).get("tasks") or {}).keys()) for feature, body in features.items()}


def _manifest() -> dict[str, object]:
    with (_repo_root() / "pixi.toml").open("rb") as handle:
        return tomllib.load(handle)


# --------------------------------------------------------------------------- reading the companions


def _tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Each markdown table as (header cells, body rows of cells); the separator row is dropped."""
    tables: list[tuple[list[str], list[list[str]]]] = []
    current: list[list[str]] | None = None
    for line in text.splitlines():
        if not line.startswith("|"):
            current = None
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if current is None:
            current = []
            tables.append((cells, current))
        elif not all(_SEPARATOR_CELL.fullmatch(cell) for cell in cells):
            current.append(cells)
    return tables


def _section(text: str, heading: str) -> str:
    """The body under ``heading`` up to the next heading of the same or a higher level ('' when absent)."""
    lines = text.splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    for start, line in enumerate(lines):
        if line.strip() == heading:
            body: list[str] = []
            for follow in lines[start + 1 :]:
                match = _HEADING.match(follow)
                if match and len(match.group(1)) <= level:
                    break
                body.append(follow)
            return "\n".join(body)
    return ""


def _listed_by_pipeline(text: str) -> dict[str, list[str]]:
    """Each ``### `<name>` `` heading -> every code token under it, up to the next heading."""
    listed: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            title = match.group(2).strip()
            tokens = _CODE_TOKEN.findall(title)
            current = tokens[0] if match.group(1) == "###" and tokens and title == f"`{tokens[0]}`" else None
            if current is not None:
                listed.setdefault(current, [])
            continue
        if current is not None:
            listed[current].extend(_CODE_TOKEN.findall(line))
    return listed


# --------------------------------------------------------------------------- the comparisons


def _dataset_problems(names: Sequence[str], literals: Mapping[str, object], text: str) -> list[str]:
    prefixes = literals["PREFIX_TO_PIPELINE"]
    counts = literals["EXPECTED_PIPELINE_COUNTS"]
    total = literals["EXPECTED_TOTAL"]
    assert isinstance(prefixes, Mapping) and isinstance(counts, Mapping)
    problems: list[str] = []

    allocation: dict[str | None, list[str]] = {}
    for name in names:
        allocation.setdefault(_pipeline_for(name, prefixes), []).append(name)
    for pipeline, members in sorted(allocation.items(), key=lambda item: str(item[0])):
        if counts.get(pipeline) != len(members):
            problems.append(
                f"the catalog puts {len(members)} entries under {pipeline!r}; the conftest pins {counts.get(pipeline)}"
            )
    if total != len(names):
        problems.append(f"the catalog has {len(names)} entries; the conftest's EXPECTED_TOTAL is {total}")

    listed = _listed_by_pipeline(text)
    known = set(names)
    for pipeline, tokens in sorted(listed.items()):
        if pipeline not in counts:
            problems.append(f"catalog-contract.md lists datasets under `{pipeline}`, which is not a pipeline")
        problems.extend(
            f"`{token}` under `{pipeline}` is not a catalog entry" for token in tokens if token not in known
        )
    for name in names:
        homes = [pipeline for pipeline, tokens in listed.items() for token in tokens if token == name]
        expected = _pipeline_for(name, prefixes)
        if homes != [expected]:
            problems.append(f"`{name}` is listed under {homes or 'no pipeline'}; expected once under `{expected}`")

    stated: dict[str, int] = {}
    stated_total: int | None = None
    for header, rows in _tables(text):
        if "Pipeline" not in header or "Datasets" not in header:
            continue
        for row in rows:
            first, figure = row[header.index("Pipeline")], row[header.index("Datasets")].strip("* ")
            tokens = _CODE_TOKEN.findall(first)
            if not figure.isdigit():
                problems.append(f"pipeline table row {first!r} states {figure!r}, not a count")
            elif first.strip("* ") == "Total":
                stated_total = int(figure)
            elif tokens:
                stated[tokens[0]] = int(figure)
    if stated != dict(counts):
        problems.append(f"the pipeline table states {stated}; the conftest pins {dict(counts)}")
    if stated_total != total:
        problems.append(f"the pipeline table's total is {stated_total}; the conftest pins {total}")
    return problems


def _gate_problems(gates: Sequence[Gate], held: Mapping[str, set[str]], text: str) -> list[str]:
    problems: list[str] = []
    rows: dict[str, list[tuple[str, list[str]]]] = {}
    for header, body in _tables(text):
        if not header or header[0] != "Gate (pixi task)":
            continue
        feature_at = next(i for i, cell in enumerate(header) if cell.startswith("pixi feature"))
        path_at = header.index("Test path")
        for row in body:
            tokens = _CODE_TOKEN.findall(row[0])
            if len(tokens) != 1:
                problems.append(f"gate table row {row[0]!r} does not name exactly one task")
                continue
            features = _CODE_TOKEN.findall(row[feature_at])
            rows.setdefault(tokens[0], []).append((features[0] if features else "", _CODE_TOKEN.findall(row[path_at])))

    for task, feature, paths in gates:
        found = rows.get(task, [])
        if len(found) != 1:
            problems.append(f"gate `{task}` (`{feature}`) has {len(found)} rows in gate-contract.md; expected one")
            continue
        stated_feature, stated_paths = found[0]
        if stated_feature != feature:
            problems.append(f"gate `{task}` is held in `{feature}`; its row says `{stated_feature}`")
        missing = [path for path in paths if path not in stated_paths]
        if missing:
            problems.append(f"gate `{task}` runs {missing}; its row's test path does not name them")

    for task, found in sorted(rows.items()):
        for stated_feature, _paths in found:
            if task not in held.get(stated_feature, set()):
                problems.append(
                    f"gate-contract.md row `{task}` names feature `{stated_feature}`, which holds no such task"
                )

    gate_names = {task for task, _feature, _paths in gates}
    for line in _section(text, _NO_PYTEST_HEADING).splitlines():
        if not line.startswith("- "):
            continue
        tokens = _CODE_TOKEN.findall(line)
        if len(tokens) < 2 or tokens[0] not in held.get(tokens[1], set()):
            problems.append(f"no-pytest entry {line[:60]!r} does not name a task and the feature that holds it")
        elif tokens[0] in gate_names:
            problems.append(f"`{tokens[0]}` runs pytest over the package; it belongs in the gate table")
    return problems


# --------------------------------------------------------------------------- the dataset family


def test_catalog_contract_names_every_dataset_under_its_pipeline() -> None:
    problems = _dataset_problems(_catalog_names(), _conftest_literals(), _companion("catalog-contract.md"))
    assert not problems, "catalog-contract.md has drifted from the catalog:\n" + "\n".join(problems)


def test_a_dataset_absent_from_the_contract_fails() -> None:
    names = [*_catalog_names(), "core_synthetic_dataset_story_47_2"]
    problems = _dataset_problems(names, _conftest_literals(), _companion("catalog-contract.md"))
    assert any("core_synthetic_dataset_story_47_2" in problem for problem in problems), problems


# --------------------------------------------------------------------------- the gate family


def test_gate_contract_has_a_row_for_every_gate_task() -> None:
    manifest = _manifest()
    gates = _gate_tasks(manifest)
    assert gates, "no pixi.toml task runs pytest over the atlas tests; the derivation is broken"
    problems = _gate_problems(gates, _feature_tasks(manifest), _companion("gate-contract.md"))
    assert not problems, "gate-contract.md has drifted from pixi.toml:\n" + "\n".join(problems)


def test_a_gate_task_absent_from_the_contract_fails() -> None:
    manifest = _manifest()
    gates = [*_gate_tasks(manifest), ("atlas-synthetic-gate-story-47-2", "pyforge-atlas", ("tests/unit",))]
    problems = _gate_problems(gates, _feature_tasks(manifest), _companion("gate-contract.md"))
    assert any("atlas-synthetic-gate-story-47-2" in problem for problem in problems), problems


# --------------------------------------------------------------------------- cited test paths


def test_every_test_path_the_companions_cite_exists() -> None:
    missing = [
        (name, cited)
        for name in _COMPANIONS
        for cited in _CITED_TEST_PATH.findall(_companion(name))
        if not (_member_root() / cited).exists()
    ]
    assert not missing, f"the companions cite test paths the package does not have: {missing}"
