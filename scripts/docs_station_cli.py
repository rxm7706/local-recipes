#!/usr/bin/env python3
"""Generator: ``docs/reference/station-cheat-sheet.md`` from each PyForge
station's own ``pyproject.toml`` ``[project.scripts]`` entry, its live
``--help`` text, and whether ``pixi.toml``'s ``feature.pyforge-guild``
composes it (Story 30.3, spec-pyforge-doctor CAP-84).

The hand-written predecessor had already drifted on exactly this last
point: it claimed "herald ... installed only in its own `pyforge-herald`
environment", but `pixi.toml`'s `feature.pyforge-guild.dependencies` has
carried `pyforge-herald` as a path dependency since Story 63.6 -- this
generator reads that table directly instead of repeating the claim.

Scope, deliberately (recorded here, not silently -- mirrors
``docs_currency.py``'s own "Design deviation" precedent): this script's own
pixi task (``docs-station-cli``) is registered under ``guild-tasks``, so it
is only ever meant to run under ``-e pyforge-guild`` -- the environment
that carries `doctor`/`herald`/`marshal`/`scribe`/`steward` directly.
Rather than shelling out across three OTHER heavy, possibly-uninstalled
pixi environments (`pyforge-atlas`, `pyforge-mason`, `pyforge-warden`) to
capture their `--help` too -- slow, and a real risk of `detectors-ci`
hanging or failing to install an environment it doesn't need for anything
else -- a station not importable via `shutil.which` in the CURRENT process
gets a short, honest, deterministic note instead of a captured `--help`
block. This is itself a mechanical, tree-derived fact (whether the console
script resolves on PATH right now), never a guess.

Usage::

    python scripts/docs_station_cli.py            # regenerate + write + stamp
    python scripts/docs_station_cli.py --check     # exit 0 if current, 1 if stale
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docs_gen_common as common  # noqa: E402

PAGE_REL = "reference/station-cheat-sheet.md"
GENERATOR_REL = "scripts/docs_station_cli.py"
TASK_NAME = "docs-station-cli"
STATIONS_DIR = "src/shared/packages"

# Packages under src/shared/packages/pyforge-* that are NOT a station CLI in
# this cheat sheet's sense: pyforge-core ships the `pyforge` router itself
# (mentioned once in the intro, not as a per-station row) and
# pyforge-testing-kit ships no console script at all.
_EXCLUDED_PACKAGES = frozenset({"pyforge-core", "pyforge-testing-kit"})

_INTRO = """\
# PyForge Station Cheat Sheet

Quick lookup for every PyForge station's own console script: which package
declares it, which environment(s) carry it, and (when captured from the
CURRENT environment -- see this generator's own docstring for why the other
three are noted rather than captured) its live `--help` text.

The `pyforge` router (`pyforge-core`'s own console script,
`pyforge.core.dispatch:main`) fronts every station as `pyforge <station>
<args>`; each station also ships its own direct console script, listed
below.
"""

_INVARIANTS = """\
## Universal Station Invariants

1. **Tests:** Station-specific tests live in
   `src/shared/packages/pyforge-<station>/tests/{unit,meta,integration,fixtures}/`
   (every station has `unit/` and `meta/`; only some have `integration/`).
   Run them with `pixi run -e pyforge-<station> pyforge-<station>-test`, or
   all stations at once with `pixi run -e pyforge-guild pyforge-station-tests`.
2. **Dashboard Isolation:** Django lives only behind the `[dashboard]`
   extra, in `src/shared/packages/pyforge-<station>/src/pyforge/<station>/dashboard/`.
   The core station logic must never import Django at the module level, and
   the base package must run its CLI without the extra installed.
3. **Verdict Projection:** A station that projects an exit-code verdict
   implements a `verdict.py` module; a station whose report is externally
   consumed also ships a frozen JSON schema for it under
   `src/pyforge/<station>/data/report-schema.json`.
"""


def _station_packages(root: Path) -> list[Path]:
    return sorted(
        p
        for p in (root / STATIONS_DIR).glob("pyforge-*")
        if p.is_dir() and p.name not in _EXCLUDED_PACKAGES
    )


def _console_scripts(pyproject: Path) -> dict[str, str]:
    if not pyproject.is_file():
        return {}
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return dict(data.get("project", {}).get("scripts", {}))


def _guild_hosted_packages(root: Path) -> set[str]:
    data = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    deps = data.get("feature", {}).get("pyforge-guild", {}).get("dependencies", {})
    return {name for name, spec in deps.items() if isinstance(spec, dict) and "path" in spec}


def capture_help(console_script: str) -> str | None:
    """``<console_script> --help`` from whatever is on PATH in the CURRENT
    process, or ``None`` when it does not resolve here. A thin, isolated
    seam (never inlined into ``render``) so a test can monkeypatch it
    without touching the real PATH or spawning a real subprocess."""
    resolved = shutil.which(console_script)
    if resolved is None:
        return None
    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    env["COLUMNS"] = "100"  # deterministic argparse/click wrapping regardless of caller's terminal
    try:
        result = subprocess.run(
            [resolved, "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return result.stdout or result.stderr


def render(root: Path, stamp: dict[str, str], *, help_capture=capture_help) -> str:
    guild_hosted = _guild_hosted_packages(root)
    packages = _station_packages(root)

    lines = [common.render_header(GENERATOR_REL, TASK_NAME, stamp), "", _INTRO]

    for package_dir in packages:
        station = package_dir.name.removeprefix("pyforge-")
        display = station.capitalize()
        scripts = _console_scripts(package_dir / "pyproject.toml")
        host_env = "pyforge-guild" if package_dir.name in guild_hosted else package_dir.name

        lines.append(f"## {display}")
        lines.append("")
        lines.append(f"Package: `{package_dir.name}` -- Environment: `{host_env}`")
        lines.append("")
        if not scripts:
            lines.append("*(no console script declared)*")
            lines.append("")
            continue
        for script_name in sorted(scripts):
            help_text = help_capture(script_name)
            lines.append(f"`{script_name} --help`:")
            lines.append("")
            if help_text is None:
                lines.append(
                    f"_not resolvable on PATH in this generator's own environment -- run "
                    f"`pixi run -e {host_env} {script_name} --help` directly._"
                )
            else:
                lines.append("```text")
                lines.append(help_text.rstrip("\n"))
                lines.append("```")
            lines.append("")

    lines.append(_INVARIANTS)

    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report staleness; never write")
    args = parser.parse_args()

    stamp = common.head_stamp(common.REPO_ROOT)
    content = render(common.REPO_ROOT, stamp)
    return common.write_generated_page(common.REPO_ROOT, PAGE_REL, content, check=args.check, stamp=stamp)


if __name__ == "__main__":
    sys.exit(main())
