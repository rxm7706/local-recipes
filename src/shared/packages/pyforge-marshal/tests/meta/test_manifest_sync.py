"""Meta test -- the two hand-duplicated package manifests stay in sync
(Story 1.1).

``pyproject.toml`` (hatchling: wheel/sdist + the pip-visible metadata) and
``pixi.toml`` (pixi-build-python: the conda package) each spell the version
and the four runtime dependencies independently -- the sibling convention
offers no single source of truth for them. ``tests/unit/test_cli.py``
already trips on ``cli/main.py``'s ``__version__`` drifting from
``pyproject.toml``; these are the remaining two tripwires, so a one-sided
edit can't ship a conda package whose version or requirement set silently
diverges from the wheel's.

Story 1.9's follow-up review adds a third tripwire: the harness-version
range the seam declares (``adapters/harness_bmadloop.py``, FR-52) against
``pyproject.toml``'s own ``bmad-loop`` pin -- see that test's docstring.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from pyforge.marshal.adapters.harness_bmadloop import (
    HARNESS_VERSION_RANGE_TEXT,
    _HARNESS_MAX_MINOR_EXCLUSIVE,
    _HARNESS_MIN_VERSION,
)

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]

# PEP 508-lite: the distribution name, then everything after it is the
# version-specifier tail. Marshal's declared deps are plain name+specifier
# (no extras/markers), which is all this needs to split.
_REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9._-]+)\s*(.*)$")


def _load(name: str) -> dict:
    return tomllib.loads((_PACKAGE_ROOT / name).read_text(encoding="utf-8"))


def test_package_pixi_version_matches_pyproject():
    """The conda package version (pixi.toml [package]) is the third copy of
    the version literal -- the cli/main.py copy is covered in test_cli.py."""
    assert (
        _load("pixi.toml")["package"]["version"]
        == _load("pyproject.toml")["project"]["version"]
    )


def test_package_run_dependencies_match_project_dependencies():
    """Same deps, same pins, both manifests -- ``python`` excluded (a
    conda-side interpreter pin with no pyproject counterpart; pyproject's
    ``requires-python`` covers it)."""
    pyproject_deps: dict[str, str] = {}
    for requirement in _load("pyproject.toml")["project"]["dependencies"]:
        match = _REQUIREMENT_RE.match(requirement)
        assert match is not None, f"unparseable requirement {requirement!r}"
        pyproject_deps[match.group(1).lower()] = match.group(2).replace(" ", "")
    pixi_deps = {
        name.lower(): spec.replace(" ", "")
        for name, spec in _load("pixi.toml")["package"]["run-dependencies"].items()
        if name != "python"
    }
    assert pixi_deps == pyproject_deps


def test_harness_range_constants_match_pyproject_dependency_pin():
    """Story 1.9 relocated the declared harness range into
    ``adapters/harness_bmadloop.py`` as THE source of truth (FR-52) -- but
    its three spellings (``_HARNESS_MIN_VERSION``,
    ``_HARNESS_MAX_MINOR_EXCLUSIVE``, ``HARNESS_VERSION_RANGE_TEXT``) are
    still hand-synced against the ``bmad-loop`` pin in ``pyproject.toml``
    (itself cross-checked against ``pixi.toml`` above). A pin bump that
    leaves the constants behind makes ``marshal preflight`` block (or
    wrongly pass) on the exact harness version the package itself installs,
    with every other test green -- this is that tripwire, the same pattern
    as ``test_cli.py``'s ``__version__`` sync test."""
    bmad_loop_specs = []
    for requirement in _load("pyproject.toml")["project"]["dependencies"]:
        match = _REQUIREMENT_RE.match(requirement)
        assert match is not None, f"unparseable requirement {requirement!r}"
        if match.group(1).lower() == "bmad-loop":
            bmad_loop_specs.append(match.group(2).replace(" ", ""))
    assert bmad_loop_specs == [HARNESS_VERSION_RANGE_TEXT]
    # And the two tuple constants must spell the SAME range as the text --
    # the text is what operators see, the tuples are what the code compares.
    min_text = ".".join(str(part) for part in _HARNESS_MIN_VERSION)
    max_text = ".".join(str(part) for part in _HARNESS_MAX_MINOR_EXCLUSIVE)
    assert HARNESS_VERSION_RANGE_TEXT == f">={min_text},<{max_text}"
