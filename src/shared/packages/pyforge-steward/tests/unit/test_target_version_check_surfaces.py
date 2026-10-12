"""Story 95.1 — target_version_check three surfaces (AC3, AC7)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[6]
SCRIPTS = ROOT / "scripts"


def _load():
    name = "_target_version_check_surfaces"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "target_version_check.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _write_pyforge(root: Path, name: str, *, ruff: str = "py314", mypy: str = "3.14", req: str = ">=3.14") -> None:
    pkg = root / "src" / "shared" / "packages" / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nrequires-python = "{req}"\n\n'
        f'[tool.ruff]\ntarget-version = "{ruff}"\n\n'
        f'[tool.mypy]\npython_version = "{mypy}"\n',
        encoding="utf-8",
    )


def _write_django(root: Path, name: str, *, ruff: str = "py314", req: str = ">=3.14", with_ruff: bool = True) -> None:
    pkg = root / "src" / "shared" / "packages" / name
    pkg.mkdir(parents=True, exist_ok=True)
    ruff_block = f'[tool.ruff]\ntarget-version = "{ruff}"\n' if with_ruff else ""
    (pkg / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nrequires-python = "{req}"\n\n{ruff_block}',
        encoding="utf-8",
    )


def _write_platform(root: Path, *, ruff: str = "py314", mypy: str = "3.14") -> None:
    plat = root / "src" / "platform"
    plat.mkdir(parents=True, exist_ok=True)
    (plat / "pyproject.toml").write_text(
        f'[tool.ruff]\ntarget-version = "{ruff}"\n\n[tool.mypy]\npython_version = "{mypy}"\n',
        encoding="utf-8",
    )


def _seed_tree(root: Path, *, pin: str = ">=3.14.7,3.14.*") -> None:
    (root / "pixi.toml").write_text(
        f'[feature.python.dependencies]\npython = "{pin}"\n',
        encoding="utf-8",
    )
    for i in range(1, 11):
        _write_pyforge(root, f"pyforge-p{i}")
    for i in range(1, 10):
        _write_django(root, f"django-p{i}")
    _write_platform(root)


def _run_main(mod, root: Path) -> int:
    old_root = mod.ROOT
    old_pkg = mod.PACKAGES_DIR
    old_plat = mod.PLATFORM_PYPROJECT
    mod.ROOT = root
    mod.PACKAGES_DIR = root / "src" / "shared" / "packages"
    mod.PLATFORM_PYPROJECT = root / "src" / "platform" / "pyproject.toml"
    try:
        return mod.main()
    finally:
        mod.ROOT = old_root
        mod.PACKAGES_DIR = old_pkg
        mod.PLATFORM_PYPROJECT = old_plat


def test_clean_tree_exits_zero(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    assert _run_main(mod, tmp_path) == 0


def test_portal_ruff_py312_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_django(tmp_path, "django-p1", ruff="py312")
    assert _run_main(mod, tmp_path) == 1


def test_portal_requires_python_below_pin_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_django(tmp_path, "django-p1", req=">=3.12")
    assert _run_main(mod, tmp_path) == 1


def test_portal_missing_ruff_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_django(tmp_path, "django-p1", with_ruff=False)
    assert _run_main(mod, tmp_path) == 1


def test_platform_ruff_py312_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_platform(tmp_path, ruff="py312")
    assert _run_main(mod, tmp_path) == 1


def test_platform_mypy_312_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_platform(tmp_path, mypy="3.12")
    assert _run_main(mod, tmp_path) == 1


def test_pyforge_requires_python_below_pin_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_pyforge(tmp_path, "pyforge-p1", req=">=3.12")
    assert _run_main(mod, tmp_path) == 1


def test_eight_portal_packages_could_not_run(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    import shutil

    shutil.rmtree(tmp_path / "src/shared/packages/django-p9")
    assert _run_main(mod, tmp_path) == 2


def test_missing_platform_pyproject_could_not_run(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    (tmp_path / "src/platform/pyproject.toml").unlink()
    assert _run_main(mod, tmp_path) == 2


def test_pin_315_moves_expected_targets(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path, pin=">=3.15.0,3.15.*")
    assert _run_main(mod, tmp_path) == 1
    _write_pyforge(tmp_path, "pyforge-p1", ruff="py315", mypy="3.15", req=">=3.15")
    for i in range(2, 11):
        _write_pyforge(tmp_path, f"pyforge-p{i}", ruff="py315", mypy="3.15", req=">=3.15")
    for i in range(1, 10):
        _write_django(tmp_path, f"django-p{i}", ruff="py315", req=">=3.15")
    _write_platform(tmp_path, ruff="py315", mypy="3.15")
    assert _run_main(mod, tmp_path) == 0


def test_mutation_dropping_django_glob_could_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: no django-* packages — same exit 2 as test_eight_portal_packages_could_not_run."""
    mod = _load()
    _seed_tree(tmp_path)
    _orig_glob = Path.glob

    def _only_pyforge(self: Path, pattern: str):
        if pattern == "django-*":
            return iter(())
        return _orig_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", _only_pyforge, raising=False)
    assert _run_main(mod, tmp_path) == 2


def test_mutation_dropping_platform_check_would_hide_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_platform(tmp_path, ruff="py312")
    assert _run_main(mod, tmp_path) == 1
    monkeypatch.setattr(mod, "findings_for_platform", lambda *a, **k: [])
    assert _run_main(mod, tmp_path) == 0


def test_mutation_hard_coding_py314_would_fail_on_315_pin(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path, pin=">=3.15.0,3.15.*")
    for i in range(1, 11):
        _write_pyforge(tmp_path, f"pyforge-p{i}", ruff="py314", mypy="3.14", req=">=3.14")
    for i in range(1, 10):
        _write_django(tmp_path, f"django-p{i}", ruff="py314", req=">=3.14")
    _write_platform(tmp_path, ruff="py314", mypy="3.14")
    assert _run_main(mod, tmp_path) == 1


def test_mutation_removing_requires_python_check_would_hide_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_django(tmp_path, "django-p1", req=">=3.12")
    assert _run_main(mod, tmp_path) == 1
    monkeypatch.setattr(mod, "_requires_python_floor", lambda *a, **k: [])
    assert _run_main(mod, tmp_path) == 0
