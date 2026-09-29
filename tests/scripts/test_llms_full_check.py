"""Unit tests for scripts/llms_full_check.py (spec-library-catalog-manifest-sync
CAP-2) -- covers the station-manifest scan added 2026-09-12: every
src/shared/packages/pyforge-*/pixi.toml's [package.run-dependencies] table must
be merged into the same active-dependency set the root-pixi.toml walk builds,
so a station declaring a real run-dep only in its own manifest is caught the
same way an undocumented root pixi.toml dep is today.

Mirrors tests/scripts/test_failure_catalog_check.py's fixture style (tmp-dir
based, reaching the module the same way, since scripts/ has no __init__.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import llms_full_check as lfc  # noqa: E402  (sys.path must be set up first)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_station_run_deps_merges_nested_manifests(tmp_path, monkeypatch):
    """A dep declared only in a station's own [package.run-dependencies] is
    picked up by station_run_deps(), including its path-dep entries."""
    station_dir = tmp_path / "src" / "shared" / "packages" / "pyforge-fake"
    _write(
        station_dir / "pixi.toml",
        """
        [package]
        name = "pyforge-fake"

        [package.run-dependencies]
        python = ">=3.14"
        real-but-undeclared = ">=1.2.3"
        pyforge-core = { path = "../pyforge-core" }
        """,
    )
    monkeypatch.setattr(
        lfc, "STATION_MANIFESTS",
        sorted((tmp_path / "src" / "shared" / "packages").glob("pyforge-*/pixi.toml")),
    )

    deps = lfc.station_run_deps()

    assert deps["real-but-undeclared"] == {">=1.2.3"}
    assert deps["pyforge-core"] == {"*"}  # path dep with no version key
    assert "python" in deps


def test_run_flags_a_station_only_dep_as_undocumented(tmp_path, monkeypatch):
    """CAP-2's stated success criterion: a synthetic station-manifest entry
    not mirrored in root pixi.toml or documented in the catalog is caught as
    undocumented-dep."""
    _write(tmp_path / "pixi.toml", '[feature.python.dependencies]\npython = ">=3.14"\n')
    _write(tmp_path / "catalog.md", "# Catalog\n\n- **python** (>=3.14) — the interpreter.\n")
    station_dir = tmp_path / "src" / "shared" / "packages" / "pyforge-fake"
    _write(
        station_dir / "pixi.toml",
        '[package.run-dependencies]\nreal-but-undeclared = ">=1.2.3"\n',
    )

    monkeypatch.setattr(lfc, "MANIFEST", tmp_path / "pixi.toml")
    monkeypatch.setattr(lfc, "CATALOG", tmp_path / "catalog.md")
    monkeypatch.setattr(
        lfc, "STATION_MANIFESTS",
        sorted((tmp_path / "src" / "shared" / "packages").glob("pyforge-*/pixi.toml")),
    )

    findings, _stats = lfc.run()

    assert any(
        f["kind"] == "undocumented-dep" and f["name"] == "real-but-undeclared"
        for f in findings
    )


def test_run_stays_clean_when_station_dep_is_mirrored_and_documented(tmp_path, monkeypatch):
    """The existing exit-code contract is unchanged: once the station-only dep
    is mirrored in root pixi.toml and documented, the merged check is clean."""
    _write(
        tmp_path / "pixi.toml",
        '[feature.python.dependencies]\npython = ">=3.14"\nreal-but-undeclared = ">=1.2.3"\n',
    )
    _write(
        tmp_path / "catalog.md",
        "# Catalog\n\n"
        "- **python** (>=3.14) — the interpreter.\n"
        "- **real-but-undeclared** (>=1.2.3) — a fixture dep.\n",
    )
    station_dir = tmp_path / "src" / "shared" / "packages" / "pyforge-fake"
    _write(
        station_dir / "pixi.toml",
        '[package.run-dependencies]\nreal-but-undeclared = ">=1.2.3"\n',
    )

    monkeypatch.setattr(lfc, "MANIFEST", tmp_path / "pixi.toml")
    monkeypatch.setattr(lfc, "CATALOG", tmp_path / "catalog.md")
    monkeypatch.setattr(
        lfc, "STATION_MANIFESTS",
        sorted((tmp_path / "src" / "shared" / "packages").glob("pyforge-*/pixi.toml")),
    )

    findings, _stats = lfc.run()

    assert findings == []


def test_no_station_manifests_falls_back_to_root_only_behavior(tmp_path, monkeypatch):
    """An empty STATION_MANIFESTS list (e.g. no pyforge-* dirs) degrades
    gracefully -- the pre-2026-09-12 root-pixi.toml-only behavior is
    unchanged, never a crash."""
    _write(tmp_path / "pixi.toml", '[feature.python.dependencies]\npython = ">=3.14"\n')
    _write(tmp_path / "catalog.md", "# Catalog\n\n- **python** (>=3.14) — the interpreter.\n")

    monkeypatch.setattr(lfc, "MANIFEST", tmp_path / "pixi.toml")
    monkeypatch.setattr(lfc, "CATALOG", tmp_path / "catalog.md")
    monkeypatch.setattr(lfc, "STATION_MANIFESTS", [])

    findings, stats = lfc.run()

    assert findings == []
    assert stats["manifest_deps"] == 1


def test_real_repo_station_manifests_all_resolve(monkeypatch):
    """Sanity check against the real repo: every real
    src/shared/packages/pyforge-*/pixi.toml's [package.run-dependencies]
    table parses without error and contributes at least one name (never a
    silently-empty scan of a real fixture set)."""
    deps = lfc.station_run_deps()
    assert deps  # the real repo has 10 pyforge-* stations; several declare real-run-deps
    assert "python" in deps
