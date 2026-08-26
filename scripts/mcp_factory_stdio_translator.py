#!/usr/bin/env python3
"""Stdio wrap for FastMCP 3 / mcp 1.x factory servers (slice 2).

Modern clients (no handshake, ``_meta``) talk to this process. This process
talks JSON-RPC to a child argv. It does **not** import mcp 1.x or mcp 2.x.

Not a CRC fix: does not change gunicorn ``/stations/<name>/mcp`` and does
not lift ``python-agent-platform``. See spec-mcp-factory-stdio-translator.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any
from typing import BinaryIO

HANDSHAKE_REVISIONS = ("2025-03-26", "2025-06-18", "2025-11-25")
MODERN_REVISION = "2026-07-28"
SUPPORTED_REVISIONS = (*HANDSHAKE_REVISIONS, MODERN_REVISION)
UNSUPPORTED_PROTOCOL_VERSION = -32022
INIT_ID = "_factory_stdio_init"


def _help_epilog() -> str:
    return (
        "Does not change gunicorn /stations/<name>/mcp and does not lift "
        "python-agent-platform. Not a CRC ImportError fix."
    )


def strip_meta(payload: Any) -> Any:
    if isinstance(payload, dict):
        out = {k: strip_meta(v) for k, v in payload.items() if k != "_meta"}
        return out
    if isinstance(payload, list):
        return [strip_meta(item) for item in payload]
    return payload


def wrap_text_result(result: Any) -> Any:
    if isinstance(result, str):
        return {"content": [{"type": "text", "text": result}]}
    if isinstance(result, dict):
        if "content" in result:
            return result
        if "text" in result and isinstance(result["text"], str):
            wrapped = dict(result)
            text = wrapped.pop("text")
            wrapped["content"] = [{"type": "text", "text": text}]
            return wrapped
    return result


def requested_revision(message: dict[str, Any]) -> str | None:
    params = message.get("params")
    if isinstance(params, dict):
        rev = params.get("protocolVersion")
        if isinstance(rev, str):
            return rev
    return None


def unsupported_error(request_id: Any, requested: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": UNSUPPORTED_PROTOCOL_VERSION,
            "message": "Unsupported protocol version",
            "data": {
                "supported": list(SUPPORTED_REVISIONS),
                "requested": requested,
            },
        },
    }


def fabricated_initialize() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": INIT_ID,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "mcp-factory-stdio-translator", "version": "0"},
        },
    }


def read_newline_json(stream: BinaryIO) -> dict[str, Any] | None:
    line = stream.readline()
    if not line:
        return None
    text = line.decode("utf-8").strip()
    if not text:
        return read_newline_json(stream)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        msg = "stdio message must be a JSON object"
        raise TypeError(msg)
    return payload


def write_newline_json(stream: BinaryIO, payload: dict[str, Any]) -> None:
    stream.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
    stream.flush()


class Translator:
    def __init__(self, child_cmd: list[str]) -> None:
        self._child_cmd = child_cmd
        self._proc: subprocess.Popen[bytes] | None = None
        self._child_ready = False
        self._modern = False

    def _start_child(self) -> None:
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(  # noqa: S603 — argv is operator-supplied
            self._child_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
        )

    def _child_io(self) -> tuple[BinaryIO, BinaryIO]:
        assert self._proc is not None
        assert self._proc.stdin is not None
        assert self._proc.stdout is not None
        return self._proc.stdin, self._proc.stdout

    def _ensure_handshake(self) -> None:
        if self._child_ready:
            return
        self._start_child()
        cin, cout = self._child_io()
        write_newline_json(cin, fabricated_initialize())
        reply = read_newline_json(cout)
        if reply is None:
            msg = "child closed during fabricated initialize"
            raise RuntimeError(msg)
        if reply.get("error"):
            write_newline_json(sys.stdout.buffer, reply)
            raise SystemExit(1)
        write_newline_json(
            cin,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        self._child_ready = True

    def _forward(self, message: dict[str, Any]) -> dict[str, Any] | None:
        self._start_child()
        cin, cout = self._child_io()
        write_newline_json(cin, strip_meta(message))
        if message.get("id") is None and str(message.get("method", "")).startswith(
            "notifications/"
        ):
            return None
        return read_newline_json(cout)

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        if method == "initialize":
            requested = requested_revision(message)
            if requested is None or requested not in HANDSHAKE_REVISIONS:
                return unsupported_error(
                    message.get("id"),
                    requested if requested is not None else "",
                )
            self._modern = False
            self._start_child()
            reply = self._forward(message)
            self._child_ready = True
            return reply
        headerish = requested_revision(message)
        if headerish is not None and headerish not in SUPPORTED_REVISIONS:
            return unsupported_error(message.get("id"), headerish)
        if not self._child_ready:
            self._modern = True
            self._ensure_handshake()
        reply = self._forward(message)
        if reply is None:
            return None
        if self._modern and "result" in reply:
            reply = dict(reply)
            reply["result"] = wrap_text_result(reply["result"])
        return reply

    def close(self) -> None:
        if self._proc is None:
            return
        if self._proc.stdin:
            self._proc.stdin.close()
        self._proc.wait(timeout=5)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp_factory_stdio_translator",
        description=(
            "Stdio translator: modern MCP client ↔ FastMCP 3 / mcp 1.x child. "
            + _help_epilog()
        ),
        epilog=_help_epilog(),
    )
    parser.add_argument(
        "child",
        nargs=argparse.REMAINDER,
        help="Child command after -- (example: -- python .claude/tools/conda_forge_server.py)",
    )
    args = parser.parse_args(argv)
    child = list(args.child)
    if child and child[0] == "--":
        child = child[1:]
    if not child:
        parser.error("child command required after --")
    args.child = child
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    translator = Translator(args.child)
    try:
        while True:
            message = read_newline_json(sys.stdin.buffer)
            if message is None:
                return 0
            reply = translator.handle(message)
            if reply is not None:
                write_newline_json(sys.stdout.buffer, reply)
    finally:
        translator.close()


if __name__ == "__main__":
    if os.environ.get("MCP_FACTORY_STDIO_TRANSLATOR_CRC"):
        sys.stderr.write(
            "mcp_factory_stdio_translator: this process is not the CRC host face\n"
        )
    raise SystemExit(main())
