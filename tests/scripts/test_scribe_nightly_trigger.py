"""Acceptance tests for scripts/scribe_nightly_trigger.py (Story 8.1).

Matrix:
  DEFAULT_OWNER           — no PYFORGE_GRAPHSTORE_OWNER set → skips the
                            PostgreSQL preflight entirely, compiles directly
  POSTGRES_OWNER_UP_OK    — owner=steward, `scribe-pg-up` succeeds → compiles
  POSTGRES_OWNER_UP_FAILS — owner=steward, `scribe-pg-up` fails → refuses
                            cleanly (exit 0), never compiles
  POSTGRES_OWNER_NO_PIXI  — owner=steward, no `pixi` resolvable anywhere →
                            refuses cleanly (exit 0), never compiles
  COMPILE_EXIT_PROPAGATES — a genuine compile failure's exit code passes
                            through unchanged (never swallowed)

Harness style matches missing_preserve_check's own meta-tests: importlib-load
the script, inject a fake `run`/`which` rather than monkeypatching
`subprocess.run` globally.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "scribe_nightly_trigger.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "scribe_nightly_trigger_under_test", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scribe_nightly_trigger_under_test"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class _FakeRun:
    """Records every command it was called with; returns a scripted exit
    code per call (default 0)."""

    def __init__(self, returncodes: dict[str, int] | None = None, default: int = 0):
        self.calls: list[list[str]] = []
        self._returncodes = returncodes or {}
        self._default = default

    def __call__(self, cmd: list[str]) -> int:
        self.calls.append(list(cmd))
        for marker, code in self._returncodes.items():
            if marker in cmd:
                return code
        return self._default


def test_nightly_sets_graphify_extra_when_unset(monkeypatch):
    """Story 8.2: the trigger opts the seventh surface on for this process."""
    import os

    mod = _load_module()
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)
    monkeypatch.delenv("SCRIBE_GRAPHIFY_EXTRA", raising=False)
    fake_run = _FakeRun()

    rc = mod.main(run=fake_run, which=lambda _: "/usr/bin/pixi")

    assert rc == 0
    assert os.environ["SCRIBE_GRAPHIFY_EXTRA"] == "1"
    assert fake_run.calls == [mod._COMPILE_CMD]


def test_nightly_preserves_explicit_graphify_extra_off(monkeypatch):
    import os

    mod = _load_module()
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)
    monkeypatch.setenv("SCRIBE_GRAPHIFY_EXTRA", "0")
    fake_run = _FakeRun()

    rc = mod.main(run=fake_run, which=lambda _: "/usr/bin/pixi")

    assert rc == 0
    assert os.environ["SCRIBE_GRAPHIFY_EXTRA"] == "0"


def test_default_owner_skips_postgres_and_compiles(monkeypatch):
    mod = _load_module()
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)
    fake_run = _FakeRun()

    rc = mod.main(run=fake_run, which=lambda _: "/usr/bin/pixi")

    assert rc == 0
    assert fake_run.calls == [mod._COMPILE_CMD]


def test_postgres_owner_pg_up_succeeds_then_compiles(monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "steward")
    fake_run = _FakeRun()

    rc = mod.main(run=fake_run, which=lambda _: "/usr/bin/pixi")

    assert rc == 0
    assert len(fake_run.calls) == 2
    assert fake_run.calls[0] == [
        "/usr/bin/pixi",
        "run",
        "-e",
        "pyforge-scribe-pg",
        "scribe-pg-up",
    ]
    assert fake_run.calls[1] == mod._COMPILE_CMD


def test_postgres_owner_pg_up_fails_refuses_cleanly(monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "steward")
    fake_run = _FakeRun(returncodes={"scribe-pg-up": 1})

    rc = mod.main(run=fake_run, which=lambda _: "/usr/bin/pixi")

    assert rc == 0
    # Only the pg-up attempt happened -- the compile must never run.
    assert len(fake_run.calls) == 1
    assert "refusing to compile" in capsys.readouterr().err


def test_postgres_owner_no_pixi_refuses_cleanly(monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "steward")
    monkeypatch.delenv("PIXI_BIN", raising=False)
    fake_run = _FakeRun()

    rc = mod.main(run=fake_run, which=lambda _: None)

    assert rc == 0
    assert fake_run.calls == []
    assert "not on PATH" in capsys.readouterr().err


def test_postgres_owner_uses_pixi_bin_env_var(monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "steward")
    monkeypatch.setenv("PIXI_BIN", "/opt/pixi/pixi")
    fake_run = _FakeRun()

    rc = mod.main(run=fake_run, which=lambda _: (_ for _ in ()).throw(
        AssertionError("shutil.which should not be consulted when PIXI_BIN is set")
    ))

    assert rc == 0
    assert fake_run.calls[0][0] == "/opt/pixi/pixi"


def test_compile_exit_code_propagates_unchanged(monkeypatch):
    mod = _load_module()
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)
    fake_run = _FakeRun(default=2)

    rc = mod.main(run=fake_run, which=lambda _: "/usr/bin/pixi")

    assert rc == 2


def test_run_catches_oserror_from_stale_pixi_binary(monkeypatch, capsys):
    """A stale/relocated `pixi` (or an unresolvable `scribe`) raises
    FileNotFoundError/OSError from subprocess.run itself -- `_run` must
    catch it and return nonzero rather than let it propagate as a raw
    traceback."""
    mod = _load_module()

    def _raise(cmd):
        raise FileNotFoundError("[Errno 2] No such file or directory: 'pixi'")

    monkeypatch.setattr(mod.subprocess, "run", _raise)

    rc = mod._run(["pixi", "run", "-e", "pyforge-scribe", "scribe"])

    assert rc != 0
    assert "failed to run" in capsys.readouterr().err


def test_postgres_preflight_oserror_refuses_cleanly(monkeypatch, capsys):
    """`_run` raising OSError at the preflight call site must be treated the
    same as any other nonzero exit: refuse cleanly, exit 0, never compile."""
    mod = _load_module()
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "steward")

    def _raise(cmd):
        raise FileNotFoundError("pixi not found")

    monkeypatch.setattr(mod.subprocess, "run", _raise)

    rc = mod.main(which=lambda _: "/usr/bin/pixi")

    assert rc == 0
    assert "refusing to compile" in capsys.readouterr().err


def test_compile_oserror_returns_nonzero_not_a_traceback(monkeypatch, capsys):
    """`_run` raising OSError at the compile call site must surface as a
    nonzero exit code with a stderr message, never an uncaught exception."""
    mod = _load_module()
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)

    def _raise(cmd):
        raise FileNotFoundError("scribe not found")

    monkeypatch.setattr(mod.subprocess, "run", _raise)

    rc = mod.main(which=lambda _: "/usr/bin/pixi")

    assert rc != 0
    assert "failed to run" in capsys.readouterr().err


def test_other_owner_values_do_not_trigger_postgres_preflight(monkeypatch):
    """Only the exact PostgreSQL-owner sentinel triggers the preflight --
    any other configured owner (including the default "scribe") compiles
    directly."""
    mod = _load_module()
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "atlas")
    fake_run = _FakeRun()

    rc = mod.main(run=fake_run, which=lambda _: "/usr/bin/pixi")

    assert rc == 0
    assert fake_run.calls == [mod._COMPILE_CMD]
