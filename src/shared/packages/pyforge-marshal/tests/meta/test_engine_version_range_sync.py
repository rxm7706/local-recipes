"""Meta test -- the pixi.toml / engine/copier.py version-range sync guard
(Story 12.1, NFR-C2), ported from ``pyforge-warden``'s identical guard
(``tests/meta/test_engine_version_range_sync.py`` there).

``pixi.toml``'s ``copier`` run-dependency pin and ``engine/copier.py``'s
``COPIER_VERSION_RANGE`` ``SpecifierSet`` constant must never drift apart --
one edited without the other is exactly the failure mode this guard exists
to catch.

The comparison runs BOTH sides through ``packaging.specifiers.SpecifierSet``
before comparing their ``str()`` forms byte-for-byte, rather than comparing
``pixi.toml``'s raw string directly: ``SpecifierSet.__str__`` canonicalizes
specifier ORDER (e.g. ``str(SpecifierSet(">=9.17,<10"))`` equals
``"<10,>=9.17"``, per its own docstring -- "the ordering of the individual
specifiers within the set may not match the input string"), so a literal
string comparison would fire on the repo's own conventional ``">=X,<Y"`` pin
style even with zero semantic drift. Normalizing both sides through the SAME
machinery keeps the guard sensitive to REAL drift (a different version
bound) while staying silent on cosmetic reordering."""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version

import pyforge.marshal
from pyforge.marshal.seed.engine.copier import COPIER_VERSION_RANGE

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
# .../src/pyforge/marshal/__init__.py -> marshal -> pyforge -> src -> package
# root (three directories up from __init__.py's own parent), where
# pixi.toml lives.
PACKAGE_ROOT = Path(_PACKAGE_FILE).resolve().parent.parent.parent.parent
PIXI_TOML = PACKAGE_ROOT / "pixi.toml"


def _run_dependencies() -> dict[str, object]:
    with PIXI_TOML.open("rb") as stream:
        data = tomllib.load(stream)
    return data["package"]["run-dependencies"]


def test_pixi_toml_is_found_where_expected():
    assert PIXI_TOML.is_file(), f"pixi.toml not found at {PIXI_TOML}"
    run_deps = _run_dependencies()
    assert "copier" in run_deps


def test_copier_range_matches_pixi_toml():
    run_deps = _run_dependencies()
    pixi_range = SpecifierSet(str(run_deps["copier"]))
    assert str(pixi_range) == str(COPIER_VERSION_RANGE), (
        "pixi.toml's copier run-dependency range and engine/copier.py's "
        "COPIER_VERSION_RANGE have drifted apart -- edit both together"
    )


def test_range_is_a_range_not_an_exact_pin():
    """NFR-C2: a range, not an exact pin -- Copier comes from conda-forge."""
    assert len(COPIER_VERSION_RANGE) >= 2


def test_evidence_backed_version_is_in_range():
    """The exact minor Spike-0 verified (copier 9.17.0) must be inside its
    own range -- a vacuous guard (a range that excludes its own evidence)
    would be worse than no guard at all."""
    assert Version("9.17.0") in COPIER_VERSION_RANGE


def test_range_does_not_widen_to_the_next_untested_minor():
    """NFR-C2's entire point: an untested newer minor must fail loud, not
    silently pass."""
    assert Version("10.0.0") not in COPIER_VERSION_RANGE
