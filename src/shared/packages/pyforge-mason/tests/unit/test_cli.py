"""Story 1.2 — the noun -> verb tree, global flags, and exit-code ownership."""

from __future__ import annotations

import pytest

from pyforge.mason import __version__
from pyforge.mason.cli import (
    EXIT_INTERNAL, EXIT_INTERRUPTED, EXIT_OK, EXIT_USAGE,
    _resolve_bool, _resolve_str, build_parser, main,
)


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


def test_doctor_invocation_stubs_and_succeeds(capsys):
    assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert "doctor" in out.err
    assert out.out == ""


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


def test_unexpected_exception_never_returns_bare_1(monkeypatch, capsys):
    """A crash must project to a documented code, not the interpreter default."""
    monkeypatch.setattr("pyforge.mason.cli.build_parser",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    rc = main([])
    assert rc == EXIT_INTERNAL
    assert rc != 1


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
