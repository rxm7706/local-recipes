"""Fleet coverage gates that name the failing module (Story 19.3 / FR-131).

Bare ``--cov-fail-under`` percentages hide *which* module dragged a station
below its floor. This module:

* holds the fleet defaults (unit >80% / integration >70%) and optional
  per-station overrides;
* evaluates a coverage.py JSON report (or an equivalent module→percent map);
* fails naming every module under the suite threshold — never only an
  aggregate percentage;
* discovers which ``pyforge-<station>`` packages a PR touched so CI can gate
  only those packages.

CAP-4 / FR-131: closing individual coverage gaps remains each station's own
story work; this story ships the gate and the named-module failure surface.

Lives at ``scripts/coverage_gate.py``, outside every ``pyforge.<station>``
package (moved from ``pyforge.marshal.coverage_gate`` 2026-09-20, doctor
Story 24.1 / ``docs/governance/spec-coverage-gate-independence/`` CAP-1):
this evaluator can red any station's pull request, including marshal's, so
no station it judges may also govern it or lower its own floor by editing a
file it owns (Charter §6). Its thresholds file is
``docs/governance/coverage-thresholds.toml`` (CAP-2), for the same reason.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Suite = Literal["unit", "integration"]

# Fleet defaults (FR-131 / CAP-4). Per-station overrides live in the thresholds
# TOML; when a station key is absent these defaults apply.
DEFAULT_UNIT_THRESHOLD = 80.0
DEFAULT_INTEGRATION_THRESHOLD = 70.0

# The eight Dream/TEA stations (Story 19.1). ``pyforge-core`` / testing-kit are
# not stations for this gate.
STATIONS: tuple[str, ...] = (
    "atlas",
    "doctor",
    "herald",
    "marshal",
    "mason",
    "scribe",
    "steward",
    "warden",
)

_PACKAGE_PATH_RE = re.compile(r"(?:^|/)src/shared/packages/pyforge-([a-z0-9-]+)/(?:src|tests)(?:/|$)")

_DEFAULT_THRESHOLDS_TOML = """\
# Per-station coverage floors for Story 19.3 / FR-131.
# Suites: unit >80%, integration >70% (fleet defaults).
# Override a station only when documenting a deliberate temporary floor;
# absent station keys inherit [defaults].

[defaults]
unit = 80.0
integration = 70.0
"""


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Unit / integration floors for one station (percent, 0–100)."""

    unit: float = DEFAULT_UNIT_THRESHOLD
    integration: float = DEFAULT_INTEGRATION_THRESHOLD

    def for_suite(self, suite: Suite) -> float:
        if suite == "unit":
            return self.unit
        if suite == "integration":
            return self.integration
        raise ValueError(f"unknown suite: {suite!r}")


@dataclass(frozen=True, slots=True)
class ModuleFailure:
    """One module under its suite threshold."""

    module: str
    percent: float
    threshold: float
    suite: Suite

    def line(self) -> str:
        return f"  - {self.module}: {self.percent:.1f}% (threshold {self.threshold:.0f}% {self.suite})"


def default_thresholds_path() -> Path:
    """Packaged thresholds file beside this module."""
    return Path(__file__).resolve().parent / "coverage_thresholds.toml"


@dataclass(frozen=True)
class ModuleFloor:
    """A deliberate, dated, story-bound floor for ONE module (percent).

    The per-station floor is the rule; a module entry is a named exception a
    Story retires. It can only lower the floor -- an entry above the station
    floor is ignored -- and it must say ``until`` (a date or a story key) and
    ``story`` (the backfill Story that removes it), so debt is never silent.
    Same shape as the per-module mypy baseline (steward Story 66.1).
    """

    module: str
    unit: float | None = None
    integration: float | None = None
    until: str = ""
    story: str = ""

    def for_suite(self, suite: Suite) -> float | None:
        if suite == "unit":
            return self.unit
        if suite == "integration":
            return self.integration
        raise ValueError(f"unknown suite: {suite!r}")


def load_module_floors(path: Path | None = None) -> dict[str, ModuleFloor]:
    """Load ``[modules."<dotted.module>"]`` entries from the thresholds file.

    Every entry needs ``until`` and ``story``; a missing key raises so the
    exception is never an anonymous number.
    """
    raw_path = path if path is not None else default_thresholds_path()
    if not raw_path.is_file():
        return {}
    data = tomllib.loads(raw_path.read_text(encoding="utf-8"))
    table = data.get("modules") or {}
    out: dict[str, ModuleFloor] = {}
    for module, entry in table.items():
        if not isinstance(entry, Mapping):
            raise TypeError(f"modules.{module} must be a table, got {entry!r}")
        until = str(entry.get("until", "")).strip()
        story = str(entry.get("story", "")).strip()
        if not until or not story:
            raise ValueError(f"modules.{module} must carry `until` and `story` -- a floor exception is never anonymous")
        out[module] = ModuleFloor(
            module=module,
            unit=float(entry["unit"]) if "unit" in entry else None,
            integration=float(entry["integration"]) if "integration" in entry else None,
            until=until,
            story=story,
        )
    return out


def floor_for_module(
    module: str,
    station_floor: float,
    *,
    suite: Suite,
    module_floors: Mapping[str, ModuleFloor],
) -> float:
    """The floor one module is held to: the station floor, or a lower named exception."""
    entry = module_floors.get(module)
    if entry is None:
        return station_floor
    own = entry.for_suite(suite)
    if own is None or own >= station_floor:
        return station_floor
    return own


def load_thresholds(path: Path | None = None) -> dict[str, Thresholds]:
    """Load ``[defaults]`` + optional ``[stations.<slug>]`` overrides.

    Returns a map keyed by station slug; every known station is present,
    inheriting defaults when not overridden. The empty-string key holds the
    fleet defaults.
    """
    raw_path = path if path is not None else default_thresholds_path()
    if raw_path.is_file():
        data = tomllib.loads(raw_path.read_text(encoding="utf-8"))
    else:
        data = tomllib.loads(_DEFAULT_THRESHOLDS_TOML)

    defaults_table = data.get("defaults") or {}
    defaults = Thresholds(
        unit=float(defaults_table.get("unit", DEFAULT_UNIT_THRESHOLD)),
        integration=float(defaults_table.get("integration", DEFAULT_INTEGRATION_THRESHOLD)),
    )
    stations_table = data.get("stations") or {}
    out: dict[str, Thresholds] = {"": defaults}
    for slug in STATIONS:
        override = stations_table.get(slug) or {}
        if not isinstance(override, Mapping):
            raise TypeError(f"stations.{slug} must be a table, got {override!r}")
        out[slug] = Thresholds(
            unit=float(override.get("unit", defaults.unit)),
            integration=float(override.get("integration", defaults.integration)),
        )
    for slug, override in stations_table.items():
        if slug in out or not isinstance(override, Mapping):
            continue
        out[str(slug)] = Thresholds(
            unit=float(override.get("unit", defaults.unit)),
            integration=float(override.get("integration", defaults.integration)),
        )
    return out


def thresholds_for(
    station: str,
    *,
    path: Path | None = None,
) -> Thresholds:
    """Thresholds for ``station`` (fleet defaults when unknown)."""
    table = load_thresholds(path)
    if station in table:
        return table[station]
    return table[""]


def module_percents_from_coverage_json(
    payload: Mapping[str, Any],
) -> dict[str, float]:
    """Extract ``module → percent_covered`` from a coverage.py JSON report.

    Accepts the standard ``coverage json`` shape (``files`` map with
    ``summary.percent_covered``) or a flat ``{module: percent}`` map for
    fixtures.
    """
    files = payload.get("files")
    if isinstance(files, Mapping):
        out: dict[str, float] = {}
        for key, meta in files.items():
            if not isinstance(meta, Mapping):
                continue
            summary = meta.get("summary")
            if isinstance(summary, Mapping) and "percent_covered" in summary:
                pct = float(summary["percent_covered"])
            elif "percent_covered" in meta:
                pct = float(meta["percent_covered"])
            else:
                continue
            out[_module_label(str(key))] = pct
        return out

    # Flat fixture map: {"pkg.mod": 72.5, ...}
    out = {}
    for key, value in payload.items():
        if key in {"meta", "totals", "files"}:
            continue
        if isinstance(value, (int, float)):
            out[_module_label(str(key))] = float(value)
    return out


def _module_label(path_or_mod: str) -> str:
    """Prefer a dotted module path; fall back to the given string."""
    text = path_or_mod.replace("\\", "/")
    marker = "/site-packages/"
    if marker in text:
        text = text.split(marker, 1)[1]
    if text.endswith(".py"):
        text = text[: -len(".py")]
    if "/pyforge/" in text:
        text = "pyforge/" + text.split("/pyforge/", 1)[1]
    return text.replace("/", ".")


def modules_below_threshold(
    percents: Mapping[str, float],
    threshold: float,
    *,
    suite: Suite,
    module_floors: Mapping[str, ModuleFloor] | None = None,
) -> list[ModuleFailure]:
    """Return every module whose coverage is strictly below its floor.

    ``threshold`` is the station floor; ``module_floors`` may lower it for
    a named module (a dated, story-bound exception) -- never raise it.
    """
    floors = module_floors or {}
    out: list[ModuleFailure] = []
    for name, pct in sorted(percents.items()):
        floor = floor_for_module(name, float(threshold), suite=suite, module_floors=floors)
        if float(pct) < floor:
            out.append(ModuleFailure(module=name, percent=float(pct), threshold=floor, suite=suite))
    return out


def format_failure_message(
    failures: Sequence[ModuleFailure],
    *,
    station: str,
    suite: Suite,
    threshold: float,
    percents: Mapping[str, float] | None = None,
) -> str:
    """Render a failure that *names* each under-threshold module (FR-131)."""
    lines = [
        (
            f"coverage gate FAILED for pyforge-{station} {suite} "
            f"(threshold {threshold:.0f}%): "
            f"{len(failures)} under-threshold module(s)"
        ),
        "under-threshold modules:",
        *[f.line() for f in failures],
    ]
    # Aggregate may appear only *alongside* named modules — never alone.
    if percents:
        total = sum(percents.values()) / len(percents)
        lines.append(
            f"aggregate mean across measured modules: {total:.1f}% (not a substitute for the named modules above)"
        )
    return "\n".join(lines)


def evaluate_suite(
    percents: Mapping[str, float],
    *,
    suite: Suite,
    threshold: float,
    station: str,
    module_floors: Mapping[str, ModuleFloor] | None = None,
) -> tuple[bool, str]:
    """Evaluate one suite; on failure the message names under-threshold modules.

    Returns ``(ok, message)``. ``ok`` is True when every module meets the
    floor (or there are no measured modules).
    """
    failures = modules_below_threshold(percents, threshold, suite=suite, module_floors=module_floors)
    if not failures:
        measured = len(percents)
        excepted = [
            f"{name} ({float(pct):.1f}% ≥ {floor_for_module(name, threshold, suite=suite, module_floors=module_floors):.0f}%, "
            f"until {module_floors[name].until}, {module_floors[name].story})"
            for name, pct in sorted(percents.items())
            if module_floors and name in module_floors and float(pct) < float(threshold)
        ]
        note = f"; {len(excepted)} under a dated exception: " + "; ".join(excepted) if excepted else ""
        return (
            True,
            (f"coverage gate OK for pyforge-{station} {suite}: {measured} module(s) ≥ {threshold:.0f}%{note}"),
        )
    return False, format_failure_message(
        failures,
        station=station,
        suite=suite,
        threshold=threshold,
        percents=percents,
    )


def touched_stations(paths: Iterable[str]) -> frozenset[str]:
    """Return station slugs whose package ``src/`` or ``tests/`` was touched."""
    found: set[str] = set()
    for raw in paths:
        match = _PACKAGE_PATH_RE.search(raw.replace("\\", "/"))
        if not match:
            continue
        slug = match.group(1)
        if slug in STATIONS:
            found.add(slug)
    return frozenset(found)


_SRC_MODULE_RE = re.compile(
    r"(?:^|/)src/shared/packages/pyforge-([a-z0-9-]+)/"
    r"src/(pyforge/\1/.+)\.py$"
)


def touched_source_modules(paths: Iterable[str]) -> frozenset[str]:
    """Dotted module names for touched package *source* files (not tests).

    CI uses this so a PR fails naming the modules it changed that sit below
    the station floor — without forcing every historical uncovered module to
    block unrelated edits (CAP-4 non-goal: no fleet-wide test-writing campaign
    in this story). Package-wide evaluate (pixi ``*-test-coverage``) still
    names every under-threshold module.
    """
    found: set[str] = set()
    for raw in paths:
        text = raw.replace("\\", "/")
        match = _SRC_MODULE_RE.search(text)
        if not match:
            continue
        slug = match.group(1)
        if slug not in STATIONS:
            continue
        rel = match.group(2)  # pyforge/<slug>/...
        if rel.endswith("/__init__"):
            rel = rel[: -len("/__init__")]
        found.add(rel.replace("/", "."))
    return frozenset(found)


def ast_fingerprint(source: str) -> str | None:
    """A formatting-insensitive fingerprint of one Python source.

    The ``ast.dump`` of the module after two normalisations: every ``import``
    statement is dropped (at any nesting) and every docstring is dropped.
    That makes the fingerprint invariant under exactly what a lint/format
    landing changes -- ``ruff format`` (quotes, wrapping, trailing commas,
    docstring indentation, PEP 758 ``except A, B:``), ``I001`` import sorting
    and merging, ``F401`` unused-import removal, a type-only import under
    ``TYPE_CHECKING`` -- none of which carries behaviour a coverage floor
    should demand a test for. Any other statement-level change (a renamed
    variable, a removed assignment, a new branch) moves it. ``None`` when the
    source does not parse, so a caller treats an unparseable file as changed.

    Steward Story 66.1 (2026-09-20): the first fleet-wide reformat made every
    module "touched" by the name-only diff, and the touched-module coverage
    floor measured the whole fleet at once. A gate that fires on formatting
    measures the formatter, not the code.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    def normalise(body: list[ast.stmt]) -> list[ast.stmt]:
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]
        return [s for s in body if not isinstance(s, (ast.Import, ast.ImportFrom))]

    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            value = getattr(node, field, None)
            if isinstance(value, list) and value and all(isinstance(s, ast.stmt) for s in value):
                setattr(node, field, normalise(value))
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                handler.body = normalise(handler.body)
    return ast.dump(tree, include_attributes=False)


def format_only_paths(pairs: Mapping[str, tuple[str | None, str | None]]) -> frozenset[str]:
    """Paths whose base and head sources share an :func:`ast_fingerprint`.

    ``pairs`` maps a repo-relative path to ``(base_source, head_source)``;
    a missing side (``None``: added or deleted file) or an unparseable side
    is never format-only.
    """
    out: set[str] = set()
    for path, (base, head) in pairs.items():
        if base is None or head is None:
            continue
        fb, fh = ast_fingerprint(base), ast_fingerprint(head)
        if fb is not None and fb == fh:
            out.add(path)
    return frozenset(out)


def filter_percents(
    percents: Mapping[str, float],
    modules: Iterable[str],
) -> dict[str, float]:
    """Keep only entries whose module is in ``modules`` (exact or prefix)."""
    wanted = set(modules)
    if not wanted:
        return {}
    out: dict[str, float] = {}
    for name, pct in percents.items():
        if name in wanted or any(name == m or name.startswith(m + ".") for m in wanted):
            out[name] = float(pct)
    return out


def package_root(repo_root: Path, station: str) -> Path:
    return repo_root / "src" / "shared" / "packages" / f"pyforge-{station}"


def package_src(repo_root: Path, station: str) -> Path:
    return package_root(repo_root, station) / "src" / "pyforge" / station


def evaluate_coverage_payload(
    payload: Mapping[str, Any],
    *,
    station: str,
    suite: Suite,
    thresholds_path: Path | None = None,
    only_modules: Iterable[str] | None = None,
) -> tuple[bool, str]:
    """Evaluate a coverage JSON payload for one station suite.

    When ``only_modules`` is set, only those modules are gated (CI touched-
    source mode). When omitted, every measured module is gated (full package
    mode / pixi ``*-test-coverage``).
    """
    thr = thresholds_for(station, path=thresholds_path).for_suite(suite)
    percents = module_percents_from_coverage_json(payload)
    if only_modules is not None:
        wanted = [m for m in only_modules if m]
        # Touched-module mode: gate only modules that this suite actually
        # measured. Absent modules are N/A for the suite (e.g. unit-only
        # code never imported by integration) — do not zero-fill them.
        percents = filter_percents(percents, wanted)
    floors = load_module_floors(thresholds_path)
    return evaluate_suite(percents, suite=suite, threshold=thr, station=station, module_floors=floors)


def _cmd_evaluate(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.coverage_json).read_text(encoding="utf-8"))
    only: list[str] | None = None
    if args.only_modules_file:
        if args.only_modules_file == "-":
            only = [line.strip() for line in sys.stdin if line.strip()]
        else:
            only = [
                line.strip()
                for line in Path(args.only_modules_file).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
    ok, message = evaluate_coverage_payload(
        payload,
        station=args.station,
        suite=args.suite,
        thresholds_path=Path(args.thresholds) if args.thresholds else None,
        only_modules=only,
    )
    print(message)
    return 0 if ok else 1


def _cmd_touched(args: argparse.Namespace) -> int:
    if args.paths_file == "-":
        paths = [line.strip() for line in sys.stdin if line.strip()]
    else:
        paths = [
            line.strip() for line in Path(args.paths_file).read_text(encoding="utf-8").splitlines() if line.strip()
        ]
    stations = sorted(touched_stations(paths))
    modules = sorted(touched_source_modules(paths)) if args.modules else []
    if args.json_out:
        payload: dict[str, Any] = {"stations": stations}
        if args.modules:
            payload["modules"] = modules
        json.dump(payload, sys.stdout)
        sys.stdout.write("\n")
    elif args.modules:
        for name in modules:
            print(name)
    else:
        for slug in stations:
            print(slug)
    return 0


def _cmd_show_thresholds(args: argparse.Namespace) -> int:
    path = Path(args.thresholds) if args.thresholds else None
    table = load_thresholds(path)
    defaults = table[""]
    print(f"defaults: unit={defaults.unit:.0f} integration={defaults.integration:.0f}")
    for slug in STATIONS:
        thr = table[slug]
        print(f"  {slug}: unit={thr.unit:.0f} integration={thr.integration:.0f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pyforge.marshal.coverage_gate",
        description=("Coverage gates that name uncovered modules (Story 19.3 / FR-131)."),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser(
        "evaluate",
        help="Evaluate a coverage.py JSON report; fail naming modules under threshold",
    )
    evaluate.add_argument("--station", required=True, help="Station slug (e.g. marshal)")
    evaluate.add_argument(
        "--suite",
        required=True,
        choices=("unit", "integration"),
        help="Which threshold floor to apply",
    )
    evaluate.add_argument(
        "--coverage-json",
        required=True,
        help="Path to coverage.py JSON report (or flat module→percent fixture JSON)",
    )
    evaluate.add_argument(
        "--thresholds",
        default=None,
        help="Optional thresholds TOML (defaults to packaged coverage_thresholds.toml)",
    )
    evaluate.add_argument(
        "--only-modules-file",
        default=None,
        help=(
            "Optional file of dotted module names to gate (one per line); "
            "'-' = stdin. When set, only those modules are checked (CI "
            "touched-source mode). When omitted, every measured module is gated."
        ),
    )
    evaluate.set_defaults(func=_cmd_evaluate)

    touched = sub.add_parser(
        "touched",
        help="List station slugs touched by a path list (CI path filter)",
    )
    touched.add_argument(
        "--paths-file",
        default="-",
        help="File of changed paths (one per line); '-' = stdin",
    )
    touched.add_argument(
        "--json-out",
        action="store_true",
        help='Emit {"stations": [...]} JSON',
    )
    touched.add_argument(
        "--modules",
        action="store_true",
        help="Also list touched source module names (dotted)",
    )
    touched.set_defaults(func=_cmd_touched)

    show = sub.add_parser("show-thresholds", help="Print effective per-station floors")
    show.add_argument("--thresholds", default=None)
    show.set_defaults(func=_cmd_show_thresholds)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
