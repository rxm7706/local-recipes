"""Unit tests for model-list refresh (Story 84.1, CAP-285)."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.model_list_live import fetch_live_ids_for_profile
from pyforge.marshal.cli import adapters as adapters_cli
from pyforge.marshal.core.harness_profile import HarnessProfile, ModelListSource, load_packaged_profiles, load_profiles
from pyforge.marshal.core.model_list_refresh import (
    DeclaredModelRef,
    HarnessListResult,
    LastOkBlock,
    SnapshotDiff,
    accumulate_last_ok_ids,
    anthropic_models_page_url,
    build_snapshot_payload,
    collect_catalog_refs,
    collect_profile_map_refs,
    collect_tier_map_refs,
    diff_harness_ids,
    ensure_no_secret_in_text,
    find_not_listed,
    gemini_models_page_url,
    last_ok_blocks,
    merge_snapshot_blocks_for_write,
    model_absent_from_live_list,
    parse_anthropic_models_page,
    parse_command_model_lines,
    parse_gemini_models_page,
    parse_snapshot_payload,
    render_report_text,
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


_SNAPSHOT_DIR = Path("_bmad-output/projects/pyforge-marshal/planning-artifacts/model-lists")
_TEST_KEY_ENV = "MODEL_LIST_TEST_KEY_84_2"


def _cursor_profile() -> HarnessProfile:
    return HarnessProfile(
        name="cursor",
        binary="cursor-agent",
        argv=("{prompt}",),
        model_list=ModelListSource(catalog_provider="cursor", command=("cursor-agent", "models")),
    )


def _http_profile(name: str, url: str, credential_env: str) -> HarnessProfile:
    return HarnessProfile(
        name=name,
        binary=name,
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url=url,
            credential_env=credential_env,
            credential_header="x-api-key",
            pagination="anthropic",
        ),
    )


def _run_models_cli(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    profiles: dict[str, HarnessProfile],
    *,
    fetch: ModelListFetchPort | None,
    fmt: str = "json",
    write: bool = False,
    overlay_errors: tuple[str, ...] = (),
) -> int:
    """``run_adapters_models`` against ``root`` with the fetch port injected
    (the handler parameter, Story 84.2) and a real filesystem."""
    monkeypatch.setattr(adapters_cli, "repo_root", lambda: root)
    monkeypatch.setattr(adapters_cli, "load_profiles", lambda _root: (profiles, overlay_errors))
    args = argparse.Namespace(slug="pyforge-marshal", format=fmt, write=write)
    return adapters_cli.run_adapters_models(args, fs=LocalFs(), fetch=fetch)


def _write_snapshot(root: Path, day: date, harnesses: dict[str, dict[str, object]]) -> None:
    snap_dir = root / _SNAPSHOT_DIR
    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / f"model-list-{day.isoformat()}.json").write_text(
        json.dumps({"date": day.isoformat(), "harnesses": harnesses}), encoding="utf-8"
    )


def _read_snapshot(root: Path, day: date) -> dict[str, object]:
    return json.loads((root / _SNAPSHOT_DIR / f"model-list-{day.isoformat()}.json").read_text(encoding="utf-8"))


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


def test_parse_command_skips_error_auth_line():
    text = "Error - not authenticated\nreal-id - Real Model\n"
    assert parse_command_model_lines(text) == frozenset({"real-id"})


@pytest.mark.parametrize(
    "line",
    [
        "Warning - model list may be stale",
        "WARNING - rate limited",
        "Error - not authenticated",
        "Note - some models are hidden",
        "Tip - run cursor-agent login to see more",
        "warning - lowercase diagnostic",
        "error - lowercase diagnostic",
        "info - lowercase diagnostic",
        "Available - Models",
    ],
)
def test_parse_command_never_reads_a_diagnostic_line_as_an_id(line):
    """Story 84.2: a ``Warning ...`` / ``Error ...`` line is never an id."""
    text = f"{line}\nauto - Auto\ngrok-4.7-high - Grok 4.7 High\nsonnet-4.5-thinking - Sonnet 4.5 Thinking\n"
    assert parse_command_model_lines(text) == frozenset({"auto", "grok-4.7-high", "sonnet-4.5-thinking"})


def test_merge_snapshot_write_keeps_same_day_ok():
    ids, status, carried = merge_snapshot_blocks_for_write(
        harness_ids={"claude": frozenset()},
        harness_status={"claude": "unavailable"},
        same_day_existing={"claude": {"status": "ok", "ids": ["a", "b"]}},
        last_ok={"claude": LastOkBlock(read_on=date(2026, 1, 1), ids=frozenset({"old"}))},
    )
    assert status["claude"] == "ok"
    assert ids["claude"] == frozenset({"a", "b"})
    assert carried == {}


def test_merge_snapshot_write_new_day_carries_with_date_never_as_ok():
    """Story 84.2: an earlier day's ok ids are recorded with their date; the
    harness stays unavailable today."""
    earlier = LastOkBlock(read_on=date(2026, 1, 1), ids=frozenset({"a", "b"}))
    ids, status, carried = merge_snapshot_blocks_for_write(
        harness_ids={"claude": frozenset(), "cursor": frozenset({"c"})},
        harness_status={"claude": "unavailable", "cursor": "ok"},
        same_day_existing={"claude": {"status": "unavailable", "ids": []}},
        last_ok={"claude": earlier, "cursor": LastOkBlock(read_on=date(2026, 1, 1), ids=frozenset({"x"}))},
    )
    assert status == {"claude": "unavailable", "cursor": "ok"}
    assert ids == {"claude": frozenset(), "cursor": frozenset({"c"})}
    assert carried == {"claude": earlier}
    payload = build_snapshot_payload(
        snapshot_date="2026-01-03", harness_ids=ids, harness_status=status, carried=carried
    )
    harnesses = payload["harnesses"]
    assert isinstance(harnesses, dict)
    assert harnesses["claude"] == {
        "status": "unavailable",
        "ids": [],
        "last_ok": {"date": "2026-01-01", "ids": ["a", "b"]},
    }
    assert harnesses["cursor"] == {"status": "ok", "ids": ["c"]}


def test_last_ok_blocks_keep_the_day_of_the_newest_ok_read():
    history = [
        (date(2026, 1, 1), {"cursor": frozenset({"a"})}, {"cursor": "ok"}),
        (date(2026, 1, 2), {"cursor": frozenset({"a", "b"})}, {"cursor": "ok"}),
        (date(2026, 1, 3), {"cursor": frozenset()}, {"cursor": "unavailable"}),
    ]
    assert last_ok_blocks(history) == {"cursor": LastOkBlock(read_on=date(2026, 1, 2), ids=frozenset({"a", "b"}))}


def test_accumulate_last_ok_skips_unavailable_day():
    from datetime import date

    history = [
        (
            date(2026, 1, 1),
            {"cursor": frozenset({"a", "b"})},
            {"cursor": "ok"},
        ),
        (
            date(2026, 1, 2),
            {"cursor": frozenset()},
            {"cursor": "unavailable"},
        ),
    ]
    assert accumulate_last_ok_ids(history)["cursor"] == frozenset({"a", "b"})


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
    day, ids, status = parse_snapshot_payload(payload)
    assert day == "2026-10-02"
    assert ids["cursor"] == frozenset({"a", "b"})
    assert status["cursor"] == "ok"


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
        'name = "cursor"\nbinary = "cursor-agent"\nargv = ["-p", "{prompt}"]\nmodel_passthrough = true\n',
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
    policy = tmp_path / "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        'harness_preference = ["cursor"]\n[model_tier_map.easy]\ndev = [{ model = "missing-model", harness = "cursor" }]\n',
        encoding="utf-8",
    )
    code = _run_models_cli(
        monkeypatch,
        tmp_path,
        {"cursor": _cursor_profile()},
        fetch=FakeFetch(command_output="listed - Listed\n"),
    )
    envelope = json.loads(capsys.readouterr().out)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-MDL-001" in codes
    assert code == 0
    assert (
        "missing-model (cursor) declared in _bmad-output/projects/pyforge-marshal/planning-artifacts/"
        "marshal-policy.toml key model_tier_map.easy.dev"
    ) in envelope["data"]["report"]


def test_fetch_command_empty_output_unavailable():
    profile = HarnessProfile(
        name="cursor",
        binary="cursor-agent",
        argv=("{prompt}",),
        model_list=ModelListSource(catalog_provider="cursor", command=("cursor-agent", "models")),
    )
    fetch = FakeFetch(command_output="no parseable lines\n")
    result = fetch_live_ids_for_profile(profile, fetch)
    assert result.status == "unavailable"
    assert result.reason == "no ids parsed"


def test_fetch_http_gemini_two_pages():
    base = "https://generativelanguage.googleapis.com/v1beta/models"
    page1_url = gemini_models_page_url(base, None)
    page2_url = gemini_models_page_url(base, "tok1")
    pages = {
        page1_url: json.dumps(
            {
                "models": [
                    {"name": "models/gemini-a", "supportedGenerationMethods": ["generateContent"]},
                ],
                "nextPageToken": "tok1",
            },
        ).encode(),
        page2_url: json.dumps(
            {
                "models": [
                    {"name": "models/gemini-b", "supportedGenerationMethods": ["generateContent"]},
                ],
            },
        ).encode(),
    }
    profile = HarnessProfile(
        name="gemini",
        binary="gemini",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="google",
            url=base,
            credential_env="GEMINI_API_KEY",
            credential_header="x-goog-api-key",
            pagination="gemini",
        ),
    )
    fetch = RecordingFetch(pages)
    result = fetch_live_ids_for_profile(profile, fetch, env={"GEMINI_API_KEY": "g-secret"})
    assert result.status == "ok"
    assert result.live_ids == frozenset({"gemini-a", "gemini-b"})
    assert len(fetch.calls) == 2
    assert fetch.calls[0][1]["x-goog-api-key"] == "g-secret"
    assert fetch.calls[1][0] == page2_url


def test_fetch_credential_with_cr_unavailable():
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
    bad_key = "secret\r"
    result = fetch_live_ids_for_profile(profile, fetch, env={"ANTHROPIC_API_KEY": bad_key})
    assert result.status == "unavailable"
    assert "invalid characters" in (result.reason or "")


def test_render_report_no_drift_when_all_unavailable():
    text = render_report_text(
        not_listed=(),
        harness_results={
            "claude": HarnessListResult("claude", "unavailable", frozenset(), "unset"),
            "copilot": HarnessListResult("copilot", "unavailable", frozenset(), "no source"),
        },
        unchecked_providers=frozenset(),
        snapshot_diff=None,
    )
    assert "no drift detected" not in text
    assert "0 harness(es) compared" in text


def test_models_cli_write_snapshot(monkeypatch, tmp_path):
    code = _run_models_cli(
        monkeypatch,
        tmp_path,
        {"cursor": _cursor_profile()},
        fetch=FakeFetch(command_output="m1 - One\n"),
        fmt="text",
        write=True,
    )
    assert code == 0
    payload = _read_snapshot(tmp_path, date.today())
    assert payload["harnesses"] == {"cursor": {"status": "ok", "ids": ["m1"]}}


def test_models_cli_prior_snapshot_diff(monkeypatch, tmp_path, capsys):
    _write_snapshot(tmp_path, date(2026, 1, 1), {"cursor": {"status": "ok", "ids": ["a"]}})
    code = _run_models_cli(
        monkeypatch,
        tmp_path,
        {"cursor": _cursor_profile()},
        fetch=FakeFetch(command_output="a - A\nb - B\n"),
        fmt="text",
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "since previous snapshot:\n  [cursor]\n    + b" in out


def test_models_cli_write_preserves_ok_when_rerun_unavailable(monkeypatch, tmp_path):
    """A same-day re-run keeps that day's earlier live ok block."""
    today = date.today()
    _write_snapshot(tmp_path, today, {"claude": {"status": "ok", "ids": ["m1", "m2"]}})
    monkeypatch.delenv(_TEST_KEY_ENV, raising=False)
    profile = _http_profile("claude", "https://models.invalid/v1/models", _TEST_KEY_ENV)
    code = _run_models_cli(monkeypatch, tmp_path, {"claude": profile}, fetch=FakeFetch(), fmt="text", write=True)
    assert code == 0
    payload = _read_snapshot(tmp_path, today)
    assert payload["harnesses"] == {"claude": {"status": "ok", "ids": ["m1", "m2"]}}


def test_models_cli_write_new_day_unavailable_records_last_ok_with_its_date(monkeypatch, tmp_path):
    """Story 84.2: on a new day an unavailable harness is written unavailable,
    its last ok ids recorded under ``last_ok`` with the day they were read --
    never as today's live read."""
    today = date.today()
    earlier = today - timedelta(days=2)
    _write_snapshot(tmp_path, earlier, {"claude": {"status": "ok", "ids": ["m1", "m2"]}})
    monkeypatch.delenv(_TEST_KEY_ENV, raising=False)
    profile = _http_profile("claude", "https://models.invalid/v1/models", _TEST_KEY_ENV)
    code = _run_models_cli(
        monkeypatch,
        tmp_path,
        {"claude": profile, "cursor": _cursor_profile()},
        fetch=FakeFetch(command_output="c1 - C1\n"),
        fmt="text",
        write=True,
    )
    assert code == 0
    payload = _read_snapshot(tmp_path, today)
    assert payload["date"] == today.isoformat()
    assert payload["harnesses"] == {
        "claude": {"status": "unavailable", "ids": [], "last_ok": {"date": earlier.isoformat(), "ids": ["m1", "m2"]}},
        "cursor": {"status": "ok", "ids": ["c1"]},
    }


def test_models_cli_diff_uses_last_ok_not_unavailable_day(monkeypatch, tmp_path, capsys):
    _write_snapshot(tmp_path, date(2026, 1, 1), {"cursor": {"status": "ok", "ids": ["a", "b"]}})
    _write_snapshot(tmp_path, date(2026, 1, 2), {"cursor": {"status": "unavailable", "ids": []}})
    code = _run_models_cli(
        monkeypatch,
        tmp_path,
        {"cursor": _cursor_profile()},
        fetch=FakeFetch(command_output="a - A\n"),
        fmt="text",
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "since previous snapshot:\n  [cursor]\n    - b" in out


def test_models_cli_all_unavailable_warn_findings(monkeypatch, capsys, tmp_path):
    profiles = {"copilot": HarnessProfile(name="copilot", binary="copilot", argv=("{prompt}",))}
    code = _run_models_cli(monkeypatch, tmp_path, profiles, fetch=FakeFetch())
    envelope = json.loads(capsys.readouterr().out)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-MDL-002" in codes
    assert code == 0
    assert envelope["data"]["harness_results"]["copilot"] == {
        "status": "unavailable",
        "count": 0,
        "reason": "no source declared",
    }
    assert "no drift detected" not in envelope["data"]["report"]


_PACKAGED_GEMINI = "src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/gemini.toml"
_OVERLAY_GEMINI = "_bmad-output/harness-profiles/gemini.toml"


def _model_map_sources(monkeypatch, capsys, root: Path) -> dict[str, set[str]]:
    """Run the CLI on ``root`` with its real overlay loading; return each
    not-listed gemini ``model_map`` id -> the files the report names for it."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "SENTINEL-NOT-A-REAL-KEY")
    page = json.dumps(
        {"models": [{"name": "models/unrelated", "supportedGenerationMethods": ["generateContent"]}]}
    ).encode()
    monkeypatch.setattr(adapters_cli, "repo_root", lambda: root)
    args = argparse.Namespace(slug="pyforge-marshal", format="json", write=False)
    code = adapters_cli.run_adapters_models(args, fs=LocalFs(), fetch=FakeFetch(http_bodies=[page]))
    assert code == 0
    envelope = json.loads(capsys.readouterr().out)
    sources: dict[str, set[str]] = {}
    for finding in envelope["findings"]:
        message = finding["message"]
        if finding["code"] == "MRS-MDL-001" and "'gemini'" in message and "key model_map." in message:
            model_id = message.split("'")[1]
            sources.setdefault(model_id, set()).add(message.split("declared in ")[1].split(" key ")[0])
    return sources


def test_model_map_refs_name_the_packaged_profile_when_the_overlay_was_rejected(monkeypatch, capsys, tmp_path):
    """Story 84.2: an overlay file that failed to load never gets credit for the map in force."""
    overlay = tmp_path / _OVERLAY_GEMINI
    overlay.parent.mkdir(parents=True)
    overlay.write_text('name = "gemini"\nbinary = \n', encoding="utf-8")
    sources = _model_map_sources(monkeypatch, capsys, tmp_path)
    assert sources == {"gemini-3-pro-preview": {_PACKAGED_GEMINI}, "gemini-3-flash-preview": {_PACKAGED_GEMINI}}


def test_model_map_refs_name_the_overlay_when_it_loaded(monkeypatch, capsys, tmp_path):
    packaged = (Path(adapters_cli.__file__).parent.parent / "data/harness_profiles/gemini.toml").read_text(
        encoding="utf-8"
    )
    assert 'haiku = "gemini-3-flash-preview"' in packaged
    overlay = tmp_path / _OVERLAY_GEMINI
    overlay.parent.mkdir(parents=True)
    overlay.write_text(
        packaged.replace('haiku = "gemini-3-flash-preview"', 'haiku = "overlay-flash"'), encoding="utf-8"
    )
    sources = _model_map_sources(monkeypatch, capsys, tmp_path)
    assert sources == {"gemini-3-pro-preview": {_OVERLAY_GEMINI}, "overlay-flash": {_OVERLAY_GEMINI}}
