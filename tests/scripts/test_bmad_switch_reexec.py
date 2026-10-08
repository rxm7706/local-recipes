"""Story 69.1: scripts/bmad-switch re-executes under pyforge-guild when scope cannot load."""
from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "bmad-switch"


def _load():
    loader = SourceFileLoader("bmad_switch_reexec_test", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = mod
    loader.exec_module(mod)
    return mod


def _fake_pixi(tmp_path: Path, *, exit_code: int = 0) -> Path:
    record = tmp_path / "pixi-record.jsonl"
    script = tmp_path / "pixi"
    script.write_text(
        f"""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path({record!r}).write_text(json.dumps(sys.argv) + "\\n", encoding="utf-8")
raise SystemExit({exit_code})
""",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def _read_pixi_argv(record_parent: Path) -> list[str]:
    record = record_parent / "pixi-record.jsonl"
    return json.loads(record.read_text(encoding="utf-8"))


def _minimal_switch_tree(root: Path, slug: str = "alpha") -> None:
    (root / "_bmad").mkdir(parents=True, exist_ok=True)
    out = root / "_bmad-output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "projects" / slug).mkdir(parents=True, exist_ok=True)
    for name in ("planning-artifacts", "implementation-artifacts"):
        target = out / "projects" / slug / name
        target.mkdir(parents=True, exist_ok=True)
        link = out / name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(Path("projects") / slug / name)
    marker = root / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(slug + "\n", encoding="utf-8")


def test_current_reexec_calls_pixi_once_with_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    mod = _load()
    fake = _fake_pixi(tmp_path, exit_code=0)
    monkeypatch.setattr(mod, "_load_verify_scope", lambda _root: None)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    calls: list[tuple[list[str], dict]] = []

    def capture_run(cmd, **kwargs):
        out = capsys.readouterr()
        assert out.out == ""
        assert out.err == ""
        calls.append((list(cmd), kwargs))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(mod.subprocess, "run", capture_run)
    monkeypatch.setattr(sys, "argv", ["bmad-switch", "--current"])

    assert mod.main() == 0
    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert cmd[:3] == ["pixi", "run", "--manifest-path"]
    assert str(REPO_ROOT / "pixi.toml") in cmd
    assert "--frozen" in cmd
    assert "-e" in cmd and "pyforge-guild" in cmd
    assert "python" in cmd
    assert str(SCRIPT.resolve()) in cmd
    assert cmd[-1] == "--current"
    assert kwargs["env"][mod._REEXEC_GUARD] == "1"


def test_list_reexec_returns_child_code_without_parent_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    mod = _load()
    _fake_pixi(tmp_path)
    monkeypatch.setattr(mod, "_load_verify_scope", lambda _root: None)
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 2),
    )
    monkeypatch.setattr(sys, "argv", ["bmad-switch", "--list"])

    rc = mod.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "active:" not in captured.out


def test_current_no_pixi_exits_eight_one_line_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    mod = _load()
    monkeypatch.setattr(mod, "_load_verify_scope", lambda _root: None)
    monkeypatch.setattr(mod.shutil, "which", lambda _name: None)
    monkeypatch.setattr(sys, "argv", ["bmad-switch", "--current"])

    assert mod.main() == 8
    err = capsys.readouterr().err
    assert err.count("\n") == 1
    assert sys.executable in err
    assert "pyforge.marshal.scope" in err
    assert "pixi run -e pyforge-guild python scripts/bmad-switch --current" in err


def test_current_guard_set_exits_eight_without_pixi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    mod = _load()
    monkeypatch.setattr(mod, "_load_verify_scope", lambda _root: None)
    monkeypatch.setenv(mod._REEXEC_GUARD, "1")
    called = False

    def boom(*_a, **_k):
        nonlocal called
        called = True
        raise AssertionError("pixi must not run")

    monkeypatch.setattr(mod.subprocess, "run", boom)
    monkeypatch.setattr(sys, "argv", ["bmad-switch", "--current"])

    assert mod.main() == 8
    assert not called
    assert capsys.readouterr().err.count("\n") == 1


def test_switch_and_clear_never_reexec_under_unloadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load()
    _minimal_switch_tree(tmp_path, "alpha")
    monkeypatch.setattr(mod, "_load_verify_scope", lambda _root: None)

    def boom(*_a, **_k):
        raise AssertionError("pixi must not run")

    monkeypatch.setattr(mod.subprocess, "run", boom)

    assert mod.cmd_clear(tmp_path) == 0
    assert mod.cmd_switch(tmp_path, "alpha") == 0


def test_mutation_without_main_gate_raises_on_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load()
    _minimal_switch_tree(tmp_path, "alpha")
    monkeypatch.setattr(mod, "_load_verify_scope", lambda _root: None)
    monkeypatch.setattr(
        mod,
        "_ensure_scope_primitive_or_exit",
        lambda _root, need_scope: None,
    )
    monkeypatch.setattr(sys, "argv", ["bmad-switch", "--current"])

    with pytest.raises(AssertionError):
        mod.main()
