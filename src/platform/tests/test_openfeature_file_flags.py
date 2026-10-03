"""Story 26.4 — one FILE flag tree flips Django, MCP, and CLI (FR-34 / AD-11).

Story 76.1 adds the per-environment rendering: the value-only
``flag-overlays.json`` beside the tree, ``PYFORGE_ENVIRONMENT``, and the chart's
ConfigMap carrying the tree rendered for ``flags.environment``. The host's FILE
provider, ``evaluate_from_source`` and the CLI reader
(``pyforge.core.flags.read_boolean``, reached through ``django_pyforge.flags``
because this package's import-linter contract bars ``pyforge`` imports) must
agree for every key in every environment.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import date
from datetime import timedelta
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
from django_pyforge.flags import evaluate_cli_boolean
from django_pyforge.flags import evaluate_cutover_root
from django_pyforge.flags import evaluate_from_source
from django_pyforge.flags import flags_asgi_app
from django_pyforge.flags import main as flags_main
from django_pyforge.flags import read_flag_tree_bytes
from django_pyforge.flags import render_flag_tree
from django_pyforge.flags import resolve_flags_path
from django_pyforge.flags import resolve_tree_path
from django_pyforge.flags import tree_view
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.mcp_http import register_station_mcp_app
from starlette.testclient import TestClient

from tests.helm_gate import requires_helm

pytest.importorskip("openfeature")
pytest.importorskip("openfeature.contrib.provider.flagd")

_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_FLAGS_JSON = _PLATFORM_DIR / "config" / "flags.json"
_OVERLAYS_JSON = _PLATFORM_DIR / "config" / "flag-overlays.json"
_ENVIRONMENTS = ("dev", "staging", "production")
_ENV_ENVIRONMENT = "PYFORGE_ENVIRONMENT"
_CORE_CHART = _PLATFORM_DIR / "deploy" / "charts" / "platform"

_TEST_IMAGE_DIGEST = "sha256:" + ("a" * 64)


def _helm_core(
    environment: str | None = "dev",
    *,
    tree: Path = _FLAGS_JSON,
    overlays: Path | None = _OVERLAYS_JSON,
) -> subprocess.CompletedProcess[str]:
    """`helm template` of the core chart, digests pinned; flag inputs are parameters."""
    argv = [
        "helm",
        "template",
        "platform",
        str(_CORE_CHART),
        "--set-file",
        f"flags.tree={tree}",
        # The chart refuses a mutable image default ("image.digest or
        # image.tag is required"); pin all three images by digest exactly
        # as tests/test_chart_invariants.py::_helm does.
        *(
            f"--set={prefix}.digest={_TEST_IMAGE_DIGEST}"
            for prefix in ("image", "sidecar.image", "mcpHost.image")
        ),
    ]
    if overlays is not None:
        argv += ["--set-file", f"flags.overlays={overlays}"]
    if environment is not None:
        argv += ["--set", f"flags.environment={environment}"]
    return subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _render_core(
    environment: str | None = "dev",
    *,
    tree: Path = _FLAGS_JSON,
    overlays: Path | None = _OVERLAYS_JSON,
) -> list[dict[str, Any]]:
    yaml = pytest.importorskip("yaml")
    result = _helm_core(environment, tree=tree, overlays=overlays)
    if result.returncode != 0:
        pytest.fail(result.stderr)
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def _flags_configmap(docs: list[dict[str, Any]]) -> dict[str, Any]:
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
    return json.loads(flags_maps[0]["data"]["flags.json"])


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
        isinstance(sample, dict) and "variants" in sample and "defaultVariant" in sample
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
    # Story 76.1: the one tree, rendered for the release's environment (dev here).
    # Since Story 84.4 a dev overlay may differ from its tree default (a flag ON in dev,
    # OFF in production), so the configmap is the dev render, carrying every tree key.
    rendered = _flags_configmap(docs)
    on_disk = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    assert rendered == json.loads(render_flag_tree("dev", _FLAGS_JSON))
    assert set(rendered["flags"]) == set(on_disk["flags"])

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
        assert env.get(_ENV_ENVIRONMENT) == "dev"
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


# --- Story 76.1: per-environment values ---------------------------------------

_OFF_IN_PRODUCTION = "pyforge.test.off_in_production"
# `configure_file_provider` waits on FLAG_KEY (FILE init is asynchronous), so every
# tree the provider loads defines it: it is the fixture's flag no overlay changes.
_ON_EVERYWHERE = FLAG_KEY
_KILLED = "pyforge.test.killed"
_OFF_BY_TREE = "pyforge.test.off_by_tree"
_BOOL_KEYS = (_OFF_IN_PRODUCTION, _ON_EVERYWHERE, _KILLED, _OFF_BY_TREE)
# What each key evaluates to per environment for the fixture pair below.
_EXPECTED = {
    "production": {
        _OFF_IN_PRODUCTION: False,
        _ON_EVERYWHERE: True,
        _KILLED: False,
        _OFF_BY_TREE: False,
    },
    "staging": {
        _OFF_IN_PRODUCTION: True,
        _ON_EVERYWHERE: True,
        _KILLED: False,
        _OFF_BY_TREE: True,
    },
    "dev": {
        _OFF_IN_PRODUCTION: True,
        _ON_EVERYWHERE: True,
        _KILLED: False,
        _OFF_BY_TREE: False,
    },
}


def _metadata(on_everywhere: str = "") -> dict[str, str]:
    """The five-field flagd `metadata` (Story 76.2); the clock is dated + 90 days."""
    cleanup_by = ""
    if on_everywhere:
        cleanup_by = (
            date.fromisoformat(on_everywhere) + timedelta(days=90)
        ).isoformat()
    return {
        "owner": "steward",
        "story": "76-2-a-fixture",
        "created": "2026-09-01",
        "on_everywhere": on_everywhere,
        "cleanup_by": cleanup_by,
    }


def _entry(
    default_variant: str, *, state: str = "ENABLED", on_everywhere: str = ""
) -> dict[str, Any]:
    return {
        "state": state,
        "variants": {"on": True, "off": False},
        "defaultVariant": default_variant,
        "metadata": _metadata(on_everywhere),
    }


# The fixture pair's overlay document: what each environment renders differently.
_FIXTURE_OVERLAYS: dict[str, dict[str, str]] = {
    "dev": {
        _OFF_IN_PRODUCTION: "on",
        _ON_EVERYWHERE: "on",
        _KILLED: "on",
        _OFF_BY_TREE: "off",
    },
    "staging": {_OFF_IN_PRODUCTION: "on", _KILLED: "on", _OFF_BY_TREE: "on"},
    "production": {_OFF_IN_PRODUCTION: "off", _KILLED: "on"},
}


def _fixture_flags(document: object) -> dict[str, Any]:
    """The fixture's four boolean flags, dated only where `document` renders one ON in
    every environment (the clock the metadata check requires)."""
    named = document if isinstance(document, dict) else {}
    tree_defaults = {
        _OFF_IN_PRODUCTION: ("on", "ENABLED"),
        _ON_EVERYWHERE: ("on", "ENABLED"),
        _KILLED: ("on", "DISABLED"),
        _OFF_BY_TREE: ("off", "ENABLED"),
    }

    def _on(key: str, environment: str) -> bool:
        default, state = tree_defaults[key]
        overlay = named.get(environment)
        variant = overlay.get(key, default) if isinstance(overlay, dict) else default
        if state == "DISABLED":  # compose ignores the overlay for a killed flag
            variant = default
        return variant == "on"

    return {
        key: _entry(
            default,
            state=state,
            on_everywhere=(
                "2026-09-01" if all(_on(key, env) for env in _ENVIRONMENTS) else ""
            ),
        )
        for key, (default, state) in tree_defaults.items()
    }


def _fixture_pair(directory: Path, overlays: object | None = None) -> Path:
    """A tree (four boolean flags) and its sibling overlay document; the tree."""
    document = overlays if overlays is not None else _FIXTURE_OVERLAYS
    tree = directory / "flags.json"
    tree.write_text(
        json.dumps({"flags": _fixture_flags(document)}, indent=2),
        encoding="utf-8",
    )
    (directory / "flag-overlays.json").write_text(
        json.dumps(document, indent=2), encoding="utf-8"
    )
    return tree


def _isolate_flag_environment(
    monkeypatch: pytest.MonkeyPatch, tree: Path, environment: str | None
) -> None:
    """`configure_file_provider` writes these process-wide; monkeypatch restores."""
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("FLAGD_OFFLINE_FLAG_SOURCE_PATH", str(tree))
    if environment is None:
        monkeypatch.delenv(_ENV_ENVIRONMENT, raising=False)
    else:
        monkeypatch.setenv(_ENV_ENVIRONMENT, environment)


def _three_readings(tree: Path, key: str) -> tuple[bool, bool, bool]:
    """(FILE provider over the resolved file, evaluate_from_source, CLI reader)."""
    path = resolve_flags_path(tree)
    assert path is not None
    configure_file_provider(path)
    provider = evaluate_boolean(key)
    return (
        provider,
        evaluate_from_source(key=key, source=tree),
        evaluate_cli_boolean(key, source=tree),
    )


@pytest.mark.parametrize("environment", _ENVIRONMENTS)
def test_host_provider_evaluate_from_source_and_cli_reader_agree_per_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    tree = _fixture_pair(tmp_path)
    _isolate_flag_environment(monkeypatch, tree, environment)
    for key in _BOOL_KEYS:
        assert _three_readings(tree, key) == (_EXPECTED[environment][key],) * 3, (
            environment,
            key,
        )


def test_an_unset_environment_reads_the_dev_rendering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = _fixture_pair(tmp_path)
    _isolate_flag_environment(monkeypatch, tree, None)
    for key in _BOOL_KEYS:
        assert _three_readings(tree, key) == (_EXPECTED["dev"][key],) * 3, key


_CUTOVER_KEY = "pyforge.cutover_root"


def _assert_cutover_root_agrees(tree: Path, environment: str) -> None:
    """The non-boolean key: the FILE provider's string, the CLI reader
    (`read_cutover_root`, which composes the overlay itself) and the rendered tree."""
    from openfeature import api  # noqa: PLC0415 -- after the importorskip above

    path = resolve_flags_path(tree)
    assert path is not None
    configure_file_provider(path)
    provider = api.get_client().get_string_value(_CUTOVER_KEY, "")
    entry = json.loads(render_flag_tree(environment, tree))["flags"][_CUTOVER_KEY]
    rendered = entry["variants"][entry["defaultVariant"]]
    assert provider == evaluate_cutover_root(tree) == rendered, environment


@pytest.mark.parametrize("environment", _ENVIRONMENTS)
def test_the_shipped_tree_and_overlay_agree_across_the_three_readers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    payload = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    boolean_keys = [
        key
        for key, entry in payload["flags"].items()
        if all(isinstance(value, bool) for value in entry["variants"].values())
    ]
    assert boolean_keys, "the shipped tree defines at least one boolean flag"
    _isolate_flag_environment(monkeypatch, _FLAGS_JSON, environment)
    for key in boolean_keys:
        provider, from_source, cli = _three_readings(_FLAGS_JSON, key)
        assert provider == from_source == cli, (environment, key)
    _assert_cutover_root_agrees(_FLAGS_JSON, environment)


# Story 76.2: what every key in the shipped tree evaluates to, per environment -- the
# values before the tree carried metadata. Metadata is inert to evaluation.
_SHIPPED_BOOLEANS = {
    "pyforge.three_surfaces": True,
    "pyforge.steward.ghe_fleet_credentials": False,
    "pyforge.steward.object_store_consumer": False,
    "pyforge.steward.sync_github_only_marker": {
        "dev": True,
        "staging": True,
        "production": False,
    },
    # Story 85.1 (CAP-286): dormant -- off everywhere until Story 85.3.
    "pyforge.marshal.verify_fix_loop": False,
}
_METADATA_FIELDS = ("owner", "story", "created", "on_everywhere", "cleanup_by")


@pytest.mark.parametrize("environment", _ENVIRONMENTS)
def test_the_shipped_tree_with_metadata_evaluates_as_it_did_without(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    payload = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    assert set(payload["flags"]) == {*_SHIPPED_BOOLEANS, _CUTOVER_KEY}, (
        "a key joined or left the shipped tree: state its evaluation here"
    )
    _isolate_flag_environment(monkeypatch, _FLAGS_JSON, environment)
    for key, expected in _SHIPPED_BOOLEANS.items():
        expected_val = expected[environment] if isinstance(expected, dict) else expected
        readings = _three_readings(_FLAGS_JSON, key)
        assert readings == (expected_val,) * 3, (environment, key)
    _assert_cutover_root_agrees(_FLAGS_JSON, environment)
    assert evaluate_cutover_root(_FLAGS_JSON) == "local-recipes"


@pytest.mark.parametrize("environment", _ENVIRONMENTS)
def test_every_flag_in_the_shipped_tree_carries_its_metadata_through_the_file_provider(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    from openfeature import api  # noqa: PLC0415 -- after the importorskip above

    payload = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    _isolate_flag_environment(monkeypatch, _FLAGS_JSON, environment)
    path = resolve_flags_path(_FLAGS_JSON)
    assert path is not None
    configure_file_provider(path)
    client = api.get_client()
    for key, entry in payload["flags"].items():
        metadata = entry["metadata"]
        assert tuple(metadata) == _METADATA_FIELDS, key
        assert all(isinstance(value, str) for value in metadata.values()), key
        details = (
            client.get_boolean_details(key, default_value=False)
            if key in _SHIPPED_BOOLEANS
            else client.get_string_details(key, "")
        )
        assert details.error_code is None, (environment, key, details)
        assert details.flag_metadata == metadata, (environment, key)
        rendered = json.loads(render_flag_tree(environment, _FLAGS_JSON))
        assert rendered["flags"][key]["metadata"] == metadata, (environment, key)


@pytest.mark.parametrize(
    ("environment", "expected"),
    [("dev", "local-recipes"), ("staging", "local-recipes"), ("production", "foundry")],
)
def test_the_non_boolean_key_follows_the_overlay_on_every_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    expected: str,
) -> None:
    tree = tmp_path / "flags.json"
    tree.write_text(
        json.dumps(
            {
                "flags": {
                    FLAG_KEY: _entry("on", on_everywhere="2026-09-01"),
                    _CUTOVER_KEY: {
                        "state": "ENABLED",
                        "variants": {
                            "local-recipes": "local-recipes",
                            "foundry": "foundry",
                        },
                        "defaultVariant": "local-recipes",
                        "metadata": _metadata(),
                    },
                },
            },
        ),
        encoding="utf-8",
    )
    (tmp_path / "flag-overlays.json").write_text(
        json.dumps({"production": {_CUTOVER_KEY: "foundry"}}), encoding="utf-8"
    )
    _isolate_flag_environment(monkeypatch, tree, environment)
    _assert_cutover_root_agrees(tree, environment)
    assert evaluate_cutover_root(tree) == expected


def test_the_provider_reads_a_materialised_copy_and_the_tree_stays_the_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = _fixture_pair(tmp_path)
    _isolate_flag_environment(monkeypatch, tree, "production")
    resolved = resolve_flags_path(tree)
    assert resolved is not None
    assert resolved != tree
    assert json.loads(resolved.read_text(encoding="utf-8")) == json.loads(
        render_flag_tree("production", tree)
    )
    assert (
        resolve_tree_path(tree) == tree
    )  # what an actuator (doctor's kill switch) edits
    # a later edit of the overlay reaches the same file the provider polls (the edit
    # keeps every flag's dated clock true: `_OFF_BY_TREE` is still off in dev)
    production = {**_FIXTURE_OVERLAYS["production"], _OFF_BY_TREE: "on"}
    edited = {**_FIXTURE_OVERLAYS, "production": production}
    (tmp_path / "flag-overlays.json").write_text(json.dumps(edited), encoding="utf-8")
    assert resolve_flags_path(tree) == resolved
    assert (
        json.loads(resolved.read_text(encoding="utf-8"))["flags"][_OFF_BY_TREE][
            "defaultVariant"
        ]
        == "on"
    )


def test_a_mounted_rendered_tree_has_no_sibling_and_is_used_as_it_is(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mount = tmp_path / "mount"
    mount.mkdir()
    path = mount / "flags.json"
    path.write_bytes(_flagd_tree("off"))
    for environment in _ENVIRONMENTS:
        _isolate_flag_environment(monkeypatch, path, environment)
        assert resolve_flags_path(path) == path
        assert read_flag_tree_bytes(path) == path.read_bytes()
        assert _three_readings(path, FLAG_KEY) == (False, False, False)


def test_an_unknown_environment_refuses_on_every_host_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _fixture_pair(tmp_path)
    _isolate_flag_environment(monkeypatch, tree, "qa")
    for call in (
        lambda: resolve_flags_path(tree),
        lambda: read_flag_tree_bytes(tree),
        lambda: evaluate_from_source(key=_ON_EVERYWHERE, source=tree),
        lambda: evaluate_cli_boolean(_ON_EVERYWHERE, default=True, source=tree),
    ):
        with pytest.raises(ValueError, match="qa"):
            call()
    assert flags_main([_ON_EVERYWHERE, "--source", str(tree)]) == 1
    assert "qa" in capsys.readouterr().err


def test_tree_view_serves_the_rendering_for_the_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = _fixture_pair(tmp_path)
    _isolate_flag_environment(monkeypatch, tree, "production")
    request = RequestFactory().get("/flags.json")
    request.user = type("U", (), {"is_authenticated": True})()
    response = tree_view(request)
    assert response.status_code == HTTPStatus.OK
    served = json.loads(response.content)
    assert served == json.loads(render_flag_tree("production", tree))
    assert served["flags"][_OFF_IN_PRODUCTION]["defaultVariant"] == "off"


def test_render_verb_writes_the_tree_for_the_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _fixture_pair(tmp_path)
    monkeypatch.delenv(_ENV_ENVIRONMENT, raising=False)
    out = tmp_path / "out" / "flags.json"
    assert (
        flags_main(
            [
                "render",
                "--environment",
                "production",
                "--source",
                str(tree),
                "--output",
                str(out),
            ]
        )
        == 0
    )
    assert out.read_bytes() == render_flag_tree("production", tree)
    assert (
        json.loads(out.read_bytes())["flags"][_OFF_IN_PRODUCTION]["defaultVariant"]
        == "off"
    )
    assert (
        flags_main(["render", "--environment", "staging", "--source", str(tree)]) == 0
    )
    assert capsys.readouterr().out.encode() == render_flag_tree("staging", tree)


def test_render_verb_refuses_with_the_named_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _fixture_pair(tmp_path)
    assert flags_main(["render", "--environment", "qa", "--source", str(tree)]) == 1
    assert "qa" in capsys.readouterr().err
    _fixture_pair(tmp_path, {"production": {"pyforge.test.missing": "off"}})
    assert flags_main(["render", "--environment", "dev", "--source", str(tree)]) == 1
    assert "pyforge.test.missing" in capsys.readouterr().err
    assert (
        flags_main(
            [
                "render",
                "--environment",
                "dev",
                "--source",
                str(tmp_path / "absent.json"),
            ]
        )
        == 1
    )
    assert "no flag tree" in capsys.readouterr().err
    with pytest.raises(SystemExit):  # --environment is required
        flags_main(["render"])


def test_render_verb_reports_an_unwritable_output_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _fixture_pair(tmp_path)
    blocker = tmp_path / "a-file"
    blocker.write_text("not a directory", encoding="utf-8")
    for output in (
        blocker / "flags.json",
        tmp_path,
    ):  # a parent that is a file; a directory
        argv = ["render", "--environment", "dev", "--source", str(tree)]
        assert flags_main([*argv, "--output", str(output)]) == 1
        err = capsys.readouterr().err
        assert "cannot write" in err
        assert str(output) in err
        assert "Traceback" not in err


def test_without_pyforge_core_the_host_reads_the_tree_as_it_is(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The mcp-host sidecar image copies `django_pyforge` but not `pyforge/core`, and
    its `AppConfig.ready()` calls `configure_from_env()` -> `resolve_flags_path()`. With
    `pyforge` unimportable the resolver must return the tree (or None), never raise."""
    tree = _fixture_pair(tmp_path)
    _isolate_flag_environment(monkeypatch, tree, "production")
    monkeypatch.setattr(
        "django_pyforge.flags.IN_CLUSTER_FLAGS_PATH", tmp_path / "absent" / "flags.json"
    )
    monkeypatch.setitem(sys.modules, "pyforge", None)
    monkeypatch.setitem(sys.modules, "pyforge.core", None)
    monkeypatch.setitem(sys.modules, "pyforge.core.flags", None)
    with pytest.raises(ImportError):
        __import__("pyforge.core.flags")  # the block is real
    assert resolve_flags_path() == tree  # PYFORGE_FLAGS_PATH
    assert resolve_flags_path(tree) == tree
    assert read_flag_tree_bytes(tree) == tree.read_bytes()
    monkeypatch.delenv("PYFORGE_FLAGS_PATH")
    monkeypatch.delenv("FLAGD_OFFLINE_FLAG_SOURCE_PATH")
    monkeypatch.chdir(tmp_path)  # no src/platform/config/flags.json above
    assert resolve_flags_path() is None


def _configmap_defaults(rendered: dict[str, Any]) -> dict[str, str]:
    return {key: entry["defaultVariant"] for key, entry in rendered["flags"].items()}


@requires_helm
@pytest.mark.parametrize("environment", _ENVIRONMENTS)
def test_chart_configmap_is_the_tree_rendered_for_the_environment(
    environment: str,
) -> None:
    docs = _render_core(environment)
    assert _flags_configmap(docs) == json.loads(
        render_flag_tree(environment, _FLAGS_JSON)
    )
    pods = [
        doc["spec"]["template"]["spec"]
        for doc in docs
        if doc.get("kind") in {"Deployment", "StatefulSet", "Job"}
    ] + [
        doc["spec"]["jobTemplate"]["spec"]["template"]["spec"]
        for doc in docs
        if doc.get("kind") == "CronJob"
    ]
    readers = 0
    for spec in pods:
        for container in [*spec["containers"], *(spec.get("initContainers") or [])]:
            env = {
                item["name"]: item.get("value") for item in container.get("env") or []
            }
            mounts_flags = any(
                mount.get("name") == "flags"
                for mount in container.get("volumeMounts") or []
            )
            if "PYFORGE_FLAGS_PATH" in env or mounts_flags:
                readers += 1
            # a workload that mounts the tree names the environment it was rendered for
            if mounts_flags:
                assert env.get(_ENV_ENVIRONMENT) == environment, container["name"]
            if "PYFORGE_FLAGS_PATH" in env:
                assert env.get(_ENV_ENVIRONMENT) == environment, container["name"]
    assert readers, "at least one workload reads the flag tree"


@requires_helm
def test_chart_production_and_dev_configmaps_differ_exactly_by_the_overlay_values(
    tmp_path: Path,
) -> None:
    tree = _fixture_pair(tmp_path)
    overlays = tmp_path / "flag-overlays.json"
    rendered = {
        env: _flags_configmap(_render_core(env, tree=tree, overlays=overlays))
        for env in _ENVIRONMENTS
    }
    for env, cm in rendered.items():
        assert cm == json.loads(render_flag_tree(env, tree)), env
    production, dev = rendered["production"], rendered["dev"]
    assert production != dev
    differing = {
        key
        for key in _BOOL_KEYS
        if _configmap_defaults(production)[key] != _configmap_defaults(dev)[key]
    }
    assert differing == {_OFF_IN_PRODUCTION}
    # everything but that one defaultVariant is identical
    patched = json.loads(json.dumps(dev))
    patched["flags"][_OFF_IN_PRODUCTION]["defaultVariant"] = "off"
    assert patched == production
    # and staging is the only place the tree's off flag turns on
    assert _configmap_defaults(rendered["staging"])[_OFF_BY_TREE] == "on"
    assert (
        _configmap_defaults(dev)[_OFF_BY_TREE]
        == _configmap_defaults(production)[_OFF_BY_TREE]
        == "off"
    )


@requires_helm
def test_chart_keeps_a_disabled_flag_disabled_in_every_environment(
    tmp_path: Path,
) -> None:
    tree = _fixture_pair(tmp_path, {env: {_KILLED: "on"} for env in _ENVIRONMENTS})
    overlays = tmp_path / "flag-overlays.json"
    for env in _ENVIRONMENTS:
        cm = _flags_configmap(_render_core(env, tree=tree, overlays=overlays))
        assert cm["flags"][_KILLED]["state"] == "DISABLED"
        assert cm["flags"][_KILLED]["defaultVariant"] == "on"
        assert cm == json.loads(render_flag_tree(env, tree))


@requires_helm
@pytest.mark.parametrize("environment", [None, "", "qa", "prod", "Production"])
def test_chart_refuses_a_release_without_a_valid_flags_environment(
    environment: str | None,
) -> None:
    result = _helm_core(environment)
    assert result.returncode != 0, result.stdout
    assert "flags.environment" in result.stderr


@requires_helm
def test_chart_refuses_a_release_without_the_overlay_document() -> None:
    result = _helm_core("production", overlays=None)
    assert result.returncode != 0, result.stdout
    assert "flags.overlays" in result.stderr


# (overlay document, the chart's message fragment, the core error's class name): the
# chart and pyforge.core.flags.compose refuse the same overlays, each naming the
# offending entry.
_REFUSED_OVERLAYS = [
    pytest.param(
        {"production": {"pyforge.nope": "off"}},
        "names a key the tree lacks",
        "OverlayUnknownKeyError",
        id="key",
    ),
    pytest.param(
        {"staging": {_ON_EVERYWHERE: "maybe"}},
        'names variant "maybe"',
        "OverlayUnknownVariantError",
        id="variant",
    ),
    pytest.param(
        {
            "production": {
                _ON_EVERYWHERE: {"variants": {"on": True}, "defaultVariant": "on"}
            }
        },
        "is not a variant name",
        "OverlayNotAVariantError",
        id="object",
    ),
    pytest.param(
        {"qa": {_ON_EVERYWHERE: "off"}},
        'environment "qa"',
        "UnknownEnvironmentError",
        id="environment",
    ),
]


@requires_helm
@pytest.mark.parametrize(("overlay", "fragment", "error"), _REFUSED_OVERLAYS)
def test_chart_and_core_refuse_the_same_overlays_naming_the_entry(
    tmp_path: Path,
    overlay: dict[str, Any],
    fragment: str,
    error: str,
) -> None:
    tree = _fixture_pair(tmp_path, overlay)
    result = _helm_core("dev", tree=tree, overlays=tmp_path / "flag-overlays.json")
    assert result.returncode != 0, result.stdout
    assert fragment in result.stderr, result.stderr
    with pytest.raises(ValueError) as caught:  # noqa: PT011 -- the class is asserted by name below
        render_flag_tree("dev", tree)
    assert type(caught.value).__name__ == error
    for name in overlay:
        assert name in result.stderr
        assert name in str(caught.value)
