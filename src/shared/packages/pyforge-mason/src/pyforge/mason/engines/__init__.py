"""Engine presence/version probing -- a minimal AD-12 seed (Story 1.8).

`pyforge.mason.doctor` needs a real `--version` string for each engine Mason
will eventually drive (`pixi`, `twine`, `conda-lock`, `build`), but AD-2's
subprocess allowlist restricts `import subprocess` to `cli.py`, `cfe.py`, and
`engines/*.py` -- `doctor.py` has no other legal way to obtain one. This
module exists only to satisfy that, and deliberately does NOT build AD-12's
full "one protocol" adapter registry: no `name`/`probe()`/operation protocol,
no typed `engine:absent`-style error, no per-engine adapter files
(`pep517.py`/`twine.py`/`pixi.py`/`condalock.py`), no `pixi.toml`
version-range declarations, and no sync meta-test. Story 3.1 ("Engine
protocol and provisioning") is chartered separately for all of that and
extends this file rather than recreating it, mirroring how Story 1.6
extended `resolve.py` and Story 1.7 extended `cfe.py`.

`_KNOWN_ENGINES` maps each engine's display name to its PATH *binary* name.
`build`'s binary is `pyproject-build`, not `build` -- the `build` PyPI/conda
package's `console_scripts` entry point is named `pyproject-build`
(`build.__main__:entrypoint`); there is no bare `build` executable. Verified
live: `pyproject-build --version` prints `build 1.5.0 (...)`.

`probe_engine` never raises. `shutil.which` finding nothing on PATH reports
`available=False, version=None` with no subprocess attempted at all. When
found, `[path, "--version"]` is run with a mandatory timeout,
`capture_output=True`, `text=True`, `check=False` -- list argv, never
`shell=True` (Consistency Conventions). `OSError` (binary vanished/not
executable between the `which` and the `run`), `UnicodeDecodeError` (output
isn't decodable text), `subprocess.TimeoutExpired`, and a non-zero exit with
no usable output all fold into `available=True, version=None`: the engine is
present but its version could not be determined, never an exception.
`version` is the full stripped stdout, falling back to stderr (some tools
print their version banner there instead) -- reported verbatim, never
truncated to a single line: review pass (2026-08-09) found the real `twine`
binary wraps its `--version` banner across multiple lines
(`twine version 7.0.0 (readme-renderer: 45.0, requests: 2.34.2, requests-` /
`toolbelt: 1.0.0, ...)`), and an earlier first-line-only cut reported a
version string truncated mid-word. Never parsed or validated (spec Never
boundary: no `packaging`-based version comparison here, unlike `cfe.py`'s
import-floor probe which does compare names, not versions).

Story 3.1 ("Engine protocol and provisioning") extends this module with
three things Story 1.8 deliberately left out, per its own docstring above:

1. `EngineAdapter`, a minimal `Protocol` (`name`, `probe()`) documenting the
   shared shape every future `engines/*.py` adapter module (Story 3.2's
   `pep517.py`, 3.4/3.5's `twine.py`, 3.2's `pixi.py`, 4.1's `condalock.py`)
   implements alongside its own operation method(s) -- e.g. `build()`,
   `upload()`, `lock()`. This module does not itself implement the
   protocol; it only names the contract those future modules structurally
   satisfy (a `Protocol`, not an ABC -- no registration, no inheritance
   required of them).
2. Four `SpecifierSet` version-range constants, one per known engine, each a
   byte-for-byte mirror of `pixi.toml`'s `[package.run-dependencies]` entry
   for that engine -- enforced by `tests/meta/test_engine_version_range_
   sync.py` (ported from `pyforge-warden`'s identical guard). These exist
   for that sync guard alone; `require_engine` below does NOT consult them
   (see its own docstring) -- version-range *gating* is deliberately left to
   whichever future adapter module first needs it, not pre-built here.
3. `require_engine`, the ONE new raising entry point this story adds --
   `probe_engine`/`probe_known_engines` above stay exactly as Story 1.8 left
   them (never raising, never parsed), per the spec's Always boundary.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol

from packaging.specifiers import SpecifierSet

from ..errors import EngineAbsentError

_PROBE_TIMEOUT_SECONDS = 10.0
"""A private constant, not a configurable knob -- mirrors `cfe.py`'s
`_PROBE_TIMEOUT_SECONDS` rationale: `--cfe-timeout`/`MASON_CFE_TIMEOUT` is
Story 1.10's closed v1 knob (AD-13) and governs CFE invocation, not engine
`--version` probing, which has no flag of its own."""

_KNOWN_ENGINES: dict[str, str] = {
    "pixi": "pixi",
    "twine": "twine",
    "conda-lock": "conda-lock",
    "build": "pyproject-build",
}
"""Display name -> PATH binary name, in probe order. See module docstring
for why `build`'s binary is `pyproject-build`."""


@dataclass(frozen=True)
class EngineStatus:
    """The outcome of probing one engine: whether it is on `PATH`, and its
    raw `--version` output when available -- never parsed or compared."""

    name: str
    available: bool
    version: str | None


def _stripped_or_none(text: str) -> str | None:
    """Return `text` with surrounding whitespace stripped, or `None` if
    nothing remains. Never truncates interior content -- a multi-line
    `--version` banner (e.g. `twine`'s real one, which wraps) is preserved
    whole, matching the "reported verbatim" contract (module docstring)."""
    stripped = text.strip()
    return stripped or None


def probe_engine(name: str, binary: str) -> EngineStatus:
    """Probe one engine by its display `name` and PATH `binary` name.

    See module docstring for the full fold-into-`available=True,
    version=None` list; this function never raises.
    """
    path = shutil.which(binary)
    if path is None:
        return EngineStatus(name=name, available=False, version=None)

    try:
        completed = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, UnicodeDecodeError, subprocess.TimeoutExpired):
        return EngineStatus(name=name, available=True, version=None)

    version = _stripped_or_none(completed.stdout) or _stripped_or_none(completed.stderr)
    return EngineStatus(name=name, available=True, version=version)


def probe_known_engines() -> tuple[EngineStatus, ...]:
    """Probe every engine in `_KNOWN_ENGINES`, in declared order."""
    return tuple(probe_engine(name, binary) for name, binary in _KNOWN_ENGINES.items())


# --- Story 3.1: the adapter protocol, version-range constants, and the ONE
# --- raising entry point (module docstring's "three things" list) ----------


class EngineAdapter(Protocol):
    """The shared adapter shape every future `engines/*.py` module
    implements (AD-12) -- Story 3.2's `pep517.py`, Stories 3.4/3.5's
    `twine.py`, Story 3.2's `pixi.py`, and Story 4.1's `condalock.py`.
    Structural, not nominal: a `Protocol`, not an ABC, so an adapter class
    satisfies this shape simply by defining the same members -- no
    registration, no base-class coupling.

    `name` is the engine's display name (an `_KNOWN_ENGINES` key, e.g.
    `"pixi"`) the adapter wraps. `probe()` returns the same `str | None` a
    call through this module's own `probe_engine(name, binary).version`
    would -- present-but-unparseable is `None`, never an exception (mirrors
    `probe_engine`'s own never-raising contract), so a caller composing
    several adapters' `probe()` results together never needs per-adapter
    exception handling. Each adapter additionally exposes its own operation
    method(s) (e.g. `build()`, `upload()`, `lock()`) that this protocol
    deliberately does not name -- those are adapter-specific, not shared.
    """

    name: str

    def probe(self) -> str | None: ...


_ENGINE_CONDA_PACKAGES: dict[str, str] = {
    "pixi": "pixi",
    "twine": "twine",
    "conda-lock": "conda-lock",
    "build": "python-build",
}
"""Display name -> conda package name that provisions it, consulted only by
`require_engine`'s `EngineAbsentError` (the provisioning hint). Distinct
from `_KNOWN_ENGINES` (display name -> PATH *binary* name) for the same
reason `build` needed a distinct binary name in the first place: the `build`
engine's conda package is `python-build` (matching `pixi.toml`'s
`[package.run-dependencies]` key), but neither its display name (`build`)
nor its binary name (`pyproject-build`) is that string."""


# Evidence-backed version ranges (spec Always boundary): one tested minor
# wide (`>=X.Y.Z,<X.(Y+1)`, the repo-wide convention -- see pyforge-warden's
# `DEPTRY_VERSION_RANGE`/`OSV_SCANNER_VERSION_RANGE`), never widened "to be
# safe". Each constant must byte-for-byte mirror `pixi.toml`'s
# `[package.run-dependencies]` entry for the same engine -- enforced by
# `tests/meta/test_engine_version_range_sync.py`. Evidence, live-verified in
# this environment: pixi 0.76.2, twine 7.0.0, conda-lock 4.0.2, build
# (`pyproject-build` binary, conda package `python-build`) 1.5.0. These
# constants exist for that sync guard alone -- `require_engine` below does
# NOT consult them; see its own docstring for why.
PIXI_VERSION_RANGE = SpecifierSet(">=0.76.2,<0.77")
TWINE_VERSION_RANGE = SpecifierSet(">=7.0.0,<7.1")
CONDA_LOCK_VERSION_RANGE = SpecifierSet(">=4.0.2,<4.1")
PYTHON_BUILD_VERSION_RANGE = SpecifierSet(">=1.5.0,<1.6")


def require_engine(name: str) -> str | None:
    """Probe `name` (an `_KNOWN_ENGINES` key) and raise `EngineAbsentError`
    if it is not on `PATH`; otherwise return its version exactly as
    `probe_engine` reported it (`str | None` -- presence, not parseability,
    is what this function requires: an engine on `PATH` whose `--version`
    output could not be read is still usable, so this returns `None` for it
    rather than raising -- see the spec's I/O matrix).

    The ONLY raising surface this story adds (Design Notes) -- deliberately
    does NOT range-check the returned version against this module's
    `SpecifierSet` constants above (spec Never boundary: no
    `packaging`-based version validation lives in the probe path, and this
    function's whole job is "is it here at all", not "is it the right
    version"). A future story that needs range-gating adds that at its own
    call site, using these same constants, rather than this function growing
    a second responsibility.

    Raises `KeyError` if `name` is not an `_KNOWN_ENGINES` key -- the same
    contract this module's own `_KNOWN_ENGINES[name]`-style lookups already
    carry; there is no engine to require provisioning for that this module
    does not itself know how to probe.
    """
    status = probe_engine(name, _KNOWN_ENGINES[name])
    if not status.available:
        raise EngineAbsentError(name, _ENGINE_CONDA_PACKAGES[name])
    return status.version
