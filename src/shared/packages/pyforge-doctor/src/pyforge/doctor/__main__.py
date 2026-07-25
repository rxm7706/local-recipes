"""The ``doctor`` console-script entry point (Story 1.1 scaffold stub).

Only ``--version``/``--help`` are wired — no ``check``/``monitor``/
``diagnose`` subcommand dispatch yet (that lands story-by-story per the
architecture spine's Structural Seed). ``main`` always RETURNS an int; it
never calls an exit primitive itself (``verdict.py`` is the sole module
permitted to do that — the sole-ownership meta-test enforces it), so any
``if __name__ == "__main__":`` guard must wrap the call in
``raise SystemExit(main())`` rather than embed a literal exit code.
"""

from __future__ import annotations

import argparse
import sys

from .verdict import EXIT_SIGINT

# Scaffold stage (Story 1.1): __init__.py stays empty (no __version__
# constant — see models.py's module docstring for the taxonomy rationale),
# so the version string duplicates pyproject.toml's version literal here
# instead. Acceptable at scaffold stage; keep the two in sync by hand.
__version__ = "0.1.0"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doctor",
        description=(
            "Pre-flight + fleet-watch diagnostics for the pyforge factory "
            "(scaffold stage: no check/monitor/diagnose verbs yet)."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and return an exit code — never raises ``SystemExit``
    itself. Exit codes stay inside Doctor's frozen ``{0, 2, 130}`` domain
    (AD-2): argparse's own ``--version``/``--help`` exits (``0``) and usage
    errors (``2``) are caught and returned as plain ints, and a
    ``KeyboardInterrupt`` during parsing returns the SIGINT constant.
    """
    if argv is None:
        argv = sys.argv[1:]
    parser = _build_parser()
    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits itself: --version/--help -> 0, a usage error -> 2
        # (never 0). Surface its code as a return value, never re-raised —
        # a non-int code (argparse never produces one under this parser
        # config) falls back to 2, still inside the guarded domain.
        if exc.code is None:
            return 0
        if isinstance(exc.code, int) and exc.code in {0, 2, 130}:
            return exc.code
        # Any other int (or non-int, e.g. a message string) is clamped to 2
        # -- defense in depth for a future argparse action that might exit
        # with something outside Doctor's frozen {0, 2, 130} domain (AD-2).
        return 2
    except KeyboardInterrupt:
        return EXIT_SIGINT
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
