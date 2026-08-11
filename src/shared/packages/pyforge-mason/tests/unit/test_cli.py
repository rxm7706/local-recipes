"""Stories 1.2 + 1.3 + 1.4 — the noun -> verb tree, global flags, the
exit-code / MasonError projection in main(), and doctor's dual-output contract.

Story 1.3 (error taxonomy) was DEFERRED when 1.4 landed, so 1.4 was built
without it and this file carried only 1.2 + 1.4. 1.3 was recovered on
2026-07-31; the two touch main()'s error handling from opposite ends, so the
docstring names all three rather than whichever landed last.

Note the stream split 1.4 established and 1.3 must not undo: `doctor`'s
result flows through `render.write` to STDOUT (AD-8), while a MasonError and a
bare-noun usage error go to STDERR. The doctor tests below assert on stdout.

Story 1.7 extends this file with `CfeUnresolvedError`'s dedicated
EXIT_CFE_UNAVAILABLE branch in main(); the pre-existing
`test_mason_error_raised_in_main_prints_message_and_returns_exit_failed`
already proves the generic MasonError -> EXIT_FAILED path is unchanged, so
no separate regression test was needed for it (review pass, 2026-08-09).

Story 1.8 replaces the four Story-1.4-era doctor tests that asserted on the
placeholder `"not implemented yet"` stub with real-report assertions:
`doctor.build_report` is mocked (`patch("pyforge.mason.cli.doctor.
build_report", ...)`) to return a fixed `DoctorReport` -- `cli.py` calls it
through the `doctor` module object (`doctor.build_report(...)`, not an
imported bare name), so patching the function on its owning module reaches
the call site with no gotcha, unlike `doctor.py`'s own patch targets (see
`test_doctor.py`'s module docstring).
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.mason import __version__
from pyforge.mason.cli import (
    _ENV_CFE_PYTHON, _ENV_CFE_ROOT, _ENV_CFE_TIMEOUT, _ENV_FORMAT, _ENV_QUIET,
    _ENV_VERBOSE, _configure_logging, _resolve_bool, _resolve_optional_float,
    _resolve_str, build_parser, main,
)
from pyforge.mason.doctor import DoctorReport
from pyforge.mason.engines import EngineStatus
from pyforge.mason.errors import CfeUnresolvedError, MasonError
from pyforge.mason.exit_codes import (
    EXIT_CFE_UNAVAILABLE, EXIT_FAILED, EXIT_INTERRUPTED, EXIT_OK, EXIT_USAGE,
)

_FIXED_REPORT = DoctorReport(
    mason_version="1.2.3+test",
    cfe_root=None,
    cfe_root_step="not-found",
    cfe_interpreter="/fake/python",
    cfe_interpreter_step="running-interpreter",
    cfe_import_floor_satisfied=False,
    cfe_import_floor_missing=("pyyaml", "requests"),
    unavailable_verbs=("recipe",),
    engines=(
        EngineStatus(name="pixi", available=True, version="pixi 0.72.2"),
        EngineStatus(name="twine", available=False, version=None),
    ),
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


def test_doctor_text_mode_reports_real_report_fields(monkeypatch, capsys):
    """Story 1.8: the stub result is gone -- `doctor`'s output now reflects
    `doctor.build_report`'s actual `DoctorReport`, rendered through
    `render.write` to stdout (AD-8). Also confirms the default format is
    text, not JSON."""
    # An ambient MASON_FORMAT=json would legitimately select JSON here --
    # this test asserts the no-flag/no-env default, so it must be hermetic.
    monkeypatch.delenv("MASON_FORMAT", raising=False)
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    assert "doctor: ok" in out.out
    assert "mason_version: 1.2.3+test" in out.out
    assert "cfe_root_step: not-found" in out.out
    assert "unavailable_verbs: ('recipe',)" in out.out
    assert not out.out.lstrip().startswith("{")
    with pytest.raises(json.JSONDecodeError):
        json.loads(out.out)


def _json_roundtripped(report: DoctorReport) -> dict:
    """`dataclasses.asdict` keeps tuples as tuples; JSON has no tuple type,
    so a round-trip through `json.dumps`/`json.loads` is what an actual
    `data` payload looks like after `render_json` serializes it (tuples ->
    lists) -- the shape this helper produces is what the assertions below
    compare `doc["data"]` against, not the raw `asdict()` result."""
    return json.loads(json.dumps(dataclasses.asdict(report)))


def test_doctor_json_mode_data_matches_dataclasses_asdict_of_the_report(capsys):
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor", "--format", "json"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "doctor"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == _json_roundtripped(_FIXED_REPORT)


def test_doctor_env_var_selects_json_format_without_the_flag(monkeypatch, capsys):
    monkeypatch.setenv("MASON_FORMAT", "json")
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert doc["command"] == "doctor"
    assert doc["data"] == _json_roundtripped(_FIXED_REPORT)


def test_doctor_status_stays_ok_and_errors_empty_regardless_of_cfe_or_engine_gaps(capsys):
    """`_FIXED_REPORT` already names an unresolved CFE root, a missing
    import floor, and an absent engine -- `doctor` must still report
    `status == "ok"`/`errors == []` and exit 0 (FR-34, AD-6): the gap is
    data in the report, never a failure of the `doctor` command itself."""
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor", "--format", "json"]) == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"]["unavailable_verbs"] == ["recipe"]


def test_doctor_invalid_env_format_falls_back_to_text(monkeypatch, capsys):
    """`--format`'s `choices=("text","json")` validates the flag, but
    `MASON_FORMAT` bypasses argparse entirely -- an out-of-choices value
    must fall back to the text default, not crash."""
    monkeypatch.setenv("MASON_FORMAT", "bogus")
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    assert not out.out.lstrip().startswith("{")
    assert "doctor: ok" in out.out


def test_doctor_calls_build_report_with_flags_environ_and_cwd():
    """`cli.py` must pass the `--cfe-root`/`--cfe-python` flags through
    unresolved (`doctor.build_report` does its own resolution), plus the
    real `os.environ` and `Path.cwd()` -- proven by inspecting the call
    rather than the rendered output.

    Review pass (2026-08-09): both flags are exercised together here (the
    original version of this test only ever passed `--cfe-root`, so
    `--cfe-python`'s own pass-through path was unproven), and `args[2]` is
    now actually asserted against `os.environ` -- this test's own docstring
    already claimed that, but the assertion was missing."""
    with patch(
        "pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT
    ) as mock_build_report:
        assert main([
            "doctor", "--cfe-root", "/explicit/root", "--cfe-python", "/explicit/python",
        ]) == EXIT_OK

    mock_build_report.assert_called_once()
    args = mock_build_report.call_args.args
    assert args[0] == "/explicit/root"
    assert args[1] == "/explicit/python"
    assert args[2] is os.environ
    assert args[3] == Path.cwd()


def test_doctor_calls_build_report_with_cfe_python_unresolved_when_absent():
    """Symmetric with the flags-given case above: when `--cfe-python` is
    never supplied, `cli.py` must pass `None` through -- `doctor.build_report`
    does its own flag -> environment -> running-interpreter resolution."""
    with patch(
        "pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT
    ) as mock_build_report:
        assert main(["doctor", "--cfe-root", "/explicit/root"]) == EXIT_OK

    args = mock_build_report.call_args.args
    assert args[0] == "/explicit/root"
    assert args[1] is None


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


def test_cfe_timeout_flag_accepted_at_either_position_and_parses_as_float():
    before = build_parser().parse_args(["--cfe-timeout", "30", "package"])
    after = build_parser().parse_args(["package", "--cfe-timeout", "30"])
    assert before.noun == after.noun == "package"
    assert before.cfe_timeout == after.cfe_timeout == 30.0
    assert isinstance(before.cfe_timeout, float)
    assert isinstance(after.cfe_timeout, float)


def test_cfe_timeout_flag_rejects_a_non_numeric_value(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--cfe-timeout", "not-a-number"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--cfe-timeout" in err
    # Review pass (2026-08-10): letting float()'s bare ValueError escape
    # made argparse name the private `type=` callable instead of the flag --
    # "invalid _parse_finite_float value: 'not-a-number'". The message a
    # user sees must not leak a helper's identifier.
    assert "_parse_finite_float" not in err
    assert "must be a number of seconds" in err


@pytest.mark.parametrize("bad_value", ["nan", "inf", "Infinity"])
def test_cfe_timeout_flag_rejects_nan_and_infinite_values(bad_value, capsys):
    """Review pass (2026-08-09): `float()` parses `nan`/`inf`/`-inf` as
    well-formed, but neither is a usable subprocess timeout -- `nan` never
    compares as expired, `inf` never expires at all. Must be rejected the
    same way a non-numeric value is.

    `-inf` is deliberately excluded from this parametrize list -- see
    `test_cfe_timeout_flag_rejects_negative_infinity_via_equals_form` below,
    which exercises it correctly."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--cfe-timeout", bad_value])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--cfe-timeout" in err
    # Asserted on the validator's own wording, not just exit code 2 + the
    # flag name (review pass, 2026-08-10, second): that weaker pair is
    # exactly what let the `-inf` case pass while argparse -- not
    # `_parse_finite_float` -- was doing the rejecting.
    assert "must be a finite, positive number" in err


def test_cfe_timeout_flag_rejects_negative_infinity_via_equals_form(capsys):
    """`-inf` as a separate argv token looks like another option string to
    argparse's own parser (leading `-`), so `--cfe-timeout -inf` is rejected
    by argparse's own "expected one argument" error *before*
    `_parse_finite_float` ever runs -- both forms exit 2 with `--cfe-timeout`
    in the message, so a naive two-token test for `-inf` passes without
    actually proving the isfinite guard rejects it (edge-case-hunter
    finding, review pass 2026-08-10). The `--cfe-timeout=-inf` single-token
    form bypasses that ambiguity and genuinely reaches the custom
    validator."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--cfe-timeout=-inf"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--cfe-timeout" in err
    # The whole point of the equals form: prove `_parse_finite_float` did the
    # rejecting, not argparse's own "expected one argument".
    assert "must be a finite, positive number" in err


@pytest.mark.parametrize("bad_value", ["0", "-1", "-0.5"])
def test_cfe_timeout_flag_rejects_non_positive_values(bad_value, capsys):
    """Review pass (2026-08-10): zero and negative timeouts are equally
    unusable as nan/inf, just via the opposite failure mode -- they expire
    before the delegated operation has any chance to run.

    `-1`/`-0.5` reach the validator rather than being read as option strings
    because argparse treats a leading-`-` token as a negative number when the
    parser has no option that looks like one; the wording assertion below
    pins that, instead of accepting any exit-2 path (review pass,
    2026-08-10, second)."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--cfe-timeout", bad_value])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--cfe-timeout" in err
    assert "must be a finite, positive number" in err


def test_all_six_v1_knobs_have_both_a_flag_and_an_environment_form(monkeypatch):
    """AD-13/FR-48: the v1 knob set is closed and fully enumerated -- each of
    the six has both a flag and an environment-variable form, and each
    resolves flag -> environment -> default. One test, all six (the spec's
    own AC wording).

    The three resolution assertions per knob were added in the 2026-08-10
    (third) review pass. This test previously only checked that six flag
    names and six variable names appear in `format_help()` -- which would
    still pass with `_resolve_optional_float` deleted outright, and asserts
    nothing whatsoever about the precedence the AC actually names. Each
    knob's environment value is chosen so no sub-assertion is vacuous: the
    flag-wins case uses an environment value that would produce a *different*
    answer if the flag were ignored, and the environment case uses one that
    differs from the default.
    """
    knobs = (
        {
            "flag": "--cfe-root", "env_var": _ENV_CFE_ROOT, "dest": "cfe_root",
            "argv": ["--cfe-root", "/from/flag"], "flag_wins": "/from/flag",
            "env_raw": "/from/env", "env_wins": "/from/env", "default": "auto",
            "resolve": lambda v: _resolve_str(v, _ENV_CFE_ROOT, "auto"),
        },
        {
            "flag": "--cfe-python", "env_var": _ENV_CFE_PYTHON, "dest": "cfe_python",
            "argv": ["--cfe-python", "/from/flag/python"], "flag_wins": "/from/flag/python",
            "env_raw": "/from/env/python", "env_wins": "/from/env/python", "default": "auto",
            "resolve": lambda v: _resolve_str(v, _ENV_CFE_PYTHON, "auto"),
        },
        {
            "flag": "--cfe-timeout", "env_var": _ENV_CFE_TIMEOUT, "dest": "cfe_timeout",
            "argv": ["--cfe-timeout", "30"], "flag_wins": 30.0,
            "env_raw": "45", "env_wins": 45.0, "default": None,
            "resolve": lambda v: _resolve_optional_float(v, _ENV_CFE_TIMEOUT),
        },
        {
            # --format's default is one of its own two choices, so the flag
            # form deliberately asks for the default value while the
            # environment asks for the other one: if the flag were ignored,
            # the flag-wins case would come back "json".
            "flag": "--format", "env_var": _ENV_FORMAT, "dest": "format",
            "argv": ["--format", "text"], "flag_wins": "text",
            "env_raw": "json", "env_wins": "json", "default": "text",
            "resolve": lambda v: _resolve_str(v, _ENV_FORMAT, "text"),
        },
        {
            # Same shape for the two booleans, whose default is also one of
            # only two possible values: the flag-wins case pairs `--verbose`
            # with a falsy environment value, the environment case with a
            # truthy one.
            "flag": "--verbose", "env_var": _ENV_VERBOSE, "dest": "verbose",
            "argv": ["--verbose"], "flag_wins": True,
            "env_raw": "1", "env_wins": True, "default": False,
            "conflict_env_raw": "0",
            "resolve": lambda v: _resolve_bool(v, _ENV_VERBOSE, False),
        },
        {
            "flag": "--quiet", "env_var": _ENV_QUIET, "dest": "quiet",
            "argv": ["--quiet"], "flag_wins": True,
            "env_raw": "1", "env_wins": True, "default": False,
            "conflict_env_raw": "0",
            "resolve": lambda v: _resolve_bool(v, _ENV_QUIET, False),
        },
    )
    assert len(knobs) == 6, "AD-13's v1 knob set is closed at six"

    help_text = build_parser().format_help()
    for knob in knobs:
        flag, env_var, dest, resolve = knob["flag"], knob["env_var"], knob["dest"], knob["resolve"]
        assert flag in help_text, f"{flag} missing from --help output"
        assert env_var in help_text, f"{env_var} missing from --help output"

        # 1. Flag beats a conflicting environment value.
        monkeypatch.setenv(env_var, knob.get("conflict_env_raw", knob["env_raw"]))
        ns = build_parser().parse_args(knob["argv"])
        assert resolve(getattr(ns, dest, None)) == knob["flag_wins"], f"{flag}: flag must win"

        # 2. Environment is read when the flag is absent.
        monkeypatch.setenv(env_var, knob["env_raw"])
        ns = build_parser().parse_args([])
        assert resolve(getattr(ns, dest, None)) == knob["env_wins"], f"{env_var}: env must apply"

        # 3. Default when neither is given.
        monkeypatch.delenv(env_var)
        ns = build_parser().parse_args([])
        assert resolve(getattr(ns, dest, None)) == knob["default"], f"{flag}: default must apply"


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


# --- Story 1.7: CfeUnresolvedError degrades to EXIT_CFE_UNAVAILABLE --------

def test_cfe_unresolved_error_raised_in_main_returns_exit_cfe_unavailable(monkeypatch, capsys):
    """A `CfeUnresolvedError` raised inside main()'s try block must be caught
    by its own branch -- listed before `except MasonError`, since it is a
    subclass -- and mapped to EXIT_CFE_UNAVAILABLE (3), not the generic
    EXIT_FAILED the MasonError branch below it produces. Same monkeypatch
    pattern as the synthetic-MasonError test above; no `recipe` verb exists
    yet to dispatch through, so this proves the handler itself (spec
    Acceptance Criteria)."""
    monkeypatch.setattr(
        "pyforge.mason.cli.build_parser",
        lambda: (_ for _ in ()).throw(CfeUnresolvedError()),
    )
    rc = main([])
    assert rc == EXIT_CFE_UNAVAILABLE
    err = capsys.readouterr().err
    assert err.strip() == str(CfeUnresolvedError())
    assert "Traceback" not in err
    for step_name in ("flag", "environment", "cwd-walk", "not-found"):
        assert step_name in err


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


class TestResolveOptionalFloat:
    """`_resolve_optional_float` has no Mason-wide `default` parameter --
    unlike `_resolve_str`/`_resolve_bool` above, its terminal fallback is
    always `None` (spec Intent: FR-4's "per-operation default" lives at a
    future call site, not in this resolver)."""

    def test_flag_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "99")
        assert _resolve_optional_float(30.0, "MASON_CFE_TIMEOUT") == 30.0

    def test_small_fractional_flag_value_still_wins_over_env(self, monkeypatch):
        """Not a truthiness check -- an unusual but *usable* timeout must
        still win over the environment."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(0.001, "MASON_CFE_TIMEOUT") == 0.001

    @pytest.mark.parametrize(
        "unusable", [0.0, -5.0, float("nan"), float("inf"), float("-inf")],
    )
    def test_unusable_flag_value_falls_through_to_env(self, monkeypatch, unusable):
        """Review pass (2026-08-10): this resolver used to validate only its
        environment half, so `nan`/`inf`/`0`/negative passed straight
        through from the flag parameter -- handing a caller exactly the
        value `_parse_finite_float` and `cfe.run_streamed` both reject. A
        flag value that fails the same finite-and-positive test is treated
        as "absent at the step that supplied it" and resolution falls
        through to the environment, mirroring `_resolve_str`'s handling of a
        whitespace-only flag value."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(unusable, "MASON_CFE_TIMEOUT") == 45.0

    @pytest.mark.parametrize(
        "unusable", [0.0, -5.0, float("nan"), float("inf"), float("-inf")],
    )
    def test_unusable_flag_value_with_no_env_resolves_to_none(self, monkeypatch, unusable):
        """...and with nothing to fall through to, the resolver returns
        `None` -- never a value its own siblings reject as unusable."""
        monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
        assert _resolve_optional_float(unusable, "MASON_CFE_TIMEOUT") is None

    @pytest.mark.parametrize("unusable", [True, False])
    def test_bool_flag_value_falls_through_to_env(self, monkeypatch, unusable):
        """`bool` is a subclass of `int`, so `True` cleared both the
        `isfinite` and `> 0` checks and was returned verbatim -- and
        `cfe.run_streamed` rejects a bool `timeout` outright, so the resolver
        was still handing out a value its documented consumer refuses
        (review pass, 2026-08-10, second). Treated as unusable, like every
        other value that fails the same standard."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(unusable, "MASON_CFE_TIMEOUT") == 45.0

    @pytest.mark.parametrize("not_a_number", ["30", "", Decimal("30"), object()])
    def test_non_numeric_flag_value_falls_through_instead_of_raising(
        self, monkeypatch, not_a_number,
    ):
        """A flag value that is not a real number at all reached
        `math.isfinite` and raised its bare "must be real number, not str" --
        naming neither this function nor the parameter (review pass,
        2026-08-10, third). `cfe.run_streamed`'s `timeout` guard was given an
        isinstance check for exactly this message; its sibling resolver was
        left without one. Treated as unusable and fallen through, like every
        other value that fails this resolver's standard -- this function is
        documented as never raising."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(not_a_number, "MASON_CFE_TIMEOUT") == 45.0

    def test_non_numeric_flag_value_with_no_env_resolves_to_none(self, monkeypatch):
        monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
        assert _resolve_optional_float("30", "MASON_CFE_TIMEOUT") is None

    def test_env_wins_over_none_default(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") == 45.0

    def test_padded_env_value_is_parsed_after_stripping(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "  12.5  ")
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") == 12.5

    def test_neither_set_falls_back_to_none(self, monkeypatch):
        monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None

    def test_malformed_env_value_falls_back_to_none(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "not-a-number")
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None

    def test_whitespace_only_env_value_falls_back_to_none(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "   ")
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None

    @pytest.mark.parametrize("raw", ["nan", "inf", "-inf", "Infinity"])
    def test_non_finite_env_value_falls_back_to_none(self, raw, monkeypatch):
        """Review pass (2026-08-09): `float()` parses these as well-formed,
        but a `nan`/`inf` timeout is unusable -- must degrade to `None`
        exactly like a genuinely malformed value, mirroring
        `_parse_finite_float`'s flag-side guard."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", raw)
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None

    @pytest.mark.parametrize("raw", ["0", "-1", "-0.5"])
    def test_non_positive_env_value_falls_back_to_none(self, raw, monkeypatch):
        """Review pass (2026-08-10): zero and negative timeouts are equally
        unusable as nan/inf -- must degrade to `None` the same way,
        mirroring `_parse_finite_float`'s flag-side guard."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", raw)
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None


# --- Story 1.10: `_configure_logging` -- verbosity -> root logger level, ---
# ------------------------------------- always stderr, never stdout --------

class TestConfigureLogging:
    def test_default_level_is_warning_and_info_is_swallowed(self, capsys):
        _configure_logging(verbose=False, quiet=False)
        assert logging.getLogger().getEffectiveLevel() == logging.WARNING
        logger = logging.getLogger("pyforge.mason.test.default")
        logger.info("swallowed-info")
        logger.warning("shown-warning")
        out = capsys.readouterr()
        assert out.out == ""
        assert "swallowed-info" not in out.err
        assert "shown-warning" in out.err

    def test_verbose_sets_level_info(self, capsys):
        _configure_logging(verbose=True, quiet=False)
        assert logging.getLogger().getEffectiveLevel() == logging.INFO
        logger = logging.getLogger("pyforge.mason.test.verbose")
        logger.info("shown-info")
        out = capsys.readouterr()
        assert out.out == ""
        assert "shown-info" in out.err

    def test_quiet_sets_level_error(self, capsys):
        _configure_logging(verbose=False, quiet=True)
        assert logging.getLogger().getEffectiveLevel() == logging.ERROR
        logger = logging.getLogger("pyforge.mason.test.quiet")
        logger.warning("swallowed-warning")
        logger.error("shown-error")
        out = capsys.readouterr()
        assert out.out == ""
        assert "swallowed-warning" not in out.err
        assert "shown-error" in out.err

    def test_quiet_wins_when_both_verbose_and_quiet_are_given(self, capsys):
        """Documented tie-break (spec Boundaries & Constraints): the ACs
        don't specify one, so `--quiet` (the more conservative choice) wins."""
        _configure_logging(verbose=True, quiet=True)
        assert logging.getLogger().getEffectiveLevel() == logging.ERROR


def test_quiet_env_var_beats_an_explicit_verbose_flag(monkeypatch):
    """Review pass (2026-08-10): the tie-break is applied to the two
    *resolved* values, after each knob independently ran AD-13's
    flag -> environment -> default chain -- so a stale `MASON_QUIET=1` in a
    shell profile silently mutes an explicit `--verbose` run. This follows
    from AD-13's per-knob precedence rather than contradicting it, but it is
    surprising, so it is pinned here rather than left to be rediscovered."""
    monkeypatch.setenv("MASON_QUIET", "1")
    monkeypatch.delenv("MASON_VERBOSE", raising=False)
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor", "--verbose"]) == EXIT_OK
    assert logging.getLogger().getEffectiveLevel() == logging.ERROR


def test_env_var_value_never_appears_in_captured_stderr_log_output(monkeypatch, capsys):
    """Regression guard for the spec's env-value-leak row: a distinctive
    marker set via a resolved env var must never appear in stderr (the log
    stream), even at --verbose. `doctor.build_report` is mocked to a fixed
    report (existing doctor-test pattern) -- its own stdout report may
    legitimately echo a resolved value; only the log stream is constrained."""
    marker = "MASON-ENV-LEAK-MARKER-3f9a7c"
    monkeypatch.setenv("MASON_CFE_ROOT", marker)
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor", "--verbose"]) == EXIT_OK
    err = capsys.readouterr().err
    assert marker not in err


# --- Story 2.3: credential isolation (AD-14) --------------------------------


@pytest.mark.parametrize(
    "flags",
    [[], ["--quiet"], ["--verbose"], ["--format", "json"], ["--verbose", "--format", "json"]],
    ids=["default", "quiet", "verbose", "json", "verbose-json"],
)
def test_jfrog_credential_sentinel_never_appears_in_doctor_output(monkeypatch, capsys, tmp_path, flags):
    """AD-14: a JFROG_* credential must never surface in `mason doctor`'s
    output at ANY verbosity (review pass, Edge Case Hunter: the original
    version only exercised --verbose despite this exact claim) or in EITHER
    output format (third review pass, Blind Hunter: `--format json` is the
    documented machine-consumed contract surface and `render_json` was never
    exercised with the sentinel set -- latent only because `render_text`
    happens to print the same `data` keys today).

    `doctor.build_report` is deliberately NOT mocked (follow-up review, both
    reviewers, reproduced): it is the only function in the `doctor` path
    that receives `os.environ` at all, so patching it made this test's own
    claim -- that the *report* never echoes the ambient environment --
    structurally unreachable. With the mock in place, a `build_report` that
    folded `environ` into the report printed `JFROG_API_KEY=<sentinel>` to
    stdout while all three parametrized cases still passed.

    Hermeticity follows `test_doctor.py::
    test_build_report_never_raises_against_a_real_unresolved_environment`'s
    established pattern (AD-16): `PATH` points at an empty directory so every
    engine probe reliably reports absent, and the CFE-root walk starts from
    an empty `tmp_path`, while `resolve.py`'s chains and `cfe.py`'s real
    subprocess probe stay genuinely unmocked. The `MASON_*` deletes are that
    hermeticity, not case separation: a stale `MASON_CFE_ROOT`/`MASON_FORMAT`
    in the runner's shell would change what is rendered (fourth review pass,
    Blind Hunter -- the earlier claim that they "keep the three verbosity
    cases from collapsing into one" was false in both directions; see
    below).

    The three verbosity ids exercise ONE render path today, deliberately and
    knowingly (fourth review pass, both reviewers, reproduced): `--quiet`
    and `--verbose` reach only `_configure_logging`, `render.py` has no
    verbosity branch at all, and nothing in the package emits a log record
    yet (`conftest.py`'s own docstring), so all three produce byte-identical
    output. They are kept as forward coverage for the AC's "at ANY
    verbosity" -- the moment a verbosity-conditional render path lands, this
    test covers it without being rewritten -- while the `format` axis is the
    one that genuinely differs today. The pre-existing
    `test_env_var_value_never_appears_in_captured_stderr_log_output` above
    owns the log-stream surface.

    The POSITIVE control is what keeps the sentinel assertions from passing
    vacuously: an absence assertion over empty output proves nothing, so the
    report must first be shown to have actually rendered."""
    for name in ("MASON_QUIET", "MASON_VERBOSE", "MASON_FORMAT", "MASON_CFE_ROOT",
                 "MASON_CFE_PYTHON"):
        monkeypatch.delenv(name, raising=False)
    empty_path_dir = tmp_path / "empty-path"
    empty_path_dir.mkdir()
    monkeypatch.setenv("PATH", str(empty_path_dir))
    monkeypatch.chdir(tmp_path)

    sentinel = "JFROG-SENTINEL-9f3e7a1c"
    monkeypatch.setenv("JFROG_API_KEY", sentinel)

    assert main(["doctor", *flags]) == EXIT_OK

    out = capsys.readouterr()
    # Positive control first: `mason_version` is a `DoctorReport` field that
    # both renderers emit (`render_text` prints one line per `data` key,
    # `render_json` puts the same keys in the envelope's `data`), so this
    # fails the moment the report stops reaching stdout -- without it, the
    # two absence assertions below would pass just as happily against empty
    # output (fourth review pass, both reviewers).
    assert "mason_version" in out.out
    assert sentinel not in out.out
    assert sentinel not in out.err
