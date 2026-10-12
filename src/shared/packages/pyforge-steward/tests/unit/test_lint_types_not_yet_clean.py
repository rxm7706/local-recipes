"""Story 93.1 — NOT_YET_CLEAN behaviour in scripts/lint_types.py (AC3, AC5, AC6)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SCRIPTS = ROOT / "scripts"
RUFF_TABLE = """
[tool.ruff]
target-version = "py312"
line-length = 120
extend-exclude = ["*/migrations/*.py"]

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"**/tests/**" = ["E402"]
"""


def _load_lint_types():
    name = "_lint_types_under_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "lint_types.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _minimal_pyforge(name: str, root: Path) -> None:
    pkg = root / name
    (pkg / "src" / "pyforge" / name.removeprefix("pyforge-")).mkdir(parents=True)
    (pkg / "pyproject.toml").write_text(
        f"[project]\nname = \"{name}\"\n\n[tool.ruff]\ntarget-version = \"py314\"\n\n[tool.mypy]\npython_version = \"3.14\"\n",
        encoding="utf-8",
    )


def _minimal_django(name: str, root: Path, *, with_ruff: bool = True) -> None:
    pkg = root / name
    (pkg / "src").mkdir(parents=True)
    body = "[project]\nname = \"x\"\n"
    if with_ruff:
        body += RUFF_TABLE
    (pkg / "pyproject.toml").write_text(body, encoding="utf-8")


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


def _seed_tree(tmp_path: Path) -> Path:
    packages = tmp_path / "packages"
    packages.mkdir()
    for name in _PYFORGE_TEN:
        _minimal_pyforge(name, packages)
    for station in ("atlas", "doctor", "herald", "marshal", "mason", "pyforge", "scribe", "steward", "warden"):
        _minimal_django(f"django-{station}", packages)
    return packages


@pytest.fixture
def lt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    mod = _load_lint_types()
    packages_dir = _seed_tree(tmp_path)
    monkeypatch.setattr(mod, "PACKAGES_DIR", packages_dir)
    return mod


def test_not_yet_clean_listed_exit_one_does_not_fail_ruff(lt, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Mutation: treat listed exit 1 like unlisted — this test fails."""
    monkeypatch.setattr(
        lt,
        "NOT_YET_CLEAN",
        {"django-herald": frozenset({"ruff"})},
    )

    def fake_run(argv: list[str], cwd: Path) -> int:
        return 1 if cwd.name == "django-herald" else 0

    monkeypatch.setattr(lt, "_run", fake_run)
    assert lt.main(["ruff"]) == 0
    out = capsys.readouterr().out
    assert "django-herald" in out and "not yet clean (listed)" in out


def test_not_yet_clean_unlisted_exit_one_fails_ruff(lt, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: swallow unlisted exit 1 — this test fails."""
    monkeypatch.setattr(lt, "NOT_YET_CLEAN", {})

    def fake_run(argv: list[str], cwd: Path) -> int:
        return 1 if cwd.name == "django-herald" else 0

    monkeypatch.setattr(lt, "_run", fake_run)
    assert lt.main(["ruff"]) == 1


def test_not_yet_clean_listed_clean_fails_ratchet(lt, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Mutation: allow listed package to stay clean — this test fails."""
    monkeypatch.setattr(
        lt,
        "NOT_YET_CLEAN",
        {"django-herald": frozenset({"ruff"})},
    )
    monkeypatch.setattr(lt, "_run", lambda _a, _c: 0)
    assert lt.main(["ruff"]) == 1
    assert "remove NOT_YET_CLEAN entry" in capsys.readouterr().out


def test_not_yet_clean_listed_exit_two_fails(lt, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: pass listed exit 2 — this test fails."""
    monkeypatch.setattr(
        lt,
        "NOT_YET_CLEAN",
        {"django-herald": frozenset({"ruff"})},
    )

    def fake_run(argv: list[str], cwd: Path) -> int:
        return 2 if cwd.name == "django-herald" else 0

    monkeypatch.setattr(lt, "_run", fake_run)
    assert lt.main(["ruff"]) == 1


def test_not_yet_clean_invalid_entry_could_not_run(lt, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: run tools despite bad NOT_YET_CLEAN — this test fails."""
    monkeypatch.setattr(lt, "NOT_YET_CLEAN", {"pyforge-herald": frozenset({"ruff"})})
    assert lt.main(["ruff"]) == 2


def test_missing_ruff_table_is_a_finding(lt, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mutation: skip missing-table packages — this test fails."""
    packages_dir = _seed_tree(tmp_path)
    _minimal_django("django-herald", packages_dir, with_ruff=False)
    monkeypatch.setattr(lt, "PACKAGES_DIR", packages_dir)
    monkeypatch.setattr(lt, "NOT_YET_CLEAN", {})
    monkeypatch.setattr(lt, "_run", lambda _a, _c: 0)
    assert lt.main(["ruff"]) == 1


def test_pyforge_count_does_not_include_django(lt, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mutation: count django-* toward the ten pyforge packages — this test fails."""
    packages_dir = tmp_path / "packages"
    packages_dir.mkdir()
    for i in range(9):
        _minimal_pyforge(f"pyforge-st{i}", packages_dir)
    for station in ("atlas", "doctor", "herald", "marshal", "mason", "pyforge", "scribe", "steward", "warden"):
        _minimal_django(f"django-{station}", packages_dir)
    monkeypatch.setattr(lt, "PACKAGES_DIR", packages_dir)
    assert lt.main(["ruff"]) == 2


def test_fewer_than_nine_django_packages_could_not_run(lt, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mutation: drop django-* from the glob — this test fails."""
    packages_dir = tmp_path / "packages"
    packages_dir.mkdir()
    for station in ("atlas", "doctor", "herald", "marshal", "mason", "pyforge", "scribe", "steward", "warden", "core"):
        _minimal_pyforge(f"pyforge-{station}" if station != "core" else "pyforge-core", packages_dir)
    _minimal_django("django-herald", packages_dir)
    monkeypatch.setattr(lt, "PACKAGES_DIR", packages_dir)
    assert lt.main(["ruff"]) == 2


def test_ruff_format_fix_skips_listed_package(lt, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Mutation: let --fix rewrite a listed package — this test fails."""
    monkeypatch.setattr(
        lt,
        "NOT_YET_CLEAN",
        {"django-herald": frozenset({"ruff-format"})},
    )
    calls: list[Path] = []

    def fake_run(argv: list[str], cwd: Path) -> int:
        calls.append(cwd)
        return 0

    monkeypatch.setattr(lt, "_run", fake_run)
    assert lt.main(["ruff-format", "--fix"]) == 0
    assert all(p.name != "django-herald" for p in calls)
    assert "skipped (listed for ruff-format)" in capsys.readouterr().out
