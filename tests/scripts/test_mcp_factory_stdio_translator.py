"""spec-mcp-factory-stdio-translator I/O matrix (newline JSON stdio)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TRANSLATOR = REPO / "scripts" / "mcp_factory_stdio_translator.py"
FAKE_CHILD = REPO / "tests" / "scripts" / "fake_fastmcp3_stdio_child.py"


def _run(messages: list[dict], extra_args: list[str] | None = None) -> list[dict]:
    payload = "".join(json.dumps(m) + "\n" for m in messages)
    cmd = [sys.executable, str(TRANSLATOR), "--", sys.executable, str(FAKE_CHILD)]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(
        cmd,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def test_help_states_not_crc() -> None:
    proc = subprocess.run(
        [sys.executable, str(TRANSLATOR), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    text = proc.stdout + proc.stderr
    assert "does not change gunicorn" in text.lower() or "Does not change gunicorn" in text
    assert "python-agent-platform" in text
    assert "Not a CRC" in text or "not a CRC" in text.lower()


def test_modern_client_fabricates_handshake_and_strips_meta() -> None:
    replies = _run(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {"_meta": {"progressToken": 1}},
            }
        ]
    )
    assert len(replies) == 1
    result = replies[0]["result"]
    assert "tools" in result
    journal = json.loads(FAKE_CHILD.with_suffix(".journal").read_text())
    assert journal[0]["method"] == "initialize"
    assert journal[0]["params"]["protocolVersion"] == "2025-06-18"
    assert journal[-1]["method"] == "tools/list"
    assert "_meta" not in journal[-1].get("params") or "_meta" not in json.dumps(
        journal[-1]
    )


def test_handshake_era_passthrough_no_double_init() -> None:
    replies = _run(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "era", "version": "0"},
                },
            }
        ]
    )
    assert replies[0]["result"]["protocolVersion"] == "2025-06-18"
    journal = json.loads(FAKE_CHILD.with_suffix(".journal").read_text())
    inits = [m for m in journal if m.get("method") == "initialize"]
    assert len(inits) == 1


def test_meta_stripped_on_any_method() -> None:
    _run(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "era", "version": "0"},
                    "_meta": {"x": 1},
                },
            }
        ]
    )
    journal = json.loads(FAKE_CHILD.with_suffix(".journal").read_text())
    assert all("_meta" not in json.dumps(m) for m in journal)


def test_text_result_wrapped_for_modern_client() -> None:
    replies = _run(
        [
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "echo_text", "arguments": {}, "_meta": {}},
            }
        ]
    )
    result = replies[0]["result"]
    assert result["content"] == [{"type": "text", "text": "hello-factory"}]


def test_unsupported_revision_does_not_start_child() -> None:
    replies = _run(
        [
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2099-01-01",
                    "capabilities": {},
                    "clientInfo": {"name": "bad", "version": "0"},
                },
            }
        ]
    )
    error = replies[0]["error"]
    assert error["code"] == -32022
    assert "2026-07-28" in error["data"]["supported"]
    journal_path = FAKE_CHILD.with_suffix(".journal")
    assert not journal_path.exists() or journal_path.read_text().strip() in {"", "[]"}


@pytest.fixture(autouse=True)
def _clean_journal() -> None:
    path = FAKE_CHILD.with_suffix(".journal")
    if path.exists():
        path.unlink()
    yield
    if path.exists():
        path.unlink()
