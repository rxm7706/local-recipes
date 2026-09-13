"""OpenFeature FILE evaluation from one flagd JSON tree (steward 26.4 / AD-11).

No Django import at module top so the steward CLI can evaluate without
loading the host. MCP and views import Django lazily.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from typing import Callable

FLAG_KEY = "pyforge.three_surfaces"
IN_CLUSTER_FLAGS_PATH = Path("/etc/pyforge/flags.json")
LOCAL_DEV_RELATIVE = Path("src/platform/config/flags.json")
ENV_FLAGS_PATH = "PYFORGE_FLAGS_PATH"
ENV_FLAGD_PATH = "FLAGD_OFFLINE_FLAG_SOURCE_PATH"
FLAGS_MCP_STATION = "flags"

_Fetch = Callable[[str, str], bytes]


def local_dev_flags_path(start: Path | None = None) -> Path | None:
    """Walk upward from *start* (or cwd) for the ConfigMap source file."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        path = candidate / LOCAL_DEV_RELATIVE
        if path.is_file():
            return path
    return None


def resolve_flags_path(explicit: Path | str | None = None) -> Path | None:
    if explicit is not None:
        path = Path(explicit)
        return path if path.is_file() else None
    for raw in (os.environ.get(ENV_FLAGS_PATH), os.environ.get(ENV_FLAGD_PATH)):
        if raw:
            path = Path(raw)
            if path.is_file():
                return path
    if IN_CLUSTER_FLAGS_PATH.is_file():
        return IN_CLUSTER_FLAGS_PATH
    return local_dev_flags_path()


def read_flag_tree_bytes(path: Path) -> bytes:
    return path.read_bytes()


def fetch_flag_tree(url: str, token: str, opener: _Fetch | None = None) -> bytes:
    """Authenticated host fetch of the same tree the ConfigMap is built from."""
    if opener is not None:
        return opener(url, token)

    request = urllib.request.Request(  # noqa: S310 -- operator-supplied host URL
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
            return response.read()
    except urllib.error.HTTPError as exc:
        msg = f"host flag fetch refused ({exc.code})"
        raise RuntimeError(msg) from exc


def configure_file_provider(path: Path | str) -> None:
    """In-process FILE resolver. Polls every 5s (unconfigurable in 0.5.0)."""
    from openfeature import api
    from openfeature.contrib.provider.flagd import FlagdProvider
    from openfeature.contrib.provider.flagd.config import ResolverType

    source = str(Path(path))
    os.environ[ENV_FLAGD_PATH] = source
    os.environ.setdefault(ENV_FLAGS_PATH, source)
    api.set_provider(
        FlagdProvider(
            resolver_type=ResolverType.FILE,
            offline_flag_source_path=source,
        ),
    )
    wait_until_ready()


def wait_until_ready(*, key: str = FLAG_KEY, timeout_s: float = 8.0) -> None:
    """FILE init is asynchronous; first reads can be PROVIDER_NOT_READY."""
    import time

    from openfeature import api

    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        last = api.get_client().get_boolean_details(key, False)
        if last.error_code is None:
            return
        time.sleep(0.05)
    msg = f"FILE provider not ready after {timeout_s}s: {last}"
    raise RuntimeError(msg)


def configure_from_env() -> Path | None:
    path = resolve_flags_path()
    if path is None:
        return None
    configure_file_provider(path)
    return path


def evaluate_boolean(key: str = FLAG_KEY, default: bool = False) -> bool:
    from openfeature import api

    return bool(api.get_client().get_boolean_value(key, default))


def evaluate_cutover_root(source: Path | str | None = None) -> str:
    """In-process cutover root — same file the FILE provider serves."""
    from pyforge.core.cutover_root import read_cutover_root

    path = resolve_flags_path(source)
    return read_cutover_root(path)



def materialize_tree_bytes(data: bytes, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def evaluate_from_source(
    *,
    key: str = FLAG_KEY,
    source: Path | str | None = None,
    host: str | None = None,
    token: str | None = None,
    fetch: _Fetch | None = None,
    workdir: Path | None = None,
) -> bool:
    """Evaluate *key* from local-dev file, explicit path, or host fetch.

    Host fetch writes the bytes to a temp file and evaluates that file —
    evaluation itself does not perform I/O to the network.
    """
    if host:
        if not token:
            msg = "host flag fetch requires --token"
            raise RuntimeError(msg)
        payload = fetch_flag_tree(host, token, opener=fetch)
        dest = (workdir or Path.cwd()) / ".pyforge-flags" / "flags.json"
        path = materialize_tree_bytes(payload, dest)
    else:
        path = resolve_flags_path(source)
        if path is None:
            msg = (
                "no flag tree: set PYFORGE_FLAGS_PATH, pass --source, "
                f"or run from a checkout containing {LOCAL_DEV_RELATIVE}"
            )
            raise RuntimeError(msg)
    configure_file_provider(path)
    return evaluate_boolean(key)


def flags_asgi_app() -> Any:
    from mcp.server.mcpserver import MCPServer

    from django_pyforge.mcp_http import asgi_for_server

    server = MCPServer("pyforge-flags")

    @server.tool()
    def get_flag(key: str = FLAG_KEY) -> bool:
        return evaluate_boolean(key)

    return asgi_for_server(server)


def tree_view(request: Any) -> Any:
    from django.http import HttpResponse
    from django.http import HttpResponseForbidden

    if not request.user.is_authenticated:
        return HttpResponseForbidden("authentication required")
    path = resolve_flags_path()
    if path is None:
        return HttpResponse(b"{}", content_type="application/json", status=404)
    return HttpResponse(read_flag_tree_bytes(path), content_type="application/json")


def eval_view(request: Any, key: str) -> Any:
    from django.http import HttpResponseForbidden
    from django.http import JsonResponse

    if not request.user.is_authenticated:
        return HttpResponseForbidden("authentication required")
    return JsonResponse({"key": key, "value": evaluate_boolean(key)})


def run_cli_namespace(ns: argparse.Namespace) -> tuple[bool, str, dict[str, object]]:
    verb = getattr(ns, "flags_verb", None)
    if verb is None:
        return (
            True,
            "flags: get KEY [--source PATH | --host URL --token TOKEN]",
            {},
        )
    try:
        value = evaluate_from_source(
            key=ns.key,
            source=ns.source,
            host=ns.host,
            token=ns.token,
        )
    except RuntimeError as exc:
        return False, str(exc), {}
    payload = {"key": ns.key, "value": value}
    return True, json.dumps(payload, sort_keys=True), payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m django_pyforge.flags")
    parser.add_argument("key", nargs="?", default=FLAG_KEY)
    parser.add_argument("--source", default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--token", default=None)
    ns = parser.parse_args(argv)
    try:
        value = evaluate_from_source(
            key=ns.key,
            source=ns.source,
            host=ns.host,
            token=ns.token,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"key": ns.key, "value": value}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
