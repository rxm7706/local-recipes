"""Unit tests for ``pyforge.doctor.sources.bmad_method.gather`` (Story 10.1,
Epic 10/CAP-1) -- covers every row of the spec's I/O & Edge-Case Matrix
against REAL tmp fixture trees (a written ``pixi.toml`` +
``_bmad/_config/manifest.yaml``), mirroring
``test_sources_chain_due_for_verification.py``'s own real-fixture discipline.
The one exception is ``test_gather_degrades_on_unexpected_exception``, which
deliberately monkeypatches ``_gather`` to force an exception shape no real
fixture can produce -- proving the outer ``degrade_on_exception`` safety net
itself, not the comparison logic (review finding: the prior wording claimed
"no mocks" unconditionally).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import bmad_method

# --- fixture helpers ---------------------------------------------------------


def _write_pixi(target: Path, text: str) -> Path:
    path = target / "pixi.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _write_manifest(target: Path, text: str) -> Path:
    path = target / "_bmad" / "_config" / "manifest.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


_PIXI_SINGLE = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"
"""

_PIXI_TWO_TABLES_SAME_FLOOR = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"

[feature.local-recipes.dependencies]
bmad-method = ">=6.11.0"
"""

_PIXI_TWO_TABLES_DIFFERENT_FLOORS = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"

[feature.local-recipes.dependencies]
bmad-method = ">=6.12.0"
"""

_PIXI_NO_BMAD_METHOD = """
[feature.python.dependencies]
pixi = ">=1.0"
"""

_PIXI_UNPARSEABLE_EQUALS = """
[feature.python.dependencies]
bmad-method = "==6.11.0"
"""

_PIXI_UNPARSEABLE_STAR = """
[feature.python.dependencies]
bmad-method = "*"
"""

_MANIFEST_610 = "installation:\n  version: 6.10.0\n"
_MANIFEST_611 = "installation:\n  version: 6.11.0\n"
_MANIFEST_612 = "installation:\n  version: 6.12.0\n"
_MANIFEST_MALFORMED_SHAPE = "installation: not-a-mapping\n"
_MANIFEST_MISSING_VERSION_KEY = "installation:\n  installDate: 2026-01-01\n"
_MANIFEST_BAD_YAML = "installation: [unterminated\n"


# --- Real drift (today's live shape) -----------------------------------------


def test_installed_behind_declared_floor_reports_one_warn_naming_both_versions(
    tmp_path: Path,
) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert finding.status is DoctorStatus.WARN
    assert "6.10.0" in finding.message
    assert "6.11.0" in finding.message
    assert finding.evidence == {"installed": "6.10.0", "declared_floor": ">=6.11.0"}


# --- Agreement ----------------------------------------------------------------


def test_installed_equal_to_declared_floor_reports_one_ok(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert finding.status is DoctorStatus.OK
    assert "6.11.0" in finding.message


def test_installed_ahead_of_declared_floor_reports_one_ok(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_612)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- Multiple declarations ------------------------------------------------------


def test_two_tables_same_floor_treated_as_one_floor(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_TWO_TABLES_SAME_FLOOR)
    _write_manifest(tmp_path, _MANIFEST_611)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence["declared_floor"] == ">=6.11.0"


def test_two_tables_different_floors_uses_the_maximum(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_TWO_TABLES_DIFFERENT_FLOORS)
    _write_manifest(tmp_path, _MANIFEST_611)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    # installed 6.11.0 is behind the MAX floor (6.12.0), even though it
    # satisfies the lower of the two declared floors.
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["declared_floor"] == ">=6.12.0"


# --- pixi.toml missing bmad-method entirely --------------------------------------


def test_pixi_toml_missing_bmad_method_entirely_reports_one_warn(
    tmp_path: Path,
) -> None:
    _write_pixi(tmp_path, _PIXI_NO_BMAD_METHOD)
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert finding.status is DoctorStatus.WARN
    assert "could not be evaluated here" in finding.message


# --- pixi.toml / manifest.yaml missing or unreadable ------------------------------


def test_missing_pixi_toml_reports_one_warn(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert "could not be evaluated here" in finding.message


def test_missing_manifest_yaml_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert "could not be evaluated here" in finding.message


# --- Unparseable constraint form ---------------------------------------------------


def test_equals_constraint_form_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_UNPARSEABLE_EQUALS)
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


def test_star_constraint_form_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_UNPARSEABLE_STAR)
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


# --- manifest.yaml malformed / missing installation.version -----------------------


def test_manifest_installation_not_a_mapping_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_MALFORMED_SHAPE)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


def test_manifest_missing_version_key_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_MISSING_VERSION_KEY)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


def test_manifest_bad_yaml_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_BAD_YAML)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


# --- never raises: degrade_on_exception safety net ---------------------------------


def test_gather_never_raises_on_a_completely_empty_target_directory(
    tmp_path: Path,
) -> None:
    # An empty target dir: neither pixi.toml nor manifest.yaml exists at all.
    findings = bmad_method.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].source is Source.BMAD_METHOD_VERSION_DRIFT


def test_gather_degrades_on_unexpected_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(target: Path):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(bmad_method, "_gather", _boom)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].source is Source.BMAD_METHOD_VERSION_DRIFT
    assert "RuntimeError" in findings[0].message


# --- helper unit coverage ------------------------------------------------------


def test_parse_version_rejects_non_three_part_string() -> None:
    with pytest.raises(ValueError):
        bmad_method._parse_version("6.11")


def test_parse_version_rejects_non_digit_segment() -> None:
    with pytest.raises(ValueError):
        bmad_method._parse_version("6.x.0")


def test_parse_version_rejects_a_leading_minus_sign() -> None:
    # int("-1") succeeds, so a bare int() conversion would silently accept
    # this -- str.isdigit() is what actually rejects it (review finding).
    with pytest.raises(ValueError):
        bmad_method._parse_version("-1.2.3")


def test_declared_floors_raises_when_bmad_method_absent() -> None:
    with pytest.raises(ValueError):
        bmad_method._declared_floors({"dependencies": {}})


def test_declared_floors_reads_the_top_level_dependencies_table() -> None:
    # No fixture elsewhere in this file declares bmad-method OUTSIDE a
    # [feature.*.dependencies] table -- this exercises that first branch
    # directly (review finding: it was previously unexercised).
    data = {"dependencies": {"bmad-method": ">=6.11.0"}}
    assert bmad_method._declared_floors(data) == [(6, 11, 0)]


def test_declared_floors_picks_max_across_tables() -> None:
    data = {
        "feature": {
            "python": {"dependencies": {"bmad-method": ">=6.11.0"}},
            "local-recipes": {"dependencies": {"bmad-method": ">=6.12.0"}},
        }
    }
    assert bmad_method._declared_floors(data) == [(6, 11, 0), (6, 12, 0)]


def test_declared_floors_reads_top_level_target_scoped_tables() -> None:
    data = {
        "target": {
            "linux-64": {"dependencies": {"bmad-method": ">=6.11.0"}},
        }
    }
    assert bmad_method._declared_floors(data) == [(6, 11, 0)]


def test_declared_floors_reads_feature_target_scoped_tables() -> None:
    # pixi.toml has no bmad-method entry under a
    # [feature.*.target.*.dependencies] table today -- this proves the
    # walk would still see one if it existed (review finding: this shape
    # was previously invisible to _declared_floors entirely).
    data = {
        "feature": {
            "local-recipes": {
                "target": {
                    "win-64": {"dependencies": {"bmad-method": ">=6.13.0"}},
                },
            },
        },
    }
    assert bmad_method._declared_floors(data) == [(6, 13, 0)]
