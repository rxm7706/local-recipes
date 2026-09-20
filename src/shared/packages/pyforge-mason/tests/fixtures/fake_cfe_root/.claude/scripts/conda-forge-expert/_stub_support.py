"""Shared runtime for the fake CFE root's stub scripts (Story 1.9, AD-16).

Every named stub script under this directory (`validate_recipe.py`,
`submit_pr.py`, ...) inserts its own directory onto `sys.path` (this
fixture's own sibling-import convention -- distinct from the real
`.claude/scripts/conda-forge-expert/*.py` wrappers, which file-relatively
locate and subprocess-delegate to the canonical skill script instead of
importing anything) and calls `emit(...)` to produce its canned output.
Per-test variation goes entirely through the `MASON_FIXTURE_*` environment
variables read here at runtime -- the fixture tree itself is never
rewritten.

Stdlib only, no third-party imports -- this tree must run under any
interpreter with no dependency on the pyforge-mason environment.
"""

from __future__ import annotations

import os


def emit(default_stdout: str, default_exit_code: int = 0) -> int:
    """Print the fixture's canned (or overridden) stdout body and return the
    exit code the caller should `sys.exit(...)` with.

    Order of output:
    1. `MASON_FIXTURE_PROGRESS_LINE`, if set -- a plain, non-JSON line
       printed first, exercising the tolerant-parsing path (FR-4).
    2. `MASON_FIXTURE_STDOUT`, if set, else `default_stdout`.

    The exit code is `int(MASON_FIXTURE_EXIT_CODE)` if that variable is set,
    else `default_exit_code`.
    """
    progress_line = os.environ.get("MASON_FIXTURE_PROGRESS_LINE")
    if progress_line is not None:
        print(progress_line)

    stdout_body = os.environ.get("MASON_FIXTURE_STDOUT", default_stdout)
    print(stdout_body)

    exit_code_override = os.environ.get("MASON_FIXTURE_EXIT_CODE")
    if exit_code_override is not None:
        return int(exit_code_override)
    return default_exit_code
