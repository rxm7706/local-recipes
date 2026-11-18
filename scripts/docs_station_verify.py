"""Generator: ``docs/reference/station-verify-commands.md`` from each
station's ``marshal-policy.toml`` (doctor Story 60.2, spec-pyforge-doctor
CAP-84: the seventh reference-page generator, in the Story 30.3 pattern).

One row per ``_bmad-output/projects/pyforge-<station>/planning-artifacts/
marshal-policy.toml``: the station and its top-level ``verify_commands``,
verbatim and in order. Purely mechanical -- ``tomllib`` reads each file; no
station name or command below is typed by hand.

The page was hand-written until this story and cited all eight policy files
as its sources, so it read stale every time any epic was minted: minting
writes that epic's ``[epic_surfaces]`` block into the same file. A generated
page is compared by content, and this one reads ``verify_commands`` only, so
an ``[epic_surfaces]`` edit no longer moves it.

Usage::

    python scripts/docs_station_verify.py            # regenerate + write + stamp
    python scripts/docs_station_verify.py --check     # exit 0 if current, 1 if stale
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docs_gen_common as common

PAGE_REL = "reference/station-verify-commands.md"
GENERATOR_REL = "scripts/docs_station_verify.py"
TASK_NAME = "docs-station-verify"

PROJECTS_REL = "_bmad-output/projects"
POLICY_REL = "planning-artifacts/marshal-policy.toml"
_PROJECT_PREFIX = "pyforge-"
_FROZEN_FLAG = "--frozen"

_INTRO = """\
# Station verify commands

What `marshal factory dispatch` runs to verify each PyForge station's
stories, and the exact string every story spec's `## Verification` →
`**Commands:**` section must declare for that station. Each row is that
station's `verify_commands`, read on each render from its
`_bmad-output/projects/pyforge-<station>/planning-artifacts/marshal-policy.toml`,
which stays the source of truth.

## The two gates this matters for

- **`MRS-GATE-010`**: the story's spec has no `## Verification` →
  `**Commands:**` section, so there is nothing to bind against. A story
  spec carries one before it reaches `marshal factory dispatch`.
- **`MRS-GATE-011`**: the spec declares a command that is not among the
  station's current `verify_commands`. The compare collapses runs of
  whitespace and is otherwise a plain string match, with no argument
  parsing: `pixi run --frozen -e X t` and `pixi run -e X t` are different
  commands. Use the string below verbatim, with or without `--frozen` as
  the row has it.

The binding is one-directional: a policy that runs more commands than a
spec declares is not a finding.
"""

_TEMPLATE = """\
## Template for a new spec's Verification section

One bullet per command in the station's row, same order, verbatim. Keep
each bullet on one line: the parser stops reading the list at the first
line that is not a bullet, so a wrapped bullet hides every command after
it.

```markdown
## Verification

**Commands:**
- `<verbatim command from the table above>` — expected: <what a green run proves for this story>.
```

The `expected:` text is yours to write; only the backtick-quoted command is
compared.

A story spec of `type: feature` also carries a `flag:` block or a
`flag-exempt:` value in its frontmatter; its one shape is
[the story-spec flag block](story-spec-flag-block.md).

## When a station's `verify_commands` changes

Every story spec for that station declares the old string, so in the same
change:

1. Regenerate this page: `pixi run -e pyforge-guild docs-station-verify`.
   `docs-currency` reds a page that no longer matches its policy files.
2. Search that station's story specs for the old command string and
   replace it in each `**Commands:**` bullet, or `MRS-GATE-011` refuses the
   next dispatch of every spec that still names it.
"""


def _policy_paths(root: Path) -> list[Path]:
    """Every station's policy file, sorted by station."""
    projects = root / PROJECTS_REL
    if not projects.is_dir():
        return []
    return sorted(
        path
        for path in projects.glob(f"{_PROJECT_PREFIX}*/{POLICY_REL}")
        if path.is_file()
    )


def _station(policy_path: Path) -> str:
    return policy_path.parent.parent.name.removeprefix(_PROJECT_PREFIX)


def _verify_commands(policy_path: Path) -> list[str]:
    """The file's top-level ``verify_commands``, in order; ``[]`` when the
    key is absent or is not a list of strings."""
    data = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    commands = data.get("verify_commands")
    if not isinstance(commands, list):
        return []
    return [command for command in commands if isinstance(command, str)]


def station_commands(root: Path) -> dict[str, list[str]]:
    """``{station: verify_commands}`` for every policy file under ``root``."""
    return {_station(path): _verify_commands(path) for path in _policy_paths(root)}


def _cell(commands: list[str]) -> str:
    if not commands:
        return "*(none declared)*"
    return "<br>".join("`" + command.replace("|", "\\|") + "`" for command in commands)


def _unfrozen_note(by_station: dict[str, list[str]]) -> list[str]:
    """Names the stations that run a command without ``--frozen`` -- the one
    difference between rows a reader is most likely to "fix" by hand."""
    unfrozen = [
        station
        for station, commands in by_station.items()
        if any(_FROZEN_FLAG not in command.split() for command in commands)
    ]
    if not unfrozen:
        return ["Every command in the table carries `--frozen`.", ""]
    names = ", ".join(f"`{station}`" for station in unfrozen)
    return [
        (
            f"Stations with a command that does not carry `--frozen`: {names} "
            f"({len(unfrozen)} of {len(by_station)}). The flag is part of the "
            "string `MRS-GATE-011` compares, so adding or removing it in a policy "
            "file refuses every story spec of that station that still declares "
            "the old string. Change it only together with those specs."
        ),
        "",
    ]


def render(root: Path, stamp: dict[str, str]) -> str:
    by_station = station_commands(root)

    lines = [
        common.render_header(GENERATOR_REL, TASK_NAME, stamp),
        "",
        _INTRO,
        "## The table",
        "",
        f"{len(by_station)} stations, as of this render.",
        "",
        "| Station | `verify_commands` (verbatim, in order) |",
        "|---|---|",
    ]
    for station, commands in by_station.items():
        lines.append(f"| {station} | {_cell(commands)} |")
    lines.append("")
    lines += _unfrozen_note(by_station)
    lines.append(_TEMPLATE)

    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="report staleness; never write"
    )
    common.configure_root_argument(parser)
    args = parser.parse_args()

    root = common.resolve_root(args)
    stamp, content = common.stamped_render(
        root, PAGE_REL, lambda stamp: render(root, stamp)
    )
    return common.write_generated_page(
        root, PAGE_REL, content, check=args.check, stamp=stamp
    )


if __name__ == "__main__":
    sys.exit(main())
