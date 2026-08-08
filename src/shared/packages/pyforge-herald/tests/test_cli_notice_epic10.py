"""Epic 10's real ``herald notice`` CLI surface (Story 10.4), replacing the
Epic 6 write-gated stub. Every write subcommand (``author``/``publish``/
``close``/``archive``) still routes through ``auth.require_operator_role``
first -- proven the same way ``test_cli_epic6.py`` proved the stub's gate:
set ``HERALD_TOKEN`` to a non-operator role and assert the refusal, exit 1,
before any state is written.
"""

from __future__ import annotations

import json

import pytest
from pyforge.herald import auth, cli, notices


@pytest.fixture(autouse=True)
def _no_real_auth_env(monkeypatch):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)


@pytest.fixture(autouse=True)
def _operator(monkeypatch):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: True)


AUTHOR_ARGS = [
    "notice",
    "author",
    "--type",
    "deprecation",
    "--component",
    "auth-api-v1",
    "--what",
    "deprecated",
    "--why",
    "superseded",
    "--migration",
    "swap urls",
    "--deadline",
    "2026-09-01",
]


def _author(monkeypatch, tmp_path, *, extra=()):
    monkeypatch.chdir(tmp_path)
    return cli.main([*AUTHOR_ARGS, *extra])


# --- write gate --------------------------------------------------------


def test_author_without_operator_role_is_refused(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok")
    assert _author(monkeypatch, tmp_path) == 1
    assert "unauthorized" in capsys.readouterr().err
    assert not (tmp_path / "notices").exists()


def test_publish_without_operator_role_is_refused(capsys, monkeypatch, tmp_path):
    _author(monkeypatch, tmp_path)
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok")
    assert cli.main(["notice", "publish", "auth-api-v1"]) == 1
    assert "unauthorized" in capsys.readouterr().err


def test_close_without_operator_role_is_refused(capsys, monkeypatch, tmp_path):
    _author(monkeypatch, tmp_path, extra=["--publish"])
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok")
    assert cli.main(["notice", "close", "auth-api-v1"]) == 1
    assert "unauthorized" in capsys.readouterr().err


def test_archive_without_operator_role_is_refused(capsys, monkeypatch, tmp_path):
    _author(monkeypatch, tmp_path, extra=["--publish"])
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok")
    assert (
        cli.main(["notice", "archive", "--rename", "auth-api-v1", "auth-api-v2"]) == 1
    )
    assert "unauthorized" in capsys.readouterr().err


def test_read_commands_never_check_auth(capsys, monkeypatch, tmp_path):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["notice"]) == 0
    assert cli.main(["notice", "list"]) == 0
    assert "unauthorized" not in capsys.readouterr().err


# --- author / publish / close / list / get / archive happy paths -------


def test_author_creates_a_draft_and_confirmation_declined_writes_nothing(
    capsys, monkeypatch, tmp_path
):
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: False)
    assert _author(monkeypatch, tmp_path) == 0
    out = capsys.readouterr().out
    assert "aborted" in out
    assert not (tmp_path / ".herald" / "notices-index.json").exists()


def test_author_then_list_shows_nothing_until_published(monkeypatch, tmp_path, capsys):
    _author(monkeypatch, tmp_path)
    capsys.readouterr()
    assert cli.main(["notice", "--json", "list"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == []


def test_author_publish_close_lifecycle_end_to_end(monkeypatch, tmp_path, capsys):
    _author(monkeypatch, tmp_path)
    capsys.readouterr()

    assert cli.main(["notice", "publish", "auth-api-v1"]) == 0
    assert "published" in capsys.readouterr().out

    assert cli.main(["notice", "--json", "list"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert [n["component"] for n in payload] == ["auth-api-v1"]
    assert payload[0]["status"] == "published"

    assert cli.main(["notice", "close", "auth-api-v1", "--reason", "done"]) == 0
    assert "closed" in capsys.readouterr().out

    assert cli.main(["notice", "--json", "get", "auth-api-v1"]) == 0
    detail = json.loads(capsys.readouterr().out.strip())
    assert detail["status"] == "closed"
    assert detail["close_reason"] == "done"
    assert detail["closed_by"]  # non-empty: role:source from the auth context


def test_list_category_filter(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    notices.author_notice(
        tmp_path,
        notice_type="deprecation",
        component="dep-one",
        what="w",
        why="w",
        migration="m",
        deadline=None,
        reason_link=None,
        publish=True,
    )
    notices.author_notice(
        tmp_path,
        notice_type="eol",
        component="eol-one",
        what="w",
        why="w",
        migration="m",
        deadline=None,
        reason_link=None,
        publish=True,
    )
    capsys.readouterr()
    assert cli.main(["notice", "--json", "list", "--category", "eol"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert [n["component"] for n in payload] == ["eol-one"]


def test_list_status_draft_flag(monkeypatch, tmp_path, capsys):
    _author(monkeypatch, tmp_path)
    capsys.readouterr()
    assert cli.main(["notice", "--json", "list", "--status", "draft"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert [n["component"] for n in payload] == ["auth-api-v1"]


def test_json_flag_works_both_before_and_after_the_list_subcommand(
    monkeypatch, tmp_path, capsys
):
    """Regression: `--json`/`--date-range`/`--station` were only attached
    to the `notice` parser itself, not `notice list`'s own sub-subparser
    -- `herald notice list --json` (the natural, expected order) failed
    with "unknown flag '--json'", exit 2, while `herald notice --json
    list` silently worked. `--help` on `notice list` gave no hint either,
    since the flags belonged to the parent parser."""
    _author(monkeypatch, tmp_path, extra=["--publish"])

    capsys.readouterr()
    assert cli.main(["notice", "list", "--json"]) == 0
    after = json.loads(capsys.readouterr().out.strip())

    assert cli.main(["notice", "--json", "list"]) == 0
    before = json.loads(capsys.readouterr().out.strip())

    assert after == before
    assert [n["component"] for n in after] == ["auth-api-v1"]


def test_get_of_unknown_component_exits_1(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["notice", "get", "nope"]) == 1
    assert "no notice found" in capsys.readouterr().err


def test_archive_rename_then_get_follows_redirect(monkeypatch, tmp_path, capsys):
    _author(monkeypatch, tmp_path, extra=["--publish"])
    assert (
        cli.main(
            [
                "notice",
                "author",
                "--type",
                "deprecation",
                "--component",
                "auth-api-v2",
                "--what",
                "w",
                "--why",
                "w",
                "--migration",
                "m",
                "--deadline",
                "2026-09-01",
                "--publish",
            ]
        )
        == 0
    )
    assert (
        cli.main(["notice", "archive", "--rename", "auth-api-v1", "auth-api-v2"]) == 0
    )
    capsys.readouterr()
    assert cli.main(["notice", "--json", "get", "auth-api-v1"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["component"] == "auth-api-v2"


# --- interactive prompting for missing author fields --------------------


def test_author_prompts_for_missing_fields(monkeypatch, tmp_path, capsys):
    """``_prompt`` (mirroring ``auth.confirm``'s injectable-``reader``
    convention) is exercised end to end here by monkeypatching the CLI's
    own ``_prompt`` -- ``auth.confirm``'s own tests take the identical
    approach for its default ``reader=input`` (patching the bound
    function, not ``builtins.input``, since the default is captured once
    at def time)."""
    monkeypatch.chdir(tmp_path)
    answers = iter(
        ["deprecation", "prompted-component", "what text", "why text", "mig text", ""]
    )
    monkeypatch.setattr(cli, "_prompt", lambda *_a, **_k: next(answers))
    assert cli.main(["notice", "author"]) == 0
    out = capsys.readouterr().out
    assert "authored" in out
    assert "prompted-component" in out
