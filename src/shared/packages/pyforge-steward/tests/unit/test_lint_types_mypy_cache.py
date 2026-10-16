"""Story 106.1 — each environment's ``mypy`` run keeps its own cache (scripts/lint_types.py).

``pr-preflight`` runs the ``mypy`` task in ``pyforge-guild`` and ``pyforge-foundry-full`` at the
same time, and CI's ``lint-types`` job runs both in one checkout. Before this story both wrote
``<package>/.mypy_cache``. These tests pin the cache key (AC1), the argv every package's run
gets (AC2), that two environments never share a directory (AC3), and that the ruff verbs are
unchanged (AC4).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[6]
SCRIPTS = ROOT / "scripts"

_PYFORGE_TEN = (
    "pyforge-atlas",
    "pyforge-core",
    "pyforge-doctor",
    "pyforge-herald",
    "pyforge-marshal",
    "pyforge-mason",
    "pyforge-scribe",
    "pyforge-steward",
    "pyforge-testing-kit",
    "pyforge-warden",
)
_DJANGO_NINE = tuple(
    f"django-{s}" for s in ("atlas", "doctor", "herald", "marshal", "mason", "pyforge", "scribe", "steward", "warden")
)


def _load_lint_types():
    name = "_lint_types_mypy_cache_under_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "lint_types.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _seed_tree(root: Path) -> Path:
    """Ten ``pyforge-*`` packages (each with ``src/pyforge/<station>/``) and nine ``django-*``."""
    packages = root / "packages"
    for name in _PYFORGE_TEN:
        pkg = packages / name
        (pkg / "src" / "pyforge" / name.removeprefix("pyforge-").replace("-", "_")).mkdir(parents=True)
        (pkg / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n', encoding="utf-8")
    for name in _DJANGO_NINE:
        pkg = packages / name
        (pkg / "src").mkdir(parents=True)
        (pkg / "pyproject.toml").write_text('[project]\nname = "x"\n\n[tool.ruff]\n', encoding="utf-8")
    return packages


@pytest.fixture
def lt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """``lint_types`` over a fixture tree, its tool lookup always finding the tool."""
    mod = _load_lint_types()
    monkeypatch.setattr(mod, "shutil", SimpleNamespace(which=lambda tool: f"/stub/bin/{tool}"))
    monkeypatch.setattr(mod, "PACKAGES_DIR", _seed_tree(tmp_path))
    monkeypatch.setattr(mod, "NOT_YET_CLEAN", {})
    return mod


def _record_runs(monkeypatch: pytest.MonkeyPatch, mod) -> list[tuple[list[str], Path]]:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(argv: list[str], *, cwd: Path) -> int:
        calls.append((list(argv), cwd))
        return 0

    monkeypatch.setattr(mod, "_run", fake_run)
    return calls


def _cache_dir_of(argv: list[str]) -> Path:
    assert argv.count("--cache-dir") == 1, argv
    return Path(argv[argv.index("--cache-dir") + 1])


# ---- AC1: the cache key -----------------------------------------------------------


def test_the_cache_is_keyed_on_the_pixi_environment_first() -> None:
    """Mutation: read ``CONDA_PREFIX`` first, or a constant — this test fails."""
    mod = _load_lint_types()
    environ = {"PIXI_ENVIRONMENT_NAME": "pyforge-guild", "CONDA_PREFIX": "/w/.pixi/envs/pyforge-foundry-full"}
    assert mod.mypy_cache_env(environ) == "pyforge-guild"


@pytest.mark.parametrize("pixi_name", [None, "", "   "])
def test_without_a_pixi_environment_the_conda_prefix_names_the_cache(pixi_name: str | None) -> None:
    """Mutation: drop the ``CONDA_PREFIX`` fallback — this test fails."""
    mod = _load_lint_types()
    environ = {"CONDA_PREFIX": "/w/.pixi/envs/pyforge-foundry-full"}
    if pixi_name is not None:
        environ["PIXI_ENVIRONMENT_NAME"] = pixi_name
    assert mod.mypy_cache_env(environ) == "pyforge-foundry-full"


def test_without_either_variable_the_interpreter_prefix_names_the_cache() -> None:
    """Mutation: return an empty name (a cache at ``.mypy_cache/`` itself) — this test fails."""
    mod = _load_lint_types()
    assert mod.mypy_cache_env({}) == Path(sys.prefix).name
    assert mod.mypy_cache_env({}) != ""


def test_the_cache_dir_is_the_environment_under_the_package_mypy_cache(tmp_path: Path) -> None:
    mod = _load_lint_types()
    pkg = tmp_path / "pyforge-atlas"
    assert mod.mypy_cache_dir(pkg, {"PIXI_ENVIRONMENT_NAME": "pyforge-guild"}) == pkg / ".mypy_cache" / "pyforge-guild"


def test_the_cache_key_reads_the_process_environment_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_lint_types()
    monkeypatch.setenv("PIXI_ENVIRONMENT_NAME", "pyforge-foundry-full")
    assert mod.mypy_cache_env() == "pyforge-foundry-full"


# ---- AC2: every package's run names its cache -------------------------------------


def test_mypy_passes_each_package_its_environment_cache_dir(
    lt, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Mutation: drop ``--cache-dir`` from the mypy argv — this test fails."""
    monkeypatch.setenv("PIXI_ENVIRONMENT_NAME", "pyforge-foundry-full")
    calls = _record_runs(monkeypatch, lt)
    assert lt.main(["mypy"]) == 0
    assert [cwd.name for _argv, cwd in calls] == list(_PYFORGE_TEN)
    for argv, cwd in calls:
        station = cwd.name.removeprefix("pyforge-").replace("-", "_")
        assert argv == [
            "mypy",
            "--cache-dir",
            str(cwd / ".mypy_cache" / "pyforge-foundry-full"),
            "-p",
            f"pyforge.{station}",
        ]
    assert "[lint-types] mypy cache  <package>/.mypy_cache/pyforge-foundry-full/" in capsys.readouterr().out


# ---- AC3: two environments, two caches --------------------------------------------


def test_two_environments_never_share_a_cache_dir(lt, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: key the cache on anything but the environment — this test fails."""
    dirs: dict[str, dict[str, Path]] = {}
    for environment in ("pyforge-guild", "pyforge-foundry-full"):
        monkeypatch.setenv("PIXI_ENVIRONMENT_NAME", environment)
        calls = _record_runs(monkeypatch, lt)
        assert lt.main(["mypy"]) == 0
        dirs[environment] = {cwd.name: _cache_dir_of(argv) for argv, cwd in calls}
    guild, full = dirs["pyforge-guild"], dirs["pyforge-foundry-full"]
    assert set(guild) == set(full) == set(_PYFORGE_TEN)
    assert not set(guild.values()) & set(full.values())
    for name in _PYFORGE_TEN:
        assert guild[name].parent == full[name].parent == lt.PACKAGES_DIR / name / ".mypy_cache"


# ---- AC4: the ruff verbs are unchanged --------------------------------------------


@pytest.mark.parametrize("verb", ["ruff", "ruff-format"])
def test_the_ruff_verbs_take_no_cache_dir(lt, monkeypatch: pytest.MonkeyPatch, verb: str) -> None:
    calls = _record_runs(monkeypatch, lt)
    assert lt.main([verb]) == 0
    assert calls
    assert all("--cache-dir" not in argv for argv, _cwd in calls)
