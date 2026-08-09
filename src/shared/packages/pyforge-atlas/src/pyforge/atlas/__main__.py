"""pyforge-atlas file for ensuring the package is executable
as `pyforge-atlas` and `python -m pyforge.atlas`
"""
import sys
from typing import Any

from kedro.framework.cli.utils import find_run_command
from kedro.framework.project import configure_project

from . import __version__


def main(*args, **kwargs) -> Any:
    # Story 7.1: Kedro's own Click-based command routing has no built-in
    # `--version` (`pyforge-atlas --version` exits 2, "no such option") --
    # intercept it here, before `configure_project`/`find_run_command` run,
    # so atlas gets the same `--version` contract every other station CLI
    # already has, without touching Kedro's own command routing otherwise.
    # The console-script entry point (`pyforge-atlas = ...__main__:main`) is
    # invoked bare, so the real args live in `sys.argv[1:]`; an explicit
    # `args[0]` (e.g. `python -m pyforge.atlas` callers passing argv directly)
    # is honored too. Scoped to the FIRST token only -- mirrors marshal's own
    # documented `--version` convention (root-only, wins before anything else
    # claims the rest of parsing) -- so `--version` appearing later among
    # real run flags/values doesn't short-circuit a legitimate invocation.
    cli_args = args[0] if args else sys.argv[1:]
    if cli_args and cli_args[0] == "--version":
        print(f"pyforge-atlas {__version__}")
        return None

    # PEP 420 namespace package: the Kedro package name is the dotted
    # `pyforge.atlas` (Story A1 AC-7) — derive it from __package__, not the
    # directory name (which would yield the bare "atlas").
    package_name = __package__ or "pyforge.atlas"
    configure_project(package_name)

    interactive = hasattr(sys, 'ps1')
    kwargs["standalone_mode"] = not interactive

    run = find_run_command(package_name)
    return run(*args, **kwargs)


if __name__ == "__main__":
    main()
