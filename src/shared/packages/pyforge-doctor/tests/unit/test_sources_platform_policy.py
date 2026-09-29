"""Unit tests for ``pyforge.doctor.sources.platform_policy`` (retro action
item 3, retro-pyforge-steward-2026-09-04.md, 2026-09-05). Covers: no
``src/platform`` in this checkout, the ``platform-ci-test`` interpreter
absent, a clean run, a policy-suite failure, and a ``CliBridgeError`` from
the subprocess layer (timeout, launch failure, an unexpected exit code)."""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor import cli_bridge
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources.platform_policy import gather


def _make_platform_root(tmp_path: Path) -> Path:
    (tmp_path / "src" / "platform").mkdir(parents=True)
    return tmp_path


def _make_interpreter(tmp_path: Path) -> Path:
    interpreter = tmp_path / ".pixi" / "envs" / "platform-ci-test" / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("", encoding="utf-8")
    return interpreter


def test_no_platform_surface_returns_no_findings(tmp_path: Path):
    assert gather(tmp_path) == ()


def test_interpreter_absent_warns_with_install_hint(tmp_path: Path):
    _make_platform_root(tmp_path)

    findings = gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].source is Source.PLATFORM_POLICY_SUITE
    assert findings[0].status is DoctorStatus.WARN
    assert "pixi install -e platform-ci-test" in findings[0].message


def test_clean_run_returns_no_findings(tmp_path: Path, monkeypatch):
    _make_platform_root(tmp_path)
    _make_interpreter(tmp_path)
    monkeypatch.setattr(cli_bridge, "run_pytest", lambda interpreter, cwd, args, timeout=120.0: (0, ""))

    assert gather(tmp_path) == ()


def test_failing_run_returns_one_fail_finding_with_output_tail(tmp_path: Path, monkeypatch):
    _make_platform_root(tmp_path)
    _make_interpreter(tmp_path)
    output = "\n".join(f"line {i}" for i in range(30)) + "\nFAILED tests/policy/x.py"
    monkeypatch.setattr(
        cli_bridge,
        "run_pytest",
        lambda interpreter, cwd, args, timeout=120.0: (1, output),
    )

    findings = gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
    assert "FAILED tests/policy/x.py" in findings[0].message
    # tail-bounded: the early lines this test wrote must NOT appear.
    assert "line 0\n" not in findings[0].message


def test_cli_bridge_error_degrades_to_warn_never_raises(tmp_path: Path, monkeypatch):
    _make_platform_root(tmp_path)
    _make_interpreter(tmp_path)

    def _raise(interpreter, cwd, args, timeout=120.0):
        raise cli_bridge.CliBridgeError("pytest timed out after 120.0s")

    monkeypatch.setattr(cli_bridge, "run_pytest", _raise)

    findings = gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert "timed out" in findings[0].message


def test_relative_target_resolves_before_invoking_run_pytest(tmp_path: Path, monkeypatch):
    """Regression test: a relative ``target`` (e.g. ``Path(".")``, what
    ``sources/__main__.py`` always passes) must not reach ``run_pytest`` as
    a relative interpreter path -- caught live: it resolves against the
    NEW ``cwd`` subprocess.run receives, not the caller's, and raised a
    bogus ``FileNotFoundError``."""
    _make_platform_root(tmp_path)
    _make_interpreter(tmp_path)
    seen: dict[str, Path] = {}

    def _fake_run_pytest(interpreter, cwd, args, timeout=120.0):
        seen["interpreter"] = interpreter
        seen["cwd"] = cwd
        return 0, ""

    monkeypatch.setattr(cli_bridge, "run_pytest", _fake_run_pytest)
    monkeypatch.chdir(tmp_path)

    gather(Path("."))

    assert seen["interpreter"].is_absolute()
    assert seen["cwd"].is_absolute()
