"""The feature-flag family: one fixture, both flag states (marshal Story 74.1, spec-feature-flag-governance CAP-4)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from openfeature import api
from openfeature.provider.in_memory_provider import InMemoryProvider

from pyforge.testing_kit import (
    CliResult,
    assert_flag_off_verb,
    flag_states,
    flagd_tree,
    installed_flags,
    invoke_cli,
    make_flag_provider_fixture,
)

# What a station does once in its conftest.py.
flag_provider = make_flag_provider_fixture()

_KEY = "pyforge.example.thing"
_USAGE = 64  # a station's own usage code; deliberately not argparse's 2
_REPO_ROOT = Path(__file__).resolve().parents[6]


def _resolve(key: str = _KEY, *, default: bool) -> bool:
    return api.get_client().get_boolean_value(key, default)


@pytest.fixture(scope="module", autouse=True)
def _baseline() -> object:
    """The default provider live before this module's first test."""
    return api.get_client().provider


# --- flag_states + the fixture (AC 1, AC 2) ------------------------------------------------------------------------


@flag_states(_KEY)
def test_the_key_resolves_on_then_off_through_the_client_api(request: pytest.FixtureRequest) -> None:
    state = request.node.callspec.id  # type: ignore[attr-defined]
    assert state in {"on", "off"}
    # The default is the opposite of the expected value, so a not-found fallback cannot pass for a hit.
    assert _resolve(default=(state == "off")) is (state == "on")


def test_flag_states_parametrizes_on_then_off_and_adds_the_fixture() -> None:
    @flag_states(_KEY)
    def probe() -> None: ...

    marks = {mark.name: mark for mark in probe.pytestmark}  # type: ignore[attr-defined]
    assert marks["parametrize"].args == ("flag_provider", [{_KEY: True}, {_KEY: False}])
    assert marks["parametrize"].kwargs == {"ids": ["on", "off"], "indirect": True}
    assert marks["usefixtures"].args == ("flag_provider",)


@flag_states(_KEY)
def test_a_decorated_test_can_read_its_state_from_the_fixture(flag_provider: dict[str, bool]) -> None:
    assert _resolve(default=not flag_provider[_KEY]) is flag_provider[_KEY]


@pytest.mark.parametrize("flag_provider", [{_KEY: True}], indirect=True)
def test_first_test_sets_the_key_on(flag_provider: dict[str, bool]) -> None:
    assert _resolve(default=False) is True
    assert isinstance(api.get_client().provider, InMemoryProvider)


def test_second_test_without_the_fixture_has_the_prior_provider_back(_baseline: object) -> None:
    assert api.get_client().provider is _baseline
    assert _resolve(default=False) is False  # the prior provider knows nothing of the key


def test_unparametrized_fixture_installs_an_empty_provider(flag_provider: dict[str, bool]) -> None:
    assert flag_provider == {}
    assert isinstance(api.get_client().provider, InMemoryProvider)
    assert _resolve(default=True) is True  # unknown key: the default comes back


def test_installed_flags_restores_the_prior_provider_even_when_the_body_raises(_baseline: object) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with installed_flags({_KEY: True}) as provider:
            assert api.get_client().provider is provider
            raise RuntimeError("boom")
    assert api.get_client().provider is _baseline


def test_nested_use_restores_the_provider_the_outer_block_set(_baseline: object) -> None:
    with installed_flags({_KEY: True}) as outer:
        with installed_flags({_KEY: False}) as inner:
            assert inner is not outer
            assert api.get_client().provider is inner
            assert _resolve(default=True) is False
        assert api.get_client().provider is outer
        assert _resolve(default=False) is True
    assert api.get_client().provider is _baseline


def test_installed_flags_refuses_a_value_that_is_not_a_bool(_baseline: object) -> None:
    with pytest.raises(ValueError, match="expected True"):
        with installed_flags({_KEY: "off"}):  # type: ignore[dict-item]
            pass
    assert api.get_client().provider is _baseline


# --- flagd_tree (AC 3) ---------------------------------------------------------------------------------------------


def test_flagd_tree_has_the_platform_trees_shape(tmp_path: Path) -> None:
    path = flagd_tree(tmp_path, {_KEY: "off"})
    assert path.parent == tmp_path
    entry = json.loads(path.read_text(encoding="utf-8"))["flags"][_KEY]
    assert entry["defaultVariant"] == "off"
    assert entry["variants"] == {"on": True, "off": False}
    assert entry["state"] == "ENABLED"

    platform = json.loads((_REPO_ROOT / "src/platform/config/flags.json").read_text(encoding="utf-8"))
    assert platform["flags"], "the platform tree carries no flag to compare the written shape against"
    # The platform flags also carry flagd `metadata` (steward Story 76.2's clock fields). Only a composed tree reads
    # it (`pyforge.core.flags.compose`, with a `flag-overlays.json` beside the tree), and a kit tree has no overlays.
    assert set(entry) == set(next(iter(platform["flags"].values()))) - {"metadata"}
    assert set(json.loads(path.read_text(encoding="utf-8"))) == set(platform)


def test_flagd_tree_writes_the_same_key_on_in_one_tree_and_off_in_the_other(tmp_path: Path) -> None:
    on = json.loads(flagd_tree(tmp_path, {_KEY: "on"}, name="on.json").read_text(encoding="utf-8"))
    off = json.loads(flagd_tree(tmp_path, {_KEY: "off"}, name="off.json").read_text(encoding="utf-8"))
    assert on["flags"][_KEY]["defaultVariant"] == "on"
    assert off["flags"][_KEY]["defaultVariant"] == "off"
    assert on["flags"][_KEY]["variants"] == off["flags"][_KEY]["variants"]


def test_flagd_tree_carries_every_key_it_is_given(tmp_path: Path) -> None:
    path = flagd_tree(tmp_path, {"a.b": "on", "c.d": "off"})
    flags = json.loads(path.read_text(encoding="utf-8"))["flags"]
    assert {key: flag["defaultVariant"] for key, flag in flags.items()} == {"a.b": "on", "c.d": "off"}


@pytest.mark.parametrize("bad", [[(_KEY, "on")], "on", None])
def test_flagd_tree_refuses_a_non_dict_mapping(tmp_path: Path, bad: object) -> None:
    with pytest.raises(ValueError, match="must be a dict"):
        flagd_tree(tmp_path, bad)  # type: ignore[arg-type]
    assert not (tmp_path / "flags.json").exists()


def test_flagd_tree_refuses_a_variant_the_tree_does_not_carry(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="variant must be 'on' or 'off'"):
        flagd_tree(tmp_path, {_KEY: "maybe"})
    assert not (tmp_path / "flags.json").exists()


# --- invoke_cli ----------------------------------------------------------------------------------------------------


def test_invoke_cli_takes_the_exit_code_from_the_return_value_and_captures_both_streams() -> None:
    def main(argv: list[str]) -> int:
        print("to stdout", argv)
        print("to stderr", file=sys.stderr)
        return 7

    result = invoke_cli(main, ("a", "b"))
    assert result == CliResult(exit_code=7, output="to stdout ['a', 'b']\nto stderr\n")


@pytest.mark.parametrize(
    ("raised", "code", "printed"),
    [(0, 0, ""), (3, 3, ""), (None, 0, ""), ("bad thing", 1, "bad thing\n")],
)
def test_invoke_cli_takes_the_exit_code_from_system_exit(raised: object, code: int, printed: str) -> None:
    def main(argv: list[str]) -> None:
        raise SystemExit(raised)

    assert invoke_cli(main, []) == CliResult(exit_code=code, output=printed)


def test_invoke_cli_reads_none_as_success_and_lets_other_exceptions_out() -> None:
    assert invoke_cli(lambda argv: None, []).exit_code == 0

    def crash(argv: list[str]) -> int:
        raise KeyError("nope")

    with pytest.raises(KeyError):
        invoke_cli(crash, [])


# --- assert_flag_off_verb (AC 4) -----------------------------------------------------------------------------------


def _fixture_cli(
    *, listed: bool = True, marked: bool = True, exits: int = _USAGE, wraps: bool = False
) -> Callable[[list[str]], int]:
    """A station CLI with one flag-gated verb, `thing`, whose flag is OFF."""

    def main(argv: list[str]) -> int:
        parser = argparse.ArgumentParser(prog="fixture")
        verbs = parser.add_subparsers(dest="verb")
        verbs.add_parser("run", help="an ordinary verb")
        if listed:
            help_text = "(disabled: flag off) the gated verb" if marked else "the gated verb"
            if wraps:
                help_text = "x" * 60 + " " + help_text  # pushes the marker onto a wrapped line
            verbs.add_parser("thing", help=help_text)
        args = parser.parse_args(argv)
        if args.verb == "thing":
            print("thing: flag off", file=sys.stderr)
            return exits
        return 0

    return main


def test_the_off_helper_passes_on_a_listed_disabled_verb_that_refuses_with_the_usage_code() -> None:
    result = assert_flag_off_verb(_fixture_cli(), "thing", _USAGE)
    assert result.exit_code == _USAGE
    assert "flag off" in result.output


def test_the_off_helper_finds_the_marker_on_a_wrapped_help_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "70")
    assert_flag_off_verb(_fixture_cli(wraps=True), "thing", _USAGE)


def test_the_off_helper_reads_a_coloured_help_the_same_as_a_plain_one(monkeypatch: pytest.MonkeyPatch) -> None:
    # argparse on Python 3.14 colours --help when either variable is set, even into a captured stream.
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("PYTHON_COLORS", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert "\x1b[" not in invoke_cli(_fixture_cli(), ["--help"]).output
    assert_flag_off_verb(_fixture_cli(), "thing", _USAGE)


def test_the_off_helper_fails_naming_a_verb_absent_from_help() -> None:
    with pytest.raises(AssertionError, match=r"verb 'thing' is absent from --help"):
        assert_flag_off_verb(_fixture_cli(listed=False), "thing", _USAGE)


def test_the_off_helper_fails_on_a_verb_listed_but_not_marked_disabled() -> None:
    with pytest.raises(AssertionError, match=r"verb 'thing' is listed in --help but not marked disabled"):
        assert_flag_off_verb(_fixture_cli(marked=False), "thing", _USAGE)


def test_the_off_helper_does_not_read_a_neighbours_marker_as_the_verbs_own() -> None:
    # `run` is an ordinary, enabled verb; `thing`'s "disabled" marker must not count for it.
    with pytest.raises(AssertionError, match=r"verb 'run' is listed in --help but not marked disabled"):
        assert_flag_off_verb(_fixture_cli(), "run", _USAGE)


def test_the_off_helper_fails_naming_the_exit_when_the_refusal_is_missing() -> None:
    with pytest.raises(AssertionError, match=r"exited 0; expected the station's usage code 64"):
        assert_flag_off_verb(_fixture_cli(exits=0), "thing", _USAGE)


def test_the_off_helper_fails_on_any_other_exit_code() -> None:
    with pytest.raises(AssertionError, match=r"exited 2; expected the station's usage code 64"):
        assert_flag_off_verb(_fixture_cli(exits=2), "thing", _USAGE)


def test_the_off_helper_passes_the_verbs_arguments_through() -> None:
    def main(argv: list[str]) -> int:
        if argv == ["--help"]:
            print("  thing  (disabled) the gated verb")
            return 0
        return _USAGE if argv == ["thing", "--flag", "x"] else 2

    assert assert_flag_off_verb(main, "thing", _USAGE, args=("--flag", "x")).exit_code == _USAGE
