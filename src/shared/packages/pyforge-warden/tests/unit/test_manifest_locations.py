"""Story 16.6 -- the one ``manifest_locations`` builder (scan and fleet approve)."""

from __future__ import annotations

from pathlib import Path

from pyforge.warden import cli
from pyforge.warden.actuator import Actuation
from pyforge.warden.cli import main
from pyforge.warden.inventory import PypiIdentity, ResolvedInventory
from pyforge.warden.manifest_locations import (
    manifest_locations_for_target,
    manifest_locations_from_inventory,
)
from pyforge.warden.models import Ecosystem

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_from_inventory_canonicalizes_and_unions_same_name_provenance(component_factory) -> None:
    inventory = ResolvedInventory(
        components=(
            component_factory("Foo_Bar", "1.0", provenance=(("b/pyproject.toml", "project.dependencies"),)),
            component_factory("foo-bar", "2.0", provenance=(("a/pyproject.toml", "project.dependencies"),)),
        ),
        resolved_scan_set=(),
    )
    assert manifest_locations_from_inventory(inventory) == {
        "foo-bar": (
            "a/pyproject.toml [project.dependencies]",
            "b/pyproject.toml [project.dependencies]",
        ),
    }


def test_from_inventory_keys_a_conda_component_by_its_pypi_identity_too(component_factory) -> None:
    component = component_factory(
        "pytorch",
        "2.4.0",
        Ecosystem.CONDA,
        provenance=(("environment.yml", "dependencies"),),
        pypi_identity=PypiIdentity(name="torch", version="2.4.0"),
    )
    locations = manifest_locations_from_inventory(ResolvedInventory(components=(component,), resolved_scan_set=()))
    assert locations == {
        "pytorch": ("environment.yml [dependencies]",),
        "torch": ("environment.yml [dependencies]",),
    }


def test_for_target_reads_the_tree_and_skips_an_unparsable_manifest(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", '[project]\nname = "demo"\ndependencies = ["Requests==2.31.0"]\n')
    _write(tmp_path / "broken" / "pyproject.toml", "[project\nnot toml")
    assert manifest_locations_for_target(tmp_path) == {
        "requests": ("pyproject.toml [project.dependencies]",),
    }


def test_for_target_never_writes_the_tree(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", '[project]\nname = "demo"\ndependencies = ["requests==2.31.0"]\n')
    before = sorted((p.relative_to(tmp_path), p.read_bytes()) for p in tmp_path.rglob("*") if p.is_file())
    manifest_locations_for_target(tmp_path)
    after = sorted((p.relative_to(tmp_path), p.read_bytes()) for p in tmp_path.rglob("*") if p.is_file())
    assert after == before


def test_scan_hands_the_helpers_map_to_the_actuator(monkeypatch, capsys) -> None:
    """AC4: ``warden scan`` builds its actuator input through the one helper."""
    built: list[dict[str, tuple[str, ...]]] = []
    received: dict[str, object] = {}

    def helper_spy(inventory: ResolvedInventory) -> dict[str, tuple[str, ...]]:
        result = manifest_locations_from_inventory(inventory)
        built.append(result)
        return result

    def actuator_spy(findings, **kwargs):  # noqa: ANN001
        received["manifest_locations"] = kwargs.get("manifest_locations")
        return Actuation(dry_run=True, outcomes=())

    monkeypatch.setattr(cli, "manifest_locations_from_inventory", helper_spy)
    monkeypatch.setattr(cli, "run_actuator", actuator_spy)

    target = FIXTURES / "vuln_critical"
    capsys.readouterr()
    rc = main(["scan", str(target), "--fix-prs-dry-run", "--format", "json"])
    assert rc == 1
    assert len(built) == 1
    assert received["manifest_locations"] is built[0]
    # The fleet approve's builder reads the same tree to the same map.
    assert built[0] == manifest_locations_for_target(target)
    assert built[0] == {"pdos-vuln-fixture": ("pyproject.toml [project.dependencies]",)}
