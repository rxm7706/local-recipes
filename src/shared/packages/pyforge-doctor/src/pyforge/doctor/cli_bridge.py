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


def run_cli_json(script_path: Path, args: list[str], *, timeout: float) -> Any:
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
        raise CliBridgeError(f"{script_path.name} timed out after {timeout}s") from exc
    except OSError as exc:
        raise CliBridgeError(f"{script_path.name} failed to launch: {exc!r}") from exc

    if result.returncode != 0:
        raise CliBridgeError(f"{script_path.name} exited {result.returncode}: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CliBridgeError(f"{script_path.name} produced unparseable JSON on stdout: {exc}") from exc


def run_git(
    cwd: Path,
    args: list[str],
    *,
    timeout: float = 30.0,
    ok_exit_codes: frozenset[int] = frozenset({0}),
) -> str:
    """Run ``git *args`` in ``cwd`` and return stdout.

    Added 2026-08-08 for ``sources/marshal.py``, which judges the Marshal's
    durability guarantee by reading the DURABLE RECORD — the committed sprint
    ledgers — rather than by asking ``pyforge.marshal`` about itself (Charter §6:
    the Doctor holds the verdict on the one station that would otherwise grade
    itself). Reading a committed blob means running ``git show``, and AD-5 says a
    new subprocess need is satisfied HERE, never by a second shell-out site.

    Narrow in the same way :func:`run_cli_json` is: argv is always a list, never
    ``shell=True``; the call is bounded by an explicit timeout; ``NO_COLOR=1`` and
    ``--no-pager`` keep decoration out of stdout. It differs in one deliberate way —
    it returns **raw text**, because git's payload here is a YAML file, not JSON.

    ``ok_exit_codes`` (Story 9.2, keyword-only, default ``{0}`` — every existing
    caller's behavior is byte-identical) lets a caller tolerate a documented
    non-zero exit that isn't a failure — ``git grep``'s exit 1 means "no match",
    not an error. A returncode outside the set still raises :class:`CliBridgeError`
    exactly as before. Story 11.3 is the first caller to use it: a mechanical
    call-site check passes ``ok_exit_codes=frozenset({0, 1})`` so ``git grep``'s
    "no matches in any file" reads as a valid, expected outcome rather than every
    other ``git`` call site becoming newly tolerant of a non-zero exit too.

    Raises :class:`CliBridgeError` on every failure mode (git absent, an exit code
    outside ``ok_exit_codes``, timeout). Callers degrade that into a ``Finding``;
    this module has no opinion on Doctor's ``Finding`` shape.
    """
    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    argv = ["git", "--no-pager", *args]

    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CliBridgeError(f"git {' '.join(args[:2])} timed out after {timeout}s") from exc
    except OSError as exc:
        raise CliBridgeError(f"git failed to launch: {exc!r}") from exc

    if result.returncode not in ok_exit_codes:
        raise CliBridgeError(f"git {' '.join(args[:2])} exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def run_pytest(
    interpreter: Path,
    cwd: Path,
    args: list[str],
    *,
    timeout: float = 120.0,
) -> tuple[int, str]:
    """Run ``interpreter -m pytest *args`` in ``cwd``; return
    ``(returncode, combined stdout+stderr)``.

    Added for ``sources/platform_policy.py`` (retro action item 3,
    2026-09-05), which judges ``src/platform``'s manifest-only policy suite —
    a Django/pytest-django surface Doctor's own lean env does not carry, so
    ``interpreter`` names a DIFFERENT pixi env's python (``platform-ci-test``)
    the caller has already confirmed exists on disk.

    Unlike :func:`run_git`, pytest's own exit codes 0 (all passed) and 1
    (some failed) are BOTH a completed, meaningful run — the caller decides
    what a Finding looks like for either. Only {2, 3, 4, 5} (usage error,
    internal error, usage error, no tests collected) mean the run itself
    could not be trusted, so those still raise :class:`CliBridgeError` —
    mirrors ``run_git``'s ``ok_exit_codes`` mechanism (Story 9.2), fixed here
    rather than parameterized since every caller wants the identical split.
    """
    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    argv = [str(interpreter), "-m", "pytest", *args]

    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CliBridgeError(f"pytest timed out after {timeout}s") from exc
    except OSError as exc:
        raise CliBridgeError(f"pytest failed to launch: {exc!r}") from exc

    if result.returncode not in (0, 1):
        raise CliBridgeError(
            f"pytest exited {result.returncode} (not a pass/fail result): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.returncode, result.stdout + result.stderr


def run_check_script(
    script_path: Path,
    args: list[str],
    *,
    cwd: Path,
    timeout: float = 60.0,
) -> tuple[int, str]:
    """Run ``sys.executable script_path *args`` in ``cwd``; return
    ``(returncode, combined stdout+stderr)`` -- for a repo-local mutator
    script's own self-check mode (Story 30.3, ``spec-pyforge-doctor``
    CAP-84), where EVERY exit code the script defines is a meaningful,
    already-decided result (0 current, non-zero stale/drifted/hand-edited)
    that the CALLER interprets, never a sign the run itself failed.

    Added for ``sources/docs_currency.py``'s generated-page-stale check:
    each ``kind: generated`` page in ``docs/map.yaml`` names its own
    generator script (``scripts/docs_*.py``, outside this installed
    package -- AD-5 forbids ``pyforge.doctor`` from importing the
    top-level ``scripts/`` tree, so the check can only reach a generator's
    logic by running it, never by importing it), and the ONE way to ask
    "would regenerating this page change it" without duplicating five
    different pages' render logic inside Doctor itself is to run that
    generator's own ``--check`` mode and read its exit code.

    Mirrors :func:`run_pytest`'s "both exit codes are a completed run"
    shape, generalized from pytest's fixed ``{0, 1}`` to an arbitrary
    script's own exit-code contract, since a docs generator's ``--check``
    mode has no reason to share pytest's specific two codes.

    Raises :class:`CliBridgeError` only when the script itself could not be
    launched or timed out -- never on account of the exit code it returns.
    """
    if not script_path.is_file():
        raise CliBridgeError(f"script not found: {script_path}")

    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    argv = [sys.executable, str(script_path), *args]

    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CliBridgeError(f"{script_path.name} timed out after {timeout}s") from exc
    except OSError as exc:
        raise CliBridgeError(f"{script_path.name} failed to launch: {exc!r}") from exc

    return result.returncode, result.stdout + result.stderr
