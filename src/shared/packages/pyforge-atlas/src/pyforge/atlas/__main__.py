"""pyforge-atlas file for ensuring the package is executable
as `pyforge-atlas` and `python -m pyforge.atlas`
"""
import sys
from typing import Any

from kedro.framework.cli.utils import find_run_command
from kedro.framework.project import configure_project


def main(*args, **kwargs) -> Any:
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
