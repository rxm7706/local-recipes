"""Invariants that fail silently if broken, so they are pinned rather than trusted."""

from __future__ import annotations

from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge"


def test_namespace_stays_implicit():
    """PEP 420: shipping src/pyforge/__init__.py would shadow the sibling stations.

    Nothing errors at build time — it only surfaces when two pyforge packages are
    installed together, which is precisely when it is most expensive to find.
    """
    assert not (PKG_ROOT / "__init__.py").exists()
    assert (PKG_ROOT / "steward" / "__init__.py").exists()


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

def test_no_duty_module_calls_sys_exit():
    """AD-8: main() is the SOLE owner of the exit code.

    A `sys.exit()` anywhere but cli.py would take the decision away from main()
    and bypass its projection — the exact failure that produces an undocumented
    bare 1.
    """
    import ast

    steward = PKG_ROOT / "steward"
    offenders: list[str] = []
    for path in steward.rglob("*.py"):
        if path.name == "cli.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # AST, not a substring scan: the first version of this test matched
            # the phrase "sys.exit()" inside a DOCSTRING and failed on a file
            # that never calls it. A matcher that does not assert what it
            # matched is not evidence.
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr == "exit" and \
               isinstance(fn.value, ast.Name) and fn.value.id == "sys":
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, f"sys.exit() call outside cli.py: {offenders}"
