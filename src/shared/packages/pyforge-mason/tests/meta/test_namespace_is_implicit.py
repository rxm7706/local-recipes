"""The PEP 420 namespace is load-bearing, and breaking it fails SILENTLY.

If any distribution ever ships `src/pyforge/__init__.py`, that package's
directory becomes a regular package and shadows the namespace — the other
`pyforge.*` distributions stop importing when installed alongside it. Nothing
errors at build time; it only surfaces when two are installed together. So it is
pinned here rather than trusted.
"""

from __future__ import annotations

from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge"


def test_no_init_at_the_namespace_root():
    assert not (PKG_ROOT / "__init__.py").exists(), (
        "src/pyforge/__init__.py must NOT exist — its absence is what makes the "
        "pyforge namespace implicit (PEP 420) and lets the sibling stations "
        "coexist in one import root."
    )


def test_the_station_package_itself_does_have_an_init():
    assert (PKG_ROOT / "mason" / "__init__.py").exists()


def test_no_cli_framework_dependency():
    """FR-41 / NFR-10 — argparse only; click and typer are forbidden.

    Parses the manifest instead of grepping it. The first version of this test
    scanned raw text and failed on this very package, because the comment
    explaining that click is forbidden *contains the word click*. A matcher that
    does not assert WHAT it matched is not evidence.
    """
    try:
        import tomllib
    except ImportError:                       # pragma: no cover
        import tomli as tomllib               # type: ignore[no-redef]

    manifest = tomllib.loads(
        (PKG_ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    project = manifest.get("project", {})
    declared = list(project.get("dependencies", []))
    for extras in (project.get("optional-dependencies") or {}).values():
        declared += list(extras)

    banned = {"click", "typer"}
    found = [d for d in declared
             if d.split("[")[0].split(">")[0].split("=")[0].strip().lower() in banned]
    assert not found, f"CLI framework forbidden by FR-41: {found}"

