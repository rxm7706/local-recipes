"""The sole subprocess site in ``pyforge.doctor`` (Story 2.1, AD-5).

``sources/atlas.py``'s CLI fallback (and any future gather filter that needs
one) calls a repo-local script through :func:`run_cli_json`, never through
``subprocess`` directly -- the meta-test ``test_cli_bridge_sole_subprocess.py``
enforces that this module is the ONE place in the installed package allowed
to shell out (mirrors ``sources/warden.py``'s sole-``pyforge.warden``-import
guard, applied to the subprocess surface instead).

``run_cli_json`` is deliberately narrow: argv is always a list (never
``shell=True``), the call is bounded by an explicit ``timeout``, the
subprocess environment carries ``NO_COLOR=1`` so an ANSI-colored table
can never leak into stdout ahead of the ``--json`` payload, and every
failure mode -- the script missing, a non-zero exit, a timeout, or
unparseable JSON on stdout -- raises the single typed :class:`CliBridgeError`
rather than letting a bare ``subprocess``/``json`` exception escape. Callers
(``sources/atlas.py``) degrade that into a ``Finding`` themselves; this
module has no opinion on Doctor's ``Finding`` shape.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class CliBridgeError(RuntimeError):
    """A CLI fallback call failed: script missing, non-zero exit, a
    timeout, or unparseable JSON on stdout."""


def run_cli_json(
    script_path: Path, args: list[str], *, timeout: float
) -> Any:
    """Run ``python3 script_path *args`` and parse its stdout as JSON.

    ``args`` must already include any flag needed to get JSON output (e.g.
    ``--json``) -- this function has no opinion on the script's CLI surface,
    only on how to run it safely and parse the result."""
    if not script_path.is_file():
        raise CliBridgeError(f"CLI script not found: {script_path}")

    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    argv = [sys.executable, str(script_path), *args]

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CliBridgeError(
            f"{script_path.name} timed out after {timeout}s"
        ) from exc
    except OSError as exc:
        raise CliBridgeError(
            f"{script_path.name} failed to launch: {exc!r}"
        ) from exc

    if result.returncode != 0:
        raise CliBridgeError(
            f"{script_path.name} exited {result.returncode}: "
            f"{result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CliBridgeError(
            f"{script_path.name} produced unparseable JSON on stdout: {exc}"
        ) from exc
