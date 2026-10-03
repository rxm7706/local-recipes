"""Live model-list fetch adapter (Story 84.1, AD-20)."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pyforge.core.client import StationClientError, urllib_request
from pyforge.core.process import PosixProcess, ProcessError

from ..core.harness_profile import HarnessProfile, ModelListSource
from ..core.model_list_refresh import (
    HarnessListResult,
    parse_anthropic_models_page,
    parse_command_model_lines,
    parse_gemini_models_page,
)
from ..ports.model_list_fetch import CommandRunResult, HttpGetResult, ModelListFetchPort

_DEFAULT_TIMEOUT_S = 60.0


class LiveModelListFetch(ModelListFetchPort):
    def __init__(self, *, repo_root: str | None = None) -> None:
        from ..adapters.harness_bmadbuild import _resolve_binary

        self._resolve_binary = _resolve_binary
        self._repo_root = repo_root
        self._process = PosixProcess()

    def run_command(
        self,
        argv: Sequence[str],
        *,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        fallback_bin_dirs: Sequence[str] = (),
    ) -> CommandRunResult:
        if not argv:
            return CommandRunResult(exit_code=127, stdout="", stderr="empty argv")
        binary = argv[0]
        rest = list(argv[1:])
        root = Path(self._repo_root) if self._repo_root is not None else None
        resolved = self._resolve_binary(binary, fallback_bin_dirs, root)
        if resolved is None and root is not None:
            resolved = self._resolve_binary(binary, (".pixi/envs/pyforge-guild/bin",), root)
        if resolved is None:
            return CommandRunResult(exit_code=127, stdout="", stderr=f"binary not found: {binary!r}")
        try:
            result = self._process.run([resolved, *rest], cwd=Path.cwd(), timeout_s=timeout_s)
        except ProcessError as exc:
            return CommandRunResult(exit_code=1, stdout="", stderr=str(exc))
        return CommandRunResult(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)

    def http_get(self, url: str, headers: Mapping[str, str], *, timeout_s: float = _DEFAULT_TIMEOUT_S) -> HttpGetResult:
        del timeout_s
        try:
            body = urllib_request("GET", url, dict(headers), None)
        except StationClientError as exc:
            return HttpGetResult(status_code=0, body=str(exc).encode("utf-8"))
        return HttpGetResult(status_code=200, body=body)


def _build_auth_headers(source: ModelListSource, env: Mapping[str, str]) -> tuple[dict[str, str], str | None]:
    headers = dict(source.static_headers)
    secret: str | None = None
    if source.credential_env:
        secret = env.get(source.credential_env, "")
        if not secret:
            return headers, None
        if source.credential_header:
            headers[source.credential_header] = secret
    return headers, secret


def fetch_live_ids_for_profile(
    profile: HarnessProfile,
    fetch: ModelListFetchPort,
    *,
    env: Mapping[str, str] | None = None,
) -> HarnessListResult:
    """Read one harness profile's declared source; never branches on harness name."""
    source = profile.model_list
    harness = profile.name
    if source is None or not source.has_source():
        return HarnessListResult(harness=harness, status="unavailable", live_ids=frozenset(), reason="no source declared")

    environment = env if env is not None else os.environ

    if source.command:
        run = fetch.run_command(
            source.command,
            timeout_s=_DEFAULT_TIMEOUT_S,
            fallback_bin_dirs=profile.fallback_bin_dirs,
        )
        if run.exit_code != 0:
            detail = (run.stderr or run.stdout).strip() or f"exit {run.exit_code}"
            return HarnessListResult(
                harness=harness,
                status="unavailable",
                live_ids=frozenset(),
                reason=f"command failed: {detail}",
            )
        return HarnessListResult(
            harness=harness,
            status="ok",
            live_ids=parse_command_model_lines(run.stdout),
        )

    if source.url:
        headers, secret = _build_auth_headers(source, environment)
        if source.credential_env and secret is None:
            return HarnessListResult(
                harness=harness,
                status="unavailable",
                live_ids=frozenset(),
                reason=f"credential env {source.credential_env!r} unset",
            )
        ids: set[str] = set()
        if source.pagination == "anthropic":
            after_id: str | None = None
            while True:
                url = _anthropic_page_url(source.url, after_id)
                result = fetch.http_get(url, headers)
                if result.status_code != 200:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason=f"HTTP {result.status_code}",
                    )
                try:
                    payload = json.loads(result.body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason=f"invalid JSON: {exc}",
                    )
                if not isinstance(payload, dict):
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="invalid JSON shape",
                    )
                page_ids, has_more, after_id = parse_anthropic_models_page(payload)
                ids.update(page_ids)
                if not has_more:
                    break
                if not after_id:
                    break
        elif source.pagination == "gemini":
            page_token: str | None = None
            while True:
                url = _gemini_page_url(source.url, page_token)
                result = fetch.http_get(url, headers)
                if result.status_code != 200:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason=f"HTTP {result.status_code}",
                    )
                try:
                    payload = json.loads(result.body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason=f"invalid JSON: {exc}",
                    )
                if not isinstance(payload, dict):
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="invalid JSON shape",
                    )
                page_ids, page_token = parse_gemini_models_page(payload)
                ids.update(page_ids)
                if not page_token:
                    break
        else:
            return HarnessListResult(
                harness=harness,
                status="unavailable",
                live_ids=frozenset(),
                reason="HTTP source missing pagination kind",
            )
        return HarnessListResult(harness=harness, status="ok", live_ids=frozenset(ids))

    return HarnessListResult(harness=harness, status="unavailable", live_ids=frozenset(), reason="no source declared")


def _anthropic_page_url(base: str, after_id: str | None) -> str:
    parsed = urlparse(base)
    query = dict(parse_qsl(parsed.query))
    query.setdefault("limit", "1000")
    if after_id:
        query["after_id"] = after_id
    return urlunparse(parsed._replace(query=urlencode(query)))


def _gemini_page_url(base: str, page_token: str | None) -> str:
    parsed = urlparse(base)
    query = dict(parse_qsl(parsed.query))
    query.setdefault("pageSize", "1000")
    if page_token:
        query["pageToken"] = page_token
    return urlunparse(parsed._replace(query=urlencode(query)))
