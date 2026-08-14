"""`pixi` engine adapter (AD-12, Story 3.2): `.conda` package construction
via `pixi build` (FR-15, FR-21).

Mirrors `engines/pep517.py`'s own shape and rationale exactly (module-level
`name`/`probe()`/`build()`, STREAM mode without porting `cfe.run_streamed`,
filesystem-based artifact discovery rather than stdout parsing) -- see that
module's docstring for the shared reasoning; only the wrapped tool, its
argv shape, and its own filename-parsing technique differ.

`_BINARY_NAME` duplicates `engines/__init__.py`'s own
`_KNOWN_ENGINES["pixi"]` entry (`"pixi"`) -- the same sanctioned small-fact
duplication `engines/pep517.py` uses for its own `_BINARY_NAME` (see that
module's docstring).

`.conda` filename version parsing (spec Design Notes): conda's own
package/version/build-string filename fields never contain a literal `-`,
so splitting the stem on the LAST two `-` characters is a safe, general
parse even though this specific project's own name (`pyforge-mason`)
itself contains one:

    stem = conda_path.name.removesuffix(".conda")
    name, version, build_string = stem.rsplit("-", 2)

`packaging.version.Version` is deliberately NOT used to re-parse this
result (unlike `engines/pep517.py`'s wheel/sdist versions): the version
segment is kept as the RAW string the `.conda` filename convention already
encodes, so `package.py::build()`'s FR-22 mismatch comparison sees exactly
what `pixi build` itself named, not a Mason-side reinterpretation of it
(AD-1).

Story 3.5 adds `upload()` (FR-16, AD-14): a `.conda` artifact upload to a
named private conda channel via `pixi upload prefix --channel <name>
<file>`, resolving epic OQ-E2 in favour of the `prefix` pixi-upload
subcommand (see this story's spec Design Notes for why `prefix`, not
`anaconda`/`artifactory`/`pixi publish`). Mirrors `engines/twine.py::
upload()`'s own gate/timeout/argv shape (`require_engine` first, list argv,
no `env=` kwarg -- `pixi` itself reads `PREFIX_API_KEY` from its inherited
environment automatically, live-verified: `pixi upload prefix --help`
documents `--api-key` as `[env: PREFIX_API_KEY=]`) with one deliberate
deviation: `stderr=subprocess.STDOUT` merges the child's stderr into the
same captured stream as stdout, rather than `twine.py`'s/this module's own
`build()`'s `stderr=None`. Live-verified against the installed `pixi
0.76.2` binary: a missing-credential failure (`pixi upload prefix
--channel x nonexistent.conda`) prints its entire diagnostic ("Error: no
prefix.dev API key provided...") to stderr and writes NOTHING to stdout --
the opposite of `twine`'s own stdout-only diagnostics -- so `stderr=None`
here would silently produce an empty `stdout` field on every real-world
channel-upload failure.

Argv token order is `["pixi", "upload", "prefix", "--channel", channel,
conda_path]` -- the `prefix` subcommand and its `--channel` flag come
BEFORE the trailing `[PACKAGE_FILES]...` positional (live-verified,
2026-08-13: `pixi upload <file> prefix --channel <name>`, with the file
positioned before the subcommand, fails immediately with clap's own
`error: unexpected argument '--channel' found` -- the file is greedily
consumed as a second package-file positional, so `prefix` never registers
as the subcommand -- while `pixi upload prefix --channel <name> <file>`
reaches the tool's real credential check, per `pixi upload prefix --help`'s
own `Usage:` line).

`PixiUploadResult` carries no `url`/`reference` field, unlike `TwineUpload
Result` (module docstring below) -- no equivalent live-verified success-
path output exists for `pixi upload prefix` (exercising it needs a real API
key, channel, and network access, out of reach during spec authoring), so
`package.py::ship_channel`'s `reference` on success is the caller-supplied
`channel_name` itself, never a value parsed out of this adapter's captured
stdout.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import probe_engine, require_engine
from ..errors import (
    PackageBuildTimeoutError, PackageProjectPathError, ShipChannelUploadTimeoutError,
)

name = "pixi"
"""`EngineAdapter.name` -- an `engines/__init__.py::_KNOWN_ENGINES` key."""

_BINARY_NAME = "pixi"
"""Duplicates `_KNOWN_ENGINES["pixi"]` (module docstring)."""

_PIXI_BUILD_TIMEOUT_SECONDS = 600.0
"""Mirrors `engines/pep517.py::_PEP517_BUILD_TIMEOUT_SECONDS` -- same
generous ten-minute allowance for a from-source build; no live evidence yet
that `.conda` construction runs meaningfully longer or shorter than the
wheel/sdist path for this project."""

_PIXI_UPLOAD_TIMEOUT_SECONDS = 300.0
"""Five minutes: mirrors `engines/twine.py::_TWINE_UPLOAD_TIMEOUT_SECONDS`'s
own rationale for a network operation against a remote service (there,
PyPI; here, a prefix.dev channel) -- generous enough for a slow connection
uploading a single `.conda` file, without being as open-ended as
`_PIXI_BUILD_TIMEOUT_SECONDS`'s ten-minute allowance for compiling from
source."""


def probe() -> str | None:
    """`EngineAdapter.probe()` -- mirrors `engines/pep517.py::probe`."""
    return probe_engine(name, _BINARY_NAME).version


@dataclass(frozen=True)
class PixiBuildResult:
    """One `build()` call's outcome -- mirrors `engines.pep517.
    Pep517BuildResult`'s own shape and rationale. `conda_path` is the
    discovered `.conda` artifact's path, or `None` under the same
    "build failed or nothing found" conditions that module documents.
    `conda_version` is the RAW version segment the `.conda` filename
    convention encodes (module docstring) -- never re-parsed through
    `packaging.version.Version`. `stdout` is the child's captured stdout in
    full (review pass, 2026-08-13) -- mirrors `models.BuildResult.stdout`'s
    own precedent: a build failure investigated outside a live terminal (CI,
    a captured test run) needs diagnostic text, not a bare returncode
    integer."""

    returncode: int
    conda_path: str | None
    conda_version: str | None
    stdout: str


def _newest(paths: list[Path]) -> Path | None:
    """Mirrors `engines.pep517._newest` exactly (this module's own
    docstring: filesystem-based discovery, not stdout parsing)."""
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def build(project_path: str, *, timeout: float | None = None) -> PixiBuildResult:
    """Build `project_path`'s `.conda` package via `pixi build` (FR-15,
    FR-21).

    Raises `EngineAbsentError` (via `require_engine`) before any subprocess
    spawns if the `pixi` engine is not on `PATH` (spec Always boundary).
    Runs with `cwd=project_path`, no `--path` flag -- `pixi build` searches
    its own cwd for a supported manifest when `--path` is omitted (verified
    live against the installed `pixi` binary), mirroring the existing
    hand-run `pyforge-mason-build-conda` pixi task's own invocation shape
    (`pixi build --output-dir dist-conda` from that same `cwd`) and this
    story's own Block-If clause: `pixi build` has no `--manifest-path` flag
    (root `pixi.toml`'s own comment), only `--path`, which behaves
    identically to omitting it entirely when `cwd` already IS the target
    directory. Output lands at `<project_path>/dist-conda/` (spec Always
    boundary, FR-24) -- the same directory name that task's own
    `--output-dir dist-conda` (relative to its `cwd`) produces.

    `timeout` defaults to `_PIXI_BUILD_TIMEOUT_SECONDS` when `None`. A
    non-zero return code is DATA on the returned `PixiBuildResult`, never
    raised (AD-4, spec Always boundary).

    Raises `PackageBuildTimeoutError` (review pass, 2026-08-13) when the
    child exceeds `timeout` -- mirrors `engines.pep517.build`'s identical
    translation (see that module's docstring). Raises
    `PackageProjectPathError` when `cwd=project_path` itself fails
    (`OSError` -- e.g. `project_path` does not exist or is not a directory):
    this is NOT the "wrapped tool reports its own failure via returncode"
    case above, since the tool never even starts.
    """
    require_engine("pixi")

    outdir = f"{project_path}/dist-conda"
    resolved_timeout = timeout if timeout is not None else _PIXI_BUILD_TIMEOUT_SECONDS
    argv = [_BINARY_NAME, "build", "--output-dir", outdir]
    try:
        completed = subprocess.run(
            argv,
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=resolved_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise PackageBuildTimeoutError(engine=name, timeout=resolved_timeout) from None
    except OSError as exc:
        raise PackageProjectPathError(project_path=project_path, reason=str(exc)) from None

    if completed.returncode != 0:
        return PixiBuildResult(
            returncode=completed.returncode,
            conda_path=None,
            conda_version=None,
            stdout=completed.stdout,
        )

    conda_path = _newest(list(Path(outdir).glob("*.conda")))
    conda_version: str | None = None
    if conda_path is not None:
        stem = conda_path.name.removesuffix(".conda")
        parts = stem.rsplit("-", 2)
        if len(parts) == 3 and parts[1]:
            conda_version = parts[1]
        else:
            conda_path = None

    return PixiBuildResult(
        returncode=completed.returncode,
        conda_path=str(conda_path) if conda_path is not None else None,
        conda_version=conda_version,
        stdout=completed.stdout,
    )


@dataclass(frozen=True)
class PixiUploadResult:
    """One `upload()` call's outcome. `returncode` is the child's raw exit
    code -- DATA, never raised (AD-4, mirrors `TwineUploadResult`/
    `PixiBuildResult`). `stdout` is the child's captured stdout AND stderr,
    merged into one field (module docstring: `stderr=subprocess.STDOUT`) --
    unlike `TwineUploadResult`, there is no `url` field here: no equivalent
    live-verified success-path output shape exists for `pixi upload prefix`
    to parse (module docstring), so this dataclass reports only what was
    live-verified -- the raw exit code and the merged diagnostic text."""

    returncode: int
    stdout: str


def upload(conda_path: str, channel: str, *, timeout: float | None = None) -> PixiUploadResult:
    """Upload `conda_path` (a built `.conda` artifact) to the named private
    conda channel `channel` via `pixi upload prefix --channel <channel>
    <conda_path>` (Story 3.5, FR-16, AD-14).

    Raises `EngineAbsentError` (via `require_engine`) before any subprocess
    spawns if the `pixi` engine is not on `PATH` (spec Always boundary). No
    `env=` kwarg is passed to `subprocess.run` (spec Always boundary,
    AD-14, module docstring) -- the child inherits the real process
    environment automatically, which is how `PREFIX_API_KEY` reaches `pixi`
    without this module (or `package.py::ship_channel`) ever touching or
    copying it.

    Argv is `["pixi", "upload", "prefix", "--channel", channel,
    conda_path]` (module docstring for the live-verified rationale behind
    this exact token order -- the `prefix` subcommand and its `--channel`
    flag MUST precede the trailing `[PACKAGE_FILES]...` positional).
    `stderr=subprocess.STDOUT` merges the child's stderr into the captured
    stdout stream (module docstring: a missing-credential failure writes
    its entire diagnostic to stderr and nothing to stdout, the opposite of
    `twine`'s own stdout-only diagnostics).

    `timeout` defaults to `_PIXI_UPLOAD_TIMEOUT_SECONDS` when `None`,
    mirroring every other engine adapter's own per-operation-default
    convention. Raises `ShipChannelUploadTimeoutError` when the child
    exceeds `timeout` -- `subprocess.run`'s own timeout handling has
    already killed and reaped the child by the time that exception reaches
    here, mirroring `engines.twine.upload`'s identical translation to its
    own timeout error.

    A non-zero return code is DATA on the returned `PixiUploadResult`,
    never raised (AD-4, spec Always boundary) -- the caller decides what a
    failed upload means; this function only reports it. No further parsing
    is performed on the captured output (module docstring: no live-verified
    success-path output shape exists for `pixi upload prefix` to scan).
    """
    require_engine("pixi")

    resolved_timeout = timeout if timeout is not None else _PIXI_UPLOAD_TIMEOUT_SECONDS
    argv = [_BINARY_NAME, "upload", "prefix", "--channel", channel, conda_path]
    try:
        completed = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=resolved_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ShipChannelUploadTimeoutError(timeout=resolved_timeout) from None

    return PixiUploadResult(returncode=completed.returncode, stdout=completed.stdout)
