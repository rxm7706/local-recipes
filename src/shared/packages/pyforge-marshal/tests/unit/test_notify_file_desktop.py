"""Unit tests for ``pyforge.marshal.adapters.notify_file_desktop`` (Story
3.7, AD-4/AD-34) -- ``FileDesktopNotifier``, ``ports.NotifyPort``'s sole
implementation.

``notify_desktop`` monkeypatches ``subprocess.run`` directly (the SAME
technique ``test_observer_mux.py``/``test_harness_bmadloop_spin.py`` use)
rather than requiring a real ``notify-send`` binary on the test host.
``notify_file`` is exercised both through a fake ``RecordPort`` (proving
delegation -- the exact path/payload reach the injected collaborator
unchanged) and through the REAL ``adapters/fs_local.py::LocalFs`` default
(proving the end-to-end write actually lands on disk), mirroring
``test_fs_local.py``'s own ``write_redacted_atomic`` convention.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pyforge.marshal.adapters.notify_file_desktop as module
import pytest
from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.notify_file_desktop import FileDesktopNotifier
from pyforge.marshal.core.egress import Redacted, to_redacted


class FakeRecord:
    """Fakes ``ports.RecordPort`` -- the ONE method ``notify_file``
    delegates to entirely (no new atomic-write logic of its own)."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, Redacted]] = []
        self.fail: Exception | None = None

    def write_redacted_atomic(self, path: Path, payload: Redacted) -> None:
        self.calls.append((path, payload))
        if self.fail:
            raise self.fail


@pytest.fixture
def notifier() -> FileDesktopNotifier:
    return FileDesktopNotifier()


# --- notify_file: delegation to RecordPort ----------------------------------------


def test_notify_file_delegates_to_the_injected_record_port():
    record = FakeRecord()
    notifier = FileDesktopNotifier(record=record)
    path = Path("/home/acme-loop/runs/acme-run-1/ESCALATION")
    payload = to_redacted({"story_key": "3.7", "reason": "ambiguous spec"})

    notifier.notify_file(path, payload)

    assert record.calls == [(path, payload)]


def test_notify_file_propagates_the_record_ports_own_failure():
    record = FakeRecord()
    record.fail = FsError("disk full")
    notifier = FileDesktopNotifier(record=record)

    with pytest.raises(FsError):
        notifier.notify_file(Path("/home/acme-loop/ESCALATION"), to_redacted({"a": 1}))


# --- notify_file: real end-to-end write (default LocalFs) -------------------------


def test_notify_file_default_construction_writes_a_real_file(tmp_path):
    notifier = FileDesktopNotifier()
    target = tmp_path / "ESCALATION"
    payload = to_redacted({"story_key": "3.7", "reason": "ambiguous spec"})

    notifier.notify_file(target, payload)

    assert target.read_text(encoding="utf-8") == payload.text


def test_notify_file_creates_parent_dirs(tmp_path):
    notifier = FileDesktopNotifier()
    target = tmp_path / "runs" / "acme-run-1" / "ESCALATION"

    notifier.notify_file(target, to_redacted({"a": 1}))

    assert target.is_file()


# --- notify_desktop: best-effort, never raises -------------------------------------


def test_notify_desktop_returns_true_on_success(notifier, monkeypatch):
    calls: list[list[str]] = []

    def _fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(args=argv, returncode=0)

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = notifier.notify_desktop(to_redacted({"story_key": "3.7"}))

    assert result is True
    assert len(calls) == 1
    assert calls[0][0] == "notify-send"


def test_notify_desktop_carries_the_payloads_text_as_the_call_body(notifier, monkeypatch):
    captured: list[list[str]] = []

    def _fake_run(argv, **kwargs):
        captured.append(list(argv))
        return subprocess.CompletedProcess(args=argv, returncode=0)

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    payload = to_redacted({"story_key": "3.7", "reason": "ambiguous"})

    notifier.notify_desktop(payload)

    assert payload.text in captured[0]


def test_notify_desktop_returns_false_for_a_nonzero_exit(notifier, monkeypatch):
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(args=argv, returncode=1),
    )
    assert notifier.notify_desktop(to_redacted({"a": 1})) is False


def test_notify_desktop_returns_false_for_a_missing_binary(notifier, monkeypatch):
    def _raise(*args, **kwargs):
        raise FileNotFoundError("notify-send: not found")

    monkeypatch.setattr(module.subprocess, "run", _raise)
    assert notifier.notify_desktop(to_redacted({"a": 1})) is False


def test_notify_desktop_returns_false_on_timeout(notifier, monkeypatch):
    def _raise(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="notify-send", timeout=5.0)

    monkeypatch.setattr(module.subprocess, "run", _raise)
    assert notifier.notify_desktop(to_redacted({"a": 1})) is False


def test_notify_desktop_never_raises_for_an_embedded_nul_byte(notifier, monkeypatch):
    """``subprocess.run`` raises a plain ``ValueError`` -- not an
    ``OSError`` -- for an embedded NUL byte in an argv element (the SAME
    CPython split ``observer_mux.py``'s own methods already guard)."""

    def _raise(*args, **kwargs):
        raise ValueError("embedded null byte")

    monkeypatch.setattr(module.subprocess, "run", _raise)
    assert notifier.notify_desktop(to_redacted({"a": 1})) is False


def test_notify_desktop_rejects_a_non_redacted_payload(notifier):
    with pytest.raises(TypeError, match="Redacted"):
        notifier.notify_desktop("a bare str")  # type: ignore[arg-type]
