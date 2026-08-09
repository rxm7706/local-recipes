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
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

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
