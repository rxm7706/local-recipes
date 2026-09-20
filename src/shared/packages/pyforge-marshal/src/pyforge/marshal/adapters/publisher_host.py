"""``HostPublisher`` — the one run-state publisher (Story 33.4, CAP-18).

Reaches the host supervisor store over ``POST {PYFORGE_HOST}/stations/marshal/mcp``
via ``pyforge.core.client.PyForgeStationClient`` transport + ``pyforge.core.assertion.HostMintClient``
assertion mint. Failures invoke an optional callback; this module never raises
to callers (best-effort, mirroring the host-side run-started publish helper).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping

from pyforge.core.assertion import MAX_TTL_SECONDS, HostMintClient
from pyforge.core.client import PyForgeStationClient, Transport

from ..core.publish import shape_heartbeat
from ..ports.publisher import PublishRecord

_DEFAULT_HOST = "http://127.0.0.1:8000"
_BEARER_ENV = "PYFORGE_IDP_BEARER_FILE"
_HOST_ENV = "PYFORGE_HOST"
_STATION = "marshal"
_MCP_PATH = f"/stations/{_STATION}/mcp"
_PUBLISH_TOOL = "publish_loop_run"
_HEARTBEAT_TOOL = "heartbeat_loop_run"
_COMPLETE_TOOL = "complete_loop_run"
_ASSERTION_REFRESH_S = max(1, MAX_TTL_SECONDS - 30)
_JSONRPC_ID = 1

PublishFindingCallback = Callable[[str, str], None]


def _default_host() -> str:
    raw = os.environ.get(_HOST_ENV, _DEFAULT_HOST)
    return raw.rstrip("/") if isinstance(raw, str) and raw.strip() else _DEFAULT_HOST


def _default_bearer_file() -> str:
    return os.environ.get(_BEARER_ENV, "")


def _read_bearer(path: str) -> str | None:
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return None
    token = raw.strip()
    return token or None


def _record_to_payload(record: PublishRecord) -> dict[str, object]:
    payload: dict[str, object] = {
        "station": record.station,
        "run_id": record.run_id,
        "run_kind": record.run_kind,
    }
    if record.story_key is not None:
        payload["story_key"] = record.story_key
    if record.phase is not None:
        payload["phase"] = record.phase
    if record.commit_sha is not None:
        payload["commit_sha"] = record.commit_sha
    if record.harness_run_id is not None:
        payload["harness_run_id"] = record.harness_run_id
    if record.layer_savings:
        payload["layer_savings"] = dict(record.layer_savings)
    return payload


def _jsonrpc_call(tool_name: str, arguments: Mapping[str, object]) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": _JSONRPC_ID,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": dict(arguments)},
    }


def _extract_handle(payload: object) -> str | None:
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    if not isinstance(payload, dict):
        return None
    for key in ("handle", "run_handle", "run_ref"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    content = payload.get("content")
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
                if text.strip():
                    return text.strip()
                continue
            handle = _extract_handle(nested)
            if handle is not None:
                return handle
    result = payload.get("result")
    if result is not payload:
        return _extract_handle(result)
    return None


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


def _resolve_transport(transport: Transport | None) -> Transport:
    if transport is not None:
        return transport
    client = PyForgeStationClient(station=_STATION)

    def _default(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
        return client._urllib(method, url, headers, body)  # noqa: SLF001

    return _default


def _mint_transport_from_station_transport(transport: Transport) -> Callable[..., bytes]:
    def mint_transport(url: str, headers: dict[str, str], body: bytes) -> bytes:
        return transport("POST", url, headers, body)

    return mint_transport


class HostPublisher:
    """``RunPublisherPort``'s host-reach implementation — sole ``pyforge.core.client`` publisher."""

    def __init__(
        self,
        *,
        on_finding: PublishFindingCallback | None = None,
        base_url: str | None = None,
        bearer_file: str | None = None,
        transport: Transport | None = None,
        mint_transport: Callable[..., bytes] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._on_finding = on_finding
        self._base_url = (base_url or _default_host()).rstrip("/")
        self._bearer_file = bearer_file if bearer_file is not None else _default_bearer_file()
        self._transport = _resolve_transport(transport)
        mint_callable = mint_transport or _mint_transport_from_station_transport(self._transport)
        self._mint_client = HostMintClient(
            f"{self._base_url}/assertion/mint/",
            transport=mint_callable,
        )
        self._monotonic = monotonic
        self._assertion = ""
        self._assertion_minted_at: float | None = None
        self._client = PyForgeStationClient(
            station=_STATION,
            base_url=self._base_url,
            transport=self._transport,
        )

    def _report(self, operation: str, message: str) -> None:
        if self._on_finding is None:
            return
        try:
            self._on_finding(operation, message)
        except Exception:  # noqa: BLE001 -- finding callback must never abort publish path
            return

    def _mcp_url(self) -> str:
        return f"{self._base_url}{_MCP_PATH}"

    def _ensure_assertion(self) -> str | None:
        now = self._monotonic()
        if (
            self._assertion
            and self._assertion_minted_at is not None
            and (now - self._assertion_minted_at) < _ASSERTION_REFRESH_S
        ):
            return self._assertion
        bearer = _read_bearer(self._bearer_file)
        if bearer is None:
            self._report(
                "publish",
                f"run-state publish skipped: {_BEARER_ENV} unset or unreadable",
            )
            return None
        try:
            assertion = self._mint_client.emit(idp_bearer=bearer, station=_STATION)
        except Exception as exc:  # noqa: BLE001 -- mint failures are best-effort findings
            self._report("publish", f"assertion mint failed: {exc}")
            return None
        self._assertion = assertion
        self._assertion_minted_at = now
        self._client = PyForgeStationClient(
            station=_STATION,
            base_url=self._base_url,
            assertion=assertion,
            transport=self._transport,
        )
        return assertion

    def _post_mcp(
        self,
        tool_name: str,
        arguments: Mapping[str, object],
    ) -> tuple[object | None, str | None]:
        body = json.dumps(_jsonrpc_call(tool_name, arguments)).encode("utf-8")
        headers = self._client.build_headers(
            extra={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            raw = self._transport("POST", self._mcp_url(), headers, body)
        except Exception as exc:  # noqa: BLE001 -- transport failures are best-effort findings
            return None, f"MCP transport failed: {exc}"
        return _parse_jsonrpc_response(raw)

    def _tool_arguments(self, arguments: Mapping[str, object]) -> dict[str, object]:
        payload = dict(arguments)
        if self._assertion and "assertion" not in payload:
            payload["assertion"] = self._assertion
        return payload

    def _call_tool(
        self,
        operation: str,
        tool_name: str,
        arguments: Mapping[str, object],
    ) -> object | None:
        result, error = self._post_mcp(tool_name, self._tool_arguments(arguments))
        if error is not None:
            self._report(operation, error)
            return None
        return result

    def publish(self, record: PublishRecord) -> str | None:
        if self._ensure_assertion() is None:
            return None
        # publish_loop_run(assertion, payload=...) -- payload is a nested
        # field on the real tool's schema, not spread kwargs (see
        # django_marshal_portal.mcp_asgi's own docstring).
        result = self._call_tool(
            "publish",
            _PUBLISH_TOOL,
            {"payload": _record_to_payload(record)},
        )
        if result is None:
            return None
        handle = _extract_handle(result)
        if handle is None:
            self._report("publish", f"{_PUBLISH_TOOL} returned no handle")
            return None
        return handle

    def heartbeat(self, handle: str) -> None:
        if not handle:
            return
        if self._ensure_assertion() is None:
            return
        # heartbeat_loop_run(handle, payload=...) -- same nested-payload
        # shape as publish_loop_run; this heartbeat never carries extra data.
        arguments = shape_heartbeat(handle)
        arguments["payload"] = {}
        self._call_tool("heartbeat", _HEARTBEAT_TOOL, arguments)

    def complete(
        self,
        handle: str,
        *,
        status: str,
        result: Mapping[str, object],
    ) -> None:
        if not handle:
            return
        if self._ensure_assertion() is None:
            return
        arguments: dict[str, object] = {
            "handle": handle,
            "status": status,
            "result": dict(result),
        }
        self._call_tool("complete", _COMPLETE_TOOL, arguments)
