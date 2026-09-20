"""`twine` engine adapter (AD-12, AD-14, Story 3.4): PyPI upload via `twine
upload` (FR-16, FR-20).

Mirrors `engines/pep517.py`'s own shape and rationale exactly (module-level
`name`/`probe()`, `require_engine` gate before any subprocess spawns, list
argv, STREAM-free CAPTURE-mode `subprocess.run` with a mandatory `timeout=`)
-- see that module's docstring for the shared reasoning. `upload()` differs
from `pep517.build()`/`pixi.build()` in two structural ways: it has no
`cwd=` (it uploads already-built artifact PATHS, not a project directory)
and it does no filesystem-based artifact discovery afterward -- the caller
already knows what it built; this module's only job is to run `twine` and
report what happened.

`_BINARY_NAME` duplicates `engines/__init__.py`'s own `_KNOWN_ENGINES
["twine"]` entry (`"twine"`) -- the same sanctioned small-fact duplication
`engines/pep517.py`/`engines/pixi.py` already use for their own
`_BINARY_NAME` (see `engines/pep517.py`'s module docstring).

No `env=` kwarg is ever passed to `subprocess.run` (spec Always boundary,
AD-14): the child inherits the real process environment automatically, and
that inheritance is the ONLY way the `TWINE_USERNAME`/`TWINE_PASSWORD`
values themselves ever reach `twine` -- `package.py::ship_pypi` (Story 3.4)
checks only their PRESENCE in the caller's `environ` before calling
`build()`, and never reads either value into a variable this module could
even pass along. `tests/meta/test_credential_isolation.py` Guard 3a enforces
this: the only two sanctioned `env=` override sites in this whole package
live inside `cfe.py`.

Argv is `["twine", "upload", "--non-interactive", "--disable-progress-bar",
*paths]`: `--non-interactive` is defense-in-depth so a spawned child can
never block on a stdin prompt (every subprocess call in this codebase
already carries a `timeout=`, but a blocked child still wastes the whole
window before that timeout fires); `--disable-progress-bar` keeps captured
stdout deterministic -- twine's own `rich` console force-enables ANSI/live-
rendering (`rich.reconfigure(force_terminal=True)` in the installed
`twine 7.0.0` binary's own `cli.py`) even when stdout is piped, not a TTY,
so an enabled progress bar would otherwise interleave cursor-movement
escape sequences into the captured text unpredictably.

Story 3.9 adds `upload()`'s `repository_url` keyword (FR-24, FR-50, AD-26):
when given, argv gains `--repository-url <repository_url>` immediately
before the artifact paths -- `twine`'s own flag for pointing an upload at a
non-default package index. This is the ENTIRE mechanism behind AD-26's
"identical code path, differing only in repository configuration": no new
vocabulary lands here, no `.pypirc`, no `TWINE_REPOSITORY`/
`TWINE_REPOSITORY_URL` env-var read (spec Never boundary) -- the TestPyPI
URL itself is a `package.py`-owned constant
(`_TESTPYPI_REPOSITORY_URL`), never hardcoded in this module. `None` (the
default) leaves argv exactly as it was before this story, so every
pre-3.9 call site's own argv shape is unchanged.

ANSI stripping and URL extraction (spec Always boundary, verified live
against the installed `twine 7.0.0` binary): a failed `twine upload` of a
nonexistent file writes `\x1b[31mERROR   \x1b[0m ...` to STDOUT (never
stderr) because of the same forced-terminal `rich` console noted above, so
raw captured stdout always needs ANSI stripping before it is either stored
or scanned for a URL. On success, twine's own `twine.commands.upload.
upload` prints a literal `"\n[green]View at:"` line followed by one
`print(url)` call per release URL (confirmed by reading the installed
twine's `commands/upload.py`/`repository.py::release_urls`); `release_urls`
is a `Set[str]` keyed by name+version, so a single `twine upload wheel
sdist` call for the same package+version yields exactly one URL. `url` is
`None` when no `"View at:"` block is found -- a genuine zero-returncode
success whose stdout happened not to contain one is still a success (state
is driven by `returncode`, never gated on whether the URL happened to
parse).
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from ..errors import ShipUploadTimeoutError
from . import probe_engine, require_engine

name = "twine"
"""`EngineAdapter.name` -- an `engines/__init__.py::_KNOWN_ENGINES` key."""

_BINARY_NAME = "twine"
"""Duplicates `_KNOWN_ENGINES["twine"]` (module docstring)."""

_TWINE_UPLOAD_TIMEOUT_SECONDS = 300.0
"""Five minutes: mirrors `cfe.py::_SUBMIT_PR_TIMEOUT_SECONDS`'s own
rationale for a network operation against a remote service (there, GitHub;
here, PyPI) -- generous enough for a slow connection uploading a wheel+
sdist pair (normally a few hundred KB to a few MB each), without being as
open-ended as `_PEP517_BUILD_TIMEOUT_SECONDS`/`_PIXI_BUILD_TIMEOUT_SECONDS`'s
ten-minute allowance for compiling from source."""

_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
"""Matches twine's own ANSI SGR (Select Graphic Rendition) escape codes --
`rich.reconfigure(force_terminal=True)` (the installed twine's own
`cli.py`) force-enables color even when stdout is piped, not a TTY (module
docstring, verified live against the installed `twine 7.0.0` binary)."""

_VIEW_AT_URL_PATTERN = re.compile(r"View at:\s*\n\s*(\S+)")
"""Matches twine's own `print("\\n[green]View at:")` followed by one
`print(url)` per release URL (module docstring) -- applied AFTER ANSI
stripping, so the `[green]` rich markup has already collapsed to plain
`"View at:"` text by the time this pattern runs; captures the first
non-whitespace token on the line immediately following it."""


def probe() -> str | None:
    """`EngineAdapter.probe()` -- mirrors `engines/pep517.py::probe`."""
    return probe_engine(name, _BINARY_NAME).version


@dataclass(frozen=True)
class TwineUploadResult:
    """One `upload()` call's outcome. `returncode` is the child's raw exit
    code -- DATA, never raised (AD-4, mirrors `Pep517BuildResult`/
    `PixiBuildResult`). `url` is the release URL twine's own stdout reports
    following its `"View at:"` block, or `None` when no match is found --
    including a genuine zero-returncode success whose stdout happened not to
    contain one (module docstring: state is driven by `returncode`, never
    gated on whether the URL happened to parse). `stdout` is the child's
    captured stdout in full, ANSI-stripped (module docstring) -- mirrors
    `Pep517BuildResult.stdout`'s own precedent: a failure investigated
    outside a live terminal needs diagnostic text, not a bare returncode
    integer."""

    returncode: int
    url: str | None
    stdout: str


def _strip_ansi(text: str) -> str:
    """Remove every ANSI SGR escape sequence from `text` (module
    docstring)."""
    return _ANSI_ESCAPE_PATTERN.sub("", text)


def _extract_view_at_url(stdout: str) -> str | None:
    """Return the URL following twine's own `"View at:"` block in
    (already ANSI-stripped) `stdout`, or `None` if no match is found (module
    docstring)."""
    match = _VIEW_AT_URL_PATTERN.search(stdout)
    return match.group(1) if match is not None else None


def upload(
    paths: Sequence[str],
    *,
    timeout: float | None = None,
    repository_url: str | None = None,
) -> TwineUploadResult:
    """Upload `paths` (the wheel+sdist artifacts) to PyPI -- or, with
    `repository_url` given, to whatever index that URL names (Story 3.9,
    e.g. TestPyPI) -- via `twine upload` (FR-16, FR-20, FR-24, FR-50,
    AD-14, AD-26).

    Raises `EngineAbsentError` (via `require_engine`) before any subprocess
    spawns if the `twine` engine is not on `PATH` (spec Always boundary). No
    `env=` kwarg is passed to `subprocess.run` (spec Always boundary, AD-14,
    module docstring) -- the child inherits the real process environment
    automatically, which is how `TWINE_USERNAME`/`TWINE_PASSWORD` reach
    `twine` without this module (or `package.py::ship_pypi`) ever touching
    or copying them.

    Argv is `["twine", "upload", "--non-interactive", "--disable-progress-
    bar", *paths]` (module docstring for the rationale behind each flag),
    except that when `repository_url` is not `None`, `"--repository-url"`
    and `repository_url` itself are inserted immediately before `*paths`
    (module docstring, Story 3.9) -- `omitted`/`None` reproduces the exact
    pre-3.9 argv shape.

    `timeout` defaults to `_TWINE_UPLOAD_TIMEOUT_SECONDS` when `None`,
    mirroring every other engine adapter's own per-operation-default
    convention. Raises `ShipUploadTimeoutError` when the child exceeds
    `timeout` -- `subprocess.run`'s own timeout handling has already killed
    and reaped the child by the time that exception reaches here, mirroring
    `engines.pep517.build`'s identical translation to its own timeout error.

    A non-zero return code is DATA on the returned `TwineUploadResult`,
    never raised (AD-4, spec Always boundary) -- the caller decides what a
    failed upload means; this function only reports it. Captured stdout is
    ANSI-stripped before being stored or scanned for a release URL (module
    docstring), and that URL scan only runs when `returncode == 0` (spec
    Always boundary): a failure's stdout is preserved verbatim, but never
    searched for a `"View at:"` block that a failed upload never printed.
    """
    require_engine("twine")

    resolved_timeout = timeout if timeout is not None else _TWINE_UPLOAD_TIMEOUT_SECONDS
    argv = [_BINARY_NAME, "upload", "--non-interactive", "--disable-progress-bar"]
    if repository_url is not None:
        argv.extend(["--repository-url", repository_url])
    argv.extend(paths)
    try:
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
        raise ShipUploadTimeoutError(timeout=resolved_timeout) from None

    stdout = _strip_ansi(completed.stdout)
    url = _extract_view_at_url(stdout) if completed.returncode == 0 else None

    return TwineUploadResult(returncode=completed.returncode, url=url, stdout=stdout)
