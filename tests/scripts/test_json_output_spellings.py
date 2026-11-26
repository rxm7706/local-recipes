"""Every station verb that can print JSON accepts both spellings (steward Story 144.1, spec-pyforge-steward:CAP-185).

``pyforge.core.cli_output.align_json_options`` gives a parser that accepts ``--json`` the twin ``--format {text,json}``
and the reverse. Each station calls it once on its built parser. This file holds the result on the real parsers, each
where its package is installed (the guild environment carries doctor, herald, marshal, mason and steward; warden's own
suite holds warden, in ``tests/meta/test_json_output_spellings.py``): no parser may accept exactly one of the two
spellings, every twin writes the destination of the option it mirrors, and no abbreviation that resolved before the
twins were added turns ambiguous.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

cli_output = pytest.importorskip("pyforge.core.cli_output")

#: what is not aligned, and why
NOT_ALIGNED = {
    "scribe": "a typer app with no JSON option",
    "atlas": "Kedro's command line; its module entry points (python -m pyforge.atlas.*) keep --json alone",
}


def _doctor() -> list[argparse.ArgumentParser]:
    main = pytest.importorskip("pyforge.doctor.__main__")
    sources = pytest.importorskip("pyforge.doctor.sources.__main__")
    return [main._build_parser()[0], sources._build_parser()]  # noqa: SLF001


def _herald() -> list[argparse.ArgumentParser]:
    return [pytest.importorskip("pyforge.herald.cli")._build_parser()]  # noqa: SLF001


def _marshal() -> list[argparse.ArgumentParser]:
    return [pytest.importorskip("pyforge.marshal.cli.main")._build_parser()]  # noqa: SLF001


def _mason() -> list[argparse.ArgumentParser]:
    return [pytest.importorskip("pyforge.mason.cli").build_parser()]


def _steward() -> list[argparse.ArgumentParser]:
    return [pytest.importorskip("pyforge.steward.cli").build_parser()]


BUILDERS = {
    "doctor": _doctor,
    "herald": _herald,
    "marshal": _marshal,
    "mason": _mason,
    "steward": _steward,
}
#: aligned, and held by a test in the station's own suite because this lane's environment does not carry the station
HELD_IN_ITS_OWN_SUITE = {
    "warden": "src/shared/packages/pyforge-warden/tests/meta/test_json_output_spellings.py"
}


def _parsers(station: str) -> list[argparse.ArgumentParser]:
    return [
        current
        for built in BUILDERS[station]()
        for current in cli_output.iter_parsers(built)
    ]


def _has_another_format(parser: argparse.ArgumentParser) -> bool:
    """A ``--format`` that is not the text/json pair is another option that shares the name (a formatter list)."""
    for action in parser._actions:  # noqa: SLF001
        if "--format" in action.option_strings:
            return action.choices is None or set(action.choices) != set(
                cli_output.FORMAT_CHOICES
            )
    return False


def _a_subcommand_has_another_format(parser: argparse.ArgumentParser) -> bool:
    return any(
        _has_another_format(child)
        for action in parser._actions  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction)  # noqa: SLF001
        for child in action.choices.values()
    )


@pytest.mark.parametrize("station", sorted(BUILDERS))
def test_no_parser_accepts_exactly_one_spelling(station: str) -> None:
    lone = {
        current.prog: sorted(cli_output.json_spellings(current))
        for current in _parsers(station)
        if len(cli_output.json_spellings(current)) == 1
        and not _has_another_format(current)
        and not _a_subcommand_has_another_format(current)
    }
    assert lone == {}


@pytest.mark.parametrize("station", sorted(BUILDERS))
def test_every_twin_writes_the_destination_of_the_option_it_mirrors(
    station: str,
) -> None:
    checked = 0
    for current in _parsers(station):
        for twin in cli_output.json_twins(current):
            mirrored = [
                action
                for action in current._actions  # noqa: SLF001
                if action is not twin
                and action.dest == twin.dest
                and action.option_strings
            ]
            assert len(mirrored) == 1, (
                f"{current.prog}: {twin.option_strings} mirrors {len(mirrored)} option(s)"
            )
            namespace = argparse.Namespace()
            if "--format" in twin.option_strings:  # the twin of a --json flag
                twin(current, namespace, "json", "--format")
                assert getattr(namespace, twin.dest) is True, current.prog
                twin(current, namespace, "text", "--format")
                assert getattr(namespace, twin.dest) is False, current.prog
            else:  # the twin of a --format option
                twin(current, namespace, None, "--json")
                assert getattr(namespace, twin.dest) == "json", current.prog
            checked += 1
    assert checked, f"{station} has no verb that prints JSON"


@pytest.mark.parametrize("station", sorted(BUILDERS))
def test_no_abbreviation_reaches_a_twin(station: str) -> None:
    """Every prefix of ``--json`` and ``--format`` resolves as it would with the twins absent."""
    for current in _parsers(station):
        twins = cli_output.json_twins(current)
        for twin in twins:
            flag = twin.option_strings[0]
            for end in range(3, len(flag)):
                matches = current._get_option_tuples(flag[:end])  # noqa: SLF001
                assert all(match[0] not in twins for match in matches), (
                    f"{current.prog}: {flag[:end]}"
                )


@pytest.mark.parametrize("station", sorted(BUILDERS))
def test_aligning_a_built_parser_again_adds_nothing(station: str) -> None:
    assert all(
        cli_output.align_json_options(built) == 0 for built in BUILDERS[station]()
    )


def test_every_station_is_aligned_or_named_with_a_reason() -> None:
    roster = pytest.importorskip("pyforge.core.roster")
    groups = (set(BUILDERS), set(NOT_ALIGNED), set(HELD_IN_ITS_OWN_SUITE))
    assert set().union(*groups) == set(roster.STATIONS)
    assert sum(len(group) for group in groups) == len(
        roster.STATIONS
    )  # each station in exactly one group
    assert all(NOT_ALIGNED.values())
    repo = Path(__file__).resolve().parents[2]
    assert all((repo / path).is_file() for path in HELD_IN_ITS_OWN_SUITE.values())
