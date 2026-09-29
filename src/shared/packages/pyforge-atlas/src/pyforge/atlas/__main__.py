"""pyforge-atlas file for ensuring the package is executable
as `pyforge-atlas` and `python -m pyforge.atlas`
"""

import sys
from typing import Any

from . import __version__


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

    from kedro.framework.cli.utils import find_run_command
    from kedro.framework.project import configure_project

    # PEP 420 namespace package: the Kedro package name is the dotted
    # `pyforge.atlas` (Story A1 AC-7) — derive it from __package__, not the
    # directory name (which would yield the bare "atlas").
    package_name = __package__ or "pyforge.atlas"
    configure_project(package_name)

    interactive = hasattr(sys, "ps1")
    kwargs["standalone_mode"] = not interactive

    run = find_run_command(package_name)
    return run(*args, **kwargs)


if __name__ == "__main__":
    main()
