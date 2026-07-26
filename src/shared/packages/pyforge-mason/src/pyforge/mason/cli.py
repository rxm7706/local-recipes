"""Mason's command surface.

Story 1.1 wires the dispatcher and `--version` only. The three verb groups are
declared now because the seam is a **capability** decision, not an
implementation one (chain decision D-1, "Option C"):

* ``recipe``       — WRAPS the conda-forge-expert craft by subprocess. The skill
                     stays canonical for recipe semantics and keeps improving
                     through the Rule-2 retro loop. Never forked: a fork is
                     structurally adversarial, because Rule 2 mandates that every
                     conda-forge effort *edits the skill*.
* ``package``      — built natively; no wheel-build/upload path exists to wrap.
* ``environment``  — built natively; no lock orchestration exists to wrap.

argparse, not click/typer: FR-41 forbids a CLI-framework dependency, and the
sibling stations dispatch the same way.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__

# main() is the sole owner of the process exit code. A verb never calls
# sys.exit() directly; it returns an int and main() projects it.
EXIT_OK = 0
EXIT_USAGE = 2          # argparse's own convention, preserved
EXIT_INTERRUPTED = 130  # 128 + SIGINT, the shell convention
EXIT_INTERNAL = 70      # EX_SOFTWARE — never the bare interpreter default of 1

_VERBS = {
    "recipe": "author, validate and build conda recipes (wraps the conda-forge-expert craft)",
    "package": "build and ship distributions to PyPI and conda-forge",
    "environment": "resolve conflicting worlds into one lockfile",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mason",
        description="Mason — forge the blocks, bind the environment, ship the structure.",
    )
    parser.add_argument("--version", action="version", version=f"mason {__version__}")
    subs = parser.add_subparsers(dest="verb", metavar="{" + ",".join(_VERBS) + "}")
    for name, help_text in _VERBS.items():
        # No verbs beneath these yet — Story 1.1 is build wiring only. They are
        # declared so `mason --help` states the whole surface from the start.
        subs.add_parser(name, help=help_text, description=help_text)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        # build_parser() is INSIDE the try deliberately: a KeyboardInterrupt (or
        # any failure) during parser construction must project like every other
        # exit, not escape as a traceback. Caught by tests/unit/test_cli.py.
        parser = build_parser()
        ns = parser.parse_args(argv)
        if not ns.verb:
            parser.print_help()
            return EXIT_OK
        print(f"mason {ns.verb}: not implemented yet (Story 1.1 is build wiring only)",
              file=sys.stderr)
        return EXIT_OK
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except SystemExit as exc:
        # argparse raises SystemExit for --help/--version/usage errors. Those are
        # legitimate; anything else is projected rather than trusted verbatim.
        code = exc.code
        if code is None:
            return EXIT_OK
        return code if isinstance(code, int) else EXIT_USAGE
    except Exception:                              # noqa: BLE001 — deliberate boundary
        import traceback
        traceback.print_exc()
        return EXIT_INTERNAL


if __name__ == "__main__":                          # pragma: no cover
    raise SystemExit(main())
