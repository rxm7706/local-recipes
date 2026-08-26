#!/usr/bin/env python3
"""Minimal mcp 1.x-shaped stdio child for translator tests (not FastMCP)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

JOURNAL = Path(__file__).with_suffix(".journal")


def _log(message: dict) -> None:
    prior: list = []
    if JOURNAL.exists():
        prior = json.loads(JOURNAL.read_text())
    prior.append(message)
    JOURNAL.write_text(json.dumps(prior))


def main() -> int:
    while True:
        line = sys.stdin.readline()
        if not line:
            return 0
        message = json.loads(line)
        _log(message)
        method = message.get("method")
        if method == "notifications/initialized":
            continue
        if method == "initialize":
            rev = (message.get("params") or {}).get("protocolVersion")
            reply = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {"protocolVersion": rev, "capabilities": {}, "serverInfo": {"name": "fake"}},
            }
        elif method == "tools/list":
            reply = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {"tools": [{"name": "echo_text"}]},
            }
        elif method == "tools/call":
            reply = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {"text": "hello-factory"},
            }
        else:
            reply = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {"code": -32601, "message": "Method not found"},
            }
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
