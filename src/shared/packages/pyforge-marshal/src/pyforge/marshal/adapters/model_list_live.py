"""Live model-list fetch adapter (Story 84.1, AD-20)."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError

from ..adapters.harness_bmadbuild import _resolve_binary
from ..adapters.oidc_pkce import PkceLoginError, http_get_bytes
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


class LiveModelListFetch(ModelListFetchPort):
    def __init__(self, *, repo_root: str | None = None) -> None:
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
        resolved = _resolve_binary(binary, fallback_bin_dirs, root)
        if resolved is None and root is not None:
            resolved = _resolve_binary(binary, (".pixi/envs/pyforge-guild/bin",), root)
        if resolved is None:
            return CommandRunResult(exit_code=127, stdout="", stderr=f"binary not found: {binary!r}")
        try:
            result = self._process.run([resolved, *rest], cwd=Path.cwd(), timeout_s=timeout_s)
        except ProcessError as exc:
            return CommandRunResult(exit_code=1, stdout="", stderr=str(exc))
        return CommandRunResult(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)

    def http_get(self, url: str, headers: Mapping[str, str], *, timeout_s: float) -> HttpGetResult:
        del timeout_s
        try:
            body = http_get_bytes(url, headers)
        except PkceLoginError as exc:
            return HttpGetResult(status_code=0, body=str(exc).encode("utf-8"))
        return HttpGetResult(status_code=200, body=body)


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
            while True:
                url = anthropic_models_page_url(source.url, after_id)
                result = fetch.http_get(url, headers, timeout_s=_DEFAULT_TIMEOUT_S)
                if result.status_code != 200:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="HTTP " + str(result.status_code),
                    )
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
                page_ids, has_more, after_id = parse_anthropic_models_page(payload)
                ids.update(page_ids)
                if not has_more:
                    break
                if not after_id:
                    break
        elif source.pagination == "gemini":
            page_token: str | None = None
            while True:
                url = gemini_models_page_url(source.url, page_token)
                result = fetch.http_get(url, headers, timeout_s=_DEFAULT_TIMEOUT_S)
                if result.status_code != 200:
                    return HarnessListResult(
                        harness=harness,
                        status="unavailable",
                        live_ids=frozenset(),
                        reason="HTTP " + str(result.status_code),
                    )
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
