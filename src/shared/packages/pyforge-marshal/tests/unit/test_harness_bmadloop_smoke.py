"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop.BmadLoopHarness``'s
Story 6.5 addition (``run_smoke``, FR-44/AD-37) -- one bounded ``bmad-loop
run --story ... --max-stories 1`` attempt against a named adapter.

Exercised against the REAL installed ``bmad_loop`` 0.9.0's own profile
registry (``adapter_probe``'s own convention -- ``tests/unit/
test_harness_bmadloop_probe.py``), with ``subprocess.run``/``shutil.which``
monkeypatched -- no fake ``BmadLoopHarness``, no fake profile.
"""

from __future__ import annotations

import subprocess

import pytest

from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness, HarnessError


@pytest.fixture
def harness() -> BmadLoopHarness:
    return BmadLoopHarness()


def test_run_smoke_binary_absent_makes_no_subprocess_call(harness, monkeypatch, tmp_path):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setenv("PATH", str(tmp_path))

    def _boom(*args, **kwargs):
        raise AssertionError("no subprocess call is expected when the binary is absent")

    monkeypatch.setattr(module.subprocess, "run", _boom)

    result = harness.run_smoke(
        tmp_path,
        adapter_name="claude",
        story="1-1-marshal-conformance-smoke",
        timeout_s=1.0,
        log_path=tmp_path / "smoke.log",
    )
    assert result.adapter == "claude"
    assert result.binary == "claude"
    assert result.binary_present is False
    assert result.launched is False
    assert result.returncode is None
    assert result.timed_out is False


def test_run_smoke_binary_present_launches_and_normalizes_returncode(harness, monkeypatch, tmp_path):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)

    captured_argv = {}

    def _fake_run(args, **kwargs):
        captured_argv["args"] = args
        captured_argv["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=None, stderr=None)

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    log_path = tmp_path / "smoke.log"
    result = harness.run_smoke(
        tmp_path,
        adapter_name="claude",
        story="1-1-marshal-conformance-smoke",
        timeout_s=5.0,
        log_path=log_path,
    )
    assert result.binary_present is True
    assert result.launched is True
    assert result.returncode == 0
    assert result.timed_out is False
    assert captured_argv["args"] == [
        "bmad-loop",
        "run",
        "--story",
        "1-1-marshal-conformance-smoke",
        "--max-stories",
        "1",
    ]
    assert captured_argv["kwargs"]["cwd"] == tmp_path
    assert captured_argv["kwargs"]["timeout"] == 5.0


def test_run_smoke_negative_returncode_normalizes_to_128_plus_signal(harness, monkeypatch, tmp_path):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(args=args, returncode=-9, stdout=None, stderr=None),
    )
    result = harness.run_smoke(
        tmp_path, adapter_name="claude", story="1-1-x", timeout_s=5.0, log_path=tmp_path / "smoke.log"
    )
    assert result.returncode == 137


def test_run_smoke_timeout_degrades_to_timed_out(harness, monkeypatch, tmp_path):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)

    def _fake_run(args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout", 5.0))

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = harness.run_smoke(
        tmp_path, adapter_name="claude", story="1-1-x", timeout_s=5.0, log_path=tmp_path / "smoke.log"
    )
    assert result.launched is True
    assert result.timed_out is True
    assert result.returncode is None


def test_run_smoke_launch_oserror_degrades_to_not_launched(harness, monkeypatch, tmp_path):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)

    def _boom(args, **kwargs):
        raise OSError("simulated: cannot fork")

    monkeypatch.setattr(module.subprocess, "run", _boom)

    result = harness.run_smoke(
        tmp_path, adapter_name="claude", story="1-1-x", timeout_s=5.0, log_path=tmp_path / "smoke.log"
    )
    assert result.launched is False
    assert result.timed_out is False
    assert result.returncode is None


def test_run_smoke_raises_harness_error_for_unknown_adapter(harness, tmp_path):
    with pytest.raises(HarnessError):
        harness.run_smoke(
            tmp_path,
            adapter_name="not-a-real-adapter",
            story="1-1-x",
            timeout_s=5.0,
            log_path=tmp_path / "smoke.log",
        )


def test_run_smoke_raises_harness_error_when_bmad_loop_unimportable(harness, monkeypatch, tmp_path):
    import sys

    monkeypatch.setitem(sys.modules, "bmad_loop.adapters.profile", None)
    with pytest.raises(HarnessError, match="not importable"):
        harness.run_smoke(
            tmp_path, adapter_name="claude", story="1-1-x", timeout_s=5.0, log_path=tmp_path / "smoke.log"
        )


# --- render_policy_toml/write_policy_toml's new `adapter=` parameter --------


def test_render_policy_toml_adapter_parameter_overwrites_name():
    import tomllib

    from pyforge.marshal.adapters.harness_bmadloop import render_policy_toml
    from pyforge.marshal.core import policy

    effective, _findings = policy.compose(project_slug="acme", project={}, flags={})
    rendered = render_policy_toml(effective, adapter="codex")
    parsed = tomllib.loads(rendered)
    assert parsed["adapter"]["name"] == "codex"


def test_render_policy_toml_omitted_adapter_keeps_template_baseline():
    from pyforge.marshal.adapters.harness_bmadloop import render_policy_toml
    from pyforge.marshal.core import policy

    effective, _findings = policy.compose(project_slug="acme", project={}, flags={})
    rendered = render_policy_toml(effective)
    assert 'name = "claude"' in rendered


def test_render_policy_toml_adapter_composes_with_difficulty():
    import tomllib

    from pyforge.marshal.adapters.harness_bmadloop import render_policy_toml
    from pyforge.marshal.core import policy

    effective, _findings = policy.compose(project_slug="acme", project={}, flags={})
    rendered = render_policy_toml(effective, difficulty=None, adapter="gemini")
    parsed = tomllib.loads(rendered)
    assert parsed["adapter"]["name"] == "gemini"


def test_write_policy_toml_adapter_parameter_persists_to_disk(tmp_path):
    import tomllib

    from pyforge.marshal.adapters.harness_bmadloop import write_policy_toml
    from pyforge.marshal.core import policy

    effective, _findings = policy.compose(project_slug="acme", project={}, flags={})
    path = write_policy_toml(effective, tmp_path, adapter="antigravity")
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["adapter"]["name"] == "antigravity"
