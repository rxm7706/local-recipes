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
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

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
    """Same four deps, same pins, both manifests -- ``python`` excluded (a
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
