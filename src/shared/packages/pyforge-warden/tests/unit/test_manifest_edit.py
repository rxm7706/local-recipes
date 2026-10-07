"""Unit tests for ``manifest_edit`` (Story 14.2)."""

from __future__ import annotations

from pathlib import Path

from pyforge.warden.manifest_edit import edit_requirement_to_floor


def test_pixi_toml_edits_exactly_one_requirement(tmp_path: Path) -> None:
    manifest = tmp_path / "pixi.toml"
    manifest.write_text(
        '[project]\nname = "demo"\n\n[pypi-dependencies]\nleftpad = ">=1.2"\n',
        encoding="utf-8",
    )
    result = edit_requirement_to_floor(manifest, package="leftpad", floor="1.3.0")
    assert result.ok
    assert 'leftpad = ">=1.3.0"' in manifest.read_text(encoding="utf-8")
    assert ">=1.2" not in manifest.read_text(encoding="utf-8")


def test_pyproject_preserves_surrounding_formatting(tmp_path: Path) -> None:
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text(
        '[project]\nname = "demo"\ndependencies = [\n  "requests>=2.0",\n  "leftpad>=1.2",\n]\n',
        encoding="utf-8",
    )
    result = edit_requirement_to_floor(manifest, package="leftpad", floor="1.3.0")
    assert result.ok
    text = manifest.read_text(encoding="utf-8")
    assert '"leftpad>=1.3.0"' in text
    assert "requests>=2.0" in text


def test_recipe_requirement_line_scoped_edit(tmp_path: Path) -> None:
    manifest = tmp_path / "recipe.yaml"
    manifest.write_text(
        "package:\n  name: demo\nrequirements:\n  run:\n    - leftpad >=1.2\n",
        encoding="utf-8",
    )
    result = edit_requirement_to_floor(manifest, package="leftpad", floor="1.3.0")
    assert result.ok
    assert "- leftpad >=1.3.0" in manifest.read_text(encoding="utf-8")


def test_jinja_declared_requirement_fails(tmp_path: Path) -> None:
    manifest = tmp_path / "recipe.yaml"
    manifest.write_text(
        "requirements:\n  run:\n    - leftpad {{ pin }}\n",
        encoding="utf-8",
    )
    result = edit_requirement_to_floor(manifest, package="leftpad", floor="1.3.0")
    assert not result.ok
    assert result.failure_reason is not None


def test_duplicate_declarations_fail(tmp_path: Path) -> None:
    manifest = tmp_path / "pixi.toml"
    manifest.write_text(
        '[pypi-dependencies]\nleftpad = ">=1.0"\nleftpad = ">=1.2"\n',
        encoding="utf-8",
    )
    result = edit_requirement_to_floor(manifest, package="leftpad", floor="1.3.0")
    assert not result.ok
