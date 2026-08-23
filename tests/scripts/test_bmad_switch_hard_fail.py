"""Story 20.7 / FR-190 CAP-2+CAP-3: scripts/bmad-switch --current hard-fails on drift."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "bmad-switch"


def _load():
    # scripts/bmad-switch has no .py suffix — SourceFileLoader is required.
    import importlib.util
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("bmad_switch_under_test", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = mod
    loader.exec_module(mod)
    return mod


def _point_triangle(root: Path, slug: str) -> None:
    marker = root / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(slug + "\n", encoding="utf-8")
    out = root / "_bmad-output"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("planning-artifacts", "implementation-artifacts"):
        target = out / "projects" / slug / name
        target.mkdir(parents=True, exist_ok=True)
        link = out / name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(Path("projects") / slug / name)


def test_current_synced_triangle_exits_zero(tmp_path: Path, capsys) -> None:
    mod = _load()
    _point_triangle(tmp_path, "alpha")
    (tmp_path / "_bmad-output" / "projects" / "alpha").mkdir(parents=True, exist_ok=True)
    assert mod.cmd_current(tmp_path) == 0
    assert capsys.readouterr().out.strip() == "alpha"


def test_current_desynced_triangle_exits_nonzero_and_names_drift(
    tmp_path: Path, capsys
) -> None:
    mod = _load()
    _point_triangle(tmp_path, "alpha")
    # Point both artifact links at beta while marker stays alpha.
    out = tmp_path / "_bmad-output"
    for name in ("planning-artifacts", "implementation-artifacts"):
        (out / "projects" / "beta" / name).mkdir(parents=True, exist_ok=True)
        link = out / name
        link.unlink()
        link.symlink_to(Path("projects") / "beta" / name)
    rc = mod.cmd_current(tmp_path)
    assert rc != 0
    captured = capsys.readouterr()
    assert "alpha" in captured.out
    err = captured.err
    assert "scope drift" in err or "drift" in err
    assert "beta" in err
    assert "alpha" in err


def test_current_missing_marker_exits_nonzero(tmp_path: Path) -> None:
    mod = _load()
    (tmp_path / "_bmad").mkdir()
    (tmp_path / "_bmad-output").mkdir()
    assert mod.cmd_current(tmp_path) == 1


def test_no_local_desync_warning_body_remains() -> None:
    """CAP-2: retired per-caller check body must not shadow verify_scope."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "def desync_warning" not in source
    assert "verify_scope" in source
