"""Story 33.12 — published-plane reader against injected transport."""

from __future__ import annotations

import json

from pyforge.core.published_loop import fetch_story_tasks


def test_fetch_story_tasks_parses_mcp_content() -> None:
    calls: list[tuple[str, str]] = []

    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
        calls.append((method, url))
        if url.endswith("/assertion/mint/"):
            return json.dumps({"assertion": "svc-token"}).encode("utf-8")
        payload = json.loads(body.decode("utf-8"))
        assert payload["params"]["name"] == "list_loop_story_tasks"
        result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"33-12": {"phase": "running", "commit_sha": "deadbeef"}},
                    ),
                },
            ],
        }
        return json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode("utf-8")

    tasks = fetch_story_tasks(
        "marshal",
        base_url="http://127.0.0.1:8000",
        bearer_file="eyJ.local",
        transport=transport,
    )
    assert tasks == {"33-12": {"phase": "running", "commit_sha": "deadbeef"}}
    assert calls[0][0] == "POST"


def test_fetch_story_tasks_returns_none_on_unparseable_mcp_result() -> None:
    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
        if url.endswith("/assertion/mint/"):
            return json.dumps({"assertion": "svc-token"}).encode("utf-8")
        return json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": []}}).encode(
            "utf-8",
        )

    assert (
        fetch_story_tasks(
            "marshal",
            base_url="http://127.0.0.1:8000",
            bearer_file="eyJ.local",
            transport=transport,
        )
        is None
    )
