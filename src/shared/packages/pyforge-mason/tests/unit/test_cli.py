"""Stories 1.2 + 1.3 + 1.4 — the noun -> verb tree, global flags, the
exit-code / MasonError projection in main(), and doctor's dual-output contract.

Story 1.3 (error taxonomy) was DEFERRED when 1.4 landed, so 1.4 was built
without it and this file carried only 1.2 + 1.4. 1.3 was recovered on
2026-07-31; the two touch main()'s error handling from opposite ends, so the
docstring names all three rather than whichever landed last.

Note the stream split 1.4 established and 1.3 must not undo: `doctor`'s stub
result flows through `render.write` to STDOUT (AD-8), while a MasonError and a
bare-noun usage error go to STDERR. The doctor tests below assert on stdout.
"""

from __future__ import annotations

import json

import pytest

from pyforge.mason import __version__
from pyforge.mason.cli import _resolve_bool, _resolve_str, build_parser, main
from pyforge.mason.errors import MasonError
from pyforge.mason.exit_codes import EXIT_FAILED, EXIT_INTERRUPTED, EXIT_OK, EXIT_USAGE


def test_version_is_reported(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_bare_invocation_prints_help_and_succeeds(capsys):
    """A true bare `mason` invocation is help output, not a diagnostic."""
    assert main([]) == EXIT_OK
    out = capsys.readouterr()
    assert "Mason" in out.out
    assert out.err == ""


def test_help_lists_the_whole_surface(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    out = capsys.readouterr().out
    for name in ("recipe", "package", "environment", "doctor"):
        assert name in out


@pytest.mark.parametrize("noun", ["recipe", "package", "environment"])
def test_bare_noun_is_a_usage_error(noun, capsys):
    """Amended contract (2026-07-30): a noun with no verb is a usage error —
    stderr, EXIT_USAGE — not the EXIT_OK/stdout stub Story 1.1 used."""
    assert main([noun]) == EXIT_USAGE
    out = capsys.readouterr()
    assert noun in out.err
    assert out.out == ""


def test_unrecognized_verb_is_a_native_argparse_usage_error(capsys):
    """`mason recipe sometypo` — argparse's own invalid-choice handling,
    unaffected by the bare-noun special case above; both land on the same
    stream and exit code."""
    assert main(["recipe", "sometypo"]) == EXIT_USAGE
    err = capsys.readouterr().err
    # The offending token must appear in the diagnostic — `err != ""` alone
    # would pass on any stderr noise without proving invalid-choice fired.
    assert "sometypo" in err


def test_doctor_invocation_stubs_and_succeeds(monkeypatch, capsys):
    """Story 1.4: the stub result now goes through `render.write` to
    stdout (AD-8) -- stderr carries no diagnostic for a successful run.
    Also confirms the default format is text, not JSON: `--format text` is
    the documented default, and the substring checks below would still
    pass on a JSON payload containing the same words, so the shape itself
    is asserted too."""
    # An ambient MASON_FORMAT=json would legitimately select JSON here --
    # this test asserts the no-flag/no-env default, so it must be hermetic.
    monkeypatch.delenv("MASON_FORMAT", raising=False)
    assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert "doctor" in out.out
    assert "not implemented yet" in out.out
    assert out.err == ""
    assert not out.out.lstrip().startswith("{")
    with pytest.raises(json.JSONDecodeError):
        json.loads(out.out)


def test_doctor_json_format_emits_the_envelope(capsys):
    assert main(["doctor", "--format", "json"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "doctor"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert "not implemented yet" in doc["data"]["message"]


def test_doctor_env_var_selects_json_format_without_the_flag(monkeypatch, capsys):
    monkeypatch.setenv("MASON_FORMAT", "json")
    assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert doc["command"] == "doctor"
    assert "not implemented yet" in doc["data"]["message"]


def test_doctor_invalid_env_format_falls_back_to_text(monkeypatch, capsys):
    """`--format`'s `choices=("text","json")` validates the flag, but
    `MASON_FORMAT` bypasses argparse entirely -- an out-of-choices value
    must fall back to the text default, not crash."""
    monkeypatch.setenv("MASON_FORMAT", "bogus")
    assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    assert not out.out.lstrip().startswith("{")
    assert "doctor" in out.out


def test_doctor_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["doctor", "--help"])
    assert exc.value.code == 0
    assert "doctor" in capsys.readouterr().out


def test_recipe_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "--help"])
    assert exc.value.code == 0
    assert "recipe" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [
    ["--format", "json", "recipe"],
    ["recipe", "--format", "json"],
])
def test_global_flag_parses_before_or_after_the_noun(argv):
    ns = build_parser().parse_args(argv)
    assert ns.format == "json"
    assert ns.noun == "recipe"


@pytest.mark.parametrize("flag,attr", [
    ("--cfe-root", "cfe_root"),
    ("--cfe-python", "cfe_python"),
])
def test_global_string_flags_accepted_at_either_position(flag, attr):
    before = build_parser().parse_args([flag, "/tmp/x", "package"])
    after = build_parser().parse_args(["package", flag, "/tmp/x"])
    assert before.noun == after.noun == "package"
    assert getattr(before, attr) == "/tmp/x"
    assert getattr(after, attr) == "/tmp/x"


@pytest.mark.parametrize("flag,attr", [
    ("--verbose", "verbose"),
    ("--quiet", "quiet"),
])
def test_global_boolean_flags_accepted_at_either_position(flag, attr):
    before = build_parser().parse_args([flag, "environment"])
    after = build_parser().parse_args(["environment", flag])
    assert before.noun == after.noun == "environment"
    assert getattr(before, attr) is True
    assert getattr(after, attr) is True


def test_keyboard_interrupt_projects_to_130(monkeypatch):
    monkeypatch.setattr("pyforge.mason.cli.build_parser",
                        lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert main([]) == EXIT_INTERRUPTED


def test_unanticipated_exception_projects_to_exit_failed_with_traceback(monkeypatch, capsys):
    """A crash must project to the documented EXIT_FAILED (AD-7), with the
    full traceback on stderr -- not the interpreter's bare default and not a
    silent failure."""
    monkeypatch.setattr("pyforge.mason.cli.build_parser",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    rc = main([])
    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "Traceback" in err
    assert "RuntimeError" in err
    assert "boom" in err


def test_mason_error_raised_in_main_prints_message_and_returns_exit_failed(monkeypatch, capsys):
    """A MasonError raised inside main()'s try block is an anticipated
    failure (AD-7): its `identifier: message` goes to stderr, no traceback,
    and the process exits EXIT_FAILED -- same monkeypatch pattern as the
    KeyboardInterrupt/RuntimeError cases above. No verb dispatch exists yet
    (later epics), so this proves the handler itself, not a dispatch path.
    The identifier is deliberately synthetic: pinning a real one like
    `cfe:unresolved` -> EXIT_FAILED would pre-break Story 1.7, which maps
    CFE-unavailable to EXIT_CFE_UNAVAILABLE (3)."""
    monkeypatch.setattr(
        "pyforge.mason.cli.build_parser",
        lambda: (_ for _ in ()).throw(
            MasonError("test:injected-failure", "synthetic anticipated failure")
        ),
    )
    rc = main([])
    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == "test:injected-failure: synthetic anticipated failure"
    assert "Traceback" not in err


# --- AD-13 precedence helpers, tested directly as pure functions -----------
#
# Nothing in main() consumes a resolved value this story (--format feeds
# render.py in Story 1.4, --cfe-root/--cfe-python feed the resolution chain
# in Stories 1.5-1.6, --verbose/--quiet feed logging in Story 1.10), so the
# precedence contract is proven against the helpers directly.

class TestResolveStr:
    def test_flag_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("MASON_FORMAT", "json")
        assert _resolve_str("text", "MASON_FORMAT", "text") == "text"

    def test_env_wins_over_default(self, monkeypatch):
        monkeypatch.setenv("MASON_FORMAT", "json")
        assert _resolve_str(None, "MASON_FORMAT", "text") == "json"

    def test_neither_set_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("MASON_FORMAT", raising=False)
        assert _resolve_str(None, "MASON_FORMAT", "text") == "text"

    def test_whitespace_only_env_value_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_ROOT", "   ")
        assert _resolve_str(None, "MASON_CFE_ROOT", "default-root") == "default-root"

    def test_whitespace_only_flag_value_falls_through_to_env(self, monkeypatch):
        monkeypatch.setenv("MASON_FORMAT", "json")
        assert _resolve_str("   ", "MASON_FORMAT", "text") == "json"

    def test_whitespace_only_flag_and_env_fall_back_to_default(self, monkeypatch):
        monkeypatch.setenv("MASON_FORMAT", "   ")
        assert _resolve_str("   ", "MASON_FORMAT", "text") == "text"

    def test_padded_flag_value_is_returned_stripped(self, monkeypatch):
        monkeypatch.delenv("MASON_CFE_ROOT", raising=False)
        assert _resolve_str("  /x  ", "MASON_CFE_ROOT", "d") == "/x"

    def test_padded_env_value_is_returned_stripped(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_ROOT", "  /x  ")
        assert _resolve_str(None, "MASON_CFE_ROOT", "d") == "/x"


class TestResolveBool:
    def test_flag_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("MASON_VERBOSE", "0")
        assert _resolve_bool(True, "MASON_VERBOSE", False) is True

    def test_env_wins_over_default(self, monkeypatch):
        monkeypatch.setenv("MASON_VERBOSE", "1")
        assert _resolve_bool(None, "MASON_VERBOSE", False) is True

    def test_neither_set_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("MASON_QUIET", raising=False)
        assert _resolve_bool(None, "MASON_QUIET", False) is False

    @pytest.mark.parametrize("raw", ["", "0", "false", "FALSE", "no", "No", "  false  "])
    def test_falsy_env_spellings(self, raw, monkeypatch):
        monkeypatch.setenv("MASON_QUIET", raw)
        assert _resolve_bool(None, "MASON_QUIET", True) is False

    @pytest.mark.parametrize("raw", ["1", "true", "yes"])
    def test_truthy_env_spellings(self, raw, monkeypatch):
        monkeypatch.setenv("MASON_VERBOSE", raw)
        assert _resolve_bool(None, "MASON_VERBOSE", False) is True
