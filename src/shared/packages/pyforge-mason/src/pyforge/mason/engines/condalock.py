"""`conda-lock` engine adapter (AD-12, Story 4.1): environment/dependency
locking via `conda-lock lock` (FR-27, FR-29).

Mirrors `engines/pep517.py`'s own shape and rationale exactly (module-level
`name`/`probe()`, `require_engine` gate before any subprocess spawns or
filesystem writes, list argv, STREAM-free CAPTURE-mode `subprocess.run` with
a mandatory `timeout=`) -- see that module's docstring for the shared
reasoning. `lock()` is the first adapter operation in this codebase to
thread its own probed engine name/version onto its own result
(`CondaLockResult.engine_name`/`engine_version`): FR-29 requires Mason to
*report* which engine ran, and this is the one adapter whose caller
genuinely cannot already know that from context (every other adapter's
result implicitly names its own engine only through which module the caller
chose to call).

`_BINARY_NAME` duplicates `engines/__init__.py`'s own `_KNOWN_ENGINES
["conda-lock"]` entry (`"conda-lock"`) -- the same sanctioned small-fact
duplication `engines/pep517.py`/`engines/twine.py` already use for their own
`_BINARY_NAME` (see `engines/pep517.py`'s module docstring).

`manifest_paths` becomes one repeated `-f <path>` per entry; `platforms`
becomes one repeated `-p <platform>` per entry -- `conda-lock lock`'s own
`-f`/`-p` options are both `multiple=True` (live-verified against installed
`conda-lock 4.0.2`). Omitting `platforms` passes no `-p` flag at all,
letting conda-lock's own default apply (FR-27) -- Mason never invents one.

Provenance via `--mdy` (live-verified against `conda-lock 4.0.2`): before
invoking, a small JSON file naming this adapter's own `name`/probed
`engine_version` is written to a `tempfile.mkstemp`-managed path and passed
via `--mdy <path>` -- `conda-lock lock --mdy meta.json ...` merges that
file's contents into the produced lockfile's own `metadata.custom_metadata`
block verbatim (FR-29's "where the format allows"). `os.fdopen(fd, "w")`
inside a `with` block closes the metadata file before `subprocess.run`
spawns the child (NFR-12: Windows disallows a second process opening a file
another process still holds open). The write itself lives inside the same
`try` as the subprocess call (review pass, 2026-08-14) -- a write failure
(e.g. disk full) still reaches the `finally` cleanup rather than leaking the
file `mkstemp` already created. The metadata file is removed in a `finally`
block after the child exits or the write fails -- success, failure, or
timeout alike -- so no temp file is ever orphaned; the removal itself
swallows `OSError` (review pass, 2026-08-14) so a cleanup failure (e.g. a
lingering Windows file handle right after a timeout-killed child) can never
replace a real propagating exception.

Subprocess invocation: list argv, never `shell=True`; `stdout=subprocess.
PIPE`, `stderr=None` (inherited) -- live-verified `conda-lock` writes every
progress/diagnostic line to stderr and nothing to stdout on both success and
failure, mirroring `engines.pep517.build`'s identical STREAM-adjacent
CAPTURE-mode choice; `text=True, encoding="utf-8", errors="replace"`, a
mandatory `timeout=` (default `_CONDA_LOCK_TIMEOUT_SECONDS = 600.0`,
mirroring `_PEP517_BUILD_TIMEOUT_SECONDS`'s "solving is closer to compiling
from source than uploading a file" rationale), `check=False`.

A non-zero return code is DATA on `CondaLockResult`, never raised (AD-4) --
live-verified a failed solve exits non-zero with a traceback on stderr, the
routine expected outcome of resolving a real dependency graph; the caller
decides what a failed lock means, this function only reports it.
`lockfile_path` is `None` whenever `returncode != 0` (no lockfile was
produced to report), and `output_path` otherwise. Raises
`EnvironmentLockTimeoutError` when the child exceeds `timeout` --
`subprocess.run`'s own timeout handling has already killed and reaped the
child by the time that exception reaches here, mirroring `engines.pep517.
build`'s identical translation to its own timeout error.

This module assembles argv and reports the child's outcome only -- no
dependency-resolution logic of its own (spec AC3): `conda-lock`'s own
vendored solver is what resolves the dependency graph.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass

from . import probe_engine, require_engine
from ..errors import EnvironmentLockTimeoutError

name = "conda-lock"
"""`EngineAdapter.name` -- an `engines/__init__.py::_KNOWN_ENGINES` key."""

_BINARY_NAME = "conda-lock"
"""Duplicates `_KNOWN_ENGINES["conda-lock"]` (module docstring)."""

_CONDA_LOCK_TIMEOUT_SECONDS = 600.0
"""Ten minutes: mirrors `_PEP517_BUILD_TIMEOUT_SECONDS`'s own "solving is
closer to compiling from source than uploading a file" rationale -- a lock
solve over a real dependency graph can run considerably longer than a
CAPTURE-mode probe or upload."""


def probe() -> str | None:
    """`EngineAdapter.probe()` -- mirrors `engines/pep517.py::probe`."""
    return probe_engine(name, _BINARY_NAME).version


@dataclass(frozen=True)
class CondaLockResult:
    """One `lock()` call's outcome. `returncode` is the child's raw exit
    code -- DATA, never raised (AD-4, mirrors `Pep517BuildResult`/
    `TwineUploadResult`). `lockfile_path` is `output_path` on a successful
    solve (`returncode == 0`), or `None` when the solve failed -- a failed
    solve never produced a lockfile to report. `engine_name`/
    `engine_version` are this adapter's own `name` and the version
    `require_engine` returned for this call (module docstring: the first
    adapter result shape in this codebase to carry them, since FR-29 needs
    Mason to report which engine ran). `stdout` is the child's captured
    stdout in full -- mirrors `Pep517BuildResult.stdout`'s own precedent: a
    failure investigated outside a live terminal needs diagnostic text, not
    a bare returncode integer."""

    returncode: int
    lockfile_path: str | None
    engine_name: str
    engine_version: str | None
    stdout: str


def lock(
    manifest_paths: Sequence[str],
    output_path: str,
    *,
    platforms: Sequence[str] = (),
    timeout: float | None = None,
) -> CondaLockResult:
    """Resolve `manifest_paths` into a lockfile at `output_path` via
    `conda-lock lock` (FR-27, FR-29).

    Raises `EngineAbsentError` (via `require_engine`) before any subprocess
    spawns or filesystem write if the `conda-lock` engine is not on `PATH`
    (spec Always boundary) -- the returned version is captured for both the
    result and the `--mdy` provenance file, never re-probed a second time.

    Argv is `["conda-lock", "lock"]` followed by one repeated `-f <path>`
    per `manifest_paths` entry, one repeated `-p <platform>` per `platforms`
    entry, `["--lockfile", output_path]`, and finally `["--mdy",
    <metadata temp file path>]` (module docstring for the rationale behind
    each piece).

    `timeout` defaults to `_CONDA_LOCK_TIMEOUT_SECONDS` when `None`,
    mirroring every other engine adapter's own per-operation-default
    convention. Raises `EnvironmentLockTimeoutError` when the child exceeds
    `timeout` -- the `--mdy` metadata file is still removed in this case
    (module docstring: removed in a `finally` block, success, failure, or
    timeout alike).

    A non-zero return code is DATA on the returned `CondaLockResult`, never
    raised (AD-4, spec Always boundary) -- the caller decides what a failed
    lock means; this function only reports it.
    """
    engine_version = require_engine("conda-lock")

    resolved_timeout = timeout if timeout is not None else _CONDA_LOCK_TIMEOUT_SECONDS

    argv = [_BINARY_NAME, "lock"]
    for manifest_path in manifest_paths:
        argv.extend(("-f", manifest_path))
    for platform in platforms:
        argv.extend(("-p", platform))
    argv.extend(("--lockfile", output_path))

    fd, metadata_path = tempfile.mkstemp(suffix=".json", prefix="mason-condalock-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(
                {"mason_engine_name": name, "mason_engine_version": engine_version}, handle
            )
        argv.extend(("--mdy", metadata_path))

        completed = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=resolved_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise EnvironmentLockTimeoutError(timeout=resolved_timeout) from None
    finally:
        try:
            os.unlink(metadata_path)
        except OSError:
            pass

    return CondaLockResult(
        returncode=completed.returncode,
        lockfile_path=output_path if completed.returncode == 0 else None,
        engine_name=name,
        engine_version=engine_version,
        stdout=completed.stdout,
    )
