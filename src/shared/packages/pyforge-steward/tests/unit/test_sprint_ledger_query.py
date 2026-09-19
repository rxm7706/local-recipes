"""Unit tests for the Sprint Ledger Query Module (`pyforge-steward`, Story 65.1).

Every test parses FIXTURE ledgers/epics under `tmp_path`, except the one
agreement test at the bottom that holds the engine to
`scripts/fleet_scan.py::parse_sprint_status` over the live tree (CAP-1 success).
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, build_parser, main
from pyforge.steward.sprint_ledger_query import (
    FLAG_DOSSIER_EXPORT,
    FLAG_HERALD_FACTS,
    FLAG_JIRA_GITHUB_MATRIX,
    FLAG_POSTGRES_SYNC,
    FLAG_VIZRO_DATASET,
    FORMATTER_FLAGS,
    KNOWN_STATUSES,
    SCHEMA_PATH,
    SCHEMA_URN,
    FormatterRegistry,
    LedgerQueryDuty,
    LedgerQueryHook,
    LedgerSourcePlugin,
    QueryFormatterPlugin,
    SprintLedgerQueryEngine,
    StationLedger,
    SummaryFormatter,
    canonical_story_key,
    default_formatter_names,
    eval_flag,
    get_runnable_backlog,
    parse_deps_text,
    parse_flag_overrides,
    sync_to_postgres,
)

_EPICS_MD = """# Epics

## Epic List

### Epic 1: Listed twice on purpose

## Epic 1: Test Epic

### Story 1.1: Story One
**FR/AD:** FR-1 • **Effort:** S • **Deps:** —
**Status:** done

### Story 1.2: Story Two
**FR/AD:** FR-2 • **Effort:** M • **Deps:** S-1.1
JIRA-ABC-12 GH-77

### Story 1.3: Story Three
**FR/AD:** FR-3 • **Effort:** M • **Deps:** steward S-1.1 (note), 1.2

### Story 1.4: Story Four
**Effort:** L • **Deps:** none

### Story 1.5: Story Five
**Effort:** S • **Deps:** 9.9

## Epic 2: Second Epic

### Story 2.1: Not Done Yet
**Deps:** n/a

### Story 2.2: Review Me
**Deps:** —

### Story 2.3: Odd One
**Deps:** —

## Deferred Work

**Deps:** 1.1
**Status:** done
"""

_LEDGER_YAML = """development_status:
  1-1-story-one: done
  1-2-story-two: backlog
  1-3-story-three: backlog
  1-4-story-four: backlog
  1-5-story-five: backlog
  2-1-not-done-yet: in-progress
  2-2-review-me: in-review
  2-3-odd-one: something-new
  epic-1: done
  epic-2: in-progress
"""


def _make_station(root: Path, station: str, epics_md: str = _EPICS_MD, ledger: str | None = _LEDGER_YAML) -> Path:
    st_dir = root / "_bmad-output" / "projects" / station / "planning-artifacts"
    st_dir.mkdir(parents=True)
    (st_dir / "epics.md").write_text(epics_md, encoding="utf-8")
    if ledger is not None:
        (st_dir / "sprint-status-ledger.yaml").write_text(ledger, encoding="utf-8")
    return st_dir


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    _make_station(tmp_path, "test-station")
    return tmp_path


@pytest.fixture
def engine(fixture_root: Path) -> SprintLedgerQueryEngine:
    return SprintLedgerQueryEngine(root_dir=fixture_root, flags_file_path=fixture_root / "no-flags.json")


def _ns(**overrides):
    base = dict(
        duty="ledger-query", unimplemented=False, unlinked=False, station=None, status=None,
        search=None, epic=None, format="summary", output=None, sync_postgres=False, flag=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def duty_engine(fixture_root: Path, monkeypatch: pytest.MonkeyPatch):
    """`LedgerQueryDuty` builds its own engine; point it at the fixture tree."""
    import pyforge.steward.sprint_ledger_query as mod

    real = mod.SprintLedgerQueryEngine

    def _factory(root_dir=None, flags_file_path=None):
        return real(root_dir=fixture_root, flags_file_path=fixture_root / "no-flags.json")

    monkeypatch.setattr(mod, "SprintLedgerQueryEngine", _factory)
    return fixture_root


# --- A1: dependency grammar + runnable backlog ---

def test_deps_grammar_matches_marshal_spec_deps() -> None:
    assert parse_deps_text("S-46.4") == ["46.4"]
    assert parse_deps_text("steward S-32.1 (note)") == ["32.1"]
    assert parse_deps_text("46.4") == ["46.4"]
    assert parse_deps_text("S-20.1, S-20.2") == ["20.1", "20.2"]
    assert parse_deps_text("28.*") == []
    assert parse_deps_text("06.02A") == ["6.2a"]
    for sentinel in ("—", "–", "-", "none", "nothing", "n/a", "N/A", ""):
        assert parse_deps_text(sentinel) == [], sentinel
    assert canonical_story_key("01.02a") == "1.2a"


def test_engine_query_parses_all_four_dep_shapes_and_runnable_set(engine: SprintLedgerQueryEngine) -> None:
    res = engine.query(station="test-station")
    by_id = {s.story_id: s for s in res.stories}
    assert by_id["1.1"].deps == []
    assert by_id["1.2"].deps == ["1.1"]
    assert by_id["1.3"].deps == ["1.1", "1.2"]
    assert by_id["1.4"].deps == []
    assert by_id["1.5"].deps == ["9.9"]

    runnable = {s.story_id for s in get_runnable_backlog(engine, station="test-station")}
    # 1.2 (dep done) and 1.4 (no deps) run; 1.3 waits on 1.2; 1.5 waits on a
    # story that does not exist; 2.x are not backlog.
    assert runnable == {"1.2", "1.4"}


def test_runnable_backlog_keys_done_by_station(tmp_path: Path) -> None:
    other_epics = "## Epic 1: Other\n\n### Story 1.1: Done Elsewhere\n**Deps:** —\n"
    _make_station(tmp_path, "station-a", other_epics, "development_status:\n  1-1-done-elsewhere: done\n")
    _make_station(
        tmp_path, "station-b",
        "## Epic 1: Mine\n\n### Story 1.1: Not Done Here\n**Deps:** —\n\n### Story 1.2: Needs 1.1\n**Deps:** 1.1\n",
        "development_status:\n  1-1-not-done-here: backlog\n  1-2-needs-1-1: backlog\n",
    )
    engine = SprintLedgerQueryEngine(root_dir=tmp_path)
    runnable = {(s.station, s.story_id) for s in get_runnable_backlog(engine)}
    # station-a's done 1.1 must NOT satisfy station-b's dependency on ITS 1.1.
    assert runnable == {("station-b", "1.1")}


# --- A2: epic status, every status bucket, --unimplemented ---

def test_epic_status_comes_from_ledger_epic_key(engine: SprintLedgerQueryEngine) -> None:
    res = engine.query(station="test-station")
    epics = {e.epic_id: e for e in res.epics}
    assert len(res.epics) == 2, "a repeated `### Epic 1` heading reuses the epic, never duplicates it"
    assert epics["1"].status == "done"
    assert epics["2"].status == "in-progress"
    assert [s.story_id for s in epics["1"].stories] == ["1.1", "1.2", "1.3", "1.4", "1.5"]


def test_epic_without_ledger_key_is_unknown(tmp_path: Path) -> None:
    _make_station(tmp_path, "s", "## Epic 7: Nameless\n\n### Story 7.1: X\n", "development_status:\n  7-1-x: done\n")
    res = SprintLedgerQueryEngine(root_dir=tmp_path).query()
    assert res.epics[0].status == "unknown"


def test_station_progress_counts_every_status_with_other_bucket(engine: SprintLedgerQueryEngine) -> None:
    res = engine.query(station="test-station")
    st = res.summary.stations["test-station"]
    assert st.total_stories == 8
    assert (st.done, st.backlog, st.in_progress, st.in_review, st.other) == (1, 4, 1, 1, 1)
    buckets = (
        st.done + st.in_progress + st.backlog + st.blocked + st.optional
        + st.in_review + st.review + st.ready_for_dev + st.ready + st.other
    )
    assert buckets == st.total_stories
    assert res.summary.total_in_review == 1
    assert res.summary.total_other == 1
    assert set(KNOWN_STATUSES) >= {"optional", "in-review", "review", "ready-for-dev", "ready"}


def test_unimplemented_means_status_not_done(engine: SprintLedgerQueryEngine) -> None:
    res = engine.query(station="test-station", unimplemented_only=True)
    assert {s.story_id for s in res.stories} == {"1.2", "1.3", "1.4", "1.5", "2.1", "2.2", "2.3"}
    assert all(s.status != "done" for s in res.stories)


# --- A3: robust ledger read ---

@pytest.mark.parametrize("ledger", ["", "development_status:\n", "development_status: 42\n", "not-a-mapping\n", "[1, 2]\n"])
def test_missing_or_non_dict_development_status_is_an_empty_map(tmp_path: Path, ledger: str, capsys) -> None:
    _make_station(tmp_path, "s", "## Epic 1: E\n\n### Story 1.1: A\n**Status:** done\n", ledger)
    res = SprintLedgerQueryEngine(root_dir=tmp_path).query()
    assert res.summary.total_stories == 1
    assert res.stories[0].status == "done"  # the block's own Status line still applies
    assert capsys.readouterr().out == ""


def test_null_or_non_string_story_value_counts_as_backlog_with_one_warning(tmp_path: Path, capsys) -> None:
    _make_station(
        tmp_path, "s",
        "## Epic 1: E\n\n### Story 1.1: A\n\n### Story 1.2: B\n\n### Story 1.3: C\n",
        "development_status:\n  1-1-a:\n  1-2-b: [x]\n  1-3-c: done\n",
    )
    res = SprintLedgerQueryEngine(root_dir=tmp_path).query()
    assert {s.story_id: s.status for s in res.stories} == {"1.1": "backlog", "1.2": "backlog", "1.3": "done"}
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("null/non-string") == 1
    assert len(res.warnings) == 1


def test_unreadable_epics_skips_station_with_warning(tmp_path: Path, capsys) -> None:
    _make_station(tmp_path, "good")
    bad = _make_station(tmp_path, "bad", "## Epic 1: E\n\n### Story 1.1: A\n")
    (bad / "epics.md").write_bytes(b"## Epic 1: E\n\n### Story 1.1: \xff\xfe broken\n")
    res = SprintLedgerQueryEngine(root_dir=tmp_path).query()
    assert set(res.summary.stations) == {"good"}
    err = capsys.readouterr().err
    assert "bad" in err and "skipped" in err
    assert any("skipped" in w for w in res.warnings)


# --- A4: parser bounds ---

def test_story_block_ends_at_any_heading_and_status_fallback_only_says_done(tmp_path: Path) -> None:
    epics = (
        "## Epic 1: E\n\n"
        "### Story 1.1: Last Story\n**Deps:** —\n\n"
        "## Deferred Work\n\n**Deps:** 9.9\n**Status:** done\n\n"
        "### Story 1.2: Not Done\n**Status:** not done\n\n"
        "### Story 1.3: Undone\n**Status:** undone yet\n\n"
        "### Story 1.4: Really Done\n**Status:** done (2026-09-19)\n\n"
        "#### Story 1.5: Not A Story Heading\n"
    )
    _make_station(tmp_path, "s", epics, "development_status: {}\n")
    res = SprintLedgerQueryEngine(root_dir=tmp_path).query()
    by_id = {s.story_id: s for s in res.stories}
    assert set(by_id) == {"1.1", "1.2", "1.3", "1.4"}
    assert by_id["1.1"].deps == [] and by_id["1.1"].status == "backlog"
    assert by_id["1.2"].status == "backlog"
    assert by_id["1.3"].status == "backlog"
    assert by_id["1.4"].status == "done"


def test_epic_headers_match_two_or_three_hashes(tmp_path: Path) -> None:
    epics = "### Epic 3: Three Hashes\n\n### Story 3.1: A\n\n## Epic 4 — Dash Separator\n\n### Story 4.1: B\n\n## Epic List\n"
    _make_station(tmp_path, "s", epics, "development_status: {}\n")
    res = SprintLedgerQueryEngine(root_dir=tmp_path).query()
    assert [(e.epic_id, e.title) for e in res.epics] == [("3", "Three Hashes"), ("4", "Dash Separator")]
    assert {s.story_id: s.epic_id for s in res.stories} == {"3.1": "3", "4.1": "4"}


def test_tracker_alias_regexes_are_word_bounded(tmp_path: Path) -> None:
    epics = (
        "## Epic 1: E\n\n"
        "### Story 1.1: Aliased\nXJIRA-NOPE-1 JIRA-ABC-12 HUGH-99 GH-42\n\n"
        "### Story 1.2: Unaliased\nJIRA-lower-1 GH-abc\n"
    )
    _make_station(tmp_path, "s", epics, "development_status: {}\n")
    res = SprintLedgerQueryEngine(root_dir=tmp_path).query()
    by_id = {s.story_id: s for s in res.stories}
    assert (by_id["1.1"].jira_key, by_id["1.1"].github_item_id) == ("ABC-12", "42")
    assert (by_id["1.2"].jira_key, by_id["1.2"].github_item_id) == (None, None)
    assert {s.story_id for s in res.stories if not s.jira_key or not s.github_item_id} == {"1.2"}
    assert {s.story_id for s in SprintLedgerQueryEngine(root_dir=tmp_path).query(unlinked_only=True).stories} == {"1.2"}


# --- A5: flags ---

def test_eval_flag_hierarchical_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "absent-flags.json"
    # 1. Override wins over everything (and string values are coerced).
    monkeypatch.setenv("FLAGS_TEST_FLAG", "false")
    assert eval_flag("test-flag", False, flag_overrides={"test-flag": True}, flags_file_path=missing) is True
    assert eval_flag("test-flag", False, flag_overrides={"test-flag": "yes"}, flags_file_path=missing) is True
    # 2. Env var.
    monkeypatch.setenv("FLAGS_MY_FEATURE", "true")
    assert eval_flag("my-feature", False, flags_file_path=missing) is True
    monkeypatch.setenv("FLAGS_MY_FEATURE", "0")
    assert eval_flag("my-feature", True, flags_file_path=missing) is False
    # 3. File.
    monkeypatch.delenv("FLAGS_FILE_FLAG", raising=False)
    flags_file = tmp_path / "flags.json"
    flags_file.write_text(
        json.dumps({"file-flag": {"state": "ENABLED"}, "bare": "v", "valued": {"state": "ENABLED", "value": "x"}}),
        encoding="utf-8",
    )
    assert eval_flag("file-flag", False, flags_file_path=flags_file) is True
    assert eval_flag("bare", None, flags_file_path=flags_file) == "v"
    assert eval_flag("valued", None, flags_file_path=flags_file) == "x"
    # 4. Default.
    assert eval_flag("nonexistent-flag", "default_val", flags_file_path=flags_file) == "default_val"


def test_eval_flag_disabled_state_is_false_regardless_of_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLAGS_OFF_FLAG", raising=False)
    flags_file = tmp_path / "flags.json"
    flags_file.write_text(json.dumps({"off-flag": {"state": "DISABLED", "value": True}}), encoding="utf-8")
    assert eval_flag("off-flag", True, flags_file_path=flags_file) is False


def test_eval_flag_empty_env_means_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLAGS_EMPTY_FLAG", "")
    assert eval_flag("empty-flag", "dflt", flags_file_path=tmp_path / "absent.json") == "dflt"


def test_eval_flag_explicit_missing_file_never_falls_back_to_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLAGS_CWD_FLAG", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "flags.json").write_text(json.dumps({"cwd-flag": True}), encoding="utf-8")
    (tmp_path / ".steward").mkdir()
    (tmp_path / ".steward" / "flags.json").write_text(json.dumps({"cwd-flag": True}), encoding="utf-8")
    assert eval_flag("cwd-flag", "dflt", flags_file_path=tmp_path / "nope.json") == "dflt"


def test_parse_flag_overrides() -> None:
    assert parse_flag_overrides(["a=true", "b=0", "c", "d=text"]) == {"a": True, "b": False, "c": True, "d": "text"}
    assert parse_flag_overrides(None) == {}
    with pytest.raises(ValueError):
        parse_flag_overrides(["=x"])


@pytest.mark.parametrize("format_name,flag_name", sorted(FORMATTER_FLAGS.items()))
def test_gated_formatter_with_flag_off_refuses(duty_engine: Path, monkeypatch: pytest.MonkeyPatch, format_name: str, flag_name: str, capsys) -> None:
    monkeypatch.delenv(f"FLAGS_{flag_name.upper()}", raising=False)
    result = LedgerQueryDuty().run(_ns(format=format_name))
    assert result.ok is False
    assert result.summary == f"flag {flag_name} is off (set FLAGS_{flag_name.upper()}=true, flags.json, or --flag {flag_name}=true)"
    assert capsys.readouterr().out == ""


def test_formatter_flag_map_is_complete() -> None:
    assert FORMATTER_FLAGS == {
        "static-dossier": FLAG_DOSSIER_EXPORT,
        "herald-facts": FLAG_HERALD_FACTS,
        "atlas-dataset": FLAG_VIZRO_DATASET,
        "sync-matrix": FLAG_JIRA_GITHUB_MATRIX,
        "jira-csv": FLAG_JIRA_GITHUB_MATRIX,
        "github-json": FLAG_JIRA_GITHUB_MATRIX,
    }


def test_sync_postgres_with_flag_off_refuses_before_any_sync(duty_engine: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pyforge.steward.sprint_ledger_query as mod

    monkeypatch.delenv("FLAGS_ENABLE_POSTGRES_SYNC", raising=False)
    monkeypatch.setattr(mod, "sync_to_postgres", lambda result: pytest.fail("sync must not run with the flag off"))
    result = LedgerQueryDuty().run(_ns(sync_postgres=True))
    assert result.ok is False
    assert result.summary.startswith(f"flag {FLAG_POSTGRES_SYNC} is off")


def test_flag_override_via_cli_flag_opens_a_gated_formatter(duty_engine: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLAGS_ENABLE_DOSSIER_EXPORT", raising=False)
    result = LedgerQueryDuty().run(_ns(format="static-dossier", flag=["enable_dossier_export=true"]))
    assert result.ok is True
    assert result.summary.startswith("<!DOCTYPE html>")
    result = LedgerQueryDuty().run(_ns(format="static-dossier", flag=["enable_dossier_export=false"]))
    assert result.ok is False


def test_flag_override_via_env_opens_a_gated_formatter(duty_engine: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLAGS_ENABLE_JIRA_GITHUB_MATRIX", "true")
    assert LedgerQueryDuty().run(_ns(format="jira-csv")).ok is True


def test_query_honours_flag_overrides_and_records_them(engine: SprintLedgerQueryEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLAGS_X", raising=False)
    res = engine.query(station="test-station", flag_overrides={"x": "on"})
    assert res.query_flags["flag_overrides"] == {"x": "on"}
    assert engine.flag("x", False, res.query_flags["flag_overrides"]) is True
    assert engine.flag("x", False) is False


def test_pre_query_hook_mutation_is_used_and_a_raising_hook_is_reported(engine: SprintLedgerQueryEngine, capsys) -> None:
    events: list[str] = []

    class Narrow(LedgerQueryHook):
        def pre_query(self, filters: dict) -> None:
            filters["search_term"] = "Story One"

    class Broken(LedgerQueryHook):
        def pre_query(self, filters: dict) -> None:
            raise RuntimeError("boom")

        def on_export(self, format_name: str, output: str) -> None:
            raise ValueError("bang")

    class After(LedgerQueryHook):
        def pre_query(self, filters: dict) -> None:
            events.append("after-pre")

        def post_query(self, result) -> None:
            events.append("post")

        def on_export(self, format_name: str, output: str) -> None:
            events.append(f"export_{format_name}")

    engine.hooks.register(Narrow())
    engine.hooks.register(Broken())
    engine.hooks.register(After())
    res = engine.query(station="test-station")
    engine.export(res, "summary")

    assert [s.story_id for s in res.stories] == ["1.1"], "the query must use the dict the hook mutated"
    assert events == ["after-pre", "post", "export_summary"], "hooks after the raising one still run"
    assert any("Broken.pre_query raised RuntimeError: boom" in w for w in res.warnings)
    assert any("Broken.on_export raised ValueError: bang" in w for w in res.warnings)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Broken.pre_query raised RuntimeError" in captured.err


# --- A6: sources ---

def test_default_source_is_registered_and_a_custom_source_is_exercised(engine: SprintLedgerQueryEngine) -> None:
    assert engine.sources.list_sources() == ["tracked-ledger"]

    class Extra(LedgerSourcePlugin):
        @property
        def name(self) -> str:
            return "extra"

        def load_station(self, station: str, project_dir: Path) -> StationLedger:
            ledger = StationLedger(station=station)
            ledger.epics, ledger.stories = [], []
            from pyforge.steward.sprint_ledger_query import parse_epics_markdown

            ledger.epics, ledger.stories = parse_epics_markdown(
                "## Epic 9: Extra\n\n### Story 9.1: From Plugin\n", station, {"9-1-from-plugin": "blocked"}
            )
            return ledger

    engine.sources.register(Extra())
    res = engine.query(station="test-station")
    assert "9.1" in {s.story_id for s in res.stories}
    assert res.summary.stations["test-station"].blocked == 1
    with pytest.raises(ValueError):
        engine.sources.register(Extra())


def test_engine_default_root_is_the_repo_root_not_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    engine = SprintLedgerQueryEngine()
    assert engine.root_dir != tmp_path
    assert (engine.root_dir / "scripts" / "bmad-loop-worktree").is_file()


# --- A7: front doors ---

def test_cli_format_choices_come_from_the_registry() -> None:
    parser = build_parser()
    ns = parser.parse_args(["ledger-query", "--format", "static-dossier", "--flag", "a=1", "--flag", "b=2"])
    assert ns.flag == ["a=1", "b=2"]
    with pytest.raises(SystemExit):
        parser.parse_args(["ledger-query", "--format", "dossier"])
    action = next(a for a in parser._actions if a.dest == "duty")
    ledger_parser = action.choices["ledger-query"]
    fmt = next(a for a in ledger_parser._actions if a.dest == "format")
    assert list(fmt.choices) == default_formatter_names() == SprintLedgerQueryEngine(root_dir=Path(".")).formatters.list_formatters()


def test_help_names_static_dossier_and_summary() -> None:
    from pyforge.steward.cli import _HELP

    assert "static-dossier" in _HELP["ledger-query"]
    assert "summary" in _HELP["ledger-query"]
    assert "/dossier/" not in _HELP["ledger-query"]


def test_duplicate_formatter_registration_raises() -> None:
    registry = FormatterRegistry()
    registry.register(SummaryFormatter())
    with pytest.raises(ValueError):
        registry.register(SummaryFormatter())
    assert registry.list_formatters() == ["summary"]


def test_unknown_station_and_status_refuse_naming_the_known_set(duty_engine: Path) -> None:
    result = LedgerQueryDuty().run(_ns(station="nope"))
    assert result.ok is False
    assert "unknown station 'nope'" in result.summary and "test-station" in result.summary

    result = LedgerQueryDuty().run(_ns(status="backlog,bogus"))
    assert result.ok is False
    assert "unknown status bogus" in result.summary
    for known in KNOWN_STATUSES:
        assert known in result.summary

    assert LedgerQueryDuty().run(_ns(station="test-station", status="backlog,In-Progress")).ok is True


def test_epic_filter_is_a_cli_front_door(duty_engine: Path) -> None:
    """CAP-146 names an epic filter; the duty passes `--epic` to the engine."""
    parser = build_parser()
    assert parser.parse_args(["ledger-query", "--epic", "2"]).epic == "2"

    result = LedgerQueryDuty().run(_ns(epic="2", format="json"))
    assert result.ok is True
    stories = json.loads(result.summary)["stories"]
    assert {s["story_id"] for s in stories} == {"2.1", "2.2", "2.3"}
    assert result.details["matching_stories"] == 3

    assert LedgerQueryDuty().run(_ns(epic="99", format="json")).details["matching_stories"] == 0


# --- A8: stdout purity ---

def test_json_with_sync_postgres_leaves_stdout_valid_json(duty_engine: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import pyforge.steward.sprint_ledger_query as mod

    monkeypatch.setattr(mod, "sync_to_postgres", lambda result: {"status": "success", "synced_count": len(result.stories), "method": "stub"})
    rc = main(["ledger-query", "--format", "json", "--sync-postgres", "--flag", "enable_postgres_sync=true"])
    captured = capsys.readouterr()
    assert rc == EXIT_OK
    payload = json.loads(captured.out)
    assert payload["$schema"] == SCHEMA_URN
    assert "[PostgreSQL Work Passport Sync] success (8 records)" in captured.err

    result = LedgerQueryDuty().run(_ns(format="json", sync_postgres=True, flag=["enable_postgres_sync=true"]))
    assert result.details["sync"]["status"] == "success"
    assert "Sync Result" not in result.summary and json.loads(result.summary)


def test_sync_postgres_not_success_is_not_ok(duty_engine: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import pyforge.steward.sprint_ledger_query as mod

    monkeypatch.setattr(mod, "sync_to_postgres", lambda result: {"status": "fallback_payload", "count": 1, "message": "no orm"})
    rc = main(["ledger-query", "--format", "json", "--sync-postgres", "--flag", "enable_postgres_sync=true"])
    captured = capsys.readouterr()
    assert rc == EXIT_FAILED
    assert captured.out == ""
    assert "fallback_payload" in captured.err and "no orm" in captured.err


def test_output_writes_file_only_and_stdout_is_empty(duty_engine: Path, tmp_path: Path, capsys) -> None:
    out = tmp_path / "nested" / "report.json"
    rc = main(["ledger-query", "--format", "json", "--output", str(out)])
    captured = capsys.readouterr()
    assert rc == EXIT_OK
    assert captured.out == ""
    assert str(out) in captured.err
    assert json.loads(out.read_text(encoding="utf-8"))["matching_stories_count"] == 8


def test_output_write_failure_is_not_ok(duty_engine: Path, tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    result = LedgerQueryDuty().run(_ns(format="json", output=str(blocker / "child.json")))
    assert result.ok is False
    assert "could not write" in result.summary


# --- A9: postgres refusal from the base package ---

def test_sync_to_postgres_refuses_without_the_dashboard_extra(engine: SprintLedgerQueryEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    real_import = importlib.import_module

    def _no_extra(name, *args, **kwargs):
        if name == "pyforge.steward.dashboard.passport_sync":
            raise ImportError("stripped install")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", _no_extra)
    res = engine.query(station="test-station")
    out = sync_to_postgres(res)
    assert out["status"] == "refused"
    assert out["message"] == "pyforge-steward[dashboard] extra not installed"
    assert "passports" not in out, "no duplicated fallback dict in the base package"


# --- A10: formatters round-trip, cross-station shapes, schema ---

def test_every_formatter_round_trips_the_fixture(engine: SprintLedgerQueryEngine) -> None:
    res = engine.query(station="test-station")
    names = engine.formatters.list_formatters()
    assert names == [
        "atlas-dataset", "github-json", "herald-facts", "jira-csv", "json", "markdown",
        "static-dossier", "summary", "sync-matrix", "table",
    ]
    outputs = {name: engine.export(res, name) for name in names}
    assert all(isinstance(o, str) and o for o in outputs.values())

    assert "Estate Sprint Ledger Query Report" in outputs["markdown"] and "Story One" in outputs["markdown"]
    assert outputs["summary"].startswith("Estate Sprint Ledger Summary: 8 stories across 1 stations.")
    assert json.loads(outputs["json"])["matching_stories_count"] == 8
    assert "| 1.1" in outputs["table"] and "Story One" in outputs["table"]
    assert "3-Way Alignment Sync Matrix" in outputs["sync-matrix"] and "ALIGNED" in outputs["sync-matrix"]

    import csv
    import io

    rows = list(csv.reader(io.StringIO(outputs["jira-csv"])))
    assert rows[0][0] == "Issue Type" and len(rows) == 9
    gh = json.loads(outputs["github-json"])
    assert len(gh["github_project_items"]) == 8 and gh["github_project_items"][1]["item_id"] == "77"
    assert outputs["static-dossier"].startswith("<!DOCTYPE html>") and "Story One" in outputs["static-dossier"]


def test_herald_facts_emits_heralds_facts_ledger_shape(engine: SprintLedgerQueryEngine) -> None:
    import yaml

    res = engine.query(station="test-station")
    ledger = yaml.safe_load(engine.export(res, "herald-facts", deck="sprint-backlog", persona="PyForge Estate", tree="abc123"))
    assert list(ledger) == ["deck", "persona", "derived_at", "tree", "facts"]
    assert ledger["deck"] == "sprint-backlog" and ledger["tree"] == "abc123"
    assert ledger["derived_at"] == res.generated_at
    ids = [f["id"] for f in ledger["facts"]]
    assert ids[0] == "stories_done_total" and "test_station_stories_done" in ids
    for fact in ledger["facts"]:
        assert set(fact) == {"id", "value", "source", "method", "shown_as"}
        assert isinstance(fact["value"], str) and fact["value"] in fact["shown_as"]
        assert fact["source"].startswith("_bmad-output/projects/")
    done_total = next(f for f in ledger["facts"] if f["id"] == "stories_done_total")
    assert done_total["value"] == "1/8" and done_total["shown_as"] == ["1/8", "1 of 8"]
    assert "kind" not in ledger and "metrics" not in ledger


def test_atlas_dataset_claims_no_atlas_catalog_name(engine: SprintLedgerQueryEngine) -> None:
    res = engine.query(station="test-station")
    dataset = json.loads(engine.export(res, "atlas-dataset"))
    assert "dataset_id" not in dataset
    assert dataset["producer"] == "pyforge-steward:sprint-ledger-query"
    assert "steward-shaped" in dataset["note"]
    assert len(dataset["records"]) == 8 and dataset["records"][0]["passport_id"]


def _structural_check(payload: dict, schema: dict) -> None:
    assert set(payload) == set(schema["required"])
    assert payload["$schema"] == schema["properties"]["$schema"]["const"]
    assert set(payload["summary"]) == set(schema["$defs"]["estate_summary"]["required"])
    for station in payload["summary"]["stations"].values():
        assert set(station) == set(schema["$defs"]["station_progress"]["required"])
    for story in payload["stories"]:
        assert set(story) == set(schema["$defs"]["story"]["required"])
    for epic in payload["epics"]:
        assert set(epic) == set(schema["$defs"]["epic"]["required"])


def test_json_payload_validates_against_the_shipped_schema(engine: SprintLedgerQueryEngine) -> None:
    assert SCHEMA_PATH.is_file(), "the $schema URN promises a shipped schema file"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$id"] == SCHEMA_URN
    payload = json.loads(engine.export(engine.query(station="test-station"), "json"))
    _structural_check(payload, schema)
    try:
        import jsonschema
    except ImportError:  # pragma: no cover -- jsonschema is not a steward dependency
        return
    jsonschema.validate(payload, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**payload, "stories": [{"passport_id": 1}]}, schema)


# --- A11: HTML escaping ---

def test_static_dossier_escapes_every_interpolated_field(tmp_path: Path) -> None:
    epics = "## Epic 1: E\n\n### Story 1.1: <name> & <script>alert(1)</script>\nJIRA-XSS-1 GH-1\n"
    _make_station(tmp_path, "st<ation", epics, "development_status:\n  1-1-x: done\n")
    engine = SprintLedgerQueryEngine(root_dir=tmp_path)
    out = engine.export(engine.query(), "static-dossier")
    assert "<name>" not in out and "<script>alert(1)</script>" not in out
    assert "&lt;name&gt; &amp; &lt;script&gt;alert(1)&lt;/script&gt;" in out
    assert "st&lt;ation" in out


# --- A12: docstring claims ---

def test_module_docstring_makes_no_sdk_claim() -> None:
    import pyforge.steward.sprint_ledger_query as mod

    assert "OpenFeature SDK" not in mod.__doc__
    assert "FLAGS_<NAME>" in mod.__doc__ and "--flag" in mod.__doc__ and "flags.json" in mod.__doc__
    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "import openfeature" not in source and "from openfeature" not in source


class _Custom(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "custom"

    def format(self, result, **kwargs) -> str:
        return f"custom:{len(result.stories)}"


def test_registered_plugin_formatter_is_exercised_without_editing_the_engine(engine: SprintLedgerQueryEngine) -> None:
    engine.formatters.register(_Custom())
    assert engine.export(engine.query(station="test-station"), "custom") == "custom:8"


# --- CAP-1 success: agreement with fleet_scan.parse_sprint_status over the live tree ---

def _repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "scripts" / "bmad-loop-worktree").is_file():
            return ancestor
    raise AssertionError("could not locate repo root")


def test_engine_counts_agree_with_fleet_scan_parse_sprint_status_over_the_live_tree() -> None:
    root = _repo_root()
    sys.path.insert(0, str(root / "scripts"))
    try:
        from fleet_scan import parse_sprint_status
    finally:
        sys.path.pop(0)

    res = SprintLedgerQueryEngine(root_dir=root).query()
    ledgers = sorted(root.glob("_bmad-output/projects/*/planning-artifacts/sprint-status-ledger.yaml"))
    assert ledgers, "the live tree carries tracked ledgers"
    for ledger in ledgers:
        station = ledger.parents[1].name
        counts = collections.Counter(
            status for key, status in parse_sprint_status(ledger).items() if not key.startswith("epic-")
        )
        progress = res.summary.stations[station]
        assert (progress.total_stories, progress.done, progress.backlog, progress.blocked) == (
            sum(counts.values()), counts["done"], counts["backlog"], counts["blocked"],
        ), station
