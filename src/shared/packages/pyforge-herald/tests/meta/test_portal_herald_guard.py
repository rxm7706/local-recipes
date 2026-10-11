"""Story 37.1 — herald_guard narrow skip semantics."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "django-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _portal_src() -> Path:
    return (
        _repo_root()
        / "src"
        / "shared"
        / "packages"
        / "django-herald"
        / "src"
    )


_portal_src = str(_portal_src())
if _portal_src not in sys.path:
    sys.path.insert(0, _portal_src)

from django_herald_portal import herald_guard  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_herald_guard() -> None:
    herald_guard._decided = False  # noqa: SLF001
    herald_guard._herald_installed = False  # noqa: SLF001
    herald_guard._absent_reason = None  # noqa: SLF001
    herald_guard._logged_absent = False  # noqa: SLF001
    yield
    herald_guard._decided = False  # noqa: SLF001
    herald_guard._herald_installed = False  # noqa: SLF001
    herald_guard._absent_reason = None  # noqa: SLF001
    herald_guard._logged_absent = False  # noqa: SLF001


@pytest.mark.parametrize(
    "missing_name",
    ["pyforge", "pyforge.herald", "pyforge.herald.deck_twins"],
)
def test_herald_is_installed_false_for_pyforge_chain(missing_name: str, monkeypatch) -> None:
    real_import = importlib.import_module

    def _fake(name: str, *args, **kwargs):
        if name == "pyforge.herald":
            raise ModuleNotFoundError(name=missing_name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(herald_guard.importlib, "import_module", _fake)
    assert herald_guard.herald_is_installed() is False
    reason = herald_guard.portal_absent_reason()
    assert "herald" in reason
    assert "pyforge.herald" in reason or missing_name in reason


def test_herald_guard_propagates_unrelated_module_not_found(tmp_path: Path) -> None:
    pkg = tmp_path / "throwaway_guard_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("import missing_dep_guard_37\n", encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        with pytest.raises(ModuleNotFoundError, match="missing_dep_guard_37"):
            importlib.import_module("throwaway_guard_pkg")
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("throwaway_guard_pkg", None)


def test_herald_guard_propagates_non_module_not_found(monkeypatch) -> None:
    def _boom(_name: str) -> None:
        raise RuntimeError("broken herald install")

    monkeypatch.setattr(herald_guard.importlib, "import_module", _boom)
    with pytest.raises(RuntimeError, match="broken herald install"):
        herald_guard.herald_is_installed()


def test_herald_guard_propagates_dependency_module_not_found(monkeypatch) -> None:
    def _fake(name: str) -> object:
        if name == "pyforge.herald":
            raise ModuleNotFoundError(name="some_herald_dependency_xyz")
        raise AssertionError(name)

    monkeypatch.setattr(herald_guard.importlib, "import_module", _fake)
    with pytest.raises(ModuleNotFoundError, match="some_herald_dependency_xyz"):
        herald_guard.herald_is_installed()
