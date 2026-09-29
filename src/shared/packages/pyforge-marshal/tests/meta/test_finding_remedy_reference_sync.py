"""Meta test — finding-remedy reference stays aligned with ``FindingType``
(Story 12.6, NFR-M3).

Every member of ``seed.detect.findings.FindingType`` must appear in the
packaged reference doc so operators and CI never depend on reading Genesis
source to interpret a finding. The doc's remedy strings must match
``REMEDIES`` exactly for each listed type.
"""

from __future__ import annotations

import re
from pathlib import Path

import pyforge.marshal
from pyforge.marshal.seed.detect.findings import REMEDIES, FindingType

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
# .../src/pyforge/marshal/__init__.py -> package root (four parents).
PACKAGE_ROOT = Path(_PACKAGE_FILE).resolve().parent.parent.parent.parent
REFERENCE_DOC = PACKAGE_ROOT / "docs" / "finding-remedy-reference.md"

# Table row: | `artifact-missing` | HARD | Run `marshal seed adopt` … |
_TABLE_ROW = re.compile(
    r"^\|\s*`([a-z0-9-]+)`\s*\|\s*(HARD|DRIFT|INFO)\s*\|\s*(.+?)\s*\|\s*$",
    re.MULTILINE,
)


def test_reference_doc_exists():
    assert REFERENCE_DOC.is_file(), f"missing reference doc at {REFERENCE_DOC}"


def test_every_finding_type_appears_in_reference_doc():
    text = REFERENCE_DOC.read_text(encoding="utf-8")
    documented = _TABLE_ROW.findall(text)
    documented_types = {row[0] for row in documented}
    expected = {member.value for member in FindingType}
    missing = expected - documented_types
    extra = documented_types - expected
    assert not missing, f"FindingType members missing from reference doc: {sorted(missing)}"
    assert not extra, f"reference doc lists unknown finding types: {sorted(extra)}"
    assert documented_types == expected


def test_reference_doc_remedies_match_remedies_mapping():
    text = REFERENCE_DOC.read_text(encoding="utf-8")
    rows = _TABLE_ROW.findall(text)
    by_type = {finding_type: (severity, remedy) for finding_type, severity, remedy in rows}
    for finding_type in FindingType:
        _severity, doc_remedy = by_type[finding_type.value]
        assert doc_remedy == REMEDIES[finding_type], f"{finding_type.value}: reference doc remedy drifted from REMEDIES"
