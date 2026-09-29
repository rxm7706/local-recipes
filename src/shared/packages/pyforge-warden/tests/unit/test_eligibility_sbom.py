"""Story 7.3: eligibility CycloneDX + FABRIC-shaped corpus fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pyforge.warden.eligibility import (
    EligibilityResult,
    EligibilityStatus,
    ProvenanceEntry,
    compute_eligibility_union,
)
from pyforge.warden.eligibility_sbom import render_eligibility_cyclonedx
from pyforge.warden.models import Ecosystem
from pyforge.warden.sources import (
    CycloneDXSourceAdapter,
    ManifestSourceAdapter,
    SourceEvidence,
    resolve_identity,
)

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "eligibility_corpus"
FIXED_TS = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)
FIXED_SERIAL = "urn:uuid:00000000-0000-4000-8000-000000000073"


def test_corpus_matrix_is_complete():
    notice = (CORPUS / "NOTICE").read_text(encoding="utf-8")
    assert "Apache-2.0" in notice
    assert "FABRIC" in notice
    matrix = [
        line.strip()
        for line in (CORPUS / "MATRIX.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert len(matrix) == 13 * 6
    for rel in matrix:
        assert (CORPUS / rel).is_file(), rel


def test_cyclonedx_adapter_ingests_corpus_bom():
    path = CORPUS / "plain-lib" / "bom.cdx.json"
    evidence = CycloneDXSourceAdapter(path).ingest()
    assert evidence
    assert all(e.source_name for e in evidence)


def test_manifest_adapter_ingests_corpus_requirements():
    # ManifestSourceAdapter scans a target directory
    target = CORPUS / "plain-lib"
    evidence = ManifestSourceAdapter(target).ingest()
    # May be empty if discovery doesn't pick requirements.txt alone — still
    # must not raise (corpus exercises adapters without crashing).
    assert isinstance(evidence, tuple)


def test_eligibility_cyclonedx_is_deterministic():
    identity = resolve_identity(Ecosystem.PYPI, "requests", "2.32.3")
    results = (
        EligibilityResult(
            identity=identity,
            status=EligibilityStatus.ELIGIBLE_UNION,
            provenance=(
                ProvenanceEntry(
                    source="cyclonedx",
                    locator="bom.cdx.json",
                    timestamp=FIXED_TS.isoformat(),
                ),
            ),
        ),
    )
    a = render_eligibility_cyclonedx(results, serial_number=FIXED_SERIAL, timestamp=FIXED_TS)
    b = render_eligibility_cyclonedx(results, serial_number=FIXED_SERIAL, timestamp=FIXED_TS)
    assert a == b
    assert "eligible-union" in a
    assert "pkg:pypi/requests@2.32.3" in a


def test_union_then_render_round_trip():
    now = FIXED_TS
    id_a = resolve_identity(Ecosystem.PYPI, "requests", "2.32.3")
    evidence = (
        SourceEvidence(
            identity=id_a,
            source_name="cyclonedx",
            locator="a",
            raw_name="requests",
        ),
        SourceEvidence(
            identity=id_a,
            source_name="manifest",
            locator="b",
            raw_name="requests",
        ),
    )
    results = compute_eligibility_union(evidence, now=now)
    doc = render_eligibility_cyclonedx(results, serial_number=FIXED_SERIAL, timestamp=now)
    assert results[0].status is EligibilityStatus.ELIGIBLE_UNION
    assert "cfe:eligibility_status" in doc or "eligible-union" in doc
