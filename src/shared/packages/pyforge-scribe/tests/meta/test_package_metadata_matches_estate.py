"""Story 33.2 / spec-pyforge-scribe CAP-28 -- the package's optional extras ask for what the estate pins.

`pyproject.toml`'s `[project.optional-dependencies]` is what a wheel install of pyforge-scribe resolves; the root
`pixi.toml`'s `[feature.pyforge-scribe.dependencies]` is what the estate installs. Until 2026-11-10 the two disagreed:
the `postgres` extra asked `psycopg>=3.3.4`, past the `<3.2.11` cap the PostgreSQL 17 rule holds (fnd:CAP-12), and the
graphify and cocoindex floors trailed the estate's. Each extra's requirement now equals the estate's pin for the same
package, cap included; a drift fails and names the extra.

The conda manifest's python floor is not held here: eight package manifests carry the same defect, so that guard
belongs to the estate detector, `scripts/target_version_check.py` (steward-station's).
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

# Story 33.1 (spec-pyforge-scribe CAP-31, relay of spec-pyforge-steward:CAP-175): the module reads the root pixi.toml,
# outside this package, so it runs in the live-tree half.
pytestmark = pytest.mark.live_tree

ESTATE_FEATURE = "pyforge-scribe"
PACKAGE = Path("src/shared/packages/pyforge-scribe")

#: `name[extras] specifier ; marker` -- the PEP 508 shapes an extra in this package uses.
_REQUIREMENT = re.compile(r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?P<spec>[^;]*?)\s*(?:;.*)?$")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / PACKAGE / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + the pyforge-scribe package)")


def _canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _clauses(spec: str) -> frozenset[str]:
    """A specifier as its set of clauses, whitespace and order ignored; `*` is no constraint."""
    return frozenset(clause.replace(" ", "") for clause in spec.split(",") if clause.strip() not in ("", "*"))


def package_extras(pyproject: Path) -> dict[str, list[str]]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return dict(data["project"].get("optional-dependencies", {}))


def estate_pins(pixi: Path, feature: str = ESTATE_FEATURE) -> dict[str, object]:
    data = tomllib.loads(pixi.read_text(encoding="utf-8"))
    return dict(data["feature"][feature]["dependencies"])


def extras_drift(extras: Mapping[str, Sequence[str]], estate: Mapping[str, object]) -> list[str]:
    """One line per requirement of an extra that differs from the estate's pin for that package, naming the extra."""
    pins = {_canonical(name): pin for name, pin in estate.items()}
    problems: list[str] = []
    for extra, requirements in sorted(extras.items()):
        for requirement in requirements:
            match = _REQUIREMENT.match(requirement)
            if match is None:
                problems.append(f"extra {extra!r}: cannot read requirement {requirement!r}")
                continue
            name = match["name"]
            pin = pins.get(_canonical(name))
            if isinstance(pin, Mapping):
                pin = pin.get("version")
            if not isinstance(pin, str):
                problems.append(
                    f"extra {extra!r}: {name} has no version pin in [feature.{ESTATE_FEATURE}.dependencies]"
                )
                continue
            have, want = _clauses(match["spec"]), _clauses(pin)
            if have != want:
                problems.append(
                    f"extra {extra!r}: {requirement!r} is not the estate pin {name} {pin!r} "
                    f"(missing {sorted(want - have)}, not in the estate {sorted(have - want)})"
                )
    return problems


def test_every_extra_matches_the_estate_pin() -> None:
    root = _repo_root()
    extras = package_extras(root / PACKAGE / "pyproject.toml")
    assert extras, "pyforge-scribe declares no optional extras; the guard would hold nothing"
    drift = extras_drift(extras, estate_pins(root / "pixi.toml"))
    assert not drift, "pyproject.toml extras drifted from the estate:\n" + "\n".join(drift)


# --- planted drift: the guard names each one ----------------------------------------------------------------------

ESTATE = {
    "psycopg": ">=3.2.10,<3.2.11",
    "graphifyy": ">=0.9.89",
    "cocoindex": ">=1.0.25",
    "pyforge-core": {"path": "src/shared/packages/pyforge-core"},
}


def test_matching_extras_pass_whatever_the_clause_order() -> None:
    extras = {
        "postgres": ["psycopg <3.2.11, >=3.2.10"],
        "graphify": ["graphifyy>=0.9.89"],
        "cocoindex": ["cocoindex >= 1.0.25"],
    }
    assert extras_drift(extras, ESTATE) == []


def test_a_floor_below_the_estate_pin_is_named() -> None:
    drift = extras_drift({"graphify": ["graphifyy>=0.9.51"]}, ESTATE)
    assert len(drift) == 1
    assert "extra 'graphify'" in drift[0] and ">=0.9.89" in drift[0] and ">=0.9.51" in drift[0]


def test_a_missing_cap_is_named() -> None:
    drift = extras_drift({"postgres": ["psycopg>=3.2.10"]}, ESTATE)
    assert len(drift) == 1
    assert "extra 'postgres'" in drift[0] and "<3.2.11" in drift[0]


def test_a_floor_past_the_estate_cap_is_named() -> None:
    drift = extras_drift({"postgres": ["psycopg>=3.3.4"]}, ESTATE)
    assert len(drift) == 1
    assert "extra 'postgres'" in drift[0] and ">=3.3.4" in drift[0]


@pytest.mark.parametrize("name", ["sqlalchemy", "pyforge-core"])
def test_a_package_the_estate_does_not_pin_is_named(name: str) -> None:
    drift = extras_drift({"orm": [f"{name}>=2"]}, ESTATE)
    assert drift == [f"extra 'orm': {name} has no version pin in [feature.{ESTATE_FEATURE}.dependencies]"]


def test_a_drifted_manifest_pair_on_disk_is_named(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\n[project.optional-dependencies]\n'
        'postgres = ["psycopg>=3.2.10,<3.2.11"]\ncocoindex = ["cocoindex>=1.0.20"]\n',
        encoding="utf-8",
    )
    (tmp_path / "pixi.toml").write_text(
        '[feature.pyforge-scribe.dependencies]\npsycopg = ">=3.2.10,<3.2.11"\ncocoindex = ">=1.0.25"\n',
        encoding="utf-8",
    )
    drift = extras_drift(package_extras(tmp_path / "pyproject.toml"), estate_pins(tmp_path / "pixi.toml"))
    assert len(drift) == 1
    assert "extra 'cocoindex'" in drift[0] and ">=1.0.25" in drift[0]
