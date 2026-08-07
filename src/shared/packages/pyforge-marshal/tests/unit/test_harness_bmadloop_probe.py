"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop.BmadLoopHarness``'s
Story 6.4 addition (``adapter_probe``, FR-43/AD-31/AD-34) -- what a named
adapter actually supports on this machine.

Exercised against the REAL installed ``bmad_loop`` 0.9.0's own profile
registry (``adapter_binary``'s own convention -- ``tests/unit/
test_harness_bmadloop_preflight.py::test_adapter_binary_for_the_real_
claude_profile``), with ``subprocess.run``/``shutil.which`` monkeypatched
the SAME way that file's own ``harness_version`` tests do -- no fake
``BmadLoopHarness``, no fake profile.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness, HarnessError


@pytest.fixture
def harness() -> BmadLoopHarness:
    return BmadLoopHarness()


def _fake_run_dispatch(version_result, probe_result):
    """Dispatches on the argv's own shape -- ``[<binary>, "--version"]``
    versus ``["bmad-loop", "probe-adapter", ...]`` -- the SAME two calls
    ``adapter_probe`` makes, in order."""

    def _fake_run(args, **kwargs):
        if args[-1] == "--version":
            return version_result
        return probe_result

    return _fake_run


# --- binary absent -----------------------------------------------------------


def test_adapter_probe_binary_absent_makes_no_subprocess_call(harness, monkeypatch, tmp_path):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setenv("PATH", str(tmp_path))

    def _boom(*args, **kwargs):
        raise AssertionError("no subprocess call is expected when the binary is absent")

    monkeypatch.setattr(module.subprocess, "run", _boom)

    probe = harness.adapter_probe("claude", tmp_path)
    assert probe.adapter == "claude"
    assert probe.binary == "claude"
    assert probe.binary_present is False
    assert probe.binary_version is None
    assert probe.probe_output is None
    assert probe.probe_note == "binary not found on PATH"
    assert probe.capabilities["hook_dialect"]


# --- binary present, both subprocess calls succeed ---------------------------


def test_adapter_probe_binary_present_captures_version_and_probe_output(
    harness, monkeypatch, tmp_path
):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)
    version_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="claude 1.2.3\n", stderr=""
    )
    probe_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout='{"schema_version": 2, "cli": "claude"}', stderr=""
    )
    monkeypatch.setattr(
        module.subprocess, "run", _fake_run_dispatch(version_result, probe_result)
    )

    probe = harness.adapter_probe("claude", tmp_path)
    assert probe.binary_present is True
    assert probe.binary == "claude"
    assert probe.binary_version == "1.2.3"
    assert probe.probe_note is None
    assert json.loads(probe.probe_output) == {"schema_version": 2, "cli": "claude"}


# --- version subprocess failure degrades only binary_version -----------------


def test_adapter_probe_version_failure_degrades_only_binary_version(harness, monkeypatch, tmp_path):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)
    version_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="boom")
    probe_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout='{"schema_version": 2}', stderr=""
    )
    monkeypatch.setattr(
        module.subprocess, "run", _fake_run_dispatch(version_result, probe_result)
    )

    probe = harness.adapter_probe("claude", tmp_path)
    assert probe.binary_version is None
    assert probe.probe_output is not None


# --- probe-adapter subprocess failure degrades only probe_output -------------


def test_adapter_probe_probe_adapter_nonzero_exit_degrades_only_probe_output(
    harness, monkeypatch, tmp_path
):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)
    version_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="claude 1.2.3\n", stderr=""
    )
    probe_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="fail")
    monkeypatch.setattr(
        module.subprocess, "run", _fake_run_dispatch(version_result, probe_result)
    )

    probe = harness.adapter_probe("claude", tmp_path)
    assert probe.binary_version == "1.2.3"
    assert probe.probe_output is None
    assert probe.probe_note == "bmad-loop probe-adapter exited 1"


def test_adapter_probe_probe_adapter_timeout_degrades_only_probe_output(
    harness, monkeypatch, tmp_path
):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)

    def _fake_run(args, **kwargs):
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="claude 1.2.3\n", stderr="")
        raise subprocess.TimeoutExpired(cmd=args, timeout=30.0)

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    probe = harness.adapter_probe("claude", tmp_path)
    assert probe.probe_output is None
    assert "could not be launched or timed out" in probe.probe_note


# --- probe_output redaction round-trip (AD-34) --------------------------------


def test_adapter_probe_output_is_redacted_at_capture(harness, monkeypatch, tmp_path):
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)
    version_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="claude 1.0\n", stderr="")
    token = "ghp_" + "a" * 40
    probe_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps({"help": f"use {token} to authenticate"}), stderr=""
    )
    monkeypatch.setattr(
        module.subprocess, "run", _fake_run_dispatch(version_result, probe_result)
    )

    probe = harness.adapter_probe("claude", tmp_path)
    assert token not in probe.probe_output
    assert "REDACTED" in probe.probe_output


def test_adapter_probe_output_redacts_secret_shaped_field_names_not_just_token_regexes(
    harness, monkeypatch, tmp_path
):
    """Review finding (Blind Hunter): the original implementation wrapped
    the WHOLE probe-adapter JSON document as one opaque string value
    (``{"text": <the whole document>}``) before redacting -- `to_redacted`'s
    field-NAME-based redaction half only ever fires on a real `Mapping`, so
    it never saw the document's actual keys, only its shape-scanned as one
    giant string. A secret-shaped field (e.g. a literal `session_token` key)
    whose VALUE does not happen to match one of the five hardcoded
    token-shape regexes (`ghp_`, `sk-`, ...) would have passed through
    unredacted. Now the document is parsed and redacted as a real dict when
    it is one, so the field-name half applies too."""
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)
    version_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="claude 1.0\n", stderr="")
    secret_value = "not-a-regex-matching-shape-at-all"
    probe_result = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps({"session_token": secret_value, "cli": "claude"}),
        stderr="",
    )
    monkeypatch.setattr(
        module.subprocess, "run", _fake_run_dispatch(version_result, probe_result)
    )

    probe = harness.adapter_probe("claude", tmp_path)
    assert secret_value not in probe.probe_output
    parsed = json.loads(probe.probe_output)
    assert parsed["session_token"] != secret_value
    assert parsed["cli"] == "claude"  # a non-secret-shaped field survives untouched


def test_adapter_probe_output_falls_back_to_opaque_redaction_for_non_json_output(
    harness, monkeypatch, tmp_path
):
    """A well-formed-JSON-document assumption must not crash on a shape
    surprise -- non-JSON stdout still redacts (opaquely) rather than
    raising or silently passing through unredacted."""
    import pyforge.marshal.adapters.harness_bmadloop as module

    monkeypatch.setattr(module.shutil, "which", lambda binary: "/usr/bin/" + binary)
    version_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="claude 1.0\n", stderr="")
    token = "ghp_" + "b" * 40
    probe_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=f"not json at all, contains {token}", stderr=""
    )
    monkeypatch.setattr(
        module.subprocess, "run", _fake_run_dispatch(version_result, probe_result)
    )

    probe = harness.adapter_probe("claude", tmp_path)
    assert probe.probe_output is not None
    assert token not in probe.probe_output


# --- raises HarnessError for the same class of failure adapter_binary does ---


def test_adapter_probe_raises_harness_error_for_unknown_adapter(harness, tmp_path):
    with pytest.raises(HarnessError):
        harness.adapter_probe("not-a-real-adapter", tmp_path)


def test_adapter_probe_raises_harness_error_when_bmad_loop_unimportable(harness, monkeypatch, tmp_path):
    import sys

    monkeypatch.setitem(sys.modules, "bmad_loop.adapters.profile", None)
    with pytest.raises(HarnessError, match="not importable"):
        harness.adapter_probe("claude", tmp_path)


# --- capabilities is a curated, read-only subset of the real profile ---------


def test_adapter_probe_capabilities_reflects_the_real_claude_profile(harness, monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    probe = harness.adapter_probe("claude", tmp_path)
    assert set(probe.capabilities) == {
        "hookless",
        "hook_dialect",
        "usage_parser",
        "skill_tree",
        "model_flag",
    }
    assert probe.capabilities["skill_tree"] == ".claude/skills"
