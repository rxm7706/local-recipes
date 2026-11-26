"""``steward init`` -- whether this machine can do a kind of work (Epic 135, spec-pyforge-steward CAP-183).

The checks are rows of ``docs/governance/machine-readiness.yaml`` (held to ``machine-readiness.schema.json``), grouped
into profiles: ``desktop``, ``container``, ``pod``, ``ocp`` and ``nkp``, each including the profiles it requires. This
module loads that file, runs each chosen row's probe and reports one verdict per profile. A requirement is a data
row; the only code here is the closed set of probe KINDS, each written once:

``tool``, ``command``, ``environments``, ``session-finding``, ``register-probe``, ``env-sync``, ``git-config``,
``git-hooks``, ``locale-utf8``, ``env-or-file``, ``file`` and ``sysctl``.

Where another duty already measures something it is composed, never written again: ``session.py``'s findings,
``provision.check_environment_sync``, the realization register's probes (``estate_realize.run_probe``) and the
preflight's lane graph. Another station's verdict is read from its command's exit code, never by import
(spec-pyforge-steward CAP-182).

The verb is read-only. A probe inside a pixi environment runs ``pixi run --as-is`` (no install, no lock write) and
only when that environment is already materialized; a row marked ``cost: deep`` (start a container, ask a cluster)
runs only with ``--deep``. A value a row checks (a variable, a file key, a file, a git identity) is reported by
presence and never read out. A probe that cannot launch is a failed row, never a crash.

``machine.py`` is a peer of ``bootstrap.py`` and ``session.py`` and has their injected seam (``MachineDeps``); the
duty itself stays ``bootstrap.InitDuty`` and returns a ``DutyResult`` (AD-8: a duty never calls ``sys.exit``).
"""

from __future__ import annotations

import argparse
import json
import os
import platform as _platform
import re
import shutil
import subprocess
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError

from .bootstrap import _first_version, _version_gte, pixi_floor_version, repo_root
from .interfaces import DutyResult

DATA_REL = Path("docs/governance/machine-readiness.yaml")
SCHEMA_REL = Path("docs/governance/machine-readiness.schema.json")

#: The data file is missing or breaks its schema: the verb cannot judge (contract.md, Exit codes).
EXIT_CANNOT_JUDGE = 3
#: A profile the data file does not define: steward's usage code, no new one.
EXIT_UNKNOWN_PROFILE = 2

DEFAULT_PROFILE = "desktop"
ALL_PROFILES = "all"
CLASSES: tuple[str, ...] = ("software", "configuration", "environment", "usable")
SEVERITIES: tuple[str, ...] = ("required", "advisory")
COSTS: tuple[str, ...] = ("cheap", "deep")
PLATFORMS: tuple[str, ...] = ("linux-64", "linux-aarch64", "osx-64", "osx-arm64", "win-64")
WHO: tuple[str, ...] = ("agent", "operator")
WHERE: tuple[str, ...] = ("any", "primary-checkout")
SESSION_FINDINGS: tuple[str, ...] = ("gh-auth", "bmad-method", "token-kit", "codegraph-index")

OK, FAIL, BLOCKED, SKIPPED, NA = "ok", "fail", "blocked", "skipped", "na"
#: A required row in one of these states does not hold a profile back.
_NOT_BLOCKING = frozenset({OK, SKIPPED, NA})

_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
#: The schema's patterns for an environment variable (``env-or-file``), a kernel setting and a remedy's page.
_VAR_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_SYSCTL_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
_DOC_RE = re.compile(r"^docs/.+\.md(#.+)?$")
_FOUND_RE = re.compile(r"\{found:([a-z0-9-]+)\}")
_ENV_PLACEHOLDER = "{env}"
#: In a command row's ``argv`` and ``stdout_match``: this machine's pixi platform name (``osx-arm64``, ...).
_PLATFORM_PLACEHOLDER = "{platform}"
_PREFLIGHT_LANES = "preflight-lanes"
_DEFAULT_TIMEOUT_S = 60.0
_TOOL_TIMEOUT_S = 20.0
_EXIT_TIMEOUT = 124
_EXIT_NO_LAUNCH = 127

#: Probe kind -> (keys of which exactly one group must be present, every key the kind allows). A kind with two groups
#: (the schema's ``oneOf`` branches) also names, in ``_GROUP_KEYS``, the keys each group allows on its own.
_PROBE_KEYS: dict[str, tuple[tuple[tuple[str, ...], ...], frozenset[str]]] = {
    "tool": ((("name",), ("any_of",)), frozenset({"name", "any_of", "version_argv", "floor", "found_note"})),
    "command": (
        (("argv",),),
        frozenset({"argv", "env", "expect_exit", "stdout_match", "miss_note", "timeout_s", "exit_notes"}),
    ),
    "environments": ((("names",), ("from",)), frozenset({"names", "from"})),
    "session-finding": ((("name",),), frozenset({"name"})),
    "register-probe": ((("package",),), frozenset({"package"})),
    "env-sync": ((), frozenset()),
    "git-config": ((("keys",),), frozenset({"keys"})),
    "git-hooks": ((("types",),), frozenset({"types"})),
    "locale-utf8": ((), frozenset()),
    "env-or-file": ((("var", "file"),), frozenset({"var", "file", "key"})),
    "file": ((("path",),), frozenset({"path"})),
    "sysctl": ((("key", "min"),), frozenset({"key", "min"})),
}
PROBE_KINDS: tuple[str, ...] = tuple(_PROBE_KEYS)
#: (kind, the group's keys) -> every key that group allows: a `tool` with `any_of` takes no top-level `version_argv`.
_GROUP_KEYS: dict[tuple[str, tuple[str, ...]], frozenset[str]] = {
    ("tool", ("name",)): frozenset({"name", "version_argv", "floor", "found_note"}),
    ("tool", ("any_of",)): frozenset({"any_of", "floor", "found_note"}),
    ("environments", ("names",)): frozenset({"names"}),
    ("environments", ("from",)): frozenset({"from"}),
}

_ROW_REQUIRED = frozenset({"id", "profile", "class", "severity", "what", "probe", "remedy"})
_ROW_ALLOWED = _ROW_REQUIRED | {"cost", "platforms", "needs", "declared_in"}
_REMEDY_ALLOWED = frozenset({"command", "who", "where", "note", "doc"})
_PROFILE_ALLOWED = frozenset({"title", "requires", "platforms"})


class DataFileError(PyforgeError, Exception):
    """The data file is absent, unreadable or breaks its schema; the verb cannot judge."""


Runner = Callable[[Sequence[str], Path, float], "subprocess.CompletedProcess[str]"]


def _default_runner(argv: Sequence[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    """Run one probe command through ``pyforge.core.process``. Never raises: a launch error reads as 127, a timeout as 124."""
    try:
        result = PosixProcess().run(list(argv), cwd=cwd, timeout_s=timeout)
    except ProcessError as exc:
        if isinstance(exc.__cause__, subprocess.TimeoutExpired):
            return subprocess.CompletedProcess(
                list(argv), _EXIT_TIMEOUT, stdout="", stderr=f"timeout after {timeout:g}s"
            )
        return subprocess.CompletedProcess(
            list(argv), _EXIT_NO_LAUNCH, stdout="", stderr=f"could not launch: {exc.__cause__ or exc}"
        )
    return subprocess.CompletedProcess(list(argv), result.returncode, stdout=result.stdout, stderr=result.stderr)


def host_platform(system: str | None = None, machine: str | None = None) -> str:
    """This machine as a pixi platform name (``osx-arm64``, ``linux-64``, ``win-64``, ...)."""
    system_name = (system if system is not None else _platform.system()).lower()
    arch = (machine if machine is not None else _platform.machine()).lower()
    arm = arch in ("arm64", "aarch64")
    if system_name == "darwin":
        return "osx-arm64" if arm else "osx-64"
    if system_name == "windows":
        return "win-arm64" if arm else "win-64"
    if system_name == "linux":
        return "linux-aarch64" if arm else "linux-64"
    return f"{system_name}-{arch}"


# ── the composed duties (production seams) ──────────────────────────────────────────────────────────────────────


def _session_findings(root: Path, names: Sequence[str]) -> dict[str, tuple[bool, str]]:
    """``session.py``'s own findings, run so that they install nothing."""
    from .session import machine_findings

    return {name: (finding.ok, finding.detail) for name, finding in machine_findings(root, names).items()}


def _register_row(root: Path, package: str) -> dict[str, Any] | None:
    """One row of the realization register, or ``None`` when it has no such package."""
    from .estate_realize import _load_register, _rows_by_package

    return _rows_by_package(_load_register(root)).get(package)


def _register_probe(root: Path, row: dict[str, Any], package: str, lock_platform: str, runner: Runner) -> str:
    """The register's own probe for ``row``: ``live``, ``stale`` or ``missing`` (its probes run ``--as-is``)."""
    from .estate_realize import RealizeDeps, run_probe

    deps = RealizeDeps(
        root=root,
        runner=lambda argv, cwd: runner(argv, cwd, _DEFAULT_TIMEOUT_S),
        platform=lambda: lock_platform,
    )
    return run_probe(deps, row, package=package)


def _env_sync(root: Path) -> tuple[bool, str]:
    """``provision.check_environment_sync``, with its two refusals read as findings."""
    from .provision import check_environment_sync

    try:
        in_sync, diff = check_environment_sync(cwd=root)
    except FileNotFoundError as exc:
        return False, f"could not compare: {exc}"
    except subprocess.CalledProcessError as exc:
        return False, f"`pixi project export conda-environment -e build` exited {exc.returncode}"
    if in_sync:
        return True, "environment.yaml matches pixi.toml"
    return False, f"environment.yaml differs from pixi.toml ({len(diff.splitlines())} diff lines)"


def _lane_environments(root: Path) -> dict[str, list[str]]:
    """Each environment a full pr-preflight lane runs in, with its lanes: derived from ``pixi.toml``, not listed."""
    from .preflight import DEFAULT_INVOKING_ENV, list_preflight_lanes

    pixi_data = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    by_env: dict[str, list[str]] = {}
    for lane in list_preflight_lanes(pixi_data, invoking_env=DEFAULT_INVOKING_ENV):
        by_env.setdefault(lane.environment, []).append(lane.task)
    return by_env


def _pixi_floor(root: Path) -> str:
    return pixi_floor_version(root=root)


@dataclass
class MachineDeps:
    """Everything a probe reaches outside this module; the unit tests replace each field."""

    root: Path
    runner: Runner = _default_runner
    which: Callable[[str], str | None] = shutil.which
    platform: str = field(default_factory=host_platform)
    environ: Mapping[str, str] = field(default_factory=lambda: os.environ)
    home: Path = field(default_factory=Path.home)
    session_findings: Callable[[Path, Sequence[str]], dict[str, tuple[bool, str]]] = _session_findings
    register_row: Callable[[Path, str], dict[str, Any] | None] = _register_row
    register_probe: Callable[[Path, dict[str, Any], str, str, Runner], str] = _register_probe
    env_sync: Callable[[Path], tuple[bool, str]] = _env_sync
    lane_environments: Callable[[Path], dict[str, list[str]]] = _lane_environments
    pixi_floor: Callable[[Path], str] = _pixi_floor


def production_deps(root: Path) -> MachineDeps:
    return MachineDeps(root=root)


# ── the data file ───────────────────────────────────────────────────────────────────────────────────────────────


def _is_words(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(word, str) and word for word in value)


def _probe_problems(where: str, probe: object) -> list[str]:
    if not isinstance(probe, dict):
        return [f"{where}: a probe is a mapping with a `kind`"]
    kind = probe.get("kind")
    if not isinstance(kind, str) or kind not in _PROBE_KEYS:
        return [f"{where}: unknown probe kind {kind!r} (kinds: {', '.join(PROBE_KINDS)})"]
    groups, allowed = _PROBE_KEYS[kind]
    problems = [f"{where}: {kind} does not take `{key}`" for key in sorted(set(probe) - allowed - {"kind"})]
    if groups:
        present = [group for group in groups if all(key in probe for key in group)]
        if len(present) != 1:
            choices = " or ".join(" + ".join(f"`{key}`" for key in group) for group in groups)
            problems.append(f"{where}: {kind} needs exactly one of {choices}")
        elif (kind, present[0]) in _GROUP_KEYS:
            own = _GROUP_KEYS[(kind, present[0])]
            with_ = " + ".join(f"`{key}`" for key in present[0])
            problems += [
                f"{where}: {kind} with {with_} does not take `{key}`"
                for key in sorted((set(probe) & allowed) - own - {"kind"})
            ]
    for key in ("argv", "names", "keys", "types", "version_argv"):
        if key in probe and not _is_words(probe[key]):
            problems.append(f"{where}: `{key}` is a non-empty list of strings")
    if "any_of" in probe:
        candidates = probe["any_of"]
        if not isinstance(candidates, list) or not candidates:
            problems.append(f"{where}: `any_of` is a non-empty list")
        else:
            for candidate in candidates:
                if (
                    not isinstance(candidate, dict)
                    or not isinstance(candidate.get("name"), str)
                    or not candidate["name"]
                ):
                    problems.append(f"{where}: each `any_of` entry is a mapping with a non-empty `name`")
                elif set(candidate) - {"name", "version_argv", "label"}:
                    problems.append(f"{where}: an `any_of` entry takes only name, version_argv and label")
                elif "version_argv" in candidate and not _is_words(candidate["version_argv"]):
                    problems.append(f"{where}: `version_argv` is a non-empty list of strings")
                elif "label" in candidate and (not isinstance(candidate["label"], str) or not candidate["label"]):
                    problems.append(f"{where}: an `any_of` entry's `label` is a non-empty string")
    if "floor" in probe:
        floor = probe["floor"]
        literal = floor.get("literal") if isinstance(floor, dict) else None
        if floor != {"pixi-requires": True} and not (
            isinstance(floor, dict)
            and set(floor) == {"literal"}
            and isinstance(literal, str)
            and re.fullmatch(r"[0-9]+(\.[0-9]+)+", literal)
        ):
            problems.append(f"{where}: `floor` is {{pixi-requires: true}} or {{literal: 'x.y.z'}}")
    if kind == "environments" and "from" in probe and probe["from"] != _PREFLIGHT_LANES:
        problems.append(f"{where}: `from` is {_PREFLIGHT_LANES}")
    if kind == "session-finding" and probe.get("name") not in SESSION_FINDINGS:
        problems.append(f"{where}: unknown session finding {probe.get('name')!r}")
    if kind == "sysctl" and (not isinstance(probe.get("min"), int) or isinstance(probe.get("min"), bool)):
        problems.append(f"{where}: `min` is an integer")
    elif kind == "sysctl" and probe["min"] < 0:
        problems.append(f"{where}: `min` is at least 0")
    patterns = (
        {"var": _VAR_RE, "key": _VAR_RE} if kind == "env-or-file" else {"key": _SYSCTL_RE} if kind == "sysctl" else {}
    )
    for key, pattern in patterns.items():
        if isinstance(probe.get(key), str) and probe[key] and not pattern.fullmatch(probe[key]):
            problems.append(f"{where}: `{key}` {probe[key]!r} does not match {pattern.pattern}")
    if "miss_note" in probe and "stdout_match" not in probe:
        problems.append(f"{where}: `miss_note` explains a missed `stdout_match`, which the probe lacks")
    for key in ("name", "package", "var", "file", "path", "key", "env", "stdout_match", "miss_note", "found_note"):
        if key in probe and (not isinstance(probe[key], str) or not probe[key]):
            problems.append(f"{where}: `{key}` is a non-empty string")
    if "stdout_match" in probe and isinstance(probe["stdout_match"], str):
        try:
            re.compile(probe["stdout_match"])
        except re.error as exc:
            problems.append(f"{where}: `stdout_match` is not a regular expression ({exc})")
    if "expect_exit" in probe and (not isinstance(probe["expect_exit"], int) or isinstance(probe["expect_exit"], bool)):
        problems.append(f"{where}: `expect_exit` is an integer")
    elif "expect_exit" in probe and probe["expect_exit"] < 0:
        problems.append(f"{where}: `expect_exit` is at least 0")
    if "timeout_s" in probe and (
        not isinstance(probe["timeout_s"], (int, float))
        or isinstance(probe["timeout_s"], bool)
        or probe["timeout_s"] <= 0
    ):
        problems.append(f"{where}: `timeout_s` is a positive number")
    if "exit_notes" in probe:
        notes = probe["exit_notes"]
        if not isinstance(notes, dict) or not all(
            isinstance(code, str) and code.isdigit() and isinstance(text, str) and text for code, text in notes.items()
        ):
            problems.append(f"{where}: `exit_notes` maps an exit code (a string of digits) to a sentence")
    return problems


def _platform_problems(where: str, value: object) -> list[str]:
    if not isinstance(value, list) or not value or any(item not in PLATFORMS for item in value):
        return [f"{where}: `platforms` is a non-empty list of {', '.join(PLATFORMS)}"]
    return _twice(where, "platforms", value)


def _twice(where: str, key: str, value: list[Any]) -> list[str]:
    """The schema's ``uniqueItems``: a list that names an item twice."""
    seen: list[Any] = []
    for item in value:
        if item in seen:
            return [f"{where}: `{key}` names {item!r} twice"]
        seen.append(item)
    return []


def validate_data(doc: object) -> list[str]:
    """Every way ``doc`` breaks the data file's contract, as sentences; empty when it holds.

    The same rules as ``machine-readiness.schema.json`` (a meta-test holds the two together), plus the references a
    schema cannot state: a row's profile, a row's ``needs`` (an EARLIER row, so the file's order is a run order) and
    a profile's ``requires`` (no cycle).
    """
    if not isinstance(doc, dict):
        return ["the document is not a mapping"]
    problems = [f"unknown top-level key `{key}`" for key in sorted(set(doc) - {"version", "profiles", "checks"})]
    if doc.get("version") != 1 or isinstance(doc.get("version"), bool):
        problems.append("`version` is 1")
    profiles = doc.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        return [*problems, "`profiles` is a non-empty mapping"]
    for name, profile in profiles.items():
        where = f"profile {name}"
        if not isinstance(name, str) or not _ID_RE.fullmatch(name):
            problems.append(f"{where}: the id is kebab-case")
        if not isinstance(profile, dict):
            problems.append(f"{where}: is a mapping")
            continue
        problems += [f"{where}: unknown key `{key}`" for key in sorted(set(profile) - _PROFILE_ALLOWED)]
        if not isinstance(profile.get("title"), str) or not profile.get("title"):
            problems.append(f"{where}: `title` is a sentence")
        requires = profile.get("requires")
        if not isinstance(requires, list) or not all(isinstance(dep, str) for dep in requires):
            problems.append(f"{where}: `requires` is a list of profile ids")
        else:
            problems += [f"{where}: requires the undefined profile {dep!r}" for dep in requires if dep not in profiles]
            problems += _twice(where, "requires", requires)
        if "platforms" in profile:
            problems += _platform_problems(where, profile["platforms"])
    if not problems:
        for name in profiles:
            try:
                profile_closure(doc, [name])
            except DataFileError as exc:
                problems.append(str(exc))
                break
    checks = doc.get("checks")
    if not isinstance(checks, list) or not checks:
        return [*problems, "`checks` is a non-empty list"]
    seen: set[str] = set()
    for index, row in enumerate(checks):
        if not isinstance(row, dict):
            problems.append(f"check #{index + 1}: is a mapping")
            continue
        row_id = row.get("id")
        where = f"check {row_id}" if isinstance(row_id, str) else f"check #{index + 1}"
        problems += [f"{where}: unknown key `{key}`" for key in sorted(set(row) - _ROW_ALLOWED)]
        problems += [f"{where}: lacks `{key}`" for key in sorted(_ROW_REQUIRED - set(row))]
        if not isinstance(row_id, str) or not _ID_RE.fullmatch(row_id):
            problems.append(f"{where}: `id` is kebab-case")
        elif row_id in seen:
            problems.append(f"{where}: the id is used twice")
        if "profile" in row and not isinstance(row["profile"], str):
            problems.append(f"{where}: `profile` is a profile id")
        elif "profile" in row and row["profile"] not in profiles:
            problems.append(f"{where}: names the undefined profile {row['profile']!r}")
        for key, allowed in (("class", CLASSES), ("severity", SEVERITIES), ("cost", COSTS)):
            if key in row and row[key] not in allowed:
                problems.append(f"{where}: `{key}` is one of {', '.join(allowed)}")
        if "what" in row and (not isinstance(row["what"], str) or not row["what"]):
            problems.append(f"{where}: `what` is a sentence")
        if "declared_in" in row and (not isinstance(row["declared_in"], str) or not row["declared_in"]):
            problems.append(f"{where}: `declared_in` is a tracked path")
        if "platforms" in row:
            problems += _platform_problems(where, row["platforms"])
        if "needs" in row:
            needs = row["needs"]
            if not isinstance(needs, list) or not needs or not all(isinstance(need, str) for need in needs):
                problems.append(f"{where}: `needs` is a non-empty list of check ids")
            else:
                problems += [
                    f"{where}: needs {need!r}, which is not an earlier check" for need in needs if need not in seen
                ]
                problems += _twice(where, "needs", needs)
        if "probe" in row:
            probes = row["probe"] if isinstance(row["probe"], list) else [row["probe"]]
            if not probes:
                problems.append(f"{where}: `probe` is one probe or a non-empty list of probes")
            for probe in probes:
                problems += _probe_problems(where, probe)
        remedy = row.get("remedy")
        if "remedy" in row:
            if not isinstance(remedy, dict):
                problems.append(f"{where}: `remedy` is a mapping")
            else:
                problems += [
                    f"{where}: remedy has the unknown key `{key}`" for key in sorted(set(remedy) - _REMEDY_ALLOWED)
                ]
                if not isinstance(remedy.get("command"), str) or not remedy.get("command"):
                    problems.append(f"{where}: remedy lacks `command`")
                if remedy.get("who") not in WHO:
                    problems.append(f"{where}: remedy lacks `who` ({' or '.join(WHO)})")
                if "where" in remedy and remedy["where"] not in WHERE:
                    problems.append(f"{where}: remedy `where` is one of {', '.join(WHERE)}")
                for key in ("note", "doc"):
                    if key in remedy and (not isinstance(remedy[key], str) or not remedy[key]):
                        problems.append(f"{where}: remedy `{key}` is a non-empty string")
                if isinstance(remedy.get("doc"), str) and remedy["doc"] and not _DOC_RE.fullmatch(remedy["doc"]):
                    problems.append(
                        f"{where}: remedy `doc` {remedy['doc']!r} is not a page under docs/ (docs/<page>.md)"
                    )
        if isinstance(row_id, str):
            seen.add(row_id)
    return problems


def load_data(root: Path) -> dict[str, Any]:
    """The data file under ``root``, validated; ``DataFileError`` when it is absent, unreadable or invalid."""
    path = root / DATA_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DataFileError(f"{DATA_REL} could not be read under {root}: {exc.strerror or exc}") from exc
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DataFileError(f"{DATA_REL} is not YAML: {str(exc).splitlines()[0]}") from exc
    problems = validate_data(doc)
    if problems:
        shown = "; ".join(problems[:5]) + (f"; and {len(problems) - 5} more" if len(problems) > 5 else "")
        raise DataFileError(f"{DATA_REL} breaks {SCHEMA_REL.name}: {shown}")
    assert isinstance(doc, dict)  # noqa: S101 - validate_data returned nothing, so it is the mapping it checked
    return doc


def profile_closure(data: Mapping[str, Any], chosen: Sequence[str]) -> list[str]:
    """``chosen`` and every profile they require, each once, a required profile before the one that requires it."""
    profiles = data["profiles"]
    order: list[str] = []

    def visit(name: str, stack: tuple[str, ...]) -> None:
        if name in stack:
            raise DataFileError(f"profile {name}: `requires` is a cycle ({' -> '.join((*stack, name))})")
        if name in order:
            return
        for dep in profiles[name].get("requires") or []:
            visit(dep, (*stack, name))
        order.append(name)

    for name in chosen:
        visit(name, ())
    return order


def _probes(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    probe = row["probe"]
    return list(probe) if isinstance(probe, list) else [probe]


def desktop_software_rows(root: Path) -> tuple[tuple[str, dict[str, Any]], ...]:
    """Each tool the default profile's software rows name, in file order, with its row's remedy."""
    tools: list[tuple[str, dict[str, Any]]] = []
    for row in load_data(root)["checks"]:
        if row["profile"] != DEFAULT_PROFILE or row["class"] != "software":
            continue
        tools += [
            (probe["name"], row["remedy"]) for probe in _probes(row) if probe["kind"] == "tool" and "name" in probe
        ]
    return tuple(tools)


def desktop_software_tools(root: Path) -> tuple[str, ...]:
    """The tools the default profile's software rows name, in file order: what ``gather_prereqs`` checks."""
    return tuple(name for name, _remedy in desktop_software_rows(root))


# ── the run ─────────────────────────────────────────────────────────────────────────────────────────────────────


@dataclass
class Outcome:
    """What one probe found. ``missing`` names the environments a remedy's ``{env}`` is printed for."""

    status: str
    detail: str
    found: str | None = None
    required: str | None = None
    composes: str | None = None
    tool: str | None = None
    missing: tuple[str, ...] = ()


@dataclass
class CheckResult:
    row: dict[str, Any]
    status: str
    detail: str
    found: str | None = None
    required: str | None = None
    composes: str | None = None
    missing: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return str(self.row["id"])

    @property
    def advisory(self) -> bool:
        return self.row["severity"] == "advisory"


@dataclass
class _Lock:
    """Which lock platforms carry each environment, and each lock platform's subdir (``osx-arm64-min`` is osx-arm64)."""

    carried: dict[str, tuple[str, ...]]
    subdir: dict[str, str]

    def key_for(self, env: str, platform: str) -> str | None:
        for key in self.carried.get(env, ()):
            if self.subdir.get(key, key) == platform:
                return key
        return None


@dataclass
class _Run:
    deps: MachineDeps
    data: dict[str, Any]
    deep: bool
    results: dict[str, CheckResult] = field(default_factory=dict)
    found: dict[str, str] = field(default_factory=dict)
    cache: dict[str, Any] = field(default_factory=dict)

    def lock(self) -> _Lock | None:
        if "lock" not in self.cache:
            self.cache["lock"] = _read_lock(self.deps.root)
        lock: _Lock | None = self.cache["lock"]
        return lock

    def materialized(self, env: str) -> bool:
        return (self.deps.root / ".pixi" / "envs" / env / "conda-meta" / "pixi").is_file()

    def lanes(self) -> dict[str, list[str]]:
        if "lanes" not in self.cache:
            self.cache["lanes"] = self.deps.lane_environments(self.deps.root)
        lanes: dict[str, list[str]] = self.cache["lanes"]
        return lanes

    def session(self, name: str) -> tuple[bool, str]:
        findings: dict[str, tuple[bool, str]] = self.cache.setdefault("session", {})
        if name not in findings:
            # token-kit and codegraph-index are two readings of one seed check: ask for both at once.
            ask = ("token-kit", "codegraph-index") if name in ("token-kit", "codegraph-index") else (name,)
            findings.update(self.deps.session_findings(self.deps.root, ask))
        return findings[name]


def _read_lock(root: Path) -> _Lock | None:
    try:
        # The C safe loader where libyaml is built in: the same document, about five times faster (Story 117.14).
        loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
        doc = yaml.load((root / "pixi.lock").read_text(encoding="utf-8"), Loader=loader)  # noqa: S506 -- a safe loader
    except OSError, yaml.YAMLError:
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("environments"), dict):
        return None
    subdir: dict[str, str] = {}
    for entry in doc.get("platforms") or []:
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            subdir[entry["name"]] = str(entry.get("subdir") or entry["name"])
    carried: dict[str, tuple[str, ...]] = {}
    for env, block in doc["environments"].items():
        packages = block.get("packages") if isinstance(block, dict) else None
        carried[str(env)] = tuple(str(key) for key in packages) if isinstance(packages, dict) else ()
    return _Lock(carried=carried, subdir=subdir)


def _tail(proc: subprocess.CompletedProcess[str]) -> str:
    lines = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip().splitlines()
    return lines[-1].strip()[:200] if lines else "no output"


def _substitute(text: str, found: Mapping[str, str]) -> str:
    return _FOUND_RE.sub(lambda match: found.get(match.group(1), f"<{match.group(1)}>"), text)


def _environment_gate(run: _Run, env: str) -> Outcome | None:
    """Why a probe inside ``env`` cannot run here, or ``None`` when it can."""
    lock = run.lock()
    if lock is None:
        return Outcome(FAIL, "pixi.lock could not be read", missing=(env,))
    if lock.key_for(env, run.deps.platform) is None:
        return Outcome(NA, f"not applicable here: the lock does not carry {env} for {run.deps.platform}")
    if not run.materialized(env):
        return Outcome(BLOCKED, f"the environment {env} is not materialized", missing=(env,))
    return None


def _floor(run: _Run, probe: Mapping[str, Any]) -> str | None:
    floor = probe.get("floor")
    if not floor:
        return None
    if floor.get("pixi-requires"):
        return run.deps.pixi_floor(run.deps.root)
    return str(floor["literal"])


def _probe_tool(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    deps = run.deps
    floor = _floor(run, probe)
    candidates = probe.get("any_of") or [{"name": probe["name"], "version_argv": probe.get("version_argv")}]
    absent: list[str] = []
    for candidate in candidates:
        name = candidate["name"]
        label = candidate.get("label") or name
        path = deps.which(name)
        if path is None:
            absent.append(f"{name} is not on PATH")
            continue
        argv = [path, *(candidate.get("version_argv") or ["--version"])]
        proc = deps.runner(argv, deps.root, _TOOL_TIMEOUT_S)
        version = _first_version(proc.stdout or "") or _first_version(proc.stderr or "")
        shown = " ".join([name, *argv[1:]])
        if proc.returncode != 0 or version is None:
            absent.append(f"`{shown}` gave no version (exit {proc.returncode})")
            continue
        if floor is not None and not _version_gte(version, floor):
            return Outcome(
                FAIL, f"{label} {version} is below the floor {floor}", found=version, required=floor, tool=name
            )
        detail = f"{label} {version}" + (f" (floor >= {floor})" if floor else "")
        if probe.get("found_note"):
            detail += "; " + str(probe["found_note"]).replace("{name}", name)
        return Outcome(OK, detail, found=version, required=floor, tool=name)
    return Outcome(FAIL, "; ".join(absent), required=floor)


def _probe_command(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    deps = run.deps
    argv = [_substitute(str(word), run.found).replace(_PLATFORM_PLACEHOLDER, deps.platform) for word in probe["argv"]]
    shown = " ".join(argv)
    env = probe.get("env")
    missing: tuple[str, ...] = ()
    if env:
        gate = _environment_gate(run, env)
        if gate is not None:
            return gate
        missing = (env,)
        shown = f"pixi run --as-is -e {env} {shown}"
        full = ["pixi", "run", "--as-is", "-x", "-e", env, *argv]
    else:
        path = deps.which(argv[0])
        if path is None:
            return Outcome(FAIL, f"{argv[0]} is not on PATH")
        full = [path, *argv[1:]]
    proc = deps.runner(full, deps.root, float(probe.get("timeout_s") or _DEFAULT_TIMEOUT_S))
    expect = int(probe.get("expect_exit", 0))
    if proc.returncode != expect:
        note = (probe.get("exit_notes") or {}).get(str(proc.returncode))
        detail = f"`{shown}` exited {proc.returncode}: " + (note or _tail(proc))
        return Outcome(FAIL, detail, missing=missing)
    pattern = probe.get("stdout_match")
    if pattern:
        pattern = str(pattern).replace(_PLATFORM_PLACEHOLDER, re.escape(deps.platform))
    if pattern and not re.search(pattern, proc.stdout or ""):
        note = probe.get("miss_note")
        why = str(note).replace(_PLATFORM_PLACEHOLDER, deps.platform) if note else _tail(proc)
        return Outcome(FAIL, f"`{shown}` printed no line matching /{pattern}/: {why}", missing=missing)
    return Outcome(OK, f"`{shown}` exit {expect}")


def _probe_environments(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    deps = run.deps
    lanes: dict[str, list[str]] = {}
    if "from" in probe:
        lanes = run.lanes()
        names = list(lanes)
    else:
        names = list(probe["names"])
    lock = run.lock()
    if lock is None:
        return Outcome(FAIL, "pixi.lock could not be read, so no environment can be judged")
    not_here: list[str] = []
    missing: list[str] = []
    present: list[str] = []
    for env in names:
        if lock.key_for(env, deps.platform) is None:
            removed = f" (its lanes do not run here: {', '.join(lanes[env])})" if lanes.get(env) else ""
            not_here.append(f"{env}{removed}")
        elif run.materialized(env):
            present.append(env)
        else:
            missing.append(env)
    aside = (
        f"; not applicable here, the lock does not carry for {deps.platform}: {'; '.join(not_here)}" if not_here else ""
    )
    if missing:
        return Outcome(FAIL, f"not materialized: {', '.join(missing)}{aside}", missing=tuple(missing))
    if not present:
        return Outcome(NA, f"not applicable here: the lock does not carry {', '.join(names)} for {deps.platform}")
    return Outcome(OK, f"materialized: {', '.join(present)}{aside}")


def _probe_session_finding(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    name = probe["name"]
    ok, detail = run.session(name)
    return Outcome(OK if ok else FAIL, detail, composes=f"steward session check: {name}")


def _probe_register(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    deps = run.deps
    package = probe["package"]
    composes = f"realization register: {package}"
    row = deps.register_row(deps.root, package)
    if row is None:
        return Outcome(FAIL, f"docs/governance/realization-register.yaml has no row {package}", composes=composes)
    env = str(row.get("env") or "pyforge-guild")
    gate = _environment_gate(run, env)
    if gate is not None:
        gate.composes = composes
        return gate
    lock = run.lock()
    lock_key = lock.key_for(env, deps.platform) if lock is not None else None
    state = deps.register_probe(deps.root, row, package, lock_key or deps.platform, deps.runner)
    if state == "live":
        return Outcome(OK, f"{package} reads live in {env}", composes=composes)
    meaning = "differs from the lock, or its probe failed" if state == "stale" else "did not answer"
    return Outcome(FAIL, f"{package} reads {state} in {env}: it {meaning}", composes=composes, missing=(env,))


def _probe_env_sync(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    ok, detail = run.deps.env_sync(run.deps.root)
    return Outcome(OK if ok else FAIL, detail, composes="steward provision --verify")


def _probe_git_config(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    deps = run.deps
    unset: list[str] = []
    for key in probe["keys"]:
        proc = deps.runner(["git", "config", "--get", key], deps.root, _TOOL_TIMEOUT_S)
        if proc.returncode != 0 or not (proc.stdout or "").strip():
            unset.append(key)
    if unset:
        return Outcome(FAIL, f"not set: {', '.join(unset)}")
    return Outcome(OK, f"set: {', '.join(probe['keys'])}")


def _probe_git_hooks(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    deps = run.deps
    proc = deps.runner(["git", "rev-parse", "--git-common-dir"], deps.root, _TOOL_TIMEOUT_S)
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return Outcome(FAIL, f"not a git checkout: `git rev-parse --git-common-dir` exited {proc.returncode}")
    hooks = (deps.root / proc.stdout.strip()).resolve() / "hooks"
    absent = [kind for kind in probe["types"] if not (hooks / kind).is_file()]
    if absent:
        return Outcome(FAIL, f"not installed in the shared hooks directory: {', '.join(absent)}")
    return Outcome(OK, f"installed in the shared hooks directory: {', '.join(probe['types'])}")


#: What CPython sets ``LC_CTYPE`` to for itself when it starts under a C locale (PEP 538). This verb is such a
#: process, so that value in its environment says nothing about the shell that started it.
_COERCED_LC_CTYPE = frozenset({"C.UTF-8", "C.utf8", "UTF-8"})


def _names_utf8(value: str) -> bool:
    return "utf8" in value.lower().replace("-", "")


def _probe_locale(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    """The character set the shell's locale variables name, by POSIX precedence: LC_ALL, LC_CTYPE, LANG.

    Read from the variables, not from ``locale charmap``: under a C locale CPython coerces its own ``LC_CTYPE`` to
    UTF-8, a child inherits it, and ``locale charmap`` then prints UTF-8 on a machine whose every other program
    sees C (measured 2026-11-25). So an ``LC_CTYPE`` that is one of the coercion values is not evidence of a UTF-8
    shell: with ``LC_ALL`` unset, ``LANG`` decides.
    """
    environ = run.deps.environ
    lc_all, lc_ctype, lang = (environ.get(name) or "" for name in ("LC_ALL", "LC_CTYPE", "LANG"))
    shown = ", ".join(
        f"{name}={value or 'unset'}" for name, value in (("LC_ALL", lc_all), ("LC_CTYPE", lc_ctype), ("LANG", lang))
    )
    if lc_all:
        ok = _names_utf8(lc_all)
    elif lc_ctype and lc_ctype not in _COERCED_LC_CTYPE:
        ok = _names_utf8(lc_ctype)
    else:
        ok = _names_utf8(lang)
    if ok:
        return Outcome(OK, f"the locale names UTF-8 ({shown})", found="UTF-8")
    return Outcome(FAIL, f"the locale does not name UTF-8 ({shown})", required="UTF-8")


def _file_has_key(path: Path, key: str) -> bool:
    """Whether a dotenv-style file gives ``key`` a non-empty value. The value itself is never returned."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError, UnicodeDecodeError:
        return False
    for line in lines:
        name, sep, value = line.strip().removeprefix("export ").partition("=")
        if sep and name.strip() == key and value.strip().strip("'\""):
            return True
    return False


def _probe_env_or_file(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    deps = run.deps
    var = probe["var"]
    key = probe.get("key") or var
    if deps.environ.get(var):
        return Outcome(OK, f"{var} is set in the environment (its value is not read out)")
    if _file_has_key(deps.root / probe["file"], key):
        return Outcome(OK, f"{key} is a key of {probe['file']} (its value is not read out)")
    return Outcome(FAIL, f"{var} is not set in the environment and {probe['file']} has no {key}")


def _probe_file(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    raw = str(probe["path"])
    if raw == "~" or raw.startswith("~/"):
        path = run.deps.home / raw[2:]
    else:
        path = Path(raw) if Path(raw).is_absolute() else run.deps.root / raw
    if path.is_file():
        return Outcome(OK, f"{raw} exists (its content is not read)")
    return Outcome(FAIL, f"{raw} does not exist")


def _probe_sysctl(run: _Run, probe: Mapping[str, Any]) -> Outcome:
    deps = run.deps
    if not deps.platform.startswith("linux-"):
        return Outcome(
            NA, f"not applicable here: {probe['key']} is a Linux kernel setting, and this is {deps.platform}"
        )
    proc = deps.runner(["sysctl", "-n", probe["key"]], deps.root, _TOOL_TIMEOUT_S)
    text = (proc.stdout or "").strip()
    minimum = int(probe["min"])
    if proc.returncode != 0 or not text.isdigit():
        return Outcome(
            FAIL, f"`sysctl -n {probe['key']}` gave no number (exit {proc.returncode})", required=str(minimum)
        )
    if int(text) < minimum:
        return Outcome(FAIL, f"{probe['key']} is {text}, below {minimum}", found=text, required=str(minimum))
    return Outcome(OK, f"{probe['key']} is {text} (at least {minimum})", found=text, required=str(minimum))


_PROBE_RUNNERS: dict[str, Callable[[_Run, Mapping[str, Any]], Outcome]] = {
    "tool": _probe_tool,
    "command": _probe_command,
    "environments": _probe_environments,
    "session-finding": _probe_session_finding,
    "register-probe": _probe_register,
    "env-sync": _probe_env_sync,
    "git-config": _probe_git_config,
    "git-hooks": _probe_git_hooks,
    "locale-utf8": _probe_locale,
    "env-or-file": _probe_env_or_file,
    "file": _probe_file,
    "sysctl": _probe_sysctl,
}


def _unsupported_reason(data: Mapping[str, Any], profile: str, platform: str) -> str | None:
    """Why ``profile`` cannot be reached on ``platform`` (its own platforms, or a required profile's), else ``None``."""
    for name in profile_closure(data, [profile]):
        platforms = data["profiles"][name].get("platforms")
        if platforms and platform not in platforms:
            return f"the {name} profile needs {' or '.join(platforms)}, and this machine is {platform}"
    return None


def _row_environments(run: _Run, row: Mapping[str, Any]) -> tuple[str, ...]:
    """The environments the row's own probes name, for a remedy's ``{env}`` when no probe measured which are missing.

    A row BLOCKED behind ``pixi`` never ran its probe; its remedy is still an exact command per environment: an
    ``environments`` probe's names (or each environment a full pr-preflight lane runs in), a command's ``env`` and a
    register probe's environment. A name that cannot be read here leaves the placeholder, never a guess.
    """
    names: list[str] = []
    for probe in _probes(row):
        try:
            if probe["kind"] == "environments":
                names += list(run.lanes()) if "from" in probe else list(probe["names"])
            elif probe.get("env"):
                names.append(str(probe["env"]))
            elif probe["kind"] == "register-probe":
                register = run.deps.register_row(run.deps.root, probe["package"])
                if register is not None:
                    names.append(str(register.get("env") or "pyforge-guild"))
        except Exception:  # noqa: BLE001, S112 - a name that cannot be read keeps the placeholder
            continue
    return tuple(dict.fromkeys(names))


def _evaluate(run: _Run, row: dict[str, Any]) -> CheckResult:
    result = _judge(run, row)
    if result.status in (FAIL, BLOCKED) and not result.missing and _ENV_PLACEHOLDER in str(row["remedy"]["command"]):
        result.missing = _row_environments(run, row)
    return result


def _judge(run: _Run, row: dict[str, Any]) -> CheckResult:
    deps = run.deps
    unsupported = _unsupported_reason(run.data, row["profile"], deps.platform)
    if unsupported:
        return CheckResult(row, NA, f"not applicable here: {unsupported}")
    platforms = row.get("platforms")
    if platforms and deps.platform not in platforms:
        return CheckResult(
            row, NA, f"not applicable here: the check applies to {', '.join(platforms)}, not {deps.platform}"
        )
    if row.get("cost") == "deep" and not run.deep:
        return CheckResult(row, SKIPPED, "a deep check; --deep runs it")
    for need in row.get("needs") or []:
        earlier = run.results.get(need)
        if earlier is None or earlier.status in (OK, NA):
            continue
        if earlier.status == SKIPPED:
            return CheckResult(row, SKIPPED, f"needs {need}, which was skipped")
        return CheckResult(row, BLOCKED, f"needs {need}, which is {earlier.status}")
    details: list[str] = []
    result = CheckResult(row, OK, "")
    for probe in _probes(row):
        try:
            outcome = _PROBE_RUNNERS[probe["kind"]](run, probe)
        except Exception as exc:  # noqa: BLE001 - a probe that cannot run is a failed row, never a crash
            outcome = Outcome(FAIL, f"the {probe['kind']} probe could not run: {type(exc).__name__}: {exc}")
        if outcome.tool and row["id"] not in run.found:
            run.found[row["id"]] = outcome.tool
        result.found = result.found or outcome.found
        result.required = result.required or outcome.required
        result.composes = result.composes or outcome.composes
        if outcome.status != OK:
            result.status, result.detail, result.missing = outcome.status, outcome.detail, outcome.missing
            return result
        details.append(outcome.detail)
    result.detail = "; ".join(details)
    return result


def select_rows(
    data: Mapping[str, Any], profiles: Sequence[str], classes: Sequence[str] | None
) -> list[dict[str, Any]]:
    """The rows of ``profiles`` in file order, narrowed to ``classes``, plus every row one of them needs."""
    rows = [row for row in data["checks"] if row["profile"] in profiles]
    by_id = {row["id"]: row for row in data["checks"]}
    wanted = {row["id"] for row in rows if not classes or row["class"] in classes}
    frontier = list(wanted)
    while frontier:
        for need in by_id[frontier.pop()].get("needs") or []:
            if need not in wanted:
                wanted.add(need)
                frontier.append(need)
    return [row for row in data["checks"] if row["id"] in wanted]


@dataclass
class ProfileVerdict:
    id: str
    title: str
    chosen: bool
    supported: bool
    ready: bool
    requires: list[str]
    reason: str
    counts: dict[str, int]
    #: The classes the verdict covers: all four, or the ``--class`` narrowing (then it is not the profile's verdict).
    classes: tuple[str, ...] = CLASSES

    @property
    def narrowed(self) -> bool:
        return self.classes != CLASSES


@dataclass
class Report:
    platform: str
    root: Path
    profiles: list[ProfileVerdict]
    checks: list[CheckResult]
    found: dict[str, str]

    @property
    def ok(self) -> bool:
        return all(profile.ready for profile in self.profiles if profile.chosen)


def _counts(results: Sequence[CheckResult]) -> dict[str, int]:
    counts = {"ok": 0, "fail": 0, "blocked": 0, "skipped": 0, "advisory": 0, "na": 0}
    for result in results:
        if result.advisory and result.status in (FAIL, BLOCKED):
            counts["advisory"] += 1
        else:
            counts[result.status] += 1
    return counts


def run_checks(
    data: dict[str, Any],
    deps: MachineDeps,
    *,
    chosen: Sequence[str],
    classes: Sequence[str] | None = None,
    deep: bool = False,
) -> Report:
    """Run the rows of ``chosen`` and of the profiles they require, and judge each profile."""
    closure = profile_closure(data, chosen)
    run = _Run(deps=deps, data=data, deep=deep)
    judged = tuple(name for name in CLASSES if not classes or name in classes)
    for row in select_rows(data, closure, classes):
        run.results[row["id"]] = _evaluate(run, row)
    results = list(run.results.values())
    verdicts: list[ProfileVerdict] = []
    for name in closure:
        profile = data["profiles"][name]
        own = [result for result in results if result.row["profile"] == name]
        within = set(profile_closure(data, [name]))
        holding = [
            result.id
            for result in results
            if result.row["profile"] in within and not result.advisory and result.status not in _NOT_BLOCKING
        ]
        unsupported = _unsupported_reason(data, name, deps.platform)
        skipped = sum(1 for result in results if result.row["profile"] in within and result.status == SKIPPED)
        if unsupported:
            reason = f"unsupported here: {unsupported}"
        elif holding:
            reason = f"not ok: {', '.join(holding)}"
        elif skipped:
            reason = f"{skipped} deep check{'s' if skipped != 1 else ''} skipped; --deep runs them"
        else:
            reason = ""
        verdicts.append(
            ProfileVerdict(
                id=name,
                title=str(profile["title"]),
                chosen=name in chosen,
                supported=unsupported is None,
                ready=unsupported is None and not holding,
                requires=list(profile.get("requires") or []),
                reason=reason,
                counts=_counts(own),
                classes=judged,
            )
        )
    return Report(platform=deps.platform, root=deps.root, profiles=verdicts, checks=results, found=dict(run.found))


# ── the reports ─────────────────────────────────────────────────────────────────────────────────────────────────


def remedy_commands(row: Mapping[str, Any], missing: Sequence[str], found: Mapping[str, str]) -> list[str]:
    """The row's remedy as exact commands: ``{env}`` once per missing environment, ``{found:<id>}`` filled in."""
    command = _substitute(str(row["remedy"]["command"]), found)
    if _ENV_PLACEHOLDER not in command:
        return [command]
    return [command.replace(_ENV_PLACEHOLDER, env) for env in (missing or ("<environment>",))]


def _label(result: CheckResult) -> str:
    if result.status == OK:
        return "ok"
    if result.status == SKIPPED:
        return "skip"
    if result.status == NA:
        return "n/a"
    if result.advisory:
        return "WARN"
    return "FAIL" if result.status == FAIL else "BLOCKED"


def _check_dict(result: CheckResult, found: Mapping[str, str]) -> dict[str, object]:
    row = result.row
    remedy = row["remedy"]
    return {
        "id": row["id"],
        "profile": row["profile"],
        "class": row["class"],
        "severity": row["severity"],
        "cost": row.get("cost", "cheap"),
        "status": result.status,
        "what": row["what"],
        "found": result.found,
        "required": result.required,
        "detail": result.detail,
        "composes": result.composes,
        "declared_in": row.get("declared_in"),
        "remedy": {
            "command": remedy["command"],
            "commands": remedy_commands(row, result.missing, found),
            "who": remedy["who"],
            "where": remedy.get("where", "any"),
            "note": remedy.get("note"),
            "doc": remedy.get("doc"),
        },
    }


def legacy_prereqs(report: Report) -> list[dict[str, object]]:
    """The ``prereqs`` array ``init --json`` carried before the profiles: the default profile's software tools."""
    prereqs: list[dict[str, object]] = []
    for result in report.checks:
        row = result.row
        probes = _probes(row)
        if row["profile"] != DEFAULT_PROFILE or row["class"] != "software" or len(probes) != 1:
            continue
        if probes[0]["kind"] != "tool" or "name" not in probes[0]:
            continue
        ok = result.status == OK
        prereqs.append(
            {
                "name": probes[0]["name"],
                "ok": ok,
                "found": result.found,
                "required": result.required,
                "remedy": None if ok else remedy_commands(row, result.missing, report.found)[0],
            }
        )
    return prereqs


def report_payload(report: Report) -> dict[str, object]:
    """The ``--json`` document (stable; contract.md and the package README describe it)."""
    return {
        "ok": report.ok,
        "platform": report.platform,
        "root": str(report.root),
        "data": DATA_REL.as_posix(),
        "profiles": [
            {
                "id": profile.id,
                "chosen": profile.chosen,
                "ready": profile.ready,
                "supported": profile.supported,
                "requires": profile.requires,
                "reason": profile.reason,
                "counts": profile.counts,
                "classes": list(profile.classes),
            }
            for profile in report.profiles
        ],
        "checks": [_check_dict(result, report.found) for result in report.checks],
        "prereqs": legacy_prereqs(report),
    }


def format_report(report: Report) -> str:
    lines = [f"steward init: machine readiness on {report.platform} ({DATA_REL.as_posix()})"]
    for profile in report.profiles:
        lines.append(f"{profile.id} - {profile.title}")
        own = [result for result in report.checks if result.row["profile"] == profile.id]
        if not own:
            lines.append("  (no check of this profile was chosen)")
        for result in own:
            lines.append(f"  {_label(result):<7} {result.id}: {result.detail}")
            if result.status not in (FAIL, BLOCKED):
                continue
            remedy = result.row["remedy"]
            where = (
                "   [from the primary checkout, never a linked worktree]"
                if remedy.get("where") == "primary-checkout"
                else ""
            )
            for command in remedy_commands(result.row, result.missing, report.found):
                lines.append(f"          remedy ({remedy['who']}): {command}{where}")
            if remedy.get("note"):
                lines.append(f"          note: {remedy['note']}")
            if remedy.get("doc"):
                lines.append(f"          see: {remedy['doc']}")
    for profile in report.profiles:
        if profile.chosen:
            verdict = "READY" if profile.ready else "NOT READY"
            qualifiers = [f"{', '.join(profile.classes)} checks only"] if profile.narrowed else []
            qualifiers += [profile.reason] if profile.reason else []
            lines.append(
                f"steward init: {profile.id} {verdict}" + (f" ({'; '.join(qualifiers)})" if qualifiers else "")
            )
    return "\n".join(lines)


def listing_payload(data: Mapping[str, Any], profiles: Sequence[str]) -> dict[str, object]:
    return {
        "data": DATA_REL.as_posix(),
        "profiles": [
            {
                "id": name,
                "title": data["profiles"][name]["title"],
                "requires": list(data["profiles"][name].get("requires") or []),
                "platforms": data["profiles"][name].get("platforms"),
            }
            for name in profiles
        ],
        "checks": [
            {
                "id": row["id"],
                "profile": row["profile"],
                "class": row["class"],
                "severity": row["severity"],
                "cost": row.get("cost", "cheap"),
                "platforms": row.get("platforms"),
                "needs": list(row.get("needs") or []),
                "what": row["what"],
                "probes": [probe["kind"] for probe in _probes(row)],
                "remedy": dict(row["remedy"]),
                "declared_in": row.get("declared_in"),
            }
            for row in data["checks"]
            if row["profile"] in profiles
        ],
    }


def format_listing(data: Mapping[str, Any], profiles: Sequence[str]) -> str:
    lines = [f"steward init --list: {DATA_REL.as_posix()} (nothing is probed)"]
    for name in profiles:
        profile = data["profiles"][name]
        requires = ", ".join(profile.get("requires") or []) or "nothing"
        only = f"; only on {', '.join(profile['platforms'])}" if profile.get("platforms") else ""
        lines.append(f"{name} - {profile['title']} (requires {requires}{only})")
        for row in data["checks"]:
            if row["profile"] != name:
                continue
            tags = [row["class"], row["severity"], *(["deep"] if row.get("cost") == "deep" else [])]
            lines.append(f"  {row['id']} [{', '.join(tags)}]: {row['what']}")
            lines.append(f"          remedy ({row['remedy']['who']}): {row['remedy']['command']}")
    return "\n".join(lines)


def _refusal(message: str, *, as_json: bool, exit_code: int) -> DutyResult:
    summary = json.dumps({"ok": False, "error": message}, indent=2) if as_json else message
    return DutyResult(ok=False, summary=summary, details={"exit_code": exit_code})


def run_init(ns: argparse.Namespace, *, deps: MachineDeps | None = None) -> DutyResult:
    """``steward init``: load the data file, run the chosen profiles' rows, report. Never exits (AD-8)."""
    as_json = bool(getattr(ns, "json", False))
    if deps is None:
        repo = getattr(ns, "repo", None)
        try:
            root = Path(repo).expanduser().resolve() if repo else repo_root()
        except RuntimeError as exc:
            return _refusal(f"init: {exc}", as_json=as_json, exit_code=1)
        deps = production_deps(root)
    try:
        data = load_data(deps.root)
    except DataFileError as exc:
        return _refusal(f"init: {exc}", as_json=as_json, exit_code=EXIT_CANNOT_JUDGE)

    listing = bool(getattr(ns, "list", False))
    asked = list(getattr(ns, "profile", None) or [])
    # Judged before `all` widens the choice, so an unknown name beside `all` is refused, never dropped.
    unknown = list(dict.fromkeys(name for name in asked if name != ALL_PROFILES and name not in data["profiles"]))
    if ALL_PROFILES in asked or (listing and not asked):
        chosen = list(data["profiles"])
    else:
        chosen = list(dict.fromkeys(asked)) or [DEFAULT_PROFILE]
    if unknown:
        known = ", ".join([*data["profiles"], ALL_PROFILES])
        return _refusal(
            f"init: unknown profile {', '.join(unknown)} (profiles: {known})",
            as_json=as_json,
            exit_code=EXIT_UNKNOWN_PROFILE,
        )
    if listing:
        closure = profile_closure(data, chosen)
        summary = json.dumps(listing_payload(data, closure), indent=2) if as_json else format_listing(data, closure)
        return DutyResult(ok=True, summary=summary, details={"listed": closure})

    report = run_checks(
        data,
        deps,
        chosen=chosen,
        classes=getattr(ns, "check_class", None) or None,
        deep=bool(getattr(ns, "deep", False)),
    )
    payload = report_payload(report)
    return DutyResult(
        ok=report.ok,
        summary=json.dumps(payload, indent=2) if as_json else format_report(report),
        # The report is the product, ready or not: it goes to stdout either way, and the exit code carries the verdict.
        details={"summary_stream": "stdout", "prereqs": payload["prereqs"], "profiles": payload["profiles"]},
    )
