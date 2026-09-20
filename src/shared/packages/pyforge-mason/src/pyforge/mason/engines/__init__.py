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
   `pep517.py`/`pixi.py` -- wheel/sdist and `.conda` build --, Story 3.4's
   `twine.py` (PyPI upload), Story 3.5's channel-publish target (also via
   `pixi.py`), and Story 4.1's `condalock.py`) implements alongside its own
   operation method(s) -- e.g. `build()`, `upload()`, `lock()`. This module
   does not itself implement the protocol; it only names the contract those
   future modules structurally satisfy (`@runtime_checkable`, so a future
   registry can `isinstance()`-check an adapter against it, mirroring every
   other structural `Protocol` in this codebase's sibling packages -- a
   `Protocol`, not an ABC, so an adapter class satisfies this shape simply by
   defining the same members, no inheritance required).
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

Story 3.7 registers a fifth engine, `gh` (FR-18, AD-10): `engines/gh.py`'s
own adapter (`name`, `probe()`, `find_open_pr()`) searches the CFE fork for
an open conda-forge/staged-recipes pull request, one of `ship_pypi`/
`ship_channel`'s three interrogation-based idempotence mechanisms (the other
two are `pypi_index.version_exists`/`engines.pixi.search`, both added by the
same story). `GH_VERSION_RANGE` below is constructed via `_minor_range`
exactly like the existing four (evidence: `gh` 2.97.0, live-verified in this
environment) -- `mason doctor` picks `gh` up automatically through this
module's existing `probe_known_engines()` call, with no `doctor.py` source
change (spec Always boundary)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

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
    "gh": "gh",
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
    except OSError, UnicodeDecodeError, subprocess.TimeoutExpired:
        return EngineStatus(name=name, available=True, version=None)

    version = _stripped_or_none(completed.stdout) or _stripped_or_none(completed.stderr)
    return EngineStatus(name=name, available=True, version=version)


def probe_known_engines() -> tuple[EngineStatus, ...]:
    """Probe every engine in `_KNOWN_ENGINES`, in declared order."""
    return tuple(probe_engine(name, binary) for name, binary in _KNOWN_ENGINES.items())


# --- Story 3.1: the adapter protocol, version-range constants, and the ONE
# --- raising entry point (module docstring's "three things" list) ----------


@runtime_checkable
class EngineAdapter(Protocol):
    """The shared adapter shape every future `engines/*.py` module
    implements (AD-12) -- Story 3.2's `pep517.py`/`pixi.py`, Story 3.4's
    `twine.py`, Story 3.5's channel-publish target (also via `pixi.py`), and
    Story 4.1's `condalock.py`. Structural, not nominal: a `Protocol`, not an
    ABC, so an adapter class satisfies this shape simply by defining the
    same members -- no registration, no base-class coupling.
    `@runtime_checkable` (matching every structural `Protocol` in this
    codebase's sibling packages, e.g. `pyforge-warden`'s `Engine`/
    `VulnStrategy`) so a future adapter registry can `isinstance()`-check a
    candidate against this shape.

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
    "gh": "gh",
}
"""Display name -> conda package name that provisions it, consulted only by
`require_engine`'s `EngineAbsentError` (the provisioning hint). Distinct
from `_KNOWN_ENGINES` (display name -> PATH *binary* name) for the same
reason `build` needed a distinct binary name in the first place: the `build`
engine's conda package is `python-build` (matching `pixi.toml`'s
`[package.run-dependencies]` key), but neither its display name (`build`)
nor its binary name (`pyproject-build`) is that string."""


def _minor_range(floor: str, ceiling: str) -> SpecifierSet:
    """Build the `>=floor,<ceiling` `SpecifierSet` every constant below uses,
    from two bare version strings rather than one inline `">=X,<Y"` literal.

    `tests/meta/test_no_recipe_knowledge.py`'s AD-1 pin-constraint-shape
    guard flags any string constant holding a comparison operator directly
    beside a digit (e.g. `">=1"`) ANYWHERE under `src/pyforge/mason/` --
    its target is a literal conda-forge *recipe* pin (a packaging decision
    CFE's generator/optimizer makes, per that guard's own docstring), not
    Mason's own engine-tooling provisioning ranges below, but the guard
    matches on shape alone and its own docstring is explicit that the
    fix for a shape collision is to construct the value differently, never
    to weaken the pattern. `floor`/`ceiling` (e.g. `"0.76.2"`, `"0.77"`) are
    plain digit-and-dot strings with no operator character, so neither they
    nor this function's own `f"..."` literal parts (`">="`, `",<"` -- never
    followed by a digit within the SAME string constant, since the digits
    only arrive via interpolation) trip the guard, while the `SpecifierSet`
    this produces at runtime is byte-identical to the inline-literal form.
    """
    return SpecifierSet(f">={floor},<{ceiling}")


def _floor(floor: str) -> SpecifierSet:
    """A floor-only range (``>=floor``), built by interpolation for the same
    reason ``_minor_range`` is: an inline ``">=7.0.0"`` literal trips the AD-1
    pin-constraint-shape guard, while ``floor`` alone is digits and dots.
    Operator ruling 2026-09-20: engine ranges carry no ceiling without a written
    reason -- the ``pyforge-foundry-full`` union solve showed a cap's cost."""
    return SpecifierSet(f">={floor}")


# Evidence-backed version FLOORS (spec Always boundary, amended 2026-09-20 by
# operator ruling -- "never cap without a reason"): each constant must
# byte-for-byte mirror `pixi.toml`'s `[package.run-dependencies]` entry for
# the same engine -- enforced by `tests/meta/test_engine_version_range_sync.py`.
# Until 2026-09-20 these were one-tested-minor windows (`>=X.Y.Z,<X.(Y+1)`);
# the `pyforge-foundry-full` union env (steward Story 63.5) showed the cost:
# `python-build <1.6` could not co-resolve with the `>=1.6.0` floors pyforge-ci
# / pyforge-core / pyforge-testing-kit / local-recipes pin, so the fleet's own
# dependency closure was unsolvable. Floors carry the evidence (live-verified:
# pixi 0.80.0, twine 7.0.0, conda-lock 4.0.2, build 1.6.0, gh 2.97.0); a
# ceiling is added only with a written reason -- `PIXI_VERSION_RANGE` keeps
# its window because an in-env pixi ABOVE the workspace's own `requires-pixi`
# line would parse a manifest the workspace has not tested (the reason is in
# pixi.toml beside the pin). These constants exist for the sync guard alone --
# `require_engine` below does NOT consult them; see its own docstring for why.
PIXI_VERSION_RANGE = _minor_range("0.80.0", "0.81")
TWINE_VERSION_RANGE = _floor("7.0.0")
CONDA_LOCK_VERSION_RANGE = _floor("4.0.2")
PYTHON_BUILD_VERSION_RANGE = _floor("1.6.0")
GH_VERSION_RANGE = _floor("2.97.0")


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
