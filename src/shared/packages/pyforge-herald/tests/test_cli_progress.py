"""``herald progress``'s real behavior (Stories 8.1-8.3, scaled-down Epic 8):
show one station's latest record, ``--update`` (operator-gated write), and
``--list``/bare listing.

Every test ``chdir``s to an empty ``tmp_path`` (via the ``_isolate_cwd``
autouse fixture below) -- ``cli._progress_path`` resolves
``progress.DEFAULT_PROGRESS_PATH`` against ``Path.cwd()``, and no test here
may read or write the real repo's own ``.herald/progress.json``."""

from __future__ import annotations

import json

import pytest

from pyforge.herald import auth, cli


@pytest.fixture(autouse=True)
def _isolate_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _no_real_auth_env(monkeypatch):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)


def _update(monkeypatch, station, *extra_args, narrative="unblocked", role="operator"):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, f"{role}:tok")
    return cli.main(
        [
            "progress",
            station,
            "--update",
            "--unblock-narrative",
            narrative,
            *extra_args,
        ]
    )


# --- Story 8.3: `herald progress <station>` (show latest) -----------------


def test_show_unknown_station_exits_1_and_lists_available(capsys):
    assert cli.main(["progress", "bogus-station"]) == 1
    err = capsys.readouterr().err
    assert "bogus-station" in err
    assert "warden" in err
    assert "--list" in err


def test_show_known_station_with_no_records_prints_helpful_message(capsys):
    assert cli.main(["progress", "warden"]) == 0
    assert "No progress recorded for warden" in capsys.readouterr().out


def test_show_known_station_with_no_records_json(capsys):
    assert cli.main(["progress", "warden", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == {"station": "warden", "record": None}


def test_show_returns_the_latest_record(capsys, monkeypatch):
    _update(
        monkeypatch,
        "warden",
        "--shipped",
        "hygiene gate",
        "--compute-hours",
        "3.5",
        "--token-spend",
        "42000",
        "--wall-clock-hours",
        "6",
    )
    capsys.readouterr()
    assert cli.main(["progress", "warden"]) == 0
    out = capsys.readouterr().out
    assert "station: warden" in out
    assert "hygiene gate" in out
    assert "compute_hours: 3.5" in out
    assert "token_spend: 42000" in out
    assert "unblock_narrative: unblocked" in out


def test_show_json_includes_every_field(capsys, monkeypatch):
    _update(monkeypatch, "warden", narrative="all clear")
    capsys.readouterr()
    assert cli.main(["progress", "warden", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    for field in (
        "id",
        "station",
        "date",
        "shipped_capabilities",
        "compute_hours",
        "token_spend",
        "wall_clock_hours",
        "unblock_narrative",
        "created_at",
        "updated_at",
    ):
        assert field in payload
    assert payload["station"] == "warden"
    assert payload["unblock_narrative"] == "all clear"


# --- Story 8.2/8.3: `herald progress <station> --update` ------------------


def test_update_without_operator_role_is_refused_exit_1(capsys, monkeypatch):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok")
    assert cli.main(["progress", "warden", "--update"]) == 1
    err = capsys.readouterr().err
    assert "unauthorized" in err
    assert "operator role" in err


def test_update_with_no_auth_context_names_the_remediation(capsys):
    assert cli.main(["progress", "warden", "--update"]) == 1
    err = capsys.readouterr().err
    assert "auth context missing" in err
    assert "HERALD_TOKEN" in err


def test_update_unknown_station_exits_1_even_with_operator_role(capsys, monkeypatch):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    assert cli.main(["progress", "bogus-station", "--update"]) == 1
    err = capsys.readouterr().err
    assert "bogus-station" in err


def test_update_creates_a_record_for_today(capsys, monkeypatch):
    assert (
        _update(
            monkeypatch,
            "warden",
            "--shipped",
            "cap-a",
            "--shipped",
            "cap-b",
            "--compute-hours",
            "1.5",
            "--token-spend",
            "1000",
            "--wall-clock-hours",
            "2",
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "Progress updated for warden" in out


def test_update_json_prints_the_full_record(capsys, monkeypatch):
    assert _update(monkeypatch, "warden", "--json", "--shipped", "cap-a") == 0
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["station"] == "warden"
    assert payload["shipped_capabilities"] == ["cap-a"]


def test_update_missing_flags_default_to_zero_and_empty(capsys, monkeypatch):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    assert cli.main(["progress", "warden", "--update", "--unblock-narrative", ""]) == 0
    capsys.readouterr()
    assert cli.main(["progress", "warden", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["shipped_capabilities"] == []
    assert payload["compute_hours"] == 0.0
    assert payload["token_spend"] == 0
    assert payload["wall_clock_hours"] == 0.0


def test_update_a_second_time_same_day_replaces_not_appends(capsys, monkeypatch):
    _update(monkeypatch, "warden", "--shipped", "first")
    capsys.readouterr()
    _update(monkeypatch, "warden", "--shipped", "second", narrative="updated")
    capsys.readouterr()
    assert cli.main(["progress", "--list", "--station", "warden", "--json"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["shipped_capabilities"] == ["second"]
    assert payload["unblock_narrative"] == "updated"


def test_update_with_no_unblock_narrative_flag_prompts_interactively(
    capsys, monkeypatch
):
    """No ``--unblock-narrative`` flag -- ``_run_progress_update`` must
    call ``_prompt_unblock_narrative`` (Story 8.2's scaled-down "operator
    prompted" AC) rather than silently defaulting to an empty narrative."""
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(
        cli, "_prompt_unblock_narrative", lambda *_a, **_k: "typed narrative"
    )
    assert cli.main(["progress", "warden", "--update"]) == 0
    capsys.readouterr()
    assert cli.main(["progress", "warden", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["unblock_narrative"] == "typed narrative"


# --- Story 8.3: `herald progress --list` / bare listing --------------------


def test_list_with_no_records_prints_helpful_message(capsys):
    assert cli.main(["progress", "--list"]) == 0
    assert "No progress records found." in capsys.readouterr().out


def test_list_filters_by_station(capsys, monkeypatch):
    _update(monkeypatch, "warden", "--shipped", "a")
    capsys.readouterr()
    _update(monkeypatch, "atlas", "--shipped", "b")
    capsys.readouterr()
    assert cli.main(["progress", "--list", "--station", "warden", "--json"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["station"] == "warden"


def test_list_unknown_station_filter_exits_1(capsys):
    assert cli.main(["progress", "--list", "--station", "bogus-station"]) == 1
    err = capsys.readouterr().err
    assert "bogus-station" in err


def test_list_json_is_ndjson_one_record_per_line(capsys, monkeypatch):
    _update(monkeypatch, "warden", "--shipped", "a")
    capsys.readouterr()
    _update(monkeypatch, "atlas", "--shipped", "b")
    capsys.readouterr()
    assert cli.main(["progress", "--list", "--json"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        json.loads(line)  # raises if not valid JSON


def test_list_plain_text_summarizes_each_record(capsys, monkeypatch):
    _update(monkeypatch, "warden", "--shipped", "a", "--shipped", "b")
    capsys.readouterr()
    assert cli.main(["progress", "--list"]) == 0
    out = capsys.readouterr().out
    assert "warden" in out
    assert "2 capabilities" in out


def test_list_read_only_never_checks_auth(capsys):
    assert cli.main(["progress", "--list"]) == 0
    assert "unauthorized" not in capsys.readouterr().err


def test_bare_progress_defaults_to_list_mode(capsys, monkeypatch):
    _update(monkeypatch, "warden", "--shipped", "a")
    capsys.readouterr()
    assert cli.main(["progress"]) == 0
    assert "warden" in capsys.readouterr().out


# --- Story 8.2: `_prompt_unblock_narrative`'s injectable reader ------------


def test_prompt_unblock_narrative_returns_the_stripped_answer():
    assert (
        cli._prompt_unblock_narrative(
            "warden", "2026-08-08", reader=lambda _p: "  all clear  "
        )
        == "all clear"
    )


def test_prompt_unblock_narrative_on_eof_returns_empty_string():
    def _raise_eof(_prompt: str) -> str:
        raise EOFError

    assert (
        cli._prompt_unblock_narrative("warden", "2026-08-08", reader=_raise_eof) == ""
    )
