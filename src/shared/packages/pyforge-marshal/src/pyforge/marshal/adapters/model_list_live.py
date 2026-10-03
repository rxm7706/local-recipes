"""Live model-list fetch adapter (Story 84.1, AD-20)."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError

from ..adapters.harness_bmadbuild import _resolve_binary
from ..adapters.model_list_http import http_get_for_model_list
from ..core.harness_profile import HarnessProfile
from ..core.model_list_refresh import (
    HarnessListResult,
    anthropic_models_page_url,
    gemini_models_page_url,
    parse_anthropic_models_page,
    parse_command_model_lines,
    parse_gemini_models_page,
)
from ..ports.model_list_fetch import CommandRunResult, HttpGetResult, ModelListFetchPort

_DEFAULT_TIMEOUT_S = 60.0
_MAX_HTTP_PAGES = 50


class LiveModelListFetch(ModelListFetchPort):
    def __init__(self, *, repo_root: str | None = None, timeout_s: float = _DEFAULT_TIMEOUT_S) -> None:
        self._repo_root = repo_root
        self._timeout_s = timeout_s
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
        resolved = _resolve_binary(binary, fallback_bin_dirs, root)
        if resolved is None and root is not None:
            resolved = _resolve_binary(binary, (".pixi/envs/pyforge-guild/bin",), root)
        if resolved is None:
            return CommandRunResult(exit_code=127, stdout="", stderr=f"binary not found: {binary!r}")
        effective_timeout = timeout_s if timeout_s > 0 else self._timeout_s
        try:
            result = self._process.run([resolved, *rest], cwd=Path.cwd(), timeout_s=effective_timeout)
        except ProcessError as exc:
            message = str(exc)
            if "timeout" in message.lower():
                return CommandRunResult(exit_code=124, stdout="", stderr="command timed out")
            return CommandRunResult(exit_code=1, stdout="", stderr=message)
        except TimeoutError:
            return CommandRunResult(exit_code=124, stdout="", stderr="command timed out")
        return CommandRunResult(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)

    def http_get(self, url: str, headers: Mapping[str, str], *, timeout_s: float = _DEFAULT_TIMEOUT_S) -> HttpGetResult:
        effective_timeout = timeout_s if timeout_s > 0 else self._timeout_s
        try:
            return http_get_for_model_list(url, headers, timeout_s=effective_timeout)
        except ValueError as exc:
            return HttpGetResult(status_code=0, body=str(exc).encode("utf-8"))


def _build_auth_headers(source, env: Mapping[str, str]) -> tuple[dict[str, str], str | None]:
    headers = dict(source.static_headers)
    secret: str | None = None
    if source.credential_env:
        secret = env.get(source.credential_env, "")
        if not secret:
            return headers, None
        if source.credential_header:
            headers[source.credential_header] = secret
    return headers, secret


def _http_unavailable(harness: str, result: HttpGetResult) -> HarnessListResult:
    if result.status_code == 0:
        detail = result.body.decode("utf-8", errors="replace").strip() or "network error"
        if detail == "timeout":
            reason = "HTTP request timed out"
        else:
            reason = detail
    else:
        reason = "HTTP " + str(result.status_code)
    return HarnessListResult(harness=harness, status="unavailable", live_ids=frozenset(), reason=reason)


def fetch_live_ids_for_profile(
    profile: HarnessProfile,
    fetch: ModelListFetchPort,
    *,
    env: Mapping[str, str] | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> HarnessListResult:
    """Read one harness profile's declared source; never branches on harness name."""
    source = profile.model_list
    harness = profile.name
    if source is None or not source.has_source():
        return HarnessListResult(
            harness=harness, status="unavailable", live_ids=frozenset(), reason="no source declared"
        )

    environment = env if env is not None else os.environ

    if source.command:
        run = fetch.run_command(
            source.command,
            timeout_s=timeout_s,
            fallback_bin_dirs=profile.fallback_bin_dirs,
        )
        if run.exit_code == 127:
            return HarnessListResult(
                harness=harness,
                status="unavailable",
                live_ids=frozenset(),
                reason="binary not found: " + repr(source.command[0]),
            )
        if run.exit_code == 124:
            return HarnessListResult(
                harness=harness,
                status="unavailable",
                live_ids=frozenset(),
                reason="command timed out",
            )
        if run.exit_code != 0:
            detail = (run.stderr or run.stdout).strip() or f"exit {run.exit_code}"
            return HarnessListResult(
                harness=harness,
                status="unavailable",
                live_ids=frozenset(),
                reason="command failed: " + detail,
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
                reason="credential env " + repr(source.credential_env) + " unset",
            )
        ids: set[str] = set()
        if source.pagination == "anthropic":
            after_id: str | None = None
            for _page in range(_MAX_HTTP_PAGES):
                try:
                    url = anthropic_models_page_url(source.url, after_id)
                except ValueError as exc:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason=str(exc),
                    )
                result = fetch.http_get(url, headers, timeout_s=timeout_s)
                if result.status_code != 200:
                    return _http_unavailable(harness, result)
                try:
                    payload = json.loads(result.body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="invalid JSON: " + str(exc),
                    )
                if not isinstance(payload, dict):
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="invalid JSON shape",
                    )
                page_ids, has_more, next_after = parse_anthropic_models_page(payload)
                ids.update(page_ids)
                if not has_more:
                    break
                if not next_after or next_after == after_id:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="pagination cursor did not advance",
                    )
                after_id = next_after
            else:
                return HarnessListResult(
                    harness=harness,
                    status="unavailable",
                    live_ids=frozenset(),
                    reason="pagination exceeded page limit",
                )
        elif source.pagination == "gemini":
            page_token: str | None = None
            for _page in range(_MAX_HTTP_PAGES):
                try:
                    url = gemini_models_page_url(source.url, page_token)
                except ValueError as exc:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason=str(exc),
                    )
                result = fetch.http_get(url, headers, timeout_s=timeout_s)
                if result.status_code != 200:
                    return _http_unavailable(harness, result)
                try:
                    payload = json.loads(result.body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="invalid JSON: " + str(exc),
                    )
                if not isinstance(payload, dict):
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="invalid JSON shape",
                    )
                page_ids, next_token = parse_gemini_models_page(payload)
                ids.update(page_ids)
                if not next_token:
                    break
                if next_token == page_token:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="pagination cursor did not advance",
                    )
                page_token = next_token
            else:
                return HarnessListResult(
                    harness=harness,
                    status="unavailable",
                    live_ids=frozenset(),
                    reason="pagination exceeded page limit",
                )
        else:
            return HarnessListResult(
                harness=harness,
                status="unavailable",
                live_ids=frozenset(),
                reason="HTTP source missing pagination kind",
            )
        return HarnessListResult(harness=harness, status="ok", live_ids=frozenset(ids))

    return HarnessListResult(harness=harness, status="unavailable", live_ids=frozenset(), reason="no source declared")
