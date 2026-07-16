"""Unit tests — ``extract/environment_yml.py``'s I/O-matrix rows (Story
2.2): ``EnvironmentYmlExtractor`` exercised directly, no CLI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.warden.discovery import ENVIRONMENT_YML_KIND
from pyforge.warden.extract import UnparsableManifestError
from pyforge.warden.extract.environment_yml import (
    ENVIRONMENT_YML_DEPENDENCIES_SECTION,
    ENVIRONMENT_YML_PIP_SECTION,
    EnvironmentYmlExtractor,
)
from pyforge.warden.models import (
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    ScannedManifest,
    WithholdReason,
)
from pyforge.warden.routing import DefaultRouter

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "projects"
    / "environment_yml_common"
    / "environment.yml"
)
MANIFEST = ScannedManifest(path="environment.yml", kind=ENVIRONMENT_YML_KIND)


def _extractor() -> EnvironmentYmlExtractor:
    return EnvironmentYmlExtractor(DefaultRouter())


def write_env(directory: Path, body: str) -> Path:
    path = directory / "environment.yml"
    path.write_text(body, encoding="utf-8")
    return path


# --- common-case fixture (I/O matrix row: nested pip) -------------------------


def test_common_case_fixture_yields_conda_and_pypi_rows():
    components = _extractor().extract(FIXTURE, MANIFEST)
    by_name = {c.name: c for c in components}
    assert set(by_name) == {"python", "numpy", "requests"}

    python = by_name["python"]
    assert python.ecosystem is Ecosystem.CONDA
    # Contiguous single `=` is conda's legacy fuzzy-prefix match -- withheld,
    # never treated as exact.
    assert python.version is None
    assert [p.section for p in python.provenance] == [
        ENVIRONMENT_YML_DEPENDENCIES_SECTION
    ]

    numpy = by_name["numpy"]
    assert numpy.ecosystem is Ecosystem.CONDA
    assert numpy.version is None  # >=1.20 is a range

    requests_component = by_name["requests"]
    assert requests_component.ecosystem is Ecosystem.PYPI
    assert requests_component.version == "2.31.0"
    assert requests_component.identity_source is IdentitySource.NATIVE
    assert requests_component.cve_match_level is CveMatchLevel.EXACT
    assert requests_component.vuln_matchable is True
    assert [p.section for p in requests_component.provenance] == [
        ENVIRONMENT_YML_PIP_SECTION
    ]


# --- conda matchspec parsing ----------------------------------------------------


def test_bare_conda_dep_is_no_version(tmp_path):
    path = write_env(tmp_path, "dependencies:\n  - python\n")
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "python"
    assert component.version is None
    assert component.indeterminate_reason in (
        WithholdReason.UNMAPPED_ECOSYSTEM,
        WithholdReason.NO_VERSION,
    )


def test_exact_double_equals_conda_dep_is_concrete(tmp_path):
    path = write_env(tmp_path, "dependencies:\n  - mypkg==1.2.3\n")
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "mypkg"
    assert component.version == "1.2.3"


def test_range_conda_dep_is_withheld(tmp_path):
    path = write_env(tmp_path, "dependencies:\n  - mypkg>=1.2.3\n")
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.version is None


# --- pip list: PEP 508 parsing --------------------------------------------------


def test_pip_range_dep_is_withheld_range_only(tmp_path):
    path = write_env(
        tmp_path, "dependencies:\n  - pip:\n      - requests>=2.0\n"
    )
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.ecosystem is Ecosystem.PYPI
    assert component.version is None
    assert component.indeterminate_reason == WithholdReason.RANGE_ONLY


def test_pip_invalid_requirement_is_raw_malformed(tmp_path):
    raw = "not a valid requirement !!!"
    path = write_env(tmp_path, f"dependencies:\n  - pip:\n      - '{raw}'\n")
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.name == raw


def test_pip_non_list_of_strings_raises_unparsable(tmp_path):
    path = write_env(tmp_path, "dependencies:\n  - pip:\n      - 42\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


# --- unrecognized entry shapes degrade, never crash ----------------------------


def test_unrecognized_dict_entry_is_raw_malformed(tmp_path):
    path = write_env(tmp_path, "dependencies:\n  - conda-forge: extra\n")
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.ecosystem is Ecosystem.CONDA


def test_non_string_non_dict_entry_is_raw_malformed(tmp_path):
    path = write_env(tmp_path, "dependencies:\n  - 42\n")
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED


# --- structural (whole-manifest) failures ---------------------------------------


def test_document_none_yields_no_components(tmp_path):
    path = write_env(tmp_path, "")
    assert _extractor().extract(path, MANIFEST) == ()


def test_non_mapping_document_raises_unparsable(tmp_path):
    path = write_env(tmp_path, "- just\n- a\n- list\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_malformed_yaml_raises_unparsable(tmp_path):
    path = write_env(tmp_path, "dependencies: [\n  - broken\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_missing_dependencies_key_yields_no_components(tmp_path):
    path = write_env(tmp_path, "name: myenv\n")
    assert _extractor().extract(path, MANIFEST) == ()


def test_dependencies_wrong_type_raises_unparsable(tmp_path):
    path = write_env(tmp_path, "dependencies: not-a-list\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_empty_dependencies_list_yields_no_components_no_error(tmp_path):
    path = write_env(tmp_path, "dependencies: []\n")
    assert _extractor().extract(path, MANIFEST) == ()


# --- NFR-S5 bounds -----------------------------------------------------------


def test_oversized_manifest_raises_unparsable(tmp_path, monkeypatch):
    from pyforge.warden.extract import environment_yml

    monkeypatch.setattr(environment_yml, "_MAX_MANIFEST_BYTES", 32)
    path = write_env(tmp_path, "dependencies: []\n# padding padding padding\n")
    with pytest.raises(UnparsableManifestError, match="size cap"):
        _extractor().extract(path, MANIFEST)


def test_oversized_line_raises_unparsable(tmp_path, monkeypatch):
    from pyforge.warden.extract import environment_yml

    monkeypatch.setattr(environment_yml, "_MAX_LINE_BYTES", 16)
    path = write_env(tmp_path, "dependencies: []\n# " + ("x" * 32) + "\n")
    with pytest.raises(UnparsableManifestError, match="length cap"):
        _extractor().extract(path, MANIFEST)


# --- routing -------------------------------------------------------------------


def test_router_routes_conda_and_pip_sections():
    router = DefaultRouter()
    assert (
        router.route(ENVIRONMENT_YML_KIND, ENVIRONMENT_YML_DEPENDENCIES_SECTION)
        is Ecosystem.CONDA
    )
    assert (
        router.route(ENVIRONMENT_YML_KIND, ENVIRONMENT_YML_PIP_SECTION)
        is Ecosystem.PYPI
    )
