"""Dependency-completeness + manifest-parity gate for every `pyforge-*` package.

This is the permanent form of the one-off auditor that found `AUD-ATLAS-010` and
`AUD-WARDEN-010`. It answers two questions the packages cannot answer for
themselves, for all of them at once:

1. **Completeness** — is every library the code imports *unconditionally* actually
   declared in `pyproject.toml [project.dependencies]`? `AUD-ATLAS-010`: atlas
   declared 3 deps while hard-importing 21, so `kedro-test` died at collection on
   17 modules and the suite only passed because the fat `local-recipes` env
   happened to supply the rest.
2. **Parity** — does `pixi.toml [package.run-dependencies]` (the `.conda`) carry
   the same set as `pyproject.toml` (the wheel)? `AUD-WARDEN-010`:
   `packageurl-python` was in the wheel's metadata but not the conda run-deps, so
   the built package got it only as cyclonedx's transitive and would break at
   import the moment cyclonedx re-bounded it.

**Why this lives at repo level rather than as eight per-package tests.** The
failure mode being guarded is *someone forgetting*, so the guard must not itself
depend on being remembered: this file discovers `src/shared/packages/pyforge-*`
by glob, so a package added next month is covered the day it lands. Eight
hand-copied per-package tests would silently not exist for it. `pyforge-warden`,
`pyforge-atlas`, and `pyforge-marshal` also carry their own in-package parity
tests — deliberate overlap, because those run inside the package's own suite
where an author editing that package will see them immediately.

**Zero third-party imports, by design.** Everything here is `ast` + `tomllib` +
`pathlib`, so the gate runs in any environment — including the deliberately lean
`pyforge-ci` env, which has no runtime libraries at all. A dependency check that
needed the dependencies installed to run would be circular.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGES_DIR = REPO_ROOT / "src/shared/packages"

# The 8 packages that exist today. This is a NON-VACUITY floor, not an allowlist:
# discovery is by glob, so new packages are picked up automatically, but if the
# glob ever breaks or a package is renamed, every parameterized test below would
# silently collapse to zero cases and "pass". test_discovery_is_not_vacuous
# turns that into a failure.
EXPECTED_PACKAGES = frozenset(
    {
        "pyforge-atlas",
        "pyforge-doctor",
        "pyforge-herald",
        "pyforge-marshal",
        "pyforge-mason",
        "pyforge-scribe",
        "pyforge-steward",
        "pyforge-warden",
    }
)


def _discover() -> list[str]:
    return sorted(
        p.name
        for p in PACKAGES_DIR.glob("pyforge-*")
        if p.is_dir() and (p / "pyproject.toml").is_file()
    )


PACKAGES = _discover()

# Import name -> the distribution name(s) that provide it. Only NON-obvious cases
# belong here; anything whose module name matches its distribution name after PEP
# 503 normalization resolves without an entry.
#
# `opentelemetry` maps to two distributions because the namespace is split across
# them; declaring either one makes the import satisfiable, which is what this
# check is about (set intersection, not equality).
MODULE_ALIASES: dict[str, frozenset[str]] = {
    "a2a": frozenset({"a2a-sdk"}),
    "attr": frozenset({"attrs"}),
    "cyclonedx": frozenset({"cyclonedx-python-lib"}),
    "google": frozenset({"protobuf"}),
    "ibis": frozenset({"ibis-framework"}),
    "openlineage": frozenset({"openlineage-python"}),
    "opentelemetry": frozenset({"opentelemetry-api", "opentelemetry-sdk"}),
    "packageurl": frozenset({"packageurl-python"}),
    "yaml": frozenset({"pyyaml"}),
}

# Conda run-deps with no `[project.dependencies]` counterpart, per package, and
# why each is legitimate. Anything not listed here must appear in BOTH manifests.
CONDA_ONLY_RUN_DEPS: dict[str, frozenset[str]] = {
    # The conda-side interpreter pin; pyproject states the same floor via
    # `requires-python`, which is different machinery for the same constraint.
    "*": frozenset({"python"}),
    # warden's two scanning ENGINES are external executables invoked by
    # subprocess (NFR1/NFR2/OD1), consumed from conda-forge feedstocks. They are
    # not importable Python distributions, so they cannot be pip requirements.
    # Their version ranges are guarded by the package's own
    # tests/meta/test_engine_version_range_sync.py.
    "pyforge-warden": frozenset({"deptry", "osv-scanner"}),
}

# The shared namespace package. `pyforge.*` imports are in-repo siblings, never a
# third-party dependency — and the one cross-package edge that exists
# (atlas -> warden, the optional `gate` extra) is governed by AC-8 and asserted
# in atlas's own tests/test_scaffold_layout.py.
NAMESPACE = "pyforge"


def _normalize(name: str) -> str:
    """PEP 503 normalization, so `PyYAML` and `pyyaml` compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(spec: str) -> str:
    """The distribution name from a PEP 508 requirement string.

    Hand-rolled rather than using `packaging.requirements` to keep this file
    importable in an environment with no third-party packages at all.
    """
    return _normalize(re.split(r"[\[<>=!~;\s]", spec.strip(), maxsplit=1)[0])


def _pin_set(spec: str) -> frozenset[str]:
    """A version constraint as an order-independent set of comparators.

    `">=0.13,<0.13.3"` and `"<0.13.3,>=0.13"` are the same constraint, so a raw
    string comparison would fire on a cosmetic reorder. Conda's `"*"` and
    pyproject's empty specifier both mean unconstrained.
    """
    spec = spec.strip()
    if spec in {"", "*"}:
        return frozenset()
    return frozenset(part.replace(" ", "") for part in spec.split(",") if part.strip())


def _load(package: str, manifest: str) -> dict:
    return tomllib.loads((PACKAGES_DIR / package / manifest).read_text(encoding="utf-8"))


def _project_dependencies(package: str) -> dict[str, frozenset[str]]:
    project = _load(package, "pyproject.toml")["project"]
    return {
        _requirement_name(spec): _pin_set(spec[len(_requirement_name(spec)) :])
        for spec in project.get("dependencies", [])
    }


def _project_extras(package: str) -> set[str]:
    optional = _load(package, "pyproject.toml")["project"].get(
        "optional-dependencies", {}
    )
    return {_requirement_name(s) for specs in optional.values() for s in specs}


def _run_dependencies(package: str) -> dict[str, frozenset[str]]:
    run_deps = _load(package, "pixi.toml").get("package", {}).get(
        "run-dependencies", {}
    )
    return {_normalize(name): _pin_set(str(spec)) for name, spec in run_deps.items()}


def _conda_only(package: str) -> frozenset[str]:
    return CONDA_ONLY_RUN_DEPS["*"] | CONDA_ONLY_RUN_DEPS.get(package, frozenset())


def _is_type_checking_guard(node: ast.If) -> bool:
    """`if TYPE_CHECKING:` — the body never executes at runtime, so an import
    there is an annotation-only reference, not a runtime dependency."""
    return any(
        (isinstance(child, ast.Name) and child.id == "TYPE_CHECKING")
        or (isinstance(child, ast.Attribute) and child.attr == "TYPE_CHECKING")
        for child in ast.walk(node.test)
    )


def _scan_imports(source_root: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Third-party imports under `source_root`, split by whether they run on import.

    Returns `(hard, deferred)`, each mapping a top-level module name to the files
    importing it.

    **hard** — evaluated unconditionally when the module is imported, so the
    distribution must be installed or the import raises. These are what
    `[project.dependencies]` has to cover.

    **deferred** — inside `try/except` (the AD-13 degrade-with-a-hint pattern), a
    function body (lazy import), or `if TYPE_CHECKING`. These may legitimately be
    extras or absent entirely, so they are reported but not enforced.

    A plain `if` is treated as HARD on purpose: it is a runtime import that a
    reader cannot prove is optional, so it should fail loudly and force an
    explicit decision rather than being quietly excused.
    """
    hard: dict[str, set[str]] = {}
    deferred: dict[str, set[str]] = {}

    for path in sorted(source_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        parents: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level or not node.module:
                    continue  # relative import — same package
                modules = [node.module.split(".")[0]]
            else:
                continue

            ancestor: ast.AST = node
            is_deferred = False
            while ancestor in parents:
                ancestor = parents[ancestor]
                if isinstance(
                    ancestor, (ast.Try, ast.FunctionDef, ast.AsyncFunctionDef)
                ) or (isinstance(ancestor, ast.If) and _is_type_checking_guard(ancestor)):
                    is_deferred = True
                    break

            for module in modules:
                if module in sys.stdlib_module_names or module == NAMESPACE:
                    continue
                bucket = deferred if is_deferred else hard
                bucket.setdefault(module, set()).add(
                    str(path.relative_to(source_root))
                )

    return hard, deferred


def _candidate_distributions(module: str) -> frozenset[str]:
    return MODULE_ALIASES.get(module, frozenset({_normalize(module)}))


# --------------------------------------------------------------------------
# Guards against this file passing for the wrong reasons
# --------------------------------------------------------------------------


def test_discovery_is_not_vacuous():
    """Every parameterized test below is driven by `PACKAGES`. If discovery
    returned nothing they would all pass having checked nothing, which is the
    one failure this suite must never have."""
    assert PACKAGES_DIR.is_dir(), f"packages dir missing: {PACKAGES_DIR}"
    missing = sorted(EXPECTED_PACKAGES - set(PACKAGES))
    assert not missing, (
        f"known packages not discovered: {missing}. If one was intentionally "
        "renamed or removed, update EXPECTED_PACKAGES; otherwise discovery is broken."
    )


@pytest.mark.parametrize("package", PACKAGES)
def test_package_declares_both_manifests(package):
    """Parity is only meaningful if both sides exist."""
    assert (PACKAGES_DIR / package / "pyproject.toml").is_file()
    assert (PACKAGES_DIR / package / "pixi.toml").is_file()


@pytest.mark.parametrize("package", PACKAGES)
def test_source_tree_is_scannable(package):
    """A package whose `src/` could not be found would report zero hard imports
    and pass the completeness check vacuously."""
    source_root = PACKAGES_DIR / package / "src"
    assert source_root.is_dir(), f"{package} has no src/ to scan"
    assert any(
        p for p in source_root.rglob("*.py") if "__pycache__" not in p.parts
    ), f"{package}/src contains no Python modules"


def test_alias_map_carries_no_redundant_entries():
    """An alias that merely restates PEP 503 normalization is dead weight and
    hides which names genuinely diverge."""
    redundant = sorted(
        module
        for module, dists in MODULE_ALIASES.items()
        if dists == frozenset({_normalize(module)})
    )
    assert not redundant, f"MODULE_ALIASES entries add nothing: {redundant}"


# --------------------------------------------------------------------------
# 1. Completeness — the code's unconditional imports are all declared
# --------------------------------------------------------------------------


@pytest.mark.parametrize("package", PACKAGES)
def test_every_hard_import_is_a_declared_dependency(package):
    """AUD-ATLAS-010. Anything imported at module level, unconditionally, must be
    in `[project.dependencies]` — not an extra, not a transitive, and not merely
    present in whichever fat environment the tests happen to run in."""
    hard, _ = _scan_imports(PACKAGES_DIR / package / "src")
    declared = set(_project_dependencies(package))
    extras = _project_extras(package)

    undeclared = {
        module: sorted(files)
        for module, files in hard.items()
        if not (_candidate_distributions(module) & declared)
    }
    if not undeclared:
        return

    lines = []
    for module, files in sorted(undeclared.items()):
        candidates = sorted(_candidate_distributions(module))
        where = "as an EXTRA only" if candidates and set(candidates) & extras else "nowhere"
        lines.append(
            f"  {module!r} (imported unconditionally by {files[0]}"
            f"{f' +{len(files) - 1} more' if len(files) > 1 else ''}) "
            f"-> expected one of {candidates}, declared {where}"
        )
    pytest.fail(
        f"{package}: module-level imports not covered by "
        f"[project.dependencies]:\n" + "\n".join(lines) + "\n\n"
        "Fix one of:\n"
        "  (a) declare the distribution in pyproject.toml (and mirror it into "
        "pixi.toml [package.run-dependencies]);\n"
        "  (b) if it is genuinely optional, move the import behind try/except or "
        "into the function that needs it, and declare it as an extra;\n"
        "  (c) if an already-declared distribution provides this module under a "
        "different name, add the mapping to MODULE_ALIASES."
    )


# --------------------------------------------------------------------------
# 2. Parity — the wheel and the .conda require the same things
# --------------------------------------------------------------------------


@pytest.mark.parametrize("package", PACKAGES)
def test_conda_run_deps_cover_every_project_dependency(package):
    """AUD-WARDEN-010: the direction that catches a dep present in the wheel's
    metadata but absent from the conda package's."""
    missing = sorted(set(_project_dependencies(package)) - set(_run_dependencies(package)))
    assert not missing, (
        f"{package}: declared in pyproject.toml [project.dependencies] but "
        f"absent from pixi.toml [package.run-dependencies]: {missing} — the "
        "built .conda would depend on these arriving as somebody else's transitive."
    )


@pytest.mark.parametrize("package", PACKAGES)
def test_conda_run_deps_add_nothing_undeclared(package):
    """The reverse direction, so the `.conda` cannot quietly grow a requirement
    the wheel never gets."""
    extra = sorted(
        set(_run_dependencies(package))
        - set(_project_dependencies(package))
        - _conda_only(package)
    )
    assert not extra, (
        f"{package}: in pixi.toml [package.run-dependencies] but not in "
        f"pyproject.toml [project.dependencies]: {extra}. Either declare it in "
        "pyproject.toml, or justify it in CONDA_ONLY_RUN_DEPS."
    )


@pytest.mark.parametrize("package", PACKAGES)
def test_shared_dependency_pins_agree(package):
    """Same dependency, same constraint on both sides."""
    run_deps = _run_dependencies(package)
    drifted = {
        name: {"pyproject": sorted(pins), "pixi": sorted(run_deps[name])}
        for name, pins in _project_dependencies(package).items()
        if name in run_deps and run_deps[name] != pins
    }
    assert not drifted, f"{package}: version-pin drift between manifests: {drifted}"


@pytest.mark.parametrize("package", PACKAGES)
def test_conda_package_version_matches_pyproject(package):
    """The version literal is spelled once per manifest with nothing tying them
    together."""
    assert (
        _load(package, "pixi.toml")["package"]["version"]
        == _load(package, "pyproject.toml")["project"]["version"]
    )
