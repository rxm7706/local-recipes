"""Meta test — remedy surfaces name ``marshal seed accept``, not ``update --force`` as accept (Story 97.1, AC8)."""

from __future__ import annotations

import re
from pathlib import Path

import pyforge.marshal
from pyforge.marshal.seed.detect.findings import REMEDIES, FindingType

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
_MARSHAL_PKG = Path(_PACKAGE_FILE).resolve().parent
_PACKAGE_ROOT = _MARSHAL_PKG.parent.parent.parent

_SURFACES = (
    _MARSHAL_PKG / "seed" / "detect" / "findings.py",
    _MARSHAL_PKG / "seed" / "verbs" / "preconditions.py",
    _PACKAGE_ROOT / "docs" / "finding-remedy-reference.md",
    _PACKAGE_ROOT / "docs" / "adoption-guide.md",
)

_BAD_ACCEPT_BASELINE = re.compile(
    r"update\s+--force[^.\n]{0,120}\b(accept|baseline)\b|accept[^.\n]{0,40}as the new baseline",
    re.IGNORECASE,
)


def test_managed_remedies_name_seed_accept_and_discard_via_force():
    for finding_type in (FindingType.MANAGED_FILE_MODIFIED, FindingType.MANAGED_REGION_MODIFIED):
        remedy = REMEDIES[finding_type]
        assert "marshal seed accept" in remedy
        assert _BAD_ACCEPT_BASELINE.search(remedy) is None
        assert "discard" in remedy.lower() or "--force" in remedy


def test_no_surface_claims_update_force_accepts_an_edit():
    for path in _SURFACES:
        text = path.read_text(encoding="utf-8")
        match = _BAD_ACCEPT_BASELINE.search(text)
        assert match is None, f"{path}: forbidden remedy wording near {match.group(0)!r}"


def test_surfaces_still_name_marshal_seed_accept():
    for path in _SURFACES:
        text = path.read_text(encoding="utf-8")
        assert "marshal seed accept" in text, f"{path} must name marshal seed accept"
