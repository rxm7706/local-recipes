"""CI parity matrix: every introspected station verb is reachable through
``pyforge <station> …`` (Story 22.1, FR-13). Generating this matrix is the
build; a verb the unified entry cannot reach, or a silent skip of an
unintrospectable CLI, fails CI.
"""

from __future__ import annotations

import ast
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pytest
from conftest import PACKAGES_ROOT

from pyforge.core.dispatch import (
    PREPARATORY_UNINTROSPECTABLE,
    SKIP_DISTRIBUTIONS,
    DispatchError,
    dispatch_argv,
    primary_console_script,
    script_map_from_packages_root,
    station_token_from_dist_name,
)


class ParityMatrixError(AssertionError):
    """Raised when the matrix would silently skip a station CLI."""


@dataclass(frozen=True)
class ParityRow:
    station: str
    primary_script: str
    verb: str | None
    preparatory: str | None


def _station_package_dirs(packages_root: Path) -> list[Path]:
    return sorted(
        p
        for p in packages_root.iterdir()
        if p.is_dir() and p.name.startswith("pyforge-") and p.name not in SKIP_DISTRIBUTIONS
    )


def _parser_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr == "add_parser":
            if node.args and isinstance(node.args[0], ast.Constant):
                value = node.args[0].value
                if isinstance(value, str) and value:
                    names.add(value)
        elif func.attr == "command":
            if node.args and isinstance(node.args[0], ast.Constant):
                value = node.args[0].value
                if isinstance(value, str) and value:
                    names.add(value)
        elif func.attr == "add_typer":
            for kw in node.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    value = kw.value.value
                    if isinstance(value, str) and value:
                        names.add(value)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            if not isinstance(dec.func, ast.Attribute):
                continue
            if dec.func.attr != "command":
                continue
            if not dec.args:
                names.add(node.name)
    return names


def introspect_verbs(station_dir: Path) -> set[str]:
    verbs: set[str] = set()
    src = station_dir / "src" / "pyforge"
    if not src.is_dir():
        return verbs
    for path in src.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        verbs.update(_parser_names(tree))
    return verbs


def _preparatory_spec_path(stem: str) -> Path:
    """Resolve a preparatory story spec to its owning BMAD project tree."""
    repo = PACKAGES_ROOT.parents[2] / "_bmad-output" / "projects"
    if stem.startswith("spec-24-3-atlas") or stem.startswith("spec-25-3-atlas"):
        project = "pyforge-atlas"
    else:
        project = "pyforge-steward"
    return repo / project / "planning-artifacts" / "specs" / f"{stem}.md"


def generate_parity_matrix(packages_root: Path) -> list[ParityRow]:
    mapping = script_map_from_packages_root(packages_root)
    rows: list[ParityRow] = []
    skipped_silent: list[str] = []
    for station_dir in _station_package_dirs(packages_root):
        token = station_token_from_dist_name(station_dir.name)
        pyproject = station_dir / "pyproject.toml"
        scripts = {}
        if pyproject.is_file():
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            scripts = dict((data.get("project") or {}).get("scripts") or {})
        if not scripts:
            continue
        primary = mapping.get(token) or primary_console_script(station_dir.name, scripts)
        if primary is None:
            raise ParityMatrixError(
                f"station {token!r} has console scripts {sorted(scripts)} but "
                "no primary script the unified entry can dispatch to"
            )
        verbs = introspect_verbs(station_dir)
        prep = PREPARATORY_UNINTROSPECTABLE.get(token)
        if not verbs:
            if not prep:
                skipped_silent.append(token)
                continue
            rows.append(
                ParityRow(
                    station=token,
                    primary_script=primary,
                    verb=None,
                    preparatory=prep,
                )
            )
            continue
        if prep:
            raise ParityMatrixError(
                f"station {token!r} is listed as unintrospectable ({prep}) but AST found verbs {sorted(verbs)}"
            )
        for verb in sorted(verbs):
            rows.append(
                ParityRow(
                    station=token,
                    primary_script=primary,
                    verb=verb,
                    preparatory=None,
                )
            )
    if skipped_silent:
        raise ParityMatrixError(
            "station CLI(s) could not be introspected and have no named "
            f"preparatory story: {skipped_silent}. Add "
            "PREPARATORY_UNINTROSPECTABLE[<token>] = '<spec-stem>' rather "
            "than skipping silently."
        )
    return rows


def test_ci_generates_parity_matrix_and_every_verb_is_reachable():
    matrix = generate_parity_matrix(PACKAGES_ROOT)
    assert matrix, "parity matrix was empty"
    mapping = script_map_from_packages_root(PACKAGES_ROOT)
    for row in matrix:
        rest = [row.verb] if row.verb else ["--help"]
        child = dispatch_argv(["pyforge", row.station, *rest], script_map=mapping)
        assert child[0] == row.primary_script
        assert child[1:] == rest
        if row.verb is None:
            assert row.preparatory
            spec = _preparatory_spec_path(row.preparatory)
            assert spec.is_file(), f"named preparatory story missing: {spec}"


def test_unmapped_station_with_a_verb_fails_the_matrix(tmp_path: Path):
    pkg = tmp_path / "pyforge-ghost"
    (pkg / "src" / "pyforge" / "ghost").mkdir(parents=True)
    (pkg / "pyproject.toml").write_text(
        '[project]\nname = "pyforge-ghost"\n[project.scripts]\nghost = "pyforge.ghost.cli:main"\n',
        encoding="utf-8",
    )
    (pkg / "src" / "pyforge" / "ghost" / "cli.py").write_text(
        "def build():\n    p.add_parser('haunt')\n",
        encoding="utf-8",
    )
    mapping = script_map_from_packages_root(tmp_path)
    assert "ghost" in mapping
    broken = {k: v for k, v in mapping.items() if k != "ghost"}
    verbs = introspect_verbs(pkg)
    assert "haunt" in verbs
    with pytest.raises(DispatchError, match="unknown station"):
        dispatch_argv(["pyforge", "ghost", "haunt"], script_map=broken)


def test_silent_skip_without_preparatory_story_fails(tmp_path: Path):
    pkg = tmp_path / "pyforge-mute"
    (pkg / "src" / "pyforge" / "mute").mkdir(parents=True)
    (pkg / "pyproject.toml").write_text(
        '[project]\nname = "pyforge-mute"\n[project.scripts]\nmute = "pyforge.mute.cli:main"\n',
        encoding="utf-8",
    )
    (pkg / "src" / "pyforge" / "mute" / "cli.py").write_text(
        "def main():\n    raise SystemExit(0)\n",
        encoding="utf-8",
    )
    with pytest.raises(ParityMatrixError, match="no named preparatory story"):
        generate_parity_matrix(tmp_path)


def test_dispatch_module_does_not_copy_station_duty_tables():
    source = (Path(__file__).resolve().parents[2] / "src" / "pyforge" / "core" / "dispatch.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "encrypt a file",
        "find_run_command",
        "DUTIES",
        "ComplianceReport",
        "Kedro",
    )
    for needle in forbidden:
        assert needle not in source, f"station logic leaked into dispatch: {needle}"
