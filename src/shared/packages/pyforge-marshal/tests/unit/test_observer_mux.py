"""Unit tests for ``pyforge.marshal.adapters.observer_mux`` (Story 3.4/3.5,
AD-4/AD-9/AD-34) -- ``MultiplexerObserver``.

``pane_content``/``send_text`` monkeypatch ``subprocess.run`` directly (the
SAME technique ``test_harness_bmadloop_spin.py`` uses for ``spin``/
``attach``/``run_foreground``) rather than requiring a real ``tmux`` binary
on the test host -- this package's own pixi environment does not provision
one, unlike the sibling ``local-recipes`` environment. ``mtime`` is
exercised against a real ``tmp_path`` file -- no adapter or binary
involved, nothing to fake.
"""

from __future__ import annotations

import subprocess

import pyforge.marshal.adapters.observer_mux as module
import pytest
from pyforge.marshal.adapters.observer_mux import MultiplexerObserver


@pytest.fixture
def observer() -> MultiplexerObserver:
    return MultiplexerObserver()


def _list_windows_result(argv, rows: list[tuple[str, str]]) -> subprocess.CompletedProcess:
    """A well-formed ``tmux list-windows -F "#{window_id}\\t#{window_active}"``
    response for the given ``(window_id, window_active)`` rows."""
    stdout = "\n".join(f"{window_id}\t{active}" for window_id, active in rows)
    if stdout:
        stdout += "\n"
    return subprocess.CompletedProcess(args=argv, returncode=0, stdout=stdout)


def _fake_run_dispatch(*, list_windows_rows=None, list_windows_ok=True, capture_result=None):
    """Builds a ``subprocess.run`` stand-in that dispatches on the tmux
    SUBCOMMAND (``list-windows`` vs. ``capture-pane``/``send-keys``) -- the
    shared window resolver and the method-specific call are two separate
    ``subprocess.run`` invocations now that the window target is resolved
    live (Story 3.5), so a single flat fake can no longer answer every call
    the same way."""
    calls: list[list[str]] = []

    def _fake_run(argv, **kwargs):
        calls.append(list(argv))
        if argv[1] == "list-windows":
            if not list_windows_ok:
                return subprocess.CompletedProcess(args=argv, returncode=1, stdout="")
            return _list_windows_result(argv, list_windows_rows or [])
        return capture_result(argv, **kwargs) if callable(capture_result) else capture_result

    return _fake_run, calls


# --- the shared window resolver --------------------------------------------------


def test_resolve_window_picks_the_sole_active_window(observer, monkeypatch):
    fake_run, calls = _fake_run_dispatch(
        list_windows_rows=[("%0", "0"), ("%3", "1")],
        capture_result=subprocess.CompletedProcess(args=[], returncode=0, stdout="pane text"),
    )
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert observer._resolve_window("acme-session") == "%3"
    list_windows_call = calls[0]
    assert list_windows_call == [
        "tmux",
        "list-windows",
        "-t",
        "=acme-session",
        "-F",
        "#{window_id}\t#{window_active}",
    ]


def test_resolve_window_returns_none_for_zero_windows(observer, monkeypatch):
    fake_run, _ = _fake_run_dispatch(list_windows_rows=[])
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert observer._resolve_window("acme-session") is None


def test_resolve_window_returns_none_when_no_session_exists(observer, monkeypatch):
    fake_run, _ = _fake_run_dispatch(list_windows_ok=False)
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert observer._resolve_window("no-such-session") is None


def test_resolve_window_returns_none_for_more_than_one_active_window(observer, monkeypatch):
    """A query-level anomaly (more than one row claims active) -- never
    guess among ambiguous candidates."""
    fake_run, _ = _fake_run_dispatch(list_windows_rows=[("%0", "1"), ("%3", "1")])
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert observer._resolve_window("acme-session") is None


def test_resolve_window_returns_none_when_tmux_is_not_installed(observer, monkeypatch):
    def _raise_not_found(argv, **kwargs):
        raise FileNotFoundError("no such file: tmux")

    monkeypatch.setattr(module.subprocess, "run", _raise_not_found)
    assert observer._resolve_window("acme-session") is None


def test_resolve_window_returns_none_on_timeout(observer, monkeypatch):
    def _raise_timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=5.0)

    monkeypatch.setattr(module.subprocess, "run", _raise_timeout)
    assert observer._resolve_window("acme-session") is None


def test_resolve_window_returns_none_for_an_embedded_null_byte(observer, monkeypatch):
    def _raise_value_error(argv, **kwargs):
        raise ValueError("embedded null byte")

    monkeypatch.setattr(module.subprocess, "run", _raise_value_error)
    assert observer._resolve_window("acme-\x00session") is None


# --- pane_content --------------------------------------------------------------


def test_pane_content_returns_the_captured_text(observer, monkeypatch):
    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%3", "1")])
        assert argv == ["tmux", "capture-pane", "-t", "%3", "-p"]
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="hello pane\n")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert observer.pane_content("acme-session") == "hello pane\n"


def test_pane_content_returns_none_when_no_window_resolves(observer, monkeypatch):
    """``pane_content`` degrades via the shared resolver -- no separate
    "no such session" capture-pane call is even attempted."""
    fake_run, calls = _fake_run_dispatch(list_windows_rows=[])
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert observer.pane_content("no-such-session") is None
    assert len(calls) == 1  # only the list-windows probe, no capture-pane call


def test_pane_content_returns_none_for_a_nonzero_capture_exit(observer, monkeypatch):
    """The window died between resolution and the capture-pane call."""

    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%3", "1")])
        return subprocess.CompletedProcess(args=argv, returncode=1, stdout="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert observer.pane_content("acme-session") is None


def test_pane_content_returns_none_when_tmux_is_not_installed(observer, monkeypatch):
    def _raise_not_found(argv, **kwargs):
        raise FileNotFoundError("no such file: tmux")

    monkeypatch.setattr(module.subprocess, "run", _raise_not_found)
    assert observer.pane_content("acme-session") is None


def test_pane_content_returns_none_on_capture_timeout(observer, monkeypatch):
    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%3", "1")])
        raise subprocess.TimeoutExpired(cmd=argv, timeout=5.0)

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert observer.pane_content("acme-session") is None


def test_pane_content_returns_none_for_an_embedded_null_byte_in_capture(observer, monkeypatch):
    """Review finding (Story 3.4): ``subprocess.run`` raises a plain
    ``ValueError`` -- not an ``OSError`` -- for an embedded NUL byte in an
    argv element, which would otherwise escape this port's own documented
    "never raises" contract. Exercised at the CAPTURE call, past a
    successfully resolved window."""

    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%3", "1")])
        raise ValueError("embedded null byte")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert observer.pane_content("acme-session") is None


def test_pane_content_redacts_a_token_shaped_secret(observer, monkeypatch):
    """AD-34: pane-derived content is redacted at CAPTURE, before it ever
    reaches ``core`` -- a leaked-looking token in the raw pane text must
    never survive this method's own return value."""
    leaked = "gh" + "p_" + "a" * 40

    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%3", "1")])
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=f"error: token {leaked} rejected\n"
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    result = observer.pane_content("acme-session")
    assert leaked not in result
    assert "REDACTED" in result


# --- send_text -----------------------------------------------------------------


def test_send_text_pastes_then_submits_against_the_resolved_window(observer, monkeypatch):
    calls: list[list[str]] = []

    def _fake_run(argv, **kwargs):
        calls.append(list(argv))
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%7", "1")])
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)

    assert observer.send_text("acme-session", "please continue") is True
    # list-windows, then send-keys -l <text>, then send-keys Enter -- the
    # exact two-call recipe confirmed live against bmad_loop's own
    # send_text (send-keys -l, settle, send-keys Enter).
    assert calls[1] == ["tmux", "send-keys", "-t", "%7", "-l", "please continue"]
    assert calls[2] == ["tmux", "send-keys", "-t", "%7", "Enter"]


def test_send_text_sleeps_between_the_paste_and_the_enter(observer, monkeypatch):
    slept: list[float] = []

    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%7", "1")])
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module.time, "sleep", slept.append)

    observer.send_text("acme-session", "hi")
    assert slept == [module._SEND_TEXT_SETTLE_S]


def test_send_text_returns_false_when_no_window_resolves(observer, monkeypatch):
    fake_run, calls = _fake_run_dispatch(list_windows_rows=[])
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert observer.send_text("no-such-session", "hi") is False
    assert len(calls) == 1  # never attempts send-keys with no window


def test_send_text_returns_false_when_the_paste_call_fails(observer, monkeypatch):
    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%7", "1")])
        return subprocess.CompletedProcess(args=argv, returncode=1, stdout="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    assert observer.send_text("acme-session", "hi") is False


def test_send_text_returns_false_when_the_enter_call_fails(observer, monkeypatch):
    call_count = {"n": 0}

    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%7", "1")])
        call_count["n"] += 1
        # First non-list-windows call is the paste (succeeds); the second
        # is Enter (fails).
        return subprocess.CompletedProcess(
            args=argv, returncode=0 if call_count["n"] == 1 else 1, stdout=""
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    assert observer.send_text("acme-session", "hi") is False


def test_send_text_returns_false_when_tmux_is_not_installed(observer, monkeypatch):
    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%7", "1")])
        raise FileNotFoundError("no such file: tmux")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    assert observer.send_text("acme-session", "hi") is False


def test_send_text_returns_false_on_timeout(observer, monkeypatch):
    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%7", "1")])
        raise subprocess.TimeoutExpired(cmd=argv, timeout=5.0)

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    assert observer.send_text("acme-session", "hi") is False


def test_send_text_returns_false_for_an_embedded_null_byte(observer, monkeypatch):
    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%7", "1")])
        raise ValueError("embedded null byte")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    assert observer.send_text("acme-session", "hi\x00") is False


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


# --- timeout / decoding discipline -----------------------------------------------


def test_pane_content_passes_the_capture_timeout_to_subprocess_run(observer, monkeypatch):
    """Follow-up review finding (Story 3.4): every fake in this module used
    to assert only ``argv``, so NOTHING pinned the ``timeout=`` kwarg
    actually reaching ``subprocess.run``. This test pins the constant to
    its USE, not just its value, for BOTH calls the resolved-window path
    now makes (the list-windows probe and the capture itself)."""
    seen: list[dict[str, object]] = []

    def _fake_run(argv, **kwargs):
        seen.append(dict(kwargs))
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%3", "1")])
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    observer.pane_content("acme-session")

    for kwargs in seen:
        assert kwargs["timeout"] == module._CAPTURE_PANE_TIMEOUT_S
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["encoding"] == "utf-8"
        assert kwargs["errors"] == "replace"


def test_capture_pane_timeout_stays_below_the_supervisor_tick():
    """Follow-up review finding (Story 3.4): ``_CAPTURE_PANE_TIMEOUT_S``'s
    own comment states a cross-MODULE invariant -- "sized well below the
    supervisor's own 60s tick ... so a hung or misbehaving tmux binary
    degrades one sample to None rather than stalling an entire tick" --
    against a constant that lives in a different file, and nothing pinned
    the two together. A future story shortening ``_TICK_SECONDS`` (or
    introducing the policy knob its own docstring anticipates) would
    silently invert the relationship and make every tick wait on tmux, with
    no test failing. This codebase pins exactly this kind of cross-artifact
    coupling elsewhere; now this pair too."""
    from pyforge.marshal.supervisor.__main__ import _TICK_SECONDS

    assert module._CAPTURE_PANE_TIMEOUT_S < _TICK_SECONDS, (
        "a capture-pane timeout at or above the supervisor's own tick lets a "
        "hung tmux stall the whole heartbeat loop -- the exact failure the "
        "constant's own comment says it is sized to prevent"
    )


def test_pane_content_returns_none_when_the_redaction_round_trip_breaks(monkeypatch):
    """Review finding (Story 3.4): ``to_redacted`` and the
    ``json.loads(...)["pane"]`` unwrap -- the ONLY two lines in this method
    that transform data -- sat OUTSIDE the try that upholds the port's
    documented "never raises" contract. Three passes hardened the inside of
    that try (NUL bytes, timeouts, non-zero exits) and left the transform
    exposed, so the contract rested entirely on ``to_redacted``'s CURRENT
    shape: any future change that wraps, caps or truncates its output (a
    size ceiling on captured text being the obvious one) raises
    ``JSONDecodeError``/``KeyError`` straight through a port that promises
    neither -- into ``supervisor/__main__.py``'s tick, which catches only
    ``(FsError, ValueError)``, killing the sidecar with a raw traceback
    AFTER ``supervisor-attach`` is journaled."""

    class _Truncated:
        text = '{"pane": "abc'  # a plausible size-capped serialization

    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%3", "1")])
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="pane text")

    monkeypatch.setattr(module, "to_redacted", lambda payload: _Truncated())
    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    assert MultiplexerObserver().pane_content("acme-session") is None


def test_pane_content_returns_none_when_the_redacted_payload_loses_its_key(monkeypatch):
    """The ``LookupError`` half of the same guard: a serialization that
    parses but no longer carries the ``pane`` key this adapter wraps and
    unwraps symmetrically."""

    class _Rekeyed:
        text = '{"content": "abc"}'

    def _fake_run(argv, **kwargs):
        if argv[1] == "list-windows":
            return _list_windows_result(argv, [("%3", "1")])
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="pane text")

    monkeypatch.setattr(module, "to_redacted", lambda payload: _Rekeyed())
    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    assert MultiplexerObserver().pane_content("acme-session") is None
