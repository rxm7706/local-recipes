"""Read published loop run-state from the host supervisor (Story 33.12, CAP-4)."""

from __future__ import annotations

import json
import os
from typing import Any

from pyforge.core.assertion import HostMintClient
from pyforge.core.client import PyForgeStationClient, Transport

_DEFAULT_HOST = "http://127.0.0.1:8000"
_BEARER_ENV = "PYFORGE_IDP_BEARER_FILE"
_HOST_ENV = "PYFORGE_HOST"
_STATION = "marshal"
_MCP_PATH = f"/stations/{_STATION}/mcp"
_LIST_TOOL = "list_loop_story_tasks"
_JSONRPC_ID = 1


def _default_host() -> str:
    raw = os.environ.get(_HOST_ENV, _DEFAULT_HOST)
    return raw.rstrip("/") if isinstance(raw, str) and raw.strip() else _DEFAULT_HOST


def _read_bearer(path: str) -> str | None:
    if not path:
        return None
    if path.startswith("ey"):
        token = path.strip()
        return token or None
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return None
    token = raw.strip()
    return token or None


def _resolve_transport(transport: Transport | None) -> Transport:
    if transport is not None:
        return transport
    client = PyForgeStationClient(station=_STATION)

    def _default(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
        return client._urllib(method, url, headers, body)  # noqa: SLF001

    return _default


def _jsonrpc_call(tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": _JSONRPC_ID,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def _parse_jsonrpc_response(raw: bytes) -> tuple[object | None, str | None]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON-RPC response: {exc}"
    if not isinstance(payload, dict):
        return None, "invalid JSON-RPC response: not an object"
    if payload.get("error") is not None:
        return None, f"MCP error: {payload['error']!r}"
    return payload.get("result"), None


def _extract_tasks(result: object) -> dict[str, dict[str, Any]] | None:
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if not isinstance(text, str):
                    continue
                try:
                    nested = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(nested, dict):
                    return {k: dict(v) for k, v in nested.items() if isinstance(v, dict)}
        if result and all(isinstance(v, dict) for v in result.values()):
            return {k: dict(v) for k, v in result.items() if isinstance(v, dict)}
    return None


def fetch_story_tasks(
    project_slug: str,
    *,
    base_url: str | None = None,
    bearer_file: str | None = None,
    transport: Transport | None = None,
) -> dict[str, dict[str, Any]] | None:
    """Return published per-story task records, or None when the plane is unreachable."""
    host = (base_url or _default_host()).rstrip("/")
    bearer_path = bearer_file if bearer_file is not None else os.environ.get(_BEARER_ENV, "")
    bearer = _read_bearer(bearer_path or "")
    if bearer is None:
        return None
    station_transport = _resolve_transport(transport)

    def mint_transport(url: str, headers: dict[str, str], body: bytes) -> bytes:
        return station_transport("POST", url, headers, body)

    mint = HostMintClient(f"{host}/assertion/mint/", transport=mint_transport)
    try:
        assertion = mint.emit(idp_bearer=bearer, station=_STATION)
    except Exception:  # noqa: BLE001 -- best-effort read degrades
        return None
    body = json.dumps(
        _jsonrpc_call(
            _LIST_TOOL,
            {"project_slug": project_slug, "assertion": assertion},
        ),
    ).encode("utf-8")
    headers = PyForgeStationClient(
        station=_STATION,
        base_url=host,
        assertion=assertion,
        transport=station_transport,
    ).build_headers(
        extra={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        raw = station_transport("POST", f"{host}{_MCP_PATH}", headers, body)
    except Exception:  # noqa: BLE001
        return None
    result, error = _parse_jsonrpc_response(raw)
    if error is not None:
        return None
    tasks = _extract_tasks(result)
    if tasks is None:
        return None
    return tasks
