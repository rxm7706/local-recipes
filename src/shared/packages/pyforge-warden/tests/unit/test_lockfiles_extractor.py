"""Unit tests — ``extract/lockfiles.py``'s I/O-matrix rows (Story 2.6):
``PixiLockExtractor`` + ``CondaLockExtractor`` exercised directly, no CLI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.warden.discovery import CONDA_LOCK_KIND, PIXI_LOCK_KIND
from pyforge.warden.extract import UnparsableManifestError
from pyforge.warden.extract import _identity, lockfiles
from pyforge.warden.extract.lockfiles import (
    CONDA_LOCK_CONDA_SECTION,
    CONDA_LOCK_PYPI_SECTION,
    PIXI_LOCK_CONDA_SECTION,
    PIXI_LOCK_PYPI_SECTION,
    CondaLockExtractor,
    PixiLockExtractor,
)
from pyforge.warden.extract.pyproject import PyprojectExtractor
from pyforge.warden.inventory import merge_components
from pyforge.warden.models import (
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    ScannedManifest,
    WithholdReason,
)
from pyforge.warden.routing import DefaultRouter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects"
PIXI_LOCK_MANIFEST = ScannedManifest(path="pixi.lock", kind=PIXI_LOCK_KIND)
CONDA_LOCK_MANIFEST = ScannedManifest(path="conda-lock.yml", kind=CONDA_LOCK_KIND)


def _pixi_lock_extractor() -> PixiLockExtractor:
    return PixiLockExtractor(DefaultRouter())


def _conda_lock_extractor() -> CondaLockExtractor:
    return CondaLockExtractor(DefaultRouter())


def write_pixi_lock(directory: Path, body: str) -> Path:
    path = directory / "pixi.lock"
    path.write_text(body, encoding="utf-8")
    return path


def write_conda_lock(directory: Path, body: str) -> Path:
    path = directory / "conda-lock.yml"
    path.write_text(body, encoding="utf-8")
    return path


# --- pixi.lock conda rows -----------------------------------------------------


def test_pixi_lock_conda_row_ordinary_url_is_unmapped_ecosystem(monkeypatch):
    # The real bundled map (Story 2.1) now maps "numpy" -- monkeypatch to a
    # deterministic empty map so this test keeps exercising the true-miss
    # path regardless of the bundled map's contents.
    # Story 2.2: the map lookup now lives in extract/_identity.py (factored
    # out of this module) -- patch it there, not on `lockfiles` itself.
    monkeypatch.setattr(_identity, "load_conda_pypi_map", lambda: {})
    path = FIXTURES / "pixi_lock_basic" / "pixi.lock"
    components = _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)
    numpy = next(c for c in components if c.name == "numpy")
    assert numpy.version == "1.26.0"
    assert numpy.ecosystem is Ecosystem.CONDA
    assert numpy.pypi_identity is None
    assert numpy.identity_source is IdentitySource.NONE
    assert numpy.cve_match_level is CveMatchLevel.NONE
    assert numpy.vuln_matchable is False
    assert numpy.indeterminate_reason is WithholdReason.UNMAPPED_ECOSYSTEM
    assert numpy.extraction_mode is ExtractionMode.PARSED
    assert [(p.manifest, p.section) for p in numpy.provenance] == [
        ("pixi.lock", PIXI_LOCK_CONDA_SECTION)
    ]


def test_pixi_lock_conda_row_verified_map_hit_resolves_pypi_identity(monkeypatch):
    """A verified-confidence map hit sets pypi_identity + vuln_matchable
    (Story 2.1 AC2)."""
    monkeypatch.setattr(
        _identity,
        "load_conda_pypi_map",
        lambda: {
            "numpy": {
                "pypi_name": "numpy",
                "match_source": "parselmouth",
                "match_confidence": "verified",
            }
        },
    )
    path = FIXTURES / "pixi_lock_basic" / "pixi.lock"
    components = _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)
    numpy = next(c for c in components if c.name == "numpy")
    assert numpy.pypi_identity is not None
    assert numpy.pypi_identity.name == "numpy"
    assert numpy.pypi_identity.version == "1.26.0"
    assert numpy.identity_source is IdentitySource.MAP
    assert numpy.mapping_confidence == "verified"
    assert numpy.vuln_matchable is True
    assert numpy.indeterminate_reason is None


def test_pixi_lock_conda_row_low_confidence_map_hit_withholds(monkeypatch):
    """A "likely"-confidence map hit withholds identity as
    UNMAPPED_ECOSYSTEM (Story 2.1 AC3) -- never a silent clean/match --
    but the raw confidence tier survives on mapping_confidence."""
    monkeypatch.setattr(
        _identity,
        "load_conda_pypi_map",
        lambda: {
            "numpy": {
                "pypi_name": "numpy",
                "match_source": "name_coincidence",
                "match_confidence": "likely",
            }
        },
    )
    path = FIXTURES / "pixi_lock_basic" / "pixi.lock"
    components = _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)
    numpy = next(c for c in components if c.name == "numpy")
    assert numpy.pypi_identity is None
    assert numpy.identity_source is IdentitySource.NONE
    assert numpy.mapping_confidence == "likely"
    assert numpy.vuln_matchable is False
    assert numpy.indeterminate_reason is WithholdReason.UNMAPPED_ECOSYSTEM


def test_url_basename_pitfall_regression():
    """The shipped-parser regression: a subdir segment must never be
    mis-captured as the package name — name=_openmp_mutex, version=4.5
    EXACTLY, never 'linux' or 'linux-64/_openmp_mutex'."""
    path = FIXTURES / "pixi_lock_url_basename_pitfall" / "pixi.lock"
    (component,) = _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)
    assert component.name == "_openmp_mutex"
    assert component.version == "4.5"
    assert component.ecosystem is Ecosystem.CONDA


def test_pixi_lock_conda_row_unparseable_basename_is_raw_malformed(tmp_path):
    body = "version: 6\npackages:\n- conda: /not/a/valid/conda/package/shape\n"
    path = write_pixi_lock(tmp_path, body)
    (component,) = _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.version is None
    assert component.pypi_identity is None
    assert component.vuln_matchable is False
    assert component.indeterminate_reason is WithholdReason.NO_VERSION
    assert component.name == "/not/a/valid/conda/package/shape"  # kept, never dropped


# --- pixi.lock pypi rows ------------------------------------------------------


def test_pixi_lock_pypi_row_explicit_name_version():
    path = FIXTURES / "pixi_lock_basic" / "pixi.lock"
    components = _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)
    bsl = next(c for c in components if c.name == "boring-semantic-layer")
    assert bsl.version == "0.3.15"
    assert bsl.ecosystem is Ecosystem.PYPI
    assert bsl.identity_source is IdentitySource.LOCK
    assert bsl.pypi_identity is not None
    assert bsl.pypi_identity.name == "boring-semantic-layer"
    assert bsl.pypi_identity.version == "0.3.15"
    assert bsl.vuln_matchable is True
    assert bsl.cve_match_level is CveMatchLevel.EXACT
    assert bsl.indeterminate_reason is None
    assert [(p.manifest, p.section) for p in bsl.provenance] == [
        ("pixi.lock", PIXI_LOCK_PYPI_SECTION)
    ]


def test_pixi_lock_pypi_row_missing_both_fields_is_raw_malformed(tmp_path):
    body = (
        "version: 6\n"
        "packages:\n"
        "- pypi: https://files.pythonhosted.org/packages/aa/bb/"
        "mystery-1.0-py3-none-any.whl\n"
    )
    path = write_pixi_lock(tmp_path, body)
    (component,) = _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.pypi_identity is None
    assert component.vuln_matchable is False
    assert component.indeterminate_reason is WithholdReason.NO_VERSION


# --- structural (whole-manifest) failures -------------------------------------


def test_pixi_lock_document_none_yields_no_components(tmp_path):
    path = write_pixi_lock(tmp_path, "")
    assert _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST) == ()


def test_pixi_lock_non_mapping_document_raises_unparsable(tmp_path):
    path = write_pixi_lock(tmp_path, "- just\n- a\n- list\n")
    with pytest.raises(UnparsableManifestError):
        _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)


def test_pixi_lock_packages_wrong_type_raises_unparsable(tmp_path):
    path = write_pixi_lock(tmp_path, "version: 6\npackages: not-a-list\n")
    with pytest.raises(UnparsableManifestError):
        _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)


def test_pixi_lock_entry_neither_conda_nor_pypi_raises_unparsable(tmp_path):
    path = write_pixi_lock(tmp_path, "version: 6\npackages:\n- name: mystery\n")
    with pytest.raises(UnparsableManifestError):
        _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)


def test_pixi_lock_malformed_yaml_raises_unparsable(tmp_path):
    path = write_pixi_lock(tmp_path, "packages: [\n  - broken\n")
    with pytest.raises(UnparsableManifestError):
        _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)


def test_pixi_lock_empty_packages_list_yields_no_components_no_error(tmp_path):
    """FR6: empty ≠ unresolved — a valid, empty packages: list parses
    successfully with 0 components (the manifest still 'parsed')."""
    path = write_pixi_lock(tmp_path, "version: 6\npackages: []\n")
    assert _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST) == ()


# --- NFR-S5 bounds -------------------------------------------------------------


def test_oversized_lockfile_raises_unparsable(tmp_path, monkeypatch):
    monkeypatch.setattr(lockfiles, "_MAX_LOCKFILE_BYTES", 32)
    path = write_pixi_lock(tmp_path, "version: 6\npackages: []\n# padding padding\n")
    with pytest.raises(UnparsableManifestError, match="size cap"):
        _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)


def test_oversized_line_raises_unparsable(tmp_path, monkeypatch):
    monkeypatch.setattr(lockfiles, "_MAX_LINE_BYTES", 16)
    path = write_pixi_lock(
        tmp_path, "version: 6\n# " + ("x" * 32) + "\npackages: []\n"
    )
    with pytest.raises(UnparsableManifestError, match="length cap"):
        _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST)


def test_lockfile_within_bounds_still_parses(tmp_path, monkeypatch):
    """The caps don't false-positive on an ordinary small lockfile."""
    monkeypatch.setattr(lockfiles, "_MAX_LOCKFILE_BYTES", 1_000)
    monkeypatch.setattr(lockfiles, "_MAX_LINE_BYTES", 200)
    path = write_pixi_lock(tmp_path, "version: 6\npackages: []\n")
    assert _pixi_lock_extractor().extract(path, PIXI_LOCK_MANIFEST) == ()


# --- conda-lock.yml rows -------------------------------------------------------


def test_conda_lock_manager_conda_row_is_unmapped_ecosystem(monkeypatch):
    # The real bundled map (Story 2.1) now maps "numpy" -- monkeypatch to a
    # deterministic empty map so this test keeps exercising the true-miss
    # path regardless of the bundled map's contents.
    # Story 2.2: the map lookup now lives in extract/_identity.py (factored
    # out of this module) -- patch it there, not on `lockfiles` itself.
    monkeypatch.setattr(_identity, "load_conda_pypi_map", lambda: {})
    path = FIXTURES / "conda_lock_basic" / "conda-lock.yml"
    components = _conda_lock_extractor().extract(path, CONDA_LOCK_MANIFEST)
    numpy = next(c for c in components if c.name == "numpy")
    assert numpy.version == "1.26.0"
    assert numpy.ecosystem is Ecosystem.CONDA
    assert numpy.pypi_identity is None
    assert numpy.identity_source is IdentitySource.NONE
    assert numpy.cve_match_level is CveMatchLevel.NONE
    assert numpy.vuln_matchable is False
    assert numpy.indeterminate_reason is WithholdReason.UNMAPPED_ECOSYSTEM
    assert [(p.manifest, p.section) for p in numpy.provenance] == [
        ("conda-lock.yml", CONDA_LOCK_CONDA_SECTION)
    ]


def test_conda_lock_manager_pip_row_is_vuln_matchable():
    path = FIXTURES / "conda_lock_basic" / "conda-lock.yml"
    components = _conda_lock_extractor().extract(path, CONDA_LOCK_MANIFEST)
    requests_component = next(c for c in components if c.name == "requests")
    assert requests_component.version == "2.31.0"
    assert requests_component.ecosystem is Ecosystem.PYPI
    assert requests_component.identity_source is IdentitySource.LOCK
    assert requests_component.vuln_matchable is True
    assert requests_component.cve_match_level is CveMatchLevel.EXACT
    assert requests_component.indeterminate_reason is None
    assert [(p.manifest, p.section) for p in requests_component.provenance] == [
        ("conda-lock.yml", CONDA_LOCK_PYPI_SECTION)
    ]


def test_conda_lock_unrecognized_manager_raises_unparsable(tmp_path):
    body = (
        "version: 1\n"
        "package:\n"
        "- name: mystery\n"
        "  version: '1.0'\n"
        "  manager: rpm\n"
    )
    path = write_conda_lock(tmp_path, body)
    with pytest.raises(UnparsableManifestError):
        _conda_lock_extractor().extract(path, CONDA_LOCK_MANIFEST)


def test_conda_lock_missing_name_raises_unparsable(tmp_path):
    body = "version: 1\npackage:\n- version: '1.0'\n  manager: conda\n"
    path = write_conda_lock(tmp_path, body)
    with pytest.raises(UnparsableManifestError):
        _conda_lock_extractor().extract(path, CONDA_LOCK_MANIFEST)


def test_conda_lock_empty_package_list_yields_no_components_no_error(tmp_path):
    path = write_conda_lock(tmp_path, "version: 1\npackage: []\n")
    assert _conda_lock_extractor().extract(path, CONDA_LOCK_MANIFEST) == ()


def test_conda_lock_package_wrong_type_raises_unparsable(tmp_path):
    path = write_conda_lock(tmp_path, "version: 1\npackage: not-a-list\n")
    with pytest.raises(UnparsableManifestError):
        _conda_lock_extractor().extract(path, CONDA_LOCK_MANIFEST)


# --- design-note proof: no new merge logic is needed --------------------------


def test_lockfile_exact_version_folds_over_pyproject_range(tmp_path):
    """``inventory.merge_components``'s existing Gap-B fold lets a
    lockfile's exact version subsume a looser ``pyproject.toml`` entry of
    the same identity for free — no new merge logic needed (this story's
    Design Notes)."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\n'
        'dependencies = ["numpy>=1"]\n',
        encoding="utf-8",
    )
    pyproject_manifest = ScannedManifest(
        path="pyproject.toml", kind="pyproject.toml"
    )
    (range_component,) = PyprojectExtractor(DefaultRouter()).extract(
        pyproject_path, pyproject_manifest
    )
    assert range_component.version is None  # the range-only pyproject entry

    lock_body = (
        "version: 6\n"
        "packages:\n"
        "- pypi: https://files.pythonhosted.org/packages/aa/bb/"
        "numpy-1.26.0-py3-none-any.whl\n"
        "  name: numpy\n"
        "  version: 1.26.0\n"
    )
    lock_path = write_pixi_lock(tmp_path, lock_body)
    (lock_component,) = _pixi_lock_extractor().extract(lock_path, PIXI_LOCK_MANIFEST)
    assert lock_component.version == "1.26.0"

    (merged,) = merge_components([range_component, lock_component])
    assert merged.version == "1.26.0"
    assert merged.vuln_matchable is True
    assert merged.cve_match_level is CveMatchLevel.EXACT
