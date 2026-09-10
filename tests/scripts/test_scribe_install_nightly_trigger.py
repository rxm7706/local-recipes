"""Acceptance tests for scripts/scribe_install_nightly_trigger.py (Story 8.1).

Focused on the parts worth unit-testing in isolation: the pure template
render, and the two "refuse before touching the filesystem" gates
(`systemctl`/`pixi` unresolvable). The real install act itself
(`systemctl --user daemon-reload`/`enable --now` against a live systemd-user
session) has no dedicated test here -- same precedent as
`scripts/scribe_pg.py`, which stands entirely untested because it drives
real service binaries a unit test cannot fake meaningfully.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "scribe_install_nightly_trigger.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "scribe_install_nightly_trigger_under_test", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scribe_install_nightly_trigger_under_test"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_render_service_unit_substitutes_repo_root_and_pixi_bin():
    mod = _load_module()
    rendered = mod.render_service_unit(Path("/home/you/local-recipes"), "/usr/bin/pixi")

    assert "WorkingDirectory=/home/you/local-recipes" in rendered
    assert "ExecStart=/usr/bin/pixi run -e pyforge-scribe pyforge-scribe-nightly-compile" in rendered
    assert "Environment=PIXI_BIN=/usr/bin/pixi" in rendered
    assert "{repo_root}" not in rendered
    assert "{pixi_bin}" not in rendered
    assert not any(
        line.startswith("Environment=PYFORGE_GRAPHSTORE_OWNER=")
        for line in rendered.splitlines()
    )


def test_render_service_unit_bakes_graphstore_owner_when_set():
    mod = _load_module()
    rendered = mod.render_service_unit(
        Path("/home/you/local-recipes"), "/usr/bin/pixi", graphstore_owner="steward"
    )

    assert "Environment=PYFORGE_GRAPHSTORE_OWNER=steward" in rendered
    assert "{graphstore_owner_line}" not in rendered


def test_refuses_cleanly_without_systemctl(capsys):
    mod = _load_module()

    rc = mod.main(which=lambda name: None, run=lambda *a, **k: None)

    assert rc == 1
    assert "systemctl" in capsys.readouterr().err


def test_refuses_cleanly_without_pixi(capsys):
    mod = _load_module()

    def which(name: str) -> str | None:
        return "/usr/bin/systemctl" if name == "systemctl" else None

    rc = mod.main(which=which, run=lambda *a, **k: None)

    assert rc == 1
    assert "pixi" in capsys.readouterr().err


def test_installs_and_enables_when_tools_present(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("USER", "tester")
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)

    class _Result:
        def __init__(self, returncode: int = 0) -> None:
            self.returncode = returncode

    calls: list[list[str]] = []

    def run(cmd, *a, **k):
        calls.append(list(cmd))
        return _Result(0)

    def which(name: str) -> str:
        return f"/usr/bin/{name}"

    rc = mod.main(home=tmp_path, which=which, run=run)

    assert rc == 0
    dest = tmp_path / ".config" / "systemd" / "user"
    assert (dest / "pyforge-scribe-nightly-compile.service").is_file()
    assert (dest / "pyforge-scribe-nightly-compile.timer").is_file()
    assert calls == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", "pyforge-scribe-nightly-compile.timer"],
        ["loginctl", "show-user", "tester", "--property=Linger"],
    ]


def test_warns_when_linger_not_enabled(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setenv("USER", "tester")
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)

    class _Result:
        def __init__(self, returncode: int = 0, stdout: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout

    def run(cmd, *a, **k):
        if cmd and cmd[0] == "loginctl":
            return _Result(0, stdout="Linger=no\n")
        return _Result(0)

    def which(name: str) -> str:
        return f"/usr/bin/{name}"

    rc = mod.main(home=tmp_path, which=which, run=run)

    assert rc == 0
    assert "loginctl enable-linger" in capsys.readouterr().err


def test_bakes_graphstore_owner_from_installer_env(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("USER", "tester")
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "steward")

    class _Result:
        def __init__(self, returncode: int = 0) -> None:
            self.returncode = returncode

    def run(cmd, *a, **k):
        return _Result(0)

    def which(name: str) -> str:
        return f"/usr/bin/{name}"

    rc = mod.main(home=tmp_path, which=which, run=run)

    assert rc == 0
    dest = tmp_path / ".config" / "systemd" / "user"
    service_content = (dest / "pyforge-scribe-nightly-compile.service").read_text(
        encoding="utf-8"
    )
    assert "Environment=PYFORGE_GRAPHSTORE_OWNER=steward" in service_content
