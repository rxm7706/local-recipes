"""Unit tests for ``pyforge.marshal.adapters.observer_mux`` (Story 3.4,
AD-4/AD-9/AD-34) -- ``MultiplexerObserver``.

``pane_content`` monkeypatches ``subprocess.run`` directly (the SAME
technique ``test_harness_bmadloop_spin.py`` uses for ``spin``/``attach``/
``run_foreground``) rather than requiring a real ``tmux`` binary on the
test host -- this package's own pixi environment does not provision one,
unlike the sibling ``local-recipes`` environment. ``mtime`` is exercised
against a real ``tmp_path`` file -- no adapter or binary involved, nothing
to fake.
"""

from __future__ import annotations

import subprocess

import pyforge.marshal.adapters.observer_mux as module
import pytest
from pyforge.marshal.adapters.observer_mux import MultiplexerObserver


@pytest.fixture
def observer() -> MultiplexerObserver:
    return MultiplexerObserver()


# --- pane_content --------------------------------------------------------------


def test_pane_content_returns_the_captured_text(observer, monkeypatch):
    def _fake_run(argv, **kwargs):
        assert argv == ["tmux", "capture-pane", "-t", "acme-session", "-p"]
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="hello pane\n")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert observer.pane_content("acme-session") == "hello pane\n"


def test_pane_content_returns_none_for_a_nonzero_exit(observer, monkeypatch):
    """tmux's own "no such session" (and any other capture failure) exit."""

    def _fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=1, stdout="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert observer.pane_content("no-such-session") is None


def test_pane_content_returns_none_when_tmux_is_not_installed(observer, monkeypatch):
    def _raise_not_found(argv, **kwargs):
        raise FileNotFoundError("no such file: tmux")

    monkeypatch.setattr(module.subprocess, "run", _raise_not_found)
    assert observer.pane_content("acme-session") is None


def test_pane_content_returns_none_on_timeout(observer, monkeypatch):
    def _raise_timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=5.0)

    monkeypatch.setattr(module.subprocess, "run", _raise_timeout)
    assert observer.pane_content("acme-session") is None


def test_pane_content_returns_none_for_an_embedded_null_byte(observer, monkeypatch):
    """Review finding: ``subprocess.run`` raises a plain ``ValueError`` --
    not an ``OSError`` -- for an embedded NUL byte in an argv element,
    which would otherwise escape this port's own documented "never
    raises" contract."""

    def _raise_value_error(argv, **kwargs):
        raise ValueError("embedded null byte")

    monkeypatch.setattr(module.subprocess, "run", _raise_value_error)
    assert observer.pane_content("acme-\x00session") is None


def test_pane_content_redacts_a_token_shaped_secret(observer, monkeypatch):
    """AD-34: pane-derived content is redacted at CAPTURE, before it ever
    reaches ``core`` -- a leaked-looking token in the raw pane text must
    never survive this method's own return value."""
    leaked = "gh" + "p_" + "a" * 40

    def _fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=f"error: token {leaked} rejected\n"
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    result = observer.pane_content("acme-session")
    assert leaked not in result
    assert "REDACTED" in result


# --- mtime -----------------------------------------------------------------------


def test_mtime_returns_the_files_last_modified_time(observer, tmp_path):
    target = tmp_path / "usage.json"
    target.write_text("{}", encoding="utf-8")
    assert observer.mtime(target) == target.stat().st_mtime


def test_mtime_returns_none_for_a_missing_path(observer, tmp_path):
    assert observer.mtime(tmp_path / "does-not-exist.json") is None


def test_mtime_returns_none_for_an_embedded_null_byte(observer, monkeypatch):
    """Review finding: ``Path.stat`` raises a plain ``ValueError`` -- not an
    ``OSError`` -- for a path containing an embedded NUL byte, which would
    otherwise escape this port's own documented "never raises" contract."""
    import pathlib

    def _raise_value_error(self):
        raise ValueError("embedded null byte")

    monkeypatch.setattr(pathlib.Path, "stat", _raise_value_error)
    assert observer.mtime(pathlib.Path("/tmp/whatever")) is None


def test_capture_pane_timeout_stays_below_the_supervisor_tick():
    """Follow-up review finding: ``_CAPTURE_PANE_TIMEOUT_S``'s own comment
    states a cross-MODULE invariant -- "sized well below the supervisor's
    own 60s tick ... so a hung or misbehaving tmux binary degrades one
    sample to None rather than stalling an entire tick" -- against a
    constant that lives in a different file, and nothing pinned the two
    together. A future story shortening ``_TICK_SECONDS`` (or introducing
    the policy knob its own docstring anticipates) would silently invert
    the relationship and make every tick wait on tmux, with no test
    failing. This codebase pins exactly this kind of cross-artifact
    coupling elsewhere; now this pair too."""
    from pyforge.marshal.supervisor.__main__ import _TICK_SECONDS

    assert module._CAPTURE_PANE_TIMEOUT_S < _TICK_SECONDS, (
        "a capture-pane timeout at or above the supervisor's own tick lets a "
        "hung tmux stall the whole heartbeat loop -- the exact failure the "
        "constant's own comment says it is sized to prevent"
    )
