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

Story 4.4 adds `check()`, `mason environment check`'s own engine operation
(FR-25, FR-27, FR-29): re-runs `conda-lock lock --check-input-hash` against a
**temporary copy** of the given lockfile, never the real `lockfile_path`.
Why the copy (corrected against installed `conda-lock` 4.0.2's own source,
review pass, 2026-08-15 second): `conda_lock.py::run_lock` writes its
`--lockfile` target on exactly the branch that matters here -- the
`write_conda_lock_file` call sits inside the `else:` of `if not
platforms_to_lock:`, so a check that finds nothing to re-solve writes
NOTHING, while a check that finds a stale input runs a real solve and
rewrites the target with the merged result. Pointing `--lockfile` at the
caller's real file would therefore regenerate it precisely when it is stale
-- both a mutation nowhere in this command's contract and a self-erasing
one, since the freshly-rewritten file would report itself current on the
very next check. (An earlier revision of this docstring claimed the write
was unconditional, including the "nothing changed" branch; that was wrong.
The copy is still required, for the stale branch alone.)

Staleness is decided by `yaml.safe_load`-parsing the copy's `metadata.
content_hash` before vs. after invoking conda-lock and comparing the two
parsed dicts for equality -- never conda-lock's own returncode (Design Notes:
`--check-input-hash`'s documented exit-code-4 behavior is dead in installed
`conda-lock` 4.0.2) and never raw file bytes (a harmless re-serialization
that only changes formatting still parses to an identical dict). Raises
`EnvironmentLockfileMissingError` (not `EngineAbsentError`) before any
subprocess spawns when `lockfile_path` does not exist on disk -- a
Mason-side precondition this operation alone needs, since `lock()` above has
no analogous "existing file" input to validate first. Raises
`EnvironmentCheckTimeoutError` (not `EnvironmentLockTimeoutError`) on a
timeout -- a dedicated class per distinct operation, mirroring
`ShipUploadTimeoutError`/`ShipChannelUploadTimeoutError`'s precedent
(errors.py). The temporary copy is removed in a `finally` block, current,
stale, or timed-out alike, mirroring `lock()`'s own `--mdy` cleanup
precedent (`OSError` on removal swallowed).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass

import yaml

from ..errors import (
    EnvironmentCheckTimeoutError,
    EnvironmentLockfileMalformedError,
    EnvironmentLockfileMissingError,
    EnvironmentLockTimeoutError,
)
from . import probe_engine, require_engine

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
            json.dump({"mason_engine_name": name, "mason_engine_version": engine_version}, handle)
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


@dataclass(frozen=True)
class CondaLockCheckResult:
    """One `check()` call's outcome (Story 4.4, FR-25, FR-27, FR-29).
    `stale` is the ONE piece of data this operation exists to produce:
    `True` when the lockfile's own `metadata.content_hash` differs before
    vs. after re-running `conda-lock lock --check-input-hash` against a
    temporary copy of it (module docstring: why a copy, never the real
    path), `False` when it does not -- never conda-lock's own returncode
    (module docstring: dead in installed 4.0.2). `returncode`/`engine_name`/
    `engine_version`/`stdout` mirror `CondaLockResult`'s own identical
    fields and rationale -- `returncode` is the delegated `conda-lock`
    subprocess's raw exit code, DATA here too (AD-4), never used to derive
    `stale`."""

    stale: bool
    returncode: int
    engine_name: str
    engine_version: str | None
    stdout: str


def check(
    lockfile_path: str,
    manifest_paths: Sequence[str],
    *,
    platforms: Sequence[str] = (),
    timeout: float | None = None,
) -> CondaLockCheckResult:
    """Report whether `lockfile_path` is stale relative to `manifest_paths`
    via `conda-lock lock --check-input-hash`, run against a **temporary
    copy** of `lockfile_path` -- never the caller's own file (module
    docstring for the full rationale).

    Raises `EngineAbsentError` (via `require_engine`) before any subprocess
    spawns or temp copy is made if the `conda-lock` engine is not on `PATH`
    -- checked FIRST, mirroring `lock()`'s own engine-presence-gate-first
    precedent. Raises `EnvironmentLockfileMissingError` if `lockfile_path`
    does not exist on disk -- checked second, still before any subprocess
    spawns or temp copy is made (spec Always boundary).

    The copy is made via `tempfile.mkstemp` + `shutil.copyfile` (module
    docstring; `copyfile`, not `copy` -- review pass, 2026-08-15: `shutil.
    copy` also calls `copymode`, overwriting `mkstemp`'s secure `0600` temp
    file with the source lockfile's own, typically wider, permission bits;
    `copyfile` copies content only, leaving `mkstemp`'s mode untouched).
    Its `metadata.content_hash` is parsed with `yaml.safe_load` (never
    `yaml.load`) both before and after invoking conda-lock, via the private
    `_read_content_hash` helper below, which translates any malformed-
    content failure (not valid YAML, empty, missing the expected keys, not
    valid UTF-8) into `EnvironmentLockfileMalformedError` rather than a raw
    exception (review pass, 2026-08-15) -- `stale` is `True` exactly when
    those two parsed values differ (module docstring: why parsed dicts, not
    raw bytes or conda-lock's own returncode). The caller's own
    `lockfile_path` is never opened for writing at any point -- only read
    once, by `shutil.copyfile`'s source side. A failure there is translated
    by cause, never as a blanket (review pass, 2026-08-15 second: catching
    bare `OSError` and re-raising "does not exist" reported an unreadable
    lockfile, a full `$TMPDIR`, or an I/O error as a missing file, and
    prescribed `mason environment lock` as a remedy that could not help):
    `FileNotFoundError` -- the narrow TOCTOU race between the earlier
    `os.path.isfile` check and this copy, the case that translation was
    added for -- raises `EnvironmentLockfileMissingError`, while every other
    `OSError` raises `EnvironmentLockfileMalformedError` carrying the OS's
    own diagnostic verbatim (AD-1). Both are typed `MasonError`s (NFR-14);
    neither leaks a raw `OSError`.

    A non-zero `completed.returncode` is surfaced as DATA on the returned
    result (AD-4, mirrors `lock()`'s own precedent) -- but review pass,
    2026-08-15 found that leaving it at that let a genuine `conda-lock`
    failure (a bad manifest, a solver crash, a network error during a real
    re-solve the hash mismatch triggered) masquerade as `stale=False`
    whenever the temp copy happened not to be rewritten before the failure:
    `cli.py`'s own dispatch now also treats a non-zero `returncode` as
    `EXIT_FAILED`, so this function itself still never raises for a failed
    child (AD-4 intact), but a caller relying on the process exit code alone
    can no longer mistake "the check itself failed" for "current."

    Argv is `["conda-lock", "lock", "--check-input-hash"]` followed by one
    repeated `-f <path>` per `manifest_paths` entry, one repeated
    `-p <platform>` per `platforms` entry, and finally `["--lockfile",
    <temp copy path>]` -- mirrors `lock()`'s own `-f`/`-p` repetition and
    omitted-`platforms`/`manifest_paths` behavior exactly. `subprocess.run`
    kwargs are byte-identical to `lock()`'s own (`stdout=PIPE, stderr=None,
    text=True, encoding="utf-8", errors="replace", check=False`, a mandatory
    `timeout=`).

    An omitted `platforms` delegates the platform set to conda-lock, never
    to Mason (spec Always boundary) -- but note what conda-lock's own
    default actually is (review pass, 2026-08-15 second, read from installed
    4.0.2): `src_parser/__init__.py::make_lock_spec` falls back to
    `DEFAULT_PLATFORMS`, FOUR platforms (`linux-64`, `osx-arm64`, `osx-64`,
    `win-64`), whenever neither `-p` nor the manifests themselves name any.
    `run_lock` then adds every platform the lockfile does not already cover
    to `platforms_to_lock` REGARDLESS of `--check-input-hash`, so checking a
    deliberately narrow lockfile (one locked with an explicit `-p` subset)
    without repeating that same subset here runs a real, network-touching
    solve for the uncovered platforms and reports `stale=True` for manifests
    that never changed. Pass the same `platforms` the lockfile was locked
    with. Defaulting instead to the lockfile's own recorded
    `metadata.platforms` would remove that footgun, but is a change to this
    command's contract rather than to its implementation -- deferred, see
    the station's deferred-work ledger.

    `timeout` defaults to `_CONDA_LOCK_TIMEOUT_SECONDS` when `None` --
    reused from `lock()` above (identical underlying `conda-lock lock`
    invocation) -- but a timeout raises `EnvironmentCheckTimeoutError`, NOT
    `EnvironmentLockTimeoutError` (module docstring). The temp copy is
    removed in a `finally` block, current, stale, or timed-out alike;
    removal swallows `OSError`.
    """
    engine_version = require_engine("conda-lock")

    if not os.path.isfile(lockfile_path):
        raise EnvironmentLockfileMissingError(lockfile_path)

    resolved_timeout = timeout if timeout is not None else _CONDA_LOCK_TIMEOUT_SECONDS

    fd, temp_lockfile_path = tempfile.mkstemp(suffix=".yml", prefix="mason-condalock-check-")
    os.close(fd)
    try:
        try:
            shutil.copyfile(lockfile_path, temp_lockfile_path)
        except FileNotFoundError as exc:
            raise EnvironmentLockfileMissingError(lockfile_path) from exc
        except OSError as exc:
            raise EnvironmentLockfileMalformedError(lockfile_path, str(exc)) from exc

        before = _read_content_hash(temp_lockfile_path, lockfile_path)

        argv = [_BINARY_NAME, "lock", "--check-input-hash"]
        for manifest_path in manifest_paths:
            argv.extend(("-f", manifest_path))
        for platform in platforms:
            argv.extend(("-p", platform))
        argv.extend(("--lockfile", temp_lockfile_path))

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

        after = _read_content_hash(temp_lockfile_path, lockfile_path)
    except subprocess.TimeoutExpired:
        raise EnvironmentCheckTimeoutError(timeout=resolved_timeout) from None
    finally:
        try:
            os.unlink(temp_lockfile_path)
        except OSError:
            pass

    return CondaLockCheckResult(
        stale=before != after,
        returncode=completed.returncode,
        engine_name=name,
        engine_version=engine_version,
        stdout=completed.stdout,
    )


def _read_content_hash(temp_path: str, lockfile_path: str) -> object:
    """Read `metadata.content_hash` out of the temp lockfile copy at
    `temp_path`, translating any malformed-content failure into
    `EnvironmentLockfileMalformedError` naming the caller's own
    `lockfile_path` (review pass, 2026-08-15) -- a lockfile that is not
    valid YAML, is empty (`yaml.safe_load` returns `None`), is not valid
    UTF-8, or lacks the expected `metadata`/`content_hash` keys is not an
    anticipated `conda-lock`-produced shape, but must still surface as a
    typed `MasonError` (NFR-14), never a raw `KeyError`/`TypeError`/
    `yaml.YAMLError`/`UnicodeDecodeError`/`OSError` escaping to `main()`'s
    generic exception handler."""
    try:
        with open(temp_path, encoding="utf-8") as handle:
            return yaml.safe_load(handle)["metadata"]["content_hash"]
    except (OSError, UnicodeDecodeError, yaml.YAMLError, KeyError, TypeError) as exc:
        raise EnvironmentLockfileMalformedError(lockfile_path, str(exc)) from exc
