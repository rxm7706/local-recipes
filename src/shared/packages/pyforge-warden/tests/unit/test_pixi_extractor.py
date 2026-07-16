"""Unit tests — ``extract/pixi.py``'s I/O-matrix rows (Story 2.2):
``PixiTomlExtractor`` exercised directly, no CLI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.warden.discovery import PIXI_TOML_KIND
from pyforge.warden.extract import UnparsableManifestError
from pyforge.warden.extract.pixi import (
    BASE_DEPENDENCIES_SECTION,
    BASE_PYPI_DEPENDENCIES_SECTION,
    FEATURE_DEPENDENCIES_SECTION,
    FEATURE_PYPI_DEPENDENCIES_SECTION,
    TARGET_DEPENDENCIES_SECTION,
    TARGET_PYPI_DEPENDENCIES_SECTION,
    PixiTomlExtractor,
)
from pyforge.warden.models import Ecosystem, ScannedManifest
from pyforge.warden.routing import DefaultRouter

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "projects"
    / "pixi_toml_common"
    / "pixi.toml"
)
MANIFEST = ScannedManifest(path="pixi.toml", kind=PIXI_TOML_KIND)


def _extractor() -> PixiTomlExtractor:
    return PixiTomlExtractor(DefaultRouter())


def write_pixi_toml(directory: Path, body: str) -> Path:
    path = directory / "pixi.toml"
    path.write_text(body, encoding="utf-8")
    return path


# --- common-case fixture (I/O matrix row: feature/target tables) -------------


def test_common_case_fixture_covers_base_feature_and_target_tables():
    components = _extractor().extract(FIXTURE, MANIFEST)
    by_name = {c.name: c for c in components}
    assert set(by_name) == {
        "python",
        "numpy",
        "requests",
        "pytest",
        "coverage",
        "compilers",
        "psutil",
    }

    assert by_name["python"].ecosystem is Ecosystem.CONDA
    assert [p.section for p in by_name["python"].provenance] == [
        BASE_DEPENDENCIES_SECTION
    ]

    requests_component = by_name["requests"]
    assert requests_component.ecosystem is Ecosystem.PYPI
    assert requests_component.version == "2.31.0"
    assert [p.section for p in requests_component.provenance] == [
        BASE_PYPI_DEPENDENCIES_SECTION
    ]

    pytest_component = by_name["pytest"]
    assert pytest_component.ecosystem is Ecosystem.CONDA
    assert [p.section for p in pytest_component.provenance] == [
        "feature.test.dependencies"
    ]

    coverage = by_name["coverage"]
    assert coverage.ecosystem is Ecosystem.PYPI
    assert [p.section for p in coverage.provenance] == [
        "feature.test.pypi-dependencies"
    ]

    compilers = by_name["compilers"]
    assert compilers.ecosystem is Ecosystem.CONDA
    assert [p.section for p in compilers.provenance] == [
        "target.linux-64.dependencies"
    ]

    psutil_component = by_name["psutil"]
    assert psutil_component.ecosystem is Ecosystem.PYPI
    assert [p.section for p in psutil_component.provenance] == [
        "target.linux-64.pypi-dependencies"
    ]


# --- conda-dependency TOML value shapes ---------------------------------------


def test_conda_dep_bare_string_wildcard_is_no_version(tmp_path):
    path = write_pixi_toml(tmp_path, '[dependencies]\npython = "*"\n')
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "python"
    assert component.version is None


def test_conda_dep_exact_equals_string_is_concrete(tmp_path):
    path = write_pixi_toml(tmp_path, '[dependencies]\nmypkg = "==1.2.3"\n')
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.version == "1.2.3"


def test_conda_dep_table_value_reads_version_subkey(tmp_path):
    path = write_pixi_toml(
        tmp_path,
        '[dependencies]\nmypkg = { version = "==1.2.3", channel = "conda-forge" }\n',
    )
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "mypkg"
    assert component.version == "1.2.3"


def test_conda_dep_table_value_without_version_subkey_is_bare(tmp_path):
    path = write_pixi_toml(
        tmp_path, '[dependencies]\nmypkg = { channel = "conda-forge" }\n'
    )
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.version is None


# --- pypi-dependency TOML value shapes ------------------------------------------


def test_pypi_dep_bare_wildcard_is_no_version(tmp_path):
    path = write_pixi_toml(tmp_path, '[pypi-dependencies]\nrequests = "*"\n')
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.ecosystem is Ecosystem.PYPI
    assert component.version is None


def test_pypi_dep_exact_string_is_concrete(tmp_path):
    path = write_pixi_toml(
        tmp_path, '[pypi-dependencies]\nrequests = "==2.31.0"\n'
    )
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.version == "2.31.0"


def test_pypi_dep_table_value_reads_version_subkey(tmp_path):
    path = write_pixi_toml(
        tmp_path,
        '[pypi-dependencies]\nrequests = { version = "==2.31.0", extras = ["security"] }\n',
    )
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.version == "2.31.0"


def test_pypi_dep_range_is_withheld(tmp_path):
    path = write_pixi_toml(tmp_path, '[pypi-dependencies]\nrequests = ">=2.0"\n')
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.version is None


def test_pypi_dep_bare_version_is_treated_as_an_exact_pin(tmp_path):
    """Fix 5 (2026-07-16 review): pixi.toml's `[pypi-dependencies]` table
    allows a BARE (no-operator) version to mean an exact pin, mirroring its
    own conda `[dependencies]` table's identical convention. The old code
    concatenated `f"{name}{specifier}"` with no operator inserted, so
    `Requirement('requests2.31.0')` silently misparsed the whole thing as
    ONE bogus package literally named `requests2.31.0` with no version at
    all -- the real `requests` dependency vanished from the inventory
    entirely (a silent dependency-loss / false-green risk)."""
    path = write_pixi_toml(tmp_path, '[pypi-dependencies]\nrequests = "2.31.0"\n')
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "requests"
    assert component.version == "2.31.0"
    assert component.ecosystem is Ecosystem.PYPI
    assert component.vuln_matchable is True


def test_pypi_dep_table_value_bare_version_subkey_is_also_an_exact_pin(tmp_path):
    path = write_pixi_toml(
        tmp_path,
        '[pypi-dependencies]\nrequests = { version = "2.31.0" }\n',
    )
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "requests"
    assert component.version == "2.31.0"


# --- structural (whole-manifest) failures ---------------------------------------


def test_missing_dependencies_key_yields_no_components(tmp_path):
    path = write_pixi_toml(tmp_path, "[workspace]\nname = \"x\"\n")
    assert _extractor().extract(path, MANIFEST) == ()


def test_malformed_toml_raises_unparsable(tmp_path):
    path = write_pixi_toml(tmp_path, "[dependencies\nfoo = 1\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_dependencies_wrong_type_raises_unparsable(tmp_path):
    path = write_pixi_toml(tmp_path, "dependencies = 42\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_feature_wrong_type_raises_unparsable(tmp_path):
    path = write_pixi_toml(tmp_path, "feature = 42\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_feature_entry_wrong_type_raises_unparsable(tmp_path):
    path = write_pixi_toml(tmp_path, "feature.test = 42\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_target_wrong_type_raises_unparsable(tmp_path):
    path = write_pixi_toml(tmp_path, "target = 42\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_empty_dependencies_table_yields_no_components_no_error(tmp_path):
    path = write_pixi_toml(tmp_path, "[dependencies]\n")
    assert _extractor().extract(path, MANIFEST) == ()


def test_no_feature_or_target_tables_yields_only_base(tmp_path):
    path = write_pixi_toml(tmp_path, '[dependencies]\npython = "*"\n')
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "python"


# --- NFR-S5 bounds -----------------------------------------------------------


def test_oversized_manifest_raises_unparsable(tmp_path, monkeypatch):
    from pyforge.warden.extract import pixi

    monkeypatch.setattr(pixi, "_MAX_MANIFEST_BYTES", 32)
    path = write_pixi_toml(tmp_path, "[dependencies]\n# padding padding padding\n")
    with pytest.raises(UnparsableManifestError, match="size cap"):
        _extractor().extract(path, MANIFEST)


def test_oversized_line_raises_unparsable(tmp_path, monkeypatch):
    from pyforge.warden.extract import pixi

    monkeypatch.setattr(pixi, "_MAX_LINE_BYTES", 16)
    path = write_pixi_toml(tmp_path, "[dependencies]\n# " + ("x" * 32) + "\n")
    with pytest.raises(UnparsableManifestError, match="length cap"):
        _extractor().extract(path, MANIFEST)


# --- routing -------------------------------------------------------------------


def test_router_routes_all_six_generic_tokens():
    router = DefaultRouter()
    assert router.route(PIXI_TOML_KIND, BASE_DEPENDENCIES_SECTION) is Ecosystem.CONDA
    assert (
        router.route(PIXI_TOML_KIND, BASE_PYPI_DEPENDENCIES_SECTION)
        is Ecosystem.PYPI
    )
    assert (
        router.route(PIXI_TOML_KIND, FEATURE_DEPENDENCIES_SECTION)
        is Ecosystem.CONDA
    )
    assert (
        router.route(PIXI_TOML_KIND, FEATURE_PYPI_DEPENDENCIES_SECTION)
        is Ecosystem.PYPI
    )
    assert (
        router.route(PIXI_TOML_KIND, TARGET_DEPENDENCIES_SECTION)
        is Ecosystem.CONDA
    )
    assert (
        router.route(PIXI_TOML_KIND, TARGET_PYPI_DEPENDENCIES_SECTION)
        is Ecosystem.PYPI
    )


def test_feature_and_target_names_never_baked_into_the_routing_key(tmp_path):
    """The 6 routing tokens stay GENERIC (Boundaries) -- two differently
    named feature tables both route through the SAME token, only
    Provenance.section differs."""
    path = write_pixi_toml(
        tmp_path,
        '[feature.a.dependencies]\nfoo = "*"\n'
        '[feature.b.dependencies]\nbar = "*"\n',
    )
    components = _extractor().extract(path, MANIFEST)
    sections = sorted(p.section for c in components for p in c.provenance)
    assert sections == ["feature.a.dependencies", "feature.b.dependencies"]
