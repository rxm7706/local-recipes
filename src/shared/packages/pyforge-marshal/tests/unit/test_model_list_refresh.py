"""Unit tests for model-list refresh (Story 84.1, CAP-285)."""

from __future__ import annotations

import json

import pytest

from pyforge.marshal.adapters.model_list_live import fetch_live_ids_for_profile
from pyforge.marshal.core.harness_profile import HarnessProfile, ModelListSource, load_packaged_profiles, load_profiles
from pyforge.marshal.core.model_list_refresh import (
    DeclaredModelRef,
    HarnessListResult,
    anthropic_models_page_url,
    append_query_params,
    collect_catalog_refs,
    collect_profile_map_refs,
    collect_tier_map_refs,
    diff_harness_ids,
    ensure_no_secret_in_text,
    find_not_listed,
    gemini_models_page_url,
    model_absent_from_live_list,
    parse_anthropic_models_page,
    parse_command_model_lines,
    parse_gemini_models_page,
    parse_snapshot_payload,
    render_report_text,
    SnapshotDiff,
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

    def http_get(self, url, headers, *, timeout_s: float = 60.0) -> HttpGetResult:
        del url, headers, timeout_s
        if self.http_status != 200:
            return HttpGetResult(status_code=self.http_status, body=b"")
        idx = min(self.http_calls, len(self.http_bodies) - 1) if self.http_bodies else 0
        self.http_calls += 1
        body = self.http_bodies[idx] if self.http_bodies else b"{}"
        return HttpGetResult(status_code=200, body=body)


class RecordingFetch(ModelListFetchPort):
    """Records URLs, headers, and pages for HTTP paging tests."""

    def __init__(self, pages: dict[str, bytes], *, status: int = 200) -> None:
        self.pages = pages
        self.status = status
        self.calls: list[tuple[str, dict[str, str]]] = []

    def run_command(self, argv, *, timeout_s: float, fallback_bin_dirs=()) -> CommandRunResult:
        del argv, timeout_s, fallback_bin_dirs
        return CommandRunResult(exit_code=127, stdout="", stderr="not used")

    def http_get(self, url, headers, *, timeout_s: float = 60.0) -> HttpGetResult:
        del timeout_s
        normalized_headers = dict(headers)
        self.calls.append((url, normalized_headers))
        body = self.pages.get(url, b"{}")
        return HttpGetResult(status_code=self.status, body=body)


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
    aliases = frozenset({"sonnet"})
    assert model_absent_from_live_list("sonnet", live, aliases) is False
    assert model_absent_from_live_list("missing-id", live, aliases) is True


def test_mutation_alias_rule_required():
    """Removing alias handling must fail this test (mutation guard)."""
    live = frozenset({"listed-only"})
    aliases = frozenset({"alias-id"})
    # Broken alias logic would report alias-id as absent:
    assert model_absent_from_live_list("alias-id", live, aliases) is False


def test_find_not_listed_respects_aliases():
    declared = (DeclaredModelRef("sonnet", "cursor", "policy.toml", "model_tier_map.heavy.dev"),)
    results = {
        "cursor": HarnessListResult("cursor", "ok", frozenset({"other"})),
    }
    aliases = {"cursor": frozenset({"sonnet"})}
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


def test_query_values_are_url_encoded():
    token = "abc+def/ghi="
    url = gemini_models_page_url("https://example.test/v1beta/models", token)
    assert "pageToken=abc%2Bdef%2Fghi%3D" in url
    url2 = anthropic_models_page_url("https://example.test/v1/models", "id/with+plus")
    assert "after_id=id%2Fwith%2Bplus" in url2


def test_diff_skips_non_comparable_harnesses():
    prev = {"cursor": frozenset({"a"})}
    curr = {"cursor": frozenset()}
    diff = diff_harness_ids(prev, curr, comparable_harnesses=frozenset())
    assert diff == {}


def test_render_report_omits_empty_snapshot_section():
    text = render_report_text(
        not_listed=(),
        harness_results={"cursor": HarnessListResult("cursor", "ok", frozenset({"a"}))},
        unchecked_providers=frozenset(),
        snapshot_diff={"cursor": SnapshotDiff(added=frozenset(), removed=frozenset())},
    )
    assert "since previous snapshot" not in text


def test_fetch_http_anthropic_two_pages():
    base = "https://api.anthropic.com/v1/models"
    page1_url = anthropic_models_page_url(base, None)
    page2_url = anthropic_models_page_url(base, "m1")
    pages = {
        page1_url: json.dumps(
            {"data": [{"id": "m1"}], "has_more": True, "last_id": "m1"},
        ).encode(),
        page2_url: json.dumps({"data": [{"id": "m2"}], "has_more": False}).encode(),
    }
    profile = HarnessProfile(
        name="claude",
        binary="claude",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url=base,
            credential_env="ANTHROPIC_API_KEY",
            credential_header="x-api-key",
            pagination="anthropic",
        ),
    )
    fetch = RecordingFetch(pages)
    result = fetch_live_ids_for_profile(profile, fetch, env={"ANTHROPIC_API_KEY": "sekret"})
    assert result.status == "ok"
    assert result.live_ids == frozenset({"m1", "m2"})
    assert len(fetch.calls) == 2
    assert fetch.calls[0][1]["x-api-key"] == "sekret"
    assert fetch.calls[1][0] == page2_url


def test_fetch_http_non_200_reports_status():
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
    fetch = RecordingFetch({}, status=401)
    result = fetch_live_ids_for_profile(profile, fetch, env={"ANTHROPIC_API_KEY": "x"})
    assert result.status == "unavailable"
    assert result.reason == "HTTP 401"


def test_overlay_inherits_packaged_model_list(tmp_path):
    overlay_dir = tmp_path / "_bmad-output" / "harness-profiles"
    overlay_dir.mkdir(parents=True)
    (overlay_dir / "cursor.toml").write_text(
        'name = "cursor"\n'
        'binary = "cursor-agent"\n'
        'argv = ["-p", "{prompt}"]\n'
        "model_passthrough = true\n",
        encoding="utf-8",
    )
    profiles, errors = load_profiles(tmp_path)
    assert errors == ()
    assert profiles["cursor"].model_list is not None
    assert profiles["cursor"].model_list.command == ("cursor-agent", "models")


def test_ensure_no_secret_in_text():
    with pytest.raises(ValueError, match="credential leaked"):
        ensure_no_secret_in_text("hello sekret world", "sekret")


def test_collect_refs_helpers():
    refs = collect_profile_map_refs(harness="cursor", profile_path="p.toml", model_map={"dev": "m1"})
    assert refs[0].model_id == "m1"
    catalog_refs = collect_catalog_refs(
        catalog={"providers": {"anthropic": {"models": {"a": {}}}}},
        catalog_path="c.toml",
        provider="anthropic",
        harness="claude",
    )
    assert catalog_refs[0].model_id == "a"
    tier_refs = collect_tier_map_refs(
        policy_path="policy.toml",
        tier_map={"easy": {"dev": [{"model": "m", "harness": "cursor"}]}},
        default_harness=None,
    )
    assert tier_refs[0].model_id == "m"


def test_models_cli_drift_exits_zero(monkeypatch, capsys, tmp_path):
    import argparse

    from pyforge.marshal.cli import adapters as adapters_cli

    monkeypatch.setattr(adapters_cli, "repo_root", lambda: tmp_path)
    profiles = {
        "cursor": HarnessProfile(
            name="cursor",
            binary="cursor-agent",
            argv=("{prompt}",),
            model_list=ModelListSource(catalog_provider="cursor", command=("cursor-agent", "models")),
        )
    }
    monkeypatch.setattr(adapters_cli, "load_profiles", lambda root: (profiles, ()))
    monkeypatch.setattr(
        adapters_cli,
        "fetch_live_ids_for_profile",
        lambda profile, fetch, **kw: HarnessListResult("cursor", "ok", frozenset({"listed"})),
    )
    monkeypatch.setattr(
        adapters_cli,
        "_gather_declared_model_refs",
        lambda root, profs: [
            DeclaredModelRef("missing-model", "cursor", "policy.toml", "model_tier_map.easy.dev"),
        ],
    )
    args = argparse.Namespace(slug="pyforge-marshal", format="json", write=False)
    class _MinimalFs:
        def ensure_dir(self, path: object) -> None:
            del path

        def write_text_atomic(self, path: object, text: str) -> None:
            del path, text

    code = adapters_cli.run_adapters_models(args, fs=_MinimalFs())
    out = capsys.readouterr().out
    envelope = json.loads(out)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-MDL-001" in codes
    assert code == 0
    assert "missing-model" in envelope["data"]["report"]
