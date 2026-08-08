"""Epic 6's CLI surface: the dispatcher (Story 6.1), shared global flags
(Story 6.2), the operator-role write gate wired into ``success
publish``/``notice author`` (Story 6.3), and inline ``--help`` (Story 6.5).

Auth is exercised through the real ``cli.main`` entry point with
``HERALD_TOKEN``/a ``config_path``-free ``auth.resolve_auth_context`` --
every write-command test sets or clears ``HERALD_TOKEN`` via ``monkeypatch``
(never touching a real ``~/.herald/config``) and stubs ``auth.confirm`` so
no test blocks on stdin.
"""

from __future__ import annotations

import json

import pytest
from pyforge.herald import auth, claims, cli, evidence

# --- Story 6.1: dispatcher ---------------------------------------------


def test_no_arguments_is_a_usage_error_exit_1(capsys):
    assert cli.main([]) == 1
    err = capsys.readouterr().err
    assert "deck" in err
    assert "progress" in err


def test_help_flag_exits_0_and_lists_subcommands(capsys):
    assert cli.main(["--help"]) == 0
    out = capsys.readouterr().out
    for command in cli.TOP_LEVEL_COMMANDS:
        assert command in out


def test_progress_with_no_flags_routes_and_exits_0(capsys, tmp_path, monkeypatch):
    """Story 8.3: bare ``herald progress`` (no station, no ``--list``)
    defaults to list mode. With no records recorded yet, that is an empty,
    still-exit-0 listing -- not an error. ``chdir`` to an empty ``tmp_path``
    so this never reads a real ``.herald/progress.json`` from wherever
    pytest happens to be invoked."""
    monkeypatch.chdir(tmp_path)
    assert cli.main(["progress"]) == 0
    assert "No progress records found." in capsys.readouterr().out


def test_keyboard_interrupt_during_a_subcommand_exits_130(monkeypatch):
    """The implementation notes' interrupt convention: a ``KeyboardInterrupt``
    raised while a subcommand's own operation runs (e.g. Ctrl-C at the
    ``success publish`` confirmation prompt) is not a ``HeraldError`` --
    ``dispatch`` does not catch it, so it propagates to ``main``'s own
    handler."""

    def _raise_interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "_run_progress", _raise_interrupt)
    assert cli.main(["progress"]) == 130


def test_unknown_deck_subcommand_exits_2_and_names_deck_choices_not_top_level(capsys):
    """Regression: the invalid-choice reword must read its 'valid
    subcommands' list from argparse's own choices at whichever nesting
    level raised -- an earlier draft hardcoded the top-level list, which
    would have wrongly suggested 'progress'/'success'/'notice' for a typo
    under `deck` (which only ever has `seed`)."""
    assert cli.main(["deck", "bogus"]) == 2
    err = capsys.readouterr().err
    assert "unknown command 'bogus'" in err
    assert "'seed'" in err
    assert "progress" not in err


def test_unknown_command_exits_2_and_names_it(capsys):
    assert cli.main(["unknown-command"]) == 2
    err = capsys.readouterr().err
    assert "unknown-command" in err
    for command in cli.TOP_LEVEL_COMMANDS:
        assert command in err


# --- Story 6.2: shared global flags -------------------------------------


def test_json_flag_prints_valid_json_no_ansi(capsys, tmp_path, monkeypatch):
    """Exercised on ``notice`` -- all three Moment subcommands (Epics
    8/9/10) are real now, so this test's job is only the shared ``--json``
    plumbing itself: the flag parses, and a fresh repo with no notices
    yet produces a clean, valid, empty JSON array."""
    monkeypatch.chdir(tmp_path)
    assert cli.main(["notice", "--json"]) == 0
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)  # raises if not valid JSON
    assert "\x1b" not in out
    assert payload == []


def test_json_short_flag_alias(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["notice", "-j"]) == 0
    json.loads(capsys.readouterr().out.strip())


def test_date_range_valid_filters_and_exits_0(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["notice", "--json", "--date-range", "2026-08-01..2026-08-31"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == []


def test_date_range_invalid_exits_1_and_names_the_problem(capsys):
    assert cli.main(["progress", "--date-range", "invalid..dates"]) == 1
    err = capsys.readouterr().err
    assert "Invalid date format" in err


def test_date_range_inverted_start_after_end_exits_1(capsys):
    """Regression: ``_parse_date_range`` only validated each half in
    isolation -- ``2026-08-31..2026-08-01`` parsed fine and silently
    returned a nonsensical (start-after-end) pair."""
    assert cli.main(["progress", "--date-range", "2026-08-31..2026-08-01"]) == 1
    err = capsys.readouterr().err
    assert "Invalid date range" in err


def test_date_range_empty_string_is_validated_not_treated_as_absent(capsys):
    """Regression: ``if args.date_range else None`` treated an explicit
    empty ``--date-range ""`` the same as no flag at all (falsy), silently
    skipping validation instead of raising ``InvalidDateRangeError``."""
    assert cli.main(["progress", "--date-range", ""]) == 1
    err = capsys.readouterr().err
    assert "Invalid date format" in err


def test_json_flag_renders_error_as_json_on_stderr(capsys):
    """Regression: a ``--json`` caller got a plain-text error line on a
    ``HeraldError`` (e.g. a bad ``--date-range``), even though it asked
    for machine-readable output -- parsing stderr as JSON on failure would
    have raised instead of surfacing the real error."""
    assert cli.main(["progress", "--json", "--date-range", "invalid..dates"]) == 1
    err = capsys.readouterr().err.strip()
    payload = json.loads(err)
    assert payload["error"] == "InvalidDateRangeError"
    assert "Invalid date format" in payload["message"]


def test_station_flag_filters(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["notice", "--json", "--station", "warden"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == []


def test_station_short_flag_alias(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["notice", "--json", "-s", "warden"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == []


def test_unknown_global_flag_exits_2_and_names_it(capsys):
    assert cli.main(["progress", "--unknown-flag"]) == 2
    err = capsys.readouterr().err
    assert "--unknown-flag" in err


# --- Story 6.3: operator-role write gate --------------------------------


@pytest.fixture(autouse=True)
def _no_real_auth_env(monkeypatch):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)


def test_success_publish_without_operator_role_is_refused_exit_1(capsys, monkeypatch):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok")
    assert cli.main(["success", "publish", "claim-123"]) == 1
    err = capsys.readouterr().err
    assert "unauthorized" in err
    assert "operator role" in err


def test_success_publish_with_no_auth_context_names_the_remediation(capsys):
    assert cli.main(["success", "publish", "claim-123"]) == 1
    err = capsys.readouterr().err
    assert "auth context missing" in err
    assert "HERALD_TOKEN" in err


def test_success_publish_with_operator_role_proceeds_to_the_real_publish(
    capsys, monkeypatch, tmp_path
):
    """Epic 9 replaces the Epic 6 stub with a real publish -- this test now
    creates a draft claim first (via ``claims.create`` directly, ahead of
    the ``--repo-root``-scoped CLI call) and asserts the gate still runs
    *before* the real work, same as the stub always did."""
    monkeypatch.setattr(evidence, "validate_for_publish", lambda url, **_k: None)
    claim = claims.create(tmp_path / claims.DEFAULT_CLAIMS_PATH, project_name="warden")
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: True)
    assert (
        cli.main(
            [
                "success",
                "--repo-root",
                str(tmp_path),
                "publish",
                claim.id,
                "--thesis",
                "Shipped it",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert claim.id in out
    assert "published" in out


def test_success_publish_confirmation_declined_takes_no_action(
    capsys, monkeypatch, tmp_path
):
    claim = claims.create(tmp_path / claims.DEFAULT_CLAIMS_PATH, project_name="warden")
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: False)
    assert cli.main(["success", "--repo-root", str(tmp_path), "publish", claim.id]) == 0
    out = capsys.readouterr().out
    assert "aborted" in out
    assert "published" not in out


def test_notice_author_without_operator_role_is_refused_exit_1(capsys, monkeypatch):
    """The Epic 10 write gate: auth is still checked (and refused) before
    any field prompting or writing -- a viewer-role caller never even
    reaches ``notices.author_notice``."""
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok")
    assert (
        cli.main(
            [
                "notice",
                "author",
                "--type",
                "deprecation",
                "--component",
                "weekly-update",
                "--what",
                "w",
                "--why",
                "w",
                "--migration",
                "m",
            ]
        )
        == 1
    )
    assert "unauthorized" in capsys.readouterr().err


def test_notice_author_with_operator_role_authors_a_draft(
    capsys, monkeypatch, tmp_path
):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: True)
    monkeypatch.chdir(tmp_path)
    assert (
        cli.main(
            [
                "notice",
                "author",
                "--type",
                "deprecation",
                "--component",
                "weekly-update",
                "--what",
                "w",
                "--why",
                "w",
                "--migration",
                "m",
                "--deadline",
                "2026-09-01",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "authored" in out
    assert "weekly-update" in out


def test_progress_read_only_never_checks_auth(capsys, monkeypatch, tmp_path):
    """AD-16: reads are public. A read command must succeed with no auth
    context at all -- proof the gate is not silently applied everywhere."""
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["progress"]) == 0
    assert "unauthorized" not in capsys.readouterr().err


def test_success_list_read_only_never_checks_auth(capsys):
    assert cli.main(["success"]) == 0


def test_notice_list_read_only_never_checks_auth(capsys):
    assert cli.main(["notice"]) == 0


# --- Story 6.5: help & usability -----------------------------------------


def test_progress_help_exits_0_and_documents_global_flags(capsys):
    assert cli.main(["progress", "--help"]) == 0
    out = capsys.readouterr().out
    assert "--json" in out
    assert "--date-range" in out
    assert "--station" in out


def test_success_help_exits_0(capsys):
    assert cli.main(["success", "--help"]) == 0


def test_notice_help_exits_0(capsys):
    assert cli.main(["notice", "--help"]) == 0


def test_success_publish_help_exits_0(capsys):
    assert cli.main(["success", "publish", "--help"]) == 0


def test_notice_author_help_exits_0(capsys):
    assert cli.main(["notice", "author", "--help"]) == 0


def test_unclear_flag_names_the_problem_and_suggests_help(capsys):
    assert cli.main(["progress", "--unknown"]) == 2
    err = capsys.readouterr().err
    assert "--unknown" in err
    assert "--help" in err


def test_top_level_epilog_has_copy_paste_examples(capsys):
    assert cli.main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "herald deck seed" in out
    assert "herald progress" in out
