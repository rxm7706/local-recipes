"""Unit tests for model-list refresh (Story 84.1, CAP-285)."""

from __future__ import annotations

import json

import pytest

from pyforge.marshal.adapters.model_list_live import fetch_live_ids_for_profile
from pyforge.marshal.core.harness_profile import HarnessProfile, ModelListSource, load_packaged_profiles
from pyforge.marshal.core.model_list_refresh import (
    find_not_listed,
    model_absent_from_live_list,
    parse_anthropic_models_page,
    parse_command_model_lines,
    parse_gemini_models_page,
    parse_snapshot_payload,
    DeclaredModelRef,
    HarnessListResult,
    diff_harness_ids,
    unchecked_catalog_providers,
)
from pyforge.marshal.ports.model_list_fetch import CommandRunResult, HttpGetResult, ModelListFetchPort


class FakeFetch(ModelListFetchPort):
    def __init__(
        self,
        *,
        command_output: str = "",
        command_exit: int = 0,
        http_bodies: list[bytes] | None = None,
        http_status: int = 200,
    ) -> None:
        self.command_output = command_output
        self.command_exit = command_exit
        self.http_bodies = list(http_bodies or [])
        self.http_status = http_status
        self.http_calls = 0

    def run_command(self, argv, *, timeout_s: float, fallback_bin_dirs=()) -> CommandRunResult:
        del argv, timeout_s, fallback_bin_dirs
        return CommandRunResult(
            exit_code=self.command_exit,
            stdout=self.command_output,
            stderr="" if self.command_exit == 0 else "fail",
        )

    def http_get(self, url, headers, *, timeout_s: float) -> HttpGetResult:
        del url, headers, timeout_s
        if self.http_status != 200:
            return HttpGetResult(status_code=self.http_status, body=b"")
        idx = min(self.http_calls, len(self.http_bodies) - 1) if self.http_bodies else 0
        self.http_calls += 1
        body = self.http_bodies[idx] if self.http_bodies else b"{}"
        return HttpGetResult(status_code=200, body=body)


def test_parse_command_model_lines():
    text = "composer-2.5-fast - Composer 2.5\n\nsonnet-4 - Sonnet\nnoise"
    assert parse_command_model_lines(text) == frozenset({"composer-2.5-fast", "sonnet-4"})


def test_parse_anthropic_paging():
    page1 = {
        "data": [{"id": "claude-sonnet-4-20250514"}, {"id": "claude-opus-4-20250514"}],
        "has_more": True,
        "last_id": "claude-opus-4-20250514",
    }
    ids, has_more, after = parse_anthropic_models_page(page1)
    assert ids == frozenset({"claude-sonnet-4-20250514", "claude-opus-4-20250514"})
    assert has_more is True
    assert after == "claude-opus-4-20250514"


def test_parse_gemini_generate_content_filter():
    payload = {
        "models": [
            {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/embedding-only", "supportedGenerationMethods": ["embedContent"]},
        ],
        "nextPageToken": "",
    }
    ids, token = parse_gemini_models_page(payload)
    assert ids == frozenset({"gemini-2.0-flash"})
    assert token is None


def test_alias_rule_absent_from_list():
    live = frozenset({"a", "b"})
    aliases = frozenset({"grok-4.6"})
    assert model_absent_from_live_list("grok-4.6", live, aliases) is False
    assert model_absent_from_live_list("missing-id", live, aliases) is True


def test_mutation_alias_rule_required():
    """Removing alias handling must fail this test (mutation guard)."""
    live = frozenset({"listed-only"})
    aliases = frozenset({"alias-id"})
    # Broken alias logic would report alias-id as absent:
    assert model_absent_from_live_list("alias-id", live, aliases) is False


def test_find_not_listed_respects_aliases():
    declared = (
        DeclaredModelRef("grok-4.6", "cursor", "policy.toml", "model_tier_map.heavy.dev"),
    )
    results = {
        "cursor": HarnessListResult("cursor", "ok", frozenset({"other"})),
    }
    aliases = {"cursor": frozenset({"grok-4.6"})}
    assert find_not_listed(declared, results, aliases) == ()


def test_unchecked_catalog_provider():
    catalog = {"providers": {"anthropic": {"models": {"x": {}}}, "openai": {"models": {"y": {}}}}}
    named = frozenset({"anthropic"})
    assert unchecked_catalog_providers(catalog, named) == frozenset({"openai"})


def test_snapshot_diff():
    prev = {"cursor": frozenset({"a", "b"})}
    curr = {"cursor": frozenset({"b", "c"})}
    diff = diff_harness_ids(prev, curr)
    assert diff["cursor"].added == frozenset({"c"})
    assert diff["cursor"].removed == frozenset({"a"})


def test_fetch_command_source():
    profile = HarnessProfile(
        name="cursor",
        binary="cursor-agent",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="cursor",
            command=("cursor-agent", "models"),
        ),
    )
    fetch = FakeFetch(command_output="m1 - One\nm2 - Two\n")
    result = fetch_live_ids_for_profile(profile, fetch)
    assert result.status == "ok"
    assert result.live_ids == frozenset({"m1", "m2"})


def test_fetch_http_anthropic_requires_credential():
    profile = HarnessProfile(
        name="claude",
        binary="claude",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url="https://api.anthropic.com/v1/models",
            credential_env="ANTHROPIC_API_KEY",
            credential_header="x-api-key",
            pagination="anthropic",
        ),
    )
    fetch = FakeFetch()
    result = fetch_live_ids_for_profile(profile, fetch, env={})
    assert result.status == "unavailable"
    assert "unset" in (result.reason or "")


def test_fetch_http_anthropic_pages():
    page = json.dumps(
        {"data": [{"id": "claude-3"}], "has_more": False},
    ).encode()
    profile = HarnessProfile(
        name="claude",
        binary="claude",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url="https://api.anthropic.com/v1/models",
            credential_env="ANTHROPIC_API_KEY",
            credential_header="x-api-key",
            pagination="anthropic",
        ),
    )
    fetch = FakeFetch(http_bodies=[page])
    result = fetch_live_ids_for_profile(profile, fetch, env={"ANTHROPIC_API_KEY": "secret"})
    assert result.status == "ok"
    assert "claude-3" in result.live_ids


def test_fetch_no_source_unavailable():
    profile = HarnessProfile(name="copilot", binary="copilot", argv=("{prompt}",))
    fetch = FakeFetch()
    result = fetch_live_ids_for_profile(profile, fetch)
    assert result.status == "unavailable"


def test_packaged_profiles_parse_model_list():
    profiles = load_packaged_profiles()
    assert profiles["cursor"].model_list is not None
    assert profiles["claude"].model_list is not None
    assert profiles["gemini"].model_list is not None
    assert profiles["copilot"].model_list is None


def test_snapshot_roundtrip():
    payload = {
        "date": "2026-10-02",
        "harnesses": {"cursor": {"status": "ok", "ids": ["a", "b"]}},
    }
    day, ids = parse_snapshot_payload(payload)
    assert day == "2026-10-02"
    assert ids["cursor"] == frozenset({"a", "b"})
