"""Story 26.4 — one FILE flag tree flips Django, MCP, and CLI (FR-34 / AD-11)."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.flags import FLAG_KEY
from django_pyforge.flags import configure_file_provider
from django_pyforge.flags import eval_view
from django_pyforge.flags import evaluate_boolean
from django_pyforge.flags import evaluate_from_source
from django_pyforge.flags import flags_asgi_app
from django_pyforge.flags import tree_view
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.mcp_http import register_station_mcp_app
from starlette.testclient import TestClient

pytest.importorskip("openfeature")
pytest.importorskip("openfeature.contrib.provider.flagd")

_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_FLAGS_JSON = _PLATFORM_DIR / "config" / "flags.json"
_CORE_CHART = _PLATFORM_DIR / "deploy" / "charts" / "platform"

requires_helm = pytest.mark.skipif(
    shutil.which("helm") is None,
    reason="helm not on PATH (AD-16: platform-dev pixi env)",
)


def _render_core() -> list[dict[str, Any]]:
    yaml = pytest.importorskip("yaml")
    flags = _PLATFORM_DIR / "config" / "flags.json"
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "helm",
            "template",
            "platform",
            str(_CORE_CHART),
            "--set-file",
            f"flags.tree={flags}",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def _flagd_tree(default_variant: str) -> bytes:
    return json.dumps(
        {
            "flags": {
                FLAG_KEY: {
                    "state": "ENABLED",
                    "variants": {"on": True, "off": False},
                    "defaultVariant": default_variant,
                },
            },
        },
        indent=2,
    ).encode()


def _looks_like_flagd(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    flags = payload.get("flags") if isinstance(payload, dict) else None
    if not isinstance(flags, dict) or not flags:
        return False
    sample = next(iter(flags.values()))
    return (
        isinstance(sample, dict)
        and "variants" in sample
        and "defaultVariant" in sample
    )


def _django_value(key: str) -> bool:
    request = RequestFactory().get(f"/flags/{key}/")
    request.user = type("U", (), {"is_authenticated": True})()
    response = eval_view(request, key)
    assert response.status_code == HTTPStatus.OK
    payload = json.loads(response.content)
    return bool(payload["value"])


def _mcp_host():
    mcp_app = flags_asgi_app()

    async def application(scope: dict[str, Any], receive: Any, send: Any) -> None:
        register_station_mcp_app("flags", mcp_app)
        if scope["type"] == "lifespan":
            await mcp_app(scope, receive, send)
            return
        if await dispatch_station_mcp(scope, receive, send):
            return
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [(b"content-type", b"text/plain")],
            },
        )
        await send({"type": "http.response.body", "body": b"not mcp"})

    return application


def _mcp_value(key: str) -> bool:
    # Story 42.1: the flags face sits behind the same transport gate as every
    # other station, so the fixture carries an `mcp:flags` assertion.
    authorization = "Bearer " + mint_assertion(
        sub="flag-fixture",
        roles=["pyforge:station:flags"],
        station="flags",
    )
    with TestClient(_mcp_host()) as client:
        init = client.post(
            "/stations/flags/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "flag-fixture", "version": "0"},
                },
            },
            headers={
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "authorization": authorization,
            },
        )
        assert init.status_code < HTTPStatus.INTERNAL_SERVER_ERROR, init.text
        response = client.post(
            "/stations/flags/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "get_flag", "arguments": {"key": key}},
            },
            headers={
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "mcp-protocol-version": "2025-03-26",
                "authorization": authorization,
            },
        )
    assert response.status_code == HTTPStatus.OK, response.text
    body = response.json()
    result = body.get("result") or {}
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and "result" in structured:
        return bool(structured["result"])
    content = result.get("content") or []
    if content and isinstance(content[0], dict) and "text" in content[0]:
        text = content[0]["text"]
        if text in {"true", "True"}:
            return True
        if text in {"false", "False"}:
            return False
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = text
        return bool(parsed)
    pytest.fail(f"unparseable MCP flag result: {body}")


def test_one_flag_tree_under_src_platform() -> None:
    trees = [
        path.resolve()
        for path in _PLATFORM_DIR.rglob("*")
        if path.is_file()
        and path.suffix == ".json"
        and "site-packages" not in path.parts
        and _looks_like_flagd(path)
    ]
    unique = sorted(set(trees))
    assert unique == [_FLAGS_JSON.resolve()], unique


def test_django_mcp_cli_see_the_same_evaluation(tmp_path: Path) -> None:
    path = tmp_path / "flags.json"
    path.write_bytes(_flagd_tree("on"))
    configure_file_provider(path)
    django_val = _django_value(FLAG_KEY)
    mcp_val = _mcp_value(FLAG_KEY)
    cli_val = evaluate_from_source(key=FLAG_KEY, source=path)
    assert django_val is True
    assert django_val == mcp_val == cli_val


def test_cli_host_fetch_evaluates_the_same_bytes(tmp_path: Path) -> None:
    path = tmp_path / "flags.json"
    path.write_bytes(_flagd_tree("off"))
    fetched = path.read_bytes()
    host_token = "operator-token"  # noqa: S105

    def _fetch(url: str, token: str) -> bytes:
        assert url.startswith("https://")
        assert token == host_token
        return fetched

    value = evaluate_from_source(
        key=FLAG_KEY,
        host="https://platform.internal/flags.json",
        token=host_token,
        fetch=_fetch,
        workdir=tmp_path,
    )
    assert value is False


def test_no_egress_during_evaluation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "flags.json"
    path.write_bytes(_flagd_tree("on"))
    configure_file_provider(path)

    def _blocked(*_args: object, **_kwargs: object) -> None:
        pytest.fail("egress during flag evaluation")

    monkeypatch.setattr("urllib.request.urlopen", _blocked)
    monkeypatch.setattr("socket.create_connection", _blocked)
    assert evaluate_boolean(FLAG_KEY) is True


def test_file_change_observed_without_process_restart(tmp_path: Path) -> None:
    path = tmp_path / "flags.json"
    path.write_bytes(_flagd_tree("off"))
    configure_file_provider(path)
    assert evaluate_boolean(FLAG_KEY) is False
    path.write_bytes(_flagd_tree("on"))
    deadline = time.monotonic() + 12
    observed = False
    while time.monotonic() < deadline:
        if evaluate_boolean(FLAG_KEY) is True:
            observed = True
            break
        time.sleep(0.5)
    assert observed, "FILE provider did not observe the on-disk change within 12s"


def test_unauthenticated_flag_views_are_forbidden() -> None:
    factory = RequestFactory()
    tree_req = factory.get("/flags.json")
    tree_req.user = AnonymousUser()
    eval_req = factory.get(f"/flags/{FLAG_KEY}/")
    eval_req.user = AnonymousUser()
    assert tree_view(tree_req).status_code == HTTPStatus.FORBIDDEN
    assert eval_view(eval_req, FLAG_KEY).status_code == HTTPStatus.FORBIDDEN


def test_src_platform_does_not_import_pyforge() -> None:
    text = (_PLATFORM_DIR / "config" / "urls.py").read_text(encoding="utf-8")
    assert "import pyforge" not in text
    assert "from pyforge" not in text


@requires_helm
def test_chart_configmap_is_the_one_tree_and_has_no_flag_sidecar() -> None:
    docs = _render_core()
    flags_maps = [
        doc
        for doc in docs
        if doc.get("kind") == "ConfigMap"
        and (doc.get("metadata") or {})
        .get("labels", {})
        .get("app.kubernetes.io/component")
        == "flags"
    ]
    assert len(flags_maps) == 1, flags_maps
    rendered = json.loads(flags_maps[0]["data"]["flags.json"])
    on_disk = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    assert rendered == on_disk

    blob = json.dumps(docs).lower()
    for needle in ("reloader", "stakater", "flagd:", "ghcr.io/open-feature/flagd"):
        assert needle not in blob, needle

    by_component: dict[str, dict[str, Any]] = {}
    for doc in docs:
        if doc.get("kind") not in {"Deployment", "StatefulSet", "Job"}:
            continue
        labels = (doc["spec"]["template"].get("metadata") or {}).get("labels") or {}
        component = labels.get("app.kubernetes.io/component")
        if component:
            by_component[component] = doc["spec"]["template"]["spec"]
    for component in ("web", "worker"):
        container = by_component[component]["containers"][0]
        env = {item["name"]: item.get("value") for item in container.get("env") or []}
        assert env.get("FLAGD_RESOLVER") == "file"
        assert env.get("FLAGD_OFFLINE_FLAG_SOURCE_PATH") == "/etc/pyforge/flags.json"
        mounts = container.get("volumeMounts") or []
        flags_mount = next(m for m in mounts if m.get("name") == "flags")
        assert flags_mount.get("mountPath") == "/etc/pyforge"
        assert flags_mount.get("readOnly") is True
        assert "subPath" not in flags_mount
        volumes = by_component[component].get("volumes") or []
        flags_vol = next(v for v in volumes if v.get("name") == "flags")
        assert flags_vol["configMap"]["name"] == "platform-flags"
        names = [c.get("name") for c in by_component[component]["containers"]]
        assert names == [container.get("name")]
    migrate_vols = by_component["migrate"].get("volumes") or []
    assert not any(v.get("name") == "flags" for v in migrate_vols)
