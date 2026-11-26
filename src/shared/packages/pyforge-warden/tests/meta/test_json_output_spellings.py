"""Warden's ``scan`` takes both spellings for JSON (warden Story 32.1, spec-pyforge-steward:CAP-185).

The repo-root fleet test holds the five stations the guild environment carries; warden is installed only in its own
environment, so its parser is held here.
"""

from __future__ import annotations

import pytest
from pyforge.core.cli_output import iter_parsers, json_spellings, json_twins

from pyforge.warden import cli


def _scan():
    parser, _ = cli._build_parser()  # noqa: SLF001 -- the built tree is the surface under test
    return next(current for current in iter_parsers(parser) if current.prog.endswith(" scan"))


def test_scan_takes_both_spellings() -> None:
    assert json_spellings(_scan()) == {"--json", "--format"}
    assert [twin.option_strings for twin in json_twins(_scan())] == [["--json"]]


def test_both_spellings_parse_to_the_same_format() -> None:
    parser, _ = cli._build_parser()  # noqa: SLF001
    assert parser.parse_args(["scan", "--json"]).format == "json"
    assert parser.parse_args(["scan", "--format", "json"]).format == "json"
    assert parser.parse_args(["scan"]).format == parser.parse_args(["scan", "--format", "text"]).format


def test_the_twin_is_matched_only_in_full() -> None:
    parser, _ = cli._build_parser()  # noqa: SLF001
    with pytest.raises(SystemExit):
        parser.parse_args(["scan", "--js"])
