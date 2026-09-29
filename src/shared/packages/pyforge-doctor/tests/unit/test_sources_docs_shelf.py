"""Unit tests for ``sources.docs_shelf`` (Story 23.7, spec-pyforge-doctor
CAP-54) -- covers the spec's I/O & Edge-Case Matrix: a dated
campaign note re-added at ``_bmad-output/`` root fires a quoted-path WARN,
and a clean MAP fixture (allow-listed occupancy only) is silent. The prose
Approach also names a second air-gap how-to outside the Story 23.2 cluster
as an equally-covered symptom, exercised here too.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import docs_shelf

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "docs_shelf"
_CLEAN = _FIXTURES / "clean"


# --- clean MAP fixture is silent (both checks) ------------------------------


def test_clean_fixture_gather_is_a_single_ok_finding():
    findings = docs_shelf.gather(_CLEAN)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.source == Source.DOCS_SHELF_OCCUPANCY
    assert finding.status == DoctorStatus.OK


def test_clean_fixture_has_no_bmad_output_root_leftovers():
    assert docs_shelf.find_bmad_output_root_leftovers(_CLEAN) == ()


def test_clean_fixture_has_no_extra_airgap_docs():
    assert docs_shelf.find_extra_airgap_docs(_CLEAN) == ()


# --- dated campaign note re-added at _bmad-output/ root ---------------------


def test_dated_campaign_note_at_root_fires_a_quoted_path_warn(tmp_path: Path):
    root = tmp_path / "_bmad-output"
    root.mkdir()
    (root / "PROJECTS.md").write_text("# index\n", encoding="utf-8")
    (root / "DREAM-TRIAGE-2026-08-09.md").write_text("# campaign\n", encoding="utf-8")

    findings = docs_shelf.find_bmad_output_root_leftovers(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source == Source.DOCS_SHELF_OCCUPANCY
    assert finding.check == "docs-shelf-bmad-output-root"
    assert finding.status == DoctorStatus.WARN
    assert finding.evidence["path"] == "_bmad-output/DREAM-TRIAGE-2026-08-09.md"
    assert "_bmad-output/DREAM-TRIAGE-2026-08-09.md" in finding.message


def test_allow_listed_root_entries_do_not_false_positive(tmp_path: Path):
    root = tmp_path / "_bmad-output"
    root.mkdir()
    (root / "PROJECTS.md").write_text("# index\n", encoding="utf-8")
    (root / "EXEMPLAR-STANDARD.md").write_text("# standard\n", encoding="utf-8")
    (root / "policy-defaults.toml").write_text("", encoding="utf-8")
    (root / "brainstorming").mkdir()
    (root / "harness-profiles").mkdir()
    (root / "projects").mkdir()
    (root / "planning-artifacts").symlink_to(root / "projects")
    (root / "implementation-artifacts").symlink_to(root / "projects")

    assert docs_shelf.find_bmad_output_root_leftovers(tmp_path) == ()


def test_missing_bmad_output_dir_is_silent(tmp_path: Path):
    assert docs_shelf.find_bmad_output_root_leftovers(tmp_path) == ()


# --- a second air-gap how-to outside the cluster -----------------------------


def test_second_airgap_howto_outside_the_cluster_fires_a_quoted_path_warn(
    tmp_path: Path,
):
    canonical = tmp_path / "docs" / "how-to" / "air-gapped-mirror-setup.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("# canonical\n", encoding="utf-8")
    second = tmp_path / "docs" / "how-to" / "airgap-operator-runbook.md"
    second.write_text("# second\n", encoding="utf-8")

    findings = docs_shelf.find_extra_airgap_docs(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source == Source.DOCS_SHELF_OCCUPANCY
    assert finding.check == "docs-shelf-airgap-cluster"
    assert finding.status == DoctorStatus.WARN
    assert finding.evidence["path"] == "docs/how-to/airgap-operator-runbook.md"


def test_canonical_airgap_pair_does_not_false_positive(tmp_path: Path):
    howto = tmp_path / "docs" / "how-to" / "air-gapped-mirror-setup.md"
    howto.parent.mkdir(parents=True)
    howto.write_text("# how-to\n", encoding="utf-8")
    explanation = tmp_path / "docs" / "explanation" / "airgap-distribution-contract.md"
    explanation.parent.mkdir(parents=True)
    explanation.write_text("# explanation\n", encoding="utf-8")

    assert docs_shelf.find_extra_airgap_docs(tmp_path) == ()


def test_substring_match_inside_an_unrelated_filename_does_not_false_positive(
    tmp_path: Path,
):
    # "repair-gap-analysis.md" contains the raw substring "air-gap" (inside
    # "rep-AIR-GAP-") but is not an air-gap-style token -- the regex needs
    # \b word boundaries so "repair"/"lair" etc. don't false-positive.
    howto_dir = tmp_path / "docs" / "how-to"
    howto_dir.mkdir(parents=True)
    (howto_dir / "repair-gap-analysis.md").write_text("# unrelated\n", encoding="utf-8")

    assert docs_shelf.find_extra_airgap_docs(tmp_path) == ()


def test_airgap_named_doc_outside_the_four_quadrants_is_out_of_scope(tmp_path: Path):
    # docs/MAP.md's own excluded layers (Dreams, specs, intake, governance)
    # are out of this check's scope, same as they are out of MAP.md's own.
    dream = tmp_path / "docs" / "dreams" / "air-gap-followup.md"
    dream.parent.mkdir(parents=True)
    dream.write_text("# not a quadrant\n", encoding="utf-8")

    assert docs_shelf.find_extra_airgap_docs(tmp_path) == ()


def test_missing_docs_dir_is_silent(tmp_path: Path):
    assert docs_shelf.find_extra_airgap_docs(tmp_path) == ()


# --- gather() combines both checks; never a second PR gate ------------------


def test_gather_combines_findings_from_both_checks(tmp_path: Path):
    root = tmp_path / "_bmad-output"
    root.mkdir()
    (root / "FLEET-RUN-2026-09-20.md").write_text("# campaign\n", encoding="utf-8")
    howto_dir = tmp_path / "docs" / "how-to"
    howto_dir.mkdir(parents=True)
    (howto_dir / "second-airgap-howto.md").write_text("# second\n", encoding="utf-8")

    findings = docs_shelf.gather(tmp_path)

    assert len(findings) == 2
    assert all(f.status == DoctorStatus.WARN for f in findings)
    assert all(f.source == Source.DOCS_SHELF_OCCUPANCY for f in findings)


def test_gather_never_reports_fail():
    # Warn-only, fail-open by construction -- this source's Finding
    # constructions only ever use OK or WARN (spec Boundaries: never a
    # second PR gate).
    findings = docs_shelf.gather(_CLEAN)
    assert all(f.status != DoctorStatus.FAIL for f in findings)


# --- live-repo proof, mirroring general_docs_consistency's own discipline ---


def test_live_repo_gather_is_clean():
    """Live proof (never validate only against a fully-synthetic fixture):
    the real repo's _bmad-output/ root and air-gap cluster are already
    clean per Stories 23.5/23.2 -- this pins that a live, unmodified repo
    reports silent, not merely that a synthetic fixture does."""
    repo_root = Path(__file__).resolve().parents[6]
    findings = docs_shelf.gather(repo_root)
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
