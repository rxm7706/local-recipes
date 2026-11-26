"""``pyforge.core.cli_output`` gives a parser that accepts one JSON spelling the other (steward Story 144.1)."""

from __future__ import annotations

import argparse

import pytest

from pyforge.core.cli_output import align_json_options, iter_parsers, json_spellings, json_twins


def _tree() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="demo")
    sub = parser.add_subparsers(dest="verb")
    flag = sub.add_parser("flag")
    flag.add_argument("--json", action="store_true", dest="as_json")
    fmt = sub.add_parser("fmt")
    fmt.add_argument("--format", choices=("text", "json"), default="text", dest="fmt")
    both = sub.add_parser("both")
    both.add_argument("--json", action="store_true")
    both.add_argument("--format", choices=("text", "json"), default="text")
    other = sub.add_parser("other")
    other.add_argument("--format", choices=("markdown", "csv", "json"), default="markdown")
    sub.add_parser("neither")
    return parser


def test_a_flag_parser_gains_format_writing_the_flags_destination() -> None:
    parser = _tree()
    assert align_json_options(parser) == 2
    assert parser.parse_args(["flag", "--format", "json"]).as_json is True
    assert parser.parse_args(["flag", "--format", "text"]).as_json is False
    assert parser.parse_args(["flag", "--json"]).as_json is True
    assert parser.parse_args(["flag"]).as_json is False


def test_a_format_parser_gains_json_writing_the_formats_destination() -> None:
    parser = _tree()
    align_json_options(parser)
    assert parser.parse_args(["fmt", "--json"]).fmt == "json"
    assert parser.parse_args(["fmt", "--format", "json"]).fmt == "json"
    assert parser.parse_args(["fmt"]).fmt == "text"


def test_the_last_spelling_given_wins() -> None:
    parser = _tree()
    align_json_options(parser)
    assert parser.parse_args(["flag", "--json", "--format", "text"]).as_json is False
    assert parser.parse_args(["fmt", "--format", "text", "--json"]).fmt == "json"


def test_a_parser_with_both_another_format_or_neither_is_left_alone() -> None:
    parser = _tree()
    before = {p.prog: [a.option_strings for a in p._actions] for p in iter_parsers(parser)}
    align_json_options(parser)
    after = {p.prog: [a.option_strings for a in p._actions] for p in iter_parsers(parser)}
    for prog in ("demo both", "demo other", "demo neither", "demo"):
        assert after[prog] == before[prog], prog
    with pytest.raises(SystemExit):
        parser.parse_args(["other", "--json"])


def test_aligning_twice_adds_nothing() -> None:
    parser = _tree()
    align_json_options(parser)
    assert align_json_options(parser) == 0


def test_json_spellings_reads_what_one_parser_accepts() -> None:
    parser = _tree()
    by_prog = {p.prog: json_spellings(p) for p in iter_parsers(parser)}
    assert by_prog["demo flag"] == {"--json"}
    assert by_prog["demo fmt"] == {"--format"}
    assert by_prog["demo other"] == frozenset()
    align_json_options(parser)
    assert json_spellings(next(p for p in iter_parsers(parser) if p.prog == "demo flag")) == {"--json", "--format"}


def test_a_json_option_that_is_not_a_plain_flag_gets_no_twin() -> None:
    parser = argparse.ArgumentParser(prog="demo")
    parser.add_argument("--json", metavar="PATH")
    assert align_json_options(parser) == 0


def test_a_twin_is_matched_only_in_full_so_no_abbreviation_turns_ambiguous() -> None:
    """``--f`` meant ``--fleet`` and ``--j`` meant ``--justification`` before the twins existed, and still do; a twin
    itself needs its full spelling."""
    flagged = argparse.ArgumentParser(prog="demo")
    flagged.add_argument("--fleet", action="store_true")
    flagged.add_argument("--json", action="store_true")
    before = flagged.parse_args(["--f"])
    align_json_options(flagged)
    assert flagged.parse_args(["--f"]) == before
    assert flagged.parse_args(["--format", "json"]).json is True
    assert flagged.parse_args(["--format=json"]).json is True
    with pytest.raises(SystemExit):
        flagged.parse_args(["--form", "json"])

    formatted = argparse.ArgumentParser(prog="demo")
    formatted.add_argument("--justification")
    formatted.add_argument("--format", choices=("text", "json"), default="text")
    before = formatted.parse_args(["--j", "why"])
    align_json_options(formatted)
    assert formatted.parse_args(["--j", "why"]) == before
    assert formatted.parse_args(["--json"]).format == "json"


def test_a_twin_does_not_replace_a_default_an_outer_parser_already_set() -> None:
    """A global option repeated on a subparser: the subparser's twin must not reset what the root parsed."""
    root = argparse.ArgumentParser(prog="demo")
    root.add_argument("--format", choices=("text", "json"), default=argparse.SUPPRESS, dest="fmt")
    verb = root.add_subparsers(dest="verb").add_parser("build")
    verb.add_argument("--format", choices=("text", "json"), default=argparse.SUPPRESS, dest="fmt")
    align_json_options(root)
    assert root.parse_args(["--format", "json", "build"]).fmt == "json"
    assert root.parse_args(["--json", "build"]).fmt == "json"
    assert root.parse_args(["build", "--json"]).fmt == "json"
    assert not hasattr(root.parse_args(["build"]), "fmt")


def test_choices_in_the_other_order_still_get_a_twin() -> None:
    parser = argparse.ArgumentParser(prog="demo")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    assert align_json_options(parser) == 1
    assert parser.parse_args(["--json"]).format == "json"


def test_a_parser_whose_subcommand_has_another_format_gets_no_format_twin() -> None:
    parser = argparse.ArgumentParser(prog="demo")
    parser.add_argument("--json", action="store_true")
    export = parser.add_subparsers(dest="verb").add_parser("export")
    export.add_argument("--format", choices=("csv", "markdown"), default="markdown")
    assert align_json_options(parser) == 0
    assert json_twins(parser) == ()


def test_json_twins_names_what_was_added() -> None:
    parser = _tree()
    align_json_options(parser)
    flag = next(p for p in iter_parsers(parser) if p.prog == "demo flag")
    assert [twin.option_strings for twin in json_twins(flag)] == [["--format"]]
    assert json_twins(next(p for p in iter_parsers(parser) if p.prog == "demo both")) == ()
