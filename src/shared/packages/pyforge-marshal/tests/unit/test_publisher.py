"""Story 33.4 — run-state publisher port/adapter/core tests (CAP-18)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from pyforge.core.client import StationClientError

from pyforge.marshal.adapters.publisher_host import HostPublisher
from pyforge.marshal.core.publish import (
    active_task_from_snapshot,
    dispatch_complete_result,
    layer_savings_dict,
    shape_heartbeat,
    shape_loop_publish,
)
from pyforge.marshal.ports.harness import LayerSavings, RunStatusSnapshot, TaskPhaseSnapshot
from pyforge.marshal.ports.publisher import PublishRecord


def _jsonrpc_result(result: object) -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode("utf-8")


def _mint_result(assertion: str) -> bytes:
    return json.dumps({"assertion": assertion}).encode("utf-8")


class RecordingTransport:
    def __init__(self, *, responses: list[bytes] | None = None, fail: bool = False) -> None:
        self.calls: list[tuple[str, str, dict[str, str], bytes | None]] = []
        self.responses = list(responses or [])
        self.fail = fail

    def __call__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> bytes:
        self.calls.append((method, url, headers, body))
        if self.fail:
            raise StationClientError
        if self.responses:
            return self.responses.pop(0)
        return _jsonrpc_result({"handle": "host-handle-1"})


class RecordingMintTransport:
    def __init__(self, station_transport: RecordingTransport) -> None:
        self._station_transport = station_transport

    def __call__(self, url: str, headers: dict[str, str], body: bytes) -> bytes:
        return self._station_transport("POST", url, headers, body)


def test_shape_loop_publish_includes_savings_fields() -> None:
    savings = LayerSavings(wire_compression_saved=2048, graph_hits_vs_file_reads=(3, 1))
    record = shape_loop_publish(
        station_slug="pyforge-marshal",
        run_id="run-1",
        harness_run_id="h-1",
        story_key="33.4",
        phase="dev",
        commit_sha="abc123",
        layer_savings=savings,
    )
    assert record.station == "pyforge-marshal"
    assert record.run_kind == "loop"
    assert record.layer_savings["wire_compression_saved"] == 2048
    assert record.layer_savings["graph_hits"] == 3
    assert record.layer_savings["file_reads"] == 1


def test_active_task_from_snapshot_prefers_non_terminal_task() -> None:
    snapshot = RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        tasks=(
            TaskPhaseSnapshot(story_key="33.3", phase="done", commit_sha="aaa"),
            TaskPhaseSnapshot(story_key="33.4", phase="dev", commit_sha="bbb"),
        ),
    )
    assert active_task_from_snapshot(snapshot) == ("33.4", "dev", "bbb")


def test_happy_publish_returns_handle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bearer = tmp_path / "bearer"
    bearer.write_text("idp-token", encoding="utf-8")
    transport = RecordingTransport(
        responses=[
            _mint_result("minted-assertion"),
            _jsonrpc_result({"handle": "held-run-42"}),
        ],
    )
    findings: list[tuple[str, str]] = []

    publisher = HostPublisher(
        on_finding=lambda op, msg: findings.append((op, msg)),
        base_url="http://127.0.0.1:8000",
        bearer_file=str(bearer),
        transport=transport,
        mint_transport=RecordingMintTransport(transport),
        monotonic=lambda: 1000.0,
    )
    handle = publisher.publish(
        shape_loop_publish(
            station_slug="pyforge-marshal",
            run_id="run-1",
            harness_run_id="h-1",
        )
    )
    assert handle == "held-run-42"
    assert findings == []
    assert transport.calls[0][1].endswith("/assertion/mint/")
    assert transport.calls[1][1].endswith("/stations/marshal/mcp")
    payload = json.loads(transport.calls[1][3] or b"{}")
    assert payload["method"] == "tools/call"
    assert payload["params"]["name"] == "publish_loop_run"


def test_no_bearer_skips_publish_and_reports_finding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = tmp_path / "missing-bearer"
    transport = RecordingTransport()
    findings: list[tuple[str, str]] = []
    publisher = HostPublisher(
        on_finding=lambda op, msg: findings.append((op, msg)),
        bearer_file=str(missing),
        transport=transport,
        mint_transport=RecordingMintTransport(transport),
    )
    assert (
        publisher.publish(
            PublishRecord(station="pyforge-marshal", run_id="run-1"),
        )
        is None
    )
    assert transport.calls == []
    assert len(findings) == 1
    assert findings[0][0] == "publish"
    assert "PYFORGE_IDP_BEARER_FILE" in findings[0][1]


def test_host_down_reports_finding_and_does_not_raise(tmp_path: Path) -> None:
    bearer = tmp_path / "bearer"
    bearer.write_text("idp-token", encoding="utf-8")
    transport = RecordingTransport(fail=True)
    findings: list[tuple[str, str]] = []
    publisher = HostPublisher(
        on_finding=lambda op, msg: findings.append((op, msg)),
        bearer_file=str(bearer),
        transport=transport,
        mint_transport=RecordingMintTransport(transport),
    )
    assert (
        publisher.publish(
            PublishRecord(station="pyforge-marshal", run_id="run-1"),
        )
        is None
    )
    assert findings[0][0] == "publish"


def test_heartbeat_and_complete_use_handle_only(tmp_path: Path) -> None:
    bearer = tmp_path / "bearer"
    bearer.write_text("idp-token", encoding="utf-8")
    transport = RecordingTransport(
        responses=[
            _mint_result("minted-assertion"),
            _jsonrpc_result({"ok": True}),
            _jsonrpc_result({"ok": True}),
        ],
    )
    findings: list[tuple[str, str]] = []
    publisher = HostPublisher(
        on_finding=lambda op, msg: findings.append((op, msg)),
        bearer_file=str(bearer),
        transport=transport,
        mint_transport=RecordingMintTransport(transport),
    )
    publisher.heartbeat("held-run-42")
    publisher.complete(
        "held-run-42",
        status="completed",
        result=dispatch_complete_result(
            verdict="completed",
            stop_reason=None,
            baseline_head_sha="aaa",
            current_head_sha="bbb",
            story_key="33.4",
        ),
    )
    assert len(transport.calls) == 3
    heartbeat_payload = json.loads(transport.calls[1][3] or b"{}")
    complete_payload = json.loads(transport.calls[2][3] or b"{}")
    assert heartbeat_payload["params"]["name"] == "heartbeat_loop_run"
    assert complete_payload["params"]["name"] == "complete_loop_run"
    assert heartbeat_payload["params"]["arguments"] == {
        **shape_heartbeat("held-run-42"),
        "payload": {},
        "assertion": "minted-assertion",
    }
    assert complete_payload["params"]["arguments"]["handle"] == "held-run-42"
    assert complete_payload["params"]["arguments"]["assertion"] == "minted-assertion"
    assert findings == []


def test_heartbeat_re_mints_when_assertion_stale(tmp_path: Path) -> None:
    bearer = tmp_path / "bearer"
    bearer.write_text("idp-token", encoding="utf-8")
    transport = RecordingTransport(
        responses=[
            _mint_result("first"),
            _jsonrpc_result({"handle": "h1"}),
            _mint_result("second"),
            _jsonrpc_result({"ok": True}),
        ],
    )
    clock = {"t": 0.0}

    def monotonic() -> float:
        return clock["t"]

    publisher = HostPublisher(
        bearer_file=str(bearer),
        transport=transport,
        mint_transport=RecordingMintTransport(transport),
        monotonic=monotonic,
    )
    assert publisher.publish(PublishRecord(station="pyforge-marshal", run_id="r1")) == "h1"
    clock["t"] = 400.0
    publisher.heartbeat("h1")
    mint_calls = [call for call in transport.calls if call[1].endswith("/assertion/mint/")]
    assert len(mint_calls) == 2


def test_re_mint_before_publish_when_assertion_stale(tmp_path: Path) -> None:
    bearer = tmp_path / "bearer"
    bearer.write_text("idp-token", encoding="utf-8")
    transport = RecordingTransport(
        responses=[
            _mint_result("first"),
            _jsonrpc_result({"handle": "h1"}),
            _mint_result("second"),
            _jsonrpc_result({"handle": "h2"}),
        ],
    )
    clock = {"t": 0.0}

    def monotonic() -> float:
        return clock["t"]

    publisher = HostPublisher(
        base_url="http://127.0.0.1:8000",
        bearer_file=str(bearer),
        transport=transport,
        mint_transport=RecordingMintTransport(transport),
        monotonic=monotonic,
    )
    assert publisher.publish(PublishRecord(station="pyforge-marshal", run_id="r1")) == "h1"
    clock["t"] = 400.0
    assert publisher.publish(PublishRecord(station="pyforge-marshal", run_id="r2")) == "h2"
    mint_calls = [call for call in transport.calls if call[1].endswith("/assertion/mint/")]
    assert len(mint_calls) == 2


def test_layer_savings_dict_omits_empty_layers() -> None:
    assert layer_savings_dict(LayerSavings()) == {}
    assert layer_savings_dict(None) == {}


class RecordingPublisher:
    """Minimal ``RunPublisherPort`` for supervisor wiring tests."""

    def __init__(self) -> None:
        self.publish_calls: list[object] = []
        self.heartbeat_calls: list[str] = []
        self.complete_calls: list[tuple[str, str, dict[str, object]]] = []

    def publish(self, record: PublishRecord) -> str:
        self.publish_calls.append(record)
        return "held-run-test"

    def heartbeat(self, handle: str) -> None:
        self.heartbeat_calls.append(handle)

    def complete(
        self,
        handle: str,
        *,
        status: str,
        result: Mapping[str, object],
    ) -> None:
        self.complete_calls.append((handle, status, dict(result)))


def test_run_supervisor_invokes_recording_publisher_lifecycle() -> None:
    from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
    from pyforge.marshal.supervisor.__main__ import run_supervisor

    launch_line = prepare_for_write(
        build_entry(
            id=JournalEntryId("spin-1", 1),
            ts="2026-09-12T00:00:00.000Z",
            run_id="run-1",
            kind="run-launch",
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("spin-1", 0),
            payload={"pid": 9999, "harness_run_id": "h-1"},
        )
    ).line

    class MinimalFs:
        def read_text(self, path: Path) -> str | None:
            del path
            return launch_line + "\n"

        def append_line(self, path: Path, line: str, *, fsync: bool = False) -> None:
            del path, line, fsync

        def write_text_atomic(self, path: Path, content: str) -> None:
            del path, content

    class DeadProcess:
        def is_alive(self, pid: int) -> bool:
            del pid
            return False

    class MinimalHarness:
        def run_status_snapshot(self, home: Path, harness_run_id: str) -> RunStatusSnapshot:
            del home, harness_run_id
            return RunStatusSnapshot(
                paused_stage=None,
                paused_story_key=None,
                paused_reason=None,
                escalated_spec_file=None,
                escalated_task_phase=None,
                deferred=(),
                tasks=(),
            )

        def usage_snapshot(self, home: Path, harness_run_id: str) -> None:
            del home, harness_run_id
            return None

    recording = RecordingPublisher()
    rc = run_supervisor(
        Path("/tmp/home"),
        "pyforge-marshal",
        "run-1",
        9999,
        Path("/tmp/log"),
        25.0,
        1000,
        5000,
        60.0,
        120.0,
        fs=MinimalFs(),
        process=DeadProcess(),
        harness=MinimalHarness(),
        publisher=recording,
    )
    assert rc == 0
    assert len(recording.publish_calls) == 1
    assert recording.heartbeat_calls == []
    assert len(recording.complete_calls) == 1
    assert recording.complete_calls[0][0] == "held-run-test"
