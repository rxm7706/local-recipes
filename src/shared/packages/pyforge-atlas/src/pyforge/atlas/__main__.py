"""pyforge-atlas file for ensuring the package is executable
as `pyforge-atlas` and `python -m pyforge.atlas`
"""

import os
import sys
from pathlib import Path
from typing import Any

from . import __version__

# The member dir (the Kedro project root), the same root the MCP face pins in
# `mcp/session.py`: .../pyforge-atlas/src/pyforge/atlas/__main__.py
#     parents[0]=atlas  [1]=pyforge  [2]=src  [3]=pyforge-atlas
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def discover_cli_verbs() -> frozenset[str]:
    """Return Kedro project command names for ``pyforge.atlas`` at runtime.

    Story 25.3: the atlas CLI⇄tool parity gate derives its verb inventory from
    Kedro's own project command surface — never from a hand-typed list or a
    copied Click group in ``pyforge-core``.
    """
    from kedro.framework.cli.project import project_group
    from kedro.framework.project import configure_project

    package_name = __package__ or "pyforge.atlas"
    configure_project(package_name)
    return frozenset(project_group.commands.keys())


# Epic 42 (spec-feature-flag-governance CAP-7): the switches `run` reads, spelled literally. The MCP face reads the
# same keys in `mcp/tools.py`; both go through `pyforge.core.flags`.
AGENT_PIPELINE_TOOLS_FLAG_KEY = "pyforge.atlas.agent_pipeline_tools"  # CAP-9, Story 42.1
MANIFEST_INVENTORY_FLAG_KEY = "pyforge.atlas.manifest_inventory"  # CAP-13, Story 42.2
MANIFEST_INVENTORY_PIPELINE = "universal_sbom"
EXIT_USAGE = 2  # Click's own usage code: the frozen atlas domain holds, nothing new is minted
RETROFIT_DEFAULT = True


def _retrofit_refusal(cli_args: list[str], project_group: Any) -> str | None:
    """The flag-off message for this invocation, or None; marks `run`'s help when a switch is OFF.

    No tree (``resolve_flags_path`` finds none) reads every switch ON with no read.
    """
    from pyforge.core.cutover_root import resolve_flags_path
    from pyforge.core.flags import disabled_help, read_boolean

    tree = resolve_flags_path()
    if tree is None:
        return None
    wants_help = any(token in {"-h", "--help"} for token in cli_args)
    run_command = project_group.commands.get("run")
    keys = [AGENT_PIPELINE_TOOLS_FLAG_KEY]
    if MANIFEST_INVENTORY_PIPELINE in cli_args:
        keys.append(MANIFEST_INVENTORY_FLAG_KEY)
    if wants_help and run_command is not None:
        text = run_command.get_short_help_str()
        for key in (AGENT_PIPELINE_TOOLS_FLAG_KEY, MANIFEST_INVENTORY_FLAG_KEY):
            text = disabled_help(text, key, RETROFIT_DEFAULT, flags_path=tree)
        run_command.short_help = text
        return None
    if cli_args[:1] != ["run"]:
        return None
    for key in keys:
        if not read_boolean(key, default=RETROFIT_DEFAULT, flags_path=tree):
            return f"flag {key} is off"
    return None


def main(*args, **kwargs) -> Any:
    # Story 7.1: Kedro's own Click-based command routing has no built-in
    # `--version` (`pyforge-atlas --version` exits 2, "no such option") --
    # intercept it here so atlas gets the same `--version` contract every
    # other station CLI already has, without touching Kedro's own command
    # routing otherwise.
    #
    # The Kedro imports live INSIDE this function, below the intercept, on
    # purpose: importing `kedro.framework.project` installs Kedro's rich
    # logging config at import time and prints an INFO banner to STDOUT
    # ("Using '<abs path>/rich_logging.yml' as logging configuration.").
    # At module scope that fired before the intercept could run, so
    # `--version` emitted nine lines -- eight of them a wrapped absolute
    # path from the build host -- instead of the one clean version line
    # every other station prints, and leaked the checkout path of whoever
    # built the image.
    #
    # Arg resolution mirrors the dispatch below, which forwards both
    # positional and keyword args to Click: the console-script entry point
    # (`pyforge-atlas = ...__main__:main`) is invoked bare, so the real args
    # live in `sys.argv[1:]`; an explicit `args[0]` (e.g. `python -m
    # pyforge.atlas` callers passing argv directly) and Click's own
    # `main(args=[...])` keyword form are honored too. An explicit `None` in
    # EITHER position means Click's documented "read sys.argv" -- so both
    # branches test `is not None` rather than truthiness, or `main(None)`
    # would resolve to a `None` argv and silently skip the intercept while
    # `main(args=None)` honored it. Scoped to the FIRST token only -- mirrors
    # marshal's own documented `--version` convention (root-only, wins before
    # anything else claims the rest of parsing) -- so `--version` appearing
    # later among real run flags/values doesn't short-circuit a legitimate
    # invocation.
    if args and args[0] is not None:
        cli_args = args[0]
    elif kwargs.get("args") is not None:
        cli_args = kwargs["args"]
    else:
        cli_args = sys.argv[1:]
    if cli_args and cli_args[0] == "--version":
        print(f"pyforge-atlas {__version__}")
        return None

    from kedro.framework.cli.project import project_group
    from kedro.framework.startup import bootstrap_project

    # Epic 42 (spec-feature-flag-governance CAP-7, Q3): `run` is the CLI face of
    # CAP-9 (Story 42.1) and, with `universal_sbom`, of CAP-13 (Story 42.2). With a
    # switch OFF the verb stays listed in `--help` marked disabled and refuses with
    # exit 2 -- usage, inside the frozen `{0, 1, 2, 130}` domain -- before Kedro runs.
    refusal = _retrofit_refusal(list(cli_args), project_group)
    if refusal is not None:
        print(f"pyforge-atlas: {refusal}", file=sys.stderr)
        return EXIT_USAGE

    # Story 33.1: dispatch to Kedro's project command group (`ipython`,
    # `package`, `run`) -- the group `discover_cli_verbs` reads for the
    # parity gate -- not to the bare `run` command `find_run_command`
    # returns, which made `pyforge atlas run …` an unexpected extra argument.
    # `bootstrap_project` configures the dotted `pyforge.atlas` package from
    # `[tool.kedro]` and hands back the metadata the group's commands take
    # as their Click `obj`. `KedroSession.create` finds its project from the
    # cwd, so the cwd moves to the member dir: from the repo root it would
    # otherwise read the repo root's own `conf/`, not atlas's catalog. The
    # caller's cwd comes back afterwards, so an in-process caller (a test, a
    # REPL) is left where it was.
    metadata = bootstrap_project(PROJECT_ROOT)

    interactive = hasattr(sys, "ps1")
    kwargs["standalone_mode"] = not interactive
    kwargs.setdefault("prog_name", "pyforge-atlas")
    # Always the project's metadata: the group's commands read it as their
    # `obj`, and no caller has another to give.
    kwargs["obj"] = metadata

    caller_cwd = os.getcwd()
    os.chdir(PROJECT_ROOT)
    try:
        return project_group(*args, **kwargs)
    finally:
        os.chdir(caller_cwd)


if __name__ == "__main__":
    main()
