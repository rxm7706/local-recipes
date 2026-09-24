"""pyforge.core.dispatch -- unified ``pyforge <station> <noun> <verb>``
front door (Story 22.1, FR-13, canopy AD-14).

Dispatch only: map the station token to that distribution's primary console
script and forward the remaining argv through ``PosixProcess``. Station
duty logic stays in the station packages.
"""

from __future__ import annotations

import sys
import tomllib
from collections.abc import Mapping, Sequence
from importlib.metadata import PackageNotFoundError, distribution, distributions
from pathlib import Path

from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

EXIT_USAGE = 2
EXIT_NOT_FOUND = 127

SKIP_DISTRIBUTIONS = frozenset({"pyforge-core", "pyforge-testing-kit"})

# Stations whose CLI cannot be AST-introspected. Values are tracked story
# spec stems under each owning station's planning-artifacts/specs/. A station
# with neither verbs nor an entry here is a silent skip -- CI must fail.
PREPARATORY_UNINTROSPECTABLE: dict[str, str] = {
    # Atlas story 24.3 (ledger key 24-3-…); was mistyped as 25-3 and broke
    # pip-install's parity-matrix gate when the prep-spec path 404'd.
    "atlas": "spec-24-3-atlas-s-mcp-tools-pass-the-cli-tool-parity-gate",
}

# Bare-noun aliases (marshal Story 46.1, spec-pyforge-marshal CAP-192): a
# token that is NOT a station but names a noun one station owns. The noun is
# forwarded, not consumed, so ``pyforge context bootstrap`` runs
# ``marshal context bootstrap``. Consulted only after the token failed to
# resolve as a real station -- a station of the same name always wins.
NOUN_ALIASES: dict[str, str] = {
    "context": "marshal",
}


class DispatchError(PyforgeError):
    """Unknown station token or missing primary console script."""


def station_token_from_dist_name(dist_name: str) -> str:
    name = dist_name.lower()
    if name.startswith("pyforge-"):
        return name[len("pyforge-") :]
    return name


def primary_console_script(dist_name: str, scripts: Mapping[str, str]) -> str | None:
    """Pick the station console script, never a sibling ``*-mcp`` extra."""
    token = station_token_from_dist_name(dist_name)
    if token in scripts:
        return token
    if dist_name in scripts:
        return dist_name
    for name in sorted(scripts):
        if not name.endswith("-mcp"):
            return name
    return None


def scripts_from_pyproject(path: Path) -> dict[str, str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project") or {}
    raw = project.get("scripts") or {}
    return {str(k): str(v) for k, v in raw.items()}


def script_map_from_packages_root(packages_root: Path) -> dict[str, str]:
    """Build station-token → primary script from sibling ``pyproject.toml``."""
    mapping: dict[str, str] = {}
    for child in sorted(packages_root.iterdir()):
        if not child.is_dir() or not child.name.startswith("pyforge-"):
            continue
        if child.name in SKIP_DISTRIBUTIONS:
            continue
        pyproject = child / "pyproject.toml"
        if not pyproject.is_file():
            continue
        scripts = scripts_from_pyproject(pyproject)
        primary = primary_console_script(child.name, scripts)
        if primary is None:
            continue
        mapping[station_token_from_dist_name(child.name)] = primary
    return mapping


def script_map_from_installed() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for dist in distributions():
        name = (dist.metadata["Name"] or "").lower()
        if not name.startswith("pyforge-") or name in SKIP_DISTRIBUTIONS:
            continue
        scripts = {ep.name: ep.value for ep in dist.entry_points if ep.group == "console_scripts"}
        primary = primary_console_script(name, scripts)
        if primary is None:
            continue
        mapping[station_token_from_dist_name(name)] = primary
    return mapping


def resolve_script_map(
    script_map: Mapping[str, str] | None = None,
    *,
    packages_root: Path | None = None,
) -> dict[str, str]:
    if script_map is not None:
        return dict(script_map)
    if packages_root is not None:
        return script_map_from_packages_root(packages_root)
    installed = script_map_from_installed()
    if installed:
        return installed
    # Editable/source checkouts may not expose sibling dists; fall back to
    # the packages tree next to this leaf so local `pyforge` still maps.
    inferred = Path(__file__).resolve().parents[4]
    if inferred.name == "packages":
        return script_map_from_packages_root(inferred)
    return {}


def dispatch_argv(
    argv: Sequence[str],
    *,
    script_map: Mapping[str, str] | None = None,
    packages_root: Path | None = None,
) -> list[str]:
    """Translate ``pyforge <station> <rest…>`` into ``<script> <rest…>``."""
    mapping = resolve_script_map(script_map, packages_root=packages_root)
    if len(argv) < 2 or argv[1] in {"-h", "--help"}:
        known = ", ".join(sorted(mapping)) or "(none installed)"
        raise DispatchError(f"usage: pyforge <station> <noun> <verb> [args...]\nstations: {known}")
    station = argv[1]
    if station.startswith("-"):
        raise DispatchError(f"unknown option {station!r}; usage: pyforge <station> <noun> <verb>")
    primary = _resolve_primary(station, mapping)
    if primary is not None:
        return [primary, *list(argv[2:])]
    owner = NOUN_ALIASES.get(station)
    if owner is not None:
        aliased = _resolve_primary(owner, mapping)
        if aliased is not None:
            return [aliased, *list(argv[1:])]
    known = ", ".join(sorted(mapping)) or "(none installed)"
    raise DispatchError(f"unknown station {station!r}; known: {known}")


def _resolve_primary(station: str, mapping: Mapping[str, str]) -> str | None:
    """The station's primary console script, or ``None`` when it is unknown."""
    primary = mapping.get(station)
    if primary is not None:
        return primary
    # Installed metadata can miss a checkout-only station; try the named dist
    # before declaring unknown.
    try:
        dist = distribution(f"pyforge-{station}")
    except PackageNotFoundError:
        return None
    scripts = {ep.name: ep.value for ep in dist.entry_points if ep.group == "console_scripts"}
    return primary_console_script(f"pyforge-{station}", scripts)


def main(
    argv: Sequence[str] | None = None,
    *,
    process: ProcessPort | None = None,
    script_map: Mapping[str, str] | None = None,
    packages_root: Path | None = None,
    cwd: Path | None = None,
) -> int:
    args = list(sys.argv if argv is None else argv)
    runner = process if process is not None else PosixProcess()
    workdir = cwd if cwd is not None else Path.cwd()
    try:
        child = dispatch_argv(args, script_map=script_map, packages_root=packages_root)
    except DispatchError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    try:
        result = runner.run(child, cwd=workdir)
    except ProcessError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_NOT_FOUND
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
